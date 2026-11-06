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
        # keeper class fix 2026-11-05: refused by the whole-host evidence gate, naming the threads it found
        self.assertIn("needs whole-host evidence", str(e.exception))
        self.assertIn("found 1", str(e.exception))
        self.assertFalse(os.path.exists(rf.ready_path(self.flags, "gx")))

    def test_omp1_quiet_host_refused(self):
        lp = self.launcher("xg", cmd="OMP_NUM_THREADS=1 python3 prof.py", extra="--gpu-quiet exclusive --claim-cpus 0-95")
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("xg", lp, regions="0-95", shape="quiet-host"), self.flags)

    def test_quiet_host_with_baseline_ref_or_override_admitted(self):
        lp = self.launcher("qa", cmd="bench -t 8", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95 --role bench")
        row = rf.publish(self.spec("qa", lp, lane="gpu", regions="mi210_0,0-95", baseline_ref="artifacts/x/baseline.json"), self.flags)
        self.assertEqual(row["shape"], "quiet-host")
        lp = self.launcher("qb", cmd="bench -t 8", extra="--claim-cpus 0-95")
        row = rf.publish(self.spec("qb", lp, regions="0-95", shape_override="operator: op 2026-11-05: full-host scan"), self.flags)
        self.assertEqual(row["shape"], "host")
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("qb", lp, regions="0-95", shape_override="because"), self.flags)

    def test_production_serving_48_threads_keeps_whole_host(self):
        lp = self.launcher("npd", cmd="llama-server -t 48", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95 --role bench")
        row = rf.publish(self.spec("npd", lp, lane="gpu", regions="mi210_0,0-95"), self.flags)
        self.assertEqual(row["shape"], "quiet-host")
        self.assertEqual(row["busy_fraction"], 0.5)

    def test_declared_threads_sets_busy_fraction(self):
        lp = self.launcher("b24", cmd="bench -t 24", extra="--claim-cpus 0-47")
        # keeper class fix 2026-11-05: 0-47 books 24 cores more than -t 24 needs -> refused unless shape_override
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("b24", lp, regions="0-47"), self.flags)
        row = rf.publish(self.spec("b24", lp, regions="0-47", shape_override="operator: op 2026-11-05: 2-quarter A/B"), self.flags)
        self.assertEqual(row["busy_fraction"], 0.5)
        lp = self.launcher("b1", cmd="gitnexus analyze --workers 1")
        row = rf.publish(self.spec("b1", lp, regions="any-cpu-quarter"), self.flags)
        self.assertAlmostEqual(rf.row_busy(row), round(1 / 24, 3))
        lp = self.launcher("bx", cmd="python3 job.py")
        self.assertNotIn("busy_fraction", rf.publish(self.spec("bx", lp, regions="any-cpu-quarter"), self.flags))

    def test_preflight_only_smoke_never_shrinks_contract(self):
        """keeper classfix 2026-11-05 (yarn v38): a PASS with units 0 / measured_threads 0.099 is no thread evidence."""
        flags = self.flags
        os.makedirs(os.path.join(flags, "dryrun", "pf"), exist_ok=True)
        json.dump({"measured_threads": 0.099, "units": 0}, open(rf.pass_path(flags, "pf"), "w"))
        self.assertIsNone(rf.row_threads({"id": "pf"}, flags))
        self.assertEqual(rf.row_threads({"id": "pf", "declared_threads": 24}, flags), 24)
        json.dump({"measured_threads": 3.6, "units": 2}, open(rf.pass_path(flags, "pf"), "w"))
        self.assertIsNone(rf.row_threads({"id": "pf"}, flags))   # a smoke's footprint is never width evidence
        self.assertEqual(rf.row_threads({"id": "pf", "declared_threads": 24}, flags), 24)
        self.assertIsNone(rf.row_threads({"id": "x", "measured_threads": 0.4}, flags))

    def test_width_justification_admits_multiquarter_cpu(self):
        """operator 2026-11-06: a justified multi-quarter CPU width needs no shape_override; short/absent still refused."""
        lp = self.launcher("wj", cmd="python3 job.py")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("wj", lp, regions="any-cpu-quarter", shape="multi-quarter(2)"), self.flags)
        self.assertIn("width_justification", str(e.exception))
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("wj", lp, regions="any-cpu-quarter", shape="multi-quarter(2)", width_justification="faster"), self.flags)
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("wj", lp, regions="any-cpu-quarter", shape="multi-quarter(2)", width_justification="   "), self.flags)
        why = "width-agnostic prefill; throughput scales with threads"
        row = rf.publish(self.spec("wj", lp, regions="any-cpu-quarter", shape="multi-quarter(2)", width_justification=why), self.flags)
        self.assertEqual(row["width_justification"], why)
        self.assertEqual(row["shape"], "multi-quarter(2)")   # the justified width is what the contract books

    def test_width_justification_never_admits_gpu_or_whole_host(self):
        why = "width-agnostic prefill; throughput scales with threads"
        lp = self.launcher("wjh", cmd="bench -t 8", extra="--claim-cpus 0-95")
        with self.assertRaises(rf.Refused):
            rf.publish(self.spec("wjh", lp, regions="0-95", shape="host", width_justification=why), self.flags)

    def test_declared_quarter_never_shrunk_by_smoke(self):
        """iqk-q8-prefill-ab/-step0 2026-11-05: declared quarter, 4-core smoke measured ~2 threads, granted 4 cores."""
        os.makedirs(os.path.join(self.flags, "dryrun", "iq"), exist_ok=True)
        json.dump({"measured_threads": 2.2, "units": 1}, open(rf.pass_path(self.flags, "iq"), "w"))
        lp = self.launcher("iq", cmd="python3 job.py")
        row = rf.publish(self.spec("iq", lp, regions="any-cpu-quarter", shape="quarter"), self.flags)
        self.assertEqual(row["shape"], "quarter")
        c = rf.contract_of(row, None, self.flags)
        self.assertEqual(c["shape"], "quarter")
        self.assertTrue(all(len(x) == 1 and next(iter(x)) in rf.QUARTERS for x in c["options"]))
        lp = self.launcher("iq1", cmd="OMP_NUM_THREADS=1 python3 job.py")
        row = rf.publish(self.spec("iq1", lp, regions="any-cpu-quarter", shape="quarter"), self.flags)
        self.assertEqual(rf.contract_of(row, None, self.flags)["shape"], "quarter")

    def test_cpu_declared_row_never_holds_gpu_quiet(self):
        """STT5 r5 2026-11-05: --class cpu, device cpu, a HIP path in its job files -> granted gpu-quiet idle."""
        d = os.path.join(self.root, "stt")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "job.py"), "w").write("BIN='/mnt/raid0/llm/whisper.cpp/build-hip/bin/whisper-cli'\n")
        lp = self.launcher("stt", cmd=f"python3 {d}/job.py -t 8", extra="")
        row = rf.publish(self.spec("stt", lp, regions="any-cpu-quarter", device="cpu", shape="quarter",
                                   gpu_fence_override="owner: t 2026-11-05: cpu-only branch"), self.flags)
        c = rf.contract_of(row, None, self.flags)
        self.assertFalse(any(rf.GPU in x for x in c["options"]), c["options"])
        self.assertFalse(rf.gpu_touch(row))

    def test_python_env_and_required_width_are_thread_evidence(self):
        d = os.path.join(self.root, "yj")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "side.py"), "w").write("env={'OMP_NUM_THREADS':'24'}\nif os.environ.get('FILLER_THREADS')!='24':raise ValueError\n")
        open(os.path.join(d, "boot.py"), "w").write("import side\n")
        open(os.path.join(d, "j.sh"), "w").write(f"export OMP_NUM_THREADS=1 X=1\nexec python3 {d}/boot.py\n")
        o = rf.parse_launcher(self.launcher("yj", cmd=f"bash {d}/j.sh"))
        self.assertEqual(o["threads"], 24)
        self.assertIn("FILLER_THREADS 24", o["threads_evidence"])

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
        lp = self.launcher(rid, cmd="bench -t 8", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95 --role bench")
        return rf.publish(self.spec(rid, lp, lane="gpu", regions="mi210_0,0-95"), self.flags)

    def test_gpu_timing_without_evidence_maps_to_gpu_q3(self):
        # coexist2 2026-11-05: a wide-claim timing row maps to gpu-q3 but its region-lock claim would fold onto
        # q3 cores 72-87 (GLOBAL.q3 exclusive): refused at publish; the explicit gpu-q3 form below is admitted
        with self.assertRaises(rf.Refused) as e:
            self.npd_like()
        self.assertRegex(str(e.exception), "gpu-q3 regions must claim only|GPU-lane row locks cpus beyond q3")   # keeper class fix: its claim locks q3 72-87
        lp = self.launcher("g3", cmd="bench -t 8", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 88-95 --role bench")
        row = rf.publish(self.spec("g3", lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3"), self.flags)
        self.assertEqual(row["shape"], "gpu-q3")
        opts, bench = rf.row_shape(row)
        self.assertEqual(len(opts), 1)
        self.assertEqual(rf.expand(opts[0]), rf.expand(rf.GPU_Q3_TOKENS))   # gpu-q3 NARROW: gpu-quiet + 88-95 + 184-191, never 72-87
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
        lent = rf.COEXIST_Q3   # keeper class fix 2026-11-05: quiet_held = the tokens the gpu-q3 grant LENDS (72-87 + siblings)
        out, _, _ = rf.plan(free, [cx], 1000, gpu_grant_open=True, quiet_held=lent)
        self.assertEqual([c["id"] for c, _ in out], ["gx"])
        bad = dict(cx, id="gy", options=[frozenset(rf.cpu_tokens("88-89"))])
        out, _, _ = rf.plan(free, [bad], 1000, gpu_grant_open=True, quiet_held=lent)
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
        # keeper-hotfix 2026-11-05: a RUNNING predecessor finishes - its STOP file is NOT touched (the engine's mid-run
        # STOP poll would kill it within seconds); only queued/armed predecessors are stopped
        self.pub("run-r1")
        g = os.path.join(self.flags, "grants", "run-r1.grant")
        open(g, "w").write("regions=0-23 holds=q0\n")
        r2 = self.pub("run-r2", supersedes=["run-r1"])
        self.assertEqual(rf.supersede(self.flags, r2, log=lambda *_: None), {"run-r1": "PENDING"})
        self.assertFalse(os.path.exists(os.path.join(self.root, "run-r1", "run-r1.STOP")), "running predecessor would be killed")
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



class GpuLaneOverreach(Fx):
    """gpushape 2026-11-05 (D9-ack: defect fix - declared shape bypass, inf34 v15)."""

    def test_declared_shape_gpu_with_whole_host_regions_refused(self):
        lp = self.launcher("v15", cmd="bench -t 8", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95 --role bench")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("v15", lp, lane="gpu", regions="mi210_0,0-95", shape="gpu"), self.flags)
        self.assertRegex(str(e.exception), "gpu-q3 regions must claim only|GPU-lane row locks cpus beyond q3")   # keeper class fix: contract gpu-q3, claim 0-95

    def test_declared_gpu_q3_shape_never_bypasses(self):
        lp = self.launcher("wq3", cmd="bench -t 8", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 0-23")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("wq3", lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3"), self.flags)
        self.assertIn("0-23", str(e.exception))

    def test_gpu_q3_form_admitted(self):
        lp = self.launcher("ok", cmd="bench -t 8", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 88-95,184-191 --role bench")
        row = rf.publish(self.spec("ok", lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3"), self.flags)
        self.assertEqual(row["shape"], "gpu-q3")

    def test_whole_host_evidence_admits(self):
        lp = self.launcher("t48", cmd="llama-server -t 48", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95 --role bench")
        # keeper class fix 2026-11-05: the declared shape is advisory; 48-thread evidence makes the contract quiet-host
        self.assertEqual(rf.publish(self.spec("t48", lp, lane="gpu", regions="mi210_0,0-95", shape="gpu"), self.flags)["shape"], "quiet-host")
        lp = self.launcher("br", cmd="bench -t 8", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95 --role bench")
        rf.publish(self.spec("br", lp, lane="gpu", regions="mi210_0,0-95", baseline_ref="artifacts/x/b.json"), self.flags)
        lp = self.launcher("so", cmd="bench -t 8", cls="cpu+gpu", extra="--gpu-quiet exclusive --claim-cpus 0-95 --role bench")
        rf.publish(self.spec("so", lp, lane="gpu", regions="mi210_0,0-95", shape="gpu",
                             shape_override="operator: op 2026-11-05: whole-host serving A/B"), self.flags)

    def test_cpu_row_untouched(self):
        # keeper class fix 2026-11-05: gpu_lane_overreach removed; the contract clips GPU rows, never CPU rows
        self.assertEqual(rf.contract_of({"lane": "cpu", "regions": "0-95"}, {"class": "cpu", "claim_cpus": "0-95"})["options"],
                         [frozenset(rf.QUARTERS)])
        hthr = frozenset({rf.GPU} | GPU_THR)
        self.assertEqual(rf.contract_of({"lane": "gpu", "regions": "mi210_0,184-191"}, {"class": "gpu"})["options"], [hthr])
        self.assertEqual(rf.contract_of({"lane": "gpu", "regions": "mi210_0,q1"}, {})["options"], [hthr])   # q1 clipped


class GpuQ3OnlyForTiming(Fx):
    """gpushape q3-parallel (operator 2026-11-05): non-timing GPU rows leave q3 to CPU rows; timing rows keep it quiet."""

    def test_non_timing_gpu_row_booking_q3_refused(self):
        lp = self.launcher("cq", cmd="python3 check.py", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 88-95,184-191")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("cq", lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3"), self.flags)
        self.assertIn("non-timing GPU row books q3", str(e.exception))
        lp = self.launcher("co", cmd="python3 check.py", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 88-95,184-191")
        rf.publish(self.spec("co", lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3",
                             shape_override="operator: op 2026-11-05: keep q3 quiet"), self.flags)

    def test_timing_declarations_admit_gpu_q3(self):
        for rid, kw in (("ta", {"timing": "profile"}), ("tb", {"admission_class": "block-timing-quiet"})):
            lp = self.launcher(rid, cmd="python3 p.py", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 88-95,184-191")
            row = rf.publish(self.spec(rid, lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3", **kw), self.flags)
            self.assertEqual(row["shape"], "gpu-q3")

    def test_non_timing_grant_leaves_q3_grantable(self):
        lp = self.launcher("ng", cmd="python3 check.py", cls="gpu", extra="--no-fold-siblings --gpu-quiet exclusive")
        row = rf.publish(self.spec("ng", lp, lane="gpu", regions="mi210_0,184-191"), self.flags)
        self.assertEqual(row["shape"], "gpu")
        opts, _ = rf.row_shape(row)
        held = rf.expand(opts[0])
        q3_cores = {f"c{n}" for n in range(72, 96)}
        self.assertFalse(held & q3_cores)
        self.assertNotIn("q3", held)

    def test_timing_grant_keeps_q3_quiet(self):
        lp = self.launcher("tg", cmd="bench -t 8", cls="gpu", extra="--gpu-quiet exclusive --claim-cpus 88-95,184-191 --role bench")
        row = rf.publish(self.spec("tg", lp, lane="gpu", regions="mi210_0,88-95,184-191", shape="gpu-q3"), self.flags)
        opts, _ = rf.row_shape(row)
        # gpu-q3 NARROW (operator 2026-11-05): holds the host threads' siblings 88-95, never q3 cores 72-87
        self.assertTrue({f"c{n}" for n in range(88, 96)} <= rf.expand(opts[0]))
        self.assertFalse({f"c{n}" for n in range(72, 88)} & rf.expand(opts[0]))
        self.assertNotIn("q3", rf.expand(opts[0]))


class LowBusySkipMessage(unittest.TestCase):
    def test_names_its_own_busy_regions(self):
        h = {"options": [frozenset({"c72", "c73"})], "busy_fraction": 0.05, "gib": 1}
        free = set(rf.CORES[:24])
        why = rf.own_block(h, free, 10_000, False, set())
        self.assertIn("busy_fraction 0.05", why)
        self.assertIn("c72", why)


if __name__ == "__main__":
    unittest.main()
