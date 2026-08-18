#!/usr/bin/env python3
"""Tests for scripts/hooks/check_d9_loop_plane.py.

The interesting cases are the FALSE-POSITIVE ones. The first implementation decided what a
commit would touch by reading the command's own tokens — every token after the first `--`,
to end-of-string. Measured 2026-08-18: a commit chained ahead of an unrelated pusher,

    git commit -m "..." -- <docs>; python3 scripts/coordination/serialized_push.py --push

read the pusher's path as part of the commit's pathspec and refused a commit that touched no
guarded file. A guard that fires on text rather than on effect teaches people to route around
it, which is how the unguarded path this hook exists to close got there in the first place.

So each false-positive case below is PAIRED with a case proving the guard still refuses the
real thing. A hook that allowed everything would pass the first half alone.

Runs against a real temp git repo, because the fix's whole point is that git — not this hook —
decides which paths a commit records.

Usage: scripts/hooks/tests/test_d9_loop_plane.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "scripts" / "hooks" / "check_d9_loop_plane.py"

GUARDED = "scripts/coordination/worker_runner.py"     # loop plane
GUARDED2 = "scripts/hooks/check_d9_loop_plane.py"     # the hook itself is guarded
EXEMPT = "scripts/coordination/tests/test_thing.py"   # tests are the counterweight
DOC = "handoffs/active/some-handoff.md"               # ordinary work plane


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


class D9HookTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.email", "t@t")
        _git(self.repo, "config", "user.name", "t")
        for rel in (GUARDED, GUARDED2, EXEMPT, DOC):
            f = self.repo / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("base\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "base")

    def tearDown(self):
        self._tmp.cleanup()

    def run_hook(self, cmd: str) -> int:
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
            capture_output=True, text=True, cwd=self.repo).returncode

    def touch(self, *rels: str) -> None:
        for rel in rels:
            p = self.repo / rel
            p.write_text(p.read_text(encoding="utf-8") + "change\n", encoding="utf-8")

    # ---- the measured false positive, and its paired coverage case -------

    def test_chained_pusher_path_is_not_this_commits_pathspec(self):
        """THE BUG: tokens after a `;` belong to the next command, not to the commit."""
        self.touch(DOC, GUARDED)          # guarded file dirty, but NOT in the pathspec
        cmd = (f'git commit -m "docs" -- {DOC}; '
               f'python3 scripts/coordination/serialized_push.py --push')
        self.assertEqual(self.run_hook(cmd), 0)

    def test_chained_with_and_and_is_also_not_the_pathspec(self):
        self.touch(DOC, GUARDED)
        cmd = f'git commit -m "docs" -- {DOC} && python3 {GUARDED} --run'
        self.assertEqual(self.run_hook(cmd), 0)

    def test_real_loop_plane_change_via_pathspec_still_refuses(self):
        """PAIRED COVERAGE: without this the tests above would pass on a no-op hook."""
        self.touch(GUARDED)
        self.assertEqual(self.run_hook(f'git commit -m "x" -- {GUARDED}'), 2)

    # ---- the staged path -------------------------------------------------

    def test_plain_commit_refuses_when_a_guarded_file_is_staged(self):
        self.touch(GUARDED)
        _git(self.repo, "add", GUARDED)
        self.assertEqual(self.run_hook('git commit -m "x"'), 2)

    def test_plain_commit_allows_when_only_a_doc_is_staged(self):
        self.touch(GUARDED, DOC)          # guarded is dirty but unstaged
        _git(self.repo, "add", DOC)
        self.assertEqual(self.run_hook('git commit -m "x"'), 0)

    def test_pathspec_commit_ignores_the_index(self):
        """`git commit -- <paths>` records the WORKING TREE of those paths, not the index.

        So a guarded file sitting staged is irrelevant to a commit that names only a doc —
        the old text-matching implementation could not express this distinction at all.
        """
        self.touch(GUARDED, DOC)
        _git(self.repo, "add", GUARDED)
        self.assertEqual(self.run_hook(f'git commit -m "x" -- {DOC}'), 0)

    # ---- acks ------------------------------------------------------------

    def test_ack_in_message_allows(self):
        self.touch(GUARDED)
        cmd = f'git commit -m "x\n\nD9-ack: operator 2026-08-18, because reasons" -- {GUARDED}'
        self.assertEqual(self.run_hook(cmd), 0)

    # ---- scope -----------------------------------------------------------

    def test_tests_under_coordination_are_exempt(self):
        self.touch(EXEMPT)
        self.assertEqual(self.run_hook(f'git commit -m "x" -- {EXEMPT}'), 0)

    def test_non_commit_git_command_is_ignored(self):
        self.touch(GUARDED)
        self.assertEqual(self.run_hook("git log --oneline -1"), 0)

    def test_clean_guarded_file_cannot_trigger(self):
        """Nothing dirty under the loop plane => no commit shape can record one."""
        self.touch(DOC)
        self.assertEqual(self.run_hook(f'git commit -m "x" -- {DOC}'), 0)

    def test_commit_message_mentioning_a_guarded_path_does_not_refuse(self):
        """The other half of match-on-effect: prose naming a path is not a change to it."""
        self.touch(DOC)
        cmd = f'git commit -m "note: {GUARDED} will change later" -- {DOC}'
        self.assertEqual(self.run_hook(cmd), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
