"""Project prospective AutoKernel property residuals from durable evaluation events.

Only producer-written ``t0.backend_op_units.measurements`` rows are admitted.  The public ingest
path accepts either the complete current event or its real journal envelope; it delegates the full
event/envelope validation and canonical event digest to ``autokernel_evaluation_event``.  Older
events without the property vector return no rows and are never reconstructed from gate prose.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402
from adapters import autokernel_evaluation_event as evaluation_event  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_property/v2"
SOURCE_SCHEMA = "epyc.autokernel.property_measurement.v1"
GATE_ID = "t0.backend_op_units"
_TRANSFORMS = frozenset({"identity", "x3", "x0p01", "negate"})
_GATE_OUTCOMES = frozenset({"PASS", "FAIL", "COULD_NOT_CHECK"})


def _required_text(obj: dict, key: str, path: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{path}.{key} is required and must be non-empty")
    return value.strip()


def _measurement_valid(event: dict, gate: dict, measurement: Any) -> bool:
    if (not isinstance(gate, dict) or gate.get("outcome") not in _GATE_OUTCOMES
            or not isinstance(gate.get("reasons"), list)
            or any(not isinstance(reason, str) for reason in gate["reasons"])
            or not isinstance(gate.get("requires_anchor"), bool)
            or not isinstance(gate.get("evidence_ref"), str)
            or not isinstance(measurement, dict)
            or measurement.get("schema") != SOURCE_SCHEMA):
        return False
    for key in ("shape_id", "op", "backend", "metric_id"):
        if not isinstance(measurement.get(key), str) or not measurement[key].strip():
            return False
    suite_seed = measurement.get("suite_seed")
    if isinstance(suite_seed, bool) or not isinstance(suite_seed, int) or suite_seed < 0:
        return False
    discipline = event["performance"].get("search_discipline")
    if not isinstance(discipline, dict) or discipline.get("suite_seed") != suite_seed:
        return False
    transform = measurement.get("input_transform", "identity")
    if transform not in _TRANSFORMS:
        return False
    residual, tolerance, passed = (
        measurement.get("residual"), measurement.get("tolerance"), measurement.get("passed"))
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value < 0 for value in (residual, tolerance)):
        return False
    return isinstance(passed, bool) and passed == (residual <= tolerance)


def native_rows(source: Any) -> tuple[dict, ...]:
    """Return one row per prospective property residual in an admissible event."""
    loaded = evaluation_event.load_event_source(source)
    if loaded is None:
        return ()
    event = loaded["event"]
    gate = event["correctness"].get(GATE_ID)
    measurements = gate.get("measurements") if isinstance(gate, dict) else None
    if measurements is None:
        return ()
    if not isinstance(measurements, list) or not measurements:
        return ()
    if any(not _measurement_valid(event, gate, measurement) for measurement in measurements):
        return ()
    return tuple({
        **loaded,
        "measurement": measurement,
        "measurement_index": index,
    } for index, measurement in enumerate(measurements))


@register("autokernel-property-measurement")
def project(native: Any) -> ClaimTuple:
    """Revalidate the source and coordinate before projecting through the shared ladder."""
    if not isinstance(native, dict) or "source" not in native:
        raise ProjectionError("AutoKernel property native row must retain its source")
    rows = native_rows(native["source"])
    index = native.get("measurement_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(rows):
        raise ProjectionError("AutoKernel property measurement_index is not in its source event")
    expected = rows[index]
    for key in ("event_sha256", "event_locator", "measurement"):
        if native.get(key) != expected[key]:
            raise ProjectionError(f"AutoKernel property native row mutated {key}")

    event, measurement = expected["event"], expected["measurement"]
    claim_grammar = event["claim_grammar"]
    event_id = _required_text(event, "event_id", "evaluation_event")
    op = _required_text(measurement, "op", "measurement")
    backend = _required_text(measurement, "backend", "measurement")
    shape_id = _required_text(measurement, "shape_id", "measurement")
    metric_id = _required_text(measurement, "metric_id", "measurement")
    suite_seed = measurement["suite_seed"]
    input_transform = measurement.get("input_transform", "identity")
    residual, tolerance, passed = (
        measurement["residual"], measurement["tolerance"], measurement["passed"])

    identity_payload = json.dumps(
        [event_id, index, backend, op, shape_id, metric_id, suite_seed, input_transform,
         expected["event_sha256"]],
        separators=(",", ":"), ensure_ascii=True)
    identity = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()[:24]
    artifact = event["artifact"]
    return ClaimTuple(
        measurement_id=f"akprop_{identity}",
        metric=metric_id,
        value=residual,
        date=event["created_at"][:10],
        category=claim_grammar["category"],
        claim=(f"AutoKernel {backend} {op} shape {shape_id} transform {input_transform} "
               f"property {metric_id}: residual {residual} <= tolerance {tolerance} is {passed}"),
        metric_direction="lower_better",
        protocol_id=claim_grammar["protocol_id"],
        reps=1,
        reps_basis="scored:one property evaluation",
        unit="residual",
        attestation_sha256=expected["event_sha256"],
        attestation_locator=expected["event_locator"],
        attestation_present=expected["attestation_present"],
        source_kind="autokernel-property-measurement",
        extra={
            "event_id": event_id,
            "campaign_id": event["campaign_id"],
            "candidate_id": event["candidate_id"],
            "backend": backend,
            "op": op,
            "shape_id": shape_id,
            "suite_seed": suite_seed,
            "input_transform": input_transform,
            "tolerance": tolerance,
            "passed": passed,
            "source_sha256": artifact["source_sha256"],
            "binary_sha256": artifact["binary_sha256"],
            "resource_claim_receipt": event["resource_claim_receipt"],
        },
    )


__all__ = ["ADAPTER_ID", "GATE_ID", "SOURCE_SCHEMA", "native_rows", "project"]
