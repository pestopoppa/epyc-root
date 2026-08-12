#!/usr/bin/env python3
"""Unit tests for the handoff dashboard parser.

Stdlib ``unittest`` only (no pytest dependency) so it runs anywhere with
``python3 tests/test_handoff_parser.py``; pytest also discovers it.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dashboard import handoff_parser as hp  # noqa: E402
from dashboard import server  # noqa: E402


CHECKBOX_DOC = """# ColBERT Reranker

**Status**: refreshed 2026-05-28; S5 gate rechecked — some long prose here.
**Created**: 2026-04-05 (extracted from something)
**Updated**: 2026-05-28
**Priority**: MEDIUM

## Work Items
- [x] **S1: instrument** ✅ 2026-04-14 — Added the thing, lots of detail here.
- [x] S2 done
- [ ] S3 not done yet
  - [ ] nested subtask
"""

NO_CHECKBOX_DOC = """# Prose-only handoff

**Status**: Phase 1+2+3 LANDED for local stack.
**Created**: 2026-04-30
**Priority**: HIGH (cheap to pilot; high payoff)

## Objective
No checkboxes here, progress lives in prose. ✅ Phase 1 ✅ Phase 2
"""

PLAIN_DOC = """# Plain handoff

**Priority**: P0 — critical path

## Body
Nothing measurable here.
"""

BLOCKED_DOC = """# A blocked handoff

**Status**: BLOCKED on external model release — waiting.
**Priority**: HIGH

## Notes
stuck.
"""

BLOCKED_MD_WITH_ROW = """# Blocked Tasks

## Current Blocked Work

| Task | Blocked On | Priority | Handoff | Current State |
|------|------------|----------|---------|---------------|
| Real blocked thing | upstream PR | HIGH | [foo](../active/foo.md) | waiting on merge |
"""

BLOCKED_MD_PLACEHOLDER = """# Blocked Tasks

## Current Blocked Work

| Task | Blocked On | Priority | Handoff | Current State |
|------|------------|----------|---------|---------------|
| _None currently tracked here_ | — | — | — | nothing blocked now |
"""


class MetadataTests(unittest.TestCase):
    def test_metadata_stops_at_first_heading(self):
        meta = hp.parse_metadata(CHECKBOX_DOC)
        self.assertEqual(meta["priority"], "MEDIUM")
        self.assertIn("status", meta)
        # A `**bold**` inside the body must not leak into metadata.
        self.assertNotIn("s1: instrument", " ".join(meta.keys()))

    def test_title(self):
        self.assertEqual(hp.parse_title(CHECKBOX_DOC, "x"), "ColBERT Reranker")
        self.assertEqual(hp.parse_title("no heading", "my-handoff_name"),
                         "My Handoff Name")

    def test_priority_mapping(self):
        self.assertEqual(hp.parse_priority({"priority": "MEDIUM"}), "MEDIUM")
        self.assertEqual(hp.parse_priority({"priority": "HIGH (cheap)"}), "HIGH")
        self.assertEqual(hp.parse_priority({"priority": "ACTIVE-HIGH — x"}), "HIGH")
        self.assertEqual(hp.parse_priority({"priority": "P0 critical"}), "P0")
        self.assertEqual(hp.parse_priority({"priority": "P2"}), "MEDIUM")
        self.assertEqual(hp.parse_priority({}), "NONE")

    def test_dates(self):
        d = hp.parse_dates(hp.parse_metadata(CHECKBOX_DOC))
        self.assertEqual(d["created"], "2026-04-05")
        self.assertEqual(d["updated"], "2026-05-28")
        # invalid date falls through to None
        self.assertIsNone(hp._first_date("2026-13-40 nonsense"))


class TaskCountTests(unittest.TestCase):
    def test_checkboxes(self):
        done, total, source, tasks = hp.count_tasks(CHECKBOX_DOC)
        self.assertEqual(source, "checkboxes")
        self.assertEqual(total, 4)   # 2 done + 1 open + 1 nested open
        self.assertEqual(done, 2)
        self.assertEqual(len(tasks), 4)
        self.assertTrue(tasks[0]["done"])

    def test_marker_fallback(self):
        done, total, source, tasks = hp.count_tasks(NO_CHECKBOX_DOC)
        self.assertEqual(source, "markers")
        self.assertEqual(total, 0)
        self.assertEqual(done, 2)     # two ✅
        self.assertEqual(tasks, [])

    def test_no_progress(self):
        done, total, source, _ = hp.count_tasks(PLAIN_DOC)
        self.assertEqual((done, total, source), (0, 0, "none"))


class ScrubTests(unittest.TestCase):
    def test_scrub_removes_script(self):
        dirty = "ok <script>alert(1)</script> and <img onerror=alert(2)> and javascript:x"
        clean = hp._scrub_html(dirty)
        self.assertNotIn("<script", clean)
        self.assertNotIn("onerror", clean)
        self.assertNotIn("javascript:", clean)


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for state in hp.STATES:
            (self.root / state).mkdir()
        (self.root / "active" / "colbert.md").write_text(CHECKBOX_DOC)
        (self.root / "active" / "prose.md").write_text(NO_CHECKBOX_DOC)
        (self.root / "active" / "stuck.md").write_text(BLOCKED_DOC)
        (self.root / "active" / "README.md").write_text("# skip me")
        (self.root / "active" / "stray.yaml").write_text("skip: true")
        (self.root / "completed" / "old.md").write_text(PLAIN_DOC)
        # nested dir should be ignored (non-recursive)
        (self.root / "completed" / "sub").mkdir()
        (self.root / "completed" / "sub" / "chapter.md").write_text(CHECKBOX_DOC)

    def tearDown(self):
        self.tmp.cleanup()

    def test_iter_skips_readme_and_nonmd(self):
        names = {p.name for _, p in hp.iter_handoff_files(self.root)}
        self.assertIn("colbert.md", names)
        self.assertNotIn("README.md", names)
        self.assertNotIn("stray.yaml", names)
        self.assertNotIn("chapter.md", names)  # nested

    def test_status_blocked_routes_to_blocked_column(self):
        board = hp.build_board(self.root)
        active_ids = {c["id"] for c in board["columns"]["active"]}
        blocked_titles = {c["title"] for c in board["columns"]["blocked"]}
        self.assertIn("active/colbert", active_ids)
        self.assertNotIn("active/stuck", active_ids)   # moved out of active
        self.assertIn("A blocked handoff", blocked_titles)
        self.assertEqual(board["counts"]["active"], 2)  # colbert + prose

    def test_blocked_table_row_parsed(self):
        (self.root / "blocked" / "BLOCKED.md").write_text(BLOCKED_MD_WITH_ROW)
        board = hp.build_board(self.root)
        titles = [c["title"] for c in board["columns"]["blocked"]]
        self.assertIn("Real blocked thing", titles)
        row = [c for c in board["columns"]["blocked"] if c["title"] == "Real blocked thing"][0]
        self.assertEqual(row["id"], "active/foo")
        self.assertEqual(row["priority"], "HIGH")
        self.assertEqual(row["blocked_on"], "upstream PR")

    def test_blocked_placeholder_skipped(self):
        (self.root / "blocked" / "BLOCKED.md").write_text(BLOCKED_MD_PLACEHOLDER)
        board = hp.build_board(self.root)
        # only the status-derived 'stuck' handoff, no placeholder row
        titles = [c["title"] for c in board["columns"]["blocked"]]
        self.assertEqual(titles, ["A blocked handoff"])

    def test_detail_has_body_and_tasks(self):
        card = hp.parse_file("active", self.root / "active" / "colbert.md", detail=True)
        self.assertIn("body", card)
        self.assertEqual(len(card["tasks"]), 4)
        self.assertGreater(len(card["body"]), 50)

    def test_backlog_priority_buckets_and_dead_lane(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for st in hp.STATES:
                (root / st).mkdir()

            today = datetime.now(timezone.utc).date()
            def ymd(days):
                return (today - timedelta(days=days)).strftime("%Y-%m-%d")

            (root / "active" / "p0_stale.md").write_text(
                f"# P0 stale\n"
                f"**Updated**: {ymd(95)}\n"
                f"**Priority**: P0\n"
                "## Work\n"
                "- [x] done\n"
                "- [ ] open\n"
            )
            (root / "active" / "high_stale.md").write_text(
                f"# High stale\n"
                f"**Updated**: {ymd(40)}\n"
                f"**Priority**: HIGH\n"
                "## Work\n"
                "- [ ] first\n"
                "- [ ] second\n"
            )
            (root / "active" / "low_fresh.md").write_text(
                f"# Low fresh\n"
                f"**Updated**: {ymd(5)}\n"
                f"**Priority**: LOW\n"
                "## Work\n"
                "- [ ] first\n"
            )
            (root / "active" / "none_no_date.md").write_text(
                "# Missing date\n"
                "**Priority**: LOW\n"
                "## Work\n"
                "No checkboxes here.\n"
            )
            (root / "completed" / "finished.md").write_text(
                "# Finished\n"
                "## Work\n"
                "- [x] completed task\n"
            )

            board = hp.build_board(root)
            backlog = board["backlog"]

            self.assertEqual(backlog["open_handoffs"], 4)
            self.assertEqual(backlog["open_tasks"], 4)
            self.assertEqual(backlog["open_tasks_done"], 1)
            self.assertEqual(backlog["all_tasks_done"], 2)
            self.assertEqual(backlog["all_tasks_total"], 6)
            self.assertEqual(backlog["open_untracked_handoffs"], 1)
            self.assertEqual(backlog["dead_lane"]["over_30"], 2)
            self.assertEqual(backlog["dead_lane"]["over_90"], 1)
            candidates = backlog["dead_lane"]["candidates"]
            self.assertEqual(candidates[0]["id"], "active/p0_stale")
            self.assertEqual(candidates[0]["lane"], "over_90")
            self.assertEqual(candidates[1]["id"], "active/high_stale")
            self.assertEqual(candidates[1]["lane"], "over_30")

            buckets = {b["priority"]: b for b in backlog["priority_buckets"]}
            self.assertEqual(buckets["P0"]["open_handoffs"], 1)
            self.assertEqual(buckets["P0"]["open_tasks_total"], 2)
            self.assertEqual(buckets["P0"]["open_tasks_done"], 1)
            self.assertEqual(buckets["HIGH"]["open_handoffs"], 1)
            self.assertEqual(buckets["HIGH"]["open_tasks_total"], 2)
            self.assertEqual(buckets["LOW"]["open_handoffs"], 2)
            self.assertEqual(buckets["LOW"]["open_untracked_handoffs"], 1)
            self.assertEqual(backlog["dead_lane"]["unknown_activity"], 1)


class FrontendContractTests(unittest.TestCase):
    def test_backlog_and_task_flow_use_absolute_and_newly_filed_contracts(self):
        html = (_REPO / "dashboard" / "static" / "handoffs.html").read_text()
        self.assertIn('bk.all_tasks_done, l: "tasks completed (all tracked)"', html)
        # E8-PANELS-c. This assertion used to read
        #     assertNotIn("const pctAll = bk.pct_all_done", html)
        # which pinned a SPELLING, not a property: that exact expression no
        # longer exists anywhere, so the guard passed while `bk.pct_all_done`
        # was still being rendered through a different expression. A guard that
        # forbids one way of writing a thing does not forbid the thing.
        #
        # The property that actually matters is the one the row is about: an
        # all-scope percentage has an INFLATED DENOMINATOR (intake sweeps file
        # tasks faster than they close), so shown bare it reads as decline. It
        # may appear ONLY if it is unambiguously scope-labelled, and only
        # alongside the open-scope figure it would otherwise be confused with.
        if "bk.pct_all_done" in html:
            self.assertIn("% done · all scope", html,
                          "pct_all_done is rendered without its scope label — bare, it reads "
                          "as decline whenever an intake sweep inflates the denominator")
            self.assertIn("% done · open scope", html,
                          "all-scope percentage shown without the open-scope figure beside it")
        self.assertIn("const filed=w=>(w.newly_filed!=null?w.newly_filed:w.opened)||0;", html)
        self.assertIn("tasks_newly_filed!=null", html)
        self.assertIn("tasks newly filed vs completed per week", html)


class PathTraversalTests(unittest.TestCase):
    """The detail endpoint's id must never escape the handoffs directory."""

    def test_rejects_traversal_and_bad_state(self):
        for bad in ("../../etc/passwd", "active/../../etc/passwd",
                    "/etc/passwd", "foo/bar", "active/", "", "active/a/b"):
            status, _ = server.detail_payload(bad)
            self.assertEqual(status, 404, f"{bad!r} should be rejected")

    def test_valid_id_shape_accepts_real_file(self):
        # Uses the live repo; a known checkbox handoff should resolve.
        status, card = server.detail_payload("active/colbert-reranker-web-research")
        # 200 if present in this checkout, 404 if it was moved — but never 500.
        self.assertIn(status, (200, 404))


class RegressionTests(unittest.TestCase):
    """Defects found + confirmed by the adversarial review."""

    def test_priority_anchored_to_leading_token(self):
        # keywords in trailing prose / inside words must not misclassify
        self.assertEqual(hp.parse_priority({"priority": "MED — start today (no blockers)"}), "MEDIUM")
        self.assertEqual(hp.parse_priority({"priority": "P2 — medium effort, high payoff"}), "MEDIUM")
        self.assertEqual(hp.parse_priority({"priority": "MEDIUM priority, high payoff"}), "MEDIUM")
        self.assertEqual(hp.parse_priority({"priority": "GATED — highest-ceiling program"}), "NONE")
        self.assertEqual(hp.parse_priority({"priority": "ACTIVE-HIGH — bench only"}), "HIGH")
        self.assertEqual(hp.parse_priority({"priority": "High"}), "HIGH")
        # BLOCKED.md-cell path shares the fix
        self.assertEqual(hp._priority_from_token("MED"), "MEDIUM")

    def test_yaml_frontmatter_parsed(self):
        doc = ("---\ntitle: Real Title Here\npriority: HIGH\ncreated: 2026-05-27\n"
               "status: active work\n---\n\nBody\n\n## Section\n")
        meta = hp.parse_metadata(doc)
        self.assertEqual(hp.parse_priority(meta), "HIGH")
        self.assertEqual(hp.parse_dates(meta)["created"], "2026-05-27")

    def test_yaml_title_fallback_when_no_h1(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.md"
            p.write_text("---\ntitle: Real Title Here\npriority: HIGH\n---\n\nno h1.\n")
            card = hp.parse_file("active", p, detail=True)
            self.assertEqual(card["title"], "Real Title Here")
            self.assertEqual(card["priority"], "HIGH")

    def test_bulleted_metadata_parsed(self):
        doc = ("# T\n\n- **Priority**: High\n- **Created**: 2026-02-13\n"
               "- **Status**: IMPLEMENTATION COMPLETE\n\n## Body\n")
        meta = hp.parse_metadata(doc)
        self.assertEqual(hp.parse_priority(meta), "HIGH")
        self.assertEqual(hp.parse_dates(meta)["created"], "2026-02-13")
        self.assertTrue(meta.get("status", "").startswith("IMPLEMENTATION"))

    def test_date_key_synonyms(self):
        self.assertEqual(hp.parse_dates({"last updated": "2026-06-26"})["updated"], "2026-06-26")
        self.assertEqual(hp.parse_dates({"opened": "2026-01-01 (kickoff)"})["created"], "2026-01-01")

    def test_neg_date_descending(self):
        # newest-updated card sorts first within a priority group
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for s in hp.STATES:
                (root / s).mkdir()
            (root / "active" / "older.md").write_text("# Older\n**Priority**: HIGH\n**Updated**: 2026-01-01\n")
            (root / "active" / "newer.md").write_text("# Newer\n**Priority**: HIGH\n**Updated**: 2026-07-01\n")
            titles = [c["title"] for c in hp.build_board(root)["columns"]["active"]]
            self.assertLess(titles.index("Newer"), titles.index("Older"))

    def test_server_null_byte_id_is_404_not_500(self):
        status, _ = server.detail_payload("active/foo\x00bar")
        self.assertEqual(status, 404)

    def test_timeline_non_dict_json_tolerated(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tl.json"
            p.write_text("[]")
            orig = server.TIMELINE_PATH
            try:
                server.TIMELINE_PATH = p
                out = server.timeline_payload()
                self.assertIsInstance(out, dict)
                self.assertIn("error", out)
            finally:
                server.TIMELINE_PATH = orig


class ActivityTests(unittest.TestCase):
    """The git/mtime-derived recency signal that drives active/blocked ordering."""

    def _root(self, d):
        root = Path(d)
        for s in hp.STATES:
            (root / s).mkdir()
        return root

    def test_git_activity_reorders_active(self):
        # older.md has the newer *frontmatter* date, but a git commit touched
        # newer.md more recently — file_activity must flip the order.
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            (root / "active" / "older.md").write_text("# Older\n**Priority**: HIGH\n**Updated**: 2026-05-01\n")
            (root / "active" / "newer.md").write_text("# Newer\n**Priority**: HIGH\n**Updated**: 2026-01-01\n")
            # Without the git map, frontmatter wins → Older first.
            plain = [c["title"] for c in hp.build_board(root)["columns"]["active"]]
            self.assertLess(plain.index("Older"), plain.index("Newer"))
            # With a fresh git touch on newer, it bubbles to the top.
            fa = {"active/newer": "2026-09-01"}
            titles = [c["title"] for c in
                      hp.build_board(root, file_activity=fa)["columns"]["active"]]
            self.assertLess(titles.index("Newer"), titles.index("Older"))

    def test_max_rule_git_beats_stale_updated(self):
        # A stale frontmatter Updated must not out-rank a newer commit date.
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            (root / "active" / "a.md").write_text("# A\n**Priority**: HIGH\n**Updated**: 2026-02-01\n")
            board = hp.build_board(root, file_activity={"active/a": "2026-08-15"})
            card = board["columns"]["active"][0]
            self.assertEqual(card["activity"], "2026-08-15")
            self.assertEqual(card["activity_source"], "git")

    def test_stale_git_loses_to_newer_updated(self):
        # Symmetric: a newer frontmatter Updated beats an older git date (max rule).
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            (root / "active" / "a.md").write_text("# A\n**Priority**: HIGH\n**Updated**: 2026-08-01\n")
            board = hp.build_board(root, file_activity={"active/a": "2026-03-01"})
            card = board["columns"]["active"][0]
            self.assertEqual(card["activity"], "2026-08-01")
            self.assertEqual(card["activity_source"], "updated")

    def test_dirty_mtime_wins_for_dirty_id_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            f = root / "active" / "wip.md"
            f.write_text("# Wip\n**Priority**: HIGH\n**Created**: 2026-01-01\n")
            mtime = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc).timestamp()
            os.utime(f, (mtime, mtime))
            # Not dirty → mtime ignored, falls back to created.
            clean = hp.build_board(root)["columns"]["active"][0]
            self.assertEqual(clean["activity_source"], "created")
            self.assertEqual(clean["activity"], "2026-01-01")
            # Dirty → mtime date surfaces as the activity via the wip source.
            dirty = hp.build_board(root, dirty_ids={"active/wip"})["columns"]["active"][0]
            self.assertEqual(dirty["activity_source"], "wip")
            self.assertEqual(dirty["activity"], "2026-06-20")

    def test_no_signals_backcompat(self):
        # No kwargs: activity is the frontmatter updated (else created), labelled honestly.
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            (root / "active" / "u.md").write_text("# U\n**Priority**: HIGH\n**Updated**: 2026-05-05\n")
            (root / "active" / "c.md").write_text("# C\n**Priority**: HIGH\n**Created**: 2026-04-04\n")
            by_id = {c["id"]: c for c in hp.build_board(root)["columns"]["active"]}
            self.assertEqual(by_id["active/u"]["activity"], "2026-05-05")
            self.assertEqual(by_id["active/u"]["activity_source"], "updated")
            self.assertEqual(by_id["active/c"]["activity"], "2026-04-04")
            self.assertEqual(by_id["active/c"]["activity_source"], "created")

    def test_no_dates_yields_none_activity(self):
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            (root / "active" / "bare.md").write_text("# Bare\n**Priority**: LOW\n\nno dates\n")
            card = hp.build_board(root)["columns"]["active"][0]
            self.assertIsNone(card["activity"])
            self.assertIsNone(card["activity_source"])

    def test_blocked_table_row_activity_none_and_sorts(self):
        # Synthetic BLOCKED.md rows carry no activity; the sort key must tolerate it.
        with tempfile.TemporaryDirectory() as d:
            root = self._root(d)
            (root / "blocked" / "BLOCKED.md").write_text(
                "## Current Blocked Work\n\n"
                "| Item | Blocked on | Priority | Handoff | Status |\n"
                "|---|---|---|---|---|\n"
                "| Stuck thing | model release | HIGH | | waiting |\n")
            board = hp.build_board(root, file_activity={"x": "2026-09-09"})
            row = board["columns"]["blocked"][0]
            self.assertIsNone(row["activity"])
            self.assertIsNone(row["activity_source"])

    def test_neg_date_accepts_full_iso_timestamp(self):
        # Defense: a full ISO timestamp must not silently sort to epoch.
        self.assertLess(hp._neg_date("2026-07-01T12:00:00"), hp._neg_date("2026-01-01"))
        self.assertLess(hp._neg_date("2026-07-01"), 0.0)
        self.assertEqual(hp._neg_date(None), 0.0)
        self.assertEqual(hp._neg_date("not-a-date"), 0.0)


class BlockedStatusTests(unittest.TestCase):
    """Routing an ``active/`` handoff to Blocked from its free-text status."""

    def test_positive_signals(self):
        for s in [
            "BLOCKED on external model release — waiting",
            "IN PROGRESS — first real backup remains blocked on a real off-host target",
            "refreshed — active but blocked on model availability check",
            "production flag remains OFF pending operator rollout decision",
            "PROPOSAL — needs operator approval before any implementation",
            "QUEUED — awaiting long-context eval datasets",
            "PARKED pending a design session",
            "waiting on upstream PR merge",
            "on hold until Q3",
        ]:
            self.assertTrue(hp._is_blocked_status(s), s)

    def test_negative_and_trap_phrases(self):
        # Trap phrases that only *look* blocked must stay in Active.
        for s in [
            "cherry-pick BLOCKED, but the fresh-upstream-build path is VERIFIED WORKING",
            "parked Phase 0 falsification gate; does not block KB-RAG",
            "QUEUED — blocker P3 long-context eval datasets resolved (2026-04-05)",
            "the retrain blocker was cleared last week",
            "this work is unblocked and shipping",
            "IN PROGRESS — Phase 2 routing done",
            "COMPLETE — landed 2026-06-18",
            "",
        ]:
            self.assertFalse(hp._is_blocked_status(s), s)

    def test_routes_active_to_blocked_column(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for st in hp.STATES:
                (root / st).mkdir()
            (root / "active" / "b.md").write_text(
                "# B\n**Priority**: HIGH\n**Status**: IN PROGRESS — waiting on upstream fix\n")
            (root / "active" / "a.md").write_text(
                "# A\n**Priority**: HIGH\n**Status**: IN PROGRESS — going well\n")
            board = hp.build_board(root)
            self.assertIn("B", [c["title"] for c in board["columns"]["blocked"]])
            self.assertIn("A", [c["title"] for c in board["columns"]["active"]])
            self.assertNotIn("B", [c["title"] for c in board["columns"]["active"]])


class ServerActivityLoaderTests(unittest.TestCase):
    """``server._load_file_activity`` tolerates every bad-artifact shape."""

    def _with_timeline(self, content):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tl.json"
            if content is not None:
                p.write_text(content)
            orig = server.TIMELINE_PATH
            try:
                server.TIMELINE_PATH = p
                return server._load_file_activity()
            finally:
                server.TIMELINE_PATH = orig

    def test_missing_file(self):
        self.assertEqual(self._with_timeline(None), {})

    def test_corrupt_json(self):
        self.assertEqual(self._with_timeline("{not json"), {})

    def test_non_dict_json(self):
        self.assertEqual(self._with_timeline("[]"), {})

    def test_missing_key(self):
        self.assertEqual(self._with_timeline('{"series": []}'), {})

    def test_non_dict_key(self):
        self.assertEqual(self._with_timeline('{"file_activity": ["x"]}'), {})

    def test_valid_map(self):
        self.assertEqual(
            self._with_timeline('{"file_activity": {"active/a": "2026-07-01"}}'),
            {"active/a": "2026-07-01"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
