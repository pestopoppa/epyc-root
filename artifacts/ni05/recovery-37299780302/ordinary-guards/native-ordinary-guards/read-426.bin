"""INFRA-FAILED disposition: absence of a measurement must never score as WRONG.

Root cause (2026-08-03): a T1 calibration reported ``0% correct`` over 70
questions purely because the orchestrator API was down. A score of 0.0 for an
unreachable endpoint is a measurement that was NEVER MADE, reported as a
measurement that was made and failed — the fail-open family.

Every failure mode below was established by driving the REAL production
functions with a fake transport (no network, no server). Behaviour BEFORE the
fix, measured:

    HTTP 400 (FastAPI ``{"detail": ...}``) → ``task_failure``  → scored WRONG
    HTTP 400 (structured ``error_code``)   → ``task_failure``  → scored WRONG
    connection refused                     → ``infrastructure``→ excluded (ok)
    ReadTimeout("") (empty message)        → error == ""       → scored WRONG
    ReadTimeout("timed out")               → ``infrastructure``→ excluded (ok)
    200 with an unparseable body           → ``task_failure``  → scored WRONG
    200 with ``answer: ""``                → no error          → scored WRONG

The two that were already excluded were excluded only because their message
text happened to contain a listed substring. That is the defect: a classifier
that must RECOGNISE a failure in order to exclude it fails open on every
message it does not recognise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (
    str(_ROOT),
    str(_ROOT / "scripts" / "autopilot"),
    str(_ROOT / "scripts" / "benchmark"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src.autopilot_core.measurement_guards import (  # noqa: E402
    DISPOSITION_INFRA_FAILED,
    DISPOSITION_SCORED,
    DISPOSITION_SCORING_FAILED,
    DISPOSITION_TASK_FAILED,
    infra_failure_reason,
    legacy_error_type,
    measurement_disposition,
)


# ── Fake transport ───────────────────────────────────────────────────
#
# Constructs each failure condition without a server or a network call.


class _FakeResponse:
    def __init__(self, status_code, json_body=None, text="", raise_json=False):
        self.status_code = status_code
        self._json = json_body
        self.text = text
        self._raise_json = raise_json
        self.request = httpx.Request("POST", "http://localhost:8000/chat")

    def json(self):
        if self._raise_json:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"Client error '{self.status_code} Bad Request' for url "
                "'http://localhost:8000/chat'",
                request=self.request,
                response=self,  # type: ignore[arg-type]
            )


def _client(behavior):
    """An httpx.Client stand-in whose post() runs ``behavior``."""
    client = Mock()
    client.post.side_effect = lambda *a, **k: behavior()
    return client


def _call(behavior, monkeypatch, **kwargs):
    """Drive the real ``call_orchestrator_forced`` against a fake transport."""
    import seeding_orchestrator as _MOD

    # Collapse the eval reconnect budget so a connect failure terminates
    # immediately instead of sleeping through exponential backoff.
    monkeypatch.setenv("AUTOPILOT_EVAL_RECONNECT_MAX_S", "0")
    monkeypatch.setattr(_MOD.time, "sleep", lambda *_a, **_k: None)
    return _MOD.call_orchestrator_forced(
        prompt="What is 2+2?",
        force_role="worker_math",
        url="http://localhost:8000",
        timeout=60,
        client=_client(behavior),
        **kwargs,
    )


# ── The four transport failure modes, end to end ─────────────────────


def test_http_400_with_unstructured_body_is_infra_failed_not_wrong():
    """A bare HTTP 400 (FastAPI ``{"detail": ...}``) is a refusal, not an answer.

    A per-slot context overflow returns 400. Scoring it as WRONG turns a
    capacity fact into a permanent, misattributed quality regression.
    """
    with pytest.MonkeyPatch.context() as mp:
        resp = _call(
            lambda: _FakeResponse(400, {"detail": "prompt exceeds n_ctx"}),
            mp,
            workload_class="eval_batch",
        )

    assert resp["failure_reason"] == "http_status"
    assert measurement_disposition(resp, error=resp.get("error")) == DISPOSITION_INFRA_FAILED
    # The pre-fix classifier, given only the message, called this a task failure.
    assert "client error" in str(resp["error"]).lower()


def test_http_400_with_structured_error_body_is_infra_failed_not_wrong():
    """A 400 whose body carries ``error_code``/``error_detail`` returns normally
    (no exception is raised), so nothing downstream sees a transport failure
    unless the status itself is recorded."""
    with pytest.MonkeyPatch.context() as mp:
        resp = _call(
            lambda: _FakeResponse(400, {"error_code": 400, "error_detail": "context overflow"}),
            mp,
            workload_class="eval_batch",
        )

    assert resp["http_status"] == 400
    assert resp["failure_reason"] == "http_status"
    assert measurement_disposition(resp, error=resp.get("error")) == DISPOSITION_INFRA_FAILED
    assert infra_failure_reason(resp, error=resp.get("error")) == "http_status"


def test_connection_refused_is_infra_failed():
    def _refused():
        raise httpx.ConnectError("[Errno 111] Connection refused")

    with pytest.MonkeyPatch.context() as mp:
        resp = _call(_refused, mp, workload_class="eval_batch")

    assert resp["failure_reason"] == "api_unreachable_after_backoff"
    assert measurement_disposition(resp, error=resp.get("error")) == DISPOSITION_INFRA_FAILED


def test_connection_refused_without_a_recognisable_message_is_infra_failed():
    """The substring list must not be load-bearing.

    httpx often raises ``ConnectError("")`` or a message with no listed
    keyword. The disposition must survive that.
    """

    def _refused():
        raise httpx.ConnectError("")

    with pytest.MonkeyPatch.context() as mp:
        resp = _call(_refused, mp, workload_class="eval_batch")

    assert measurement_disposition(resp, error=resp.get("error")) == DISPOSITION_INFRA_FAILED


def test_read_timeout_with_empty_exception_message_is_infra_failed():
    """``str(httpx.ReadTimeout(""))`` is ``""`` — and ``""`` is FALSY.

    Before the fix the error field was empty, so every ``if not error:`` guard
    treated the dead request as a clean generation and scored its empty answer
    against the gold answer.
    """

    def _timeout():
        raise httpx.ReadTimeout("")

    with pytest.MonkeyPatch.context() as mp:
        resp = _call(_timeout, mp, workload_class="eval_batch")

    assert str(resp["error"]).strip(), "error text must never be empty/falsy"
    assert resp["failure_reason"] == "read_timeout"
    assert resp["failure_provenance"]["class"] == "client_transport_timeout"
    assert measurement_disposition(resp, error=resp.get("error")) == DISPOSITION_INFRA_FAILED


def test_unparseable_200_body_is_infra_failed_not_wrong():
    with pytest.MonkeyPatch.context() as mp:
        resp = _call(
            lambda: _FakeResponse(200, None, text="", raise_json=True),
            mp,
            workload_class="eval_batch",
        )

    assert resp["failure_reason"] == "invalid_json"
    assert measurement_disposition(resp, error=resp.get("error")) == DISPOSITION_INFRA_FAILED


def test_empty_200_answer_with_zero_tokens_is_infra_failed_not_wrong():
    """A 200 carrying ``answer: ""`` and zero generated tokens is a non-event.

    Nothing was produced, so there is nothing to score; grading it against
    ``expected`` manufactures a WRONG verdict out of an absent measurement.
    """
    resp = {"answer": "", "tokens_generated": 0}
    assert infra_failure_reason(resp, error=None) == "empty_response"
    assert measurement_disposition(resp, error=None) == DISPOSITION_INFRA_FAILED


def test_empty_answer_with_generated_tokens_is_still_a_real_wrong_answer():
    """Guard against over-reach: a model that DID generate but emitted nothing
    scoreable is a genuine task failure, not an infra failure."""
    resp = {"answer": "", "tokens_generated": 128}
    assert infra_failure_reason(resp, error=None) is None
    assert measurement_disposition(resp, error=None) == DISPOSITION_SCORED


def test_a_normal_answer_is_scored():
    resp = {"answer": "4", "tokens_generated": 3}
    assert infra_failure_reason(resp, error=None) is None
    assert measurement_disposition(resp, error=None) == DISPOSITION_SCORED


def test_a_model_error_that_is_not_transport_is_task_failed():
    """The taxonomy must still be able to say WRONG. A disposition that called
    everything infra_failed would be as useless as one that called everything
    wrong."""
    resp = {"answer": "I refuse", "tokens_generated": 4}
    assert measurement_disposition(resp, error="model declined the task") == (
        DISPOSITION_TASK_FAILED
    )


def test_scoring_failure_is_distinct_from_infra_failure():
    """A broken INSTRUMENT and a broken ENDPOINT are both excluded from quality,
    but conflating them hides which one a run's exclusions came from.

    Note the error text here contains "unreachable", a substring on the legacy
    infra list — proving the structural `scoring_failed` fact wins over the
    heuristic rather than being overwritten by it.
    """
    resp = {"answer": "42", "tokens_generated": 2}
    assert measurement_disposition(
        resp,
        error="scoring_unavailable: llm_judge unreachable",
        scoring_failed=True,
    ) == DISPOSITION_SCORING_FAILED


def test_inband_error_banner_is_infra_failed():
    """The circuit breaker returns ``[ERROR: ...]`` AS the answer with error=None."""
    resp = {"answer": "[ERROR: Backend unavailable (circuit open): http://x]"}
    assert infra_failure_reason(resp, error=None) == "inband_error"
    assert measurement_disposition(resp, error=None) == DISPOSITION_INFRA_FAILED


def test_legacy_error_type_mapping_keeps_seeding_vocabulary():
    assert legacy_error_type(DISPOSITION_SCORED) == "none"
    assert legacy_error_type(DISPOSITION_INFRA_FAILED) == "infrastructure"
    assert legacy_error_type(DISPOSITION_SCORING_FAILED) == "infrastructure"
    assert legacy_error_type(DISPOSITION_TASK_FAILED) == "task_failure"


# ── The seeding row builder ──────────────────────────────────────────


def _build_role_result(resp, *, expected="4"):
    import seeding_eval

    return seeding_eval._build_role_result(
        role="worker_math",
        mode="direct",
        resp=resp,
        elapsed=1.0,
        expected=expected,
        scoring_method="exact_match",
        scoring_config={},
        allow_delegation=False,
    )


def test_seeding_row_for_http_400_is_excluded_not_scored_wrong():
    """The seeding path is the one that scored these as WRONG: ``passed=False``
    with ``error_type="task_failure"`` feeds a 0.0 reward into MemRL and
    poisons the learned router."""
    rr, error_type = _build_role_result(
        {
            "answer": "",
            "error": "Client error '400 Bad Request' for url 'http://localhost:8000/chat'",
            "failure_reason": "http_status",
            "http_status": 400,
        }
    )
    assert error_type == "infrastructure"
    assert rr.error_type == "infrastructure"


def test_seeding_row_for_empty_message_timeout_is_excluded_and_gets_error_text():
    """An empty error string is falsy and sails through every ``if error:``
    guard. The row must be excluded AND given a non-empty, self-describing
    error so it cannot be mistaken for a clean generation downstream."""
    rr, error_type = _build_role_result(
        {
            "answer": "",
            "error": "",
            "failure_reason": "read_timeout",
            "failure_provenance": {"class": "client_transport_timeout"},
        }
    )
    assert error_type == "infrastructure"
    assert str(rr.error).strip(), "an excluded row must carry non-empty error text"
    assert "read_timeout" in str(rr.error)


def test_seeding_row_for_a_genuine_wrong_answer_is_still_scored_wrong():
    """Mutation guard: the fix must not launder real wrong answers into
    exclusions. If it did, every quality number would silently rise."""
    rr, error_type = _build_role_result(
        {"answer": "5", "tokens_generated": 1}, expected="4"
    )
    assert error_type == "none"
    assert rr.passed is False


def test_seeding_row_for_a_correct_answer_is_scored_correct():
    rr, error_type = _build_role_result(
        {"answer": "4", "tokens_generated": 1}, expected="4"
    )
    assert error_type == "none"
    assert rr.passed is True


# ── Aggregation: the distinction must survive the fold ───────────────


def _question_result(**kwargs):
    from eval_tower import QuestionResult

    base = dict(
        question_id="q",
        suite="math",
        prompt="What is 2+2?",
        expected="4",
    )
    base.update(kwargs)
    return QuestionResult(**base)


def _infra_row(reason="http_status", qid="q"):
    return _question_result(
        question_id=qid,
        answer="",
        correct=False,
        error=f"infra_failed: {reason}",
        disposition=DISPOSITION_INFRA_FAILED,
        infra_reason=reason,
    )


def _scored_row(correct, qid="q"):
    return _question_result(
        question_id=qid,
        answer="4" if correct else "5",
        correct=correct,
        tokens_generated=4,
        elapsed_s=1.0,
        disposition=DISPOSITION_SCORED,
    )


def _aggregate(rows):
    from eval_tower import EvalTower

    tower = EvalTower.__new__(EvalTower)  # no I/O, no pool loading
    tower._count_instruction_tokens = lambda _results: 0  # type: ignore[method-assign]
    return EvalTower._aggregate(tower, rows, tier=1)


def test_infra_failed_rows_are_not_counted_as_zero_in_the_quality_mean():
    """THE aggregate contract: 2 correct + 2 infra-failed is 100% over what was
    measured, never 50%. An infra row folded in as a 0.0 is the fail-open."""
    result = _aggregate([_scored_row(True, "a"), _scored_row(True, "b"), _infra_row(qid="c"), _infra_row(qid="d")])

    assert result.quality == pytest.approx(3.0)  # 2/2 on the 0-3 scale
    assert result.details["n_scored"] == 2
    assert result.details["quality_denominator"] == 2
    assert result.quality_measured is True


def test_aggregate_reports_infra_failed_count_and_reasons():
    """A distinction that exists per-row but collapses in the aggregate is not
    a fix — the run-level record must carry it."""
    result = _aggregate(
        [
            _scored_row(True, "a"),
            _infra_row("http_status", "b"),
            _infra_row("read_timeout", "c"),
            _infra_row("read_timeout", "d"),
        ]
    )

    assert result.infra_failed_count == 3
    assert result.details["infra_failed"] == 3
    assert result.details["infra_failed_reasons"] == {"http_status": 1, "read_timeout": 2}
    assert result.infra_failed_reasons == {"http_status": 1, "read_timeout": 2}


def test_all_infra_failed_run_is_not_reported_as_a_zero_score():
    """THE 2026-08-03 incident, reproduced. Every row failed for transport
    reasons. `quality` is a float on the Pareto contract and stays 0.0, so the
    honesty has to be carried explicitly: quality_measured=False says that 0.0
    is a placeholder, not "the model scored 0%"."""
    result = _aggregate([_infra_row(qid=f"q{i}") for i in range(70)])

    assert result.quality_measured is False
    assert result.quality_unmeasured_reason == "all_rows_infra_failed"
    assert result.infra_failed_count == 70
    assert result.details["quality_measured"] is False
    assert result.details["n_scored"] == 0
    assert result.reliability == 0.0


def test_a_genuine_all_wrong_run_is_distinguishable_from_an_all_infra_run():
    """The whole point: a 0.0 that means "the model is bad" and a 0.0 that
    means "the endpoint was unreachable" must not be the same record."""
    all_wrong = _aggregate([_scored_row(False, f"q{i}") for i in range(70)])
    all_infra = _aggregate([_infra_row(qid=f"q{i}") for i in range(70)])

    assert all_wrong.quality == 0.0
    assert all_infra.quality == 0.0  # same number …
    assert all_wrong.quality_measured is True  # … different fact
    assert all_infra.quality_measured is False
    assert all_wrong.infra_failed_count == 0
    assert all_infra.infra_failed_count == 70
    assert all_wrong.reliability == 1.0
    assert all_infra.reliability == 0.0


def test_empty_result_set_is_not_reported_as_a_zero_score():
    result = _aggregate([])
    assert result.quality_measured is False
    assert result.quality_unmeasured_reason == "no_question_results"


def test_scoring_failed_rows_are_counted_separately_from_infra_failed():
    rows = [
        _scored_row(True, "a"),
        _infra_row(qid="b"),
        _question_result(
            question_id="c",
            answer="42",
            error="scoring_unavailable: no oracle",
            disposition=DISPOSITION_SCORING_FAILED,
        ),
    ]
    result = _aggregate(rows)

    assert result.infra_failed_count == 1
    assert result.scoring_failed_count == 1
    assert result.details["scoring_failed"] == 1
    # Both are excluded from quality; the split says which is which.
    assert result.details["n_scored"] == 1


# ── Reporting surfaces ───────────────────────────────────────────────


def test_compact_question_row_carries_the_disposition():
    """A consumer must never have to substring-match ``error_detail`` to learn
    what kind of failure a row was — that inference is what failed open."""
    from eval_tower import _compact_question_result

    item = _compact_question_result(_infra_row("read_timeout"))
    assert item["disposition"] == DISPOSITION_INFRA_FAILED
    assert item["infra_reason"] == "read_timeout"

    clean = _compact_question_result(_scored_row(True))
    assert "disposition" not in clean
    assert "infra_reason" not in clean


def test_calibration_jsonl_row_surfaces_infra_failure():
    """The T1 calibration artifact is what a human and core_v2_select read. If
    the run was all infra failures, that has to be legible there."""
    from core_v2_calibrate import result_to_row

    result = _aggregate([_infra_row(qid=f"q{i}") for i in range(70)])
    row = result_to_row(
        result=result,
        calibration_id="cal",
        repeat_index=0,
        repeats=1,
        requested_n=70,
        seed=4242,
        trial_id=900000,
        started_at="2026-08-12T00:00:00Z",
    )

    assert row["quality"] == 0.0
    assert row["quality_measured"] is False
    assert row["quality_unmeasured_reason"] == "all_rows_infra_failed"
    assert row["infra_failed_count"] == 70
    # The row must survive serialization — it is written as JSONL.
    assert json.loads(json.dumps(row, sort_keys=True))["quality_measured"] is False


def test_self_labelled_error_text_reports_its_exact_reason():
    """Rows whose error text prefixes the reason must keep that reason in the
    aggregate histogram rather than collapsing into one generic bucket."""
    assert infra_failure_reason(
        {}, error="forced_role_fallback: forced=worker_math served_by=worker_general"
    ) == "forced_role_fallback"
    assert infra_failure_reason({}, error="deadline_starved: budget 1.0s") == (
        "deadline_starved"
    )
    assert infra_failure_reason({}, error="infra_failed: read_timeout") == "read_timeout"


def test_compact_row_and_aggregate_accept_duck_typed_rows():
    """The recovery path does NOT pass QuestionResult instances.

    `run_e8_quality_baseline_v5._merged_retry_sidecar` rebuilds a row from JSONL
    as a `types.SimpleNamespace` and hands it to `_compact_question_result`. A
    bare `r.disposition` raises AttributeError there — caught by the full suite
    as a real regression, not by any targeted run. Rows without a disposition
    must be treated as `scored`, so an old row keeps its previous accounting.
    """
    import types

    from eval_tower import _compact_question_result

    legacy = types.SimpleNamespace(
        question_id="q",
        qid="q",
        suite="math",
        prompt="What is 2+2?",
        expected="4",
        answer="4",
        correct=True,
        error=None,
        elapsed_s=1.0,
        tokens_generated=4,
        tools_used=0,
        tools_called=[],
        eval_partition="core",
        host_covariates={},
        retrieval_compaction={},
        scoring_method="exact_match",
        route_used="",
        confidence=1.0,
        confidence_source="binary_correctness_proxy",
        partial=False,
        degraded=False,
        exogenous_recovered=False,
        exogenous_unrecovered=False,
        external_restart=False,
        retry_count=0,
        rubric_scores={},
        rubric_source="",
        failure_provenance=None,
    )

    item = _compact_question_result(legacy)  # must not raise
    assert item["correct"] is True
    assert "disposition" not in item
    assert "infra_reason" not in item


def test_aggregate_treats_a_row_with_no_disposition_as_scored():
    """Rows recovered from an older journal carry no disposition. They must fold
    exactly as they did before the field existed — `error` alone still decides
    exclusion, so the accounting of historical data is unchanged."""
    legacy_scored = _scored_row(True, "a")
    legacy_scored.disposition = ""  # pre-disposition row
    legacy_scored.infra_reason = ""
    result = _aggregate([legacy_scored, _scored_row(False, "b")])

    assert result.quality_measured is True
    assert result.infra_failed_count == 0
    assert result.details["n_scored"] == 2
    assert result.quality == pytest.approx(1.5)  # 1/2 on the 0-3 scale
