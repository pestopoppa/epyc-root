"""D9 2026-11-18 GPU-Q3-GUARD: a CPU row on q3 never takes 88-95/184-191 while a GPU-lane row is queued."""
import os
import sys
import unittest

_RF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow")
sys.path.insert(0, _RF)
import rowflow as rf  # noqa: E402

ALL = {"q0", "q1", "q2", "q3", "gpu-quiet"}
NARROW_CPUS = ",".join(str(c) for c in list(range(72, 88)) + list(range(168, 184)))


def cpu(rid="c", threads=16, rank=50, opts=None, shape="quarter"):
    return {"id": rid, "kind": "grant", "lane": "cpu", "rank": rank, "lane_count": 0, "gib": 8, "bench": False,
            "shape": shape, "threads": threads, "options": opts or [frozenset({q}) for q in rf.QUARTERS]}


def gpu(rid="g", rank=60):
    return {"id": rid, "kind": "grant", "lane": "gpu", "rank": rank, "lane_count": 0, "gib": 8, "bench": False,
            "shape": "gpu-q3", "options": [frozenset(rf.GPU_Q3_TOKENS)]}


def placed(assigned):
    return {x["id"]: o for x, o in assigned}


class GpuQ3Guard(unittest.TestCase):
    def test_q3_only_free_narrow_grant_72_87(self):
        a, idle, pend = rf.plan({"q3"}, [cpu()], 1000, gpu_queued=True)
        o = placed(a)["c"]
        self.assertNotIn("q3", o)
        self.assertEqual(set(rf.expand(o)), set(rf.Q3_NARROW))
        self.assertEqual(rf.grant_regions({"regions": "any-cpu-quarter"}, o), NARROW_CPUS)
        self.assertEqual(rf.lock_cpus(o), NARROW_CPUS)

    def test_q3_only_free_full_quarter_row_waits(self):
        a, idle, pend = rf.plan({"q3"}, [cpu(threads=24)], 1000, gpu_queued=True)
        self.assertEqual(a, [])
        a, idle, pend = rf.plan({"q3"}, [cpu(threads=None)], 1000, gpu_queued=True)
        self.assertEqual(a, [])

    def test_gpu_candidate_alone_triggers_guard(self):
        # GPU row is a candidate (gpu-quiet busy so it cannot run): still narrows
        a, idle, pend = rf.plan({"q3"}, [cpu(threads=24), gpu()], 1000)
        self.assertEqual(a, [])

    def test_gpu_queued_q2_free_goes_to_q2(self):
        a, _, _ = rf.plan({"q2", "q3"}, [cpu()], 1000, gpu_queued=True)
        self.assertEqual(placed(a)["c"], frozenset({"q2"}))

    def test_no_gpu_rows_unchanged(self):
        a, _, _ = rf.plan({"q3"}, [cpu(threads=24)], 1000)
        self.assertEqual(placed(a)["c"], frozenset({"q3"}))
        a, _, _ = rf.plan({"q3"}, [cpu(threads=8)], 1000)
        self.assertEqual(placed(a)["c"], frozenset({"q3"}))

    def test_gpu_q3_row_grantable_beside_narrow(self):
        a, _, _ = rf.plan({"q3", "gpu-quiet"}, [cpu(rank=10), gpu(rank=60)], 1000)
        p = placed(a)
        self.assertEqual(set(rf.expand(p["c"])), set(rf.Q3_NARROW))
        self.assertIn("gpu-quiet", p["g"])
        self.assertFalse(rf.expand(p["c"]) & rf.expand(p["g"]))

    def test_host_rows_unchanged(self):
        h = cpu("h", threads=96, shape="host", opts=[frozenset(rf.QUARTERS)])
        a, _, _ = rf.plan({"q0", "q1", "q2", "q3"}, [h], 1000, gpu_queued=True)
        self.assertEqual(placed(a)["h"], frozenset(rf.QUARTERS))
        qh = cpu("qh", threads=96, shape="quiet-host", opts=[frozenset(set(rf.QUARTERS) | {rf.GPU})])
        a, _, _ = rf.plan(ALL, [qh, gpu()], 1000)
        self.assertEqual(placed(a)["qh"], frozenset(set(rf.QUARTERS) | {rf.GPU}))

def blk(lo):
    return frozenset({f"c{c}" for c in range(lo, lo + 4)} | {f"t{c + 96}" for c in range(lo, lo + 4)})


def sub(rid, opts, explicit=False, rank=50):
    return dict(cpu(rid, threads=4, rank=rank, opts=opts, shape="sub-quarter"), explicit=explicit)


class GpuQ3GuardSubQuarter(unittest.TestCase):
    def test_sub_blocks_never_offer_gpu_host_cores(self):
        for b in rf._sub_blocks():
            self.assertFalse(b & rf.Q3_GUARD)

    def test_gpu_queued_sub_row_takes_q2_or_narrow_never_88_95(self):
        free = rf.expand({"q2"}) | blk(88) | blk(92) | blk(72)
        free -= {"q2"} | blk(48)   # q2 partly used, so its blocks are packable
        a, _, _ = rf.plan(free, [sub("s", [blk(56), blk(88), blk(72)])], 1000, gpu_queued=True)
        o = rf.expand(placed(a)["s"])
        self.assertFalse(o & rf.Q3_GUARD)
        a, _, _ = rf.plan(blk(88) | blk(92), [sub("s", [blk(88)])], 1000, gpu_queued=True)
        self.assertEqual(a, [])

    def test_no_gpu_rows_72_87_preferred_over_88_95(self):
        free = blk(72) | blk(88)
        a, _, _ = rf.plan(free, [sub("s", [blk(88), blk(72)])], 1000)
        self.assertEqual(rf.expand(placed(a)["s"]), blk(72))

    def test_explicit_pin_on_88_95_still_honoured(self):
        a, _, _ = rf.plan(blk(88), [sub("s", [blk(88)], explicit=True)], 1000, gpu_queued=True)
        self.assertEqual(rf.expand(placed(a)["s"]), blk(88))

    def test_two_sub_rows_and_gpu_q3_row_fit_together(self):
        free = rf.expand({"q3"}) | set(rf.GPU_Q3_TOKENS)
        subs = [sub("s1", rf._sub_blocks(("q3",))), sub("s2", rf._sub_blocks(("q3",)))]
        a, _, _ = rf.plan(free, subs + [gpu(rank=60)], 1000)
        p = placed(a)
        self.assertEqual(set(p), {"s1", "s2", "g"})
        for k in ("s1", "s2"):
            self.assertTrue(rf.expand(p[k]) <= rf.Q3_NARROW)
        self.assertEqual(set(rf.expand(p["g"])), set(rf.GPU_Q3_TOKENS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
