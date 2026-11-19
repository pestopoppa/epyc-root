"""SC68 read side: project BEAM conversational-memory run sidecars into measurement ClaimTuples.

Strict by construction. The only admissible input is a producer-authored
``belief_measurements.jsonl`` sidecar written by ``beam_memory_capture.write_belief_measurements``
at score-time, beside the folded artifact. This adapter PROJECTS each row into the canonical
:class:`ClaimTuple` and delegates every grading decision to ``claim_tuple.grade()`` — it holds no
ladder and never returns a lattice level of its own.

Doctrine (§4.7 "absence is recorded, never filled"):

* **Pre-hook runs emit zero rows, permanently.** A folded or judged BEAM artifact with no sidecar
  is never read to reconstruct a tuple: its arm and judge identity were never attested.
* A sidecar that fails validation — wrong schema, broken self-hash, an id that does not re-derive,
  a value that is not the BEAM fold of its own per-ability columns, a non-JSON line, a duplicated
  id — voids the WHOLE file (zero rows).
* Missing or empty sidecar -> zero rows, no error.

**One claim per run arm: the BEAM-fold headline.** The rubric-item micro-average and the binarised
pass count are recorded context carried into ``ClaimTuple.extra`` — never separate claims, so the
two folds cannot be graded as two corroborating witnesses of one run.

**Locator = the run** (with its split, arm and judge), never a per-question or per-nugget file:
400 questions judged in one harness execution are samples of one witness.

Attestation is the folded artifact the producer hashed. A moved or mutated artifact grades DOWN
through the shared ladder instead of being skipped.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.beam_memory_capture import (  # noqa: E402
    CAPTURE_SCHEMA,
    SIDECAR_NAME,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.beam_memory/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "beam-memory-measurement"


def _scored_present(row: dict) -> bool:
    """True only when the attested folded artifact still carries the hashed bytes."""
    path = Path(row["scored_path"])
    if not path.is_file():
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest() == row["scored_sha256"]


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
    if len({row["measurement_id"] for row in rows}) != len(rows):
        return None
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
        "attestation_present": _scored_present(row),
    } for row in rows)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    """All admissible rows for one run directory. A pre-hook run has no sidecar: zero rows."""
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Revalidates the producer row so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("BEAM native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError(
            "BEAM row is not a producer-authored capture: " + "; ".join(problems))
    present = _scored_present(row)
    extra = row["extra"]
    locator = (f"beam:{row['run_id']}:{extra['split']}:arm-{extra['arm']}:"
               f"judge-{extra['judge_model']}")
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
        attestation_sha256=row["scored_sha256"],
        attestation_locator=locator,
        attestation_present=present,
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={
            "schema": row["schema"],
            "producer": row["producer"],
            "emitted_at": row["emitted_at"],
            "run_id": row["run_id"],
            "row_sha256": row["row_sha256"],
            "scored_path": row["scored_path"],
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
