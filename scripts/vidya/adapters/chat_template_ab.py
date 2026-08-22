"""SC46 / CT-8 read side: project chat-template A/B sidecars into measurement ClaimTuples.

Strict by construction. The only admissible input is a producer-authored
``belief_measurements.jsonl`` sidecar written by ``chat_template_ab_capture.write_belief_measurements``
at summarize-time, sitting next to the run's ``summary.json``. This adapter PROJECTS each row into
the canonical :class:`ClaimTuple` and delegates every grading decision to ``claim_tuple.grade()``
— it holds no ladder and never returns a lattice level of its own.

Doctrine (the DF2-4 precedent, §4.7 "absence is recorded, never filled"):

* The completed CT-1 / CT-1b / CT-5(c)+16K runs and any E-7 recalibration already in flight when
  this hook landed are PRE-HOOK: their run directories carry ``summary.json`` but no producer
  sidecar, and they emit **zero rows**. This adapter never reads ``summary.json`` or the
  per-question JSONL to reconstruct a tuple — a tuple invented on read claims warrant the original
  run never captured.
* A sidecar that fails validation — wrong schema, a broken self-hash, a measurement id that does
  not re-derive, a non-JSON line — voids the WHOLE file (zero rows), because the writer emits the
  file atomically: partial validity is not a partial run, it is corruption or tampering.
* Missing or empty sidecar → zero rows, no error.

Attestation is the per-arm per-question results JSONL the producer hashed at summarize-time. The
reader re-hashes it on read: present-and-matching projects with the artifact present; moved or
mutated grades DOWN through the shared ladder instead of being skipped, so decay surfaces.

Locator note: each (arm, suite) cell is a DISTINCT claim (different suite = different question),
so per-cell claims do not manufacture same-harness corroboration; every locator still names the
run id first so the shared harness is visible in the identity.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.chat_template_ab_capture import (  # noqa: E402
    CAPTURE_SCHEMA,
    SIDECAR_NAME,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.chat_template_ab/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "chat-template-ab-measurement"


def _results_present(row: dict) -> bool:
    """True only when the attested per-question results file still carries the hashed bytes."""
    path = Path(row["results_path"])
    if not path.is_file():
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest() == row["results_sha256"]


def _load_rows(sidecar_path: Path) -> list[dict] | None:
    """Parse and validate every producer row; ``None`` means the file is inadmissible."""
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
    seen = {row["measurement_id"] for row in rows}
    if len(seen) != len(rows):
        return None  # duplicated identity inside one sidecar is producer corruption
    return rows


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Admissible native rows from one sidecar. Missing/empty/invalid file -> zero rows."""
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    rows = _load_rows(path)
    if not rows:
        return ()
    return tuple({
        "row": row,
        "sidecar_path": str(path),
        "attestation_present": _results_present(row),
    } for row in rows)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    """All admissible rows for one run directory. A pre-hook run has no sidecar: zero rows."""
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Revalidates the producer row so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("chat-template A/B native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError(
            "chat-template A/B row is not a producer-authored capture: " + "; ".join(problems))
    present = _results_present(row)
    extra = row["extra"]
    locator = (f"chat-template-ab:{row['run_id']}:arm{extra['arm']}:{extra['suite']}:"
               f"{row['results_path']}")
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
        attestation_sha256=row["results_sha256"],
        attestation_locator=locator,
        # Presence is decided by the projector (re-hash of the attested results file), so a moved
        # or mutated artifact grades DOWN through the shared ladder instead of being skipped.
        attestation_present=present,
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
    """Uniform frame emission through the shared carrier (`claim_tuple.to_frames`)."""
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "CAPTURE_SCHEMA", "SIDECAR_NAME",
    "native_rows", "rows_for_run", "project", "frames_for_sidecar",
]
