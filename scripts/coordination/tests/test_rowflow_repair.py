#!/usr/bin/env python3
"""CAF-4: publish_row.py spec lint + --repair. Lint rewrites a completion-marker result_path and fills derivable fields;
a class-(1) dry-run FAIL (no unit at the declared path while results.jsonl was written) is repaired and republished under
the same id with the launcher sha recorded; an unknown FAIL exits 3 and changes nothing. Temp tree via test_rowflow.Fixture."""
import contextlib
import io
import os
import sys
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TESTS)
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture  # noqa: E402


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = pr.main(argv)
    return rc, out.getvalue()


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_01_lint_rewrites_marker_and_fills_fields(self):
        fx = self.fx
        rid = "t-lint-20261101"
        d = fx.job(rid)
        spec = fx.spec(rid, d, result_path=os.path.join(d, "out", "run.complete"), result_format="jsonl")
        del spec["lane"]
        notes = pr.lint(spec)
        self.assertEqual(spec["result_path"], os.path.join(d, "out", "results.jsonl"))
        self.assertEqual(spec["lane"], "cpu")
        self.assertEqual(spec["scratch_root"], d)
        self.assertEqual(spec["keep"], ["out/results.jsonl"])
        self.assertEqual(spec["kind"], "compute")
        self.assertTrue(any(n.startswith("result_path=") for n in notes), notes)
        # no declared format -> one-line refusal, nothing published
        with self.assertRaises(rf.Refused):
            pr.lint(fx.spec(rid, d, result_path=os.path.join(d, "out", "RUN_COMPLETE.txt")))
        # the CLI path: lint + rowflow.publish; LINT lines precede PUBLISHED
        sp = os.path.join(d, "spec.json")
        rf.atomic_json(sp, fx.spec(rid, d, result_path=os.path.join(d, "out", "COMPLETE.json"), result_format="json"))
        rc, out = run([sp, "--flags", fx.flags])
        self.assertEqual(rc, 0, out)
        self.assertIn("LINT result_path=", out)
        self.assertIn("PUBLISHED " + rid, out)
        self.assertEqual(rf.rows(fx.flags)[rid]["result_path"], os.path.join(d, "out", "RESULT.json"))

    def test_02_class1_fail_is_repaired_and_republished(self):
        fx = self.fx
        rid = "t-repair-20261101"
        d = fx.job(rid)  # writes out/results.jsonl, exits 0 after 10 units
        marker = os.path.join(d, "out", "run.complete")
        rf.publish(fx.spec(rid, d, result_path=marker, dryrun_timeout_s=60), fx.flags)  # pre-lint row, as legacy rows were
        v, msg = rf.dryrun_run(fx.flags, rid, "0-23")
        self.assertEqual(v, "FAIL", msg)
        self.assertIn("before writing a unit to " + marker, msg)
        old_sha = rf.row_sha(fx.flags, rid)
        rc, out = run(["--repair", rid, "--flags", fx.flags])
        self.assertEqual(rc, 0, out)
        self.assertIn(f"REPAIRED {rid} -> {rid}: result_path", out)
        row = rf.rows(fx.flags)[rid]
        self.assertEqual(row["result_path"], os.path.join(d, "out", "results.jsonl"))
        self.assertEqual(row["result_format"], "jsonl")
        self.assertEqual(row["launcher"]["sha256"], rf.sha256(os.path.join(d, "launch.sh")))
        self.assertTrue(row["published_from"].startswith("repair:"))
        self.assertNotEqual(rf.row_sha(fx.flags, rid), old_sha)
        self.assertEqual(rf.status(fx.flags, rid)["state"], "needs-dryrun")  # the keeper re-dry-runs it; --repair did not
        self.assertFalse(os.path.exists(rf.running_path(fx.flags, rid)))

    def test_03_unknown_fail_exits_3_and_changes_nothing(self):
        fx = self.fx
        rid = "t-unknown-20261101"
        d = fx.job(rid, "crash")
        rf.publish(fx.spec(rid, d, dryrun_timeout_s=40), fx.flags)
        self.assertEqual(rf.dryrun_run(fx.flags, rid, "0-23")[0], "FAIL")
        old_sha = rf.row_sha(fx.flags, rid)
        rc, out = run(["--repair", rid, "--flags", fx.flags])
        self.assertEqual(rc, 3, out)
        self.assertTrue(out.startswith("UNKNOWN-FAILURE-CLASS job ended"), out)
        self.assertEqual(rf.row_sha(fx.flags, rid), old_sha)
        self.assertEqual(rf.status(fx.flags, rid)["state"], "failed")
        # a row with no FAIL record is refused, not "repaired"
        rc, out = run(["--repair", "t-lint-20261101", "--flags", fx.flags])
        self.assertEqual(rc, 2, out)


if __name__ == "__main__":
    unittest.main()
