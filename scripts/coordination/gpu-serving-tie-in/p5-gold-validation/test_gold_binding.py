"""Model-free controls for the prospective P5 report-coverage helper."""
import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location("gold_binding", Path(__file__).with_name("gold_binding.py"))
binding = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(binding)


class GoldBindingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.questions = [{"id": "repo-1", "prompt": "fix the issue"}]
        self.dataset = [{"instance_id": "repo-1", "repo": "org/repo", "base_commit": "abc",
                         "patch": "gold patch", "FAIL_TO_PASS": '["test_one"]'}]
        self.report = {"total_instances": 1, "completed_instances": 1, "resolved_instances": 1,
                       "unresolved_instances": 0, "error_instances": 0,
                       "completed_ids": ["repo-1"], "resolved_ids": ["repo-1"],
                       "unresolved_ids": [], "error_ids": []}
        self.write_json("questions.json", self.questions)
        self.write_json("dataset.json", self.dataset)
        self.write_json("report.json", self.report)
        (self.root / "scorer.py").write_text("# exact scorer entry\n", encoding="utf-8")
        self.args = argparse.Namespace(questions=str(self.root / "questions.json"),
                                       dataset=str(self.root / "dataset.json"),
                                       scorer=str(self.root / "scorer.py"),
                                       binding=str(self.root / "binding.json"),
                                       report=str(self.root / "report.json"))
        self.write_json("binding.json", binding.freeze(self.args))

    def write_json(self, name, value):
        (self.root / name).write_text(json.dumps(value), encoding="utf-8")

    def test_complete_report_has_only_coverage_claim(self):
        result = binding.check(self.args)
        self.assertEqual(result["status"], "REPORT_COVERAGE_MATCH")
        self.assertEqual(result["cases"], 1)
        self.assertIn("does not prove", result["limitation"])

    def test_dataset_patch_tampering_is_refused(self):
        self.dataset[0]["patch"] = "different patch"
        self.write_json("dataset.json", self.dataset)
        with self.assertRaises(ValueError):
            binding.check(self.args)

    def test_question_tampering_is_refused(self):
        self.questions[0]["prompt"] = "different issue"
        self.write_json("questions.json", self.questions)
        with self.assertRaises(ValueError):
            binding.check(self.args)

    def test_duplicate_question_ids_are_refused(self):
        self.questions.append(dict(self.questions[0]))
        self.write_json("questions.json", self.questions)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            binding.freeze(self.args)

    def test_duplicate_dataset_ids_are_refused(self):
        self.dataset.append(dict(self.dataset[0]))
        self.write_json("dataset.json", self.dataset)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            binding.freeze(self.args)

    def test_changed_scorer_is_refused(self):
        (self.root / "scorer.py").write_text("# changed scorer\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            binding.check(self.args)

    def test_incomplete_report_is_refused(self):
        self.report["completed_ids"] = []
        self.write_json("report.json", self.report)
        with self.assertRaises(ValueError):
            binding.check(self.args)

    def test_error_report_is_refused(self):
        self.report["error_ids"] = ["repo-1"]
        self.report["error_instances"] = 1
        self.write_json("report.json", self.report)
        with self.assertRaises(ValueError):
            binding.check(self.args)

    def test_contradictory_optional_native_status_is_refused(self):
        for key, value in (("submitted_ids", []), ("submitted_instances", 0),
                           ("empty_patch_ids", ["repo-1"]), ("empty_patch_instances", 1),
                           ("incomplete_ids", ["repo-1"]), ("incomplete_instances", 1)):
            with self.subTest(field=key):
                report = dict(self.report, **{key: value})
                self.write_json("report.json", report)
                with self.assertRaises(ValueError):
                    binding.check(self.args)

    def test_consistent_optional_native_status_is_accepted(self):
        self.report.update(submitted_ids=["repo-1"], submitted_instances=1,
                           empty_patch_ids=[], empty_patch_instances=0,
                           incomplete_ids=[])
        self.write_json("report.json", self.report)
        self.assertEqual(binding.check(self.args)["status"], "REPORT_COVERAGE_MATCH")

    def test_boolean_counts_are_refused(self):
        for key, value in (("total_instances", True), ("error_instances", False),
                           ("submitted_instances", True), ("empty_patch_instances", False)):
            with self.subTest(field=key):
                self.write_json("report.json", dict(self.report, **{key: value}))
                with self.assertRaises(ValueError):
                    binding.check(self.args)

    def test_missing_fail_to_pass_is_refused(self):
        self.dataset[0]["FAIL_TO_PASS"] = "[]"
        self.write_json("dataset.json", self.dataset)
        with self.assertRaises(ValueError):
            binding.freeze(self.args)


if __name__ == "__main__":
    unittest.main()
