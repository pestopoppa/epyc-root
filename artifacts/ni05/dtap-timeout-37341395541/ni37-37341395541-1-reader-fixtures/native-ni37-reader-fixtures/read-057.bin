"""SC75 / VB-INF70-ARMS read side: project INF-70 serving-arm sidecars into measurement ClaimTuples.

This reader is strict by construction. The only input it accepts is a producer-authored
``<label>.belief_measurements.jsonl`` sidecar, which
``inf70_serving_arm_capture.write_arm_measurement`` writes at arm end next to that arm's
``rows.jsonl`` and ``coresidency``. The adapter PROJECTS each row into the canonical
:class:`ClaimTuple` and leaves every grading decision to ``claim_tuple.grade()``. It
holds no ladder and never returns a lattice level of its own. It is also distinct from
``inf70_roofline_ledger.py``, which reads the C0/C5/B1/D0 roofline run directories, a
different producer.

Doctrine (§4.7, "absence is recorded, never filled"):

* **An arm with no sidecar emits zero rows.** Every arm the harness ran before this hook
  existed has a ``.coresidency`` and a ``.timeline`` but no sidecar. That covers all of
  ``agents/*/runs`` up to 2026-09-16, including the 2026-09-07 HARNESS-1 arms, whose
  verdicts came from the corrected sampler. This adapter never parses those files to
  reconstruct a verdict. The timeline's clock carries no date, and a verdict attached
  after the fact claims warrant the arm never captured.
* **An arm from before 2026-09-07 emits zero rows even if a sidecar exists.** The shared
  ``validate_row`` refuses it. Its label came from the sampler that read cpus 184-191 as
  disjoint, so the label is wrong, not merely missing.
* **One bad row voids the whole sidecar.** Any validation failure (wrong schema, broken
  self-hash, an id that does not re-derive, a non-JSON line) means zero rows for that file.
* **Locator = the arm/launch**, never a per-prompt row (SC6-HAZARD). The verdict is part of
  both the identity and the locator.

Attestation is the arm's ``rows.jsonl``, which the producer hashed at arm end. The reader
hashes it again. If it still matches, the row projects with the artifact present. If the file
was moved or changed, the row grades DOWN through the shared ladder instead of being skipped.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.inf70_serving_arm_capture import (  # noqa: E402
    CAPTURE_SCHEMA,
    SIDECAR_SUFFIX,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.inf70_serving_arm/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "inf70-serving-arm-measurement"


def _rows_present(row: dict) -> bool:
    path = Path(row["rows_path"])
    if not path.is_file():
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest() == row["rows_sha256"]


def _load_rows(sidecar_path: Path) -> list[dict] | None:
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
    return tuple({"row": row, "sidecar_path": str(path),
                  "attestation_present": _rows_present(row)} for row in rows)


def rows_for_run_dir(run_dir: str | Path) -> tuple[dict, ...]:
    """Every admissible arm row in one harness ``runs/`` directory. Pre-hook arms: none."""
    out: list[dict] = []
    for sidecar in sorted(Path(run_dir).glob(f"*{SIDECAR_SUFFIX}")):
        out.extend(native_rows(sidecar))
    return tuple(out)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Revalidates the producer row so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("INF-70 serving-arm native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError(
            "INF-70 serving-arm row is not a producer-authored capture: " + "; ".join(problems))
    present = _rows_present(row)
    extra = row["extra"]
    verdict = extra["contention"]["contention_verdict"]
    locator = (f"inf70-serving-arm:{extra['launch_id']}:{row['label']}:"
               f"{extra['arm_started_at']}:contention-{verdict}")
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
        attestation_sha256=row["rows_sha256"],
        attestation_locator=locator,
        attestation_present=present,
        # SC69: `present` is the re-read-and-match check done at this boundary.
        attestation_verified=True if present else None,
        source_kind=SOURCE_KIND,
        extra={
            "schema": row["schema"],
            "producer": row["producer"],
            "emitted_at": row["emitted_at"],
            "label": row["label"],
            "row_sha256": row["row_sha256"],
            "rows_path": row["rows_path"],
            "sidecar_path": native.get("sidecar_path", ""),
            "contention_verdict": verdict,
            **{key: extra[key] for key in sorted(extra)},
        },
    )


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


def frames_for_run_dir(run_dir: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in rows_for_run_dir(run_dir):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "CAPTURE_SCHEMA", "SIDECAR_SUFFIX",
    "native_rows", "rows_for_run_dir", "project", "frames_for_sidecar", "frames_for_run_dir",
]
