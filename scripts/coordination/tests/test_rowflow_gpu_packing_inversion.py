"""AK audit 2026-11-20 (GPU idle 11:50-12:11Z): the PACKING rule kept a sub-quarter gpu-q3 row (gpu-quiet + 88-95 +
184-191) off a free q3 because "whole-quarter rows that fit now" counted quarter rows that could not be placed (drain-
late against the q0-q2 drain until 12:36Z; under GPU-Q3-GUARD no CPU row may take q3's 88-95 anyway). Rank-30 GPU rows
idled the MI210 behind rank-45/57 rows that never ran. A drain or reservation for a BETTER row must still hold."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
M = 60.0
T = NOW + 46 * M


def cand(rid, options, rank, shape="quarter", lane="cpu", window=4 * 3600, est=3 * 3600, minwin=3600, since=NOW, threads=None):
    c = {"id": rid, "kind": "grant", "lane": lane, "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
         "options": [frozenset(o) for o in options], "shape": shape, "since": since, "window_s": window,
         "estimate_s": est, "min_window_s": minwin}
    if threads:
        c["threads"] = threads
    return c


def gpu_row(rid, rank=30, mins=40):
    return cand(rid, [{rf.GPU} | set(rf.Q3_GUARD)], rank, shape="gpu-q3", lane="gpu", window=mins * M, est=mins * M * 0.8,
                minwin=mins * M)


def drain_row(rank=30):
    return cand("draftfa", [{"q0", "q1", "q2"}], rank, shape="multi-quarter(3)", since=NOW - 3 * 3600, window=3 * 3600)


def quarter_rows():
    return [cand(f"df2-{i}", [{"q0"}, {"q1"}, {"q2"}, {"q3"}], 45, threads=24) for i in range(3)] + \
           [cand("dcp12", [set(rf.QUARTERS) | {rf.GPU}], 57, shape="quiet-host", window=3 * 3600)]


FREE = rf.expand({"q1", "q3"}) | {rf.GPU} | {f"t{k}" for k in range(184, 192)}
ENDS = {r: T for r in rf.expand({"q0", "q2"})}


def run(rows):
    return rf.plan(FREE, rows, 1000, now=NOW, grant_ends=[T], region_ends=ENDS)


class GpuPackingInversion(unittest.TestCase):
    def test_gpu_row_takes_mi210_while_quarter_rows_are_drain_late(self):
        a, _, _ = run([drain_row(), gpu_row("ak-dtree-batch-27b-gpu-r2"), gpu_row("ak-dtree0-wvsk16")] + quarter_rows())
        ids = {c["id"] for c, _ in a}
        self.assertTrue(ids & {"ak-dtree-batch-27b-gpu-r2", "ak-dtree0-wvsk16"}, ids)
        self.assertEqual(rf.plan.last_drain[0]["id"], "draftfa")

    def test_better_ranked_quiet_host_drain_still_holds_gpu_row(self):
        qh = cand("qh-better", [set(rf.QUARTERS) | {rf.GPU}], 20, shape="quiet-host", window=3 * 3600)
        a, _, _ = run([qh, gpu_row("g", rank=30, mins=70)])
        self.assertEqual(a, [])
        self.assertEqual(rf.plan.last_drain[0]["id"], "qh-better")

    def test_worse_ranked_quiet_host_drain_never_holds_better_gpu_row(self):
        # the brief's case: rank-57 quiet-host + rank-30 70-min GPU row -> drain_blocker holds the drain, the row runs
        qh = cand("dcp12", [set(rf.QUARTERS) | {rf.GPU}], 57, shape="quiet-host", window=3 * 3600)
        a, _, _ = run([qh, gpu_row("g", rank=30, mins=70)])
        self.assertEqual({c["id"] for c, _ in a}, {"g"})
        self.assertIn(("dcp12", "g"), [(h["id"], b["id"]) for h, b in rf.plan.drain_held])


if __name__ == "__main__":
    unittest.main()
