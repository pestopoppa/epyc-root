#!/usr/bin/env python3
"""Scratch filing-time selector. Not qualification or cryptographic authority.

Native formats: rowflow.write_grant and filler launcher rc/time/reason first line.
COMPLETE binding fields are prospective requirements, not retrofitted run facts.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def aware(value: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d(?:\.\d+)?)?(?:Z|[+-]\d\d:\d\d)", value):
        raise ValueError("timestamp must be ISO with an explicit timezone")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc


def unique(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError("duplicate key: " + key)
        fields[key] = value
    return fields


def regular(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected regular non-symlink file")
    return path.read_text()


def kv_line(path: Path) -> dict[str, str]:
    raw = regular(path)
    if len(raw.splitlines()) != 1:
        raise ValueError("grant must contain one line")
    pairs = []
    for token in raw.split():
        if not re.fullmatch(r"[a-z_]+=[^\s=]+", token):
            raise ValueError("malformed grant token")
        pairs.append(token.split("=", 1))
    fields = unique(pairs)
    if not {"start", "end", "regions", "holds"}.issubset(fields):
        raise ValueError("grant missing rowflow fields")
    if set(fields) - {"start", "end", "regions", "holds", "cpus"}:
        raise ValueError("unknown grant fields")
    return fields


def receipt_fields(path: Path) -> dict[str, str]:
    lines = regular(path).splitlines()
    if not lines:
        raise ValueError("empty ended receipt")
    match = re.fullmatch(r"rc=(0|[1-9]\d*) time=(\S+) reason=(.+)", lines[0])
    if not match:
        raise ValueError("ended receipt missing rc/time/reason")
    pairs = list(zip(("rc", "time", "reason"), match.groups()))
    # Native appended metadata is key=value per line. Never let it override header.
    for line in lines[1:]:
        if not re.fullmatch(r"[a-z_]+=[^\n]+", line):
            raise ValueError("malformed ended metadata")
        pairs.append(line.split("=", 1))
    return unique(pairs)


def run_time(name: str) -> datetime:
    if not re.fullmatch(r"\d{8}T\d{6}Z", name):
        raise ValueError("run directory must be canonical UTC")
    return datetime.strptime(name, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def select_run(root: Path, complete_path: Path, grant_path: Path, ended_path: Path) -> Path:
    root = root.resolve()
    complete = json.loads(regular(complete_path), object_pairs_hook=unique)
    if not isinstance(complete, dict):
        raise ValueError("COMPLETE must be an object")
    if grant_path.suffix != ".grant" or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", grant_path.stem):
        raise ValueError("invalid grant filename")
    grant_id = grant_path.stem
    grant = kv_line(grant_path)
    receipt = receipt_fields(ended_path)
    if ended_path.name != grant_id + ".ended" or ended_path.parent.resolve() != grant_path.parent.resolve():
        raise ValueError("ended receipt id/location does not match grant")
    if receipt["rc"] != "0":
        raise ValueError("ended receipt is not successful")
    if "job_id" in receipt and receipt["job_id"] != grant_id:
        raise ValueError("ended job_id mismatch")
    if complete.get("grant_id") != grant_id:
        raise ValueError("COMPLETE grant_id mismatch")
    if complete.get("grant_sha256") != hashlib.sha256(grant_path.read_bytes()).hexdigest():
        raise ValueError("COMPLETE grant digest mismatch")
    start, end = aware(grant["start"]), aware(grant["end"])
    if start >= end:
        raise ValueError("invalid grant window")
    if aware(complete.get("grant_start")) != start or aware(complete.get("grant_end")) != end:
        raise ValueError("COMPLETE grant window mismatch")
    ended = aware(receipt["time"])
    if not start <= ended <= end:
        raise ValueError("ended receipt outside grant window")
    pointer = complete.get("run")
    if not isinstance(pointer, str) or not Path(pointer).is_absolute():
        raise ValueError("COMPLETE needs an absolute run pointer")
    raw_run = Path(pointer)
    run = raw_run.resolve()
    runs_root = (root / "out/runs").resolve()
    if raw_run.is_symlink() or run.parent != runs_root or not run.is_dir():
        raise ValueError("run must be a direct existing child of out/runs")
    if not start <= run_time(run.name) <= ended:
        raise ValueError("run timestamp outside grant/completion window")
    candidates = []
    for path in runs_root.iterdir():
        if path.is_symlink() or not path.is_dir():
            continue
        try:
            stamp = run_time(path.name)
        except ValueError:
            continue
        if start <= stamp <= end:
            candidates.append(path.resolve())
    if candidates != [run] or not (run / "calls.jsonl").is_file():
        raise ValueError("grant window does not identify exactly the COMPLETE run")
    return run
