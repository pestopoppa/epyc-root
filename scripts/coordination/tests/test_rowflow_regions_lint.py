"""Keeper audit 2026-11-10 fix 4: publish lints (warns, never refuses) a row whose concrete regions name more cores than
its evidence contract holds. Temp dirs only."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow"))
import rowflow as rf  # noqa: E402
from test_rowflow_shape_evidence import Fx  # noqa: E402

LINT = "REGIONS-WIDER-THAN-SHAPE"


def lints(row):
    return [w for w in row.get("publish_warnings") or [] if LINT in w]


class RegionsLint(Fx):
    def test_unit_wider_regions_warn(self):
        c = {"shape": "quarter", "held": 24}
        self.assertIn(LINT, rf.regions_wider_lint("48-95", c))
        self.assertIn(LINT, rf.regions_wider_lint("q1,q2", c))
        self.assertIsNone(rf.regions_wider_lint("48-71", c))
        self.assertIsNone(rf.regions_wider_lint("any-cpu-quarter", c))
        self.assertIsNone(rf.regions_wider_lint("48-95", c, {"shape_override": "operator: op 2026-11-10: wide"}))

    def test_gpu_host_threads_are_not_counted(self):
        self.assertIsNone(rf.regions_wider_lint("mi210_0,184-191", {"shape": "gpu", "held": 0}))
        self.assertIn(LINT, rf.regions_wider_lint("mi210_0,48-95,144-191", {"shape": "gpu", "held": 0}))

    def test_publish_records_lint_for_quarter_shape_with_two_quarters_of_regions(self):
        lp = self.launcher("wq", cmd="bench -t 24")
        row = rf.publish(self.spec("wq", lp, regions="48-95", shape="quarter",
                                   width_justification="lint fixture: wide declared regions, quarter job"), self.flags)
        self.assertTrue(lints(row), row.get("publish_warnings"))

    def test_publish_clean_row_has_no_lint(self):
        lp = self.launcher("ok", cmd="bench -t 24")
        row = rf.publish(self.spec("ok", lp, regions="any-cpu-quarter", shape="quarter"), self.flags)
        self.assertFalse(lints(row))
        lp = self.launcher("gg", cmd="bench -t 2", cls="gpu", extra="--no-fold-siblings")
        row = rf.publish(self.spec("gg", lp, lane="gpu", regions="mi210_0,184-191"), self.flags)
        self.assertFalse(lints(row))


if __name__ == "__main__":
    unittest.main()
