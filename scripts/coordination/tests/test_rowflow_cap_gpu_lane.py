"""D9 cap-at-T backfill on the GPU lane (pipeline-mgmt 2026-11-11, ws58 17:47Z symptom).

A quiet-host row drains gpu-quiet,q0..q3 until T while q0..q3 are busy until T and gpu-quiet + t184-191 are free.
A GPU-lane row (gpu-quiet + its host threads) whose cap clears min_window is admitted with end capped at T; a row whose
min_window does not fit before T waits; a gpu-q3 row (needs c88-95) waits on busy q3 regardless of the cap."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

NOW = 1_800_000_000.0
H = 3600.0
T = NOW + 4 * H
GPU_TOK = {rf.GPU} | {f"t{k}" for k in range(184, 192)}


def cand(rid, options, rank=150, shape="gpu", since=NOW, est=9000, window=11100 + 4 * H, minwin=3600):
    return {"id": rid, "kind": "grant", "lane": "gpu", "rank": rank, "lane_count": 1, "gib": 8, "bench": False,
            "options": [frozenset(o) for o in options], "shape": shape, "since": since, "window_s": window,
            "estimate_s": est, "min_window_s": minwin}


def quiet_host():
    return cand("qh-drain", [set(rf.QUARTERS) | {rf.GPU}], rank=40, shape="quiet-host", since=NOW - H, est=H, window=2 * H)


def free_tokens():
    busy = rf.expand(set(rf.QUARTERS))
    return {t for t in rf.expand(set(rf.QUARTERS)) | GPU_TOK if t not in busy} | GPU_TOK


def run(rows):
    busy = rf.expand(set(rf.QUARTERS))
    return rf.plan(free_tokens(), rows, 1000, now=NOW, grant_ends=[T], region_ends={r: T for r in busy})


class CapGpuLaneAtT(unittest.TestCase):
    def test_gpu_row_capped_at_T_during_quiet_host_drain(self):
        a, idle, _ = run([quiet_host(), cand("gpu-long", [GPU_TOK])])   # window 25500 s > 4 h to T, min 3600 s fits
        self.assertEqual(rf.plan.last_drain[0]["id"], "qh-drain")
        self.assertEqual(rf.plan.last_drain[1], T)
        self.assertEqual({c["id"] for c, _ in a}, {"gpu-long"})
        self.assertEqual(rf.plan.hard_end, {"gpu-long": T})
        self.assertNotIn(rf.GPU, idle)

    def test_gpu_row_min_window_too_long_waits(self):
        a, idle, _ = run([quiet_host(), cand("gpu-minwin", [GPU_TOK], minwin=4 * H)])
        self.assertEqual(a, [])
        self.assertEqual(rf.plan.hard_end, {})
        self.assertIn("draining for quiet-host qh-drain", idle[rf.GPU])

    def test_gpu_q3_row_waits_on_busy_q3_cores(self):
        q3row = cand("gpu-q3", [GPU_TOK | {f"c{k}" for k in range(88, 96)}], shape="gpu-q3")
        a, _, _ = run([quiet_host(), q3row])
        self.assertEqual(a, [])

    def test_drain_row_still_takes_everything_at_T(self):
        a, _, _ = rf.plan(set(rf.QUARTERS) | {rf.GPU}, [quiet_host(), cand("gpu-long", [GPU_TOK])], 1000,
                          now=T, grant_ends=[], region_ends={})
        self.assertEqual([c["id"] for c, _ in a], ["qh-drain"])

    def test_capped_window_ends_at_T(self):
        start = rf.grant_start(NOW).timestamp()   # grants are back-dated 1-2 min
        self.assertLessEqual(start + rf.capped_window(25500, T, now=NOW), T)


if __name__ == "__main__":
    unittest.main()
