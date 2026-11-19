#!/usr/bin/env python3
"""Tests for scripts/handoffs/belief_capture_check.py (LOOP-50, blocking since 2026-11-02).

Each case makes a REAL commit in a throwaway repo whose pre-commit hook runs the checker the
way scripts/hooks/pre-commit.extras does, so git decides which index is being judged (shared,
private via GIT_INDEX_FILE, or a pathspec commit's temporary index). Refusals are paired with
passes, so a checker that refused everything would fail half the suite.

Run: python3 -I scripts/handoffs/tests/test_belief_capture_check.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "belief_capture_check.py"
H = "handoffs/active/demo.md"
H2 = "handoffs/active/other.md"

BASE = """# Demo

- [ ] **DEMO-1 — build the parity fixture.** 200 chunks, both roles.
- [ ] **DEMO-2 — measure decode t/s on the champion.**
- [x] **DEMO-3 — already done long ago.** ✅ 2026-10-01 [no-belief: not-a-result]
- [x] **DEMO-4 — a legacy tick with no tag.** ✅ 2026-09-01
"""


def git(cwd: Path, *args: str, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    full = dict(os.environ)
    if env:
        full.update(env)
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=full, check=check)


class BeliefCaptureGateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        self.write(H, BASE)
        self.write(H2, "# Other\n\n- [ ] **OTHER-1 — unrelated open task.**\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text(
            "#!/bin/bash\nstatus=0\n"
            f'python3 "{CHECKER}" --no-receipts --strict || status=1\n'
            'exit "$status"\n', encoding="utf-8")
        hook.chmod(0o755)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def read(self, rel: str) -> str:
        return (self.repo / rel).read_text(encoding="utf-8")

    def edit(self, rel: str, old: str, new: str) -> None:
        text = self.read(rel)
        assert old in text, old
        self.write(rel, text.replace(old, new))

    def commit(self, *paths: str, env: dict | None = None) -> subprocess.CompletedProcess:
        args = ["commit", "-q", "-m", "x"]
        if paths:
            args += ["--", *paths]
        return git(self.repo, *args, env=env, check=False)

    # ---- T1: a new tick needs its tag ---------------------------------------

    def test_blocked_untagged_flip_names_the_line_and_the_tag(self):
        self.edit(H, "- [ ] **DEMO-1 — build the parity fixture.** 200 chunks, both roles.",
                  "- [x] **DEMO-1 — build the parity fixture.** 200 chunks, both roles. ✅ 2026-11-02")
        r = self.commit(H)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(f"{H}:3:", r.stderr)
        self.assertIn("[belief: clm_<id>]", r.stderr)
        self.assertIn("[no-belief: <reason>]", r.stderr)

    def test_passing_tagged_flip(self):
        self.edit(H, "- [ ] **DEMO-1 — build the parity fixture.** 200 chunks, both roles.",
                  "- [x] **DEMO-1 — build the parity fixture.** 200 chunks, both roles. "
                  "✅ 2026-11-02 [no-belief: not-a-result]")
        r = self.commit(H)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_born_ticked_untagged_line_is_blocked(self):
        self.edit(H, "- [x] **DEMO-4", "- [x] **DEMO-9 — new and already done.** ✅ 2026-11-02\n- [x] **DEMO-4")
        r = self.commit(H)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(f"{H}:6:", r.stderr)

    def test_tag_on_a_wrapped_continuation_line_counts(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**",
                  "- [x] **DEMO-2 — measure decode t/s on the champion.** 41.2 t/s on run r1,\n"
                  "  recorded in `progress/2026-11/x.md`. ✅ 2026-11-02 [belief: cc]")
        r = self.commit(H)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_malformed_belief_tag_is_blocked(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**",
                  "- [x] **DEMO-2 — measure decode t/s on the champion.** ✅ 2026-11-02 [belief: yes]")
        r = self.commit(H)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("malformed tag [belief: yes]", r.stderr)

    # ---- folds and edits never count as ticks ------------------------------

    def test_fold_only_move_of_tagged_box_passes(self):
        """Folds move boxes verbatim: an already-tagged [x] moving to another file is no tick."""
        line = "- [x] **DEMO-3 — already done long ago.** ✅ 2026-10-01 [no-belief: not-a-result]\n"
        self.edit(H, line, "")
        self.write(H2, self.read(H2) + line)
        r = self.commit(H, H2)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_fold_only_move_of_open_boxes_and_legacy_untagged_tick_passes(self):
        text = self.read(H)
        moved = [l for l in text.splitlines(keepends=True) if l.startswith("- [")]
        self.write(H, "# Demo\n\nFolded into other.md.\n")
        self.write(H2, self.read(H2) + "".join(moved))
        r = self.commit(H, H2)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_adding_the_tag_to_an_existing_tick_passes(self):
        self.edit(H, "- [x] **DEMO-4 — a legacy tick with no tag.** ✅ 2026-09-01",
                  "- [x] **DEMO-4 — a legacy tick with no tag.** ✅ 2026-09-01 [no-belief: not-a-result]")
        r = self.commit(H)
        self.assertEqual(r.returncode, 0, r.stderr)

    # ---- D1: dropped open boxes ---------------------------------------------

    def test_dropped_open_box_is_blocked_with_the_marker_it_needs(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**\n", "")
        r = self.commit(H)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(f"{H}:4 (old line)", r.stderr)
        self.assertIn("[moved: <path>]", r.stderr)
        self.assertIn("[declined: <who> <YYYY-MM-DD> <reason>]", r.stderr)

    def test_declined_line_replacing_an_open_box_passes(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**",
                  "- **DEMO-2 — measure decode t/s on the champion.** "
                  "[declined: operator 2026-11-02 superseded by DEMO-1]")
        r = self.commit(H)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_retirement_banner_with_moved_marker_passes(self):
        self.write(H, "# Demo\n\n> Retired. [moved: docs/guides/demo-checklist.md]\n\n"
                      "- [x] **DEMO-3 — already done long ago.** ✅ 2026-10-01 [no-belief: not-a-result]\n"
                      "- [x] **DEMO-4 — a legacy tick with no tag.** ✅ 2026-09-01\n")
        r = self.commit(H)
        self.assertEqual(r.returncode, 0, r.stderr)

    # ---- science rules ------------------------------------------------------

    def test_nonterminal_completion_text_is_blocked(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**",
                  "- [x] **DEMO-2 — measure decode t/s on the champion.** ✅ 2026-11-02 "
                  "rule NOT MET [belief: cc] `progress/x.md`")
        r = self.commit(H)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown/inconclusive", r.stderr)

    def test_cc_tick_without_sha_or_path_is_blocked(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**",
                  "- [x] **DEMO-2 — measure decode t/s on the champion.** ✅ 2026-11-02 41 t/s [belief: cc]")
        r = self.commit(H)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("needs a commit SHA or a repository path", r.stderr)
        self.edit(H, "41 t/s [belief: cc]", "41 t/s in 3159fda2d [belief: cc]")
        r = self.commit(H)
        self.assertEqual(r.returncode, 0, r.stderr)

    # ---- judged on the commit, not the shared clone -------------------------

    def test_private_index_commit_judged_on_its_own_index(self):
        idx = self.root / "private.index"
        shutil.copy(self.repo / ".git" / "index", idx)
        env = {"GIT_INDEX_FILE": str(idx)}
        # A peer's bad tick sits staged in the SHARED index.
        self.edit(H, "- [ ] **DEMO-1 — build the parity fixture.** 200 chunks, both roles.",
                  "- [x] **DEMO-1 — build the parity fixture.** 200 chunks, both roles. ✅ 2026-11-02")
        git(self.repo, "add", H)
        # This session commits only other.md through its private index: allowed.
        self.write(H2, self.read(H2) + "- [ ] **OTHER-2 — another open task.**\n")
        git(self.repo, "add", H2, env=env)
        r = git(self.repo, "commit", "-q", "-m", "private", env=env, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        # PAIRED: the same bad tick staged in the PRIVATE index is refused.
        git(self.repo, "add", H, env=env)
        r = git(self.repo, "commit", "-q", "-m", "private bad", env=env, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(f"{H}:3:", r.stderr)

    def test_merge_does_not_rejudge_a_parent_line(self):
        git(self.repo, "checkout", "-q", "-b", "side")
        self.edit(H, "- [ ] **DEMO-1 — build the parity fixture.** 200 chunks, both roles.",
                  "- [x] **DEMO-1 — build the parity fixture.** 200 chunks, both roles. ✅ 2026-11-02")
        self.assertEqual(git(self.repo, "commit", "-q", "--no-verify", "-am", "legacy").returncode, 0)
        git(self.repo, "checkout", "-q", "main")
        self.write(H2, self.read(H2) + "- [ ] **OTHER-2 — another open task.**\n")
        git(self.repo, "commit", "-q", "-am", "main side")
        r = git(self.repo, "merge", "-q", "--no-ff", "--no-commit", "side", check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = git(self.repo, "commit", "-q", "--no-edit", check=False)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_replay_mode_matches_the_hook(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**",
                  "- [x] **DEMO-2 — measure decode t/s on the champion.** ✅ 2026-11-02")
        git(self.repo, "commit", "-q", "--no-verify", "-am", "bad")
        r = subprocess.run([sys.executable, str(CHECKER), "--no-receipts", "--commit", "HEAD"],
                           cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, "advisory by default: replay exits 0")
        self.assertIn(f"{H}:4:", r.stderr)
        self.assertIn("ADVISORY", r.stderr)
        r = subprocess.run([sys.executable, str(CHECKER), "--no-receipts", "--strict", "--commit", "HEAD"],
                           cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"{H}:4:", r.stderr)

    # ---- advisory (operator 2026-11-03): same guidance, never refuses -------

    def _advisory_hook(self):
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.write_text(
            "#!/bin/bash\nstatus=0\n"
            f'python3 "{CHECKER}" --no-receipts || true\n'
            'exit "$status"\n', encoding="utf-8")
        hook.chmod(0o755)

    def test_advisory_hook_warns_with_same_guidance_but_commit_lands(self):
        self._advisory_hook()
        self.edit(H, "- [ ] **DEMO-1 — build the parity fixture.** 200 chunks, both roles.",
                  "- [x] **DEMO-1 — build the parity fixture.** 200 chunks, both roles. ✅ 2026-11-02")
        r = self.commit(H)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"{H}:3:", r.stderr)
        self.assertIn("[belief: clm_<id>]", r.stderr)
        self.assertIn("ADVISORY", r.stderr)
        self.assertNotIn("BLOCKED", r.stderr)

    def test_advisory_checker_exits_zero_even_for_dropped_box_and_cannot_verify(self):
        self.edit(H, "- [ ] **DEMO-2 — measure decode t/s on the champion.**\n", "")
        git(self.repo, "add", H)
        r = subprocess.run([sys.executable, str(CHECKER), "--no-receipts"],
                           cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn(f"{H}", r.stderr)
        r = subprocess.run([sys.executable, str(CHECKER), "--no-receipts", "--strict"],
                           cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        r = subprocess.run([sys.executable, str(CHECKER), "--no-receipts", "--commit", "deadbeef"],
                           cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("cannot verify", r.stderr)
        r = subprocess.run([sys.executable, str(CHECKER), "--no-receipts", "--strict", "--commit", "deadbeef"],
                           cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_pre_commit_extras_line_is_advisory(self):
        extras = (CHECKER.parents[2] / "scripts" / "hooks" / "pre-commit.extras").read_text(encoding="utf-8")
        line = [l for l in extras.splitlines() if 'python3 "$_belief_checker"' in l]
        self.assertEqual(len(line), 1)
        self.assertIn("|| true", line[0])
        self.assertNotIn("status=1", line[0])
        self.assertNotIn("--strict", line[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
