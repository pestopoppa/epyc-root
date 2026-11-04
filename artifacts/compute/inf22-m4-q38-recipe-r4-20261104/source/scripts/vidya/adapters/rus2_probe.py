"""VB-RUS2-PROBE-WIRE: RUS-2 trace-length probe cells as measurement OBSERVATIONS.

Source: ``scripts/analysis/rus2_trace_length_probe.py`` (research repo, zero inference) writes ONE
aggregate JSON (``artifacts/rus-2-20261021/rus2_result.json``): per (role, mode, suite) cell the
between-question and within-question AUROC of ``tokens_generated`` for correct vs incorrect samples.
The per-sample eval JSONL it read is not hashed or retained by the probe, so the attested artifact
here is the result JSON itself, never the samples.

Doctrine, in the order it bites:

* PROJECTION ONLY. The writer copies values out of the result file (the caller authors no number),
  the reader re-validates and projects into a ``ClaimTuple``; ``claim_tuple.grade()`` decides.
* ``protocol_id`` is ALWAYS empty. The eval records carry neither ``temperature`` nor
  ``finish_reason`` (the result's own ``temperature_field`` / ``fields_absent`` say so), so the
  sampling protocol is incomplete and no ratified protocol applies: the tuple is an OBSERVATION and
  the ladder downgrades it on its own ("no protocol citation"). The absent fields ride in
  ``extra.absent_protocol_fields`` and are never inferred or back-filled.
* The within-question arm is only emitted where the probe found mixed questions, and its sample
  size (mixed questions, pairs) is carried; most cells have 0 and carry no within row.
* ``metric_direction`` is a carrier label only. AUROC here is P(tokens correct > tokens incorrect);
  < 0.5 means correct samples are SHORTER. Neither direction is "better".
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.rus2_probe_capture.v1"
SIDECAR_NAME = "rus2_probe.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.rus2_probe/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "rus2-trace-length-probe"
UNIT = "AUROC P(tokens_generated correct > incorrect), ties 0.5"
#: metric name -> (cell field holding the value, cell field holding n, n basis)
METRICS = {
    "rus2_between_auroc_tokens": ("between_auroc_tokens", "samples", "scored:samples"),
    "rus2_within_pooled_auroc": ("within_pooled_auroc", "within_pairs",
                                 "scored:correct/incorrect sample pairs"),
}
CELL_FIELDS = ("role", "mode", "suite", "questions", "samples", "correct", "cap_proxy_excluded",
               "cap_value", "between_auroc_tokens", "between_pairs", "between_ci95",
               "within_questions_mixed", "within_pairs", "within_pooled_auroc", "within_ci95",
               "within_share_correct_shorter", "review_ratio_samples", "review_ratio_auroc")
#: protocol-relevant sampling fields the probe's records may lack; checked against the result file.
PROTOCOL_FIELDS = ("temperature", "finish_reason")


def absent_protocol_fields(result: Mapping[str, Any]) -> list[str]:
    """Which of temperature / finish_reason the SOURCE RESULT says its records lack."""
    absent = []
    tf = result.get("temperature_field")
    if isinstance(tf, dict) and tf.get("not_recorded", 0) > 0:
        absent.append("temperature")
    declared = result.get("fields_absent") or []
    if any(str(x).startswith("finish_reason") for x in declared):
        absent.append("finish_reason")
    return sorted(absent)


def _load_result(path: Path) -> dict:
    try:
        result = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"RUS-2 result unreadable: {exc}") from exc
    if not isinstance(result, dict) or not isinstance(result.get("rows"), list):
        raise CaptureError("RUS-2 result must be an object with a 'rows' list")
    for key in ("files_scanned", "drops", "temperature_field", "fields_absent"):
        if key not in result:
            raise CaptureError(f"RUS-2 result lacks producer field {key!r}")
    return result


def _ci_ok(ci: Any) -> bool:
    return ci is None or (isinstance(ci, list) and len(ci) == 2 and all(ns.finite(x) for x in ci))


def cell_problems(cell: Any, where: str = "extra.cell") -> list[str]:
    if not isinstance(cell, dict):
        return [f"{where} must be an object"]
    p = []
    if set(cell) != set(CELL_FIELDS):
        p.append(f"{where} must carry exactly the probe cell fields "
                 f"(missing {sorted(set(CELL_FIELDS) - set(cell))}, "
                 f"unknown {sorted(set(cell) - set(CELL_FIELDS))})")
        return p
    for k in ("role", "mode", "suite"):
        if not ns.text(cell[k]):
            p.append(f"{where}.{k} must be a non-empty string")
    for k in ("questions", "samples", "correct", "cap_proxy_excluded", "between_pairs",
              "within_questions_mixed", "within_pairs", "review_ratio_samples"):
        if not ns.nonneg_int(cell[k]):
            p.append(f"{where}.{k} must be a non-negative integer")
    for k in ("between_auroc_tokens", "within_pooled_auroc", "within_share_correct_shorter",
              "review_ratio_auroc"):
        if cell[k] is not None and not (ns.finite(cell[k]) and 0 <= cell[k] <= 1):
            p.append(f"{where}.{k} must be null or in [0,1]")
    for k in ("between_ci95", "within_ci95"):
        if not _ci_ok(cell[k]):
            p.append(f"{where}.{k} must be null or [lo, hi]")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: temperature/finish_reason are absent from the source "
                 "records, so no protocol applies and the tuple is an OBSERVATION")
    e = row["extra"]
    if row.get("metric") not in METRICS:
        p.append(f"metric must be one of {sorted(METRICS)}")
        return p + ns.self_hash_problems(row)
    value_field, n_field, basis = METRICS[row["metric"]]
    p += cell_problems(e.get("cell"))
    cell = e.get("cell") if isinstance(e.get("cell"), dict) else None
    if cell and not cell_problems(cell):
        if cell[value_field] is None or row.get("value") != cell[value_field]:
            p.append(f"value must equal extra.cell.{value_field} (non-null)")
        if row.get("reps") != cell[n_field] or cell[n_field] == 0:
            p.append(f"reps must equal extra.cell.{n_field} (> 0)")
        if row.get("reps_basis") != basis:
            p.append(f"reps_basis must be {basis!r}")
        if row["metric"] == "rus2_within_pooled_auroc" and cell["within_questions_mixed"] < 1:
            p.append("within-question row needs >= 1 mixed question")
    ab = e.get("absent_protocol_fields")
    if not (isinstance(ab, list) and ab and set(ab) <= set(PROTOCOL_FIELDS)
            and ab == sorted(set(ab))):
        p.append("extra.absent_protocol_fields must list the temperature/finish_reason fields "
                 "the source result declares absent (non-empty, sorted)")
    for key in ("temperature_field", "drops"):
        if not isinstance(e.get(key), dict):
            p.append(f"extra.{key} must be the probe's own object")
    if not ns.nonneg_int(e.get("files_scanned")):
        p.append("extra.files_scanned must be a non-negative integer")
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "role": cell["role"], "mode": cell["mode"],
            "suite": cell["suite"], "metric": row["metric"], "results": row["results_sha256"]},
            "rus2")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    min_questions: int = 20, emitted_at: str | None = None,
) -> Path:
    """Emit ``rus2_probe.beliefs.jsonl`` from a finished ``rus2_result.json``.

    Every number is copied from the result file. A cell yields a between-question row when it has
    ``>= min_questions`` questions and a non-null between AUROC (the probe's own CI threshold), and
    a within-question row when it has >= 1 mixed question and a non-null within AUROC. Raises
    :class:`CaptureError` when the result lacks the producer fields, declares no absent protocol
    field (then a protocol is the caller's to cite; this carrier is the incomplete-protocol one) or
    yields no row.
    """
    raw = Path(results_path)
    result = _load_result(raw)
    absent = absent_protocol_fields(result)
    if not absent:
        raise CaptureError("source result declares neither temperature nor finish_reason absent; "
                           "this carrier is only for the protocol-incomplete RUS-2 records")
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for cell in result["rows"]:
        bad = cell_problems(cell)
        if bad:
            raise CaptureError("result cell malformed: " + "; ".join(bad))
        for metric, (vfield, nfield, basis) in METRICS.items():
            if cell[vfield] is None:
                continue
            if metric == "rus2_between_auroc_tokens" and cell["questions"] < min_questions:
                continue
            row = {
                "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
                "emitted_at": when, "date": when[:10], "metric": metric,
                "value": cell[vfield], "unit": UNIT, "metric_direction": "higher_better",
                "category": "BASELINE",
                "claim": (f"RUS-2 {run_id}: {cell['role']}:{cell['mode']} on {cell['suite']} "
                          f"{metric}={cell[vfield]} (descriptive log analysis; AUROC<0.5 means "
                          f"correct samples are shorter; direction label is carrier-only; "
                          f"temperature/finish_reason not recorded in the source samples)"),
                "protocol_id": "", "reps": cell[nfield], "reps_basis": basis,
                "results_path": str(raw), "results_sha256": digest,
                "extra": {"cell": {k: cell[k] for k in CELL_FIELDS},
                          "absent_protocol_fields": absent,
                          "temperature_field": result["temperature_field"],
                          "drops": result["drops"], "files_scanned": result["files_scanned"],
                          "min_questions": min_questions},
            }
            row["measurement_id"] = "rus2_" + ns.content_hash({
                "run_id": run_id, "role": cell["role"], "mode": cell["mode"],
                "suite": cell["suite"], "metric": metric, "results": digest})[:24]
            ns.seal(row)
            bad = validate_row(row)
            if bad:
                raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
            rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate role x mode x suite x metric cell")
    if not rows:
        raise CaptureError("no cell met the emission thresholds")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("RUS-2 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("RUS-2 row is not a producer-authored capture: " + "; ".join(problems))
    c = row["extra"]["cell"]
    locator = (f"rus2:{row['run_id']}:{c['role']}:{c['mode']}:{c['suite']}:{row['metric']}:"
               f"{row['results_path']}")
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
