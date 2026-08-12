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


def arena_receipt(*, checkpoint_hours=2.0, ended_at="2026-08-12T08:23:37Z"):
    value = {
        "schema": aux._ARENA_SCHEMA,
        "producer_id": aux._ARENA_PRODUCER,
        "status": "pass",
        "authority": "diagnostic_only",
        "campaign_id": "inf03-mi210-controller-ab-v1-available-source-six-arm-v1",
        "started_at": "2026-08-12T08:20:00Z",
        "ended_at": ended_at,
        "task": {
            "task_id": "instruction2triton.rocmbench.test_add_kernel",
            "controller_id": "claude_codex_actor_critic",
        },
        "source": {
            "checkpoint_hours": checkpoint_hours,
            "entrypoint_sha256": "a" * 64,
        },
        "artifacts": [{"path": "workspace/kernel.py", "sha256": "b" * 64}],
        "dependencies": {},
        "belief_measurements": [
            {
                "measurement_id": "arena_correctness_pass_rate",
                "metric": "geak_arena_correctness_pass_rate",
                "value": 1.0,
                "unit": "fraction",
                "metric_direction": "higher_better",
                "category": "CANDIDATE",
                "reps": 1,
                "reps_basis": "one centralized task evaluation",
                "claim": "correctness pass rate",
                "extra": {"controller_id": "claude_codex_actor_critic"},
            },
            {
                "measurement_id": "arena_timing_harness_validity_rate",
                "metric": "geak_arena_timing_harness_validity_rate",
                "value": 1.0,
                "unit": "fraction",
                "metric_direction": "higher_better",
                "category": "CANDIDATE",
                "reps": 1,
                "reps_basis": "one centralized timing phase",
                "claim": "timing validity rate",
                "extra": {"controller_id": "claude_codex_actor_critic"},
            },
        ],
    }
    value["receipt_sha256"] = aux._canonical_sha256(value)
    return value


def arena_intermediate_receipt():
    campaign = "inf03-mi210-controller-ab-v2-available-source-seven-arm-v2"
    attempt = "inf03-available-source-seven-arm-r18-20260812"
    task = "instruction2triton.rocmbench.test_add_kernel"
    arm = "claude_codex_actor_critic"
    source = {"test_add_kernel.py": "a" * 64}
    opened = {"campaign_id": attempt, "claim_id": "akd-intermediate",
              "device_id": "mi210_0", "released_at": None}
    released = {**opened, "released_at": "2026-08-12T19:40:05Z"}
    sampler = {"schema": "epyc.autokernel.device_sampling_receipt.v1",
               "sample_count": 2,
               "samples": [{"offset_s": 0.0}, {"offset_s": 0.25}]}
    sampler["sha256"] = aux._canonical_sha256(sampler)
    window = {
        "schema": aux._ARENA_INTERMEDIATE_WINDOW_SCHEMA,
        "status": "complete", "phase": "controller_intermediate_evaluation",
        "failure": None, "gpu_action_executed_only_while_claim_held": True,
        "campaign_id": campaign, "claim_campaign_id": attempt,
        "task_id": task, "arm_id": arm, "checkpoint_hours": 2.0,
        "ordinal": 1, "device_claim_open": opened,
        "device_claim_released": released, "device_sampling": sampler,
    }
    window["receipt_sha256"] = aux._canonical_sha256(window)
    producer = {"producer_id": aux._ARENA_INTERMEDIATE_PRODUCER,
                "path": aux._ARENA_INTERMEDIATE_PRODUCER_PATH,
                "sha256": "b" * 64}
    evaluation = {"pass_compilation": True, "pass_correctness": True,
                  "valid_optimized_cases": 4}
    shared = {
        "measurement_role": "kernel_authoring_intermediate_evaluation",
        "campaign_id": campaign, "attempt_id": attempt,
        "claim_campaign_id": attempt, "task_id": task, "controller_id": arm,
        "checkpoint_hours": 2.0, "evaluation_ordinal": 1,
        "source_sha256": source, "baseline_receipt_sha256": "c" * 64,
        "measurement_window_sha256": window["receipt_sha256"],
        "producer_id": producer["producer_id"], "producer_path": producer["path"],
        "producer_sha256": producer["sha256"],
        "authority": "diagnostic_only_no_ranking_or_promotion_authority",
    }
    measurements = []
    for measurement_id, metric, role, claim in (
        ("arena_intermediate_correctness_pass_rate",
         "geak_arena_intermediate_correctness_pass_rate",
         "kernel_authoring_intermediate_correctness",
         "Whether this brokered intermediate candidate passed compilation and correctness"),
        ("arena_intermediate_timing_harness_validity_rate",
         "geak_arena_intermediate_timing_harness_validity_rate",
         "kernel_authoring_intermediate_timing_validity",
         "Whether this brokered intermediate evaluation admitted any optimized timing case"),
    ):
        row = {"measurement_id": measurement_id, "metric": metric, "value": 1.0,
               "unit": "fraction", "metric_direction": "higher_better",
               "category": "CANDIDATE", "claim": claim, "reps": 1,
               "reps_basis": "one brokered AgentKernelArena intermediate evaluation",
               "extra": {**shared, "measurement_role": role, "passed": 1,
                         "total": 1}}
        row["measurement_sha256"] = aux._canonical_sha256(row)
        measurements.append(row)
    value = {
        "schema": aux._ARENA_INTERMEDIATE_SCHEMA, "campaign_id": campaign,
        "attempt_id": attempt, "claim_campaign_id": attempt, "task_id": task,
        "arm_id": arm, "checkpoint_hours": 2.0, "evaluation_ordinal": 1,
        "workspace": "/campaign/cell/workspace", "evaluation_root": "/campaign/eval",
        "source_sha256": source, "baseline_receipt_sha256": "c" * 64,
        "evaluation": evaluation, "measurement_window": window, "producer": producer,
        "belief_measurements": measurements, "previous_receipt_sha256": None,
        "authority": "controller_feedback_only",
    }
    value["receipt_sha256"] = aux._canonical_sha256(value)
    return value


def test_arena_intermediate_projects_only_exact_prospective_rows():
    source = arena_intermediate_receipt()
    rows = aux.native_rows(source, receipt_locator="/r18/0001-result.json",
                           receipt_sha256="d" * 64, attestation_present=True)
    claims = [aux.project(row) for row in rows]
    assert len(claims) == 2
    assert all(claim.protocol_id == aux._ARENA_INTERMEDIATE_SCHEMA for claim in claims)
    assert all(claim.extra["authority"] ==
               "diagnostic_only_no_ranking_or_promotion_authority" for claim in claims)
    assert len({claim.measurement_id for claim in claims}) == 2


@pytest.mark.parametrize("mutation", ["row", "window", "claim", "authority"])
def test_arena_intermediate_refuses_tampered_or_upgraded_evidence(mutation):
    source = arena_intermediate_receipt()
    if mutation == "row":
        source["belief_measurements"][0]["value"] = 0.0
    elif mutation == "window":
        source["measurement_window"]["device_sampling"]["sample_count"] = 3
    elif mutation == "claim":
        source["measurement_window"]["device_claim_released"]["released_at"] = None
    else:
        source["authority"] = "rankable"
    source["receipt_sha256"] = aux._canonical_sha256(
        {key: value for key, value in source.items() if key != "receipt_sha256"})
    with pytest.raises(ct.ProjectionError):
        aux.native_rows(source)


def hip_receipt():
    campaign = "ak-hip-arm-fixture-r1"
    task_id = "torch2hip/gpumode/16636_SiLU"
    candidate_sha = "c" * 64

    def window(phase, claim_id, started_at, ended_at):
        opened = {"schema": "epyc.autokernel.device_claim_receipt.v1",
                  "campaign_id": campaign, "claim_id": claim_id,
                  "device_id": "mi210_0", "acquired_at": started_at,
                  "released_at": None}
        released = dict(opened)
        released["released_at"] = ended_at
        sampling = {"schema": "epyc.autokernel.device_sampling_receipt.v1",
                    "sample_count": 2, "samples": [{"offset_s": 0.0},
                                                     {"offset_s": 0.25}]}
        sampling["sha256"] = aux._canonical_sha256(sampling)
        value = {"schema": aux._HIP_WINDOW_SCHEMA, "phase": phase,
                 "task_id": task_id, "campaign_id": campaign,
                 "status": "complete", "started_at": started_at,
                 "ended_at": ended_at, "device_claim_open": opened,
                 "device_claim_released": released,
                 "device_sampling": sampling,
                 "gpu_action_executed_only_while_claim_held": True,
                 "failure": None}
        value["receipt_sha256"] = aux._canonical_sha256(value)
        return value

    common = {"unit": "fraction", "metric_direction": "higher_better",
              "category": "CANDIDATE", "reps": 11,
              "reps_basis": "scored_public_cases"}
    value = {
        "schema": aux._HIP_SCHEMA, "status": "complete",
        "authority": "observation_only", "campaign_id": campaign,
        "started_at": "2026-08-12T09:30:00Z", "ended_at": "2026-08-12T09:31:00Z",
        "producer": {"producer_id": aux._HIP_PRODUCER,
                     "path": aux._HIP_PRODUCER_PATH, "sha256": "a" * 64},
        "task": {"schema": aux._HIP_TASK_SCHEMA, "task_id": task_id,
                 "task_type": "torch2hip", "target_file": "hip/candidate.hip",
                 "target": {"gpu_model": "MI210", "gfx_arch": "gfx90a"},
                 "file_sha256": {"config.yaml": "b" * 64},
                 "vendor_identity": {"clean": True,
                                     "commit": aux._HIP_VENDOR_COMMIT}},
        "hardware": {"architectures": ["gfx90a"], "target_gfx_arch": "gfx90a",
                     "target_gpu_model": "MI210"},
        "candidate": {"source": "/fixture/candidate.hip", "sha256": candidate_sha},
        "evaluation": {"compiled": True, "correct": True,
                       "public_correctness_cases": 11, "valid_baseline_cases": 11,
                       "speedup_rankable": False, "profiler_metrics": {},
                       "integrity_flags": ["public_shapes_only",
                                           "honest_vendor_baseline_not_bound"]},
        "measurement_windows": [
            window("vendor_baseline", "akd-baseline", "2026-08-12T09:30:10Z",
                   "2026-08-12T09:30:15Z"),
            window("centralized_final_evaluation", "akd-final",
                   "2026-08-12T09:30:20Z", "2026-08-12T09:30:55Z")],
        "belief_measurements": [
            {"measurement_id": "hip_public_correctness_pass_rate",
             "metric": "autokernel_hip_public_correctness_pass_rate", "value": 1.0,
             "claim": "Fraction of scored public Torch2HIP correctness cases that passed",
             **common, "extra": {"measurement_role": "raw_hip_authoring_correctness",
                                 "passed": 11, "total": 11,
                                 "candidate_source_sha256": candidate_sha,
                                 "authority": "observation_only"}},
            {"measurement_id": "hip_timing_harness_validity_rate",
             "metric": "autokernel_hip_timing_harness_validity_rate", "value": 1.0,
             "claim": "Fraction of scored Torch2HIP timing cases admitted as valid",
             **common, "extra": {"measurement_role": "raw_hip_timing_validity",
                                 "passed": 11, "total": 11,
                                 "candidate_source_sha256": candidate_sha,
                                 "authority": "observation_only"}}],
        "constraints": {"performance_claim": False, "promotion_authority": False,
                        "production_tree_touched": False, "frozen_kernel_built": False},
    }
    value["receipt_sha256"] = aux._canonical_sha256(value)
    return value


def hip_decision_receipt():
    campaign = "hip-silu-decision-grade-fixture-r1"

    def window(phase, claim_id):
        opened = {"claim_id": claim_id, "device_id": "mi210_0",
                  "campaign_id": campaign, "released_at": None}
        released = {**opened, "released_at": "2026-08-12T10:22:00Z"}
        sampling = {"sample_count": 2, "samples": [{"sclk_mhz": 800.0},
                                                      {"sclk_mhz": 1700.0}]}
        sampling["sha256"] = aux._canonical_sha256(sampling)
        value = {"schema": aux._HIP_WINDOW_SCHEMA, "phase": phase,
                 "campaign_id": campaign, "task_id": "torch2hip/gpumode/16636_SiLU",
                 "status": "complete", "device_claim_open": opened,
                 "device_claim_released": released, "device_sampling": sampling}
        value["receipt_sha256"] = aux._canonical_sha256(value)
        return value

    blocks = [{"block_index": index,
               "order": "anchor_first" if index % 2 == 0 else "candidate_first",
               "candidate_ns": 9_200.0, "anchor_ns": 9_936.0,
               "candidate_measured_duration_ns": 276_000_000.0,
               "anchor_measured_duration_ns": 298_080_000.0}
              for index in range(20)]
    speedup = 9_936.0 / 9_200.0
    checks = [{"outcome": "PASS", "reasons": ["fixture"]} for _ in range(40)]
    cases = [{"case_id": f"s{index:02d}", "shape": [255 + index],
              "distribution": f"d{index:02d}"} for index in range(24)]
    correctness_cases = [{"case_id": row["case_id"], "passed": True,
                          "max_abs_error": 1e-7} for row in cases]
    sandbox = {}
    for phase, devices in (("compile", []),
                           ("correctness", ["/dev/kfd", "/dev/dri/renderD128"]),
                           ("timing", ["/dev/kfd", "/dev/dri/renderD128"])):
        sandbox[phase] = {
            "activation": {"euid": 1000, "writable_device_paths": devices},
            "teardown": {"verified_empty": True, "removed": True}}
    rows = [
        {"measurement_id": "hip_sealed_correctness_pass_rate",
         "metric": "autokernel_hip_sealed_correctness_pass_rate", "value": 1.0,
         "unit": "fraction", "metric_direction": "higher_better",
         "category": "CANDIDATE",
         "claim": "Fraction of sealed hostile host-double SiLU cases passed",
         "reps": 24, "reps_basis": "sealed_hostile_cases"},
        {"measurement_id": "hip_exact_provider_speedup",
         "metric": "autokernel_hip_speedup_vs_exact_torch_rocm_compile",
         "value": speedup, "unit": "ratio", "metric_direction": "higher_better",
         "category": "CANDIDATE",
         "claim": "Median paired-block speedup over exact Torch-ROCm-compile SiLU",
         "reps": 20, "reps_basis": "paired_randomized_blocks"},
    ]
    value = {
        "schema": aux._HIP_DECISION_SCHEMA, "status": "complete",
        "authority": aux._HIP_DECISION_AUTHORITY, "campaign_id": campaign,
        "ended_at": "2026-08-12T10:22:00Z",
        "producer": {"producer_id": aux._HIP_DECISION_PRODUCER,
                     "path": "/repo/scripts/kernel_rnd/autokernel/controller/hip_decision_grade.py",
                     "sha256": "a" * 64},
        "candidate": {"sha256": "b" * 64, "unchanged_at_terminal": True},
        "task": {"schema": aux._HIP_TASK_SCHEMA,
                 "task_id": "torch2hip/gpumode/16636_SiLU",
                 "target": {"gpu_model": "MI210", "gfx_arch": "gfx90a"},
                 "vendor_identity": {"clean": True, "commit": aux._HIP_VENDOR_COMMIT}},
        "sealed_suite": {"suite_id": "sealed_silu_boundary_host_double/v1",
                         "suite_seed_generated_after_candidate_seal": True,
                         "exact_shapes_disclosed_after_candidate_seal": True,
                         "cases": cases},
        "correctness": {"oracle": "independent_host_double_stable_silu/v1",
                        "all_passed": True, "passed": 24, "total": 24,
                        "bitwise_repeatability_required": True,
                        "two_distinct_output_poisons": ["nan", -12345.25],
                        "cases": correctness_cases},
        "integrity": {"clean": True, "candidate_never_received_expected_outputs": True,
                      "static_scan": {"clean": True, "findings": []},
                      "sandbox": sandbox},
        "timing": {"provider": {"provider_id": aux._HIP_DECISION_PROVIDER,
                                 "expression": "x * torch.sigmoid(x)",
                                 "backend": "inductor", "fullgraph": True,
                                 "dynamic": False, "graph_count": 1,
                                 "graph_break_count": 0,
                                 "implementation_identity": {"tree_sha256": "c" * 64}},
                   "blocks": blocks, "block_count": 20, "repetitions_per_arm": 30_000,
                   "ranked_duration_admission": {"all_arms_passed": True,
                                                "minimum_ns": 250_090_903,
                                                "minimum_observed_ns": 276_000_000.0,
                                                "checks": checks},
                   "median_speedup": speedup,
                   "e_process": {"construction_id":
                                 "sign_martingale_predictable_lambda/v1",
                                 "threshold": 20.0, "first_crossing_block": 9,
                                 "signs": [1.0] * 20},
                   "candidate_beats_exact_provider": True},
        "decision": {"rankable_against_exact_task_local_provider": True,
                     "candidate_beats_exact_provider": True,
                     "release_or_promotion_authority": False,
                     "experimental_llama_integration_required_before_any_release": True},
        "constraints": {"production_tree_touched": False, "frozen_kernel_built": False,
                        "promotion_authority": False, "shared_rocm_mutated": False},
        "measurement_windows": [window("sealed_correctness", "akd-one"),
                                window("exact_provider_timing", "akd-two")],
        "belief_measurements": rows,
    }
    value["receipt_sha256"] = aux._canonical_sha256(value)
    return value


def p2_receipt():
    shape = {"np_slots": 8, "slot_context_tokens": 8192,
             "total_context_tokens": 65536, "mtp": False}
    summaries = {}
    measurements = []
    for arm, (cpu_list, cpu_region, numa_node, relation, role, category) in (
            aux._P2_ARMS.items()):
        factor = {"I": 1.0, "H": 1.01, "Lp": 1.03, "Ls": 1.0}[arm]
        samples = []
        for block in range(10):
            samples.append({
                "sample_id": f"sample-{block}-{arm}",
                "aggregate_decode_tps": (100.0 + block) * factor,
                "p50_latency_ms": 1000.0 - block,
                "p95_latency_ms": 1200.0 - block,
                "cpu_claim": {"opened": {"claim_id": f"cpu-{block}-{arm}"}},
                "device_claim": {"opened": {"claim_id": f"gpu-{block}-{arm}"}},
            })
        decode = [sample["aggregate_decode_tps"] for sample in samples]
        p50 = [sample["p50_latency_ms"] for sample in samples]
        p95 = [sample["p95_latency_ms"] for sample in samples]
        ratios = [factor] * 10
        summaries[arm] = {
            "cpu_list": cpu_list, "cpu_region": cpu_region,
            "numa_node": numa_node, "relation": relation, "role": role,
            "n": 10, "median_decode_tps": sum(decode[4:6]) / 2,
            "median_p50_latency_ms": sum(p50[4:6]) / 2,
            "median_p95_latency_ms": sum(p95[4:6]) / 2,
            "paired_ratios_to_incumbent": ratios,
            "median_paired_ratio_to_incumbent": factor,
            "samples": samples,
        }
        common = {
            "measurement_surface": "p2_5j_four_arm_host_thread_placement",
            "arm": arm, "arm_role": role, "cpu_list": cpu_list,
            "cpu_region": cpu_region, "numa_node": numa_node,
            "relation": relation, "device_id": "mi210_0", "shape": shape,
            "authority": aux._P2_AUTHORITY,
            "placement_selection_authority": False,
            "kernel_speedup_authority": False, "carve_authority": False,
            "production_activation_authority": False,
            "sample_ids": [sample["sample_id"] for sample in samples],
            "cpu_claim_ids": [sample["cpu_claim"]["opened"]["claim_id"]
                              for sample in samples],
            "device_claim_ids": [sample["device_claim"]["opened"]["claim_id"]
                                 for sample in samples],
        }
        for suffix, (metric, unit, direction, summary_key, sample_key,
                     measurement_role) in aux._P2_METRICS.items():
            values = ratios if suffix == "paired_ratio_to_incumbent" else [
                sample[sample_key] for sample in samples]
            row = {
                "measurement_id": f"p2_5j_{arm.lower()}_{suffix}",
                "metric": metric, "value": summaries[arm][summary_key], "unit": unit,
                "metric_direction": direction, "category": category, "reps": 10,
                "reps_basis": aux._P2_REPS_BASIS,
                "claim": f"fixture P2-5j {arm} {suffix}; observation only",
                "extra": {**common, "measurement_role": measurement_role,
                          "block_values": values, "aggregation": "median"},
            }
            if suffix == "paired_ratio_to_incumbent":
                row["extra"]["incumbent_arm"] = "I"
            row["measurement_sha256"] = aux._canonical_sha256(row)
            measurements.append(row)
    value = {
        "schema": aux._P2_SCHEMA, "status": "passed",
        "authority": aux._P2_AUTHORITY, "campaign_id": "p2-5j-successor",
        "ended_at": "2026-08-12T02:00:00Z",
        "producer": {"producer_id": aux._P2_PRODUCER,
                     "path": aux._P2_PRODUCER_PATH, "sha256": "9" * 64},
        "identity": {"device": {"device_id": "mi210_0"}},
        "shape": shape, "arm_summaries": summaries,
        "belief_measurements": measurements,
    }
    value["receipt_sha256"] = aux._canonical_sha256(value)
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


def iq2_model_receipt():
    campaign = "ak-iq2-model-confirmation"
    candidate_id = "akc-iq2-one-row"
    claim_id = "akclaim-iq2model"
    model_path = "/models/Qwen3-IQ2_XXS.gguf"
    now = "2026-08-11T20:00:00+00:00"

    def digest(tag):
        import hashlib
        return hashlib.sha256(tag.encode()).hexdigest()

    anchor = {
        "source_commit": digest("anchor")[:40],
        "binary_sha256": digest("anchor-binary"),
        "linkage_sha256": digest("anchor-linkage"),
        "measurement_event_ids": ["ake-anchor-iq2"],
    }
    model = {
        "model_id": "Qwen3-IQ2-XXS", "path": model_path,
        "sha256": digest("model"), "quantization": "IQ2_XXS",
    }
    lock_root = "/tmp/autokernel-locks"
    regions = ["q0", "q1", "q2", "q3"]
    claim = {
        "schema": aux._IQ2_CLAIM_SCHEMA, "claim_id": claim_id,
        "role": "autokernel", "roles": ["autokernel"], "cpu_list": "0-191",
        "physical_core_list": "0-95", "regions": regions,
        "lock_paths": sorted(
            f"{lock_root}/cpu_region.{role}.{region}.lock"
            for region in regions for role in ("GLOBAL", "autokernel")
        ),
        "lock_root": lock_root, "state": "held", "holder_pid": 1234,
        "holder_start_ticks": 5678,
        "holder_boot_id": "00000000-0000-0000-0000-000000000001",
        "host": "Beelzebub", "purpose": "IQ2 model confirmation",
        "campaign_id": campaign, "acquired_at": "2026-08-11T19:55:00+00:00",
        "released_at": "2026-08-11T20:05:00+00:00",
    }
    event_ids = [
        f"ake-iq2-{lane}-{tier}" for lane in ("tg", "pp") for tier in ("t1", "t2")
    ]
    candidate = {
        "schema": aux._IQ2_CANDIDATE_SCHEMA, "candidate_id": candidate_id,
        "campaign_id": campaign, "status": "evaluating",
        "worktree": {"path": "/work/candidate", "source_commit": digest("source")[:40]},
        "source_snapshot": {"snapshot_sha256": digest("snapshot"),
                            "patch_bundle_sha256": digest("patch")},
        "build": {"build_dir": "/work/candidate/build",
                  "log_sha256": digest("build-log")},
        "artifacts": {"binary_sha256": digest("candidate-binary"),
                      "linkage_sha256": digest("candidate-linkage")},
        "receipts": {"host_receipt": "host-iq2", "resource_claim_receipt": claim_id},
        "evaluation_event_ids": event_ids,
    }

    def execution(lane, arm):
        recipe = aux._IQ2_LANES[lane][0]
        is_candidate = arm == "candidate"
        root = "/work/candidate" if is_candidate else "/work/anchor"
        binary = (candidate["artifacts"]["binary_sha256"] if is_candidate
                  else anchor["binary_sha256"])
        binary_path = f"{root}/build/bin/llama-bench"
        return {
            "runner_id": "autokernel.execution.microbench/v1",
            "registry_id": "ak-recipe-registry/v1", "arm": arm,
            "recipe_id": recipe, "constructor_sha256": digest(f"constructor-{lane}"),
            "argv_sha256": digest(f"argv-{lane}-{arm}"),
            "env_sha256": digest(f"env-{lane}-{arm}"),
            "recipe_env": {"GGML_IQK": "1"}, "params": {"model": model_path},
            "binary_path": binary_path, "binary_sha256": binary, "binary_size": 123,
            "source_root": root, "library_path": f"{root}/build/bin",
        }

    def block(lane, index, anchor_samples, candidate_samples):
        order = "anchor_first" if index == 0 else "candidate_first"
        unit_id = f"qwen3-iq2-xxs:{lane}"
        paired = [index, unit_id, "confirmation", order, "base", None, now,
                  anchor_samples, candidate_samples]

        def invocation(arm, samples):
            return {
                "arm": arm, "receipt": execution(lane, arm),
                "row": {"model_filename": model_path, "samples_ts": samples},
                "samples": samples,
                "checks": [["output_matches_recipe", {"outcome": "PASS"}]],
                "spawn": {"returncode": 0, "timed_out": False},
            }
        return {
            "plan": {"block_index": index, "unit_id": unit_id, "order": order},
            "invocations": [invocation("anchor", anchor_samples),
                            invocation("candidate", candidate_samples)],
            "paired_block": paired, "refusals": [], "complete": True,
        }

    def event(lane, tier, raw_samples, estimate, transfer):
        event_id = f"ake-iq2-{lane}-{'t1' if tier == 'T1a' else 't2'}"
        metric = aux._IQ2_LANES[lane][1] if tier == "T2" else "backend_op_time"
        return {
            "schema": aux._IQ2_EVENT_SCHEMA, "event_id": event_id,
            "campaign_id": campaign, "candidate_id": candidate_id, "tier": tier,
            "backend": "llama_cpu", "device_state": None, "co_residency": "single",
            "status": "pass", "integrity_flags": [], "resource_claim_receipt": claim_id,
            "host_receipt": "host-iq2",
            "artifact": {"source_sha256": candidate["source_snapshot"]["snapshot_sha256"],
                         "binary_sha256": candidate["artifacts"]["binary_sha256"],
                         "linkage_sha256": candidate["artifacts"]["linkage_sha256"]},
            "anchor": anchor,
            "claim_grammar": {"protocol_id": "P-AK-SEARCH-1/v1", "metric": metric,
                              "metric_direction": ("higher_better" if tier == "T2"
                                                   else "lower_better"),
                              "category": "CANDIDATE", "reps": 2},
            "scope_denominator": {"machine_subset": "full", "cores": 96},
            "performance": {"raw_samples": raw_samples, "paired_blocks": 2,
                            "estimate": estimate,
                            "search_discipline": {
                                "search_grade": {"satisfied": True, "failed": []},
                                "void_findings": [], "effect_resolution": "improvement",
                                "speed_rank_admissible": True,
                            }},
            "transfer_ratio_to": transfer, "created_at": now,
        }

    def lane(lane_name):
        samples = {
            "tg": [([10.0, 12.0], [11.0, 13.0]), ([14.0, 16.0], [15.0, 17.0])],
            "pp": [([100.0, 102.0], [103.0, 105.0]),
                   ([104.0, 106.0], [107.0, 109.0])],
        }[lane_name]
        blocks = [block(lane_name, index, a, c)
                  for index, (a, c) in enumerate(samples)]
        raw = {
            "schema": aux._IQ2_RAW_SCHEMA,
            "runner_id": "autokernel.execution.microbench/v1",
            "recipe_id": aux._IQ2_LANES[lane_name][0], "candidate_id": candidate_id,
            "complete": True, "refusals": [], "order_control": {"outcome": "PASS"},
            "scope_denominator": {"machine_subset": "full", "cores": 96},
            "anchor_identity": anchor, "started_at": now,
            "ended_at": "2026-08-11T20:04:00+00:00",
            "candidate_receipt": execution(lane_name, "candidate"),
            "anchor_receipt": execution(lane_name, "anchor"),
            "claim_attestations": [
                {"claim_id": claim_id, "outcome": "PASS", "cpu_list": "0-191"}
            ],
            "blocks": blocks,
        }
        t1_id = f"ake-iq2-{lane_name}-t1"
        t1 = event(lane_name, "T1a", [1.0, 0.9], -0.1, [])
        t2 = event(lane_name, "T2", [item["paired_block"] for item in blocks], 0.05,
                   [{"event_id": t1_id, "tier": "T1a", "source_effect": 0.05,
                     "target_effect": -0.1, "ratio": -0.5}])
        return {"t1_event": t1, "t2_event": t2, "raw_vectors": [raw]}

    source = {
        "schema": aux._IQ2_MODEL_SCHEMA, "status": "complete",
        "campaign_id": campaign, "candidate_id": candidate_id,
        "created_at": now, "ended_at": "2026-08-11T20:05:00+00:00",
        "model_identity": model, "candidate_record": candidate,
        "anchor_identity": anchor, "resource_claim_receipt": claim,
        "lanes": {lane_name: lane(lane_name) for lane_name in ("tg", "pp")},
    }
    source_sha = aux._ak_content_sha256(source)
    producer_sha = digest("producer")
    evidence = {
        lane_name: aux._iq2_lane_evidence(
            lane_name, source["lanes"][lane_name], campaign_id=campaign,
            candidate_id=candidate_id, candidate=candidate, model=model,
            anchor=anchor, claim=claim,
        ) for lane_name in ("tg", "pp")
    }
    measurements = [
        aux._iq2_expected_row(
            lane=lane_name, arm=arm, evidence=evidence[lane_name], model=model,
            candidate=candidate, anchor=anchor, claim=claim, source_sha=source_sha,
            producer_sha=producer_sha,
        )
        for lane_name in ("tg", "pp") for arm in ("anchor", "candidate")
    ]
    finalized = copy.deepcopy(source)
    finalized.update({
        "source_receipt_sha256": source_sha, "producer_id": aux._IQ2_MODEL_PRODUCER,
        "producer_sha256": producer_sha, "belief_measurements": measurements,
    })
    finalized["self_sha256"] = aux._ak_content_sha256(finalized)
    return finalized


def resign_iq2_model(value):
    value.pop("self_sha256", None)
    value["self_sha256"] = aux._ak_content_sha256(value)


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


def test_iq2_model_confirmation_rederives_four_model_level_rows():
    source = iq2_model_receipt()
    native = aux.native_rows(
        source, receipt_locator="probe:sc23b/finalized.json",
        receipt_sha256="8" * 64, attestation_present=True,
    )
    projected = [aux.project(row) for row in native]
    assert [row.extra["native_measurement_id"] for row in projected] == [
        "iq2_xxs_model_tg_anchor_median_tokens_per_s",
        "iq2_xxs_model_tg_candidate_median_tokens_per_s",
        "iq2_xxs_model_pp_anchor_median_tokens_per_s",
        "iq2_xxs_model_pp_candidate_median_tokens_per_s",
    ]
    assert [row.value for row in projected] == [13.0, 14.0, 103.0, 106.0]
    assert all(row.protocol_id == aux._IQ2_MODEL_SCHEMA for row in projected)
    assert all(row.metric_direction == "higher_better" for row in projected)
    assert all(row.extra["model_identity"]["quantization"] == "IQ2_XXS"
               for row in projected)


@pytest.mark.parametrize("defect", [
    "final_self", "source", "producer", "model", "candidate", "anchor", "claim",
    "event", "transfer", "raw_digest", "raw_samples", "row", "row_self",
])
def test_iq2_model_confirmation_binding_defects_fail_closed(defect):
    source = iq2_model_receipt()
    if defect == "final_self":
        source["self_sha256"] = "0" * 64
    elif defect == "source":
        source["source_receipt_sha256"] = "0" * 64
        resign_iq2_model(source)
    elif defect == "producer":
        source["belief_measurements"][0]["extra"]["producer_sha256"] = "0" * 64
        resign_iq2_model(source)
    elif defect == "model":
        source["belief_measurements"][0]["extra"]["model_identity"]["sha256"] = "0" * 64
        resign_iq2_model(source)
    elif defect == "candidate":
        source["belief_measurements"][0]["extra"]["candidate_identity"][
            "binary_sha256"] = "0" * 64
        resign_iq2_model(source)
    elif defect == "anchor":
        source["belief_measurements"][0]["extra"]["anchor_identity"][
            "binary_sha256"] = "0" * 64
        resign_iq2_model(source)
    elif defect == "claim":
        source["belief_measurements"][0]["extra"][
            "resource_claim_receipt_sha256"] = "0" * 64
        resign_iq2_model(source)
    elif defect == "event":
        source["belief_measurements"][0]["extra"]["t2_event_sha256"] = "0" * 64
        resign_iq2_model(source)
    elif defect == "transfer":
        source["lanes"]["tg"]["t2_event"]["transfer_ratio_to"][0]["ratio"] = -0.4
        resign_iq2_model(source)
    elif defect == "raw_digest":
        source["belief_measurements"][0]["extra"]["raw_vector_sha256s"] = ["0" * 64]
        resign_iq2_model(source)
    elif defect == "raw_samples":
        source["lanes"]["tg"]["raw_vectors"][0]["blocks"][0]["invocations"][0][
            "samples"][0] = 99.0
        resign_iq2_model(source)
    elif defect == "row":
        source["belief_measurements"][0]["value"] = 999.0
        resign_iq2_model(source)
    else:
        source["belief_measurements"][0]["extra"]["self_sha256"] = "0" * 64
        resign_iq2_model(source)
    with pytest.raises(ct.ProjectionError):
        aux.native_rows(source)


def test_iq2_model_unfinalized_receipt_is_not_a_legacy_empty_vector():
    source = iq2_model_receipt()
    source.pop("belief_measurements")
    source.pop("self_sha256")
    with pytest.raises(ct.ProjectionError, match="requires finalized"):
        aux.native_rows(source)

    legacy = receipt(status="complete")
    legacy["schema"] = "epyc.inf37.iq2_fancy_simd_ab.v1"
    legacy.pop("belief_measurements")
    assert aux.native_rows(legacy) == ()


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


def test_profile_finalizer_rows_use_the_same_measurement_ladder():
    source = receipt()
    source["schema"] = "epyc.autokernel.profile_beliefs.v1"
    source["campaign_id"] = "profile-beliefs-20260811"
    source["belief_measurements"][0].update({
        "measurement_id": "c4_q4k_mul_mat_vec_q_device_ns_per_suite",
        "metric": "profiled_kernel_family_device_duration_ns_per_suite",
        "value": 74336.4,
        "unit": "ns",
        "reps": 5,
        "reps_basis": "scored:formal production-optimization profiler suites",
        "claim": "C4 Q4_K mul_mat_vec_q mean formal device time is 74336.4 ns",
        "extra": {"kernel_family": "mul_mat_vec_q", "promotion_authority": False},
    })
    row = aux.native_rows(
        source, receipt_locator="probe:profile-beliefs/c4-q4k.json",
        receipt_sha256="d" * 64, attestation_present=True)[0]
    projected = aux.project(row)
    assert projected.protocol_id == "epyc.autokernel.profile_beliefs.v1"
    assert projected.metric_direction == "lower_better"
    assert projected.extra["kernel_family"] == "mul_mat_vec_q"
    assert ct.grade(projected)[:2] == ("Witnessed", "Attested")


def test_p2_5j_rows_project_without_acquiring_placement_authority():
    source = p2_receipt()
    rows = aux.native_rows(
        source, receipt_locator="probe:p2-5j/receipt.json",
        receipt_sha256="8" * 64, attestation_present=True)
    assert len(rows) == 16
    tuples = [aux.project(row) for row in rows]
    assert {tup.metric_direction for tup in tuples} == {
        "higher_better", "lower_better"}
    assert all(tup.protocol_id == aux._P2_SCHEMA for tup in tuples)
    assert all(tup.extra["placement_selection_authority"] is False for tup in tuples)
    assert all(tup.extra["kernel_speedup_authority"] is False for tup in tuples)
    assert all(ct.grade(tup)[:2] == ("Witnessed", "Attested") for tup in tuples)


def test_p2_5j_authority_or_measurement_tamper_is_refused():
    authority = p2_receipt()
    authority["belief_measurements"][0]["extra"]["placement_selection_authority"] = True
    authority["belief_measurements"][0].pop("measurement_sha256")
    authority["belief_measurements"][0]["measurement_sha256"] = aux._canonical_sha256(
        authority["belief_measurements"][0])
    authority.pop("receipt_sha256")
    authority["receipt_sha256"] = aux._canonical_sha256(authority)
    with pytest.raises(ct.ProjectionError, match="identity or authority"):
        aux.native_rows(authority)

    value = p2_receipt()
    value["belief_measurements"][0]["value"] += 1.0
    value["belief_measurements"][0].pop("measurement_sha256")
    value["belief_measurements"][0]["measurement_sha256"] = aux._canonical_sha256(
        value["belief_measurements"][0])
    value.pop("receipt_sha256")
    value["receipt_sha256"] = aux._canonical_sha256(value)
    with pytest.raises(ct.ProjectionError, match="rederive"):
        aux.native_rows(value)


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


def test_arena_identity_distinguishes_attempts_with_one_logical_campaign_id():
    r3 = arena_receipt(checkpoint_hours=2.0, ended_at="2026-08-12T07:49:41Z")
    r4 = arena_receipt(checkpoint_hours=2.0, ended_at="2026-08-12T08:23:37Z")
    r4["artifacts"][0]["sha256"] = "c" * 64
    r4.pop("receipt_sha256")
    r4["receipt_sha256"] = aux._canonical_sha256(r4)

    r3_rows = tuple(aux.project(row) for row in aux.native_rows(r3))
    r4_rows = tuple(aux.project(row) for row in aux.native_rows(r4))
    assert {row.measurement_id for row in r3_rows}.isdisjoint(
        row.measurement_id for row in r4_rows)
    assert len({row.measurement_id for row in (*r3_rows, *r4_rows)}) == 4
    assert all(row.extra["arena_receipt_identity_sha256"] in {
        r3["receipt_sha256"], r4["receipt_sha256"]} for row in (*r3_rows, *r4_rows))


def test_arena_identity_refuses_a_tampered_self_digest():
    value = arena_receipt()
    value["source"]["checkpoint_hours"] = 8.0
    with pytest.raises(ct.ProjectionError, match="does not bind"):
        aux.native_rows(value)


def test_hip_rows_rederive_and_preserve_observation_only_identity():
    source = hip_receipt()
    rows = aux.native_rows(source, receipt_locator="campaign:r4/receipt.json",
                           receipt_sha256="d" * 64, attestation_present=True)
    projected = tuple(aux.project(row) for row in rows)
    assert len(projected) == 2
    assert all(row.extra["hip_receipt_identity_sha256"] == source["receipt_sha256"]
               for row in projected)
    assert all(row.date == "2026-08-12" for row in projected)
    assert all(row.extra["authority"] == "observation_only" for row in projected)
    assert all(ct.grade(row)[:2] == ("Witnessed", "Attested") for row in projected)


def test_hip_row_or_claim_tamper_is_refused():
    source = hip_receipt()
    source["belief_measurements"][0]["value"] = 0.5
    source.pop("receipt_sha256")
    source["receipt_sha256"] = aux._canonical_sha256(source)
    with pytest.raises(ct.ProjectionError, match="do not exactly rederive"):
        aux.native_rows(source)


def test_hip_decision_rows_rederive_task_local_rank_without_release_authority():
    source = hip_decision_receipt()
    projected = tuple(aux.project(row) for row in aux.native_rows(
        source, receipt_locator="campaign:r6/receipt.json",
        receipt_sha256="e" * 64, attestation_present=True))
    assert len(projected) == 2
    assert all(row.extra["hip_decision_receipt_identity_sha256"]
               == source["receipt_sha256"] for row in projected)
    assert all(row.protocol_id == aux._HIP_DECISION_SCHEMA for row in projected)
    assert all(ct.grade(row)[:2] == ("Witnessed", "Attested") for row in projected)


def test_hip_decision_sub_floor_or_release_authority_is_refused():
    source = hip_decision_receipt()
    source["timing"]["blocks"][0]["candidate_measured_duration_ns"] = 2_000_000.0
    source.pop("receipt_sha256")
    source["receipt_sha256"] = aux._canonical_sha256(source)
    with pytest.raises(ct.ProjectionError, match="sub-floor"):
        aux.native_rows(source)

    source = hip_decision_receipt()
    source["decision"]["release_or_promotion_authority"] = True
    source.pop("receipt_sha256")
    source["receipt_sha256"] = aux._canonical_sha256(source)
    with pytest.raises(ct.ProjectionError, match="no-release"):
        aux.native_rows(source)

    source = hip_receipt()
    source["measurement_windows"][0]["device_claim_released"]["released_at"] = None
    source["measurement_windows"][0].pop("receipt_sha256")
    source["measurement_windows"][0]["receipt_sha256"] = aux._canonical_sha256(
        source["measurement_windows"][0])
    source.pop("receipt_sha256")
    source["receipt_sha256"] = aux._canonical_sha256(source)
    with pytest.raises(ct.ProjectionError, match="released MI210 claim"):
        aux.native_rows(source)


def test_invalid_direction_is_rejected_by_shared_carrier():
    source = receipt()
    source["belief_measurements"][0]["metric_direction"] = "neutral"
    with pytest.raises(ct.ProjectionError, match="metric_direction"):
        aux.project(aux.native_rows(source)[0])
