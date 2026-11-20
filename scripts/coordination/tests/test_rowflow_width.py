#!/usr/bin/env python3
"""F6 (AK audit B6): booking width is checked against the launcher's LITERAL thread knobs."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_rowflow_shape_evidence import Fx  # noqa: E402
import rowflow as rf  # noqa: E402


class LiteralWidth(Fx):
    def test_threads48_multiquarter3_refused_without_justification(self):
        lp = self.launcher("w48", cmd="llama-bench --threads 48")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("w48", lp, regions="any-cpu-quarter", shape="multi-quarter(3)"), self.flags)
        self.assertIn("literal thread knobs sum to 48", str(e.exception))
        self.assertIn("multi-quarter(2)", str(e.exception))

    def test_justified_admitted(self):
        lp = self.launcher("w48j", cmd="llama-bench --threads 48")
        row = rf.publish(self.spec("w48j", lp, regions="any-cpu-quarter", shape="multi-quarter(3)",
                                   width_justification="third quarter holds the KV-cache prefill shard"), self.flags)
        self.assertEqual(row["shape"], "multi-quarter(3)")

    def test_matching_width_admitted(self):
        lp = self.launcher("w48m", cmd="llama-bench --threads 48")
        self.assertEqual(rf.publish(self.spec("w48m", lp, regions="any-cpu-quarter", shape="multi-quarter(2)"),
                                    self.flags)["shape"], "multi-quarter(2)")

    def test_literal_sum(self):
        lp = self.launcher("wsum", cmd="OMP_NUM_THREADS=24 a; b -t 24", pre="# --threads 96 in a comment\n")
        self.assertEqual(rf.literal_threads_sum(lp), 48)


if __name__ == "__main__":
    unittest.main()
