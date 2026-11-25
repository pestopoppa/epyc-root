#!/usr/bin/env python3
"""deploy_rowflow.sh (coordinator 2026-11-23): a deploy flock (a second deploy is refused, rc 79) and a LIGHT claim on 84-87 that the
test gates run under (nice -n 19 taskset -c 84-87), retried, released on exit."""
import fcntl
import os
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.join(HERE, "..", "rowflow", "deploy_rowflow.sh")
STUB = '''#!/usr/bin/env python3
import os, sys
log = os.environ["STUB_LOG"]
open(log, "a").write(" ".join(sys.argv[1:]) + "\\n")
if "claim" in sys.argv:
    n = len([l for l in open(log) if " claim " in " " + l])
    if n <= int(os.environ.get("STUB_REFUSE", "0")):
        print("LIGHT-REFUSED another light claim is open", file=sys.stderr); sys.exit(2)
    print("BUILD-GRANT build-tester-1 regions=84-87")
'''


class DeployLockClaim(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.flags = os.path.join(self.d, "flags")
        os.makedirs(os.path.join(self.flags, "bin", "rowflow"))
        stub = os.path.join(self.flags, "bin", "rowflow", "rowflow.py")
        open(stub, "w").write(STUB)
        os.chmod(stub, os.stat(stub).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.d, "stub.log")
        self.env = dict(os.environ, ROWFLOW_FLAGS=self.flags, STUB_LOG=self.log, DEPLOY_LIGHT_RETRY_S="0", USER="tester")

    def run_deploy(self, *args, **env):
        return subprocess.run(["bash", DEPLOY, *args], env=dict(self.env, **env), capture_output=True, text=True, timeout=60)

    def calls(self):
        return open(self.log).read().splitlines() if os.path.exists(self.log) else []

    def test_second_deploy_is_refused_by_the_flock(self):
        subprocess.run(["git", "init", "-q", self.d], check=True)
        subprocess.run(["git", "-C", self.d, "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "--allow-empty", "-m", "fixture"], check=True)
        # Bootstrap pins and validates the deploy script before acquiring the lock.
        os.makedirs(os.path.join(self.d, "scripts", "coordination", "rowflow"))
        import shutil
        shutil.copy(DEPLOY, os.path.join(self.d, "scripts", "coordination", "rowflow", "deploy_rowflow.sh"))
        subprocess.run(["git", "-C", self.d, "add", "scripts"], check=True)
        subprocess.run(["git", "-C", self.d, "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-q", "-m", "deploy fixture"], check=True)
        fd = os.open(os.path.join(self.flags, ".deploy_rowflow.lock"), os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            r = self.run_deploy("--ref", "HEAD", "--repo", self.d)
        finally:
            os.close(fd)
        self.assertEqual(r.returncode, 79, r.stderr)
        self.assertIn("another deploy_rowflow.sh holds", r.stderr)
        self.assertEqual(self.calls(), [])   # refused before any claim

    def test_light_claim_taken_gate_prefix_and_released_on_exit(self):
        r = self.run_deploy("--selftest-claim", "--by", "pipeline-mgmt")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("GATE_PREFIX=nice -n 19 taskset -c 84-87", r.stdout)
        c = self.calls()
        self.assertTrue(any("claim --build --light --owner pipeline-mgmt --cpus 84-87 --minutes 15" in x for x in c), c)
        self.assertTrue(any(x.endswith("release build-tester-1 --by pipeline-mgmt --reason deploy-gate-done") or
                            "release build-tester-1 --by pipeline-mgmt" in x for x in c), c)

    def test_owner_defaults_to_user_and_refusals_are_retried(self):
        r = self.run_deploy("--selftest-claim", STUB_REFUSE="2")
        self.assertEqual(r.returncode, 0, r.stderr)
        c = self.calls()
        self.assertEqual(len([x for x in c if " claim " in " " + x]), 3)
        self.assertIn("--owner tester", " ".join(c))
        self.assertIn("retry in 0s (2/15)", r.stderr)

    def test_no_claim_within_budget_refuses_without_installing(self):
        r = self.run_deploy("--selftest-claim", STUB_REFUSE="99", DEPLOY_LIGHT_TRIES="2")
        self.assertEqual(r.returncode, 80)
        self.assertIn("nothing installed", r.stderr)
        self.assertFalse(any("release" in x.split()[:1] for x in self.calls()))

    def test_lock_is_released_when_the_deploy_exits(self):
        self.assertEqual(self.run_deploy("--selftest-claim").returncode, 0)
        self.assertEqual(self.run_deploy("--selftest-claim").returncode, 0)


if __name__ == "__main__":
    unittest.main()
