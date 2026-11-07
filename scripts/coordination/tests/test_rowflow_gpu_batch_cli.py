#!/usr/bin/env python3
"""Session review 2026-11-03 §5 item 8: queued GPU smokes run on ANY GPU-free tick, not only inside the keeper's
allocate. `rowflow.py gpu-batch` is the same start_gpu_batch the allocator calls, invocable by any session; the
allocator path is unchanged. Every outcome is one line naming the next command."""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402


class GpuBatchCliTests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "grants"))

    def _queue(self, rid="g1"):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), "GPU-SMOKE-QUEUED.json"), {"id": rid})

    def _cli(self, rl=None, grants=()):
        out = io.StringIO()
        with mock.patch.object(rf, "rl_status", return_value=rl or {rf.GPU: ("free", "")}), \
                mock.patch.object(rf, "open_grants", return_value=list(grants)), \
                mock.patch.object(rf, "alive", side_effect=lambda pid: pid == os.getpid()), \
                mock.patch.object(rf.subprocess, "Popen") as P, redirect_stdout(out):  # alive() shells out to ps
            P.return_value.pid = os.getpid()
            rc = rf.main(["--flags", self.flags, "gpu-batch"])
        lines = out.getvalue().strip().splitlines()
        self.assertEqual(len(lines), 1, lines)
        return rc, lines[0], P

    def test_nothing_queued(self):
        rc, line, P = self._cli()
        self.assertEqual(rc, 0)
        self.assertIn("no queued GPU smokes", line)
        P.assert_not_called()

    def test_gpu_free_starts_the_allocators_batch(self):
        self._queue()
        rc, line, P = self._cli()
        self.assertEqual(rc, 0)
        self.assertIn("GPU-SMOKE-BATCH started", line)
        self.assertIn("--run-gpu-queue", P.call_args[0][0])
        self.assertTrue(rf.gpu_batch_running(self.flags))

    def test_gpu_held_by_region_lock_or_grant_waits(self):
        self._queue()
        rc, line, P = self._cli(rl={rf.GPU: ("EXCL", "bench[pid 4133851] filler-x")})
        self.assertEqual(rc, 3)
        self.assertIn("GPU busy", line)
        self.assertIn("gpu-batch", line, "names the command to re-run")
        P.assert_not_called()
        rc, line, P = self._cli(grants=[{"id": "r9", "holds": {rf.GPU}}])
        self.assertEqual(rc, 3)
        self.assertIn("r9", line)
        P.assert_not_called()

    def test_running_batch_is_reported_not_restarted(self):
        self._queue()
        rf.atomic_json(rf.gpu_batch_lock(self.flags), {"pid": os.getpid()})
        rc, line, P = self._cli()
        self.assertEqual(rc, 0)
        self.assertIn("already running", line)
        P.assert_not_called()

    def test_hold_file_stops_it(self):
        self._queue()
        open(os.path.join(self.flags, "HOLD_operator"), "w").close()
        rc, line, P = self._cli()
        self.assertEqual(rc, 3)
        self.assertIn("HOLD", line)
        P.assert_not_called()

    def test_allocator_path_unchanged(self):
        src = open(os.path.join(os.path.dirname(_TESTS), "rowflow", "rowflow.py")).read()
        self.assertIn("if GPU in free and not dry and not admit_hold and start_gpu_batch(flags, log):", src)


if __name__ == "__main__":
    unittest.main()
