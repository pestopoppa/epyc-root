"""SC85 read side: project OCC-1 optical-compression sidecars into measurement ClaimTuples.

This adapter is strict by construction. It admits exactly one kind of input: a producer-authored
``belief_measurements.jsonl`` sidecar that ``occ1_optical_compression_capture.write_belief_measurements``
wrote at report time, next to the run's ``summary.json``. The adapter PROJECTS each row into the
canonical :class:`ClaimTuple` and leaves every grading decision to ``claim_tuple.grade()``.

Doctrine (§4.7: "absence is recorded, never filled"):

* A run directory with ``summary.json`` but no producer sidecar is pre-hook (or VOID) and emits
  **zero rows**. The adapter never reads ``summary.json`` or ``records.jsonl`` to rebuild a tuple.
* If any line of a sidecar fails validation, the WHOLE file emits zero rows. Examples: the wrong
  schema, a broken self-hash, a measurement id that does not re-derive, or a line that is not JSON.
  The writer emits the file atomically, so a partly valid file is corruption, not a partial run.
* A missing or empty sidecar emits zero rows and raises no error.
* ``protocol_id`` is projected exactly as the producer wrote it. While no OCC protocol is codified
  it is empty, so ``grade()`` returns ``Judged``: every OCC-1 tuple is an OBSERVATION until one is.

The attestation is the per-request ``records.jsonl`` that the producer hashed. The reader hashes
it again on every read. If the file has moved or changed, the tuple grades DOWN through the shared
ladder instead of being skipped.

The locator names the RUN (run id, suite fingerprint, records file) and is shared by every row of
that run. Arm and metric separate the claims, so the harness they share stays visible in the
identity.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

from adapters.occ1_optical_compression_capture import (
    CAPTURE_SCHEMA,
    SIDECAR_NAME,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.occ1_optical_compression/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "occ1-optical-compression-measurement"


def _records_present(row: dict) -> bool:
    """True only when the attested records file still carries the bytes that were hashed."""
    path = Path(row["records_path"])
    if not path.is_file():
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest() == row["records_sha256"]


def _load_rows(sidecar_path: Path) -> list[dict] | None:
    """Parse and validate every producer row. ``None`` means the file is inadmissible."""
    try:
        text = sidecar_path.read_text()
    except OSError:
        return None
    rows: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        if validate_row(row):
            return None
        rows.append(row)
    if len({row["measurement_id"] for row in rows}) != len(rows):
        return None  # a duplicated identity inside one sidecar is producer corruption
    if len({(row["run_id"], row["records_sha256"], row["extra"]["suite_fingerprint"])
             for row in rows}) > 1:
        return None  # one sidecar is one run; mixed runs are corruption
    return rows


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Admissible native rows from one sidecar. A missing, empty or invalid file gives zero rows."""
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    rows = _load_rows(path)
    if not rows:
        return ()
    return tuple({"row": row, "sidecar_path": str(path)} for row in rows)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    """All admissible rows for one run directory. A pre-hook or VOID run gives zero rows."""
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. It validates the producer row again so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("OCC-1 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError(
            "OCC-1 row is not a producer-authored capture: " + "; ".join(problems))
    present = _records_present(row)
    extra = row["extra"]
    locator = (f"occ1:{row['run_id']}:suite{extra['suite_fingerprint']}:"
               f"{row['records_path']}")
    return ClaimTuple(
        measurement_id=row["measurement_id"],
        metric=row["metric"],
        value=row["value"],
        date=row["date"],
        category=row["category"],
        claim=row["claim"],
        metric_direction=row["metric_direction"],
        protocol_id=row["protocol_id"],
        reps=row["reps"],
        reps_basis=row["reps_basis"],
        unit=row["unit"],
        attestation_sha256=row["records_sha256"],
        attestation_locator=locator,
        attestation_present=present,
        # SC69: `present` IS the write-boundary check, because `_records_present` re-reads the
        # file and recomputes its digest.
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={
            "schema": row["schema"],
            "producer": row["producer"],
            "emitted_at": row["emitted_at"],
            "run_id": row["run_id"],
            "row_sha256": row["row_sha256"],
            "sidecar_path": native.get("sidecar_path", ""),
            **{key: extra[key] for key in sorted(extra)},
        },
    )


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    """Emit frames uniformly through the shared carrier (`claim_tuple.to_frames`)."""
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = [
    "ADAPTER_ID",
    "AUTHORITY",
    "CAPTURE_SCHEMA",
    "SIDECAR_NAME",
    "SOURCE_KIND",
    "frames_for_sidecar",
    "native_rows",
    "project",
    "rows_for_run",
]
