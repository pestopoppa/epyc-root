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
from adapters import _llama_bench_protocol as _lbp  # noqa: E402

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
    "epyc.autokernel.gpu_screening_baseline.v2",
    "epyc.autokernel.gpu_candidate_only_screen.v2",
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
_GPU_BANK_SCHEMA = "epyc.autokernel.gpu_screening_baseline.v2"
_GPU_RESULT_SCHEMA = "epyc.autokernel.gpu_candidate_only_screen.v2"
_GPU_PRODUCER = "scripts.benchmark.run_autokernel_gpu_discovery/v3"
_GPU_PRODUCER_PATH = "scripts/benchmark/run_autokernel_gpu_discovery.py"
_GPU_AUTHORITY = "nonpromotable_candidate_only_discovery"


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
    # VB-LLAMA-BENCH-HARDEN-PROTOCOL: the recorded argv (embedded receipt, else the spawn record) decides
    # the request; the row decides the protocol. A disagreement is refused before any sample is projected.
    spawn_record = invocation.get("spawn")
    _lbp.assess(row=row, argv=embedded.get("argv") or (
        spawn_record.get("argv") if isinstance(spawn_record, dict) else None),
        label=f"{path}.{arm} llama-bench row")
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


def _gpu_samples(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ProjectionError(f"{label} must contain exactly three samples")
    result = []
    for index, item in enumerate(value):
        if (isinstance(item, bool) or not isinstance(item, (int, float))
                or not math.isfinite(item) or item <= 0):
            raise ProjectionError(f"{label}[{index}] must be positive and finite")
        result.append(float(item))
    return result


def _gpu_expected_row(*, measurement_id: str, metric: str, value: float,
                      unit: str, category: str, claim: str, reps_basis: str,
                      extra: dict, protocol_id: str) -> dict:
    row = {
        "measurement_id": measurement_id, "metric": metric, "value": value,
        "unit": unit, "metric_direction": "higher_better", "category": category,
        "protocol_id": protocol_id, "reps": 3, "reps_basis": reps_basis,
        "claim": claim, "extra": extra,
    }
    row["measurement_sha256"] = _ak_content_sha256(row)
    return row


def _gpu_common(receipt: dict, *, samples: list[float]) -> tuple[dict, dict]:
    if receipt.get("authority") != _GPU_AUTHORITY:
        raise ProjectionError("GPU discovery receipt upgrades its non-promotable authority")
    producer = receipt.get("producer")
    if (not isinstance(producer, dict)
            or set(producer) != {"producer_id", "path", "sha256"}
            or producer.get("producer_id") != _GPU_PRODUCER
            or producer.get("path") != _GPU_PRODUCER_PATH):
        raise ProjectionError("GPU discovery receipt lacks its exact producer identity")
    _sha(producer.get("sha256"), "receipt.producer.sha256")
    frame = receipt.get("frame")
    if (not isinstance(frame, dict)
            or frame.get("backend") != "llama_gpu"
            or frame.get("recipe") != "pp512-ngl99"
            or frame.get("metric") != "prefill_tokens_per_s"
            or frame.get("metric_direction") != "higher_better"
            or frame.get("device") != "AMD Instinct MI210"
            or frame.get("architecture") != "gfx90a"
            or not _COMMIT.fullmatch(str(frame.get("source_commit", "")))
            or not isinstance(frame.get("cpu_list"), str)
            or not isinstance(frame.get("model"), str)):
        raise ProjectionError("GPU discovery receipt is not the sealed MI210 pp512 frame")
    _sha(frame.get("model_sha256"), "frame.model_sha256")
    factor = receipt.get("sole_factor")
    if (not isinstance(factor, dict)
            or set(factor) != {"name", "anchor", "candidate"}
            or (factor.get("name"), factor.get("anchor"), factor.get("candidate"))
            not in {
                ("GGML_HIP_MMQ_MFMA", "ON", "OFF"),
                ("flash_attention", "OFF", "ON"),
                ("GGML_HIP_ROCWMMA_FATTN", "OFF", "ON"),
            }):
        raise ProjectionError("GPU discovery sole factor is not an admitted factor transition")
    evidence = {
        "campaign_id": receipt.get("campaign_id"), "authority": _GPU_AUTHORITY,
        "frame": frame, "sole_factor": factor, "samples": samples,
        "producer_sha256": producer["sha256"],
    }
    common = {
        "authority": _GPU_AUTHORITY, "non_promotable": True,
        "top_k_discovery_only": True, "promotion_authority": False,
        "production_tree_touched": False, "frame": frame, "sole_factor": factor,
        "producer_id": producer["producer_id"],
        "producer_sha256": producer["sha256"], "evidence_basis": evidence,
        "evidence_sha256": _ak_content_sha256(evidence),
    }
    return common, factor


def _gpu_identity(value: Any, *, frame: dict, factor: dict, arm: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"GPU discovery {arm}_identity must be a dict")
    if value.get("source_commit") != frame["source_commit"] \
            or not isinstance(value.get("rocwmma_fattn"), bool) \
            or not isinstance(value.get("mmq_mfma"), bool):
        raise ProjectionError(f"GPU discovery {arm} identity does not bind its source/factors")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get("binary"), str):
        raise ProjectionError(f"GPU discovery {arm} identity lacks build artifacts")
    _sha(artifacts.get("binary_sha256"), f"{arm}_identity.artifacts.binary_sha256")
    libraries = artifacts.get("libraries")
    if not isinstance(libraries, dict) or not libraries:
        raise ProjectionError(f"GPU discovery {arm} identity lacks DSO identities")
    for name, digest in libraries.items():
        if not isinstance(name, str) or not name:
            raise ProjectionError(f"GPU discovery {arm} DSO name is invalid")
        _sha(digest, f"{arm}_identity.artifacts.libraries[{name!r}]")
    if arm == "candidate":
        if factor["name"] == "GGML_HIP_MMQ_MFMA" \
                and (value["rocwmma_fattn"], value["mmq_mfma"]) != (True, False):
            raise ProjectionError("GPU MMQ candidate identity changes more than its sole factor")
        if factor["name"] in {"flash_attention", "GGML_HIP_ROCWMMA_FATTN"} \
                and (value["rocwmma_fattn"], value["mmq_mfma"]) != (True, False):
            raise ProjectionError("GPU candidate identity does not bind the r1m0 build")
    return value


def _gpu_run_protocol(run: dict, label: str) -> dict:
    """VB-LLAMA-BENCH-HARDEN-PROTOCOL: a run's own argv and raw row decide its protocol (see the shared helper)."""
    row = run.get("raw_row")
    return _lbp.assess(row=row if isinstance(row, dict) else None, argv=run.get("argv"),
                       label=f"{label} llama-bench row")


def _validate_gpu_discovery_measurements(receipt: dict,
                                         measurements: list[dict]) -> None:
    schema = receipt.get("schema")
    if receipt.get("status") != "complete" or not isinstance(receipt.get("campaign_id"), str):
        raise ProjectionError("GPU discovery belief rows require a complete campaign receipt")
    self_field = "baseline_sha256" if schema == _GPU_BANK_SCHEMA else "result_sha256"
    claimed_self = _sha(receipt.get(self_field), f"receipt.{self_field}")
    if claimed_self != _ak_content_sha256(
            {key: value for key, value in receipt.items() if key != self_field}):
        raise ProjectionError(f"GPU discovery {self_field} does not bind its receipt")
    samples_key = "anchor_samples" if schema == _GPU_BANK_SCHEMA else "candidate_samples"
    runs_key = "anchor_runs" if schema == _GPU_BANK_SCHEMA else "candidate_runs"
    samples = _gpu_samples(receipt.get(samples_key), samples_key)
    runs = receipt.get(runs_key)
    if (not isinstance(runs, list) or len(runs) != 3
            or any(not isinstance(run, dict) or run.get("metric") != sample
                   or run.get("hip_residency_proved") is not True
                   for run, sample in zip(runs, samples))):
        raise ProjectionError("GPU discovery runs do not bind three resident samples")
    for run_index, run in enumerate(runs):
        _gpu_run_protocol(run, f"{runs_key}[{run_index}]")
    common, factor = _gpu_common(receipt, samples=samples)
    frame = receipt["frame"]
    if schema == _GPU_BANK_SCHEMA:
        anchor = _gpu_identity(receipt.get("anchor_identity"), frame=frame,
                               factor=factor, arm="anchor")
        candidate = _gpu_identity(receipt.get("candidate_identity"), frame=frame,
                                  factor=factor, arm="candidate")
        if factor["name"] == "flash_attention" and anchor != candidate:
            raise ProjectionError("flash-attention screen changes its build identity")
        if factor["name"] == "GGML_HIP_MMQ_MFMA" \
                and (anchor["rocwmma_fattn"], anchor["mmq_mfma"]) != (True, True):
            raise ProjectionError("MMQ anchor identity does not bind r1m1")
        if factor["name"] == "GGML_HIP_ROCWMMA_FATTN" \
                and (anchor["rocwmma_fattn"], anchor["mmq_mfma"]) != (False, False):
            raise ProjectionError("ROCWMMA anchor identity does not bind r0m0")
        common.update({"arm": "anchor", "build_identity": anchor,
                       "arithmetic_baseline_center": sum(samples) / 3})
        expected = [_gpu_expected_row(
            measurement_id="gpu_discovery_anchor_pp512_median_tokens_per_s",
            metric="gpu_prefill_tokens_per_s", value=statistics.median(samples),
            unit="tokens/s", category="BASELINE",
            claim=("Non-promotable GPU discovery anchor observed median pp512 "
                   f"throughput {statistics.median(samples):.9g} tokens/s"),
            reps_basis="scored:three anchor-bank MI210 llama-bench invocations",
            extra=common, protocol_id=_GPU_BANK_SCHEMA)]
    else:
        if (receipt.get("state") != "decided" or receipt.get("ok") is not True
                or receipt.get("non_promotable") is not True
                or receipt.get("nomination") != "top_k_candidate_only_not_a_keep"
                or receipt.get("hip_residency_proved") is not True):
            raise ProjectionError("GPU candidate result upgrades or lacks its discovery boundary")
        candidate = _gpu_identity(receipt.get("candidate_identity"), frame=frame,
                                  factor=factor, arm="candidate")
        baseline_sha = _sha(receipt.get("baseline_sha256"), "baseline_sha256")
        anchor_samples = _gpu_samples(
            receipt.get("baseline_anchor_samples"), "baseline_anchor_samples")
        center = receipt.get("baseline_center")
        if (isinstance(center, bool) or not isinstance(center, (int, float))
                or not math.isfinite(center) or center <= 0):
            raise ProjectionError("GPU baseline center must be positive and finite")
        if not math.isclose(float(center), sum(anchor_samples) / 3,
                            rel_tol=1e-12, abs_tol=1e-12):
            raise ProjectionError("GPU baseline center does not rederive from anchor samples")
        effects = [(sample - float(center)) / float(center) for sample in samples]
        declared = receipt.get("relative_effects")
        if (not isinstance(declared, list) or len(declared) != 3
                or any(isinstance(item, bool) or not isinstance(item, (int, float))
                       or not math.isclose(float(item), expected,
                                           rel_tol=1e-12, abs_tol=1e-12)
                       for item, expected in zip(declared, effects))
                or not isinstance(receipt.get("median_relative"), (int, float))
                or not math.isclose(float(receipt["median_relative"]),
                                    statistics.median(effects),
                                    rel_tol=1e-12, abs_tol=1e-12)):
            raise ProjectionError("GPU relative effect does not rederive from its samples")
        common.update({
            "arm": "candidate", "build_identity": candidate,
            "baseline_sha256": baseline_sha, "baseline_center": float(center),
            "baseline_anchor_samples": anchor_samples,
            "hip_residency_proved": True,
        })
        basis = "scored:three candidate-only MI210 llama-bench invocations"
        expected = [
            _gpu_expected_row(
                measurement_id="gpu_discovery_candidate_pp512_median_tokens_per_s",
                metric="gpu_prefill_tokens_per_s", value=statistics.median(samples),
                unit="tokens/s", category="CANDIDATE",
                claim=("Non-promotable GPU candidate discovery observed median pp512 "
                       f"throughput {statistics.median(samples):.9g} tokens/s"),
                reps_basis=basis, extra=common, protocol_id=_GPU_RESULT_SCHEMA),
            _gpu_expected_row(
                measurement_id="gpu_discovery_candidate_pp512_median_relative_effect",
                metric="gpu_prefill_relative_effect_vs_sealed_anchor",
                value=statistics.median(effects), unit="fraction", category="CANDIDATE",
                claim=("Non-promotable GPU candidate discovery observed median relative "
                       f"effect {statistics.median(effects):.9g} versus its sealed anchor bank"),
                reps_basis=basis, extra={**common, "relative_effects": effects},
                protocol_id=_GPU_RESULT_SCHEMA),
        ]
    if measurements != expected:
        raise ProjectionError("GPU discovery belief rows do not exactly rederive")



_NEMO_NATIVE_AUTHORITY = {
    "protocol": "914fd9b116a7d9c84fb10842165069db428d7ab26992c2e281bb9be89cd692ca",
    "original_l": "e746d105ccfa01e7542d918a9aaf6ed3073b0171775f341979895b988a278a4d",
    "libggml": "b89dcc64a3687f0c8e918200046d302d2a1c8cd38e44ece7e86c04db176ee33e",
    "libggml_base": "7b5376ef2a3c9cd4c9aa74b4abb92ca2d979e123999601db6ed98dd639c0c155",
    "libggml_cpu": "74be93aa3e1443217c1e1e18dfff930a8ebbcba13b53455cb4a3f0c25e1b0d8b",
    "profiler_sdk": "44d8548b9e31c7ab4ecad3023878d9b9d8bcf62b69350ba3837c01270d45639c",
    "source_manifest": "e7859f018098bedb9c8951c76a8264ec350f80764f0b4b3fa36022eee9d6b986",
    "server": "83805b23f09b35abb04b53aefdd15fb3e71f5eb55861c2d3945b28a846753e65",
    "libllama": "7d317ac83a4fede24714e044295156e94ed86ffd70ef154acbf88d700bac9453",
    "libggml_hip": "1f3c92e30db1f9c4c675a1627698f46aa3834a8e2e2cf12b7deabfc292070357",
    "profiler": "c753449eb635ecb4d8be794e8b66439b200b252c157555920d260df5cbac767a",
    "roctx": "93db9899dfccfcdac33f5721f81ed1df39251c2b98f795bac36ca563d3e8e7d8",
}
_NEMO_CODE_PROMPT = "Write a Python function that parses a CSV file into a list of dictionaries, with type inference for integer and float columns, and add a docstring and two usage examples."
_NEMO_PROSE_PROMPT = "Explain in a short paragraph why the sky is blue."
_NEMO_BOLT_MODEL = "/mnt/raid0/llm/models/nvidia/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB-GGUF/NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf"


def _nemo_artifact_identity(path):
    """Stream bytes with a before/after identity check, never trust supplied hashes."""
    p = Path(path)
    before = p.stat()
    digest = hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 2**20), b""):
            digest.update(chunk)
    after = p.stat()

    def key(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

    if key(before) != key(after) or not p.is_absolute() or not p.is_file():
        raise ProjectionError("artifact identity changed while reading")
    return {"path": str(p), "size": after.st_size, "sha256": digest.hexdigest()}


def _nemo_phase_payloads(pass_name):
    def chat(prompt, count, extra=None):
        return {
            "endpoint": "/v1/chat/completions",
            "payload": {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": count,
                "temperature": 0.0,
                "top_k": 1,
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": False},
                **(extra or {}),
            },
        }

    if pass_name == "L":
        return {
            "warm": chat(_NEMO_CODE_PROMPT, 160),
            "S": chat(_NEMO_CODE_PROMPT, 160),
            "P": chat(_NEMO_CODE_PROMPT, 160, {"speculative.n_max": 0}),
        }
    if pass_name == "B":
        return {"warm": chat(_NEMO_PROSE_PROMPT, 48), "M": chat(_NEMO_CODE_PROMPT, 96)}
    raise ProjectionError("unknown original pass")


def _nemo_validate_capture_contract(capture, run):
    """Prospective artifact/workload/owner evidence; independent of grade policy."""
    from datetime import datetime

    def require(ok, why):
        if not ok:
            raise ProjectionError("capture contract: " + why)

    def instant(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None, "timezone missing")
        return parsed

    contract = capture.get("capture_contract", {})
    require(
        contract.get("schema") == "epyc.autokernel.nemo_native_contract.v1",
        "missing identity contract",
    )
    require(
        contract.get("purpose")
        == capture.get("purpose")
        == "prospective_scored_profile",
        "canary or relabelled purpose",
    )
    digest = _canonical_sha256(contract)
    require(
        run.get("capture_contract_sha256") == digest,
        "source-time contract hash differs",
    )
    require(
        contract.get("native_commit") == "b1e820a0ad8bc2192fc38c3c1beda7abf3a28ecf"
        and contract.get("native_base") == "ffc1bac82eeca6f9099e1ccd9ba49703c460a115",
        "native source era differs",
    )
    require(
        contract.get("analysis_sources") == capture.get("analysis_sources"),
        "analysis not frozen at source time",
    )
    require(
        instant(contract["declared_at"]) <= instant(run["started_at"]), "late contract"
    )
    analysis_artifacts = contract.get("analysis_artifacts", {})
    require(
        set(analysis_artifacts) == set(contract["analysis_sources"]),
        "missing analysis artifact map",
    )
    for name, item in analysis_artifacts.items():
        require(
            _nemo_artifact_identity(item["path"]) == item
            and item["sha256"] == contract["analysis_sources"][name],
            "analysis module bytes differ",
        )
    artifacts = contract.get("artifacts", {})
    required = set(_NEMO_NATIVE_AUTHORITY) | {
        "producer",
        "claim_module",
        "claim_schemas",
        "worktree_module",
        "contract_module",
        "interpreter",
        "launcher",
        "capture_source_manifest",
        "module_closure",
        "model",
        "template",
    }
    if contract.get("pass") == "L":
        required.add("draft_model")
    require(set(artifacts) == required, "missing or extra artifact identities")
    require(
        run.get("source_time_artifacts") == artifacts,
        "source-time artifact map differs",
    )
    for role, item in artifacts.items():
        require(
            _nemo_artifact_identity(item["path"]) == item,
            "artifact bytes differ: " + role,
        )
        if role in _NEMO_NATIVE_AUTHORITY:
            require(
                item["sha256"] == _NEMO_NATIVE_AUTHORITY[role],
                "unapproved source/build/protocol: " + role,
            )
    closure = json.loads(Path(artifacts["module_closure"]["path"]).read_bytes())
    require(
        isinstance(closure, dict) and len(closure) >= 12,
        "missing imported module closure",
    )
    for path, expected_sha in closure.items():
        require(
            _nemo_artifact_identity(path)["sha256"] == expected_sha,
            "imported module bytes differ",
        )
    for role in ("claim_module", "claim_schemas", "worktree_module"):
        require(
            closure.get(artifacts[role]["path"]) == artifacts[role]["sha256"],
            "module outside pinned closure",
        )
    server = contract["server_argv"]
    require(
        isinstance(server, list) and server[0] == artifacts["server"]["path"],
        "server identity differs",
    )
    port = server[server.index("--port") + 1]
    if contract["pass"] == "L":
        original = json.loads(Path(artifacts["original_l"]["path"]).read_bytes())[
            "argv"
        ]
        index = next(i for i, x in enumerate(original) if x.endswith("/llama-server"))
        expected = [server[0]] + original[index + 1 :]
        for flag, value in (("--port", port), ("-np", "1"), ("-c", "16384")):
            expected[expected.index(flag) + 1] = value
        if "--slot-save-path" in expected:
            index = expected.index("--slot-save-path")
            del expected[index : index + 2]
        require(expected == server, "original L argv differs")
        for role, flag in (
            ("model", "-m"),
            ("draft_model", "-md"),
            ("template", "--chat-template-file"),
        ):
            require(
                server[server.index(flag) + 1] == artifacts[role]["path"],
                "L model/template binding differs",
            )
    else:
        expected = [
            server[0],
            "-m",
            _NEMO_BOLT_MODEL,
            "--host",
            "127.0.0.1",
            "--port",
            port,
            "--batch-size",
            "2048",
            "--ubatch-size",
            "512",
            "--ctx-size",
            "16384",
            "--parallel",
            "1",
            "-ngl",
            "999",
            "--cache-type-k",
            "q8_0",
            "--cache-type-v",
            "q8_0",
            "--flash-attn",
            "on",
            "--jinja",
            "-t",
            "8",
        ]
        require(
            expected == server and artifacts["model"]["path"] == _NEMO_BOLT_MODEL,
            "original B model/argv differs",
        )
        require(
            artifacts["template"] == artifacts["model"]
            and contract.get("template_mode") == "embedded_gguf",
            "B embedded template not bound to actual model",
        )
    require(
        all(m.get("runtime_server_argv") == server for m in run["marks"]),
        "actual running server argv differs",
    )
    require(
        run.get("server_argv") == server
        and run.get("argv") == contract.get("argv")
        and run.get("env") == contract.get("env"),
        "actual argv/env differs",
    )
    require(
        contract["argv"][-len(server) :] == server,
        "wrapper does not launch bound server",
    )
    for flag in (
        "--kernel-trace",
        "--memory-copy-trace",
        "--hip-trace",
        "--marker-trace",
        "--stats",
    ):
        require(flag in contract["argv"][: -len(server)], "capture API missing " + flag)
    require(
        contract["env"]["set"].get("LLAMA_NATIVE_ROCTX_LIBRARY")
        == artifacts["roctx"]["path"]
        and "GGML_CUDA_DISABLE_GRAPHS" in contract["env"]["unset"]
        and "GGML_CUDA_DISABLE_GRAPHS" not in contract["env"]["set"],
        "ROCTX/graph env differs",
    )
    for mark in run["marks"]:
        expected_runtime = {
            role: _nemo_artifact_identity(str(Path(artifacts[role]["path"]).resolve()))
            for role in (
                "server",
                "libllama",
                "libggml_hip",
                "libggml",
                "libggml_base",
                "libggml_cpu",
                "roctx",
                "profiler_sdk",
            )
        }
        require(
            mark.get("runtime_artifacts") == expected_runtime,
            "actual loaded image/DSO identities differ",
        )
    require(
        artifacts["contract_module"]["sha256"]
        == contract["analysis_sources"]["nemo_native_join.py"],
        "producer contract module differs from frozen analysis",
    )
    wrapper = contract["argv"][: -len(server)]
    require(wrapper and wrapper[0] == "env", "unexpected launch wrapper")
    index, actual_unset, actual_sets = 1, [], {}
    while index < len(wrapper):
        if wrapper[index] == "-u":
            actual_unset.append(wrapper[index + 1])
            index += 2
        elif "=" in wrapper[index] and not wrapper[index].startswith("--"):
            key, value = wrapper[index].split("=", 1)
            require(key not in actual_sets, "duplicate environment binding")
            actual_sets[key] = value
            index += 1
        else:
            break
    require(
        actual_unset == contract["env"]["unset"]
        and actual_sets == contract["env"]["set"],
        "environment launch prefix differs",
    )
    cpus = contract.get("cpu_list")
    require(cpus == "184-191", "original GPU CPU placement differs")
    expected_wrapper = [
        "numactl",
        "--membind=3",
        "--",
        "taskset",
        "-c",
        cpus,
        artifacts["interpreter"]["path"],
        artifacts["profiler"]["path"],
        "--kernel-trace",
        "--memory-copy-trace",
        "--hip-trace",
        "--marker-trace",
        "--stats",
        "--output-format",
        "csv",
        "-d",
        contract["trace_dir"],
        "-o",
        "prof",
        "--",
    ]
    require(wrapper[index:] == expected_wrapper, "profiler/placement wrapper differs")
    expected_phases = _nemo_phase_payloads(contract["pass"])
    require(
        contract.get("phases") == expected_phases, "original workload/payload differs"
    )
    require(
        [m["label"] for m in run["marks"]] == list(expected_phases),
        "phase order/coverage differs",
    )
    opened, released = capture["device_claim_open"], capture["device_claim_released"]
    for field in (
        "schema",
        "claim_id",
        "device_id",
        "lock_path",
        "holder_pid",
        "holder_start_ticks",
        "holder_boot_id",
        "campaign_id",
        "purpose",
        "acquired_at",
        "expires_at",
    ):
        require(
            opened.get(field) is not None and opened.get(field) == released.get(field),
            "claim identity differs: " + field,
        )
    require(
        all(
            type(opened[key]) is int and opened[key] > 0
            for key in ("holder_pid", "holder_start_ticks")
        ),
        "invalid claim PID/birth",
    )
    require(
        opened["lock_path"] == "/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock",
        "foreign device lock identity",
    )
    require(
        opened["schema"] == "epyc.autokernel.device_claim_receipt.v1"
        and opened.get("state") == released.get("state") == "held",
        "claim was not held",
    )
    require(
        opened["device_id"]
        == capture["agent_binding"]["device_id"]
        == contract.get("device_id")
        == "mi210_0",
        "physical device differs",
    )
    require(
        opened["campaign_id"] == capture["campaign_id"] == contract["campaign_id"],
        "claim campaign differs",
    )
    require(
        run.get("capture_owner")
        == {
            key: opened[key]
            for key in (
                "holder_pid",
                "holder_start_ticks",
                "holder_boot_id",
                "claim_id",
                "device_id",
            )
        },
        "source-time owner differs",
    )
    require(opened["holder_boot_id"] == run["host_boot_id"], "claim boot differs")
    acquired, expires, release = map(
        instant, (opened["acquired_at"], opened["expires_at"], released["released_at"])
    )
    start, end = map(instant, (run["started_at"], run["finished_at"]))
    require(
        acquired <= start < end <= release <= expires
        and instant(run["drained_at"]) <= release,
        "run/drain outside held claim window",
    )
    for mark in run["marks"]:
        phase = expected_phases[mark["label"]]
        require(
            {"endpoint": mark.get("endpoint"), "payload": mark.get("payload")} == phase
            and mark.get("capture_contract_sha256") == digest,
            "actual HTTP/template payload differs",
        )
        require(
            start <= instant(mark["started_at"]) < instant(mark["ended_at"]) <= end,
            "request outside captured/claimed window",
        )


_NEMO_CAPTURE_SCHEMA = "epyc.autokernel.nemo_native_capture.v1"
_PROFILE_SCHEMA = "epyc.autokernel.profile_beliefs.v1"


def _is_nemo_profile(receipt: dict) -> bool:
    return (
        receipt.get("schema") == _PROFILE_SCHEMA
        and receipt.get("source_receipt", {}).get("schema") == _NEMO_CAPTURE_SCHEMA
    )


def _nemo_union(intervals: list[tuple[int, int]]) -> int:
    total = 0
    end = None
    for a, b in sorted(intervals):
        if b < a:
            raise ProjectionError("reversed native device interval")
        total += max(0, b - max(a, end if end is not None else a))
        end = max(b, end if end is not None else b)
    return total


def _validate_nemo_profile(receipt: dict, measurements: list) -> None:
    """Independent raw-data rederivation, without importing producer code."""
    import csv
    import io
    from collections import defaultdict

    def require(ok, reason):
        if not ok:
            raise ProjectionError("NEMO native profile: " + reason)

    require(
        receipt.get("receipt_sha256")
        == _canonical_sha256(
            {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        ),
        "final receipt digest differs",
    )
    ref = receipt["source_receipt"]
    path = Path(ref["locator"])
    require(path.is_absolute(), "capture locator must be absolute")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ref["sha256"], "capture bytes differ")
    source = json.loads(raw)
    require(
        source.get("schema") == _NEMO_CAPTURE_SCHEMA
        and source.get("status") == "complete"
        and source.get("purpose") == "prospective_scored_profile",
        "unqualified capture purpose/state",
    )
    roles = {"run", "native", "markers", "hip", "kernels", "agents"}
    require(set(source.get("files", {})) == roles, "raw readset roles differ")
    root = path.parent.resolve()
    values = {}
    for role, item in source["files"].items():
        p = root / item["path"]
        require(
            not Path(item["path"]).is_absolute()
            and p.resolve().is_relative_to(root)
            and not p.is_symlink(),
            "raw readset path escapes",
        )

        def stable(st):
            return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

        before = stable(p.stat())
        body = p.read_bytes()
        require(
            stable(p.stat()) == before
            and hashlib.sha256(body).hexdigest() == item["sha256"],
            "raw readset bytes differ",
        )
        values[role] = (
            json.loads(body)
            if role == "run"
            else [json.loads(x) for x in body.splitlines() if x]
            if role == "native"
            else list(csv.DictReader(io.StringIO(body.decode())))
        )
    require(
        set(source.get("analysis_sources", {}))
        == {"nemo_native_join.py", "autokernel_profile_beliefs.py"},
        "analysis source set differs",
    )
    for name, digest in source["analysis_sources"].items():
        _sha(digest, "analysis source " + name)
    require(
        receipt.get("producer")
        == {
            "producer_id": "scripts.benchmark.autokernel_profile_beliefs/v1",
            "path": "scripts/benchmark/autokernel_profile_beliefs.py",
            "sha256": source["analysis_sources"]["autokernel_profile_beliefs.py"],
        },
        "producer does not bind prospective source",
    )
    run, native = values["run"], values["native"]
    _nemo_validate_capture_contract(source, run)
    report = receipt.get("native_join", {})
    require(
        report.get("status") == "complete"
        and report.get("schema") == "epyc.autokernel.nemo_native_join.v1",
        "native join is not complete",
    )
    require(
        report.get("raw_readset")
        == {k: v["sha256"] for k, v in source["files"].items()}
        and report.get("source_run_hash") == _canonical_sha256(run),
        "report readset/run binding differs",
    )
    require(
        run.get("status") == "capture-complete-unvalidated"
        and not run.get("trip")
        and run.get("server_core_limit") == [0, 0]
        and run.get("teardown", {}).get("verified_dead") is True
        and run["teardown"].get("returncode") == 0
        and not run.get("cpu_only_instrumentation_smoke")
        and not run.get("tiny_gpu_instrumentation_smoke"),
        "canary/partial/undrained capture",
    )

    def parse_time(x):
        return datetime.fromisoformat(x.replace("Z", "+00:00"))

    require(
        parse_time(source["declared_at"]).tzinfo is not None
        and parse_time(source["declared_at"]) <= parse_time(run["started_at"])
        and source["started_at"] == run["started_at"]
        and source["ended_at"] == run["finished_at"],
        "prospective time/frame differs",
    )
    claim = receipt.get("device_claim", {})
    require(
        claim
        == {
            "opened": source["device_claim_open"],
            "released": source["device_claim_released"],
        },
        "device claim bytes differ",
    )
    for phase in ("opened", "released"):
        require(
            claim[phase].get("schema") == "epyc.autokernel.device_claim_receipt.v1"
            and claim[phase].get("campaign_id")
            == source["campaign_id"]
            == receipt["campaign_id"],
            "device claim identity differs",
        )
    require(
        claim["opened"]["claim_id"] == claim["released"]["claim_id"]
        and claim["opened"]["device_id"] == claim["released"]["device_id"]
        and claim["released"].get("released_at"),
        "claim release binding differs",
    )
    binding = source["agent_binding"]
    agents = [
        a
        for a in values["agents"]
        if a.get("Agent_Type") == "GPU" and int(a["Node_Id"]) == binding["agent_id"]
    ]
    require(
        len(agents) == 1
        and binding["device_id"] == claim["opened"]["device_id"]
        and all(
            int(agents[0][column]) == binding[key]
            for key, column in (
                ("drm_render_minor", "Drm_Render_Minor"),
                ("location_id", "Location_Id"),
                ("gpu_id", "Gpu_Id"),
            )
        ),
        "physical GPU binding differs",
    )
    process = (run["pid"], run["pid_birth_ticks"])
    require(
        (report.get("pid"), report.get("birth")) == process
        and report.get("host_boot_id") == run["host_boot_id"],
        "process incarnation differs",
    )

    def key(e):
        return (e["pid"], e["process_start_ticks"], e["tid"], e["api"], e["call_id"])

    begins, ends = {}, {}
    for event in native:
        require(
            event.get("schema") == "epyc.native_profile.v1"
            and (event.get("pid"), event.get("process_start_ticks")) == process,
            "foreign native event",
        )
        if event["event"] in (
            "encode_begin",
            "decode_begin",
            "encode_end",
            "decode_end",
        ):
            require(
                event["api"] in ("encode", "decode")
                and event["event"].startswith(event["api"]),
                "native API kind differs",
            )
            target = begins if event["event"].endswith("begin") else ends
            require(key(event) not in target, "duplicate native API event")
            target[key(event)] = event
    calls = report.get("calls", [])
    require(
        set(begins) == set(ends) == {tuple(c["key"]) for c in calls}
        and len(calls) == len(begins),
        "native call coverage differs",
    )
    for call in calls:
        k = tuple(call["key"])
        require(
            call.get("begin") == begins[k] and call.get("end") == ends[k],
            "native API payload differs",
        )
        markers = [
            r
            for r in values["markers"]
            if r["Function"] == f"epyc.{k[3]}.{k[4]}"
            and int(r["Process_Id"]) == k[0]
            and int(r["Thread_Id"]) == k[2]
        ]
        require(
            len(markers) == 1 and call.get("marker") == markers[0],
            "ROCTX marker differs",
        )
        require(
            int(markers[0]["Start_Timestamp"])
            <= begins[k]["monotonic_ns"]
            <= ends[k]["monotonic_ns"]
            <= int(markers[0]["End_Timestamp"]),
            "native marker clock differs",
        )
    owners, hip_by_corr = {}, defaultdict(list)
    for index, row in enumerate(values["hip"]):
        matches = [
            i
            for i, c in enumerate(calls)
            if int(row["Process_Id"]) == c["key"][0]
            and int(row["Thread_Id"]) == c["key"][2]
            and int(c["marker"]["Start_Timestamp"])
            <= int(row["Start_Timestamp"])
            <= int(row["End_Timestamp"])
            <= int(c["marker"]["End_Timestamp"])
        ]
        owners[index] = matches
        hip_by_corr[row["Correlation_Id"]].append(index)
    dispatches = defaultdict(list)
    unbound = []
    seen = set()
    for row in values["kernels"]:
        require(int(row["Agent_Id"]) == binding["agent_id"], "foreign dispatch agent")
        identity = tuple(
            row[k]
            for k in (
                "Agent_Id",
                "Queue_Id",
                "Kernel_Id",
                "Correlation_Id",
                "Start_Timestamp",
                "End_Timestamp",
            )
        )
        matches = hip_by_corr[row["Correlation_Id"]]
        target = owners[matches[0]] if len(matches) == 1 else []
        if len(target) == 1 and identity not in seen:
            dispatches[target[0]].append(row)
        else:
            unbound.append(row)
        seen.add(identity)
    require(
        report.get("unbound_dispatches") == unbound,
        "unbound dispatch inventory differs",
    )
    for index, call in enumerate(calls):
        require(
            call.get("dispatches") == dispatches[index]
            and call.get("hip_rows") == [i for i in owners if index in owners[i]],
            "HIP/dispatch ownership differs",
        )
        spans = [
            (int(d["Start_Timestamp"]), int(d["End_Timestamp"]))
            for d in dispatches[index]
        ]
        require(
            call.get("busy_ns") == (_nemo_union(spans) if spans else None)
            and call.get("kernel_sum_ns")
            == (sum(b - a for a, b in spans) if spans else None),
            "native device durations do not rederive",
        )
    metrics = []
    require(
        len(report.get("requests", [])) == len(run["marks"]), "request coverage differs"
    )
    for req, mark in zip(report["requests"], run["marks"]):
        rid = mark["response_request_id"]
        require(
            mark.get("clock") == "clock_gettime(CLOCK_MONOTONIC)"
            and not mark.get("err")
            and req["request_id"] == rid
            and req["label"] == mark["label"]
            and req["predicted_n"] == mark["predicted_n"]
            and req["start_ns"] == mark["start_monotonic_ns"]
            and req["end_ns"] == mark["end_monotonic_ns"]
            and req["status"] == "complete"
            and not req["unknown"],
            "request identity/coverage is unknown",
        )
        tokens = [
            e
            for e in native
            if e["event"] == "sampled_token" and e["request_id"] == rid
        ]
        require(
            req["tokens"] == tokens
            and [e["ordinal"] for e in tokens] == list(range(1, len(tokens) + 1))
            and len(tokens) == mark["predicted_n"],
            "emitted token identity differs",
        )
        indices = [
            i
            for i, c in enumerate(calls)
            if len(c["begin"]["slots"]) == 1
            and c["begin"]["slots"][0]["request_id"] == rid
        ]
        require(req["calls"] == indices, "native request call inventory differs")
        for i in indices:
            c, event = calls[i], calls[i]["begin"]
            slot = event["slots"][0]
            role = (
                "target"
                if event["ctx"] == slot["target_ctx"]
                else "drafter"
                if event["ctx"] == slot["drafter_ctx"]
                else "unknown"
            )
            require(
                not c["unknown"]
                and event["scope_id"] > 0
                and c["slot"] == slot
                and c["context_role"] == role != "unknown"
                and c["request_id"] == rid
                and len(event["rows"]) == event["n_tokens"]
                and [r["index"] for r in event["rows"]]
                == list(range(event["n_tokens"]))
                and c["end"]["rc"] == 0
                and req["start_ns"]
                <= event["monotonic_ns"]
                <= c["end"]["monotonic_ns"]
                <= req["end_ns"],
                "native request association differs",
            )
        ordered = sorted(
            (calls[i] for i in indices), key=lambda c: c["begin"]["monotonic_ns"]
        )
        for c in ordered:
            if c["key"][3] != "encode":
                continue
            following = [
                other
                for other in ordered
                if other["key"][2] == c["key"][2]
                and other["begin"]["ctx"] == c["begin"]["ctx"]
                and other["begin"]["scope_id"] == c["begin"]["scope_id"]
                and other["begin"]["monotonic_ns"] > c["begin"]["monotonic_ns"]
            ]
            inject = following[0] if following else None
            require(
                inject is not None
                and inject["key"][3] == "decode"
                and c["context_role"] == "drafter"
                and c.get("injection_call_key") == inject["key"]
                and c["begin"]["n_tokens"] == inject["begin"]["n_tokens"]
                and all(
                    r["pos"] is not None and r["seq_ids"] == [c["slot"]["slot"]]
                    for r in inject["begin"]["rows"]
                ),
                "encode/injection association differs",
            )
        for d in unbound:
            require(
                not (
                    int(d["Start_Timestamp"]) < req["end_ns"]
                    and int(d["End_Timestamp"]) > req["start_ns"]
                ),
                "unbound device work intersects request",
            )
        label = req["label"]
        if label not in ("S", "P", "M"):
            continue
        valid_samples = [
            s
            for s in run.get("during_request_gpu_proofs", [])
            if s.get("pid") == process[0]
            and s.get("kfd_present") is True
            and s.get("vram_bytes", 0) > 0
            and s.get("hip_library_maps")
            and req["start_ns"]
            <= s["sample_begin_monotonic_ns"]
            <= s["sample_end_monotonic_ns"]
            <= req["end_ns"]
        ]
        require(len(valid_samples) >= 5, "during-request residency is missing")
        if label in ("P", "M"):
            selected = [
                calls[i]
                for i in indices
                if calls[i]["context_role"] == "target"
                and calls[i]["slot"]["server_phase"] == "generation"
                and calls[i]["key"][3] == "decode"
            ]
            require(
                len(selected) >= (20 if label == "P" else 30) and not req["rounds"],
                "plain metric source differs",
            )
            for c in selected:
                expected = [
                    t
                    for t in tokens
                    if t["ordinal"] == c["slot"]["generated_before"] + 1
                    and t["target_ctx"] == c["begin"]["ctx"]
                    and t["slot"] == c["slot"]["slot"]
                    and t["task"] == c["slot"]["task"]
                    and t["tid"] == c["key"][2]
                ]
                previous = [
                    t
                    for t in tokens
                    if expected and t["ordinal"] == expected[0]["ordinal"] - 1
                ]
                input_rows = c["begin"]["rows"]
                require(
                    len(expected) == 1
                    and c["emitted"] == expected
                    and c["begin"]["n_tokens"] == 1
                    and len(previous) == 1
                    and len(input_rows) == 1
                    and input_rows[0]["token"] == previous[0]["token"]
                    and input_rows[0]["pos"] is not None
                    and input_rows[0]["seq_ids"] == [c["slot"]["slot"]],
                    "plain token identity differs",
                )
            numbers = [c["busy_ns"] / 1e6 for c in selected]
            metric = (
                "plain_token_busy_ms" if label == "P" else "bolt_decode_step_busy_ms"
            )
        else:
            accepts = [
                e
                for e in native
                if e["event"] == "spec_accept" and e["request_id"] == rid
            ]
            require(
                len(accepts) >= 10 and [g["event"] for g in req["rounds"]] == accepts,
                "native speculative vector coverage differs",
            )
            numbers, used = [], set()
            for group in req["rounds"]:
                event = group["event"]
                expected = [
                    i
                    for i in indices
                    if calls[i]["slot"]["generated_before"] == event["generated_before"]
                    and calls[i]["slot"]["server_phase"] == "generation"
                ]
                emitted = [
                    t
                    for t in tokens
                    if event["generated_before"]
                    < t["ordinal"]
                    <= event["generated_before"]
                    + len(event["accepted_tokens_including_bonus"])
                ]
                require(
                    expected == group["call_indices"]
                    and not used.intersection(expected)
                    and emitted == group["emitted"]
                    and emitted
                    and [t["token"] for t in emitted]
                    == event["accepted_tokens_including_bonus"][: len(emitted)]
                    and group["per_token_busy_ns"] is None,
                    "speculative round/token binding differs",
                )
                used.update(expected)
                spans = [
                    (int(d["Start_Timestamp"]), int(d["End_Timestamp"]))
                    for i in expected
                    for d in calls[i]["dispatches"]
                ]
                require(bool(spans), "speculative round device work missing")
                numbers.append(_nemo_union(spans) / 1e6)
            metric = "dflash_round_busy_ms"
        metrics.append(
            {
                "metric": metric,
                "label": label,
                "value_ms": sum(numbers) / len(numbers),
                "raw_values_ms": numbers,
                "observed_dependent_units": len(numbers),
                "request_id": rid,
                "reps": 1,
                "reps_basis": "one traced request; dependent native calls/rounds, no repeats or noise floor",
            }
        )
    require(
        metrics == receipt.get("native_metric_vectors")
        and len(metrics) == len(measurements),
        "native metric vectors differ",
    )
    for vector, row in zip(metrics, measurements):
        require(
            row["metric"] == vector["metric"]
            and row["value"] == vector["value_ms"]
            and row["unit"] == "ms"
            and row["metric_direction"] == "lower_better"
            and row["category"] == "BASELINE"
            and row["reps"] == 1
            and row["reps_basis"] == vector["reps_basis"],
            "measurement does not rederive",
        )
        expected = {
            "measurement_id": source["campaign_id"]
            + ":"
            + vector["label"]
            + ":"
            + vector["metric"],
            "metric": vector["metric"],
            "value": vector["value_ms"],
            "unit": "ms",
            "metric_direction": "lower_better",
            "category": "BASELINE",
            "reps": 1,
            "reps_basis": vector["reps_basis"],
            "claim": (
                "One traced native request observed "
                + vector["metric"]
                + "; attribution only, no keep/ship or optimization conclusion"
            ),
            "extra": {
                "native_request_id": vector["request_id"],
                "phase": vector["label"],
                "raw_values_ms": vector["raw_values_ms"],
                "observed_dependent_units": vector["observed_dependent_units"],
                "protocol_scope": "original NEMO L/B attribution, unratified single-request observation",
                "native_join_sha256": _canonical_sha256(report),
                "raw_readset": report["raw_readset"],
                "analysis_sources": source["analysis_sources"],
            },
        }
        expected["measurement_sha256"] = _canonical_sha256(expected)
        require(
            row == expected, "full producer-written measurement row does not rederive"
        )


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
    if receipt.get("schema") in {_GPU_BANK_SCHEMA, _GPU_RESULT_SCHEMA}:
        if not isinstance(measurements, list) or not measurements:
            raise ProjectionError(
                "GPU discovery v2 requires prospective producer-written belief rows")
        _validate_gpu_discovery_measurements(receipt, measurements)
    if _is_nemo_profile(receipt):
        _validate_nemo_profile(receipt, measurements)
    protocol = None
    if receipt.get("schema") in {_GPU_BANK_SCHEMA, _GPU_RESULT_SCHEMA}:
        runs_key = "anchor_runs" if receipt["schema"] == _GPU_BANK_SCHEMA else "candidate_runs"
        protocol = _gpu_run_protocol(receipt[runs_key][0], runs_key)
    return tuple({
        **({"llama_bench_protocol": protocol} if protocol else {}),
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
    if _is_nemo_profile(receipt):
        _validate_nemo_profile(receipt, receipt["belief_measurements"])
        index = native.get("measurement_index")
        if (type(index) is not int or not 0 <= index < len(receipt["belief_measurements"])
                or measurement != receipt["belief_measurements"][index]):
            raise ProjectionError("NEMO projection row differs from finalized measurement vector")
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
        protocol_id="" if _is_nemo_profile(receipt) else schema,
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
            **({"llama_bench_protocol": native["llama_bench_protocol"]}
               if isinstance(native.get("llama_bench_protocol"), dict) else {}),
            **extra,
        },
    )
