#!/usr/bin/env python3
"""BRF-T6-1 (D6 staged), RELAXED by operator decision 2026-11-03: publish_row binds `task_lint.py publish` to the task box
handoff_task names. A row is refused before any smoke ONLY when its box names no model/build identity (check c), states no
stop rule (check s), or handoff_task does not resolve to a real open task box (file-only, not found, not open). Every
other finding (NEEDS-*, metric/rule/region/estimate fields, ...) is a WARNING printed and recorded
in the row's publish_warnings; the smoke still gates every row. RTG-100 (2026-11-10): a compute row whose box is
confidently non-inference, or whose launcher runs gitnexus analyze, is refused."""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TESTS)
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture  # noqa: E402

GOOD = ("- [ ] **T-1** [inference] Measure Qwen3-8B Q4_K_M decode t/s on the v10 production build, CPU quarter Q0; "
        "keep if t/s >= 10; est 600 s from run r1; stop rule: stop on answer or futility.")
BOXES = {
    "T-1": GOOD,
    "T-NOSTOP": GOOD.replace("T-1", "T-NOSTOP").replace("; stop rule: stop on answer or futility", ""),
    "T-NONINF": "- [ ] **T-NONINF** [non-inference] Implement the scorer adapter and land its unit tests.",
    "T-NOCITE": GOOD.replace("T-1", "T-NOCITE").replace("est 600 s from run r1", "est 600 s"),
    "T-PILOT": GOOD.replace("T-1", "T-PILOT").replace("est 600 s from run r1", "est: provisional ~900 s; pilot: bounded n=6 launches/arm"),
    "T-PROV": GOOD.replace("T-1", "T-PROV").replace("est 600 s from run r1", "est: provisional"),
    "T-NOID": "- [ ] **T-NOID** [inference] Measure decode t/s; est 600 s from run r1; stop rule: stop on futility.",
    "T-OWNER": GOOD.replace("T-1", "T-OWNER") + " NEEDS-OWNER",
    "T-PEND": GOOD.replace("T-1", "T-PEND") + " The operator must decide whether to adopt it.",
    "T-HOLD": GOOD.replace("T-1", "T-HOLD") + " STANDING CONSTRAINT: keep off.",
    "T-ROLL": GOOD.replace("T-1", "T-ROLL") + " [roll-up]",
    "T-DONE": GOOD.replace("- [ ] **T-1**", "- [x] **T-DONE**"),
}


class PublishLintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = tempfile.mkdtemp(prefix="brf-t6-")
        os.makedirs(os.path.join(cls.repo, "handoffs", "active"))
        with open(os.path.join(cls.repo, "handoffs", "active", "h.md"), "w") as f:
            f.write("# h\n\n" + "\n\n".join(BOXES.values()) + "\n")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo, ignore_errors=True)

    def lint(self, task):
        pr.check_task_lint({"handoff_task": f"h.md:{task}" if task else "h.md"}, self.repo)

    def refused(self, task, needle):
        with self.assertRaises(rf.Refused) as cm:
            self.lint(task)
        self.assertIn(needle, str(cm.exception))

    def warned(self, task, needle):
        spec = {"handoff_task": f"h.md:{task}"}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            w = pr.check_task_lint(spec, self.repo)   # must NOT raise
        self.assertTrue(any(needle in x for x in w), w)
        self.assertEqual(spec["publish_warnings"], w, "recorded for the row's publish record")
        self.assertIn("WARN task_lint", out.getvalue())

    def test_good_box_passes_without_warnings(self):
        spec = {"handoff_task": "h.md:T-1"}
        self.assertEqual(pr.check_task_lint(spec, self.repo), [])
        self.assertNotIn("publish_warnings", spec)
        self.lint("3")  # line number form

    def test_stop_rule_required(self):
        self.refused("T-NOSTOP", "stop rule")

    def test_identity_missing_refused_and_names_fields(self):
        with self.assertRaises(rf.Refused) as cm:
            self.lint("T-NOID")
        msg = str(cm.exception)
        for f in ("model:", "quant_build:"):
            self.assertIn(f, msg)
        self.assertIn("identity incomplete", msg)
        self.assertIn("h.md:", msg)

    def test_non_inference_payload_refused_as_compute_row(self):
        # RTG-100 (operator 2026-11-10): an explicitly non-inference box cannot be a compute row
        self.refused("T-NONINF", "non-inference payload cannot be a compute row")

    def test_non_inference_payload_allowed_for_non_compute_kind(self):
        spec = {"handoff_task": "h.md:T-NONINF", "kind": "non-inference"}
        with contextlib.redirect_stdout(io.StringIO()):
            w = pr.check_task_lint(spec, self.repo)
        self.assertTrue(any("non-inference payload" in x for x in w), w)

    def test_gitnexus_launcher_refused_as_compute_row(self):
        lp = os.path.join(self.repo, "gx.sh")
        with open(lp, "w") as f:
            f.write("#!/bin/bash\n# gitnexus analyze is mentioned in a comment only\ncd /x && gitnexus analyze --workers 1\n")
        self.assertIsNotNone(pr.noninference_payload(lp))
        with self.assertRaises(rf.Refused) as cm:
            pr.lint({"launcher": lp})
        self.assertIn("non-inference payload", str(cm.exception))
        with open(lp, "w") as f:
            f.write("#!/bin/bash\n# gitnexus analyze\nllama-bench -m m.gguf\n")
        self.assertIsNone(pr.noninference_payload(lp))

    def test_needs_tag_only_warns(self):
        self.warned("T-OWNER", "NEEDS tags present")

    def test_estimate_and_metric_fields_only_warn(self):
        self.warned("T-PROV", "estimate")        # bare provisional estimate: a warning now
        self.lint("T-NOCITE")                     # plain numeric est passes
        self.lint("T-PILOT")

    def test_pending_choice_and_standing_hold_and_rollup_only_warn(self):
        self.warned("T-PEND", "pending operator choice")
        self.warned("T-HOLD", "standing constraint")
        self.warned("T-ROLL", "roll-up")

    def test_task_must_be_named_found_and_open(self):
        self.refused("", "names no task")
        self.refused("T-404", "no checkbox **T-404**")
        self.refused("T-DONE", "not open")

    def test_main_warns_records_and_still_runs_the_smoke(self):
        fx = Fixture()
        try:
            os.makedirs(os.path.join(fx.root, "repo", "handoffs", "active"))
            shutil.copy(os.path.join(self.repo, "handoffs", "active", "h.md"), os.path.join(fx.root, "repo", "handoffs", "active", "h.md"))
            old, pr.REPO = pr.REPO, os.path.join(fx.root, "repo")
            rid = "t-warn-20261103"
            d = fx.job(rid)
            sp = os.path.join(d, "spec.json")
            rf.atomic_json(sp, fx.spec(rid, d, handoff_task="h.md:T-OWNER"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                try:
                    pr.main([sp, "--flags", fx.flags])
                except Exception:   # the smoke may fail in this fixture; what matters is that lint did not refuse
                    pass
            text = out.getvalue()
            self.assertIn("WARN task_lint", text)
            self.assertNotIn("task_lint publish REFUSED", text)
            row = rf.load_json(rf.ready_path(fx.flags, rid)) or rf.load_json(os.path.join(rf.dry_dir(fx.flags, rid), "unpublished.json"))
            self.assertIsNotNone(row, text)
            self.assertTrue(any("NEEDS tags" in w for w in row["publish_warnings"]), row.get("publish_warnings"))
        finally:
            pr.REPO = old
            fx.cleanup()

    def test_main_refuses_before_smoke(self):
        fx = Fixture()
        try:
            os.makedirs(os.path.join(fx.root, "repo", "handoffs", "active"))
            shutil.copy(os.path.join(self.repo, "handoffs", "active", "h.md"), os.path.join(fx.root, "repo", "handoffs", "active", "h.md"))
            old, pr.REPO = pr.REPO, os.path.join(fx.root, "repo")
            rid = "t-lint-20261102"
            d = fx.job(rid)
            sp = os.path.join(d, "spec.json")
            rf.atomic_json(sp, fx.spec(rid, d, handoff_task="h.md:T-NOSTOP"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = pr.main([sp, "--flags", fx.flags])
            self.assertEqual(rc, 2, out.getvalue())
            self.assertIn("task_lint publish REFUSED", out.getvalue())
            self.assertNotIn(rid, rf.rows(fx.flags))
            self.assertFalse(os.path.exists(rf.dry_dir(fx.flags, rid)) and os.listdir(rf.dry_dir(fx.flags, rid)), "no smoke ran")
        finally:
            pr.REPO = old
            fx.cleanup()


if __name__ == "__main__":
    unittest.main()
