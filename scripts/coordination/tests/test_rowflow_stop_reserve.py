"""PM-STOPRES 2026-11-21 (keeper ~11:40Z): champion gate c17-fold-cpu (rank 22, q0-q2) waited while its owner STOPped
nta (q0) and idxk (q1+q2). q0 freed first and went to rank-40 single-quarter indexer-topk (until 16:17Z) although q1+q2
were still checkpointing. Regions of STOPped grants count as freeing within stopping_horizon_s; the already-free quarters
are reserved for the better multi-quarter row."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0


def cand(rid, options, rank, shape, est, minwin=H):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": NOW - H, "window_s": est * 1.5,
            "estimate_s": est, "min_window_s": minwin}


def c17():
    return cand("c17-fold-cpu-20261121", [{"q0", "q1", "q2"}], 22, "multi-quarter(3)", 4 * H)


def topk(est=4.6 * H):
    return cand("ak-q38fn-indexer-topk-exact-cpu-20261120-r3q0", [{"q0"}, {"q1"}, {"q2"}], 40, "quarter", est)


def run(rows, free, stopping, **kw):
    free = set(free)
    return rf.plan(free | rf.expand(free), rows, 1000, now=NOW, grant_ends=[NOW + 3 * H], stopping=stopping, **kw)


class StopReserve(unittest.TestCase):
    def test_incident_q0_free_idxk_stopping_worse_row_refused(self):
        a, _, _ = run([topk(), c17()], {"q0"}, {"q1", "q2"})
        self.assertEqual(a, [])
        self.assertEqual([(l["id"], h["id"]) for l, h, _ in rf.plan.stop_reserves],
                         [("ak-q38fn-indexer-topk-exact-cpu-20261120-r3q0", "c17-fold-cpu-20261121")])
        self.assertIn("q0", rf.plan.stop_reserves[0][2])

    def test_without_stopping_baseline_reproduces_incident(self):
        a, _, _ = run([topk(), c17()], {"q0"}, set())
        self.assertEqual([c["id"] for c, _ in a], ["ak-q38fn-indexer-topk-exact-cpu-20261120-r3q0"])

    def test_short_worse_row_within_horizon_may_take_it(self):
        a, _, _ = run([topk(est=300), c17()], {"q0"}, {"q1", "q2"})
        self.assertEqual([c["id"] for c, _ in a], ["ak-q38fn-indexer-topk-exact-cpu-20261120-r3q0"])

    def test_unrelated_quarter_not_reserved(self):
        topk_ = topk(); topk_["options"] = [frozenset(rf.expand({q})) | {q} for q in ("q0", "q1", "q2", "q3")]
        # q3 is free and not part of c17's option: the worse row may take it
        a, _, _ = run([topk_, c17()], {"q0", "q3"}, {"q1", "q2"})
        self.assertEqual([sorted(o) for _, o in a], [["q3"]])

    def test_better_row_placed_once_stopping_ends(self):
        a, _, _ = run([topk(), c17()], {"q0", "q1", "q2"}, set())
        self.assertEqual([c["id"] for c, _ in a], ["c17-fold-cpu-20261121"])

    def test_better_row_not_fitting_even_after_stop_reserves_nothing(self):
        # q2 held by a grant that is NOT stopping: c17 cannot become placeable, so q0 stays usable
        a, _, _ = run([topk(), c17()], {"q0"}, {"q1"})
        self.assertEqual([c["id"] for c, _ in a], ["ak-q38fn-indexer-topk-exact-cpu-20261120-r3q0"])

    def test_policy_horizon_in_data(self):
        self.assertEqual(rf.build_pocket_policy()["stopping_horizon_s"], 600)


if __name__ == "__main__":
    unittest.main()
