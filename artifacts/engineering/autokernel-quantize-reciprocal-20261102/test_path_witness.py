import csv
import tempfile
import unittest
from pathlib import Path
from path_witness import inspect_trace


class WitnessTests(unittest.TestCase):
    def inspect(self, rows, fields=None):
        fields = fields or ["Kind", "Kernel_Name", "Start_Timestamp", "End_Timestamp", "Grid_Size_Y", "Grid_Size_Z"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.csv"
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(fields)
                writer.writerows(rows)
            return inspect_trace(path, 100, 200)

    def row(self, name="quantize_q8_1(float const*, void*)", start=110, end=120, y=2, z=1):
        return ["KERNEL_DISPATCH", name, start, end, y, z]

    def test_target_and_one_d_separate(self):
        result = self.inspect([self.row(), self.row("quantize_q8_1_1d(float const*, void*)", y=1)])
        self.assertEqual(result["target_dispatch_count"], 1)
        self.assertEqual(result["one_d_dispatch_count"], 1)
        self.assertFalse(result["performance_evidence_eligible"])

    def test_one_d_only_fails_coverage(self):
        self.assertEqual(self.inspect([self.row("quantize_q8_1_1d(float const*, void*)", y=1)])["dispatch_coverage"], "not_observed")

    def test_excludes_warmup_and_crossing_edges(self):
        rows = [self.row(start=80, end=90), self.row(start=90, end=110), self.row(start=190, end=210)]
        self.assertEqual(self.inspect(rows)["target_dispatch_count"], 0)

    def test_rejects_similar_names(self):
        self.assertEqual(self.inspect([self.row("quantize_q8_1_helper()")])["target_dispatch_count"], 0)

    def test_rejects_contradictory_grid(self):
        with self.assertRaises(ValueError):
            self.inspect([self.row(y=1)])

    def test_accepts_z_multidimensional(self):
        self.assertEqual(self.inspect([self.row(y=1, z=2)])["target_dispatch_count"], 1)

    def test_rejects_stats_csv(self):
        with self.assertRaises(ValueError):
            self.inspect([], ["Name", "Calls", "TotalDurationNs"])


if __name__ == "__main__":
    unittest.main()
