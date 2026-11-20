"""PM-INVERSION 2026-11-20 (keeper 22:50Z): q0-q2 idled ~2.75 h. Rank-22/40 multi-quarter(3) q0-q2 rows were
build-pocket-held (invisible to drain_blocker), so the rank-110 host row akx-all-13a drained q0-q3 until q3 freed at
01:37Z; once the build claim cleared, the better rows were drain-late (estimates past T) and still locked out.
A drain must never block a strictly better-ranked row; equal/worse rows stay drain-late (whole-host starvation guard)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0
T = NOW + 2.75 * H
Q012 = [{"q0", "q1", "q2"}]


def cand(rid, options, rank, shape, est, window, minwin, since=NOW - 3 * H):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": since, "window_s": window,
            "estimate_s": est, "min_window_s": minwin}


def host_row():
    return cand("akx-all-13a-q38fn-threads-20261118-r2", [{"q0", "q1", "q2", "q3"}], 110, "host", 2 * H, 4 * H, 4 * H)


def better_rows():
    return [cand("c16-fold-cpu-20261118", Q012, 22, "multi-quarter(3)", 4 * H, 6 * H, 4 * H),
            cand("ak-q38fn-draftfa-w8192-cpu-20261120-r2", Q012, 40, "multi-quarter(3)", 4 * H, 6 * H, 4 * H)]


def run(rows, **kw):
    free = rf.expand({"q0", "q1", "q2"}) | {"q0", "q1", "q2"}
    ends = {r: T for r in rf.expand({"q3"}) | {"q3"}}
    return rf.plan(free, rows, 1000, now=NOW, grant_ends=[T], region_ends=ends, **kw)


class DrainRankInversion(unittest.TestCase):
    def test_better_rows_placed_no_drain(self):
        a, _, _ = run([host_row()] + better_rows())
        self.assertIn("c16-fold-cpu-20261118", {c["id"] for c, _ in a})
        self.assertIsNone(rf.plan.last_drain)

    def test_build_held_better_rows_block_worse_drain(self):
        pol = dict(rf.build_pocket_policy(), long_hold_s=7200, max_hold_s=7200)
        a, _, _ = run([host_row()] + better_rows(), build_waiting=True, build_policy=pol)
        self.assertEqual(sorted(rf.plan.build_held), sorted(c["id"] for c in better_rows()))
        self.assertIsNone(rf.plan.last_drain)   # no drain for the rank-110 row over build-held rank-22/40 rows
        self.assertIn("akx-all-13a-q38fn-threads-20261118-r2", {c["id"] for c, _ in rf.plan.drain_held})

    def test_active_drain_never_binds_better_row(self):
        # even with a persisted drain for a worse row, a better row overrunning T is not drain-late
        drain = host_row()
        self.assertFalse(rf.drain_outranks(better_rows()[0], drain))
        self.assertTrue(rf.drain_outranks(cand("worse", Q012, 120, "multi-quarter(3)", 4 * H, 6 * H, 4 * H), drain))
        self.assertTrue(rf.drain_outranks(cand("equal", Q012, 110, "multi-quarter(3)", 4 * H, 6 * H, 4 * H), drain))

    def test_worse_rows_still_drain_late(self):
        worse = cand("worse-mq3", Q012, 150, "multi-quarter(3)", 4 * H, 6 * H, 4 * H, since=NOW)
        a, _, _ = run([host_row(), worse])
        self.assertIsNotNone(rf.plan.last_drain)
        self.assertEqual(rf.plan.last_drain[0]["id"], "akx-all-13a-q38fn-threads-20261118-r2")
        self.assertNotIn("worse-mq3", {c["id"] for c, _ in a})


    def test_worse_quarter_row_does_not_fragment_better_mq3(self):
        # 22:54Z: rank-35 quarter row lsa (starved lane, ordered first) took q0; rank-22 c16 (q0-q2) then could not fit
        lsa = cand("lsa-cpu-sparse-e2e-bound-20261120-r1", [{"q0"}, {"q1"}, {"q2"}], 35, "quarter", 2 * H, 2.6 * H, H)
        lsa["lane_count"] = 0
        c16 = better_rows()[0]
        a, idle, _ = run([lsa, c16])
        self.assertEqual({c["id"] for c, _ in a}, {"c16-fold-cpu-20261118"})

    def test_idle_why_names_build_pocket_hold(self):
        pol = dict(rf.build_pocket_policy(), long_hold_s=7200, max_hold_s=7200)
        _, idle, _ = run(better_rows(), build_waiting=True, build_policy=pol)
        self.assertIn("BUILD-POCKET-HELD", idle["q1"])
        self.assertIn("c16-fold-cpu-20261118", idle["q1"])


if __name__ == "__main__":
    unittest.main()
