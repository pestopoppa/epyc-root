"""Pipeline-mgmt 2026-11-20 (dcp12 vs r7d / ak-dtree-attn-route2): a quiet-host (whole host) drain whose earliest start is days
away (q0 held to the 22nd by a 52 h row) must not keep a better-ranked GPU row off a free GPU, and must not set a
reservation that delays it. Locks the BACKFILL-IF-FITS behaviour the 17:54Z IDLE-WHY line made look like a deadlock."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0
GPU_OPT = {rf.GPU} | {f"c{k}" for k in range(88, 96)} | {f"t{k}" for k in range(184, 192)}
FAR = NOW + 52 * H


def cand(rid, options, rank, shape, lane="cpu", est=3600, window=5400, minwin=2400):
    return {"id": rid, "kind": "grant", "lane": lane, "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": NOW - 4 * H, "window_s": window,
            "estimate_s": est, "min_window_s": minwin}


class QuietDrainFar(unittest.TestCase):
    def setUp(self):
        self.dcp12 = cand("dcp12", [{rf.GPU, "q0", "q1", "q2", "q3"}], 57, "quiet-host", est=7200, window=9000, minwin=3600)
        # q0-q2 held to FAR; q3 cores 88-95 + the GPU host threads + gpu-quiet free
        self.free = set(GPU_OPT) | {f"c{k}" for k in range(72, 88)}
        self.ends = {t: FAR for t in rf.expand({"q0", "q1", "q2"}) | {"q0", "q1", "q2"}}

    def plan(self, rows):
        return rf.plan(self.free, rows, 1000, now=NOW, grant_ends=[FAR], region_ends=self.ends)

    def test_better_ranked_gpu_rows_placed_beside_far_quiet_drain(self):
        r7d = cand("r7d", [GPU_OPT], 50, "gpu-q3", lane="gpu")
        ak = cand("ak-route2", [GPU_OPT], 20, "gpu-q3", lane="gpu")
        a, _, _ = self.plan([self.dcp12, r7d, ak])
        ids = [c["id"] for c, _ in a]
        self.assertEqual(ids, ["ak-route2"])   # the better-ranked GPU-q3 row takes the GPU; r7d waits on ak (same cores), not on dcp12
        self.assertNotIn("dcp12", ids)
        self.assertEqual(rf.plan.hard_end.get("ak-route2"), None)   # no cap: it ends long before dcp12's earliest start
        a2, _, _ = self.plan([self.dcp12, r7d])
        self.assertEqual([c["id"] for c, _ in a2], ["r7d"])

    def test_no_idle_gpu_label_blames_drain_when_gpu_row_fits(self):
        r7d = cand("r7d", [GPU_OPT], 50, "gpu-q3", lane="gpu")
        a, idle, _ = self.plan([self.dcp12, r7d])
        self.assertTrue(a)
        self.assertNotIn(rf.GPU, idle)

    def test_unattributed_core_hold_is_named_not_question_mark(self):
        import tempfile
        flags = tempfile.mkdtemp(prefix="idl-")
        busy = {f"c{k}" for k in range(88, 96)}
        out = rf.idle_partial_quarters(flags, set(), busy, [], {})
        self.assertIn("untracked", out["q3"])
        self.assertNotIn("held by ?", out["q3"])


if __name__ == "__main__":
    unittest.main()
