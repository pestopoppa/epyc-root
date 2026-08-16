#!/usr/bin/env python3
"""Regression tests for the P3-4 fleet-health gate and the P0-2b liveness filter.

WHAT THESE PIN, AND WHY IT IS WORTH PINNING. On 2026-08-14 the fleet's tmux
windows vanished and the daemon kept assigning to the sessions that used to be
behind them; fourteen rows walked ASSIGNED -> lease expiry -> STALE_REQUEUED ->
INFRA_BLOCKED overnight. On 2026-08-16, minutes after those rows were reset,
the SAME loop immediately handed four of them back to mainA-D, still dead. So
this defect has now been observed twice, and the second time it was observed
inside the fix for the first.

TWO GATES SHIPPED IN PHASE 0, AND THEY HAVE DIFFERENT FATES.

  * per-agent `dead_agents` filter in `compute_advice` (P0-2b) — is THIS
    recipient there? PERMANENT. It is what actually stops rows being burned,
    and it is the gate that reproduced and blocked the bug live on 08-16.
    Tested here, and mutation-guarded, unchanged.
  * `_fleet_presence` (P0-2) — was there ANY main at all, and HALT if not.
    RETIRED by P3-4, which is what this file was rewritten for. Its predicate
    was declared transitional in its own comment: after Phase 3 the worker pool
    is exec'd fresh per assignment and holds no session, so "zero live workers"
    is the NORMAL IDLE STATE. Keeping it would have halted assignment and paged
    critical on every quiet hour — the alarm that fires on a well-run night,
    which is how a fleet learns to ignore its alarms.

WHAT REPLACED IT, and what these tests hold it to:

  * RUNNER LIVENESS, three-valued (functional | broken | unknown). Asked about
    a MECHANISM, not a session.
  * STARVATION: dispatchable work AND free capacity AND an idle runner AND no
    spawn attempt, held for N consecutive ticks.
  * UNKNOWN NEVER ALARMS ON EITHER BRANCH — no raise (paging on a blind
    instrument) and no clear (silently resolving a real alarm because the
    instrument went dark).
  * A QUIET, HEALTHY NIGHT PRODUCES ZERO ALARMS. That is a stated gate metric
    of the plan of record, so it is a test, not a hope:
    `QuietNightTests.test_quiet_healthy_night_touches_no_alarm_at_all`.

The old `_looks_dead` calibration tests survive verbatim: both gates fold over
that one predicate, so if it drifts, everything drifts.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import session_bus_coordinator as C  # noqa: E402


def _roster(*ids, role="main", session="testsess"):
    return [{"id": i, "role": role, "lanes": ["none"], "endpoint": f"tmux:{session}:{i}"} for i in ids]


def _pool_roster(endpoint="exec:worker_runner", lanes=("cpu", "none")):
    return [{"id": "workerpool", "role": "main", "lanes": list(lanes), "endpoint": endpoint}]


def _row(tid, *, status="READY", lane="none", screened=True, occupancy=1.0,
         owner=None, **extra):
    row = {"task_id": tid, "status": status, "lane": lane}
    if screened:
        row["screened_by"] = "backlog_row_check.py@test"
    if occupancy is not None:
        row["expected_occupancy"] = {"est_h": occupancy, "basis": "test"}
    if owner:
        row["owner"] = owner
    row.update(extra)
    return row


def _latest(*rows):
    return {r["task_id"]: r for r in rows}


_FREE_SNAPSHOT = {"cpu_busy": False, "gpu_busy": False, "none_busy": False,
                  "cpu_state": "free", "gpu_state": "free", "none_state": "free",
                  "load_class": "idle", "gpu_signal": None, "ts": "test"}


class _GateFixture(unittest.TestCase):
    """A bus root, a pool root with lanes, and every host probe pinned.

    Nothing here reaches the real tmux, the real lane snapshot or the real
    contention matrix: a test that reads production state is a test whose result
    depends on who is logged in.
    """

    POOL_LANES = ("lane0", "lane1")

    def setUp(self):
        # A THROWAWAY bus root, not a fixed directory beside the test. The old
        # `_tmp_fleetgate/` littered a TRACKED directory with untracked state
        # that survived the run — which is how a `git clean -ffdx` in a parallel
        # session becomes an event rather than a no-op.
        self.tmp = Path(tempfile.mkdtemp(prefix="fleetgate-"))
        for sub in ("heartbeats", "tokens"):
            (self.tmp / sub).mkdir(parents=True, exist_ok=True)

        self.pool_root = self.tmp / "pool"
        for lane in self.POOL_LANES:
            (self.pool_root / lane).mkdir(parents=True, exist_ok=True)

        self.alarms: list[tuple] = []
        self._real_alarm = C._alarm
        self._real_snapshot = C.lane_snapshot_cached
        self._real_co = C.co_residency_cached
        C._alarm = lambda bus_root, action, key, severity="critical", message="", evidence=None: \
            self.alarms.append((action, key, severity, message))
        C.lane_snapshot_cached = lambda: dict(_FREE_SNAPSHOT)
        C.co_residency_cached = lambda cfg: None

    def tearDown(self):
        C._alarm = self._real_alarm
        C.lane_snapshot_cached = self._real_snapshot
        C.co_residency_cached = self._real_co
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- fixture helpers ---------------------------------------------------

    def cfg(self, *, enabled=True, cap=4, pool_root=None, ticks=None):
        pool = {"enabled": enabled, "max_concurrent_workers": cap,
                "pool_root": str(pool_root if pool_root is not None else self.pool_root)}
        if ticks is not None:
            pool["starvation_ticks"] = ticks
        return {"worker_pool": pool}

    def hold_lane(self, lane="lane0", pid=None):
        """Make a lane read as HELD by a live worker (this process's own pid)."""
        (self.pool_root / lane / ".worker.lock").write_text(
            str(pid if pid is not None else os.getpid()), encoding="utf-8")

    def state(self):
        return C._read_fleet_gate_state(self.tmp)

    def health(self, latest, *, cfg=None, roster=None, tick=1, prev=None):
        return C.evaluate_fleet_health(self.tmp, cfg or self.cfg(),
                                       roster if roster is not None else _pool_roster(),
                                       latest, tick, prev or {})

    def run_ticks(self, latest, n, *, cfg=None, roster=None, start_tick=1):
        """Drive `fleet_health_pass` n times over an unchanging world."""
        cfg = cfg or self.cfg()
        roster = roster if roster is not None else _pool_roster()
        rows: list[dict] = []
        for i in range(n):
            prev = self.state()
            rows = C.fleet_health_pass(self.tmp, cfg, roster, latest, 7,
                                       start_tick + i, prev)
        return rows


# =========================================================================
# SURVIVING FROM P0-2: the one calibration both gates fold over.
# =========================================================================

class LooksDeadContractTests(unittest.TestCase):
    """If this drifts, everything that reads liveness drifts with it."""

    def test_live_window_beats_stale_heartbeat(self):
        entry = {"id": "a", "endpoint": "tmux:s:a"}
        states = {"a": {"age_s": 999999}}
        self.assertIsNone(C._looks_dead("a", entry, states, {"a"}, "s"),
                          "a live window must suppress a stale-heartbeat verdict")

    def test_no_window_and_stale_heartbeat_is_dead(self):
        entry = {"id": "a", "endpoint": "tmux:s:a"}
        states = {"a": {"age_s": C._RECIPIENT_LOOKS_DEAD_S + 1}}
        self.assertIsNotNone(C._looks_dead("a", entry, states, set(), "s"))

    def test_fresh_heartbeat_without_window_is_alive(self):
        entry = {"id": "a", "endpoint": "tmux:s:a"}
        states = {"a": {"age_s": 1.0}}
        self.assertIsNone(C._looks_dead("a", entry, states, set(), "s"))


# =========================================================================
# P3-4 part 1: runner liveness is about a MECHANISM, and it is THREE-VALUED.
# =========================================================================

class RunnerLivenessTests(_GateFixture):

    def verdict(self, cfg, roster):
        return C._runner_liveness(cfg, roster, C._pool_lane_state(cfg))

    def test_healthy_pool_reads_functional(self):
        v = self.verdict(self.cfg(), _pool_roster())
        self.assertEqual(v["runner"], C.RUNNER_FUNCTIONAL, v["reason"])

    def test_no_exec_endpoint_declared_is_unknown_not_broken(self):
        """A roster with no runner asserts nothing about a runner.

        Every pre-P2-5 config and every unrelated unit test lives here, and none
        of them may page."""
        v = self.verdict(self.cfg(), _roster("gm0"))
        self.assertEqual(v["runner"], C.RUNNER_UNKNOWN)
        self.assertIn("no exec", v["reason"])

    def test_pool_disabled_by_policy_is_unknown_not_broken(self):
        """`enabled: false` is an OPERATOR DECISION, not a fault.

        The pool ships disabled. Reading the shipped default as BROKEN would
        page critical on a stock checkout — the well-run-night alarm wearing a
        different hat."""
        v = self.verdict(self.cfg(enabled=False), _pool_roster())
        self.assertEqual(v["runner"], C.RUNNER_UNKNOWN)
        self.assertTrue(v["policy_disabled"])

    def test_missing_runner_program_is_broken(self):
        v = self.verdict(self.cfg(), _pool_roster(endpoint="exec:no_such_runner_program"))
        self.assertEqual(v["runner"], C.RUNNER_BROKEN)
        self.assertIn("no_such_runner_program", v["reason"])

    def test_missing_pool_root_is_broken(self):
        """The lanes were pre-created by P2-0. Their disappearance is a defect."""
        v = self.verdict(self.cfg(pool_root=self.tmp / "no-such-pool"), _pool_roster())
        self.assertEqual(v["runner"], C.RUNNER_BROKEN)

    def test_pool_root_with_no_lanes_is_broken(self):
        empty = self.tmp / "emptypool"
        empty.mkdir(exist_ok=True)
        v = self.verdict(self.cfg(pool_root=empty), _pool_roster())
        self.assertEqual(v["runner"], C.RUNNER_BROKEN)

    @unittest.skipIf(os.geteuid() == 0, "root can read a 000 directory")
    def test_unreadable_pool_root_is_unknown_not_broken(self):
        """UNREADABLE IS NOT ABSENT. The C14 polarity rule, one level up."""
        blind = self.tmp / "blindpool"
        blind.mkdir(exist_ok=True)
        (blind / "lane0").mkdir(exist_ok=True)
        blind.chmod(0o000)
        try:
            v = self.verdict(self.cfg(pool_root=blind), _pool_roster())
        finally:
            blind.chmod(stat.S_IRWXU)
        self.assertEqual(v["runner"], C.RUNNER_UNKNOWN)

    def test_lane_state_probe_and_free_pool_lane_agree(self):
        """One probe, two questions. A second calibration would be the fifth."""
        cfg = self.cfg()
        self.assertEqual(C._free_pool_lane(cfg), C._pool_lane_state(cfg)["free_lane"])
        self.hold_lane("lane0")
        self.assertEqual(C._free_pool_lane(cfg), C._pool_lane_state(cfg)["free_lane"])
        self.assertEqual(C._pool_lane_state(cfg)["live"], 1)

    def test_concurrency_cap_closes_capacity_even_with_a_free_lane(self):
        self.hold_lane("lane0")
        cfg = self.cfg(cap=1)
        self.assertIsNone(C._free_pool_lane(cfg))
        self.assertEqual(C._pool_lane_state(cfg)["state"], "full")


# =========================================================================
# P3-4 part 2: "dispatchable work" is a FOLD, never raw READY.
# =========================================================================

class DispatchableFoldTests(_GateFixture):

    def fold(self, latest, roster=None):
        ids, _lanes = C._dispatchable_for_runner(roster or _pool_roster(), latest,
                                                 dict(_FREE_SNAPSHOT), "", None)
        return ids

    def test_a_fully_gated_ready_row_is_dispatchable(self):
        self.assertEqual(self.fold(_latest(_row("t1"))), ["t1"])

    def test_unscreened_ready_row_is_not_dispatchable(self):
        """THE NIGHTLY-ALARM TEST, and the reason this fold exists.

        `dispatch_gate` refuses an unscreened row, and refusing it does not
        change its status: it stays READY for ever. A starvation predicate built
        on raw `status == "READY"` would therefore be TRUE every night from the
        moment the first ungated row was seeded, with the loop behaving
        perfectly — and the operator would learn to mute it."""
        self.assertEqual(self.fold(_latest(_row("t1", screened=False))), [])

    def test_row_without_occupancy_estimate_is_not_dispatchable(self):
        self.assertEqual(self.fold(_latest(_row("t1", occupancy=None))), [])

    def test_row_on_a_lane_the_pool_cannot_take_is_not_dispatchable(self):
        """A gpu row is not the pool starving. It is a row for somebody else."""
        self.assertEqual(self.fold(_latest(_row("t1", lane="gpu"))), [])

    def test_non_assignable_status_is_not_dispatchable(self):
        for status in ("ASSIGNED", "RUNNING", "DONE_PASS", "INFRA_BLOCKED"):
            with self.subTest(status=status):
                self.assertEqual(self.fold(_latest(_row("t1", status=status))), [])

    def test_stale_requeued_is_dispatchable(self):
        """It is an ASSIGNABLE status; treating it otherwise was its own black hole."""
        self.assertEqual(self.fold(_latest(_row("t1", status="STALE_REQUEUED"))), ["t1"])

    def test_ungranted_operator_gate_is_not_dispatchable(self):
        self.assertEqual(self.fold(_latest(_row("t1", operator_gates=["OP-9"]))), [])


# =========================================================================
# P3-4 part 3: the starvation conjunction, one conjunct per test.
# =========================================================================

class StarvationTests(_GateFixture):

    def test_work_capacity_and_an_idle_runner_starve_after_n_ticks(self):
        latest = _latest(_row("t1"), _row("t2"))
        prev = {}
        seen = []
        for tick in range(1, 5):
            h = self.health(latest, tick=tick, prev=prev)
            seen.append((h["starvation_ticks"], h["starved"]))
            prev = {"starvation_ticks": h["starvation_ticks"]}
        self.assertEqual(seen, [(1, False), (2, False), (3, True), (4, True)],
                         "starvation must require N consecutive condition-ticks")

    def test_a_single_condition_tick_never_starves(self):
        """Two-sample persistence: one reading is a sample, not a state."""
        h = self.health(_latest(_row("t1")))
        self.assertFalse(h["starved"])
        self.assertEqual(h["starvation_ticks"], 1)

    def test_no_dispatchable_work_never_starves(self):
        h = self.health(_latest(_row("t1", screened=False)),
                        prev={"starvation_ticks": 99})
        self.assertFalse(h["starved"])
        self.assertEqual(h["starvation_ticks"], 0, "the counter must RESET, not pause")

    def test_a_live_worker_is_not_a_starving_pool(self):
        """The back door the nightly alarm would have come in through.

        `compute_advice` skips `workerpool` while it owns a live row, so a
        healthy 40-minute worker means no spawn attempt for 40 minutes. Without
        this conjunct that reads as starvation every single time."""
        latest = _latest(_row("t1"), _row("t2", status="RUNNING", owner="workerpool"))
        h = self.health(latest, prev={"starvation_ticks": 99})
        self.assertFalse(h["starved"])
        self.assertFalse(h["runner_idle"])
        self.assertEqual(h["in_flight"], ["t2"])

    def test_a_held_lane_lock_is_not_a_starving_pool(self):
        self.hold_lane("lane0")
        h = self.health(_latest(_row("t1")), prev={"starvation_ticks": 99})
        self.assertFalse(h["starved"])
        self.assertFalse(h["runner_idle"])

    def test_full_capacity_never_starves(self):
        for lane in self.POOL_LANES:
            self.hold_lane(lane)
        h = self.health(_latest(_row("t1")), prev={"starvation_ticks": 99})
        self.assertFalse(h["capacity_free"])
        self.assertFalse(h["starved"])

    def test_a_spawn_attempt_this_tick_resets_the_counter(self):
        h = self.health(_latest(_row("t1")), tick=5,
                        prev={"starvation_ticks": 99, "last_spawn_attempt_tick": 5})
        self.assertTrue(h["spawned_this_tick"])
        self.assertEqual(h["starvation_ticks"], 0)
        self.assertFalse(h["starved"])

    def test_starvation_is_not_evaluated_when_the_runner_is_unknown(self):
        h = self.health(_latest(_row("t1")), cfg=self.cfg(enabled=False),
                        prev={"starvation_ticks": 99})
        self.assertEqual(h["runner"], C.RUNNER_UNKNOWN)
        self.assertFalse(h["starved"])

    def test_starvation_is_not_evaluated_when_the_runner_is_broken(self):
        h = self.health(_latest(_row("t1")), roster=_pool_roster(endpoint="exec:nope"),
                        prev={"starvation_ticks": 99})
        self.assertEqual(h["runner"], C.RUNNER_BROKEN)
        self.assertFalse(h["starved"])

    def test_the_threshold_is_data(self):
        h = self.health(_latest(_row("t1")), cfg=self.cfg(ticks=1))
        self.assertTrue(h["starved"], "worker_pool.starvation_ticks must be honoured")

    def test_the_verdict_never_halts_assignment(self):
        for latest, kw in ((_latest(_row("t1")), {}),
                           (_latest(), {}),
                           (_latest(_row("t1")), {"roster": _pool_roster(endpoint="exec:nope")})):
            with self.subTest(kw=kw):
                self.assertFalse(self.health(latest, **kw)["halt_assignment"])


# =========================================================================
# P3-4 part 4: the alarm contract. Zero alarms on a well-run night.
# =========================================================================

class QuietNightTests(_GateFixture):

    def test_quiet_healthy_night_touches_no_alarm_at_all(self):
        """THE GATE METRIC, as a test.

        Eight hours of ticks: the pool is enabled and healthy, both lanes free,
        nothing dispatchable (the queue holds only rows a gate refuses and rows
        already done). The old P0-2 predicate would have read this as "zero live
        mains" and paged CRITICAL on the first tick, then halted assignment for
        the rest of the night. The replacement must not raise, must not clear,
        and must not so much as invoke the alarm channel."""
        latest = _latest(_row("done", status="DONE_PASS"),
                         _row("ungated", screened=False))
        self.run_ticks(latest, 480)
        self.assertEqual(self.alarms, [], f"a quiet night produced alarms: {self.alarms}")

    def test_a_quiet_night_followed_by_morning_work_does_not_page(self):
        """The off-by-design trap: a night with no spawn is not a starved night.

        Counting ticks-since-last-spawn would put this number in the thousands
        by 06:00, so the first row seeded in the morning would trip the alarm on
        the tick it arrived, BEFORE the daemon had any chance to dispatch it.
        Counting consecutive condition-ticks is what makes this quiet."""
        self.run_ticks(_latest(), 480)
        rows = self.run_ticks(_latest(_row("t1")), 1, start_tick=481)
        self.assertEqual(self.alarms, [])
        health = [r for r in rows if r["kind"] == "fleet-health"][0]
        self.assertEqual(health["starvation_ticks"], 1)
        self.assertFalse(health["starved"])

    def test_a_healthy_working_pool_is_silent(self):
        """Work in flight, a free lane, more rows queued: a good busy night."""
        latest = _latest(_row("t1"), _row("t2", status="RUNNING", owner="workerpool"))
        self.hold_lane("lane0")
        self.run_ticks(latest, 120)
        self.assertEqual(self.alarms, [])


class AlarmTransitionTests(_GateFixture):

    def keys(self, action=None):
        return [a[1] for a in self.alarms if action is None or a[0] == action]

    def test_broken_runner_raises_critical_once(self):
        roster = _pool_roster(endpoint="exec:no_such_runner_program")
        self.run_ticks(_latest(_row("t1")), 5, roster=roster)
        raises = [a for a in self.alarms if a[0] == "raise"]
        self.assertTrue(raises)
        self.assertTrue(all(a[1] == C.ALARM_RUNNER_BROKEN and a[2] == "critical"
                            for a in raises))
        # The channel dedupes; the ADVISORY row is emitted only on the edge.
        rows = C.fleet_health_pass(self.tmp, self.cfg(), roster, _latest(_row("t1")),
                                   7, 99, self.state())
        self.assertEqual([r for r in rows if r["kind"] == "fleet-alarm"], [])

    def test_recovery_clears_the_broken_alarm_exactly_once(self):
        broken = _pool_roster(endpoint="exec:no_such_runner_program")
        self.run_ticks(_latest(), 2, roster=broken)
        self.alarms.clear()
        self.run_ticks(_latest(), 3, roster=_pool_roster(), start_tick=3)
        self.assertEqual(self.keys("clear"), [C.ALARM_RUNNER_BROKEN],
                         "the clear must fire on the edge and only on the edge")

    def test_unknown_neither_raises_nor_clears_an_active_alarm(self):
        """UNKNOWN IS NOT RECOVERY.

        Clearing a live critical alarm because the instrument went dark is the
        fail-closed twin of paging on it — it manufactures the belief that the
        fault is gone."""
        broken = _pool_roster(endpoint="exec:no_such_runner_program")
        self.run_ticks(_latest(), 2, roster=broken)
        self.alarms.clear()
        # Pool switched off by the operator: runner reads UNKNOWN.
        self.run_ticks(_latest(_row("t1")), 5, cfg=self.cfg(enabled=False),
                       roster=broken, start_tick=3)
        self.assertEqual(self.alarms, [])
        self.assertIn(C.ALARM_RUNNER_BROKEN, self.state()["raised_alarms"])

    def test_starvation_raises_a_warning_not_a_critical(self):
        self.run_ticks(_latest(_row("t1")), 4)
        raises = [a for a in self.alarms if a[0] == "raise"]
        self.assertTrue(raises)
        self.assertTrue(all(a[1] == C.ALARM_POOL_STARVED and a[2] == "warning"
                            for a in raises))

    def test_starvation_clears_when_the_work_is_taken(self):
        self.run_ticks(_latest(_row("t1")), 4)
        self.alarms.clear()
        self.run_ticks(_latest(_row("t1", status="ASSIGNED", owner="workerpool")), 2,
                       start_tick=5)
        self.assertEqual(self.keys("clear"), [C.ALARM_POOL_STARVED])

    def test_a_broken_runner_does_not_also_report_starvation(self):
        """One fault, one alarm. Starvation is evaluated only under `functional`."""
        self.run_ticks(_latest(_row("t1")), 6,
                       roster=_pool_roster(endpoint="exec:no_such_runner_program"))
        self.assertNotIn(C.ALARM_POOL_STARVED, self.keys())

    def test_health_row_is_emitted_every_tick(self):
        rows = self.run_ticks(_latest(), 1)
        self.assertEqual(len([r for r in rows if r["kind"] == "fleet-health"]), 1)


class RetiredFleetAbsentAlarmTests(_GateFixture):

    def test_fleet_absent_is_cleared_exactly_once_ever(self):
        """A retired alarm that never clears is indistinguishable from an ignored one.

        P0-2's key can be ACTIVE at the moment this predicate lands (the pool
        ships `enabled: false`, which the old gate read as "no live main"), and
        the code that would have cleared it is being deleted in the same commit.
        """
        state = {}
        self.assertTrue(C._retire_fleet_absent_alarm(self.tmp, state))
        self.assertEqual(self.alarms, [("clear", C.ALARM_FLEET_ABSENT_RETIRED,
                                        "critical", "")])
        self.alarms.clear()
        for _ in range(10):
            self.assertFalse(C._retire_fleet_absent_alarm(self.tmp, state))
        self.assertEqual(self.alarms, [], "the retirement clear must not repeat")
        self.assertTrue(state["fleet_absent_retired"])

    def test_the_retirement_marker_is_durable(self):
        state = C._read_fleet_gate_state(self.tmp)
        C._retire_fleet_absent_alarm(self.tmp, state)
        C._write_fleet_gate_state(self.tmp, state)
        self.assertTrue(C._read_fleet_gate_state(self.tmp)["fleet_absent_retired"])
        self.alarms.clear()
        reread = C._read_fleet_gate_state(self.tmp)
        self.assertFalse(C._retire_fleet_absent_alarm(self.tmp, reread))
        self.assertEqual(self.alarms, [])


class GateStateTests(_GateFixture):

    def test_an_unreadable_state_file_reads_as_empty_and_silent(self):
        (self.tmp / C._FLEET_GATE_STATE).write_text("{ not json", encoding="utf-8")
        self.assertEqual(C._read_fleet_gate_state(self.tmp), {})
        self.run_ticks(_latest(_row("t1")), 1)
        self.assertEqual(self.alarms, [],
                         "a gate that cannot remember must go quiet, not page")

    def test_the_tick_counter_is_not_the_epoch(self):
        """`epoch` counts daemon GENERATIONS. Reading it as ticks would make
        'no spawn in 3 ticks' true forever on a daemon that never restarts."""
        C._note_spawn_attempt(self.tmp, "t1", 41)
        st = self.state()
        self.assertEqual(st["last_spawn_attempt_epoch"], 41)
        self.assertEqual(st["last_spawn_attempt_tick"], 0)
        self.assertIn("last_spawn_attempt_ts", st)


# =========================================================================
# PERMANENT: the per-recipient filter, and the mutation guards.
# =========================================================================

class MutationGuardTests(unittest.TestCase):
    """Prove the load-bearing pieces are load-bearing, not decorative.

    Without these, a refactor that drops the filter would leave every test green
    while restoring the exact 2026-08-14 behaviour.
    """

    src = Path(C.__file__).read_text(encoding="utf-8")

    def test_dead_agent_filter_is_present_in_the_pick_loop(self):
        """P0-2b. PERMANENT — this is the gate that stopped the live 08-16 repro."""
        self.assertIn("dead_agents", self.src,
                      "the per-agent liveness filter vanished from compute_advice")
        # It must be consulted BEFORE the busy check, or a dead agent that also
        # holds a stale row would be reported as merely busy and stay eligible.
        i_dead = self.src.index("if aid in dead_agents:")
        i_busy = self.src.index("if aid in busy_owners:")
        self.assertLess(i_dead, i_busy, "liveness must be checked before busyness")

    def test_the_fleet_gate_no_longer_halts_assignment(self):
        """P3-4. Zero live workers is the NORMAL idle state; halting on it would
        stop the fleet every quiet hour."""
        # The bare name survives in ONE place — the historical note explaining
        # what was retired. A definition or a CALL is what must not come back.
        self.assertNotIn("def _fleet_presence", self.src)
        self.assertNotIn("_fleet_presence(", self.src)
        body = self.src[self.src.index("def apply_assignment("):]
        body = body[:body.index("\ndef ")]
        self.assertNotIn("assignment-halted", body)

    def test_the_health_pass_runs_after_the_assignment_writes(self):
        """Evaluated at the top it would judge a queue the same tick is about to
        drain, and a working loop would page."""
        body = self.src[self.src.index("def apply_assignment("):]
        body = body[:body.index("\ndef ")]
        self.assertLess(body.index('"kind": "assigned"'), body.index("fleet_health_pass("))

    def test_a_spawn_attempt_is_marked_before_the_lane_check(self):
        """An attempt is 'the loop reached the runner', not 'the runner succeeded'.
        Marking it after the early return would let a lane-starved tick read as a
        tick where nothing was tried."""
        body = self.src[self.src.index("def _exec_worker_runner("):]
        body = body[:body.index("\ndef ")]
        self.assertLess(body.index("_note_spawn_attempt("), body.index("_free_pool_lane("))

    def test_unknown_is_a_no_touch_branch(self):
        body = self.src[self.src.index("def _sync_alarm("):]
        body = body[:body.index("\ndef ")]
        self.assertIn("if want is None:", body)
        self.assertLess(body.index("if want is None:"), body.index("if want:"),
                        "the UNKNOWN branch must short-circuit before any alarm call")


if __name__ == "__main__":
    unittest.main(verbosity=2)
