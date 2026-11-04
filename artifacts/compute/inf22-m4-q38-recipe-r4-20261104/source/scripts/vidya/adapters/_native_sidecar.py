"""Shared plumbing for producer-authored, self-hashed belief sidecars (write side + strict read).

Used by the TOC A/B, SkillBank A/B, HIL feature A/B and AutoKernel history-field carriers. It holds
NO ladder and decides nothing: each carrier validates its own row shape, projects into a
:class:`ClaimTuple`, and ``claim_tuple.grade()`` decides. Same row vocabulary as
``chat_template_ab_capture`` (``measurement_id / metric / value / unit / metric_direction / category /
claim / protocol_id / reps / reps_basis / extra`` + ``row_sha256``); one definition of
"well-formed" shared by writer and reader so the two cannot drift into two dialects.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

SHA256 = re.compile(r"^[0-9a-f]{64}$")
CATEGORIES = frozenset({"OPTIMUM", "BASELINE", "CANDIDATE"})
DIRECTIONS = frozenset({"higher_better", "lower_better"})
COMMON_TEXT = ("run_id", "producer", "measurement_id", "metric", "unit", "claim", "protocol_id",
               "reps_basis", "results_path", "date")


class CaptureError(ValueError):
    """The producer asked for a sidecar it did not capture the identity for."""


def canonical_json(value: Any) -> str:
    def check(obj: Any, path: str) -> None:
        if obj is None or isinstance(obj, (bool, int, str)):
            return
        if isinstance(obj, float):
            if not math.isfinite(obj):
                raise CaptureError(f"{path}: non-finite float is not canonical JSON")
            return
        if isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                check(item, f"{path}[{i}]")
            return
        if isinstance(obj, dict):
            for key, item in obj.items():
                if not isinstance(key, str):
                    raise CaptureError(f"{path}: canonical JSON keys must be strings")
                check(item, f"{path}.{key}")
            return
        raise CaptureError(f"{path}: {type(obj).__name__} is not canonical JSON")

    check(value, "$")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def row_digest(row: Mapping[str, Any]) -> str:
    return content_hash({k: v for k, v in row.items() if k != "row_sha256"})


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def results_present(row: Mapping[str, Any]) -> bool:
    """True only when the attested file still carries the hashed bytes."""
    path = Path(row["results_path"])
    return path.is_file() and file_sha256(path) == row["results_sha256"]


def utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def common_problems(row: Any, *, schema: str,
                    optional_text: tuple[str, ...] = ()) -> list[str]:
    """Envelope checks every carrier shares. Returns problems (empty == envelope valid).

    ``optional_text`` names COMMON_TEXT keys that may be the empty string (a carrier whose tuple is a
    deliberate OBSERVATION carries ``protocol_id == ""``); the key must still be present and a str.
    """
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != schema:
        p.append(f"schema must be {schema!r}")
    for key in COMMON_TEXT:
        if key in optional_text:
            if not isinstance(row.get(key), str):
                p.append(f"{key} must be a string (empty when absent)")
        elif not text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not utc_timestamp(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if row.get("metric_direction") not in DIRECTIONS:
        p.append("metric_direction must be recorded as higher_better or lower_better")
    if row.get("category") not in CATEGORIES:
        p.append("category must be exactly one of OPTIMUM/BASELINE/CANDIDATE")
    if not SHA256.match(str(row.get("results_sha256", ""))):
        p.append("results_sha256 must be a 64-hex digest over the attested file")
    if not isinstance(row.get("extra"), dict):
        p.append("extra must be an object carrying the run identity")
    if not finite(row.get("value")):
        p.append("value must be a finite number")
    return p


def self_hash_problems(row: Mapping[str, Any]) -> list[str]:
    if not SHA256.match(str(row.get("row_sha256", ""))):
        return ["row_sha256 must be a 64-hex self-hash"]
    try:
        if row_digest(row) != row["row_sha256"]:
            return ["row_sha256 does not bind the row content"]
    except CaptureError as exc:
        return [f"row is not canonically hashable: {exc}"]
    return []


def seal(row: dict[str, Any]) -> dict[str, Any]:
    row["row_sha256"] = row_digest(row)
    return row


def write_rows_atomic(sidecar: Path, rows: list[dict[str, Any]]) -> Path:
    if not rows:
        raise CaptureError("no rows to write")
    tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
    with open(tmp, "w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, sidecar)
    return sidecar


def load_rows(sidecar: Path, validate) -> list[dict] | None:
    """Parse + validate every row. ``None`` voids the WHOLE file (the writer is atomic)."""
    try:
        body = sidecar.read_text()
    except OSError:
        return None
    rows: list[dict] = []
    for line in body.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        if validate(row):
            return None
        rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        return None
    return rows


def native_rows(sidecar_path: str | Path, validate) -> tuple[dict, ...]:
    path = Path(sidecar_path)
    if not path.is_file():
        return ()
    rows = load_rows(path, validate)
    if not rows:
        return ()
    return tuple({"row": r, "sidecar_path": str(path),
                  "attestation_present": results_present(r)} for r in rows)


def check_identity(row: Mapping[str, Any], parts: Mapping[str, Any], prefix: str) -> list[str]:
    expected = f"{prefix}_{content_hash(dict(parts))[:24]}"
    if row.get("measurement_id") != expected:
        return ["measurement_id does not re-derive from its identity parts"]
    return []


LEGACY_NO_PROTOCOL = "observation:none"


def to_claim_tuple(row: Mapping[str, Any], *, source_kind: str, locator: str,
                   sidecar_path: str = "", no_protocol_ids: tuple[str, ...] = (),
                   legacy_schema_protocol: bool = False):
    """Projection only: authored fields -> ClaimTuple. ``claim_tuple.grade()`` decides."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from claim_tuple import ClaimTuple  # noqa: E402

    present = results_present(row)
    extra = row["extra"]
    # An OBSERVATION carries an EMPTY protocol_id: grade() reads any non-empty id as a protocol
    # and would grade the row Witnessed/Attested. Rows written before the fix carry the literal
    # "observation:none" or their own capture schema string as a pseudo-protocol; both mean "none".
    # Opt-in per adapter (``no_protocol_ids`` / ``legacy_schema_protocol``): other carriers may carry
    # a real protocol id of their own.
    protocol_id = row["protocol_id"]
    if protocol_id in no_protocol_ids or (legacy_schema_protocol and protocol_id == row.get("schema")):
        protocol_id = ""
    return ClaimTuple(
        measurement_id=row["measurement_id"], metric=row["metric"], value=row["value"],
        date=row["date"], category=row["category"], claim=row["claim"],
        metric_direction=row["metric_direction"], protocol_id=protocol_id,
        reps=row["reps"], reps_basis=row["reps_basis"], unit=row["unit"],
        attestation_sha256=row["results_sha256"], attestation_locator=locator,
        attestation_present=present,
        # `present` IS the write-boundary verification: the file was re-read and re-hashed.
        attestation_verified=True if present else None,
        source_kind=source_kind,
        extra={"schema": row["schema"], "producer": row["producer"],
               "emitted_at": row["emitted_at"], "run_id": row["run_id"],
               "row_sha256": row["row_sha256"], "sidecar_path": sidecar_path,
               **{k: extra[k] for k in sorted(extra)}},
    )
