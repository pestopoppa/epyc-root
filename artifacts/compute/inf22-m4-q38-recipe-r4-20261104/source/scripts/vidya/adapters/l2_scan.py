"""VB-L2-WRITE read side: project L2 scan / calibration sidecars into measurement ClaimTuples.

Input is only a producer-authored ``<report>.beliefs.jsonl`` written at run time by
``l2_scan_capture.write_belief_measurements``. This adapter PROJECTS each row and leaves every
grading decision to ``claim_tuple.grade()``. A report with no sidecar is pre-hook and emits ZERO
rows; a sidecar with one invalid line is void as a whole; the report is re-hashed on read and a
moved or mutated report grades DOWN instead of disappearing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.l2_scan_capture import (  # noqa: E402
    CAPTURE_SCHEMA, NO_PROTOCOL, SIDECAR_SUFFIX, file_sha256, sidecar_path, validate_row,
)

ADAPTER_ID = "vidya.adapters.l2_scan/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "l2-scan-measurement"


def _present(row: dict) -> bool:
    p = Path(row["report_path"])
    return p.is_file() and file_sha256(p) == row["report_sha256"]


def native_rows(sidecar: str | Path) -> tuple[dict, ...]:
    path = Path(sidecar)
    if not path.is_file():
        return ()
    rows: list[dict] = []
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ()
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return ()
        if validate_row(row):
            return ()
        rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        return ()
    return tuple({"row": r, "sidecar_path": str(path), "attestation_present": _present(r)} for r in rows)


def rows_for_report(report_path: str | Path) -> tuple[dict, ...]:
    return native_rows(sidecar_path(report_path))


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("L2 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("L2 row is not a producer-authored capture: " + "; ".join(problems))
    present = _present(row)
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"], date=row["date"],
        category=row["category"], claim=row["claim"], metric_direction=row["metric_direction"],
        protocol_id=NO_PROTOCOL, reps=row["reps"], reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=row["report_sha256"],
        attestation_locator=f"l2-scan:{row['run_id']}:{row['locator']}:{row['metric']}:{row['report_path']}",
        attestation_present=present, attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "kind": row["kind"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "run_id": row["run_id"], "row_sha256": row["row_sha256"],
               "sidecar_path": native.get("sidecar_path", ""), **{k: row["extra"][k] for k in sorted(row["extra"])}},
    )


def frames_for_sidecar(sidecar: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "CAPTURE_SCHEMA", "SIDECAR_SUFFIX",
           "native_rows", "rows_for_report", "project", "frames_for_sidecar"]
