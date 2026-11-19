#!/usr/bin/env python3
"""Audit #1 (GPU residency attribution): filler_run15 runs the job in its own cgroup v2 leaf <base>/<id>@<launcher pid>.
A cleaned-env, setsid, double-forked grandchild stays in it, so rowflow attributes it by /proc/<pid>/cgroup alone; the leaf
is removed when the row ends. With no usable base the engine runs the job anyway (legacy attribution)."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_RF = os.path.join(os.path.dirname(_HERE), "rowflow")
sys.path.insert(0, _RF)
import rowflow as rf  # noqa: E402

BASE = "/sys/fs/cgroup/rowflow"
# the job detaches a grandchild the old layers could miss: env -i (no FILLER_ID), new session, double fork
JOB = ("env -i /usr/bin/setsid /bin/bash -c '( /usr/bin/setsid /bin/sleep 1000 & echo $! > \"$0\" ) ; /bin/sleep 1000' "
       "\"$FILLER_STATE_DIR/gc.pid\"")


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class EngineLeaf(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="filler-cg-")
        self.bin, self.grants, self.state = (os.path.join(self.d, x) for x in ("bin", "grants", "state"))
        for p in (self.bin, self.grants, self.state):
            os.makedirs(p)
        shutil.copy(os.path.join(_RF, "filler_run15.sh"), self.bin)
        self.stop = os.path.join(self.d, "row.STOP")
        self.proc = None

    def tearDown(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        shutil.rmtree(self.d, ignore_errors=True)

    def launch(self, rid, base):
        now = datetime.now(timezone.utc)
        with open(os.path.join(self.grants, rid + ".grant"), "w") as f:
            f.write(f"regions=q0 start={iso(now - timedelta(seconds=5))} end={iso(now + timedelta(seconds=900))}\n")
        rl = os.path.join(self.bin, "region-lock")
        open(rl, "w").write('#!/bin/bash\nwhile [ $# -gt 0 ] && [ "$1" != -- ]; do shift; done; shift\n"$@" &\nwait\n')
        os.chmod(rl, 0o755)
        env = dict(os.environ, FILLER_FLAGS_DIR=self.d, FILLER_GRANTS_DIR=self.grants, FILLER_STATE_DIR=self.state,
                   FILLER_POLL="1", FILLER_DISK_FLOOR_GIB="0", FILLER_DOCKER_BIN="/nonexistent/docker", FILLER_RL=rl,
                   FILLER_CGROUP_BASE=base)
        argv = ["bash", os.path.join(self.bin, "filler_run15.sh"), "--id", rid, "--class", "cpu", "--cmd", JOB,
                "--min-window", "60", "--stop", self.stop, "--complete-cmd", "false", "--workdir", self.d, "--stop-grace", "3"]
        self.log = os.path.join(self.d, rid + ".out")
        self.proc = subprocess.Popen(argv, env=env, stdout=open(self.log, "w"), stderr=subprocess.STDOUT)

    def grandchild(self):
        p = os.path.join(self.state, "gc.pid")
        for _ in range(150):
            try:
                return int(open(p).read())
            except (OSError, ValueError):
                time.sleep(0.2)
        self.fail(open(self.log).read())

    @unittest.skipUnless(os.access(BASE, os.W_OK), "no writable cgroup v2 rowflow base")
    def test_detached_grandchild_is_in_the_row_leaf_and_leaf_is_removed(self):
        rid = f"cgleaf-{os.getpid()}"
        self.launch(rid, BASE)
        gc = self.grandchild()
        leaf = os.path.join(BASE, f"{rid}@{self.proc.pid}")
        try:
            self.assertEqual(rf.pid_cgroup_row(gc), rid)
            self.assertNotIn(b"FILLER_ID", open(f"/proc/{gc}/environ", "rb").read())
            self.assertIn(gc, rf.row_leaf_pids(rid)[1])
            self.assertFalse(rf.pid_is_rows(gc, "another-row", {gc}))
            open(self.stop, "w").close()
            self.assertEqual(self.proc.wait(timeout=60), 0, open(self.log).read())
            self.assertFalse(os.path.exists(leaf), open(self.log).read())
            self.assertFalse(os.path.exists(f"/proc/{gc}") and rf._proc_stat(gc), "grandchild survived the row")
        finally:
            if os.path.isdir(leaf):   # cleanup only our own leaf
                open(os.path.join(leaf, "cgroup.kill"), "w").write("1")
                time.sleep(0.5)
                os.rmdir(leaf)

    def test_unusable_base_runs_the_job_anyway(self):
        rid = "cgleaf-nobase"
        self.launch(rid, "/proc/no-cgroup-here")   # mkdir fails there
        gc = self.grandchild()
        self.assertIsNone(rf.pid_cgroup_row(gc))
        self.assertIn("WARN cgroup: no leaf", open(self.log).read())
        open(self.stop, "w").close()
        self.assertEqual(self.proc.wait(timeout=60), 0, open(self.log).read())


if __name__ == "__main__":
    unittest.main()
