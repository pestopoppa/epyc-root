"""Tests for RI-10 canary sample coverage reporting."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.analysis import ri10_canary_sample_report as report_mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _routing_row(
    timestamp: str,
    *,
    band: str,
    action: str = "",
    mode: str = "",
    routing: list[str] | None = None,
) -> dict:
    return {
        "event_type": "routing_decision",
        "timestamp": timestamp,
        "data": {
            "routing": routing or ["frontdoor"],
            "factual_risk_score": 0.72 if band == "high" else 0.2,
            "factual_risk_band": band,
            "risk_gate_action": action,
            "factual_risk_mode": mode,
            "decision_source": "rules",
        },
    }


def test_build_report_counts_high_risk_and_canary_arms(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "2026-04-07.jsonl",
        [
            _routing_row("2026-04-07T00:00:00Z", band="high", action="enforce"),
            _routing_row("2026-04-07T00:01:00Z", band="high", action="shadow"),
            _routing_row("2026-04-07T00:02:00Z", band="low", action="shadow"),
        ],
    )
    _write_jsonl(
        tmp_path / "2026-04-05.jsonl",
        [_routing_row("2026-04-05T00:00:00Z", band="high", action="enforce")],
    )

    summary = report_mod.build_report(
        tmp_path,
        canary_start="2026-04-06",
        decision_gate=2,
        min_arm_samples=1,
    )

    assert summary["high_risk_rows_total"] == 3
    assert summary["high_risk_rows_since_canary_start"] == 2
    assert summary["frontdoor_high_risk_rows_since_canary_start"] == 2
    assert summary["sample_count_ready"] is True
    assert summary["canary_arm_sample_count_ready"] is True
    assert summary["canary_arm_balance_ready"] is True
    assert summary["canary_decision_ready"] is True
    assert summary["canary_arm_counts_since_canary_start"] == {
        "enforce_high_risk": 1,
        "shadow_high_risk": 1,
    }


def test_build_report_requires_observable_canary_arms(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "2026-04-07.jsonl",
        [
            _routing_row(
                "2026-04-07T00:00:00Z",
                band="high",
                action="not_enforced",
                routing=["frontdoor"],
            ),
            _routing_row(
                "2026-04-07T00:01:00Z",
                band="high",
                action="not_enforced",
                routing=["frontdoor"],
            ),
        ],
    )

    summary = report_mod.build_report(tmp_path, canary_start="2026-04-06", decision_gate=2)

    assert summary["sample_count_ready"] is True
    assert summary["canary_decision_ready"] is False
    assert "observable enforce/shadow canary arms" in summary["decision_reason"]


def test_build_report_requires_decision_grade_arm_counts(tmp_path: Path) -> None:
    rows = []
    rows.extend(
        _routing_row(
            f"2026-04-07T00:{idx:02d}:00Z",
            band="high",
            mode="shadow",
            routing=["frontdoor"],
        )
        for idx in range(18)
    )
    rows.append(
        _routing_row(
            "2026-04-07T01:00:00Z",
            band="high",
            mode="enforce",
            routing=["frontdoor"],
        )
    )
    rows.extend(
        _routing_row(
            f"2026-04-07T02:{idx:02d}:00Z",
            band="high",
            action="not_enforced",
            routing=["frontdoor"],
        )
        for idx in range(40)
    )
    _write_jsonl(tmp_path / "2026-04-07.jsonl", rows)

    summary = report_mod.build_report(
        tmp_path,
        canary_start="2026-04-06",
        decision_gate=50,
        min_arm_samples=10,
    )

    assert summary["high_risk_rows_since_canary_start"] == 59
    assert summary["evaluable_canary_arm_high_risk_rows"] == 19
    assert summary["non_evaluable_high_risk_rows_since_canary_start"] == 40
    assert summary["canary_role_observable_factual_risk_mode_high_risk_rows"] == 19
    assert summary["canary_role_missing_factual_risk_mode_high_risk_rows"] == 40
    assert summary["canary_role_factual_risk_modes_since_canary_start"] == {
        "<missing>": 40,
        "enforce": 1,
        "shadow": 18,
    }
    assert summary["sample_count_ready"] is True
    assert summary["canary_arm_sample_count_ready"] is False
    assert summary["canary_arm_balance_ready"] is False
    assert summary["canary_decision_ready"] is False


def test_build_report_does_not_count_non_canary_role_shadow_as_arm(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "2026-04-07.jsonl",
        [
            _routing_row(
                "2026-04-07T00:00:00Z",
                band="high",
                mode="enforce",
                routing=["frontdoor"],
            ),
            _routing_row(
                "2026-04-07T00:01:00Z",
                band="high",
                mode="shadow",
                routing=["frontdoor"],
            ),
            _routing_row(
                "2026-04-07T00:02:00Z",
                band="high",
                mode="shadow",
                routing=["worker_general"],
            ),
        ],
    )

    summary = report_mod.build_report(
        tmp_path,
        canary_start="2026-04-06",
        decision_gate=3,
        min_arm_samples=1,
    )

    assert summary["high_risk_rows_since_canary_start"] == 3
    assert summary["canary_roles"] == ["frontdoor"]
    assert summary["canary_role_high_risk_rows_since_canary_start"] == 2
    assert summary["non_canary_role_high_risk_rows_since_canary_start"] == 1
    assert summary["evaluable_canary_arm_high_risk_rows"] == 2
    assert summary["canary_role_factual_risk_modes_since_canary_start"] == {
        "enforce": 1,
        "shadow": 1,
    }
    assert summary["canary_arm_counts_since_canary_start"] == {
        "enforce_high_risk": 1,
        "shadow_high_risk": 1,
    }


def test_build_report_separates_factual_mode_from_memory_gate_action(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "2026-04-07.jsonl",
        [
            _routing_row(
                "2026-04-07T00:00:00Z",
                band="high",
                action="not_enforced",
                routing=["frontdoor"],
            ),
            _routing_row(
                "2026-04-07T00:01:00Z",
                band="high",
                mode="shadow",
                action="not_enforced",
                routing=["frontdoor"],
            ),
        ],
    )

    summary = report_mod.build_report(
        tmp_path,
        canary_start="2026-04-06",
        decision_gate=2,
        min_arm_samples=1,
    )

    assert summary["high_risk_gate_actions_since_canary_start"] == {"not_enforced": 2}
    assert summary["memory_risk_gate_actions_since_canary_start"] == {"not_enforced": 2}
    assert summary["canary_role_factual_risk_modes_since_canary_start"] == {
        "<missing>": 1,
        "shadow": 1,
    }
    assert summary["canary_role_missing_factual_risk_mode_high_risk_rows"] == 1
    assert summary["evaluable_canary_arm_high_risk_rows"] == 1


def test_build_report_separates_historical_missing_modes_from_current_scope_starvation(
    tmp_path: Path,
) -> None:
    _write_jsonl(
        tmp_path / "2026-04-07.jsonl",
        [
            _routing_row(
                "2026-04-07T00:00:00Z",
                band="high",
                action="not_enforced",
                routing=["frontdoor"],
            )
        ],
    )
    _write_jsonl(
        tmp_path / "2026-06-20.jsonl",
        [
            _routing_row(
                "2026-06-20T00:00:00Z",
                band="high",
                mode="shadow",
                routing=["worker_general"],
            ),
            _routing_row(
                "2026-06-20T00:01:00Z",
                band="high",
                mode="shadow",
                routing=["worker_vision"],
            ),
            _routing_row(
                "2026-06-20T00:02:00Z",
                band="high",
                mode="shadow",
                routing=["worker_general"],
            ),
            _routing_row(
                "2026-06-20T00:03:00Z",
                band="high",
                mode="shadow",
                routing=["frontdoor"],
            ),
            _routing_row(
                "2026-06-20T00:04:00Z",
                band="high",
                mode="enforce",
                routing=["frontdoor"],
            ),
        ],
    )

    summary = report_mod.build_report(
        tmp_path,
        canary_start="2026-04-06",
        telemetry_health_start="2026-06-20",
        decision_gate=10,
        min_arm_samples=1,
    )

    assert summary["canary_role_missing_factual_risk_mode_high_risk_rows"] == 1
    assert summary["high_risk_rows_since_telemetry_health_start"] == 5
    assert summary["canary_role_high_risk_rows_since_telemetry_health_start"] == 2
    assert summary["non_canary_role_high_risk_rows_since_telemetry_health_start"] == 3
    assert summary["missing_factual_risk_mode_high_risk_rows_since_telemetry_health_start"] == 0
    assert (
        summary[
            "canary_role_missing_factual_risk_mode_high_risk_rows_since_telemetry_health_start"
        ]
        == 0
    )
    assert summary["telemetry_producer_currently_healthy"] is True
    assert summary["telemetry_canary_role_scope_starved"] is True
    assert summary["telemetry_collection_blocker"] == "canary_role_scope_starved"
    assert summary["canary_arm_counts_since_telemetry_health_start"] == {
        "enforce_high_risk": 1,
        "shadow_high_risk": 1,
    }
    assert summary["high_risk_by_role_since_telemetry_health_start"] == {
        "frontdoor": 2,
        "worker_general": 2,
        "worker_vision": 1,
    }
    assert summary["canary_role_high_risk_by_role_since_telemetry_health_start"] == {
        "frontdoor": 2
    }
    assert summary["canary_arm_counts_by_role_since_telemetry_health_start"] == {
        "frontdoor": {
            "enforce_high_risk": 1,
            "shadow_high_risk": 1,
        }
    }
    assert summary["canary_role_sample_deficit_since_telemetry_health_start"] == 8
    assert summary["canary_arm_volume_deficit_since_telemetry_health_start"] == 8
    assert summary["canary_arm_balance_deficits_since_telemetry_health_start"] == {
        "enforce_high_risk": 0,
        "shadow_high_risk": 0,
    }


def test_build_report_flags_current_missing_factual_mode(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "2026-06-20.jsonl",
        [
            _routing_row(
                "2026-06-20T00:00:00Z",
                band="high",
                action="not_enforced",
                routing=["frontdoor"],
            )
        ],
    )

    summary = report_mod.build_report(
        tmp_path,
        canary_start="2026-04-06",
        telemetry_health_start="2026-06-20",
        decision_gate=1,
        min_arm_samples=1,
    )

    assert summary["high_risk_rows_since_telemetry_health_start"] == 1
    assert summary["missing_factual_risk_mode_high_risk_rows_since_telemetry_health_start"] == 1
    assert (
        summary[
            "canary_role_missing_factual_risk_mode_high_risk_rows_since_telemetry_health_start"
        ]
        == 1
    )
    assert summary["telemetry_producer_currently_healthy"] is False
    assert summary["telemetry_collection_blocker"] == "current_missing_factual_risk_mode"


def test_configured_canary_roles_reads_classifier_config(tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
factual_risk:
  mode: canary
  canary_roles:
    - frontdoor
    - worker_general
    - worker_vision
""",
        encoding="utf-8",
    )

    assert report_mod._configured_canary_roles(config) == [
        "frontdoor",
        "worker_general",
        "worker_vision",
    ]


def test_main_uses_configured_canary_roles_by_default(tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
factual_risk:
  mode: canary
  canary_roles: [frontdoor, worker_general]
""",
        encoding="utf-8",
    )
    log_dir = tmp_path / "logs"
    _write_jsonl(
        log_dir / "2026-06-20.jsonl",
        [
            _routing_row(
                "2026-06-20T00:00:00Z",
                band="high",
                mode="shadow",
                routing=["worker_general"],
            )
        ],
    )
    output = tmp_path / "report.json"

    rc = report_mod.main(
        [
            "--log-dir",
            str(log_dir),
            "--classifier-config",
            str(config),
            "--canary-start",
            "2026-04-06",
            "--telemetry-health-start",
            "2026-06-20",
            "--output",
            str(output),
        ]
    )

    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["canary_roles"] == ["frontdoor", "worker_general"]
    assert summary["canary_role_high_risk_rows_since_telemetry_health_start"] == 1
    assert summary["non_canary_role_high_risk_rows_since_telemetry_health_start"] == 0
