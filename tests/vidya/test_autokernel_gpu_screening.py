"""The prospective GPU screening rows are exact, non-promotable projections."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_gpu_screening as gpu  # noqa: E402

ANCHOR_COMMIT = "0db32c06e3e550065b78311a6031ef3dd2c4f27c"
CANDIDATE_COMMIT = "5bbcc5498e4732162356953b7be96a53073a6706"


def identity(tag, *, commit=None):
    return {
        "source_commit": commit or (ANCHOR_COMMIT if tag == "anchor"
                                    else CANDIDATE_COMMIT),
        "hip_graphs": False, "rocwmma_fattn": True, "mmq_mfma": False,
        "artifacts": {"binary": f"/build/{tag}/bin/llama-bench",
                      "binary_sha256": ("a" if tag == "anchor" else "b") * 64,
                      "libraries": {"libggml-hip.so":
                                    ("c" if tag == "anchor" else "d") * 64}},
    }


def frame(*, serialized=True):
    contract = ({"schema": gpu.SERIALIZED_CONTRACT,
                 "scope": "integrity_discovery_only",
                 "production_throughput_authority": False,
                 "graph_mode": "disabled_for_integrity",
                 "scored_sample": "min(first_tokens_per_s,second_tokens_per_s)",
                 "serialization_env": {"AMD_SERIALIZE_KERNEL": "3",
                                       "AMD_SERIALIZE_COPY": "3",
                                       "GGML_CUDA_DISABLE_GRAPHS": "1"}}
                if serialized else
                {"schema": gpu.NATIVE_CONTRACT,
                 "scope": "legacy_nonpromotable_discovery",
                 "production_throughput_authority": False})
    return {
        "backend": "llama_gpu", "recipe": "tg128-ngl99",
        "metric": "decode_tokens_per_s", "metric_direction": "higher_better",
        "metric_contract": contract, "n_prompt": 512, "n_gen": 128,
        "model": "/models/test.gguf", "model_sha256": "e" * 64,
        "source_commit": CANDIDATE_COMMIT, "cpu_list": "184-191",
        "device": "AMD Instinct MI210", "architecture": "gfx90a",
    }


def factor():
    return {"name": "source_patch", "anchor": ANCHOR_COMMIT[:12],
            "candidate": CANDIDATE_COMMIT[:12]}


def producer():
    return {"producer_id": gpu.PRODUCER_ID, "path": gpu.PRODUCER_PATH,
            "sha256": "f" * 64}


def run(samples, metric):
    return {"metric": metric, "samples": list(samples),
            "sample_count": len(samples), "seed": 8613,
            "raw_row": {"avg_ts": metric},
            "residency": [{"owned_kfd_pids": [123, 456],
                           "vram_used_bytes": 1024}],
            "hip_residency_proved": True}


def common(receipt, samples):
    evidence = {
        "campaign_id": receipt["campaign_id"], "authority": gpu.AUTHORITY,
        "frame": receipt["frame"], "sole_factor": receipt["sole_factor"],
        "samples": samples, "producer_sha256": producer()["sha256"],
    }
    return {
        "authority": gpu.AUTHORITY, "non_promotable": True,
        "top_k_discovery_only": True, "promotion_authority": False,
        "production_tree_touched": False, "frame": receipt["frame"],
        "sole_factor": receipt["sole_factor"],
        "producer_id": producer()["producer_id"],
        "producer_sha256": producer()["sha256"], "evidence_basis": evidence,
        "evidence_sha256": gpu._canonical_sha(evidence),
    }


def row(**values):
    value = dict(values)
    value["measurement_sha256"] = gpu._canonical_sha(value)
    return value


def bank_receipt(*, serialized=True):
    samples = [100.0, 102.0, 101.0]
    center = 105.0 if serialized else sum(samples) / 3
    receipt = {
        "schema": gpu.BANK_SCHEMA, "status": "complete",
        "campaign_id": "ak-gpu-screen-v27", "authority": gpu.AUTHORITY,
        "started_at": "2026-08-26T12:00:00Z", "ended_at": "2026-08-26T12:00:05Z",
        "frame": frame(serialized=serialized),
        "sole_factor": factor(),
        "anchor_invocations": 3, "anchor_identity": identity("anchor"),
        "candidate_identity": identity("candidate"), "anchor_processes": 1,
        "arm_order_schedule": ["anchor", "candidate"],
        "arm_order_seed_sha256": "0" * 64,
        "anchor_samples": samples, "anchor_runs": [run(samples, center)],
        "producer": producer(),
    }
    common_row = {**common(receipt, samples), "arm": "anchor",
                  "build_identity": receipt["anchor_identity"],
                  "sealed_baseline_center": center,
                  "baseline_center_method": (
                      "tokens_per_mean_protected_latency" if serialized
                      else "arithmetic_mean_native_samples")}
    receipt["belief_measurements"] = [row(
        measurement_id="gpu_discovery_anchor_tg128_median_tokens_per_s",
        metric="gpu_decode_tokens_per_s", value=101.0, unit="tokens/s",
        metric_direction="higher_better", category="BASELINE",
        protocol_id=gpu.BANK_SCHEMA, reps=3,
        reps_basis="scored:3 anchor-bank MI210 llama-bench native repetitions",
        claim=("Non-promotable GPU discovery anchor observed median tg128 throughput "
               "101 tokens/s"), extra=common_row)]
    receipt["baseline_sha256"] = gpu._canonical_sha(receipt)
    return receipt


def result_receipt(*, bank=None, serialized=True):
    bank = bank or bank_receipt(serialized=serialized)
    samples = [110.0, 112.0, 111.0]
    center = bank["anchor_runs"][0]["metric"] if serialized else \
        sum(bank["anchor_samples"]) / 3
    effects = [(value - center) / center for value in samples]
    receipt = {
        "schema": gpu.RESULT_SCHEMA, "status": "complete",
        "campaign_id": bank["campaign_id"], "authority": gpu.AUTHORITY,
        "started_at": bank["started_at"], "ended_at": "2026-08-26T12:00:10Z",
        "state": "decided", "ok": True, "non_promotable": True,
        "nomination": gpu.NOMINATION, "promotion_claim": False,
        "baseline_sha256": bank["baseline_sha256"],
        "anchor_invocations": 3, "candidate_invocations": 3,
        "anchor_processes": 1, "candidate_processes": 1,
        "arm_order_schedule": ["anchor", "candidate"],
        "arm_order_seed_sha256": "0" * 64,
        "baseline_center": center, "candidate_samples": samples,
        "baseline_anchor_samples": bank["anchor_samples"],
        "relative_effects": effects,
        "median_relative": sorted(effects)[1],
        "host_noise_policy": "ordinary_host_activity_recorded_not_blocking",
        "cpu_overlap_policy": "cold_serialized_load_window",
        "model_size_bytes": 1234, "site_load_decision": "serialized",
        "runtime_graphs": "off",
        "frame": bank["frame"], "sole_factor": bank["sole_factor"],
        "candidate_identity": bank["candidate_identity"],
        "candidate_runs": [run(samples, samples[0])],
        "device_sampling": {"sample_count": 2},
        "hip_residency_proved": True,
        "cpu_coverage_windows": ["184-191"],
        "device_claim_open": {"claim_id": "mi210-window-v1",
                              "device_id": "mi210_0",
                              "campaign_id": "ak-discovery",
                              "acquired_at": "2026-08-26T11:59:00Z"},
        "device_claim_mode": "borrowed_outer_reservation",
        "device_claim_borrowed_phase_end": {
            "schema": "epyc.autokernel.borrowed_device_claim_phase.v1",
            "mode": "borrowed_outer_reservation",
            "outer_claim_id": "mi210-window-v1",
            "physical_release": False},
        "producer": producer(),
    }
    base = {**common(receipt, samples), "arm": "candidate",
            "build_identity": receipt["candidate_identity"],
            "baseline_sha256": bank["baseline_sha256"],
            "baseline_anchor_samples": bank["anchor_samples"],
            "baseline_center": center, "hip_residency_proved": True}
    basis = "scored:3 candidate-only MI210 llama-bench invocations"
    receipt["belief_measurements"] = [
        row(measurement_id="gpu_discovery_candidate_tg128_median_tokens_per_s",
            metric="gpu_decode_tokens_per_s", value=111.0, unit="tokens/s",
            metric_direction="higher_better", category="CANDIDATE",
            protocol_id=gpu.RESULT_SCHEMA, reps=3, reps_basis=basis,
            claim=("Non-promotable GPU candidate discovery observed median tg128 "
                   "throughput 111 tokens/s"), extra=base),
        row(measurement_id="gpu_discovery_candidate_tg128_median_relative_effect",
            metric="gpu_decode_relative_effect_vs_sealed_anchor",
            value=sorted(effects)[1], unit="fraction",
            metric_direction="higher_better", category="CANDIDATE",
            protocol_id=gpu.RESULT_SCHEMA, reps=3, reps_basis=basis,
            claim=("Non-promotable GPU candidate discovery observed median relative effect "
                   f"{sorted(effects)[1]:.9g} versus its sealed anchor bank"),
            extra={**base, "relative_effects": effects}),
    ]
    receipt["result_sha256"] = gpu._canonical_sha(receipt)
    return receipt


def resign(receipt):
    field = "baseline_sha256" if receipt["schema"] == gpu.BANK_SCHEMA \
        else "result_sha256"
    receipt.pop(field, None)
    receipt[field] = gpu._canonical_sha(receipt)


def test_projects_baseline_and_candidate_rows_through_the_shared_ladder():
    bank = gpu.native_rows(bank_receipt(), receipt_locator="gpu:v27/baseline-bank.json",
                           receipt_sha256="1" * 64, attestation_present=True)
    candidate = gpu.native_rows(
        result_receipt(), receipt_locator="gpu:v27/result.json",
        receipt_sha256="2" * 64, attestation_present=True)
    tuples = [gpu.project(native) for native in (*bank, *candidate)]
    assert len(tuples) == 3
    assert [item.category for item in tuples] == ["BASELINE", "CANDIDATE", "CANDIDATE"]
    assert [item.protocol_id for item in tuples] == [
        gpu.BANK_SCHEMA, gpu.RESULT_SCHEMA, gpu.RESULT_SCHEMA]
    assert [item.reps for item in tuples] == [3, 3, 3]
    assert all(item.extra["promotion_authority"] is False for item in tuples)
    assert all(item.extra["authority"] == gpu.AUTHORITY for item in tuples)
    assert all(item.attestation_locator for item in tuples)
    assert len({item.measurement_id for item in tuples}) == 3
    assert all(ct.grade(item)[:2] == ("Witnessed", "Attested") for item in tuples)


def test_native_contract_baseline_center_rederives_from_anchor_samples():
    bank = gpu.native_rows(bank_receipt(serialized=False),
                           receipt_locator="gpu:v27/native-baseline-bank.json",
                           receipt_sha256="3" * 64, attestation_present=True)
    assert len(bank) == 1
    assert bank[0]["measurement"]["extra"]["sealed_baseline_center"] == 101.0
    assert bank[0]["measurement"]["extra"]["baseline_center_method"] == \
        "arithmetic_mean_native_samples"
    result = gpu.native_rows(result_receipt(serialized=False),
                             receipt_locator="gpu:v27/native-result.json",
                             receipt_sha256="4" * 64, attestation_present=True)
    assert len(result) == 2
    assert all(ct.grade(gpu.project(native))[:2] == ("Witnessed", "Attested")
               for native in (*bank, *result))


def test_pre_hook_s2_screen_emits_zero_rows_not_retrofilled_on_read():
    old = {"schema": gpu.RESULT_SCHEMA, "status": "complete",
           "campaign_id": "ak-gpu-screen-s2-pre-hook", "median_relative": 0.1}
    assert gpu.native_rows(old) == ()


def test_historical_v1_screens_emit_zero_rows_always():
    bank_v1 = {"schema": "epyc.autokernel.gpu_screening_baseline.v1",
               "status": "complete", "campaign_id": "ak-gpu-mmq-mfma-screen-20260813-s2"}
    result_v1 = {"schema": "epyc.autokernel.gpu_candidate_only_screen.v1",
                 "status": "complete", "campaign_id": "ak-gpu-mmq-mfma-screen-20260813-s2",
                 "median_relative": 0.1}
    assert gpu.native_rows(bank_v1) == ()
    assert gpu.native_rows(result_v1) == ()


def test_missing_residency_is_refused():
    receipt = result_receipt()
    receipt["candidate_runs"][0].pop("residency", None)
    resign(receipt)
    with pytest.raises(ct.ProjectionError):
        gpu.native_rows(receipt)


def test_unproved_hip_residency_is_refused():
    receipt = result_receipt()
    receipt["candidate_runs"][0]["hip_residency_proved"] = False
    resign(receipt)
    with pytest.raises(ct.ProjectionError):
        gpu.native_rows(receipt)


def test_no_owned_kfd_pid_or_vram_delta_is_refused():
    receipt = result_receipt()
    receipt["candidate_runs"][0]["residency"] = [
        {"owned_kfd_pids": [], "vram_used_bytes": 0}]
    resign(receipt)
    with pytest.raises(ct.ProjectionError):
        gpu.native_rows(receipt)


@pytest.mark.parametrize("defect", [
    "row", "self", "effect", "anchor_samples", "producer", "authority",
    "residency", "factor", "build", "center", "nomination", "claim_open",
    "borrowed_release",
])
def test_screen_tampering_and_authority_upgrades_fail_closed(defect):
    receipt = result_receipt()
    if defect == "row":
        receipt["belief_measurements"][0]["value"] += 1
        resign(receipt)
    elif defect == "self":
        receipt["result_sha256"] = "0" * 64
    elif defect == "effect":
        receipt["median_relative"] += 0.1
        resign(receipt)
    elif defect == "anchor_samples":
        receipt["baseline_anchor_samples"][0] = 1.0
        resign(receipt)
    elif defect == "producer":
        receipt["producer"]["producer_id"] = "invented"
        resign(receipt)
    elif defect == "authority":
        receipt["belief_measurements"][0]["extra"]["promotion_authority"] = True
        resign(receipt)
    elif defect == "residency":
        receipt["candidate_runs"][0]["residency"] = [
            {"owned_kfd_pids": [123], "vram_used_bytes": 0}]
        resign(receipt)
    elif defect == "factor":
        receipt["sole_factor"]["candidate"] = "MAYBE"
        resign(receipt)
    elif defect == "build":
        receipt["candidate_identity"]["mmq_mfma"] = True
        resign(receipt)
    elif defect == "center":
        receipt["baseline_center"] = 1.0
        resign(receipt)
    elif defect == "nomination":
        receipt["nomination"] = "top_k_candidate_only_keep_me"
        resign(receipt)
    elif defect == "claim_open":
        receipt["device_claim_open"] = {}
        resign(receipt)
    else:
        receipt["device_claim_borrowed_phase_end"]["physical_release"] = True
        resign(receipt)
    with pytest.raises(ct.ProjectionError):
        gpu.native_rows(receipt)


def test_pre_hook_artifact_with_fabricated_rows_is_refused():
    receipt = result_receipt()
    receipt["belief_measurements"] = [dict(receipt["belief_measurements"][0])]
    receipt["belief_measurements"][0]["extra"]["promotion_authority"] = True
    resign(receipt)
    with pytest.raises(ct.ProjectionError):
        gpu.native_rows(receipt)


def test_unsupported_schema_and_bad_receipt_sha_fail_closed():
    with pytest.raises(ct.ProjectionError):
        gpu.native_rows({"schema": "epyc.autokernel.some_other.v1"})
    with pytest.raises(ct.ProjectionError):
        gpu.native_rows(bank_receipt(), receipt_sha256="z" * 64)


def test_project_refuses_non_object_native_rows():
    with pytest.raises(ct.ProjectionError):
        gpu.project(None)
    with pytest.raises(ct.ProjectionError):
        gpu.project({"receipt": {}, "measurement": {}})


def test_fixtures_are_self_consistent_against_the_producer_contract():
    bank = bank_receipt()
    assert bank["schema"] == gpu.BANK_SCHEMA
    assert gpu._canonical_sha(
        {key: value for key, value in bank.items() if key != "baseline_sha256"}
    ) == bank["baseline_sha256"]
    result = result_receipt(bank=bank)
    assert result["baseline_sha256"] == bank["baseline_sha256"]
    assert gpu._canonical_sha(
        {key: value for key, value in result.items() if key != "result_sha256"}
    ) == result["result_sha256"]
    assert result["median_relative"] == sorted([
        (value - result["baseline_center"]) / result["baseline_center"]
        for value in result["candidate_samples"]])[1]
