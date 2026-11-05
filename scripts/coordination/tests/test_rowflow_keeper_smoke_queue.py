#!/usr/bin/env python3
"""Operator 2026-11-05 ("doesn't it get queued by the keeper? That's the keeper's ENTIRE point!"): a CPU row's pre-publish
smoke is a KEEPER-SCHEDULED filler. publish_row queues it; the allocator places it first on 4 genuinely free cores;
waiting for a slot is WAIT, never FAIL; the first-progress timer starts only once the engine reached START."""
import os
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
sys.path.insert(0, _HERE)
from test_rowflow import Fixture  # noqa: E402

ALL = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)


def free_minus(*tokens):
    busy = rf.expand(set(tokens))
    busy |= {q for q in rf.QUARTERS if rf.expand({q}) & busy}
    return ALL - busy


class QueueAndPlaceTests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        self.rid = "c1"

    def _publish(self, spec, flags, source=None):
        rf.atomic_json(rf.ready_path(flags, self.rid), {"id": self.rid})
        return {"id": self.rid}

    def _queue(self):
        with mock.patch.object(rf, "publish", self._publish), \
                mock.patch.object(rf, "dryrun_run", side_effect=AssertionError("queued smokes never run in the owner's turn")):
            return pr.publish_smoked({"lane": "cpu"}, self.flags, "t", queue_cpu=True)

    def test_full_host_queues_then_waits_never_fails(self):
        self.assertIsNone(self._queue())
        self.assertTrue(os.path.exists(rf.smoke_queued_path(self.flags, self.rid)))
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, self.rid)), "unpublished until PASS")
        logs = []
        with mock.patch.object(rf.subprocess, "Popen", side_effect=AssertionError("nothing is free")):
            placed = rf.place_smokes(self.flags, free_minus(*rf.QUARTERS), logs.append)   # whole host held (npd1-step5)
        self.assertEqual(placed, [])
        self.assertTrue(any(l.startswith("SMOKE-WAIT c1") for l in logs), logs)
        self.assertEqual(rf.fail_paths(self.flags, self.rid), [])
        self.assertTrue(os.path.exists(rf.smoke_queued_path(self.flags, self.rid)), "still queued")

    def test_placed_on_the_next_tick_once_4_cpus_are_free(self):
        self._queue()
        free = free_minus("q0", "q1", "q3") - rf.expand({"q2"}) | {f"c{n}" for n in range(48, 52)} | {f"t{n}" for n in range(144, 148)}

        class P:
            pid = os.getpid()   # alive: the placed smoke's cpus then count as busy in the next snapshot
        calls = []
        with mock.patch.object(rf.subprocess, "Popen", side_effect=lambda argv, **kw: calls.append(argv) or P()):
            placed = rf.place_smokes(self.flags, free, print)
        self.assertEqual(placed, [("c1", "48-51")])
        self.assertIn("--run-smoke", calls[0])
        self.assertEqual(calls[0][calls[0].index("--regions") + 1], "48-51")
        self.assertFalse({"c48", "t144"} & free, "the smoke's cores leave the plan's free set")
        self.assertEqual(rf.load_json(rf.smoke_placed_path(self.flags, self.rid))["regions"], "48-51")
        with mock.patch.object(rf, "alive", return_value=True):
            self.assertTrue({"c48", "c51", "t147"} <= rf.live_smoke_tokens(self.flags))
            self.assertEqual(rf.place_smokes(self.flags, set(ALL), print), [], "already running: not placed twice")

    def test_pick_prefers_a_partly_used_quarter_and_never_the_mi210_host_threads(self):
        self.assertEqual(rf.pick_smoke_cpus(free_minus("c0")), "1-4")
        only_q3_tail = {f"c{n}" for n in range(88, 96)} | {f"t{n}" for n in range(184, 192)}
        self.assertIsNone(rf.pick_smoke_cpus(only_q3_tail))

    def test_quiet_grant_leaves_the_q3_coexist_cores_alone(self):
        self._queue()
        free = {f"c{n}" for n in range(84, 88)} | {f"t{n}" for n in range(180, 184)}
        logs = []
        with mock.patch.object(rf.subprocess, "Popen", side_effect=AssertionError("coexist cores are not free for smokes")):
            self.assertEqual(rf.place_smokes(self.flags, set(free), logs.append, reserved=rf.COEXIST_Q3), [])
        self.assertTrue(any(l.startswith("SMOKE-WAIT") for l in logs), logs)
        self.assertEqual([p for p in rf.place_smokes(self.flags, set(free), print, dry=True)], [("c1", "84-87")])

    def test_runner_wait_keeps_it_queued_pass_dequeues(self):
        self._queue()
        with mock.patch.object(rf, "dryrun_run", return_value=("WAIT", "lock")):
            self.assertEqual(pr.run_queued_smoke(self.flags, self.rid, "0-3"), "WAIT")
        self.assertTrue(os.path.exists(rf.smoke_queued_path(self.flags, self.rid)))
        self.assertEqual(rf.fail_paths(self.flags, self.rid), [])
        with mock.patch.object(rf, "dryrun_run", return_value=("PASS", "ok")), mock.patch.object(rf, "supersede"), \
                mock.patch.object(pr, "file_if_complete", return_value=False):
            self.assertEqual(pr.run_queued_smoke(self.flags, self.rid, "0-3"), "PASS")
        self.assertFalse(os.path.exists(rf.smoke_queued_path(self.flags, self.rid)))
        self.assertTrue(os.path.exists(rf.ready_path(self.flags, self.rid)))

    def test_gpu_smokes_keep_their_own_batch_queue(self):
        with mock.patch.object(rf, "publish", self._publish), mock.patch.object(pr, "gpu_busy", return_value=True):
            pr.publish_smoked({"lane": "gpu", "regions": "mi210_0,184-191"}, self.flags, "t", queue_cpu=True)
        self.assertTrue(os.path.exists(pr.queued_path(self.flags, self.rid)))
        self.assertFalse(os.path.exists(rf.smoke_queued_path(self.flags, self.rid)))
        with mock.patch.object(rf.subprocess, "Popen", side_effect=AssertionError("not a CPU smoke")):
            self.assertEqual(rf.place_smokes(self.flags, set(ALL), print), [])


class TimerTests(unittest.TestCase):
    """The first-progress timer starts at engine START (lock held), never at launch."""

    def _run(self, lines):
        fx = Fixture()
        self.addCleanup(fx.cleanup)
        rid = "t-timer"
        d = fx.job(rid)
        rf.publish(fx.spec(rid, d), fx.flags)
        clock = [1_000_000.0]

        def now():
            clock[0] += 7
            return clock[0]

        class Live:
            pid = 424242
            def poll(self): return None
            def wait(self, timeout=None): return 0

        def launch(argv, **kw):
            if argv[:2] == ["bash", "-c"]:
                raise AssertionError("no predicate")
            kw["stdout"].write("".join(l + "\n" for l in lines)); kw["stdout"].flush()
            return Live()
        with mock.patch.object(rf, "status", return_value={"state": "needs-dryrun"}), \
                mock.patch.object(rf, "row_orphans", return_value=[]), mock.patch.object(rf, "kill_group"), \
                mock.patch.object(rf, "reap_pids", return_value=([], [])), \
                mock.patch.object(rf.subprocess, "Popen", side_effect=launch), \
                mock.patch.object(rf.time, "sleep", return_value=None), mock.patch.object(rf.time, "time", side_effect=now):
            v, msg = rf.dryrun_run(fx.flags, rid, "0-3", True, smoke_s=60)
        return v, msg, rf.fail_paths(fx.flags, rid)

    def test_never_started_is_wait_not_fail(self):
        v, msg, fails = self._run(["2026-11-05T10:30:43Z [t-timer] launcher up pid=1 class=cpu"])
        self.assertEqual(v, "WAIT", msg)
        self.assertIn("did not reach START", msg)
        self.assertEqual(fails, [])

    def test_started_without_progress_fails_after_the_timer(self):
        v, msg, fails = self._run(["2026-11-05T10:30:43Z [t-timer] START regions=0-3 cpus=0-3"])
        self.assertEqual(v, "FAIL", msg)
        self.assertIn("of engine START", msg)
        self.assertTrue(fails)


if __name__ == "__main__":
    unittest.main()
