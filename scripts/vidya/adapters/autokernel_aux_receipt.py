"""Project prospective AutoKernel auxiliary-receipt measurements into ClaimTuple.

The adapter reads only the producer-written ``belief_measurements`` vector. Older receipts yield no
rows: reconstructing tuples from their prose or profiler payload would invent write-time provenance.
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

ADAPTER_ID = "vidya.adapters.autokernel_aux_receipt/v1"
PROJECTION_SCHEMA = "epyc.vidya.autokernel_aux_measurements.v1"
SOURCE_SCHEMAS = frozenset({
    "epyc.autokernel.hipkittens_lds.v1",
    "epyc.autokernel.rocprofv1_attribution.v1",
    "epyc.autokernel.omniperf_fallback.v1",
    "epyc.autokernel.geak_arena_roundtrip.v1",
    "epyc.autokernel.mmq_wgm_profile.v1",
    "epyc.inf37.iq2_fancy_simd_ab.v1",
    "epyc.autokernel.q4k_unpack_attribution.v1",
})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_Q4K_SCHEMA = "epyc.autokernel.q4k_unpack_attribution.v1"
_Q4K_PRODUCER = "scripts.benchmark.run_autokernel_q4k_unpack_attribution/v2"
_Q4K_PRODUCER_PATH = "scripts/benchmark/run_autokernel_q4k_unpack_attribution.py"
_Q4K_PMC_LINE = "pmc: SQ_WAVES SQ_INSTS_VALU SQ_INSTS_VALU_INT32"
_Q4K_METRICS = {
    "valu_insts_per_wave_delta": (
        "q4k_minus_control_valu_instructions_per_wave_delta",
        "instructions/wave", "SQ_INSTS_VALU", "differential_mechanism_counter",
    ),
    "int32_insts_per_wave_delta": (
        "q4k_minus_control_int32_instructions_per_wave_delta",
        "instructions/wave", "SQ_INSTS_VALU_INT32", "differential_mechanism_counter",
    ),
    "device_duration_ns_delta": (
        "q4k_minus_control_dispatch_device_duration_ns_delta",
        "ns", "rocprofv2_dispatch_timestamps", "dispatch_duration_diagnostic",
    ),
}
_Q4K_CONTROLS = ("q4_0", "q8_0")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _q4k_source_digest(identity: dict) -> str:
    commit = identity.get("source_commit")
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise ProjectionError("receipt.identity.source_commit must be a full commit")
    return _canonical_sha256({
        "source_commit": commit,
        "mmvq_sha256": _sha(identity.get("mmvq_sha256"), "identity.mmvq_sha256"),
        "vecdotq_sha256": _sha(
            identity.get("vecdotq_sha256"), "identity.vecdotq_sha256"
        ),
        "ggml_header_sha256": _sha(
            identity.get("ggml_header_sha256"), "identity.ggml_header_sha256"
        ),
        "binary_sha256": _sha(
            identity.get("binary_sha256"), "identity.binary_sha256"
        ),
    })


def _q4k_device_claim_digest(receipt: dict) -> str:
    opened = receipt.get("device_claim_open")
    released = receipt.get("device_claim_released")
    if not isinstance(opened, dict) or not isinstance(released, dict):
        raise ProjectionError("Q4_K receipt requires opened and released device claims")
    for label, claim in (("opened", opened), ("released", released)):
        if claim.get("schema") != "epyc.autokernel.device_claim_receipt.v1":
            raise ProjectionError(f"{label} device claim has the wrong schema")
        if claim.get("campaign_id") != receipt.get("campaign_id"):
            raise ProjectionError(f"{label} device claim names a different campaign")
    for field in ("claim_id", "device_id", "acquired_at"):
        if not isinstance(opened.get(field), str) or not opened[field]:
            raise ProjectionError(f"opened device claim lacks {field}")
        if opened[field] != released.get(field):
            raise ProjectionError(f"device claim {field} changed across release")
    if not isinstance(released.get("released_at"), str) or not released["released_at"]:
        raise ProjectionError("released device claim lacks released_at")
    return _canonical_sha256({"opened": opened, "released": released})


def _validate_q4k_measurements(receipt: dict, measurements: list[dict]) -> None:
    """Validate only producer-written fields; never reconstruct a pre-hook row."""
    if receipt.get("authority") != "diagnostic_only":
        raise ProjectionError("Q4_K receipt authority must remain diagnostic_only")
    producer = receipt.get("producer")
    if not isinstance(producer, dict):
        raise ProjectionError("Q4_K receipt lacks producer identity")
    if producer.get("producer_id") != _Q4K_PRODUCER:
        raise ProjectionError("Q4_K receipt names a different producer")
    if producer.get("path") != _Q4K_PRODUCER_PATH:
        raise ProjectionError("Q4_K receipt names a different producer path")
    producer_sha = _sha(producer.get("sha256"), "producer.sha256")
    identity = receipt.get("identity")
    if not isinstance(identity, dict):
        raise ProjectionError("Q4_K receipt lacks source identity")
    if identity.get("runner_sha256") != producer_sha:
        raise ProjectionError("Q4_K source identity and producer digest differ")
    source_digest = _q4k_source_digest(identity)
    if receipt.get("source_identity_sha256") != source_digest:
        raise ProjectionError("Q4_K source_identity_sha256 does not bind identity")
    claim_digest = _q4k_device_claim_digest(receipt)
    if receipt.get("device_claim_sha256") != claim_digest:
        raise ProjectionError("Q4_K device_claim_sha256 does not bind claim receipts")
    logical = dict(receipt)
    stored_receipt_sha = logical.pop("receipt_sha256", None)
    if _sha(stored_receipt_sha, "receipt.receipt_sha256") != _canonical_sha256(logical):
        raise ProjectionError("Q4_K receipt_sha256 does not bind the logical receipt")
    workload = receipt.get("workload")
    if not isinstance(workload, dict) or workload.get("counter_transport") != "rocprofv2":
        raise ProjectionError("Q4_K belief rows require the direct rocprofv2 transport")
    counter_support = receipt.get("counter_support")
    if (not isinstance(counter_support, dict)
            or counter_support.get("single_pass_group") is not True
            or counter_support.get("counter_file_line") != _Q4K_PMC_LINE
            or counter_support.get("arch_device") != "gfx90a:0"):
        raise ProjectionError("Q4_K receipt lacks the exact single-pass gfx90a PMC contract")
    profiler_sha = _sha(
        counter_support.get("profiler_sha256"), "counter_support.profiler_sha256"
    )
    shape = workload.get("shape")
    if not isinstance(shape, dict) or set(shape) != {"m", "n", "k"}:
        raise ProjectionError("Q4_K receipt shape must contain exactly m, n, and k")
    if any(isinstance(shape[key], bool) or not isinstance(shape[key], int)
           or shape[key] < 1 for key in shape):
        raise ProjectionError("Q4_K receipt shape must contain positive integers")
    expected_ids = {
        f"q4k_minus_{control.replace('_', '')}_{native_field}"
        for control in _Q4K_CONTROLS for native_field in _Q4K_METRICS
    }
    observed_ids = {row.get("measurement_id") for row in measurements
                    if isinstance(row, dict)}
    if len(measurements) != len(expected_ids) or observed_ids != expected_ids:
        raise ProjectionError("Q4_K receipt must carry the exact six directional rows")
    opened = receipt["device_claim_open"]
    for row in measurements:
        unsigned = dict(row)
        stored_measurement_sha = unsigned.pop("measurement_sha256", None)
        if _sha(stored_measurement_sha, "measurement.measurement_sha256") != _canonical_sha256(
            unsigned
        ):
            raise ProjectionError("Q4_K measurement_sha256 does not bind its row")
        local_id = row["measurement_id"]
        native_field = next(
            (field for field in _Q4K_METRICS if local_id.endswith(field)), None
        )
        if native_field is None:
            raise ProjectionError("Q4_K measurement id has an unknown native field")
        metric, unit, instrument, role = _Q4K_METRICS[native_field]
        control = next(
            (item for item in _Q4K_CONTROLS
             if local_id.startswith(f"q4k_minus_{item.replace('_', '')}_")), None
        )
        if control is None:
            raise ProjectionError("Q4_K measurement id has an unknown control")
        if row.get("metric") != metric or row.get("unit") != unit:
            raise ProjectionError("Q4_K measurement metric/unit differs from its row id")
        if row.get("metric_direction") != "lower_better" or row.get("category") != "BASELINE":
            raise ProjectionError("Q4_K measurement direction/category is not admitted")
        if row.get("reps_basis") != "scored:balanced paired direct-PMC blocks":
            raise ProjectionError("Q4_K measurement does not name the scored block basis")
        extra = row.get("extra")
        if not isinstance(extra, dict):
            raise ProjectionError("Q4_K measurement.extra must be an object")
        if extra.get("measurement_role") != role:
            raise ProjectionError("Q4_K measurement role differs from its metric")
        if extra.get("arm") != "q4_K" or extra.get("control") != control:
            raise ProjectionError("Q4_K measurement arm/control differs from its id")
        if extra.get("shape") != shape:
            raise ProjectionError("Q4_K measurement shape differs from the receipt")
        if extra.get("source_commit") != identity["source_commit"]:
            raise ProjectionError("Q4_K measurement source commit differs from identity")
        if extra.get("source_identity_sha256") != source_digest:
            raise ProjectionError("Q4_K measurement source digest differs from identity")
        if extra.get("binary_sha256") != identity["binary_sha256"]:
            raise ProjectionError("Q4_K measurement binary digest differs from identity")
        if (extra.get("producer_id") != _Q4K_PRODUCER
                or extra.get("producer_sha256") != producer_sha):
            raise ProjectionError("Q4_K measurement producer identity differs from receipt")
        if (extra.get("device_id") != opened["device_id"]
                or extra.get("device_claim_id") != opened["claim_id"]
                or extra.get("device_claim_sha256") != claim_digest):
            raise ProjectionError("Q4_K measurement device claim differs from receipt")
        if extra.get("authority") != "diagnostic_only":
            raise ProjectionError("Q4_K measurement authority must remain diagnostic_only")
        if (extra.get("promotion_authority") is not False
                or extra.get("inside_unpack_wall_share_emitted") is not False):
            raise ProjectionError("Q4_K measurement invented promotion or wall-share authority")
        basis = extra.get("counter_basis")
        if not isinstance(basis, dict):
            raise ProjectionError("Q4_K measurement lacks its exact counter basis")
        if extra.get("evidence_sha256") != _canonical_sha256(basis):
            raise ProjectionError("Q4_K evidence_sha256 does not bind its counter basis")
        if (basis.get("arm") != "q4_K" or basis.get("control") != control
                or basis.get("shape") != shape or basis.get("native_field") != native_field
                or basis.get("instrument") != instrument
                or basis.get("counter_transport") != "rocprofv2"
                or basis.get("counter_file_line") != _Q4K_PMC_LINE):
            raise ProjectionError("Q4_K measurement counter basis differs from its row")
        identifiability = basis.get("identifiability")
        if (not isinstance(identifiability, dict)
                or identifiability.get("direct_hardware_counter_attribution")
                != "differential_mechanism_only"
                or identifiability.get("exact_inside_kernel_wall_share") is not None):
            raise ProjectionError("Q4_K row lacks the fused-dispatch authority boundary")
        if (basis.get("source_identity_sha256") != source_digest
                or basis.get("producer_sha256") != producer_sha
                or basis.get("device_claim_sha256") != claim_digest
                or basis.get("profiler_sha256") != profiler_sha):
            raise ProjectionError("Q4_K counter basis identity digests differ from receipt")
        values = basis.get("block_values")
        reps = row.get("reps")
        if (isinstance(reps, bool) or not isinstance(reps, int) or reps < 1
                or not isinstance(values, list) or len(values) != reps):
            raise ProjectionError("Q4_K counter basis does not contain one value per scored block")
        if (basis.get("scored_blocks") != reps
                or basis.get("active_dispatches_per_arm_per_block")
                != workload.get("active_repetitions")
                or basis.get("comparison_id") != f"q4_K_minus_{control}"
                or basis.get("aggregation") != "median(paired_block_arm_minus_control)"):
            raise ProjectionError("Q4_K counter basis aggregation differs from the receipt")
        if role == "differential_mechanism_counter":
            if (basis.get("normalizer") != "SQ_WAVES"
                    or basis.get("per_arm_reduction")
                    != "median(dispatch PMC)/median(dispatch SQ_WAVES)"):
                raise ProjectionError("Q4_K counter row lacks its per-wave normalization")
        elif (basis.get("diagnostic_only") is not True
              or basis.get("timestamp_fields")
              != ["Start_Timestamp", "End_Timestamp"]
              or basis.get("per_arm_reduction")
              != "median(dispatch End_Timestamp-Start_Timestamp)"):
            raise ProjectionError("Q4_K duration row lacks its diagnostic timestamp basis")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) for value in values):
            raise ProjectionError("Q4_K counter basis block values must be finite")
        value = row.get("value")
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or float(value) != float(statistics.median(values))):
            raise ProjectionError("Q4_K measurement value is not the median counter-basis value")


def native_rows(receipt: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return only measurements explicitly written by a successful native producer."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported AutoKernel auxiliary receipt schema")
    if receipt_sha256 and not _SHA256.fullmatch(receipt_sha256):
        raise ProjectionError("receipt_sha256 must be a lowercase SHA-256 digest")
    measurements = receipt.get("belief_measurements")
    if measurements is None:
        return ()
    if not isinstance(measurements, list):
        raise ProjectionError("belief_measurements must be a list")
    if not measurements:
        return ()
    if receipt.get("status") not in {"pass", "passed", "complete"}:
        raise ProjectionError("a failed auxiliary receipt cannot carry belief measurements")
    if receipt.get("schema") == _Q4K_SCHEMA:
        _validate_q4k_measurements(receipt, measurements)
    return tuple({
        "receipt": receipt,
        "measurement": measurement,
        "measurement_index": index,
        "receipt_locator": receipt_locator,
        "receipt_sha256": receipt_sha256,
        "attestation_present": attestation_present,
    } for index, measurement in enumerate(measurements))


def _text(obj: dict, key: str, path: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{path}.{key} is required and must be non-empty")
    return value.strip()


@register("autokernel-aux-receipt-measurement")
def project(native: Any) -> ClaimTuple:
    """Project one producer-written measurement; the shared ladder alone grades it."""
    if not isinstance(native, dict):
        raise ProjectionError("AutoKernel auxiliary native row must be a dict")
    receipt = native.get("receipt")
    measurement = native.get("measurement")
    if not isinstance(receipt, dict) or not isinstance(measurement, dict):
        raise ProjectionError("native row needs receipt and measurement dicts")
    schema = _text(receipt, "schema", "receipt")
    if schema not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported AutoKernel auxiliary receipt schema")
    campaign_id = _text(receipt, "campaign_id", "receipt")
    local_id = _text(measurement, "measurement_id", "measurement")
    metric = _text(measurement, "metric", "measurement")
    claim = _text(measurement, "claim", "measurement")
    reps_basis = _text(measurement, "reps_basis", "measurement")
    value = measurement.get("value")
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value)):
        raise ProjectionError("measurement.value must be a finite number")
    reps = measurement.get("reps")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
        raise ProjectionError("measurement.reps must be a positive integer")
    extra = measurement.get("extra", {})
    if not isinstance(extra, dict):
        raise ProjectionError("measurement.extra must be a dict")
    identity_payload = json.dumps(
        [schema, campaign_id, local_id, native.get("measurement_index")],
        separators=(",", ":"), ensure_ascii=True)
    identity = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()[:24]
    return ClaimTuple(
        measurement_id=f"akaux_{identity}",
        metric=metric,
        value=value,
        date=str(receipt.get("ended_at") or "")[:10],
        category=_text(measurement, "category", "measurement"),
        claim=claim,
        metric_direction=_text(measurement, "metric_direction", "measurement"),
        protocol_id=schema,
        reps=reps,
        reps_basis=reps_basis,
        unit=_text(measurement, "unit", "measurement"),
        attestation_sha256=str(native.get("receipt_sha256") or ""),
        attestation_locator=str(native.get("receipt_locator") or ""),
        attestation_present=native.get("attestation_present"),
        source_kind="autokernel-aux-receipt-measurement",
        extra={
            "projection_schema": PROJECTION_SCHEMA,
            "source_schema": schema,
            "campaign_id": campaign_id,
            "native_measurement_id": local_id,
            **({"native_measurement_sha256": measurement["measurement_sha256"]}
               if measurement.get("measurement_sha256") else {}),
            **({"receipt_self_sha256": receipt["receipt_sha256"]}
               if receipt.get("receipt_sha256") else {}),
            **extra,
        },
    )
