#!/usr/bin/env python3
"""Tests for scripts/hooks/check_d9_loop_plane.py.

The interesting cases are the FALSE-POSITIVE ones. The first implementation decided what a
commit would touch by reading the command's own tokens — every token after the first `--`,
to end-of-string. Measured 2026-08-18: a commit chained ahead of an unrelated pusher,

    git commit -m "..." -- <docs>; python3 scripts/coordination/serialized_push.py --push

read the pusher's path as part of the commit's pathspec and refused a commit that touched no
guarded file. A guard that fires on text rather than on effect teaches people to route around
it, which is how the unguarded path this hook exists to close got there in the first place.

A second false-positive class, measured 2026-10-06: "is this command a commit at all" was
decided by substring-searching the RAW command text for the words "git" and "commit". That
matched inside a heredoc BODY (data handed to a command's stdin, not more shell source) and
inside a quoted string/`-c` argument, so a `python3 <<'EOF' ... EOF` payload that merely
mentioned "git commit" — and committed nothing — was treated as a commit and evaluated
against whatever repo the hook happened to be probing (often /workspace, unrelated to the
heredoc's real target), refusing a command that was not a commit at all.

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

        # A second, independent repo WITHOUT a loop plane at all — used by the
        # cross-repo false-positive cases (`-C`/`cd` into it).
        self._tmp_other = tempfile.TemporaryDirectory()
        self.other_repo = Path(self._tmp_other.name)
        _git(self.other_repo, "init", "-q", "-b", "main")
        _git(self.other_repo, "config", "user.email", "t@t")
        _git(self.other_repo, "config", "user.name", "t")
        (self.other_repo / "README.md").write_text("base\n", encoding="utf-8")
        _git(self.other_repo, "add", "-A")
        _git(self.other_repo, "commit", "-q", "-m", "base")

    def tearDown(self):
        self._tmp.cleanup()
        self._tmp_other.cleanup()

    def run_hook(self, cmd: str, cwd: Path | None = None) -> int:
        cwd = cwd or self.repo
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"tool_name": "Bash",
                               "tool_input": {"command": cmd},
                               "cwd": str(cwd)}),
            capture_output=True, text=True, cwd=cwd).returncode

    def touch(self, *rels: str, repo: Path | None = None) -> None:
        repo = repo or self.repo
        for rel in rels:
            p = repo / rel
            p.write_text(p.read_text(encoding="utf-8") + "change\n", encoding="utf-8")

    # ---- the 2026-08-18 false positive, and its paired coverage case -----

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

    # ---- the 2026-10-06 false positive: heredoc body is data, not source -

    def test_heredoc_body_mentioning_commit_text_is_not_a_commit(self):
        """THE 2026-10-06 BUG, reproduced exactly: a heredoc payload containing
        commit-shaped text with a syntactically invalid pathspec (`:(fooinvalid)bogus`)
        makes `git diff HEAD --name-only -- <pathspec>` fail, which trips the
        deliberately-over-broad fallback (staged union dirty) and refuses a command
        that committed nothing at all. Confirmed against the unpatched hook: it
        returns 2 here; the fix must return 0."""
        self.touch(GUARDED)   # guarded file genuinely dirty in THIS repo, nothing staged
        cmd = (
            "python3 <<'EOF'\n"
            'git commit -m "x" -- :(fooinvalid)bogus\n'
            "EOF\n"
        )
        self.assertEqual(self.run_hook(cmd), 0)

    def test_quoted_dash_c_argument_mentioning_commit_is_not_a_commit(self):
        """Same class: the words live inside a single quoted token, not as bare commands."""
        self.touch(GUARDED)
        cmd = 'python3 -c "print(\'please run git commit by hand\')"'
        self.assertEqual(self.run_hook(cmd), 0)

    def test_real_commit_after_a_heredoc_in_the_same_command_still_refuses(self):
        """PAIRED COVERAGE: a real commit chained AFTER a heredoc must still be caught —
        proves _strip_heredocs only removes the body, not the rest of the command."""
        self.touch(GUARDED)
        cmd = (
            "python3 <<'EOF'\n"
            "print('no git commit here, just talking about it')\n"
            "EOF\n"
            f'\ngit commit -m "x" -- {GUARDED}'
        )
        self.assertEqual(self.run_hook(cmd), 2)

    # ---- cross-repo resolution: a commit targeting an unguarded repo ------

    def test_commit_in_another_repo_via_dash_c_is_not_guarded(self):
        """A `-C <dir>` commit targets THAT repo, not wherever the hook payload cwd was."""
        self.touch(GUARDED)  # dirty in self.repo, but the commit below targets other_repo
        (self.other_repo / "README.md").write_text("changed\n", encoding="utf-8")
        cmd = f'git -C {self.other_repo} commit -am "x"'
        self.assertEqual(self.run_hook(cmd, cwd=self.repo), 0)

    def test_commit_in_another_repo_via_cd_is_not_guarded(self):
        """Same resolution, via a `cd` earlier in the same chained command."""
        self.touch(GUARDED)
        (self.other_repo / "README.md").write_text("changed\n", encoding="utf-8")
        cmd = f'cd {self.other_repo} && git commit -am "x"'
        self.assertEqual(self.run_hook(cmd, cwd=self.repo), 0)

    def test_commit_via_cd_into_this_repo_is_still_guarded(self):
        """PAIRED COVERAGE: `cd` resolution must not become a blanket escape hatch."""
        self.touch(GUARDED)
        cmd = f'cd {self.repo} && git commit -am "x"'
        self.assertEqual(self.run_hook(cmd, cwd=self.other_repo), 2)

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

    # ---- -a / --all --------------------------------------------------------

    def test_commit_dash_a_still_caught(self):
        """`-a` records the working tree, not the (empty) index — paired with the -am
        regression fixed 2026-09-05."""
        self.touch(GUARDED)
        self.assertEqual(self.run_hook('git commit -am "x"'), 2)

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
