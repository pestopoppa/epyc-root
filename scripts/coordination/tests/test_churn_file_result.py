#!/usr/bin/env python3
"""Tests for CAF-5 churn/file_result.py — numeric-rule filing without an agent turn.

Temp flags dir only; never touches live compute-flags or a real handoff. Stdlib unittest.
Run: python3 -W ignore -m unittest scripts.coordination.tests.test_churn_file_result
"""
import io
import builtins
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

_COORD = Path(__file__).resolve().parents[1]
for p in (str(_COORD), str(_COORD / "churn"), str(_COORD / "rowflow")):
    if p not in sys.path:
        sys.path.insert(0, p)

import file_result as fr  # noqa: E402
import reclaim_row  # noqa: E402
import publish_row as publisher  # noqa: E402

HANDOFF = "# H\n\n- [ ] **akx-lb3-2-cv5-pair-r2** tune the thing\n- [ ] **pf1-expand-r2** other\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = os.path.join(self.tmp.name, "flags")
        self.lane = os.path.join(self.tmp.name, "lane")
        for d in ("ready/armed", "grants"):
            os.makedirs(os.path.join(self.flags, d))
        os.makedirs(os.path.join(self.lane, "handoffs/active"))
        Path(self.lane, "handoffs/active/h.md").write_text(HANDOFF)
        # RECLAIM-AT-FILING: scratch roots live under a temp tmp root; reclaim is recorded, never run here
        # tmp root = parent of the temp dir, so scratch_root = the temp dir (which holds the result files)
        self.tmproot = os.path.dirname(os.path.realpath(self.tmp.name))
        self._env = patch.dict(os.environ, {"RECLAIM_TMP_ROOT": self.tmproot})
        self._env.start()
        self.reclaims = []
        self._rc = patch.object(reclaim_row, "main", lambda argv: self.reclaims.append(list(argv)) or 0)
        self._rc.start()

    def tearDown(self):
        self._rc.stop()
        self._env.stop()
        self.tmp.cleanup()

    def row(self, rid, rule, result, fmt="json", rc=0, armed=False, end=".ended"):
        rp = os.path.join(self.tmp.name, f"{rid}.{fmt}")
        if result is not None:
            if fmt == "jsonl":
                Path(rp).write_text("".join(json.dumps(r) + "\n" for r in result))
            else:
                Path(rp).write_text(json.dumps(result))
        man = {"schema": "epyc.row.v3", "id": rid, "owner": "t", "result_path": rp, "result_format": fmt,
               "decision_rule": rule, "handoff_task": f"handoffs/active/h.md:{rid}",
               "scratch_root": os.path.realpath(self.tmp.name)}
        sub = "ready/armed" if armed else "ready"
        Path(self.flags, sub, rid + ".json").write_text(json.dumps(man))
        Path(self.flags, "grants", rid + end).write_text(f"rc={rc} time=2026-11-01T00:00:00Z reason=x\njob_id={rid}\n")

    def smoke_identity(self, rid):
        """Real launcher + engine files bound by sha256, as publish_row binds them (the old fixture used bare hashes).
        Rewrites the published manifest and returns (row, pass_receipt) for a smoke that completed the whole job."""
        sc = os.path.realpath(self.tmp.name)
        engine, checker, launcher = (Path(sc, n) for n in ("filler_run15.sh", "checker.py", "launch.sh"))
        engine.write_text("#!/bin/bash\nexit 99 # MUST NEVER RUN\n")
        checker.write_text("import sys\nsys.exit(0)\n")
        ready = Path(self.flags, "ready", rid + ".json")
        row = json.loads(ready.read_text())
        launcher.write_text(f'#!/bin/bash\nexec bash {engine} --id {rid} --class cpu --min-window 300 --stop {sc}/STOP '
                            f'--workdir {sc} --cmd "false" --complete-cmd "python3 {checker} {row["result_path"]}"\n')
        row.update(launcher={"path": str(launcher), "sha256": publisher.rf.sha256(launcher)},
                   engine={"path": str(engine), "sha256": publisher.rf.sha256(engine)})
        ready.write_text(json.dumps(row))
        passed = {"id": rid, "job_complete": True, "launcher_sha256": row["launcher"]["sha256"],
                  "engine_sha256": row["engine"]["sha256"], "result_format": row["result_format"],
                  "result_path": row["result_path"]}
        return row, passed

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
    def file_agent_tick(self, task):
        self.row("akx-lb3-2-cv5-pair-r2", "judge by eye", {"x": 1})
        manifest = Path(self.flags, "ready/akx-lb3-2-cv5-pair-r2.json")
        row = json.loads(manifest.read_text())
        row["handoff_task"] = task
        manifest.write_text(json.dumps(row))
        verdict = Path(self.tmp.name, "agent-verdict.json")
        verdict.write_text(json.dumps({"verdict": "pass", "rationale": "observed",
                                       "tick_text": "scoped native evidence"}))
        return self.run_main("akx-lb3-2-cv5-pair-r2", "--verdict-json", str(verdict))

    def test_basename_task_ticks_active_handoff_not_same_named_root_file(self):
        root_file = Path(self.lane, "h.md")
        root_file.write_text(HANDOFF)
        code, _, err = self.file_agent_tick("h.md:akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0, err)
        active = Path(self.lane, "handoffs/active/h.md").read_text()
        self.assertIn("- [x] **akx-lb3-2-cv5-pair-r2**", active)
        self.assertIn("- [ ] **pf1-expand-r2**", active)
        self.assertEqual(root_file.read_text(), HANDOFF)
        self.assertTrue(self.filed("akx-lb3-2-cv5-pair-r2"))

    def test_qualified_task_keeps_its_file_and_token(self):
        code, _, err = self.file_agent_tick("handoffs/active/h.md:pf1-expand-r2")
        self.assertEqual(code, 0, err)
        active = Path(self.lane, "handoffs/active/h.md").read_text()
        self.assertIn("- [ ] **akx-lb3-2-cv5-pair-r2**", active)
        self.assertIn("- [x] **pf1-expand-r2**", active)
        self.assertTrue(self.filed("akx-lb3-2-cv5-pair-r2"))

    def test_tick_rejects_absolute_and_parent_traversal_paths(self):
        outside = Path(self.tmp.name, "outside.md")
        outside.write_text(HANDOFF)
        for path in (str(outside), "../outside.md", "handoffs/active/../../../outside.md"):
            with self.subTest(path=path):
                code, _, err = self.file_agent_tick(path + ":akx-lb3-2-cv5-pair-r2")
                self.assertEqual(code, 5)
                self.assertIn("tick failed", err)
                self.assertFalse(self.filed("akx-lb3-2-cv5-pair-r2"))
                self.assertEqual(outside.read_text(), HANDOFF)
                self.assertEqual(Path(self.lane, "handoffs/active/h.md").read_text(), HANDOFF)

    def test_tick_rejects_symlink_escape_without_receipt(self):
        outside = Path(self.tmp.name, "outside.md")
        outside.write_text(HANDOFF)
        Path(self.lane, "handoffs/active/escape.md").symlink_to(outside)
        code, _, err = self.file_agent_tick("escape.md:akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 5)
        self.assertIn("outside the lane", err)
        self.assertFalse(self.filed("akx-lb3-2-cv5-pair-r2"))
        self.assertEqual(outside.read_text(), HANDOFF)

    def test_completed_smoke_identity_mismatch_unpublishes(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": True})
        ready = Path(self.flags, "ready", "akx-lb3-2-cv5-pair-r2.json")
        row = json.loads(ready.read_text()); row["id"] = "OTHER"
        dry = Path(self.flags, "dryrun", "akx-lb3-2-cv5-pair-r2"); dry.mkdir(parents=True)
        (dry / "PASS.json").write_text(json.dumps({"id": "akx-lb3-2-cv5-pair-r2", "job_complete": True}))
        with self.assertRaises(publisher.rf.Refused):
            publisher.file_if_complete(self.flags, "akx-lb3-2-cv5-pair-r2", row)
        self.assertFalse(ready.exists())
        self.assertTrue((dry / "unpublished.json").exists())
        self.assertFalse(Path(self.flags, "grants", "akx-lb3-2-cv5-pair-r2.complete").exists())

    def test_missing_completed_smoke_result_never_leaves_ready(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": True})
        ready = Path(self.flags, "ready", "akx-lb3-2-cv5-pair-r2.json")
        row = json.loads(ready.read_text())
        dry = Path(self.flags, "dryrun", "akx-lb3-2-cv5-pair-r2"); dry.mkdir(parents=True)
        (dry / "PASS.json").write_text(json.dumps({"id": "akx-lb3-2-cv5-pair-r2", "job_complete": True,
                                                  "result_path": str(dry / "missing.json")}))
        with self.assertRaises(publisher.rf.Refused):
            publisher.file_if_complete(self.flags, "akx-lb3-2-cv5-pair-r2", row)
        self.assertFalse(ready.exists())
        self.assertEqual(json.loads((dry / "unpublished.json").read_text()), row)
        self.assertFalse(Path(self.flags, "grants", "akx-lb3-2-cv5-pair-r2.complete").exists())

    def test_post_completion_copy_or_terminal_failure_never_leaves_ready(self):
        for rid, fail_at in (("stt5-whisper-cpu-copy-r1-20261105", "archive"), ("stt5-whisper-cpu-term-r1-20261105", "terminal")):
            with self.subTest(fail_at=fail_at):
                self.row(rid, "rc == 0", {"ok": True})
                ready = Path(self.flags, "ready", rid + ".json")
                row, passed = self.smoke_identity(rid)
                row = json.loads(ready.read_text())
                dry = Path(self.flags, "dryrun", rid); dry.mkdir(parents=True)
                (dry / "PASS.json").write_text(json.dumps(passed))
                Path(self.flags, "grants", rid + ".ended").unlink()
                if fail_at == "archive":
                    failure = patch.object(publisher.rf, "atomic_json", side_effect=OSError("archive failed"))
                else:
                    real_open = builtins.open
                    def fail_complete(path, *args, **kwargs):
                        if str(path).endswith(rid + ".complete.tmp"):
                            raise OSError("terminal write failed")
                        return real_open(path, *args, **kwargs)
                    failure = patch("builtins.open", side_effect=fail_complete)
                with failure, self.assertRaises(OSError):
                    publisher.file_if_complete(self.flags, rid, row)
                self.assertFalse(ready.exists())
                self.assertEqual(json.loads((dry / "unpublished.json").read_text())["id"], rid)
                self.assertEqual((dry / "completed-manifest.json").exists(), fail_at == "terminal")
                self.assertFalse(Path(self.flags, "grants", rid + ".complete").exists())

    def test_archive_failure_unpublishes_without_creating_terminal_grants(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": True})
        ready = Path(self.flags, "ready", "akx-lb3-2-cv5-pair-r2.json")
        row, passed = self.smoke_identity("akx-lb3-2-cv5-pair-r2")
        dry = Path(self.flags, "dryrun", "akx-lb3-2-cv5-pair-r2"); dry.mkdir(parents=True)
        (dry / "PASS.json").write_text(json.dumps(passed))
        Path(self.flags, "grants", "akx-lb3-2-cv5-pair-r2.ended").unlink()
        with patch.object(publisher.rf, "atomic_json", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                publisher.file_if_complete(self.flags, "akx-lb3-2-cv5-pair-r2", row)
        self.assertFalse(ready.exists())
        self.assertEqual(json.loads((dry / "unpublished.json").read_text()), row)
        self.assertFalse(Path(self.flags, "grants", "akx-lb3-2-cv5-pair-r2.complete").exists())

    def test_queued_smoke_completion_archives_and_cannot_be_regranted(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": True})
        ready = Path(self.flags, "ready", "akx-lb3-2-cv5-pair-r2.json")
        row = json.loads(ready.read_text())
        row, passed = self.smoke_identity("akx-lb3-2-cv5-pair-r2")
        dry = Path(self.flags, "dryrun", "akx-lb3-2-cv5-pair-r2"); dry.mkdir(parents=True)
        (dry / "GPU-SMOKE-QUEUED.json").write_text(json.dumps({"regions": "mi210_0,184-191"}))
        (dry / "PASS.json").write_text(json.dumps(passed))
        with patch.object(publisher, "run_smoke", return_value=("PASS", "complete")):
            self.assertEqual(publisher.run_gpu_queue(self.flags), 1)
        self.assertFalse(ready.exists())
        self.assertFalse((dry / "GPU-SMOKE-QUEUED.json").exists())
        archived = json.loads((dry / "completed-manifest.json").read_text())
        self.assertEqual(json.loads((dry / "published-manifest.json").read_text()), row)
        self.assertEqual(archived["declared_result_path"], row["result_path"])
        self.assertEqual(archived["id"], row["id"])
        self.assertEqual(self.run_main("akx-lb3-2-cv5-pair-r2")[0], 0)

    def test_completed_smoke_archives_manifest_and_files_without_ready(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": True})
        ready = Path(self.flags, "ready", "akx-lb3-2-cv5-pair-r2.json")
        row = json.loads(ready.read_text())
        row, passed = self.smoke_identity("akx-lb3-2-cv5-pair-r2")
        dry = Path(self.flags, "dryrun", "akx-lb3-2-cv5-pair-r2"); dry.mkdir(parents=True)
        (dry / "PASS.json").write_text(json.dumps(passed))
        self.assertTrue(publisher.file_if_complete(self.flags, "akx-lb3-2-cv5-pair-r2", row))
        self.assertFalse(ready.exists())
        archived = json.loads((dry / "completed-manifest.json").read_text())
        self.assertEqual(json.loads((dry / "published-manifest.json").read_text()), row)
        self.assertEqual(archived["declared_result_path"], row["result_path"])
        self.assertEqual(archived["id"], row["id"])
        code, _, err = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.verdict("akx-lb3-2-cv5-pair-r2")["row_verdict"], "pass")
        self.assertEqual(self.verdict("akx-lb3-2-cv5-pair-r2")["manifest"], str(dry / "completed-manifest.json"))
        self.assertTrue(self.filed("akx-lb3-2-cv5-pair-r2"))

    def test_completed_manifest_fallback_refuses_unmatched_or_nonterminal_receipts(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": True})
        ready = Path(self.flags, "ready", "akx-lb3-2-cv5-pair-r2.json")
        row = json.loads(ready.read_text()); ready.unlink()
        row.update(launcher={"sha256": "a" * 64}, engine={"sha256": "b" * 64})
        dry = Path(self.flags, "dryrun", "akx-lb3-2-cv5-pair-r2"); dry.mkdir(parents=True)
        (dry / "completed-manifest.json").write_text(json.dumps(row))
        receipt = {"id": "akx-lb3-2-cv5-pair-r2", "job_complete": True, "launcher_sha256": "a" * 64,
                   "engine_sha256": "b" * 64, "result_format": "json"}
        (dry / "PASS.json").write_text(json.dumps(receipt))
        self.assertEqual(self.run_main("akx-lb3-2-cv5-pair-r2")[0], 2)  # .ended alone is not enough
        Path(self.flags, "grants", "akx-lb3-2-cv5-pair-r2.complete").write_text("complete\n")
        for mutation in ({"job_complete": False}, {"id": "OTHER"}, {"launcher_sha256": "c" * 64},
                         {"engine_sha256": "c" * 64}, {"result_format": "jsonl"}):
            (dry / "PASS.json").write_text(json.dumps(dict(receipt, **mutation)))
            self.assertEqual(self.run_main("akx-lb3-2-cv5-pair-r2")[0], 2, mutation)
            self.assertFalse(self.filed("akx-lb3-2-cv5-pair-r2"))

    def test_numeric_pass(self):
        self.row("akx-lb3-2-cv5-pair-r2", "tps_delta >= +2% and ppl_delta <= 0.1%", {"tps_delta": 3.5, "ppl_delta": 0.05})
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0)
        v = self.verdict("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(v["row_verdict"], "pass")
        self.assertEqual(v["values"], {"tps_delta": 3.5, "ppl_delta": 0.05})
        self.assertEqual(v["filed_by"], "file_result.py")
        self.assertEqual(v["outcome_class"], "SCIENCE-VERDICT")
        self.assertTrue(self.filed("akx-lb3-2-cv5-pair-r2"))
        self.assertIn("SUGGESTED-TICK akx-lb3-2-cv5-pair-r2", out)
        self.assertIn("[no-belief: row verdict filed by file_result.py]", out)
        self.assertEqual(Path(self.lane, "handoffs/active/h.md").read_text(), HANDOFF)  # no tick without tick_text

    def test_no_tick_written_prints_suggested_tick_never_bare_tick(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": 1})
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0)
        self.assertIn("SUGGESTED-TICK akx-lb3-2-cv5-pair-r2", out)
        self.assertFalse([l for l in out.splitlines() if l.startswith("TICK ")])
        self.assertEqual(Path(self.lane, "handoffs/active/h.md").read_text(), HANDOFF)
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2", "--dry-run")  # already filed -> use a fresh row for the dry-run path
        self.row("pf1-expand-r2", "rc == 0", {"ok": 1})
        _, out, _ = self.run_main("pf1-expand-r2", "--dry-run")
        self.assertIn("SUGGESTED-TICK pf1-expand-r2", out)
        self.assertFalse([l for l in out.splitlines() if l.startswith("TICK ")])

    def test_filing_record_carries_owner_session_token_figure(self):
        per = {"t": {"tokens": 1500, "input": 1000, "output": 500, "completed": 3, "tokens_per_task": 500.0}}
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": 1})
        with patch("tokens_per_task.compute", lambda **kw: {"per": per}):
            self.assertEqual(self.run_main("akx-lb3-2-cv5-pair-r2")[0], 0)
        t = self.verdict("akx-lb3-2-cv5-pair-r2")["tokens"]
        self.assertTrue(t["available"])
        self.assertEqual((t["owner_slug"], t["tokens"], t["completed"], t["tokens_per_task"]), ("t", 1500, 3, 500.0))

    def test_token_accounting_never_blocks_filing(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0", {"ok": 1})
        with patch("tokens_per_task.compute", side_effect=RuntimeError("boom")):
            self.assertEqual(self.run_main("akx-lb3-2-cv5-pair-r2")[0], 0)
        t = self.verdict("akx-lb3-2-cv5-pair-r2")["tokens"]
        self.assertFalse(t["available"])
        self.assertIn("boom", t["reason"])
        self.assertTrue(self.filed("akx-lb3-2-cv5-pair-r2"))
        self.row("pf1-expand-r2", "rc == 0", {"ok": 1})  # owner has no rollouts today
        with patch("tokens_per_task.compute", lambda **kw: {"per": {}}):
            self.run_main("pf1-expand-r2")
        self.assertFalse(self.verdict("pf1-expand-r2")["tokens"]["available"])

    def test_numeric_fail_with_rc_and_armed_manifest(self):
        self.row("akx-lb3-2-cv5-pair-r2", "rc == 0 and tps >= 10", {"tps": 12}, rc=1, armed=True)
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0)
        v = self.verdict("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(v["row_verdict"], "fail")
        self.assertEqual(v["rc"], 1)
        self.assertEqual(v["values"]["rc"], 1.0)

    def test_percent_sign_and_dotted_path(self):
        self.row("akx-lb3-2-cv5-pair-r2", "(m.delta > -1.5% or m.delta == 0) and ppl != 0", {"m": {"delta": "-1.2%"}, "ppl": 3})
        code, _, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0)
        self.assertEqual(self.verdict("akx-lb3-2-cv5-pair-r2")["row_verdict"], "pass")

    def test_missing_metric_is_inconclusive_not_pass(self):
        self.row("akx-lb3-2-cv5-pair-r2", "tps_delta >= 2 and ppl_delta <= 0.1", {"tps_delta": 9})
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0)
        v = self.verdict("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(v["row_verdict"], "inconclusive")
        self.assertIn("ppl_delta", v["reason"])
        self.assertEqual(v["outcome_class"], "PARTIAL-VERDICT")
        self.assertTrue(self.filed("akx-lb3-2-cv5-pair-r2"))

    def test_missing_result_file_is_inconclusive(self):
        self.row("akx-lb3-2-cv5-pair-r2", "tps >= 1", None)
        code, _, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0)
        v = self.verdict("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(v["row_verdict"], "inconclusive")
        self.assertFalse(v["result_exists"])

    def test_jsonl_last_record_and_units(self):
        self.row("akx-lb3-2-cv5-pair-r2", "units >= 3 and acc > 0.8", [{"acc": 0.1}, {"acc": 0.2}, {"acc": 0.9}], fmt="jsonl", end=".complete")
        code, _, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 0)
        v = self.verdict("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(v["row_verdict"], "pass")
        self.assertEqual(v["values"], {"units": 3.0, "acc": 0.9})
        self.assertEqual(v["rc"], 0)

    def test_non_numeric_rule_exits_4(self):
        self.row("akx-lb3-2-cv5-pair-r2", "coherent output at 32k with no repetition; judge by eye", {"x": 1})
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 4)
        self.assertTrue(out.startswith("NEEDS-AGENT-VERDICT akx-lb3-2-cv5-pair-r2: coherent"))
        self.assertFalse(os.path.exists(os.path.join(self.flags, "filing-done")))

    def test_verdict_json_applies_and_ticks(self):
        self.row("akx-lb3-2-cv5-pair-r2", "judge by eye", {"x": 1}, rc=0)
        vj = os.path.join(self.tmp.name, "v.json")
        Path(vj).write_text(json.dumps({"verdict": "fail", "rationale": "repeats after 20k", "tick_text": "32k repetition seen"}))
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2", "--verdict-json", vj)
        self.assertEqual(code, 0)
        v = self.verdict("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(v["row_verdict"], "fail")
        self.assertEqual(v["filed_by"], "agent")
        self.assertEqual(v["reason"], "repeats after 20k")
        self.assertTrue(self.filed("akx-lb3-2-cv5-pair-r2"))
        text = Path(self.lane, "handoffs/active/h.md").read_text()
        self.assertIn("- [x] **akx-lb3-2-cv5-pair-r2** tune the thing ✅", text)
        self.assertIn("32k repetition seen", text)
        self.assertIn("- [ ] **pf1-expand-r2** other", text)
        self.assertIn("TICKED akx-lb3-2-cv5-pair-r2", out)

    def test_bad_verdict_json_exits_2(self):
        self.row("akx-lb3-2-cv5-pair-r2", "judge by eye", {"x": 1})
        vj = os.path.join(self.tmp.name, "v.json")
        Path(vj).write_text(json.dumps({"verdict": "maybe"}))
        code, _, err = self.run_main("akx-lb3-2-cv5-pair-r2", "--verdict-json", vj)
        self.assertEqual(code, 2)
        self.assertIn("bad --verdict-json", err)

    def test_dry_run_touches_nothing(self):
        self.row("akx-lb3-2-cv5-pair-r2", "tps >= 1", {"tps": 5})
        code, out, _ = self.run_main("akx-lb3-2-cv5-pair-r2", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("pass", out)
        self.assertIn("(dry-run)", out)
        self.assertFalse(os.path.exists(os.path.join(self.flags, "filing-done")))

    def test_missing_manifest_or_end_exits_2(self):
        code, _, err = self.run_main("NOPE")
        self.assertEqual(code, 2)
        self.assertIn("no manifest", err)
        self.row("akx-lb3-2-cv5-pair-r2", "tps >= 1", {"tps": 5})
        os.remove(os.path.join(self.flags, "grants", "akx-lb3-2-cv5-pair-r2.ended"))
        code, _, err = self.run_main("akx-lb3-2-cv5-pair-r2")
        self.assertEqual(code, 2)
        self.assertIn(".ended|.complete", err)

    def test_parser_rejects_prose_and_accepts_rules(self):
        for ok in ("rc == 0", "a>=1 and b<2 or c!=3", "x.y.z <= +0.5%", "( a > 1 )"):
            fr.parse(ok)
        for bad in ("", "a >= b", "a > 1 and", "tps improves", "a = 1", "a > 1 andb < 2"):
            with self.assertRaises(fr.RuleError, msg=bad):
                fr.parse(bad)



class TestScratchRootAndReclaim(Base):
    def drop_scratch_root(self, rid):
        mp = Path(self.flags, "ready", rid + ".json")
        m = json.loads(mp.read_text()); m.pop("scratch_root"); mp.write_text(json.dumps(m))

    def test_no_scratch_root_refused_exit6_nothing_written(self):
        self.row("stt5-device-declare-ns-r1", "tps >= 10", {"tps": 12})
        self.drop_scratch_root("stt5-device-declare-ns-r1")
        code, _out, err = self.run_main("stt5-device-declare-ns-r1")
        self.assertEqual(code, 6)
        self.assertIn("REFUSED stt5-device-declare-ns-r1", err)
        self.assertFalse(os.path.exists(os.path.join(self.flags, "filing-done", "stt5-device-declare-ns-r1.verdict.json")))
        self.assertFalse(self.filed("stt5-device-declare-ns-r1"))
        self.assertEqual(self.reclaims, [])

    def test_scratch_root_outside_tmp_root_refused(self):
        self.row("stt5-device-declare-out-r1", "tps >= 10", {"tps": 12})
        mp = Path(self.flags, "ready", "stt5-device-declare-out-r1.json")
        m = json.loads(mp.read_text()); m["scratch_root"] = "/elsewhere/x"; mp.write_text(json.dumps(m))
        self.assertEqual(self.run_main("stt5-device-declare-out-r1")[0], 6)

    def test_allow_no_scratch_root_files(self):
        self.row("stt5-device-declare-al-r1", "tps >= 10", {"tps": 12})
        self.drop_scratch_root("stt5-device-declare-al-r1")
        code, _o, _e = self.run_main("stt5-device-declare-al-r1", "--allow-no-scratch-root")
        self.assertEqual(code, 0)
        self.assertTrue(self.filed("stt5-device-declare-al-r1"))

    def test_filing_calls_reclaim_after_filed(self):
        self.row("stt5-device-declare-rc-r1", "tps >= 10", {"tps": 12})
        self.assertEqual(self.run_main("stt5-device-declare-rc-r1")[0], 0)
        self.assertEqual(self.reclaims, [["stt5-device-declare-rc-r1", "--flags", self.flags, "--apply", "--pre-filed"]])

    def test_no_reclaim_flag_and_dry_run(self):
        self.row("stt5-device-declare-nr-r1", "tps >= 10", {"tps": 12})
        self.assertEqual(self.run_main("stt5-device-declare-nr-r1", "--no-reclaim")[0], 0)
        self.assertEqual(self.reclaims, [])
        self.row("stt5-device-declare-dr-r1", "tps >= 10", {"tps": 12})
        self.assertEqual(self.run_main("stt5-device-declare-dr-r1", "--dry-run")[0], 0)
        self.assertEqual(self.reclaims, [["stt5-device-declare-dr-r1", "--flags", self.flags, "--pre-filed"]])

    def test_raising_reclaim_still_returns_0_with_filed(self):
        self.row("stt5-device-declare-rx-r1", "tps >= 10", {"tps": 12})

        def boom(argv):
            raise RuntimeError("disk on fire")
        with patch.object(reclaim_row, "main", boom):
            code, out, _e = self.run_main("stt5-device-declare-rx-r1")
        self.assertEqual(code, 0)
        self.assertTrue(self.filed("stt5-device-declare-rx-r1"))
        self.assertIn("RECLAIM-ERROR stt5-device-declare-rx-r1", out)
        with patch.object(reclaim_row, "main", lambda argv: 7):
            self.row("stt5-device-declare-r7-r1", "tps >= 10", {"tps": 12})
            code, out, _e = self.run_main("stt5-device-declare-r7-r1")
        self.assertEqual((code, "RECLAIM-ERROR stt5-device-declare-r7-r1" in out, self.filed("stt5-device-declare-r7-r1")), (0, True, True))


class TestWithdrawnManifest(unittest.TestCase):
    def test_withdrawn_predecessor_manifest_is_found(self):
        with tempfile.TemporaryDirectory() as flags:
            w = os.path.join(flags, "ready", ".withdrawn")
            os.makedirs(w)
            Path(w, "old-r1.json").write_text(json.dumps({"id": "old-r1", "schema": "epyc.row.v3"}))
            p, m = fr.load_manifest(flags, "old-r1")
            self.assertEqual((os.path.basename(os.path.dirname(p)), m["id"]), (".withdrawn", "old-r1"))



class TestKeepTailOnRealIds(Base):
    """KEEP-TAIL-1 wiring (4ae73176e) + scope matching (16e987ba6) through the real filing path, on real row ids."""
    REGION = {"warm_up": "3 discarded", "timed_loop": "20 iters", "compile_import_check": "excluded"}

    def setUp(self):
        super().setUp()
        self.journal = os.path.join(self.tmp.name, "refusals.jsonl")
        self.addCleanup(os.environ.pop, "KEEP_TAIL_JOURNAL", None)
        os.environ["KEEP_TAIL_JOURNAL"] = self.journal

    def gpu_ab(self, rid, effect):
        xs = [100.0] * 19 + [104.0, 104.0]
        self.row(rid, "rc == 0", {"samples_a": xs, "samples_b": xs, "effect_pct": effect, "timing_region": self.REGION})
        mp = Path(self.flags, "ready", rid + ".json")
        m = json.loads(mp.read_text()); m["lane"] = "gpu"; mp.write_text(json.dumps(m))

    def test_in_scope_row_id_matches_by_tokens_and_is_refused_inside_tail(self):
        rid = "ak-asm-h8b-e2e-20261106"  # scope pattern h8b-e2e matches as whole tokens inside a longer id
        self.gpu_ab(rid, 1.0)
        self.assertEqual(self.run_main(rid)[0], 0)
        kt = self.verdict(rid)["keep_tail"]
        self.assertTrue(kt["reported"] and kt["enforced"] and kt["refused"])
        self.assertTrue(Path(self.journal).exists())

    def test_excluded_c7r_and_out_of_scope_rows_report_but_are_never_refused(self):
        for rid in ("c7r-fa-ctx64k-r2-20261105", "pf1-expand-r2"):
            self.gpu_ab(rid, 1.0)
            self.assertEqual(self.run_main(rid)[0], 0)
            kt = self.verdict(rid)["keep_tail"]
            self.assertTrue(kt["reported"], rid)
            self.assertFalse(kt["enforced"] or kt["refused"], rid)

    def test_gpu_row_without_samples_not_counted_and_cpu_row_has_no_block(self):
        self.row("lsa-oracle-reference-build-f6dddb7-20261104", "rc == 0", {"ok": 1})
        mp = Path(self.flags, "ready", "lsa-oracle-reference-build-f6dddb7-20261104.json")
        m = json.loads(mp.read_text()); m["lane"] = "gpu"; mp.write_text(json.dumps(m))
        self.run_main("lsa-oracle-reference-build-f6dddb7-20261104")
        self.assertFalse(self.verdict("lsa-oracle-reference-build-f6dddb7-20261104")["keep_tail"]["reported"])
        self.row("stt5-device-declare-cpu-r1", "rc == 0", {"ok": 1})
        self.run_main("stt5-device-declare-cpu-r1")
        self.assertNotIn("keep_tail", self.verdict("stt5-device-declare-cpu-r1"))
        self.assertFalse(Path(self.flags, "filing-done", "keep_tail_counter.jsonl").exists())

if __name__ == "__main__":
    unittest.main()
