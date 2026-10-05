"""ETR-3 (eval-tower loop robustness audit, 2026-07-20): the narrow silent-scoring hole.

The audit's finding, precisely: an unrecognized failure that carries a non-empty error
string becomes `task_failed` (charged to the model rather than the platform), which is
defensible. The genuine fail-open is narrower — a **non-blank answer with no error field
and no structural signal** returned `None` from `infra_failure_reason` and was scored as an
ordinary WRONG answer.

The structural fact that closes it was already on the wire and simply unread: the response
reports ZERO generated tokens. Text with no decode behind it (a templated/echoed/stub body)
is the ABSENCE of a measurement, in the same class as `empty_response` — whose blank-answer
requirement is exactly why this shape slipped past it.

The residue is named, not hidden: a non-blank answer WITH a real token count is a genuine
generation, so garbage there is the model's own failure and stays scored WRONG.

The leg is opt-in (``require_generation_evidence``) and the MEASUREMENT paths set it — the
eval tower, and the seeding/calibration classifier. The live-serving reward path
deliberately does not, so a genuine wrong answer keeps earning its negative reward even on
a path that reports no fresh decode.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.autopilot_core.measurement_guards import (  # noqa: E402
    DISPOSITION_INFRA_FAILED,
    DISPOSITION_SCORED,
    INFRA_FAILURE_REASONS,
    infra_failure_reason,
    is_quality_admissible,
    measurement_disposition,
)

GARBAGE = "Sure! Here is the answer you requested."


def test_non_blank_answer_with_zero_generated_tokens_is_not_a_measurement():
    resp = {"answer": GARBAGE, "tokens_generated": 0}
    assert infra_failure_reason(resp, require_generation_evidence=True) == (
        "answer_without_generation"
    )
    disposition = measurement_disposition(resp, require_generation_evidence=True)
    assert disposition == DISPOSITION_INFRA_FAILED
    assert is_quality_admissible(disposition) is False


def test_serving_reward_path_is_unchanged_without_the_opt_in():
    """Default OFF: a live-serving wrong answer must keep earning its negative reward."""
    resp = {"answer": GARBAGE, "tokens_generated": 0}
    assert infra_failure_reason(resp) is None
    assert measurement_disposition(resp) == DISPOSITION_SCORED


def test_measurement_paths_actually_opt_in():
    """A flag that no caller sets is the very defect ETR-2 was about."""
    eval_tower = (REPO_ROOT / "scripts" / "autopilot" / "eval_tower.py").read_text()
    seeding = (REPO_ROOT / "scripts" / "benchmark" / "seeding_scoring.py").read_text()
    seeding_eval = (REPO_ROOT / "scripts" / "benchmark" / "seeding_eval.py").read_text()
    for name, text in (
        ("eval_tower.py", eval_tower),
        ("seeding_scoring.py", seeding),
        ("seeding_eval.py", seeding_eval),
    ):
        assert "require_generation_evidence=True" in text, (
            f"{name} must opt in: it is a measurement path"
        )


def test_the_new_reason_is_in_the_structural_vocabulary():
    """A caller may also stamp it as failure_reason; the token must round-trip."""
    assert "answer_without_generation" in INFRA_FAILURE_REASONS
    assert (
        infra_failure_reason({"failure_reason": "answer_without_generation"})
        == "answer_without_generation"
    )


def test_non_blank_answer_with_real_tokens_is_still_scored():
    """The residue, pinned: a real generation that is wrong is the MODEL's failure."""
    resp = {"answer": GARBAGE, "tokens_generated": 37}
    assert infra_failure_reason(resp, require_generation_evidence=True) is None
    assert measurement_disposition(resp, require_generation_evidence=True) == DISPOSITION_SCORED


def test_mock_mode_reply_is_not_relabelled_infra():
    """Mock replies legitimately report no decode; they must not change disposition."""
    resp = {"answer": GARBAGE, "tokens_generated": 0, "mock_mode": True}
    assert infra_failure_reason(resp, require_generation_evidence=True) is None
    assert measurement_disposition(resp, require_generation_evidence=True) == DISPOSITION_SCORED


def test_legacy_response_without_a_token_counter_is_unchanged():
    """No token counter = no structural signal; a legacy row must not be dropped."""
    resp = {"answer": GARBAGE}
    assert infra_failure_reason(resp, require_generation_evidence=True) is None
    assert measurement_disposition(resp, require_generation_evidence=True) == DISPOSITION_SCORED


def test_blank_answer_with_zero_tokens_is_still_empty_response():
    """The pre-existing leg keeps its own distinguishable reason, opt-in or not."""
    blank = {"answer": "", "tokens_generated": 0}
    assert infra_failure_reason(blank) == "empty_response"
    assert infra_failure_reason(blank, require_generation_evidence=True) == "empty_response"
    assert infra_failure_reason({"answer": "   ", "tokens_generated": 0}) == "empty_response"


def test_blank_answer_with_real_tokens_is_unchanged():
    assert infra_failure_reason({"answer": "", "tokens_generated": 12}) is None
    assert (
        infra_failure_reason({"answer": "", "tokens_generated": 12}, require_generation_evidence=True)
        is None
    )


def test_error_bearing_response_keeps_its_own_classification():
    """ETR-3 is scoped to the no-error-field case; the error paths are untouched.

    An unrecognized error string still lands on `task_failed` — the audit called that
    defensible and explicitly OUT of ETR-3's scope (it is ETR-1's operator decision).
    """
    resp = {"answer": GARBAGE, "tokens_generated": 0}
    assert infra_failure_reason(resp, error="connection refused") == "legacy_error_text_match"
    assert measurement_disposition(resp, error="model produced nonsense") == "task_failed"
