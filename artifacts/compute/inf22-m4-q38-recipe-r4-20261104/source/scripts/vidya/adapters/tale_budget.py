"""VB-PRB-T4 read side: project TALE-EP budget-eval sidecars into measurement ClaimTuples.

The only admissible input is a producer-authored ``<results>.beliefs.jsonl`` written by
``tale_budget_capture.write_belief_measurements`` at write time. This adapter PROJECTS each row
into :class:`ClaimTuple` and leaves every grading decision to ``claim_tuple.grade()``.

Doctrine (DF2-4 precedent, §4.7): a results file with no sidecar is pre-hook and emits ZERO rows;
the per-question ``.jsonl`` is never read to reconstruct a tuple. A sidecar with any invalid line
is void as a whole. Attestation = the per-question results file AND its ``.meta.json``, both
re-hashed on read; a moved or mutated artifact grades DOWN instead of disappearing.

Locator: run x suite x condition (x metric) -- never per question.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.tale_budget_capture import (  # noqa: E402
    CAPTURE_SCHEMA,
    NO_PROTOCOL,
    SIDECAR_SUFFIX,
    file_sha256,
    sidecar_path,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.tale_budget/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "tale-budget-measurement"


def _present(row: dict) -> bool:
    for path_key, sha_key in (("results_path", "results_sha256"), ("meta_path", "meta_sha256")):
        path = Path(row[path_key])
        if not path.is_file() or file_sha256(path) != row[sha_key]:
            return False
    return True


def native_rows(sidecar: str | Path) -> tuple[dict, ...]:
    """Admissible native rows from one sidecar. Missing/empty/invalid -> zero rows."""
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
    return tuple({"row": r, "sidecar_path": str(path), "attestation_present": _present(r)}
                 for r in rows)


def rows_for_results(results_path: str | Path) -> tuple[dict, ...]:
    """All admissible rows for one per-question results file; pre-hook results -> zero rows."""
    return native_rows(sidecar_path(results_path))


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("TALE native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("TALE row is not a producer-authored capture: " + "; ".join(problems))
    present = _present(row)
    extra = row["extra"]
    locator = (f"tale-budget:{row['run_id']}:{extra['suite']}:{extra['condition']}:"
               f"{row['metric']}:{row['results_path']}")
    return ClaimTuple(
        measurement_id=row["measurement_id"],
        metric=row["metric"],
        value=row["value"],
        date=row["date"],
        category=row["category"],
        claim=row["claim"],
        metric_direction=row["metric_direction"],
        # Capture schema != protocol; no TALE protocol is codified (see NO_PROTOCOL).
        protocol_id=NO_PROTOCOL,
        reps=row["reps"],
        reps_basis=row["reps_basis"],
        unit=row["unit"],
        attestation_sha256=row["results_sha256"],
        attestation_locator=locator,
        attestation_present=present,
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "run_id": row["run_id"],
               "row_protocol_id": row["protocol_id"],
               "row_sha256": row["row_sha256"], "meta_sha256": row["meta_sha256"],
               "sidecar_path": native.get("sidecar_path", ""),
               **{key: extra[key] for key in sorted(extra)}},
    )


def frames_for_sidecar(sidecar: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "CAPTURE_SCHEMA", "SIDECAR_SUFFIX",
           "native_rows", "rows_for_results", "project", "frames_for_sidecar"]
