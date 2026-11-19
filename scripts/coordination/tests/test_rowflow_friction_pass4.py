"""Keeper friction review Pass 4 (operator 2026-11-06, emergency deploy into the frozen keeper) - three fixes, each with
its unit tests and a NEGATIVE CONTROL that flips the fix's module flag off and shows the OLD behaviour fails the new test.

1. Refusal terminal once: a --precond-cmd refusal (grant_ok_launcher rc=12) parks the row at the FIRST refusal; one FAIL
   record, one alert; retried only after a launcher/spec sha change or `rowflow.py unpark` (kpf50/kpf41: 171 refusals of
   one unchanged precond, one per 120 s tick, 171 alerts; 478 false vs 3 real this window).
2. A completed row is not rc=14: a poller that is dead AFTER grants/<id>.complete (or an .ended rc=0 reason=complete
   receipt) is COMPLETION, never a "launcher pid dead" FAIL (11 of 11 rc=14 FAILs since 11-04 had .complete).
3. GPU idleness by GPU signals: a grant holding the GPU token is idle only when its own KFD client set is empty AND the
   device reads < IDLE_PCT for GPU_IDLE_SAMPLES consecutive samples; its CPU regions are never judged by CPU %; the
   dry run's OVER-DECLARED busy_fraction flag is never raised for a GPU-token row (43 of 72 flags were GPU rows).
Temp flags trees only; notify's bus is never live here; no process is started or killed."""
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402
from test_rowflow_arming_park import GPU_OPT, QUIET_OPT, Fixture  # noqa: E402

PRECOND_LINE = ("refuse rc=12: not ready: precond-cmd failed: printf '%s %s\\n' c66f05148e35355bd04292958d9a123b0a80f1db "
                "'/mnt/raid0/llm/tmp/heterogeneous-slot-fabric/kpf50/input.json' | sha256sum -c --status")
DEAD_LINE = "refuse rc=14: launcher pid 1917013 of {rid} is dead (no /proc/1917013 or zombie)"
GPU_IDLE = {"q0": 50.0, "q1": 3.0, "q2": 0.0, "q3": 0.0, "gpu": {"busy": 0, "vram_pct": 0.0, "vram_gib": 0.0, "card": "card2"}}
GPU_BUSY = dict(GPU_IDLE, gpu={"busy": 80, "vram_pct": 60.0, "vram_gib": 38.0, "card": "card2"})
TICK = 120


def alerts(flags, kind=None):
    p = os.path.join(flags, "rowflow-alerts.jsonl")
    out = [json.loads(x) for x in open(p)] if os.path.exists(p) else []
    return [a for a in out if kind is None or a.get("kind") == kind]


class Pass4(Fixture):
    def setUp(self):
        super().setUp()
        os.environ.pop("ROWFLOW_BUS_ROOT", None)
        self.flags_saved = {k: getattr(rf, k) for k in ("COMPLETE_BEFORE_RC14", "armed_engine_ok")}
        rf.armed_engine_ok = lambda pid, rid, proc="/proc": True   # the fixture's ARMED pid IS the row's engine (live incident shape)

    def tearDown(self):
        for k, v in self.flags_saved.items():
            setattr(rf, k, v)
        super().tearDown()

    def fails(self, rid):
        return rf.fail_paths(self.flags, rid)

    def refuse_with(self, line_of):
        rf.admit = lambda flags, rid, d, pid, regions, window_s: (False, line_of(rid))


# ---------------------------------------------------------------------------------------------- fix 1
class PrecondRefusalTerminalOnce(Pass4):
    RID = "kpf50-child-evidence-main-impact-20261104-r2"

    def test_first_refusal_parks_one_fail_one_alert_no_retry(self):
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_with(lambda rid: PRECOND_LINE)
        for _ in range(5):   # five keeper ticks = 10 minutes of the live loop
            self.tick()
        self.assertEqual(len(self.fails(self.RID)), 1, "exactly one FAIL record per refusal episode, not one per tick")
        self.assertEqual(len(alerts(self.flags, "smoke-fail")), 1, "exactly one alert per refusal episode")
        st = rf.status(self.flags, self.RID)
        self.assertEqual(st["state"], "parked")
        self.assertTrue(st.get("precond_parked"))
        self.assertIn("unpark", st["reason"])
        self.assertEqual(len([l for l in self.lines if l.startswith(f"PARK {self.RID}:")]), 1)
        self.assertEqual([l for l in self.lines if l.startswith(f"SKIP {self.RID}:")], [], "a parked row is never re-admitted")
        rec = rf.load_json(self.fails(self.RID)[0])
        self.assertEqual(rec["kind"], "launch")
        self.assertIn("PARKED now", rec["fix_task"])

    def test_spec_change_retries_once_more(self):
        d = self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_with(lambda rid: PRECOND_LINE)
        self.tick(); self.tick()
        self.assertEqual(len(self.fails(self.RID)), 1)
        d["notes"] = "precondition input regenerated"       # a republish: the manifest sha changes
        rf.atomic_json(rf.ready_path(self.flags, self.RID), d)
        self.assertEqual(rf.status(self.flags, self.RID)["state"], "armed", "the parked FAIL is keyed to the OLD spec sha")
        self.tick(); self.tick()
        self.assertEqual(len(self.fails(self.RID)), 2, "one new refusal episode after the spec edit, then parked again")
        self.assertEqual(rf.status(self.flags, self.RID)["state"], "parked")

    def test_launcher_change_lifts_the_park(self):
        d = self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_with(lambda rid: PRECOND_LINE)
        self.tick()
        self.assertEqual(rf.status(self.flags, self.RID)["state"], "parked")
        with open(d["launcher"]["path"], "a") as f:
            f.write("# precond fixed\n")
        self.assertNotEqual(rf.status(self.flags, self.RID)["state"], "parked")   # stale: a new dry run, not a parked row

    def test_unpark_makes_the_row_grantable_again(self):
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_with(lambda rid: PRECOND_LINE)
        self.tick()
        self.assertEqual(rf.status(self.flags, self.RID)["state"], "parked")
        rec = rf.unpark(self.flags, self.RID, by="operator", note="input regenerated by hand")
        self.assertTrue(os.path.exists(rf.unpark_path(self.flags, self.RID)))
        self.assertEqual(rf.status(self.flags, self.RID)["state"], "armed")
        rf.admit = lambda flags, rid, d, pid, regions, window_s: (True, "precond=ok")
        self.tick()
        self.assertTrue([l for l in self.lines if l.startswith(f"GRANT {self.RID} ")], "after unpark the next tick grants it")
        self.assertEqual(rec["by"], "operator")

    def test_unpark_cli(self):
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_with(lambda rid: PRECOND_LINE)
        self.tick()
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = rf.main(["--flags", self.flags, "unpark", self.RID, "--by", "op"])
        self.assertEqual(rc, 0)
        self.assertIn("UNPARKED", buf.getvalue())
        self.assertNotEqual(rf.status(self.flags, self.RID)["state"], "parked")

    def test_other_refusals_keep_the_max_fails_rule(self):
        """A non-precond refusal (a launcher window too short, rc=12 of another kind) is still counted to MAX_FAILS."""
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_with(lambda rid: "refuse rc=12: window 600 s < min-window 900 s + 300 s")
        rf.armed_engine_ok = self.flags_saved["armed_engine_ok"]
        for _ in range(5):
            self.tick()
        self.assertEqual(len(self.fails(self.RID)), rf.MAX_FAILS)
        self.assertEqual(rf.status(self.flags, self.RID)["state"], "parked")
        self.assertFalse(rf.status(self.flags, self.RID).get("precond_parked"))


# ---------------------------------------------------------------------------------------------- fix 2
class CompletedRowIsNotRc14(Pass4):
    RID = "v11-122-llg-build-cpu-20261105"

    def refuse_dead_after(self, receipt):
        """The live race: status() saw the row `armed`; between that and admit the smoke/poller finished the whole job
        and wrote its receipt; admit then finds the pid dead."""
        def adm(flags, rid, d, pid, regions, window_s):
            receipt(rid)
            return False, DEAD_LINE.format(rid=rid)
        rf.admit = adm

    def complete_marker(self, rid):
        open(os.path.join(self.flags, "grants", rid + ".complete"), "w").write("complete\n")

    def ended_receipt(self, rid, line="rc=0 time=2026-11-05T12:43:00Z reason=complete\n"):
        open(os.path.join(self.flags, "grants", rid + ".ended"), "w").write(line)

    def test_dead_poller_after_complete_marker_is_completion(self):
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_dead_after(self.complete_marker)
        self.tick()
        self.assertEqual(self.fails(self.RID), [], "no rc=14 FAIL for a completed row")
        self.assertEqual(alerts(self.flags, "smoke-fail"), [])
        self.assertTrue([l for l in self.lines if l.startswith(f"COMPLETE {self.RID}:") and ".complete" in l])
        self.assertEqual(rf.status(self.flags, self.RID)["state"], "done")

    def test_dead_poller_after_ended_rc0_complete_is_completion(self):
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_dead_after(self.ended_receipt)
        self.tick()
        self.assertEqual(self.fails(self.RID), [])
        self.assertTrue([l for l in self.lines if l.startswith(f"COMPLETE {self.RID}:")])

    def test_dead_poller_with_a_failed_receipt_or_none_still_fails(self):
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_dead_after(lambda rid: self.ended_receipt(rid, "rc=1 time=2026-11-05T12:43:00Z reason=exit\n"))
        self.tick()
        self.assertEqual(len(self.fails(self.RID)), 1, "rc=1 is not a success receipt")
        other = "akx-c6-n4-generic-vs-candidate-20261104"
        self.row(other, 10, QUIET_OPT, "quarter")
        self.refuse_dead_after(lambda rid: None)
        self.tick()
        self.assertEqual(len(self.fails(other)), 1, "a genuinely dead poller (no receipt) is still a launch FAIL")

    def test_receipt_present_before_arming_skips_arming(self):
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        rf.admit = lambda *a, **k: self.fail("admit must not run for a completed row")
        real_arm = rf.arm_one
        rf.arm_one = lambda *a, **k: self.fail("arm_one must not run for a completed row")
        try:
            # the receipt lands after this tick's status() (which still says grantable) - simulate by hooking contract_of
            saved = self.saved["contract_of"]

            def hook(d, o=None, flags=None):
                if d and d.get("id") == self.RID:
                    self.complete_marker(self.RID)
                return saved(d, o, flags)
            rf.contract_of = hook
            rf.allocate(self.flags, log=self.lines.append)
        finally:
            rf.arm_one = real_arm
        self.assertEqual(self.fails(self.RID), [])
        self.assertTrue([l for l in self.lines if l.startswith(f"COMPLETE {self.RID}:")])

    def test_terminal_success_helper(self):
        self.assertIsNone(rf.terminal_success(self.flags, "nope"))
        self.ended_receipt("x", "rc=0 time=2026-11-05T12:43:00Z reason=complete\n")
        self.assertIn("reason=complete", rf.terminal_success(self.flags, "x"))
        self.ended_receipt("y", "rc=10 time=2026-11-05T12:43:00Z reason=complete\n")
        self.assertIsNone(rf.terminal_success(self.flags, "y"), "rc=10 is not rc=0")
        self.ended_receipt("z", "rc=0 time=2026-11-05T12:43:00Z reason=stopped\n")
        self.assertIsNone(rf.terminal_success(self.flags, "z"), "a stop is not a completion")
        self.complete_marker("w")
        self.assertEqual(rf.terminal_success(self.flags, "w"), "grants/w.complete")

    def test_negative_control_old_rule_fails_the_completed_row(self):
        rf.COMPLETE_BEFORE_RC14 = False
        self.row(self.RID, 10, QUIET_OPT, "quarter")
        self.refuse_dead_after(self.complete_marker)
        self.tick()
        self.assertEqual(len(self.fails(self.RID)), 1, "old rule: rc=14 FAIL written for a completed row")
        self.assertIn("rc=14", rf.load_json(self.fails(self.RID)[0])["reason"])
        self.assertEqual(len(alerts(self.flags, "smoke-fail")), 1)


# ---------------------------------------------------------------------------------------------- fix 3
class GpuIdleByDevice(Pass4):
    RID = "ak-asm-t1-harness-20261106"

    def gpu_grant(self, rid, holds="gpu-quiet,q3", age_s=600, armed_pid=None):
        p = os.path.join(self.flags, "grants", rid + ".grant")
        with open(p, "w") as f:
            f.write(f"regions=mi210_0,72-95 start=2026-11-06T02:00Z end=2026-11-06T05:00Z holds={holds}\n")
        t = time.time() - age_s
        os.utime(p, (t, t))
        if armed_pid:
            rf.atomic_json(rf.armed_path(self.flags, rid), {"id": rid, "pid": armed_pid, "regions": "mi210_0,72-95", "at": rf.now_iso()})
        return p

    def run_idle(self, holders, utils, occs):
        out = []
        t0 = time.time()
        for i, (u, occ) in enumerate(zip(utils, occs)):
            out.append(rf.idle_held(self.flags, rf.open_grants(self.flags), holders, u, self.lines.append, set(), now=t0 + i * TICK, occ=occ))
        return out

    def test_own_kfd_client_means_busy_whatever_cpu_and_device_read(self):
        me = os.getpid()
        self.row(self.RID, 10, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,72-95")
        self.gpu_grant(self.RID, armed_pid=me)
        occ = {"pids": {me: 2 << 30}, "vram_used": 2 << 30}
        idle = self.run_idle({"gpu-quiet": self.RID, "q3": self.RID}, [GPU_IDLE] * 5, [occ] * 5)
        self.assertEqual(idle, [[]] * 5, "a grant whose process tree holds a KFD client is never IDLE-HELD")
        self.assertEqual([l for l in self.lines if l.startswith("IDLE-HELD")], [])

    def test_cpu_regions_of_a_gpu_grant_are_never_judged_by_cpu_pct(self):
        self.row(self.RID, 10, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,72-95")
        self.gpu_grant(self.RID, armed_pid=os.getpid())
        occ = {"pids": {}, "vram_used": 0}
        idle = self.run_idle({"gpu-quiet": self.RID, "q3": self.RID}, [GPU_BUSY] * 3, [occ] * 3)   # q3 reads 0 %, device 80 %
        self.assertEqual(idle, [[]] * 3, "q3 at 0 % under a busy GPU grant is the expected reading, not idleness")

    def test_quiet_device_and_no_kfd_is_idle_only_after_two_samples(self):
        self.row(self.RID, 10, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,72-95")
        self.gpu_grant(self.RID, armed_pid=os.getpid())
        occ = {"pids": {4242: 1 << 30}, "vram_used": 1 << 30}   # a FOREIGN client is not this grant's work
        idle = self.run_idle({"gpu-quiet": self.RID, "q3": self.RID}, [GPU_IDLE] * 3, [occ] * 3)
        self.assertEqual([[(r, rid) for r, rid, _ in x] for x in idle], [[], [("gpu-quiet", self.RID)], [("gpu-quiet", self.RID)]])
        st = rf.load_json(rf.gpu_idle_state_path(self.flags))
        self.assertEqual(st[self.RID], 3)
        self.assertTrue([l for l in self.lines if l.startswith(f"IDLE-HELD gpu-quiet {self.RID}:") and "no own KFD client" in l])

    def test_a_busy_sample_resets_the_quiet_count(self):
        me = os.getpid()
        self.row(self.RID, 10, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,72-95")
        self.gpu_grant(self.RID, armed_pid=me)
        quiet, own = {"pids": {}, "vram_used": 0}, {"pids": {me: 1 << 30}, "vram_used": 1 << 30}
        idle = self.run_idle({"gpu-quiet": self.RID}, [GPU_IDLE] * 4, [quiet, own, quiet, quiet])
        self.assertEqual([bool(x) for x in idle], [False, False, False, True])

    def test_status_blocker_follows_the_device_verdict(self):
        self.row(self.RID, 10, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,72-95")
        self.gpu_grant(self.RID, armed_pid=os.getpid())
        st = rf.status(self.flags, self.RID, util=GPU_IDLE)
        self.assertEqual(st["state"], "running")
        self.assertNotIn("blocker", st, "no persisted 2-sample verdict yet: no IDLE-HELD blocker from one CPU/GPU reading")
        self.run_idle({"gpu-quiet": self.RID}, [GPU_IDLE] * 2, [{"pids": {}, "vram_used": 0}] * 2)
        st = rf.status(self.flags, self.RID, util=GPU_IDLE)
        self.assertIn("IDLE-HELD gpu-quiet", st.get("blocker", ""))
        self.assertNotIn("q3", st.get("blocker", ""))

    def test_cpu_grants_keep_the_cpu_rule(self):
        rid = "cpu-q1-row"
        self.row(rid, 10, QUIET_OPT, "quiet-host")
        p = os.path.join(self.flags, "grants", rid + ".grant")
        open(p, "w").write("regions=24-47 start=2026-11-06T02:00Z end=2026-11-06T05:00Z holds=q1\n")
        os.utime(p, (time.time() - 600, time.time() - 600))
        idle = self.run_idle({"q1": rid}, [dict(GPU_BUSY, q1=2.0)], [{"pids": {}, "vram_used": 0}])
        self.assertEqual([(r, x) for r, x, _ in idle[0]], [("q1", rid)], "a CPU grant is still judged by its CPU %, first sample")

    def test_over_declared_flag_suppressed_for_gpu_token_rows(self):
        self.assertIsNotNone(rf.busy_flag(1.0, 0.1))
        self.assertIsNone(rf.busy_flag(1.0, 0.1, gpu=True), "a GPU-token row's low CPU share is by design")
        self.assertIsNone(rf.busy_flag(0.2, 0.1))

    def test_allocate_tick_never_warns_a_working_gpu_harness(self):
        """End to end: the ak-asm-t1-harness shape - GPU grant, device 0 % between kernels, own KFD client present,
        q3 at 0 % - over 6 ticks (12 min) never reads IDLE-HELD and never warns the owner."""
        me = os.getpid()
        self.row(self.RID, 10, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,72-95")
        self.gpu_grant(self.RID, armed_pid=me)
        rf.measure_util = lambda *a, **k: GPU_IDLE
        rf.gpu_occupancy = lambda: {"pids": {me: 2 << 30}, "vram_used": 2 << 30}
        rf.underused = self.saved["underused"]
        saved_time = rf.time.time
        try:
            for i in range(6):
                now = time.time() + i * TICK
                rf.time.time = lambda now=now: now
                rf.allocate(self.flags, log=self.lines.append)
        finally:
            rf.time.time = saved_time
        self.assertEqual([l for l in self.lines if l.startswith("IDLE-HELD")], [])
        self.assertEqual(alerts(self.flags, "idle-held"), [])


if __name__ == "__main__":
    unittest.main()
