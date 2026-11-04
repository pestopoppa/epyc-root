"""Provider-authored full-quarter flock receipts. No scheduler authority is inferred."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "region-lock-claim.v1"


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _birth():
    return int(Path(f"/proc/{os.getpid()}/stat").read_text().rsplit(") ", 1)[1].split()[19])


def _flock_proof(regions, lock_root):
    """Sample kernel flock ownership in this provider process before open."""
    rows = Path("/proc/locks").read_text().splitlines()
    proof = []
    for region in sorted(regions):
        path = Path(lock_root) / f"cpu_region.GLOBAL.{region}.lock"
        stat = path.stat()
        dev = (os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino)
        matches = []
        for row in rows:
            parts = row.split()
            if len(parts) < 8 or parts[1:4] != ["FLOCK", "ADVISORY", "WRITE"]:
                continue
            try:
                major, minor, inode = parts[5].split(":")
                identity = (int(major, 16), int(minor, 16), int(inode))
                if int(parts[4]) == os.getpid() and identity == dev:
                    matches.append(row)
            except (ValueError, IndexError):
                continue
        if len(matches) != 1:
            raise RuntimeError(f"provider lacks one witnessed global flock for {region}")
        proof.append({"region": region, "path": str(path.resolve()), "device_major": dev[0],
                      "device_minor": dev[1], "inode": dev[2], "proc_locks_row": matches[0]})
    return proof


def _cpu_set(text):
    result = set()
    for part in text.split(","):
        if not re.fullmatch(r"\d+(?:-\d+)?", part):
            raise ValueError("invalid CPU list")
        first, _, last = part.partition("-")
        lo, hi = int(first), int(last or first)
        if hi < lo or hi > 100000:
            raise ValueError("invalid CPU range")
        result.update(range(lo, hi + 1))
    if not result:
        raise ValueError("empty CPU list")
    return result


def _time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return result


def _grant_fields(raw):
    fields = {}
    for item in raw.decode().split():
        key, sep, value = item.partition("=")
        if not sep or key in fields or not value:
            raise ValueError("malformed grant")
        fields[key] = value
    return fields


def _grant(path, cpus):
    raw = path.read_bytes()
    if not path.name.endswith(".grant") or not raw:
        raise ValueError("grant must be a nonempty named .grant")
    fields = _grant_fields(raw)
    if not {"regions", "start", "end"} <= fields.keys() or _cpu_set(fields["regions"]) != _cpu_set(cpus):
        raise ValueError("grant CPU mismatch")
    if not _time(fields["start"]) <= datetime.now(timezone.utc) < _time(fields["end"]):
        raise ValueError("grant inactive")
    return raw, fields


def _write_bytes(path, data):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return data


def _write(path, obj):
    data = (json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    return _write_bytes(path, data)


def open_receipt(prefix, grant_path, cpus, regions, provider, lock, lock_root):
    grant_path = Path(grant_path)
    raw, grant = _grant(grant_path, cpus)
    flock_proof = _flock_proof(regions, lock_root)
    grant_copy = Path(str(prefix) + ".grant")
    if grant_copy.resolve() == grant_path.resolve():
        raise ValueError("grant copy must not overwrite original")
    _write_bytes(grant_copy, raw)
    obj = {"schema": SCHEMA, "phase": "open", "claim_id": uuid.uuid4().hex, "provider": "region-lock",
           "provider_pid": os.getpid(), "provider_pid_starttime": _birth(), "cpu_list": cpus,
           "lock_root": str(Path(lock_root).resolve()),
           "flock_proof": flock_proof,
           "regions": sorted(regions), "grant_id": grant_path.name[:-6], "grant_path": str(grant_path.resolve()),
           "grant_copy_path": str(grant_copy.resolve()),
           "grant_sha256": _sha(raw), "grant_start": grant["start"], "grant_end": grant["end"],
           "opened_utc": datetime.now(timezone.utc).isoformat(),
           "receipt_source_path": str(Path(__file__).resolve()), "receipt_source_sha256": _sha(Path(__file__).read_bytes()),
           "provider_source_path": str(provider.resolve()), "provider_source_sha256": _sha(provider.read_bytes()),
           "lock_source_path": str(lock.resolve()), "lock_source_sha256": _sha(lock.read_bytes())}
    path = Path(str(prefix) + ".open.json")
    data = _write(path, obj)
    return {"record": obj, "path": str(path.resolve()), "sha256": _sha(data)}


def close_receipt(prefix, opened, child_rc):
    obj = {"schema": SCHEMA, "phase": "close", "claim_id": opened["record"]["claim_id"],
           "open_path": opened["path"], "open_sha256": opened["sha256"], "provider_pid": os.getpid(),
           "provider_pid_starttime": _birth(), "closed_utc": datetime.now(timezone.utc).isoformat(),
           "child_rc": child_rc}
    _write(Path(str(prefix) + ".close.json"), obj)
    return obj


def verify(open_path, close_path, *, provider_sha256, lock_sha256, receipt_sha256, expected_lock_root):
    open_path, close_path = Path(open_path), Path(close_path)
    raw = open_path.read_bytes()
    opened, closed = json.loads(raw), json.loads(close_path.read_bytes())
    if opened.get("schema") != SCHEMA or opened.get("phase") != "open" or opened.get("provider") != "region-lock":
        raise ValueError("invalid provider open")
    if (not re.fullmatch(r"[0-9a-f]{32}", str(opened.get("claim_id", "")))
            or type(opened.get("provider_pid")) is not int or opened["provider_pid"] <= 0
            or type(opened.get("provider_pid_starttime")) is not int or opened["provider_pid_starttime"] <= 0):
        raise ValueError("invalid provider identity")
    if opened.get("lock_root") != str(Path(expected_lock_root).resolve()):
        raise ValueError("unexpected physical lock root")
    if closed.get("schema") != SCHEMA or closed.get("phase") != "close":
        raise ValueError("invalid provider close")
    if closed.get("open_sha256") != _sha(raw) or closed.get("open_path") != str(open_path.resolve()):
        raise ValueError("close does not bind open")
    for key in ("claim_id", "provider_pid", "provider_pid_starttime"):
        if not opened.get(key) or closed.get(key) != opened[key]:
            raise ValueError(f"open/close {key} mismatch")
    if type(closed.get("child_rc")) is not int:
        raise ValueError("invalid child status")
    if opened.get("provider_source_sha256") != provider_sha256 or opened.get("lock_source_sha256") != lock_sha256:
        raise ValueError("provider source pin mismatch")
    if opened.get("receipt_source_sha256") != receipt_sha256 or _sha(Path(opened["receipt_source_path"]).read_bytes()) != receipt_sha256:
        raise ValueError("receipt source pin mismatch")
    if _sha(Path(opened["provider_source_path"]).read_bytes()) != provider_sha256 or _sha(Path(opened["lock_source_path"]).read_bytes()) != lock_sha256:
        raise ValueError("provider source changed")
    grant = Path(opened["grant_path"])
    grant_raw = Path(opened["grant_copy_path"]).read_bytes()
    if _sha(grant_raw) != opened["grant_sha256"] or grant.name != opened["grant_id"] + ".grant":
        raise ValueError("grant identity changed")
    fields = _grant_fields(grant_raw)
    regions = opened.get("regions")
    if not isinstance(regions, list) or not regions or any(r not in ("q0", "q1", "q2", "q3") for r in regions):
        raise ValueError("invalid provider regions")
    proof = opened.get("flock_proof")
    if (not isinstance(proof, list) or len(proof) != len(regions)
            or {p.get("region") for p in proof if isinstance(p, dict)} != set(regions)):
        raise ValueError("incomplete provider flock witness")
    for item in proof:
        expected_path = str((Path(expected_lock_root) / f"cpu_region.GLOBAL.{item['region']}.lock").resolve())
        if item.get("path") != expected_path:
            raise ValueError("flock witness path differs from lock root")
        parts = item.get("proc_locks_row", "").split()
        try:
            major, minor, inode = parts[5].split(":")
            identity = (int(major, 16), int(minor, 16), int(inode))
            recorded = (item["device_major"], item["device_minor"], item["inode"])
            if (len(parts) < 8 or parts[1:4] != ["FLOCK", "ADVISORY", "WRITE"]
                    or int(parts[4]) != opened["provider_pid"] or identity != recorded):
                raise ValueError("flock witness contents disagree")
        except (ValueError, IndexError, KeyError, TypeError) as exc:
            raise ValueError("invalid provider flock witness") from exc
    expected = {cpu for name in regions for cpu in range(int(name[1:]) * 24, (int(name[1:]) + 1) * 24)}
    if _cpu_set(opened["cpu_list"]) != expected:
        raise ValueError("provider regions differ from full-quarter CPUs")
    if (_cpu_set(fields["regions"]) != _cpu_set(opened["cpu_list"])
            or fields["start"] != opened["grant_start"] or fields["end"] != opened["grant_end"]):
        raise ValueError("grant scope changed")
    if not _time(fields["start"]) <= _time(opened["opened_utc"]) < _time(fields["end"]):
        raise ValueError("claim opened outside grant")
    if _time(closed["closed_utc"]) < _time(opened["opened_utc"]):
        raise ValueError("claim close precedes open")
    return opened, closed
