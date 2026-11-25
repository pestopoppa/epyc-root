#!/usr/bin/env python3
"""R8 (waste audit 2026-11-25, docs/design/ak-waste-audit-20261125.md): the GPU smoke hold ends when the smoke ends.
(1) the batch drops GPU-SMOKE-BATCH.lock the moment its queue is empty; (2) a smoke whose tree exited no longer holds the
device while its runner records the verdict; (3) a smoke PASS / FAIL / exit and a batch end wake the keeper (ready/ mtime
moves by >= 1 s, which the keeper's 5 s poll sees); (4) the wake adds no concurrency: start_gpu_batch still refuses a
second batch while a live one holds the lock; (5) after the keeper's own smoke exited, an EXCLUSIVE row needs one quiet
sample, but any KFD sighting after the exit still needs two."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402
import publish_row as pr  # noqa: E402


def keeper_stamp(flags):
    """The keeper's own wake expression: stat -c %Y grants ready | sort -n | tail -1."""
    out = subprocess.run(["stat", "-c", "%Y", os.path.join(flags, "grants"), os.path.join(flags, "ready")],
                         capture_output=True, text=True, check=True).stdout.split()
    return max(int(x) for x in out)


class R8Tests(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        for d in ("grants", "ready", "dryrun"):
            os.makedirs(os.path.join(self.flags, d))

    def _queue(self, rid):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), "GPU-SMOKE-QUEUED.json"), {"id": rid, "smoke_s": 30})

    # ---- (3) event-driven wake
    def test_poke_moves_keeper_stamp_even_within_same_second(self):
        m0 = keeper_stamp(self.flags)
        rf.poke_keeper(self.flags)
        self.assertGreater(keeper_stamp(self.flags), m0)
        m1 = keeper_stamp(self.flags)
        rf.poke_keeper(self.flags)
        self.assertGreater(keeper_stamp(self.flags), m1)

    def test_fail_record_wakes(self):
        rid = "r-fail"
        os.makedirs(rf.dry_dir(self.flags, rid))
        m0 = keeper_stamp(self.flags)
        with mock.patch.object(rf, "ak_failclass", return_value=None), mock.patch.object(rf.notify, "smoke_fail"):
            rf.record_fail(self.flags, rid, {"launcher": {"path": "/nonexistent"}}, "boom", {})
        self.assertTrue(os.path.exists(os.path.join(rf.dry_dir(self.flags, rid), "FAIL-1.json")))
        self.assertGreater(keeper_stamp(self.flags), m0)

    def test_smoke_exit_wakes(self):
        rid = "r-exit"
        os.makedirs(rf.dry_dir(self.flags, rid))
        m0 = keeper_stamp(self.flags)
        rf.record_smoke_exit(self.flags, rid, 12345, [12345], [])
        self.assertTrue(os.path.exists(rf.smoke_exited_path(self.flags, rid)))
        self.assertGreater(keeper_stamp(self.flags), m0)

    def test_pass_write_is_followed_by_poke(self):
        src = open(rf.__file__).read()
        i = src.index("atomic_json(pass_path(flags, rid), {\"id\": rid, \"passed_at\"")
        self.assertIn("poke_keeper(flags)", src[i:i + 300])

    # ---- (1) batch releases its lock when the queue is empty
    def test_batch_releases_own_lock_when_queue_empty(self):
        rf.atomic_json(rf.gpu_batch_lock(self.flags), {"pid": os.getpid(), "started": rf.now_iso()})
        m0 = keeper_stamp(self.flags)
        self.assertEqual(pr.run_gpu_queue(self.flags), 0)
        self.assertFalse(os.path.exists(rf.gpu_batch_lock(self.flags)))
        self.assertGreater(keeper_stamp(self.flags), m0)

    def test_batch_runs_queue_then_releases(self):
        self._queue("s1")
        rf.atomic_json(rf.gpu_batch_lock(self.flags), {"pid": os.getpid(), "started": rf.now_iso()})
        seen = []

        def smoke(flags, rid, regions, smoke_s, keep_on_wait=False):
            seen.append(os.path.exists(rf.gpu_batch_lock(flags)))   # lock held DURING the smoke
            return "FAIL", "x"
        with mock.patch.object(pr, "run_smoke", side_effect=smoke), mock.patch.object(pr, "alert_queued_nonpass"), \
                mock.patch.object(pr, "clear_stale_dryrun"):
            self.assertEqual(pr.run_gpu_queue(self.flags), 1)
        self.assertEqual(seen, [True])
        self.assertFalse(os.path.exists(rf.gpu_batch_lock(self.flags)))

    def test_batch_never_removes_another_batchs_lock(self):
        rf.atomic_json(rf.gpu_batch_lock(self.flags), {"pid": os.getpid() + 999999, "started": rf.now_iso()})
        pr.run_gpu_queue(self.flags)
        self.assertTrue(os.path.exists(rf.gpu_batch_lock(self.flags)))

    # ---- (4) no double batch / double grant from an early wake
    def test_no_second_batch_while_live_lock(self):
        self._queue("s1")
        rf.atomic_json(rf.gpu_batch_lock(self.flags), {"pid": os.getpid(), "started": rf.now_iso()})
        with mock.patch.object(rf, "alive", side_effect=lambda p: p == os.getpid()), \
                mock.patch.object(rf.subprocess, "Popen") as P:
            for _ in range(3):   # three event wakes in a row
                self.assertTrue(rf.start_gpu_batch(self.flags, lambda m: None))
        P.assert_not_called()

    # ---- (2) a smoke whose tree exited does not hold the GPU
    def _lock_sidecar(self, rid, at):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        rf.atomic_json(rf.smoke_lock_path(self.flags, rid), {"pid": os.getpid(), "who": "batch", "at": at})

    def test_exited_smoke_releases_hold(self):
        rid = "s-done"
        self._lock_sidecar(rid, "2026-11-25T10:00:00Z")
        with mock.patch.object(rf, "harness_tree", return_value=[]):
            self.assertIn(rid, rf.running_smoke_gpu_occupants(self.flags, {"pids": {os.getpid(): 1}}))
            rf.atomic_json(rf.smoke_exited_path(self.flags, rid), {"id": rid, "exited_at": "2026-11-25T10:01:00Z"})
            self.assertNotIn(rid, rf.running_smoke_gpu_occupants(self.flags, {"pids": {os.getpid(): 1}}))

    def test_old_exit_receipt_does_not_release_a_new_smoke(self):
        rid = "s-again"
        self._lock_sidecar(rid, "2026-11-25T10:05:00Z")
        rf.atomic_json(rf.smoke_exited_path(self.flags, rid), {"id": rid, "exited_at": "2026-11-25T10:01:00Z"})
        with mock.patch.object(rf, "harness_tree", return_value=[]):
            self.assertIn(rid, rf.running_smoke_gpu_occupants(self.flags, {"pids": {os.getpid(): 1}}))

    def test_running_json_still_holds(self):
        rid = "s-live"
        self._lock_sidecar(rid, "2026-11-25T10:00:00Z")
        rf.atomic_json(rf.running_path(self.flags, rid), {"pid": os.getpid(), "regions": "mi210_0,184-191"})
        rf.atomic_json(rf.smoke_exited_path(self.flags, rid), {"id": rid, "exited_at": "2026-11-25T10:01:00Z"})
        with mock.patch.object(rf, "harness_tree", return_value=[]):
            self.assertIn(rid, rf.running_smoke_gpu_occupants(self.flags, {"pids": {os.getpid(): 1}}))

    # ---- (5) quiet sampling after the keeper's own smoke
    def _gate(self, occ, sm):
        with mock.patch.object(rf, "gpu_occupancy", return_value=occ), \
                mock.patch.object(rf, "running_smoke_gpu_occupants", return_value=sm), \
                mock.patch.object(rf, "gpu_foreign", return_value=([], 0)), \
                mock.patch.object(rf, "state_dir", return_value=self.flags):
            return rf.gpu_quiet_gate(self.flags, [], {}, lambda m: None, set())

    def test_one_sample_after_own_smoke_exit(self):
        rid = "s1"
        os.makedirs(rf.dry_dir(self.flags, rid))
        dead = 2 ** 22 + 7
        self.assertIn("held by smoke", self._gate({"pids": {dead: 1}}, {rid: {"pids": [dead], "until": None}}))
        time.sleep(1.1)
        rf.atomic_json(rf.smoke_exited_path(self.flags, rid), {"id": rid, "exited_at": rf.now_iso()})
        self.assertIsNone(self._gate({"pids": {}}, {}))

    def test_two_samples_without_exit_receipt(self):
        rid = "s2"
        os.makedirs(rf.dry_dir(self.flags, rid))
        dead = 2 ** 22 + 9
        self._gate({"pids": {dead: 1}}, {rid: {"pids": [dead], "until": None}})
        self.assertIn("device quiet 1/2", self._gate({"pids": {}}, {}))
        self.assertIsNone(self._gate({"pids": {}}, {}))

    def test_kfd_after_exit_needs_two_samples(self):
        rid = "s3"
        os.makedirs(rf.dry_dir(self.flags, rid))
        dead = 2 ** 22 + 11
        self._gate({"pids": {dead: 1}}, {rid: {"pids": [dead], "until": None}})
        rf.atomic_json(rf.smoke_exited_path(self.flags, rid), {"id": "s3", "exited_at": "2000-01-01T00:00:00Z"})
        self.assertIn("device quiet 1/2", self._gate({"pids": {}}, {}))


if __name__ == "__main__":
    unittest.main()
