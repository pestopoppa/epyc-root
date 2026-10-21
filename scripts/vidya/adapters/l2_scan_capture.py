"""VB-L2-WRITE write-side hook: producer-authored belief rows for the L2 scan and its calibration.

HIL-13 (``scripts/trace/l2_scan.py``) and HIL-14 (``scripts/trace/l2_calibrate.py``) in the
orchestrator repo call :func:`write_belief_measurements` at write time, right after saving their
JSON report, which emits ``<report>.beliefs.jsonl`` next to it. One claim-tuple-shaped row per
reported rate, carrying its denominator in ``reps``. Pre-hook reports stay pre-hook: this is never
run over a finished report to backfill it (the retrofit rule, README "wiring new sources").

No grading rule lives here. The reader (``l2_scan.py``) projects each row and
``claim_tuple.grade()`` decides. Every row is an OBSERVATION (no protocol is codified for the L2
scan), and rows are rates over stated denominators:

* scan:        share with a mechanical signature; per-category rate on failed and on passed traces.
* calibration: per-detector precision and recall with N positives, per external set; construction
               baselines; TraceElephant first-event agreement (exact / within 1 / within 5).

Scope caveat carried on every calibration row (``extra.scope``): Who&When Pro rows test a detector
on INJECTED behaviour, not natural frequency; no natural-recall claim is made without a
human-labelled sample (HIL-12 item 6).
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

CAPTURE_SCHEMA = "epyc.vidya.l2_scan_capture.v1"
SIDECAR_SUFFIX = ".beliefs.jsonl"
KINDS = ("scan", "calibration")
NO_PROTOCOL = ""
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_METRIC = re.compile(r"^l2_(share_mechanical_signature|category_rate_(failed|passed)|"
                     r"cal_(precision|recall)|cal_baseline_(precision|recall)|te_(exact|within1|within5))$")


class CaptureError(ValueError):
    """The report does not carry what a claim tuple needs."""


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def content_hash(v: Any) -> str:
    return hashlib.sha256(_canon(v).encode()).hexdigest()


def row_digest(row: Mapping[str, Any]) -> str:
    return content_hash({k: v for k, v in row.items() if k != "row_sha256"})


def file_sha256(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as h:
        for chunk in iter(lambda: h.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def sidecar_path(report: str | Path) -> Path:
    p = Path(report)
    return p.with_name(p.stem + SIDECAR_SUFFIX)


def measurement_identity(*, run_id: str, kind: str, locator: str, metric: str, report_sha256: str) -> str:
    return "l2scan_" + content_hash({"run_id": run_id, "kind": kind, "locator": locator,
                                     "metric": metric, "report_sha256": report_sha256})[:24]


def _text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _utc(v: Any) -> bool:
    try:
        return _text(v) and datetime.fromisoformat(v.replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def validate_row(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for k in ("run_id", "producer", "measurement_id", "metric", "unit", "claim", "reps_basis",
              "report_path", "date", "locator"):
        if not _text(row.get(k)):
            p.append(f"{k} must be a non-empty string")
    if row.get("kind") not in KINDS:
        p.append(f"kind must be one of {KINDS}")
    if row.get("protocol_id") != NO_PROTOCOL:
        p.append("protocol_id must be empty: no protocol is codified for the L2 scan")
    if row.get("category") != "CANDIDATE":
        p.append("category must be CANDIDATE (an observation of a candidate scan)")
    if row.get("metric_direction") not in ("higher_better", "lower_better"):
        p.append("metric_direction must be higher_better or lower_better")
    if not _METRIC.match(str(row.get("metric", ""))):
        p.append("metric is not a declared L2 metric")
    if not _utc(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if not _SHA256.match(str(row.get("report_sha256", ""))):
        p.append("report_sha256 must be a 64-hex digest")
    v = row.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1:
        p.append("value must be a finite fraction in [0, 1]")
    reps = row.get("reps")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
        p.append("reps must be a positive integer (the denominator)")
    ex = row.get("extra")
    if not isinstance(ex, dict) or not _text(ex.get("denominator_label")) or not _text(ex.get("code_ref")):
        p.append("extra must carry denominator_label and code_ref (the producer revision)")
    elif row.get("kind") == "calibration" and not _text(ex.get("scope")):
        p.append("calibration rows must carry extra.scope (injected vs natural)")
    if not _SHA256.match(str(row.get("row_sha256", ""))):
        p.append("row_sha256 must be a 64-hex self-hash")
    else:
        try:
            if row_digest(row) != row["row_sha256"]:
                p.append("row_sha256 does not bind the row content")
        except (ValueError, TypeError) as exc:
            p.append(f"row is not canonically hashable: {exc}")
    if all(_text(row.get(k)) for k in ("run_id", "kind", "locator", "metric")) and _SHA256.match(str(row.get("report_sha256", ""))):
        if row.get("measurement_id") != measurement_identity(
                run_id=row["run_id"], kind=row["kind"], locator=row["locator"], metric=row["metric"],
                report_sha256=row["report_sha256"]):
            p.append("measurement_id does not re-derive from (run_id, kind, locator, metric, report_sha256)")
    return p


def _scan_cells(rep: dict) -> list[tuple[str, str, float, int, str, str, str]]:
    """(locator, metric, value, reps, denominator_label, direction, unit)."""
    out = []
    cov = rep["coverage"]
    if cov["share_mechanical_signature"] is not None:
        out.append(("scan:failed", "l2_share_mechanical_signature", cov["share_mechanical_signature"],
                    cov["denominator_failed"], "failed traces", "higher_better", "fraction"))
    for cat, row in sorted(rep["category_rates"].items()):
        for grp in ("failed", "passed"):
            r = row[grp]
            if r["rate"] is not None and r["n"] > 0:
                out.append((f"scan:{cat}", f"l2_category_rate_{grp}", r["rate"], r["n"],
                            f"{grp} traces with observed steps" if cat == "zero_step_violation" else f"{grp} traces",
                            "lower_better", "fraction"))
    return out


def _cal_cells(rep: dict) -> list[tuple[str, str, float, int, str, str, str]]:
    out = []
    w = rep.get("whowhen_pro_text")
    if w:
        for tgt, t in sorted(w["targets"].items()):
            s = t["detector_score"]
            if s.get("scored"):
                for m in ("precision", "recall"):
                    if s[m] is not None:
                        out.append((f"whowhen_pro_text:{tgt}", f"l2_cal_{m}", s[m], s["n_positive"] if m == "recall" else s["tp"] + s["fp"],
                                    "positives" if m == "recall" else "detector firings", "higher_better", "fraction"))
            b = t.get("construction_only_baseline") or {}
            for m in ("precision", "recall"):
                if b.get(m) is not None:
                    out.append((f"whowhen_pro_text:{tgt}", f"l2_cal_baseline_{m}", b[m], s["n_positive"] if m == "recall" else b["tp"] + b["fp"],
                                "positives" if m == "recall" else "baseline firings", "higher_better", "fraction"))
    te = rep.get("traceelephant")
    if te:
        a = te["agreement"].get("ALL|detector_fvd")
        if a and a["n"]:
            for key, m in (("exact", "l2_te_exact"), ("within1", "l2_te_within1"), ("within5", "l2_te_within5")):
                out.append(("traceelephant:ALL", m, a[key] / a["n"], a["n"], "failed traces with a human decisive step", "higher_better", "fraction"))
    return out


def write_belief_measurements(report_path: str | Path, *, kind: str, run_id: str, producer: str,
                              code_ref: str, emitted_at: str | None = None) -> Path:
    """Emit ``<report>.beliefs.jsonl``. Any invalid row raises :class:`CaptureError`; nothing is written."""
    if kind not in KINDS:
        raise CaptureError(f"kind must be one of {KINDS}")
    path = Path(report_path)
    rep = json.loads(path.read_text())
    cells = _scan_cells(rep) if kind == "scan" else _cal_cells(rep)
    if not cells:
        raise CaptureError(f"no reportable cells in {path}")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sha = file_sha256(path)
    rows = []
    for locator, metric, value, reps, denom, direction, unit in cells:
        row: dict[str, Any] = {
            "schema": CAPTURE_SCHEMA, "kind": kind, "run_id": run_id, "producer": producer,
            "emitted_at": when, "date": when[:10], "locator": locator, "metric": metric,
            "measurement_id": measurement_identity(run_id=run_id, kind=kind, locator=locator, metric=metric, report_sha256=sha),
            "value": value, "unit": unit, "metric_direction": direction, "category": "CANDIDATE",
            "claim": f"L2 {kind} {run_id}: {locator} {metric} = {value:.4f} (n={reps} {denom})",
            "protocol_id": NO_PROTOCOL, "reps": reps, "reps_basis": f"denominator:{denom}",
            "report_path": str(path), "report_sha256": sha,
            "extra": {"denominator_label": denom, "code_ref": code_ref,
                      **({"scope": "injected behaviour (Who&When Pro) or external gold; not natural frequency"} if kind == "calibration" else {}),
                      "header": rep.get("header", "")[:300]},
        }
        row["row_sha256"] = row_digest(row)
        problems = validate_row(row)
        if problems:
            raise CaptureError(f"{locator}/{metric}: refusing an invalid row: " + "; ".join(problems))
        rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate measurement ids")
    out = sidecar_path(path)
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, out)
    return out


__all__ = ["CAPTURE_SCHEMA", "SIDECAR_SUFFIX", "KINDS", "CaptureError", "validate_row", "row_digest",
           "file_sha256", "sidecar_path", "write_belief_measurements"]
