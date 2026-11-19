#!/usr/bin/env python3
"""Replay a retained CH-26 hostscope producer receipt through the strict verifier.

The input is an immutable producer manifest plus raw per-CPU mmap snapshots.
This adapter proves only receipt structure and internally reported continuity;
it does not upgrade the producer's host coverage, losslessness, placement,
contention, or DS41-floor claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from loss_coverage_verifier import verify


def adapt(manifest_path: Path, expected_cpus: set[int], expected_sha256: str | None = None) -> dict:
    manifest_path = manifest_path.resolve(strict=True)
    manifest_bytes = manifest_path.read_bytes()
    if expected_sha256 is not None and hashlib.sha256(manifest_bytes).hexdigest() != expected_sha256:
        raise ValueError("producer manifest digest mismatch")
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict):
        raise ValueError("producer manifest must be an object")
    if manifest.get("schema") != "epyc.ch26.hostscope-perf-evidence.v1":
        raise ValueError("unexpected producer receipt schema")
    if manifest.get("measurement_claim") != "none":
        raise ValueError("producer receipt carries a measurement claim")
    captures = manifest.get("captures")
    if not isinstance(captures, list) or len(captures) != len(expected_cpus):
        raise ValueError("capture inventory size differs from declared CPUs")

    sources, snapshots, terminal = [], [], []
    enable_bounds, disable_bounds = [], []
    seen = set()
    for capture in captures:
        if not isinstance(capture, dict):
            raise ValueError("capture row malformed")
        cpu = capture.get("cpu")
        if type(cpu) is not int or cpu not in expected_cpus or cpu in seen:
            raise ValueError("unexpected or duplicate CPU capture")
        seen.add(cpu)
        event_id = capture.get("event_id")
        tracepoint_id = capture.get("tracepoint_id")
        if type(event_id) is not int or event_id <= 0 or type(tracepoint_id) is not int or tracepoint_id <= 0:
            raise ValueError("event identity missing")
        raw_name = capture.get("raw_file")
        if not isinstance(raw_name, str) or Path(raw_name).name != raw_name:
            raise ValueError("unsafe raw ring path")
        raw = (manifest_path.parent / raw_name).read_bytes()
        if len(raw) != capture.get("raw_size") or hashlib.sha256(raw).hexdigest() != capture.get("raw_sha256"):
            raise ValueError("raw ring size or digest mismatch")
        if capture.get("data_size") != len(raw):
            raise ValueError("perf data_size differs from retained ring")

        counter = capture.get("counter")
        target = capture.get("target")
        if not isinstance(counter, dict) or not isinstance(target, dict):
            raise ValueError("counter or child identity missing")
        # Retain the producer's identity attributes in the source name and IDs;
        # this check does not independently authenticate the producer process.
        if (type(target.get("pid")) is not int or target["pid"] <= 0
                or type(target.get("start_ticks")) is not int or target["start_ticks"] <= 0):
            raise ValueError("owned-child identity missing")
        source = {"cpu": cpu, "name": "sched_switch", "event_id": event_id,
                  "tracepoint_id": tracepoint_id}
        ring = {"snapshot": raw, "head": capture.get("head"),
                "tail": capture.get("tail"), "errors": []}
        sources.append(source)
        snapshots.append({**source, "ring": ring})
        terminal.append({**source, "errors": [], "lost_samples": counter.get("lost_samples"),
                         "enable_after_ns": capture.get("enable_after_ns"),
                         "disable_before_ns": capture.get("disable_before_ns"),
                         "enabled_ns": counter.get("enabled_ns"),
                         "running_ns": counter.get("running_ns"), "count": counter.get("count"),
                         "ring": ring})
        enable_bounds.append(capture.get("enable_after_ns"))
        disable_bounds.append(capture.get("disable_before_ns"))
    if seen != expected_cpus or any(type(x) is not int for x in enable_bounds + disable_bounds):
        raise ValueError("CPU coverage or interval bounds malformed")
    start, end = max(enable_bounds), min(disable_bounds)
    if start >= end:
        raise ValueError("captures have no common conservative interval")
    return {"measurement_admission": "none", "errors": [],
            "producer_run_id": manifest.get("run_id"),
            "markers": [{"timestamp_ns": start}, {"timestamp_ns": end}],
            "source_provenance": sources, "snapshots": snapshots, "rings": terminal}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--cpus", required=True, help="explicit comma-separated CPU IDs")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_sha256 = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    if manifest_sha256 != args.manifest_sha256:
        raise ValueError("producer manifest digest mismatch")
    cpus = {int(x) for x in args.cpus.split(",") if x}
    document = adapt(args.manifest, cpus, expected_sha256=args.manifest_sha256)
    result = verify(document, expected_cpus=cpus,
                    expected_events=frozenset({"sched_switch"}))
    result["capture_overlap_ns"] = result.pop("request_window_ns")
    result.update({"producer_schema": "epyc.ch26.hostscope-perf-evidence.v1",
                   "producer_manifest_sha256": manifest_sha256,
                   "producer_run_id": document["producer_run_id"],
                   "measurement_admission": "none",
                   "limitations": result["limitations"] + [
                       "empty error arrays are adapter scaffolding, not producer error receipts",
                       "replay verifies only the retained receipt; it does not authenticate capture code or kernel",
                       "one historical diagnostic capture is not a full-host coverage or calibration sample"]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "refused", "measurement_admission": "none",
                          "reason": str(exc)}, sort_keys=True))
        raise SystemExit(2)
