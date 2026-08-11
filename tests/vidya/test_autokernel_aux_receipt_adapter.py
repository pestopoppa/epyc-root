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


def test_historical_mmq_wgm_r2_schemas_are_not_registered_or_backfilled():
    for schema in (
        "epyc.autokernel.inf36_mmq_wgm_correctness.v2",
        "epyc.autokernel.inf36_mmq_wgm_walltime.v2",
        "epyc.autokernel.inf36_mmq_wgm_tcc.v1",
    ):
        historical = {
            "schema": schema,
            "campaign_id": "inf36-mmq-wgm-gfx90a-20260811-r2",
            "results": [{"wgm": 8, "summary": {"t": {"median": 8.666878}}}],
        }
        with pytest.raises(ct.ProjectionError, match="unsupported"):
            aux.native_rows(historical)


def test_prospective_wgm_rows_project_directions_arm_and_shared_grade():
    prospective = {
        "schema": "epyc.autokernel.mmq_wgm_profile.v1",
        "status": "pass",
        "campaign_id": "inf36-mmq-wgm-successor-r1",
        "ended_at": "2026-08-11T18:10:00Z",
        "belief_measurements": [
            {
                "measurement_id": "mmq_wgm_arm_8_end_to_end_wall_time_ms",
                "metric": "mmq_wgm_end_to_end_wall_time_ms",
                "value": 8.6,
                "unit": "ms",
                "metric_direction": "lower_better",
                "category": "CANDIDATE",
                "reps": 3,
                "reps_basis": "scored: three matched end-to-end repetitions",
                "claim": "Median end-to-end wall time for real MMQ WGM arm 8",
                "extra": {"wgm_arm": 8},
            },
            {
                "measurement_id": "mmq_wgm_arm_8_all_mmq_tcc_hit_rate",
                "metric": "mmq_wgm_all_mmq_tcc_hit_rate",
                "value": 0.65,
                "unit": "fraction",
                "metric_direction": "higher_better",
                "category": "CANDIDATE",
                "reps": 2,
                "reps_basis": "scored: two all-MMQ counter repetitions",
                "claim": "Pooled all-MMQ TCC hit rate for real MMQ WGM arm 8",
                "extra": {"wgm_arm": 8},
            },
            {
                "measurement_id": "mmq_wgm_arm_8_all_mmq_read_requests_per_rep",
                "metric": "mmq_wgm_all_mmq_read_request_volume_per_rep",
                "value": 1100.0,
                "unit": "requests/repetition",
                "metric_direction": "lower_better",
                "category": "CANDIDATE",
                "reps": 2,
                "reps_basis": "scored: two all-MMQ counter repetitions",
                "claim": "Mean all-MMQ read-request volume for real MMQ WGM arm 8",
                "extra": {"wgm_arm": 8},
            },
        ],
    }
    rows = aux.native_rows(
        prospective,
        receipt_locator="probe:successor/receipt.json",
        receipt_sha256="a" * 64,
        attestation_present=True,
    )
    tuples = [aux.project(row) for row in rows]
    assert [tup.metric_direction for tup in tuples] == [
        "lower_better", "higher_better", "lower_better",
    ]
    assert all(tup.extra["wgm_arm"] == 8 for tup in tuples)
    assert all(ct.grade(tup)[:2] == ("Witnessed", "Attested") for tup in tuples)


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
