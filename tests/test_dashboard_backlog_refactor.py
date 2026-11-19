"""Backlog refactor 2026-11 dashboard fixes (BRF-T2-2, BRF-T2-3, BRF-T2-4).

Folded sources get their own lifecycle/column, roll-up parents never double-count,
fold commits report moved boxes instead of progress, and `.folded.json` redirects keep
detail ids, queue refs, rowflow rows and session slugs attached to a graph node.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from dashboard import handoff_parser as hp
from dashboard import pipeline_status as ps
from dashboard import server

TARGET = """# Target handoff

**Status**: active

## Track: merged work

- [ ] **T-1** [roll-up] Non-dispatchable parent.
- [ ] T-1a child one
- [x] T-1b child two
"""

SOURCE = """# Old source

> **Folded into [target](../active/target.md#track-merged-work)** on 2026-11-03 (BRF).

- [x] already closed item
"""


def _tree(root: Path, folded: dict | None = None) -> Path:
    h = root / "handoffs"
    for state in hp.STATES:
        (h / state).mkdir(parents=True)
    (h / "active" / "target.md").write_text(TARGET)
    (h / "completed" / "old.md").write_text(SOURCE)
    if folded is not None:
        (h / ".folded.json").write_text(json.dumps(folded))
    return h


FOLDED = {"files": {"old.md": {"target": "target.md", "track": "Track: merged work"}},
          "ids": {"OLD-01": "TGT-01"}}


class ParserFoldedAndRollup(unittest.TestCase):
    def test_banner_sets_folded_lifecycle_and_target(self):
        self.assertEqual(hp.parse_folded(SOURCE), "target.md")
        with tempfile.TemporaryDirectory() as d:
            h = _tree(Path(d))
            card = hp.parse_file("completed", h / "completed" / "old.md")
        self.assertEqual(card["lifecycle"], "folded")
        self.assertEqual(card["folded_into"], "target.md")

    def test_task_line_remark_is_not_a_banner(self):
        text = "# X\n\n- [x] MH-4 eval — **Folded into AR-3** (2026-04-12).\n"
        self.assertIsNone(hp.parse_folded(text))
        self.assertEqual(hp.parse_folded("> **Folded into** somewhere\n"), "")

    def test_rollup_boxes_excluded_from_count_tasks(self):
        done, total, source, tasks = hp.count_tasks(TARGET)
        self.assertEqual((done, total, source), (1, 2, "checkboxes"))
        self.assertFalse(any("[roll-up]" in t["text"] for t in tasks))
        self.assertEqual(hp.count_open_rollups(TARGET), 1)

    def test_board_puts_folded_source_in_its_own_column(self):
        with tempfile.TemporaryDirectory() as d:
            board = hp.build_board(_tree(Path(d)))
        self.assertEqual(board["counts"]["completed"], 0)
        self.assertEqual(board["counts"]["folded"], 1)
        self.assertEqual(board["columns"]["folded"][0]["id"], "completed/old")
        self.assertEqual(board["counts"]["active"], 1)


class FoldedMap(unittest.TestCase):
    def test_absent_file_is_empty_map(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(hp.load_folded_map(Path(d)), {"files": {}, "ids": {}})
            (Path(d) / ".folded.json").write_text("{not json")
            self.assertEqual(hp.load_folded_map(Path(d)), {"files": {}, "ids": {}})

    def test_shapes_chain_and_form(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".folded.json").write_text(json.dumps(
                {"handoffs/active/a.md": "handoffs/active/b.md", "b.md": "c.md"}))
            fmap = hp.load_folded_map(Path(d))
        self.assertEqual(hp.resolve_folded_file("a.md", fmap), "c.md")
        self.assertEqual(hp.resolve_folded_file("handoffs/completed/a.md", fmap), "handoffs/active/c.md")
        self.assertEqual(hp.resolve_folded_file("handoffs/active/z.md", fmap), "handoffs/active/z.md")
        cyc = {"files": {"x.md": {"target": "y.md"}, "y.md": {"target": "x.md"}}, "ids": {}}
        self.assertIn(hp.resolve_folded_file("x.md", cyc), ("x.md", "y.md"))
        self.assertEqual(hp.resolve_folded_id("OLD-01", {"ids": {"OLD-01": {"target": "TGT-01"}}}), "TGT-01")




class DetailAndQueueRedirect(unittest.TestCase):
    def test_retired_detail_id_resolves_to_target_card(self):
        with tempfile.TemporaryDirectory() as d:
            h = _tree(Path(d), FOLDED)
            with mock.patch.object(server, "HANDOFF_DIR", h):
                code, card = server.detail_payload("active/old")
                self.assertEqual(code, 200)
                self.assertEqual(card["id"], "active/target")
                self.assertEqual(card["redirected_from"], "active/old")
                self.assertEqual(card["anchor"], "Track: merged work")
                code, card = server.detail_payload("completed/old")   # the source itself still opens
                self.assertEqual((code, card["lifecycle"]), (200, "folded"))
                self.assertEqual(server.detail_payload("active/nope")[0], 404)

    def test_no_map_means_plain_404(self):
        with tempfile.TemporaryDirectory() as d:
            h = _tree(Path(d))
            with mock.patch.object(server, "HANDOFF_DIR", h):
                self.assertEqual(server.detail_payload("active/old")[0], 404)

    def test_queue_spec_ref_resolves_through_fold(self):
        with tempfile.TemporaryDirectory() as d:
            h = _tree(Path(d), FOLDED)
            bus = Path(d) / "bus"
            bus.mkdir()
            rows = [{"task_id": "t1", "status": "READY", "lane": "none", "gating": "none",
                     "spec_ref": "handoffs/active/old.md#L4"},
                    {"task_id": "t2", "status": "READY", "lane": "none", "gating": "none",
                     "spec_ref": "handoffs/active/target.md#L2"}]
            (bus / "queue.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            with mock.patch.object(server, "HANDOFF_DIR", h), mock.patch.object(server, "_BUS_ROOT", bus):
                q = server.queue_payload()
        by = {r["task_id"]: r for r in q["rows"]}
        self.assertEqual(q["count"], 2)
        self.assertEqual(by["t1"]["spec_ref_resolved"], "handoffs/active/target.md#L4")
        self.assertNotIn("spec_ref_resolved", by["t2"])


class PipelineFoldedScratchTree(unittest.TestCase):
    """Every ready/running row and every session slug resolves to a graph node after a fold."""

    def _flags(self, root: Path) -> Path:
        f = root / "flags"
        for sub in ("grants", "ready", "dryrun/r-ready"):
            (f / sub).mkdir(parents=True)
        (f / "ready" / "r-ready.json").write_text(json.dumps({"handoff_task": "handoffs/active/old.md:OLD-01"}))
        (f / "dryrun" / "r-ready" / "PASS.json").write_text("{}")
        (f / "ready" / "r-run.json").write_text(json.dumps({"handoff_task": "handoffs/completed/old.md:OLD-02"}))
        (f / "grants" / "r-run.grant").write_text("regions=q1 kind=bench")
        (f / "handoff-sessions.json").write_text(json.dumps({"max_live": 2, "sessions": {
            "old-slug": {"handoff": "handoffs/active/old.md", "status": "suspended"},
            "tgt-slug": {"handoff": "handoffs/active/target.md", "status": "suspended"}}}))
        (f / "handoff-sessions.log").write_text("")
        return f

    def test_rows_and_slugs_attach_to_the_target_node(self):
        graph = {"nodes": [{"id": "TGT-01", "handoff": "target.md", "state": "active", "open": 3,
                            "priority_basis": {"tier": 3}}]}
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            h = _tree(root, FOLDED)
            p = ps.build_payload(self._flags(root), time.time(), graph=graph, handoff_root=h)
            nodes = {f"handoffs/{n['state']}/{n['handoff']}" for n in graph["nodes"]}
            rows = ps.compute_payload(self._flags_again(root), time.time(), hp.load_folded_map(h))["rows"]
        live_rows = [r for r in rows.values() if r["state"] in ("ready", "running")]
        self.assertEqual(len(live_rows), 2)
        for r in live_rows:
            self.assertIn(r["handoff"], nodes)
        for s in p["queued_next"] + p["sessions"]:
            self.assertIn(s["handoff"], nodes)
        (tgt,) = p["overview"]["handoffs"]
        self.assertEqual((tgt["ready_rows"], tgt["running_rows"]), (1, 1))
        self.assertEqual(tgt["open"], 2)          # 3 open minus the one [roll-up] parent
        self.assertEqual(tgt["rollup_open"], 1)

    def _flags_again(self, root: Path) -> Path:
        return root / "flags"

    def test_rollup_only_handoff_is_done(self):
        graph = {"nodes": [{"id": "TGT-01", "handoff": "target.md", "state": "active", "open": 1,
                            "priority_basis": {"tier": 7}}]}
        out = ps.classify_handoffs(graph, {}, {"handoffs/active/target.md": 1})
        self.assertEqual(out["handoffs"][0]["class"], "done")
        self.assertEqual(out["class_counts"]["done"], 1)
        unchanged = ps.classify_handoffs(graph, {})
        self.assertEqual(unchanged["handoffs"][0]["class"], "non-inference")


if __name__ == "__main__":
    unittest.main()
