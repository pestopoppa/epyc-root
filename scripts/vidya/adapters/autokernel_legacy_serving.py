"""Direct serving observations; no protocol, eligibility, or placement warrant.

Only prospective producer captures are admitted. The native comparison is reopened
and rederived, including original vectors, input identity and CPU dependency bytes.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_legacy_serving/v1"
RECEIPT_SCHEMA = "epyc.vidya.legacy_serving_receipt.v1"
_CAPTURE = "epyc.vidya.legacy_serving_capture.v1"
_MAX_BYTES = 64 << 20


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def _source(receipt, locator):
    if set(receipt) != {"schema", "capture_id", "capture_sha256", "native_reference"}:
        raise ProjectionError("legacy serving receipt fields differ")
    ident = receipt["capture_id"]
    if not isinstance(ident, str) or not re.fullmatch("[0-9a-f]{64}", ident):
        raise ProjectionError("legacy serving capture ID is malformed")
    ref = receipt["native_reference"]
    if (not isinstance(ref, dict) or set(ref) != {"path", "sha256", "size"}
            or ref["path"] != f"sources/{ident}.json"
            or type(ref["size"]) is not int or not 0 < ref["size"] <= _MAX_BYTES):
        raise ProjectionError("legacy serving source reference differs")
    if not locator.startswith("autokernel:"):
        raise ProjectionError("legacy serving receipt needs its original file locator")
    directory = Path(locator.removeprefix("autokernel:")).parent
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    root_fd = os.open(directory, flags | os.O_DIRECTORY)
    try:
        sources_fd = os.open("sources", flags | os.O_DIRECTORY, dir_fd=root_fd)
        try:
            fd = os.open(f"{ident}.json", flags, dir_fd=sources_fd)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_size != ref["size"]:
                    raise ProjectionError("legacy serving source is not the original bounded file")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    raw = stream.read(_MAX_BYTES + 1)
                after = os.fstat(fd)
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise ProjectionError("legacy serving source changed during read")
            finally:
                os.close(fd)
        finally:
            os.close(sources_fd)
    finally:
        os.close(root_fd)
    if len(raw) != ref["size"] or hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ProjectionError("legacy serving source digest differs")
    return json.loads(raw)


def _rows(source, receipt):
    if not isinstance(source, dict) or not isinstance(source.get("comparison"), dict):
        raise ProjectionError("legacy serving native comparison is not an object")
    comparison = source["comparison"]
    capture = comparison["belief_capture"]
    if (not isinstance(capture, dict)
            or set(capture) != {"schema", "inputs", "capture_id", "native_sha256", "belief_measurements", "capture_sha256"}
            or capture["schema"] != _CAPTURE
            or capture["capture_sha256"] != receipt["capture_sha256"]
            or _digest({key: value for key, value in capture.items() if key != "capture_sha256"}) != capture["capture_sha256"]):
        raise ProjectionError("legacy serving prospective capture differs")
    inputs = capture["inputs"]
    if (set(inputs) != {"producer", "issued_at", "recipe", "pairs", "resolved_arms", "build_paths", "requests",
                       "protocol_id", "loaded_instrument_attestation"}
            or inputs["producer"] != "autokernel.loop.serving_beliefs/v1"
            or inputs["protocol_id"] != ""
            or inputs["loaded_instrument_attestation"] != "not_recorded"):
        raise ProjectionError("legacy serving inputs imply unsupported authority")
    issued = datetime.fromisoformat(inputs["issued_at"])
    if issued.tzinfo is None:
        raise ProjectionError("legacy serving issue time lacks a timezone")
    native = {key: value for key, value in comparison.items()
              if key not in {"belief_capture", "surface", "baseline_scope"}}
    digest = _digest(native)
    if (native["schema"] != "epyc.autokernel.serving_ab.v1"
            or native["metric"] != "aggregate_tok_s"
            or inputs["recipe"]["metric"] != native["metric"]
            or _digest(inputs["recipe"]) != native["recipe_hash"]
            or native["np"] != inputs["recipe"]["np"]
            or capture["native_sha256"] != digest
            or capture["capture_id"] != receipt["capture_id"]
            or _digest({"native_sha256": digest, "inputs": inputs}) != capture["capture_id"]):
        raise ProjectionError("legacy serving native/input binding differs")
    pairs = inputs["pairs"]
    if type(pairs) is not int or not 1 <= pairs <= 64 or pairs != native["pairs"]:
        raise ProjectionError("legacy serving original launch count differs")
    if set(inputs["resolved_arms"]) != {"anchor", "candidate"}:
        raise ProjectionError("legacy serving original arm identity differs")
    if (not isinstance(inputs["build_paths"], dict) or set(inputs["build_paths"]) != {"anchor", "candidate"}
            or any(not isinstance(value, str) or not value for value in inputs["build_paths"].values())):
        raise ProjectionError("legacy serving supplied build paths are missing")
    for arm, resolved in inputs["resolved_arms"].items():
        if resolved is not None and (not isinstance(resolved, dict)
                                    or resolved.get("build_dir") != inputs["build_paths"][arm]):
            raise ProjectionError("legacy serving resolved/supplied build path differs")
    requests = inputs["requests"]
    if requests is not None:
        if (not isinstance(requests, list) or len(requests) != native["np"]
                or any(not isinstance(row, list) or len(row) != 2
                       or not isinstance(row[0], str) or not row[0]
                       or not isinstance(row[1], str) or not re.fullmatch("[0-9a-f]{64}", row[1]) for row in requests)
                or len({row[0] for row in requests}) != len(requests)):
            raise ProjectionError("legacy serving request rows differ")
        request_digest = hashlib.sha256(json.dumps(requests, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        if (native.get("request_digest") != request_digest
                or native.get("floor_request_digest") != (request_digest if native["noise_floor_pct"] is not None else None)):
            raise ProjectionError("legacy serving request/floor identity differs")
    rows = []
    for arm, category in (("anchor", "BASELINE"), ("candidate", "CANDIDATE")):
        samples, windows = native[f"{arm}_samples"], native[f"{arm}_residency"]
        resolved = inputs["resolved_arms"][arm]
        if (len(samples) != pairs or len(windows) != pairs
                or any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in samples)
                or median(samples) != native[f"{arm}_tok_s"]):
            raise ProjectionError("legacy serving original process vectors do not rederive")
        if any(not math.isfinite(row["window_end"]) or row["window_end"] < row["window_start"]
               for row in windows):
            raise ProjectionError("legacy serving observation window differs")
        date = datetime.fromtimestamp(max(row["window_end"] for row in windows), timezone.utc).isoformat()
        rows.append({"measurement_id": f"legacy-serving:{capture['capture_id']}:{arm}",
                     "metric": native["metric"], "value": native[f"{arm}_tok_s"],
                     "unit": "t/s", "metric_direction": "higher_better", "category": category,
                     "claim": f"{arm} observed median aggregate serving rate; protocol and scientific witnesses unqualified",
                     "date": date, "protocol_id": "", "reps": pairs,
                     "reps_basis": "scored:original independent server launches; not threads/prompts/affinity samples",
                     "extra": {"arm": arm, "capture_id": capture["capture_id"],
                               "native_sha256": digest,
                               "build_path": inputs["build_paths"][arm],
                               "recipe_hash": native["recipe_hash"],
                               "request_digest": native.get("request_digest"),
                               "resolved_snapshot_digest": None if resolved is None else resolved.get("snapshot_digest"),
                               "execution_digest": None if resolved is None else resolved.get("execution_digest"),
                               "model_path": inputs["recipe"]["model"],
                               "applicability": "direct_serving_observation_only",
                               "cpu_facts": "dependency_only_not_placement_or_contention_proof"}})
    if rows != capture["belief_measurements"]:
        raise ProjectionError("legacy serving belief rows differ from original observations")
    return rows


def native_rows(receipt, *, receipt_locator, receipt_sha256, attestation_present=True):
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        return []
    try:
        source = _source(receipt, receipt_locator)
        rows = _rows(source, receipt)
    except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise ProjectionError(f"legacy serving source refused: {exc}") from exc
    return [{"receipt": receipt, "receipt_locator": receipt_locator,
             "receipt_sha256": receipt_sha256, "attestation_present": attestation_present,
             "claim": row} for row in rows]


@register("autokernel-legacy-serving")
def project(native):
    rows = native_rows(native["receipt"], receipt_locator=native["receipt_locator"],
                       receipt_sha256=native["receipt_sha256"],
                       attestation_present=native["attestation_present"])
    if native not in rows:
        raise ProjectionError("legacy serving projected row differs")
    return ClaimTuple(**native["claim"], source_kind="autokernel-legacy-serving",
                      attestation_locator=native["receipt_locator"],
                      attestation_sha256=native["receipt_sha256"],
                      attestation_present=native["attestation_present"])
