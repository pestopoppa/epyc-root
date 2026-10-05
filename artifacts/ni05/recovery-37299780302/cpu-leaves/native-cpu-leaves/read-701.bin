"""RD-12 + TM-8 — per-decision accounting + trace-coverage tests.

Covers (zero inference — stub completion callables only):

  RD-12  per-decision latency_ms + prompt/completion token accounting in the
         emitted trace rows and the decision artifact (telemetry block)
  RD-12  parse-failure fallback counting: distinct, exactly-once, never
         double-counted, never dropped (vs model-call failures on their own
         counter)
  RD-12  build_review_decision_artifact → schema-valid ReviewDecision artifact
         whose telemetry feeds review_decision_to_ledger_row (H-LB/H4 path)
  TM-8   shadow_decide emits a trace row for EVERY invocation (coverage gate
         substrate) and the trace rows carry phase tags + executor-model-id
  TM-8   src.trace.coverage helpers: coverage %, aggregates, enforcement
         side-effect tripwire, phase/metadata verification
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from src.proactive_delegation.review_service import (
    ArchitectReviewService,
    build_review_decision_artifact,
)
from src.proactive_delegation.types import ArchitectReview, ReviewDecision
from src.trace.coverage import (
    aggregate_decision_metrics,
    enforcement_side_effects,
    review_trace_coverage,
    verify_phase_metadata,
)


# ─── stubs / fixtures ─────────────────────────────────────────────────────────


class StubPrimitives:
    """llm_call returns a canned response (str or object); records calls."""

    def __init__(self, response: str | Exception = ""):
        self.response = response
        self.calls: list[dict] = []

    def llm_call(self, prompt, role=None, n_tokens=None, **kwargs):
        self.calls.append({"prompt": prompt, "role": role, "n_tokens": n_tokens, **kwargs})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class SequencedPrimitives:
    """llm_call pops responses off a queue: [0] is the FIRST (constrained) call,
    subsequent entries are ``parse_with_repair``'s repair turn(s). Records every
    call's kwargs (including ``json_schema``) so TD-21.6/21.7 tests can assert
    the schema actually reached the wire, not just that parsing tolerates noise."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def llm_call(self, prompt, role=None, n_tokens=None, **kwargs):
        self.calls.append({"prompt": prompt, "role": role, "n_tokens": n_tokens, **kwargs})
        if not self.responses:
            raise AssertionError("SequencedPrimitives ran out of canned responses")
        return self.responses.pop(0)


class UsageResponse:
    """A response object carrying server-reported usage (RD-12 real-count path)."""

    def __init__(self, text: str, prompt_tokens: int, completion_tokens: int):
        self.text = text
        self.usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }


@pytest.fixture
def capturing_service():
    """Service whose emitted Events are captured in a list (no DB)."""
    events: list = []

    def _make(response="", **kwargs):
        kwargs.setdefault("trace_sink", events.append)
        svc = ArchitectReviewService(StubPrimitives(response), **kwargs)
        return svc, events

    return _make


def _review(**kw) -> ArchitectReview:
    kw.setdefault("subtask_id", "S1")
    kw.setdefault("decision", ReviewDecision.APPROVE)
    return ArchitectReview(**kw)


def _detail(ev) -> dict:
    return json.loads(ev.detail_json)


# ═══ RD-12: token accounting in trace rows ════════════════════════════════════


class TestTokenAccounting:
    def test_review_emits_tokens_in_and_out(self, capturing_service):
        svc, events = capturing_service('{"d":"approve","s":0.9,"f":"ok"}')
        svc.review(
            spec={"objective": "o"}, subtask={"id": "S1", "action": "a"}, output="hello world"
        )
        detail = _detail(events[0])
        assert "latency_ms" in detail and detail["latency_ms"] >= 0
        assert detail["tokens"]["tokens_in"] >= 1  # prompt side now accounted
        assert detail["tokens"]["tokens_out"] >= 1
        assert detail["tokens"]["chars_out"] >= 1

    def test_review_plan_emits_tokens_in_and_out(self, capturing_service):
        svc, events = capturing_service('{"d":"ok","s":0.9,"f":"good"}')
        svc.review_plan(
            objective="o",
            task_type="code",
            plan_steps=[{"id": "S1", "actor": "coder", "action": "x"}],
        )
        detail = _detail(events[0])
        assert detail["tokens"]["tokens_in"] >= 1
        assert detail["tokens"]["tokens_out"] >= 1
        assert detail["phase"] == "plan"

    def test_review_candidate_emits_tokens_in_and_out(self, capturing_service):
        svc, events = capturing_service(
            '{"decision":"approve","confidence":0.8,"blocking":{"tripwire":false}}'
        )
        svc.review_candidate({"task_ref": "T1", "objective": "x", "outputs": []}, subtask_id="C1")
        detail = _detail(events[0])
        assert detail["tokens"]["tokens_in"] >= 1
        assert detail["tokens"]["tokens_out"] >= 1
        assert detail["phase"] == "review"

    def test_review_plan_rubric_emits_tokens_in_and_out(self, capturing_service):
        svc, events = capturing_service(
            '{"decision":"approve","confidence":0.7,"advisory":{"score":0.6}}'
        )
        svc.review_plan_rubric("o", "code", [{"id": "S1", "actor": "coder", "action": "x"}])
        detail = _detail(events[0])
        assert detail["tokens"]["tokens_in"] >= 1
        assert detail["tokens"]["tokens_out"] >= 1

    def test_server_reported_usage_preferred_over_estimate(self, capturing_service):
        """A response object carrying usage wins over the char estimate (RD-12)."""
        stub = StubPrimitives(
            UsageResponse(
                '{"decision":"approve","confidence":0.5,"blocking":{"tripwire":false}}',
                prompt_tokens=123,
                completion_tokens=45,
            )
        )
        svc = ArchitectReviewService(stub, trace_sink=lambda ev: None)
        svc.review_candidate({"task_ref": "T", "outputs": []})
        # _response_tokens is the unit under test; call it directly with the object.
        tokens = ArchitectReviewService._response_tokens(
            UsageResponse("some text", prompt_tokens=123, completion_tokens=45),
            prompt="a prompt",
        )
        assert tokens["tokens_in"] == 123
        assert tokens["tokens_out"] == 45

    def test_estimate_path_uses_prompt_length(self):
        tokens = ArchitectReviewService._response_tokens("", prompt="x" * 400)
        assert tokens["tokens_in"] >= 90  # ~4 chars/token
        assert tokens["tokens_out"] == 0


# ═══ RD-12: parse-failure fallback counting (distinct, exactly once) ══════════


class TestParseFailureCounting:
    def test_review_unparseable_counts_parse_failure(self, capturing_service):
        svc, events = capturing_service("this is not json at all")
        r = svc.review(spec={}, subtask={"id": "S1", "action": "a"}, output="o")
        # TD-21.6: a terminal (repair-exhausted) parse failure withholds as
        # REQUEST_EVIDENCE -- never the old silent "request_changes" default,
        # which was indistinguishable from a genuine reviewer verdict.
        assert r.decision == ReviewDecision.REQUEST_EVIDENCE
        assert svc.parse_failure_count == 1
        assert svc.model_call_failures == 0
        detail = _detail(events[0])
        assert detail["parse_ok"] is False
        assert detail["parse_failure"]  # a concrete reason string, never blank
        assert detail["repaired"] is False

    def test_review_model_call_failure_counts_separately(self, capturing_service):
        svc, events = capturing_service(TimeoutError("boom"))
        svc.review(spec={}, subtask={"id": "S1", "action": "a"}, output="o")
        assert svc.parse_failure_count == 0
        assert svc.model_call_failures == 1
        detail = _detail(events[0])
        assert detail["parse_ok"] is False
        assert detail["model_call_failed"] is True

    def test_review_valid_response_counts_nothing(self, capturing_service):
        svc, _ = capturing_service('{"d":"approve","s":0.9,"f":"ok"}')
        svc.review(spec={}, subtask={"id": "S1", "action": "a"}, output="o")
        assert svc.parse_failure_count == 0
        assert svc.model_call_failures == 0

    def test_review_plan_unparseable_counts_parse_failure(self, capturing_service):
        svc, events = capturing_service("not json")
        res = svc.review_plan(
            objective="o",
            task_type="code",
            plan_steps=[{"id": "S1", "actor": "coder", "action": "x"}],
        )
        assert res is not None  # non-blocking contract preserved
        # TD-21.6: a terminal failure is the PARSE_FAILURE_SENTINEL, never the old
        # silent "ok" default (which was indistinguishable from genuine approval).
        assert res.decision == "parse_failure"
        assert res.patches == []
        assert svc.parse_failure_count == 1
        assert svc.model_call_failures == 0
        assert _detail(events[0])["parse_ok"] is False
        assert _detail(events[0])["decision"] == "parse_failure"

    def test_review_plan_model_call_failure_counts_separately(self, capturing_service):
        svc, events = capturing_service(RuntimeError("down"))
        res = svc.review_plan(
            objective="o",
            task_type="code",
            plan_steps=[{"id": "S1", "actor": "coder", "action": "x"}],
        )
        assert res is None
        assert svc.parse_failure_count == 0
        assert svc.model_call_failures == 1
        assert _detail(events[0])["model_call_failed"] is True

    def test_review_candidate_unparseable_counts_parse_failure(self, capturing_service):
        svc, events = capturing_service("not json at all")
        r = svc.review_candidate({"task_ref": "T", "outputs": []})
        assert r.decision == ReviewDecision.REQUEST_EVIDENCE  # withheld, never reject
        assert svc.parse_failure_count == 1
        assert svc.model_call_failures == 0
        assert _detail(events[0])["parse_ok"] is False

    def test_review_candidate_non_object_json_counts_once(self, capturing_service):
        """A JSON array is a parse failure too — and it counts exactly once."""
        svc, events = capturing_service("[1, 2, 3]")
        svc.review_candidate({"task_ref": "T", "outputs": []})
        assert svc.parse_failure_count == 1
        assert svc.model_call_failures == 0

    def test_review_candidate_model_call_failure_counts_separately(self, capturing_service):
        svc, events = capturing_service(RuntimeError("down"))
        svc.review_candidate({"task_ref": "T", "outputs": []})
        assert svc.parse_failure_count == 0
        assert svc.model_call_failures == 1
        assert _detail(events[0])["model_call_failed"] is True

    def test_review_plan_rubric_unparseable_counts_parse_failure(self, capturing_service):
        svc, events = capturing_service("garbage")
        res = svc.review_plan_rubric("o", "code", [{"id": "S1", "actor": "coder", "action": "x"}])
        # TD-21.6: PARSE_FAILURE_SENTINEL, never the old silent "approve" default,
        # and the rubric axes are unknown (None) rather than defaulting True.
        assert res["decision"] == "parse_failure"
        assert res["phase_coverage"] is None
        assert res["order"] is None
        assert res["executor_alignment"] is None
        assert svc.parse_failure_count == 1
        assert _detail(events[0])["parse_ok"] is False
        assert _detail(events[0])["per_item_grades"] is None

    def test_review_plan_rubric_model_call_failure_counts_separately(self, capturing_service):
        svc, events = capturing_service(RuntimeError("down"))
        svc.review_plan_rubric("o", "code", [{"id": "S1", "actor": "coder", "action": "x"}])
        assert svc.parse_failure_count == 0
        assert svc.model_call_failures == 1

    def test_no_double_count_across_review_paths(self, capturing_service):
        """Three consecutive unparseable reviews → exactly three parse failures."""
        svc, events = capturing_service("still not json")
        for i in range(3):
            svc.review_candidate({"task_ref": f"T{i}", "outputs": []}, subtask_id=f"C{i}")
        assert svc.parse_failure_count == 3
        assert svc.model_call_failures == 0

    def test_generate_taskir_does_not_touch_counters(self, capturing_service):
        """TaskIR generation is not a review decision — its fallback is uncounted."""
        svc, _ = capturing_service("nonsense")
        out = svc.generate_taskir("objective here")
        assert "plan" in out  # parse-failure fallback still returns a task
        # TD-21.6: the fallback is now explicitly TYPED, never a silent empty-plan
        # (the old bug: a genuine JSON-parse failure fell through _parse_review_
        # response's sentinel into an empty steps[] returned as if valid).
        assert out["parse_failed"] is True
        assert out["plan"]["steps"]  # the safe single-step fallback, not empty
        assert svc.parse_failure_count == 0
        assert svc.model_call_failures == 0

    def test_parse_fallback_marker_never_leaks_into_decision(self, capturing_service):
        """A terminal parse failure withholds -- REQUEST_EVIDENCE, never a
        default verdict -- and never leaks an internal marker key."""
        svc, events = capturing_service("not json")
        r = svc.review(spec={}, subtask={"id": "S1", "action": "a"}, output="o")
        assert r.decision == ReviewDecision.REQUEST_EVIDENCE
        assert r.feedback.startswith("parse_failure:")
        detail = _detail(events[0])
        assert "_parse_fallback" not in detail


# ═══ TD-21.6/21.7: schema on the wire + repair recovers a malformed reply ═════


class TestSchemaOnWireAndRepair:
    """Two failure modes TD-21.6/21.7 close, proven per call site:

      1. the FIRST ``llm_call`` now carries ``json_schema`` (was silently
         unconstrained before TD-21.0/TD-21.6/21.7);
      2. a malformed-but-recoverable reply is REPAIRED (one extra constrained
         turn) instead of immediately becoming a parse failure -- exercised with
         ``SequencedPrimitives`` so the second call's response is the "fixed"
         emission a real repair turn would produce.
    """

    def test_review_forwards_json_schema_on_first_call(self):
        prims = SequencedPrimitives(['{"d":"approve","s":0.9,"f":"ok"}'])
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        svc.review(spec={}, subtask={"id": "S1", "action": "a"}, output="o")
        assert prims.calls[0]["json_schema"]["properties"]["d"]["enum"] == [
            "approve", "changes", "request_changes", "escalate", "reject",
        ]

    def test_review_plan_forwards_json_schema_on_first_call(self):
        prims = SequencedPrimitives(['{"d":"ok","s":0.9,"f":"good"}'])
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        svc.review_plan(
            objective="o", task_type="code",
            plan_steps=[{"id": "S1", "actor": "coder", "action": "x"}],
        )
        assert prims.calls[0]["json_schema"]["properties"]["d"]["enum"] == [
            "ok", "reorder", "drop", "add", "reroute",
        ]

    def test_review_plan_rubric_forwards_json_schema_on_first_call(self):
        prims = SequencedPrimitives(['{"decision":"approve","confidence":0.7}'])
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        svc.review_plan_rubric("o", "code", [{"id": "S1", "actor": "coder", "action": "x"}])
        assert prims.calls[0]["json_schema"]["required"] == ["decision"]

    def test_generate_taskir_forwards_json_schema_on_first_call(self):
        prims = SequencedPrimitives(['{"steps":[{"id":"S1","actor":"coder","action":"x"}]}'])
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        svc.generate_taskir("build a thing")
        assert prims.calls[0]["json_schema"]["required"] == ["steps"]

    def test_review_candidate_forwards_json_schema_on_first_call(self):
        prims = SequencedPrimitives(
            ['{"decision":"approve","confidence":0.8,"blocking":{"tripwire":false}}']
        )
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        svc.review_candidate({"task_ref": "T", "outputs": []})
        assert prims.calls[0]["json_schema"]["required"] == ["decision", "confidence", "blocking"]

    def test_review_recovers_malformed_response_via_repair(self):
        prims = SequencedPrimitives([
            "not json at all, but score 0.8, feedback: fixed",
            '{"d":"approve","s":0.8,"f":"fixed"}',
        ])
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        r = svc.review(spec={}, subtask={"id": "S1", "action": "a"}, output="o")
        assert r.decision == ReviewDecision.APPROVE
        assert r.score == 0.8
        assert svc.parse_failure_count == 0  # recovered -- not a terminal failure
        assert len(prims.calls) == 2  # initial + exactly ONE repair turn

    def test_review_plan_recovers_malformed_response_via_repair(self):
        prims = SequencedPrimitives([
            "garbage but score 0.7, ok",
            '{"d":"reroute","s":0.7,"f":"ok","p":[]}',
        ])
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        res = svc.review_plan(
            objective="o", task_type="code",
            plan_steps=[{"id": "S1", "actor": "coder", "action": "x"}],
        )
        assert res.decision == "reroute"
        assert svc.parse_failure_count == 0
        assert len(prims.calls) == 2

    def test_review_plan_rubric_recovers_malformed_response_via_repair(self):
        prims = SequencedPrimitives(
            [
                "garbage but confidence 0.7",
                '{"decision":"approve","confidence":0.7,"phase_coverage":true,'
                '"order":true,"executor_alignment":true}',
            ]
        )
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        res = svc.review_plan_rubric("o", "code", [{"id": "S1", "actor": "coder", "action": "x"}])
        assert res["decision"] == "approve"
        assert res["phase_coverage"] is True
        assert svc.parse_failure_count == 0

    def test_generate_taskir_recovers_via_repair(self):
        prims = SequencedPrimitives(
            [
                "not json: step S1, actor coder, do x, output f.py",
                '{"steps":[{"id":"S1","actor":"coder","action":"do x","out":["f.py"]}]}',
            ]
        )
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        out = svc.generate_taskir("build a thing")
        assert out["plan"]["steps"][0]["actor"] == "coder"
        assert out.get("repaired") is True
        assert "parse_failed" not in out

    def test_review_candidate_recovers_malformed_response_via_repair(self):
        prims = SequencedPrimitives(
            [
                "nonsense but confidence 0.7",
                '{"decision":"approve","confidence":0.7,"blocking":{"tripwire":false}}',
            ]
        )
        svc = ArchitectReviewService(prims, trace_sink=lambda ev: None)
        r = svc.review_candidate({"task_ref": "T", "outputs": []})
        assert r.decision == ReviewDecision.APPROVE
        assert svc.parse_failure_count == 0
        assert len(prims.calls) == 2


# ═══ RD-12: decision artifact (telemetry block, schema-valid) ═════════════════


class TestDecisionArtifact:
    def test_shadow_decide_artifact_carries_telemetry(self, capturing_service):
        svc, _ = capturing_service()
        art = svc.shadow_decide(
            _review(decision=ReviewDecision.REQUEST_CHANGES),
            latency_ms=12.5,
            tokens={"tokens_in": 100, "tokens_out": 30, "chars_out": 120},
        )
        assert art["shadow"] is True
        assert art["telemetry"] == {"wall_ms": 12.5, "tokens_in": 100, "tokens_out": 30}
        # still a superset of ArchitectReview.to_dict()
        assert art["decision"] == "request_changes"
        assert art["subtask_id"] == "S1"

    def test_shadow_decide_without_telemetry_keeps_artifact_unchanged(self, capturing_service):
        svc, _ = capturing_service()
        art = svc.shadow_decide(_review())
        assert "telemetry" not in art

    def test_build_artifact_validates_against_schema(self):
        from jsonschema import Draft202012Validator

        from src.proactive_delegation.review_grammar import load_review_decision_schema

        art = build_review_decision_artifact(
            _review(decision=ReviewDecision.REJECT, tripwire=True),
            latency_ms=8.0,
            tokens={"tokens_in": 50, "tokens_out": 12},
            decision_id="revdec-test-1",
            executor_model_id="frontdoor-35b-iq2",
        )
        errors = sorted(
            Draft202012Validator(load_review_decision_schema()).iter_errors(art),
            key=lambda e: list(e.absolute_path),
        )
        assert errors == [], f"artifact violates review_decision.schema.json: {errors[:3]}"

    def test_build_artifact_feeds_ledger_adapter(self):
        """telemetry.wall_ms/tokens_out → review_ledger latency_ms/tokens (H-LB path)."""
        from src.trace.review_ledger import review_decision_to_ledger_row

        art = build_review_decision_artifact(
            _review(decision=ReviewDecision.APPROVE),
            latency_ms=7.5,
            tokens={"tokens_in": 40, "tokens_out": 9},
        )
        row = review_decision_to_ledger_row(art, role="architect_general")
        assert row.latency_ms == 7.5
        assert row.tokens == 9
        assert row.decision == "approve"


# ═══ TM-8: every shadow invocation yields a trace row (coverage substrate) ════


class TestShadowEmissionCoverage:
    def test_shadow_decide_always_emits_even_with_no_substeps(self, capturing_service):
        """Approve + admissible + warn-only-inactive: sub-steps emit nothing, but the
        invocation MUST still produce a trace row — this is the coverage gate."""
        svc, events = capturing_service(warn_only=True)
        svc.shadow_decide(_review(decision=ReviewDecision.APPROVE))
        assert any(e.category == "review_decision" for e in events)
        ev = next(e for e in events if e.category == "review_decision")
        detail = _detail(ev)
        assert detail["mode"] == "shadow_decide"
        assert detail["phase"] == "decision"
        assert detail["shadow"] is True

    def test_n_shadow_invocations_produce_n_traced_sessions(self, tmp_path):
        """N invocations with distinct session_ids → coverage 100% over the set."""
        db = tmp_path / "trace.sqlite"
        svc = ArchitectReviewService(
            StubPrimitives(),
            trace_db_path=str(db),
        )
        # Mix of sub-step outcomes so the always-on emit is the only common row.
        svc.shadow_decide(_review(decision=ReviewDecision.APPROVE), session_id="cov-01")
        # warn_only off path via a warn_only=False service:
        svc2 = ArchitectReviewService(StubPrimitives(), trace_db_path=str(db), warn_only=False)
        svc2.shadow_decide(_review(decision=ReviewDecision.REJECT), session_id="cov-02")
        svc2.shadow_decide(_review(decision=ReviewDecision.ESCALATE), session_id="cov-03")
        cov = review_trace_coverage(db, ["cov-01", "cov-02", "cov-03"])
        assert cov["coverage_pct"] == 100.0
        assert cov["missing_session_ids"] == []

    def test_coverage_reports_missing_sessions(self, tmp_path):
        db = tmp_path / "trace.sqlite"
        svc = ArchitectReviewService(StubPrimitives(), trace_db_path=str(db))
        svc.shadow_decide(_review(), session_id="present-1")
        cov = review_trace_coverage(db, ["present-1", "absent-2"])
        assert cov["traced"] == 1
        assert cov["coverage_pct"] == 50.0
        assert cov["missing_session_ids"] == ["absent-2"]

    def test_coverage_missing_db_fails_loud(self, tmp_path):
        cov = review_trace_coverage(tmp_path / "nope.sqlite", ["a", "b"])
        assert cov["coverage_pct"] == 0.0
        assert cov["missing_session_ids"] == ["a", "b"]


# ═══ TM-8: phase tags + executor-model-id + reminders in trace rows ═══════════


class TestPhaseMetadata:
    def test_review_rows_carry_phase_and_executor(self, tmp_path):
        db = tmp_path / "trace.sqlite"
        svc = ArchitectReviewService(
            StubPrimitives('{"d":"approve","s":0.9}'), trace_db_path=str(db)
        )
        svc.review(
            spec={"objective": "o"},
            subtask={"id": "S1", "action": "a", "role": "worker_general"},
            output="out",
            session_id="pm-1",
        )
        svc.review_candidate(
            {"task_ref": "T1", "objective": "x", "outputs": []},
            subtask_id="C1",
            session_id="pm-2",
            executor_model_id="frontdoor-35b-iq2",
        )
        svc.build_plan_reminder(
            [{"id": "S1", "actor": "coder", "action": "x"}],
            cadence_n=5,
            step_index=10,
            emit=True,
            session_id="pm-2",
        )
        meta = verify_phase_metadata(db, ["pm-1", "pm-2"])
        assert meta["n_rows"] >= 3
        assert meta["phase_tagged"]["pct"] == 100.0
        assert meta["executor_model_id_present"]["n"] >= 2
        assert meta["reminder_events"] == 1
        assert "reminder" in meta["phases_seen"]
        assert meta["untagged_session_ids"] == []

    def test_untagged_rows_are_reported(self, tmp_path):
        db = tmp_path / "trace.sqlite"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS event (id INTEGER PRIMARY KEY, ts_utc TEXT NOT NULL, "
            "source TEXT NOT NULL, source_path TEXT NOT NULL, source_line INTEGER, session_id TEXT, "
            "trial_id INTEGER, role TEXT, category TEXT, status TEXT, summary TEXT, detail_json TEXT, "
            "redacted INTEGER NOT NULL DEFAULT 0)"
        )
        conn.execute(
            "INSERT INTO event (ts_utc, source, source_path, source_line, session_id, category, detail_json) "
            "VALUES ('2026-08-24T00:00:00Z', 'review_plane', 'emit://x/1', 0, 'bare-1', 'review_decision', '{}')"
        )
        conn.commit()
        conn.close()
        meta = verify_phase_metadata(db, ["bare-1"])
        assert meta["phase_tagged"]["n"] == 0
        assert meta["untagged_session_ids"] == ["bare-1"]


# ═══ RD-12/TM-8: aggregates + enforcement tripwire ════════════════════════════


class TestAggregatesAndEnforcement:
    def test_aggregate_decision_metrics(self, tmp_path):
        db = tmp_path / "trace.sqlite"
        svc = ArchitectReviewService(
            StubPrimitives('{"decision":"approve","confidence":0.9,"blocking":{"tripwire":false}}'),
            trace_db_path=str(db),
        )
        for i in range(3):
            svc.review_candidate({"task_ref": f"T{i}", "outputs": []}, session_id=f"agg-{i}")
        svc_bad = ArchitectReviewService(StubPrimitives("garbage"), trace_db_path=str(db))
        svc_bad.review_candidate({"task_ref": "Tbad", "outputs": []}, session_id="agg-3")
        metrics = aggregate_decision_metrics(db, [f"agg-{i}" for i in range(4)])
        assert metrics["n_decisions"] == 4
        assert metrics["n_parse_failures"] == 1
        assert metrics["n_model_call_failures"] == 0
        assert metrics["latency_ms"]["mean"] is not None
        assert metrics["tokens_in"]["sum"] >= 4
        assert metrics["tokens_out"]["sum"] >= 4
        assert len(metrics["per_decision"]) == 4

    def test_enforcement_side_effects_empty_in_shadow(self, tmp_path):
        db = tmp_path / "trace.sqlite"
        svc = ArchitectReviewService(
            StubPrimitives('{"decision":"approve","confidence":0.5,"blocking":{"tripwire":false}}'),
            trace_db_path=str(db),
        )
        svc.shadow_decide(_review(), session_id="enc-1")
        assert enforcement_side_effects(db, ["enc-1"]) == []

    def test_enforcement_side_effects_tripwire_detects_planted_row(self, tmp_path):
        db = tmp_path / "trace.sqlite"
        svc = ArchitectReviewService(StubPrimitives(), trace_db_path=str(db))
        svc.shadow_decide(_review(), session_id="enc-2")
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO event (ts_utc, source, source_path, source_line, session_id, category, status, detail_json) "
            "VALUES ('2026-08-24T00:00:00Z', 'review_plane', 'emit://x/2', 0, 'enc-2', 'review_decision', "
            "'enforced', '{\"enforced\": true}')"
        )
        conn.commit()
        conn.close()
        hits = enforcement_side_effects(db, ["enc-2"])
        assert len(hits) == 1
        assert hits[0]["session_id"] == "enc-2"
