"""Tests for post-hoc model grading helpers.

TD-21.23: `grade_answer` now sends a schema-constrained call
(`_classification_schema`, a json-schema `enum` over the spec's own
`choice_strings`) instead of a bare prompt, parses the reply natively first
(`_native_classification`), and falls back to the pre-existing last-line
regex (`_extract_classification`) only on a native miss. A mis-formatted
reply that neither path recovers is no longer a silent `classification=None`
"ungraded" row: it becomes the typed sentinel `"parse_error"`, counted in
`GRADER_CLASSIFICATION_OUTCOME_COUNTS`.
"""

from __future__ import annotations

import sys
from types import ModuleType

import pytest

from src.pipeline_monitor import model_grader


@pytest.fixture(autouse=True)
def _clear_grader_counts():
    model_grader.reset_grader_outcome_counts_for_tests()
    yield
    model_grader.reset_grader_outcome_counts_for_tests()


def _install_fake_seeding_orchestrator(monkeypatch, calls: list[dict], answer: str = "Reasoning\nA") -> None:
    module = ModuleType("seeding_orchestrator")

    def call_orchestrator_forced(**kwargs):
        calls.append(kwargs)
        return {"answer": answer}

    module.call_orchestrator_forced = call_orchestrator_forced
    monkeypatch.setitem(sys.modules, "seeding_orchestrator", module)


def test_grade_answer_defaults_to_live_worker_general(monkeypatch):
    calls: list[dict] = []
    _install_fake_seeding_orchestrator(monkeypatch, calls)

    result = model_grader.grade_answer(
        {
            "spec_name": "quality",
            "prompt_template": "Question: {question}",
            "choice_strings": ["A"],
            "choice_scores": {"A": 1.0},
        },
        {"question_id": "q1"},
    )

    assert result is not None
    assert result["classification"] == "A"
    assert calls[0]["force_role"] == "worker_general"


def test_grade_answer_preserves_explicit_judge_role(monkeypatch):
    calls: list[dict] = []
    _install_fake_seeding_orchestrator(monkeypatch, calls)

    model_grader.grade_answer(
        {
            "spec_name": "quality",
            "judge_role": "architect_general",
            "prompt_template": "Question: {question}",
            "choice_strings": ["A"],
            "choice_scores": {"A": 1.0},
        },
        {"question_id": "q1"},
    )

    assert calls[0]["force_role"] == "architect_general"


# --------------------------------------------------------------------------- TD-21.23: native enum + counted parse_error


def test_grade_answer_sends_enum_constrained_output_schema(monkeypatch):
    calls: list[dict] = []
    _install_fake_seeding_orchestrator(monkeypatch, calls)

    model_grader.grade_answer(
        {
            "spec_name": "quality",
            "prompt_template": "Question: {question}",
            "choice_strings": ["A", "B", "C"],
            "choice_scores": {"A": 1.0, "B": 0.5, "C": 0.0},
        },
        {"question_id": "q1"},
    )

    schema = calls[0]["output_schema"]
    assert schema["type"] == "object"
    assert schema["properties"]["classification"]["enum"] == ["A", "B", "C"]
    assert schema["additionalProperties"] is False


def test_grade_answer_native_reply_parsed_without_fishing(monkeypatch):
    calls: list[dict] = []
    _install_fake_seeding_orchestrator(monkeypatch, calls, answer='{"classification": "B"}')

    result = model_grader.grade_answer(
        {
            "spec_name": "quality",
            "prompt_template": "Question: {question}",
            "choice_strings": ["A", "B", "C"],
            "choice_scores": {"A": 1.0, "B": 0.5, "C": 0.0},
        },
        {"question_id": "q1"},
    )

    assert result["classification"] == "B"
    assert result["score"] == 0.5
    assert model_grader.GRADER_CLASSIFICATION_OUTCOME_COUNTS.get(("quality", "native")) == 1
    assert model_grader.GRADER_CLASSIFICATION_OUTCOME_COUNTS.get(("quality", "fished"), 0) == 0


def test_grade_answer_falls_back_to_fish_when_reply_is_not_json(monkeypatch):
    calls: list[dict] = []
    _install_fake_seeding_orchestrator(monkeypatch, calls, answer="Some reasoning here.\nB")

    result = model_grader.grade_answer(
        {
            "spec_name": "quality",
            "prompt_template": "Question: {question}",
            "choice_strings": ["A", "B", "C"],
            "choice_scores": {"A": 1.0, "B": 0.5, "C": 0.0},
        },
        {"question_id": "q1"},
    )

    assert result["classification"] == "B"
    assert result["score"] == 0.5
    assert model_grader.GRADER_CLASSIFICATION_OUTCOME_COUNTS.get(("quality", "fished")) == 1


def test_grade_answer_unparseable_reply_becomes_typed_parse_error_not_silent_none(monkeypatch):
    calls: list[dict] = []
    _install_fake_seeding_orchestrator(
        monkeypatch, calls, answer="I refuse to answer in the requested format today."
    )

    result = model_grader.grade_answer(
        {
            "spec_name": "quality",
            "prompt_template": "Question: {question}",
            "choice_strings": ["A", "B", "C"],
            "choice_scores": {"A": 1.0, "B": 0.5, "C": 0.0},
        },
        {"question_id": "q1"},
    )

    assert result is not None  # a graded row -- the CALL succeeded, only the parse failed
    assert result["classification"] == "parse_error"
    assert result["score"] is None
    assert model_grader.GRADER_CLASSIFICATION_OUTCOME_COUNTS.get(("quality", "parse_error")) == 1


def test_grade_answer_logs_on_parse_error(monkeypatch, caplog):
    _install_fake_seeding_orchestrator(monkeypatch, [], answer="no usable letter anywhere")

    with caplog.at_level("WARNING"):
        model_grader.grade_answer(
            {
                "spec_name": "quality",
                "prompt_template": "Question: {question}",
                "choice_strings": ["A", "B"],
                "choice_scores": {"A": 1.0, "B": 0.0},
            },
            {"question_id": "q1"},
        )

    assert any("parse_error" in record.message for record in caplog.records)


def test_grade_answer_no_schema_when_choice_strings_empty(monkeypatch):
    calls: list[dict] = []
    _install_fake_seeding_orchestrator(monkeypatch, calls, answer="free-form reasoning, no letter")

    model_grader.grade_answer(
        {
            "spec_name": "quality",
            "prompt_template": "Question: {question}",
            "choice_strings": [],
            "choice_scores": {},
        },
        {"question_id": "q1"},
    )

    assert calls[0]["output_schema"] is None


def test_native_classification_rejects_a_value_outside_the_closed_choices():
    """A json-schema `enum` on the wire should make this unreachable in
    practice, but the parser itself never trusts an off-set value either."""
    assert model_grader._native_classification('{"classification": "Z"}', ["A", "B"]) is None


def test_extract_classification_backstop_unchanged():
    assert model_grader._extract_classification("some reasoning\nB", ["A", "B"]) == "B"
    assert model_grader._extract_classification("no letter here", ["A", "B"]) is None
