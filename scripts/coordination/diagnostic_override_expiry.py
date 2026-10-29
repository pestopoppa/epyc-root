"""Read diagnostic TTL records for owner routing and hub health; never restore them."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def snapshot(record_dir: Path, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    result = {"schema": "epyc.diagnostic_override_expiry.v1", "checked_at": now.isoformat(),
              "record_dir": str(record_dir), "expired": [], "errors": []}
    try:
        paths = sorted(record_dir.iterdir())
    except FileNotFoundError:
        paths = []  # A diagnostic experiment has not created this directory yet.
    except OSError as exc:
        result["errors"].append(f"cannot read diagnostic override records: {exc}")
        paths = []
    for path in paths:
        if path.suffix != ".json":
            continue
        try:
            record = json.loads(path.read_text())
            if not isinstance(record, dict) or record.get("schema") != "epyc.env_override.v1":
                raise ValueError("invalid diagnostic override schema")
            component = record["component"]
            if not isinstance(component, str) or component != path.stem:
                raise ValueError("component does not match its record filename")
            expires_at = record["expires_at"]
            if not isinstance(expires_at, str):
                raise ValueError("expiry is not a timestamp")
            expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires.tzinfo is None:
                raise ValueError("expiry has no timezone")
            if now < expires:
                continue
            identity = json.dumps({key: record.get(key) for key in
                                   ("component", "applied_at", "expires_at", "pids", "owner")},
                                  sort_keys=True, separators=(",", ":"))
            result["expired"].append({
                "component": component, "owner": record.get("owner"),
                "expires_at": record["expires_at"], "record_path": str(path),
                "restore_command": record.get("restore") or f"orchestrator_stack.py reload {component}",
                "corr_id": "diagnostic-override-expired-" + hashlib.sha256(identity.encode()).hexdigest(),
            })
        except (OSError, ValueError, TypeError, KeyError) as exc:
            result["errors"].append(f"{path.name}: {exc}")
    result["status"] = "degraded" if result["expired"] or result["errors"] else "ok"
    return result
