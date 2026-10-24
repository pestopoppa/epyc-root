#!/usr/bin/env python3
"""Unit tests for the handoff timeline generator.

Builds a throwaway git repo (create -> flip checkbox -> move active->completed)
and asserts the reconstructed timeline. Stdlib ``unittest`` only.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO / "scripts" / "handoffs"
for p in (str(_REPO), str(_SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_handoff_timeline as bt  # noqa: E402


def _iso_week(date_str: str) -> str:
    dt = datetime.fromisoformat(date_str)
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


class TaskKeyTests(unittest.TestCase):
    def test_flip_decoration_matches_plain(self):
        # A flip appends "✅ <date> — notes"; the key must ignore that.
        before = bt._task_key("**S1: instrument relevance logging**")
        after = bt._task_key("**S1: instrument relevance logging** ✅ 2026-04-14 — Added the thing")
        self.assertEqual(before, after)
        self.assertNotEqual(before, bt._task_key("**S2: something else**"))

    def test_non_handoff_and_nested_excluded(self):
        self.assertIsNone(bt._path_state_stem("handoffs/blocked/BLOCKED.md"))
        self.assertIsNone(bt._path_state_stem("handoffs/completed/sub/chapter.md"))
        self.assertEqual(bt._path_state_stem("handoffs/active/foo.md"), ("active", "foo"))


class ParseCommitsTests(unittest.TestCase):
    def test_parses_header_and_added_checkbox(self):
        log = (
            "\x00abc1234def 2026-03-02T10:00:00+00:00\n"
            "diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md\n"
            "--- a/handoffs/active/foo.md\n"
            "+++ b/handoffs/active/foo.md\n"
            "@@ -1 +1 @@\n"
            "-- [ ] task one\n"
            "+- [x] task one ✅ done\n"
        )
        commits = bt._parse_commits(log)
        self.assertEqual(len(commits), 1)
        sha, ts, blocks = commits[0]
        self.assertEqual(sha, "abc1234def")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].checkboxes, [("x", "task one ✅ done", None)])

    def test_inline_dates_extracted(self):
        self.assertEqual(bt._inline_task_date("S1 done ✅ 2026-01-15 — notes"), "2026-01-15")
        # falls back to any ISO date when no ✅ marker
        self.assertEqual(bt._inline_task_date("done on 2026-02-03"), "2026-02-03")
        self.assertIsNone(bt._inline_task_date("no date here"))


class GitRepo:
    def __init__(self, root: Path):
        self.root = root
        self.n = 0

    def git(self, *args, date=None):
        env = dict(os.environ)
        env.update({
            "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
        })
        if date:
            env["GIT_AUTHOR_DATE"] = date
            env["GIT_COMMITTER_DATE"] = date
        subprocess.run(["git", "-C", str(self.root), *args],
                       check=True, env=env, capture_output=True, text=True)

    def commit(self, date):
        self.git("add", "-A")
        self.git("commit", "-m", f"c{self.n}", date=date)
        self.n += 1


class TimelineEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = GitRepo(self.root)
        self.repo.git("init", "-q")
        (self.root / "handoffs" / "active").mkdir(parents=True)
        (self.root / "handoffs" / "completed").mkdir(parents=True)

        # In-file **Created** predates the commit (simulates a bulk-imported file
        # whose real creation is earlier than when it first hit this repo's git).
        self.foo = self.root / "handoffs" / "active" / "foo.md"
        self.foo.write_text(
            "# Foo\n\n**Created**: 2026-01-10\n\n## Work\n- [ ] task one\n- [ ] task two\n")
        self.repo.commit("2026-03-02T10:00:00")

        # flip task one, dated ✅ 2026-01-15 (backdated — the real completion date);
        # add task three already-checked dated 2026-03-03; task two stays open.
        self.foo.write_text(
            "# Foo\n\n**Created**: 2026-01-10\n\n## Work\n"
            "- [x] task one ✅ 2026-01-15 — did it with lots of notes\n"
            "- [ ] task two\n"
            "- [x] task three ✅ 2026-03-03\n"
        )
        self.repo.commit("2026-03-03T10:00:00")

        # move active -> completed
        self.repo.git("mv", "handoffs/active/foo.md", "handoffs/completed/foo.md")
        self.repo.commit("2026-03-10T10:00:00")

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end(self):
        data = bt.build_timeline(self.root)
        t = data["totals"]
        # task one (flip) + task three (created-done); task two never checked.
        self.assertEqual(t["tasks_completed"], 2)
        self.assertEqual(t["active"], 0)
        self.assertEqual(t["completed"], 1)

        last = data["series"][-1]
        self.assertEqual(last["active"], 0)
        self.assertEqual(last["completed"], 1)
        # series is seeded back to the in-file Created date, not the commit date.
        self.assertEqual(data["totals"]["earliest"], "2026-01-10")

        # created bucket uses the in-file **Created** (Jan), NOT the commit (March).
        created = {r["week"]: r["created"] for r in data["handoffs_weekly"]}
        completed = {r["week"]: r["completed"] for r in data["handoffs_weekly"]}
        self.assertEqual(created.get(_iso_week("2026-01-10")), 1)
        self.assertEqual(created.get(_iso_week("2026-03-02")), 0)  # no false March creation (zero-filled week)
        self.assertEqual(completed.get(_iso_week("2026-03-10")), 1)

        # task completions land on their inline ✅ dates, not the commit date.
        tasks_by_week = {r["week"]: r["tasks_completed"] for r in data["tasks_weekly"]}
        self.assertEqual(tasks_by_week.get(_iso_week("2026-01-15")), 1)  # backdated flip
        self.assertEqual(tasks_by_week.get(_iso_week("2026-03-03")), 1)  # created-done
        filed_by_week = {r["week"]: r["newly_filed"] for r in data["tasks_weekly"]}
        opened_by_week = {r["week"]: r["opened"] for r in data["tasks_weekly"]}
        self.assertEqual(filed_by_week.get(_iso_week("2026-03-02")), 3)
        self.assertEqual(filed_by_week.get(_iso_week("2026-01-10")), 0)
        self.assertEqual(opened_by_week.get(_iso_week("2026-01-10")), 3)
        self.assertEqual(t["tasks_newly_filed"], 3)

        self.assertIsNotNone(data["last_sha"])

    def test_rename_does_not_recount_tasks(self):
        # A pure rename (100% similarity) carries no '+' content lines, so a
        # checked task must not be recounted when the handoff is moved.
        data = bt.build_timeline(self.root)
        self.assertEqual(data["totals"]["tasks_completed"], 2)

    def test_file_activity_migrates_on_move(self):
        # foo was last touched by the active->completed move (2026-03-10); the map
        # must key it under the NEW path and drop the stale active key.
        fa = bt.build_timeline(self.root)["file_activity"]
        self.assertEqual(fa.get("completed/foo"), "2026-03-10")
        self.assertNotIn("active/foo", fa)


class StemCollisionTests(unittest.TestCase):
    """Two distinct handoffs sharing a basename across state dirs must not merge."""

    def test_distinct_same_basename_counted_separately(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = GitRepo(root)
            repo.git("init", "-q")
            (root / "handoffs" / "active").mkdir(parents=True)
            (root / "handoffs" / "completed").mkdir(parents=True)
            (root / "handoffs" / "active" / "foo.md").write_text(
                "# Active Foo\n**Created**: 2026-03-01\n\n- [ ] a\n")
            (root / "handoffs" / "completed" / "foo.md").write_text(
                "# Completed Foo\n**Created**: 2026-02-01\n\n- [x] b ✅ 2026-02-15\n")
            repo.commit("2026-03-02T10:00:00")
            data = bt.build_timeline(root)
            # both survive — a bare-stem key would have merged them into one
            self.assertEqual(data["totals"]["active"], 1)
            self.assertEqual(data["totals"]["completed"], 1)
            # file_activity keys them separately too, each at its commit day
            fa = data["file_activity"]
            self.assertEqual(fa.get("active/foo"), "2026-03-02")
            self.assertEqual(fa.get("completed/foo"), "2026-03-02")


class OpenedMigrationTests(unittest.TestCase):
    """A rename-that-also-checks-a-task must not double-count 'opened'."""

    def test_rename_with_check_no_opened_double_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = GitRepo(root)
            repo.git("init", "-q")
            (root / "handoffs" / "active").mkdir(parents=True)
            (root / "handoffs" / "completed").mkdir(parents=True)
            f = root / "handoffs" / "active" / "bar.md"
            # padding keeps rename similarity high when the checkbox flips
            body = "# Bar\n\n## Work\n" + "".join(f"context line {i}\n" for i in range(30))
            f.write_text(body + "- [ ] alpha task\n")
            repo.commit("2026-03-01T10:00:00")
            # same commit: move to completed AND check the task
            repo.git("mv", "handoffs/active/bar.md", "handoffs/completed/bar.md")
            (root / "handoffs" / "completed" / "bar.md").write_text(
                body + "- [x] alpha task ✅ 2026-03-05\n")
            repo.commit("2026-03-05T10:00:00")
            data = bt.build_timeline(root)
            self.assertEqual(data["totals"]["tasks_opened"], 1)      # not 2
            self.assertEqual(data["totals"]["tasks_newly_filed"], 1)  # not 2
            self.assertEqual(data["totals"]["tasks_completed"], 1)


class DeleteIntervalTests(unittest.TestCase):
    """A deleted handoff keeps its active interval up to the deletion date."""

    def test_delete_preserves_pre_deletion_interval(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = GitRepo(root)
            repo.git("init", "-q")
            (root / "handoffs" / "active").mkdir(parents=True)
            f = root / "handoffs" / "active" / "ephemeral.md"
            f.write_text("# Ephemeral\n**Created**: 2026-03-01\n\n## body\n")
            repo.commit("2026-03-01T10:00:00")
            f.unlink()
            repo.commit("2026-03-20T10:00:00")
            data = bt.build_timeline(root)
            byday = {p["date"]: p for p in data["series"]}
            # active before the delete, gone after — interval not erased
            self.assertEqual(byday["2026-03-01"]["active"], 1)
            self.assertEqual(data["series"][-1]["active"], 0)
            # a deleted handoff drops out of the activity map (no ghost card)
            self.assertNotIn("active/ephemeral", data["file_activity"])


_HDR = "| ID | Track | Handoff | Next action | Deps |\n|----|----|----|----|----|\n"


def _row(rid: str, action: str, deps: str = "—") -> str:
    return f"| {rid} | track | [h.md](h.md) | {action} | {deps} |\n"


class NextActionRepointTests(unittest.TestCase):
    """RTG-46: a re-pointed ``Next action`` keeps its previous text and a reason.

    Each positive case is paired with a negative that differs in exactly one thing
    (same text, non-index file, row deleted, deps-only edit), so a pass cannot come
    from an inert fixture.
    """

    def _repo(self, td):
        root = Path(td)
        repo = GitRepo(root)
        repo.git("init", "-q")
        (root / "handoffs" / "active").mkdir(parents=True)
        return root, repo

    def _commit(self, repo, date, msg):
        repo.git("add", "-A")
        repo.git("commit", "-m", msg, date=date)

    def test_repoint_with_trailer_reason_and_subject_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root, repo = self._repo(td)
            idx = root / "handoffs" / "active" / "demo-index.md"
            idx.write_text(_HDR + _row("DEM-01", "try path A") + _row("DEM-02", "do X"))
            self._commit(repo, "2026-09-01T10:00:00", "seed")
            idx.write_text(_HDR + _row("DEM-01", "try path B") + _row("DEM-02", "do Y"))
            self._commit(repo, "2026-09-02T10:00:00",
                         "indices: re-point two rows\n\n"
                         "Repoint-Reason: DEM-01: path A measured null (n=24)\n")
            data = bt.build_timeline(root)
            ev = {e["id"]: e for e in data["next_action_repoints"]}
            self.assertEqual(set(ev), {"DEM-01", "DEM-02"})
            self.assertEqual(ev["DEM-01"]["from"], "try path A")
            self.assertEqual(ev["DEM-01"]["to"], "try path B")
            self.assertEqual(ev["DEM-01"]["reason"], "path A measured null (n=24)")
            self.assertEqual(ev["DEM-01"]["reason_source"], "trailer")
            self.assertEqual(ev["DEM-02"]["reason"], "indices: re-point two rows")
            self.assertEqual(ev["DEM-02"]["reason_source"], "commit_subject")
            self.assertEqual(ev["DEM-01"]["date"], "2026-09-02")
            self.assertEqual(data["totals"]["next_action_repoints"], 2)
            self.assertEqual(data["totals"]["repoints_with_trailer_reason"], 1)

    def test_non_repoints_are_not_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root, repo = self._repo(td)
            a = root / "handoffs" / "active" / "a-index.md"
            b = root / "handoffs" / "active" / "b-index.md"
            h = root / "handoffs" / "active" / "notes.md"   # not an index
            a.write_text(_HDR + _row("DEM-01", "same") + _row("DEM-02", "gone soon")
                         + _row("DEM-03", "keep"))
            b.write_text(_HDR)
            h.write_text(_HDR + _row("DEM-09", "old"))
            self._commit(repo, "2026-09-01T10:00:00", "seed")
            # DEM-01 re-homed unchanged; DEM-02 deleted; DEM-03 deps-only edit;
            # DEM-09 changed but lives in a non-index file.
            a.write_text(_HDR + _row("DEM-03", "keep", "DEM-01"))
            b.write_text(_HDR + _row("DEM-01", "same"))
            h.write_text(_HDR + _row("DEM-09", "new"))
            self._commit(repo, "2026-09-02T10:00:00", "rehome")
            data = bt.build_timeline(root)
            self.assertEqual(data["next_action_repoints"], [])

    def test_repoint_across_index_files_still_pairs(self):
        with tempfile.TemporaryDirectory() as td:
            root, repo = self._repo(td)
            a = root / "handoffs" / "active" / "a-index.md"
            b = root / "handoffs" / "active" / "b-index.md"
            a.write_text(_HDR + _row("DEM-01", "old target"))
            b.write_text(_HDR)
            self._commit(repo, "2026-09-01T10:00:00", "seed")
            a.write_text(_HDR)
            b.write_text(_HDR + _row("DEM-01", "new target"))
            self._commit(repo, "2026-09-02T10:00:00", "move and re-point")
            ev = bt.build_timeline(root)["next_action_repoints"]
            self.assertEqual([(e["id"], e["from"], e["to"], e["index"]) for e in ev],
                             [("DEM-01", "old target", "new target", "b-index.md")])

    def test_escaped_pipe_does_not_shift_cells(self):
        self.assertEqual(bt._row_next_action(_row("DEM-01", r"a \| b")), r"a \| b")
        self.assertIsNone(bt._row_next_action("| DEM-01 | only | three |"))



class DailyFlowTests(unittest.TestCase):
    """Open-box stock + flows: rewording, removal, born-ticked, move to completed/,
    a merge commit (needs --first-parent to be visible), and zero-filled days."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.g = GitRepo(self.root)
        self.g.git("init", "-q", "-b", "main")
        for d in ("active", "blocked", "completed"):
            (self.root / "handoffs" / d).mkdir(parents=True)
        self.a = self.root / "handoffs" / "active" / "a.md"
        self.b = self.root / "handoffs" / "active" / "b.md"
        # day 1: a has 3 open, b has 2 open
        self.a.write_text("# A\n- [ ] alpha task one\n- [ ] beta task two\n- [ ] gamma third thing\n")
        self.b.write_text("# B\n- [ ] delta item four\n- [ ] epsilon item five\n")
        self.g.commit("2026-03-02T10:00:00")
        # day 3: reword alpha (open->open, similar), tick beta, drop gamma,
        # add a really new box and a born-ticked box
        self.a.write_text("# A\n- [ ] alpha task one reworded\n- [x] beta task two \u2705 2026-03-04\n"
                          "- [ ] brand new zeta box\n- [x] born done eta\n")
        self.g.commit("2026-03-04T10:00:00")
        # day 5: b moves to completed with its 2 open boxes
        self.g.git("mv", "handoffs/active/b.md", "handoffs/completed/b.md")
        self.g.commit("2026-03-06T10:00:00")

    def tearDown(self):
        self.tmp.cleanup()

    def _flow(self):
        log = bt._run_git_log(self.root, first_parent=True)
        return {r["date"]: r for r in bt.build_daily_flow(log, today="2026-03-08")}

    def test_stock_and_flows(self):
        f = self._flow()
        self.assertEqual(f["2026-03-02"]["open_stock"], 5)
        self.assertEqual(f["2026-03-02"]["new_open"], 5)
        d = f["2026-03-04"]
        self.assertEqual(d["reworded"], 1)        # alpha reword is not a new filing
        self.assertEqual(d["ticked"], 1)          # beta open -> [x] (same text)
        self.assertEqual(d["new_open"], 1)        # only zeta is genuinely new
        self.assertEqual(d["born_ticked"], 1)     # eta filed already done
        self.assertEqual(d["removed_open"], 1)    # gamma dropped
        # a: alpha + zeta open = 2; b: 2 -> 4 (stock nets removals/ticks)
        self.assertEqual(d["open_stock"], 4)

    def test_move_to_completed_closes_open_boxes(self):
        f = self._flow()
        d = f["2026-03-06"]
        self.assertEqual(d["closed_by_completion"], 2)
        self.assertEqual(d["handoffs_completed"], 1)
        self.assertEqual(d["open_stock"], 2)      # only a's boxes remain
        self.assertEqual(d["ticked"], 0)

    def test_zero_days_filled_and_carry_stock(self):
        f = self._flow()
        self.assertIn("2026-03-03", f)
        self.assertEqual(f["2026-03-03"]["open_stock"], 5)
        self.assertEqual(f["2026-03-03"]["new_open"], 0)
        self.assertEqual(f["2026-03-08"]["open_stock"], 2)  # carried to "today"
        self.assertEqual(list(f)[-1], "2026-03-08")

    def test_merge_commit_changes_are_counted(self):
        self.g.git("checkout", "-q", "-b", "side")
        self.a.write_text(self.a.read_text() + "- [ ] side branch box\n")
        self.g.commit("2026-03-07T09:00:00")
        self.g.git("checkout", "-q", "main")
        (self.root / "other.txt").write_text("x")
        self.g.commit("2026-03-07T10:00:00")
        self.g.git("merge", "--no-ff", "-m", "merge side", "side", date="2026-03-07T11:00:00")
        f = self._flow()
        self.assertEqual(f["2026-03-08"]["open_stock"], 3)

    def test_deleted_handoff_counts_as_removed_not_completed(self):
        self.g.git("rm", "-q", "handoffs/active/a.md")
        self.g.commit("2026-03-07T10:00:00")
        d = self._flow()["2026-03-07"]
        self.assertEqual(d["removed_open"], 2)
        self.assertEqual(d["closed_by_completion"], 0)
        self.assertEqual(d["open_stock"], 0)

    def test_weekly_series_has_no_missing_weeks(self):
        self.g.commit  # keep linter quiet
        data = bt.build_timeline(self.root)
        weeks = [r["week"] for r in data["tasks_weekly"]]
        self.assertEqual(weeks, sorted(weeks))
        ys = [tuple(int(x) for x in w.split("-W")) for w in weeks]
        for (y1, w1), (y2, w2) in zip(ys, ys[1:]):
            self.assertTrue((y2, w2) == (y1, w1 + 1) or (y2 == y1 + 1 and w2 == 1))
        self.assertIn("daily_flow", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
