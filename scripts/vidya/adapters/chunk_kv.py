"""VB-KVCHUNK-WRITE: chunk-KV and prefix-hit measurements as a prospective measurement source.

Covers KPF-60 / KPF-64 outputs (per-role prefill rate, inject latency, drift curve, realised vs
ideal prefix-hit share) and the RTE-LOG-1 reader reports. One self-hashed row per measurement, each
recording the SERVED PIN (role, model, kernel_ref) and the WINDOW claim (window id, region-lock
claim, UTC span) it was taken under: a timing number without its window is not a claim.

Row kinds (``extra.kind``): ``prefill_rate`` (tok/s, higher better, value = median of samples),
``inject_latency`` (ms, lower better, median of samples), ``drift_curve`` (value = max drift over
the declared points, lower better; the points ride in the row), ``prefix_hit_share`` (value =
realised_tokens / ideal_tokens, higher better; both counts ride in the row). The strict reader
re-derives every value. No retrospective tuple, no ladder: ``claim_tuple.grade()`` decides.
"""

from __future__ import annotations

import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.chunk_kv_capture.v1"
SIDECAR_NAME = "chunk_kv.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.chunk_kv/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "chunk-kv-prefix-measurement"
PROGRAMS = frozenset({"KPF-60", "KPF-64", "RTE-LOG-1"})
PIN_KEYS = ("role", "model", "kernel_ref")
WINDOW_KEYS = ("window_id", "region_lock_claim", "start_utc", "end_utc")
#: kind -> (metric, unit, direction)
KINDS = {
    "prefill_rate": ("chunk_kv_prefill_rate", "tok_s", "higher_better"),
    "inject_latency": ("chunk_kv_inject_latency", "ms", "lower_better"),
    "drift_curve": ("chunk_kv_drift_max", "drift_units_as_declared", "lower_better"),
    "prefix_hit_share": ("prefix_hit_realised_over_ideal", "fraction_of_ideal", "higher_better"),
}


def _derive(kind: str, m: Mapping[str, Any]) -> tuple[float, int, str] | str:
    """(value, reps, reps_basis) from the per-kind payload, or a problem string."""
    if kind in ("prefill_rate", "inject_latency"):
        s = m.get("samples")
        if not isinstance(s, list) or not s or not all(ns.finite(x) and x >= 0 for x in s):
            return "samples must be a non-empty list of finite non-negative numbers"
        return float(statistics.median(s)), len(s), "scored:samples"
    if kind == "drift_curve":
        pts = m.get("points")
        if not isinstance(pts, list) or len(pts) < 2 or not all(
                isinstance(x, dict) and ns.nonneg_int(x.get("position")) and ns.finite(x.get("drift"))
                for x in pts):
            return "points must be a list of >= 2 {position:int, drift:number}"
        if not ns.text(m.get("drift_unit")):
            return "drift_unit must be declared (what the drift number is)"
        return float(max(x["drift"] for x in pts)), len(pts), "scored:points"
    r, i = m.get("realised_tokens"), m.get("ideal_tokens")
    if not (ns.nonneg_int(r) and ns.nonneg_int(i) and i > 0):
        return "realised_tokens and ideal_tokens must be non-negative integers with ideal > 0"
    return r / i, i, "scored:ideal_tokens"


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    kind = e.get("kind")
    if kind not in KINDS:
        return p + [f"extra.kind must be one of {sorted(KINDS)}"]
    metric, unit, direction = KINDS[kind]
    if (row.get("metric"), row.get("unit"), row.get("metric_direction")) != (metric, unit, direction):
        p.append(f"kind {kind!r} fixes metric/unit/direction to {metric!r}/{unit!r}/{direction!r}")
    if e.get("source_program") not in PROGRAMS:
        p.append(f"extra.source_program must be one of {sorted(PROGRAMS)}")
    pin, win = e.get("served_pin"), e.get("window")
    if not isinstance(pin, dict) or not all(ns.text(pin.get(k)) for k in PIN_KEYS):
        p.append(f"extra.served_pin must name {list(PIN_KEYS)}")
    if not isinstance(win, dict) or not all(ns.text(win.get(k)) for k in WINDOW_KEYS) or not (
            ns.utc_timestamp(win.get("start_utc")) and ns.utc_timestamp(win.get("end_utc"))):
        p.append(f"extra.window must record {list(WINDOW_KEYS)} (UTC span)")
    d = _derive(kind, e)
    if isinstance(d, str):
        p.append("extra." + d)
    else:
        value, reps, basis = d
        if ns.finite(row.get("value")) and abs(row["value"] - value) > 1e-9 * max(1.0, abs(value)):
            p.append("value does not re-derive from the recorded measurement payload")
        if row.get("reps") != reps or row.get("reps_basis") != basis:
            p.append(f"reps/reps_basis must be {reps}/{basis!r} for kind {kind!r}")
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "kind": kind, "prog": e["source_program"],
            "pin": e["served_pin"], "win": e["window"], "subject": e.get("subject"),
            "results": row["results_sha256"]}, "kvchunk")
    return p + ns.self_hash_problems(row) if isinstance(row, dict) else p


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    measurements: list[Mapping[str, Any]], protocol_id: str = CAPTURE_SCHEMA,
    emitted_at: str | None = None,
) -> Path:
    """``measurements``: each ``{kind, source_program, subject, served_pin, window, is_control?,
    <kind payload: samples | points+drift_unit | realised_tokens+ideal_tokens>}``. ``subject`` names
    what was measured (e.g. ``role=frontdoor`` or ``chunk=doc_chunk``). Raises CaptureError."""
    results = Path(results_path)
    if not results.is_file():
        raise CaptureError(f"results artifact missing: {results}")
    if not measurements:
        raise CaptureError("at least one measurement is required")
    digest = ns.file_sha256(results)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for m in measurements:
        kind = m.get("kind")
        if kind not in KINDS:
            raise CaptureError(f"unknown kind {kind!r}")
        d = _derive(kind, m)
        if isinstance(d, str):
            raise CaptureError(f"{kind}: {d}")
        value, reps, basis = d
        metric, unit, direction = KINDS[kind]
        keep = ("samples", "points", "drift_unit", "realised_tokens", "ideal_tokens")
        extra = {"kind": kind, "source_program": m.get("source_program"), "subject": m.get("subject"),
                 "served_pin": dict(m.get("served_pin") or {}), "window": dict(m.get("window") or {}),
                 **{k: m[k] for k in keep if k in m}}
        row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
               "emitted_at": when, "date": when[:10], "metric": metric, "value": value, "unit": unit,
               "metric_direction": direction,
               "category": "BASELINE" if m.get("is_control") else "CANDIDATE",
               "claim": f"{m.get('source_program')} {kind} for {m.get('subject')}: {value:.6g} {unit} "
                        f"under window {extra['window'].get('window_id')}",
               "protocol_id": protocol_id, "reps": reps, "reps_basis": basis,
               "results_path": str(results), "results_sha256": digest, "extra": extra}
        if m.get("source_program") in PROGRAMS:
            row["measurement_id"] = "kvchunk_" + ns.content_hash({
                "run_id": run_id, "kind": kind, "prog": extra["source_program"],
                "pin": extra["served_pin"], "win": extra["window"], "subject": extra["subject"],
                "results": digest})[:24]
        ns.seal(row)
        problems = validate_row(row)
        if problems:
            raise CaptureError(f"{kind}: refusing to emit an invalid row: " + "; ".join(problems))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("chunk-KV native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("chunk-KV row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = f"chunk-kv:{row['run_id']}:{e['kind']}:{e['window']['window_id']}:{row['results_path']}"
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
