"""Tests for RI-10 canary rollout decision reporting."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.analysis import ri10_canary_decision_report as report_mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _routing_row(
    task_id: str,
    timestamp: str,
    *,
    mode: str,
    role: str = "frontdoor",
    cost: float = 0.001,
) -> dict:
    return {
        "event_type": "routing_decision",
        "task_id": task_id,
        "timestamp": timestamp,
        "data": {
            "routing": [role],
            "factual_risk_score": 0.72,
            "factual_risk_band": "high",
            "factual_risk_mode": mode,
            "risk_gate_action": "not_enforced",
            "estimated_cost": cost,
        },
    }


def _completed(task_id: str, timestamp: str, *, elapsed: float, outcome: str = "success") -> dict:
    return {
        "event_type": "task_completed",
        "task_id": task_id,
        "timestamp": timestamp,
        "outcome": outcome,
        "outcome_details": f"Direct answer mode (frontdoor), {elapsed:.3f}s",
        "data": {"final_answer_role": "frontdoor"},
    }


def _write_scored_summary(
    path: Path,
    *,
    enforce_accuracy: float,
    shadow_accuracy: float,
    enforce_f1: float = 0.2,
    shadow_f1: float = 0.1,
) -> None:
    payload = {
        "schema_version": "ri10_canary_scored_response_report.v1",
        "generated_at": "2026-07-05T18:56:38Z",
        "answer_key_schema": "ri10_canary_answer_key.v1",
        "f1_threshold": 0.8,
        "status": "ready",
        "rows": 20,
        "status_counts": {"scored": 20},
        "buckets": {
            "arm:enforce": {
                "rows": 10,
                "scored": 10,
                "missing": 0,
                "correct": int(enforce_accuracy * 10),
                "accuracy": enforce_accuracy,
                "mean_token_f1": enforce_f1,
            },
            "arm:shadow": {
                "rows": 10,
                "scored": 10,
                "missing": 0,
                "correct": int(shadow_accuracy * 10),
                "accuracy": shadow_accuracy,
                "mean_token_f1": shadow_f1,
            },
        },
        "arm_comparison": {
            "status": "ready",
            "accuracy_delta_enforce_minus_shadow": enforce_accuracy - shadow_accuracy,
            "mean_token_f1_delta_enforce_minus_shadow": enforce_f1 - shadow_f1,
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_build_report_holds_when_factuality_is_unscored(tmp_path: Path) -> None:
    rows = [
        _routing_row("e1", "2026-06-20T00:00:00Z", mode="enforce", cost=0.001),
        _completed("e1", "2026-06-20T00:00:02Z", elapsed=1.0),
        _routing_row("s1", "2026-06-20T00:01:00Z", mode="shadow", cost=0.002),
        _completed("s1", "2026-06-20T00:01:03Z", elapsed=2.0),
    ]
    _write_jsonl(tmp_path / "2026-06-20.jsonl", rows)

    report = report_mod.build_report(
        tmp_path,
        telemetry_health_start="2026-06-20",
        decision_gate=2,
        min_arm_samples=1,
    )

    assert report["sample_coverage"]["canary_decision_ready"] is True
    assert report["decision"]["status"] == "hold_quality_unscored"
    assert report["decision"]["blockers"] == ["factuality_not_scored"]
    assert report["arms"]["enforce"]["rows"] == 1
    assert report["arms"]["shadow"]["rows"] == 1
    assert report["comparison"]["estimated_cost_mean_ratio_enforce_over_shadow"] == 0.5


def test_build_report_holds_when_scored_factuality_has_no_enforce_lift(tmp_path: Path) -> None:
    rows = [
        _routing_row("e1", "2026-06-20T00:00:00Z", mode="enforce"),
        _completed("e1", "2026-06-20T00:00:02Z", elapsed=1.0),
        _routing_row("s1", "2026-06-20T00:01:00Z", mode="shadow"),
        _completed("s1", "2026-06-20T00:01:03Z", elapsed=1.0),
    ]
    _write_jsonl(tmp_path / "2026-06-20.jsonl", rows)
    scored_path = tmp_path / "scored_summary.json"
    _write_scored_summary(scored_path, enforce_accuracy=0.1, shadow_accuracy=0.1)

    report = report_mod.build_report(
        tmp_path,
        telemetry_health_start="2026-06-20",
        decision_gate=2,
        min_arm_samples=1,
        scored_summary_path=scored_path,
    )

    assert report["quality_evidence"]["status"] == "ready"
    assert report["quality_evidence"]["arms"]["enforce"]["scored"] == 10
    assert report["decision"]["status"] == "hold_quality_scored_no_lift"
    assert report["decision"]["blockers"] == ["factuality_no_enforce_lift"]


def test_build_report_promotes_when_scored_factuality_lifts_without_blockers(tmp_path: Path) -> None:
    rows = [
        _routing_row("e1", "2026-06-20T00:00:00Z", mode="enforce"),
        _completed("e1", "2026-06-20T00:00:02Z", elapsed=1.0),
        _routing_row("s1", "2026-06-20T00:01:00Z", mode="shadow"),
        _completed("s1", "2026-06-20T00:01:03Z", elapsed=1.0),
    ]
    _write_jsonl(tmp_path / "2026-06-20.jsonl", rows)
    scored_path = tmp_path / "scored_summary.json"
    _write_scored_summary(scored_path, enforce_accuracy=0.2, shadow_accuracy=0.1)

    report = report_mod.build_report(
        tmp_path,
        telemetry_health_start="2026-06-20",
        decision_gate=2,
        min_arm_samples=1,
        scored_summary_path=scored_path,
    )

    assert report["decision"]["status"] == "promote_candidate"
    assert report["decision"]["blockers"] == []


def test_build_report_blocks_latency_regression(tmp_path: Path) -> None:
    rows = [
        _routing_row("e1", "2026-06-20T00:00:00Z", mode="enforce"),
        _completed("e1", "2026-06-20T00:00:30Z", elapsed=30.0),
        _routing_row("s1", "2026-06-20T00:01:00Z", mode="shadow"),
        _completed("s1", "2026-06-20T00:01:03Z", elapsed=3.0),
    ]
    _write_jsonl(tmp_path / "2026-06-20.jsonl", rows)

    report = report_mod.build_report(
        tmp_path,
        telemetry_health_start="2026-06-20",
        decision_gate=2,
        min_arm_samples=1,
    )

    assert report["decision"]["status"] == "hold"
    assert "p95_latency_regression" in report["decision"]["blockers"]
    assert "factuality_not_scored" in report["decision"]["blockers"]
    assert report["comparison"]["latency_p95_ratio_enforce_over_shadow"] == 10.0


def test_build_report_counts_escalation_and_plan_review_by_arm(tmp_path: Path) -> None:
    rows = [
        _routing_row("e1", "2026-06-20T00:00:00Z", mode="enforce"),
        {
            "event_type": "escalation_triggered",
            "task_id": "e1",
            "timestamp": "2026-06-20T00:00:01Z",
            "data": {"from_tier": "frontdoor", "to_tier": "coder_escalation"},
        },
        {
            "event_type": "plan_reviewed",
            "task_id": "e1",
            "timestamp": "2026-06-20T00:00:02Z",
            "data": {"decision": "add"},
        },
        _completed("e1", "2026-06-20T00:00:03Z", elapsed=1.0),
        _routing_row("s1", "2026-06-20T00:01:00Z", mode="shadow"),
        _completed("s1", "2026-06-20T00:01:03Z", elapsed=1.0),
    ]
    _write_jsonl(tmp_path / "2026-06-20.jsonl", rows)

    report = report_mod.build_report(
        tmp_path,
        telemetry_health_start="2026-06-20",
        decision_gate=2,
        min_arm_samples=1,
    )

    enforce = report["arms"]["enforce"]
    assert enforce["escalation_task_count"] == 1
    assert enforce["plan_review_task_count"] == 1
    assert enforce["plan_review_decisions"] == {"add": 1}
    assert "escalation_rate_inflation" in report["decision"]["blockers"]
    assert "review_rate_inflation" in report["decision"]["blockers"]


def test_build_report_awaits_telemetry_when_sample_is_not_ready(tmp_path: Path) -> None:
    rows = [
        _routing_row("e1", "2026-06-20T00:00:00Z", mode="enforce"),
        _completed("e1", "2026-06-20T00:00:03Z", elapsed=1.0),
    ]
    _write_jsonl(tmp_path / "2026-06-20.jsonl", rows)

    report = report_mod.build_report(
        tmp_path,
        telemetry_health_start="2026-06-20",
        decision_gate=2,
        min_arm_samples=1,
    )

    assert report["decision"]["status"] == "awaiting_telemetry"
    assert "telemetry_not_decision_ready" in report["decision"]["blockers"]


def test_render_markdown_includes_status_and_arm_table(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "2026-06-20.jsonl",
        [
            _routing_row("e1", "2026-06-20T00:00:00Z", mode="enforce"),
            _completed("e1", "2026-06-20T00:00:02Z", elapsed=1.0),
            _routing_row("s1", "2026-06-20T00:01:00Z", mode="shadow"),
            _completed("s1", "2026-06-20T00:01:03Z", elapsed=2.0),
        ],
    )

    markdown = report_mod.render_markdown(
        report_mod.build_report(
            tmp_path,
            telemetry_health_start="2026-06-20",
            decision_gate=2,
            min_arm_samples=1,
        )
    )

    assert "# RI-10 Canary Decision Report" in markdown
    assert "hold_quality_unscored" in markdown
    assert "| enforce |" in markdown
