"""PM-DRAINFIX 2026-11-22 (inf45-e5v2-stageb-r7-20261121, rank 25 quiet-host, estimate 21420 s): the drain formed at
21:58Z "until 00:01Z" and slid 00:55Z -> 01:46Z -> ... -> 05:14Z. Two causes: (1) the keeper overwrote drain_state.json
with {} on every tick without a drain (DRAIN-HELD by a placeable rank-20 GPU row, WAIT-FOR-SMOKE removing the row), so
the next drain recomputed T from the newest backfill end; (2) drain_blocker dropped an already formed drain for every
better-ranked row and drain_outranks let those rows end past T on gpu-quiet. A formed drain is now STICKY."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0
T = NOW + 1.0 * H
QH = [{"gpu-quiet", "q0", "q1", "q2", "q3"}]
GPU_OPT = [{"gpu-quiet", "c88", "c89", "c90", "c91", "c92", "c93", "c94", "c95"} | {f"t{k}" for k in range(184, 192)}]


def cand(rid, options, rank, shape, est, window, minwin, lane="cpu", since=NOW - 3 * H):
    return {"id": rid, "kind": "grant", "lane": lane, "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": since, "window_s": window,
            "estimate_s": est, "min_window_s": minwin}


def e5():
    return cand("inf45-e5v2-stageb-r7-20261121", QH, 25, "quiet-host", 21420, 5400, 4800)


def ak(rid="ak-dtree-batch-rerun-gpu-20261121", est=2 * H, minwin=H):
    return cand(rid, GPU_OPT, 20, "gpu-q3", est, est * 1.2, minwin, lane="gpu")


def lsa():
    return cand("lsa-cpu-sparse-e2e-20261122-r3", [{"q0", "q1", "q2"}], 35, "multi-quarter(3)", 2 * H, 7260, 6900)


def run(rows, drain_prev=None):
    # q0-q2 busy until T (the earlier backfill); gpu-quiet and q3 free (the last GPU row just ended)
    busy = {"q0", "q1", "q2"}
    free = rf.expand({"q3", "gpu-quiet"}) | {"q3", "gpu-quiet"} | {f"t{k}" for k in range(184, 192)}
    ends = {r: T for r in rf.expand(busy) | busy}
    return rf.plan(free, rows, 1000, now=NOW, grant_ends=[T], region_ends=ends, drain_prev=drain_prev)


class StickyDrain(unittest.TestCase):
    def test_old_behaviour_without_prev_better_row_holds_the_drain(self):
        # first formation: a placeable better-ranked row still takes precedence (PM-INVERSION kept)
        a, _, _ = run([e5(), ak()])
        self.assertIn("ak-dtree-batch-rerun-gpu-20261121", {c["id"] for c, _ in a})
        self.assertIn("inf45-e5v2-stageb-r7-20261121", {c["id"] for c, _ in rf.plan.drain_held})

    def test_sticky_drain_not_dropped_for_better_row(self):
        a, _, _ = run([e5(), ak(), lsa()], drain_prev={"inf45-e5v2-stageb-r7-20261121": T})
        ids = {c["id"] for c, _ in a}
        self.assertNotIn("ak-dtree-batch-rerun-gpu-20261121", ids)   # would hold gpu-quiet past T
        self.assertNotIn("lsa-cpu-sparse-e2e-20261122-r3", ids)
        self.assertEqual(rf.plan.drain_held, [])
        self.assertEqual(rf.plan.last_drain[0]["id"], "inf45-e5v2-stageb-r7-20261121")
        self.assertEqual(rf.plan.last_drain[1], T)

    def test_sticky_T_never_moves_later(self):
        later = T + 2 * H
        busy = {"q0", "q1", "q2"}
        free = rf.expand({"q3"}) | {"q3"}
        ends = {r: later for r in rf.expand(busy) | busy}
        ends["gpu-quiet"] = later
        rf.plan(free, [e5()], 1000, now=NOW, grant_ends=[later], region_ends=ends, drain_prev={e5()["id"]: T})
        self.assertEqual(rf.plan.last_drain[1], T)

    def test_sticky_T_moves_earlier(self):
        early = NOW + 0.5 * H
        busy = {"q0", "q1", "q2"}
        free = rf.expand({"q3", "gpu-quiet"}) | {"q3", "gpu-quiet"}
        ends = {r: early for r in rf.expand(busy) | busy}
        rf.plan(free, [e5()], 1000, now=NOW, grant_ends=[early], region_ends=ends, drain_prev={e5()["id"]: T})
        self.assertEqual(rf.plan.last_drain[1], early)

    def test_short_better_row_backfills_by_T(self):
        short = ak("ak-short-gpu", est=0.5 * H, minwin=600)
        a, _, _ = run([e5(), short], drain_prev={e5()["id"]: T})
        self.assertIn("ak-short-gpu", {c["id"] for c, _ in a})

    def test_better_row_capped_at_T_when_cap_clears_min_window(self):
        capable = ak("ak-cap-gpu", est=2 * H, minwin=1200)
        a, _, _ = run([e5(), capable], drain_prev={e5()["id"]: T})
        self.assertIn("ak-cap-gpu", {c["id"] for c, _ in a})
        self.assertLessEqual(rf.plan.hard_end["ak-cap-gpu"], T)

    def test_expired_prev_is_not_sticky(self):
        a, _, _ = run([e5(), ak()], drain_prev={e5()["id"]: NOW - 60})
        self.assertIn("ak-dtree-batch-rerun-gpu-20261121", {c["id"] for c, _ in a})


class DrainStateNext(unittest.TestCase):
    def test_carry_when_no_drain_this_tick(self):
        st = rf.drain_state_next(None, {"e5": NOW + 600, "gone": NOW + 600, "old": NOW - 1}, ["e5", "old"], [], now=NOW)
        self.assertEqual(st, {"e5": NOW + 600})

    def test_granted_row_drops_its_drain(self):
        self.assertEqual(rf.drain_state_next(None, {"e5": NOW + 600}, ["e5"], ["e5"], now=NOW), {})

    def test_planner_drain_wins(self):
        self.assertEqual(rf.drain_state_next(({"id": "x"}, NOW + 5), {"e5": NOW + 600}, ["e5", "x"], [], now=NOW),
                         {"x": NOW + 5})

    def test_drain_live(self):
        self.assertEqual(rf.drain_live({"a": NOW + 1, "b": NOW - 1, "c": "junk"}, now=NOW), {"a": NOW + 1})


if __name__ == "__main__":
    unittest.main()
