"""Project prospective AutoKernel auxiliary-receipt measurements into ClaimTuple.

The adapter reads only the producer-written ``belief_measurements`` vector. Older receipts yield no
rows: reconstructing tuples from their prose or profiler payload would invent write-time provenance.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
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
    "epyc.autokernel.profile_beliefs.v1",
    "epyc.inf37.iq2_fancy_simd_ab.v1",
})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def native_rows(receipt: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return only measurements explicitly written by a successful native producer."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported AutoKernel auxiliary receipt schema")
    if receipt_sha256 and not _SHA256.match(receipt_sha256):
        raise ProjectionError("receipt_sha256 must be a lowercase SHA-256 digest")
    measurements = receipt.get("belief_measurements")
    if measurements is None:
        return ()
    if receipt.get("status") not in {"pass", "passed", "complete"}:
        raise ProjectionError("a failed auxiliary receipt cannot carry belief measurements")
    if not isinstance(measurements, list):
        raise ProjectionError("belief_measurements must be a list")
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
            **extra,
        },
    )
