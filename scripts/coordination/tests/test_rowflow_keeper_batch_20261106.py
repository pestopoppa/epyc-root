#!/usr/bin/env python3
"""Operator 2026-11-06 emergency batch (keeper): (1) lineage unpark + one fresh attempt per new launcher/job sha,
(2) NEEDS-OWNER vs NEEDS-OPERATOR, (3) rank across the smoke queue, (4) predicate rows' smoke not self-shrunk to one unit,
(5) 1 s residency (the job-written record was retired by audit #1). Every fix carries a negative control."""
import json
import os
import sys
import textwrap
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
sys.path.insert(0, _TESTS)
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture, write  # noqa: E402


def put_fail(fx, oid, n, launcher_sha, at, job_sha=None):
    dd = rf.dry_dir(fx.flags, oid)
    os.makedirs(dd, exist_ok=True)
    rec = {"id": oid, "at": at, "launcher_sha256": launcher_sha, "reason": "smoke_predicate never passed", "kind": "smoke"}
    if job_sha:
        rec["job_sha256"] = job_sha
    rf.atomic_json(os.path.join(dd, f"FAIL-{n}.json"), rec)


class Lineage(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)
        self.rid = "lin-a-20261101"
        d = self.fx.job(self.rid)
        rf.publish(self.fx.spec(self.rid, d, lineage="lin-a"), self.fx.flags)
        self.d = d
        self.cur = rf.sha256(os.path.join(d, "launch.sh"))
        for i in range(rf.MAX_FAILS):
            put_fail(self.fx, self.rid, i + 1, "oldsha", "2026-11-06T10:00:0%dZ" % i)

    def st(self):
        rf.row_sha  # noqa: B018
        return rf.status(self.fx.flags, self.rid)

    def pin_current(self):
        """one FAIL already carries the current launcher+job sha: no fresh attempt is left, the lineage is parked"""
        put_fail(self.fx, self.rid, 9, self.cur, "2026-11-06T10:00:09Z", job_sha=rf.job_sha(os.path.join(self.d, "launch.sh")))

    def test_parked_by_failures_then_owner_unparks_by_lineage_id(self):
        self.pin_current()
        self.assertEqual(self.st()["state"], "parked")
        self.assertEqual(self.st()["lineage"], "lin-a")
        # `unpark <lineage id>`: not a ready/ row, no dryrun dir of its own yet
        rec = rf.unpark(self.fx.flags, "lin-a", by="owner")
        self.assertTrue(rec["at"])
        st = self.st()
        self.assertNotEqual(st["state"], "parked", st)
        self.assertEqual(st["lineage_fails"], 0)

    def test_negative_control_without_unpark_stays_parked(self):
        self.pin_current()
        self.assertEqual(self.st()["state"], "parked")
        self.assertEqual(self.st()["lineage_fails"], rf.MAX_FAILS + 1)

    def test_new_failures_after_unpark_count_again(self):
        self.pin_current()
        rf.unpark(self.fx.flags, "lin-a", by="owner")
        import time
        time.sleep(1.1)
        for i in range(rf.MAX_FAILS):
            put_fail(self.fx, self.rid, 10 + i, "oldsha", rf.now_iso())
        self.assertEqual(self.st()["state"], "parked")

    def test_changed_launcher_gets_one_fresh_attempt_then_parks_again(self):
        self.assertEqual(self.st()["state"], "needs-dryrun")          # fails recorded for "oldsha"; current sha is new
        put_fail(self.fx, self.rid, 9, self.cur, rf.now_iso(), job_sha=rf.job_sha(os.path.join(self.d, "launch.sh")))
        self.assertEqual(self.st()["state"], "parked")                # the one attempt failed: parked again, no second try

    def test_changed_job_file_with_same_launcher_is_fresh(self):
        job = os.path.join(self.d, "job.sh")
        lp = os.path.join(self.d, "launch.sh")
        put_fail(self.fx, self.rid, 9, self.cur, rf.now_iso(), job_sha=rf.job_sha(lp))
        self.assertEqual(self.st()["state"], "parked")
        with open(job, "a") as f:
            f.write("\n# edited\n")
        self.assertEqual(self.st()["state"], "needs-dryrun")


class Escalation(unittest.TestCase):
    def test_tags(self):
        self.assertEqual(rf.escalation_tag([("fix", False), ("drop", False)]), "NEEDS-OWNER")
        self.assertEqual(rf.escalation_tag([("fix", False), ("ratify the change", True)]), "NEEDS-OPERATOR")

    def test_lineage_and_arming_files_say_needs_owner(self):
        fx = Fixture()
        self.addCleanup(fx.cleanup)
        rid = "esc-a-20261101"
        rf.publish(fx.spec(rid, fx.job(rid), lineage="esc-a"), fx.flags)
        for i in range(rf.MAX_FAILS):
            put_fail(fx, rid, i + 1, "x", "2026-11-06T10:00:0%dZ" % i)
        rf.write_escalation(fx.flags, rid, rf.rows(fx.flags))
        head = open(os.path.join(fx.flags, "operator-escalations", "esc-a.md")).readline()
        self.assertIn("NEEDS-OWNER", head)
        self.assertNotIn("NEEDS-OPERATOR", head)
        self.assertIn("unpark", open(os.path.join(fx.flags, "operator-escalations", "esc-a.md")).read())


class RankAcrossQueues(unittest.TestCase):
    def test_min_rank_of_queued_marker(self):
        fx = Fixture()
        self.addCleanup(fx.cleanup)
        self.assertIsNone(rf.queued_gpu_min_rank(fx.flags))
        for rid, rank in (("q-a", 8), ("q-b", None)):
            row = {"id": rid} if rank is None else {"id": rid, "priority_rank": rank}
            rf.atomic_json(os.path.join(rf.dry_dir(fx.flags, rid), "unpublished.json"), row)
            rf.atomic_json(os.path.join(rf.dry_dir(fx.flags, rid), "GPU-SMOKE-QUEUED.json"), {"id": rid})
        self.assertEqual(rf.queued_gpu_min_rank(fx.flags), 8.0)

    def test_allocate_holds_back_worse_ranked_gpu_row_while_rank8_smoke_waits(self):
        src = open(os.path.join(os.path.dirname(_TESTS), "rowflow", "rowflow.py")).read()
        i = src.index("qr = queued_gpu_min_rank(flags)")
        block = src[i:i + 600]
        self.assertIn('c["rank"] > qr', block)       # strictly worse ranks wait; an equal/better ready row is not held
        self.assertIn("any(GPU in o for o in c[\"options\"])", block)


class ResidencyContract(unittest.TestCase):
    def _late_grandchild_case(self):
        """root 100 -> job 200 (tracked on the first sample) -> GPU server 300 started LATER by 200, cleaned env (no
        FILLER_ID). 999 is an unrelated KFD client (ppid 1)."""
        fx = Fixture()
        self.addCleanup(fx.cleanup)
        dd = os.path.join(fx.root, "dd")
        os.makedirs(dd)
        procs = {100: (1, 100, "s100"), 200: (100, 100, "s200"), 999: (1, 999, "s999")}
        listdir = lambda d: [str(k) for k in procs] if d == "/proc" else os.listdir(d)
        with mock.patch.object(rf.os, "listdir", listdir), mock.patch.object(rf, "_proc_stat", procs.get), \
                mock.patch.object(rf, "pid_filler_id", return_value=None):
            tracked = rf.harness_tree(100, {})
            self.assertEqual(set(tracked), {100, 200})
            procs[300] = (200, 100, "s300")             # the job starts its GPU server after 200 was already tracked
            kfd = {}
            occ = {"pids": {300: 2 << 30, 999: 4 << 30}}
            with mock.patch.object(rf, "gpu_occupancy", return_value=occ):
                rf.sample_gpu_residency(100, tracked, kfd, rid="row-x")
        self.assertIn(300, tracked)
        self.assertNotIn(999, tracked)
        self.assertEqual(set(kfd), {300})
        return kfd

    def test_late_grandchild_is_attributed_and_unrelated_pid_refused(self):   # legacy (pre-cgroup) path
        self.assertEqual(set(self._late_grandchild_case()), {300})

    def test_reused_pid_is_not_walked_through(self):
        procs = {100: (1, 100, "s100"), 200: (100, 100, "new"), 300: (200, 100, "s300")}
        listdir = lambda d: [str(k) for k in procs]
        with mock.patch.object(rf.os, "listdir", listdir), mock.patch.object(rf, "_proc_stat", procs.get):
            tracked = rf.harness_tree(100, {100: "s100", 200: "old"})
        self.assertNotIn(300, tracked)


class SmokeRuns(unittest.TestCase):
    """End-to-end dryrun_run with a faked MI210 (GPU residency forced on a CPU-lane row)."""

    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.cleanup)

    def job(self, rid, residency):
        d = self.fx.job(rid)
        res = ('printf \'{"schema":"epyc.rowflow.residency.v1","pid":%s,"vram_bytes":3435973836,"at":"%s"}\' "$$" '
               '"$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$FILLER_RESIDENCY_FILE"\n') if residency else ""
        write(os.path.join(d, "job.sh"), textwrap.dedent(f"""\
            #!/bin/bash
            D={d}
            echo "$$" > "$D/out/job.pid"
            echo "units=${{FILLER_SMOKE_UNITS:-unset}}" > "$D/out/env.txt"
            {res}for i in 1 2 3 4 5 6 7 8 9 10; do [ -e "$FILLER_STOPFILE" ] && exit 75; echo "{{\\"item\\": $i, \\"score\\": 1}}" >> "$D/out/results.jsonl"; sleep 2; done
            exit 0
            """), 0o755)
        return d

    def run_smoke(self, rid, residency, kfd_vram, dev_vram=13_094_912, **spec):
        d = self.job(rid, residency)
        rf.publish(self.fx.spec(rid, d, **spec), self.fx.flags)

        def occ():
            try:
                pid = int(open(os.path.join(d, "out", "job.pid")).read())
            except (OSError, ValueError):
                return {"pids": {}, "vram_used": None}
            return {"pids": {pid: kfd_vram} if kfd_vram is not None else {}, "vram_used": None}
        with mock.patch.object(rf, "gpu_residency_required", return_value=True), \
                mock.patch.object(rf, "vram_used_bytes", return_value=dev_vram), mock.patch.object(rf, "gpu_occupancy", occ):
            v, msg = rf.dryrun_run(self.fx.flags, rid, "0-3", True, smoke_s=60)
        return v, msg, d

    def test_sampled_max_13mb_fails_without_any_evidence(self):          # the yarn-e1-mem-c7 r1 shape, no job record
        v, msg, _ = self.run_smoke("res-none-20261101", False, None)
        self.assertEqual(v, "FAIL")
        self.assertIn("VRAM never showed residency", msg)

    def test_job_written_record_is_no_longer_evidence(self):   # audit #1: residency.json retired, the cgroup leaf replaces it
        v, msg, _ = self.run_smoke("res-job-20261101", True, 1 << 20)
        self.assertEqual(v, "FAIL", msg)
        self.assertIn("VRAM never showed residency", msg)

    def test_negative_control_job_record_for_a_pid_that_is_no_kfd_client_is_rejected(self):
        v, msg, _ = self.run_smoke("res-fake-20261101", True, None)
        self.assertEqual(v, "FAIL", msg)

    def test_own_kfd_tree_sampling_alone_passes(self):
        v, msg, _ = self.run_smoke("res-kfd-20261101", False, 2 << 30)
        self.assertEqual(v, "PASS", msg)

    def test_predicate_row_is_not_shrunk_to_one_unit_but_plain_row_is(self):
        v, msg, d = self.run_smoke("res-pred-20261101", False, 2 << 30, smoke_predicate="test -s out/results.jsonl")
        self.assertEqual(v, "PASS", msg)
        self.assertEqual(open(os.path.join(d, "out", "env.txt")).read().strip(), "units=unset")
        v, msg, d = self.run_smoke("res-plain-20261101", False, 2 << 30)      # negative control: the old env
        self.assertEqual(open(os.path.join(d, "out", "env.txt")).read().strip(), "units=1")


if __name__ == "__main__":
    unittest.main()
