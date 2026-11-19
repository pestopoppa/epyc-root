#!/usr/bin/env python3
"""2026-11-19 (ak-gap-1-step1-gpu-20261119, D9 "Fix all"): the queued-GPU-smoke batch
  a. clears a stale RUNNING.json (dead pid + dead harness) before the smoke so it actually runs; a WAIT keeps the
     GPU-SMOKE-QUEUED marker with a wait_attempts count, puts the manifest back where it was (never into ready/ unsmoked,
     never stealing the ready/ manifest of a live concurrent smoke), and only the QUEUED_WAIT_MAX-th WAIT alerts + drops;
  b. queue_status lists a queued GPU smoke (manifest only in unpublished.json) as SMOKE-QUEUED (GPU), expected start = the
     end of the current GPU grant;
  c. smoke-fail / queued-smoke-dropped go to the row owner's roster id (autokernel), not the stale codex-ak-main-01a11473."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
_COORD = os.path.dirname(_TESTS)
_ROOT = os.path.dirname(os.path.dirname(_COORD))
sys.path.insert(0, os.path.join(_COORD, "rowflow"))
sys.path.insert(0, os.path.join(_ROOT, ".claude", "skills", "inference-backlog-scheduling", "scripts"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
import notify  # noqa: E402
import queue_status as qs  # noqa: E402

DEAD = 2 ** 22 + 12345   # above pid_max on this host: never alive


class Base(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.flags, True)
        os.makedirs(os.path.join(self.flags, "ready"))
        p = mock.patch.object(rf.notify, "_bus_send", return_value="skipped:test")
        p.start()
        self.addCleanup(p.stop)

    def queue(self, rid, owner="autokernel"):
        rf.atomic_json(pr.unpublished_path(self.flags, rid), {"id": rid, "owner": owner})
        rf.atomic_json(pr.queued_path(self.flags, rid), {"id": rid, "queued_at": "2026-11-19T17:46:00Z",
                                                         "regions": "mi210_0,184-191", "smoke_s": 60})

    def batch(self, verdict, seen=None):
        def dry(flags, rid, regions, one_quarter=False, smoke_s=None):
            if seen is not None:
                seen.append((os.path.exists(rf.running_path(flags, rid)), os.path.exists(rf.ready_path(flags, rid))))
            return verdict
        with mock.patch.object(rf, "dryrun_run", dry), mock.patch.object(pr, "file_if_complete", return_value=False):
            return pr.run_gpu_queue(self.flags)

    def alerts(self):
        p = os.path.join(self.flags, "rowflow-alerts.jsonl")
        return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


class StaleAndWait(Base):
    def test_stale_running_json_is_cleared_before_the_smoke(self):
        self.queue("s1")
        grant = os.path.join(rf.dry_dir(self.flags, "s1"), "grants", "s1.grant")
        os.makedirs(os.path.dirname(grant))
        open(grant, "w").write("regions=mi210_0 start=x end=y\n")
        rf.atomic_json(rf.running_path(self.flags, "s1"), {"pid": DEAD, "harness_pid": DEAD, "grant": grant})
        seen = []
        self.batch(("PASS", "ok"), seen)
        self.assertEqual(seen, [(False, True)])          # RUNNING.json gone, manifest in ready/ when the smoke ran
        self.assertFalse(os.path.exists(grant))

    def test_live_running_json_is_left_alone(self):
        self.queue("s2")
        rf.atomic_json(rf.running_path(self.flags, "s2"), {"pid": os.getpid(), "harness_pid": DEAD})
        self.assertFalse(pr.clear_stale_dryrun(self.flags, "s2"))
        self.assertTrue(os.path.exists(rf.running_path(self.flags, "s2")))

    def test_wait_keeps_marker_counts_and_restores_manifest(self):
        self.queue("w1")
        for k in range(1, pr.QUEUED_WAIT_MAX):
            self.batch(("WAIT", "state dryrun-running; nothing to do"))
            q = rf.load_json(pr.queued_path(self.flags, "w1"))
            self.assertEqual(q["wait_attempts"], k)
            self.assertTrue(os.path.exists(pr.unpublished_path(self.flags, "w1")))
            self.assertFalse(os.path.exists(rf.ready_path(self.flags, "w1")))   # never sits in ready/ unsmoked
            self.assertEqual(self.alerts(), [])
        self.batch(("WAIT", "state dryrun-running; nothing to do"))
        self.assertFalse(os.path.exists(pr.queued_path(self.flags, "w1")))
        self.assertEqual([a["kind"] for a in self.alerts()], ["queued-smoke-dropped"])
        self.assertIn(f"WAIT in {pr.QUEUED_WAIT_MAX} batches", self.alerts()[0]["summary"])

    def test_wait_does_not_steal_a_live_concurrent_smokes_ready_manifest(self):
        """The incident: another smoke had moved the manifest to ready/ and was running; the batch's WAIT unpublished it,
        so the concurrent PASS landed with no ready manifest."""
        self.queue("c1")
        os.replace(pr.unpublished_path(self.flags, "c1"), rf.ready_path(self.flags, "c1"))
        self.batch(("WAIT", "state dryrun-running; nothing to do"))
        self.assertTrue(os.path.exists(rf.ready_path(self.flags, "c1")))
        self.assertTrue(os.path.exists(pr.queued_path(self.flags, "c1")))

    def test_fail_still_unpublishes_and_dequeues(self):
        self.queue("f1")
        self.batch(("FAIL", "norecord"))
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, "f1")))
        self.assertFalse(os.path.exists(pr.queued_path(self.flags, "f1")))


class QueueStatusGpu(Base):
    def test_gpu_queued_row_listed_with_expected_start(self):
        self.queue("g1")
        os.makedirs(os.path.join(self.flags, "grants"))
        open(os.path.join(self.flags, "grants", "other.grant"), "w").write(
            "regions=mi210_0,184-191 start=2026-11-19T17:00Z end=2026-11-19T19:30Z holds=gpu-quiet,q3\n")
        with mock.patch.object(qs, "keeper_state", return_value={"parsed": {}, "idle_why": {}, "snapshot_at": None}):
            r = qs.classify(self.flags)
        rec = [x for x in r["SMOKE-QUEUED"] if x["id"] == "g1"]
        self.assertEqual(len(rec), 1, r["SMOKE-QUEUED"])
        self.assertEqual(rec[0]["kind"], "SMOKE-QUEUED (GPU)")
        self.assertTrue(rec[0]["expected_start"].startswith("2026-11-19T19:30Z"), rec[0])

    def test_no_gpu_grant_means_now(self):
        self.queue("g2")
        with mock.patch.object(qs, "keeper_state", return_value={"parsed": {}, "idle_why": {}, "snapshot_at": None}):
            r = qs.classify(self.flags)
        self.assertTrue([x for x in r["SMOKE-QUEUED"] if x["id"] == "g2"][0]["expected_start"].startswith("now"))


class OwnerRouting(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bus = os.path.join(self.root, "bus")
        shutil.copytree(os.path.join(_ROOT, "coordination", "session-bus"), self.bus,
                        ignore=shutil.ignore_patterns("outbox", "inbox", "archive", "*.jsonl", "claims", "tasks", "tokens"))
        self.env = mock.patch.dict(os.environ, {"ROWFLOW_BUS_ROOT": self.bus,
                                                "ROWFLOW_SESSION_BUS": os.path.join(_COORD, "session_bus.py")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.flags = os.path.join(self.root, "flags")
        os.makedirs(os.path.join(self.flags, "ready"))

    def test_smoke_fail_routes_to_autokernel(self):
        m = notify.smoke_fail(self.flags, "r1", os.path.join(self.flags, "FAIL-1.json"), {"reason": "boom"}, owner="autokernel")
        self.assertTrue(m["bus"].startswith("sent:autokernel:"), m["bus"])

    def test_queued_smoke_dropped_routes_to_autokernel(self):
        m = notify.emit(self.flags, "queued-smoke-dropped", "r2", "QUEUED-DROPPED-1.json", "row r2 dropped", "warning",
                        "autokernel", {"reason": "x"})
        self.assertTrue(m["bus"].startswith("sent:autokernel:"), m["bus"])
        self.assertNotIn("codex-ak-main-01a11473", m["bus"])


if __name__ == "__main__":
    unittest.main()
