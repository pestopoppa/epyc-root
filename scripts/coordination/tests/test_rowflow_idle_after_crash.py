#!/usr/bin/env python3
"""F6 (AK audit B6): a grant whose launcher survives its crashed worker ends (alert first, then the STOP file);
UNDERUSED for 30 min sends one "shrink to <n> quarters" note to the owner."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

RID = "iac-row-20261120"


class IdleAfterCrash(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="iac-")
        os.makedirs(os.path.join(self.flags, "ready"))
        self.stop = os.path.join(self.flags, "job", "STOP")
        json.dump({"id": RID, "owner": "autokernel", "stop_file": self.stop}, open(rf.ready_path(self.flags, RID), "w"))
        # fixture job: the launcher forks a worker; the worker is killed, the launcher stays alive
        self.parent = subprocess.Popen([sys.executable, "-c", "import subprocess,sys,time\n"
                                        "w=subprocess.Popen(['sleep','600']); print(w.pid, flush=True); time.sleep(600)"],
                                       stdout=subprocess.PIPE, text=True)
        self.worker = int(self.parent.stdout.readline())
        self.emits, self.logs = [], []

    def tearDown(self):
        for pid in (self.worker, self.parent.pid):   # only the pids this fixture captured
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        self.parent.wait(5)

    def grant(self):
        return {"id": RID, "regions": "0-23", "holds": {"q0"}, "start": "2026-11-20T00:00Z", "pid": self.parent.pid,
                "dryrun": False, "started": True}

    def tick(self, now, busy=0.0):
        return rf.idle_after_crash(self.flags, [self.grant()], {"q0": busy}, self.logs.append, now=now,
                                   emit=lambda *a, **k: self.emits.append(a[1]) or {"ok": 1})

    def test_crashed_worker_grant_ended_within_10_min(self):
        os.kill(self.worker, signal.SIGKILL)
        t0 = time.time()
        self.assertEqual(self.tick(t0), [])                              # baseline
        self.assertEqual(self.tick(t0 + 60), [(RID, "pending")])         # alert before acting
        self.assertEqual(self.emits, ["idle-after-crash-pending"])
        self.assertFalse(os.path.exists(self.stop))
        self.assertEqual(self.tick(t0 + 120), [(RID, "ended")])          # 2 min < 10 min
        self.assertIn("idle-after-crash", open(self.stop).read())
        self.assertEqual(self.emits[-1], "idle-after-crash")
        self.assertIsNone(self.parent.poll())                             # never killed
        self.assertEqual(self.tick(t0 + 180), [])                        # once only

    def test_busy_region_never_ends(self):
        os.kill(self.worker, signal.SIGKILL)
        t0 = time.time()
        for i in range(4):
            self.assertEqual(self.tick(t0 + 60 * i, busy=40.0), [])
        self.assertFalse(os.path.exists(self.stop))

    def test_close_samples_do_not_count(self):
        os.kill(self.worker, signal.SIGKILL)
        t0 = time.time()
        self.tick(t0)
        self.assertEqual(self.tick(t0 + 5), [])
        self.assertEqual(self.tick(t0 + 10), [])
        self.assertFalse(os.path.exists(self.stop))

    def test_dryrun_and_unstarted_skipped(self):
        g = dict(self.grant(), dryrun=True)
        self.assertEqual(rf.idle_after_crash(self.flags, [g], {"q0": 0.0}, self.logs.append, now=time.time()), [])


class ShrinkSuggest(unittest.TestCase):
    def test_one_note_after_30_min(self):
        flags = tempfile.mkdtemp(prefix="shr-")
        os.makedirs(os.path.join(flags, "ready"))
        json.dump({"id": "w", "owner": "autokernel"}, open(rf.ready_path(flags, "w"), "w"))
        sent = []
        holders = {"q0": "w", "q1": "w", "q2": "w"}
        now = 10_000.0
        rf.shrink_suggest(flags, holders, [("q1", "w", 0.5), ("q2", "w", 0.4)], {"q1:w": now - 600, "q2:w": now - 600}, now,
                          lambda m: None, emit=lambda *a: sent.append(a) or {})
        self.assertEqual(sent, [])
        rf.shrink_suggest(flags, holders, [("q1", "w", 0.5), ("q2", "w", 0.4)], {"q1:w": now - 1900, "q2:w": now - 1900}, now,
                          lambda m: None, emit=lambda *a: sent.append(a) or {})
        self.assertEqual(len(sent), 1)
        self.assertIn("shrink to 1 quarter", sent[0][4])
        self.assertEqual(sent[0][6], "autokernel")


if __name__ == "__main__":
    unittest.main()
