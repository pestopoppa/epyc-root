#!/usr/bin/env python3
"""BRF-T6-1 (D6 staged): publish_row binds `task_lint.py publish` to the task box handoff_task names. A row is refused
before any smoke when its box fails the inference identity (c, including a provisional estimate without a bounded pilot),
the stop rule (s), carries NEEDS-* or is a non-inference payload (a plain numeric est passes: ws58 2026-11-02); handoff_task must name the task, which must be an open box."""
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

    def test_good_box_passes(self):
        self.lint("T-1")
        self.lint("3")  # line number form

    def test_stop_rule_required(self):
        self.refused("T-NOSTOP", "stop rule")

    def test_non_inference_payload_refused(self):
        self.refused("T-NONINF", "non-inference payload refused")

    def test_plain_numeric_estimate_passes(self):
        # ws58 2026-11-02: the run-cited estimate rule (4d6ea0b3d) was not in the plan; a plain numeric est passes
        self.lint("T-NOCITE")

    def test_refusal_names_exact_missing_fields(self):
        with self.assertRaises(rf.Refused) as cm:
            self.lint("T-NOID")
        msg = str(cm.exception)
        for f in ("model:", "quant_build:", "rule:", "region:"):
            self.assertIn(f, msg)
        self.assertIn("h.md:", msg)

    def test_provisional_estimate_needs_bounded_pilot(self):
        self.lint("T-PILOT")
        self.refused("T-PROV", "identity incomplete")

    def test_identity_incomplete_refused(self):
        self.refused("T-NOID", "identity incomplete")

    def test_needs_tag_refused(self):
        self.refused("T-OWNER", "NEEDS tags present")

    def test_task_must_be_named_found_and_open(self):
        self.refused("", "names no task")
        self.refused("T-404", "no checkbox **T-404**")
        self.refused("T-DONE", "not open")

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
