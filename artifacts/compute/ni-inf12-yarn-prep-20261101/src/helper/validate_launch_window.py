#!/usr/bin/env python3
"""Resolve only a manifest-bound owner booking; never choose a window locally."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]

def refuse(reason: str) -> None:
    print(f"REFUSED_UNREADY: {reason}", file=sys.stderr)
    raise SystemExit(70)

def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def sha(path: Path) -> str:
    return digest_bytes(path.read_bytes())

def canonical_digest(value: dict) -> str:
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())

def cpu_set(value):
    if isinstance(value, list) and all(type(item) is int and item >= 0 for item in value):
        return sorted(set(value))
    if not isinstance(value, str) or not value:
        return None
    result = set()
    try:
        for part in value.split(","):
            ends = [int(x) for x in part.split("-")]
            if len(ends) == 1:
                result.add(ends[0])
            elif len(ends) == 2 and ends[0] <= ends[1]:
                result.update(range(ends[0], ends[1] + 1))
            else:
                return None
    except ValueError:
        return None
    return sorted(result)

def main() -> int:
    manifest_value = os.environ.get("WS58_MANIFEST_PATH", "")
    if not manifest_value:
        refuse("keeper accepted manifest is absent")
    manifest_path = Path(manifest_value)
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError):
        refuse("keeper accepted manifest is unreadable")
    request_path = HERE / "qualification/request_manifest.json"
    recipe_path = HERE / "qualification/production_recipe.json"
    fixture_path = HERE / "qualification/qual_fixture.json"
    source_path = HERE / "SOURCE.sha256"
    expected_request_sha, expected_recipe_sha, expected_fixture_sha, source_sha = map(
        sha, (request_path, recipe_path, fixture_path, source_path))
    engine = manifest.get("engine", {})
    source = manifest.get("source_manifest", {})
    if (manifest.get("id") != "codex-ni-yarn-e1-mem-phase-r2-20261101" or
            manifest.get("request_manifest_sha256") != expected_request_sha or
            manifest.get("production_recipe", {}).get("sha256") != expected_recipe_sha or
            manifest.get("production_recipe", {}).get("path") != str(recipe_path) or
            manifest.get("qual_fixture", {}).get("sha256") != expected_fixture_sha or
            source.get("sha256") != source_sha or
            not isinstance(engine.get("path"), str) or
            not isinstance(engine.get("sha256"), str)):
        refuse("accepted manifest identity or source/request/recipe/fixture/engine pins differ from this packet")
    window_s, min_window_s = manifest.get("window_s"), manifest.get("min_window_s")
    if (type(window_s) is not int or type(min_window_s) is not int or
            window_s <= 0 or min_window_s <= 0 or window_s % 60 or min_window_s % 60 or
            window_s < min_window_s + 300):
        refuse("accepted manifest window/min_window are absent or malformed")
    booking = manifest.get("qualification", {}).get("booking", {})
    if (booking.get("mode") != "owner-booked-long-native" or
            type(booking.get("requested_max_wall_s")) is not int or
            booking["requested_max_wall_s"] <= 600 or
            type(booking.get("cleanup_reserve_s")) is not int or
            booking["cleanup_reserve_s"] <= 0):
        refuse("owner-booked-long-native READY booking is absent or malformed")
    record_pin = booking.get("record", {})
    if not isinstance(record_pin, dict) or not record_pin.get("path") or not record_pin.get("sha256"):
        refuse("owner booking record pin is missing")
    record_path = Path(record_pin["path"])
    if record_path.name != f"{manifest['id']}.json" or record_path.parent.name != "qual-bookings":
        refuse("owner booking record path is outside the canonical qual-bookings/<id>.json location")
    try:
        if sha(record_path) != record_pin["sha256"]:
            refuse("owner booking record digest mismatch")
        record = json.loads(record_path.read_text())
    except (OSError, ValueError):
        refuse("owner booking record is unreadable")
    request = json.loads(request_path.read_text())
    recipe = json.loads(recipe_path.read_text())
    fixture = json.loads(fixture_path.read_text())
    manifest_without_booking = dict(manifest)
    manifest_without_booking["qualification"] = dict(manifest.get("qualification", {}))
    manifest_without_booking["qualification"].pop("booking", None)
    target = {key: recipe[key] for key in ("images", "model", "request", "qualification_work_unit")}
    pins = record.get("pins", {})
    limits = record.get("limits", {})
    resource = record.get("resource", {})
    start, end = record.get("start_utc"), record.get("end_utc")
    try:
        start_dt = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = dt.datetime.fromisoformat(end.replace("Z", "+00:00"))
        times_ok = start.endswith("Z") and end.endswith("Z") and end_dt > start_dt
    except (AttributeError, ValueError):
        times_ok = False
    required_pin_values = {
        "manifest_binding_sha256": canonical_digest(manifest_without_booking),
        "source_manifest_sha256": source_sha,
        "production_recipe_sha256": expected_recipe_sha,
        "engine_sha256": engine["sha256"],
        "qual_fixture_sha256": expected_fixture_sha,
        "request_manifest_sha256": expected_request_sha,
        "prompt_tokens_required": request["request_max"]["prompt_tokens_required"],
        "window_s": window_s,
        "min_window_s": min_window_s,
        "recipe_target_sha256": canonical_digest(target),
    }
    required_limits = {
        "max_wall_s": booking["requested_max_wall_s"],
        "cleanup_reserve_s": booking["cleanup_reserve_s"],
        "disk_floor_gib": 150,
    }
    if (record.get("kind") != "epyc.qual.booking.v1" or record.get("state") != "BOOKED" or
            record.get("id") != manifest["id"] or not record.get("owner") or
            not record.get("calendar_ref") or
            not all(type(record.get("issuer", {}).get(k)) is int and record["issuer"][k] > 0
                    for k in ("pid", "birth_ticks")) or not times_ok or
            resource.get("class") != "gpu-quiet" or resource.get("gpu") != "mi210_0" or
            resource.get("gpu_quiet_exclusive") is not True or not resource.get("cpus") or
            cpu_set(resource.get("cpus")) is None or
            not resource.get("physical_family") or
            any(pins.get(k) != value for k, value in required_pin_values.items()) or
            any(limits.get(k) != value for k, value in required_limits.items()) or
            type(limits.get("max_rss_gib")) not in (int, float) or limits["max_rss_gib"] <= 0 or
            type(limits.get("max_output_gib")) not in (int, float) or limits["max_output_gib"] <= 0 or
            window_s < booking["requested_max_wall_s"] + booking["cleanup_reserve_s"]):
        refuse("owner booking record identity, resource, limits or pins do not match the accepted manifest")
    print(min_window_s)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
