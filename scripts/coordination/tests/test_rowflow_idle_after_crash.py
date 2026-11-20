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
        os.makedirs(os.path.join(self.flags, "grants"))
        self.job = os.path.join(self.flags, "job")
        os.makedirs(self.job)
        self.stop = os.path.join(self.job, "STOP")
        self.result = os.path.join(self.job, "results.jsonl")
        self.gpath = os.path.join(self.flags, "grants", RID + ".grant")
        open(self.gpath, "w").write("regions=0-23 holds=q0\n")
        self.manifest()
        # fixture job: the launcher forks a worker; the worker is killed, the launcher stays alive
        self.parent = subprocess.Popen([sys.executable, "-c", "import subprocess,sys,time\n"
                                        "w=subprocess.Popen(['sleep','600']); print(w.pid, flush=True); time.sleep(600)"],
                                       stdout=subprocess.PIPE, text=True)
        self.worker = int(self.parent.stdout.readline())
        self.emits, self.logs = [], []

    def manifest(self, **kw):
        json.dump(dict({"id": RID, "owner": "autokernel", "stop_file": self.stop, "result_path": self.result}, **kw),
                  open(rf.ready_path(self.flags, RID), "w"))

    def progress(self):
        time.sleep(0.01)
        open(self.result, "a").write('{"u": 1}\n')   # first progress, newer than the grant file

    def tearDown(self):
        for pid in (self.worker, self.parent.pid):   # only the pids this fixture captured
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        self.parent.wait(5)

    def grant(self):
        return {"id": RID, "regions": "0-23", "holds": {"q0"}, "start": "2026-11-20T00:00Z", "pid": self.parent.pid,
                "dryrun": False, "started": True, "path": self.gpath}

    def tick(self, now, busy=0.0):
        return rf.idle_after_crash(self.flags, [self.grant()], {"q0": busy}, self.logs.append, now=now,
                                   emit=lambda *a, **k: self.emits.append(a[1]) or {"ok": 1})

    def run_minutes(self, minutes, t0=None, busy=0.0):
        t0 = time.time() if t0 is None else t0
        return [self.tick(t0 + 60 * i, busy) for i in range(minutes + 1)]

    def test_genuinely_idle_10_min_stopped(self):
        self.progress()
        os.kill(self.worker, signal.SIGKILL)
        res = self.run_minutes(11)
        self.assertEqual(res[2], [(RID, "pending")])                     # alert at 2 samples ...
        self.assertEqual(self.emits[0], "idle-after-crash-pending")
        ended_at = next(i for i, r in enumerate(res) if r == [(RID, "ended")])
        self.assertEqual(ended_at, 10)                                  # ... act only after >= 10 min continuous
        self.assertIn("idle-after-crash", open(self.stop).read())
        self.assertEqual(self.emits[-1], "idle-after-crash")
        self.assertEqual(self.emits.count("idle-after-crash-pending"), 1)
        self.assertIsNone(self.parent.poll())                            # never killed
        self.assertEqual(res[11], [])                                    # once only

    def test_load_phase_over_2_min_not_stopped(self):
        self.progress()
        os.kill(self.worker, signal.SIGKILL)
        res = self.run_minutes(4)                                       # a quiet mmap load of ~4 min
        self.assertNotIn([(RID, "ended")], res)
        self.assertFalse(os.path.exists(self.stop))

    def test_no_first_progress_not_stopped(self):
        os.kill(self.worker, signal.SIGKILL)
        self.assertEqual([r for r in self.run_minutes(15) if r], [])
        self.assertFalse(os.path.exists(self.stop))
        self.assertEqual(self.emits, [])

    def test_build_row_not_stopped(self):
        self.progress()
        self.manifest(kind="build")
        os.kill(self.worker, signal.SIGKILL)
        self.assertEqual([r for r in self.run_minutes(15) if r], [])

    def test_quiet_host_and_timing_rows_not_stopped(self):
        self.progress()
        os.kill(self.worker, signal.SIGKILL)
        for kw in ({"shape": "quiet-host"}, {"shape": "gpu-q3"}, {"timing": "bench"}, {"admission_class": "block-timing-quiet"}):
            self.manifest(**kw)
            self.assertEqual([r for r in self.run_minutes(15) if r], [], kw)
        self.assertFalse(os.path.exists(self.stop))

    def test_single_process_worker_25pct_not_stopped(self):
        self.progress()
        state = {"cpu": 0.0}

        def tree(pid):   # the launcher IS the worker: 25% of one core, no descendants
            state["cpu"] += 15.0
            return {str(pid): ("1", state["cpu"])}
        with mock.patch.object(rf, "_tree_cpu", side_effect=tree):
            self.assertEqual([r for r in self.run_minutes(15) if r], [])
        self.assertFalse(os.path.exists(self.stop))

    def test_busy_region_never_ends(self):
        self.progress()
        os.kill(self.worker, signal.SIGKILL)
        self.assertEqual([r for r in self.run_minutes(12, busy=40.0) if r], [])

    def test_close_samples_do_not_count(self):
        self.progress()
        os.kill(self.worker, signal.SIGKILL)
        t0 = time.time()
        self.tick(t0)
        self.assertEqual(self.tick(t0 + 5), [])
        self.assertEqual(self.tick(t0 + 10), [])

    def test_dryrun_skipped(self):
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
