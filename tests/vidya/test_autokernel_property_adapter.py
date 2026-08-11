"""SC18: AutoKernel property residuals preserve their write-side coordinates."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_property as akp  # noqa: E402


def event(*, measurements=True):
    row = {
        "schema": "epyc.autokernel.property_measurement.v1",
        "shape_id": "SOFT_MAX(type=f32,ne=[83,2,1,1])#0",
        "op": "SOFT_MAX", "backend": "CPU",
        "metric_id": "softmax_invariants/v1",
        "residual": 2.5e-08, "tolerance": 1e-4,
        "suite_seed": 4711, "passed": True,
    }
    gate = {"outcome": "PASS", "evidence_ref": "akcap:backend-ops-001"}
    if measurements:
        gate["measurements"] = [row]
    return {
        "schema": "epyc.autokernel.evaluation_event.v5",
        "event_id": "ake-001", "campaign_id": "ak-001", "candidate_id": "akc-001",
        "claim_grammar": {
            "category": "CANDIDATE", "protocol_id": "P-AK-SEARCH-1",
            "metric": "decode_tps", "metric_direction": "higher_better", "reps": 20,
            "attestation_ref": "akcap:campaign-001",
        },
        "correctness": {"t0.backend_op_units": gate},
        "performance": {"search_discipline": {"suite_seed": 4711}},
        "created_at": "2026-08-11T12:34:56Z",
    }


def test_old_event_without_write_side_payload_is_not_backfilled():
    assert akp.native_rows(event(measurements=False)) == ()


def test_projection_preserves_residual_coordinates_and_uses_shared_ladder():
    row = akp.native_rows(event())[0]
    tup = akp.project(row)
    assert tup.metric == "softmax_invariants/v1"
    assert tup.value == 2.5e-08
    assert tup.metric_direction == "lower_better"
    assert tup.extra["suite_seed"] == 4711
    assert tup.extra["shape_id"] == "SOFT_MAX(type=f32,ne=[83,2,1,1])#0"
    assert ct.grade(tup)[:2] == ("Witnessed", "Anchored")


def test_distinct_measurements_have_distinct_claim_identity():
    source = event()
    second = copy.deepcopy(source["correctness"]["t0.backend_op_units"]["measurements"][0])
    second["shape_id"] = "SOFT_MAX(type=f32,ne=[127,1,1,1])#1"
    source["correctness"]["t0.backend_op_units"]["measurements"].append(second)
    identities = {akp.project(row).measurement_id for row in akp.native_rows(source)}
    assert len(identities) == 2


def test_suite_seed_mismatch_refuses_instead_of_relabelling():
    source = event()
    source["performance"]["search_discipline"]["suite_seed"] = 99
    with pytest.raises(ct.ProjectionError, match="does not match"):
        akp.project(akp.native_rows(source)[0])


def test_derived_property_verdict_cannot_be_self_reported():
    source = event()
    source["correctness"]["t0.backend_op_units"]["measurements"][0]["passed"] = False
    with pytest.raises(ct.ProjectionError, match="residual <= tolerance"):
        akp.project(akp.native_rows(source)[0])


def test_real_event_hash_can_reach_attested_without_borrowing_the_binary_hash():
    row = akp.native_rows(
        event(), event_locator="journal:auto/events.jsonl#ake-001",
        event_sha256="a" * 64, attestation_present=True)[0]
    assert ct.grade(akp.project(row))[:2] == ("Witnessed", "Attested")
