"""PM-WFSFIX 2026-11-25 replay: WAIT-FOR-SMOKE held host / quiet-host rows (q1/q2 idle) behind a queued rank-3 GPU smoke
that could not start because grant ak-c22-knee-batch-gate-gpu-20261125-r3 held the GPU until 17:14Z."""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rowflow"))
import rowflow as rf  # noqa: E402

ALLQ = {"q0", "q1", "q2", "q3", rf.GPU}
PERNUMA = dict(id="ak-pernuma-contam-cpu-20261124-r3", shape="host", kind="cpu", rank=15.0, options=[set(ALLQ)])
CENSUS = dict(id="ak-q38fn-served-census-full-cpu-20261125", shape="quiet-host", kind="cpu", rank=42.0, options=[set(ALLQ)])
GPUROW = dict(id="g-worse", shape="gpu", kind="gpu", rank=20.0, options=[{rf.GPU, "t184"}])
FLEX = dict(id="cpu-flex", shape="quarter", kind="cpu", rank=30.0, options=[{"q1"}, {"q3"}])
Q1 = dict(id="cpu-q1", shape="quarter", kind="cpu", rank=30.0, options=[{"q1"}])


def knee_grant(end_s=7800):
    return {"id": "ak-c22-knee-batch-gate-gpu-20261125-r3", "holds": {rf.GPU, "t184"},
            "end": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + end_s))}


class WaitForSmokeGpuHeld(unittest.TestCase):
    def test_live_state_nothing_waits_while_gpu_granted(self):
        gh = rf.gpu_smoke_blocker([knee_grant()])
        self.assertEqual(gh[0], "ak-c22-knee-batch-gate-gpu-20261125-r3")
        cands = [PERNUMA, CENSUS, GPUROW]
        self.assertEqual(rf.smoke_wait_rows(cands, 3.0, gpu_holder=gh), [])
        self.assertEqual(rf.smoke_wait_trim(cands, 3.0, gpu_holder=gh), cands)

    def test_ended_grant_does_not_block(self):
        self.assertIsNone(rf.gpu_smoke_blocker([knee_grant(-60)]))
        self.assertEqual(rf.gpu_smoke_blocker([], {rf.GPU})[0], "running GPU smoke")

    def test_gpu_free_keeps_intent(self):
        cands = [PERNUMA, CENSUS, GPUROW, FLEX, Q1]
        ids = [c["id"] for c in rf.smoke_wait_rows(cands, 3.0)]
        self.assertEqual(ids, [PERNUMA["id"], CENSUS["id"], GPUROW["id"]])   # all touch q3 / GPU host threads
        trimmed = {c["id"]: c for c in rf.smoke_wait_trim(cands, 3.0)}
        self.assertEqual(trimmed["cpu-flex"]["options"], [{"q1"}])            # never q3 ahead of the smoke
        self.assertEqual(trimmed["cpu-q1"]["options"], [{"q1"}])
        self.assertEqual(FLEX["options"], [{"q1"}, {"q3"}])                   # input not mutated

    def test_better_rank_and_exempt_never_wait(self):
        self.assertEqual(rf.smoke_wait_rows([PERNUMA], 20.0), [])
        self.assertEqual(rf.smoke_wait_rows([PERNUMA], 3.0, exempt={PERNUMA["id"]}), [])

    def test_host_shape_starves_out(self):
        with tempfile.TemporaryDirectory() as d:
            now = 1_000_000.0
            self.assertEqual(rf.smoke_wait_starved(d, [PERNUMA], now=now), [])
            self.assertEqual(rf.smoke_wait_starved(d, [PERNUMA], now=now + rf.QH_SMOKE_WAIT_MAX_S + 1), [PERNUMA["id"]])


if __name__ == "__main__":
    unittest.main()
