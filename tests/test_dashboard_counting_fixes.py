"""Dashboard counting fixes (2026-11-03): one box grammar, roll-up skip, router exclusion,
``**Key:**`` metadata, HIGHEST priority, and fold-aware timeline/flow counting."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
for p in (str(_REPO), str(_REPO / "scripts" / "handoffs")):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_handoff_timeline as bt  # noqa: E402
import index_state as ist  # noqa: E402
from dashboard import handoff_parser as hp  # noqa: E402
from dashboard import pipeline_status as ps  # noqa: E402
from dashboard import server  # noqa: E402

MIXED = """# Mixed

**Status**: active

## Work
- [ ] bullet open
- [x] bullet done
* [ ] star open
+ [x] plus done
1. [x] numbered done
2) [ ] numbered paren open
  3. [x] nested numbered done
- [ ] **P-1** [roll-up] Non-dispatchable parent.
- [x] **P-2** [roll-up] Ticked parent.
-[ ] not a box (no space)
"""


class OneBoxGrammar(unittest.TestCase):
    def test_numbered_boxes_count_on_the_board(self):
        done, total, source, _ = hp.count_tasks(MIXED)
        self.assertEqual(source, "checkboxes")
        self.assertEqual((done, total), (4, 7))

    def test_roll_up_boxes_skipped_by_the_graph_scanner(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mixed.md"
            p.write_text(MIXED)
            st = ist.scan_handoff(p)
        self.assertEqual(st["closed"], 4)
        self.assertEqual(st["open"] + st["guarded"] + st["blocked"], 3)
        self.assertEqual(st["total"], 7)

    def test_board_and_graph_agree_on_the_same_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mixed.md"
            p.write_text(MIXED)
            st = ist.scan_handoff(p)
            done, total, _, _ = hp.count_tasks(p.read_text())
        self.assertEqual(done, st["closed"])
        self.assertEqual(total - done, st["open"] + st["guarded"] + st["blocked"])

    def test_grammar_copies_are_identical(self):
        self.assertEqual(bt._BOX_MARKER, hp.BOX_MARKER)
        import re
        bullet = ist.brc._BULLET
        for line in MIXED.splitlines():
            graph = bool(re.match(rf"{bullet}\[([ xX])\]", line.lstrip()))
            self.assertEqual(bool(hp.CHECKBOX_RE.match(line)), graph, line)
            self.assertEqual(bool(bt._ANY_CHECKBOX_RE.match("+" + line)), graph, line)


class RouterExclusion(unittest.TestCase):
    def test_router_set_matches_index_state(self):
        self.assertEqual(set(hp.ROUTER_NAMES) | {"BLOCKED.md", "README.md"}, ist.REGISTERS)

    def test_backlog_counts_only_real_handoffs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for s in ("active", "blocked", "completed", "archived"):
                (root / s).mkdir()
            (root / "active" / "real-one.md").write_text("# One\n\n**Priority**: HIGH\n\n## W\n- [ ] a\n- [x] b\n")
            (root / "active" / "real-two.md").write_text("# Two\n\nprose only\n")
            for name in ("master-handoff-index.md", "CURRENT-CAMPAIGN.md", "inference-research-index.md"):
                (root / "active" / name).write_text(f"# {name}\n\n| ID | x |\n")
            # a stem in both dirs counts once (the blocked copy)
            (root / "active" / "dup.md").write_text("# Dup pointer\n")
            (root / "blocked" / "dup.md").write_text("# Dup\n\n## W\n- [ ] c\n")
            board = hp.build_board(root)
        bk = board["backlog"]
        self.assertEqual(bk["open_handoffs"], 3)            # real-one, real-two, dup
        self.assertEqual(bk["open_untracked_handoffs"], 1)  # real-two only, no routers
        self.assertEqual(bk["routers_excluded"], 3)
        self.assertEqual((bk["open_tasks"], bk["open_tasks_done"]), (2, 1))
        self.assertEqual(board["counts"]["routers"], 3)
        routers = [c for c in board["columns"]["active"] if c["router"]]
        self.assertEqual(len(routers), 3)                   # still shown on the board


class PriorityParsing(unittest.TestCase):
    def test_colon_inside_bold_key(self):
        meta = hp.parse_metadata("# T\n\n**Status:** Active\n**Priority:** HIGH after the move\n\n## X\n")
        self.assertEqual(meta.get("priority"), "HIGH after the move")
        self.assertEqual(hp.parse_priority(meta), "HIGH")

    def test_classic_key_unchanged(self):
        meta = hp.parse_metadata("# T\n\n**Priority**: MEDIUM — why\n- **Owner**: x\n\n## X\n")
        self.assertEqual(hp.parse_priority(meta), "MEDIUM")
        self.assertEqual(meta.get("owner"), "x")

    def test_highest_maps_to_high(self):
        self.assertEqual(hp._priority_from_value("HIGHEST — the program spine"), "HIGH")
        self.assertEqual(hp._priority_from_value("HIGH"), "HIGH")


class PipelineRollupNotSubtractedTwice(unittest.TestCase):
    def test_flagged_graph_skips_legacy_rollup_correction(self):
        graph = {"rollups_excluded": True,
                 "nodes": [{"id": "T-01", "handoff": "t.md", "state": "active", "open": 2,
                            "priority_basis": {"tier": 7}}]}
        out = ps.classify_handoffs(graph, {}, {"handoffs/active/t.md": 1})
        self.assertEqual(out["handoffs"][0]["open"], 2)


class _Git:
    def __init__(self, root: Path):
        self.root = root

    def __call__(self, *args, date=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "-C", str(self.root), *args], check=True, env=env,
                       capture_output=True, text=True)

    def commit(self, msg, date):
        self("add", "-A")
        self("commit", "-q", "-m", msg, date=date)


class TimelineFoldPairing(unittest.TestCase):
    """A fold commit moves boxes from a source into a target: no filing, no second
    completion, no completed handoff; the stock is unchanged and the day is marked."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        g = self.g = _Git(self.root)
        g("init", "-q", "-b", "main")
        act = self.root / "handoffs" / "active"
        (self.root / "handoffs" / "completed").mkdir(parents=True)
        act.mkdir(parents=True)
        (act / "src.md").write_text("# Src\n\n## W\n- [ ] move me one\n- [ ] move me two\n"
                                    "- [x] done long ago ✅ 2026-03-01\n")
        (act / "tgt.md").write_text("# Tgt\n\n## W\n- [ ] target own\n")
        (act / "inference-research-index.md").write_text("# Index\n\n- [ ] router box\n")
        g.commit("seed", "2026-03-02T10:00:00")
        # the fold: source body appended to the target, source left as a stub in completed/
        (act / "tgt.md").write_text("# Tgt\n\n## W\n- [ ] target own\n\n## Track: src\n"
                                    "- [ ] move me one\n- [ ] move me two\n"
                                    "- [x] done long ago ✅ 2026-03-01\n")
        (act / "src.md").unlink()
        (self.root / "handoffs" / "completed" / "src.md").write_text(
            "# Src\n\n> **Folded into [tgt](../active/tgt.md#track-src)** (BRF).\n")
        g.commit("fold src into tgt\n\nRepoint-Reason: SRC-1: folded into TGT-1\nD9-ack: backlog refactor\n",
                 "2026-03-16T10:00:00")

    def tearDown(self):
        self.tmp.cleanup()

    def test_daily_flow_counts_moves_not_filings(self):
        log = bt._run_git_log(self.root, first_parent=True)
        flow = {r["date"]: r for r in bt.build_daily_flow(log, today="2026-03-17")}
        seed, fold = flow["2026-03-02"], flow["2026-03-16"]
        self.assertEqual(seed["open_stock"], 3)              # router box excluded
        self.assertEqual(fold["moved"], 3)
        self.assertEqual((fold["new_open"], fold["born_ticked"], fold["ticked"],
                          fold["removed_open"], fold["handoffs_completed"]), (0, 0, 0, 0, 0))
        self.assertEqual(fold["open_stock"], 3)
        self.assertEqual(bt.refactor_markers(list(flow.values())),
                         [{"date": "2026-03-16", "moved": 3,
                           "label": "backlog refactor fold: boxes moved, not closed or filed"}])

    def test_weekly_first_seen_and_completions_not_double_counted(self):
        data = bt.build_timeline(self.root)
        t = data["totals"]
        self.assertEqual(t["tasks_newly_filed"], 4)   # 3 src + 1 tgt; router box excluded
        self.assertEqual(t["tasks_completed"], 1)     # the moved [x] is not completed again
        self.assertEqual(t["tasks_moved"], 3)
        weeks = {w["week"]: w for w in data["tasks_weekly"]}
        self.assertEqual(weeks[bt._iso_week("2026-03-16")]["newly_filed"], 0)
        self.assertEqual(t["completed"], 0)           # a fold stub is not a completed handoff
        self.assertEqual(t["active"], 1)              # tgt only; the router is not a handoff
        self.assertEqual([m["date"] for m in data["refactor_markers"]], ["2026-03-16"])

    def test_no_data_weeks_are_flagged(self):
        data = bt.build_timeline(self.root)
        weeks = {w["week"]: w for w in data["tasks_weekly"]}
        gap = weeks[bt._iso_week("2026-03-09")]          # no commit at all that week
        self.assertTrue(gap["no_data"])
        self.assertEqual((gap["commits"], gap["box_events"]), (0, 0))
        self.assertFalse(weeks[bt._iso_week("2026-03-02")]["no_data"])
        self.assertFalse(weeks[bt._iso_week("2026-03-16")]["no_data"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
