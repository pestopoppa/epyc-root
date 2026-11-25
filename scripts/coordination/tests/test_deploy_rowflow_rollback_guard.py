#!/usr/bin/env python3
"""Ancestry guard runs under the deploy lock before staging and test gates."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
COORD = HERE.parent
DEPLOY = COORD / "rowflow" / "deploy_rowflow.sh"


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c",
                           "user.email=test@example.com", *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class RollbackGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo, self.flags, self.scratch = root / "repo", root / "flags", root / "scratch"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        rowflow = self.repo / "scripts/coordination/rowflow"
        shutil.copytree(COORD / "rowflow", rowflow, ignore=shutil.ignore_patterns("__pycache__", "*.bak*"))
        (self.repo / "scripts/coordination/tests").mkdir()
        (rowflow / "x.txt").write_text("one\n")
        (self.repo / "scripts/coordination/INSTALL.manifest").write_text(
            "bin/rowflow/x.txt scripts/coordination/rowflow/x.txt data\n")
        self.first = self.commit("first")
        (rowflow / "x.txt").write_text("two\n")
        self.second = self.commit("second")
        (rowflow / "x.txt").write_text("three\n")
        self.third = self.commit("third")
        self.record = self.flags / "bin/rowflow/DEPLOYED.json"
        self.record.parent.mkdir(parents=True)
        stub = root / "stub"
        stub.mkdir()
        python = shutil.which("python3")
        (stub / "python3").write_text(
            '#!/bin/bash\nif [ "$1" = "-m" ] && [ "$2" = "pytest" ]; then\n'
            '  echo gate-stub; exit 0\nfi\n'
            'case "${1:-}" in */destructive_scratch_scan.py) exit 0 ;; esac\n'
            f'exec "{python}" "$@"\n')
        (stub / "python3").chmod(0o755)
        self.env = dict(os.environ, ROWFLOW_FLAGS=str(self.flags), REPLAY_SCRATCH=str(self.scratch),
                        PATH=str(stub) + os.pathsep + os.environ["PATH"])

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)
        return git(self.repo, "rev-parse", "HEAD")

    def live(self, sha):
        self.record.write_text(json.dumps({"sha": sha}))

    def deploy(self, ref, *args):
        return subprocess.run(["bash", str(DEPLOY), "--repo", str(self.repo), "--ref", ref,
                               "--by", "tester", "--no-light-claim", "--check-only", *args],
                              env=self.env, capture_output=True, text=True, timeout=60)

    def test_refuses_older_ref_before_staging(self):
        self.live(self.third)
        result = self.deploy(self.first)
        self.assertEqual(result.returncode, 81, result.stdout + result.stderr)
        self.assertIn(f"REFUSED: --ref {self.first} does not contain live {self.third} "
                      "(would roll back 2 commits); deploy origin/main or pass --allow-rollback", result.stderr)
        self.assertFalse(self.scratch.exists())

    def test_same_and_descendant_pass(self):
        self.live(self.second)
        for ref in (self.second, self.third):
            with self.subTest(ref=ref):
                result = self.deploy(ref)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("gates PASS", result.stdout)

    def test_diverged_history_counts_only_lost_commits(self):
        git(self.repo, "checkout", "-q", "--detach", self.first)
        (self.repo / "branch.txt").write_text("branch\n")
        branch = self.commit("branch")
        self.live(self.third)
        result = self.deploy(branch)
        self.assertEqual(result.returncode, 81, result.stdout + result.stderr)
        self.assertIn("would roll back 2 commits", result.stderr)

    def test_override_logs_and_reaches_gates(self):
        self.live(self.third)
        result = self.deploy(self.first, "--allow-rollback")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"ROLLBACK from {self.third} to {self.first} by tester", result.stdout)
        self.assertIn("gates PASS", result.stdout)

    def test_missing_and_malformed_record_warn_and_proceed(self):
        for contents in (None, "{", '{}'):
            with self.subTest(contents=contents):
                if contents is None:
                    self.record.unlink(missing_ok=True)
                else:
                    self.record.write_text(contents)
                result = self.deploy(self.first)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("WARNING: missing or unreadable", result.stderr)
                self.assertIn("gates PASS", result.stdout)

    def test_unknown_live_commit_refuses(self):
        self.live("f" * 40)
        result = self.deploy(self.first, "--allow-rollback")
        self.assertEqual(result.returncode, 81, result.stdout + result.stderr)
        self.assertIn("cannot resolve live sha", result.stderr)
        self.assertFalse(self.scratch.exists())


if __name__ == "__main__":
    unittest.main()
