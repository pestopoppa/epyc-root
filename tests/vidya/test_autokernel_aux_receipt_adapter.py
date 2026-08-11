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


def q4k_receipt():
    campaign = "inf37-q4k-unpack-successor-r8"
    producer_sha = "a" * 64
    identity = {
        "source_commit": "0" * 39 + "1",
        "mmvq_sha256": "b" * 64,
        "vecdotq_sha256": "c" * 64,
        "ggml_header_sha256": "d" * 64,
        "binary_sha256": "e" * 64,
        "runner_sha256": producer_sha,
    }
    source_digest = aux._q4k_source_digest(identity)
    opened = {
        "schema": "epyc.autokernel.device_claim_receipt.v1",
        "campaign_id": campaign,
        "claim_id": "akd-q4k-r8",
        "device_id": "mi210_0",
        "acquired_at": "2026-08-12T00:00:00Z",
        "released_at": None,
    }
    released = dict(opened)
    released["released_at"] = "2026-08-12T00:01:00Z"
    claim_digest = aux._canonical_sha256({"opened": opened, "released": released})
    shape = {"m": 17408, "n": 1, "k": 5120}
    profiler_sha = "f" * 64
    measurements = []
    for control in aux._Q4K_CONTROLS:
        for native_field, (metric, unit, instrument, role) in aux._Q4K_METRICS.items():
            values = ([3.0, 3.0] if role == "differential_mechanism_counter"
                      else [8.0, 9.0])
            basis = {
                "arm": "q4_K",
                "control": control,
                "comparison_id": f"q4_K_minus_{control}",
                "shape": shape,
                "scored_blocks": 2,
                "active_dispatches_per_arm_per_block": 5,
                "block_values": values,
                "native_field": native_field,
                "instrument": instrument,
                "counter_transport": "rocprofv2",
                "counter_file_line": aux._Q4K_PMC_LINE,
                "aggregation": "median(paired_block_arm_minus_control)",
                "identifiability": {
                    "direct_hardware_counter_attribution": "differential_mechanism_only",
                    "exact_inside_kernel_wall_share": None,
                    "reason": "fused dispatch fixture",
                    "closest_control": "Q4_K minus Q4_0 at identical m,n,k",
                },
                "source_identity_sha256": source_digest,
                "producer_sha256": producer_sha,
                "profiler_sha256": profiler_sha,
                "device_claim_sha256": claim_digest,
            }
            if role == "differential_mechanism_counter":
                basis.update({
                    "normalizer": "SQ_WAVES",
                    "per_arm_reduction": (
                        "median(dispatch PMC)/median(dispatch SQ_WAVES)"),
                    "counter_semantics": "fixture semantics",
                })
            else:
                basis.update({
                    "timestamp_fields": ["Start_Timestamp", "End_Timestamp"],
                    "per_arm_reduction": (
                        "median(dispatch End_Timestamp-Start_Timestamp)"),
                    "diagnostic_only": True,
                })
            row = {
                "measurement_id": (
                    f"q4k_minus_{control.replace('_', '')}_{native_field}"),
                "metric": metric,
                "value": sum(values) / len(values),
                "unit": unit,
                "metric_direction": "lower_better",
                "category": "BASELINE",
                "reps": 2,
                "reps_basis": "scored:balanced paired direct-PMC blocks",
                "claim": f"fixture {native_field}",
                "extra": {
                    "measurement_role": role,
                    "arm": "q4_K",
                    "control": control,
                    "shape": shape,
                    "counter_basis": basis,
                    "source_commit": identity["source_commit"],
                    "source_identity_sha256": source_digest,
                    "binary_sha256": identity["binary_sha256"],
                    "producer_id": aux._Q4K_PRODUCER,
                    "producer_sha256": producer_sha,
                    "evidence_sha256": aux._canonical_sha256(basis),
                    "device_id": opened["device_id"],
                    "device_claim_id": opened["claim_id"],
                    "device_claim_sha256": claim_digest,
                    "authority": "diagnostic_only",
                    "promotion_authority": False,
                    "inside_unpack_wall_share_emitted": False,
                },
            }
            row["measurement_sha256"] = aux._canonical_sha256(row)
            measurements.append(row)
    value = {
        "schema": aux._Q4K_SCHEMA,
        "status": "passed",
        "authority": "diagnostic_only",
        "campaign_id": campaign,
        "ended_at": "2026-08-12T00:01:01Z",
        "identity": identity,
        "producer": {
            "producer_id": aux._Q4K_PRODUCER,
            "path": aux._Q4K_PRODUCER_PATH,
            "sha256": producer_sha,
        },
        "source_identity_sha256": source_digest,
        "device_claim_sha256": claim_digest,
        "device_claim_open": opened,
        "device_claim_released": released,
        "workload": {
            "counter_transport": "rocprofv2",
            "shape": shape,
            "blocks": 2,
            "active_repetitions": 5,
        },
        "counter_support": {
            "single_pass_group": True,
            "counter_file_line": aux._Q4K_PMC_LINE,
            "arch_device": "gfx90a:0",
            "profiler_sha256": profiler_sha,
        },
        "belief_measurements": measurements,
    }
    value["receipt_sha256"] = aux._canonical_sha256(value)
    return value


def resign_q4k(value, *measurement_indices):
    for index in measurement_indices:
        row = value["belief_measurements"][index]
        row.pop("measurement_sha256", None)
        row["measurement_sha256"] = aux._canonical_sha256(row)
    value.pop("receipt_sha256", None)
    value["receipt_sha256"] = aux._canonical_sha256(value)


def test_old_receipt_without_write_side_vector_is_not_backfilled():
    assert aux.native_rows(receipt(measurements=False)) == ()


def test_attestation_digest_refuses_trailing_bytes():
    with pytest.raises(ct.ProjectionError, match="lowercase SHA-256"):
        aux.native_rows(receipt(), receipt_sha256="a" * 65)


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


def test_q4k_direct_pmc_rows_project_exact_directions_and_digests():
    source = q4k_receipt()
    rows = aux.native_rows(
        source, receipt_locator="probe:inf37-r8/receipt.json",
        receipt_sha256="9" * 64, attestation_present=True)
    assert len(rows) == 6
    tuples = [aux.project(row) for row in rows]
    assert {tup.extra["control"] for tup in tuples} == {"q4_0", "q8_0"}
    assert {tup.metric for tup in tuples} == {
        "q4k_minus_control_valu_instructions_per_wave_delta",
        "q4k_minus_control_int32_instructions_per_wave_delta",
        "q4k_minus_control_dispatch_device_duration_ns_delta",
    }
    assert all(tup.metric_direction == "lower_better" for tup in tuples)
    assert all(tup.category == "BASELINE" for tup in tuples)
    assert all(tup.extra["arm"] == "q4_K" for tup in tuples)
    assert all(tup.extra["promotion_authority"] is False for tup in tuples)
    assert all(tup.extra["inside_unpack_wall_share_emitted"] is False for tup in tuples)
    assert all(tup.extra["native_measurement_sha256"] for tup in tuples)
    assert all(tup.extra["receipt_self_sha256"] == source["receipt_sha256"]
               for tup in tuples)
    assert all(ct.grade(tup)[:2] == ("Witnessed", "Attested") for tup in tuples)


def test_historical_q4k_r7_empty_vector_is_not_backfilled():
    historical = {
        "schema": aux._Q4K_SCHEMA,
        "status": "passed",
        "campaign_id": "inf37-q4k-unpack-v9-20260811-r7",
        "ended_at": "2026-08-11T18:40:10Z",
        "summary": {"comparisons": {"q4_K_minus_q4_0": [{"block": 0}]}},
        "belief_measurements": [],
    }
    assert aux.native_rows(historical) == ()


@pytest.mark.parametrize("defect", [
    "measurement_self", "receipt_self", "evidence", "source", "producer",
    "device_claim", "promotion", "wall_share",
])
def test_q4k_digest_and_authority_defects_fail_closed(defect):
    source = q4k_receipt()
    if defect == "measurement_self":
        source["belief_measurements"][0]["measurement_sha256"] = "0" * 64
        resign_q4k(source)
    elif defect == "receipt_self":
        source["receipt_sha256"] = "0" * 64
    elif defect == "evidence":
        source["belief_measurements"][0]["extra"]["evidence_sha256"] = "0" * 64
        resign_q4k(source, 0)
    elif defect == "source":
        source["belief_measurements"][0]["extra"]["source_identity_sha256"] = "0" * 64
        resign_q4k(source, 0)
    elif defect == "producer":
        source["belief_measurements"][0]["extra"]["producer_sha256"] = "0" * 64
        resign_q4k(source, 0)
    elif defect == "device_claim":
        source["belief_measurements"][0]["extra"]["device_claim_sha256"] = "0" * 64
        resign_q4k(source, 0)
    elif defect == "promotion":
        source["belief_measurements"][0]["extra"]["promotion_authority"] = True
        resign_q4k(source, 0)
    else:
        source["belief_measurements"][0]["extra"]["inside_unpack_wall_share_emitted"] = True
        resign_q4k(source, 0)
    with pytest.raises(ct.ProjectionError):
        aux.native_rows(source)


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
