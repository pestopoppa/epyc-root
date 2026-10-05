"""TD-21.9 / TD-21.10 / TD-21.15: judge OUTPUT SHAPE, behind CONSTRAIN_JUDGE_OUTPUT.

Covers, per `handoffs/active/typed-decision-plane.md` TD-21.9/21.10/21.15/21.32:

* TD-21.9  — `debug_scorer._score_llm_judge` / `_parse_judge_boolean_verdict`
  (orchestrator `/chat` branch): flag OFF is the pre-existing prefix-match
  parse, byte-identical; flag ON is a strict true/false parse that raises
  `ScoringUnavailableError` (never `AnswerParseError`) on anything else.
* TD-21.10 — `debug_scorer.request_llm_judge_text` raw llama-server branch:
  flag OFF never sends a schema (today's behaviour, the defect the handoff
  names); flag ON sends the same schema as an OpenAI `response_format`.
* TD-21.15 — `eval_tower.EvalTower._rubric_scores_for_answer`: flag OFF never
  sends `output_schema` and never spends a repair call; flag ON sends
  `RUBRIC_JUDGE_SCHEMA` and spends exactly one `parse_with_repair` extraction
  turn against the SAME judge role when the lenient fisher finds nothing.
* The judge-parse-outcome counters (`debug_scorer.judge_parse_stats`) are
  always on, independent of the flag, and zero-score-effect.

AUTOUSE fixture below forces httpx.post to raise if any test forgets to
supply its own fake — nothing here reaches a live server, and a missing fake
fails LOUDLY rather than silently hanging on a real socket.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT))

import debug_scorer  # noqa: E402
from debug_scorer import ScoringUnavailableError, request_llm_judge_text, score_answer  # noqa: E402

import eval_tower  # noqa: E402
from eval_tower import EvalTower  # noqa: E402
from rubric_scoring import RUBRIC_JUDGE_SCHEMA  # noqa: E402

# eval_tower reaches debug_scorer through `_load_orchestrator_debug_scorer()`
# (a private, module-identity-safe `importlib` load under the
# `epyc_orch_debug_scorer` sys.modules key — see `seeding_scoring.py`), which
# is a DIFFERENT Python module object than the bare `import debug_scorer`
# above even though both load the same file. TD-21.15 tests below must read
# and mutate the SAME object `_rubric_scores_for_answer` actually reads, or
# they would be testing a module nothing production touches.
orch_scorer = eval_tower._load_orchestrator_debug_scorer()

# Captured at IMPORT/collection time, before any fixture below (or any other
# test file sharing this process) can mutate the module attribute — same
# reasoning as `test_debug_scorer_td21_parse_exclusion.py`'s
# `_SHIPPED_DEFAULT_ON_IMPORT` (EQ1_RATIFICATION_TEST_SENTINEL): pytest
# imports every test module during COLLECTION, before any test body or
# fixture runs, so this reflects the module's real top-level default
# regardless of collection order.
_JUDGE_SHIPPED_DEFAULT_ON_IMPORT = debug_scorer.CONSTRAIN_JUDGE_OUTPUT


def test_judge_shipped_default_matches_ratification_state():
    """Pins CONSTRAIN_JUDGE_OUTPUT's SHIPPED value to the ratification state.

    Pre-ratification (today): ships False — every judge site above is
    byte-identical to pre-TD-21.9/21.10/21.15. The extended ratification
    script (`scripts/operator/ratify_eq1_answer_parse_exclusion_20260924.sh`,
    which now also flips this flag alongside EXCLUDE_UNPARSEABLE_ANSWERS)
    performs the matching update here as part of --apply, via its own
    anchor-based single-occurrence replace on this sentinel and its paired
    assertion, so this test is never stale after a real ratification run —
    only after a hand-edit that skips the script.
    #CJO1_RATIFICATION_TEST_SENTINEL: CONSTRAIN_JUDGE_OUTPUT ships True (ratified — see instrument_eras.yaml E19)
    """
    assert _JUDGE_SHIPPED_DEFAULT_ON_IMPORT is True


@pytest.fixture(autouse=True)
def _no_live_http(monkeypatch):
    """Refuse any HTTP call this module's own fixtures did not explicitly fake.

    Hard rule: tests must never reach a live server. Every test below either
    overrides this with its own `fake_post`/`fake_call_orchestrator_forced`
    fixture, or never triggers a network call at all.
    """

    def _forbidden_post(*args, **kwargs):
        raise AssertionError("test attempted a live httpx.post — add a fake first")

    monkeypatch.setattr(httpx, "post", _forbidden_post)

    def _forbidden_call_orchestrator_forced(*args, **kwargs):
        raise AssertionError(
            "test attempted a live call_orchestrator_forced — add a fake first"
        )

    monkeypatch.setattr(
        eval_tower, "call_orchestrator_forced", _forbidden_call_orchestrator_forced
    )
    yield


def _reset_scorer_state(scorer) -> None:
    scorer.CONSTRAIN_JUDGE_OUTPUT = False
    scorer.reset_judge_parse_stats(arm_key=None)
    scorer.reset_parse_failure_stats(arm_key=None)
    for arm_key in ("arm-a", "arm-b", "arm-x", "arm-y", "arm-z"):
        scorer.reset_judge_parse_stats(arm_key=arm_key)
        scorer.reset_parse_failure_stats(arm_key=arm_key)


@pytest.fixture(autouse=True)
def _reset_judge_flag_and_counters():
    """Flag starts OFF for every test and is always restored; counters cleared.

    Resets BOTH module objects (see the `orch_scorer` comment above): the
    bare `debug_scorer` import the TD-21.9/21.10 tests use directly, and the
    `_load_orchestrator_debug_scorer()` singleton the TD-21.15 tests exercise
    through `eval_tower`.
    """
    _reset_scorer_state(debug_scorer)
    _reset_scorer_state(orch_scorer)
    yield
    _reset_scorer_state(debug_scorer)
    _reset_scorer_state(orch_scorer)


# ─────────────────────────────────────────────────────────────── TD-21.9/21.10


class _Resp:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._body


@pytest.fixture
def orchestrator_judge(monkeypatch):
    """Fakes the orchestrator `/chat` branch (`use_orchestrator=True`)."""
    calls: list[dict[str, Any]] = []
    replies: list[dict[str, Any]] = []

    def fake_post(url, json=None, timeout=None):  # noqa: A002
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _Resp(replies.pop(0))

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.delenv("ORCHESTRATOR_API_URL", raising=False)
    return calls, replies


@pytest.fixture
def raw_judge(monkeypatch):
    """Fakes the raw llama-server override branch (`judge_host`+`judge_port`)."""
    calls: list[dict[str, Any]] = []
    replies: list[dict[str, Any]] = []

    def fake_post(url, json=None, timeout=None):  # noqa: A002
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _Resp(replies.pop(0))

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls, replies


def test_flag_off_boolean_judge_is_prefix_match_byte_identical(orchestrator_judge):
    calls, replies = orchestrator_judge
    assert debug_scorer.CONSTRAIN_JUDGE_OUTPUT is False

    # A prefix-match artifact: this is NOT exactly "true", but the legacy
    # `.lower().startswith("true")` scores it True. Byte-identical means it
    # still does under the flag's default.
    replies.append({"answer": "truely not the same, but close"})
    assert score_answer("answer", "reference", "llm_judge", {}) is True

    replies.append({"answer": "false, they differ"})
    assert score_answer("answer", "reference", "llm_judge", {}) is False
    assert len(calls) == 2


def test_flag_off_raw_branch_never_sends_schema_identical_request(raw_judge):
    """TD-21.10: the explicit identical-request test for the raw branch.

    This is the one branch this change touches even at flag-OFF time (the
    orchestrator branch's payload was already covered and unchanged — see
    `test_debug_scorer_nugget_judge_transport.py`), so it gets its own
    identical-request pin: no `response_format` key appears on the wire
    regardless of what `output_schema` the caller supplies.
    """
    calls, replies = raw_judge
    replies.append({"choices": [{"message": {"content": "true"}}]})
    text = request_llm_judge_text(
        "P",
        {"judge_host": "127.0.0.1", "judge_port": 8082},
        max_tokens=8,
        output_schema={"type": "boolean"},
    )
    assert text == "true"
    assert len(calls) == 1
    body = calls[0]["json"]
    assert "response_format" not in body
    assert body == {
        "messages": [{"role": "user", "content": "P"}],
        "max_tokens": 8,
        "temperature": 0.0,
    }


def test_flag_on_boolean_judge_strict_parse(orchestrator_judge):
    debug_scorer.CONSTRAIN_JUDGE_OUTPUT = True
    calls, replies = orchestrator_judge

    replies.append({"answer": "true"})
    assert score_answer("answer", "reference", "llm_judge", {}) is True

    replies.append({"answer": "false"})
    assert score_answer("answer", "reference", "llm_judge", {}) is False
    assert len(calls) == 2


def test_flag_on_boolean_judge_unparseable_raises_scoring_unavailable_not_answer_parse(
    orchestrator_judge,
):
    debug_scorer.CONSTRAIN_JUDGE_OUTPUT = True
    _, replies = orchestrator_judge

    # A prefix-match would have accepted this as True; strict parse must not.
    replies.append({"answer": "truely not the same, but close"})
    with pytest.raises(ScoringUnavailableError, match="llm_judge_unparseable_verdict") as exc:
        score_answer("answer", "reference", "llm_judge", {})
    # Explicitly NOT the model-side AnswerParseError subclass (TD-21.11..21.14
    # is a different failure class from a judge-side parse failure).
    assert not isinstance(exc.value, debug_scorer.AnswerParseError)


def test_flag_on_raw_branch_sends_response_format_schema(raw_judge):
    debug_scorer.CONSTRAIN_JUDGE_OUTPUT = True
    calls, replies = raw_judge
    replies.append({"choices": [{"message": {"content": "true"}}]})
    request_llm_judge_text(
        "P",
        {"judge_host": "127.0.0.1", "judge_port": 8082},
        max_tokens=8,
        output_schema={"type": "boolean"},
    )
    body = calls[0]["json"]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "llm_judge_verdict", "schema": {"type": "boolean"}},
    }


def test_judge_parse_counters_always_on_regardless_of_flag(orchestrator_judge):
    """Counters observe the STRICT outcome even while the flag stays OFF."""
    _, replies = orchestrator_judge
    replies.append({"answer": "true"})
    score_answer("answer", "reference", "llm_judge", {})
    replies.append({"answer": "truely not"})  # strictly unparseable, but flag OFF
    score_answer("answer", "reference", "llm_judge", {})

    stats = debug_scorer.judge_parse_stats(arm_key=None)
    assert stats["llm_judge_boolean"] == {"parsed": 1, "unparseable": 1}


def test_judge_parse_counters_bucketed_by_arm_key_and_resettable(orchestrator_judge):
    _, replies = orchestrator_judge
    replies.append({"answer": "true"})
    score_answer("answer", "reference", "llm_judge", {"_eval_batch_id": "arm-a"})
    replies.append({"answer": "true"})
    score_answer("answer", "reference", "llm_judge", {"_eval_batch_id": "arm-b"})

    assert debug_scorer.judge_parse_stats(arm_key="arm-a") == {
        "llm_judge_boolean": {"parsed": 1}
    }
    assert debug_scorer.judge_parse_stats(arm_key="arm-b") == {
        "llm_judge_boolean": {"parsed": 1}
    }
    debug_scorer.reset_judge_parse_stats(arm_key="arm-a")
    assert debug_scorer.judge_parse_stats(arm_key="arm-a") == {}
    assert debug_scorer.judge_parse_stats(arm_key="arm-b") == {
        "llm_judge_boolean": {"parsed": 1}
    }
    debug_scorer.reset_judge_parse_stats(arm_key="arm-b")


# ────────────────────────────────────────────────────────────────── TD-21.15


def _mk_tower(monkeypatch):
    tower = EvalTower()
    monkeypatch.setattr(eval_tower, "check_cross_family_status", lambda gen, role: (True, "cross_family"))
    monkeypatch.setenv("AUTOPILOT_RUBRIC_JUDGE_ROLES", "architect_general")
    return tower


def _fake_call_orchestrator_forced(monkeypatch, responses: list[dict[str, Any]]):
    calls: list[dict[str, Any]] = []

    def fake(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    monkeypatch.setattr(eval_tower, "call_orchestrator_forced", fake)
    return calls


def test_rubric_flag_off_never_sends_schema_and_no_repair_call(monkeypatch):
    tower = _mk_tower(monkeypatch)
    calls = _fake_call_orchestrator_forced(
        monkeypatch, [{"answer": "not json at all, unparseable"}]
    )

    scores, source = tower._rubric_scores_for_answer(
        q={"prompt": "p", "_eval_batch_id": "arm-x"},
        answer="the model's answer",
        generator_model="worker_general",
        tool_events=[],
        client=object(),
    )

    assert len(calls) == 1  # no repair call spent
    assert calls[0].get("output_schema") is None
    assert source == "heuristic_fallback"
    stats = orch_scorer.judge_parse_stats(arm_key="arm-x")
    assert stats["rubric_judge"] == {"unparseable": 1}


def test_rubric_flag_off_parsed_reply_is_unchanged(monkeypatch):
    tower = _mk_tower(monkeypatch)
    calls = _fake_call_orchestrator_forced(
        monkeypatch,
        [{"answer": '{"scores": {"factual_accuracy": 0.8}}'}],
    )

    scores, source = tower._rubric_scores_for_answer(
        q={"prompt": "p", "_eval_batch_id": "arm-x"},
        answer="the model's answer",
        generator_model="worker_general",
        tool_events=[],
        client=object(),
    )

    assert len(calls) == 1
    assert calls[0].get("output_schema") is None
    assert source == "judge"
    assert scores["factual_accuracy"] == 0.8
    stats = orch_scorer.judge_parse_stats(arm_key="arm-x")
    assert stats["rubric_judge"] == {"parsed": 1}


def test_rubric_flag_on_sends_schema_and_repairs_on_miss(monkeypatch):
    orch_scorer.CONSTRAIN_JUDGE_OUTPUT = True
    tower = _mk_tower(monkeypatch)
    calls = _fake_call_orchestrator_forced(
        monkeypatch,
        [
            {"answer": "not json at all, unparseable"},
            {"answer": '{"scores": {"factual_accuracy": 0.6}}'},
        ],
    )

    scores, source = tower._rubric_scores_for_answer(
        q={"prompt": "p", "_eval_batch_id": "arm-y"},
        answer="the model's answer",
        generator_model="worker_general",
        tool_events=[],
        client=object(),
    )

    assert len(calls) == 2
    assert calls[0]["output_schema"] == RUBRIC_JUDGE_SCHEMA
    # The repair turn sends the TD-21.35 relaxed WIRE schema (required dropped, validated
    # against the original afterwards); the judge turn above keeps the full schema.
    from src.structured_output.repair import _relax_required_for_wire
    assert calls[1]["output_schema"] == _relax_required_for_wire(RUBRIC_JUDGE_SCHEMA)
    assert calls[1]["scoring_method"] == "rubric_judge_repair"
    assert source == "judge"
    assert scores["factual_accuracy"] == 0.6
    stats = orch_scorer.judge_parse_stats(arm_key="arm-y")
    assert stats["rubric_judge"] == {"repaired": 1}


def test_rubric_flag_on_falls_back_when_repair_also_fails(monkeypatch):
    orch_scorer.CONSTRAIN_JUDGE_OUTPUT = True
    tower = _mk_tower(monkeypatch)
    calls = _fake_call_orchestrator_forced(
        monkeypatch,
        [
            {"answer": "still not json"},
            {"answer": "still not json after repair either"},
        ],
    )

    scores, source = tower._rubric_scores_for_answer(
        q={"prompt": "p", "_eval_batch_id": "arm-z"},
        answer="the model's answer",
        generator_model="worker_general",
        tool_events=[],
        client=object(),
    )

    assert len(calls) == 2
    assert source == "heuristic_fallback"
    stats = orch_scorer.judge_parse_stats(arm_key="arm-z")
    assert stats["rubric_judge"] == {"unparseable": 1}
