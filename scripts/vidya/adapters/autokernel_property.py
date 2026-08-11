"""Project AutoKernel property residuals into the shared measurement ClaimTuple.

This adapter deliberately reads only the write-side payload emitted inside
``evaluation_event.correctness[t0.backend_op_units].measurements``.  An older event with no such
payload yields no native rows: the read side never reconstructs a residual from a pass/fail gate,
because doing so would invent the measurement SC18 exists to preserve.
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

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_property/v1"
SOURCE_SCHEMA = "epyc.autokernel.property_measurement.v1"
GATE_ID = "t0.backend_op_units"
_EVENT_SCHEMA = re.compile(r"^epyc\.autokernel\.evaluation_event\.v[0-9]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def native_rows(event: dict, *, event_locator: str = "",
                event_sha256: str = "", attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return one native row per residual actually written by the producer.

    Missing measurements are an empty tuple, not a synthesized row.  A supplied event hash is
    accepted only when it is a real SHA-256; the adapter never substitutes the candidate binary or
    source hash, because those attest to different artifacts.
    """
    if not isinstance(event, dict) or not _EVENT_SCHEMA.match(str(event.get("schema", ""))):
        raise ProjectionError("native AutoKernel source must be a versioned evaluation_event")
    if event_sha256 and not _SHA256.match(event_sha256):
        raise ProjectionError("event_sha256 must be a 64-character lowercase hex digest")
    correctness = event.get("correctness")
    gate = correctness.get(GATE_ID) if isinstance(correctness, dict) else None
    measurements = gate.get("measurements") if isinstance(gate, dict) else None
    if measurements is None:
        return ()
    if not isinstance(measurements, list):
        raise ProjectionError(f"correctness.{GATE_ID}.measurements must be a list")
    rows = []
    for index, measurement in enumerate(measurements):
        if not isinstance(measurement, dict) or measurement.get("schema") != SOURCE_SCHEMA:
            raise ProjectionError(
                f"property measurement {index} must have schema {SOURCE_SCHEMA!r}")
        rows.append({
            "event": event,
            "measurement": measurement,
            "measurement_index": index,
            "event_locator": event_locator or str(gate.get("evidence_ref") or ""),
            "event_sha256": event_sha256,
            "attestation_present": attestation_present,
        })
    return tuple(rows)


def _required_text(obj: dict, key: str, path: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{path}.{key} is required and must be non-empty")
    return value.strip()


@register("autokernel-property-measurement")
def project(native: Any) -> ClaimTuple:
    """Project one row returned by :func:`native_rows`; grading stays in claim_tuple."""
    if not isinstance(native, dict):
        raise ProjectionError("AutoKernel property native row must be a dict")
    event = native.get("event")
    measurement = native.get("measurement")
    if not isinstance(event, dict) or not isinstance(measurement, dict):
        raise ProjectionError("AutoKernel property native row needs event and measurement dicts")
    claim_grammar = event.get("claim_grammar")
    if not isinstance(claim_grammar, dict):
        raise ProjectionError("evaluation_event.claim_grammar is required")

    event_id = _required_text(event, "event_id", "evaluation_event")
    op = _required_text(measurement, "op", "measurement")
    backend = _required_text(measurement, "backend", "measurement")
    shape_id = _required_text(measurement, "shape_id", "measurement")
    metric_id = _required_text(measurement, "metric_id", "measurement")
    suite_seed = measurement.get("suite_seed")
    if isinstance(suite_seed, bool) or not isinstance(suite_seed, int) or suite_seed < 0:
        raise ProjectionError("measurement.suite_seed must be a non-negative int")
    discipline = ((event.get("performance") or {}).get("search_discipline")
                  if isinstance(event.get("performance"), dict) else None)
    event_seed = discipline.get("suite_seed") if isinstance(discipline, dict) else None
    if event_seed != suite_seed:
        raise ProjectionError(
            f"measurement suite_seed {suite_seed} does not match event suite_seed {event_seed}")

    residual = measurement.get("residual")
    tolerance = measurement.get("tolerance")
    passed = measurement.get("passed")
    for name, value in (("residual", residual), ("tolerance", tolerance)):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ProjectionError(f"measurement.{name} must be a non-negative number")
    if not isinstance(passed, bool) or passed != (residual <= tolerance):
        raise ProjectionError("measurement.passed must equal residual <= tolerance")

    identity_payload = json.dumps(
        [event_id, native.get("measurement_index"), backend, op, shape_id, metric_id, suite_seed],
        separators=(",", ":"), ensure_ascii=True)
    identity = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()[:24]
    digest = str(native.get("event_sha256") or "")
    locator = str(native.get("event_locator") or "")
    return ClaimTuple(
        measurement_id=f"akprop_{identity}",
        metric=metric_id,
        value=residual,
        date=str(event.get("created_at") or "")[:10],
        category=_required_text(claim_grammar, "category", "claim_grammar"),
        claim=(f"AutoKernel {backend} {op} shape {shape_id} property {metric_id}: "
               f"residual {residual} <= tolerance {tolerance} is {passed}"),
        metric_direction="lower_better",
        protocol_id=_required_text(claim_grammar, "protocol_id", "claim_grammar"),
        reps=1,
        reps_basis="scored:one property evaluation",
        unit="residual",
        attestation_sha256=digest,
        attestation_locator=locator,
        attestation_present=native.get("attestation_present"),
        source_kind="autokernel-property-measurement",
        extra={
            "event_id": event_id,
            "campaign_id": event.get("campaign_id"),
            "candidate_id": event.get("candidate_id"),
            "backend": backend,
            "op": op,
            "shape_id": shape_id,
            "suite_seed": suite_seed,
            "tolerance": tolerance,
            "passed": passed,
        },
    )
