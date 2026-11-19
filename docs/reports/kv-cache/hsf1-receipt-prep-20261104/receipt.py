"""Small, offline-safe HSF-1 launch receipt writer.

Integration point: orchestrator_stack.start_server, around its existing Popen,
health gate, and existing first-token log observation. All expensive custody
(hash GGUF, server binary, and kernel-store files; fincore) is acquired before a
GPU grant and supplied to this module. This module never opens model/binary
files or starts a process.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc(ts: datetime) -> str:
    if ts.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _aware(ts: datetime, name: str) -> None:
    if not isinstance(ts, datetime) or ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _safe_role(role: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", role):
        raise ValueError("role must be a filename-safe identifier")
    return role


def build_receipt(*, role: str, model_id: str, device_id: str,
                  started_at: datetime, load_model_at: datetime | None,
                  loaded_at: datetime | None, healthy_at: datetime | None,
                  first_token_at: datetime | None, argv: list[str],
                  server_sha256: str, kernel_store_sha256: str,
                  gguf_sha256: str, fincore_resident_bytes: int | None,
                  fincore_file_bytes: int | None, outcome: str,
                  error_class: str | None = None) -> dict[str, Any]:
    """Build a receipt from already captured events and pre-grant custody."""
    if outcome not in {"healthy_first_token", "healthy_no_first_token", "health_failed", "spawn_failed"}:
        raise ValueError("unrecognized outcome")
    if not isinstance(model_id, str) or not model_id.strip() or not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("model_id and device_id must be nonempty strings")
    _aware(started_at, "started_at")
    for name, digest in (("server", server_sha256), ("kernel_store", kernel_store_sha256), ("gguf", gguf_sha256)):
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{name} digest must be a lowercase SHA-256")
    if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) for arg in argv):
        raise ValueError("argv must be a nonempty list of strings")
    # Hash the effective argv before discarding it. Never persist argument text:
    # secrets may be embedded in free-form headers or values of innocuous flags.
    argv_sha256 = hashlib.sha256(json.dumps(argv, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if (fincore_resident_bytes is None) != (fincore_file_bytes is None):
        raise ValueError("fincore resident/file byte counts must both be known or both be null")
    if fincore_file_bytes is not None:
        if (isinstance(fincore_resident_bytes, bool) or isinstance(fincore_file_bytes, bool)
                or not isinstance(fincore_resident_bytes, int) or not isinstance(fincore_file_bytes, int)
                or fincore_file_bytes <= 0 or fincore_resident_bytes < 0
                or fincore_resident_bytes > fincore_file_bytes):
            raise ValueError("invalid fincore byte counts")
        page_cache_fraction = fincore_resident_bytes / fincore_file_bytes
    else:
        page_cache_fraction = None
    timestamps = {
        "process_start": started_at, "load_model": load_model_at,
        "model_loaded": loaded_at, "healthy": healthy_at,
        "first_token": first_token_at,
    }
    for name, ts in timestamps.items():
        if ts is not None:
            _aware(ts, name)
    ordered = [(k, v) for k, v in timestamps.items() if v is not None]
    for (left_name, left), (right_name, right) in zip(ordered, ordered[1:]):
        if right.astimezone(timezone.utc) < left.astimezone(timezone.utc):
            raise ValueError(f"non-monotone phase timestamps: {left_name} then {right_name}")
    if loaded_at is not None and load_model_at is None:
        raise ValueError("model_loaded requires a load_model event")
    if healthy_at is not None and loaded_at is None:
        raise ValueError("healthy requires a model_loaded event")
    if first_token_at is not None and healthy_at is None:
        raise ValueError("first_token requires a healthy event")
    if outcome == "healthy_first_token" and any(t is None for t in (load_model_at, loaded_at, healthy_at, first_token_at)):
        raise ValueError("healthy_first_token requires all launch phases")
    if outcome == "healthy_no_first_token" and any(t is None for t in (load_model_at, loaded_at, healthy_at)):
        raise ValueError("healthy_no_first_token requires load, loaded, and healthy phases")
    if outcome == "healthy_no_first_token" and first_token_at is not None:
        raise ValueError("healthy_no_first_token cannot have a first-token event")
    if outcome == "health_failed" and healthy_at is not None:
        raise ValueError("health_failed cannot have a healthy event")
    if outcome in {"health_failed", "spawn_failed"} and error_class is None:
        raise ValueError(f"{outcome} requires error_class")
    if outcome in {"healthy_first_token", "healthy_no_first_token"} and error_class is not None:
        raise ValueError("successful outcomes cannot have error_class")
    if outcome == "spawn_failed" and any(t is not None for t in (load_model_at, loaded_at, healthy_at, first_token_at)):
        raise ValueError("spawn_failed cannot have post-spawn phase events")
    return {
        "schema": "epyc.hsf1.launch-phase.v1",
        "role": _safe_role(role), "model_id": model_id, "device_id": device_id,
        "timestamps_utc": {k: _utc(v) if v else None for k, v in timestamps.items()},
        "durations_s": {
            "start_to_load_model": (load_model_at - started_at).total_seconds() if load_model_at else None,
            "start_to_loaded": (loaded_at - started_at).total_seconds() if loaded_at else None,
            "start_to_healthy": (healthy_at - started_at).total_seconds() if healthy_at else None,
            "start_to_first_token": (first_token_at - started_at).total_seconds() if first_token_at else None,
        },
        "argv": None, "argv_redacted": True, "argv_sha256": argv_sha256,
        "custody_sha256": {"server": server_sha256, "kernel_store": kernel_store_sha256, "gguf": gguf_sha256},
        "fincore_before_exec": {
            "resident_bytes": fincore_resident_bytes,
            "file_bytes": fincore_file_bytes,
            "page_cache_fraction": page_cache_fraction,
        },
        "cache_class": "hot" if page_cache_fraction is not None and page_cache_fraction >= 0.99 else ("unknown" if page_cache_fraction is None else "cold_or_partial"),
        "outcome": outcome, "error_class": error_class,
    }


def write_receipt(directory: Path, receipt: dict[str, Any]) -> Path:
    """Atomically create one immutable role/UTC-named receipt; never overwrite."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = receipt["timestamps_utc"]["process_start"].replace(":", "").replace("-", "")
    target = directory / f"{_safe_role(receipt['role'])}-{stamp}.json"
    if target.exists():
        raise FileExistsError(target)
    fd, temporary = tempfile.mkstemp(prefix=".hsf1-", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return target
