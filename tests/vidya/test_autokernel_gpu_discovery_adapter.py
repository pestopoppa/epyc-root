"""The prospective GPU discovery rows are exact, non-promotable projections."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_aux_receipt as aux  # noqa: E402


def identity(tag):
    return {
        "source_commit": "0db32c06e3e550065b78311a6031ef3dd2c4f27c",
        "rocwmma_fattn": tag == "candidate", "mmq_mfma": False,
        "artifacts": {"binary": f"/build/{tag}/bin/llama-bench",
                      "binary_sha256": ("a" if tag == "anchor" else "b") * 64,
                      "libraries": {"libggml-hip.so":
                                    ("c" if tag == "anchor" else "d") * 64}},
    }


def frame():
    return {
        "backend": "llama_gpu", "recipe": "pp512-ngl99",
        "metric": "prefill_tokens_per_s", "metric_direction": "higher_better",
        "model": "/models/test.gguf", "model_sha256": "e" * 64,
        "source_commit": "0db32c06e3e550065b78311a6031ef3dd2c4f27c",
        "cpu_list": "184-191", "device": "AMD Instinct MI210",
        "architecture": "gfx90a",
    }


def producer():
    return {"producer_id": aux._GPU_PRODUCER, "path": aux._GPU_PRODUCER_PATH,
            "sha256": "f" * 64}


def run(sample):
    return {"metric": sample, "hip_residency_proved": True,
            "raw_row": {"avg_ts": sample},
            "residency": [{"owned_kfd_pids": [123]}]}


def common(receipt, samples):
    evidence = {
        "campaign_id": receipt["campaign_id"], "authority": aux._GPU_AUTHORITY,
        "frame": receipt["frame"], "sole_factor": receipt["sole_factor"],
        "samples": samples, "producer_sha256": producer()["sha256"],
    }
    return {
        "authority": aux._GPU_AUTHORITY, "non_promotable": True,
        "top_k_discovery_only": True, "promotion_authority": False,
        "production_tree_touched": False, "frame": receipt["frame"],
        "sole_factor": receipt["sole_factor"],
        "producer_id": producer()["producer_id"],
        "producer_sha256": producer()["sha256"], "evidence_basis": evidence,
        "evidence_sha256": aux._ak_content_sha256(evidence),
    }


def row(**values):
    value = dict(values)
    value["measurement_sha256"] = aux._ak_content_sha256(value)
    return value


def bank_receipt():
    samples = [100.0, 102.0, 101.0]
    receipt = {
        "schema": aux._GPU_BANK_SCHEMA, "status": "complete",
        "campaign_id": "ak-gpu-screen-r3", "authority": aux._GPU_AUTHORITY,
        "started_at": "2026-08-13T16:00:00Z", "ended_at": "2026-08-13T16:00:05Z",
        "frame": frame(),
        "sole_factor": {"name": "GGML_HIP_ROCWMMA_FATTN",
                        "anchor": "OFF", "candidate": "ON"},
        "anchor_identity": identity("anchor"),
        "candidate_identity": identity("candidate"),
        "anchor_samples": samples, "anchor_runs": [run(value) for value in samples],
        "producer": producer(),
    }
    extra = {**common(receipt, samples), "arm": "anchor",
             "build_identity": receipt["anchor_identity"],
             "arithmetic_baseline_center": 101.0}
    receipt["belief_measurements"] = [row(
        measurement_id="gpu_discovery_anchor_pp512_median_tokens_per_s",
        metric="gpu_prefill_tokens_per_s", value=101.0, unit="tokens/s",
        metric_direction="higher_better", category="BASELINE",
        protocol_id=aux._GPU_BANK_SCHEMA, reps=3,
        reps_basis="scored:three anchor-bank MI210 llama-bench invocations",
        claim=("Non-promotable GPU discovery anchor observed median pp512 throughput "
               "101 tokens/s"), extra=extra)]
    receipt["baseline_sha256"] = aux._ak_content_sha256(receipt)
    return receipt


def result_receipt():
    bank = bank_receipt()
    samples = [110.0, 112.0, 111.0]
    center = 101.0
    effects = [(value - center) / center for value in samples]
    receipt = {
        "schema": aux._GPU_RESULT_SCHEMA, "status": "complete",
        "campaign_id": bank["campaign_id"], "authority": aux._GPU_AUTHORITY,
        "started_at": bank["started_at"], "ended_at": "2026-08-13T16:00:10Z",
        "state": "decided", "ok": True, "non_promotable": True,
        "nomination": "top_k_candidate_only_not_a_keep",
        "baseline_sha256": bank["baseline_sha256"],
        "baseline_anchor_samples": bank["anchor_samples"],
        "anchor_invocations": 3, "candidate_invocations": 3,
        "baseline_center": center, "candidate_samples": samples,
        "relative_effects": effects, "median_relative": sorted(effects)[1],
        "host_noise_policy": "ordinary_host_activity_recorded_not_blocking",
        "frame": bank["frame"], "sole_factor": bank["sole_factor"],
        "candidate_identity": bank["candidate_identity"],
        "candidate_runs": [run(value) for value in samples],
        "device_sampling": {"sample_count": 2}, "hip_residency_proved": True,
        "cpu_claim_open": {"claim_id": "cpu", "cpu_list": "184-191"},
        "device_claim_open": {"claim_id": "gpu", "device_id": "mi210_0"},
        "producer": producer(),
    }
    base = {**common(receipt, samples), "arm": "candidate",
            "build_identity": receipt["candidate_identity"],
            "baseline_sha256": bank["baseline_sha256"],
            "baseline_anchor_samples": bank["anchor_samples"],
            "baseline_center": center, "hip_residency_proved": True}
    basis = "scored:three candidate-only MI210 llama-bench invocations"
    receipt["belief_measurements"] = [
        row(measurement_id="gpu_discovery_candidate_pp512_median_tokens_per_s",
            metric="gpu_prefill_tokens_per_s", value=111.0, unit="tokens/s",
            metric_direction="higher_better", category="CANDIDATE",
            protocol_id=aux._GPU_RESULT_SCHEMA, reps=3, reps_basis=basis,
            claim=("Non-promotable GPU candidate discovery observed median pp512 "
                   "throughput 111 tokens/s"), extra=base),
        row(measurement_id="gpu_discovery_candidate_pp512_median_relative_effect",
            metric="gpu_prefill_relative_effect_vs_sealed_anchor",
            value=sorted(effects)[1], unit="fraction",
            metric_direction="higher_better", category="CANDIDATE",
            protocol_id=aux._GPU_RESULT_SCHEMA, reps=3, reps_basis=basis,
            claim=("Non-promotable GPU candidate discovery observed median relative effect "
                   f"{sorted(effects)[1]:.9g} versus its sealed anchor bank"),
            extra={**base, "relative_effects": effects}),
    ]
    receipt["result_sha256"] = aux._ak_content_sha256(receipt)
    return receipt


def resign(receipt):
    field = "baseline_sha256" if receipt["schema"] == aux._GPU_BANK_SCHEMA \
        else "result_sha256"
    receipt.pop(field, None)
    receipt[field] = aux._ak_content_sha256(receipt)


def test_projects_baseline_and_candidate_rows_through_the_shared_ladder():
    bank = aux.native_rows(bank_receipt(), receipt_locator="gpu:r3/bank.json",
                           receipt_sha256="1" * 64, attestation_present=True)
    candidate = aux.native_rows(result_receipt(), receipt_locator="gpu:r3/result.json",
                                receipt_sha256="2" * 64, attestation_present=True)
    tuples = [aux.project(native) for native in (*bank, *candidate)]
    assert len(tuples) == 3
    assert [item.category for item in tuples] == ["BASELINE", "CANDIDATE", "CANDIDATE"]
    assert all(item.extra["promotion_authority"] is False for item in tuples)
    assert all(ct.grade(item)[:2] == ("Witnessed", "Attested") for item in tuples)


@pytest.mark.parametrize("defect", [
    "row", "self", "effect", "anchor_samples", "producer", "authority", "residency",
    "factor", "build",
])
def test_gpu_discovery_tampering_and_authority_upgrades_fail_closed(defect):
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
        receipt["candidate_runs"][0]["hip_residency_proved"] = False
        resign(receipt)
    elif defect == "factor":
        receipt["sole_factor"]["candidate"] = "MAYBE"
        resign(receipt)
    else:
        receipt["candidate_identity"]["rocwmma_fattn"] = False
        resign(receipt)
    with pytest.raises(ct.ProjectionError):
        aux.native_rows(receipt)


def test_pre_hook_gpu_receipts_are_not_retrofilled_on_read():
    old = {"schema": aux._GPU_RESULT_SCHEMA, "status": "complete",
           "campaign_id": "ak-gpu-screen-s2-pre-hook", "median_relative": 0.1}
    assert aux.native_rows(old) == ()
