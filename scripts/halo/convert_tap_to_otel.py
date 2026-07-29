#!/usr/bin/env python3
"""Convert EPYC autopilot trace artifacts → OTel/OTLP-shaped JSONL for HALO.

Spike target: feed halo-engine an OTLP-shaped trace it can analyze. The handoff
estimates ~30 LoC for autopilot telemetry alone; this is bigger because in
practice the live artifact is `autopilot_journal.jsonl` (one row per trial,
emitted by every production run) and the OTLP-shaped `TelemetryCollector` is
not enabled by default. We accept either source.

Sources supported:
  * `autopilot_telemetry.jsonl` — per-transition TransitionRecord rows
    (TelemetryCollector — already OTLP-shaped via `.to_otlp_span()`).
  * `autopilot_journal.jsonl` — per-trial summary rows (the actually-live
    artifact); synthesize 4 spans per trial: controller_reasoning → action →
    eval → safety_gate. Mirrors the structure that TelemetryCollector
    .record_trial() would have produced, so HALO sees the same shape either way.

Output: a JSONL file where each line is one OTLP span object
(traceId/spanId/parentSpanId/name/startTimeUnixNano/endTimeUnixNano/attributes/status),
grouped into traces by trial_id.

No halo-engine import; the converter is the only thing that needs to ship
before HALO-3 (running halo against the output) can be operator-approved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


# ── public API ─────────────────────────────────────────────────────────


def convert_autopilot_telemetry(input_path: Path, output_path: Path) -> int:
    """OTLP-shaped TelemetryCollector rows → OTLP JSONL. ~30 LoC core (handoff target).

    Each input row is already a TransitionRecord (asdict); we re-emit each as
    an OTLP span via the same to_otlp_span() shape, and assemble parent links
    by treating the first span per trial as the parent.
    """
    written = 0
    parent_by_trial: dict[int, str] = {}
    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            trial_id = int(row.get("trial_id", 0))
            span = _telemetry_row_to_otlp_span(row, parent_by_trial.get(trial_id, ""))
            parent_by_trial.setdefault(trial_id, span["spanId"])
            dst.write(json.dumps(span, default=str) + "\n")
            written += 1
    return written


def convert_journal(input_path: Path, output_path: Path) -> int:
    """`autopilot_journal.jsonl` → OTLP JSONL.

    Synthesises 4 spans per trial in the same step_type order that
    TelemetryCollector.record_trial() would emit, so HALO sees the same shape
    regardless of source. Each trial becomes one trace.
    """
    written = 0
    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            trial = json.loads(line)
            for span in _journal_trial_to_otlp_spans(trial):
                dst.write(json.dumps(span, default=str) + "\n")
                written += 1
    return written


# ── helpers ────────────────────────────────────────────────────────────


def _telemetry_row_to_otlp_span(row: dict[str, Any], parent_span_id: str) -> dict[str, Any]:
    """Re-emit a TransitionRecord row as an OTLP span (mirrors to_otlp_span)."""
    ts = row.get("timestamp", "")
    start_ns = _iso_to_unix_nanos(ts)
    duration_ns = int(float(row.get("duration_ms", 0.0)) * 1e6)
    return {
        "traceId": row.get("trace_id", ""),
        "spanId": row.get("span_id", ""),
        "parentSpanId": row.get("parent_span_id", "") or parent_span_id,
        "name": f"{row.get('species', '')}/{row.get('step_type', '')}",
        "kind": "SPAN_KIND_INTERNAL",
        "startTimeUnixNano": start_ns,
        "endTimeUnixNano": start_ns + duration_ns if start_ns else 0,
        "attributes": [
            {"key": "trial_id", "value": {"intValue": int(row.get("trial_id", 0))}},
            {"key": "species", "value": {"stringValue": row.get("species", "")}},
            {"key": "role", "value": {"stringValue": row.get("role", "")}},
            {"key": "action_type", "value": {"stringValue": row.get("action_type", "")}},
            {"key": "reward", "value": {"doubleValue": float(row.get("reward", 0.0))}},
            {"key": "input_text", "value": {"stringValue": (row.get("input_text") or "")[:2000]}},
            {"key": "output_text", "value": {"stringValue": (row.get("output_text") or "")[:2000]}},
        ],
        "status": {"code": "STATUS_CODE_OK" if float(row.get("reward", 0.0)) > 0 else "STATUS_CODE_UNSET"},
    }


def _journal_trial_to_otlp_spans(trial: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """One journal row → 4 OTLP spans (controller_reasoning, action, eval, safety_gate)."""
    trial_id = int(trial.get("trial_id", 0))
    species = trial.get("species", "")
    action_type = trial.get("action_type", "")
    quality = float(trial.get("quality", 0.0))
    speed = float(trial.get("speed", 0.0))
    pareto_status = trial.get("pareto_status", "")
    passed = pareto_status in ("frontier", "dominated_but_kept")
    trace_id = _stable_id(f"trial-{trial_id}-{trial.get('timestamp', '')}", 32)
    start_ns = _iso_to_unix_nanos(trial.get("timestamp", ""))
    parent_span_id = _stable_id(f"{trace_id}-trial", 16)

    # Walk synthetic timestamps so HALO sees a sequence rather than a pile.
    step_offset_ns = 1_000_000  # 1 ms between synthetic steps
    steps = [
        ("controller_reasoning", json.dumps(trial.get("config_snapshot", {}), default=str)[:2000],
         (trial.get("reasoning_hash") or "")[:2000], 0.0),
        ("action_execution", action_type, f"q={quality:.3f} s={speed:.1f}", quality),
        ("eval", f"tier={trial.get('tier', '')}", f"q={quality:.3f}", quality),
        ("safety_gate", f"q={quality:.3f} s={speed:.1f}",
         "passed" if passed else f"failed: {pareto_status}", quality if passed else 0.0),
    ]
    for idx, (step_type, input_text, output_text, reward) in enumerate(steps):
        span_start = start_ns + idx * step_offset_ns if start_ns else 0
        yield {
            "traceId": trace_id,
            "spanId": _stable_id(f"{trace_id}-{step_type}-{idx}", 16),
            "parentSpanId": parent_span_id,
            "name": f"{species}/{step_type}",
            "kind": "SPAN_KIND_INTERNAL",
            "startTimeUnixNano": span_start,
            "endTimeUnixNano": span_start + step_offset_ns if span_start else 0,
            "attributes": [
                {"key": "trial_id", "value": {"intValue": trial_id}},
                {"key": "species", "value": {"stringValue": species}},
                {"key": "action_type", "value": {"stringValue": action_type}},
                {"key": "reward", "value": {"doubleValue": reward}},
                {"key": "input_text", "value": {"stringValue": input_text}},
                {"key": "output_text", "value": {"stringValue": output_text}},
                {"key": "pareto_status", "value": {"stringValue": pareto_status}},
            ],
            "status": {"code": "STATUS_CODE_OK" if reward > 0 else "STATUS_CODE_UNSET"},
        }


def _iso_to_unix_nanos(iso: str) -> int:
    if not iso:
        return 0
    try:
        return int(datetime.fromisoformat(iso).timestamp() * 1e9)
    except ValueError:
        return 0


def _stable_id(seed: str, hex_chars: int) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:hex_chars]


# ── CLI ─────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="autopilot_telemetry.jsonl OR autopilot_journal.jsonl")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output OTLP JSONL path")
    parser.add_argument(
        "--source",
        choices=["auto", "telemetry", "journal"],
        default="auto",
        help="Force source format (default: auto-detect by inspecting first row).",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    source = args.source
    if source == "auto":
        source = _detect_source(args.input)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if source == "telemetry":
        n = convert_autopilot_telemetry(args.input, args.output)
    else:
        n = convert_journal(args.input, args.output)
    print(f"wrote {n} OTLP spans → {args.output} (source={source})")
    return 0


def _detect_source(path: Path) -> str:
    """Sniff the first non-empty line to choose telemetry vs journal."""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "step_type" in row and "trace_id" in row:
                return "telemetry"
            if "pareto_status" in row or "config_snapshot" in row:
                return "journal"
            return "journal"
    return "journal"


if __name__ == "__main__":
    raise SystemExit(main())
