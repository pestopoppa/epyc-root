#!/usr/bin/env python3
"""AK audit B1 (2026-11-23): a quiet / whole-host CPU row holds the CPU quarters only (q0-q2 + q3's 72-87); the GPU and its host
threads (88-95 / 184-191) only when it declares bandwidth_heavy or uses the GPU (E5 r8 drain held them 145 GPU-min)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_rowflow_shape_evidence import Fx, rf  # noqa: E402


class QuietHostCpuOnly(Fx):
    def mk(self, rid, honour=True, **spec):
        lp = self.launcher(rid, cmd="llama-bench -t 80", extra="--gpu-quiet exclusive --role bench --claim-cpus 0-95")
        if honour:
            with open(os.path.join(self.root, rid, "filler_run15.sh"), "a") as f:
                f.write("# CONTRACT_LOCK\n")
        return rf.publish(self.spec(rid, lp, regions="0-95", shape="quiet-host", baseline_ref="x", **spec), self.flags)

    def test_cpu_only_option_holds_no_gpu_and_no_host_threads(self):
        k = rf.contract_of(self.mk("e5a"), flags=self.flags)
        self.assertEqual(k["shape"], "quiet-host")
        self.assertTrue(k["cpu_only"])
        (o,) = k["options"]
        ex = rf.expand(o)
        self.assertNotIn(rf.GPU, o)
        self.assertFalse(ex & rf.Q3_GUARD, "88-95 / 184-191 stay with the GPU")
        self.assertTrue({"q0", "q1", "q2"} <= set(o) and rf.Q3_NARROW <= ex)

    def test_bandwidth_heavy_declaration_keeps_the_gpu(self):
        k = rf.contract_of(self.mk("e5b", bandwidth_heavy=True), flags=self.flags)
        self.assertFalse(k["cpu_only"])
        self.assertIn(rf.GPU, k["options"][0])

    def test_legacy_engine_unchanged(self):
        k = rf.contract_of(self.mk("e5c", honour=False), flags=self.flags)
        self.assertFalse(k["cpu_only"])
        self.assertIn(rf.GPU, k["options"][0])

    def test_grant_regions_and_fit_beside_open_gpu_grant(self):
        row = self.mk("e5d")
        k = rf.contract_of(row, flags=self.flags)
        (o,) = k["options"]
        regs = rf.grant_regions(row, frozenset(rf.compress(rf.expand(o))))
        self.assertTrue(regs.startswith("0-23,24-47,48-71,"), regs)
        self.assertNotIn("88", regs.replace("168", ""))
        free = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
        free -= rf.GPU_Q3_TOKENS   # a GPU grant holds gpu-quiet + 88-95 + 184-191
        free = {t for t in free if t not in rf.QUARTERS or rf.expand({t}) <= free}
        cand = {"id": "e5d", "options": [frozenset(rf.expand(o))], "bench": True, "cpu_only": True, "gib": 8}
        self.assertTrue(rf._fits(cand, free | {"q0", "q1", "q2"}, 900.0, True))
        self.assertFalse(rf._fits(dict(cand, cpu_only=False), free | {"q0", "q1", "q2"}, 900.0, True))


if __name__ == "__main__":
    unittest.main()
