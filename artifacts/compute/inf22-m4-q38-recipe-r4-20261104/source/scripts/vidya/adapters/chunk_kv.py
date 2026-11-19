"""VB-KVCHUNK-WRITE: chunk-KV and prefix-hit measurements as a prospective measurement source.

Covers KPF-60 / KPF-62 / KPF-64 outputs (per-role prefill rate, inject latency, G1 shift exactness,
G3 per-position approximation statistics, drift curve, realised vs ideal prefix-hit share) and the
RTE-LOG-1 reader reports. One self-hashed row per measurement, each
recording the SERVED PIN (role, model, kernel_ref) and the WINDOW claim (window id, region-lock
claim, UTC span) it was taken under: a timing number without its window is not a claim.

Row kinds (``extra.kind``): ``prefill_rate`` (tok/s, higher better, value = median of samples),
``inject_latency`` (ms, lower better, median of samples), ``drift_curve`` (value = max drift over
the declared points, lower better; the points ride in the row), ``uncached_prompt_tokens`` (tokens, lower better, median of per-trial samples), ``prefix_hit_share`` (value =
realised_tokens / ideal_tokens, higher better; both counts ride in the row). The strict reader
re-derives every value. No retrospective tuple, no ladder: ``claim_tuple.grade()`` decides.
"""

from __future__ import annotations

import math
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
G1_POSITION_SCHEMA = "epyc.chunk_kv.g1_position.v1"
PROGRAMS = frozenset({"KPF-60", "KPF-62", "KPF-64", "RTE-LOG-1", "RTE-PFX-2"})
PIN_KEYS = ("role", "model", "kernel_ref")
WINDOW_KEYS = ("window_id", "region_lock_claim", "start_utc", "end_utc")
#: kind -> (metric, unit, direction)
KINDS = {
    "prefill_rate": ("chunk_kv_prefill_rate", "tok_s", "higher_better"),
    "inject_latency": ("chunk_kv_inject_latency", "ms", "lower_better"),
    "drift_curve": ("chunk_kv_drift_max", "drift_units_as_declared", "lower_better"),
    "prefix_hit_share": ("prefix_hit_realised_over_ideal", "fraction_of_ideal", "higher_better"),
    # VB-RTEPFX2-WIRE: server-reported uncached prompt tokens per trial (a COUNT; median of samples).
    "uncached_prompt_tokens": ("chunk_kv_uncached_prompt_tokens", "tokens", "lower_better"),
}

# KPF-62 uses the same carrier, but its values are derived from producer-native
# per-position records. The metric selector fixes the claim's unit and direction.
KPF62_METRICS = {
    "shift_exactness": {
        "k_nmse": ("chunk_kv_shift_k_nmse", "nmse", "lower_better"),
        "v_nmse": ("chunk_kv_shift_v_nmse", "nmse", "lower_better"),
        "logits_nmse": ("chunk_kv_shift_logits_nmse", "nmse", "lower_better"),
        "mismatch_fraction": ("chunk_kv_shift_mismatch_fraction", "fraction", "lower_better"),
    },
    "approx_gate": {
        "mean_kl": ("chunk_kv_approx_mean_kl", "nats", "lower_better"),
        "p95_kl": ("chunk_kv_approx_p95_kl", "nats", "lower_better"),
        "top1": ("chunk_kv_approx_top1_agreement", "fraction", "higher_better"),
        "nmse_median": ("chunk_kv_approx_logits_nmse_median", "nmse", "lower_better"),
        "nmse_p95": ("chunk_kv_approx_logits_nmse_p95", "nmse", "lower_better"),
        "naive_ratio": ("chunk_kv_approx_naive_kl_ratio", "ratio", "higher_better"),
    },
}


def _metric_spec(kind: str, m: Mapping[str, Any]) -> tuple[str, str, str] | str:
    if kind in KINDS:
        return KINDS[kind]
    if kind in KPF62_METRICS:
        measure = m.get("measure")
        if measure not in KPF62_METRICS[kind]:
            return f"measure must be one of {sorted(KPF62_METRICS[kind])} for kind {kind!r}"
        return KPF62_METRICS[kind][measure]
    return f"unknown kind {kind!r}"


def _nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(1, math.ceil(percentile / 100.0 * len(ordered))) - 1
    return ordered[index]


def _derive_shift_exactness(m: Mapping[str, Any]) -> tuple[float, int, str] | str:
    """Reduce source-computed sufficient statistics, never reconstructing them from text logs.

    One row is scoped to one G1 delta, tensor component, comparison, and metric. `sq_error` and
    `reference_sq` are sums over all elements for that token position. The denominator fallback
    matches test-chunk-kv's NMSE: when total reference energy is zero, use the squared-error sum.
    """
    rows = m.get("position_rows")
    component = m.get("component")
    comparison = m.get("comparison")
    delta = m.get("delta")
    measure = m.get("measure")
    if component not in {"k", "v", "logits"}:
        return "component must be one of 'k', 'v', or 'logits'"
    if comparison not in {"inject_vs_seq_add", "inject_vs_in_place_ref"}:
        return "comparison must be inject_vs_seq_add or inject_vs_in_place_ref"
    expected_component = {"k_nmse": "k", "v_nmse": "v", "logits_nmse": "logits"}.get(measure)
    if expected_component is not None and component != expected_component:
        return f"measure {measure!r} requires component {expected_component!r}"
    if measure == "mismatch_fraction" and comparison != "inject_vs_seq_add":
        return "mismatch_fraction is defined only for the gated inject_vs_seq_add comparison"
    if not ns.nonneg_int(delta) or delta == 0:
        return "delta must be a positive integer"
    if not isinstance(rows, list) or not rows:
        return "position_rows must be a non-empty list of native per-position sufficient statistics"
    seen: set[int] = set()
    sq_error = reference_sq = 0.0
    element_count = mismatch_count = 0
    for row in rows:
        if (not isinstance(row, dict) or row.get("schema") != G1_POSITION_SCHEMA or row.get("delta") != delta
                or row.get("component") != component or row.get("comparison") != comparison):
            return f"each position row must use {G1_POSITION_SCHEMA!r} and retain delta/component/comparison identity"
        pos = row.get("position")
        if not ns.nonneg_int(pos) or pos in seen:
            return "position_rows must have unique non-negative integer positions"
        seen.add(pos)
        err = row.get("sum_sq_error")
        ref = row.get("reference_sq_norm")
        count = row.get("element_count")
        mismatches = row.get("mismatch_count")
        if not ns.finite(err) or err < 0 or not ns.finite(ref) or ref < 0:
            return "each position requires finite non-negative sum_sq_error and reference_sq_norm"
        if not ns.nonneg_int(count) or count < 1:
            return "each position requires a positive integer element_count"
        if not ns.nonneg_int(mismatches) or mismatches > count:
            return "each position requires mismatch_count in [0, element_count]"
        sq_error += err
        reference_sq += ref
        element_count += count
        mismatch_count += mismatches
    if measure == "mismatch_fraction":
        return mismatch_count / element_count, len(rows), "scored:positions"
    if measure not in {"k_nmse", "v_nmse", "logits_nmse"}:
        return "measure must be k_nmse, v_nmse, logits_nmse, or mismatch_fraction"
    return (sq_error / reference_sq if reference_sq > 0 else sq_error), len(rows), "scored:positions"


def _derive_approx_gate(m: Mapping[str, Any]) -> tuple[float, int, str] | str:
    """Derive a descriptive G3 statistic from the native g3_gate.py JSONL row shape.

    Retention is intentionally absent: the current harness reads it from a separate B7 score
    artifact and does not yet provide a bound, paired native payload to this carrier.
    """
    requests = m.get("request_rows")
    positions = m.get("position_rows")
    selector = m.get("selector_mode")
    naive = m.get("naive_mode")
    measure = m.get("measure")
    if selector not in {"head", "none"} or naive not in {"head", "none"} or selector == naive:
        return "selector_mode and naive_mode must be distinct native modes ('head' and 'none')"
    if not isinstance(requests, list) or not requests:
        return "request_rows must retain the non-empty native requests.jsonl rows"
    if not isinstance(positions, list) or not positions:
        return "position_rows must retain the non-empty native positions.jsonl rows"
    request_modes: set[tuple[str, str]] = set()
    selected_ids: set[str] = set()
    all_inject_ids: set[str] = set()
    for row in requests:
        if not isinstance(row, dict) or not ns.text(row.get("id")) or row.get("mode") not in {selector, naive, "all-inject"}:
            return "request_rows must retain native {id, mode} rows for selector, naive, and all-inject modes"
        key = (row["id"], row["mode"])
        if key in request_modes:
            return "request_rows contain a duplicate {id, mode} pair"
        request_modes.add(key)
        if row["mode"] == selector:
            selected_ids.add(row["id"])
        if row["mode"] == "all-inject":
            if row.get("bit_identical_to_ref") is not True:
                return "all-inject sanity rows must carry bit_identical_to_ref=true"
            all_inject_ids.add(row["id"])
    if not selected_ids:
        return "request_rows have no selector-mode requests"
    if any((rid, naive) not in request_modes for rid in selected_ids):
        return "each selector request requires its native naive-mode request row"
    if not selected_ids.issubset(all_inject_ids):
        return "each selector request requires its all-inject harness-sanity request row"
    seen: set[tuple[str, str, int, int]] = set()
    selected: list[dict] = []
    baseline: list[dict] = []
    selected_keys: dict[str, set[tuple[int, int]]] = {}
    baseline_keys: dict[str, set[tuple[int, int]]] = {}
    for row in positions:
        if (not isinstance(row, dict) or not ns.text(row.get("id")) or row.get("mode") not in {selector, naive, "all-inject"}
                or not ns.nonneg_int(row.get("row")) or not ns.nonneg_int(row.get("pos"))
                or not ns.finite(row.get("kl")) or row["kl"] < 0
                or row.get("top1") not in (0, 1) or not ns.finite(row.get("nmse")) or row["nmse"] < 0):
            return "position_rows must retain native {id, mode, row, pos, kl, top1, nmse} values"
        key = (row["id"], row["mode"], row["row"], row["pos"])
        if key in seen:
            return "position_rows contain a duplicate {id, mode, row, pos} key"
        seen.add(key)
        if row["id"] not in selected_ids or row["mode"] == "all-inject":
            continue
        if row["mode"] == selector:
            selected.append(row)
            selected_keys.setdefault(row["id"], set()).add((row["row"], row["pos"]))
        else:
            baseline.append(row)
            baseline_keys.setdefault(row["id"], set()).add((row["row"], row["pos"]))
    if not selected:
        return "position_rows have no selector positions for the selected request ids"
    if {row["id"] for row in selected} != selected_ids:
        return "every selector request must have at least one native scored position"
    if measure == "naive_ratio" and not baseline:
        return "naive_ratio requires native naive-mode positions for the selector request ids"
    if measure == "naive_ratio":
        if set(baseline_keys) != selected_ids:
            return "naive_ratio requires baseline positions for every selector request id"
        if any(selected_keys.get(rid) != baseline_keys.get(rid) for rid in selected_ids):
            return "naive_ratio requires selector/baseline positions joined by identical {id, row, pos} keys"
    if measure not in KPF62_METRICS["approx_gate"]:
        return "unsupported approx_gate measure"
    kl = [float(row["kl"]) for row in selected]
    nmse = [float(row["nmse"]) for row in selected]
    if measure == "mean_kl":
        value = sum(kl) / len(kl)
    elif measure == "p95_kl":
        value = _nearest_rank(kl, 95.0)
    elif measure == "top1":
        value = sum(row["top1"] for row in selected) / len(selected)
    elif measure == "nmse_median":
        value = _nearest_rank(nmse, 50.0)
    elif measure == "nmse_p95":
        value = _nearest_rank(nmse, 95.0)
    else:
        selector_mean = sum(kl) / len(kl)
        naive_mean = sum(float(row["kl"]) for row in baseline) / len(baseline)
        if selector_mean <= 0:
            return "naive_ratio is undefined when selector mean KL is zero"
        value = naive_mean / selector_mean
    if not math.isfinite(value):
        return "derived G3 value must be finite"
    return value, len(selected), "scored:positions"


def _derive(kind: str, m: Mapping[str, Any]) -> tuple[float, int, str] | str:
    """(value, reps, reps_basis) from the per-kind payload, or a problem string."""
    if kind == "shift_exactness":
        return _derive_shift_exactness(m)
    if kind == "approx_gate":
        return _derive_approx_gate(m)
    if kind in ("prefill_rate", "inject_latency", "uncached_prompt_tokens"):
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
    if kind not in KINDS and kind not in KPF62_METRICS:
        return p + [f"extra.kind must be one of {sorted((*KINDS, *KPF62_METRICS))}"]
    spec = _metric_spec(kind, e)
    if isinstance(spec, str):
        return p + ["extra." + spec]
    metric, unit, direction = spec
    if (row.get("metric"), row.get("unit"), row.get("metric_direction")) != (metric, unit, direction):
        p.append(f"kind {kind!r} fixes metric/unit/direction to {metric!r}/{unit!r}/{direction!r}")
    if e.get("source_program") not in PROGRAMS:
        p.append(f"extra.source_program must be one of {sorted(PROGRAMS)}")
    if kind in KPF62_METRICS and e.get("source_program") != "KPF-62":
        p.append(f"kind {kind!r} requires extra.source_program='KPF-62'")
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
        identity = {
            "run_id": row["run_id"], "kind": kind, "prog": e["source_program"],
            "pin": e["served_pin"], "win": e["window"], "subject": e.get("subject"),
            "results": row["results_sha256"]}
        # Keep existing KPF-60/KPF-64 identities stable. KPF-62 emits multiple rows per kind.
        if kind in KPF62_METRICS:
            identity.update({key: e.get(key) for key in ("measure", "component", "comparison", "delta",
                                                           "selector_mode", "naive_mode")})
        p += ns.check_identity(row, identity, "kvchunk")
    return p + ns.self_hash_problems(row) if isinstance(row, dict) else p


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    measurements: list[Mapping[str, Any]], protocol_id: str = CAPTURE_SCHEMA,
    emitted_at: str | None = None,
) -> Path:
    """Each measurement carries the common pin/window envelope and a kind-specific payload.

    KPF-62 `shift_exactness` retains per-position G1 sufficient statistics; `approx_gate` retains
    native G3 request and position rows. Raises CaptureError on incomplete or unreproducible data.
    """
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
        if kind not in KINDS and kind not in KPF62_METRICS:
            raise CaptureError(f"unknown kind {kind!r}")
        d = _derive(kind, m)
        if isinstance(d, str):
            raise CaptureError(f"{kind}: {d}")
        value, reps, basis = d
        spec = _metric_spec(kind, m)
        if isinstance(spec, str):
            raise CaptureError(f"{kind}: {spec}")
        metric, unit, direction = spec
        keep = ("samples", "points", "drift_unit", "realised_tokens", "ideal_tokens", "detail",
                "measure", "component", "comparison", "delta", "position_rows", "selector_mode",
                "naive_mode", "request_rows")
        extra = {"kind": kind, "source_program": m.get("source_program"), "subject": m.get("subject"),
                 "served_pin": dict(m.get("served_pin") or {}), "window": dict(m.get("window") or {}),
                 **{k: m[k] for k in keep if k in m}}
        claim = (f"{m.get('source_program')} {kind} for {m.get('subject')}: {value:.6g} {unit} "
                 f"under window {extra['window'].get('window_id')}")
        if kind == "shift_exactness":
            claim = (f"{m.get('source_program')} {kind}/{m.get('measure')} for {m.get('subject')}: "
                     f"{value:.6g} {unit} under window {extra['window'].get('window_id')}")
            purpose = ("G1a inject-vs-seq_add exactness" if m.get("comparison") == "inject_vs_seq_add"
                       else "G1 translation-drift diagnostic; informational and not a G1a gate")
            claim = f"{purpose}: {claim}"
        elif kind == "approx_gate":
            claim = (f"{m.get('source_program')} {kind}/{m.get('measure')} for {m.get('subject')}: "
                     f"{value:.6g} {unit} under window {extra['window'].get('window_id')}")
            claim = f"G3 descriptive per-position statistic; g3_gate.py owns corpus gates: {claim}"
        row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
               "emitted_at": when, "date": when[:10], "metric": metric, "value": value, "unit": unit,
               "metric_direction": direction,
               "category": "BASELINE" if m.get("is_control") else "CANDIDATE",
               "claim": claim,
               "protocol_id": protocol_id, "reps": reps, "reps_basis": basis,
               "results_path": str(results), "results_sha256": digest, "extra": extra}
        if m.get("source_program") in PROGRAMS:
            identity = {"run_id": run_id, "kind": kind, "prog": extra["source_program"],
                        "pin": extra["served_pin"], "win": extra["window"], "subject": extra["subject"],
                        "results": digest}
            if kind in KPF62_METRICS:
                identity.update({key: extra.get(key) for key in ("measure", "component", "comparison", "delta",
                                                                  "selector_mode", "naive_mode")})
            row["measurement_id"] = "kvchunk_" + ns.content_hash(identity)[:24]
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
                             sidecar_path=native.get("sidecar_path", ""), no_protocol_ids=("unknown",))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
