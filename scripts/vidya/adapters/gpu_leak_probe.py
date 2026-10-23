"""VB-GPU-LEAK-WRITE: GPU-LEAK-1 / 1d own-PID VRAM-slope probes as measurement OBSERVATIONS.

Source: the probe job's ``RESULT.json`` (``/mnt/raid0/llm/tmp/gpu-leak-1-probe-20261023/`` arms G (HIP graphs on,
default) and N (``GGML_CUDA_DISABLE_GRAPHS=1``); ``/mnt/raid0/llm/tmp/gpu-leak-1d-probe/`` arms P (production
``architect_critic`` argv) and PN (P + graphs off)). Each arm records the own-PID KFD VRAM sampled after every
completed request (``series_<arm>`` = ``[requests_done, MiB]``), a least-squares slope over requests 5..n, and (1d)
two segment slopes. The attested artifact is ``RESULT.json`` itself; the arm launch evidence (``run-*/<arm>.argv``,
``<arm>.env_proof.txt``, ``version.txt``, the binary's sha256) is copied into the row, never inferred.

Doctrine, in the order it bites:

* PROJECTION ONLY. The writer copies numbers out of the result file; the reader re-validates and projects into a
  ``ClaimTuple``; ``claim_tuple.grade()`` decides. The producer's verdict word ("graphs implicated", "production not
  exposed") is carried VERBATIM as ``observation.outcome_native`` and ``extra.verdict`` and is never re-derived here.
* RE-DERIVABLE. Every slope is recomputed from the recorded series on read (least squares over the declared request
  window); a row whose value does not follow from its own series is refused. The series is the evidence, the slope
  a summary of it.
* ``protocol_id`` is ALWAYS empty: one run per arm, a non-quiet host, and no ratified protocol -- an OBSERVATION the
  ladder caps on its own. The 1d speed figure is the producer's own "INDICATIVE ONLY" and is NOT projected as a claim.
* ``metric_direction`` is ``lower_better`` (a smaller VRAM growth per request is better); no arm is called good here.
"""

from __future__ import annotations

import dataclasses
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._argv_scope import scope_from_argv  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.gpu_leak_probe_capture.v1"
SIDECAR_NAME = "gpu_leak_probe.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.gpu_leak_probe/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "gpu-leak-probe"
UNIT = "MiB of own-PID VRAM per completed request"
#: metric -> (request window [lo, hi] over `requests done`, where the producer stored the value)
METRICS = {
    "gpu_leak_vram_slope_mib_per_req": ((5, None), "slope_{arm}_mib_per_req"),
    "gpu_leak_vram_slope_fixed_segment_mib_per_req": ((3, 10), "segments_{arm}.fixed_4096_tok_3_to_10"),
    "gpu_leak_vram_slope_varied_segment_mib_per_req": ((10, None), "segments_{arm}.varied_10_to_n"),
}
#: graphs-off arm -> its graphs-default comparison arm.
CONTRAST = {"N": "G", "PN": "P"}
TOLERANCE = 0.006  # the producer rounds slopes to 2 decimals
_ARM = re.compile(r"^slope_([A-Za-z0-9]+)_mib_per_req$")


def fit_slope(series: list, lo: int, hi: int | None) -> tuple[float, int] | None:
    """Least squares of MiB on requests done over ``lo <= x <= hi``; None with fewer than 2 distinct x."""
    pts = [(float(x), float(y)) for x, y in series if x >= lo and (hi is None or x <= hi)]
    if len({x for x, _ in pts}) < 2:
        return None
    mx = sum(x for x, _ in pts) / len(pts)
    my = sum(y for _, y in pts) / len(pts)
    return sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts), len(pts)


def _series_ok(series: Any) -> bool:
    return (isinstance(series, list) and len(series) >= 2 and all(
        isinstance(p, list) and len(p) == 2 and ns.nonneg_int(p[0]) and ns.finite(p[1]) for p in series)
        and [p[0] for p in series] == sorted(p[0] for p in series))


def _load_result(path: Path) -> dict:
    try:
        result = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"GPU-LEAK result unreadable: {exc}") from exc
    if not isinstance(result, dict) or not result.get("verdict") or not result.get("item"):
        raise CaptureError("GPU-LEAK result needs the producer's item and verdict")
    return result


def arms_of(result: Mapping[str, Any]) -> list[str]:
    return sorted(m.group(1) for k in result if (m := _ARM.match(k)))


def _stored(result: Mapping[str, Any], spec: str, arm: str) -> Any:
    head, _, leaf = spec.format(arm=arm).partition(".")
    value = result.get(head)
    return value.get(leaf) if leaf and isinstance(value, dict) else (None if leaf else value)


def _run_evidence(run_dir: Path | None, arm: str) -> dict:
    """argv / env proof / version / binary sha as the probe job left them (absent -> absent, never filled)."""
    if run_dir is None or not (run_dir / f"{arm}.argv").is_file():
        return {}
    argv = (run_dir / f"{arm}.argv").read_text().split("\n")
    argv = [t for t in argv if t != ""]
    env = (run_dir / f"{arm}.env_proof.txt").read_text() if (run_dir / f"{arm}.env_proof.txt").is_file() else ""
    out: dict = {"argv": argv, "graphs_disabled": "GGML_CUDA_DISABLE_GRAPHS=1" in env.split(),
                 "env_proof_sha256": ns.file_sha256(run_dir / f"{arm}.env_proof.txt") if env else None}
    version = run_dir / "version.txt"
    if version.is_file():
        out["server_version"] = version.read_text().splitlines()[0]
    binary = Path(argv[0]) if argv else None
    if binary and binary.is_file():
        out["binary_realpath"] = str(binary.resolve())
        out["binary_sha256"] = ns.file_sha256(binary.resolve())
    return out


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: one run per arm, no ratified protocol, an OBSERVATION")
    if row.get("metric_direction") != "lower_better":
        p.append("metric_direction must be lower_better")
    e = row["extra"]
    if row.get("metric") not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    window, _ = METRICS[row["metric"]]
    if not (isinstance(e.get("arm"), str) and e["arm"]):
        p.append("extra.arm must name the probe arm")
    if not _series_ok(e.get("series")):
        p.append("extra.series must be the recorded [requests_done, MiB] points, ascending")
    elif ns.finite(row.get("value")):
        fitted = fit_slope(e["series"], *window)
        if fitted is None:
            p.append("series has no two distinct request counts in the fit window")
        else:
            if abs(fitted[0] - row["value"]) > TOLERANCE:
                p.append(f"value {row['value']} does not follow from its series (least squares {fitted[0]:.4f})")
            if row.get("reps") != fitted[1]:
                p.append(f"reps must be the {fitted[1]} series points inside the fit window")
    for key in ("verdict", "probe_item"):
        if not ns.text(e.get(key)):
            p.append(f"extra.{key} must carry the producer's own word")
    for key in ("n_done", "n_requested"):
        if not ns.nonneg_int(e.get(key)):
            p.append(f"extra.{key} must be a non-negative integer")
    if not isinstance(e.get("errors"), list):
        p.append("extra.errors must be the probe's own error list (errors are counted, never dropped)")
    if not p:
        p += ns.check_identity(row, {"run_id": row["run_id"], "arm": e["arm"], "metric": row["metric"],
                                     "results": row["results_sha256"]}, "gpuleak")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


def write_belief_measurements(out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
                              run_dir: str | Path | None = None, emitted_at: str | None = None) -> Path:
    """Emit ``gpu_leak_probe.beliefs.jsonl`` from a finished probe ``RESULT.json`` (+ its ``run-*`` evidence dir)."""
    raw = Path(results_path)
    result = _load_result(raw)
    arms = arms_of(result)
    if not arms:
        raise CaptureError("result has no slope_<arm>_mib_per_req field")
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run = Path(run_dir) if run_dir else None
    rows = []
    for arm in arms:
        series = result.get(f"series_{arm}")
        if not _series_ok(series):
            raise CaptureError(f"series_{arm} missing or malformed")
        evidence = _run_evidence(run, arm)
        for metric, (window, spec) in METRICS.items():
            value = _stored(result, spec, arm)
            if value is None:
                continue
            fitted = fit_slope(series, *window)
            row = {
                "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when,
                "date": str(result.get("date") or when), "metric": metric, "value": value, "unit": UNIT,
                "metric_direction": "lower_better", "category": "BASELINE",
                "claim": (f"{result['item']} arm {arm}: {metric} = {value} {UNIT} over {fitted[1] if fitted else 0} "
                          f"series points (own-PID KFD VRAM after each request); producer verdict "
                          f"{result['verdict']!r}; one run per arm, no ratified protocol"),
                "protocol_id": "", "reps": fitted[1] if fitted else 0,
                "reps_basis": "VRAM samples (one per completed request) inside the least-squares window",
                "results_path": str(raw), "results_sha256": digest,
                "extra": {"arm": arm, "probe_item": result["item"], "verdict": result["verdict"],
                          "series": series, "n_done": result.get(f"n_done_{arm}"),
                          "n_requested": result.get(f"n_requested_{arm}", result.get(f"n_done_{arm}")),
                          "errors": result.get(f"errors_{arm}", []), "fit": result.get("fit"),
                          "attribution": result.get(f"attribution_{arm}"),
                          "oom_estimate": result.get("oom_estimate") if arm == "P" else None,
                          "contrast_anchor_arm": CONTRAST.get(arm), **evidence},
            }
            row["measurement_id"] = "gpuleak_" + ns.content_hash({
                "run_id": run_id, "arm": arm, "metric": metric, "results": digest})[:24]
            ns.seal(row)
            bad = row_problems(row)
            if bad:
                raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
            rows.append(row)
    if not rows:
        raise CaptureError("no arm yielded a row")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    natives = ns.native_rows(sidecar_path, row_problems)
    by_key = {(n["row"]["run_id"], n["row"]["extra"]["arm"], n["row"]["metric"]): n["row"] for n in natives}
    return tuple({**n, "anchor": by_key.get((n["row"]["run_id"], n["row"]["extra"]["contrast_anchor_arm"],
                                             n["row"]["metric"])) if n["row"]["extra"].get("contrast_anchor_arm")
                  else None} for n in natives)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("GPU-LEAK native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("GPU-LEAK row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    locator = f"gpuleak:{row['run_id']}:{e['arm']}:{row['metric']}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    obs: dict = {"outcome_native": str(e["verdict"])[:120]}
    anchor = native.get("anchor")
    if isinstance(anchor, dict) and not row_problems(anchor):
        obs["anchor_value"] = anchor["value"]
        if anchor["value"]:
            obs["effect_rel"] = (row["value"] - anchor["value"]) / anchor["value"]
    applicability = scope_from_argv(
        e.get("argv"), binary=e.get("binary_realpath"), binary_sha256=e.get("binary_sha256"),
        family="gpu_vram_residency", varied=["GGML_CUDA_DISABLE_GRAPHS"]) if e.get("argv") else {}
    return dataclasses.replace(tup, observation=obs, applicability=applicability)


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames
