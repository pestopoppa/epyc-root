from __future__ import annotations

import pytest

from scripts.analysis import ri10_canary_score_responses as scorer


def _answer_key(
    request_id: str,
    *,
    role: str = "worker_general",
    arm: str = "enforce",
    expected: str = "multiprocessing",
) -> dict:
    return {
        "request_id": request_id,
        "role": role,
        "expected_factual_risk_mode": arm,
        "expected_answer": expected,
        "prompt_hash": f"hash-{request_id}",
        "domain": "Software Engineering",
        "label_source": "aa_omniscience",
    }


def test_score_responses_summarizes_by_arm_and_role() -> None:
    answer_key = [
        _answer_key("r1", role="worker_general", arm="enforce"),
        _answer_key("r2", role="worker_general", arm="shadow"),
        _answer_key("r3", role="frontdoor", arm="enforce", expected="Safari"),
        _answer_key("r4", role="frontdoor", arm="shadow", expected="Safari"),
    ]
    responses = [
        {"request_id": "r1", "response": "multiprocessing"},
        {"request_id": "r2", "response": "not sure"},
        {"request_id": "r3", "choices": [{"message": {"content": "Safari"}}]},
        {"request_id": "r4", "choices": [{"message": {"content": "Firefox"}}]},
    ]

    scored, summary = scorer.score_responses(
        answer_key_rows=answer_key,
        response_rows=responses,
    )

    assert summary["status"] == "ready"
    assert summary["rows"] == 4
    assert summary["buckets"]["overall"]["accuracy"] == 0.5
    assert summary["buckets"]["arm:enforce"]["accuracy"] == 1.0
    assert summary["buckets"]["arm:shadow"]["accuracy"] == 0.0
    assert summary["arm_comparison"]["status"] == "ready"
    assert summary["arm_comparison"]["accuracy_delta_enforce_minus_shadow"] == 1.0
    assert [row["outcome"] for row in scored] == [
        "CORRECT",
        "INCORRECT",
        "CORRECT",
        "INCORRECT",
    ]


def test_score_responses_accepts_exact_answer_inside_explanation() -> None:
    scored, summary = scorer.score_responses(
        answer_key_rows=[_answer_key("r1", expected="multiprocessing")],
        response_rows=[
            {
                "request_id": "r1",
                "response": "The package introduced by PEP 371 is multiprocessing.",
            }
        ],
    )

    assert summary["status"] == "ready"
    assert summary["buckets"]["overall"]["accuracy"] == 1.0
    assert scored[0]["binary_correct"] is True
    assert scored[0]["outcome"] == "CORRECT"


def test_score_responses_reports_missing_response() -> None:
    scored, summary = scorer.score_responses(
        answer_key_rows=[
            _answer_key("r1", arm="enforce"),
            _answer_key("r2", arm="shadow"),
        ],
        response_rows=[{"request_id": "r1", "response": "multiprocessing"}],
    )

    assert summary["status"] == "missing_responses"
    assert summary["status_counts"] == {"missing_response": 1, "scored": 1}
    missing = [row for row in scored if row["status"] == "missing_response"]
    assert missing[0]["request_id"] == "r2"


def test_score_responses_rejects_duplicate_responses() -> None:
    with pytest.raises(ValueError, match="duplicate response request_id"):
        scorer.score_responses(
            answer_key_rows=[_answer_key("r1")],
            response_rows=[
                {"request_id": "r1", "response": "multiprocessing"},
                {"request_id": "r1", "response": "multiprocessing"},
            ],
        )


def test_response_text_requires_known_shape() -> None:
    with pytest.raises(ValueError, match="response row must contain"):
        scorer.score_responses(
            answer_key_rows=[_answer_key("r1")],
            response_rows=[{"request_id": "r1", "unexpected": "shape"}],
        )
