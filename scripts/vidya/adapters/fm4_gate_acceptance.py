"""FM-4 selected-gate and native Codex dispatch observations for the coordinator.

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
import re
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

# The standalone Vidya CLI puts scripts/vidya, but not the repository, on sys.path.
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.experiments.fm4 import codex_dispatch, task_acceptance  # noqa: E402

SOURCE_KIND = "fm4-gate-acceptance"
ADAPTER_ID = "vidya.adapters.fm4_gate_acceptance/v1"
AUTHORITY = "selected_gate_observation_only"
DISPATCH_AUTHORITY = "native_codex_dispatch_observation_only"
PLANNER_CONSUMER = "coordination.fm4"
DISPATCH_BUNDLE_SCHEMA = "fm4.codex_dispatch.replay.v1"
DISPATCH_CENSUS_SCHEMA = "fm4.codex_dispatch.census.v1"
DISPATCH_PINS_SCHEMA = "fm4.codex_dispatch.census_inputs.v1"
DISPATCH_UNIT = "terminal_dispatch_indicator"
DISPATCH_LIMITATION = "Task outcome is unknown. The receipt records dispatch identity and the first child turn's terminal event."
_PAIR_ID = re.compile(r"[A-Za-z0-9_-]+")
_ROLL_ROLES = ("parent", "child")
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
    """Read an explicit FM-4 input and rederive the native observation rows."""
    try:
        path = Path(path).absolute()
        with _open_regular(path, read_only=True) as stream:
            raw = stream.read()
        path = path.resolve(strict=True)
        acceptance = _decode(raw)
        if isinstance(acceptance, dict) and acceptance.get("schema") == DISPATCH_BUNDLE_SCHEMA:
            return _dispatch_rows(path, raw, acceptance)
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


def _digest(value: Any) -> bool:
    return isinstance(value, str) and task_acceptance.SHA256.fullmatch(value) is not None


def _absolute(value: Any) -> Path:
    if not isinstance(value, str) or not value.startswith("/") or "\x00" in value:
        raise ValueError("dispatch replay paths must be canonical absolute paths")
    path = Path(value)
    if str(path) != value or path.resolve(strict=True) != path:
        raise ValueError("dispatch replay paths must be canonical absolute paths")
    return path


def _pairs(value: Any) -> list[str]:
    if (not isinstance(value, list) or not value
            or any(not isinstance(pair, str) or not _PAIR_ID.fullmatch(pair) for pair in value)
            or len(set(value)) != len(value)):
        raise ValueError("expected unique dispatch pair IDs")
    return value


def _sealed_json(path: Path, expected: str) -> dict:
    with _open_regular(path) as stream:
        raw = stream.read()
    if not _digest(expected) or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"{path.name} digest mismatch")
    record = _decode(raw)
    if not isinstance(record, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return record


def _replay_dispatch(snapshot_dir: Path, pair: dict, receipt: dict) -> dict:
    pair_id = pair["pair_id"]
    files = {}
    for role in _ROLL_ROLES:
        pin = pair["inputs"][role]
        filename = f"{pair_id}.{role}.jsonl"
        if (not isinstance(pin, dict) or set(pin) != {"bytes", "file", "sha256"}
                or pin["file"] != f"private/{filename}" or not _digest(pin["sha256"])
                or type(pin["bytes"]) is not int or pin["bytes"] <= 0):
            raise ValueError(f"{pair_id}: invalid {role} input pin")
        files[role] = snapshot_dir / filename
        try:
            with _open_regular(files[role], read_only=True) as stream:
                if os.fstat(stream.fileno()).st_size != pin["bytes"]:
                    raise ValueError("rollout size drift")
        except (OSError, ValueError):
            raise ValueError(f"{pair_id}: {role} snapshot type, mode or size drift") from None
    try:
        replayed = codex_dispatch.collect(files["parent"], files["child"])
    except (OSError, RuntimeError, ValueError):
        # A parsing error may contain private rollout content.
        raise ValueError(f"{pair_id}: private rollout replay refused") from None
    for role, observed in replayed["inputs"].items():
        if observed != {"path": str(files[role]), "sha256": pair["inputs"][role]["sha256"]}:
            raise ValueError(f"{pair_id}: {role} snapshot digest or path drift")
        del observed["path"]
    if replayed["disposition"] != "terminal_child":
        raise ValueError(f"{pair_id}: {replayed['disposition']}")
    if (replayed["identity"] != pair["identity"] or replayed["binding_kind"] != pair["binding_kind"]
            or replayed["lineage"]["child_agent_path"] != pair["child_agent_path"]):
        raise ValueError(f"{pair_id}: dispatch identity disagrees with input pins")
    replayed["pair_id"] = pair_id
    # Compare typed JSON, since Python equality treats bool and int as equal.
    if json.dumps(replayed, sort_keys=True) != json.dumps(receipt, sort_keys=True):
        raise ValueError(f"{pair_id}: filed receipt disagrees with native replay")
    return replayed


def _dispatch_rows(path: Path, raw: bytes, bundle: dict) -> tuple[dict, ...]:
    if set(bundle) != {"schema", "result", "result_sha256", "snapshot_dir", "pair_ids"}:
        raise ValueError("invalid Codex dispatch replay bundle")
    result_path = _absolute(bundle["result"])
    snapshot_dir = _absolute(bundle["snapshot_dir"])
    selected = _pairs(bundle["pair_ids"])
    result = _sealed_json(result_path, bundle["result_sha256"])
    if (set(result) != {"schema", "id", "mode", "input_pins_sha256", "collector_sha256",
                        "pair_ids", "receipts", "task_outcome", "cpus", "terminal_receipt_count",
                        "refusal_count"} or result["schema"] != DISPATCH_CENSUS_SCHEMA
            or result["mode"] != "official" or result["task_outcome"] is not None
            or type(result["refusal_count"]) is not int or result["refusal_count"] != 0):
        raise ValueError("expected a completed official Codex dispatch census with unknown task outcome")
    pair_ids = _pairs(result["pair_ids"])
    receipts = result["receipts"]
    if (not isinstance(receipts, list) or any(not isinstance(row, dict) for row in receipts)
            or [row.get("pair_id") for row in receipts] != pair_ids
            or type(result["terminal_receipt_count"]) is not int
            or result["terminal_receipt_count"] != len(pair_ids) or not set(selected) <= set(pair_ids)):
        raise ValueError("Codex dispatch receipt membership disagrees with the census")
    pins = _sealed_json(result_path.parent.parent / "input-pins.json", result["input_pins_sha256"])
    if (set(pins) != {"schema", "pairs", "collector_sha256"} or pins["schema"] != DISPATCH_PINS_SCHEMA
            or not isinstance(pins["pairs"], list)
            or any(not isinstance(pair, dict) or set(pair) != {
                "pair_id", "inputs", "identity", "binding_kind", "child_agent_path",
            } or not isinstance(pair["inputs"], dict) or set(pair["inputs"]) != set(_ROLL_ROLES)
                   for pair in pins["pairs"])
            or [pair["pair_id"] for pair in pins["pairs"]] != pair_ids):
        raise ValueError("Codex dispatch inputs disagree with census membership")
    with _open_regular(Path(codex_dispatch.__file__)) as stream:
        collector_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    if collector_sha != result["collector_sha256"] or collector_sha != pins["collector_sha256"]:
        raise ValueError("Codex dispatch collector digest mismatch")

    rows = []
    for pair, receipt in zip(pins["pairs"], receipts):
        if pair["pair_id"] in selected:
            rows.append({"path": str(path), "bundle_sha256": hashlib.sha256(raw).hexdigest(),
                         "result_path": str(result_path), "sha256": bundle["result_sha256"],
                         "receipt": _replay_dispatch(snapshot_dir, pair, receipt)})
    identities = [row["receipt"]["identity"] for row in rows]
    if (len({(i["parent_session_id"], i["dispatch_tool_use_id"]) for i in identities}) != len(rows)
            or len({i["child_agent_id"] for i in identities}) != len(rows)):
        raise ValueError("ambiguous duplicate dispatch identities in the census")
    return tuple(rows)


def _project_dispatch(current: dict) -> ClaimTuple:
    receipt = current["receipt"]
    pair_id = receipt["pair_id"]
    event = receipt["child_turn"]["terminal_event"]
    state = receipt["child_turn"]["state"]
    return ClaimTuple(
        measurement_id=f"{SOURCE_KIND}:{current['sha256']}:{pair_id}",
        metric="fm4_codex_terminal_dispatch",
        value=1,
        date="",
        category="CANDIDATE",
        claim=(f"FM-4 Codex dispatch {pair_id} bound by {receipt['binding_kind']} had a first-turn "
               f"terminal event {event} ({state}). {DISPATCH_LIMITATION}"),
        reps=1,
        reps_basis="one original Codex parent/child rollout pair",
        unit=DISPATCH_UNIT,
        attestation_path=current["result_path"],
        attestation_sha256=current["sha256"],
        attestation_locator=f"{current['result_path']}#sha256={current['sha256']}&pair_id={pair_id}",
        attestation_present=True,
        attestation_verified=True,
        source_kind=SOURCE_KIND,
        applicability={"consumer": PLANNER_CONSUMER},
        observation={"outcome_native": state, "outcome_reason": DISPATCH_LIMITATION},
        extra={"adapter": ADAPTER_ID, "receipt": receipt},
    )


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("path"), str):
        raise ProjectionError(f"{SOURCE_KIND}: native row malformed")
    for current in native_rows(native["path"]):
        if current == native:
            return _project_current(current)
    raise ProjectionError(f"{SOURCE_KIND}: native row does not rederive from its evidence")


def _project_current(current: dict) -> ClaimTuple:
    if "receipt" in current:
        return _project_dispatch(current)
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


def emit(path: Path, *, as_of: str, limit: int | None = None) -> list[dict]:
    """Use the shared carrier and preserve the authority of each native schema."""
    frames = []
    for row in native_rows(path)[:limit]:
        authority = DISPATCH_AUTHORITY if "receipt" in row else AUTHORITY
        frames.extend(to_frames(_project_current(row), as_of=as_of, adapter_id=ADAPTER_ID, authority=authority))
    return frames
