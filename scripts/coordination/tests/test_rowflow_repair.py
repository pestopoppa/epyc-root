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


GOOD_BOX = ("- [ ] **T-1** [inference] Measure Qwen3-8B Q4_K_M decode t/s on the v10 production build, CPU quarter Q0; "
            "keep if t/s >= 10; est 600 s from run r1; stop rule: stop on answer or futility.")


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = pr.main(argv)
    return rc, out.getvalue()


class RepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()
        os.makedirs(os.path.join(cls.fx.root, "repo", "handoffs", "active"), exist_ok=True)
        with open(os.path.join(cls.fx.root, "repo", "handoffs", "active", "test.md"), "w") as f:
            f.write(GOOD_BOX + "\n")
        pr.REPO = os.path.join(cls.fx.root, "repo")

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
        self.assertNotIn("keep", spec)   # operator 2026-11-03: the lint no longer narrows an empty keep to the result file
        self.assertFalse(any(n.startswith("keep=") for n in notes), notes)
        self.assertEqual(spec["kind"], "compute")
        self.assertTrue(any(n.startswith("result_path=") for n in notes), notes)
        # no declared format -> one-line refusal, nothing published
        with self.assertRaises(rf.Refused):
            pr.lint(fx.spec(rid, d, result_path=os.path.join(d, "out", "RUN_COMPLETE.txt")))
        # the CLI path: lint + rowflow.publish; LINT lines precede PUBLISHED
        sp = os.path.join(d, "spec.json")
        rf.atomic_json(sp, fx.spec(rid, d, result_path=os.path.join(d, "out", "COMPLETE.json"), result_format="json"))
        rc, out = run([sp, "--flags", fx.flags])
        self.assertEqual(rc, 0, out)  # operator 2026-11-05: the CLI queues the smoke for the keeper and returns at once
        self.assertIn("LINT result_path=", out)
        self.assertIn("queued for smoke", out)
        self.assertTrue(os.path.exists(rf.smoke_queued_path(fx.flags, rid)))
        rc, out = run(["--run-smoke", rid, "--regions", "0-3", "--flags", fx.flags])   # the keeper's placed runner
        self.assertEqual(rc, 1, out)  # the job writes results.jsonl, not RESULT.json: the smoke FAILs
        self.assertIn("SMOKE FAIL " + rid, out)
        self.assertFalse(os.path.exists(rf.smoke_queued_path(fx.flags, rid)), "a FAIL dequeues")
        self.assertNotIn(rid, rf.rows(fx.flags))  # ws58: ready/<id>.json survives only a smoke PASS
        self.assertEqual(rf.load_json(pr.unpublished_path(fx.flags, rid))["result_path"], os.path.join(d, "out", "RESULT.json"))

    def test_01b_handoff_task_must_name_an_active_handoff_and_smoke_is_the_dry_run(self):
        fx = self.fx
        rid = "t-owner-20261102"
        d = fx.job(rid)
        sp = os.path.join(d, "spec.json")
        rf.atomic_json(sp, fx.spec(rid, d, handoff_task="FILLERS"))
        rc, out = run([sp, "--flags", fx.flags])
        self.assertEqual(rc, 2, out)
        self.assertIn("<file>.md:<ROW-ID>", out)
        self.assertNotIn(rid, rf.rows(fx.flags))
        rf.atomic_json(sp, fx.spec(rid, d))
        rc, out = run([sp, "--flags", fx.flags])
        self.assertEqual(rc, 0, out)
        self.assertIn("queued for smoke", out)
        self.assertNotIn(rid, rf.rows(fx.flags), "unpublished until the keeper's smoke PASSes")
        rc, out = run(["--run-smoke", rid, "--regions", "0-3", "--flags", fx.flags])
        self.assertEqual(rc, 0, out)
        self.assertIn("SMOKE PASS", out)
        self.assertFalse(os.path.exists(rf.smoke_queued_path(fx.flags, rid)))
        self.assertEqual(rf.status(fx.flags, rid)["state"], "grantable", "a smoke PASS readies the row at once")
        self.assertEqual([g for g in os.listdir(os.path.join(fx.flags, "grants")) if rid in g], [], "no dry-run grant")
        bad = "t-crash-20261102"
        d2 = fx.job(bad, "crash")
        rf.atomic_json(sp, fx.spec(bad, d2))
        rc, out = run([sp, "--flags", fx.flags, "--smoke-now"])   # --smoke-now: the old immediate path, still one line
        if "queued for smoke" in out:   # no free cores on this host right now: the keeper's runner takes it
            rc, out = run(["--run-smoke", bad, "--regions", "0-3", "--flags", fx.flags])
            self.assertEqual(rc, 1, out)
        else:
            self.assertEqual(rc, 2, out)
        self.assertIn("(log: " + os.path.join(rf.dry_dir(fx.flags, bad), "launcher.out"), out)  # one line; the log stays on disk
        self.assertNotIn("launcher_out_tail", out)
        self.assertNotIn(bad, rf.rows(fx.flags))  # ws58: a failed smoke leaves no ready/ manifest
        self.assertTrue(rf.fail_paths(fx.flags, bad))

    def test_02_class1_fail_is_repaired_and_republished(self):
        fx = self.fx
        rid = "t-repair-20261101"
        d = fx.job(rid)  # writes out/results.jsonl, exits 0 after 10 units
        marker = os.path.join(d, "out", "run.complete")
        rf.publish(fx.spec(rid, d, result_path=marker, dryrun_timeout_s=60, admission_class="diagnostic"), fx.flags)  # pre-lint row, as legacy rows were
        v, msg = rf.dryrun_run(fx.flags, rid, "0-23")
        self.assertEqual(v, "FAIL", msg)
        self.assertIn("no unit in " + marker + " (", msg)  # the phrase repair's _UNIT_RE parses
        old_sha = rf.row_sha(fx.flags, rid)
        rc, out = run(["--repair", rid, "--flags", fx.flags])
        self.assertEqual(rc, 0, out)
        self.assertIn(f"REPAIRED {rid} -> {rid}: result_path", out)
        row = rf.rows(fx.flags)[rid]
        self.assertEqual(row["result_path"], os.path.join(d, "out", "results.jsonl"))
        self.assertEqual(row["result_format"], "jsonl")
        self.assertEqual(row["admission_class"], "diagnostic")
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
        rc, out = run(["--repair", "t-owner-20261102", "--flags", fx.flags])
        self.assertEqual(rc, 2, out)


if __name__ == "__main__":
    unittest.main()


class PrepInGrantTests(unittest.TestCase):
    """Operator 23:55Z: weight hashing / single-core prep inside the grant is flagged at publish; operator 2026-11-03:
    a WARNING recorded in publish_warnings, never a refusal."""

    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_refuses_hash_and_prep_accepts_clean(self):
        fx = self.fx
        rid = "t-prep-20261101"
        d = fx.job(rid)
        self.assertIsNone(pr.prep_in_grant(os.path.join(d, "launch.sh")), "the fixture launcher is clean")
        pr.lint(fx.spec(rid, d))  # clean launcher passes the lint
        # 1. hashing the model inside --cmd (the sr6 shape, even when guarded by FILLER_DRYRUN)
        bad = os.path.join(d, "launch-hash.sh")
        src = open(os.path.join(d, "launch.sh")).read()
        open(bad, "w").write(src.replace("--cmd \"", "--cmd \"if [ \\\"${FILLER_DRYRUN:-0}\\\" != 1 ]; then sha256sum -c --quiet $D/FULL-MODEL.sha256; fi && ", 1))
        self.assertIn("sha256sum", open(bad).read())
        hit = pr.prep_in_grant(bad)
        self.assertIsNotNone(hit)
        spec = fx.spec(rid, d, launcher=bad)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            pr.lint(spec)  # warns, does not refuse
            pr.lint(spec)  # idempotent: one warning recorded, not two
        self.assertEqual(len(spec["publish_warnings"]), 1, spec)
        self.assertIn("verify/prepare inputs once before publishing, not inside the grant", spec["publish_warnings"][0])
        self.assertIn("sha256sum", spec["publish_warnings"][0])
        self.assertEqual(len(out.getvalue().strip().splitlines()), 2)
        self.assertTrue(all(l.startswith("WARN prep-in-grant: ") for l in out.getvalue().strip().splitlines()))
        # 2. single-core prep in a script the launcher executes ($D/prep.py referenced from the launcher)
        open(os.path.join(d, "prep.py"), "w").write("ids = tokenizer.encode(text)\n")
        bad2 = os.path.join(d, "launch-tok.sh")
        open(bad2, "w").write(src.replace("--cmd \"", "--cmd \"/usr/bin/python3 $D/prep.py && ", 1))
        hit = pr.prep_in_grant(bad2)
        self.assertIsNotNone(hit)
        self.assertTrue(hit[0].endswith("prep.py"), hit)
        spec2 = fx.spec(rid, d, launcher=bad2)
        with contextlib.redirect_stdout(io.StringIO()):
            pr.lint(spec2)
        self.assertIn("prep.py", spec2["publish_warnings"][0])
        # a comment is not an offence
        ok = os.path.join(d, "launch-comment.sh")
        open(ok, "w").write("# sha256sum -c FULL-MODEL.sha256 was done at prep time\n" + src)
        self.assertIsNone(pr.prep_in_grant(ok))
