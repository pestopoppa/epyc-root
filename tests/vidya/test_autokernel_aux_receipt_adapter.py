"""Prospective auxiliary receipts project without retrofitting historical runs."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_aux_receipt as aux  # noqa: E402


def receipt(*, measurements=True, status="passed"):
    value = {
        "schema": "epyc.autokernel.rocprofv1_attribution.v1",
        "status": status,
        "campaign_id": "k28-r4",
        "ended_at": "2026-08-11T13:07:19Z",
    }
    if measurements:
        value["belief_measurements"] = [{
            "measurement_id": "gdn_share_p2048",
            "metric": "gated_delta_net_summed_kernel_time_share",
            "value": 0.15397,
            "unit": "fraction",
            "metric_direction": "lower_better",
            "category": "BASELINE",
            "reps": 3,
            "reps_basis": "scored:llama-bench prompt repetitions",
            "claim": "p2048 GDN share is 0.15397",
            "extra": {"prompt_tokens": 2048},
        }]
    return value


def test_old_receipt_without_write_side_vector_is_not_backfilled():
    assert aux.native_rows(receipt(measurements=False)) == ()


def test_iq2_complete_receipt_projects_only_producer_written_rows():
    source = receipt(status="complete")
    source["schema"] = "epyc.inf37.iq2_fancy_simd_ab.v1"
    source["belief_measurements"][0].update({
        "measurement_id": "iq2_xxs_n1_candidate_median_time_us",
        "metric": "iq2_xxs_backend_op_median_time_us",
        "value": 3360.0,
        "unit": "us",
        "category": "CANDIDATE",
        "reps": 10,
        "reps_basis": "scored:balanced paired fresh-process blocks",
        "claim": "IQ2_XXS n=1 candidate median backend-op time is 3360 us",
        "extra": {"shape": {"m": 4096, "n": 1, "k": 14336}},
    })
    native = aux.native_rows(
        source, receipt_locator="probe:inf37-r6/receipt.json",
        receipt_sha256="b" * 64, attestation_present=True)
    assert len(native) == 1
    projected = aux.project(native[0])
    assert projected.metric_direction == "lower_better"
    assert projected.reps == 10
    assert projected.attestation_sha256 == "b" * 64

    old = copy.deepcopy(source)
    old.pop("belief_measurements")
    assert aux.native_rows(old, receipt_sha256="c" * 64) == ()


def test_projection_uses_native_schema_as_protocol_and_shared_ladder():
    row = aux.native_rows(
        receipt(), receipt_locator="probe:k28-r4/receipt.json",
        receipt_sha256="a" * 64, attestation_present=True)[0]
    tup = aux.project(row)
    assert tup.protocol_id == "epyc.autokernel.rocprofv1_attribution.v1"
    assert tup.metric_direction == "lower_better"
    assert tup.extra["prompt_tokens"] == 2048
    assert ct.grade(tup)[:2] == ("Witnessed", "Attested")


def test_failed_receipt_cannot_smuggle_measurements():
    with pytest.raises(ct.ProjectionError, match="failed"):
        aux.native_rows(receipt(status="failed"))


def test_identity_distinguishes_native_measurement_ids():
    source = receipt()
    second = copy.deepcopy(source["belief_measurements"][0])
    second["measurement_id"] = "gdn_share_p8192"
    source["belief_measurements"].append(second)
    identities = {aux.project(row).measurement_id for row in aux.native_rows(source)}
    assert len(identities) == 2


def test_invalid_direction_is_rejected_by_shared_carrier():
    source = receipt()
    source["belief_measurements"][0]["metric_direction"] = "neutral"
    with pytest.raises(ct.ProjectionError, match="metric_direction"):
        aux.project(aux.native_rows(source)[0])
