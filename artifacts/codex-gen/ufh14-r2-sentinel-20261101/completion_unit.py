"""Write only complete, native two-leg A3a per-attempt result units."""
import hashlib
import json
import os
import math
import re
import sys
from pathlib import Path

REQUIRED_TIMINGS = ("cache_n", "prompt_n", "prompt_ms", "predicted_n", "predicted_ms")
LEGS = ("cold", "warm")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rowflow_unit(attempt: Path, row_id: str) -> Path:
    attempt = Path(attempt)
    legs = {}
    for name in LEGS:
        leg = attempt / name
        group_path = leg / "group" / "native-group.json"
        bindings_path = leg / "group" / "timing-bindings.json"
        wire_path = leg / "proxy-wire" / "wire.jsonl"
        bodies_path = leg / "proxy-wire" / "wire-bodies.jsonl.gz"
        cleanup_path = leg / "cleanup.json"
        if not all(p.is_file() for p in (group_path, bindings_path, wire_path, bodies_path, cleanup_path)):
            raise ValueError(f"{name} leg lacks completed native outputs")
        group = json.loads(group_path.read_text())
        bindings = json.loads(bindings_path.read_text())
        expected = group.get("warm_requests", []) + group.get("members", [])
        if not expected or len(bindings) != len(expected):
            raise ValueError(f"{name} leg request/binding count mismatch")
        for row in bindings:
            timings = row.get("timings")
            if not isinstance(timings, dict) or any(k not in timings for k in REQUIRED_TIMINGS):
                raise ValueError(f"{name} leg has incomplete native timing data")
            for key in REQUIRED_TIMINGS:
                value = timings[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f"{name} leg has invalid native timing {key}")
        cleanup = json.loads(cleanup_path.read_text())
        if cleanup.get("server_dead") is not True or cleanup.get("proxy_dead") is not True:
            raise ValueError(f"{name} leg cleanup is unverified")
        legs[name] = {
            "request_count": len(bindings),
            "timings": bindings,
            "native_group_sha256": _sha(group_path),
            "timing_bindings_sha256": _sha(bindings_path),
            "wire_sha256": _sha(wire_path),
            "wire_bodies_sha256": _sha(bodies_path),
            "cleanup": cleanup,
        }
    payload = {"schema": "epyc.ufh14.a3a.native_result.v1", "row_id": row_id,
               "complete": True, "legs": legs}
    target = attempt / "ROWFLOW-UNIT.json"
    tmp = attempt / f".ROWFLOW-UNIT.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    os.replace(tmp, target)
    return target


def publish_production_marker(root: Path, unit: Path, *, dry_run: bool) -> None:
    """Keep completion state separate from attempt results and never set it in dry-run."""
    if dry_run:
        return
    root = Path(root)
    target = root / "RUN_COMPLETE.json"
    tmp = root / f".RUN_COMPLETE.{os.getpid()}"
    tmp.write_text(str(unit) + "\n")
    os.replace(tmp, target)


def production_unit_is_current(root: Path, row_id: str) -> bool:
    """Accept completion only from this packet's current, content-bound native unit."""
    root = Path(root).resolve()
    marker = root / "RUN_COMPLETE.json"
    try:
        target = Path(marker.read_text().strip()).resolve(strict=True)
        if target.name != "ROWFLOW-UNIT.json" or target.parent.parent != root / "attempts":
            return False
        if not re.fullmatch(r"run\.[A-Za-z0-9]+", target.parent.name):
            return False
        payload = json.loads(target.read_text())
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    if (payload.get("schema") != "epyc.ufh14.a3a.native_result.v1" or
            payload.get("row_id") != row_id or payload.get("complete") is not True or
            set(payload.get("legs", {})) != set(LEGS)):
        return False
    for name in LEGS:
        leg = payload["legs"][name]
        base = target.parent / name
        paths = {
            "native_group_sha256": base / "group" / "native-group.json",
            "timing_bindings_sha256": base / "group" / "timing-bindings.json",
            "wire_sha256": base / "proxy-wire" / "wire.jsonl",
            "wire_bodies_sha256": base / "proxy-wire" / "wire-bodies.jsonl.gz",
        }
        try:
            if any(not path.is_file() or _sha(path) != leg.get(key) for key, path in paths.items()):
                return False
            group = json.loads(paths["native_group_sha256"].read_text())
            bindings = json.loads(paths["timing_bindings_sha256"].read_text())
            cleanup = json.loads((base / "cleanup.json").read_text())
        except (OSError, ValueError, json.JSONDecodeError):
            return False
        expected = group.get("warm_requests", []) + group.get("members", [])
        if (not expected or len(bindings) != len(expected) or
                leg.get("request_count") != len(bindings) or
                cleanup.get("server_dead") is not True or cleanup.get("proxy_dead") is not True):
            return False
        for row in bindings:
            timings = row.get("timings")
            if not isinstance(timings, dict) or any(k not in timings for k in REQUIRED_TIMINGS):
                return False
            for key in REQUIRED_TIMINGS:
                value = timings[key]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    return False
    return True


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "--check-production":
        raise SystemExit(64)
    raise SystemExit(0 if production_unit_is_current(Path(sys.argv[2]), sys.argv[3]) else 1)
