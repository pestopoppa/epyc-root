"""[Pass 5 2026-11-07: the coexist/lends machinery (COEXIST_MAX_THREADS, coexist_holds, _avail, quiet_held, FALLBACK-free
lends branches) was deleted - it was inert since gpu-q3 NARROW. This file keeps the gpu-q3 NARROW and drain tests.]"""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402

ALL_TOKENS = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
QH_OPT = frozenset(rf.compress(rf.expand(set(rf.REGIONS))))


def cx_opt(cpus):
    return frozenset(rf.cpu_tokens(cpus))


def cand(cid, options, rank=50, shape="quarter", busy=None, est=3000, lane="cpu"):
    c = {"id": cid, "kind": "grant", "lane": lane, "rank": rank, "lane_count": 0, "gib": 4, "bench": shape == "quiet-host",
         "options": [frozenset(o) for o in options], "shape": shape, "since": time.time(), "window_s": est,
         "estimate_s": est}
    if busy is not None:
        c["busy_fraction"] = busy
    return c


class Plan(unittest.TestCase):
    def test_unmarked_q3_row_still_blocks_and_drains(self):
        now = time.time()
        held = cx_opt("72-73")   # held by a NON-coexist sub-quarter row
        free = ALL_TOKENS - held - {"q3"}
        npd = cand("npd1", [QH_OPT], rank=40, shape="quiet-host", lane="gpu")
        out, _, _ = rf.plan(free, [npd], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual(out, [])
        self.assertEqual(rf.plan.last_drain[0]["id"], "npd1")
        # an unmarked low-busy q3 row is still held back by the drain
        gx = {**cand("plain", [cx_opt("74-75")], rank=55, busy=0.05, est=7200), "min_window_s": 1000 * 3600}  # D9 2026-11-11: min_window above the gap, so the cap fails cap_ok and the row stays late
        out, _, _ = rf.plan(free, [npd, gx], 1000, now=now, grant_ends=[now + 1800])
        self.assertEqual(out, [])


GPU_THR = {f"t{k}" for k in range(184, 192)}


class Coexist2(unittest.TestCase):
    """Pass 5 2026-11-07: the coexist/lends path is deleted; what remains is the gpu-q3 claim geometry."""
    GPU_ROW = {"id": "hsf5p", "lane": "gpu", "shape": "gpu-q3", "regions": "mi210_0,88-95,184-191", "timing": "bench"}

    def test_gpu_q3_claim_never_includes_72_87(self):
        self.assertEqual(rf.gpu_q3_claim_cores("mi210_0,88-95,184-191"), set(range(88, 96)))
        self.assertTrue(rf.gpu_q3_claim_cores("mi210_0,q3,184-191") & set(range(72, 88)))
        self.assertTrue(rf.gpu_q3_claim_cores("mi210_0,168-169") & set(range(72, 88)))   # siblings fold
        self.assertFalse(rf.GPU_HOST_THREADS & set(range(168, 184)))
        self.assertFalse({f"t{k}" for k in range(184, 192)} & rf.COEXIST_Q3)
        self.assertFalse(rf.cpu_tokens("88-95") & rf.COEXIST_Q3)


class GpuTimingNarrow(unittest.TestCase):
    """gpu-q3 NARROW (operator 2026-11-05 "Narrow + emergency deploy"): a GPU grant holds gpu-quiet + its host threads
    t184-191; a GPU TIMING grant also holds their SMT-sibling cores 88-95 and NEVER the rest of q3. q38p4b-int8-20261105
    (GPU timing) was refused "needs gpu-quiet,q3,t184..t191: q3 busy" while an 8-core AITER build sat on 80-87/176-183."""
    Q3_72_87 = {f"c{n}" for n in range(72, 88)} | {f"t{n}" for n in range(168, 184)}
    TIMING_FORMS = (
        {"id": "q38p4b", "lane": "gpu", "shape": "gpu-q3", "regions": "mi210_0,184-191", "timing": "bench"},
        {"id": "hsf5p", "lane": "gpu", "regions": "mi210_0,88-95,184-191", "timing": "profile"},
        {"id": "akk", "lane": "gpu", "regions": "mi210_0,184-191", "admission_class": "block-timing-quiet"},
        {"id": "akp", "lane": "gpu", "regions": "mi210_0,184-191", "admission_class": "block-timing-pairable"},
    )

    def test_gpu_timing_holds_never_include_q3_cores_72_87(self):
        for row in self.TIMING_FORMS:
            for o in ({"class": "gpu", "nofold": True, "gpu_quiet": "exclusive"}, {"class": "gpu", "launch_role": "bench"}):
                c = rf.contract_of(row, o)
                self.assertEqual(c["shape"], "gpu-q3", row["id"])
                self.assertTrue(c["timing"], row["id"])
                held = set().union(*[rf.expand(x) for x in c["options"]])
                self.assertFalse(held & self.Q3_72_87, (row["id"], sorted(held & self.Q3_72_87)))
                self.assertNotIn("q3", held, row["id"])
                self.assertTrue({rf.GPU} | rf.cpu_tokens("88-95") <= held, row["id"])   # gpu-quiet + 88-95 + t184-191

    def test_gpu_timing_tokens_constant_is_narrow(self):
        self.assertEqual(rf.GPU_Q3_TOKENS, frozenset({rf.GPU} | rf.cpu_tokens("88-95")))
        self.assertFalse(rf.GPU_Q3_TOKENS & rf.GPU_TIMING_NEVER_HELD)
        self.assertEqual(rf.GPU_TIMING_NEVER_HELD, frozenset({"q3"} | self.Q3_72_87))

    def test_gpu_correctness_and_production_rows_unchanged(self):
        hthr = frozenset({rf.GPU} | {f"t{k}" for k in range(184, 192)})
        self.assertEqual(rf.contract_of({"lane": "gpu", "regions": "mi210_0,184-191", "admission_class": "correctness"},
                                        {"class": "gpu", "nofold": True})["options"], [hthr])
        self.assertEqual(rf.contract_of({"lane": "gpu", "regions": "mi210_0,184-191"}, {"class": "gpu"})["options"], [hthr])

    def test_gpu_timing_grantable_beside_8_core_q3_cpu_grant(self):
        # the live refusal: an 8-core CPU build holds 80-87 (+176-183) on q3 -> the GPU timing row must still fit
        build = rf.cpu_tokens("80-87")
        free = ALL_TOKENS - build - {"q3"}   # q3 is not whole-free; its other cores are
        g = cand("q38p4b", [rf.GPU_Q3_TOKENS], rank=50, shape="gpu-q3", lane="gpu")
        out, idle, _ = rf.plan(free, [g], 1000)
        self.assertEqual([c["id"] for c, _ in out], ["q38p4b"])
        self.assertFalse(out[0][1] & self.Q3_72_87)
        # and the other way round: a GPU timing grant open, an 8-core CPU row on 80-87 is granted beside it
        free = ALL_TOKENS - rf.expand(set(rf.GPU_Q3_TOKENS)) - {"q3"}
        b = cand("aiter-build", [build], rank=60, shape="sub-quarter")
        out, _, _ = rf.plan(free, [b], 1000, gpu_grant_open=True)
        self.assertEqual([c["id"] for c, _ in out], ["aiter-build"])
        # negative control (the rule this replaces): with the old gpu-q3 option holding all of q3 the timing row is refused
        old = frozenset({rf.GPU, "q3"} | {f"t{k}" for k in range(184, 192)})
        free = ALL_TOKENS - build - {"q3"}
        out, idle, _ = rf.plan(free, [cand("q38p4b-old", [old], rank=50, shape="gpu-q3", lane="gpu")], 1000)
        self.assertEqual(out, [])
        self.assertIn("q3", idle[rf.GPU])

    def test_cpu_timing_row_still_keeps_off_q3_while_gpu_grant_open(self):
        # SMT-sibling rule (rowflow2 3ee751108, kept consistent here): a CPU timing row on q3 needs gpu-quiet; else q0-q2
        free = ALL_TOKENS - rf.expand(set(rf.GPU_Q3_TOKENS)) - {"q3"}
        t = cand("cpu-bench", [rf.cpu_tokens("72-79")], rank=50, shape="quiet-host")   # bench=True
        t["bench"] = True
        out, _, _ = rf.plan(free, [t], 1000, gpu_grant_open=True)
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
