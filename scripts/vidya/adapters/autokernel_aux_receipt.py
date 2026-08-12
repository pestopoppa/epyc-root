"""Project prospective AutoKernel auxiliary-receipt measurements into ClaimTuple.

The adapter reads only the producer-written ``belief_measurements`` vector. Older receipts yield no
rows: reconstructing tuples from their prose or profiler payload would invent write-time provenance.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import statistics
import sys
from datetime import datetime
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
    "epyc.autokernel.q4k_unpack_attribution.v1",
    "epyc.autokernel.iq2_xxs_model_confirmation.v1",
    "epyc.autokernel.p2_5j_placement_receipt.v1",
    "epyc.autokernel.hip_authoring_roundtrip.v1",
    "epyc.autokernel.hip_decision_grade.v1",
    "epyc.autokernel.arena_controller_evaluation.v1",
})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_ARENA_SCHEMA = "epyc.autokernel.geak_arena_roundtrip.v1"
_ARENA_PRODUCER = "autokernel.controller.arena_roundtrip/v1"
_ARENA_INTERMEDIATE_SCHEMA = "epyc.autokernel.arena_controller_evaluation.v1"
_ARENA_INTERMEDIATE_PRODUCER = (
    "autokernel.controller.arena_cell_runner/intermediate_evaluation_v1")
_ARENA_INTERMEDIATE_PRODUCER_PATH = (
    "scripts/kernel_rnd/autokernel/controller/arena_cell_runner.py")
_ARENA_INTERMEDIATE_WINDOW_SCHEMA = (
    "epyc.autokernel.arena_gpu_measurement_window.v1")
_HIP_SCHEMA = "epyc.autokernel.hip_authoring_roundtrip.v1"
_HIP_PRODUCER = "autokernel.controller.hip_authoring_arm/v1"
_HIP_PRODUCER_PATH = "scripts/kernel_rnd/autokernel/controller/hip_authoring_arm.py"
_HIP_TASK_SCHEMA = "epyc.autokernel.hip_authoring_task_audit.v1"
_HIP_WINDOW_SCHEMA = "epyc.autokernel.hip_authoring_gpu_window.v1"
_HIP_VENDOR_COMMIT = "2dbbf1d3f676b948c04c339de50516fe80ed4ab9"
_HIP_DECISION_SCHEMA = "epyc.autokernel.hip_decision_grade.v1"
_HIP_DECISION_PRODUCER = "autokernel.controller.hip_decision_grade/v1"
_HIP_DECISION_AUTHORITY = "task_local_rank_no_release_or_promotion_authority"
_HIP_DECISION_PROVIDER = "torch_rocm_compile"
_HIP_DECISION_DURATION_FLOOR_NS = 250_090_903
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
_IQ2_MODEL_SCHEMA = "epyc.autokernel.iq2_xxs_model_confirmation.v1"
_IQ2_MODEL_PRODUCER = "autokernel.iq2_xxs_model_beliefs/v1"
_IQ2_RAW_SCHEMA = "epyc.autokernel.microbench_raw_vector.v1"
_IQ2_EVENT_SCHEMA = "epyc.autokernel.evaluation_event.v5"
_IQ2_CANDIDATE_SCHEMA = "epyc.autokernel.candidate.v1"
_IQ2_CLAIM_SCHEMA = "epyc.autokernel.cpu_region_claim_receipt.v1"
_IQ2_QUANTIZATION = "IQ2_XXS"
_IQ2_LANES = {
    "tg": ("t1b.llama_cpu.llama_bench_decode.v1", "decode_tokens_per_s"),
    "pp": ("t1b.llama_cpu.llama_bench_prefill.v1", "prefill_tokens_per_s"),
}
_IQ2_T1_TIERS = frozenset({"T1", "T1a", "T1b", "T1c"})
_IQ2_RECEIPT_IDENTITY_FIELDS = (
    "runner_id", "registry_id", "arm", "binary_path", "binary_sha256",
    "binary_size", "source_root", "library_path",
)
_P2_SCHEMA = "epyc.autokernel.p2_5j_placement_receipt.v1"
_P2_PRODUCER = "scripts.benchmark.autokernel_p2_5j_receipt/v1"
_P2_PRODUCER_PATH = "scripts/benchmark/autokernel_p2_5j_receipt.py"
_P2_AUTHORITY = (
    "observation_only_placement_context_no_selection_speedup_carve_or_activation")
_P2_REPS_BASIS = "scored:ten randomized complete four-arm placement blocks"
_P2_ARMS = {
    "I": ("184-191", "q3", 3, "cross_node", "incumbent", "BASELINE"),
    "H": ("88-95", "q3", 3, "cross_node", "historical_physical", "BASELINE"),
    "Lp": ("40-47", "q1", 1, "device_local", "local_physical", "CANDIDATE"),
    "Ls": ("136-143", "q1", 1, "device_local", "local_smt", "CANDIDATE"),
}
_P2_METRICS = {
    "decode_tps": (
        "aggregate_decode_tokens_per_second", "tokens/s", "higher_better",
        "median_decode_tps", "aggregate_decode_tps", "placement_observation",
    ),
    "p50_latency_ms": (
        "request_latency_p50_ms", "ms", "lower_better",
        "median_p50_latency_ms", "p50_latency_ms", "placement_observation",
    ),
    "p95_latency_ms": (
        "request_latency_p95_ms", "ms", "lower_better",
        "median_p95_latency_ms", "p95_latency_ms", "placement_observation",
    ),
    "paired_ratio_to_incumbent": (
        "paired_decode_ratio_to_incumbent", "ratio", "higher_better",
        "median_paired_ratio_to_incumbent", "paired_ratios_to_incumbent",
        "placement_comparison",
    ),
}


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _ak_content_sha256(value: Any) -> str:
    """Match AutoKernel schemas.content_hash without changing older producers."""
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _arena_receipt_identity(receipt: dict) -> str:
    """Return the immutable Arena observation identity, not its logical campaign.

    A campaign id names the matched matrix and is intentionally reused when an
    interrupted campaign is restarted under a new output root.  It therefore
    cannot identify an observation: r3 and r4, as well as every task/controller/
    checkpoint inside either attempt, share it.  The producer's self digest
    binds the exact task, controller, checkpoint, artifacts and time interval.
    """
    if (receipt.get("producer_id") != _ARENA_PRODUCER
            or receipt.get("authority") != "diagnostic_only"):
        raise ProjectionError("Arena receipt lacks its producer or authority identity")
    claimed = _sha(receipt.get("receipt_sha256"), "receipt.receipt_sha256")
    logical = {key: value for key, value in receipt.items()
               if key != "receipt_sha256"}
    if _canonical_sha256(logical) != claimed:
        raise ProjectionError("Arena receipt_sha256 does not bind the logical receipt")
    task = receipt.get("task")
    source = receipt.get("source")
    if (not isinstance(task, dict)
            or not isinstance(task.get("task_id"), str)
            or not isinstance(task.get("controller_id"), str)
            or not isinstance(source, dict)
            or isinstance(source.get("checkpoint_hours"), bool)
            or not isinstance(source.get("checkpoint_hours"), (int, float))):
        raise ProjectionError("Arena receipt lacks task/controller/checkpoint identity")
    return claimed


def _arena_intermediate_receipt_identity(receipt: dict) -> str:
    """Strictly re-derive one prospective controller-feedback observation."""
    if receipt.get("authority") != "controller_feedback_only":
        raise ProjectionError("intermediate Arena receipt exceeds feedback-only authority")
    claimed = _sha(receipt.get("receipt_sha256"), "receipt.receipt_sha256")
    logical = {key: value for key, value in receipt.items()
               if key != "receipt_sha256"}
    if _canonical_sha256(logical) != claimed:
        raise ProjectionError("intermediate Arena receipt_sha256 does not bind the receipt")

    campaign_id = _text(receipt, "campaign_id", "receipt")
    claim_campaign_id = _text(receipt, "claim_campaign_id", "receipt")
    task_id = _text(receipt, "task_id", "receipt")
    arm_id = _text(receipt, "arm_id", "receipt")
    checkpoint = receipt.get("checkpoint_hours")
    ordinal = receipt.get("evaluation_ordinal")
    if (isinstance(checkpoint, bool) or not isinstance(checkpoint, (int, float))
            or not math.isfinite(checkpoint) or checkpoint <= 0
            or isinstance(ordinal, bool) or not isinstance(ordinal, int)
            or ordinal < 1):
        raise ProjectionError("intermediate Arena checkpoint/ordinal identity is invalid")
    attempt_id = receipt.get("attempt_id")
    if attempt_id is not None and (not isinstance(attempt_id, str) or not attempt_id):
        raise ProjectionError("intermediate Arena attempt_id is invalid")
    source = receipt.get("source_sha256")
    if (not isinstance(source, dict) or not source
            or any(not isinstance(path, str) or not path
                   or not isinstance(digest, str) or not _SHA256.fullmatch(digest)
                   for path, digest in source.items())):
        raise ProjectionError("intermediate Arena source identity is malformed")
    baseline_sha = _sha(
        receipt.get("baseline_receipt_sha256"), "baseline_receipt_sha256")

    producer = receipt.get("producer")
    if (not isinstance(producer, dict)
            or producer.get("producer_id") != _ARENA_INTERMEDIATE_PRODUCER
            or producer.get("path") != _ARENA_INTERMEDIATE_PRODUCER_PATH):
        raise ProjectionError("intermediate Arena producer identity differs")
    producer_sha = _sha(producer.get("sha256"), "producer.sha256")

    evaluation = receipt.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ProjectionError("intermediate Arena evaluation must be an object")
    valid_cases = evaluation.get("valid_optimized_cases")
    if (isinstance(valid_cases, bool) or not isinstance(valid_cases, int)
            or valid_cases < 0):
        raise ProjectionError("intermediate Arena valid case count is invalid")
    passed_correctness = int(
        bool(evaluation.get("pass_compilation"))
        and bool(evaluation.get("pass_correctness")))

    window = receipt.get("measurement_window")
    if not isinstance(window, dict):
        raise ProjectionError("intermediate Arena measurement window must be an object")
    window_sha = _sha(window.get("receipt_sha256"), "measurement_window.receipt_sha256")
    window_unsigned = {key: value for key, value in window.items()
                       if key != "receipt_sha256"}
    if _canonical_sha256(window_unsigned) != window_sha:
        raise ProjectionError("intermediate Arena measurement-window digest is invalid")
    if (window.get("schema") != _ARENA_INTERMEDIATE_WINDOW_SCHEMA
            or window.get("status") != "complete"
            or window.get("phase") != "controller_intermediate_evaluation"
            or window.get("failure") is not None
            or window.get("gpu_action_executed_only_while_claim_held") is not True
            or window.get("campaign_id") != campaign_id
            or window.get("claim_campaign_id") != claim_campaign_id
            or window.get("task_id") != task_id
            or window.get("arm_id") != arm_id
            or window.get("checkpoint_hours") != checkpoint
            or window.get("ordinal") != ordinal):
        raise ProjectionError("intermediate Arena measurement-window identity differs")
    opened = window.get("device_claim_open")
    released = window.get("device_claim_released")
    if (not isinstance(opened, dict) or not isinstance(released, dict)
            or opened.get("claim_id") != released.get("claim_id")
            or opened.get("campaign_id") != claim_campaign_id
            or released.get("campaign_id") != claim_campaign_id
            or opened.get("device_id") != "mi210_0"
            or released.get("device_id") != "mi210_0"
            or opened.get("released_at") is not None
            or not isinstance(released.get("released_at"), str)
            or not released["released_at"]):
        raise ProjectionError("intermediate Arena device claim is not exact and released")
    sampler = window.get("device_sampling")
    if not isinstance(sampler, dict):
        raise ProjectionError("intermediate Arena sampling receipt is missing")
    sampler_sha = _sha(sampler.get("sha256"), "device_sampling.sha256")
    if _canonical_sha256({key: value for key, value in sampler.items()
                          if key != "sha256"}) != sampler_sha:
        raise ProjectionError("intermediate Arena sampling digest is invalid")
    samples = sampler.get("samples")
    if (isinstance(sampler.get("sample_count"), bool)
            or sampler.get("sample_count") != len(samples or ())
            or not isinstance(samples, list) or not samples):
        raise ProjectionError("intermediate Arena sampling evidence is incomplete")

    shared = {
        "measurement_role": "kernel_authoring_intermediate_evaluation",
        "campaign_id": campaign_id,
        **({"attempt_id": attempt_id} if attempt_id is not None else {}),
        "claim_campaign_id": claim_campaign_id,
        "task_id": task_id,
        "controller_id": arm_id,
        "checkpoint_hours": checkpoint,
        "evaluation_ordinal": ordinal,
        "source_sha256": dict(sorted(source.items())),
        "baseline_receipt_sha256": baseline_sha,
        "measurement_window_sha256": window_sha,
        "producer_id": _ARENA_INTERMEDIATE_PRODUCER,
        "producer_path": _ARENA_INTERMEDIATE_PRODUCER_PATH,
        "producer_sha256": producer_sha,
        "authority": "diagnostic_only_no_ranking_or_promotion_authority",
    }
    expected = []
    for measurement_id, metric, value, role, claim in (
        ("arena_intermediate_correctness_pass_rate",
         "geak_arena_intermediate_correctness_pass_rate", passed_correctness,
         "kernel_authoring_intermediate_correctness",
         "Whether this brokered intermediate candidate passed compilation and correctness"),
        ("arena_intermediate_timing_harness_validity_rate",
         "geak_arena_intermediate_timing_harness_validity_rate",
         int(valid_cases > 0), "kernel_authoring_intermediate_timing_validity",
         "Whether this brokered intermediate evaluation admitted any optimized timing case"),
    ):
        row = {
            "measurement_id": measurement_id, "metric": metric,
            "value": float(value), "unit": "fraction",
            "metric_direction": "higher_better", "category": "CANDIDATE",
            "claim": claim, "reps": 1,
            "reps_basis": "one brokered AgentKernelArena intermediate evaluation",
            "extra": {**shared, "measurement_role": role, "passed": value,
                      "total": 1},
        }
        row["measurement_sha256"] = _canonical_sha256(row)
        expected.append(row)
    if receipt.get("belief_measurements") != expected:
        raise ProjectionError("intermediate Arena belief rows do not rederive from evidence")
    return claimed


def _hip_receipt_identity(receipt: dict) -> str:
    """Re-derive the observation-only raw-HIP receipt and its two native rows."""
    if receipt.get("authority") != "observation_only" or receipt.get("status") != "complete":
        raise ProjectionError("HIP receipt must be a complete observation-only record")
    campaign_id = _iq2_text(receipt.get("campaign_id"), "campaign_id")
    started = _iq2_instant(receipt.get("started_at"), "started_at")
    ended = _iq2_instant(receipt.get("ended_at"), "ended_at")
    if ended < started:
        raise ProjectionError("HIP receipt ended before it started")
    producer = receipt.get("producer")
    if (not isinstance(producer, dict)
            or producer.get("producer_id") != _HIP_PRODUCER
            or producer.get("path") != _HIP_PRODUCER_PATH):
        raise ProjectionError("HIP receipt lacks its exact producer identity")
    _sha(producer.get("sha256"), "producer.sha256")
    claimed = _sha(receipt.get("receipt_sha256"), "receipt.receipt_sha256")
    logical = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if _canonical_sha256(logical) != claimed:
        raise ProjectionError("HIP receipt_sha256 does not bind the logical receipt")

    task = receipt.get("task")
    vendor = task.get("vendor_identity") if isinstance(task, dict) else None
    if (not isinstance(task, dict) or task.get("schema") != _HIP_TASK_SCHEMA
            or task.get("task_type") != "torch2hip"
            or not re.fullmatch(r"torch2hip/[a-z0-9_-]+/[A-Za-z0-9_-]+",
                                str(task.get("task_id", "")))
            or not str(task.get("target_file", "")).endswith(".hip")
            or task.get("target") != {"gpu_model": "MI210", "gfx_arch": "gfx90a"}
            or not isinstance(vendor, dict) or vendor.get("clean") is not True
            or vendor.get("commit") != _HIP_VENDOR_COMMIT):
        raise ProjectionError("HIP receipt lacks its exact Torch2HIP task/vendor binding")
    files = task.get("file_sha256")
    if (not isinstance(files, dict) or not files
            or any(not isinstance(path, str) or not path or not _SHA256.fullmatch(str(digest))
                   for path, digest in files.items())):
        raise ProjectionError("HIP task file manifest is malformed")
    hardware = receipt.get("hardware")
    if (not isinstance(hardware, dict)
            or hardware.get("architectures") != ["gfx90a"]
            or hardware.get("target_gfx_arch") != "gfx90a"
            or hardware.get("target_gpu_model") != "MI210"):
        raise ProjectionError("HIP receipt does not bind the physical gfx90a target")
    candidate = receipt.get("candidate")
    candidate_sha = _sha(
        candidate.get("sha256") if isinstance(candidate, dict) else None,
        "candidate.sha256")
    evaluation = receipt.get("evaluation")
    if (not isinstance(evaluation, dict)
            or evaluation.get("compiled") is not True
            or evaluation.get("correct") is not True
            or evaluation.get("speedup_rankable") is not False
            or evaluation.get("profiler_metrics") != {}
            or set(evaluation.get("integrity_flags", ())) != {
                "public_shapes_only", "honest_vendor_baseline_not_bound"}):
        raise ProjectionError("HIP evaluation exceeds or lacks its observation-only boundary")
    correctness_cases = evaluation.get("public_correctness_cases")
    timing_cases = evaluation.get("valid_baseline_cases")
    if (isinstance(correctness_cases, bool) or not isinstance(correctness_cases, int)
            or correctness_cases < 1 or isinstance(timing_cases, bool)
            or not isinstance(timing_cases, int) or not 0 < timing_cases <= correctness_cases):
        raise ProjectionError("HIP evaluation case counts are invalid")
    constraints = receipt.get("constraints")
    if (not isinstance(constraints, dict)
            or constraints.get("performance_claim") is not False
            or constraints.get("promotion_authority") is not False
            or constraints.get("production_tree_touched") is not False
            or constraints.get("frozen_kernel_built") is not False):
        raise ProjectionError("HIP receipt invents performance, promotion, or production authority")

    windows = receipt.get("measurement_windows")
    if not isinstance(windows, list) or [item.get("phase") for item in windows
            if isinstance(item, dict)] != ["vendor_baseline", "centralized_final_evaluation"]:
        raise ProjectionError("HIP receipt requires the exact two measurement windows")
    claim_ids = []
    for window in windows:
        unsigned = {key: value for key, value in window.items() if key != "receipt_sha256"}
        if (_sha(window.get("receipt_sha256"), "window.receipt_sha256")
                != _canonical_sha256(unsigned)):
            raise ProjectionError("HIP measurement-window digest is invalid")
        if (window.get("schema") != _HIP_WINDOW_SCHEMA or window.get("status") != "complete"
                or window.get("campaign_id") != campaign_id
                or window.get("task_id") != task["task_id"]
                or window.get("gpu_action_executed_only_while_claim_held") is not True):
            raise ProjectionError("HIP measurement window changes task, campaign, or claim scope")
        opened, released, sampling = (window.get("device_claim_open"),
                                      window.get("device_claim_released"),
                                      window.get("device_sampling"))
        if not isinstance(opened, dict) or not isinstance(released, dict):
            raise ProjectionError("HIP measurement window lacks claim receipts")
        if (opened.get("claim_id") != released.get("claim_id")
                or opened.get("device_id") != "mi210_0"
                or opened.get("campaign_id") != campaign_id
                or not isinstance(released.get("released_at"), str)
                or not released.get("released_at")):
            raise ProjectionError("HIP measurement window lacks a released MI210 claim")
        claim_ids.append(opened["claim_id"])
        if not isinstance(sampling, dict) or sampling.get("sample_count", 0) < 1:
            raise ProjectionError("HIP measurement window lacks device samples")
        sampler_unsigned = {key: value for key, value in sampling.items() if key != "sha256"}
        if _sha(sampling.get("sha256"), "device_sampling.sha256") != _canonical_sha256(
                sampler_unsigned):
            raise ProjectionError("HIP device-sampling digest is invalid")
    if len(set(claim_ids)) != 2:
        raise ProjectionError("HIP baseline and final evaluation must use distinct claims")

    common = {"unit": "fraction", "metric_direction": "higher_better",
              "category": "CANDIDATE", "reps_basis": "scored_public_cases"}
    expected = [
        {"measurement_id": "hip_public_correctness_pass_rate",
         "metric": "autokernel_hip_public_correctness_pass_rate", "value": 1.0,
         "claim": "Fraction of scored public Torch2HIP correctness cases that passed",
         "reps": correctness_cases, **common,
         "extra": {"measurement_role": "raw_hip_authoring_correctness",
                   "passed": correctness_cases, "total": correctness_cases,
                   "candidate_source_sha256": candidate_sha,
                   "authority": "observation_only"}},
        {"measurement_id": "hip_timing_harness_validity_rate",
         "metric": "autokernel_hip_timing_harness_validity_rate",
         "value": timing_cases / correctness_cases,
         "claim": "Fraction of scored Torch2HIP timing cases admitted as valid",
         "reps": correctness_cases, **common,
         "extra": {"measurement_role": "raw_hip_timing_validity",
                   "passed": timing_cases, "total": correctness_cases,
                   "candidate_source_sha256": candidate_sha,
                   "authority": "observation_only"}},
    ]
    if receipt.get("belief_measurements") != expected:
        raise ProjectionError("HIP belief rows do not exactly rederive from native evidence")
    return claimed


def _hip_decision_receipt_identity(receipt: dict) -> str:
    """Strictly rederive the sealed HIP task-local decision receipt."""
    if (receipt.get("status") != "complete"
            or receipt.get("authority") != _HIP_DECISION_AUTHORITY):
        raise ProjectionError("HIP decision receipt lacks complete task-local authority")
    claimed = _sha(receipt.get("receipt_sha256"), "receipt.receipt_sha256")
    logical = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if _canonical_sha256(logical) != claimed:
        raise ProjectionError("HIP decision receipt_sha256 does not bind the receipt")
    campaign_id = _iq2_text(receipt.get("campaign_id"), "campaign_id")
    producer = receipt.get("producer")
    if (not isinstance(producer, dict)
            or producer.get("producer_id") != _HIP_DECISION_PRODUCER
            or not str(producer.get("path", "")).endswith(
                "/scripts/kernel_rnd/autokernel/controller/hip_decision_grade.py")):
        raise ProjectionError("HIP decision receipt lacks its exact producer")
    _sha(producer.get("sha256"), "producer.sha256")
    candidate = receipt.get("candidate")
    if (not isinstance(candidate, dict)
            or candidate.get("unchanged_at_terminal") is not True):
        raise ProjectionError("HIP decision candidate was not sealed through terminal reduction")
    _sha(candidate.get("sha256"), "candidate.sha256")
    task = receipt.get("task")
    vendor = task.get("vendor_identity") if isinstance(task, dict) else None
    if (not isinstance(task, dict) or task.get("schema") != _HIP_TASK_SCHEMA
            or task.get("task_id") != "torch2hip/gpumode/16636_SiLU"
            or task.get("target") != {"gpu_model": "MI210", "gfx_arch": "gfx90a"}
            or not isinstance(vendor, dict) or vendor.get("clean") is not True
            or vendor.get("commit") != _HIP_VENDOR_COMMIT):
        raise ProjectionError("HIP decision receipt changes the task or vendor identity")
    suite = receipt.get("sealed_suite")
    cases = suite.get("cases") if isinstance(suite, dict) else None
    if (not isinstance(suite, dict)
            or suite.get("suite_id") != "sealed_silu_boundary_host_double/v1"
            or suite.get("suite_seed_generated_after_candidate_seal") is not True
            or suite.get("exact_shapes_disclosed_after_candidate_seal") is not True
            or not isinstance(cases, list) or len(cases) != 24
            or len({(tuple(row.get("shape", ())), row.get("distribution"))
                    for row in cases if isinstance(row, dict)}) != 24):
        raise ProjectionError("HIP decision sealed hostile suite is incomplete")
    correctness = receipt.get("correctness")
    correctness_cases = correctness.get("cases") if isinstance(correctness, dict) else None
    if (not isinstance(correctness, dict)
            or correctness.get("oracle") != "independent_host_double_stable_silu/v1"
            or correctness.get("all_passed") is not True
            or correctness.get("passed") != 24 or correctness.get("total") != 24
            or correctness.get("bitwise_repeatability_required") is not True
            or correctness.get("two_distinct_output_poisons") != ["nan", -12345.25]
            or not isinstance(correctness_cases, list) or len(correctness_cases) != 24
            or any(row.get("passed") is not True for row in correctness_cases)):
        raise ProjectionError("HIP decision correctness does not rederive as 24/24")
    integrity = receipt.get("integrity")
    static = integrity.get("static_scan") if isinstance(integrity, dict) else None
    sandboxes = integrity.get("sandbox") if isinstance(integrity, dict) else None
    if (not isinstance(integrity, dict) or integrity.get("clean") is not True
            or integrity.get("candidate_never_received_expected_outputs") is not True
            or not isinstance(static, dict) or static.get("clean") is not True
            or static.get("findings") != [] or not isinstance(sandboxes, dict)
            or set(sandboxes) != {"compile", "correctness", "timing"}):
        raise ProjectionError("HIP decision C6 integrity is incomplete")
    expected_devices = {
        "compile": [],
        "correctness": ["/dev/kfd", "/dev/dri/renderD128"],
        "timing": ["/dev/kfd", "/dev/dri/renderD128"],
    }
    for phase, record in sandboxes.items():
        activation = record.get("activation") if isinstance(record, dict) else None
        teardown = record.get("teardown") if isinstance(record, dict) else None
        if (not isinstance(activation, dict) or activation.get("euid") == 0
                or activation.get("writable_device_paths") != expected_devices[phase]
                or not isinstance(teardown, dict)
                or teardown.get("verified_empty") is not True
                or teardown.get("removed") is not True):
            raise ProjectionError("HIP decision sandbox activation/teardown is incomplete")

    timing = receipt.get("timing")
    provider = timing.get("provider") if isinstance(timing, dict) else None
    blocks = timing.get("blocks") if isinstance(timing, dict) else None
    admission = timing.get("ranked_duration_admission") if isinstance(timing, dict) else None
    e_process = timing.get("e_process") if isinstance(timing, dict) else None
    if (not isinstance(provider, dict) or provider.get("provider_id") != _HIP_DECISION_PROVIDER
            or provider.get("expression") != "x * torch.sigmoid(x)"
            or provider.get("backend") != "inductor"
            or provider.get("fullgraph") is not True or provider.get("dynamic") is not False
            or provider.get("graph_count") != 1 or provider.get("graph_break_count") != 0
            or not isinstance(provider.get("implementation_identity"), dict)):
        raise ProjectionError("HIP decision lacks the exact Torch-ROCm-compile provider")
    _sha(provider["implementation_identity"].get("tree_sha256"),
         "provider.implementation_identity.tree_sha256")
    if (not isinstance(blocks, list) or len(blocks) != 20
            or timing.get("block_count") != 20
            or timing.get("repetitions_per_arm") != 30_000):
        raise ProjectionError("HIP decision lacks 20 complete paired timing blocks")
    speedups = []
    for index, block in enumerate(blocks):
        if (not isinstance(block, dict) or block.get("block_index") != index
                or block.get("order") not in {"anchor_first", "candidate_first"}):
            raise ProjectionError("HIP decision timing order/block identity is malformed")
        candidate_ns = block.get("candidate_ns")
        anchor_ns = block.get("anchor_ns")
        candidate_duration = block.get("candidate_measured_duration_ns")
        anchor_duration = block.get("anchor_measured_duration_ns")
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) or value <= 0 for value in (
                   candidate_ns, anchor_ns, candidate_duration, anchor_duration)):
            raise ProjectionError("HIP decision timing block contains an invalid duration")
        if min(candidate_duration, anchor_duration) < _HIP_DECISION_DURATION_FLOOR_NS:
            raise ProjectionError("HIP decision carries a sub-floor ranked arm")
        speedups.append(anchor_ns / candidate_ns)
    if (not isinstance(admission, dict) or admission.get("all_arms_passed") is not True
            or admission.get("minimum_ns") != _HIP_DECISION_DURATION_FLOOR_NS
            or admission.get("minimum_observed_ns") != min(
                min(row["candidate_measured_duration_ns"], row["anchor_measured_duration_ns"])
                for row in blocks)
            or not isinstance(admission.get("checks"), list)
            or len(admission["checks"]) != 40
            or any(check.get("outcome") != "PASS" for check in admission["checks"])):
        raise ProjectionError("HIP decision duration admission does not rederive per arm")
    expected_speedup = statistics.median(speedups)
    if timing.get("median_speedup") != expected_speedup:
        raise ProjectionError("HIP decision median speedup does not rederive from blocks")
    if (not isinstance(e_process, dict)
            or e_process.get("construction_id") != "sign_martingale_predictable_lambda/v1"
            or e_process.get("threshold") != 20.0
            or e_process.get("first_crossing_block") != 9
            or e_process.get("signs") != [1.0] * 20
            or timing.get("candidate_beats_exact_provider") is not True):
        raise ProjectionError("HIP decision e-process/rank conclusion is incomplete")
    decision = receipt.get("decision")
    constraints = receipt.get("constraints")
    if (not isinstance(decision, dict)
            or decision.get("rankable_against_exact_task_local_provider") is not True
            or decision.get("candidate_beats_exact_provider") is not True
            or decision.get("release_or_promotion_authority") is not False
            or decision.get("experimental_llama_integration_required_before_any_release") is not True
            or not isinstance(constraints, dict)
            or constraints.get("production_tree_touched") is not False
            or constraints.get("frozen_kernel_built") is not False
            or constraints.get("promotion_authority") is not False
            or constraints.get("shared_rocm_mutated") is not False):
        raise ProjectionError("HIP decision exceeds its task-local/no-release boundary")

    windows = receipt.get("measurement_windows")
    if (not isinstance(windows, list)
            or [window.get("phase") for window in windows] != [
                "sealed_correctness", "exact_provider_timing"]):
        raise ProjectionError("HIP decision lacks its exact two GPU windows")
    claim_ids = []
    for window in windows:
        unsigned = {key: value for key, value in window.items()
                    if key != "receipt_sha256"}
        if (_sha(window.get("receipt_sha256"), "window.receipt_sha256")
                != _canonical_sha256(unsigned)
                or window.get("schema") != _HIP_WINDOW_SCHEMA
                or window.get("status") != "complete"
                or window.get("campaign_id") != campaign_id):
            raise ProjectionError("HIP decision measurement-window digest/scope is invalid")
        opened, released, sampling = (window.get("device_claim_open"),
                                      window.get("device_claim_released"),
                                      window.get("device_sampling"))
        if (not isinstance(opened, dict) or not isinstance(released, dict)
                or opened.get("claim_id") != released.get("claim_id")
                or opened.get("device_id") != "mi210_0"
                or not released.get("released_at")):
            raise ProjectionError("HIP decision window lacks a released MI210 claim")
        claim_ids.append(opened["claim_id"])
        sampler_unsigned = {key: value for key, value in sampling.items()
                            if key != "sha256"} if isinstance(sampling, dict) else {}
        if (not isinstance(sampling, dict) or sampling.get("sample_count", 0) < 1
                or _sha(sampling.get("sha256"), "device_sampling.sha256")
                != _canonical_sha256(sampler_unsigned)):
            raise ProjectionError("HIP decision window lacks valid device sampling")
    if len(set(claim_ids)) != 2:
        raise ProjectionError("HIP decision windows must hold distinct claims")
    expected_rows = [
        {"measurement_id": "hip_sealed_correctness_pass_rate",
         "metric": "autokernel_hip_sealed_correctness_pass_rate", "value": 1.0,
         "unit": "fraction", "metric_direction": "higher_better",
         "category": "CANDIDATE",
         "claim": "Fraction of sealed hostile host-double SiLU cases passed",
         "reps": 24, "reps_basis": "sealed_hostile_cases"},
        {"measurement_id": "hip_exact_provider_speedup",
         "metric": "autokernel_hip_speedup_vs_exact_torch_rocm_compile",
         "value": expected_speedup, "unit": "ratio",
         "metric_direction": "higher_better", "category": "CANDIDATE",
         "claim": "Median paired-block speedup over exact Torch-ROCm-compile SiLU",
         "reps": 20, "reps_basis": "paired_randomized_blocks"},
    ]
    if receipt.get("belief_measurements") != expected_rows:
        raise ProjectionError("HIP decision belief rows do not exactly rederive")
    return claimed


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


def _validate_p2_measurements(receipt: dict, measurements: list[dict]) -> None:
    """Re-derive the prospective P2-5j rows without granting placement authority."""
    if receipt.get("authority") != _P2_AUTHORITY:
        raise ProjectionError("P2-5j receipt changed its observation-only authority")
    producer = receipt.get("producer")
    if (not isinstance(producer, dict)
            or producer.get("producer_id") != _P2_PRODUCER
            or producer.get("path") != _P2_PRODUCER_PATH):
        raise ProjectionError("P2-5j receipt names a different producer")
    _sha(producer.get("sha256"), "producer.sha256")
    logical = dict(receipt)
    stored_receipt_sha = logical.pop("receipt_sha256", None)
    if _sha(stored_receipt_sha, "receipt.receipt_sha256") != _canonical_sha256(logical):
        raise ProjectionError("P2-5j receipt_sha256 does not bind the logical receipt")
    summaries = receipt.get("arm_summaries")
    shape = receipt.get("shape")
    identity = receipt.get("identity")
    if (not isinstance(summaries, dict) or set(summaries) != set(_P2_ARMS)
            or shape != {"np_slots": 8, "slot_context_tokens": 8192,
                         "total_context_tokens": 65536, "mtp": False}
            or not isinstance(identity, dict)
            or not isinstance(identity.get("device"), dict)):
        raise ProjectionError("P2-5j receipt lacks its exact four-arm shape/identity")
    device_id = identity["device"].get("device_id")
    if not isinstance(device_id, str) or not device_id:
        raise ProjectionError("P2-5j receipt lacks device identity")
    expected_ids = {
        f"p2_5j_{arm.lower()}_{suffix}"
        for arm in _P2_ARMS for suffix in _P2_METRICS
    }
    if (len(measurements) != len(expected_ids)
            or {row.get("measurement_id") for row in measurements
                if isinstance(row, dict)} != expected_ids):
        raise ProjectionError("P2-5j receipt must carry the exact sixteen placement rows")
    for row in measurements:
        unsigned = dict(row)
        stored_measurement_sha = unsigned.pop("measurement_sha256", None)
        if _sha(stored_measurement_sha, "measurement.measurement_sha256") != _canonical_sha256(
                unsigned):
            raise ProjectionError("P2-5j measurement_sha256 does not bind its row")
        arm = next((candidate for candidate in _P2_ARMS
                    if row["measurement_id"].startswith(
                        f"p2_5j_{candidate.lower()}_")), None)
        if arm is None:
            raise ProjectionError("P2-5j measurement id has an unknown arm")
        suffix = row["measurement_id"][len(f"p2_5j_{arm.lower()}_"):]
        if suffix not in _P2_METRICS:
            raise ProjectionError("P2-5j measurement id has an unknown metric")
        metric, unit, direction, summary_key, sample_key, role = _P2_METRICS[suffix]
        cpu_list, cpu_region, numa_node, relation, arm_role, category = _P2_ARMS[arm]
        summary = summaries[arm]
        if not isinstance(summary, dict):
            raise ProjectionError("P2-5j arm summary must be an object")
        samples = summary.get("samples")
        if (summary.get("n") != 10 or not isinstance(samples, list)
                or len(samples) != 10):
            raise ProjectionError("P2-5j arm must contain ten scored samples")
        values = (summary.get(sample_key) if suffix == "paired_ratio_to_incumbent"
                  else [sample.get(sample_key) for sample in samples
                        if isinstance(sample, dict)])
        if (not isinstance(values, list) or len(values) != 10
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) for value in values)):
            raise ProjectionError("P2-5j measurement lacks ten finite block values")
        expected_value = float(statistics.median(values))
        if (row.get("metric") != metric or row.get("unit") != unit
                or row.get("metric_direction") != direction
                or row.get("category") != category
                or row.get("reps") != 10 or row.get("reps_basis") != _P2_REPS_BASIS
                or float(row.get("value")) != expected_value
                or float(summary.get(summary_key)) != expected_value):
            raise ProjectionError("P2-5j measurement does not rederive from its arm summary")
        extra = row.get("extra")
        if not isinstance(extra, dict):
            raise ProjectionError("P2-5j measurement.extra must be an object")
        expected_common = {
            "measurement_surface": "p2_5j_four_arm_host_thread_placement",
            "arm": arm, "arm_role": arm_role, "cpu_list": cpu_list,
            "cpu_region": cpu_region, "numa_node": numa_node,
            "relation": relation, "device_id": device_id, "shape": shape,
            "authority": _P2_AUTHORITY, "placement_selection_authority": False,
            "kernel_speedup_authority": False, "carve_authority": False,
            "production_activation_authority": False,
            "measurement_role": role, "block_values": values,
            "aggregation": "median",
        }
        if any(extra.get(key) != value for key, value in expected_common.items()):
            raise ProjectionError("P2-5j measurement changes identity or authority")
        if suffix == "paired_ratio_to_incumbent" and extra.get("incumbent_arm") != "I":
            raise ProjectionError("P2-5j paired ratio must name incumbent arm I")
        for field, nested in (("sample_ids", "sample_id"),
                              ("cpu_claim_ids", "cpu_claim"),
                              ("device_claim_ids", "device_claim")):
            observed = extra.get(field)
            if not isinstance(observed, list) or len(observed) != 10:
                raise ProjectionError(f"P2-5j measurement lacks ten {field}")
            if nested == "sample_id":
                expected = [sample.get(nested) for sample in samples]
            else:
                expected = [sample.get(nested, {}).get("opened", {}).get("claim_id")
                            for sample in samples]
            if observed != expected or any(not isinstance(value, str) or not value
                                           for value in observed):
                raise ProjectionError(f"P2-5j measurement {field} differs from samples")


def _iq2_mapping(value: Any, path: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"{path} must be an object")
    return value


def _iq2_list(value: Any, path: str, *, nonempty: bool = False) -> list:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = " non-empty" if nonempty else ""
        raise ProjectionError(f"{path} must be a{qualifier} list")
    return value


def _iq2_text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectionError(f"{path} must be a non-empty string")
    return value.strip()


def _iq2_number(value: Any, path: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProjectionError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0):
        raise ProjectionError(f"{path} must be a finite{' positive' if positive else ''} number")
    return result


def _iq2_instant(value: Any, path: str) -> datetime:
    value = _iq2_text(value, path)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectionError(f"{path} must be an ISO-8601 timestamp") from exc
    if result.tzinfo is None:
        raise ProjectionError(f"{path} must include a timezone")
    return result


def _iq2_receipt_identity(receipt: dict) -> dict:
    return {key: receipt.get(key) for key in _IQ2_RECEIPT_IDENTITY_FIELDS}


def _iq2_validate_claim(receipt: dict, campaign_id: str) -> dict:
    claim = _iq2_mapping(receipt.get("resource_claim_receipt"),
                         "resource_claim_receipt")
    if claim.get("schema") != _IQ2_CLAIM_SCHEMA:
        raise ProjectionError("resource_claim_receipt has the wrong schema")
    if claim.get("campaign_id") != campaign_id:
        raise ProjectionError("resource_claim_receipt names a different campaign")
    if claim.get("role") != "autokernel" or claim.get("roles") != ["autokernel"]:
        raise ProjectionError("resource_claim_receipt is not an exclusive AutoKernel claim")
    if claim.get("state") != "held":
        raise ProjectionError("resource_claim_receipt state must preserve the held snapshot")
    _iq2_text(claim.get("claim_id"), "resource_claim_receipt.claim_id")
    acquired = _iq2_instant(claim.get("acquired_at"),
                            "resource_claim_receipt.acquired_at")
    released = _iq2_instant(claim.get("released_at"),
                            "resource_claim_receipt.released_at")
    if released < acquired:
        raise ProjectionError("resource_claim_receipt was released before acquisition")
    for key in ("cpu_list", "physical_core_list", "lock_root", "host", "purpose"):
        _iq2_text(claim.get(key), f"resource_claim_receipt.{key}")
    regions = _iq2_list(claim.get("regions"), "resource_claim_receipt.regions", nonempty=True)
    if any(not isinstance(region, str) or not region for region in regions):
        raise ProjectionError("resource_claim_receipt.regions must contain names")
    expected_paths = sorted(
        f"{claim['lock_root']}/cpu_region.{role}.{region}.lock"
        for region in regions for role in ("GLOBAL", "autokernel")
    )
    if claim.get("lock_paths") != expected_paths:
        raise ProjectionError("resource_claim_receipt.lock_paths do not derive from its regions")
    if isinstance(claim.get("holder_pid"), bool) or not isinstance(claim.get("holder_pid"), int):
        raise ProjectionError("resource_claim_receipt.holder_pid must be an integer")
    if (isinstance(claim.get("holder_start_ticks"), bool)
            or not isinstance(claim.get("holder_start_ticks"), int)):
        raise ProjectionError("resource_claim_receipt.holder_start_ticks must be an integer")
    _iq2_text(claim.get("holder_boot_id"), "resource_claim_receipt.holder_boot_id")
    return claim


def _iq2_validate_candidate(receipt: dict, campaign_id: str, candidate_id: str,
                            claim_id: str) -> dict:
    candidate = _iq2_mapping(receipt.get("candidate_record"), "candidate_record")
    if candidate.get("schema") != _IQ2_CANDIDATE_SCHEMA:
        raise ProjectionError("candidate_record has the wrong schema")
    if (candidate.get("campaign_id") != campaign_id
            or candidate.get("candidate_id") != candidate_id):
        raise ProjectionError("candidate_record names a different campaign or candidate")
    if candidate.get("status") not in {"evaluating", "banked"}:
        raise ProjectionError("candidate_record is not evaluating or banked")
    worktree = _iq2_mapping(candidate.get("worktree"), "candidate_record.worktree")
    _iq2_text(worktree.get("path"), "candidate_record.worktree.path")
    commit = _iq2_text(worktree.get("source_commit"),
                       "candidate_record.worktree.source_commit")
    if not _COMMIT.fullmatch(commit):
        raise ProjectionError("candidate_record.worktree.source_commit must be a full commit")
    source = _iq2_mapping(candidate.get("source_snapshot"),
                          "candidate_record.source_snapshot")
    _sha(source.get("snapshot_sha256"), "candidate_record.source_snapshot.snapshot_sha256")
    _sha(source.get("patch_bundle_sha256"),
         "candidate_record.source_snapshot.patch_bundle_sha256")
    build = _iq2_mapping(candidate.get("build"), "candidate_record.build")
    _iq2_text(build.get("build_dir"), "candidate_record.build.build_dir")
    _sha(build.get("log_sha256"), "candidate_record.build.log_sha256")
    artifacts = _iq2_mapping(candidate.get("artifacts"), "candidate_record.artifacts")
    _sha(artifacts.get("binary_sha256"), "candidate_record.artifacts.binary_sha256")
    _sha(artifacts.get("linkage_sha256"), "candidate_record.artifacts.linkage_sha256")
    receipts = _iq2_mapping(candidate.get("receipts"), "candidate_record.receipts")
    _iq2_text(receipts.get("host_receipt"), "candidate_record.receipts.host_receipt")
    if receipts.get("resource_claim_receipt") != claim_id:
        raise ProjectionError("candidate_record does not name the released CPU claim")
    event_ids = _iq2_list(candidate.get("evaluation_event_ids"),
                          "candidate_record.evaluation_event_ids", nonempty=True)
    if len(event_ids) != len(set(event_ids)) or any(
            not isinstance(value, str) or not value for value in event_ids):
        raise ProjectionError("candidate_record.evaluation_event_ids must be unique names")
    return candidate


def _iq2_validate_event(value: Any, *, path: str, campaign_id: str,
                        candidate_id: str, candidate: dict, anchor: dict,
                        claim_id: str, tiers: frozenset[str]) -> tuple[dict, float]:
    event = _iq2_mapping(value, path)
    if event.get("schema") != _IQ2_EVENT_SCHEMA:
        raise ProjectionError(f"{path} is not a current evaluation event")
    if (event.get("campaign_id") != campaign_id
            or event.get("candidate_id") != candidate_id):
        raise ProjectionError(f"{path} names a different campaign or candidate")
    if event.get("tier") not in tiers:
        raise ProjectionError(f"{path} has an inadmissible tier")
    if (event.get("backend") != "llama_cpu" or event.get("device_state") is not None
            or event.get("co_residency") != "single"):
        raise ProjectionError(f"{path} is not a single-resident CPU event")
    if event.get("status") != "pass" or event.get("integrity_flags") != []:
        raise ProjectionError(f"{path} is not a clean PASS")
    if event.get("resource_claim_receipt") != claim_id:
        raise ProjectionError(f"{path} names a different CPU claim")
    if event.get("host_receipt") != candidate["receipts"]["host_receipt"]:
        raise ProjectionError(f"{path} names a different host receipt")
    expected_artifact = {
        "source_sha256": candidate["source_snapshot"]["snapshot_sha256"],
        "binary_sha256": candidate["artifacts"]["binary_sha256"],
        "linkage_sha256": candidate["artifacts"]["linkage_sha256"],
    }
    if event.get("artifact") != expected_artifact or event.get("anchor") != anchor:
        raise ProjectionError(f"{path} changes candidate or anchor identity")
    event_id = _iq2_text(event.get("event_id"), f"{path}.event_id")
    grammar = _iq2_mapping(event.get("claim_grammar"), f"{path}.claim_grammar")
    _iq2_text(grammar.get("protocol_id"), f"{path}.claim_grammar.protocol_id")
    reps = grammar.get("reps")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
        raise ProjectionError(f"{path}.claim_grammar.reps must be positive")
    performance = _iq2_mapping(event.get("performance"), f"{path}.performance")
    estimate = _iq2_number(performance.get("estimate"), f"{path}.performance.estimate")
    discipline = _iq2_mapping(performance.get("search_discipline"),
                               f"{path}.performance.search_discipline")
    search_grade = _iq2_mapping(discipline.get("search_grade"),
                                f"{path}.performance.search_discipline.search_grade")
    if (search_grade.get("satisfied") is not True or search_grade.get("failed") != []
            or discipline.get("void_findings") != []
            or discipline.get("effect_resolution") != "improvement"
            or discipline.get("speed_rank_admissible") is not True):
        raise ProjectionError(f"{path} is not search-grade improvement evidence")
    _iq2_instant(event.get("created_at"), f"{path}.created_at")
    if event_id not in candidate["evaluation_event_ids"]:
        raise ProjectionError(f"candidate_record omits {path}.event_id")
    return event, estimate


def _iq2_validate_execution(value: Any, *, path: str, arm: str, recipe: str,
                            model: dict, candidate: dict, anchor: dict) -> dict:
    execution = _iq2_mapping(value, path)
    if (execution.get("runner_id") != "autokernel.execution.microbench/v1"
            or execution.get("arm") != arm or execution.get("recipe_id") != recipe):
        raise ProjectionError(f"{path} names the wrong runner, arm, or recipe")
    for key in ("constructor_sha256", "argv_sha256", "env_sha256", "binary_sha256"):
        _sha(execution.get(key), f"{path}.{key}")
    params = _iq2_mapping(execution.get("params"), f"{path}.params")
    if params.get("model") != model["path"]:
        raise ProjectionError(f"{path}.params.model changes model identity")
    env = _iq2_mapping(execution.get("recipe_env"), f"{path}.recipe_env")
    if env.get("GGML_IQK") != "1":
        raise ProjectionError(f"{path} does not enable GGML_IQK")
    binary_path = _iq2_text(execution.get("binary_path"), f"{path}.binary_path")
    if arm == "candidate":
        expected_binary = candidate["artifacts"]["binary_sha256"]
        if execution.get("source_root") != candidate["worktree"]["path"]:
            raise ProjectionError(f"{path}.source_root changes candidate identity")
        build_dir = str(Path(candidate["build"]["build_dir"]).resolve())
        try:
            inside_build = Path(binary_path).resolve().is_relative_to(build_dir)
        except (OSError, ValueError):
            inside_build = False
        if not inside_build:
            raise ProjectionError(f"{path}.binary_path is outside the candidate build")
    else:
        expected_binary = anchor["binary_sha256"]
    if execution.get("binary_sha256") != expected_binary:
        raise ProjectionError(f"{path}.binary_sha256 changes {arm} identity")
    return execution


def _iq2_invocation_samples(block: dict, *, path: str, arm: str, model_path: str,
                            execution_identity: dict) -> tuple[float, ...]:
    invocations = _iq2_list(block.get("invocations"), f"{path}.invocations", nonempty=True)
    matches = [item for item in invocations
               if isinstance(item, dict) and item.get("arm") == arm]
    if len(matches) != 1:
        raise ProjectionError(f"{path} must contain exactly one {arm} invocation")
    invocation = matches[0]
    embedded = _iq2_mapping(invocation.get("receipt"), f"{path}.{arm}.receipt")
    if _iq2_receipt_identity(embedded) != execution_identity:
        raise ProjectionError(f"{path}.{arm}.receipt changes execution identity")
    row = _iq2_mapping(invocation.get("row"), f"{path}.{arm}.row")
    if row.get("model_filename") != model_path:
        raise ProjectionError(f"{path}.{arm}.row changes model identity")
    samples = tuple(
        _iq2_number(item, f"{path}.{arm}.samples[{index}]", positive=True)
        for index, item in enumerate(
            _iq2_list(invocation.get("samples"), f"{path}.{arm}.samples", nonempty=True)
        )
    )
    if row.get("samples_ts") is not None:
        try:
            row_samples = tuple(float(item) for item in row["samples_ts"])
        except (TypeError, ValueError) as exc:
            raise ProjectionError(f"{path}.{arm}.row.samples_ts is invalid") from exc
        if row_samples != samples:
            raise ProjectionError(f"{path}.{arm}.row.samples_ts changes raw samples")
    for check in _iq2_list(invocation.get("checks"), f"{path}.{arm}.checks"):
        if (not isinstance(check, list) or len(check) != 2
                or not isinstance(check[1], dict) or check[1].get("outcome") != "PASS"):
            raise ProjectionError(f"{path}.{arm} contains a non-PASS invocation check")
    spawn = _iq2_mapping(invocation.get("spawn"), f"{path}.{arm}.spawn")
    if spawn.get("returncode") != 0 or spawn.get("timed_out") is not False:
        raise ProjectionError(f"{path}.{arm} invocation did not exit cleanly")
    return samples


def _iq2_lane_evidence(lane: str, value: Any, *, campaign_id: str,
                       candidate_id: str, candidate: dict, model: dict,
                       anchor: dict, claim: dict) -> dict:
    path = f"lanes.{lane}"
    value = _iq2_mapping(value, path)
    recipe, metric = _IQ2_LANES[lane]
    t1, t1_effect = _iq2_validate_event(
        value.get("t1_event"), path=f"{path}.t1_event", campaign_id=campaign_id,
        candidate_id=candidate_id, candidate=candidate, anchor=anchor,
        claim_id=claim["claim_id"], tiers=_IQ2_T1_TIERS,
    )
    t2, t2_effect = _iq2_validate_event(
        value.get("t2_event"), path=f"{path}.t2_event", campaign_id=campaign_id,
        candidate_id=candidate_id, candidate=candidate, anchor=anchor,
        claim_id=claim["claim_id"], tiers=frozenset({"T2"}),
    )
    grammar = t2["claim_grammar"]
    if (grammar.get("metric") != metric
            or grammar.get("metric_direction") != "higher_better"
            or grammar.get("category") != "CANDIDATE"):
        raise ProjectionError(f"{path}.t2_event has the wrong model metric grammar")
    transfers = _iq2_list(t2.get("transfer_ratio_to"),
                          f"{path}.t2_event.transfer_ratio_to")
    matches = [row for row in transfers if isinstance(row, dict)
               and row.get("event_id") == t1["event_id"]]
    if len(matches) != 1 or matches[0].get("tier") != t1["tier"]:
        raise ProjectionError(f"{path}.t2_event lacks its exact T1 transfer binding")
    transfer = matches[0]
    source_effect = _iq2_number(transfer.get("source_effect"),
                                f"{path}.transfer.source_effect")
    target_effect = _iq2_number(transfer.get("target_effect"),
                                f"{path}.transfer.target_effect")
    ratio = _iq2_number(transfer.get("ratio"), f"{path}.transfer.ratio")
    if (not math.isclose(source_effect, t2_effect, rel_tol=1e-12, abs_tol=1e-15)
            or not math.isclose(target_effect, t1_effect, rel_tol=1e-12, abs_tol=1e-15)
            or target_effect == 0
            or not math.isclose(ratio, source_effect / target_effect,
                                rel_tol=1e-12, abs_tol=1e-15)):
        raise ProjectionError(f"{path}.t2_event transfer effects or ratio are inconsistent")

    vectors = _iq2_list(value.get("raw_vectors"), f"{path}.raw_vectors", nonempty=True)
    blocks: list[list] = []
    block_indexes: set[int] = set()
    unit_ids: set[str] = set()
    vector_digests: list[str] = []
    candidate_execution = None
    anchor_execution = None
    acquired = _iq2_instant(claim["acquired_at"], "resource_claim_receipt.acquired_at")
    released = _iq2_instant(claim["released_at"], "resource_claim_receipt.released_at")
    for vector_index, raw_value in enumerate(vectors):
        raw_path = f"{path}.raw_vectors[{vector_index}]"
        raw = _iq2_mapping(raw_value, raw_path)
        if (raw.get("schema") != _IQ2_RAW_SCHEMA
                or raw.get("runner_id") != "autokernel.execution.microbench/v1"):
            raise ProjectionError(f"{raw_path} is not a formal raw vector")
        if raw.get("recipe_id") != recipe or raw.get("candidate_id") != candidate_id:
            raise ProjectionError(f"{raw_path} changes recipe or candidate identity")
        if raw.get("complete") is not True or raw.get("refusals") != []:
            raise ProjectionError(f"{raw_path} is incomplete or refused")
        control = _iq2_mapping(raw.get("order_control"), f"{raw_path}.order_control")
        if control.get("outcome") != "PASS":
            raise ProjectionError(f"{raw_path} failed order control")
        if raw.get("scope_denominator") != t2.get("scope_denominator"):
            raise ProjectionError(f"{raw_path} changes the T2 scope denominator")
        if raw.get("anchor_identity") != anchor:
            raise ProjectionError(f"{raw_path} changes anchor identity")
        started = _iq2_instant(raw.get("started_at"), f"{raw_path}.started_at")
        ended = _iq2_instant(raw.get("ended_at"), f"{raw_path}.ended_at")
        if not acquired <= started <= ended <= released:
            raise ProjectionError(f"{raw_path} falls outside the released CPU claim")
        candidate_receipt = _iq2_validate_execution(
            raw.get("candidate_receipt"), path=f"{raw_path}.candidate_receipt",
            arm="candidate", recipe=recipe, model=model, candidate=candidate, anchor=anchor,
        )
        anchor_receipt = _iq2_validate_execution(
            raw.get("anchor_receipt"), path=f"{raw_path}.anchor_receipt",
            arm="anchor", recipe=recipe, model=model, candidate=candidate, anchor=anchor,
        )
        candidate_identity = _iq2_receipt_identity(candidate_receipt)
        anchor_identity = _iq2_receipt_identity(anchor_receipt)
        if candidate_execution is None:
            candidate_execution = candidate_identity
            anchor_execution = anchor_identity
        elif (candidate_execution != candidate_identity
              or anchor_execution != anchor_identity):
            raise ProjectionError(f"{raw_path} mixes execution identities")
        attestations = _iq2_list(raw.get("claim_attestations"),
                                 f"{raw_path}.claim_attestations", nonempty=True)
        if any(not isinstance(item, dict) or item.get("claim_id") != claim["claim_id"]
               or item.get("outcome") != "PASS" or item.get("cpu_list") != claim["cpu_list"]
               for item in attestations):
            raise ProjectionError(f"{raw_path} has a foreign or failed claim attestation")
        for local_index, block_value in enumerate(
                _iq2_list(raw.get("blocks"), f"{raw_path}.blocks", nonempty=True)):
            block_path = f"{raw_path}.blocks[{local_index}]"
            block = _iq2_mapping(block_value, block_path)
            if block.get("complete") is not True or block.get("refusals") != []:
                raise ProjectionError(f"{block_path} is incomplete or refused")
            paired = _iq2_list(block.get("paired_block"),
                               f"{block_path}.paired_block")
            if len(paired) != 9:
                raise ProjectionError(f"{block_path}.paired_block must have nine fields")
            block_index, unit_id, _, order, _, _, measured_at, anchor_values, candidate_values = paired
            if (isinstance(block_index, bool) or not isinstance(block_index, int)
                    or block_index < 0 or block_index in block_indexes):
                raise ProjectionError(f"{block_path} has an invalid or duplicate block index")
            block_indexes.add(block_index)
            unit_ids.add(_iq2_text(unit_id, f"{block_path}.paired_block.unit_id"))
            if order not in {"anchor_first", "candidate_first"}:
                raise ProjectionError(f"{block_path}.paired_block.order is invalid")
            _iq2_instant(measured_at, f"{block_path}.paired_block.measured_at")
            paired_anchor = tuple(
                _iq2_number(item, f"{block_path}.paired_block.anchor", positive=True)
                for item in _iq2_list(anchor_values, f"{block_path}.paired_block.anchor",
                                      nonempty=True)
            )
            paired_candidate = tuple(
                _iq2_number(item, f"{block_path}.paired_block.candidate", positive=True)
                for item in _iq2_list(candidate_values, f"{block_path}.paired_block.candidate",
                                      nonempty=True)
            )
            plan = _iq2_mapping(block.get("plan"), f"{block_path}.plan")
            if (plan.get("block_index") != block_index or plan.get("unit_id") != unit_id
                    or plan.get("order") != order):
                raise ProjectionError(f"{block_path}.plan changes its paired block")
            observed_anchor = _iq2_invocation_samples(
                block, path=block_path, arm="anchor", model_path=model["path"],
                execution_identity=anchor_identity,
            )
            observed_candidate = _iq2_invocation_samples(
                block, path=block_path, arm="candidate", model_path=model["path"],
                execution_identity=candidate_identity,
            )
            if observed_anchor != paired_anchor or observed_candidate != paired_candidate:
                raise ProjectionError(f"{block_path} invocation samples change paired_block")
            blocks.append(paired)
        vector_digests.append(_ak_content_sha256(raw))
    if len(unit_ids) != 1:
        raise ProjectionError(f"{path} mixes model/recipe unit identities")
    blocks.sort(key=lambda item: item[0])
    performance = t2["performance"]
    if performance.get("raw_samples") != blocks:
        raise ProjectionError(f"{path}.t2_event.raw_samples do not bind the raw vectors")
    if (performance.get("paired_blocks") != len(blocks)
            or grammar.get("reps") != len(blocks)):
        raise ProjectionError(f"{path} changes the scored block denominator")
    return {
        "anchor_samples": tuple(sample for block in blocks for sample in block[7]),
        "candidate_samples": tuple(sample for block in blocks for sample in block[8]),
        "block_count": len(blocks),
        "samples_per_block": [
            {"block_index": block[0], "anchor": len(block[7]),
             "candidate": len(block[8])} for block in blocks
        ],
        "unit_id": next(iter(unit_ids)),
        "recipe_id": recipe,
        "protocol_id": grammar["protocol_id"],
        "t1_event_id": t1["event_id"],
        "t1_event_sha256": _ak_content_sha256(t1),
        "t2_event_id": t2["event_id"],
        "t2_event_sha256": _ak_content_sha256(t2),
        "raw_vector_sha256s": vector_digests,
        "candidate_execution": candidate_execution,
        "anchor_execution": anchor_execution,
    }


def _iq2_expected_row(*, lane: str, arm: str, evidence: dict, model: dict,
                      candidate: dict, anchor: dict, claim: dict,
                      source_sha: str, producer_sha: str) -> dict:
    samples = evidence[f"{arm}_samples"]
    metric = _IQ2_LANES[lane][1]
    median = float(statistics.median(samples))
    row = {
        "measurement_id": f"iq2_xxs_model_{lane}_{arm}_median_tokens_per_s",
        "metric": f"iq2_xxs_model_{metric}",
        "value": median,
        "unit": "tokens/s",
        "metric_direction": "higher_better",
        "category": "BASELINE" if arm == "anchor" else "CANDIDATE",
        "reps": len(samples),
        "reps_basis": (
            f"scored:{len(samples)} llama-bench samples from "
            f"{evidence['block_count']} admitted matched paired blocks"
        ),
        "claim": (
            f"{model['model_id']} {_IQ2_QUANTIZATION} {arm} median "
            f"{metric} is {median:.9g} tokens/s"
        ),
        "extra": {
            "measurement_role": "model_level_confirmation",
            "lane": lane,
            "arm": arm,
            "reduction": "median_of_all_scored_arm_samples",
            "model_identity": dict(model),
            "candidate_identity": {
                "candidate_id": candidate["candidate_id"],
                "candidate_record_sha256": _ak_content_sha256(candidate),
                "source_commit": candidate["worktree"]["source_commit"],
                "source_snapshot_sha256": candidate["source_snapshot"]["snapshot_sha256"],
                "patch_bundle_sha256": candidate["source_snapshot"]["patch_bundle_sha256"],
                "build_identity_sha256": _ak_content_sha256(candidate["build"]),
                "build_log_sha256": candidate["build"]["log_sha256"],
                "binary_sha256": candidate["artifacts"]["binary_sha256"],
                "linkage_sha256": candidate["artifacts"]["linkage_sha256"],
            },
            "anchor_identity": dict(anchor),
            "candidate_execution": dict(evidence["candidate_execution"]),
            "anchor_execution": dict(evidence["anchor_execution"]),
            "recipe_id": evidence["recipe_id"],
            "evaluation_protocol_id": evidence["protocol_id"],
            "unit_id": evidence["unit_id"],
            "scored_blocks": evidence["block_count"],
            "samples_per_block": evidence["samples_per_block"],
            "resource_claim_receipt": claim["claim_id"],
            "resource_claim_receipt_sha256": _ak_content_sha256(claim),
            "cpu_list": claim["cpu_list"],
            "claim_released_at": claim["released_at"],
            "t1_event_id": evidence["t1_event_id"],
            "t1_event_sha256": evidence["t1_event_sha256"],
            "t2_event_id": evidence["t2_event_id"],
            "t2_event_sha256": evidence["t2_event_sha256"],
            "raw_vector_sha256s": evidence["raw_vector_sha256s"],
            "source_receipt_sha256": source_sha,
            "producer_id": _IQ2_MODEL_PRODUCER,
            "producer_sha256": producer_sha,
        },
    }
    row["extra"]["self_sha256"] = _ak_content_sha256(row)
    return row


def _validate_iq2_model_measurements(receipt: dict, measurements: list[dict]) -> None:
    """Rebuild every model-confirmation row from formal source evidence."""
    if receipt.get("status") != "complete":
        raise ProjectionError("IQ2 model receipt status must be complete")
    campaign_id = _iq2_text(receipt.get("campaign_id"), "campaign_id")
    candidate_id = _iq2_text(receipt.get("candidate_id"), "candidate_id")
    _iq2_instant(receipt.get("created_at"), "created_at")
    _iq2_instant(receipt.get("ended_at"), "ended_at")
    if receipt.get("producer_id") != _IQ2_MODEL_PRODUCER:
        raise ProjectionError("IQ2 model receipt names a different producer")
    producer_sha = _sha(receipt.get("producer_sha256"), "producer_sha256")
    final_unsigned = copy.deepcopy(receipt)
    stored_self = final_unsigned.pop("self_sha256", None)
    if _sha(stored_self, "self_sha256") != _ak_content_sha256(final_unsigned):
        raise ProjectionError("IQ2 model self_sha256 does not bind the finalized receipt")
    source = copy.deepcopy(receipt)
    for key in ("source_receipt_sha256", "producer_id", "producer_sha256",
                "belief_measurements", "self_sha256"):
        source.pop(key, None)
    source_sha = _sha(receipt.get("source_receipt_sha256"), "source_receipt_sha256")
    if source_sha != _ak_content_sha256(source):
        raise ProjectionError("IQ2 model source_receipt_sha256 does not bind source evidence")

    model = _iq2_mapping(receipt.get("model_identity"), "model_identity")
    if set(model) != {"model_id", "path", "sha256", "quantization"}:
        raise ProjectionError("model_identity must contain exactly id, path, digest, and quantization")
    _iq2_text(model.get("model_id"), "model_identity.model_id")
    _iq2_text(model.get("path"), "model_identity.path")
    _sha(model.get("sha256"), "model_identity.sha256")
    if model.get("quantization") != _IQ2_QUANTIZATION:
        raise ProjectionError("model_identity.quantization must be IQ2_XXS")
    anchor = _iq2_mapping(receipt.get("anchor_identity"), "anchor_identity")
    if set(anchor) != {"source_commit", "binary_sha256", "linkage_sha256",
                       "measurement_event_ids"}:
        raise ProjectionError("anchor_identity has unexpected or missing fields")
    if not _COMMIT.fullmatch(str(anchor.get("source_commit", ""))):
        raise ProjectionError("anchor_identity.source_commit must be a full commit")
    _sha(anchor.get("binary_sha256"), "anchor_identity.binary_sha256")
    _sha(anchor.get("linkage_sha256"), "anchor_identity.linkage_sha256")
    _iq2_list(anchor.get("measurement_event_ids"),
              "anchor_identity.measurement_event_ids", nonempty=True)
    claim = _iq2_validate_claim(receipt, campaign_id)
    candidate = _iq2_validate_candidate(
        receipt, campaign_id, candidate_id, claim["claim_id"])
    lanes = _iq2_mapping(receipt.get("lanes"), "lanes")
    if set(lanes) != set(_IQ2_LANES):
        raise ProjectionError("IQ2 model receipt must contain exactly TG and PP lanes")
    evidence = {
        lane: _iq2_lane_evidence(
            lane, lanes[lane], campaign_id=campaign_id, candidate_id=candidate_id,
            candidate=candidate, model=model, anchor=anchor, claim=claim,
        ) for lane in _IQ2_LANES
    }
    if (evidence["tg"]["candidate_execution"] != evidence["pp"]["candidate_execution"]
            or evidence["tg"]["anchor_execution"] != evidence["pp"]["anchor_execution"]):
        raise ProjectionError("TG and PP change candidate or anchor execution identity")
    expected = [
        _iq2_expected_row(
            lane=lane, arm=arm, evidence=evidence[lane], model=model,
            candidate=candidate, anchor=anchor, claim=claim, source_sha=source_sha,
            producer_sha=producer_sha,
        )
        for lane in _IQ2_LANES for arm in ("anchor", "candidate")
    ]
    if measurements != expected:
        raise ProjectionError(
            "IQ2 model belief rows do not exactly rederive from their formal evidence")


def native_rows(receipt: dict, *, receipt_locator: str = "",
                receipt_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    """Return only measurements explicitly written by a successful native producer."""
    if not isinstance(receipt, dict) or receipt.get("schema") not in SOURCE_SCHEMAS:
        raise ProjectionError("unsupported AutoKernel auxiliary receipt schema")
    if receipt_sha256 and not _SHA256.fullmatch(receipt_sha256):
        raise ProjectionError("receipt_sha256 must be a lowercase SHA-256 digest")
    measurements = receipt.get("belief_measurements")
    if receipt.get("schema") == _IQ2_MODEL_SCHEMA:
        if not isinstance(measurements, list) or not measurements:
            raise ProjectionError(
                "IQ2 model confirmation requires finalized producer-written rows")
        _validate_iq2_model_measurements(receipt, measurements)
    if measurements is None:
        return ()
    if not isinstance(measurements, list):
        raise ProjectionError("belief_measurements must be a list")
    if not measurements:
        return ()
    if (receipt.get("schema") != _ARENA_INTERMEDIATE_SCHEMA
            and receipt.get("status") not in {"pass", "passed", "complete"}):
        raise ProjectionError("a failed auxiliary receipt cannot carry belief measurements")
    if receipt.get("schema") == _Q4K_SCHEMA:
        _validate_q4k_measurements(receipt, measurements)
    if receipt.get("schema") == _P2_SCHEMA:
        _validate_p2_measurements(receipt, measurements)
    if receipt.get("schema") == _ARENA_SCHEMA:
        _arena_receipt_identity(receipt)
    if receipt.get("schema") == _HIP_SCHEMA:
        _hip_receipt_identity(receipt)
    if receipt.get("schema") == _HIP_DECISION_SCHEMA:
        _hip_decision_receipt_identity(receipt)
    if receipt.get("schema") == _ARENA_INTERMEDIATE_SCHEMA:
        _arena_intermediate_receipt_identity(receipt)
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
    observation_identity = (
        _arena_receipt_identity(receipt) if schema == _ARENA_SCHEMA
        else _arena_intermediate_receipt_identity(receipt)
        if schema == _ARENA_INTERMEDIATE_SCHEMA
        else _hip_receipt_identity(receipt) if schema == _HIP_SCHEMA
        else _hip_decision_receipt_identity(receipt)
        if schema == _HIP_DECISION_SCHEMA
        else campaign_id)
    identity_payload = json.dumps(
        [schema, observation_identity, local_id, native.get("measurement_index")],
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
            **({"arena_receipt_identity_sha256": observation_identity}
               if schema == _ARENA_SCHEMA else {}),
            **({"arena_intermediate_receipt_identity_sha256": observation_identity}
               if schema == _ARENA_INTERMEDIATE_SCHEMA else {}),
            **({"hip_receipt_identity_sha256": observation_identity}
               if schema == _HIP_SCHEMA else {}),
            **({"hip_decision_receipt_identity_sha256": observation_identity}
               if schema == _HIP_DECISION_SCHEMA else {}),
            **({"native_measurement_sha256": measurement["measurement_sha256"]}
               if measurement.get("measurement_sha256") else {}),
            **({"receipt_self_sha256": receipt["receipt_sha256"]}
               if receipt.get("receipt_sha256") else {}),
            **extra,
        },
    )
