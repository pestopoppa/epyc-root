#!/usr/bin/env python3
"""KEEP-TAIL-1: file_result.py appends P and F to every GPU A/B row's verdict and counts it (closure counter).

Run: python3 -W ignore -m unittest scripts.coordination.tests.test_file_result_keep_tail
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TESTS))
from test_churn_file_result import Base, fr  # noqa: E402
import keep_tail  # noqa: E402

REGION = {"warm_up": "3 discarded", "timed_loop": "20 iters", "compile_import_check": "excluded"}


def samples(p_pct, n=21):
    xs = [100.0] * n
    xs[-1] = xs[-2] = 100.0 * (1 + p_pct / 100)
    return xs


class TestKeepTailWiring(Base):
    def setUp(self):
        super().setUp()
        os.environ["KEEP_TAIL_JOURNAL"] = os.path.join(self.tmp.name, "refusals.jsonl")
        self.addCleanup(os.environ.pop, "KEEP_TAIL_JOURNAL", None)

    def gpu_row(self, rid, result, lane="gpu"):
        self.row(rid, "rc == 0", result)
        mp = Path(self.flags, "ready", rid + ".json")
        m = json.loads(mp.read_text()); m["lane"] = lane; mp.write_text(json.dumps(m))

    def counter(self):
        return keep_tail.counter(Path(self.flags, "filing-done", "keep_tail_counter.jsonl"))

    def test_gpu_ab_row_gets_P_and_F_and_is_counted(self):
        self.gpu_row("FA-r5-x", {"samples_a": samples(3.9), "samples_b": samples(1.0), "effect_pct": 4.5, "timing_region": REGION})
        code, _, err = self.run_main("FA-r5-x")
        self.assertEqual(code, 0, err)
        kt = self.verdict("FA-r5-x")["keep_tail"]
        self.assertTrue(kt["reported"])
        self.assertAlmostEqual(kt["P_pct"], 3.9, places=3)
        self.assertAlmostEqual(kt["F_pct"], 5.515, places=2)
        self.assertTrue(kt["refused"])  # in scope (FA-r5*), 4.5% inside F=5.52%
        c = self.counter()
        self.assertEqual(c["rows_with_P_and_F"], 1)
        self.assertEqual(c["refusals"], 1)
        self.assertTrue(Path(self.tmp.name, "refusals.jsonl").is_file())

    def test_counter_closes_at_ten_distinct_rows(self):
        for i in range(10):
            self.gpu_row(f"ZZ-{i}", {"samples_a": samples(1.0), "samples_b": samples(1.0)})
            self.assertEqual(self.run_main(f"ZZ-{i}")[0], 0)
        self.assertEqual(self.run_main("ZZ-0")[0], 0)  # refiling does not double count
        c = self.counter()
        self.assertEqual((c["rows_with_P_and_F"], c["closed"]), (10, True))

    def test_gpu_row_without_samples_is_not_counted(self):
        self.gpu_row("G-1", {"x": 1})
        self.assertEqual(self.run_main("G-1")[0], 0)
        self.assertFalse(self.verdict("G-1")["keep_tail"]["reported"])
        self.assertEqual(self.counter()["rows_with_P_and_F"], 0)

    def test_cpu_row_untouched_and_dry_run_writes_no_counter(self):
        self.gpu_row("C-1", {"samples_a": samples(1.0), "samples_b": samples(1.0)}, lane="cpu")
        self.assertEqual(self.run_main("C-1")[0], 0)
        self.assertNotIn("keep_tail", self.verdict("C-1"))
        self.gpu_row("D-1", {"samples_a": samples(1.0), "samples_b": samples(1.0)})
        self.assertEqual(self.run_main("D-1", "--dry-run")[0], 0)
        self.assertEqual(self.counter()["rows_with_P_and_F"], 0)


if __name__ == "__main__":
    unittest.main()
