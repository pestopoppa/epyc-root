"""filler_run15.sh mid-job STOP (keeper-friction-review 2026-11-05, refinement 4). Fake job + fake region-lock; temp dirs only.

The fake region-lock mirrors region_lock_cli's layout: the launcher `setsid`s it, it keeps running as the parent of the
`--inner` engine (it holds the claim), so the group kill must take the region-lock child, the inner engine and the job.
"""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

_RF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow")

FAKE_RL = """#!/bin/bash
# fake region-lock: record our pid, then run the inner as a CHILD (never exec) like region_lock_cli holding a claim
echo $$ > "$RL_PIDS/rl.pid"
while [ $# -gt 0 ] && [ "$1" != -- ]; do shift; done; shift
trap '' TERM
"$@" &
wait
"""
# the job ignores TERM and keeps a grandchild alive: only the KILL after the grace ends it
FAKE_JOB = """trap '' TERM; echo $$ > "$RL_PIDS/job.pid"; sleep 1000 & echo $! > "$RL_PIDS/child.pid"; while :; do sleep 1; done"""


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def alive(pid):
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() and not r.stdout.strip().startswith("Z")


class FillerStop(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="filler-stop-")
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        shutil.copy(os.path.join(_RF, "filler_run15.sh"), self.bin)  # no notify.py beside it: nothing is pushed
        self.rl = os.path.join(self.bin, "region-lock")
        open(self.rl, "w").write(FAKE_RL)
        os.chmod(self.rl, 0o755)
        self.pids = os.path.join(self.d, "pids")
        self.grants = os.path.join(self.d, "grants")
        os.makedirs(self.pids)
        os.makedirs(self.grants)
        self.stop = os.path.join(self.d, "row.STOP")
        self.proc = None

    def tearDown(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        shutil.rmtree(self.d, ignore_errors=True)

    def grant(self, rid):
        now = datetime.now(timezone.utc)
        with open(os.path.join(self.grants, rid + ".grant"), "w") as f:
            f.write(f"regions=q0 start={iso(now - timedelta(seconds=5))} end={iso(now + timedelta(seconds=900))}\n")

    def launch(self, rid, extra=()):
        env = dict(os.environ, FILLER_RL=self.rl, FILLER_FLAGS_DIR=self.d, FILLER_GRANTS_DIR=self.grants,
                   FILLER_STATE_DIR=os.path.join(self.d, "state"), FILLER_POLL="1", FILLER_DISK_FLOOR_GIB="0",
                   RL_PIDS=self.pids)
        argv = ["bash", os.path.join(self.bin, "filler_run15.sh"), "--id", rid, "--class", "cpu", "--cmd", FAKE_JOB,
                "--min-window", "60", "--stop", self.stop, "--complete-cmd", "false", "--workdir", self.d, *extra]
        self.log = open(os.path.join(self.d, rid + ".out"), "w")
        self.proc = subprocess.Popen(argv, env=env, stdout=self.log, stderr=subprocess.STDOUT)

    def out(self, rid):
        return open(os.path.join(self.d, rid + ".out")).read()

    def wait_file(self, path, t=30):
        end = time.time() + t
        while time.time() < end and not os.path.exists(path):
            time.sleep(0.2)
        return os.path.exists(path)

    def test_stop_midrun_kills_group_after_grace_and_writes_ended(self):
        rid = "stopmid"
        self.grant(rid)
        self.launch(rid, ["--stop-grace", "3"])
        self.assertTrue(self.wait_file(os.path.join(self.pids, "child.pid")), self.out(rid))
        pids = [int(open(os.path.join(self.pids, n)).read()) for n in ("rl.pid", "job.pid", "child.pid")]
        self.assertTrue(all(alive(p) for p in pids))
        t0 = time.time()
        open(self.stop, "w").close()
        self.assertEqual(self.proc.wait(timeout=60), 0, self.out(rid))
        took = time.time() - t0
        self.assertGreaterEqual(took, 3, "KILL came before the grace")
        self.assertLess(took, 25, "STOP not polled within 10 s + grace")
        ended = open(os.path.join(self.grants, rid + ".ended")).readline()
        self.assertRegex(ended, r"^rc=75 .*reason=stopped$")
        self.assertFalse(os.path.exists(os.path.join(self.grants, rid + ".grant")), "grant not released")
        time.sleep(0.5)
        self.assertEqual([p for p in pids if alive(p)], [], "region-lock child / job / grandchild survived")
        self.assertIn("STOP seen mid-run", self.out(rid))

    def test_stop_before_start_writes_terminal_ended(self):
        rid = "stopbefore"
        open(self.stop, "w").close()
        self.grant(rid)
        self.launch(rid)
        self.assertEqual(self.proc.wait(timeout=30), 0, self.out(rid))
        ended = open(os.path.join(self.grants, rid + ".ended")).readline()
        self.assertRegex(ended, r"^rc=75 .*reason=stopped-before-start$")
        self.assertFalse(os.path.exists(os.path.join(self.grants, rid + ".grant")))
        self.assertFalse(os.path.exists(os.path.join(self.pids, "job.pid")), "job started despite STOP")

    def test_bad_stop_grace_refused(self):
        r = subprocess.run(["bash", os.path.join(self.bin, "filler_run15.sh"), "--id", "x", "--class", "cpu", "--cmd", "true",
                            "--stop", self.stop, "--complete-cmd", "false", "--workdir", self.d, "--stop-grace", "1m"],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 64)


if __name__ == "__main__":
    unittest.main()
