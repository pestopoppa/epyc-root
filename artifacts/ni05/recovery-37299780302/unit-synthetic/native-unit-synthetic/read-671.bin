"""Tests for FINAL() output-schema validation (Fast-RLM pattern).

Covers the three helpers introduced in src/graph/helpers.py plus the
ChatRequest plumbing and feature-flag declaration.

Implementation surface:
- src/features.py:    final_schema_validation flag (default-off)
- src/api/models/requests.py: ChatRequest.output_schema (default-None)
- src/graph/helpers.py: _render_schema_preamble,
                        _validate_final_answer,
                        _format_validation_failure_message
- src/api/routes/chat_pipeline/repl_executor.py: integrated retry-on-failure
  pass within _execute_repl (covered indirectly here; full-pipeline coverage
  lives in test_repl_executor.py with heavy mocking).
"""

import json

from pydantic import BaseModel

from src.api.models import ChatRequest
from src.features import features as get_features
from src.graph.helpers import (
    _format_validation_failure_message,
    _render_schema_preamble,
    _validate_final_answer,
)


# ── Helper: _validate_final_answer ──────────────────────────────────────


class _PydModel(BaseModel):
    answer: str
    score: int


def test_validate_accepts_pydantic_schema():
    schema = _PydModel.model_json_schema()
    payload = json.dumps({"answer": "hello", "score": 7})
    ok, err, parsed = _validate_final_answer(payload, schema)
    assert ok is True
    assert err is None
    assert parsed == {"answer": "hello", "score": 7}


def test_validate_accepts_raw_jsonschema_dict():
    schema = {"type": "integer", "minimum": 0}
    ok, err, parsed = _validate_final_answer("42", schema)
    assert ok is True and err is None and parsed == 42


def test_validate_accepts_primitive_int_via_typeadapter():
    # Raw type passed to TypeAdapter (e.g. an int spec)
    schema = {"type": "string"}
    ok, err, parsed = _validate_final_answer('"hi"', schema)
    assert ok is True and parsed == "hi"


def test_validate_rejects_invalid_json():
    schema = {"type": "object"}
    ok, err, _ = _validate_final_answer("not valid json{", schema)
    assert ok is False
    assert err and "not valid JSON" in err


def test_validate_rejects_schema_mismatch():
    schema = _PydModel.model_json_schema()
    payload = json.dumps({"answer": "hello"})  # missing 'score'
    ok, err, _ = _validate_final_answer(payload, schema)
    assert ok is False
    assert err  # pydantic error message present


# ── Helper: _render_schema_preamble ─────────────────────────────────────


def test_preamble_contains_schema_and_final_hint():
    schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    text = _render_schema_preamble(schema)
    assert "FINAL" in text
    assert "json.dumps" in text  # example hint
    assert "integer" in text  # schema is embedded


# ── Helper: _format_validation_failure_message ──────────────────────────


def test_failure_message_includes_schema_error_and_rejected():
    schema = {"type": "integer"}
    msg = _format_validation_failure_message(
        schema, "value must be int", '"not an int"'
    )
    assert "schema validation" in msg.lower()
    assert "integer" in msg
    assert "value must be int" in msg
    assert "not an int" in msg
    assert "State is preserved" in msg


def test_failure_message_truncates_long_rejected_value():
    schema = {"type": "string"}
    rejected = "x" * 2000
    msg = _format_validation_failure_message(schema, "err", rejected, max_rejected_chars=100)
    assert "[truncated" in msg
    assert msg.count("x") <= 110  # 100 plus a little slack for the trailing marker


# ── ChatRequest plumbing ────────────────────────────────────────────────


def test_chat_request_accepts_output_schema_dict():
    req = ChatRequest(prompt="hi", output_schema={"type": "string"})
    assert req.output_schema == {"type": "string"}


def test_chat_request_output_schema_defaults_none():
    req = ChatRequest(prompt="hi")
    assert req.output_schema is None


# ── Feature flag ─────────────────────────────────────────────────────────


def test_final_schema_validation_flag_exists_and_default_off():
    f = get_features()
    assert hasattr(f, "final_schema_validation")
    assert f.final_schema_validation is False


def test_final_schema_validation_flag_in_registry_default_off_in_prod():
    """Registry entry must have default_prod=False — opt-in per request only."""
    from src.features import _FEATURE_REGISTRY

    spec = next(s for s in _FEATURE_REGISTRY if s.name == "final_schema_validation")
    assert spec.default_test is False
    assert spec.default_prod is False
    assert spec.env_var == "FINAL_SCHEMA_VALIDATION"
