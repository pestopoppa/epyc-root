"""D9 2026-11-18 (KEEPER-DRAIN-HOLDS-GPU, FINDINGS pm-drain-gpu-20261118): the IDLE-WHY "draining for" prefix names
only regions in the active drain's reserve set, and a drain target whose earliest start lies beyond
DRAIN_RESERVE_HORIZON_S gets no reservation."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0
GPU_OPT = {rf.GPU} | {f"c{k}" for k in range(88, 96)} | {f"t{k}" for k in range(184, 192)}


def cand(rid, options, rank=50, shape="quarter", since=NOW, est=600, window=21600, minwin=300, lane="cpu"):
    return {"id": rid, "kind": "grant", "lane": lane, "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": since, "window_s": window,
            "estimate_s": est, "min_window_s": minwin}


def mq_drain():
    # CPU multi-quarter(2): contract_of keeps q0-q2 only (q3 excluded)
    opts = [{"q0", "q1"}, {"q0", "q2"}, {"q1", "q2"}]
    return cand("rka-a3b48", opts, rank=30, shape="multi-quarter(2)", since=NOW - 4 * H, est=H, window=2 * H, minwin=2 * H)


def gpu_row(rid="c14-fold-gpu", window=3 * H, est=3 * H, minwin=300):
    return cand(rid, [GPU_OPT], rank=26, shape="gpu", est=est, window=window, minwin=minwin, lane="gpu")


def free_tokens(gpu=True, q0=True):
    f = set()
    if q0:
        f |= rf.expand({"q0"})
    if gpu:
        f |= GPU_OPT
    return f


def run(rows, T, free=None):
    ends = {r: T for r in rf.expand({"q1", "q2"}) | {"q1", "q2"}}
    return rf.plan(free_tokens() if free is None else free, rows, 1000, now=NOW, grant_ends=[T], region_ends=ends)


class DrainHorizon(unittest.TestCase):
    def test_0_production_horizon_is_2h(self):
        self.assertEqual(rf.DRAIN_RESERVE_HORIZON_S, 7200)
        self.assertTrue(rf.drain_horizon_applies({"shape": "multi-quarter(2)"}))
        self.assertTrue(rf.drain_horizon_applies({"shape": "quarter"}))
        self.assertTrue(rf.drain_horizon_applies({"shape": "sub-quarter"}))
        for sh in ("host", "quiet-host", "gpu", "gpu-q3"):
            self.assertFalse(rf.drain_horizon_applies({"shape": sh}))

    def test_1_gpu_row_assigned_under_far_cpu_drain(self):
        a, _, _ = run([mq_drain(), gpu_row()], NOW + 7 * H)
        self.assertIn("c14-fold-gpu", {c["id"] for c, _ in a})
        self.assertNotIn("c14-fold-gpu", rf.plan.hard_end)

    def test_2_within_horizon_drain_disjoint_gpu_row_uncapped(self):
        a, _, _ = run([mq_drain(), gpu_row(minwin=1.5 * H)], NOW + 2 * H)
        self.assertIsNotNone(rf.plan.last_drain)   # within the horizon: still drains
        self.assertEqual(rf.plan.last_drain[0]["id"], "rka-a3b48")
        self.assertEqual(rf.plan.last_drain[1], NOW + 2 * H)
        self.assertIn("c14-fold-gpu", {c["id"] for c, _ in a})
        self.assertNotIn("c14-fold-gpu", rf.plan.hard_end)

    def test_3_busy_gpu_not_labelled_draining(self):
        free = free_tokens() - {rf.GPU}   # gpu-quiet busy; its host threads free
        free |= {"q3"} | rf.expand({"q3"})
        rows = [mq_drain(), gpu_row(), cand("q3-row", [{"q3", rf.GPU}], rank=60)]
        _, idle, _ = run(rows, NOW + 2 * H, free=free)
        self.assertIsNotNone(rf.plan.last_drain)
        self.assertIn("q3", idle)
        self.assertNotIn("draining for", idle["q3"])

    def test_3b_gpu_region_idle_not_labelled_draining(self):
        # gpu-quiet free but its host threads busy: the idle gpu-quiet line names its real blocker, not the drain
        free = free_tokens() - {f"t{k}" for k in range(184, 192)}
        _, idle, _ = run([mq_drain(), gpu_row()], NOW + 2 * H, free=free)
        self.assertIsNotNone(rf.plan.last_drain)
        self.assertNotIn("draining for", idle[rf.GPU])
        self.assertIn("busy", idle[rf.GPU])

    def test_4_reserved_q0_labelled_draining(self):
        _, idle, _ = run([mq_drain()], NOW + 2 * H)
        self.assertIn("draining for multi-quarter(2) rka-a3b48", idle["q0"])

    def test_5_beyond_horizon_no_reservation(self):
        T = NOW + 20 * H
        q = cand("five-h-quarter", [{"q0"}], rank=60, est=5 * H, window=5 * H, minwin=H)
        a, idle, _ = run([mq_drain(), q], T)
        self.assertIsNone(rf.plan.last_drain)
        self.assertEqual([c["id"] for c, _ in rf.plan.drain_deferred], ["rka-a3b48"])
        self.assertTrue(any(c["id"] == "rka-a3b48" and "horizon" in why for c, why in rf.plan.no_reserve))
        # PM-CAP 2026-11-21: bounded by the target's real earliest start S (20 h), not the 2 h horizon - a 5 h row ending
        # before S cannot delay it, so it gets its full window (ak-draft-head-svd-cpu-20261121-r2q0 was cut at 7260 s)
        self.assertIn("five-h-quarter", {c["id"] for c, _ in a})
        self.assertNotIn("five-h-quarter", rf.plan.hard_end)

        self.assertFalse(any("draining for" in v for v in idle.values()))

    def test_5f_row_overrunning_deferred_start_is_capped_at_S(self):
        T = NOW + 6 * H
        q = cand("long-q", [{"q0"}], rank=60, est=8 * H, window=8 * H, minwin=H)
        a, _, _ = run([mq_drain(), q], T)
        self.assertEqual([c["id"] for c, _ in rf.plan.drain_deferred], ["rka-a3b48"])
        self.assertIn("long-q", {c["id"] for c, _ in a})
        self.assertEqual(rf.plan.hard_end["long-q"], T)

    def test_5c_beyond_horizon_long_row_refused_on_deferred_regions(self):
        # a row that outlasts the deferred target's earliest start and cannot be capped (min window 25 h) stays off q0
        q = cand("five-h-quarter", [{"q0"}], rank=60, est=25 * H, window=25 * H, minwin=25 * H)
        a, _, _ = run([mq_drain(), q], NOW + 20 * H)
        self.assertEqual([c["id"] for c, _ in rf.plan.drain_deferred], ["rka-a3b48"])
        self.assertNotIn("five-h-quarter", {c["id"] for c, _ in a})

    def test_5d_long_row_off_deferred_regions_unaffected(self):
        q3 = cand("q3-long", [{"q3"}], rank=60, est=5 * H, window=5 * H, minwin=5 * H)
        free = free_tokens() | {"q3"} | rf.expand({"q3"})
        a, _, _ = run([mq_drain(), q3], NOW + 20 * H, free=free)
        self.assertIn("q3-long", {c["id"] for c, _ in a})
        self.assertNotIn("q3-long", rf.plan.hard_end)

    def test_5e_host_target_far_ahead_still_reserves(self):
        host = cand("host-tgt", [set(rf.QUARTERS)], rank=30, shape="host", since=NOW - 4 * H, est=H, window=2 * H)
        q = cand("five-h-quarter", [{"q0"}], rank=60, est=5 * H, window=5 * H, minwin=5 * H)
        T = NOW + 20 * H
        a, _, _ = rf.plan(rf.expand({"q0"}) | {"q0"}, [host, q], 1000, now=NOW, grant_ends=[T],
                          region_ends={r: T for r in rf.expand({"q1", "q2", "q3"}) | {"q1", "q2", "q3"}})
        self.assertEqual(rf.plan.drain_deferred, [])
        self.assertEqual((rf.plan.last_drain[0]["id"], rf.plan.last_drain[1]), ("host-tgt", T))
        # ends 5 h out, before T: backfills; a row ending after T must not
        self.assertIn("five-h-quarter", {c["id"] for c, _ in a})
        lng = cand("long-quarter", [{"q0"}], rank=60, est=25 * H, window=25 * H, minwin=25 * H)
        a, _, _ = rf.plan(rf.expand({"q0"}) | {"q0"}, [host, lng], 1000, now=NOW, grant_ends=[T],
                          region_ends={r: T for r in rf.expand({"q1", "q2", "q3"}) | {"q1", "q2", "q3"}})
        self.assertNotIn("long-quarter", {c["id"] for c, _ in a})

    def test_5b_within_horizon_blocks_long_quarter_row(self):
        q = cand("five-h-quarter", [{"q0"}], rank=60, est=5 * H, window=5 * H, minwin=5 * H)
        a, _, _ = run([mq_drain(), q], NOW + 1.5 * H)
        self.assertEqual(rf.plan.last_drain[0]["id"], "rka-a3b48")
        self.assertNotIn("five-h-quarter", {c["id"] for c, _ in a})

    def test_6_quiet_host_drain_still_blocks_late_gpu_row(self):
        wide = cand("drain-host", [set(rf.QUARTERS) | {rf.GPU}], rank=40, shape="quiet-host", since=NOW - 4 * H,
                    est=H, window=2 * H)
        late = cand("late-gpu", [{rf.GPU}], est=5 * H, window=5 * H, minwin=5 * H, lane="gpu")
        T = NOW + 2 * H
        a, _, _ = rf.plan({"q2", "q3", rf.GPU}, [wide, late], 1000, now=NOW, grant_ends=[T],
                          region_ends={r: T for r in rf.expand({"q0", "q1"})})
        self.assertEqual(rf.plan.last_drain[0]["id"], "drain-host")
        self.assertNotIn("late-gpu", {c["id"] for c, _ in a})


def _sim_start(dur, e0, e1, e2, step=600, ticks=3000):
    """Repeated plan() ticks: q0/q1/q2 busy until e0/e1/e2 h; every tick a fresh D-long quarter row arrives for each of
    q0, q1, q2 (min window = D, or 300 s). Returns the hour the deferred multi-quarter(2) target is granted, or None."""
    ends = {"q0": NOW + e0 * H, "q1": NOW + e1 * H, "q2": NOW + e2 * H}
    for i in range(ticks):
        t = NOW + i * step
        free = {"q3"} | rf.expand({"q3"})
        for q, e in ends.items():
            if e <= t:
                free |= {q} | rf.expand({q})
        busy = {r: e for q, e in ends.items() if e > t for r in rf.expand({q}) | {q}}
        rows = [mq_drain()] + [cand(f"s{i}-{q}-{m}", [{q}], rank=60, est=dur, window=dur, minwin=m)
                               for q in ("q0", "q1", "q2") for m in (dur, 300)]
        a, _, _ = rf.plan(free, rows, 10 ** 6, now=t, grant_ends=[e for e in ends.values() if e > t], region_ends=busy)
        for c, regs in a:
            if c["id"] == "rka-a3b48":
                return (t - NOW) / H
            q = next(r for r in ("q0", "q1", "q2", "q3") if r in regs)
            if q != "q3":
                ends[q] = min(rf.plan.hard_end.get(c["id"], t + dur), t + dur)
    return None


class DeferredTargetAntiStarvation(unittest.TestCase):
    """D9 2026-11-18 "only admit rows that end within 2 h": BOUND - a deferred partial-host target is granted no later
    than its original earliest start S0 (here the 2nd-earliest q0-q2 end), whatever the length D of the quarter rows
    streaming onto its regions. Without the rule D=20 h under 20/24/28 never started (>500 h)."""

    def test_bound_s0_staggered_layouts(self):
        for e, s0 in (((20, 24, 28), 24.0), ((20, 30, 40), 30.0)):
            for d in (1, 5, 10, 20):
                with self.subTest(layout=e, D=d):
                    got = _sim_start(d * H, *e)
                    self.assertIsNotNone(got, "target starved")
                    self.assertLessEqual(got, s0)


if __name__ == "__main__":
    unittest.main()
