import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("completion_unit", HERE / "completion_unit.py")
completion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(completion)
sys.path.insert(0, "/workspace/scripts/coordination/rowflow")
import rowflow

def write_attempt_result(attempt, owner, **changes):
    result = {"status":"pass", "partial":False, "drained":True, "survivors":[],
        "boundary_reason":None, "owner_result":str(owner), "captured_returncodes":{}}
    result.update(changes)
    (attempt / "RESULT.json").write_text(json.dumps(result))

class RowflowContractTests(unittest.TestCase):
    def test_native_dryrun_unit_is_not_production_completion(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "SOURCE-REVIEW.sha256").write_text("seal\n")
            p = root / "attempts/production-a/ROWFLOW-UNIT.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"schema":"rte.rowflow.unit.v1", "row_id":completion.ROW_ID,
                "unit_kind":"native_tokenizer_qualification", "acceptance":False,
                "source_review_sha256":completion.sha(root / "SOURCE-REVIEW.sha256")}))
            self.assertFalse(completion.production_complete(root))

    def test_complete_requires_hashed_owner_receipt_and_matching_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            manifest = root / "SOURCE-REVIEW.sha256"
            manifest.write_text("seal\n")
            owner = root / "attempts/production-a/owner/RESULT.json"
            owner.parent.mkdir(parents=True)
            receipt = {"status":"pass", "request_completed":True, "owner_boundary_required":True,
                "expected_source":completion.EXPECTED_SOURCE, "committed_live_checker_rc":0, "request_id":"rte-owner-x"}
            owner.write_text(json.dumps(receipt))
            unit = {"schema":"rte.rowflow.unit.v1", "row_id":completion.ROW_ID,
                "unit_kind":"production_owner_acceptance", "acceptance":True,
                "attempt_mode":"production", "attempt_id":"production-a", "qualification_only":False, "grant_sha256":"a" * 64,
                "source_review_sha256":completion.sha(manifest), "owner_result_path":str(owner),
                "owner_result_sha256":completion.sha(owner), "request_id":"rte-owner-x",
                "expected_source":completion.EXPECTED_SOURCE, "committed_live_checker_rc":0}
            p = root / "attempts/production-a/ROWFLOW-UNIT.json"
            p.write_text(json.dumps(unit))
            attempt = p.parent
            write_attempt_result(attempt, owner)
            self.assertTrue(completion.production_complete(root))
            unit["owner_result_sha256"] = "0" * 64
            p.write_text(json.dumps(unit))
            self.assertFalse(completion.production_complete(root))

            unit["owner_result_sha256"] = completion.sha(owner)
            p.write_text(json.dumps(unit))
            for changes in (
                {"status":"failure"}, {"partial":True}, {"drained":False},
                {"survivors":[999999]}, {"owner_result":str(root / "other.json")},
                {"error":"cleanup failed"},
            ):
                write_attempt_result(attempt, owner, **changes)
                self.assertFalse(completion.production_complete(root), changes)

            (attempt / "RESULT.json").unlink()
            self.assertFalse(completion.production_complete(root), "missing final attempt result")


    def test_valid_dryrun_owner_receipt_cannot_satisfy_production_completion(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            manifest = root / "SOURCE-REVIEW.sha256"
            manifest.write_text("seal\n")
            owner = root / "attempts/dryrun-a/owner/RESULT.json"
            owner.parent.mkdir(parents=True)
            receipt = {"status":"pass", "request_completed":True, "owner_boundary_required":True,
                "expected_source":completion.EXPECTED_SOURCE, "committed_live_checker_rc":0, "request_id":"rte-owner-dryrun"}
            owner.write_text(json.dumps(receipt))
            unit = {"schema":"rte.rowflow.unit.v1", "row_id":completion.ROW_ID,
                "unit_kind":"dryrun_owner_acceptance", "acceptance":False,
                "attempt_mode":"dryrun", "attempt_id":"dryrun-a", "qualification_only":True, "grant_sha256":"b" * 64,
                "source_review_sha256":completion.sha(manifest), "owner_result_path":str(owner),
                "owner_result_sha256":completion.sha(owner), "request_id":"rte-owner-dryrun",
                "expected_source":completion.EXPECTED_SOURCE, "committed_live_checker_rc":0}
            (root / "attempts/dryrun-a/ROWFLOW-UNIT.json").write_text(json.dumps(unit))
            self.assertFalse(completion.production_complete(root))

    def test_spec_glob_counts_only_real_json_units(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "attempts/production-a").mkdir(parents=True)
            (root / "attempts/production-a/ROWFLOW-UNIT.json").write_text(json.dumps({"schema":"rte.rowflow.unit.v1"}))
            glob = str(root / "attempts/*/ROWFLOW-UNIT.json")
            self.assertEqual(rowflow.count_units(glob, "json"), 1)
            (root / "attempts/b").mkdir()
            (root / "attempts/b/ROWFLOW-UNIT.json").write_text(json.dumps({"schema":"rte.rowflow.unit.v1"}))
            self.assertEqual(rowflow.count_units(glob, "json"), 2)

    def test_launcher_uses_v15_engine_and_stop_contract(self):
        parsed = rowflow.parse_launcher(str(HERE / "launcher.v15.sh"))
        self.assertEqual(pathlib.Path(parsed["engine"]).name, "filler_run15.sh")
        self.assertEqual(parsed["id"], completion.ROW_ID)
        job = (HERE / "frontdoor_job.py").read_text()
        self.assertIn("FILLER_STOPFILE", job)
        self.assertIn("FILLER_DRYRUN", (HERE / "launcher.v15.sh").read_text())
        self.assertNotIn("if os.environ.get('FILLER_DRYRUN')=='1':", job)
        self.assertIn("FILLER_ID", job)
        self.assertIn("grants/codex-ni-rte-frontdoor-quarter-20261031.grant", job)
        self.assertLess(job.index("assert checker.returncode==0"), job.index("'unit_kind':'dryrun_owner_acceptance'"))
        self.assertIn("qualification_only':attempt_mode=='dryrun'", job)
        self.assertIn('unit.get("attempt_mode") != "production"', (HERE / "completion_unit.py").read_text())

if __name__ == "__main__":
    unittest.main()
