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


FOLD_LOG = """\
commit:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|2026-11-03|split track into target|
diff --git a/handoffs/active/old.md b/handoffs/active/old.md
--- a/handoffs/active/old.md
+++ b/handoffs/active/old.md
-- [ ] port the kernel
-- [x] closed long ago
-- [ ] BRF box
+- [x] BRF box
diff --git a/handoffs/active/target.md b/handoffs/active/target.md
--- a/handoffs/active/target.md
+++ b/handoffs/active/target.md
+- [ ] port the kernel
+- [x] closed long ago
+- [ ] migrated with new lint tag (a)
commit:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb|2026-11-03||ws58 (backlog refactor 2026-11, operator-approved)
diff --git a/handoffs/active/x.md b/handoffs/active/x.md
--- a/handoffs/active/x.md
+++ b/handoffs/active/x.md
-- [ ] moved again
diff --git a/handoffs/active/y.md b/handoffs/active/y.md
--- a/handoffs/active/y.md
+++ b/handoffs/active/y.md
+- [ ] moved again
commit:cccccccccccccccccccccccccccccccccccccccc|2026-11-02||
diff --git a/handoffs/active/y.md b/handoffs/active/y.md
--- a/handoffs/active/y.md
+++ b/handoffs/active/y.md
-- [ ] real work
+- [x] real work
+- [ ] newly filed
"""


class ActivityFoldCommits(unittest.TestCase):
    def test_moved_boxes_paired_and_fold_commits_excluded(self):
        act = server._parse_activity_log(FOLD_LOG)
        self.assertEqual(act["moved"], 3)          # 2 in the Repoint commit + 1 in the D9-ack one
        self.assertEqual(act["fold_commits"], 2)
        self.assertEqual(act["commits"], 2)        # the Repoint fold is excluded; D9-ack-only is not
        self.assertEqual(act["boxes_checked"], 2)  # the in-place BRF tick + the ordinary tick
        self.assertEqual(act["boxes_added"], 1)    # only the ordinary commit files a task
        self.assertEqual(act["handoffs_touched"], 2)
        self.assertEqual(set(act), set(server._ACT_EMPTY))

    def test_by_day_rows_and_one_refactor_marker(self):
        rows = server._parse_activity_log_by_day(FOLD_LOG)
        self.assertEqual([r["date"] for r in rows], ["2026-11-03", "2026-11-02"])
        day = rows[0]
        self.assertEqual((day["commits"], day["fold_commits"], day["moved"],
                          day["boxes_added"], day["boxes_checked"]), (1, 2, 3, 0, 1))
        marks = server._refactor_markers(rows)
        self.assertEqual(len(marks), 1)
        self.assertEqual(marks[0]["date"], "2026-11-03")
        self.assertEqual(marks[0]["moved"], 3)
        self.assertEqual(marks[0]["commits"], ["aaaaaaaaaaaa", "bbbbbbbbbbbb"])

    def test_refactor_ack_without_moves_counts_normally(self):
        log = ("commit:dddd|2026-11-03||ws58 (backlog refactor 2026-11, operator-approved)\n"
               "diff --git a/handoffs/active/r.md b/handoffs/active/r.md\n"
               "+- [ ] BRF-T9 new tooling task\n+- [x] BRF-T8 done\n")
        act = server._parse_activity_log(log)
        self.assertEqual((act["commits"], act["boxes_added"], act["boxes_checked"],
                          act["moved"], act["fold_commits"]), (1, 1, 1, 0, 0))
        self.assertEqual(server._refactor_markers(server._parse_activity_log_by_day(log)), [])

    def test_unfolded_log_is_unchanged(self):
        plain = FOLD_LOG.split("commit:cccc")[1]
        act = server._parse_activity_log("commit:cccc" + plain)
        self.assertEqual((act["boxes_checked"], act["boxes_added"], act["moved"]), (1, 1, 0))
        self.assertEqual(server._refactor_markers(server._parse_activity_log_by_day("commit:cccc" + plain)), [])


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
