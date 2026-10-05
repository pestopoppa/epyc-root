"""VB-REVIEW-F1 write-side hook: producer-authored belief rows for EV-13b review-finding F1.

The EV-13b driver (`review_f1/ev13b_run.py`) calls :func:`write_belief_measurements` right after
`semantic_judge.py score` wrote `_summary.semantic.<judge>.json`, emitting
`_summary.semantic.<judge>.beliefs.jsonl` beside it. One row per (reader model/quant, judge, run set) x
metric in {review_f1_mean, review_precision_mean, review_recall_mean}; per-run values and the
StdDev ride in `extra`. Never per finding.

Refusals (the task's own list): judge == reader; no golden manifest checksum; fewer than 3
non-malfunction runs; missing matcher-spec sha; missing `cross_family_ok`. The judge-swap delta rides
in `extra` when the summary carries it. Pre-hook summaries emit zero rows (never backfilled).
The strict reader is `review_f1.py`; both share :func:`validate_row`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

CAPTURE_SCHEMA = "epyc.vidya.review_f1_capture.v1"
METRICS = {"review_f1_mean": "f1", "review_precision_mean": "precision", "review_recall_mean": "recall"}
UNIT = "fraction"
_SHA = re.compile(r"^[0-9a-f]{64}$")
#: The capture schema and the pinned matcher spec are not a codified measurement protocol
#: (MEASUREMENT.md:13; nothing under measurement/protocols/ covers EV-13b). Every row is an
#: observation until one is, as for OCC-1 (SC85). Rows from the pre-port /workspace copy carry
#: CAPTURE_SCHEMA here; the reader accepts them and projects the same empty citation.
NO_PROTOCOL = ""


class CaptureError(ValueError):
    pass


def content_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def row_digest(row: Mapping[str, Any]) -> str:
    return content_hash({k: v for k, v in row.items() if k != "row_sha256"})


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def measurement_identity(*, run_id: str, reader: str, judge: str, metric: str, summary_sha256: str) -> str:
    return "rf1_" + content_hash({"run_id": run_id, "reader": reader, "judge": judge, "metric": metric,
                                  "summary_sha256": summary_sha256})[:24]


def sidecar_path(summary_path: str | Path) -> Path:
    p = Path(summary_path)
    return p.with_name(p.stem + ".beliefs.jsonl")


def _text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _frac(v: Any) -> bool:
    return not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1


def validate_row(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not an object"]
    p: list[str] = []
    if row.get("schema") != CAPTURE_SCHEMA:
        p.append("schema mismatch")
    for k in ("run_id", "producer", "measurement_id", "metric", "claim", "reps_basis",
              "summary_path", "date", "emitted_at"):
        if not _text(row.get(k)):
            p.append(f"{k} must be a non-empty string")
    if row.get("protocol_id") not in (NO_PROTOCOL, CAPTURE_SCHEMA):
        p.append("protocol_id must be empty (no review-F1 protocol is codified under measurement/protocols/)")
    if row.get("metric") not in METRICS:
        p.append("unknown metric")
    if row.get("unit") != UNIT or row.get("metric_direction") != "higher_better":
        p.append("unit/direction must be fraction/higher_better")
    if row.get("category") != "CANDIDATE":
        p.append("category must be CANDIDATE (an internal-only ranking instrument)")
    if not _frac(row.get("value")):
        p.append("value must be a fraction")
    if not _SHA.match(str(row.get("summary_sha256", ""))):
        p.append("summary_sha256 must be 64-hex")
    x = row.get("extra")
    if not isinstance(x, dict):
        return p + ["extra missing"]
    for k in ("reader_model", "reader_quant", "judge_model", "judge_quant", "matcher"):
        if not _text(x.get(k)):
            p.append(f"extra.{k} required")
    if _text(x.get("reader_model")) and x.get("reader_model") == x.get("judge_model"):
        p.append("judge == reader is refused")
    if not _SHA.match(str(x.get("golden_manifest_checksum", ""))):
        p.append("extra.golden_manifest_checksum required (64-hex)")
    if not _SHA.match(str(x.get("matcher_spec_sha256", ""))):
        p.append("extra.matcher_spec_sha256 required (64-hex)")
    if not isinstance(x.get("cross_family_ok"), bool):
        p.append("extra.cross_family_ok must be recorded")
    runs = x.get("per_run_values")
    n = row.get("reps")
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        p.append("reps (non-malfunction runs) must be >= 3")
    elif not isinstance(runs, list) or len(runs) != n or not all(_frac(v) for v in runs):
        p.append("extra.per_run_values must list one fraction per counted run")
    else:
        mean = sum(runs) / n
        sd = (sum((v - mean) ** 2 for v in runs) / n) ** 0.5
        if not math.isclose(row.get("value", -1), mean, rel_tol=1e-9, abs_tol=1e-12):
            p.append("value must equal the mean of per_run_values")
        if not isinstance(x.get("sd"), (int, float)) or not math.isclose(x["sd"], sd, rel_tol=1e-9, abs_tol=1e-12):
            p.append("extra.sd must equal the population sd of per_run_values")
        if row.get("reps_basis") != f"runs:{n} non-malfunction (reader x judge)":
            p.append("reps_basis mismatch")
    if all(_text(row.get(k)) for k in ("run_id", "metric")) and _text(x.get("reader_model")) \
            and _SHA.match(str(row.get("summary_sha256", ""))):
        reader = f"{x.get('reader_model')}__{x.get('reader_quant')}"
        judge = f"{x.get('judge_model')}__{x.get('judge_quant')}"
        if row.get("measurement_id") != measurement_identity(run_id=row["run_id"], reader=reader, judge=judge,
                                                             metric=row["metric"],
                                                             summary_sha256=row["summary_sha256"]):
            p.append("measurement_id does not re-derive")
    if not _SHA.match(str(row.get("row_sha256", ""))) or row_digest(row) != row.get("row_sha256"):
        p.append("row_sha256 does not bind the row")
    return p


def write_belief_measurements(summary_path: str | Path, *, run_id: str, producer: str,
                              served: Mapping[str, Any] | None = None, emitted_at: str | None = None) -> Path:
    path = Path(summary_path)
    s = json.loads(path.read_text())
    jc = s.get("judge_config") or {}
    valid = [r for r in s.get("per_run", []) if not r.get("malfunction")]
    if jc.get("judge_model") == jc.get("reader_model"):
        raise CaptureError("judge == reader")
    if not _SHA.match(str(s.get("golden_manifest_checksum", ""))):
        raise CaptureError("summary lacks golden_manifest_checksum")
    if len(valid) < 3:
        raise CaptureError(f"only {len(valid)} non-malfunction runs (need >= 3)")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ssha = file_sha256(path)
    reader = f"{jc.get('reader_model')}__{jc.get('reader_quant')}"
    judge = f"{jc.get('judge_model')}__{jc.get('judge_quant')}"
    rows = []
    for metric, key in METRICS.items():
        vals = [float(r[key]) for r in valid]
        n = len(vals)
        mean = sum(vals) / n
        sd = (sum((v - mean) ** 2 for v in vals) / n) ** 0.5
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when,
            "date": when[:10],
            "measurement_id": measurement_identity(run_id=run_id, reader=reader, judge=judge, metric=metric,
                                                   summary_sha256=ssha),
            "metric": metric, "value": mean, "unit": UNIT, "metric_direction": "higher_better",
            "category": "CANDIDATE",
            "claim": (f"EV-13b {run_id}: reader {reader} judged by {judge} -> {metric} = {mean:.4f} "
                      f"(sd {sd:.4f}, {n} runs; internal-only, not leaderboard-comparable)"),
            "protocol_id": NO_PROTOCOL, "reps": n,
            "reps_basis": f"runs:{n} non-malfunction (reader x judge)",
            "summary_path": str(path), "summary_sha256": ssha,
            "extra": {"reader_model": jc.get("reader_model"), "reader_quant": jc.get("reader_quant"),
                      "judge_model": jc.get("judge_model"), "judge_quant": jc.get("judge_quant"),
                      "cross_family_ok": jc.get("cross_family_ok"),
                      "judge_distinct_from_reader": jc.get("judge_distinct_from_reader"),
                      "matcher": s.get("matcher"), "matcher_spec_sha256": s.get("spec_sha256"),
                      "golden_manifest_checksum": s.get("golden_manifest_checksum"),
                      "golden_checksum": s.get("golden_checksum"),
                      "per_run_values": vals, "sd": sd,
                      "runs_excluded_malfunction": len(s.get("per_run", [])) - n,
                      "judge_parse_fail_rate": s.get("judge_parse_fail_rate"),
                      "location_validity_rate": s.get("location_validity_rate"),
                      "judge_swap": s.get("judge_swap"),
                      "served": dict(served or {})},
        }
        row["row_sha256"] = row_digest(row)
        problems = validate_row(row)
        if problems:
            raise CaptureError(f"{metric}: " + "; ".join(problems))
        rows.append(row)
    out = sidecar_path(path)
    tmp = out.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    os.replace(tmp, out)
    return out


__all__ = ["CAPTURE_SCHEMA", "NO_PROTOCOL", "METRICS", "CaptureError", "validate_row", "write_belief_measurements",
           "sidecar_path", "file_sha256", "measurement_identity"]
