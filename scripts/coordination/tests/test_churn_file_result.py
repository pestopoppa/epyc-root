#!/usr/bin/env python3
"""Tests for CAF-5 churn/file_result.py — numeric-rule filing without an agent turn.

Temp flags dir only; never touches live compute-flags or a real handoff. Stdlib unittest.
Run: python3 -W ignore -m unittest scripts.coordination.tests.test_churn_file_result
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_COORD = Path(__file__).resolve().parents[1]
for p in (str(_COORD), str(_COORD / "churn")):
    if p not in sys.path:
        sys.path.insert(0, p)

import file_result as fr  # noqa: E402

HANDOFF = "# H\n\n- [ ] **ROW-1** tune the thing\n- [ ] **ROW-2** other\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = os.path.join(self.tmp.name, "flags")
        self.lane = os.path.join(self.tmp.name, "lane")
        for d in ("ready/armed", "grants"):
            os.makedirs(os.path.join(self.flags, d))
        os.makedirs(os.path.join(self.lane, "handoffs/active"))
        Path(self.lane, "handoffs/active/h.md").write_text(HANDOFF)

    def tearDown(self):
        self.tmp.cleanup()

    def row(self, rid, rule, result, fmt="json", rc=0, armed=False, end=".ended"):
        rp = os.path.join(self.tmp.name, f"{rid}.{fmt}")
        if result is not None:
            if fmt == "jsonl":
                Path(rp).write_text("".join(json.dumps(r) + "\n" for r in result))
            else:
                Path(rp).write_text(json.dumps(result))
        man = {"schema": "epyc.row.v3", "id": rid, "owner": "t", "result_path": rp, "result_format": fmt,
               "decision_rule": rule, "handoff_task": f"handoffs/active/h.md:{rid}"}
        sub = "ready/armed" if armed else "ready"
        Path(self.flags, sub, rid + ".json").write_text(json.dumps(man))
        Path(self.flags, "grants", rid + end).write_text(f"rc={rc} time=2026-11-01T00:00:00Z reason=x\njob_id={rid}\n")

    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = fr.main(list(args) + ["--flags", self.flags, "--lane", self.lane])
        return code, out.getvalue(), err.getvalue()

    def verdict(self, rid):
        return json.loads(Path(self.flags, "filing-done", rid + ".verdict.json").read_text())

    def filed(self, rid):
        return os.path.exists(os.path.join(self.flags, "filing-done", rid + ".FILED"))


class TestFileResult(Base):
    def test_numeric_pass(self):
        self.row("ROW-1", "tps_delta >= +2% and ppl_delta <= 0.1%", {"tps_delta": 3.5, "ppl_delta": 0.05})
        code, out, _ = self.run_main("ROW-1")
        self.assertEqual(code, 0)
        v = self.verdict("ROW-1")
        self.assertEqual(v["row_verdict"], "pass")
        self.assertEqual(v["values"], {"tps_delta": 3.5, "ppl_delta": 0.05})
        self.assertEqual(v["filed_by"], "file_result.py")
        self.assertEqual(v["outcome_class"], "SCIENCE-VERDICT")
        self.assertTrue(self.filed("ROW-1"))
        self.assertIn("TICK ROW-1", out)
        self.assertIn("[no-belief: row verdict filed by file_result.py]", out)
        self.assertEqual(Path(self.lane, "handoffs/active/h.md").read_text(), HANDOFF)  # no tick without tick_text

    def test_numeric_fail_with_rc_and_armed_manifest(self):
        self.row("ROW-1", "rc == 0 and tps >= 10", {"tps": 12}, rc=1, armed=True)
        code, out, _ = self.run_main("ROW-1")
        self.assertEqual(code, 0)
        v = self.verdict("ROW-1")
        self.assertEqual(v["row_verdict"], "fail")
        self.assertEqual(v["rc"], 1)
        self.assertEqual(v["values"]["rc"], 1.0)

    def test_percent_sign_and_dotted_path(self):
        self.row("ROW-1", "(m.delta > -1.5% or m.delta == 0) and ppl != 0", {"m": {"delta": "-1.2%"}, "ppl": 3})
        code, _, _ = self.run_main("ROW-1")
        self.assertEqual(code, 0)
        self.assertEqual(self.verdict("ROW-1")["row_verdict"], "pass")

    def test_missing_metric_is_inconclusive_not_pass(self):
        self.row("ROW-1", "tps_delta >= 2 and ppl_delta <= 0.1", {"tps_delta": 9})
        code, out, _ = self.run_main("ROW-1")
        self.assertEqual(code, 0)
        v = self.verdict("ROW-1")
        self.assertEqual(v["row_verdict"], "inconclusive")
        self.assertIn("ppl_delta", v["reason"])
        self.assertEqual(v["outcome_class"], "PARTIAL-VERDICT")
        self.assertTrue(self.filed("ROW-1"))

    def test_missing_result_file_is_inconclusive(self):
        self.row("ROW-1", "tps >= 1", None)
        code, _, _ = self.run_main("ROW-1")
        self.assertEqual(code, 0)
        v = self.verdict("ROW-1")
        self.assertEqual(v["row_verdict"], "inconclusive")
        self.assertFalse(v["result_exists"])

    def test_jsonl_last_record_and_units(self):
        self.row("ROW-1", "units >= 3 and acc > 0.8", [{"acc": 0.1}, {"acc": 0.2}, {"acc": 0.9}], fmt="jsonl", end=".complete")
        code, _, _ = self.run_main("ROW-1")
        self.assertEqual(code, 0)
        v = self.verdict("ROW-1")
        self.assertEqual(v["row_verdict"], "pass")
        self.assertEqual(v["values"], {"units": 3.0, "acc": 0.9})
        self.assertEqual(v["rc"], 0)

    def test_non_numeric_rule_exits_4(self):
        self.row("ROW-1", "coherent output at 32k with no repetition; judge by eye", {"x": 1})
        code, out, _ = self.run_main("ROW-1")
        self.assertEqual(code, 4)
        self.assertTrue(out.startswith("NEEDS-AGENT-VERDICT ROW-1: coherent"))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "filing-done")))

    def test_verdict_json_applies_and_ticks(self):
        self.row("ROW-1", "judge by eye", {"x": 1}, rc=0)
        vj = os.path.join(self.tmp.name, "v.json")
        Path(vj).write_text(json.dumps({"verdict": "fail", "rationale": "repeats after 20k", "tick_text": "32k repetition seen"}))
        code, out, _ = self.run_main("ROW-1", "--verdict-json", vj)
        self.assertEqual(code, 0)
        v = self.verdict("ROW-1")
        self.assertEqual(v["row_verdict"], "fail")
        self.assertEqual(v["filed_by"], "agent")
        self.assertEqual(v["reason"], "repeats after 20k")
        self.assertTrue(self.filed("ROW-1"))
        text = Path(self.lane, "handoffs/active/h.md").read_text()
        self.assertIn("- [x] **ROW-1** tune the thing ✅", text)
        self.assertIn("32k repetition seen", text)
        self.assertIn("- [ ] **ROW-2** other", text)
        self.assertIn("TICKED ROW-1", out)

    def test_bad_verdict_json_exits_2(self):
        self.row("ROW-1", "judge by eye", {"x": 1})
        vj = os.path.join(self.tmp.name, "v.json")
        Path(vj).write_text(json.dumps({"verdict": "maybe"}))
        code, _, err = self.run_main("ROW-1", "--verdict-json", vj)
        self.assertEqual(code, 2)
        self.assertIn("bad --verdict-json", err)

    def test_dry_run_touches_nothing(self):
        self.row("ROW-1", "tps >= 1", {"tps": 5})
        code, out, _ = self.run_main("ROW-1", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("pass", out)
        self.assertIn("(dry-run)", out)
        self.assertFalse(os.path.exists(os.path.join(self.flags, "filing-done")))

    def test_missing_manifest_or_end_exits_2(self):
        code, _, err = self.run_main("NOPE")
        self.assertEqual(code, 2)
        self.assertIn("no manifest", err)
        self.row("ROW-1", "tps >= 1", {"tps": 5})
        os.remove(os.path.join(self.flags, "grants", "ROW-1.ended"))
        code, _, err = self.run_main("ROW-1")
        self.assertEqual(code, 2)
        self.assertIn(".ended|.complete", err)

    def test_parser_rejects_prose_and_accepts_rules(self):
        for ok in ("rc == 0", "a>=1 and b<2 or c!=3", "x.y.z <= +0.5%", "( a > 1 )"):
            fr.parse(ok)
        for bad in ("", "a >= b", "a > 1 and", "tps improves", "a = 1", "a > 1 andb < 2"):
            with self.assertRaises(fr.RuleError, msg=bad):
                fr.parse(bad)


if __name__ == "__main__":
    unittest.main()
