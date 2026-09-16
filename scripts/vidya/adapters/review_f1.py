"""VB-REVIEW-F1 read side: project EV-13b review-F1 sidecars into measurement ClaimTuples.

Only producer-authored `_summary.semantic.<judge>.beliefs.jsonl` rows (``review_f1_capture``) are
admissible. A summary without a sidecar is pre-hook: zero rows. Any invalid line voids the file.
The attested `_summary.semantic.*.json` is re-hashed on read; a moved/mutated summary grades DOWN.
Locator = reader model/quant x judge x run, never per finding. Grading is `claim_tuple.grade()`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.review_f1_capture import (  # noqa: E402
    NO_PROTOCOL,
    file_sha256,
    sidecar_path,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.review_f1/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "review-f1-measurement"


def _present(row: dict) -> bool:
    p = Path(row["summary_path"])
    return p.is_file() and file_sha256(p) == row["summary_sha256"]


def native_rows(sidecar: str | Path) -> tuple[dict, ...]:
    path = Path(sidecar)
    if not path.is_file():
        return ()
    rows = []
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
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
    return tuple({"row": r, "sidecar_path": str(path)} for r in rows)


def rows_for_summary(summary_path: str | Path) -> tuple[dict, ...]:
    return native_rows(sidecar_path(summary_path))


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("review-F1 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("review-F1 row is not a producer-authored capture: " + "; ".join(problems))
    present = _present(row)
    x = row["extra"]
    locator = (f"review-f1:{row['run_id']}:{x['reader_model']}__{x['reader_quant']}:"
               f"{x['judge_model']}__{x['judge_quant']}:{row['metric']}")
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"], date=row["date"],
        category=row["category"], claim=row["claim"], metric_direction=row["metric_direction"],
        protocol_id=NO_PROTOCOL, reps=row["reps"], reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=row["summary_sha256"], attestation_locator=locator,
        attestation_present=present, attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "producer": row["producer"], "run_id": row["run_id"],
               "row_protocol_id": row["protocol_id"],
               "row_sha256": row["row_sha256"], "sidecar_path": native.get("sidecar_path", ""),
               **{k: x[k] for k in sorted(x)}},
    )


def frames_for_sidecar(sidecar: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "rows_for_summary", "project",
           "frames_for_sidecar"]
