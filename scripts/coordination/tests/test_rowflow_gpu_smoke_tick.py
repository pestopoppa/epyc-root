"""2026-11-21 keeper bug: queued GPU smokes went unrun for >1 h with the GPU idle. Cause: a DISK-PAUSE (admit_hold) gated
start_gpu_batch on the allocate tick, and IDLE-WHY gpu-quiet said "no runnable row needs it". On any tick where the GPU is
free and GPU-SMOKE-QUEUED markers exist the allocator starts the batch, except for a real quiet-host smoke hold or an
operator HOLD file. Mirrors the state: markers in dryrun/, no candidate rows, DISK-PAUSE active."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402
import diskpause  # noqa: E402
from test_rowflow_arming_park import Fixture  # noqa: E402

QUEUED = ("ak-a3b-nondet-gpu-20261121", "ak-gap-1-sample-gpu-20261121-r2")


class GpuSmokeTick(Fixture):
    def setUp(self):
        super().setUp()
        self.saved_extra = {k: getattr(rf, k) for k in ("quiet_host_smoke_hold",)}
        self.started = []
        rf.start_gpu_batch = lambda flags, log: (self.started.append(1), log("GPU-SMOKE-BATCH started pid=1"), True)[2]
        for rid in QUEUED:
            rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), "GPU-SMOKE-QUEUED.json"), {"id": rid, "smoke_s": 300})
        self._paused = diskpause.is_paused
        diskpause.is_paused = lambda flags: True      # the incident: DISK-PAUSE since 05:21Z
        self._tick = diskpause.tick
        diskpause.tick = lambda *a, **k: None

    def tearDown(self):
        diskpause.is_paused = self._paused
        diskpause.tick = self._tick
        for k, v in self.saved_extra.items():
            setattr(rf, k, v)
        super().tearDown()

    def test_disk_pause_does_not_starve_the_batch(self):
        self.tick()
        self.assertEqual(self.started, [1], "\n".join(self.lines))

    def test_operator_hold_file_blocks_and_idle_why_names_the_smokes(self):
        open(os.path.join(self.flags, diskpause.HOLD_FILE), "w").write("owner=op\nreason=test\n")
        self.tick()
        self.assertEqual(self.started, [])
        why = [x for x in self.lines if x.startswith(f"IDLE-WHY {rf.GPU}")]
        self.assertTrue(why and "2 queued GPU smoke(s)" in why[0] and QUEUED[0] in why[0], self.lines)

    def test_real_quiet_host_hold_blocks(self):
        rf.quiet_host_smoke_hold = lambda cands, *a, **k: ({"id": "qh-row", "rank": 57.0}, rf.time.time() + 100)
        self.tick()
        self.assertEqual(self.started, [])

    def test_note_when_batch_running(self):
        real = rf.gpu_batch_running
        rf.gpu_batch_running = lambda f: True
        try:
            self.assertIn("batch running", rf.gpu_idle_smoke_note(self.flags, "no runnable row needs it"))
        finally:
            rf.gpu_batch_running = real
