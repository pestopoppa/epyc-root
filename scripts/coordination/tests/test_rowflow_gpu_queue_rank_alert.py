#!/usr/bin/env python3
"""Operator 2026-11-06 (emergency): the queued-GPU-smoke batch (publish_row.py --run-gpu-queue)
  1. drains by priority_rank (unpublished.json), then queued_at, then id - not alphabetically;
  2. alerts the owner on EVERY non-PASS (FAIL with its FAIL path / fix_task; WAIT, an exception or a record-less FAIL leave a
     QUEUED-DROPPED record + alert) - there is no silent drop.
Every fix has a negative control: the same scenario with the old behaviour must fail the new assertion."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402


def alphabetical(flags, q):
    return os.path.basename(os.path.dirname(q))


class Base(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        self.p = [mock.patch.object(rf.notify, "_bus_send", return_value="skipped:test")]
        for p in self.p:
            p.start()
            self.addCleanup(p.stop)

    def queue(self, rid, rank=None, queued_at="2026-11-06T16:00:00Z", owner="main-x"):
        row = {"id": rid, "owner": owner}
        if rank is not None:
            row["priority_rank"] = rank
        rf.atomic_json(pr.unpublished_path(self.flags, rid), row)   # a queued row's manifest is unpublished until its smoke
        rf.atomic_json(pr.queued_path(self.flags, rid), {"id": rid, "queued_at": queued_at, "regions": "mi210_0,184-191",
                                                         "smoke_s": 60, "spec": {"id": rid}})

    def run_batch(self, verdicts=None, key=None):
        order, verdicts = [], verdicts or {}

        def dry(flags, rid, regions, one_quarter=False, smoke_s=None):
            order.append(rid)
            v = verdicts.get(rid, ("PASS", "ok"))
            if isinstance(v, Exception):
                raise v
            if v[0] == "FAIL" and v[1] != "norecord":
                rf.atomic_json(os.path.join(rf.dry_dir(flags, rid), "FAIL-1.json"),
                               {"id": rid, "reason": v[1], "fix_task": f"fix {rid}: {v[1]}", "kind": "smoke"})
            return v
        ctx = [mock.patch.object(rf, "dryrun_run", dry), mock.patch.object(pr, "file_if_complete", return_value=False)]
        if key:
            ctx.append(mock.patch.object(pr, "queue_order_key", key))
        for c in ctx:
            c.start()
        try:
            pr.run_gpu_queue(self.flags)
        finally:
            for c in ctx:
                c.stop()
        return order

    def alerts(self):
        p = os.path.join(self.flags, "rowflow-alerts.jsonl")
        return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


class RankOrder(Base):
    def _incident(self):
        # 2026-11-06 18:15Z: alphabetical put the rank-100 AITER row ahead of the rank-8 bisect
        self.queue("ak-asm-aiter-vs-c6-timing-20261106-r2")                       # no priority_rank -> 100
        self.queue("c7-q38-ppl-bisect-20261106", rank=8)
        self.queue("yarn-e1-mem-c7-20261106", rank=8, queued_at="2026-11-06T15:00:00Z")   # earlier queued_at beats the bisect
        self.queue("a-first-by-id-same-rank", rank=8, queued_at="2026-11-06T15:00:00Z")   # id breaks the last tie

    def test_rank_then_queued_time_then_id(self):
        self._incident()
        self.assertEqual(self.run_batch(), ["a-first-by-id-same-rank", "yarn-e1-mem-c7-20261106", "c7-q38-ppl-bisect-20261106",
                                            "ak-asm-aiter-vs-c6-timing-20261106-r2"])

    def test_negative_control_alphabetical_order_fails_the_assertion(self):
        self._incident()
        order = self.run_batch(key=alphabetical)
        self.assertEqual(order[0], "a-first-by-id-same-rank")
        self.assertLess(order.index("ak-asm-aiter-vs-c6-timing-20261106-r2"), order.index("c7-q38-ppl-bisect-20261106"))
        self.assertNotEqual(order[-1], "ak-asm-aiter-vs-c6-timing-20261106-r2")   # the old order is not the rank order

    def test_default_rank_is_100_and_explicit_zero_is_kept(self):
        self.queue("b-default")
        self.queue("z-zero", rank=0)
        self.assertEqual(self.run_batch(), ["z-zero", "b-default"])

    def test_rank_read_from_ready_manifest_when_not_unpublished(self):
        self.queue("a-late")
        self.queue("z-urgent", rank=1)
        os.replace(pr.unpublished_path(self.flags, "z-urgent"), rf.ready_path(self.flags, "z-urgent"))
        self.assertEqual(self.run_batch(), ["z-urgent", "a-late"])


class OwnerAlert(Base):
    def test_fail_alerts_with_id_reason_fix_task_and_fail_path(self):
        self.queue("c7b-fa128-gate-20261106")
        self.run_batch({"c7b-fa128-gate-20261106": ("FAIL", "VRAM never showed residency, max 13 MB")})
        a = [x for x in self.alerts() if x["kind"] == "smoke-fail"]
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["row_id"], "c7b-fa128-gate-20261106")
        self.assertEqual(a[0]["row_owner"], "main-x")
        self.assertIn("VRAM never showed residency", a[0]["summary"])
        self.assertTrue(a[0]["detail"]["fail_file"].endswith("FAIL-1.json"))
        self.assertIn("fix", a[0]["detail"]["fix_task"])
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, "c7b-fa128-gate-20261106")))   # still unpublished

    def test_fail_alert_is_idempotent_with_the_record_failed_path(self):
        self.queue("r1")
        self.run_batch({"r1": ("FAIL", "boom")})
        fp = os.path.join(rf.dry_dir(self.flags, "r1"), "FAIL-1.json")
        rf.notify.smoke_fail(self.flags, "r1", fp, rf.load_json(fp), owner="main-x")   # what record_fail already does in dryrun_run
        self.assertEqual(len([x for x in self.alerts() if x["kind"] == "smoke-fail"]), 1)

    def test_pass_emits_nothing(self):
        self.queue("ok1")
        self.run_batch()
        self.assertEqual(self.alerts(), [])

    def test_wait_is_not_a_silent_drop(self):
        self.queue("w1")
        self.run_batch({"w1": ("WAIT", "state dryrun-running; nothing to do")})
        a = self.alerts()
        self.assertEqual([x["kind"] for x in a], ["queued-smoke-dropped"])
        self.assertEqual(a[0]["row_id"], "w1")
        self.assertIn("dryrun-running", a[0]["summary"])
        self.assertTrue(os.path.exists(a[0]["detail"]["fail_file"]))
        self.assertIn("unpublished.json", a[0]["detail"]["fix_task"])
        self.assertTrue(os.path.exists(pr.unpublished_path(self.flags, "w1")))   # manifest kept for re-publish

    def test_exception_is_not_a_silent_drop(self):
        self.queue("e1")
        self.run_batch({"e1": RuntimeError("boom")})
        a = self.alerts()
        self.assertEqual([x["kind"] for x in a], ["queued-smoke-dropped"])
        self.assertIn("RuntimeError: boom", a[0]["summary"])

    def test_record_less_fail_is_not_a_silent_drop(self):
        self.queue("n1")
        self.run_batch({"n1": ("FAIL", "norecord")})
        self.assertEqual([x["kind"] for x in self.alerts()], ["queued-smoke-dropped"])

    def test_one_failing_row_does_not_stop_the_batch(self):
        self.queue("a1", rank=1)
        self.queue("b1", rank=2)
        order = self.run_batch({"a1": RuntimeError("x")})
        self.assertEqual(order, ["a1", "b1"])

    def test_negative_control_old_batch_alerts_nothing_for_wait(self):
        """The pre-fix batch (no alert_queued_nonpass) leaves a WAIT row with zero alerts and zero records: the silent drop."""
        self.queue("w2")
        with mock.patch.object(pr, "alert_queued_nonpass", lambda *a, **k: None):
            self.run_batch({"w2": ("WAIT", "state failed; nothing to do")})
        self.assertEqual(self.alerts(), [])
        self.assertFalse(os.path.exists(os.path.join(rf.dry_dir(self.flags, "w2"), "QUEUED-DROPPED-1.json")))
        self.assertFalse(os.path.exists(pr.queued_path(self.flags, "w2")))   # marker gone: the row vanished


if __name__ == "__main__":
    unittest.main()
