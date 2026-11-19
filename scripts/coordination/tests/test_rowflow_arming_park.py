"""ws58 2026-11-03 allocator deadlock: arming failures after a PASS park the row; an unplaceable or arm-failing row holds
nobody back; IDLE-VIOLATION fires when free regions + fitting grantable rows see no grant for 2 ticks.

Incident (2026-11-02T23:58Z .. 2026-11-03T07:10Z): yarn-e1-a2-gpu-20261102-v1 (rank 7, GPU) failed to arm 172 times
(its launcher's seal refused a dependency that a repo sync had changed, so the poller never logged "launcher up pid=").
status() kept it `grantable` because a PASS with the current launcher sha existed; every tick plan() handed it the MI210
first, DRAIN-HELD held every quiet-host row for it, the arm failed, and the whole host idled with every region free."""
import glob
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

PASSED_AT = "2026-11-02T20:50:17Z"
YARN = "yarn-e1-a2-gpu-20261102-v1"
LEGACY_REASON = "poller did not log 'launcher up pid=' within 30 s of arming"
GPU_OPT = [frozenset({rf.GPU, "c88", "c89", "c90", "c91"})]
QUIET_OPT = [frozenset(rf.REGIONS)]
KVU_OPT = [frozenset({rf.GPU, "q3"})]


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = self.tmp.name
        for d in ("ready", "grants", "dryrun"):
            os.makedirs(os.path.join(self.flags, d))
        self.saved = {k: getattr(rf, k) for k in ("rl_status", "arm_one", "admit", "mem_available_gib", "start_gpu_batch",
                                                   "underused", "vram_used_bytes", "row_shape", "measure_util", "route_alert",
                                                   "contract_of", "gpu_occupancy")}
        rf.gpu_occupancy = lambda: {"pids": {}, "vram_used": 0}   # never the live host's sysfs
        rf.measure_util = lambda *a, **k: {"q0": 0.0, "q1": 0.0, "q2": 0.0, "q3": 0.0, "gpu": None}
        rf.route_alert = lambda *a, **k: False
        rf.rl_status = lambda: {r: ("free", "") for r in rf.REGIONS}
        rf.mem_available_gib = lambda: 1000.0
        rf.start_gpu_batch = lambda flags, log: False
        rf.underused = lambda *a, **k: []
        rf.vram_used_bytes = lambda: 0
        rf.row_shape = lambda d: (list(d["_opts"]), False)
        rf.admit = lambda flags, rid, d, pid, regions, window_s: (True, "ok")
        self.broken = {YARN}
        self.armed_calls = []

        def fake_arm(flags, rid, d, regions=None, log=print):
            self.armed_calls.append(rid)
            if rid in self.broken:
                n = rf.record_arm_fail(flags, rid, d, "arm", LEGACY_REASON, log)
                return None, f"fail: no launcher pid within 30 s ({n})"
            rf.atomic_json(rf.armed_path(flags, rid), {"id": rid, "pid": os.getpid(), "regions": d["regions"], "at": rf.now_iso()})
            return os.getpid(), f"ARMED {rid}"
        rf.arm_one = fake_arm
        self.lines = []

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(rf, k, v)
        self.tmp.cleanup()

    def row(self, rid, rank, opts, shape, lane="cpu", regions="0-95", passed=PASSED_AT):
        lp = os.path.join(self.flags, rid + ".launcher.sh")
        with open(lp, "w") as f:
            f.write(f"#!/bin/bash\n# {rid}\n")
        d = {"schema": rf.SCHEMA, "id": rid, "owner": "t", "lane": lane, "priority_rank": rank, "shape": shape,
             "regions": regions, "window_s": 3600, "estimate_s": 1800, "gib": 0, "launcher": {"path": lp},
             "result_path": os.path.join(self.flags, rid + ".json"), "_opts": [sorted(o) for o in opts]}
        rf.atomic_json(rf.ready_path(self.flags, rid), d)
        rf.atomic_json(rf.pass_path(self.flags, rid), {"id": rid, "passed_at": passed, "launcher_sha256": rf.sha256(lp)})
        return d

    def legacy_fails(self, rid, n, start_h=23):
        for i in range(1, n + 1):
            m = 58 + i * 2.5
            at = f"2026-11-0{2 if m < 60 else 3}T{(start_h + int(m // 60)) % 24:02d}:{int(m % 60):02d}:29Z"
            rf.atomic_json(os.path.join(rf.dry_dir(self.flags, rid), f"FAIL-{i}.json"), {"id": rid, "at": at, "reason": LEGACY_REASON})

    def tick(self):
        rf.row_shape = lambda d: ([frozenset(o) for o in d["_opts"]], False)
        real = self.saved["contract_of"]

        def fake_contract(d, o=None, flags=None):   # allocate() builds candidates from contract_of: inject the options
            c = real(d, o, flags)
            if d and "_opts" in d:
                c = dict(c, options=[frozenset(x) for x in d["_opts"]], bench=False)
            return c
        rf.contract_of = fake_contract
        return rf.allocate(self.flags, log=self.lines.append)

    def end(self, rid):
        open(os.path.join(self.flags, "grants", rid + ".ended"), "w").close()
        os.remove(os.path.join(self.flags, "grants", rid + ".grant"))


class ArmingFailuresPark(Fixture):
    def test_status_parks_after_three_consecutive_arm_failures_since_pass(self):
        d = self.row(YARN, 7, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,88-91")
        self.assertEqual(rf.status(self.flags, YARN)["state"], "grantable")
        for k in range(1, rf.MAX_FAILS):
            rf.record_arm_fail(self.flags, YARN, d, "arm", LEGACY_REASON)
            st = rf.status(self.flags, YARN)
            self.assertEqual((st["state"], st["arm_fails"]), ("grantable", k))
        rf.record_arm_fail(self.flags, YARN, d, "launch", "admission refused the armed poller: refuse rc=14")
        st = rf.status(self.flags, YARN)
        self.assertEqual(st["state"], "parked")
        self.assertIn("consecutive arming/launch failures", st["reason"])
        esc = os.path.join(self.flags, "operator-escalations", YARN + ".arming.md")
        self.assertTrue(os.path.isfile(esc))
        self.assertIn("PARKED NEEDS-OWNER", open(esc).read())

    def test_failures_before_the_pass_or_before_a_grant_do_not_count(self):
        d = self.row(YARN, 7, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,88-91", passed="2026-11-03T08:00:00Z")
        self.legacy_fails(YARN, 5)   # 2026-11-02T23:58Z.. : all before this PASS
        self.assertEqual(rf.status(self.flags, YARN)["state"], "grantable")
        rf.atomic_json(rf.pass_path(self.flags, YARN), {"passed_at": PASSED_AT, "launcher_sha256": rf.sha256(d["launcher"]["path"])})
        self.assertEqual(rf.status(self.flags, YARN)["state"], "parked")
        rf.atomic_json(rf.granted_path(self.flags, YARN), {"at": "2026-11-03T09:00:00Z"})   # a later successful grant resets
        self.assertEqual(rf.status(self.flags, YARN)["state"], "grantable")

    def test_dry_run_failures_are_not_arming_failures(self):
        self.row(YARN, 7, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,88-91")
        for i in range(1, 5):
            rf.atomic_json(os.path.join(rf.dry_dir(self.flags, YARN), f"FAIL-{i}.json"),
                           {"at": "2026-11-03T01:00:0%dZ" % i, "reason": "dry run wrote 0 units"})
        self.assertEqual(rf.arm_fails_since_pass(self.flags, YARN), [])
        self.assertEqual(rf.status(self.flags, YARN)["state"], "grantable")


class IncidentReplay(Fixture):
    def setUp(self):
        super().setUp()
        self.yarn = self.row(YARN, 7, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,88-91")
        self.row("sr6-qwen36-width-w1-retry-20261102", 30, QUIET_OPT, "quiet-host")
        self.row("sr7-qwen36-proposer-w1-20261102", 30, QUIET_OPT, "quiet-host")
        self.row("handoff-kvu12-5-quarter-r2-20261102", 50, KVU_OPT, "gpu", lane="gpu", regions="mi210_0,72-95")

    def test_172_legacy_arming_failures_park_yarn_and_the_others_are_granted(self):
        self.legacy_fails(YARN, 172)
        st = rf.status(self.flags, YARN)
        self.assertEqual(st["state"], "parked")
        self.assertEqual(st["arm_fails"], 172)
        out = self.tick()
        self.assertNotIn(YARN, self.armed_calls)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0][1].startswith("sr"), out)   # a quiet-host row takes the idle host
        self.assertFalse([l for l in self.lines if l.startswith("DRAIN-HELD")])

    def test_replay_from_the_first_failure(self):
        # tick 1: yarn is healthy as far as the allocator knows -> it is placed first, its arm fails; 2026-11-03 item 7:
        # the SAME tick re-plans without it and the quiet-host row is promoted and granted (no idle tick)
        out = self.tick()
        self.assertEqual(self.armed_calls[0], YARN)
        self.assertTrue([l for l in self.lines if l.startswith("DRAIN-HELD")])
        self.assertTrue([l for l in self.lines if l.startswith("RE-PLAN same tick: " + YARN)])
        self.assertEqual([r for _, r, _ in out], ["sr6-qwen36-width-w1-retry-20261102"])
        self.assertEqual(rf.status(self.flags, YARN)["state"], "grantable")
        # the quiet row ends; yarn (rank 7) is tried again on the free host until it parks; others are granted meanwhile
        granted = [r for _, r, _ in out]
        for _ in range(8):
            for g in glob.glob(os.path.join(self.flags, "grants", "*.grant")):
                self.end(os.path.basename(g)[:-6])
            granted += [r for _, r, _ in self.tick()]
        self.assertEqual(rf.status(self.flags, YARN)["state"], "parked")
        self.assertEqual(self.armed_calls.count(YARN), rf.MAX_FAILS)
        self.assertEqual(sorted(granted), ["handoff-kvu12-5-quarter-r2-20261102", "sr6-qwen36-width-w1-retry-20261102",
                                           "sr7-qwen36-proposer-w1-20261102"])
        self.assertTrue(os.path.isfile(os.path.join(self.flags, "operator-escalations", YARN + ".arming.md")))
        self.assertTrue([l for l in self.lines if l.startswith(f"PARK {YARN}")])

    def test_launch_refusals_count_too(self):
        self.broken = set()
        rf.admit = lambda flags, rid, d, pid, regions, window_s: (rid != YARN, "refuse rc=14: launcher pid dead")
        for _ in range(8):
            self.assertNotIn(YARN, [r for _, r, _ in self.tick()])
            for g in glob.glob(os.path.join(self.flags, "grants", "*.grant")):
                self.end(os.path.basename(g)[:-6])
            if os.path.exists(rf.armed_path(self.flags, YARN)):
                os.remove(rf.armed_path(self.flags, YARN))   # the refused poller is gone
        self.assertEqual(rf.status(self.flags, YARN)["state"], "parked")
        self.assertEqual([f.get("kind") for f in rf.arm_fails_since_pass(self.flags, YARN)], ["launch"] * rf.MAX_FAILS)


class IdleViolation(Fixture):
    def test_alert_after_two_idle_ticks_once_per_episode(self):
        c = {"id": "quiet", "options": QUIET_OPT, "gib": 0, "ports": []}
        free = set(rf.REGIONS)
        alerts = os.path.join(self.flags, "ws58-keeper-alerts.jsonl")
        self.assertEqual(rf.idle_violation(self.flags, free, [c], [], 1000, log=self.lines.append), 1)
        self.assertFalse(os.path.exists(alerts))
        self.assertEqual(rf.idle_violation(self.flags, free, [c], [], 1000, log=self.lines.append), 2)
        self.assertEqual(rf.idle_violation(self.flags, free, [c], [], 1000, log=self.lines.append), 3)
        recs = [json.loads(l) for l in open(alerts)]
        self.assertEqual([r["kind"] for r in recs], ["idle-violation"])
        self.assertEqual(len([l for l in self.lines if l.startswith("IDLE-VIOLATION ALERT")]), 2)
        # a grant ends the episode
        self.assertEqual(rf.idle_violation(self.flags, free, [c], [("grant", "quiet", "0-95")], 1000, log=self.lines.append), 0)
        self.assertEqual(rf.idle_violation(self.flags, free, [c], [], 1000, log=self.lines.append), 1)

    def test_no_alert_when_nothing_fits_or_nothing_is_free(self):
        c = {"id": "host", "options": [frozenset(rf.QUARTERS)], "gib": 0, "ports": []}
        for _ in range(3):
            self.assertEqual(rf.idle_violation(self.flags, {"q0"}, [c], [], 1000, log=self.lines.append), 0)
            self.assertEqual(rf.idle_violation(self.flags, set(), [c], [], 1000, log=self.lines.append), 0)
            self.assertEqual(rf.idle_violation(self.flags, set(rf.REGIONS), [], [], 1000, log=self.lines.append), 0)
        self.assertFalse(self.lines)

    def test_allocate_raises_it_on_the_pre_fix_deadlock(self):
        # pre-fix behaviour (a failing row still holds the drain and is never parked) -> the alert fires on tick 2.
        # 2026-11-03 item 7: the same-tick re-plan would grant the quiet row after yarn fails; pin it off here so the
        # alert path itself is still exercised (every row refuses to arm).
        self.row(YARN, 7, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,88-91")
        self.row("quiet", 30, QUIET_OPT, "quiet-host")
        self.broken = {YARN, "quiet"}
        saved_place, saved_af = rf.placeable, rf.arm_fails_since_pass
        rf.placeable = lambda x, *a, **k: True
        rf.arm_fails_since_pass = lambda *a, **k: []
        try:
            self.assertEqual(self.tick(), [])
            self.assertEqual(self.tick(), [])
        finally:
            rf.placeable, rf.arm_fails_since_pass = saved_place, saved_af
        self.assertTrue([l for l in self.lines if l.startswith("IDLE-VIOLATION ALERT 2 ticks")])

    def test_same_tick_replan_grants_the_next_row_when_the_first_fails_to_arm(self):
        self.row(YARN, 7, GPU_OPT, "gpu", lane="gpu", regions="mi210_0,88-91")
        self.row("quiet", 30, QUIET_OPT, "quiet-host")
        out = self.tick()
        self.assertEqual([r for _, r, _ in out], ["quiet"])
        self.assertFalse([l for l in self.lines if l.startswith("IDLE-VIOLATION")])


class ReviewItem7(Fixture):
    """2026-11-03 session review item 7: arm-failed rows order last; a non-engine ARMED pid is re-armed; a STOP file
    holds the row (state `held`, one-line fix) instead of burning the id; the engine parser tolerates unknown flags."""

    def test_arm_failed_rows_sort_after_every_healthy_row(self):
        healthy = {"id": "b", "kind": "grant", "rank": 50, "lane_count": 3, "arm_fails": 0}
        failing = {"id": "a", "kind": "grant", "rank": 1, "lane_count": 0, "arm_fails": 1}
        self.assertEqual([c["id"] for c in sorted([failing, healthy], key=rf.plan_order)], ["b", "a"])

    def test_armed_pid_without_a_filler_engine_is_rearmed_not_trusted(self):
        rid = "row-x"
        d = self.row(rid, 10, QUIET_OPT, "quiet-host")
        rf.atomic_json(rf.armed_path(self.flags, rid), {"id": rid, "pid": os.getpid(), "regions": d["regions"], "at": rf.now_iso()})
        self.assertFalse(rf.armed_engine_ok(os.getpid(), rid))   # this test process runs no filler_run*.sh
        st = rf.status(self.flags, rid)
        self.assertEqual(st["state"], "grantable")
        self.assertIn("re-armed", st["rearm"])
        self.tick()
        self.assertEqual(self.armed_calls, [rid])
        self.assertTrue([l for l in self.lines if l.startswith(f"RE-ARM {rid}")])

    def test_stop_file_holds_the_row_with_a_one_line_fix(self):
        rid = "row-stop"
        d = self.row(rid, 10, QUIET_OPT, "quiet-host")
        sf = os.path.join(self.flags, rid + ".STOP")
        d["stop_file"] = sf
        rf.atomic_json(rf.ready_path(self.flags, rid), d)
        open(sf, "w").close()
        st = rf.status(self.flags, rid)
        self.assertEqual(st["state"], "stopped")
        self.assertEqual(st["fix"], f"rm {sf}")
        self.assertEqual(self.tick(), [])
        self.assertEqual(self.armed_calls, [])
        os.remove(sf)
        self.assertEqual(rf.status(self.flags, rid)["state"], "grantable")
        self.assertEqual([r for _, r, _ in self.tick()], [rid])

    def test_engine_parser_tolerates_an_unknown_flag(self):
        gate = rf._gate()
        argv = ["bash", "/x/filler_run15.sh", "--id", "r1", "--class", "cpu", "--cmd", "true", "--min-window", "600",
                "--stop", "/x/STOP", "--complete-cmd", "true", "--new-flag-from-a-newer-engine", "--self-claim"]
        o = gate.parse_engine(argv)
        self.assertIsNotNone(o)
        self.assertEqual(o["id"], "r1")
        self.assertTrue(o["self_claim"])
        self.assertEqual(o["unknown"], ["--new-flag-from-a-newer-engine"])


if __name__ == "__main__":
    unittest.main()
