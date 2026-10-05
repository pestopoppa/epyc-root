"""Unit tests for TD-4 tool-argument mapping (src/typed_decisions/tool_args.py).

Closed-set projection of JSON-schema tool parameters into typed questions and
the reverse assembly back into a validated argument dict. No model/server call:
the one end-to-end test drives ``run_typed_decisions`` with a canned response
fake, mirroring ``tests/unit/test_typed_decisions.py``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

import pytest
from jsonschema import Draft202012Validator

from src.typed_decisions import run_typed_decisions
from src.typed_decisions.tool_args import (
    ToolArgumentError,
    ToolQuestionMapping,
    assemble_arguments,
    tool_schema_to_questions,
)
from src.typed_decisions.types import Decision, Question, QuestionKind

ROLE = "worker"
STATE = "unit-test state for tool-argument mapping"

_TOOL_PARAMETERS: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "mode": {"type": "string", "enum": ["fast", "safe"], "description": "Routing mode."},
        "dry_run": {"type": "boolean"},
        "retries": {"type": "integer", "minimum": 0, "maximum": 3},
        "tags": {
            "type": "array",
            "items": {"type": "string", "enum": ["alpha", "beta", "gamma"]},
        },
        "notes": {"type": "string"},
    },
    "required": ["mode"],
}


def _mapping() -> ToolQuestionMapping:
    return tool_schema_to_questions("deploy", _TOOL_PARAMETERS)


def _decision(question: Question, value: object) -> Decision:
    return Decision(
        question_id=question.id,
        kind=question.kind,
        value=value,
        probabilities={},
        confidence=1.0,
        mode="json",
    )


def _decisions(mapping: ToolQuestionMapping, values: Mapping[str, object]) -> list[Decision]:
    by_id = {question.id: question for question in mapping.questions}
    return [_decision(by_id[question_id], value) for question_id, value in values.items()]


# ── 1. Schema -> questions ────────────────────────────────────────────────


class TestSchemaToQuestions:
    def test_mapping_shapes_and_ids(self):
        mapping = _mapping()

        assert isinstance(mapping, ToolQuestionMapping)
        assert [question.id for question in mapping.questions] == [
            "mode",
            "dry_run",
            "retries",
            "tags__alpha",
            "tags__beta",
            "tags__gamma",
        ]
        assert [question.kind for question in mapping.questions] == [
            QuestionKind.CHOICE,
            QuestionKind.NOUL,
            QuestionKind.SCORE,
            QuestionKind.NOUL,
            QuestionKind.NOUL,
            QuestionKind.NOUL,
        ]
        mode = mapping.questions[0]
        assert mode.options == ("fast", "safe")
        assert "Routing mode." in mode.criteria
        retries = mapping.questions[2]
        assert retries.levels == (0, 1, 2, 3)
        assert mapping.skipped == ["notes: unsupported JSON-schema type 'string'"]

    def test_integer_enum_maps_to_score_levels(self):
        parameters = {
            "type": "object",
            "properties": {"priority": {"type": "integer", "enum": [1, 2, 4]}},
        }

        mapping = tool_schema_to_questions("tool", parameters)

        assert mapping.skipped == []
        assert len(mapping.questions) == 1
        assert mapping.questions[0].kind is QuestionKind.SCORE
        assert mapping.questions[0].levels == (1, 2, 4)

    def test_partial_mapping_skips_unsupported_without_raising(self):
        parameters = {
            "type": "object",
            "properties": {
                "free_text": {"type": "string"},
                "blob": {"type": "object"},
                "unbounded": {"type": "integer"},
                "one_sided": {"type": "integer", "minimum": 0},
                "too_wide": {"type": "integer", "minimum": 0, "maximum": 100},
                "open_items": {"type": "array", "items": {"type": "string"}},
            },
        }

        mapping = tool_schema_to_questions("tool", parameters)

        assert mapping.questions == []
        assert len(mapping.skipped) == 6
        assert all(
            reason.startswith(("free_text:", "blob:", "unbounded:", "one_sided:"))
            for reason in mapping.skipped[:4]
        )
        assert "too_wide:" in mapping.skipped[4]
        assert "open_items:" in mapping.skipped[5]

    def test_bounds_boundary_is_inclusive_at_the_cap(self):
        at_cap = {
            "type": "object",
            "properties": {"level": {"type": "integer", "minimum": 0, "maximum": 15}},
        }
        over_cap = {
            "type": "object",
            "properties": {"level": {"type": "integer", "minimum": 0, "maximum": 16}},
        }

        mapped = tool_schema_to_questions("tool", at_cap)
        skipped = tool_schema_to_questions("tool", over_cap)

        assert mapped.questions[0].levels == tuple(range(16))
        assert skipped.questions == []
        assert len(skipped.skipped) == 1

    def test_question_ids_are_stable_across_calls(self):
        first = _mapping()
        second = _mapping()

        assert [question.id for question in first.questions] == [
            question.id for question in second.questions
        ]
        assert first.questions[3].id == "tags__alpha"

    def test_non_object_schema_raises_typed_error(self):
        with pytest.raises(ToolArgumentError) as excinfo:
            tool_schema_to_questions("tool", {"type": "array", "items": {"type": "string"}})

        assert excinfo.value.reasons
        assert "object" in str(excinfo.value)

    def test_non_mapping_parameters_raises_typed_error(self):
        with pytest.raises(ToolArgumentError):
            tool_schema_to_questions("tool", ["not", "a", "schema"])


# ── 2. Decisions -> arguments ─────────────────────────────────────────────


class TestAssembleArguments:
    def test_full_round_trip_and_schema_validation(self):
        mapping = _mapping()
        decisions = _decisions(
            mapping,
            {
                "mode": "fast",
                "dry_run": True,
                "retries": 2,
                "tags__alpha": True,
                "tags__beta": False,
                "tags__gamma": False,
            },
        )

        assembled = assemble_arguments(mapping.questions, decisions, _TOOL_PARAMETERS)

        assert assembled == {"mode": "fast", "dry_run": True, "retries": 2, "tags": ["alpha"]}
        Draft202012Validator(_TOOL_PARAMETERS).validate(assembled)

    def test_optional_unanswered_arguments_are_omitted(self):
        mapping = _mapping()

        assembled = assemble_arguments(
            mapping.questions,
            _decisions(mapping, {"mode": "safe"}),
            _TOOL_PARAMETERS,
        )

        assert assembled == {"mode": "safe"}
        Draft202012Validator(_TOOL_PARAMETERS).validate(assembled)

    def test_missing_required_argument_raises_with_reasons(self):
        mapping = _mapping()

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(
                mapping.questions,
                _decisions(mapping, {"retries": 1}),
                _TOOL_PARAMETERS,
            )

        assert any("'mode'" in reason for reason in excinfo.value.reasons)

    def test_value_outside_declared_enum_raises(self):
        mapping = _mapping()
        decisions = _decisions(mapping, {"mode": "warp"})

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(mapping.questions, decisions, _TOOL_PARAMETERS)

        assert any("outside the declared" in reason for reason in excinfo.value.reasons)

    def test_integer_decision_outside_levels_raises(self):
        mapping = _mapping()
        decisions = _decisions(mapping, {"mode": "fast", "retries": 9})

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(mapping.questions, decisions, _TOOL_PARAMETERS)

        assert any("declared levels" in reason for reason in excinfo.value.reasons)

    def test_array_multiselect_is_rejected(self):
        mapping = _mapping()
        decisions = _decisions(
            mapping,
            {
                "mode": "fast",
                "tags__alpha": True,
                "tags__beta": True,
                "tags__gamma": False,
            },
        )

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(mapping.questions, decisions, _TOOL_PARAMETERS)

        assert any("single-select" in reason for reason in excinfo.value.reasons)

    def test_partial_array_answers_are_rejected_not_defaulted(self):
        mapping = _mapping()
        decisions = _decisions(mapping, {"mode": "fast", "tags__alpha": False})

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(mapping.questions, decisions, _TOOL_PARAMETERS)

        assert any("unanswered" in reason for reason in excinfo.value.reasons)

    def test_required_unsupported_argument_raises(self):
        parameters = {
            "type": "object",
            "properties": {"free_text": {"type": "string"}},
            "required": ["free_text"],
        }
        mapping = tool_schema_to_questions("tool", parameters)

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(mapping.questions, [], parameters)

        assert any("not mappable" in reason for reason in excinfo.value.reasons)

    def test_decisions_as_mapping_by_question_id(self):
        mapping = _mapping()
        by_id = {
            decision.question_id: decision for decision in _decisions(mapping, {"mode": "safe"})
        }

        assembled = assemble_arguments(mapping.questions, by_id, _TOOL_PARAMETERS)

        assert assembled == {"mode": "safe"}

    def test_non_decision_record_is_rejected(self):
        mapping = _mapping()

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(
                mapping.questions,
                [{"question_id": "mode", "value": "fast"}],
                _TOOL_PARAMETERS,
            )

        assert any("not Decision" in reason for reason in excinfo.value.reasons)


# ── 3. Runner -> assemble end to end ──────────────────────────────────────


class _FakePrimitives:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[dict] = []

    def llm_call(self, prompt: str, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return self.response


def _runner_response(questions: Sequence[Question]) -> str:
    answers: dict[str, dict] = {}
    for question in questions:
        if question.kind is QuestionKind.CHOICE:
            labels = list(question.options)
            answers[question.id] = {
                "choice": labels[0],
                "probabilities": {label: 1.0 / len(labels) for label in labels},
                "confidence": 0.5,
            }
        elif question.kind is QuestionKind.SCORE:
            labels = [str(level) for level in question.levels]
            answers[question.id] = {
                "score": question.levels[-1],
                "probabilities": {label: 1.0 / len(labels) for label in labels},
                "confidence": 0.5,
            }
        else:
            answers[question.id] = {
                "noul": question.id.endswith("__beta"),
                "probabilities": {"true": 0.5, "false": 0.5},
                "confidence": 0.5,
            }
    return json.dumps({"answers": answers})


class TestRunnerToAssembly:
    def test_mapped_catalogue_runs_and_assembles_to_a_valid_argument_dict(self):
        mapping = _mapping()
        primitives = _FakePrimitives(_runner_response(mapping.questions))

        result = run_typed_decisions(
            primitives,
            state=STATE,
            questions=mapping.questions,
            role=ROLE,
        )
        assembled = assemble_arguments(mapping.questions, result.decisions, _TOOL_PARAMETERS)

        assert result.failures == ()
        assert assembled == {
            "mode": "fast",
            "dry_run": False,
            "retries": 3,
            "tags": ["beta"],
        }
        Draft202012Validator(_TOOL_PARAMETERS).validate(assembled)
        assert len(primitives.calls) == 1

    def test_assembled_dict_failing_a_schema_constraint_raises(self):
        parameters = {
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": ["fast", "safe"]}},
            "required": ["mode"],
            "minProperties": 2,
        }
        mapping = tool_schema_to_questions("tool", parameters)
        decisions = _decisions(mapping, {"mode": "fast"})

        with pytest.raises(ToolArgumentError) as excinfo:
            assemble_arguments(mapping.questions, decisions, parameters)

        assert any("schema validation failed" in reason for reason in excinfo.value.reasons)
