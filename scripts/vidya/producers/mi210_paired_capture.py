"""Prospective MI210 paired-serving raw custody; deliberately no grading rule.

Call begin BEFORE launching a fresh run, record AFTER EACH launch (including failures),
and finish on every terminal path. Unknown native fields stay null. This component is
not a historical importer, measurement attestation, adapter or planning-context canary.
The producer must supply model/build digests, grant, native request timings, actual
placement, and in-request residency/linkage observations; it never infers these.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.vidya.adapters import _native_sidecar as carrier

SCHEMA = "epyc.mi210.paired.raw.v1"
SOURCES = {"NPD1-STEP3", "Q38P-3a"}
MAX_BYTES = 8 * 1024 * 1024
ATTEMPT_FIELDS = {"pair", "arm", "state", "requests", "actual_placement",
                  "residency_linkage", "grant", "stop", "errors", "release"}


def _root(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("existing nonsymlink capture directory required")
    return root


def _create(path, row):
    row = dict(row)
    row["row_sha256"] = carrier.row_digest(row)
    raw = (carrier.canonical_json(row) + "\n").encode()
    if len(raw) > MAX_BYTES:
        raise ValueError("capture exceeds bounded record size")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short capture write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return row


def _read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("invalid capture path or size")
    row = json.loads(path.read_bytes())
    if (row.get("schema") != SCHEMA or row.get("row_sha256") != carrier.row_digest(row)):
        raise ValueError("capture schema or digest mismatch")
    return row


def _declaration(declaration):
    required = {"source", "mode", "model", "builds", "recipe", "order", "grant", "native_producer"}
    if not isinstance(declaration, dict):
        raise ValueError("declaration must be an object")
    if not required <= declaration.keys():
        raise ValueError("declaration fields missing")
    if declaration["source"] not in SOURCES or declaration["mode"] not in {"smoke", "measurement"}:
        raise ValueError("source or mode")
    order = declaration["order"]
    if (not isinstance(order, list) or not 1 <= len(order) <= 16
            or any(not isinstance(x, list) or len(x) != 2
                   or any(not isinstance(y, str) or not y for y in x) for x in order)):
        raise ValueError("ordered pair/arm launch list required")
    native = declaration["native_producer"]
    if (not isinstance(native, dict) or not isinstance(native.get("path"), str)
            or not native["path"] or not carrier.SHA256.fullmatch(str(native.get("sha256", "")))):
        raise ValueError("original native producer path/hash required")


def begin(root, declaration):
    """Create-once write-side declaration. Missing warrant is explicit, never filled in."""
    root = _root(root)
    _declaration(declaration)
    native = declaration["native_producer"]
    source = Path(native["path"])
    if (source.is_symlink() or not source.is_file()
            or carrier.file_sha256(source) != native["sha256"]):
        raise ValueError("original native producer bytes do not match declaration")
    if list(root.iterdir()):
        raise ValueError("fresh capture directory required; historical adoption forbidden")
    return _create(root / "declaration.json", {
        "schema": SCHEMA, "kind": "declaration", "run_id": root.name,
        "started_ns": time.monotonic_ns(), "declaration": declaration,
        "date": datetime.now(timezone.utc).isoformat(),
        "producer_sha256": carrier.file_sha256(Path(__file__)),
    })


def _chain(root):
    intent = _read(root / "declaration.json")
    if intent.get("kind") != "declaration" or intent.get("run_id") != root.name:
        raise ValueError("declaration identity")
    _declaration(intent.get("declaration"))
    attempts = []
    previous = intent["row_sha256"]
    order = intent["declaration"]["order"]
    paths = sorted(root.glob("attempt-*.json"))
    if len(paths) > len(order):
        raise ValueError("extra attempt")
    for index, path in enumerate(paths):
        row = _read(path)
        native = row.get("native")
        if (not isinstance(native, dict) or not ATTEMPT_FIELDS <= native.keys()
                or native["state"] not in {"complete", "partial", "failed", "stopped"}):
            raise ValueError("native fields or state")
        if (path.name != f"attempt-{index:02d}.json" or row.get("kind") != "attempt"
                or row.get("run_id") != root.name or row.get("index") != index
                or row.get("previous_sha256") != previous
                or [row["native"]["pair"], row["native"]["arm"]] != order[index]
                or row["recorded_ns"] < (attempts[-1]["recorded_ns"] if attempts else intent["started_ns"])):
            raise ValueError("attempt order or declaration custody")
        attempts.append(row)
        previous = row["row_sha256"]
    return intent, attempts, previous


def record(root, native):
    """Persist native evidence even for stopped, failed and incomplete launches."""
    root = _root(root)
    if (root / "terminal.json").exists():
        raise ValueError("run already terminal")
    intent, attempts, previous = _chain(root)
    index = len(attempts)
    if not ATTEMPT_FIELDS <= native.keys() or native["state"] not in {"complete", "partial", "failed", "stopped"}:
        raise ValueError("native fields or state")
    order = intent["declaration"]["order"]
    if index >= len(order) or [native["pair"], native["arm"]] != order[index]:
        raise ValueError("launch differs from declared order")
    return _create(root / f"attempt-{index:02d}.json", {
        "schema": SCHEMA, "kind": "attempt", "run_id": root.name, "index": index,
        "previous_sha256": previous, "recorded_ns": time.monotonic_ns(), "native": native,
    })


def finish(root, state, *, stop=None, errors=None):
    root = _root(root)
    intent, attempts, previous = _chain(root)
    if state not in {"complete", "partial", "failed", "stopped"}:
        raise ValueError("terminal state")
    if state == "complete" and (len(attempts) != len(intent["declaration"]["order"])
                                or any(x["native"]["state"] != "complete" for x in attempts)):
        raise ValueError("complete run requires every declared launch")
    return _create(root / "terminal.json", {
        "schema": SCHEMA, "kind": "terminal", "run_id": root.name,
        "previous_sha256": previous, "attempt_count": len(attempts),
        "state": state, "stop": stop, "errors": errors, "finished_ns": time.monotonic_ns(),
    })


def read(root):
    """Strict readback; an unclosed run is exposed as interrupted, never complete."""
    root = _root(root)
    intent, attempts, previous = _chain(root)
    terminal = None
    if (root / "terminal.json").exists():
        terminal = _read(root / "terminal.json")
        if terminal.get("state") not in {"complete", "partial", "failed", "stopped"}:
            raise ValueError("terminal state")
        if terminal["state"] == "complete" and (
                len(attempts) != len(intent["declaration"]["order"])
                or any(x["native"]["state"] != "complete" for x in attempts)):
            raise ValueError("complete run requires every declared launch")
        last_ns = attempts[-1]["recorded_ns"] if attempts else intent["started_ns"]
        if (terminal.get("kind") != "terminal" or terminal.get("run_id") != root.name
                or terminal.get("previous_sha256") != previous
                or terminal.get("attempt_count") != len(attempts)
                or terminal.get("finished_ns", -1) < last_ns):
            raise ValueError("terminal custody")
    return {"intent": intent, "attempts": attempts, "terminal": terminal,
            "state": terminal["state"] if terminal else "interrupted"}
