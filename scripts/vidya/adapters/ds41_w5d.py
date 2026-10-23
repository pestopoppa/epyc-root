"""VB-DS41-W5D-WRITE: DS41-W5d 1017 llama-bench baseline + MUL_MAT_ID pp512 microbench as measurement OBSERVATIONS.

Source: ``out/RESULT.json`` of ``/mnt/raid0/llm/tmp/ds41-1017-baseline-mmid-20261023/analyze.py result`` (task
``DS41-W5d``). ``analyze.py`` is sha-pinned by ``PREDECLARED.md`` and is NOT edited; this separate post-processor
reads its ``RESULT.json`` (hooked, non-fatally, into ``job.sh``'s ``finish`` and runnable by hand).

* (a) 1017-only llama-bench baseline: ``pp512`` / ``tg128`` mean t/s over the six predeclared processes (one model
  load each), emitted only when all six ran; ``values`` ride along and mean / sd / CV re-derive from them.
* (b) MUL_MAT_ID microbench: served-MXFP4 / Q4_K-iqk per-layer expert time ratio (geometric mean over the six
  rounds) at each N, plus the pp512 wall-share ceiling when (a) supplied the denominator. The gm re-derives from the
  recorded per-round ratios.

Doctrine: PROJECTION ONLY; the analyzer's verdict words (BASELINE_VALID, INVALID_NOISY, PREMISE_STANDS, ...) are
carried verbatim as ``outcome_native`` and never re-derived; VOID / INCOMPLETE halves yield NO row (a half with no
valid statistic is recorded by its absence); ``protocol_id`` is always empty (a predeclared analysis plan, one
window, not a codified protocol), so the ladder caps the tuples.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.ds41_w5d_capture.v1"
SIDECAR_NAME = "ds41_w5d.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.ds41_w5d/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ds41-w5d-baseline-mmid"
TASK = "DS41-W5d"
M_BENCH = {"pp512": "ds41_w5d_1017_pp512_ts", "tg128": "ds41_w5d_1017_tg128_ts"}
M_RATIO = "ds41_w5d_mmid_t_ratio_served_over_q4k_iqk"
M_CEIL = "ds41_w5d_s5_ceiling_pct_of_pp512_wall"
METRICS = frozenset(M_BENCH.values()) | {M_RATIO, M_CEIL}
REL = 1e-6


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=REL, abs_tol=1e-9)


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"DS41-W5d RESULT unreadable: {exc}") from exc
    if not isinstance(data, dict) or data.get("task") != TASK or not isinstance(data.get("a_baseline_1017_llama_bench"), dict) \
            or not isinstance(data.get("b_mmid_pp512_premise"), dict):
        raise CaptureError("RESULT must be a DS41-W5d analyzer result with halves (a) and (b)")
    return data


def _num_list(xs: Any, n: int | None = None) -> bool:
    return isinstance(xs, list) and bool(xs) and all(ns.finite(x) for x in xs) and (n is None or len(xs) == n)


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: a predeclared analysis plan, one window, no codified protocol")
    if row.get("metric") not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    if not ns.text(e.get("verdict")):
        p.append("extra.verdict must carry the analyzer's own word")
    if not ns.text(e.get("predeclared_sha256")):
        p.append("extra.predeclared_sha256 must bind the plan the analyzer applied")
    if row["metric"] in M_BENCH.values():
        vals = e.get("values")
        if not _num_list(vals, 6):
            p.append("extra.values must be the six process values")
        elif ns.finite(row.get("value")):
            if not _close(statistics.mean(vals), row["value"]):
                p.append("value must equal the mean of extra.values")
            if ns.finite(e.get("cv_pct")) and not _close(100 * statistics.stdev(vals) / statistics.mean(vals), e["cv_pct"]):
                p.append("extra.cv_pct must re-derive from extra.values")
            if row.get("reps") != 6:
                p.append("reps must be the six llama-bench processes")
    elif row["metric"] == M_RATIO:
        rr = e.get("per_round")
        if not _num_list(rr, 6) or any(x <= 0 for x in rr):
            p.append("extra.per_round must be the six positive per-round ratios")
        elif ns.finite(row.get("value")) and not _close(math.exp(statistics.mean(math.log(x) for x in rr)), row["value"]):
            p.append("value must equal the geometric mean of extra.per_round")
        if not (isinstance(e.get("n_rows"), int) and e["n_rows"] > 0):
            p.append("extra.n_rows must name the microbench N")
        if row.get("reps") != 6:
            p.append("reps must be the six interleaved rounds")
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "metric": row["metric"], "n": e.get("n_rows"),
                                     "results": row["results_sha256"]}, "ds41w5d")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


def _base(run_id, producer, when, raw, digest, data, *, metric, value, unit, direction, claim, reps, reps_basis, extra):
    row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when, "date": when,
           "metric": metric, "value": value, "unit": unit, "metric_direction": direction, "category": "BASELINE",
           "claim": claim, "protocol_id": "", "reps": reps, "reps_basis": reps_basis, "results_path": str(raw),
           "results_sha256": digest,
           "extra": {"predeclared_sha256": data.get("predeclared_sha256") or "", "constants": data.get("constants"),
                     **extra}}
    row["measurement_id"] = "ds41w5d_" + ns.content_hash({"run_id": run_id, "metric": metric, "n": extra.get("n_rows"),
                                                         "results": digest})[:24]
    ns.seal(row)
    bad = row_problems(row)
    if bad:
        raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
    return row


def write_belief_measurements(out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
                              emitted_at: str | None = None) -> Path:
    raw = Path(results_path)
    data = _load(raw)
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    a, b = data["a_baseline_1017_llama_bench"], data["b_mmid_pp512_premise"]
    rows = []
    for name, metric in M_BENCH.items():
        d = (a.get("metrics") or {}).get(name) or {}
        if d.get("n") != 6 or not _num_list(d.get("values"), 6) or not ns.finite(d.get("mean")):
            continue
        rows.append(_base(
            run_id, producer, when, raw, digest, data, metric=metric, value=d["mean"],
            unit="t/s (llama-bench avg_ts, one process = one model load)", direction="higher_better",
            claim=(f"DS41-W5d 1017-only llama-bench {name}: mean {d['mean']:.3f} t/s over 6 processes, "
                   f"CV {d.get('cv_pct', float('nan')):.2f}%; analyzer verdict {a.get('verdict')!r}; absolute baseline, "
                   f"unhardened, no comparison arm"),
            reps=6, reps_basis="llama-bench processes (one model load each)",
            extra={"verdict": a.get("verdict"), "reason": a.get("reason"), "values": d["values"], "sd": d.get("sd"),
                   "cv_pct": d.get("cv_pct"), "ci95": d.get("ci95"), "ci95_halfwidth_pct": d.get("ci95_halfwidth_pct"),
                   "noisy_runs_within_cv": d.get("noisy_runs_within_cv"), "half": "a", "n_rows": None}))
    for n_key, d in sorted((b.get("ratio_served_over_Q4K_iqk") or {}).items(), key=lambda kv: int(kv[0])):
        if not _num_list(d.get("per_round"), 6) or not ns.finite(d.get("gm")):
            continue
        rows.append(_base(
            run_id, producer, when, raw, digest, data, metric=M_RATIO, value=d["gm"],
            unit="ratio of per-layer expert time T, served MXFP4 / Q4_K iqk (geometric mean over rounds)",
            direction="lower_better",
            claim=(f"DS41-W5d MUL_MAT_ID microbench N={n_key}: served({b.get('served_mxfp4_arm')})/Q4_K-iqk T ratio "
                   f"gm {d['gm']:.4f}, CI95 {d.get('ci95')}; analyzer verdict {b.get('verdict')!r}; synthetic weights, "
                   f"bounds the MMID kernel only"),
            reps=6, reps_basis="interleaved rounds (6 harness processes each)",
            extra={"verdict": b.get("verdict"), "reason": b.get("reason"), "half": "b", "n_rows": int(n_key),
                   "per_round": d["per_round"], "ci95": d.get("ci95"), "all_rounds_gt_1": d.get("all_rounds_gt_1"),
                   "premise_verdict_if_valid": b.get("premise_verdict_if_valid"),
                   "served_mxfp4_arm": b.get("served_mxfp4_arm"), "repack_na": b.get("repack_na"),
                   "primary_n": (b.get("constants") or {}).get("primary_n"), "tol_pct": (b.get("constants") or {}).get("tol_pct")}))
    sc = b.get("s5_ceiling") or {}
    if ns.finite(sc.get("s5_ceiling_pct_of_pp512_wall")):
        rows.append(_base(
            run_id, producer, when, raw, digest, data, metric=M_CEIL, value=sc["s5_ceiling_pct_of_pp512_wall"],
            unit="percent of the pp512 wall recoverable if the served path matched Q4_K iqk (model-free upper bound)",
            direction="higher_better",
            claim=(f"DS41-W5d S5 ceiling: {sc['s5_ceiling_pct_of_pp512_wall']:.2f}% of pp512 wall (MMID share "
                   f"{sc.get('mmid_share_pct_of_pp512_wall', float('nan')):.1f}%); a bound, not a measured speedup; the "
                   f"higher_better label is carrier-only"),
            reps=6, reps_basis="interleaved rounds (6 harness processes each)",
            extra={"verdict": b.get("verdict"), "reason": b.get("reason"), "half": "b", "n_rows": 512,
                   "s5_ceiling": sc, "per_round": None}))
    if not rows:
        raise CaptureError(f"no valid statistic in RESULT (a={a.get('verdict')!r}, b={b.get('verdict')!r}): "
                           "a VOID/INCOMPLETE half has no value to project")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, row_problems)


_OUTCOME = {"PREMISE_STANDS": True, "PREMISE_REFUTED": True, "INCONCLUSIVE": False}


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("DS41-W5d native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("DS41-W5d row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = f"ds41w5d:{row['run_id']}:{row['metric']}:n={e.get('n_rows')}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    obs: dict = {"outcome_native": str(e["verdict"])[:120]}
    if row["metric"] in M_BENCH.values() and ns.finite(e.get("cv_pct")):
        obs["noise_floor_rel"] = e["cv_pct"] / 100.0
    if row["metric"] == M_RATIO:
        obs["anchor_value"] = 1.0
        obs["effect_rel"] = row["value"] - 1.0
        obs["n_pairs"] = 6
        if ns.finite(e.get("tol_pct")):
            obs["noise_floor_rel"] = e["tol_pct"] / 100.0
        if e.get("n_rows") == e.get("primary_n") and e.get("premise_verdict_if_valid") in _OUTCOME:
            obs["decisive"] = _OUTCOME[e["premise_verdict_if_valid"]]
    return dataclasses.replace(
        tup, observation=obs,
        applicability={"scope_basis": "native", "backend": "cpu", "knob_family": "mmid_prefill",
                       "knobs": {"model": "DeepSeek-V4.1-Flash-1017-MXFP4", "threads": 48}})


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write the DS41-W5d belief sidecar from analyze.py's RESULT.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--results", required=True)
    w.add_argument("--out-dir", required=True)
    w.add_argument("--run-id", default="ds41-w5d-baseline-mmid-20261023")
    w.add_argument("--producer", default="ds41-1017-baseline-mmid-20261023/analyze.py")
    a = ap.parse_args(argv)
    try:
        path = write_belief_measurements(a.out_dir, run_id=a.run_id, producer=a.producer, results_path=a.results)
    except CaptureError as exc:  # a VOID/INCOMPLETE or unmeasured result has nothing to project: say so, no traceback
        print(f"belief sidecar NOT written: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"sidecar": str(path), "rows": len(native_rows(path))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
