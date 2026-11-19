"""AUD-15 / R-8: commits touching auto-loaded instruction surfaces need `Operator-Ratified: yes`.

Every case is a REAL commit through the installer-generated commit-msg wrapper, so git
itself decides which index is judged (shared, pathspec temporary, private via
GIT_INDEX_FILE). Each refusal is paired with the ratified form of the same commit, so the
suite cannot pass by refusing everything.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
INSTALLER = HOOKS / "install_git_hooks.sh"
RATIFIED = "\n\nOperator-Ratified: yes\n"


def _git(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          env=env)


class InstructionSurfaceGateTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        self.env = {**os.environ, "EPYC_HOOK_SRC_DIR": str(HOOKS)}
        self.env.pop("EPYC_D9_ACK", None)
        _git(self.repo, "init", "-q", "-b", "main")
        _git(self.repo, "config", "user.email", "t@t")
        _git(self.repo, "config", "user.name", "t")
        for rel in ("CLAUDE.md", "agents/AGENT_INSTRUCTIONS.md", "agents/shared/POLICY.md",
                    "agents/shared/sub/NESTED.md", "agents/coder.md", "docs/notes.md"):
            f = self.repo / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("base\n", encoding="utf-8")
        os.symlink("CLAUDE.md", self.repo / "AGENTS.md")
        _git(self.repo, "add", "-A")
        self.assertEqual(_git(self.repo, "commit", "-q", "-m", "base").returncode, 0)
        wrapper = subprocess.run(["bash", str(INSTALLER), "--emit-commit-msg"],
                                 capture_output=True, text=True, check=True).stdout
        hook = self.repo / ".git" / "hooks" / "commit-msg"
        hook.write_text(wrapper, encoding="utf-8")
        hook.chmod(0o755)

    def tearDown(self):
        self._tmp.cleanup()

    # -- helpers -------------------------------------------------------------

    def edit(self, rel: str) -> None:
        p = self.repo / rel
        p.write_text(p.read_text(encoding="utf-8") + "agent premise\n", encoding="utf-8")

    def commit(self, msg: str, *extra: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return _git(self.repo, "commit", "-q", "-m", msg, *extra, env=env or self.env)

    def head(self) -> str:
        return _git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def assert_refused(self, r: subprocess.CompletedProcess, before: str) -> None:
        self.assertNotEqual(r.returncode, 0, r.stderr)
        self.assertIn("AUD-15", r.stderr)
        self.assertEqual(self.head(), before, "a refused commit must not move HEAD")

    def assert_landed(self, r: subprocess.CompletedProcess, before: str) -> None:
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(self.head(), before)

    # -- edits -----------------------------------------------------------------

    def test_agent_edit_of_each_surface_is_refused_and_ratified_edit_lands(self):
        for rel in ("CLAUDE.md", "agents/AGENT_INSTRUCTIONS.md", "agents/shared/POLICY.md",
                    "agents/shared/sub/NESTED.md"):
            with self.subTest(rel=rel):
                before = self.head()
                self.edit(rel)
                _git(self.repo, "add", rel)
                self.assert_refused(self.commit("tighten wording"), before)
                self.assert_landed(self.commit("Ratify wording" + RATIFIED), before)

    def test_unrelated_and_role_overlay_commits_pass_without_a_trailer(self):
        for rel in ("docs/notes.md", "agents/coder.md"):
            with self.subTest(rel=rel):
                before = self.head()
                self.edit(rel)
                _git(self.repo, "add", rel)
                self.assert_landed(self.commit("ordinary change"), before)

    def test_pathspec_commit_is_judged_on_its_temporary_index(self):
        before = self.head()
        self.edit("CLAUDE.md")
        self.assert_refused(self.commit("sneak", "--", "CLAUDE.md"), before)
        self.assert_landed(self.commit("ratified" + RATIFIED, "--", "CLAUDE.md"), before)

    def test_private_index_commit_is_judged(self):
        before = self.head()
        private = Path(self._tmp.name) / "private.index"
        env = {**self.env, "GIT_INDEX_FILE": str(private)}
        _git(self.repo, "read-tree", "HEAD", env=env)
        self.edit("agents/shared/POLICY.md")
        _git(self.repo, "add", "agents/shared/POLICY.md", env=env)
        self.assert_refused(self.commit("private", env=env), before)

    def test_alias_symlink_retarget_is_refused(self):
        before = self.head()
        (self.repo / "AGENTS.md").unlink()
        os.symlink("docs/notes.md", self.repo / "AGENTS.md")
        _git(self.repo, "add", "AGENTS.md")
        self.assert_refused(self.commit("point AGENTS.md elsewhere"), before)

    # -- renames and deletes ---------------------------------------------------

    def test_rename_out_of_a_surface_is_refused_both_directions(self):
        before = self.head()
        _git(self.repo, "mv", "agents/shared/POLICY.md", "docs/POLICY.md")
        self.assert_refused(self.commit("move policy"), before)
        self.assert_landed(self.commit("move policy" + RATIFIED), before)
        before = self.head()
        _git(self.repo, "mv", "docs/notes.md", "agents/shared/NOTES.md")
        self.assert_refused(self.commit("promote notes into shared policy"), before)

    def test_delete_is_refused_and_ratified_delete_lands(self):
        before = self.head()
        _git(self.repo, "rm", "-q", "agents/AGENT_INSTRUCTIONS.md")
        self.assert_refused(self.commit("drop instructions"), before)
        self.assert_landed(self.commit("drop instructions" + RATIFIED), before)

    # -- the trailer ---------------------------------------------------------

    def test_trailer_only_in_a_comment_or_with_another_value_does_not_count(self):
        before = self.head()
        self.edit("CLAUDE.md")
        _git(self.repo, "add", "CLAUDE.md")
        self.assert_refused(self.commit("x\n\n# Operator-Ratified: yes"), before)
        self.assert_refused(self.commit("x\n\nOperator-Ratified: no"), before)
        self.assert_refused(self.commit("x\n\nOperator-Ratified: yes please"), before)
        self.assert_landed(self.commit("x\n\noperator-ratified: YES"), before)

    def test_ratify_script_shape_commit_with_d9_ack_and_trailer_lands(self):
        """The operator's ratify scripts commit with -F and carry the trailer."""
        before = self.head()
        self.edit("CLAUDE.md")
        self.edit("agents/shared/POLICY.md")
        _git(self.repo, "add", "-A")
        msg = Path(self._tmp.name) / "msg.txt"
        msg.write_text("Ratify LOOP-XX: wording\n\nOperator-Ratified: yes\n"
                       "Co-Authored-By: someone <x@y>\n", encoding="utf-8")
        r = _git(self.repo, "commit", "-q", "-F", str(msg), env=self.env)
        self.assert_landed(r, before)

    # -- merges ----------------------------------------------------------------

    def test_merge_carrying_an_already_ratified_change_is_not_rejudged(self):
        _git(self.repo, "checkout", "-q", "-b", "side")
        self.edit("CLAUDE.md")
        _git(self.repo, "add", "CLAUDE.md")
        self.assertEqual(self.commit("ratified on side" + RATIFIED).returncode, 0)
        _git(self.repo, "checkout", "-q", "main")
        self.edit("docs/notes.md")
        _git(self.repo, "add", "docs/notes.md")
        self.assertEqual(self.commit("main moves on").returncode, 0)
        before = self.head()
        r = _git(self.repo, "merge", "--no-ff", "-q", "-m", "merge side", "side", env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(self.head(), before)

    def test_unratified_conflict_resolution_in_a_merge_is_judged(self):
        _git(self.repo, "checkout", "-q", "-b", "side")
        (self.repo / "CLAUDE.md").write_text("side version\n", encoding="utf-8")
        _git(self.repo, "add", "CLAUDE.md")
        self.assertEqual(self.commit("side" + RATIFIED).returncode, 0)
        _git(self.repo, "checkout", "-q", "main")
        (self.repo / "CLAUDE.md").write_text("main version\n", encoding="utf-8")
        _git(self.repo, "add", "CLAUDE.md")
        self.assertEqual(self.commit("main" + RATIFIED).returncode, 0)
        _git(self.repo, "merge", "-q", "side", env=self.env)        # conflicts
        (self.repo / "CLAUDE.md").write_text("an agent's own resolution\n", encoding="utf-8")
        _git(self.repo, "add", "CLAUDE.md")
        before = self.head()
        self.assert_refused(self.commit("resolve"), before)


if __name__ == "__main__":
    unittest.main()
