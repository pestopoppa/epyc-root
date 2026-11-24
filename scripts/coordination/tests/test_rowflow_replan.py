#!/usr/bin/env python3
"""REPLAN "C" (operator 2026-11-24 "Keep B shadow, build C"; docs/design/rowflow-replanning-scheduler.md): the pure solver
(replan.py) - hard constraints, objective, deferral, hysteresis, anti-starvation pin, time budget, determinism, verify() -
the keeper adapter (rowflow.replan_items / replan_flags), the shadow metrics day record, and the 2026-11-24 incident
snapshots (10:27, 11:20, 11:39, 15:51, 16:19Z) replayed as C's would-place decisions."""
import json
import os
import random
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import replan as R  # noqa: E402
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
DAY0 = 1795478400.0          # 2026-11-24T00:00:00Z


def Q(*qs):
    return frozenset(rf.expand(set(qs)))


HOST = frozenset(rf.expand({"q0", "q1", "q2"}) | rf.HOST_Q3_CPU)   # the CPU-only host booking 0-83
GPU_OPT = frozenset(rf.GPU_Q3_TOKENS)


def item(rid, rank=50, opts=(("q0",),), dur=3600, **kw):
    c = {"id": rid, "kind": "row", "lane": "cpu", "rank": rank, "options": [Q(*o) if isinstance(o, tuple) else frozenset(o) for o in opts],
         "dur": dur, "since": NOW - 60}
    c.update(kw)
    return c


def start(res, rid):
    e = next((e for e in res["plan"] if e["id"] == rid), None)
    return None if e is None else e["start"] - NOW


def overlap(res, a, b):
    ea = next(e for e in res["plan"] if e["id"] == a)
    eb = next(e for e in res["plan"] if e["id"] == b)
    return ea["start"] < eb["end"] and eb["start"] < ea["end"]


class Constraints(unittest.TestCase):
    def test_tokens_serialise_and_disjoint_rows_run_together(self):
        r = R.solve([item("a", 40), item("b", 40), item("c", 40, opts=(("q1",),))], [], {}, NOW, 900)
        self.assertFalse(r["violations"])
        self.assertFalse(overlap(r, "a", "b"))
        self.assertEqual(start(r, "c"), 0)
        self.assertEqual(sorted(r["start_now"]), sorted({"c", min(("a", "b"), key=lambda x: start(r, x))}))

    def test_no_preemption_running_tokens(self):
        run = [{"id": "g", "tokens": Q("q0"), "end": NOW + 1800}]
        r = R.solve([item("a", 9)], run, {}, NOW, 900)
        self.assertEqual(start(r, "a"), 1800)
        self.assertEqual(r["start_now"], [])

    def test_busy_tokens_known_and_unknown_end(self):
        r = R.solve([item("a", 9), item("b", 9, opts=(("q1",),))], [], {"c3": NOW + 900, "c30": None}, NOW, 900)
        self.assertEqual(start(r, "a"), 900)
        self.assertEqual(start(r, "b"), R.UNKNOWN_HOLD_S)   # unknown end = hold from now (next tick)

    def test_quiet_serial(self):
        r = R.solve([item("a", 40, quiet=True), item("b", 40, opts=(("q1",),), quiet=True)], [], {}, NOW, 900, lock=False)
        self.assertFalse(overlap(r, "a", "b"))
        run = [{"id": "q", "tokens": Q("q2"), "end": NOW + 600, "quiet": True}]
        r = R.solve([item("a", 40, quiet=True)], run, {}, NOW, 900, lock=False)
        self.assertEqual(start(r, "a"), 600)

    def test_quiet_host_vs_loud_both_ways_and_plain_rows_coexist(self):
        r = R.solve([item("qh", 9, qh=True), item("loud", 40, opts=(("q1",),), loud=True, dur=600),
                     item("plain", 40, opts=(("q2",),))], [], {}, NOW, 900)
        self.assertFalse(overlap(r, "qh", "loud"))
        self.assertTrue(overlap(r, "qh", "plain"))
        run = [{"id": "b", "tokens": Q("q1"), "end": NOW + 1200, "loud": True}]
        r = R.solve([item("qh", 9, qh=True)], run, {}, NOW, 900)
        self.assertEqual(start(r, "qh"), 1200)
        run = [{"id": "h", "tokens": Q("q1"), "end": NOW + 1200, "qh": True}]
        r = R.solve([item("loud", 9, loud=True)], run, {}, NOW, 900)
        self.assertEqual(start(r, "loud"), 1200)

    def test_exclusive_cpu_blocks_new_cpu_starts_not_gpu(self):
        run = [{"id": "x", "tokens": Q("q0"), "end": NOW + 3000, "excl": True}]
        r = R.solve([item("cpu", 40, opts=(("q1",),)), item("gpu", 40, opts=(GPU_OPT,), lane="gpu")], run, {}, NOW, 900, lock=False)
        self.assertEqual(start(r, "cpu"), 3000)
        self.assertEqual(start(r, "gpu"), 0)

    def test_ports_and_ram(self):
        r = R.solve([item("a", 40, ports=[8080]), item("b", 40, opts=(("q1",),), ports=[8080])], [], {}, NOW, 900, lock=False)
        self.assertFalse(overlap(r, "a", "b"))
        r = R.solve([item("a", 40, gib=500), item("b", 40, opts=(("q1",),), gib=500)], [], {}, NOW, 1000, lock=False)
        self.assertFalse(overlap(r, "a", "b"))   # 1000 - 500 - 500 < 100 margin
        run = [{"id": "big", "tokens": Q("q2"), "end": NOW + 900, "gib": 400}]
        r = R.solve([item("a", 40, gib=500)], run, {}, NOW, 500, lock=False)
        self.assertEqual(start(r, "a"), 900)    # RAM frees when the running row ends

    def test_gpu_token_exclusive(self):
        r = R.solve([item("g1", 20, opts=(GPU_OPT,), lane="gpu", dur=600), item("g2", 20, opts=(GPU_OPT,), lane="gpu", dur=600)],
                    [], {}, NOW, 900)
        self.assertFalse(overlap(r, "g1", "g2"))
        self.assertFalse(r["violations"])

    def test_phantom_never_starts_now(self):
        r = R.solve([item("p", 9, opts=[Q("q0") | {"hold:p"}], phantom=True, rel=NOW + 600)], [], {"hold:p": NOW + 600}, NOW, 900)
        self.assertEqual(start(r, "p"), 600)
        self.assertEqual(r["start_now"], [])


class Objective(unittest.TestCase):
    def test_urgent_first_and_low_row_stays_off(self):
        """the 10:27Z shape: a rank-9 quiet-host head released in 10 min; a rank-60 4.6 h quiet row fits now on q0."""
        run = [{"id": "claim", "tokens": Q("q0"), "end": NOW + 600, "loud": True}]
        r = R.solve([item("c21", 9, opts=[HOST], dur=5925, qh=True, loud=True, excl=True),
                     item("calib", 60, opts=(("q1",), ("q2",)), dur=12420, quiet=True, loud=True)], run, {}, NOW, 900)
        self.assertEqual(start(r, "c21"), 600)
        self.assertNotIn("calib", r["start_now"])
        self.assertFalse(r["violations"])

    def test_negative_value_deferred_forced_rows_never(self):
        # lock term: with urgent arrivals, a long loud non-urgent row is worth less than leaving it for later
        st = {"urgent_seen": {f"u{i}": [NOW - 600, "cpu"] for i in range(6)}}
        r = R.solve([item("long", 60, dur=6 * 3600, loud=True)], [], {}, NOW, 900, state=st)
        self.assertIn("long", r["unplaced"])
        r = R.solve([item("urg", 9, dur=6 * 3600, loud=True)], [], {}, NOW, 900, state=st)
        self.assertEqual(r["start_now"], ["urg"])

    def test_rank_weight_orders_one_lane(self):
        """the start discount is w * size * dur * s / 2H: between EQUAL weights the order is value-neutral (the incumbent /
        rank seed decides); a higher rank weight goes first whatever its length."""
        gs = [item("g60", 60, opts=(GPU_OPT,), lane="gpu", dur=600), item("g15", 15, opts=(GPU_OPT,), lane="gpu", dur=3600)]
        r = R.solve(gs, [], {}, NOW, 900)
        self.assertEqual([e["id"] for e in r["plan"]], ["g15", "g60"])


class Hysteresis(unittest.TestCase):
    def test_incumbent_kept_on_equal_value(self):
        a, b = item("a", 40), item("b", 40)
        r0 = R.solve([a, b], [], {}, NOW, 900)
        self.assertEqual(r0["start_now"], ["a"])
        r1 = R.solve([a, b], [], {}, NOW, 900, state={"order": ["b", "a"]})
        self.assertEqual(r1["start_now"], ["b"])          # the incumbent order wins a tie
        self.assertTrue(r1["hysteresis_kept"] or r1["plan"][0]["id"] == "b")

    def test_small_move_not_reordered(self):
        """an alternative that moves every start by < HYST_S is cosmetic: the incumbent stays (5-min rows, rank 20 vs 25)."""
        a, b = item("a", 35, dur=300), item("b", 20, dur=300)
        r = R.solve([a, b], [], {}, NOW, 900, state={"order": ["a", "b"]})
        self.assertEqual(r["start_now"], ["a"])
        self.assertTrue(r["hysteresis_kept"])

    def test_big_gain_reorders(self):
        hi, lo = item("hi", 15, dur=3600), item("lo", 80, dur=4 * 3600)
        r = R.solve([hi, lo], [], {}, NOW, 900, state={"order": ["lo", "hi"]})
        self.assertEqual(r["start_now"], ["hi"])
        self.assertFalse(r["hysteresis_kept"])

    def test_deterministic(self):
        cs = [item(f"r{i}", 20 + 7 * i, opts=(("q0",), ("q1",), ("q2",)), dur=1800 + 600 * i, quiet=i % 2 == 0) for i in range(8)]
        r1 = R.solve(cs, [], {}, NOW, 900)
        r2 = R.solve(list(reversed(cs)), [], {}, NOW, 900)
        self.assertEqual([(e["id"], e["start"], e["tokens"]) for e in r1["plan"]], [(e["id"], e["start"], e["tokens"]) for e in r2["plan"]])


class Pin(unittest.TestCase):
    def test_wait_pin_forces_a_deferred_row(self):
        st = {"urgent_seen": {f"u{i}": [NOW - 600, "cpu"] for i in range(6)}}
        r = R.solve([item("long", 60, dur=6 * 3600, loud=True, since=NOW - 13 * 3600)], [], {}, NOW, 900, state=st)
        self.assertEqual(r["pinned"], ["long"])
        self.assertEqual(r["start_now"], ["long"])

    def test_pinned_row_ahead_of_better_ranked_non_urgent(self):
        r = R.solve([item("old", 80, dur=3600, since=NOW - 12.5 * 3600), item("new", 20, dur=3600)], [], {}, NOW, 900)
        self.assertEqual(r["start_now"], ["old"])
        self.assertLess(start(r, "old"), start(r, "new"))

    def test_bumps_pin_next_solve(self):
        st = {"starts": {"x": NOW - 2000.0}, "bumps": {"x": R.PIN_BUMPS - 1}}
        run = [{"id": "g", "tokens": Q("q0"), "end": NOW + 3600}]
        r = R.solve([item("x", 60)], run, {}, NOW, 900, state=st)
        self.assertEqual(r["state"]["bumps"]["x"], R.PIN_BUMPS)
        self.assertIn("x", r["state"]["pinned"])
        r2 = R.solve([item("x", 60)], run, {}, NOW + 120, 900, state=r["state"])
        self.assertIn("x", r2["pinned"])

    def test_urgent_rows_never_pinned(self):
        r = R.solve([item("u", 5, since=NOW - 13 * 3600)], [], {}, NOW, 900)
        self.assertEqual(r["pinned"], [])


class Budget(unittest.TestCase):
    def _synthetic(self, n, seed=7):
        rng = random.Random(seed)
        out = []
        for i in range(n):
            k = rng.random()
            if k < 0.25:
                out.append(item(f"g{i}", rng.choice([3, 15, 20, 30, 50, 100]), opts=(GPU_OPT,), lane="gpu",
                                dur=rng.choice([300, 900, 2400, 6000]), since=NOW - rng.randint(0, 20000)))
            elif k < 0.35:
                out.append(item(f"h{i}", rng.choice([9, 40, 110]), opts=[HOST], dur=rng.choice([3600, 10500]), qh=True, loud=True,
                                since=NOW - rng.randint(0, 20000)))
            else:
                out.append(item(f"c{i}", rng.choice([9, 20, 40, 45, 60, 100]), opts=(("q0",), ("q1",), ("q2",)),
                                dur=rng.choice([600, 1800, 3600, 12000, 28000]), quiet=rng.random() < 0.6, loud=rng.random() < 0.6,
                                gib=rng.choice([8, 40, 200]), since=NOW - rng.randint(0, 40000)))
        run = [{"id": "run0", "tokens": Q("q0"), "end": NOW + 2400, "quiet": True, "loud": True},
               {"id": "run1", "tokens": GPU_OPT, "end": NOW + 1500, "lane": "gpu"}]
        return out, run

    def test_budget_respected_at_60_rows(self):
        cs, run = self._synthetic(60)
        r = R.solve(cs, run, {}, NOW, 1000, budget_s=0.2, max_evals=10 ** 6)
        self.assertTrue(r["budget_hit"])
        self.assertLess(r["solve_ms"], 600)   # budget 200 ms + the one evaluation in flight + verify()
        self.assertFalse(r["violations"])

    def test_live_budget_p99_under_1s(self):
        ms = []
        for s in range(6):
            cs, run = self._synthetic(30, seed=s)
            r = R.solve(cs, run, {}, NOW, 1000)
            self.assertFalse(r["violations"], r["violations"][:3])
            ms.append(r["solve_ms"])
        self.assertLess(max(ms), R.BUDGET_S * 1000 * 1.5)

    def test_verify_catches_a_bad_plan(self):
        cs = [item("a", 40), item("b", 40)]
        s = R.Solver(cs, [], {}, NOW, 900)
        bad = [{"id": "a", "start": NOW, "end": NOW + 3600, "tokens": sorted(Q("q0"))},
               {"id": "b", "start": NOW + 60, "end": NOW + 3660, "tokens": sorted(Q("q0"))}]
        v = R.verify(bad, s.items, s.running, s.busy, NOW, 900, 100, NOW + R.H_S)
        self.assertTrue(any("overlap" in x for x in v))


class Metrics(unittest.TestCase):
    def test_day_record_carries_enforce_criteria(self):
        acc = None
        t = DAY0 + 10 * 3600
        live_row = {"rank": 60, "size": 1.0, "dur": 12420, "quiet": True, "since": t - 60}
        for i in range(5):
            now = t + 120 * i
            r = R.solve([item("c21", 9, opts=[HOST], dur=5925, qh=True, loud=True, since=t - 60),
                         item("calib", 60, opts=(("q1",),), dur=12420, quiet=True, loud=True, since=t - 60)], [], {}, now, 900,
                        live_now={"calib": Q("q1")} if i == 0 else None)
            acc, done = R.metrics_tick(acc, now, r, {"calib": live_row} if i == 0 else {}, build_hot=False)
            self.assertIsNone(done)
        acc, done = R.metrics_tick(acc, DAY0 + 86400 + 60, None, {})
        for k in ("constraint_violations", "solver_ms", "weighted_work", "urgent_wait_min", "build_lane_collisions",
                  "pinned_rows", "enforce_criteria", "enforce_ready_today"):
            self.assertIn(k, done)
        self.assertEqual(done["day"], "2026-11-24")
        self.assertEqual(done["constraint_violations"], 0)
        self.assertEqual(done["urgent_wait_min"]["plan_n"], 1)
        self.assertTrue(done["enforce_criteria"]["solver_p99_lt_1s"])
        self.assertEqual(acc["day"], "2026-11-25")
        self.assertEqual(acc["errors"], 1)

    def test_collision_counted_when_build_hot(self):
        r = R.solve([item("q", 40, quiet=True)], [], {}, NOW, 900, lock=False)
        acc, _ = R.metrics_tick(None, NOW, r, {}, build_hot=True)
        self.assertEqual(acc["collisions_plan"], ["q"])


# ------------------------------------------------------------------------------------- keeper adapter (rowflow.replan_*)
def man_c21(rid):
    return {"id": rid, "shape": "host", "lane": "cpu", "requires_quiet_host": True, "busy_fraction": 0.75, "exclusive_cpu": True,
            "priority_rank": 9, "estimate_s": 7900, "book_s": 5925, "owner": "autokernel"}


def man_ak(rid, rank, est, quiet=True, book=None):
    m = {"id": rid, "shape": "quarter", "lane": "cpu", "busy_fraction": 1.0, "priority_rank": rank, "estimate_s": est,
         "book_s": book or int(est * 0.75), "owner": "autokernel"}
    m["requires_quiet_host" if quiet else "quiet_sensitive"] = True
    return m


def cand(rid, rank, opts, d, since=None, **kw):
    c = {"id": rid, "kind": "grant", "lane": d.get("lane", "cpu"), "rank": float(rank), "lane_count": 0, "gib": 8,
         "bench": False, "options": [frozenset(o) for o in opts], "shape": d.get("shape"), "window_s": int(d["estimate_s"]) + 900,
         "estimate_s": d["estimate_s"], "min_window_s": 600, "book_s": d.get("book_s"), "since": since if since is not None else NOW - 600,
         "ports": [], "arm_fails": 0}
    c.update(kw)
    return c


def grant(gid, holds, start, end):
    return {"id": gid, "holds": set(holds), "start": rf.dt.datetime.fromtimestamp(start, rf.dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "end": rf.dt.datetime.fromtimestamp(end, rf.dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}


def allfree():
    return set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)


class Adapter(unittest.TestCase):
    def test_flags_match_the_live_gates(self):
        f = rf.replan_flags(man_c21("c21"), {"id": "c21", "options": [HOST], "rank": 9})
        self.assertEqual(f, {"quiet": False, "qh": True, "loud": True, "excl": True})
        f = rf.replan_flags(man_ak("a", 40, 3600), {"id": "a", "options": [Q("q0")], "rank": 40})
        self.assertEqual(f, {"quiet": True, "qh": True, "loud": True, "excl": False})
        f = rf.replan_flags(man_ak("s", 60, 3600, quiet=False), {"id": "s", "options": [Q("q0")], "rank": 60})
        self.assertEqual(f, {"quiet": True, "qh": False, "loud": True, "excl": False})
        g = {"id": "g", "lane": "gpu", "shape": "gpu-q3", "busy_fraction": 1.0}
        self.assertEqual(rf.replan_flags(g, {"id": "g", "lane": "gpu", "options": [GPU_OPT]}),
                         {"quiet": False, "qh": False, "loud": False, "excl": False})
        self.assertTrue(rf.replan_flags({}, {"kind": "claim", "loud": True})["loud"])

    def test_items_running_estimate_and_busy(self):
        mans = {"run": man_ak("run", 40, 8000, book=6000), "c21": man_c21("c21")}
        g = grant("run", {"q0"}, NOW - 1200, NOW + 9 * 3600)
        lc = grant("build-pipeline-mgmt-x", {"c84", "c85", "c86", "c87"}, NOW - 60, NOW + 840)
        free = allfree() - Q("q0") - {"c84", "c85", "c86", "c87", "t180", "t181", "t182", "t183"} - {"c50"}
        its, run, busy = rf.replan_items([cand("c21", 9, [HOST], mans["c21"])], lambda r: mans.get(r, {}), [g, lc], free,
                                         {"c50": NOW + 777}, NOW, light_ids={"build-pipeline-mgmt-x"})
        r0 = next(x for x in run if x["id"] == "run")
        self.assertAlmostEqual(r0["end"], NOW - 1200 + 6000 - 1200 % 60, delta=61)   # start + book_s, not the 9 h grant end
        self.assertFalse(next(x for x in run if x["id"].startswith("build-"))["loud"])   # a light claim is not loud
        self.assertEqual(busy.get("c50"), NOW + 777)
        self.assertEqual(its[0]["dur"], 5925)
        self.assertTrue(its[0]["qh"] and its[0]["excl"])

    def test_gate_hold_re_decided_next_tick_phantom_keeps_smoke_end(self):
        """B's hold:<id> for a gate-dropped quiet head ends at the latest loud grant END; C models those grants itself from
        their estimates, so for C the gate hold is next tick. A phantom (smoke pending) keeps its smoke-budget end."""
        h, p = rf.HOLD_PREFIX + "c21", rf.HOLD_PREFIX + "ph"
        cs = [cand("c21", 9, [set(HOST) | {h}], man_c21("c21"), hold="QUIET-SERIAL"),
              cand("ph", 9, [set(Q("q2")) | {p}], man_c21("ph"), phantom=True, hold="smoke pending")]
        its, _, busy = rf.replan_items(cs, lambda r: {}, [], allfree(), {h: NOW + 5 * 3600, p: NOW + 1500}, NOW)
        self.assertEqual(busy[h], NOW + rf.RESERVE_TICK_S)
        self.assertEqual(busy[p], NOW + 1500)
        self.assertEqual(next(i for i in its if i["id"] == "ph")["rel"], NOW + 1500)


# ------------------------------------------------------------------- 2026-11-24 incident snapshots: C's would-place
def snap(cands, mans, grants, free, region_ends, now, gpu_q3=False, live=None, state=None):
    its, run, busy = rf.replan_items(cands, lambda r: mans.get(r, {}), grants, free, region_ends, now, gpu_q3=gpu_q3)
    return R.solve(its, run, busy, now, 900, live_now=live, state=state)


T = DAY0


class IncidentReplays(unittest.TestCase):
    def test_1027_calib_a3b_not_started_c21_r2_planned(self):
        """10:27Z live: GRANT ak-cpu-aa-calibration-q-a3b (rank 60, 4.6 h) on q0 while c21-fold-cpu-r2 (rank 9) was gate-dropped
        (foreign busy on q0 + BUILD-LANE) -> owner STOP at 10:45. C: c21-r2 (B's hold head, re-decided next tick) first; the
        calibration row only after it (or deferred)."""
        now = T + 10 * 3600 + 27 * 60
        mans = {"c21-fold-cpu-20261124-r2": man_c21("c21-fold-cpu-20261124-r2"),
                "ak-cpu-aa-calibration-q-a3b-20261123": man_ak("ak-cpu-aa-calibration-q-a3b-20261123", 60, 16560, quiet=False),
                "c21-gpu27b-identity-r2-20261124": {"lane": "gpu", "shape": "gpu-q3", "priority_rank": 5}}
        gpu = grant("c21-gpu27b-identity-r2-20261124", GPU_OPT, T + 8.13 * 3600, T + 14.4 * 3600)
        tok = rf.HOLD_PREFIX + "c21-fold-cpu-20261124-r2"
        c21 = cand("c21-fold-cpu-20261124-r2", 9, [set(HOST) | {tok}], mans["c21-fold-cpu-20261124-r2"], since=now - 1080,
                   hold="foreign busy on q0")
        calib = cand("ak-cpu-aa-calibration-q-a3b-20261123", 60, [Q(q) for q in ("q0", "q1", "q2")],
                     mans["ak-cpu-aa-calibration-q-a3b-20261123"], since=T + 8 * 3600)
        free = allfree() - GPU_OPT
        r = snap([c21, calib], mans, [gpu], free, {tok: now + rf.RESERVE_TICK_S}, now, gpu_q3=True,
                 live={"ak-cpu-aa-calibration-q-a3b-20261123": Q("q0")})
        self.assertEqual(r["start_now"], [])
        self.assertEqual(start(r, "c21-fold-cpu-20261124-r2") + NOW - now, rf.RESERVE_TICK_S)
        cal = "ak-cpu-aa-calibration-q-a3b-20261123"   # after the head, or deferred (lane lock: 4.6 h quiet row)
        self.assertTrue(start(r, cal) is None or not overlap(r, "c21-fold-cpu-20261124-r2", cal))
        self.assertGreater(r["value"], r["live_value"])   # the live decision is worth less under C's objective
        self.assertFalse(r["violations"])

    def test_1120_specpit_r4_not_started(self):
        """11:20Z live: c21-fold-cpu-r3 refused for foreign busy 31% on q3; ak-specpit1-t1p100-r4 (rank 40, 7.7 h, quiet) took q0
        -> owner STOP 11:26. C: c21-r3 at the hold's end, specpit after it."""
        now = T + 11 * 3600 + 20 * 60
        h = "c21-fold-cpu-20261124-r3"
        sp = "ak-specpit1-a3b-mtp-cpu-t1p100-20261123-r4"
        c18 = "ak-cpu-aa-calibration-q-c18-20261123-r3"
        mans = {h: man_c21(h), sp: man_ak(sp, 40, 28020), c18: man_ak(c18, 60, 24840, quiet=False)}
        tok = rf.HOLD_PREFIX + h
        cs = [cand(h, 9, [set(HOST) | {tok}], mans[h], since=now - 120, hold="foreign busy 31% on q3"),
              cand(sp, 40, [Q(q) for q in ("q0", "q1", "q2")], mans[sp], since=T + 9 * 3600),
              cand(c18, 60, [Q(q) for q in ("q0", "q1", "q2")], mans[c18], since=T + 9 * 3600)]
        free = allfree() - {"q3"} - {f"t{k}" for k in range(184, 191)}
        r = snap(cs, mans, [], free, {tok: now + rf.RESERVE_TICK_S}, now, live={sp: Q("q0")})
        self.assertEqual(r["start_now"], [])
        self.assertEqual(start(r, h) + NOW - now, rf.RESERVE_TICK_S)
        for low in (sp, c18):
            s = start(r, low)
            self.assertTrue(s is None or not overlap(r, h, low), low)
        self.assertGreater(r["value"], r["live_value"])

    def test_1139_specpit_t1p095_not_started_head_not_pushed_to_gpu_end(self):
        """11:39Z live: RANK-SKIP c21-r3 'needs busy regions until 13:56Z' (the GPU grant's end, which it does not need) ->
        GRANT ak-specpit1-t1p095 (rank 40, 19.8 h) on q0 -> owner STOP 11:42. C: c21-r3 planned at the end of ITS OWN busy
        cores (q3 72-83, unknown end -> next tick), never at the 13:56Z GPU end; nothing overlapping it starts."""
        now = T + 11 * 3600 + 39 * 60
        h, sp = "c21-fold-cpu-20261124-r3", "ak-specpit1-a3b-mtp-cpu-t1p095-20261123"
        mans = {h: man_c21(h), sp: man_ak(sp, 40, 85800),
                "c21-fold-gpu-20261124-r2": {"lane": "gpu", "shape": "gpu-q3", "priority_rank": 4, "estimate_s": 7000, "book_s": 7000}}
        gpu = grant("c21-fold-gpu-20261124-r2", GPU_OPT, T + 11.54 * 3600, T + 13.94 * 3600)
        cs = [cand(h, 9, [HOST], mans[h], since=now - 1260), cand(sp, 40, [Q(q) for q in ("q0", "q1", "q2")], mans[sp], since=T + 9 * 3600)]
        q3busy = {f"c{k}" for k in range(72, 84)} | {f"t{k}" for k in range(168, 180)}
        free = allfree() - GPU_OPT - {"q3"} - q3busy
        r = snap(cs, mans, [gpu], free, {}, now, gpu_q3=True, live={sp: Q("q0")})
        self.assertEqual(r["start_now"], [])
        self.assertLessEqual(start(r, h) + NOW - now, rf.RESERVE_TICK_S)   # not 13:56Z
        self.assertTrue(start(r, sp) is None or not overlap(r, h, sp))

    def test_1551_gpu_short_rows_first(self):
        """15:51Z: the device frees with 13 GPU rows queued; live granted ak-df2-pointmass (rank 15, 46 min) at 15:52. Three urgent
        GPU rows were released in the trailing 2 h (c21-fold-gpu-r4 13:53Z, c21-nospec 14:24Z, c21-stepc-r3 15:05Z: rho_gpu =
        1.5/h), so the lane lock prices every long GPU placement. C starts the oldest-waiting rank-20 row, then the 5- and 10-min
        rows, then pointmass; the 102-min vidya row is deferred."""
        now = T + 15 * 3600 + 52 * 60
        rows = [("ak-df2-pointmass-gpu-20261124", 15, 2785, 15.78), ("vidya-r18d-aa-27b-20261124-r2", 15, 6100, 12.75),
                ("ak-c21-tree-official-gpu-20261124", 20, 3600, 8.06), ("ak-gdn-pscale-rocm-tests-gpu-20261124", 20, 600, 15.78),
                ("ak-mmid-ub-ceil-gpu-20261124", 25, 300, 12.75), ("ak-c21-census-refresh-gpu-20261124", 30, 660, 15.11),
                ("ak-a3b-router-fuse-gate-gpu-20261124", 30, 1400, 15.5), ("fold-kld-floor-gpu-20261124-r2", 30, 1800, 15.5),
                ("ak-i8gemm-pc-sol-gpu-20261124", 40, 900, 15.51), ("ak-specstale1-df2-np2-c21-bands-gpu-20261124-r2", 50, 3600, 15.52),
                ("ak-df2-np4-parity-reuse-gpu-20261124-r2", 50, 3600, 15.52), ("ak-27b-tail-fuse-gate-gpu-20261124", 100, 3300, 15.56),
                ("ak-gvfattn-served-gpu-20261124-r4", 100, 3600, 15.67)]
        mans, cs = {}, []
        for rid, rank, bs, pas in rows:
            mans[rid] = {"lane": "gpu", "shape": "gpu-q3", "priority_rank": rank, "estimate_s": bs, "book_s": bs}
            cs.append(cand(rid, rank, [GPU_OPT], mans[rid], since=T + pas * 3600, lane="gpu", shape="gpu-q3", bench=True))
        urg = {"c21-fold-gpu-20261124-r4": [T + 13.88 * 3600, "gpu"], "c21-nospec-determinism-gpu-20261124": [T + 14.40 * 3600, "gpu"],
               "c21-fold-gpu-27b-stepc-20261124-r3": [T + 15.08 * 3600, "gpu"]}
        r = snap(cs, mans, [], allfree(), {}, now, gpu_q3=True, live={"ak-df2-pointmass-gpu-20261124": GPU_OPT},
                 state={"urgent_seen": urg})
        self.assertFalse(r["violations"])
        # the oldest rank-20 row (waiting since 08:03Z, aged x1.98) first, then the 5- and 10-min rows, then pointmass;
        # vidya (102 min) is deferred by the GPU lane lock - the set the simulator's C ran (design doc section 9)
        self.assertEqual(r["start_now"], ["ak-c21-tree-official-gpu-20261124"])
        order = [e["id"] for e in sorted(r["plan"], key=lambda e: e["start"])]
        self.assertEqual(order[1:4], ["ak-mmid-ub-ceil-gpu-20261124", "ak-gdn-pscale-rocm-tests-gpu-20261124",
                                      "ak-df2-pointmass-gpu-20261124"], order)
        self.assertIn("vidya-r18d-aa-27b-20261124-r2", r["unplaced"])
        self.assertGreater(r["value"], r["live_value"])

    def test_1619_draftwin_head_past_grant_end_holds_q0(self):
        """16:19Z live: ak-q38fn-draftwin (rank 40, host) could start only at a live smoke's end (16:38Z) - past every grant end
        (16:31Z) - so B's earliest_start dropped it (NO-RESERVE / RANK-SKIP) and cdr-a3b-q4kv-32k (rank 45, 1 h) took q0. C sees
        the smoke end as a busy token: draftwin is planned at 16:38Z and cdr is NOT started into its window."""
        now = T + 16 * 3600 + 19 * 60
        dw, cdr, occ = "ak-q38fn-draftwin-c22-cpu-20261124", "cdr-a3b-q4kv-32k-cpu-20261124", "rka-occupant-q1"
        mans = {dw: dict(man_c21(dw), priority_rank=40, exclusive_cpu=False, estimate_s=14000, book_s=10500),
                cdr: {"shape": "quarter", "lane": "cpu", "priority_rank": 45, "estimate_s": 3000, "book_s": 3600, "owner": "pipeline-mgmt"},
                occ: man_ak(occ, 20, 3600, quiet=False)}
        g = grant(occ, {"q1"}, now - 3000, T + 16 * 3600 + 31 * 60)
        mans[occ]["book_s"] = int(T + 16 * 3600 + 31 * 60 - (now - 3000 - (now - 3000) % 60))
        smoke = Q("q2")
        cs = [cand(dw, 40, [HOST], mans[dw], since=T + 15.15 * 3600, shape="host"),
              cand(cdr, 45, [Q(q) for q in ("q0", "q1", "q2")], mans[cdr], since=T + 15.88 * 3600, shape="quarter")]
        free = allfree() - Q("q1") - smoke
        r = snap(cs, mans, [g], free, {t: T + 16 * 3600 + 38 * 60 for t in smoke}, now, live={cdr: Q("q0")})
        self.assertFalse(r["violations"])
        self.assertAlmostEqual(start(r, dw) + NOW, T + 16 * 3600 + 38 * 60, delta=60)
        self.assertNotIn(cdr, r["start_now"])
        self.assertFalse(overlap(r, dw, cdr))
        self.assertGreater(r["value"], r["live_value"])


class AllocateShadow(unittest.TestCase):
    """allocate() wiring in a temp flags dir is covered by the replay gate (tests/replay scenarios replan-*); here: the
    report path persists state + plan and appends a day record on rollover, and a solver failure is logged, not raised."""
    def test_report_persists_and_rolls_day(self):
        with tempfile.TemporaryDirectory() as fl:
            lines = []
            r = R.solve([item("a", 40, since=DAY0)], [], {}, DAY0 + 3600, 900)
            r["_items"] = {}
            rf.replan_report(fl, r, [], "shadow", lines.append, now=DAY0 + 3600)
            sd = rf.state_dir(fl)
            self.assertTrue(os.path.exists(os.path.join(sd, rf.REPLAN_STATE)))
            self.assertEqual(json.load(open(os.path.join(sd, rf.REPLAN_PLAN)))["start_now"], ["a"])
            self.assertTrue(any(l.startswith("REPLAN-SHADOW place a at now") for l in lines), lines)
            self.assertTrue(any(l.startswith("REPLAN-SHADOW diff live=- plan=a") for l in lines), lines)
            self.assertTrue(any(l.startswith("REPLAN-SHADOW solve ") for l in lines), lines)
            rf.replan_report(fl, None, [], "shadow", lines.append, error=RuntimeError("boom"), now=DAY0 + 86400 + 10)
            recs = [json.loads(l) for l in open(os.path.join(sd, rf.REPLAN_METRICS))]
            self.assertEqual([x["day"] for x in recs], ["2026-11-24"])
            self.assertIn("enforce_criteria", recs[0])
            self.assertTrue(any("REPLAN-SHADOW failed" in l for l in lines))

    def test_mode_constant_is_shadow(self):
        self.assertEqual(rf.REPLAN_MODE, "shadow")
        self.assertEqual(rf.replan_mode(), "shadow")
        self.assertEqual(rf.RESERVATION_MODE, "shadow")


if __name__ == "__main__":
    unittest.main()
