from __future__ import annotations

import json

from scripts.benchmark import dcp_j7_ab as dcp


def test_arm_sequence_uses_abba_blocks():
    assert dcp._arm_sequence(1) == [False, True]
    assert dcp._arm_sequence(2) == [False, True, True, False]


def test_summarize_response_extracts_delegation_metrics():
    data = {
        "elapsed_seconds": 12.5,
        "turns": 3,
        "tokens_used": 101,
        "tokens_generated": 55,
        "prompt_eval_ms": 4.0,
        "generation_ms": 8.0,
        "predicted_tps": 6.875,
        "tools_used": 2,
        "tools_called": ["open", "grep"],
        "delegation_success": True,
        "delegation_diagnostics": {
            "break_reason": "synthesis_complete",
            "report_handles_count": 1,
            "delegation_inference_hops": 2,
        },
        "delegation_events": [
            {
                "tokens_generated": 11,
                "inference_meta": {"tokens": 7, "prompt_ms": 10.5},
            },
            {
                "tokens_generated": 13,
                "inference_meta": {"prompt_ms": 2.5},
            },
        ],
        "answer": "done",
    }

    summary = dcp._summarize_response(data, elapsed_s=13.25, status=200)

    assert summary["status"] == 200
    assert summary["elapsed_s"] == 13.25
    assert summary["tools_called_count"] == 2
    assert summary["delegation_events_count"] == 2
    assert summary["delegation_break_reason"] == "synthesis_complete"
    assert summary["delegation_inference_hops"] == 2
    assert summary["delegation_event_tokens"] == 20
    assert summary["delegation_event_prompt_ms"] == 13.0
    assert summary["quality_score"] is None
    assert summary["quality_pass"] is None
    assert summary["answer_chars"] == 4


def test_aggregate_reports_arm_deltas():
    rows = [
        {
            "arm": "off",
            "summary": {
                "elapsed_s": 10,
                "tokens_generated": 100,
                "delegation_event_tokens": 80,
                "delegation_events_count": 2,
                "status": 200,
            },
        },
        {
            "arm": "off",
            "summary": {
                "elapsed_s": 20,
                "tokens_generated": 120,
                "delegation_event_tokens": 90,
                "delegation_events_count": 2,
                "status": 200,
            },
        },
        {
            "arm": "on",
            "summary": {
                "elapsed_s": 8,
                "tokens_generated": 70,
                "delegation_event_tokens": 50,
                "delegation_events_count": 1,
                "status": 200,
            },
        },
        {
            "arm": "on",
            "summary": {
                "elapsed_s": 12,
                "tokens_generated": 90,
                "delegation_event_tokens": 60,
                "delegation_events_count": 1,
                "status": 200,
            },
        },
    ]

    agg = dcp._aggregate(rows)

    assert agg["off"]["n"] == 2
    assert agg["on"]["n"] == 2
    assert agg["off"]["p50_elapsed_s"] == 20
    assert agg["on"]["p50_elapsed_s"] == 12
    assert agg["delta"]["p50_elapsed_pct"] == 0.4
    assert agg["delta"]["avg_tokens_generated_delta"] == -30
    assert agg["delta"]["avg_delegation_event_tokens_delta"] == -30
    assert agg["decision"]["status"] == "insufficient"
    assert "too_few_rows_per_arm" in agg["decision"]["blockers"]
    assert "quality_not_scored" in agg["decision"]["blockers"]


def test_decision_holds_on_latency_regression():
    rows = []
    for index in range(3):
        rows.append(
            {
                "arm": "off",
                "summary": {
                    "elapsed_s": 20 + index,
                    "tokens_generated": 100,
                    "delegation_event_tokens": 80,
                    "delegation_events_count": 2,
                    "delegation_success": True,
                    "quality_score": 1.0,
                    "quality_pass": True,
                    "status": 200,
                },
            }
        )
        rows.append(
            {
                "arm": "on",
                "summary": {
                    "elapsed_s": 30 + index,
                    "tokens_generated": 80,
                    "delegation_event_tokens": 60,
                    "delegation_events_count": 1,
                    "delegation_success": True,
                    "quality_score": 1.0,
                    "quality_pass": True,
                    "status": 200,
                },
            }
        )

    agg = dcp._aggregate(rows)

    assert agg["decision"]["status"] == "hold"
    assert agg["decision"]["recommendation"] == "keep dcp_pre_assembly default-off"
    assert "latency_not_improved" in agg["decision"]["blockers"]


def test_decision_promotes_only_with_quality_and_latency_pass():
    rows = []
    for index in range(3):
        rows.append(
            {
                "arm": "off",
                "summary": {
                    "elapsed_s": 20 + index,
                    "tokens_generated": 100,
                    "delegation_event_tokens": 80,
                    "delegation_events_count": 2,
                    "delegation_success": True,
                    "quality_score": 1.0,
                    "quality_pass": True,
                    "status": 200,
                },
            }
        )
        rows.append(
            {
                "arm": "on",
                "summary": {
                    "elapsed_s": 10 + index,
                    "tokens_generated": 80,
                    "delegation_event_tokens": 60,
                    "delegation_events_count": 1,
                    "delegation_success": True,
                    "quality_score": 1.0,
                    "quality_pass": True,
                    "status": 200,
                },
            }
        )

    agg = dcp._aggregate(rows)

    assert agg["decision"]["status"] == "promote_advisory"
    assert agg["decision"]["blockers"] == []


def test_real_run_refuses_without_host_quiet(capsys):
    code = dcp.main(["--real", "--reps", "1"])
    err = capsys.readouterr().err

    assert code == 2
    assert "REFUSING real J7 run" in err


def test_default_main_is_stub_and_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(dcp, "_orch_head", lambda: "abc123")
    code = dcp.main(["--reps", "1", "--output", str(tmp_path)])

    assert code == 0
    assert '"mode": "stub"' in (tmp_path / "meta.json").read_text()
    assert len((tmp_path / "results.jsonl").read_text().strip().splitlines()) == len(dcp.PROMPTS) * 2


def test_stub_main_writes_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(dcp, "_orch_head", lambda: "abc123")
    code = dcp.main(["--stub", "--reps", "1", "--output", str(tmp_path)])

    assert code == 0
    assert (tmp_path / "meta.json").exists()
    assert (tmp_path / "summary.json").exists()
    rows = (tmp_path / "results.jsonl").read_text().strip().splitlines()
    assert len(rows) == len(dcp.PROMPTS) * 2
    assert '"orch_checkout_unchanged": true' in (tmp_path / "meta.json").read_text()
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["decision"]["schema_version"] == "dcp_j7_decision.v1"
    assert isinstance(summary["decision"]["blockers"], list)
