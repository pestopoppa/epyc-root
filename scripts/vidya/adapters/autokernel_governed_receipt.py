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
import re
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_governed_receipt/v1"
LIVE_SCHEMA = "epyc.autokernel.live_control_beliefs.v1"
REPLAY_SCHEMA = "epyc.autokernel.async_prefetch_replay.v1"
SOURCE_SCHEMAS = frozenset({LIVE_SCHEMA, REPLAY_SCHEMA})
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
    if receipt["schema"] == LIVE_SCHEMA:
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
        protocol_id=_text(measurement.get("protocol_id"), "measurement.protocol_id"),
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
