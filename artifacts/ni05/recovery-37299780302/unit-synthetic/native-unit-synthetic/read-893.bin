"""Unit tests for the TD-5 typed-decision shadow (src/typed_decisions/shadow).

Fake-primitives pattern borrowed from ``tests/unit/test_typed_decisions.py``
(one canned response, captured call kwargs). No model/server call; the
background executor is drained explicitly at every task boundary.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from src.features import Features, reset_features, set_features
from src.typed_decisions import Question, QuestionKind
from src.typed_decisions import shadow
from src.typed_decisions.shadow import (
    ENV_LOG_PATH,
    MAX_PENDING,
    drain_shadow,
    shadow_decision,
    shadow_stats,
    submit_shadow,
)

ROLE = "worker_general"
STATE = "unit-test state: choose the serving role for the request below."
ROLES = ("worker_math", "worker_general", "frontdoor")


class _FakePrimitives:
    """Canned-response stand-in for ``LLMPrimitives`` (last response repeats)."""

    def __init__(self, responses: str | Sequence[str]):
        if isinstance(responses, str):
            responses = [responses]
        self.responses = list(responses)
        self.calls: list[dict] = []

    def llm_call(self, prompt: str, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


class _GatedPrimitives:
    """Blocks every call until ``gate`` is set, for bound/drop tests."""

    def __init__(self, response: str, gate: threading.Event):
        self.response = response
        self.gate = gate
        self.calls = 0

    def llm_call(self, prompt: str, **kwargs):
        self.calls += 1
        self.gate.wait(timeout=10)
        return self.response


def _questions() -> tuple[Question, ...]:
    return (
        Question(id="role", kind=QuestionKind.CHOICE, text="Pick a role.", options=ROLES),
        Question(id="requires_escalation", kind=QuestionKind.NOUL, text="Escalate?"),
    )


def _valid_response(questions: Sequence[Question]) -> str:
    answers: dict[str, dict] = {}
    for question in questions:
        if question.kind is QuestionKind.CHOICE:
            labels = list(question.options)
            answers[question.id] = {
                "choice": labels[0],
                "probabilities": {label: 1.0 / len(labels) for label in labels},
                "confidence": 0.7,
            }
        else:
            answers[question.id] = {
                "noul": False,
                "probabilities": {"true": 0.25, "false": 0.75},
                "confidence": 0.75,
            }
    return json.dumps({"answers": answers})


_RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": [
        "timestamp",
        "surface",
        "mode",
        "role",
        "order",
        "state_sha256",
        "prompt_sha256",
        "decisions",
        "failures",
        "incumbent",
        "elapsed_ms",
    ],
    "properties": {
        "timestamp": {"type": "string", "minLength": 20},
        "surface": {"type": "string"},
        "mode": {"type": "string"},
        "role": {"type": "string"},
        "order": {"type": "array", "items": {"type": "string"}},
        "state_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "prompt_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "kind", "value", "confidence", "probabilities"],
                "properties": {
                    "id": {"type": "string"},
                    "kind": {"enum": ["choice", "score", "noul"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "probabilities": {
                        "type": "object",
                        "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            },
        },
        "failures": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["reason", "detail"],
                "properties": {
                    "reason": {"type": "string"},
                    "detail": {"type": "string"},
                },
            },
        },
        "incumbent": {"type": "object"},
        "elapsed_ms": {"type": "number", "minimum": 0},
    },
}

_ERROR_RECORD_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["timestamp", "status", "error", "surface", "mode", "role"],
    "properties": {
        "timestamp": {"type": "string", "minLength": 20},
        "status": {"const": "shadow_error"},
        "error": {"type": "string", "minLength": 1},
        "surface": {"type": "string"},
        "mode": {"type": "string"},
        "role": {"type": "string"},
    },
}


@pytest.fixture(autouse=True)
def _clean_shadow(monkeypatch):
    reset_features()
    shadow._reset_for_tests()
    monkeypatch.delenv(ENV_LOG_PATH, raising=False)
    yield
    shadow._reset_for_tests()
    reset_features()


def _enable(monkeypatch, log_path: Path) -> None:
    set_features(Features(typed_decisions_shadow=True))
    monkeypatch.setenv(ENV_LOG_PATH, str(log_path))


def _records(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line]


# ── 1. Flag / sink gating ──────────────────────────────────────────────────


def test_flag_off_submit_shadow_is_a_noop(tmp_path, monkeypatch):
    log_path = tmp_path / "shadow.jsonl"
    primitives = _FakePrimitives(_valid_response(_questions()))

    queued = submit_shadow(
        primitives,
        surface="unit.test",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
        log_path=log_path,
    )
    drain_shadow()

    assert queued is False
    assert not log_path.exists()
    assert primitives.calls == []
    assert shadow_stats() == {"pending": 0, "dropped": 0, "bound": MAX_PENDING}


def test_flag_on_without_log_path_is_a_noop(tmp_path, monkeypatch):
    set_features(Features(typed_decisions_shadow=True))
    primitives = _FakePrimitives(_valid_response(_questions()))

    queued = submit_shadow(
        primitives,
        surface="unit.test",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
        log_path=None,
    )
    drain_shadow()

    assert queued is False
    assert primitives.calls == []


# ── 2. Record shape ────────────────────────────────────────────────────────


def test_shadow_decision_appends_one_well_formed_record(tmp_path):
    log_path = tmp_path / "nested" / "shadow.jsonl"
    questions = _questions()
    primitives = _FakePrimitives(_valid_response(questions))

    shadow_decision(
        primitives,
        surface="unit.surface",
        state=STATE,
        questions=questions,
        incumbent={"roles": list(ROLES), "strategy": "rules", "task_id": "chat-1"},
        role=ROLE,
        log_path=log_path,
    )

    rows = _records(log_path)
    assert len(rows) == 1
    record = rows[0]
    Draft202012Validator(_RECORD_SCHEMA).validate(record)

    assert record["surface"] == "unit.surface"
    assert record["mode"] == "json"
    assert record["role"] == ROLE
    assert record["order"] == ["role", "requires_escalation"]
    assert record["state_sha256"] == hashlib.sha256(STATE.encode("utf-8")).hexdigest()
    assert (
        record["prompt_sha256"]
        == hashlib.sha256(primitives.calls[0]["prompt"].encode()).hexdigest()
    )
    assert record["incumbent"] == {"roles": list(ROLES), "strategy": "rules", "task_id": "chat-1"}
    assert record["failures"] == []
    assert record["elapsed_ms"] >= 0
    assert datetime.fromisoformat(record["timestamp"]).tzinfo is not None

    decisions = {decision["id"]: decision for decision in record["decisions"]}
    assert set(decisions) == {"role", "requires_escalation"}
    for decision in decisions.values():
        probabilities = decision["probabilities"]
        assert list(probabilities) == sorted(probabilities)
        assert sum(probabilities.values()) == pytest.approx(1.0)
        assert 0.0 <= decision["confidence"] <= 1.0
    assert decisions["role"]["kind"] == "choice"
    assert decisions["role"]["value"] == ROLES[0]
    assert decisions["requires_escalation"]["kind"] == "noul"
    assert decisions["requires_escalation"]["value"] is False


def test_submit_shadow_writes_the_record_from_the_background_worker(tmp_path, monkeypatch):
    log_path = tmp_path / "shadow.jsonl"
    _enable(monkeypatch, log_path)
    primitives = _FakePrimitives(_valid_response(_questions()))

    assert submit_shadow(
        primitives,
        surface="unit.background",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
    )
    drain_shadow()

    rows = _records(log_path)
    assert len(rows) == 1
    assert rows[0]["surface"] == "unit.background"
    assert primitives.calls
    assert shadow_stats()["pending"] == 0


# ── 3. Fail-open contract ──────────────────────────────────────────────────


class _ExplodingPrimitives:
    def llm_call(self, prompt: str, **kwargs):
        raise RuntimeError("transport exploded")


def test_run_exception_becomes_shadow_error_and_never_propagates(tmp_path):
    log_path = tmp_path / "shadow.jsonl"

    shadow_decision(
        _ExplodingPrimitives(),
        surface="unit.explode",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
        log_path=log_path,
    )

    rows = _records(log_path)
    assert len(rows) == 1
    record = rows[0]
    Draft202012Validator(_ERROR_RECORD_SCHEMA).validate(record)
    assert record["status"] == "shadow_error"
    assert "RuntimeError" in record["error"]
    assert "transport exploded" in record["error"]


def test_garbage_return_becomes_shadow_error(tmp_path, monkeypatch):
    log_path = tmp_path / "shadow.jsonl"
    monkeypatch.setattr(shadow, "run_typed_decisions", lambda *args, **kwargs: "garbage")

    shadow_decision(
        _FakePrimitives(""),
        surface="unit.garbage",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
        log_path=log_path,
    )

    record = _records(log_path)[0]
    Draft202012Validator(_ERROR_RECORD_SCHEMA).validate(record)
    assert "DecisionResult" in record["error"]


def test_unwritable_sink_is_swallowed_and_logged(tmp_path, caplog, monkeypatch):
    # A directory used as the log file makes every append fail.
    log_path = tmp_path / "shadow.jsonl"
    log_path.mkdir()
    primitives = _FakePrimitives(_valid_response(_questions()))

    with caplog.at_level("WARNING", logger="src.typed_decisions.shadow"):
        shadow_decision(
            primitives,
            surface="unit.unwritable",
            state=STATE,
            questions=_questions(),
            incumbent={"roles": list(ROLES), "strategy": "rules"},
            role=ROLE,
            log_path=log_path,
        )

    assert primitives.calls  # the run itself happened; only the sink failed
    assert any("write failed" in message for message in caplog.messages)


# ── 4. Malformed emissions are recorded faithfully ─────────────────────────


def test_malformed_response_records_typed_failures(tmp_path):
    log_path = tmp_path / "shadow.jsonl"
    primitives = _FakePrimitives(json.dumps({"answers": {}}))

    shadow_decision(
        primitives,
        surface="unit.malformed",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
        log_path=log_path,
    )

    record = _records(log_path)[0]
    Draft202012Validator(_RECORD_SCHEMA).validate(record)
    assert record["decisions"] == []
    # Default max_retries=1: the first attempt plus its corrective retry.
    assert len(record["failures"]) == 2
    assert {failure["reason"] for failure in record["failures"]} == {"schema_violation"}
    assert all(failure["detail"] for failure in record["failures"])
    assert len(primitives.calls) == 2


def test_transport_error_marker_recorded_as_transport_failure(tmp_path):
    log_path = tmp_path / "shadow.jsonl"

    shadow_decision(
        _FakePrimitives("[ERROR: connection refused]"),
        surface="unit.transport",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
        log_path=log_path,
    )

    record = _records(log_path)[0]
    assert record["decisions"] == []
    assert [failure["reason"] for failure in record["failures"]] == ["transport_error"]


# ── 5. Bounded worker ──────────────────────────────────────────────────────


def test_excess_submissions_are_dropped_and_counted(tmp_path, monkeypatch):
    log_path = tmp_path / "shadow.jsonl"
    _enable(monkeypatch, log_path)
    gate = threading.Event()
    primitives = _GatedPrimitives(_valid_response(_questions()), gate)

    payload = dict(
        surface="unit.bound",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
    )
    accepted = [submit_shadow(primitives, **payload) for _ in range(MAX_PENDING + 3)]

    assert accepted.count(True) == MAX_PENDING
    assert accepted.count(False) == 3
    assert shadow_stats() == {"pending": MAX_PENDING, "dropped": 3, "bound": MAX_PENDING}

    gate.set()
    drain_shadow()

    assert shadow_stats()["pending"] == 0
    assert shadow_stats()["dropped"] == 3
    assert len(_records(log_path)) == MAX_PENDING


def test_background_worker_thread_is_a_daemon(tmp_path, monkeypatch):
    log_path = tmp_path / "shadow.jsonl"
    _enable(monkeypatch, log_path)
    gate = threading.Event()
    primitives = _GatedPrimitives(_valid_response(_questions()), gate)

    assert submit_shadow(
        primitives,
        surface="unit.daemon",
        state=STATE,
        questions=_questions(),
        incumbent={"roles": list(ROLES), "strategy": "rules"},
        role=ROLE,
    )
    assert shadow._executor is not None
    threads = list(shadow._executor._threads)
    assert threads, "expected the first submit to start the worker"

    gate.set()
    drain_shadow()

    assert all(thread.daemon for thread in threads)


# ── 6. Routing-plane helper ────────────────────────────────────────────────


def test_route_questions_puts_incumbent_first_and_stays_bounded():
    questions = shadow.route_questions(["worker_math"])

    assert len(questions) <= 3
    assert questions[0].kind is QuestionKind.CHOICE
    assert questions[0].options[0] == "worker_math"
    assert len(questions[0].options) >= 2
    assert len(set(questions[0].options)) == len(questions[0].options)
    assert questions[1].kind is QuestionKind.NOUL


def test_submit_route_shadow_passes_incumbent_verbatim(monkeypatch):
    captured: dict = {}

    def _capture(primitives, **kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(shadow, "submit_shadow", _capture)
    set_features(Features(typed_decisions_shadow=True))

    queued = shadow.submit_route_shadow(
        object(),
        prompt="summarize the incident report",
        context="context body",
        incumbent_roles=["worker_math", "frontdoor"],
        strategy="learned",
        task_id="chat-abcd1234",
    )

    assert queued is True
    assert captured["incumbent"] == {
        "roles": ["worker_math", "frontdoor"],
        "strategy": "learned",
        "task_id": "chat-abcd1234",
    }
    assert captured["surface"] == "chat_pipeline.routing"
    assert captured["role"] == "worker_general"
    assert [question.id for question in captured["questions"]] == ["role", "requires_escalation"]
    assert captured["questions"][0].options[0] == "worker_math"


def test_submit_route_shadow_is_a_noop_when_flag_off(monkeypatch):
    called: list = []
    monkeypatch.setattr(shadow, "submit_shadow", lambda *args, **kwargs: called.append(1))

    assert (
        shadow.submit_route_shadow(object(), prompt="x", incumbent_roles=["worker_math"]) is False
    )
    assert called == []


def test_route_state_is_length_bounded():
    state = shadow._route_state("p" * 100_000, "c" * 100_000)

    assert len(state) <= shadow._MAX_ROUTE_PROMPT_CHARS + shadow._MAX_ROUTE_CONTEXT_CHARS + 64


# ── 7. Pipeline call site ──────────────────────────────────────────────────


def _stub_route():
    return SimpleNamespace(
        routing_decision=["worker_math"],
        routing_strategy="rules",
        task_ir={},
        task_id="chat-stub",
        factual_risk_mode="enforce",
        factual_risk_band="",
    )


def test_pipeline_call_site_flag_off_adds_no_shadow_work(monkeypatch):
    from src.api.routes.chat_pipeline import routing as routing_module

    def _explode(*args, **kwargs):
        raise AssertionError("shadow must not be invoked when the flag is off")

    monkeypatch.setattr("src.typed_decisions.shadow.submit_route_shadow", _explode)
    monkeypatch.setattr(routing_module, "_needs_plan_review", lambda *args, **kwargs: False)
    request = SimpleNamespace(real_mode=True, prompt="hi", context="")

    result = routing_module._plan_review_gate(request, _stub_route(), object(), object())

    assert result is None


def test_pipeline_call_site_submits_incumbent_when_flag_on(monkeypatch):
    from src.api.routes.chat_pipeline import routing as routing_module

    captured: dict = {}
    monkeypatch.setattr(
        "src.typed_decisions.shadow.submit_route_shadow",
        lambda primitives, **kwargs: captured.update(kwargs),
    )
    monkeypatch.setattr(routing_module, "_needs_plan_review", lambda *args, **kwargs: False)
    set_features(Features(typed_decisions_shadow=True))
    request = SimpleNamespace(real_mode=True, prompt="hi", context="ctx")

    result = routing_module._plan_review_gate(request, _stub_route(), object(), object())

    assert result is None
    # The call site relies on submit_route_shadow's own surface/role defaults;
    # it must forward the incumbent decision fields as plain values.
    assert captured["incumbent_roles"] == ["worker_math"]
    assert captured["strategy"] == "rules"
    assert captured["task_id"] == "chat-stub"
    assert captured["prompt"] == "hi"
    assert captured["context"] == "ctx"
