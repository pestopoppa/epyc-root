"""Synthetic-only MF-FS-1 controls. Never reads the real BEP corpus."""
import importlib.util
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).with_name("mf_fs1_classify.py")
spec = importlib.util.spec_from_file_location("mf_fs1_classify_private", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SyntheticControls(unittest.TestCase):
    def test_markers_and_signal_semantics(self):
        mod.self_test()

    def test_selection_duplicates_unknowns_readset_and_privacy(self):
        with tempfile.TemporaryDirectory(prefix="mf-fs1-synth-") as td:
            repo = Path(td)
            data = repo / "data" / "bep_sandbox"
            run = data / "results-synthetic"
            (run / "traces").mkdir(parents=True)
            (data / "INVALID-synthetic").mkdir()
            (data / "INVALID-synthetic" / "results.jsonl").write_text(
                json.dumps({"mode":"real","task":"must-not-count","arm":"off","block":0,
                    "turns":1,"answer_preview":"[Max turns reached]"})+"\n")
            trace1 = [
                {"turn":1,"calls_open":True,"calls_file_write_safe":False,
                 "prompt_has_loop_halt":False,"repeat_count_seen":0,
                 "raw_output":"PRIVATE_SYNTHETIC_MODEL_TEXT","extracted_code":"PRIVATE_SYNTHETIC_CODE"},
                {"turn":2,"calls_open":True,"calls_file_write_safe":True,
                 "prompt_has_loop_halt":True,"repeat_count_seen":2}
            ]
            trace2 = [{"turn":1,"calls_open":False}]
            (run / "traces" / "a.jsonl").write_text("".join(json.dumps(x)+"\n" for x in trace1))
            (run / "traces" / "b.jsonl").write_text(json.dumps(trace2[0])+"\n")
            good={"mode":"real","task":"t2","arm":"off","block":0,"turns":8,
                "answer_preview":"[Max turns (8) reached]","trace":{"path":"traces/a.jsonl"}}
            duplicate=dict(good)
            ambiguous={"mode":"real","task":"t3","arm":"on","block":1,"turns":8,
                "answer_preview":"[ERROR: overlap [Max turns]","trace":{"path":"traces/b.jsonl"}}
            missing={"mode":"real","task":"t4","arm":"off","block":2,"turns":8,
                "answer_preview":"[ERROR: backend]","trace":{"path":"traces/missing.jsonl"}}
            malformed={"mode":"real","task":"bad","block":9,"turns":1,"answer_preview":"done"}
            stub={"mode":"stub","task":"stub","arm":"off","block":0,"turns":1,"answer_preview":"done"}
            rows=[good,duplicate,ambiguous,missing,malformed,stub]
            (run / "results.jsonl").write_text("".join(json.dumps(x)+"\n" for x in rows)+"{bad json\n")
            report=mod.analyze(data,repo,check_pins=False)
            c=report["eligibility"]
            self.assertEqual(c["real_rows_eligible"],3)
            self.assertEqual(c["forced_max_turns"],1)
            self.assertEqual(c["forced_error"],1)
            self.assertEqual(c["ambiguous_terminal_unknown"],1)
            self.assertEqual(c["duplicate_result_identities_excluded"],1)
            self.assertEqual(c["malformed_required_rows_excluded"],1)
            self.assertEqual(c["non_real_rows_excluded"],1)
            self.assertEqual(c["results_malformed_json_lines"],1)
            self.assertEqual(c["invalid_run_directories_excluded"],1)
            self.assertEqual(c["trace_valid"],2)
            self.assertEqual(c["trace_missing"],1)
            groups=report["by_task_arm"]
            self.assertEqual(groups["t2|off"]["signals_by_terminal"]["forced_max_turns"]["repeated_open_activity"]["true"],1)
            self.assertEqual(groups["t2|off"]["signals_by_terminal"]["forced_max_turns"]["loop_halt_observed"]["true"],1)
            encoded=json.dumps(report)
            self.assertNotIn("PRIVATE_SYNTHETIC_MODEL_TEXT",encoded)
            self.assertNotIn("PRIVATE_SYNTHETIC_CODE",encoded)
            self.assertEqual(len(report["readset_sha256"]),64)
            self.assertEqual(len(report["readset"]),3)
            self.assertTrue(all("sha256" in item and "byte_count" in item and "snapshot_path" in item
                for item in report["readset"]))
            snap=Path(mod.SCRATCH)/report["readset"][0]["snapshot_path"]
            self.assertEqual(snap.stat().st_mode & 0o777,0o600)
            for item in report["readset"]:
                saved=(Path(mod.SCRATCH)/item["snapshot_path"]).read_bytes()
                self.assertEqual(len(saved),item["byte_count"])
                self.assertEqual(hashlib.sha256(saved).hexdigest(),item["sha256"])
            self.assertEqual((Path(mod.SCRATCH)/"input-snapshots").stat().st_mode & 0o777,0o700)



    def test_companion_bytes_are_bound_at_module_load(self):
        original=mod._capture_companion_bytes
        try:
            mod._capture_companion_bytes=lambda: b"changed after module load"
            with self.assertRaises(ValueError):
                mod.verify_companion_unchanged()
        finally:
            mod._capture_companion_bytes=original

    def test_total_budget_exceeded_aborts_instead_of_becoming_invalid_trace(self):
        with tempfile.TemporaryDirectory(prefix="mf-fs1-budget-") as td:
            repo=Path(td); data=repo/"data"/"bep_sandbox"; run=data/"results-budget"
            (run/"traces").mkdir(parents=True)
            trace_raw=(json.dumps({"turn":1,"calls_open":False,"calls_file_write_safe":False,
                "prompt_has_loop_halt":False})+"\n").encode()
            (run/"traces"/"trace.jsonl").write_bytes(trace_raw)
            row={"mode":"real","task":"t2","arm":"off","block":0,"turns":8,
                "answer_preview":"[Max turns reached]","trace":{"path":"traces/trace.jsonl"}}
            result_raw=(json.dumps(row)+"\n").encode()
            (run/"results.jsonl").write_bytes(result_raw)
            old_budget=mod.MAX_TOTAL_INPUT_BYTES
            mod.MAX_TOTAL_INPUT_BYTES=len(result_raw)
            try:
                with self.assertRaises(mod.InputBudgetExceeded):
                    mod.analyze(data,repo,check_pins=False)
            finally:
                mod.MAX_TOTAL_INPUT_BYTES=old_budget

    def test_symlink_trace_is_unknown_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory(prefix="mf-fs1-synth-") as td:
            base=Path(td); repo=base/"repo"; data=repo/"data"/"bep_sandbox"
            run=data/"results-synthetic"; (run/"traces").mkdir(parents=True)
            outside=base/"outside.jsonl"; outside.write_text(json.dumps({"turn":1})+"\n")
            (run/"traces"/"link.jsonl").symlink_to(outside)
            row={"mode":"real","task":"t5","arm":"off","block":0,"turns":8,
                "answer_preview":"[Max turns reached]","trace":{"path":"traces/link.jsonl"}}
            (run/"results.jsonl").write_text(json.dumps(row)+"\n")
            report=mod.analyze(data,repo,check_pins=False)
            self.assertEqual(report["eligibility"]["trace_invalid_or_missing"],1)
            self.assertEqual(report["by_task_arm"]["t5|off"]["trace_missing_or_invalid"],1)
            self.assertEqual(report["by_task_arm"]["t5|off"]["signals_by_terminal"]["forced_max_turns"]
                ["write_signal_observed"]["unknown"],1)
            empty_run=data/"results-empty"; (empty_run/"traces").mkdir(parents=True)
            (empty_run/"traces"/"empty.jsonl").write_text("")
            empty_row={"mode":"real","task":"t6","arm":"on","block":0,"turns":8,
                "answer_preview":"[Max turns reached]","trace":{"path":"traces/empty.jsonl"}}
            (empty_run/"results.jsonl").write_text(json.dumps(empty_row)+"\n")
            report=mod.analyze(data,repo,check_pins=False)
            self.assertEqual(report["eligibility"]["trace_empty"],1)
            self.assertEqual(report["by_task_arm"]["t6|on"]["signals_by_terminal"]["forced_max_turns"]
                ["loop_halt_observed"]["unknown"],1)
            with self.assertRaises(ValueError):
                mod.trace_rel(Path("results-x/results.jsonl"),"../../outside.jsonl")

if __name__=="__main__":
    unittest.main()
