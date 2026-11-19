#!/usr/bin/env python3
"""Prospective FM-4 gate evidence capture; never infer or grade task outcomes.

The caller supplies an explicit gate result and all dispatch identities. Evidence
is copied to a read-only content-addressed snapshot before the record is written.
SHA-256 detects later edits; filesystem owners can still replace these files.
This module does not establish that a gate was appropriate, actually executed,
or that caller-supplied identities match a transcript. It has no replay/import
mode and no historical oracle integration.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import sys


SCHEMA = "fm4.task_acceptance.v1"
# v1.1 adds only an optional transcript snapshot; records without one stay v1.
SCHEMA_V11 = "fm4.task_acceptance.v1.1"
IDENTITIES = ("parent_session_id", "dispatch_tool_use_id", "child_agent_id", "task_id")
FIELDS = {"schema", *IDENTITIES, "gate_result", "timestamp", "evidence"}
FIELDS_V11 = FIELDS | {"transcripts"}
TRANSCRIPT_ROLES = ("child", "parent")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z\Z")


def _digest(value):
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError("sha256 must be 64 lowercase hexadecimal characters")


def _read_evidence(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("evidence must be an existing regular file, not a symlink")
    return path.read_bytes()


def _validate_snapshot(evidence, label):
    """Rehash one content-addressed read-only snapshot {path, sha256}."""
    if not isinstance(evidence, dict) or set(evidence) != {"path", "sha256"}:
        raise ValueError(f"{label} must contain exactly path and sha256")
    _digest(evidence["sha256"])
    value = evidence["path"]
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError(f"invalid {label} path")
    path = Path(value)
    if not path.is_absolute() or str(path.resolve()) != value:
        raise ValueError(f"{label} path must be canonical and absolute")
    if path.name != evidence["sha256"] + ".bin":
        raise ValueError(f"{label} path must be content-addressed")
    raw = _read_evidence(path)
    if path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError(f"{label} snapshot must be read-only")
    if hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
        raise ValueError(f"{label} digest mismatch")


def validate_record(record):
    """Validate the exact v1/v1.1 shape and rehash every referenced snapshot."""
    if not isinstance(record, dict) or record.get("schema") not in (SCHEMA, SCHEMA_V11):
        raise ValueError("unsupported schema version")
    expected = FIELDS if record["schema"] == SCHEMA else FIELDS_V11
    if set(record) != expected:
        raise ValueError("record must contain exactly the " + record["schema"] + " fields")
    for name in IDENTITIES:
        value = record[name]
        if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
            raise ValueError(f"invalid {name}")
        if any(part in (".", "..") for part in value.split("/")):
            raise ValueError(f"invalid {name}")
    if not isinstance(record["gate_result"], str) or record["gate_result"] not in ("pass", "fail"):
        raise ValueError("gate_result must be exactly pass or fail")
    timestamp = record["timestamp"]
    if not isinstance(timestamp, str) or not UTC_TIMESTAMP.fullmatch(timestamp):
        raise ValueError("timestamp must be a UTC timestamp with microseconds")
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    _validate_snapshot(record["evidence"], "evidence")
    if record["schema"] == SCHEMA_V11:
        transcripts = record["transcripts"]
        if (not isinstance(transcripts, dict) or not transcripts
                or not set(transcripts) <= set(TRANSCRIPT_ROLES)):
            raise ValueError("transcripts must name child and/or parent snapshots")
        for role, snapshot in transcripts.items():
            _validate_snapshot(snapshot, role + " transcript")
    return record


def _write_new(path, raw):
    """Exclusive creation avoids overwriting a prior evidence or acceptance file."""
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(0o444)


def write_record(output, *, parent_session_id, dispatch_tool_use_id, child_agent_id,
                 task_id, gate_result, evidence_path, evidence_sha256,
                 child_transcript=None, parent_transcript=None):
    """Capture a new explicit gate decision now; caller cannot backdate it.

    Optional transcripts are copied byte-for-byte into the evidence store at
    capture time, so later rotation of the live JSONL cannot erase the inputs.
    """
    _digest(evidence_sha256)
    raw = _read_evidence(evidence_path)
    if hashlib.sha256(raw).hexdigest() != evidence_sha256:
        raise ValueError("evidence digest mismatch")
    transcript_bytes = {}
    for role, source in (("child", child_transcript), ("parent", parent_transcript)):
        if source is not None:
            try:
                transcript_bytes[role] = _read_evidence(source)
            except ValueError as exc:
                raise ValueError(f"{role} transcript: {exc}") from exc
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists")
    store = output.parent / "evidence"
    if store.is_symlink():
        raise ValueError("evidence store must not be a symlink")
    snapshot = store.resolve() / (evidence_sha256 + ".bin")
    record = dict(schema=SCHEMA, parent_session_id=parent_session_id,
                  dispatch_tool_use_id=dispatch_tool_use_id, child_agent_id=child_agent_id,
                  task_id=task_id, gate_result=gate_result,
                  timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                  evidence={"path": str(snapshot), "sha256": evidence_sha256})
    if transcript_bytes:
        record["schema"] = SCHEMA_V11
        record["transcripts"] = {
            role: {"path": str(store.resolve() / (hashlib.sha256(data).hexdigest() + ".bin")),
                   "sha256": hashlib.sha256(data).hexdigest()}
            for role, data in transcript_bytes.items()}
    # Validate scalar fields before creating any artifacts. Full validation below
    # additionally verifies the snapshot; no acceptance record exists until then.
    for name in IDENTITIES:
        value = record[name]
        if (not isinstance(value, str) or not IDENTIFIER.fullmatch(value)
                or any(part in (".", "..") for part in value.split("/"))):
            raise ValueError(f"invalid {name}")
    if not isinstance(gate_result, str) or gate_result not in ("pass", "fail"):
        raise ValueError("gate_result must be exactly pass or fail")
    store.mkdir(parents=True, exist_ok=True)
    blobs = [(snapshot, raw)] + [(Path(record["transcripts"][role]["path"]), data)
                                 for role, data in transcript_bytes.items()]
    for path, data in blobs:
        try:
            _write_new(path, data)
        except FileExistsError:
            pass  # Existing snapshots must pass the same integrity checks.
    validate_record(record)
    _write_new(output, (json.dumps(record, sort_keys=True, indent=2) + "\n").encode())
    return record


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("write")
    create.add_argument("--out", required=True, type=Path)
    for name in IDENTITIES:
        create.add_argument("--" + name.replace("_", "-"), required=True)
    create.add_argument("--gate-result", required=True, choices=("pass", "fail"))
    create.add_argument("--evidence-path", required=True, type=Path)
    create.add_argument("--evidence-sha256", required=True)
    create.add_argument("--child-transcript", type=Path)
    create.add_argument("--parent-transcript", type=Path)
    check = commands.add_parser("validate")
    check.add_argument("record", type=Path)
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "write":
            output = args.pop("out")
            record = write_record(output, **args)
        else:
            record = validate_record(json.loads(args["record"].read_text(),
                                                object_pairs_hook=_unique_object))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
