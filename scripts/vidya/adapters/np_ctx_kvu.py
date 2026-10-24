"""np x ctx x KV-mode study capture rows as scoped OBSERVATION beliefs (VB-KVU-1 adapter, first used by VB-KVU-CPU).

Native records, all of schema ``epyc.vidya.np_ctx_kvu_capture.v1`` and self-hashed (``row_sha256``) by the research
driver ``kvu_cpu_matrix.py`` (``kvu_ckpt_arms.py`` reuses its emitter):

* CELL shape: a launch-group directory holding ``summary.jsonl`` (one cell row per cell, ``wave`` null, with the cell's
  medians) beside ``<launch>/<cell>/waves_capture.jsonl`` (one row per wave with the per-stream lists). Example:
  ``artifacts/np_context_kvu_cpu_study_20261020/w2_20261021/s1b_unified_np4_L64k_depth/``.
* REQUEST shape: ``requests.jsonl`` (one row per HTTP request; ``pmode`` ``ckpt_arms``), e.g. KVU-12.1
  ``/mnt/raid0/llm/tmp/kvu121-arms/out/requests.jsonl``. The sibling ``cells.jsonl`` (``epyc.kvu121.ckpt_arms.v1``) holds
  the decision rows, is NOT read here, and only carries ``row_sha256`` from the 2026-10-24 driver change onward.

PROJECTION ONLY. ``claim_tuple.grade()`` decides; this module holds no ladder. STRICT reader: every row's
``row_sha256`` is re-derived, the shared validator rules are re-applied, and each cell median is RE-DERIVED from the wave
rows and compared with the producer's stated value; a difference is a ``ProjectionError`` (refused, never repaired).

Failed requests stay in the denominator: ``request_ok_fraction`` counts every attempted request (HTTP 400 included) and
a failed request row projects ``request_ok`` = 0 with no timing value. Cell medians are projected even for a cell whose
result is ``ERRORS``, with ``outcome_native`` saying so and ``request_ok_fraction`` < 1 beside them.

Cautions that ride every tuple (README source row): (1) the KV mode is an argv fact read back from the launch log
(``kv_unified_from_log``), never a default; (2) unified vs split changes outputs at the same seed, so an aggregate t/s
across arms confounds answer length; (3) record ``c``, ``-np`` and ``n_ctx_slot`` (``c = L * np`` silently truncates
under split); (4) shared-prefix waves >= 2 hit per-slot caches, so wave 1 and waves >= 2 are distinct; (5) depth-mode
decode waves re-send each stream's own document, so they measure decode at depth, not independent prefill.

``decode_tps_overlap_med`` is NOT projected: the wave rows carry no per-wave overlap value, so it cannot be re-derived.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters._argv_scope import BUILD_SHA, QUANT  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

SCHEMA = "epyc.vidya.np_ctx_kvu_capture.v1"
ADAPTER_ID = "vidya.adapters.np_ctx_kvu/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "np-ctx-kvu-measurement"
KNOB_FAMILY = "slot_serving"
SUMMARY, WAVES, REQUESTS = "summary.jsonl", "waves_capture.jsonl", "requests.jsonl"
_MAX_BYTES = 64 << 20
_TOL = 0.0051   # the producer rounds medians to 2 decimals

#: key -> (metric, unit, direction)
CELL_METRICS = {
    "prefill_tps_med": ("prefill_tps_median", "tok/s", "higher_better"),
    "ttft_s_med": ("ttft_s_median", "s", "lower_better"),
    "decode_tps_sum_med": ("decode_tps_sum_median", "tok/s", "higher_better"),
    "decode_tps_stream_med": ("decode_tps_per_stream_median", "tok/s", "higher_better"),
    "agg_e2e_med": ("e2e_tps_median", "tok/s", "higher_better"),
}
REQ_FRACTION = ("request_ok_fraction", "fraction", "higher_better")
REQ_OK = ("request_ok", "boolean", "higher_better")
REQ_TTFT = ("ttft_s", "s", "lower_better")
REQ_PROMPT_N = ("prompt_n_tokens", "tokens", "lower_better")
METRICS = {**{k: v[0] for k, v in CELL_METRICS.items()}, "request_ok_fraction": REQ_FRACTION[0],
           "request_ok": REQ_OK[0], "ttft_s": REQ_TTFT[0], "prompt_n_tokens": REQ_PROMPT_N[0]}

_REQUIRED = ("binary_sha256", "binary_realpath", "n_ctx_slot", "c", "np", "prompt_mode", "ts", "cpu_list", "loadavg_start")


# --- reading ----------------------------------------------------------------------------------------------------
def row_hash(row: dict) -> str:
    """The producer's convention (``kvu_cpu_matrix.row_hash``): sha256 over the row minus ``row_sha256``."""
    body = {k: v for k, v in row.items() if k != "row_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _legacy_hash_ok(row: dict) -> bool:
    """KVU-12.1 request rows written before research ``0bda5f323`` hashed the row BEFORE ``validation_problems`` was added.
    Accepted only for an empty ``validation_problems`` (which this reader re-derives itself), over the row without it."""
    if row.get("validation_problems") != []:
        return False
    return row.get("row_sha256") == row_hash({k: v for k, v in row.items() if k != "validation_problems"})


def validate_row(row: dict) -> list[str]:
    """The producer's ``validate_row`` rules, re-applied by the reader. [] = valid."""
    bad = []
    if row.get("schema") != SCHEMA:
        bad.append("schema")
    if row.get("row_sha256") != row_hash(row) and not _legacy_hash_ok(row):
        bad.append("row_sha256 mismatch")
    if row.get("kv_unified_from_log") not in ("true", "false"):
        bad.append("kv_unified not read back from launch log")
    for k in _REQUIRED:
        if row.get(k) in (None, ""):
            bad.append(f"missing {k}")
    return bad


def _read_rows(path: Path) -> tuple[list[dict], str]:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= _MAX_BYTES:
        raise ProjectionError(f"{path.name} is not a bounded regular file")
    raw = path.read_bytes()
    rows = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"{path.name} has a torn line: {exc}") from exc
        if not isinstance(row, dict):
            raise ProjectionError(f"{path.name} has a non-object row")
        rows.append(row)
    return rows, hashlib.sha256(raw).hexdigest()


def _strict(row: dict, where: str) -> None:
    if row.get("schema") != SCHEMA:
        raise ProjectionError(f"{where}: pre-hook row (schema {row.get('schema')!r}), not projected")
    bad = validate_row(row)
    if bad:
        raise ProjectionError(f"{where}: row fails the producer's own validator: {bad}")
    if row.get("validation_problems"):
        raise ProjectionError(f"{where}: row records validation_problems {row['validation_problems']}")


def _med(values: list[float]) -> float | None:
    return round(statistics.median(values), 2) if values else None


def _same(stated: Any, derived: float | None, what: str) -> None:
    if stated is None and derived is None:
        return
    if type(stated) not in (int, float) or derived is None or abs(stated - derived) > _TOL:
        raise ProjectionError(f"{what} does not re-derive from the wave rows: stated {stated!r}, re-derived {derived!r}")


def _nums(values: list) -> list[float]:
    return [float(v) for v in values if type(v) in (int, float) and math.isfinite(v)]


# --- native rows --------------------------------------------------------------------------------------------------
def _common(row: dict, path: Path, file_sha: str, shape: str) -> dict:
    return {"shape": shape, "rows_path": str(path), "rows_sha256": file_sha, "row": row}


def _cell(unit: Path) -> list[dict]:
    cells, sha = _read_rows(unit / SUMMARY)
    out: list[dict] = []
    for c in cells:
        _strict(c, f"{SUMMARY} cell {c.get('launch')}/{c.get('cell')}")
        if c.get("wave") is not None:
            raise ProjectionError(f"{SUMMARY} holds a per-wave row; cell rows have wave null")
        wf = unit / str(c["launch"]) / str(c["cell"]) / WAVES
        if not wf.is_file():
            raise ProjectionError(f"cell {c['launch']}/{c['cell']} has no {WAVES} to re-derive its medians from")
        waves, wsha = _read_rows(wf)
        for w in waves:
            _strict(w, f"{WAVES} {c['launch']}/{c['cell']} wave {w.get('wave')}")
            for k in ("arm", "cell", "np", "clients", "kv_unified_from_log", "binary_sha256", "n_ctx_slot", "c"):
                if w.get(k) != c.get(k):
                    raise ProjectionError(f"wave {w.get('wave')} disagrees with its cell row on {k}")
        if sorted(w.get("wave") for w in waves) != list(range(len(waves))) or not waves:
            raise ProjectionError(f"cell {c['launch']}/{c['cell']}: wave rows are not 0..n-1")
        depth = c.get("prompt_mode") == "depth"
        pre = waves[:1] if depth else waves
        dec = waves[1:] if depth else waves
        derived = {
            "prefill_tps_med": (_med(_nums([v for w in pre for v in w["prefill_tps"]])), len(_nums([v for w in pre for v in w["prefill_tps"]]))),
            "ttft_s_med": (_med(_nums([v for w in pre for v in w["ttft_s"]])), len(_nums([v for w in pre for v in w["ttft_s"]]))),
            "decode_tps_sum_med": (_med(_nums([w["decode_tps_sum"] for w in dec])), len(dec)),
            "decode_tps_stream_med": (_med(_nums([v for w in dec for v in w["decode_tps_per_stream"]])),
                                      len(_nums([v for w in dec for v in w["decode_tps_per_stream"]]))),
            "agg_e2e_med": (_med(_nums([w["agg_e2e_tok_s"] for w in dec])), len(dec)),
        }
        for key, (val, _n) in derived.items():
            _same(c.get(key), val, f"{c['launch']}/{c['cell']} {key}")
        n_req = sum(len(w["ttft_s"]) for w in waves)
        n_ok = sum(1 for w in waves for v in w["ttft_s"] if v is not None)
        n_ok_pn = sum(1 for w in waves for v in w["prompt_n"] if v is not None)
        if n_ok != n_ok_pn:
            raise ProjectionError(f"cell {c['launch']}/{c['cell']}: ttft_s and prompt_n disagree on which requests succeeded")
        if n_req != c["clients"] * len(waves):
            raise ProjectionError(f"cell {c['launch']}/{c['cell']}: {n_req} request slots, expected clients x waves")
        base = _common(c, unit / SUMMARY, sha, "cell")
        base.update(waves_path=str(wf), waves_sha256=wsha, n_waves=len(waves), n_requests=n_req, n_ok=n_ok,
                    derived={k: v for k, v in derived.items()})
        out.append(base)
    return out


def _request(path: Path) -> list[dict]:
    rows, sha = _read_rows(path)
    out, seen = [], set()
    for r in rows:
        _strict(r, f"{REQUESTS} {r.get('cell_key')}/{r.get('probe')}")
        key = (r.get("cell_key"), r.get("probe"))
        if key in seen:
            raise ProjectionError(f"{REQUESTS}: duplicate request row {key}")
        seen.add(key)
        if r.get("status") not in (200, None) and type(r.get("status")) is not int:
            raise ProjectionError(f"{REQUESTS}: non-integer status on {key}")
        out.append(_common(r, path, sha, "request"))
    return out


def _natives(unit: str | Path) -> list[dict]:
    """One native record per cell or request row; ``[]`` for a path that is neither shape."""
    p = Path(unit)
    if p.is_file():
        return _request(p) if p.name == REQUESTS else []
    if (p / SUMMARY).is_file():
        return _cell(p)
    if (p / REQUESTS).is_file():
        return _request(p / REQUESTS)
    return []


# --- projection ---------------------------------------------------------------------------------------------------
def _scope(row: dict) -> dict:
    scope: dict = {"scope_basis": "native"}
    model = row.get("model")
    if isinstance(model, str) and model.strip():
        scope["model_file"] = model
        q = QUANT.search(model)
        if q:
            scope["quant"] = q.group(1)
    binary = str(row.get("binary_realpath") or "")
    if "/cpu-" in binary or "build-cpu" in binary:
        scope["backend"] = "cpu"
    if type(row.get("np")) is int and row["np"] > 0:
        scope["np"] = row["np"]
    if type(row.get("n_ctx_slot")) is int and row["n_ctx_slot"] > 0:
        scope["context_tokens"] = row["n_ctx_slot"]
    if binary and row.get("binary_sha256"):
        scope["kernel"] = {"build_path": binary, "execution_digest": row["binary_sha256"]}
        b = BUILD_SHA.search(binary)
        if b:
            scope["build_sha"] = b.group(1)
    scope["knob_family"] = KNOB_FAMILY
    knobs: dict = {"kv_unified": row["kv_unified_from_log"] == "true", "c": int(row["c"]),
                   "threads": int(row["threads"]) if type(row.get("threads")) is int else 0,
                   "cache_idle_slots": str(row.get("cache_idle_slots_argv") or "unstated"),
                   "prompt_mode": str(row["prompt_mode"]), "cpu_list": str(row["cpu_list"])}
    if not knobs["threads"]:
        knobs.pop("threads")
    if type(row.get("pool")) is int:
        knobs["pool"] = row["pool"]
    if type(row.get("L")) is int:
        knobs["L"] = row["L"]
    if type(row.get("mtp")) is bool:
        knobs["mtp"] = row["mtp"]
    if type(row.get("draft_depth")) is int:
        knobs["draft_depth"] = row["draft_depth"]
    scope["knobs"] = knobs
    scope["varied"] = ["kv_unified"] if row.get("prompt_mode") != "ckpt_arms" else ["checkpoint_policy_arm"]
    scope["run_id"] = f"np-ctx-kvu:{row.get('arm')}:{row.get('cell') or row.get('cell_key')}:{row.get('ts')}"
    off_store = bool(binary) and not binary.startswith(str(row.get("kernel_store_path") or "\0"))
    scope["recipe"] = (
        f"np x ctx x KV-mode capture | mode {row.get('prompt_mode')} | KV mode from the launch log, not a default | "
        "c, -np, n_ctx_slot recorded | unified vs split changes outputs, so compare per-request decode not aggregate | "
        "depth waves re-send each stream's own document (decode at depth, not independent prefill) | "
        "waves >= 2 of shared-prefix hit per-slot caches" + (" | binary is NOT the kernel-store build" if off_store else "")
    )[:600]
    return scope


def _claim(native: dict, metric: str, unit: str, value: Any) -> str:
    r = native["row"]
    what = f"{r.get('arm')} {r.get('cell') or r.get('cell_key')}"
    kv = "--kv-unified" if r["kv_unified_from_log"] == "true" else "--no-kv-unified"
    v = f"{value:.6g}" if type(value) is float else str(value)
    text = (f"np-ctx-kvu {what} (np {r.get('np')}, c {r.get('c')}, n_ctx_slot {r.get('n_ctx_slot')}, {kv}, "
            f"mode {r.get('prompt_mode')}): {metric} = {v} {unit}")
    if native["shape"] == "cell":
        text += f"; result {r.get('result')}; {native['n_ok']} of {native['n_requests']} requests ok"
    else:
        text += f"; probe {r.get('probe')} wave {r.get('wave')} status {r.get('status')}"
    return text


def _tuple(native: dict, metric: str, unit: str, direction: str, value: Any, reps: int, basis: str, locator: str,
           mid_key: str) -> ClaimTuple:
    row = native["row"]
    digest = native["rows_sha256"]
    try:
        reread = hashlib.sha256(Path(native["rows_path"]).read_bytes()).hexdigest()
    except OSError as exc:
        raise ProjectionError(f"{native['rows_path']} cannot be re-read for attestation: {exc}") from exc
    if reread != digest:
        raise ProjectionError(f"{Path(native['rows_path']).name} changed between read and projection")
    obs: dict = {}
    if native["shape"] == "cell":
        obs["outcome_native"] = f"{row.get('result')}: {native['n_ok']} of {native['n_requests']} requests ok"[:120]
    else:
        obs["outcome_native"] = f"HTTP {row.get('status')}"
    extra = {k: row.get(k) for k in (
        "arm", "launch", "cell", "cell_key", "probe", "wave", "result", "status", "prompt_mode", "L", "np", "c", "pool",
        "n_ctx_slot", "kv_unified_from_log", "kv_unified_argv_flag", "cache_idle_slots_argv", "extra_argv", "mtp",
        "draft_depth", "threads", "cpu_list", "loadavg_start", "binary_sha256", "binary_realpath", "kernel_store_path",
        "row_sha256", "stderr_hits", "n_reprefill_by_wave", "error", "ts") if row.get(k) is not None}
    extra["rows_sha256"] = digest
    if native["shape"] == "cell":
        extra.update(waves_sha256=native["waves_sha256"], n_waves=native["n_waves"], n_requests=native["n_requests"],
                     n_ok=native["n_ok"], overlap_not_projected="decode_tps_overlap_med cannot be re-derived from the wave rows")
    binary = str(row.get("binary_realpath") or "")
    if binary and not binary.startswith(str(row.get("kernel_store_path") or "\0")):
        extra["binary_not_kernel_store"] = True
    return ClaimTuple(
        measurement_id=f"npctxkvu:v1:{row['row_sha256'][:24]}:{mid_key}",
        metric=metric, value=value, unit=unit, date=str(row.get("ts") or "")[:10], category="BASELINE",
        claim=_claim(native, metric, unit, value), metric_direction=direction, protocol_id="",
        reps=reps if reps >= 1 else None, reps_basis=basis,
        attestation_locator=locator, attestation_sha256=digest, attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, extra=extra, applicability=_scope(row), observation=obs)


def project_all(native: dict) -> list[ClaimTuple]:
    """Every tuple one native record yields (a cell yields up to six, a request one to three)."""
    row, name = native["row"], Path(native["rows_path"]).name
    out: list[ClaimTuple] = []
    if native["shape"] == "cell":
        tag = f"{row['launch']}/{row['cell']}"
        for key, (metric, unit, direction) in CELL_METRICS.items():
            value, n = native["derived"][key]
            if value is None:
                continue
            basis = ("per-stream values pooled over the contributing waves" if key in ("prefill_tps_med", "ttft_s_med", "decode_tps_stream_med")
                     else "contributing waves, each one launch of the cell (decode waves re-send the same documents)")
            out.append(_tuple(native, metric, unit, direction, value, n, basis, f"npctxkvu:{name}#{tag}:{metric}", metric))
        frac = native["n_ok"] / native["n_requests"]
        out.append(_tuple(native, REQ_FRACTION[0], REQ_FRACTION[1], REQ_FRACTION[2], frac, native["n_requests"],
                          "ATTEMPTED requests across all waves; HTTP errors stay in the denominator",
                          f"npctxkvu:{name}#{tag}:{REQ_FRACTION[0]}", REQ_FRACTION[0]))
        return out
    tag = f"{row['cell_key']}#{row.get('probe')}"
    ok = row.get("status") == 200
    out.append(_tuple(native, REQ_OK[0], REQ_OK[1], REQ_OK[2], 1 if ok else 0, 1, "attempted requests (n = 1 per row)",
                      f"npctxkvu:{name}#{tag}:{REQ_OK[0]}", REQ_OK[0]))
    if ok:
        for field, spec in (("ttft_s", REQ_TTFT), ("prompt_n", REQ_PROMPT_N)):
            if type(row.get(field)) in (int, float) and math.isfinite(row[field]):
                out.append(_tuple(native, spec[0], spec[1], spec[2], row[field], 1, "one request",
                                  f"npctxkvu:{name}#{tag}:{spec[0]}", spec[0]))
    return out


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    """Single-tuple entry point for the registry: the native record names its ``metric_key``."""
    key = native.get("metric_key")
    if key not in METRICS.values():
        raise ProjectionError("np-ctx-kvu native record must name a known metric_key")
    for t in project_all(native):
        if t.metric == key:
            return t
    raise ProjectionError(f"np-ctx-kvu native record has no {key} value")


def native_rows(unit: str | Path) -> list[dict]:
    """One native per projectable metric of every cell / request row (what the ingest hands to ``project``)."""
    return [{**n, "metric_key": t.metric} for n in _natives(unit) for t in project_all(n)]


__all__ = ["ADAPTER_ID", "AUTHORITY", "KNOB_FAMILY", "METRICS", "SOURCE_KIND", "native_rows", "project", "project_all"]
