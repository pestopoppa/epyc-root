#!/usr/bin/env python3
"""AK audit acceptance fixtures (test-only items from the F2-F9 triage, plus the B1 orphan detector):
  B1  five GPU rows queued while a fixture grant holds the MI210; once released, ONE batch smokes all five in
      priority_rank order with no owner action; a marker deleted by hand -> one owner-addressed alert within one tick.
  B14 a GPU row's smoke runs on mi210_0,184-191 (never the 4-cpu pocket) and the residency check applies to it."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402

GPU_REGIONS = "mi210_0,184-191"


class Base(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp(prefix="b1-")
        self.addCleanup(shutil.rmtree, self.flags, True)
        os.makedirs(os.path.join(self.flags, "ready"))
        p = mock.patch.object(rf.notify, "_bus_send", return_value="skipped:test")
        p.start()
        self.addCleanup(p.stop)


class B1FiveRowOrdering(Base):
    RANKS = {"gpu-e-20261120": 50, "gpu-a-20261120": 90, "gpu-c-20261120": 10, "gpu-b-20261120": 30, "gpu-d-20261120": 70}

    def test_five_rows_run_in_priority_order_after_release(self):
        busy = {"held": True}
        with mock.patch.object(pr, "gpu_busy", side_effect=lambda flags: busy["held"]), \
                mock.patch.object(pr.rf, "publish", side_effect=lambda spec, flags, source=None: (
                    rf.atomic_json(rf.ready_path(flags, spec["id"]), dict(spec)) or dict(spec))), \
                mock.patch.object(pr, "retire_old_verdicts"), mock.patch.object(pr, "supersede_prior_attempts"):
            for rid, rank in self.RANKS.items():
                self.assertIsNone(pr.publish_smoked({"id": rid, "owner": "autokernel", "lane": "gpu", "regions": GPU_REGIONS,
                                                     "priority_rank": rank}, self.flags, "src"))
        self.assertEqual(len([r for r in self.RANKS if os.path.exists(pr.queued_path(self.flags, r))]), 5)
        self.assertEqual([r for r in self.RANKS if os.path.exists(rf.ready_path(self.flags, r))], [])
        busy["held"] = False   # the fixture grant releases the MI210; the allocator's one batch runs
        order = []

        def dry(flags, rid, regions, one_quarter=False, smoke_s=None):
            order.append((rid, regions))
            return "PASS", "first progress"
        with mock.patch.object(rf, "dryrun_run", dry), mock.patch.object(pr, "file_if_complete", return_value=False), \
                mock.patch.object(rf, "supersede"):
            self.assertEqual(pr.run_gpu_queue(self.flags), 5)
        self.assertEqual([r for r, _ in order], sorted(self.RANKS, key=self.RANKS.get))
        self.assertTrue(all(reg == GPU_REGIONS for _, reg in order))
        self.assertEqual(sorted(r for r in self.RANKS if os.path.exists(rf.ready_path(self.flags, r))), sorted(self.RANKS))

    def test_hand_deleted_marker_alerts_owner_within_one_tick(self):
        rid = "gpu-x-20261120"
        rf.atomic_json(pr.unpublished_path(self.flags, rid), {"id": rid, "owner": "autokernel"})
        rf.atomic_json(pr.queued_path(self.flags, rid), {"id": rid, "queued_at": rf.now_iso()})
        now = time.time() + 300
        self.assertEqual(rf.orphaned_smoke_alerts(self.flags, log=lambda m: None, now=now), [])   # marker present
        os.remove(pr.queued_path(self.flags, rid))                                                # by hand
        self.assertEqual(rf.orphaned_smoke_alerts(self.flags, log=lambda m: None, now=now), [rid])
        self.assertEqual(rf.orphaned_smoke_alerts(self.flags, log=lambda m: None, now=now + 60), [])   # once
        a = [json.loads(x) for x in open(os.path.join(self.flags, "rowflow-alerts.jsonl"))]
        self.assertEqual([(x["kind"], x["row_owner"]) for x in a], [("queued-smoke-orphaned", "autokernel")])

    def test_fail_record_is_not_an_orphan(self):
        rid = "gpu-y-20261120"
        rf.atomic_json(pr.unpublished_path(self.flags, rid), {"id": rid, "owner": "autokernel"})
        time.sleep(0.01)
        rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), "FAIL-1.json"), {"reason": "x"})
        self.assertEqual(rf.orphaned_smoke_alerts(self.flags, log=lambda m: None, now=time.time() + 300), [])


class B14GpuSmokeResidency(Base):
    def test_gpu_row_smoke_runs_on_mi210_with_residency_required(self):
        seen = []

        def dry(flags, rid, regions, one_quarter=False, smoke_s=None, **kw):
            seen.append(regions)
            return "PASS", "resident"
        row = {"id": "gpu-r-20261120", "owner": "autokernel", "lane": "gpu", "regions": GPU_REGIONS}
        with mock.patch.object(pr, "gpu_busy", return_value=False), \
                mock.patch.object(pr.rf, "publish", side_effect=lambda spec, flags, source=None: (
                    rf.atomic_json(rf.ready_path(flags, spec["id"]), dict(spec)) or dict(spec))), \
                mock.patch.object(pr, "retire_old_verdicts"), mock.patch.object(pr, "supersede_prior_attempts"), \
                mock.patch.object(rf, "dryrun_run", dry), mock.patch.object(pr, "file_if_complete", return_value=False), \
                mock.patch.object(rf, "supersede"):
            self.assertIsNotNone(pr.publish_smoked(row, self.flags, "src", queue_cpu=True))
        self.assertEqual(seen, [GPU_REGIONS])                       # never the 4-cpu pocket
        self.assertTrue(rf.gpu_residency_required(row, seen[0]))   # the smoke must prove VRAM residency
        self.assertFalse(rf.gpu_residency_required(dict(row, gpu_use="quiet-only"), seen[0]))


if __name__ == "__main__":
    unittest.main()
