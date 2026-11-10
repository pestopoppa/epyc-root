#!/usr/bin/env python3
"""Pipeline audit 2026-11-10 workstream C (operator scope "Scheduling model"): ONE booking duration (#3), smoke pockets
(#5), and the publish gate that refuses a declared shape the GPU-timing contract would silently override."""
import os
import sys
import unittest

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_COORD, "rowflow"))
sys.path.insert(0, os.path.join(_COORD, "churn"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture  # noqa: E402


class BookingDuration(unittest.TestCase):
    def test_formula_clamps(self):
        self.assertEqual(rf.compute_book_s(4900, 882, 6300), int(4900 * rf.BOOK_K))
        self.assertEqual(rf.compute_book_s(600, 882, 1500), 882)            # floor: min_window_s
        self.assertEqual(rf.compute_book_s(100000, 600, 20000), 20000)       # ceiling: window_s

    def test_legacy_row_without_book_s_gets_the_same_formula(self):
        d = {"estimate_s": 21600, "min_window_s": 882, "window_s": 26220}
        self.assertEqual(rf.book_s(d), rf.compute_book_s(21600, 882, 26220))
        self.assertEqual(rf.book_s(dict(d, book_s=1234)), 1234)


class PublishFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_book_s_and_resumable_stored(self):
        fx = self.fx
        d = fx.job("t-book-20261110")
        row = rf.publish(fx.spec("t-book-20261110", d, estimate_s=4000), fx.flags)
        self.assertEqual(row["book_s"], rf.compute_book_s(4000, row["min_window_s"], row["window_s"]))
        self.assertIs(row["resumable"], False)

    def test_estimate_beyond_window_refused_unless_resumable(self):
        fx = self.fx
        d = fx.job("t-res-20261110")
        with self.assertRaises(rf.Refused) as cm:
            rf.publish(fx.spec("t-res-20261110", d, estimate_s=7200, max_window_s=3600), fx.flags)
        self.assertIn("resumable", str(cm.exception))
        row = rf.publish(fx.spec("t-res-20261110", d, estimate_s=7200, max_window_s=3600, resumable=True), fx.flags)
        self.assertEqual(row["window_s"], 3600)
        self.assertEqual(row["book_s"], 3600)
        with self.assertRaises(rf.Refused):
            rf.publish(fx.spec("t-res-20261110", d, resumable="yes"), fx.flags)


class SmokePockets(unittest.TestCase):
    ALL = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)

    def test_pockets_are_outside_every_quarter_booking(self):
        for q in rf.QUARTERS:
            self.assertFalse(rf.expand({q}) & rf.POCKET_TOKENS, q)
        for b in rf._sub_blocks():
            self.assertFalse(b & rf.POCKET_TOKENS)

    def test_smoke_takes_a_pocket_and_leaves_the_quarter_whole(self):
        cpus = rf.pick_smoke_cpus(set(self.ALL))
        self.assertEqual(cpus, "116-119")
        toks = rf.cpu_tokens(cpus, gpu_threads=True)
        self.assertEqual(toks, {"t116", "t117", "t118", "t119"})
        self.assertFalse(rf.expand({"q0"}) & toks)

    def test_timing_neighbour_pocket_skipped(self):
        self.assertEqual(rf.pick_smoke_cpus(set(self.ALL), timing_q={"q0"}), "140-143")

    def test_no_pocket_and_only_whole_quarters_waits(self):
        free = set(self.ALL) - rf.POCKET_TOKENS
        self.assertIsNone(rf.pick_smoke_cpus(free))


class TimingShapeGate(unittest.TestCase):
    def test_role_bench_with_gpu_shape_refused(self):
        with self.assertRaises(rf.Refused) as cm:
            rf.check_timing_shape({"shape": "gpu"}, {"launch_role": "bench"}, "gpu-q3")
        self.assertIn("--role bench", str(cm.exception))
        self.assertIn('shape "gpu-q3"', str(cm.exception))

    def test_timing_class_or_kind_with_gpu_shape_refused(self):
        with self.assertRaises(rf.Refused) as cm:
            rf.check_timing_shape({"shape": "gpu", "admission_class": rf.GPU_TIMING_CLASSES[0]}, {}, "gpu-q3")
        self.assertIn("admission_class", str(cm.exception))
        with self.assertRaises(rf.Refused) as cm:
            rf.check_timing_shape({"shape": "gpu", "timing": "bench"}, {}, "gpu-q3")
        self.assertIn("spec timing", str(cm.exception))

    def test_agreeing_undeclared_or_evidence_resolved_passes(self):
        rf.check_timing_shape({"shape": "gpu-q3"}, {"launch_role": "bench"}, "gpu-q3")
        rf.check_timing_shape({}, {"launch_role": "bench"}, "gpu-q3")
        rf.check_timing_shape({"shape": "gpu"}, {"launch_role": "bench"}, "quiet-host")   # whole-host evidence
        rf.check_timing_shape({"shape": "gpu"}, {}, "gpu")


class TimingShapePublish(unittest.TestCase):
    """End to end on the vidya-r234-native-sweep-20261104e/f spec shape."""

    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_vidya_r234_shape_refused_at_publish(self):
        fx = self.fx
        d = fx.job("t-vidya-20261110")
        lp = os.path.join(d, "launch.sh")
        text = open(lp).read().replace("--class cpu", "--class gpu --no-fold-siblings --role bench")
        open(lp, "w").write(text)
        spec = fx.spec("t-vidya-20261110", d, lane="gpu", regions="mi210_0,0-23,184-191", shape="gpu",
                       width_justification="operator: replay 2026-11-10: q0 for the native sweep's tokenizer workers")
        with self.assertRaises(rf.Refused) as cm:
            rf.publish(spec, fx.flags)
        self.assertIn("declared shape 'gpu' but launcher --role bench", str(cm.exception))


class ResumableFiling(unittest.TestCase):
    def test_window_end_on_resumable_row_is_partial(self):
        import file_result as fr
        m = {"resumable": True}
        self.assertTrue(fr.window_end_resumable(m, 75, "rc=75 time=x reason=hard-end"))
        self.assertTrue(fr.window_end_resumable(m, 75, "rc=75 time=x reason=exited"))
        self.assertFalse(fr.window_end_resumable(m, 75, "rc=75 time=x reason=stopped"))
        self.assertFalse(fr.window_end_resumable({}, 75, "rc=75 time=x reason=hard-end"))


if __name__ == "__main__":
    unittest.main()
