"""Disk guards 2026-11-21: publish_row warns when scratch_gb is undeclared; the keeper logs SCRATCH-OVER (log-only)."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_COORD = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_COORD, 'rowflow'))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
sys.path.insert(0, _HERE)
from test_rowflow import Fixture  # noqa: E402


class LintTests(unittest.TestCase):
    def test_warns_without_scratch_gb_and_records_it(self):
        spec = {"id": "x", "regions": "q0", "result_path": "/x/RESULT.json", "kind": "compute"}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            pr.lint(spec)
        self.assertIn("no-scratch-gb", buf.getvalue())
        self.assertTrue(any("no-scratch-gb" in w for w in spec["publish_warnings"]))

    def test_declared_scratch_gb_is_silent_and_a_spec_key(self):
        spec = {"id": "x", "regions": "q0", "result_path": "/x/RESULT.json", "kind": "compute", "scratch_gb": 12}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            pr.lint(spec)
        self.assertNotIn("no-scratch-gb", buf.getvalue())
        self.assertIn("scratch_gb", pr.SPEC_KEYS)


class PublishTests(unittest.TestCase):
    def test_scratch_gb_lands_in_the_manifest(self):
        fx = Fixture()
        try:
            d = fx.job("scratchgb-r2")
            row = rf.publish(fx.spec("scratchgb-r2", d, scratch_gb=7.5), fx.flags)
            self.assertEqual(row["scratch_gb"], 7.5)
        finally:
            fx.cleanup()


class OverTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="so-")
        os.makedirs(os.path.join(self.d, "ready"))
        self.root = os.path.join(self.d, "scratch")
        os.makedirs(self.root)
        self.lines = []

    def manifest(self, rid, **kw):
        with open(os.path.join(self.d, "ready", rid + ".json"), "w") as fh:
            json.dump(dict({"id": rid, "scratch_root": self.root}, **kw), fh)

    def run_it(self, gb, now, rid="r1"):
        return rf.scratch_over(self.d, [{"id": rid}], self.lines.append, now=now, du_gb=lambda p: gb)

    def test_default_40g_and_declared_cap(self):
        self.manifest("r1")
        self.assertEqual(self.run_it(39.9, 1000), [])
        self.assertEqual(self.run_it(41.0, 2000), [("r1", 41.0)])
        self.assertIn("SCRATCH-OVER r1 41.0G", self.lines[-1])
        self.manifest("r2", scratch_gb=5)
        self.assertEqual(self.run_it(6.0, 2000, rid="r2"), [("r2", 6.0)])

    def test_throttled_and_regrow_only_and_never_kills(self):
        self.manifest("r1")
        self.assertEqual(len(self.run_it(50, 1000)), 1)
        self.assertEqual(self.run_it(60, 1100), [])      # within SCRATCH_OVER_EVERY_S
        self.assertEqual(self.run_it(52, 2000), [])      # grew < 5 GB since the last line
        self.assertEqual(len(self.run_it(56, 3000)), 1)  # grew >= 5 GB
        self.assertTrue(os.path.isdir(self.root))        # log only: nothing touched


if __name__ == "__main__":
    unittest.main()
