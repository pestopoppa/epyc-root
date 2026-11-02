"""Operator rule 2026-11-02: a dry run never holds the whole host (ws58)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rowflow"))
import rowflow as rf

HOST = [frozenset({"q0", "q1", "q2", "q3"})]
QUIET = [frozenset({"q0", "q1", "q2", "q3", "gpu-quiet"})]


class DryrunOneQuarter(unittest.TestCase):
    def check_one_quarter(self, row, opts):
        dopts, one_q = rf.dryrun_shape(row, opts)
        self.assertTrue(one_q)
        for o in dopts:
            self.assertEqual(len([q for q in o if q in rf.QUARTERS]), 1, dopts)
            self.assertNotIn(rf.GPU, o)
        self.assertEqual(rf.grant_regions(row, dopts[0], one_q), "0-23")
        self.assertEqual(rf.ws58_cpus(rf.grant_regions(row, dopts[0], one_q)), "0-23")
        # the real grant keeps its full shape
        self.assertEqual(rf.grant_regions(row, opts[0], False), row["regions"])

    def test_host_row_private_engine_big_ram_whole_host_flag(self):
        row = {"regions": "0-95", "shape": "host", "gib": 900, "dryrun_whole_host": True,
               "engine": {"path": "/somewhere/private-engine.sh"}}
        self.check_one_quarter(row, HOST)

    def test_quiet_host_row(self):
        row = {"regions": "0-95", "shape": "quiet-host", "gib": 600, "engine": {"path": "/private/engine.sh"}}
        self.check_one_quarter(row, QUIET)

    def test_gpu_row_unchanged(self):
        row = {"regions": "mi210_0,184-191", "shape": "gpu", "gib": 40}
        opts = [frozenset({"q3", "gpu-quiet"})]
        dopts, one_q = rf.dryrun_shape(row, opts)
        self.assertEqual(dopts, opts)
        self.assertFalse(one_q)
        self.assertEqual(rf.grant_regions(row, dopts[0], one_q), "mi210_0,184-191")


if __name__ == "__main__":
    unittest.main()
