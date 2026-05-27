"""Unit tests for the HALO-2 OTLP converter (handoff: halo-trace-loop-spike.md HALO-2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import convert_tap_to_otel as conv  # type: ignore[import-not-found]


def _journal_row(trial_id: int = 1, quality: float = 1.5, speed: float = 40.0,
                 pareto: str = "frontier") -> dict:
    return {
        "trial_id": trial_id,
        "timestamp": "2026-04-12T07:05:13.659740+00:00",
        "species": "structural_lab",
        "action_type": "structural_prune",
        "tier": 1,
        "quality": quality,
        "speed": speed,
        "cost": 0.5,
        "reliability": 0.9,
        "pareto_status": pareto,
        "reasoning_hash": "abc123",
        "config_snapshot": {"type": "structural_prune", "file": "x.md"},
    }


def _telemetry_row(trial_id: int = 1, step_type: str = "controller_reasoning",
                   trace_id: str = "t" * 32, span_id: str = "s" * 16) -> dict:
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": "",
        "timestamp": "2026-04-12T07:05:13.659740+00:00",
        "duration_ms": 12.5,
        "trial_id": trial_id,
        "species": "structural_lab",
        "step_type": step_type,
        "input_text": "in",
        "output_text": "out",
        "reward": 1.5,
        "role": "worker_general",
        "action_type": "structural_prune",
    }


# ── journal converter ──────────────────────────────────────────────────


def test_journal_emits_four_spans_per_trial(tmp_path):
    src = tmp_path / "j.jsonl"
    src.write_text(json.dumps(_journal_row()) + "\n")
    out = tmp_path / "o.jsonl"
    n = conv.convert_journal(src, out)
    assert n == 4
    spans = [json.loads(line) for line in out.read_text().splitlines()]
    names = [s["name"] for s in spans]
    assert names == [
        "structural_lab/controller_reasoning",
        "structural_lab/action_execution",
        "structural_lab/eval",
        "structural_lab/safety_gate",
    ]


def test_journal_spans_share_trace_and_parent(tmp_path):
    src = tmp_path / "j.jsonl"
    src.write_text(json.dumps(_journal_row()) + "\n")
    out = tmp_path / "o.jsonl"
    conv.convert_journal(src, out)
    spans = [json.loads(line) for line in out.read_text().splitlines()]
    trace_ids = {s["traceId"] for s in spans}
    parent_ids = {s["parentSpanId"] for s in spans}
    span_ids = {s["spanId"] for s in spans}
    assert len(trace_ids) == 1, "all 4 spans must share one traceId"
    assert len(parent_ids) == 1, "all 4 spans must share one parent (the trial-level node)"
    assert len(span_ids) == 4, "each span must have a unique spanId"


def test_journal_failed_trial_marks_safety_gate_status(tmp_path):
    src = tmp_path / "j.jsonl"
    src.write_text(json.dumps(_journal_row(pareto="rejected")) + "\n")
    out = tmp_path / "o.jsonl"
    conv.convert_journal(src, out)
    spans = [json.loads(line) for line in out.read_text().splitlines()]
    gate = next(s for s in spans if s["name"].endswith("/safety_gate"))
    assert gate["status"]["code"] == "STATUS_CODE_UNSET"
    out_attr = next(a["value"]["stringValue"] for a in gate["attributes"] if a["key"] == "output_text")
    assert "failed" in out_attr


def test_journal_multiple_trials_distinct_traces(tmp_path):
    src = tmp_path / "j.jsonl"
    src.write_text(json.dumps(_journal_row(trial_id=1)) + "\n"
                   + json.dumps(_journal_row(trial_id=2)) + "\n")
    out = tmp_path / "o.jsonl"
    conv.convert_journal(src, out)
    spans = [json.loads(line) for line in out.read_text().splitlines()]
    trace_ids = {s["traceId"] for s in spans}
    assert len(trace_ids) == 2


# ── telemetry converter ────────────────────────────────────────────────


def test_telemetry_preserves_trace_id(tmp_path):
    src = tmp_path / "t.jsonl"
    src.write_text(json.dumps(_telemetry_row()) + "\n")
    out = tmp_path / "o.jsonl"
    n = conv.convert_autopilot_telemetry(src, out)
    assert n == 1
    span = json.loads(out.read_text().splitlines()[0])
    assert span["traceId"] == "t" * 32
    assert span["spanId"] == "s" * 16


def test_telemetry_assigns_parent_to_followups(tmp_path):
    src = tmp_path / "t.jsonl"
    rows = [
        _telemetry_row(trial_id=1, step_type="controller_reasoning",
                       trace_id="a" * 32, span_id="1" * 16),
        _telemetry_row(trial_id=1, step_type="action_execution",
                       trace_id="a" * 32, span_id="2" * 16),
        _telemetry_row(trial_id=2, step_type="controller_reasoning",
                       trace_id="b" * 32, span_id="3" * 16),
    ]
    src.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    out = tmp_path / "o.jsonl"
    conv.convert_autopilot_telemetry(src, out)
    spans = [json.loads(line) for line in out.read_text().splitlines()]
    assert spans[0]["parentSpanId"] == "", "first span per trial has no parent"
    assert spans[1]["parentSpanId"] == "1" * 16, "second span gets first span as parent"
    assert spans[2]["parentSpanId"] == "", "new trial → new parent chain"


# ── source detection ───────────────────────────────────────────────────


def test_detect_source_journal(tmp_path):
    src = tmp_path / "j.jsonl"
    src.write_text(json.dumps(_journal_row()) + "\n")
    assert conv._detect_source(src) == "journal"


def test_detect_source_telemetry(tmp_path):
    src = tmp_path / "t.jsonl"
    src.write_text(json.dumps(_telemetry_row()) + "\n")
    assert conv._detect_source(src) == "telemetry"


# ── CLI entry point ────────────────────────────────────────────────────


def test_cli_runs_against_journal(tmp_path, capsys):
    src = tmp_path / "j.jsonl"
    src.write_text(json.dumps(_journal_row()) + "\n")
    out = tmp_path / "o.jsonl"
    rc = conv.main([str(src), "-o", str(out)])
    assert rc == 0
    assert out.exists()
    captured = capsys.readouterr().out
    assert "wrote 4 OTLP spans" in captured
    assert "source=journal" in captured
