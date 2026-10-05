"""Unit tests for J11/BSV-2 observe-only payload (scripts/autopilot/bsv_observe.py).

Pure: no autopilot loop, no inference. Verifies the coarse trial-level signature, the partial-
confidence policy, and the diff severities the observe-only run would journal.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

# scripts/autopilot is not a package / not on the default test path (mirror autopilot.py's runtime).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "autopilot"))

from bsv_observe import (  # noqa: E402
    SUITE_PASS_QUALITY,
    build_conflict_report,
    build_mutation_dependency_entry,
    compute_bsv_observe_payload,
    _question_answer_hashes,
    _question_outcomes,
    _suite_outcomes,
)


def _er(**kw) -> SimpleNamespace:
    base = dict(
        routing_distribution={},
        per_suite_quality={},
        oracle_adequacy={},
        avg_prompt_tokens=0.0,
        metric_schema_version=1,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_suite_outcomes_proxy_uses_bsv_vocab():
    out = _suite_outcomes({"qa": 2.6, "coding": 1.0, "math": SUITE_PASS_QUALITY})
    assert out == {"qa": "pass", "coding": "fail", "math": "pass"}  # >= threshold => pass
    assert _suite_outcomes(None) == {}


def test_question_outcomes_use_bsv_vocab_and_skip_malformed_rows():
    out = _question_outcomes(
        [
            {"qid": "q1", "correct": True},
            {"question_id": "q2", "correct": False},
            {"qid": " ", "correct": True},
            {"qid": "q3"},
            "not-a-row",
        ]
    )
    assert out == {"q1": "pass", "q2": "fail", "q3": "fail"}
    assert _question_outcomes(None) == {}


def test_question_answer_hashes_skip_raw_answer_and_malformed_rows():
    out = _question_answer_hashes(
        [
            {"qid": "q1", "answer_hash": "abc123", "answer": "private"},
            {"question_id": "q2", "normalized_answer_hash": "def456"},
            {"qid": "q3", "answer": "private only"},
            "not-a-row",
        ]
    )

    assert out == {"q1": "abc123", "q2": "def456"}
    assert _question_answer_hashes(None) == {}


def test_no_incumbent_has_no_severity():
    p = compute_bsv_observe_payload(
        _er(routing_distribution={"frontdoor": 1.0}),
        species_name="seeder",
        trial_id=1,
        incumbent_signature=None,
    )
    assert p["severity"] is None
    assert p["compared_to_incumbent"] is False
    assert p["signature_confidence"] == "partial"
    assert "route_path_hash" in p["signature"]
    assert p["archive_member_id"] == "seeder"
    assert p["signature_hash"] == p["signature"]["signature_hash"]
    assert p["sentinel_outcome_source"] == "none"
    assert p["sentinel_outcome_count"] == 0


def test_question_results_are_preferred_over_suite_proxy():
    p = compute_bsv_observe_payload(
        _er(
            question_results=[
                {"qid": "suite_a/q1", "correct": True},
                {"question_id": "suite_a/q2", "correct": False},
            ],
            per_suite_quality={"suite_a": 2.8},
        ),
        species_name="seeder",
        trial_id=1,
        incumbent_signature=None,
    )
    assert p["signature"]["sentinel_outcomes"] == {
        "suite_a/q1": "pass",
        "suite_a/q2": "fail",
    }
    assert p["sentinel_outcome_source"] == "question_results"
    assert p["sentinel_outcome_count"] == 2


def test_question_result_answer_hashes_are_included_without_raw_answers():
    p = compute_bsv_observe_payload(
        _er(
            question_results=[
                {"qid": "suite_a/q1", "correct": True, "answer_hash": "a1"},
                {"qid": "suite_a/q2", "correct": False, "answer_hash": "a2"},
            ],
        ),
        species_name="seeder",
        trial_id=1,
        incumbent_signature=None,
    )

    assert p["signature"]["answer_hash"]
    assert p["answer_hash_source"] == "question_results.answer_hash"
    assert p["answer_hash_count"] == 2
    assert "answer" not in p["signature"]


def test_suite_proxy_remains_fallback_when_question_results_absent():
    p = compute_bsv_observe_payload(
        _er(per_suite_quality={"qa": 2.6, "coding": 1.0}),
        species_name="seeder",
        trial_id=1,
        incumbent_signature=None,
    )
    assert p["signature"]["sentinel_outcomes"] == {"qa": "pass", "coding": "fail"}
    assert p["sentinel_outcome_source"] == "suite_quality_proxy"
    assert p["sentinel_outcome_count"] == 2


def test_archive_member_identity_overrides_species_name():
    p = compute_bsv_observe_payload(
        _er(routing_distribution={"frontdoor": 1.0}),
        species_name="seeder",
        trial_id=7,
        archive_member_id="trial:7",
        incumbent_archive_member_id="trial:3",
        incumbent_signature=None,
    )
    assert p["archive_member_id"] == "trial:7"
    assert p["signature"]["archive_member_id"] == "trial:7"
    assert p["signature"]["trial_id"] == 7
    assert p["incumbent_archive_member_id"] == "trial:3"
    assert p["signature_hash"]


def test_identical_partial_signature_is_watch_not_benign():
    # Two identical trials: nothing changed, but partial-confidence cannot certify BENIGN.
    er = _er(routing_distribution={"frontdoor": 1.0}, per_suite_quality={"qa": 2.6})
    inc = compute_bsv_observe_payload(er, species_name="s", trial_id=1, incumbent_signature=None)[
        "signature"
    ]
    p = compute_bsv_observe_payload(er, species_name="s", trial_id=2, incumbent_signature=inc)
    assert p["severity"] == "watch"
    assert any("partial" in r for r in p["reasons"])


def test_suite_regression_is_blocking():
    inc = compute_bsv_observe_payload(
        _er(per_suite_quality={"coding": 2.6}),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )["signature"]
    p = compute_bsv_observe_payload(
        _er(per_suite_quality={"coding": 1.0}),
        species_name="s",
        trial_id=2,
        incumbent_signature=inc,
    )
    assert p["severity"] == "blocking"
    assert any("coding" in r for r in p["reasons"])


def test_routing_change_flags_at_least_watch():
    inc = compute_bsv_observe_payload(
        _er(routing_distribution={"frontdoor": 1.0}, per_suite_quality={"qa": 2.6}),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )["signature"]
    p = compute_bsv_observe_payload(
        _er(routing_distribution={"worker_coder": 1.0}, per_suite_quality={"qa": 2.6}),
        species_name="s",
        trial_id=2,
        incumbent_signature=inc,
    )
    assert p["severity"] in ("watch", "blocking")
    assert any("route_path_hash" in r for r in p["reasons"])


def test_question_result_process_signals_are_signed():
    p = compute_bsv_observe_payload(
        _er(
            question_results=[
                {
                    "qid": "q1",
                    "correct": True,
                    "latency_ms": 1250,
                    "tools_used": 2,
                    "tools_called": ["python", "python"],
                    "route": "frontdoor->worker_general",
                },
                {
                    "qid": "q2",
                    "correct": True,
                    "latency_ms": 2500,
                    "tools_used": 0,
                    "route": "frontdoor",
                },
            ],
            tool_use_rate=0.5,
        ),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )
    signature = p["signature"]
    assert signature["tool_sequence_hash"]
    assert signature["escalation_path_hash"]
    assert signature["latency_bucket"] == "1-5s"
    assert p["process_signal_sources"] == {
        "tool_sequence": "question_results.tools_used",
        "escalation_path": "question_results.route",
        "latency_ms": "question_results.latency_ms_mean",
    }


def test_tool_and_latency_drift_flags_watch_or_blocking():
    incumbent = compute_bsv_observe_payload(
        _er(
            question_results=[
                {"qid": "q1", "correct": True, "latency_ms": 1000, "tools_used": 0},
                {"qid": "q2", "correct": True, "latency_ms": 1000, "tools_used": 0},
            ]
        ),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )["signature"]
    p = compute_bsv_observe_payload(
        _er(
            question_results=[
                {
                    "qid": "q1",
                    "correct": True,
                    "latency_ms": 2000,
                    "tools_used": 1,
                    "tools_called": ["python"],
                },
                {"qid": "q2", "correct": True, "latency_ms": 2000, "tools_used": 0},
            ],
            tool_use_rate=0.5,
        ),
        species_name="s",
        trial_id=2,
        incumbent_signature=incumbent,
    )
    assert p["severity"] in ("watch", "blocking")
    assert any("tool_sequence_hash" in reason for reason in p["reasons"])


def test_legacy_tool_name_counts_are_signed_when_question_rows_absent():
    p = compute_bsv_observe_payload(
        _er(details={"tool_name_counts": {"python": 3, "read_file": 1}, "eval_wall_s": 8.0}),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )
    assert p["signature"]["tool_sequence_hash"]
    assert p["signature"]["latency_bucket"] == "5-30s"
    assert p["process_signal_sources"]["tool_sequence"] == "details.tool_name_counts"
    assert p["process_signal_sources"]["latency_ms"] == "eval_result.eval_wall_s"


def test_graceful_on_empty_eval_result():
    # Missing fields must not raise — observe-only must never disrupt the trial loop.
    p = compute_bsv_observe_payload(
        SimpleNamespace(), species_name="", trial_id=0, incumbent_signature=None
    )
    assert p["severity"] is None
    assert "signature" in p and p["signature_confidence"] == "partial"


def test_routing_weight_drift_flags_change():
    # finding #3: SAME roles, but a major weight shift must change route_path_hash (it would not
    # under name-only hashing). frontdoor 0.9->0.1 (q4->q1), worker_coder 0.1->0.9 (q1->q4).
    inc = compute_bsv_observe_payload(
        _er(
            routing_distribution={"frontdoor": 0.9, "worker_coder": 0.1},
            per_suite_quality={"qa": 2.6},
        ),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )["signature"]
    p = compute_bsv_observe_payload(
        _er(
            routing_distribution={"frontdoor": 0.1, "worker_coder": 0.9},
            per_suite_quality={"qa": 2.6},
        ),
        species_name="s",
        trial_id=2,
        incumbent_signature=inc,
    )
    assert p["severity"] in ("watch", "blocking")
    assert any("route_path_hash" in r for r in p["reasons"])


def test_diagnostics_are_named_not_fake_signature_ids():
    # finding #2: schema/count live under explicit diagnostic keys, not fake IDs in the signature.
    p = compute_bsv_observe_payload(
        _er(
            oracle_adequacy={"a": 1, "b": 2},
            metric_schema_version=3,
            details={"trace_event_id": 42, "harness_metrics_id": 7},
        ),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )
    assert p["metric_schema_version"] == 3
    assert p["oracle_adequacy_count"] == 2
    assert p["trace_event_id"] == 42
    assert p["trace_event_id_source"] == "details.trace_event_id"
    assert p["harness_metrics_id"] == 7
    assert p["harness_metrics_id_source"] == "details.harness_metrics_id"
    assert p["signature"]["event_id"] == 42
    assert "harness_metrics_id" not in p["signature"]  # signature is the diffable subset only


def test_mutation_dependency_entry_extracts_bsv3_keys():
    incumbent = compute_bsv_observe_payload(
        _er(question_results=[{"qid": "q1", "correct": False}]),
        species_name="s",
        trial_id=1,
        incumbent_signature=None,
    )["signature"]
    payload = compute_bsv_observe_payload(
        _er(
            routing_distribution={"frontdoor": 1.0},
            question_results=[{"qid": "q1", "correct": True}],
        ),
        species_name="s",
        trial_id=2,
        incumbent_signature=incumbent,
        archive_member_id="trial:2",
    )
    entry = build_mutation_dependency_entry(
        trial_id=2,
        action={
            "type": "prompt_mutation",
            "file": "prompts/frontdoor.md",
            "section": "rubric",
            "flags": {"AUTOPILOT_BSV_OBSERVE": True},
        },
        parent_trial=1,
        bsv_payload=payload,
        incumbent_signature=incumbent,
        pareto_status="frontier",
    )
    assert entry["subsystem"] == "prompt"
    assert entry["files_touched"] == ["prompts/frontdoor.md"]
    assert entry["prompt_sections_touched"] == ["rubric"]
    assert entry["feature_flags"] == {"AUTOPILOT_BSV_OBSERVE": True}
    assert entry["behavior_signature_delta"]["improved_sentinels"] == ["q1"]
    assert entry["parent_trial"] == 1
    assert entry["archive_member_id"] == "trial:2"


def test_conflict_report_flags_shared_subsystem_and_file():
    prior = {
        "trial_id": 10,
        "action_type": "prompt_mutation",
        "subsystem": "prompt",
        "files_touched": ["prompts/frontdoor.md"],
        "prompt_sections_touched": ["rubric"],
        "feature_flags": {},
        "behavior_signature_delta": {
            "severity": "watch",
            "changed_fields": ["route_path_hash"],
            "improved_sentinels": ["q1"],
            "regressed_sentinels": [],
        },
    }
    new = {
        "trial_id": 11,
        "action_type": "prompt_mutation",
        "subsystem": "prompt",
        "files_touched": ["prompts/frontdoor.md"],
        "prompt_sections_touched": ["rubric"],
        "feature_flags": {},
        "behavior_signature_delta": {
            "severity": "watch",
            "changed_fields": ["token_bucket"],
            "improved_sentinels": ["q2"],
            "regressed_sentinels": [],
        },
    }
    report = build_conflict_report(new, [prior])
    assert report["severity"] == "blocking"
    assert report["conflict_count"] == 1
    assert report["conflicts"][0]["prior_trial"] == 10
    assert any("shared file" in reason for reason in report["conflicts"][0]["reasons"])
    assert any("sentinel movement" in reason for reason in report["conflicts"][0]["reasons"])


def test_conflict_report_ignores_disjoint_mutations():
    prior = {
        "trial_id": 10,
        "subsystem": "prompt",
        "files_touched": ["prompts/frontdoor.md"],
        "prompt_sections_touched": [],
        "feature_flags": {},
        "behavior_signature_delta": {"severity": "watch"},
    }
    new = {
        "trial_id": 11,
        "subsystem": "routing",
        "files_touched": ["src/routing/policy.py"],
        "prompt_sections_touched": [],
        "feature_flags": {},
        "behavior_signature_delta": {"severity": "watch"},
    }
    report = build_conflict_report(new, [prior])
    assert report["severity"] == "none"
    assert report["conflict_count"] == 0


def test_conflict_report_skips_same_trial_archive_member_duplicate():
    prior = {
        "trial_id": 10,
        "archive_member_id": "trial:10",
        "action_type": "prompt_mutation",
        "subsystem": "prompt",
        "files_touched": ["prompts/frontdoor.md"],
        "prompt_sections_touched": ["rubric"],
        "feature_flags": {},
        "behavior_signature_delta": {
            "severity": "watch",
            "changed_fields": ["route_path_hash"],
            "improved_sentinels": ["q1"],
            "regressed_sentinels": [],
        },
    }
    new = {
        **prior,
        "behavior_signature_delta": {
            "severity": "watch",
            "changed_fields": ["token_bucket"],
            "improved_sentinels": ["q2"],
            "regressed_sentinels": [],
        },
    }

    report = build_conflict_report(new, [prior])

    assert report["severity"] == "none"
    assert report["conflict_count"] == 0
