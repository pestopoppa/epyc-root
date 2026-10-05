"""Per-worker durable configuration attestation for the API fleet."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from src.features import Features, feature_sources


def attestation_dir() -> Path:
    try:
        from src.config import get_config

        root = get_config().paths.tmp_dir
    except Exception:
        root = Path("/mnt/raid0/llm/tmp")
    return Path(root) / "orchestrator_config_attest"


def attestation_payload(current: Features) -> dict[str, Any]:
    return {
        "pid": os.getpid(),
        "flags": current.summary(),
        "sources": feature_sources(),
    }


def publish_config_attestation(current: Features) -> Path:
    """Atomically publish this worker's effective feature configuration."""
    payload = attestation_payload(current)
    destination = attestation_dir() / f"{payload['pid']}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(destination)
    finally:
        tmp.unlink(missing_ok=True)
    return destination


def remove_config_attestation(pid: int | None = None) -> None:
    (attestation_dir() / f"{pid or os.getpid()}.json").unlink(missing_ok=True)


def read_config_attestations(pids: list[int]) -> dict[int, dict[str, Any]]:
    """Read exactly the requested live-worker attestations."""
    result: dict[int, dict[str, Any]] = {}
    for pid in pids:
        path = attestation_dir() / f"{pid}.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
        if isinstance(payload, dict) and payload.get("pid") == pid:
            result[pid] = payload
    return result
