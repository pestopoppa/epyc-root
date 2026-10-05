"""Self-criticism keep/revert decisions must respect eval resolution."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from safety_gate import EvalResult, SafetyVerdict  # type: ignore[import-not-found]
from self_criticism import generate_self_criticism  # type: ignore[import-not-found]


def _result(quality: float, n_questions: int) -> EvalResult:
    return EvalResult(
        tier=1,
        quality=quality,
        speed=50.0,
        cost=0.2,
        reliability=0.98,
        n_questions=n_questions,
    )


def test_small_passed_delta_within_single_question_quantum_is_unchanged() -> None:
    criticism = generate_self_criticism(
        {"type": "seed_batch"},
        _result(quality=1.55, n_questions=10),  # quantum = 0.3
        SafetyVerdict(passed=True),
        failure_analysis="",
        baseline_quality=1.50,
    )
    assert criticism.keep_or_revert == "unchanged"
    assert "within eval resolution" in criticism.keep_revert_reasoning


def test_passed_delta_above_single_question_quantum_is_keep() -> None:
    criticism = generate_self_criticism(
        {"type": "seed_batch"},
        _result(quality=1.58, n_questions=50),  # quantum = 0.06
        SafetyVerdict(passed=True),
        failure_analysis="",
        baseline_quality=1.50,
    )
    assert criticism.keep_or_revert == "keep"


def test_high_n_delta_below_floor_is_unchanged() -> None:
    criticism = generate_self_criticism(
        {"type": "seed_batch"},
        _result(quality=1.515, n_questions=500),  # quantum = 0.006, floor = 0.02
        SafetyVerdict(passed=True),
        failure_analysis="",
        baseline_quality=1.50,
    )
    assert criticism.keep_or_revert == "unchanged"
