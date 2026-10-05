from __future__ import annotations

import json

from scripts.analysis.trinity_shadow_telemetry import (
    render_report,
    summarize_trinity_telemetry,
)


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def _routing_row(task_id: str, timestamp: str, role: str | None, strategy: str = "learned"):
    data = {
        "strategy": strategy,
        "decision_source": strategy,
    }
    if role is not None:
        data["assigned_role"] = role
    return {
        "event_type": "routing_decision",
        "task_id": task_id,
        "timestamp": timestamp,
        "data": data,
    }


def test_summarize_trinity_telemetry_counts_roles_and_window(tmp_path):
    _write_jsonl(
        tmp_path / "2026-06-12.jsonl",
        [
            _routing_row("t1", "2026-06-12T00:00:00+00:00", "worker"),
            _routing_row("t2", "2026-06-12T12:00:00+00:00", "thinker", "mock"),
            _routing_row("t3", "2026-06-12T23:59:00+00:00", "verifier"),
            _routing_row("t4", "2026-06-12T23:59:01+00:00", None),
            {"event_type": "task_completed", "task_id": "t1", "data": {}},
            "{not-json",
        ],
    )

    report = summarize_trinity_telemetry(
        log_dir=tmp_path,
        from_date="2026-06-12",
        to_date="2026-06-12",
        min_days=7.0,
    )

    assert report.total_routing_rows == 4
    assert report.role_bearing_rows == 3
    assert report.missing_role_rows == 1
    assert report.malformed_rows == 1
    assert report.role_counts == {"worker": 1, "thinker": 1, "verifier": 1}
    assert report.strategy_counts == {"learned": 3, "mock": 1}
    assert report.distribution_non_degenerate is True
    assert report.collection_window_satisfied is False


def test_render_report_keeps_collection_gate_separate_from_distribution(tmp_path):
    _write_jsonl(
        tmp_path / "2026-06-12.jsonl",
        [
            _routing_row(f"w{i}", f"2026-06-12T00:00:{i:02d}+00:00", "worker")
            for i in range(9)
        ]
        + [_routing_row("x", "2026-06-12T00:01:00+00:00", "thinker")],
    )

    report = summarize_trinity_telemetry(log_dir=tmp_path, min_days=7.0)
    rendered = render_report(report)

    assert "TR-3.3 collection window: PENDING" in rendered
    assert "TR-3.4 non-degenerate distribution: PASS" in rendered
    assert "Do not promote TR-4/5" in rendered
