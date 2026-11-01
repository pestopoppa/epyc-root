"""EvalTower sidecar reader tests, anchored to a privacy-minimized producer row set."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from dashboard import eval_errors, panels, server


FIXTURE = Path(__file__).parent / "fixtures" / "eval_errors" / "source_batch.jsonl"


class EvalErrorsReaderTests(unittest.TestCase):
    def _root(self, *, extra: str | None = None) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "eval_tower_trials"
        trial = root / "trial_unknown"
        trial.mkdir(parents=True)
        shutil.copyfile(FIXTURE, trial / "question_results.jsonl")
        if extra:
            with (trial / "question_results.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(extra + "\n")
        return root

    def test_projects_source_batch_and_keeps_infra_out_of_wrong_answers(self):
        data = eval_errors.read_latest(self._root())
        self.assertEqual(data["status"], "reported")
        self.assertEqual(data["batch"]["completed"], 3)
        self.assertEqual(data["counts"]["error"], 2)
        self.assertEqual(data["counts"]["infra_failed"], 2)
        self.assertEqual(data["counts"]["excluded_error"], 2)
        self.assertEqual(data["counts"]["scored_wrong"], 0)
        self.assertEqual(data["counts"]["non_error"], 1)
        self.assertEqual(data["attribution"], "unattributed")
        self.assertAlmostEqual(data["counts"]["error_rate"], 2 / 3)
        self.assertAlmostEqual(data["counts"]["reliability"], 1 / 3)

    def test_incomplete_newer_batch_does_not_replace_latest_complete(self):
        start = {
            "schema_version": 1, "row_type": "batch_start",
            "eval_batch_id": "later-incomplete", "requested_n": 1,
            "label": "T2", "complete": False,
        }
        data = eval_errors.read_latest(self._root(extra=json.dumps(start)))
        self.assertEqual(data["batch"]["eval_batch_id"],
                         "evaltower-T1-1793396458477-ee7e0158-3q")

    def test_duplicate_start_or_mismatched_join_refuses_batch(self):
        lines = FIXTURE.read_text(encoding="utf-8").splitlines()
        duplicate_start = lines[0]
        data = eval_errors.read_latest(self._root(extra=duplicate_start))
        self.assertEqual(data["status"], "incomplete")

        root = self._root()
        path = root / "trial_unknown" / "question_results.jsonl"
        copied_lines = path.read_text(encoding="utf-8").splitlines()
        mismatched = json.loads(copied_lines[1])
        mismatched["label"] = "other-batch"
        copied_lines[1] = json.dumps(mismatched)
        path.write_text("\n".join(copied_lines) + "\n", encoding="utf-8")
        data = eval_errors.read_latest(root)
        self.assertEqual(data["status"], "incomplete")

    def test_duplicate_ordinals_and_completed_count_mismatch_refuse_batch(self):
        root = self._root()
        path = root / "trial_unknown" / "question_results.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        duplicate_ordinal = json.loads(lines[2])
        duplicate_ordinal["ordinal"] = 0
        lines[2] = json.dumps(duplicate_ordinal)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        data = eval_errors.read_latest(root)
        self.assertEqual(data["status"], "incomplete")

        root = self._root()
        path = root / "trial_unknown" / "question_results.jsonl"
        lines = path.read_text(encoding="utf-8").splitlines()
        complete = json.loads(lines[-1])
        complete["completed_n"] = 2
        lines[-1] = json.dumps(complete)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        data = eval_errors.read_latest(root)
        self.assertEqual(data["status"], "incomplete")

    def test_missing_and_unreadable_are_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "missing"
            absent = eval_errors.read_latest(root)
            self.assertEqual(absent["status"], "missing")
            self.assertIsNone(absent["counts"])
            root.mkdir()
            (root / "trial_1").mkdir()
            (root / "trial_1" / "question_results.jsonl").write_text("{bad\n")
            unreadable = eval_errors.read_latest(root)
            self.assertEqual(unreadable["status"], "unreadable")
            self.assertIsNone(unreadable["counts"])

    def test_panel_envelope_uses_semantic_result_timestamp(self):
        data = eval_errors.read_latest(self._root())
        obs = server._eval_errors_observation(data)
        self.assertEqual(obs.source, "question_result.ended_at_s")
        self.assertEqual(obs.watermark, data["batch"]["eval_batch_id"])
        self.assertEqual(panels.source("eval_errors").route, "/api/eval_errors")

    def test_task_failed_is_separate_from_excluded_and_scored_wrong(self):
        start = {"requested_n": 4, "label": "control", "trial_id": None,
                 "eval_batch_id": "control", "complete": False}
        dispositions = [
            ("scored", False, False),
            ("task_failed", True, False),
            ("infra_failed", True, False),
            ("scoring_failed", True, False),
        ]
        results = [
            {"eval_batch_id": "control", "label": "control", "trial_id": None,
             "requested_n": 4, "ordinal": index, "ended_at_s": 1000 + index,
             "result": {"disposition": disposition, "error": error,
                        "correct": correct}}
            for index, (disposition, error, correct) in enumerate(dispositions)
        ]
        batch = {"start": start,
                 "complete": {"complete": True, "requested_n": 4, "completed_n": 4,
                              "label": "control", "trial_id": None,
                              "eval_batch_id": "control"},
                 "results": results, "start_count": 1, "complete_count": 1}
        projected = eval_errors._batch_projection("control", batch)
        self.assertEqual(projected["counts"]["scored_wrong"], 1)
        self.assertEqual(projected["counts"]["task_failed"], 1)
        self.assertEqual(projected["counts"]["excluded_error"], 2)
        self.assertEqual(projected["counts"]["error"], 3)

    def test_route_and_panel_registry_are_closed(self):
        self.assertIs(server.API_ROUTES["/api/eval_errors"], server.eval_errors_payload)
        self.assertFalse(any(panels.registry_gaps(server).values()))

    def test_zero_row_complete_batch_has_no_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trial = root / "trial_7"
            trial.mkdir()
            rows = [
                {"schema_version": 1, "row_type": "batch_start",
                 "eval_batch_id": "empty", "requested_n": 0, "label": "T0",
                 "complete": False},
                {"schema_version": 1, "row_type": "batch_complete",
                 "eval_batch_id": "empty", "label": "T0", "requested_n": 0,
                 "completed_n": 0, "complete": True},
            ]
            (trial / "question_results.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            data = eval_errors.read_latest(root)
        self.assertEqual(data["status"], "empty_batch")
        self.assertIsNone(data["counts"]["error_rate"])
        self.assertIsNone(server._eval_errors_observation(data).timestamp)


if __name__ == "__main__":
    unittest.main()
