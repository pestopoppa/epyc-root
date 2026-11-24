#!/usr/bin/env python3
"""deploy_rowflow.sh stage hygiene (2026-11-24): every exit removes THIS run's stage (+ replay scratch), the unit/replay logs stay,
a refused deploy keeps only the newest stage as deploy-<ts>-REFUSED-keep, --keep-stage keeps it, other deploys' paths are untouched."""
import glob
import os
import shutil
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COORD = os.path.abspath(os.path.join(HERE, ".."))
DEPLOY = os.path.join(COORD, "rowflow", "deploy_rowflow.sh")
GIT = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]


def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True, check=True)


class StageCleanup(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.repo = os.path.join(self.d, "repo")
        self.scratch = os.path.join(self.d, "scratch")
        self.flags = os.path.join(self.d, "flags")
        os.makedirs(self.scratch)
        os.makedirs(os.path.join(self.flags, "bin", "rowflow"))
        sh("git", "init", "-q", self.repo)
        shutil.copytree(os.path.join(COORD, "rowflow"), os.path.join(self.repo, "scripts", "coordination", "rowflow"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.bak*"))
        os.makedirs(os.path.join(self.repo, "scripts", "coordination", "tests"))
        open(os.path.join(self.repo, "scripts", "coordination", "rowflow", "x.txt"), "w").write("x\n")
        open(os.path.join(self.repo, "scripts", "coordination", "INSTALL.manifest"), "w").write(
            "bin/rowflow/x.txt scripts/coordination/rowflow/x.txt data\n")
        self.commit(passing=True)
        self.env = dict(os.environ, ROWFLOW_FLAGS=self.flags, REPLAY_SCRATCH=self.scratch, USER="tester")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def commit(self, passing):
        t = os.path.join(self.repo, "scripts", "coordination", "tests", "test_rowflow_fake.py")
        open(t, "w").write("def test_x():\n    assert %s\n" % ("True" if passing else "False"))
        sh(*GIT, "add", "-A", cwd=self.repo)
        sh(*GIT, "commit", "-q", "-m", "c", cwd=self.repo)

    def deploy(self, *args):
        return subprocess.run(["bash", DEPLOY, "--ref", "HEAD", "--repo", self.repo, "--no-light-claim", "--check-only", *args],
                              env=self.env, capture_output=True, text=True, timeout=600)

    def stages(self):
        return sorted(os.path.basename(p) for p in glob.glob(os.path.join(self.scratch, "deploy-*"))
                      if os.path.isdir(p) and not p.endswith(("-unit.log", "-replay.log")))

    def logs(self):
        return glob.glob(os.path.join(self.scratch, "deploy-*-unit.log"))

    def test_success_leaves_no_stage_and_keeps_log(self):
        r = self.deploy()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.stages(), [])
        self.assertEqual(len(self.logs()), 1)

    def test_refusal_keeps_only_newest_refused_stage(self):
        self.commit(passing=False)
        foreign = os.path.join(self.scratch, "deploy-19990101T000000Z-abcd")   # another deploy's stage: never touched
        os.makedirs(foreign)
        for _ in range(2):
            r = self.deploy()
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            time.sleep(1.1)
        kept = [s for s in self.stages() if s.endswith("-REFUSED-keep")]
        self.assertEqual(len(kept), 1, self.stages())
        self.assertEqual(sorted(self.stages()), sorted(kept + ["deploy-19990101T000000Z-abcd"]))
        self.assertEqual(len(self.logs()), 2)
        self.assertIn(kept[0][:len("deploy-YYYYMMDDTHHMMSSZ")], sorted(os.path.basename(l)[:-9] for l in self.logs())[-1])

    def test_keep_stage_flag(self):
        r = self.deploy("--keep-stage")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(len(self.stages()), 1)


if __name__ == "__main__":
    unittest.main()
