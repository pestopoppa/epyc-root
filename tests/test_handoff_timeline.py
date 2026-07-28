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
        self.assertNotIn(_iso_week("2026-03-02"), created)  # no false March creation
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
