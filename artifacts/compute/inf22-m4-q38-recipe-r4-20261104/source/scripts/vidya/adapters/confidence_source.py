"""VB-EVCONF2 read side: project EV-CONF-2 confidence-source sidecars into measurement ClaimTuples.

The only admissible input is a producer-authored ``<report>.beliefs.jsonl`` written by
``confidence_source_capture.write_belief_measurements`` right after the report was computed.
This adapter PROJECTS each row into :class:`ClaimTuple` and leaves every grading decision to
``claim_tuple.grade()``. It holds no ladder. The empty ``protocol_id`` that the producer records
for an observation-grade report is what makes the shared ladder answer ``Judged/Located``; this
module does not decide it.

Doctrine (the DF2-4 precedent, §4.7):

* A report with no sidecar is pre-hook and emits ZERO rows. That includes the E7c math and EV-4c
  code aggregates quoted in the ESC-7 draft and P-CAL. The report and the per-question sidecars
  are never read to reconstruct a tuple.
* A sidecar with any invalid line is void as a whole.
* Attestation is the compare report. The reader re-hashes it, the serving-identity file and
  every input question-result sidecar the report names. A moved or mutated artifact grades DOWN
  through the shared ladder instead of disappearing.

The speculative-decoding state rides in ``extra.spec`` and, for ``on`` / ``unknown``, leads the
claim text. A spec-on AUROC and a spec-off AUROC are different measurements, and the locator
names the arm.

Locator: run x arm x source x metric, never per question. The 200 probe rows are scored samples
from one run, not 200 witnesses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.confidence_source_capture import (  # noqa: E402
    CAPTURE_SCHEMA,
    SIDECAR_SUFFIX,
    file_sha256,
    sidecar_path,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.confidence_source/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ev-conf2-confidence-source"


def _matches(path: str, sha: str) -> bool:
    p = Path(path)
    return p.is_file() and file_sha256(p) == sha


def _present(row: dict) -> bool:
    if not _matches(row["report_path"], row["report_sha256"]):
        return False
    if not _matches(row["identity_path"], row["identity_sha256"]):
        return False
    return all(_matches(s["path"], s["sha256"]) for s in row["extra"]["sidecars"])


def native_rows(sidecar: str | Path) -> tuple[dict, ...]:
    """Admissible native rows from one sidecar. Missing/empty/invalid -> zero rows."""
    path = Path(sidecar)
    if not path.is_file():
        return ()
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ()
    rows: list[dict] = []
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
        return ()  # duplicated identity inside one sidecar is producer corruption
    if len({(r["report_sha256"], r["extra"]["arm"]) for r in rows}) > 1:
        return ()  # one sidecar describes one report of one arm
    return tuple({"row": r, "sidecar_path": str(path), "attestation_present": _present(r)}
                 for r in rows)


def rows_for_report(report_path: str | Path) -> tuple[dict, ...]:
    """All admissible rows for one compare report; a pre-hook report -> zero rows."""
    return native_rows(sidecar_path(report_path))


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Revalidates the producer row so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("EV-CONF-2 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("EV-CONF-2 row is not a producer-authored capture: " + "; ".join(problems))
    present = _present(row)
    extra = row["extra"]
    locator = (f"ev-conf2:{row['run_id']}:{extra['arm']}:{extra['source']}:{row['metric']}:"
               f"{row['report_path']}")
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
        attestation_sha256=row["report_sha256"],
        attestation_locator=locator,
        attestation_present=present,
        # `present` IS the write-boundary re-hash (SC69), carried so the ladder stays pure.
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={"schema": row["schema"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "run_id": row["run_id"],
               "row_sha256": row["row_sha256"], "identity_sha256": row["identity_sha256"],
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
           "native_rows", "rows_for_report", "project", "frames_for_sidecar"]
