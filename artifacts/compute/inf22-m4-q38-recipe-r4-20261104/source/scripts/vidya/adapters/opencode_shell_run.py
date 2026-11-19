"""SC86 read side: project HS-4 OpenCode-shell run sidecars into measurement ClaimTuples.

Strict by construction. The only admissible input is the producer-authored
``opencode_shell_run.beliefs.jsonl`` that ``opencode_shell_run_capture.write_belief_measurements``
wrote at run end. The adapter PROJECTS each row, and ``claim_tuple.grade()`` decides.

Doctrine (§4.7: "absence is recorded, never filled"):

* A run directory with a run sidecar (``opencode_shell_run.json``) but no belief sidecar is
  pre-hook or refused, and emits **zero rows**. The reader never rebuilds a row from the run
  sidecar or the records file.
* If any line fails :func:`validate_row`, the WHOLE file emits zero rows. The writer is atomic, so
  a partly valid file is corruption.
* ``protocol_id`` is projected as written. No shell-run protocol is codified yet (SC86b), so every
  tuple grades ``Judged/Located``, an OBSERVATION.
* The attested per-attempt records file is re-hashed on every read. A moved or mutated file grades
  DOWN through the shared ladder; it is not skipped.

The locator names the RUN (run id, harness pin, config hash, records file). Every row of a run
shares it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters.opencode_shell_run_capture import (  # noqa: E402
    CAPTURE_SCHEMA,
    SIDECAR_NAME,
    file_sha256,
    validate_row,
)

ADAPTER_ID = "vidya.adapters.opencode_shell_run/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "opencode-shell-run-measurement"

_RUN_KEYS = ("run_id", "records_sha256")
_EXTRA_RUN_KEYS = ("harness_pin", "config_sha256", "plugin_sha256", "x_memory",
                   "run_sidecar_sha256")


def _records_present(row: dict) -> bool:
    path = Path(row["records_path"])
    return path.is_file() and file_sha256(path) == row["records_sha256"]


def _load_rows(path: Path) -> list[dict] | None:
    """Parse and validate every row. ``None`` means the file is inadmissible."""
    try:
        text = path.read_text()
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
        return None  # duplicated identity inside one sidecar
    identities = {tuple(row[k] for k in _RUN_KEYS)
                  + tuple(row["extra"][k] for k in _EXTRA_RUN_KEYS) for row in rows}
    if len(identities) > 1:
        return None  # one sidecar is one run
    return rows


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """Admissible rows from a run directory or a belief sidecar. Absent/invalid gives zero rows."""
    p = Path(path)
    sidecar = p / SIDECAR_NAME if p.is_dir() else p
    if not sidecar.is_file():
        return ()
    rows = _load_rows(sidecar)
    if not rows:
        return ()
    return tuple({"row": row, "sidecar_path": str(sidecar)} for row in rows)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. Re-validates so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("OpenCode shell-run native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError(
            "OpenCode shell-run row is not a producer-authored capture: " + "; ".join(problems))
    extra = row["extra"]
    present = _records_present(row)
    locator = (f"opencode-shell:{row['run_id']}:pin{extra['harness_pin']}:"
               f"cfg{extra['config_sha256']}:{row['records_path']}")
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
        # SC69: `present` re-read the file and recomputed its digest.
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


def frames_for_sidecar(path: str | Path, *, as_of: str) -> list[dict]:
    """Emit frames through the shared carrier (`claim_tuple.to_frames`)."""
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "CAPTURE_SCHEMA", "SIDECAR_NAME", "SOURCE_KIND",
           "frames_for_sidecar", "native_rows", "project"]
