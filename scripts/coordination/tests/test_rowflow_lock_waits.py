#!/usr/bin/env python3
"""Session review 2026-11-03 §5 item 8: the dry run's lock-wait detector must match region-lock's REAL stderr lines
(epyc-orchestrator src/runtime/region_lock_cli.py). The old pattern only knew `acquiring regions [...]` and never matched
`acquiring gpu-quiet exclusive + regions [...]` nor the `waiting Ns for <region>` holder line."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "rowflow"))
import rowflow as rf  # noqa: E402
sys.path.insert(0, _HERE)
from test_rowflow import Fixture  # noqa: E402
from unittest import mock  # noqa: E402

ACQ_GPU = "[region-lock] acquiring gpu-quiet exclusive + regions ['q0', 'q1'] as role='bench' (timeout_s=600.0) …"
ACQ_REG = "[region-lock] acquiring regions ['q2'] as role='build' (timeout_s=10.0) …"
ACQ_GPU_ONLY = "[region-lock] acquiring gpu-quiet shared as role='bench' (timeout_s=600.0) …"
WAIT_Q0 = ("[region-lock] waiting 15.0s for q0 (q0.lock) as role='bench' tag='filler-x': held by pid 4133851 "
           "role=bench tag=filler-other age=812s")
WAIT_GPU = ("[region-lock] waiting 30.2s for gpu-quiet (gpu-quiet.lock) as role='bench' tag='t': held by pid 9 role=bench "
            "tag=filler-y age=40s | vram=3.1GiB busy=97%")
HELD_GPU = "[region-lock] held gpu-quiet exclusive + regions ['q0', 'q1'] after 41.0s wait; running: bash job.sh"
HELD_REG = "[region-lock] held ['q2'] after 0.0s wait; running: bash job.sh"
HELD_GPU_ONLY = "[region-lock] held gpu-quiet shared + regions [] after 0.0s wait; running: x"
TIMEOUT = "[region-lock] TIMEOUT acquiring regions ['q2']: CpuRegionLockTimeout(...)"


class LockWaitTests(unittest.TestCase):
    def test_acquiring_gpu_quiet_plus_regions_is_a_pending_claim(self):
        self.assertEqual(rf.lock_waits([ACQ_GPU], set()), [{"gpu-quiet", "q0", "q1"}])
        self.assertEqual(rf.lock_waits([ACQ_GPU, HELD_GPU], set()), [])

    def test_plain_regions_form_still_works(self):
        self.assertEqual(rf.lock_waits([ACQ_REG], set()), [{"q2"}])
        self.assertEqual(rf.lock_waits([ACQ_REG, HELD_REG], set()), [])
        self.assertEqual(rf.lock_waits([ACQ_REG, TIMEOUT], set()), [], "a timed-out acquire is no longer waiting")

    def test_gpu_only_form(self):
        self.assertEqual(rf.lock_waits([ACQ_GPU_ONLY], set()), [{"gpu-quiet"}])
        self.assertEqual(rf.lock_waits([ACQ_GPU_ONLY, HELD_GPU_ONLY], set()), [])

    def test_waiting_line_is_a_wait_even_without_its_acquire_line(self):
        self.assertEqual(rf.lock_waits([WAIT_Q0], set()), [{"q0"}])
        self.assertEqual(rf.lock_waits([WAIT_GPU], set()), [{"gpu-quiet"}])
        self.assertEqual(rf.lock_waits([ACQ_GPU, WAIT_Q0], set()), [{"gpu-quiet", "q0", "q1"}], "folded into its acquire")
        self.assertEqual(rf.lock_waits([ACQ_GPU, WAIT_Q0, HELD_GPU], set()), [])

    def test_unrelated_lines_are_ignored(self):
        lines = ["[region-lock] dry run: no lock taken (cpus=0-3)", "2026-11-03T10:00:00Z [x] START regions=0-3",
                 "[region-lock] held sub-quarter cores {q0: [0, 1]}"]
        self.assertEqual(rf.lock_waits(lines, set()), [])


class DryrunLockWaitTests(unittest.TestCase):
    def test_smoke_waits_never_fails_when_the_job_waits_on_a_region_lock(self):
        """operator 2026-11-05: lock contention is WAIT (requeued by the keeper), never FAIL."""
        fx = Fixture()
        try:
            rid = "t-lockwait"
            d = fx.job(rid)
            rf.publish(fx.spec(rid, d), fx.flags)

            class Live:
                pid = 424242
                def poll(self): return None
                def wait(self, timeout=None): return 0

            def launch(argv, **kw):
                kw["stdout"].write(ACQ_GPU + "\n" + WAIT_Q0 + "\n")
                kw["stdout"].flush()
                return Live()
            with mock.patch.object(rf, "status", return_value={"state": "needs-dryrun"}), \
                    mock.patch.object(rf, "row_orphans", return_value=[]), mock.patch.object(rf, "kill_group"), \
                    mock.patch.object(rf, "reap_pids", return_value=([], [])), \
                    mock.patch.object(rf.subprocess, "Popen", side_effect=launch), \
                    mock.patch.object(rf.time, "sleep", return_value=None):
                v, msg = rf.dryrun_run(fx.flags, rid, "48-51", True, smoke_s=300)
            self.assertEqual(v, "WAIT", msg)
            self.assertTrue(msg.startswith("job waits on region-lock for gpu-quiet,q0,q1 while the smoke holds"), msg)
            self.assertIn("no FAIL recorded", msg)
            self.assertNotIn("\n", msg)
            self.assertEqual(rf.fail_paths(fx.flags, rid), [])
        finally:
            fx.cleanup()


if __name__ == "__main__":
    unittest.main()
