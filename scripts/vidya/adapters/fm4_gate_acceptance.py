"""Prospective FM-4 selected-gate observations for the coordination planner.

Use the native acceptance record, its adjacent execution JSON, and the
content-addressed snapshot. Their agreement establishes record integrity.
Gate suitability and dispatch provenance remain caller obligations.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

# The standalone Vidya CLI puts scripts/vidya, but not the repository, on sys.path.
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.experiments.fm4 import task_acceptance  # noqa: E402

SOURCE_KIND = "fm4-gate-acceptance"
ADAPTER_ID = "vidya.adapters.fm4_gate_acceptance/v1"
AUTHORITY = "selected_gate_observation_only"
PLANNER_CONSUMER = "coordination.fm4"
EXECUTION_SCHEMA = "fm4.gate_execution.v1"
EXECUTION_FIELDS = {
    "schema", *task_acceptance.IDENTITIES, "argv", "cwd", "timeout_s", "returncode",
    "timed_out", "launch_error", "started_at", "ended_at", "stdout_base64", "stderr_base64",
}
LIMITATION = (
    "Scope is the selected gate's exit only. Task accuracy and historical verdicts "
    "are outside this record's scope. Gate suitability and dispatch identities are caller-supplied."
)


def _open_regular(path: Path, *, read_only: bool = False):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    stream = open(path, "rb", opener=lambda name, mode: os.open(name, mode | flags))
    mode = os.fstat(stream.fileno()).st_mode
    if not stat.S_ISREG(mode) or (read_only and mode & 0o222):
        stream.close()
        kind = "read-only regular file" if read_only else "regular file"
        raise ValueError(f"{path.name} must be a {kind}")
    return stream


def _invalid_constant(_: str) -> None:
    raise ValueError("nonfinite JSON constant")


def _decode(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"), object_pairs_hook=task_acceptance._unique_object,
                      parse_constant=_invalid_constant)


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not task_acceptance.UTC_TIMESTAMP.fullmatch(value):
        raise ValueError("timestamp must be UTC with microseconds")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


def _validate_execution(execution: Any, acceptance: dict) -> None:
    if (not isinstance(execution, dict) or set(execution) != EXECUTION_FIELDS
            or execution["schema"] != EXECUTION_SCHEMA):
        raise ValueError("evidence must contain exactly the fm4.gate_execution.v1 fields")
    for name in task_acceptance.IDENTITIES:
        if execution[name] != acceptance[name]:
            raise ValueError(f"execution {name} does not match acceptance")
    argv, cwd = execution["argv"], execution["cwd"]
    if (not isinstance(argv, list) or not argv or not argv[0]
            or any(not isinstance(word, str) or "\x00" in word for word in argv)):
        raise ValueError("invalid execution argv")
    # Validate the producer's recorded path without relying on the worktree still existing.
    if (not isinstance(cwd, str) or not cwd.startswith("/") or cwd.startswith("//")
            or "\x00" in cwd or os.path.normpath(cwd) != cwd):
        raise ValueError("execution cwd must be a canonical absolute path")
    timeout = execution["timeout_s"]
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("execution timeout must be finite and positive")
    code = execution["returncode"]
    if (execution["timed_out"] is not False or execution["launch_error"] is not None
            or type(code) is not int or not 0 <= code <= 255):
        raise ValueError("execution did not complete with a normal exit status")
    if acceptance["gate_result"] != ("pass" if code == 0 else "fail"):
        raise ValueError("execution exit status does not match gate result")
    started, ended, recorded = map(_timestamp, (
        execution["started_at"], execution["ended_at"], acceptance["timestamp"],
    ))
    if not started <= ended <= recorded:
        raise ValueError("execution and acceptance timestamps are out of order")
    for name in ("stdout_base64", "stderr_base64"):
        value = execution[name]
        if not isinstance(value, str) or base64.b64encode(
                base64.b64decode(value, validate=True)).decode("ascii") != value:
            raise ValueError(f"invalid {name} capture")


def units(path: Path) -> list[Path]:
    return [path] if path.is_file() or path.is_symlink() else []


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """Read one explicit acceptance bundle and verify both evidence copies."""
    try:
        path = Path(path).absolute()
        with _open_regular(path, read_only=True) as stream:
            raw = stream.read()
        path = path.resolve(strict=True)
        acceptance = _decode(raw)
        evidence = acceptance.get("evidence") if isinstance(acceptance, dict) else None
        digest = evidence.get("sha256") if isinstance(evidence, dict) else None
        if not isinstance(digest, str) or not task_acceptance.SHA256.fullmatch(digest):
            raise ValueError("acceptance evidence must name a SHA-256 digest")
        snapshot = path.parent / "evidence" / f"{digest}.bin"
        if evidence.get("path") != str(snapshot):
            raise ValueError("evidence snapshot must be in the acceptance bundle")
        task_acceptance.validate_record(acceptance)
        with _open_regular(snapshot, read_only=True) as stream:
            body = stream.read()
        if hashlib.sha256(body).hexdigest() != digest:
            raise ValueError("execution snapshot digest mismatch")
        sidecar = path.with_name(f"{path.name}.execution.json")
        with _open_regular(sidecar) as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                raise ValueError("adjacent execution JSON disagrees with the evidence snapshot")
        execution = _decode(body)
        _validate_execution(execution, acceptance)
    except (TypeError, ValueError, OverflowError, OSError, RuntimeError) as exc:
        raise ProjectionError(f"{SOURCE_KIND}: {exc}") from exc
    stdout_and_stderr = {"stdout_base64", "stderr_base64"}
    return ({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "acceptance": acceptance,
             "execution": {k: v for k, v in execution.items() if k not in stdout_and_stderr}},)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("path"), str):
        raise ProjectionError(f"{SOURCE_KIND}: native row malformed")
    (current,) = native_rows(native["path"])
    if native != current:
        raise ProjectionError(f"{SOURCE_KIND}: native row does not rederive from its evidence")
    record, execution = current["acceptance"], current["execution"]
    result = record["gate_result"]
    return ClaimTuple(
        measurement_id=f"{SOURCE_KIND}:{current['sha256']}",
        metric="fm4_selected_gate_pass",
        value=int(result == "pass"),
        date=record["timestamp"][:10],
        category="CANDIDATE",
        claim=(f"FM-4 selected gate reported {result} for task {record['task_id']} "
               f"(exit {execution['returncode']}). {LIMITATION}"),
        metric_direction="higher_better",
        protocol_id="",
        reps=1,
        reps_basis="one normally completed selected gate",
        unit="gate_pass_indicator",
        attestation_path=current["path"],
        attestation_sha256=current["sha256"],
        attestation_locator=f"{current['path']}#sha256={current['sha256']}",
        attestation_present=True,
        attestation_verified=True,
        source_kind=SOURCE_KIND,
        applicability={"consumer": PLANNER_CONSUMER},
        observation={"outcome_native": result, "outcome_reason": LIMITATION},
        extra={"adapter": ADAPTER_ID, "acceptance": record, "execution": execution},
    )
