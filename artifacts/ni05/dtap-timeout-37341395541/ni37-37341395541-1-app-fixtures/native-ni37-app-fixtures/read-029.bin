"""Project prospective AutoKernel live-control and governed-replay receipts.

Only producer-written ``belief_measurements`` are eligible.  The hardened
instrument smoke and async-prefetch replay captured before this hook carry no
such vector and therefore yield no rows; this adapter never reconstructs them.
Every admitted row is independently re-derived from the native receipt before
projection into :class:`ClaimTuple`.  Grading remains exclusively in
``claim_tuple.grade()``.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_governed_receipt/v1"
LIVE_SCHEMA = "epyc.autokernel.live_control_beliefs.v1"
REPLAY_SCHEMA = "epyc.autokernel.async_prefetch_replay.v1"
DIRECT_GPU_SCHEMA = "epyc.autokernel.direct_gpu_control_beliefs.v1"
SOURCE_SCHEMAS = frozenset({LIVE_SCHEMA, REPLAY_SCHEMA, DIRECT_GPU_SCHEMA})
LIVE_PROTOCOL = "P-AK-SEARCH-1/v1"
LIVE_PRODUCER = "autokernel.execution.live_controls/v2"
LIVE_PRODUCER_PATH = "scripts/kernel_rnd/autokernel/execution/live_controls.py"
REPLAY_PRODUCER = "scripts.benchmark.run_autokernel_async_prefetch_replay/v2"
REPLAY_PRODUCER_PATH = "scripts/benchmark/run_autokernel_async_prefetch_replay.py"
LIVE_CONTROLS = (
    "positive", "neutral", "degraded_negative", "aa", "historical_win_replay")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{label} must be non-empty text")
    return value.strip()


def _mapping(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"{label} must be an object")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value):
        raise ProjectionError(f"{label} must be a finite number")
    return float(value)


def _receipt_self_hash(receipt: dict) -> None:
    logical = dict(receipt)
    stored = logical.pop("receipt_sha256", None)
    if _sha(stored, "receipt.receipt_sha256") != _canonical_sha256(logical):
        raise ProjectionError("receipt_sha256 does not bind the logical receipt")


def _row_self_hash(row: dict) -> None:
    unsigned = dict(row)
    stored = unsigned.pop("measurement_sha256", None)
    if _sha(stored, "measurement.measurement_sha256") != _canonical_sha256(unsigned):
        raise ProjectionError("measurement_sha256 does not bind its row")


def _producer(receipt: dict, *, expected_id: str, expected_path: str) -> str:
    producer = _mapping(receipt.get("producer"), "receipt.producer")
    if producer.get("producer_id") != expected_id or producer.get("path") != expected_path:
        raise ProjectionError("receipt names a different producer identity")
    return _sha(producer.get("sha256"), "receipt.producer.sha256")


def _validate_replay(receipt: dict, rows: list[dict]) -> None:
    _receipt_self_hash(receipt)
    producer_sha = _producer(
        receipt, expected_id=REPLAY_PRODUCER, expected_path=REPLAY_PRODUCER_PATH)
    if len(rows) != 1:
        raise ProjectionError("governed replay receipt must carry exactly one row")
    source = {
        "source_root": receipt.get("source_root"),
        "source_branch": receipt.get("source_branch"),
        "source_commit": receipt.get("source_commit"),
        "binary": receipt.get("binary"),
        "binary_sha256": receipt.get("binary_sha256"),
        "linkage_sha256": receipt.get("linkage_sha256"),
        "model": receipt.get("model"),
        "model_sha256": receipt.get("model_sha256"),
    }
    for key in ("source_root", "source_branch", "binary", "model"):
        _text(source[key], f"receipt.{key}")
    if not isinstance(source["source_commit"], str) \
            or not _COMMIT.fullmatch(source["source_commit"]):
        raise ProjectionError("receipt.source_commit must be a full commit")
    for key in ("binary_sha256", "linkage_sha256", "model_sha256"):
        _sha(source[key], f"receipt.{key}")
    source_sha = _canonical_sha256(source)
    if receipt.get("source_identity_sha256") != source_sha:
        raise ProjectionError("source_identity_sha256 does not bind replay identities")

    opened = _mapping(receipt.get("device_claim_open"), "device_claim_open")
    released = _mapping(receipt.get("device_claim_released"), "device_claim_released")
    for key in ("claim_id", "device_id", "acquired_at"):
        _text(opened.get(key), f"device_claim_open.{key}")
        if released.get(key) != opened[key]:
            raise ProjectionError(f"device claim {key} changed across release")
    _text(released.get("released_at"), "device_claim_released.released_at")
    claim_sha = _canonical_sha256({"opened": opened, "released": released})
    if receipt.get("claim_identity_sha256") != claim_sha:
        raise ProjectionError("claim_identity_sha256 does not bind device claims")

    result = _mapping(receipt.get("result"), "receipt.result")
    paired = result.get("paired_blocks")
    blocks = receipt.get("blocks")
    if isinstance(blocks, bool) or not isinstance(blocks, int) or blocks < 2 \
            or not isinstance(paired, list) or len(paired) != blocks:
        raise ProjectionError("replay result must retain every scored paired block")
    deltas = []
    for index, block in enumerate(paired):
        block = _mapping(block, f"paired_blocks[{index}]")
        if block.get("block") != index:
            raise ProjectionError("replay paired blocks must be contiguous")
        anchor = _finite(block.get("anchor"), f"paired_blocks[{index}].anchor")
        candidate = _finite(block.get("candidate"), f"paired_blocks[{index}].candidate")
        if anchor <= 0 or candidate <= 0:
            raise ProjectionError("replay throughput must be positive")
        delta = candidate / anchor - 1.0
        if _finite(block.get("relative_delta"), "relative_delta") != delta:
            raise ProjectionError("replay relative delta does not re-derive from arms")
        deltas.append(delta)
    median = statistics.median(deltas)
    floor = _finite(result.get("contribution_floor"), "result.contribution_floor")
    all_positive = all(value > 0 for value in deltas)
    verdict = "REPRODUCED_KNOWN_WIN" if all_positive and median > floor \
        else "NOT_REPRODUCED"
    if (_finite(result.get("median_relative_delta"), "result.median_relative_delta") != median
            or _finite(result.get("minimum_relative_delta"),
                       "result.minimum_relative_delta") != min(deltas)
            or result.get("all_blocks_positive") is not all_positive
            or result.get("verdict") != verdict):
        raise ProjectionError("replay native verdict does not re-derive from paired blocks")

    row = _mapping(rows[0], "belief_measurements[0]")
    _row_self_hash(row)
    if (row.get("measurement_id") != "async_prefetch_median_relative_delta"
            or row.get("metric")
            != "async_prefetch_paired_median_relative_throughput_delta"
            or _finite(row.get("value"), "measurement.value") != median
            or row.get("unit") != "fraction"
            or row.get("metric_direction") != "higher_better"
            or row.get("category") != "BASELINE"
            or row.get("protocol_id") != REPLAY_SCHEMA
            or row.get("reps") != blocks
            or row.get("reps_basis") != "scored:balanced paired replay blocks"
            or row.get("native_verdict") != verdict):
        raise ProjectionError("governed replay measurement fields do not re-derive")
    extra = _mapping(row.get("extra"), "measurement.extra")
    if (extra.get("source_identity") != source
            or extra.get("source_identity_sha256") != source_sha
            or extra.get("binary_sha256") != source["binary_sha256"]
            or extra.get("model_sha256") != source["model_sha256"]
            or extra.get("device_claim_id") != opened["claim_id"]
            or extra.get("claim_identity_sha256") != claim_sha
            or extra.get("producer_id") != REPLAY_PRODUCER
            or extra.get("producer_sha256") != producer_sha):
        raise ProjectionError("governed replay row identity bindings differ from receipt")
    evidence = {
        "paired_blocks": paired,
        "aggregation": "median(candidate_tokens_per_s/anchor_tokens_per_s-1)",
        "scored_blocks": blocks,
        "samples_per_arm_per_block": receipt["cell"]["repetitions"],
        "contribution_floor": floor,
        "all_blocks_positive": all_positive,
        "native_verdict": verdict,
        "orders": receipt.get("orders"),
        "order_seed": receipt.get("order_seed"),
        "source_identity_sha256": source_sha,
        "claim_identity_sha256": claim_sha,
        "producer_sha256": producer_sha,
    }
    if extra.get("evidence_basis") != evidence \
            or extra.get("evidence_sha256") != _canonical_sha256(evidence):
        raise ProjectionError("governed replay evidence digest does not bind its basis")


def _validate_live(receipt: dict, rows: list[dict]) -> None:
    _receipt_self_hash(receipt)
    producer_sha = _producer(
        receipt, expected_id=LIVE_PRODUCER, expected_path=LIVE_PRODUCER_PATH)
    if receipt.get("protocol_id") != LIVE_PROTOCOL:
        raise ProjectionError("live-control receipt names a different protocol")
    campaign_id = _text(receipt.get("campaign_id"), "receipt.campaign_id")
    source = _mapping(receipt.get("source_identity"), "source_identity")
    if set(source) != {
            "production_source_commit", "measurement_instrument_commit",
            "runtime_source_sha256"}:
        raise ProjectionError("live-control source identity has unexpected fields")
    if (not _COMMIT.fullmatch(str(source.get("production_source_commit", "")))
            or not _COMMIT.fullmatch(str(source.get("measurement_instrument_commit", "")))):
        raise ProjectionError("live-control source commits must be full commits")
    _sha(source.get("runtime_source_sha256"), "source.runtime_source_sha256")
    source_sha = _canonical_sha256(source)
    if receipt.get("source_identity_sha256") != source_sha:
        raise ProjectionError("live-control source identity digest differs")
    binary = _mapping(receipt.get("binary_identity"), "binary_identity")
    model = _mapping(receipt.get("model_identity"), "model_identity")
    _text(binary.get("path"), "binary_identity.path")
    _sha(binary.get("sha256"), "binary_identity.sha256")
    _sha(binary.get("linkage_sha256"), "binary_identity.linkage_sha256")
    if binary.get("copy_exact") is not True:
        raise ProjectionError("live-control evidence binary is not an exact copy")
    _text(model.get("path"), "model_identity.path")
    _sha(model.get("sha256"), "model_identity.sha256")
    claim = _mapping(receipt.get("resource_claim_identity"), "resource_claim_identity")
    if (claim.get("schema") != "epyc.autokernel.cpu_region_claim_receipt.v1"
            or claim.get("campaign_id") != campaign_id):
        raise ProjectionError("live-control CPU claim names a different campaign/schema")
    for key in ("claim_id", "cpu_list", "acquired_at", "released_at"):
        _text(claim.get(key), f"resource_claim_identity.{key}")
    claim_sha = _canonical_sha256(claim)
    if receipt.get("claim_identity_sha256") != claim_sha:
        raise ProjectionError("live-control claim identity digest differs")
    sweep_sha = _sha(receipt.get("control_sweep_sha256"), "control_sweep_sha256")
    raw = _mapping(receipt.get("raw_vector_sha256"), "raw_vector_sha256")
    if set(raw) != set(LIVE_CONTROLS):
        raise ProjectionError("live-control receipt does not bind exactly five raw controls")
    for control_id, digests in raw.items():
        digests = _mapping(digests, f"raw_vector_sha256.{control_id}")
        if not digests:
            raise ProjectionError("live-control raw digest set cannot be empty")
        for label, digest in digests.items():
            _text(label, "raw vector label")
            _sha(digest, f"raw_vector_sha256.{control_id}.{label}")
    expected_ids = {f"live_control_{control}_requirement_satisfied"
                    for control in LIVE_CONTROLS}
    if len(rows) != 5 or {row.get("measurement_id") for row in rows} != expected_ids:
        raise ProjectionError("live-control receipt must carry exactly five control rows")
    control_panel = _mapping(receipt.get("control_panel"), "control_panel")
    panel_outcomes = control_panel.get("outcomes")
    panel_observations = control_panel.get("observations")
    if not isinstance(panel_outcomes, list) or not isinstance(panel_observations, list):
        raise ProjectionError("live-control receipt lacks its native panel evidence")
    panel_outcomes_by_id = {
        row.get("control_id"): row for row in panel_outcomes if isinstance(row, dict)}
    panel_observations_by_id = {
        row.get("control_id"): row for row in panel_observations if isinstance(row, dict)}
    if set(panel_outcomes_by_id) != set(LIVE_CONTROLS) \
            or set(panel_observations_by_id) != set(LIVE_CONTROLS):
        raise ProjectionError("native panel does not cover exactly five controls")
    for row in rows:
        row = _mapping(row, "belief measurement")
        _row_self_hash(row)
        extra = _mapping(row.get("extra"), "measurement.extra")
        control_id = extra.get("control_id")
        if control_id not in LIVE_CONTROLS \
                or row.get("measurement_id") != f"live_control_{control_id}_requirement_satisfied":
            raise ProjectionError("live-control row id and control identity differ")
        evidence = _mapping(extra.get("evidence_basis"), "measurement.evidence_basis")
        outcome = _mapping(evidence.get("outcome"), "evidence_basis.outcome")
        observation = _mapping(evidence.get("observation"), "evidence_basis.observation")
        verdict = outcome.get("outcome")
        if (outcome.get("control_id") != control_id
                or observation.get("control_id") != control_id
                or outcome != panel_outcomes_by_id[control_id]
                or observation != panel_observations_by_id[control_id]
                or verdict not in {"PASS", "FAIL"}):
            raise ProjectionError("live-control native outcome does not bind its control")
        reps = observation.get("abs_effect_count")
        if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
            raise ProjectionError("live-control observation lacks scored blocks")
        expected_evidence = {
            "control_id": control_id,
            "outcome": outcome,
            "observation": observation,
            "raw_vector_sha256": raw[control_id],
            "control_sweep_sha256": sweep_sha,
            "source_identity_sha256": source_sha,
            "binary_sha256": binary["sha256"],
            "model_sha256": model["sha256"],
            "claim_identity_sha256": claim_sha,
            "producer_sha256": producer_sha,
        }
        if evidence != expected_evidence \
                or extra.get("evidence_sha256") != _canonical_sha256(expected_evidence):
            raise ProjectionError("live-control evidence digest does not bind its basis")
        expected_value = 1.0 if verdict == "PASS" else 0.0
        if (row.get("metric") != "autokernel_control_requirement_satisfaction"
                or _finite(row.get("value"), "measurement.value") != expected_value
                or row.get("unit") != "fraction"
                or row.get("metric_direction") != "higher_better"
                or row.get("category") != "BASELINE"
                or row.get("protocol_id") != LIVE_PROTOCOL
                or row.get("reps") != reps
                or row.get("reps_basis") != "scored:paired live-control blocks"
                or row.get("native_verdict") != verdict):
            raise ProjectionError("live-control row fields do not re-derive from native outcome")
        if (extra.get("source_identity") != source
                or extra.get("source_identity_sha256") != source_sha
                or extra.get("binary_identity") != binary
                or extra.get("model_identity") != model
                or extra.get("resource_claim_identity") != claim
                or extra.get("claim_identity_sha256") != claim_sha
                or extra.get("producer_id") != LIVE_PRODUCER
                or extra.get("producer_sha256") != producer_sha):
            raise ProjectionError("live-control row identities differ from receipt")
    native = _mapping(receipt.get("native_verdict"), "native_verdict")
    expected_native = {
        "marker": control_panel.get("marker"),
        "may_rank": control_panel.get("may_rank"),
        "halts_campaign": control_panel.get("halts_campaign"),
        "voids_window": control_panel.get("voids_window"),
    }
    if native != expected_native:
        raise ProjectionError("live-control native verdict differs from its panel result")


def _direct_gpu_sources(basis, locator):
    """Bounded exact native leaves, never launch/regrade or invent missing rows."""
    if not locator:
        raise ProjectionError("direct GPU control requires its original receipt locator")
    root = Path(locator.removeprefix("autokernel:")).parent
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    root_fd = os.open(root, flags | os.O_DIRECTORY)
    cache, remaining = {}, 64 * 1024 * 1024
    def read(reference, namespace):
        nonlocal remaining
        if (not isinstance(reference, dict) or set(reference) != {"locator", "sha256", "verified"}
                or type(reference["verified"]) is not bool):
            raise ProjectionError("direct GPU original artifact reference differs")
        name, digest = reference["locator"], _sha(reference["sha256"], "original SHA")
        prefix = hashlib.sha256(namespace.encode()).hexdigest() + "-"
        if (not isinstance(name, str) or not name.startswith(prefix)
                or "/" in name or len(name) > 256 or not name.endswith(".json")):
            raise ProjectionError("direct GPU original namespace or leaf differs")
        key = (name, digest)
        if key in cache:
            return cache[key]
        if len(cache) >= 16384:
            raise ProjectionError("direct GPU original reference capacity exceeded")
        fd = os.open(name, flags, dir_fd=root_fd)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > min(16 * 1024 * 1024, remaining):
                raise ProjectionError("direct GPU original file exceeds bounded metadata capacity")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(before.st_size + 1)
            after = os.fstat(fd)
            if any(getattr(before, field) != getattr(after, field) for field in (
                    "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")):
                raise ProjectionError("direct GPU original file changed during read")
        finally:
            os.close(fd)
        if len(raw) != before.st_size or hashlib.sha256(raw).hexdigest() != digest:
            raise ProjectionError("direct GPU original artifact digest differs")
        remaining -= len(raw)
        cache[key] = json.loads(raw)
        if name != prefix + _canonical_sha256(cache[key]) + ".json":
            raise ProjectionError("direct GPU original namespace/content binding differs")
        return cache[key]
    try:
        declaration = read(basis["declaration"], "direct-gpu-declaration")
        if (declaration.get("belief_capture_schema") != DIRECT_GPU_SCHEMA
                or declaration["fixture"]["frame"] != basis["frame"]
                or declaration["source"] != basis["source"]
                or declaration["holders"] != basis["held_components"]):
            raise ProjectionError("direct GPU prospective declaration differs")
        material = None if basis["material"] is None else read(basis["material"], "direct-gpu-material")
        checkpoint = None if basis["window"] is None else read(basis["window"], "direct-gpu-window-checkpoint")
        launches = [] if checkpoint is None else checkpoint["launches"]
        if basis["completed_launches"] != len(launches) or (material is not None and material["launches"] != launches):
            raise ProjectionError("direct GPU completed native membership differs")
        for entry in [*launches, *([] if checkpoint is None else checkpoint["invalid"])]:
            raw = read(entry["reference"], "direct-gpu-bench-launch")
            if raw["membership"] != entry["membership"]:
                raise ProjectionError("direct GPU original launch membership differs")
            for key in ("claim_open", "claim_close"):
                read(raw[key], "direct-gpu-held-observation")
            if material is not None and entry in launches:
                label, index, arm = entry["membership"]
                rows = json.loads(raw["stdout"])
                if (len(rows) != 1 or material["pairs"][label][index][arm + "_samples"] != [rows[0]["avg_ts"]]):
                    raise ProjectionError("direct GPU native process mean differs from original pair")
        if material is not None:
            t0 = read(material["t0"], "direct-gpu-t0")
            for ref in (*t0["anchor_captures"], *t0["candidate_captures"]):
                read(ref, "direct-gpu-t0-process")
            for arm in ("anchor", "candidate"):
                read(material["identities"][arm]["source"], "direct-gpu-source")
            for key in ("open", "close"):
                read(material["boundaries"][key], "direct-gpu-boundary")
        return declaration, material
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProjectionError(f"direct GPU original source cannot be reopened: {exc}") from exc
    finally:
        os.close(root_fd)


def _validate_direct_gpu(receipt, rows, locator):
    _receipt_self_hash(receipt)
    producer = "autokernel.loop.direct_gpu_control/v1"
    sha = _producer(receipt, expected_id=producer,
        expected_path="scripts/kernel_rnd/autokernel/loop/direct_gpu_control.py")
    basis = _mapping(receipt.get("native_basis"), "direct GPU native basis")
    declaration, material = _direct_gpu_sources(basis, locator)
    if receipt["campaign_id"] != declaration["control_campaign_id"] or sha != basis["source"]["self"]:
        raise ProjectionError("direct GPU original producer/campaign differs")
    ids = ("positive", "historical_win_replay")
    if len(rows) != 2 or set(basis["observations"]) != set(ids):
        raise ProjectionError("direct GPU supplier must preserve its two original observations")
    for control_id, row in zip(ids, rows):
        _row_self_hash(row)
        observation = basis["observations"][control_id]
        stages = basis["tier_evaluations"].get(control_id, [])
        if type(observation["ran"]) is not bool:
            raise ProjectionError("direct GPU ran must be an original boolean")
        if observation["ran"]:
            if (not stages or material is None or observation["verdict_status"] != stages[-1]["status"]
                    or observation["abs_effect_count"] != len(material["pairs"][control_id])):
                raise ProjectionError("direct GPU observation differs from original evaluator result")
        elif (observation["verdict_status"] is not None or observation["could_not_run_reason"] != basis["error"]
                or not basis["error"] or observation["abs_effect_count"] != 0):
            raise ProjectionError("unavailable GPU control cannot become a scientific failure")
        expected = {"control_id": control_id, "observation": observation, "basis": basis}
        extra = _mapping(row.get("extra"), "direct GPU row extra")
        if (extra.get("evidence_basis") != expected or extra.get("evidence_sha256") != _canonical_sha256(expected)
                or extra.get("producer_id") != producer or extra.get("producer_sha256") != sha
                or row.get("measurement_id") != "direct_gpu_" + control_id + "_ran"
                or row.get("metric") != "autokernel_control_execution_observed"
                or _finite(row.get("value"), "direct GPU value") != float(observation["ran"])
                or row.get("unit") != "fraction" or row.get("category") != "BASELINE"
                or row.get("metric_direction") != "higher_better" or row.get("protocol_id") != ""
                or row.get("reps") != (observation["abs_effect_count"] or None)
                or row.get("reps_basis") != "observed:original GPU control paired blocks"
                or row.get("native_verdict") != observation["verdict_status"]):
            raise ProjectionError("direct GPU producer row does not rederive as observation-only")


def native_rows(receipt: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return only producer-written future rows; pre-hook receipts yield none."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported AutoKernel governed receipt schema")
    if receipt_sha256:
        _sha(receipt_sha256, "receipt_sha256")
    measurements = receipt.get("belief_measurements")
    if measurements is None:
        return ()
    if not isinstance(measurements, list) or not measurements:
        raise ProjectionError("belief_measurements must be a non-empty list")
    if receipt.get("status") != "complete":
        raise ProjectionError("only a complete governed receipt may carry belief rows")
    if receipt["schema"] == DIRECT_GPU_SCHEMA:
        _validate_direct_gpu(receipt, measurements, receipt_locator)
    elif receipt["schema"] == LIVE_SCHEMA:
        _validate_live(receipt, measurements)
    else:
        _validate_replay(receipt, measurements)
    return tuple({
        "receipt": receipt, "measurement": row, "measurement_index": index,
        "receipt_locator": receipt_locator, "receipt_sha256": receipt_sha256,
        "attestation_present": attestation_present,
    } for index, row in enumerate(measurements))


@register("autokernel-governed-receipt-measurement")
def project(native: Any) -> ClaimTuple:
    """Project one already-validated row; the shared ladder alone grades it."""
    if not isinstance(native, dict):
        raise ProjectionError("AutoKernel governed native row must be a dict")
    receipt = _mapping(native.get("receipt"), "native.receipt")
    measurement = _mapping(native.get("measurement"), "native.measurement")
    schema = _text(receipt.get("schema"), "receipt.schema")
    if schema not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported AutoKernel governed receipt schema")
    campaign_id = _text(receipt.get("campaign_id"), "receipt.campaign_id")
    local_id = _text(measurement.get("measurement_id"), "measurement.measurement_id")
    identity = hashlib.sha256(json.dumps(
        [schema, campaign_id, local_id, native.get("measurement_index")],
        separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()[:24]
    extra = _mapping(measurement.get("extra"), "measurement.extra")
    return ClaimTuple(
        measurement_id=f"akgov_{identity}",
        metric=_text(measurement.get("metric"), "measurement.metric"),
        value=_finite(measurement.get("value"), "measurement.value"),
        date=str(receipt.get("ended_at") or receipt.get("created_at") or "")[:10],
        category=_text(measurement.get("category"), "measurement.category"),
        claim=_text(measurement.get("claim"), "measurement.claim"),
        metric_direction=_text(
            measurement.get("metric_direction"), "measurement.metric_direction"),
        protocol_id=("" if schema == DIRECT_GPU_SCHEMA and measurement.get("protocol_id") == ""
                     else _text(measurement.get("protocol_id"), "measurement.protocol_id")),
        reps=measurement.get("reps"),
        reps_basis=_text(measurement.get("reps_basis"), "measurement.reps_basis"),
        unit=_text(measurement.get("unit"), "measurement.unit"),
        attestation_sha256=str(native.get("receipt_sha256") or ""),
        attestation_locator=str(native.get("receipt_locator") or ""),
        attestation_present=native.get("attestation_present"),
        source_kind="autokernel-governed-receipt-measurement",
        extra={
            "source_schema": schema,
            "campaign_id": campaign_id,
            "native_measurement_id": local_id,
            "native_verdict": measurement.get("native_verdict"),
            "native_measurement_sha256": measurement.get("measurement_sha256"),
            "receipt_self_sha256": receipt.get("receipt_sha256"),
            **extra,
        },
    )
