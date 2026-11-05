#!/usr/bin/env python3
"""Keeper-friction review 2026-11-05, refinements 1 (shape from evidence), 2 (gpu-q3) and 5 (supersede withdraws).
Every fixture lives under a temp dir (rf.TMP and flags are redirected); nothing live is touched."""
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402

ALL_TOKENS = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
GPU_THR = {f"t{k}" for k in range(184, 192)}


class Fx(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp() + "/"
        self.flags = os.path.join(self.root, "compute-flags")
        os.makedirs(os.path.join(self.flags, "ready"))
        os.makedirs(os.path.join(self.flags, "grants"))
        self._tmp, rf.TMP = rf.TMP, self.root

    def tearDown(self):
        rf.TMP = self._tmp

    def launcher(self, rid, cmd="python3 job.py", cls="cpu", extra="", stop=None, pre=""):
        d = os.path.join(self.root, rid)
        os.makedirs(d, exist_ok=True)
        eng = os.path.join(d, "filler_run15.sh")
        open(eng, "w").write("#!/bin/bash\n")
        lp = os.path.join(d, "launch.sh")
        stop = stop or f"{d}/{rid}.STOP"
        open(lp, "w").write(f"#!/bin/bash\n{pre}exec bash {eng} --id {rid} --class {cls} {extra} --min-window 300 "
                            f"--stop {stop} --complete-cmd true --workdir {d} --cmd \"{cmd}\"\n")
        return lp

    def spec(self, rid, lp, **kw):
        s = {"id": rid, "owner": "t", "launcher": lp, "lane": "cpu", "result_path": os.path.join(self.root, rid, "r.jsonl"),
             "decision_rule": "x", "estimate_s": 600, "handoff_task": "handoffs/active/x.md:T1"}
        s.update(kw)
        return s


class ShapeEvidence(Fx):
    def test_parse_launcher_reads_thread_knobs(self):
        for cmd, n in (("llama-bench -t 24", 24), ("gitnexus analyze --workers 1", 1), ("OMP_NUM_THREADS=1 python3 p.py", 1),
                       ("taskset -c 72-79 make", 8), ("llama-server --threads=48", 48)):
            o = rf.parse_launcher(self.launcher("t" + str(n) + cmd[:3].strip(), cmd=cmd))
            self.assertEqual(o["threads"], n, cmd)
        o = rf.parse_launcher(self.launcher("tvar", cmd="bench -t $NT", pre="NT=12\n"))
        self.assertEqual(o["threads"], 12)

    def test_workers1_host_refused(self):
        lp = self.launcher("gx", cmd="gitnexus analyze --workers 1", extra="--claim-cpus 0-95")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("gx", lp, regions="0-95", shape="host"), self.flags)
        self.assertIn("right-sized: quarter", str(e.exception))
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, "gx")))

    def test_omp1_quiet_host_refused(self):
        lp = self.launcher("xg", cmd="OMP_NUM_THREADS=1 python3 prof.py", extra="--gpu-quiet exclusive --claim-cpus 0-95")
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("xg", lp, regions="0-95", shape="quiet-host"), self.flags)

    def test_quiet_host_with_baseline_ref_or_override_admitted(self):
        lp = self.launcher("qa", cmd="bench -t 8", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95")
        row = rf.publish(self.spec("qa", lp, lane="gpu", regions="mi210_0,0-95", baseline_ref="artifacts/x/baseline.json"), self.flags)
        self.assertEqual(row["shape"], "quiet-host")
        lp = self.launcher("qb", cmd="bench -t 8", extra="--claim-cpus 0-95")
        row = rf.publish(self.spec("qb", lp, regions="0-95", shape_override="operator: op 2026-11-05: full-host scan"), self.flags)
        self.assertEqual(row["shape"], "host")
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("qb", lp, regions="0-95", shape_override="because"), self.flags)

    def test_production_serving_48_threads_keeps_whole_host(self):
        lp = self.launcher("npd", cmd="llama-server -t 48", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95")
        row = rf.publish(self.spec("npd", lp, lane="gpu", regions="mi210_0,0-95"), self.flags)
        self.assertEqual(row["shape"], "quiet-host")
        self.assertEqual(row["busy_fraction"], 0.5)

    def test_declared_threads_sets_busy_fraction(self):
        lp = self.launcher("b24", cmd="bench -t 24", extra="--claim-cpus 0-47")
        row = rf.publish(self.spec("b24", lp, regions="0-47"), self.flags)
        self.assertEqual(row["busy_fraction"], 0.5)
        lp = self.launcher("b1", cmd="gitnexus analyze --workers 1")
        row = rf.publish(self.spec("b1", lp, regions="any-cpu-quarter"), self.flags)
        self.assertAlmostEqual(rf.row_busy(row), round(1 / 24, 3))
        lp = self.launcher("bx", cmd="python3 job.py")
        self.assertNotIn("busy_fraction", rf.publish(self.spec("bx", lp, regions="any-cpu-quarter"), self.flags))

    def test_measured_busy_and_flag(self):
        samples = [(t, 0.05 * t) for t in range(0, 120, 5)]
        th, bf = rf.measured_busy(samples, 24)
        self.assertAlmostEqual(th, 0.05, places=3)
        self.assertLess(bf, 0.01)
        self.assertIn("OVER-DECLARED", rf.busy_flag(1.0, bf))
        self.assertIsNone(rf.busy_flag(0.9, 0.8))

    def test_unresolvable_stop_file_refused(self):
        lp = self.launcher("sf", stop="$X/sf.STOP")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("sf", lp, regions="any-cpu-quarter"), self.flags)
        self.assertIn("stop_file", str(e.exception))
        lp = self.launcher("sd", stop="$D/sd.STOP", pre='D="$(cd "$(dirname "$0")" && pwd)"\n')
        row = rf.publish(self.spec("sd", lp, regions="any-cpu-quarter"), self.flags)
        self.assertEqual(row["stop_file"], os.path.join(self.root, "sd", "sd.STOP"))


class GpuQ3(Fx):
    def npd_like(self, rid="g3"):
        lp = self.launcher(rid, cmd="bench -t 8", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95")
        return rf.publish(self.spec(rid, lp, lane="gpu", regions="mi210_0,0-95"), self.flags)

    def test_gpu_timing_without_evidence_maps_to_gpu_q3(self):
        # coexist2 2026-11-05: a wide-claim timing row maps to gpu-q3 but its region-lock claim would fold onto
        # q3 cores 72-87 (GLOBAL.q3 exclusive): refused at publish; the explicit gpu-q3 form below is admitted
        with self.assertRaises(rf.Refused) as e:
            self.npd_like()
        self.assertIn("72-87 stay lockable", str(e.exception))
        lp = self.launcher("g3", cmd="bench -t 8", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 88-95")
        row = rf.publish(self.spec("g3", lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3"), self.flags)
        self.assertEqual(row["shape"], "gpu-q3")
        opts, bench = rf.row_shape(row)
        self.assertEqual(len(opts), 1)
        self.assertEqual(rf.expand(opts[0]), rf.expand({"gpu-quiet", "q3"}) | GPU_THR)
        self.assertTrue(bench)

    def test_q0_q2_free_under_gpu_q3(self):
        held = rf.expand(rf.GPU_Q3_TOKENS)
        free = ALL_TOKENS - held
        c = {"id": "q", "kind": "grant", "lane": "cpu", "rank": 50, "lane_count": 0, "gib": 4, "bench": False,
             "options": [frozenset({q}) for q in rf.QUARTERS], "shape": "quarter", "since": time.time(), "window_s": 600}
        out, _, _ = rf.plan(free, [c], 1000, gpu_grant_open=True, quiet_held=held)
        self.assertIn(next(iter(out[0][1])), ("q0", "q1", "q2"))

    def test_coexist_backfills_q3_cores_never_gpu_threads(self):
        held = rf.expand(rf.GPU_Q3_TOKENS)
        free = ALL_TOKENS - held
        cx = {"id": "gx", "kind": "grant", "lane": "cpu", "rank": 50, "lane_count": 0, "gib": 4, "bench": False,
              "options": [frozenset(rf.cpu_tokens("72-73"))], "shape": "quarter", "coexist": True, "busy_fraction": 0.05,
              "since": time.time(), "window_s": 600}
        out, _, _ = rf.plan(free, [cx], 1000, gpu_grant_open=True, quiet_held=held)
        self.assertEqual([c["id"] for c, _ in out], ["gx"])
        bad = dict(cx, id="gy", options=[frozenset(rf.cpu_tokens("88-89"))])
        out, _, _ = rf.plan(free, [bad], 1000, gpu_grant_open=True, quiet_held=held)
        self.assertEqual(out, [])

    def test_timing_never_backfills_q3(self):
        held = rf.expand(rf.GPU_Q3_TOKENS)
        free = ALL_TOKENS - held
        t = {"id": "tb", "kind": "grant", "lane": "cpu", "rank": 50, "lane_count": 0, "gib": 4, "bench": True,
             "options": [frozenset(rf.cpu_tokens("72-79"))], "shape": "quarter", "since": time.time(), "window_s": 600}
        out, _, _ = rf.plan(free, [t], 1000, gpu_grant_open=True, quiet_held=held)
        self.assertEqual(out, [])


class Supersede(Fx):
    def pub(self, rid, **kw):
        return rf.publish(self.spec(rid, self.launcher(rid), regions="any-cpu-quarter", **kw), self.flags)

    def test_publish_r2_withdraws_r1_ready_manifest(self):
        self.pub("row-r1")
        r2 = self.pub("row-r2", supersedes="row-r1", fix_ref="abc123")
        self.assertEqual(rf.supersede(self.flags, r2), {"row-r1": "WITHDRAWN"})
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, "row-r1")))
        self.assertTrue(os.path.exists(os.path.join(rf.withdrawn_dir(self.flags), "row-r1.json")))
        self.assertIn("reason=superseded-by:row-r2", rf.head1(os.path.join(self.flags, "grants", "row-r1.ended")))
        self.assertNotIn("row-r1", rf.rows(self.flags))
        self.assertTrue(os.path.exists(os.path.join(self.root, "row-r1", "row-r1.STOP")))

    def test_running_predecessor_not_killed_but_pending(self):
        self.pub("run-r1")
        g = os.path.join(self.flags, "grants", "run-r1.grant")
        open(g, "w").write("regions=0-23 holds=q0\n")
        r2 = self.pub("run-r2", supersedes=["run-r1"])
        self.assertEqual(rf.supersede(self.flags, r2, log=lambda *_: None), {"run-r1": "PENDING"})
        self.assertTrue(os.path.exists(rf.ready_path(self.flags, "run-r1")))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "grants", "run-r1.ended")))
        os.remove(g)
        open(os.path.join(self.flags, "grants", "run-r1.ended"), "w").write("rc=0\n")
        rf.finish_withdrawals(self.flags, log=lambda *_: None)
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, "run-r1")))
        self.assertEqual(rf.head1(os.path.join(self.flags, "grants", "run-r1.ended")), "rc=0")

    def test_fix_ref_resets_lineage_fails(self):
        self.pub("lin-r1")
        for i in range(3):
            rf.atomic_json(os.path.join(rf.dry_dir(self.flags, "lin-r1"), f"FAIL-{i}.json"), {"reason": "x"})
        self.pub("lin-r2", supersedes="lin-r1")
        allrows = rf.rows(self.flags)
        self.assertEqual(rf.lineage_fails(self.flags, "lin-r2", allrows)[1], 3)
        self.pub("lin-r3", supersedes="lin-r2", fix_ref="deadbeef")
        allrows = rf.rows(self.flags)
        self.assertEqual(rf.lineage_fails(self.flags, "lin-r3", allrows)[1], 0)
        self.assertNotEqual(rf.status(self.flags, "lin-r3", allrows)["state"], "parked")

    def test_withdraw_verb(self):
        self.pub("wd")
        self.assertEqual(rf.main(["--flags", self.flags, "withdraw", "wd", "--reason", "owner dropped it"]), 0)
        self.assertIn("reason=owner_dropped_it", rf.head1(os.path.join(self.flags, "grants", "wd.ended")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "wd", "wd.STOP")))
        self.assertEqual(rf.main(["--flags", self.flags, "withdraw", "nope", "--reason", "x"]), 2)


if __name__ == "__main__":
    unittest.main()
