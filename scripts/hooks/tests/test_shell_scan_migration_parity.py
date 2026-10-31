"""Compare three guard verdicts with the pre-migration command corpus.

Every baseline verdict comes from the original source at 12ffc57a5. The only
approved difference is pytest text found exclusively in a shell comment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

from operator_apply_copy_scan import copy_execution_verdict  # noqa: E402
from process_pattern_kill_scan import pattern_kill_verdict  # noqa: E402
from pytest_worker_scan import unsafe_worker_verdict  # noqa: E402

BASELINE = Path(__file__).resolve().parents[3] / "tests" / "hooks" / "fixtures" / "shell_scan_migration_baseline.json"
EXPECTED_DIFFERENCE = {
    "case": "pytest_only_in_comment",
    "scanner": "pytest",
    "before": "auto",
    "after": "",
}
ORIGINALS = {Path("/tmp/ni-shell-scan-protected.py"): frozenset({"protected marker"})}


def test_verdicts_match_pre_migration_corpus_except_documented_comment_case() -> None:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    differences = []
    for case in baseline["cases"]:
        command = case["command"]
        after = {
            "pytest": unsafe_worker_verdict(command),
            "process_pattern_kill": pattern_kill_verdict(command),
            "operator_apply_copy": copy_execution_verdict(command, ORIGINALS),
        }
        for scanner, before in case["before"].items():
            if after[scanner] != before:
                differences.append({
                    "case": case["id"], "scanner": scanner,
                    "before": before, "after": after[scanner],
                })
    assert differences == [EXPECTED_DIFFERENCE]
