from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/handoffs/belief_capture_check.py"
SPEC = importlib.util.spec_from_file_location("belief_capture_check", SCRIPT)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class CompletionEvidenceTests(unittest.TestCase):
    def test_failure_states_in_task_title_are_not_a_failed_completion_claim(self):
        line = (
            "LOOP-50 refuses FAILED/INCONCLUSIVE/PARTIAL receipts; "
            "✅ 2026-11-01 — implementation passed with retained evidence"
        )
        self.assertFalse(checker.UNKNOWN.search(checker.completion_evidence(line)))

    def test_unknown_in_completion_evidence_is_still_rejected(self):
        line = "Example task ✅ 2026-11-01 — verdict unknown"
        self.assertTrue(checker.UNKNOWN.search(checker.completion_evidence(line)))

    def test_undated_unknown_tick_keeps_whole_line_under_review(self):
        line = "Evidence check: unknown completion"
        self.assertTrue(checker.UNKNOWN.search(checker.completion_evidence(line)))


if __name__ == "__main__":
    unittest.main()
