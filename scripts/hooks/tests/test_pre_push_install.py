"""The INSTALLED pre-push wrapper, both directions (operator decision 2026-11-02).

`test_pre_push_serialization_guard.sh` pins the guard's own contract. This suite pins
what the installer ships: the generated wrapper refuses an unserialized push of main,
lets serialized_push.py's own push through, passes a lane branch, and is what
`install_git_hooks.sh` writes for every repo it covers.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
ROOT = HOOKS.parents[1]
INSTALLER = HOOKS / "install_git_hooks.sh"
WRITER = ROOT / "scripts" / "coordination" / "serialized_push.py"


def _run(args, cwd, env=None):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, env=env)


class InstalledPrePushTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.origin = root / "origin.git"
        self.work = root / "work"
        env = {k: v for k, v in os.environ.items()
               if k not in ("AGENT_ID", "EPYC_PUSH_LOCK_HOLDER", "EPYC_ALLOW_UNSERIALIZED_PUSH",
                            "EPYC_PUSH_LOCK_FILE", "EPYC_PUSH_LOCK_DIR")}
        env.update({"EPYC_HOOK_SRC_DIR": str(HOOKS), "EPYC_SERIALIZED_PUSH": str(WRITER),
                    "SERIALIZED_PUSH_LOCK_DIR": str(root / "locks"),
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        self.env = env
        _run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], root)
        _run(["git", "clone", "-q", str(self.origin), str(self.work)], root)
        (self.work / "a.txt").write_text("a\n")
        _run(["git", "add", "a.txt"], self.work, env)
        _run(["git", "commit", "-qm", "a"], self.work, env)
        r = _run(["git", "push", "-q", "origin", "HEAD:main"], self.work, env)   # no hook yet
        self.assertEqual(r.returncode, 0, r.stderr)
        _run(["git", "branch", "-u", "origin/main"], self.work, env)
        wrapper = _run(["bash", str(INSTALLER), "--emit-pre-push"], ROOT).stdout
        hook = self.work / ".git" / "hooks" / "pre-push"
        hook.write_text(wrapper)
        hook.chmod(0o755)
        (self.work / "a.txt").write_text("a\nb\n")
        _run(["git", "commit", "-qam", "b"], self.work, env)

    def tearDown(self):
        self._tmp.cleanup()

    def origin_main(self) -> str:
        return _run(["git", "rev-parse", "main"], self.origin).stdout.strip()

    def head(self) -> str:
        return _run(["git", "rev-parse", "HEAD"], self.work).stdout.strip()

    def test_plain_push_of_main_is_refused(self):
        before = self.origin_main()
        r = _run(["git", "push", "origin", "HEAD:main"], self.work, self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PUSH REFUSED — pre-push serialization guard", r.stderr)
        self.assertIn("NOT HELD", r.stderr)
        self.assertEqual(self.origin_main(), before)

    def test_serialized_push_publishes_through_the_installed_guard(self):
        r = _run(["python3", str(WRITER), "--agent", "probe", "--repo", str(self.work),
                  "--fetch", "--push"], self.work, self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("serialization lock held by probe", r.stdout + r.stderr)
        self.assertEqual(self.origin_main(), self.head())

    def test_lane_branch_push_passes_without_a_lock(self):
        r = _run(["git", "push", "origin", "HEAD:refs/heads/lane/probe"], self.work, self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(_run(["git", "rev-parse", "lane/probe"], self.origin).stdout.strip(),
                         self.head())

    def test_missing_guard_fails_closed(self):
        env = {**self.env, "EPYC_HOOK_SRC_DIR": str(Path(self._tmp.name) / "nowhere")}
        r = _run(["git", "push", "origin", "HEAD:refs/heads/lane/x"], self.work, env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("guard script was not found", r.stderr)


class InstallerCoverageTests(unittest.TestCase):

    def test_every_covered_repo_gets_the_pre_push_wrapper(self):
        text = INSTALLER.read_text()
        repos = re.search(r"REPOS=\((.*?)\n\)", text, re.S).group(1)
        self.assertGreaterEqual(len(re.findall(r'^\s*"(/[^"]+)"', repos, re.M)), 4)
        loop = text[text.index('for repo in "${REPOS[@]}"; do'):]
        self.assertIn('pp_hook="$(dirname "$hook")/pre-push"', loop)
        self.assertIn('pp_desired="$(emit_pre_push)"', loop)

    def test_emitted_wrapper_runs_the_guard_then_lfs(self):
        out = _run(["bash", str(INSTALLER), "--emit-pre-push"], ROOT).stdout
        self.assertLess(out.index("pre_push_serialization_guard.sh"), out.index("git lfs pre-push"))
        self.assertNotIn("/mnt/raid0/llm/worktrees", out)   # nothing baked in at install time


if __name__ == "__main__":
    unittest.main()
