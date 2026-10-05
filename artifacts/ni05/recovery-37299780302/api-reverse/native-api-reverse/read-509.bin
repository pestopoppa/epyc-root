from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import model_gate_report as report_mod  # noqa: E402


def test_build_report_blocks_on_underlying_fable5_gates(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
xmas_routing:
  mode: "off"
  winner_table_path: ""
  require_complete_table: false
""",
        encoding="utf-8",
    )
    table = tmp_path / "xmas_winner_table.yaml"
    table.write_text("placeholder: true\n", encoding="utf-8")
    ab_root = tmp_path / "xmas_live_ab"
    run = ab_root / "run1"
    run.mkdir(parents=True)
    (run / "summary.json").write_text(
        """
{
  "decision": {
    "status": "hold",
    "blockers": ["latency regression"]
  },
  "xmas_policy": "unknown_legacy",
  "score_delta_xmas_minus_baseline": -0.35,
  "latency_ratio_xmas_over_baseline": 16.18
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(report_mod, "validate_xmas_config", lambda path: [])
    monkeypatch.setattr(report_mod, "validate_xmas_table", lambda path, **kwargs: [])
    monkeypatch.setattr(
        report_mod,
        "xmas_quiet_window_report",
        lambda: {"ready": False, "blockers": ["active AutoPilot process(es): 123"]},
    )
    monkeypatch.setattr(
        report_mod,
        "ds_e1_clean_window_report",
        lambda: {
            "ready": False,
            "blockers": ["active AutoPilot process(es): 123 autopilot"],
        },
    )
    a9_manifest = tmp_path / "offline_reward_pairwise_expanded_gap_collection_manifest.json"
    monkeypatch.setattr(
        report_mod,
        "build_a9_collection_status",
        lambda path: {
            "ready": False,
            "status": "blocked",
            "manifest_path": str(a9_manifest),
            "manifest_schema_version": (
                "offline_reward_pairwise_collection_window.v1"
            ),
            "source_plan_decision": {"status": "expansion_plan_ready"},
            "batch_count": 9,
            "post_collection_step_count": 7,
            "autopilot_guard": {"refusal_exit_code": 75},
            "blockers": ["active AutoPilot process(es): 123 autopilot"],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        report_mod,
        "build_restart_readiness_report",
        lambda state, rows, **kwargs: {
            "restart_ready": False,
            "blockers": ["sequential verdict cutover readiness is blocked"],
            "archive_authority": {
                "journal_max_trial_id": 895,
                "state_trial_counter": 896,
            },
            "snapshot_replay": {
                "payload_journal_max_trial_id": 895,
            },
            "summary": {
                "seq_cutover_ready": False,
                "seq_trusted_vector_trials": 62,
                "seq_min_trusted_vector_trials": 120,
                "seq_trusted_vector_trials_remaining": 58,
                "seq_shadow_rows": 10,
                "seq_min_shadow_rows": 30,
                "seq_shadow_rows_remaining": 20,
                "snapshot_restart_readiness": "tail_fold_ready",
                "archive_source_surface_ok": True,
                "archive_source_surface_count": 6,
                "archive_source_surface_failed_count": 0,
                "w6_audit_cutover_ready": False,
                "w6_audited_trial_count": 34,
                "w6_min_audited_trials": 30,
                "w6_audited_trial_count_remaining": 0,
                "w6_alarm_clearance_clean_trials_required": 4,
                "w6_raw_audited_trial_count": 40,
                "w6_trusted_audited_trial_count": 39,
                "w6_untrusted_audited_trial_count": 1,
                "w6_untrusted_audited_trial_ids": [889],
                "w6_gaming_alarm": True,
                "w6_potential_overfit_divergences": 4,
                "cutover_horizon_clean_trials_remaining": 58,
                "cutover_horizon_blocker": "seq_trusted_vectors",
                "cutover_horizon_components": {
                    "seq_trusted_vectors": 58,
                    "seq_shadow_rows": 20,
                    "w6_audited_trials": 0,
                    "w6_alarm_clearance": 4,
                },
                "baseline_seed_append_ready": True,
                "baseline_seed_append_required": True,
                "baseline_seed_append_expect_trial_counter": 896,
                "baseline_seed_append_expect_journal_max_trial_id": 895,
            },
        },
    )

    report = report_mod.build_model_gate_report(
        state={"trial_counter": 896},
        journal_rows=[],
        phase_report={
            "ok": True,
            "status": "active",
            "trial_id": 896,
            "phase": "dispatch_action",
            "action_type": "deep_eval",
            "heartbeat_age_s": 4.0,
            "pid": 123,
            "pid_alive": True,
        },
        ds_e1_packet={
            "ready_for_profile_decision": False,
            "generated_at": "2026-06-20T00:00:00Z",
            "blockers": ["kv_size_measurements: missing"],
            "sections": [
                {
                    "key": "kv_size_measurements",
                    "status": "missing",
                    "details": {
                        "required_measurements": {
                            "frontdoor": [2048, 8192, 32768],
                            "worker_general": [2048, 8192],
                        },
                        "expected_csv_columns": [
                            "role",
                            "context_length",
                            "server_kv_size_mb",
                        ],
                        "searched_globs": ["orchestration/reports/ds_e1*kv*"],
                    },
                },
                {
                    "key": "ri10_canary",
                    "status": "insufficient_data",
                    "details": {
                        "telemetry_collection_blocker": (
                            "canary_role_sample_count_insufficient"
                        ),
                        "telemetry_collection_reason": (
                            "only 20 current high-risk row(s) matched "
                            "configured canary_roles; gate requires 50"
                        ),
                        "canary_role_sample_deficit_since_telemetry_health_start": 30,
                        "canary_arm_volume_deficit_since_telemetry_health_start": 30,
                        "canary_arm_balance_deficits_since_telemetry_health_start": {
                            "enforce_high_risk": 9,
                            "shadow_high_risk": 0,
                        },
                        "report_summary": {
                            "high_risk_by_role_since_telemetry_health_start": {
                                "frontdoor": 2,
                                "worker_general": 17,
                                "worker_vision": 1,
                            },
                            "canary_role_high_risk_by_role_since_telemetry_health_start": {
                                "frontdoor": 2,
                                "worker_general": 17,
                                "worker_vision": 1,
                            },
                            "canary_arm_counts_since_telemetry_health_start": {
                                "enforce_high_risk": 1,
                                "shadow_high_risk": 19,
                            },
                            "canary_arm_counts_by_role_since_telemetry_health_start": {
                                "frontdoor": {
                                    "enforce_high_risk": 0,
                                    "shadow_high_risk": 2,
                                },
                                "worker_general": {
                                    "enforce_high_risk": 1,
                                    "shadow_high_risk": 16,
                                },
                                "worker_vision": {
                                    "enforce_high_risk": 0,
                                    "shadow_high_risk": 1,
                                },
                            },
                        },
                    },
                }
            ],
        },
        config_path=config,
        xmas_table_path=table,
        xmas_ab_root=ab_root,
        a9_collection_manifest=a9_manifest,
        a9_audit_target_ranker_summary_path=None,
        a9_audit_target_direction_audit_path=None,
        include_tool_use_activation=False,
    )

    assert report["ready"] is False
    assert report["summary"]["ready"] is False
    assert report["summary"]["blocker_count"] == 7
    assert report["summary"]["blocked_sections"] == [
        "w4_w6_restart_cutover",
        "ds_e1_dynamic_stack",
        "a9_pairwise_collection",
        "xmas_production_path",
    ]
    assert report["summary"]["section_statuses"]["phase_health"] == "ready"
    assert report["summary"]["section_statuses"]["w4_w6_restart_cutover"] == "blocked"
    assert report["summary"]["section_statuses"]["a9_pairwise_collection"] == "blocked"
    assert report["summary"]["next_action_keys"] == [
        "append_baseline_seed_event",
        "continue_w4_w6_accrual",
        "run_ds_e1_kv_measurements",
        "collect_ri10_canary_arm_telemetry",
        "run_xmas_constrained_policy_ab",
        "run_a9_pairwise_collection_window",
    ]
    assert report["summary"]["active_next_action_keys"] == [
        "continue_w4_w6_accrual",
        "collect_ri10_canary_arm_telemetry",
    ]
    assert report["summary"]["blocked_next_action_keys"] == [
        "append_baseline_seed_event",
        "run_ds_e1_kv_measurements",
        "run_xmas_constrained_policy_ab",
        "run_a9_pairwise_collection_window",
    ]
    assert report["summary"]["restart_ready"] is False
    assert report["summary"]["phase_trial_id"] == 896
    assert report["summary"]["ds_e1_ready_for_profile_decision"] is False
    assert report["summary"]["ds_e1_clean_window_ready"] is False
    assert report["summary"]["ds_e1_clean_window_blockers"] == [
        "active AutoPilot process(es): 123 autopilot"
    ]
    assert report["summary"]["a9_collection_status"] == "blocked"
    assert report["summary"]["a9_collection_ready"] is False
    assert report["summary"]["a9_collection_batch_count"] == 9
    assert report["summary"]["a9_collection_blockers"] == [
        "active AutoPilot process(es): 123 autopilot"
    ]
    assert report["summary"]["xmas_mode"] == "off"
    assert report["summary"]["xmas_latest_ab_policy"] == "unknown_legacy"
    assert report["summary"]["xmas_latest_ab_decision_status"] == "hold"
    assert "w4_w6_restart_cutover: sequential verdict cutover readiness is blocked" in report[
        "blockers"
    ]
    assert "ds_e1_dynamic_stack: kv_size_measurements: missing" in report["blockers"]
    assert "a9_pairwise_collection: active AutoPilot process(es): 123 autopilot" in report[
        "blockers"
    ]
    assert "xmas_production_path: xmas_routing.mode is off; enforce remains default-off" in report[
        "blockers"
    ]
    assert (
        "xmas_production_path: latest X-MAS held-out A/B policy is "
        "unknown_legacy; required incumbent_constrained_cheapfirst_v2"
    ) in report["blockers"]
    assert "xmas_production_path: latest X-MAS held-out A/B decision is hold" in report[
        "blockers"
    ]
    xmas = [section for section in report["sections"] if section["key"] == "xmas_production_path"][0]
    assert xmas["details"]["latest_ab_decision_status"] == "hold"
    assert xmas["details"]["latest_ab_policy"] == "unknown_legacy"
    assert xmas["details"]["required_ab_policy"] == (
        "incumbent_constrained_cheapfirst_v2"
    )
    assert xmas["details"]["latest_ab_latency_ratio"] == 16.18
    assert xmas["details"]["quiet_window_ready"] is False
    assert xmas["details"]["quiet_window_blockers"] == [
        "active AutoPilot process(es): 123"
    ]
    assert report["sections"][0]["key"] == "phase_health"
    assert report["sections"][0]["status"] == "ready"
    restart = [
        section for section in report["sections"] if section["key"] == "w4_w6_restart_cutover"
    ][0]
    assert restart["details"]["durable_journal_max_trial_id"] == 895
    assert restart["details"]["state_trial_counter"] == 896
    assert restart["details"]["seq_trusted_vector_trials_remaining"] == 58
    assert restart["details"]["seq_shadow_rows_remaining"] == 20
    assert restart["details"]["archive_source_surface_ok"] is True
    assert restart["details"]["archive_source_surface_count"] == 6
    assert restart["details"]["archive_source_surface_failed_count"] == 0
    assert restart["details"]["w6_audited_trial_count_remaining"] == 0
    assert restart["details"]["w6_alarm_clearance_clean_trials_required"] == 4
    assert restart["details"]["snapshot_restart_readiness"] == "tail_fold_ready"
    assert restart["details"]["snapshot_payload_journal_max_trial_id"] == 895
    assert restart["details"]["baseline_seed_append_required"] is True
    assert restart["details"]["baseline_seed_append_expect_trial_counter"] == 896
    assert restart["details"]["baseline_seed_append_expect_journal_max_trial_id"] == 895
    assert restart["details"]["w6_untrusted_audited_trial_count"] == 1
    assert restart["details"]["w6_untrusted_audited_trial_ids"] == [889]
    assert restart["details"]["cutover_horizon_clean_trials_remaining"] == 58
    assert restart["details"]["cutover_horizon_blocker"] == "seq_trusted_vectors"
    assert restart["details"]["cutover_horizon_components"] == {
        "seq_trusted_vectors": 58,
        "seq_shadow_rows": 20,
        "w6_audited_trials": 0,
        "w6_alarm_clearance": 4,
    }
    assert [action["key"] for action in report["next_actions"]] == [
        "append_baseline_seed_event",
        "continue_w4_w6_accrual",
        "run_ds_e1_kv_measurements",
        "collect_ri10_canary_arm_telemetry",
        "run_xmas_constrained_policy_ab",
        "run_a9_pairwise_collection_window",
    ]
    seed_action = report["next_actions"][0]
    assert seed_action["status"] == "blocked"
    assert seed_action["blocked_by"] == [
        "active AutoPilot process; seed tool refuses live append"
    ]
    assert seed_action["evidence"] == {
        "baseline_seed_append_ready": True,
        "baseline_seed_append_required": True,
        "expect_trial_counter": 896,
        "expect_journal_max_trial_id": 895,
    }
    assert "baseline_authority_seed.py --append" in seed_action["command"]
    assert "--expect-trial-counter 896" in seed_action["command"]
    assert "--expect-journal-max-trial-id 895" in seed_action["command"]
    assert seed_action["follow_up"] == (
        "cd /mnt/raid0/llm/epyc-orchestrator && "
        "uv run python scripts/autopilot/restart_readiness_report.py "
        "--json --strict --require-seq-cutover --require-w6-audit --require-current-code"
    )
    assert report["next_actions"][1]["status"] == "active"
    assert report["next_actions"][1]["evidence"]["trusted_vectors_required"] == 120
    assert report["next_actions"][1]["evidence"]["trusted_vectors_remaining"] == 58
    assert report["next_actions"][1]["evidence"]["seq_shadow_rows_required"] == 30
    assert report["next_actions"][1]["evidence"]["seq_shadow_rows_remaining"] == 20
    assert report["next_actions"][1]["evidence"]["w6_audited_rows_required"] == 30
    assert report["next_actions"][1]["evidence"]["w6_audited_rows_remaining"] == 0
    assert (
        report["next_actions"][1]["evidence"][
            "w6_alarm_clearance_clean_trials_required"
        ]
        == 4
    )
    assert (
        report["next_actions"][1]["evidence"][
            "cutover_horizon_clean_trials_remaining"
        ]
        == 58
    )
    assert (
        report["next_actions"][1]["evidence"]["cutover_horizon_blocker"]
        == "seq_trusted_vectors"
    )
    assert "restart_readiness_report.py" in report["next_actions"][1]["command"]
    assert "--require-seq-cutover --require-w6-audit --require-current-code" in report[
        "next_actions"
    ][1]["command"]
    assert report["next_actions"][1]["follow_up"] == (
        "uv run python scripts/autopilot/model_gate_report.py --json --strict"
    )
    ds_e1 = [
        section for section in report["sections"] if section["key"] == "ds_e1_dynamic_stack"
    ][0]
    assert ds_e1["details"]["kv_required_measurements"]["frontdoor"] == [
        2048,
        8192,
        32768,
    ]
    assert ds_e1["details"]["kv_expected_csv_columns"] == [
        "role",
        "context_length",
        "server_kv_size_mb",
    ]
    assert "ds_e1_kv_measurements.sh --execute" in report["next_actions"][2]["command"]
    assert report["next_actions"][2]["status"] == "blocked"
    assert "$(date -u +%Y%m%dT%H%M%SZ)" in report["next_actions"][2]["follow_up"]
    assert "ds_e1_evidence_packet_20260620.md" not in report["next_actions"][2]["follow_up"]
    assert report["next_actions"][3]["command"] == (
        "uv run python scripts/analysis/ri10_canary_sample_report.py"
    )
    assert report["next_actions"][3]["evidence"] == {
        "telemetry_collection_blocker": "canary_role_sample_count_insufficient",
        "telemetry_collection_reason": (
            "only 20 current high-risk row(s) matched configured canary_roles; "
            "gate requires 50"
        ),
        "canary_role_sample_deficit": 30,
        "canary_arm_volume_deficit": 30,
        "canary_arm_balance_deficits": {
            "enforce_high_risk": 9,
            "shadow_high_risk": 0,
        },
        "high_risk_by_role_current": {
            "frontdoor": 2,
            "worker_general": 17,
            "worker_vision": 1,
        },
        "canary_role_high_risk_by_role_current": {
            "frontdoor": 2,
            "worker_general": 17,
            "worker_vision": 1,
        },
        "canary_arm_counts_current": {
            "enforce_high_risk": 1,
            "shadow_high_risk": 19,
        },
        "canary_arm_counts_by_role_current": {
            "frontdoor": {
                "enforce_high_risk": 0,
                "shadow_high_risk": 2,
            },
            "worker_general": {
                "enforce_high_risk": 1,
                "shadow_high_risk": 16,
            },
            "worker_vision": {
                "enforce_high_risk": 0,
                "shadow_high_risk": 1,
            },
        },
    }
    xmas_action = report["next_actions"][4]
    assert xmas_action["status"] == "blocked"
    assert xmas_action["blocked_by"] == ["active AutoPilot process(es): 123"]
    assert "latest X-MAS held-out A/B decision is hold" in xmas_action["evidence_blockers"]
    assert "xmas_live_ab.py" in xmas_action["command"]
    assert "<heldout_prompts.jsonl>" not in xmas_action["command"]
    assert xmas_action["prompt_manifest"] == (
        "benchmarks/results/runs/xmas_live_ab/20260618-heldout-resilient/prompts.jsonl"
    )
    assert xmas_action["required_policy"] == "incumbent_constrained_cheapfirst_v2"
    assert f"--prompts {xmas_action['prompt_manifest']}" in xmas_action["command"]
    assert "$(date -u +%Y%m%dT%H%M%SZ)-constrained-policy" in xmas_action["command"]
    a9_action = report["next_actions"][5]
    assert a9_action["status"] == "blocked"
    assert a9_action["blocked_by"] == [
        "active AutoPilot process(es): 123 autopilot"
    ]
    assert a9_action["manifest"] == str(a9_manifest)
    assert a9_action["batch_count"] == 9
    assert a9_action["post_collection_step_count"] == 7
    assert a9_action["source_plan_decision"] == {"status": "expansion_plan_ready"}
    assert "collect_offline_reward_pairwise_expanded_gap.sh" in a9_action["command"]
    assert "offline_reward_pairwise_collection_status.py" in a9_action["follow_up"]


def test_tool_use_activation_section_surfaces_missing_sentinel_env() -> None:
    section = report_mod.tool_use_activation_section(
        phase_report={"pid": 123},
        journal_rows=[
            {
                "trial_id": 1106,
                "eval_details": {
                    "total_tool_calls": 0,
                    "mean_tools_used": 0.0,
                    "tool_use_rate": 0.0,
                },
            }
        ],
        autopilot_env={},
        api_attest={
            "pid": 456,
            "flags": {
                "tools": True,
                "repl": True,
                "structured_tool_output": True,
            },
        },
        api_env={},
    )

    assert section.status == "attention"
    assert section.blockers == []
    assert section.details["activation_gaps"] == [
        "autopilot_env_missing_AUTOPILOT_TOOL_SENTINELS",
        "api_env_missing_AUTOPILOT_TOOL_SENTINELS",
        "latest_eval_total_tool_calls_zero",
    ]
    assert section.details["latest_tool_metrics"]["trial_id"] == 1106
    assert section.details["recent_tool_metrics"]["nonzero_rows"] == 0


def test_tool_use_activation_accepts_recent_nonzero_tool_telemetry() -> None:
    section = report_mod.tool_use_activation_section(
        phase_report={"pid": 123},
        journal_rows=[
            {
                "trial_id": 1115,
                "eval_details": {
                    "total_tool_calls": 8,
                    "mean_tools_used": 0.08,
                    "tool_use_rate": 0.074,
                    "tool_name_counts": {"get_eval_secret": 8},
                },
            },
            {
                "trial_id": 1116,
                "eval_details": {
                    "total_tool_calls": 0,
                    "mean_tools_used": 0.0,
                    "tool_use_rate": 0.0,
                    "tool_name_counts": {},
                },
            },
        ],
        autopilot_env={report_mod.TOOL_SENTINEL_ENV: "1"},
        api_attest={
            "pid": 456,
            "flags": {
                "tools": True,
                "repl": True,
                "structured_tool_output": True,
            },
        },
        api_env={report_mod.TOOL_SENTINEL_ENV: "1"},
    )

    assert section.status == "ready"
    assert section.details["activation_gaps"] == []
    assert section.details["latest_tool_metrics"]["trial_id"] == 1116
    assert section.details["latest_tool_metrics"]["total_tool_calls"] == 0
    assert section.details["recent_tool_metrics"]["nonzero_rows"] == 1
    assert (
        section.details["recent_tool_metrics"]["latest_nonzero_tool_metrics"][
            "trial_id"
        ]
        == 1115
    )


def test_eval_task_coverage_section_is_advisory_attention() -> None:
    section = report_mod.eval_task_coverage_section(
        {
            "coverage": {
                "status": "low_coverage",
                "question_result_rows": 200,
                "distinct_journal_question_keys": 20,
                "pool_stable_question_keys": 1000,
                "distinct_vs_pool_stable_upper_bound_pct": 2.0,
                "matched_pool_stable_pct": 1.5,
                "repeat_factor": 10.0,
                "interpretation": "planner coverage is narrow",
            },
            "journal": {
                "eval_bearing_trials": 5,
                "trial_id_min": 1,
                "trial_id_max": 10,
            },
            "questions": {
                "tier_coverage": {
                    "1": {
                        "eval_bearing_trials": 4,
                        "question_result_rows": 180,
                        "distinct_journal_question_keys": 18,
                        "pool_question_keys": 900,
                        "distinct_vs_pool_pct": 2.0,
                    }
                },
                "suite_distinct_question_counts": {
                    "sentinel_tool_use": 1,
                    "agentic": 2,
                    "coder": 5,
                },
            },
            "pool": {"path": "question_pool.jsonl"},
            "recommendation": {"do_not_change_mid_w8": True},
        }
    )

    assert section.key == "eval_task_coverage"
    assert section.status == "attention"
    assert section.blockers == []
    assert "20/1000" in section.summary
    assert section.details["coverage_status"] == "low_coverage"
    assert section.details["least_covered_non_sentinel_suites"] == [
        {"suite": "agentic", "distinct_qids": 2},
        {"suite": "coder", "distinct_qids": 5},
    ]


def test_p0_2_amendment_bundle_section_surfaces_ready_inputs() -> None:
    restart = report_mod.GateSection(
        key="w4_w6_restart_cutover",
        status="ready",
        summary="ready",
        blockers=[],
        details={
            "w8_latest_combined_E": 24.0,
            "w8_latest_required_E": 20.0,
            "w8_latest_seq_state": "confirmed",
            "w8_latest_fresh_eval": True,
            "w8_promotion_status": "confirmed_waiting_fresh_eval",
        },
    )
    ds_e1 = report_mod.GateSection(
        key="ds_e1_dynamic_stack",
        status="ready",
        summary="ready",
        blockers=[],
        details={"section_statuses": {"ri10_canary": "ready"}},
    )
    eval_coverage = report_mod.GateSection(
        key="eval_task_coverage",
        status="ready",
        summary="ok",
        blockers=[],
        details={
            "coverage_status": "ok",
            "distinct_vs_pool_stable_upper_bound_pct": 18.0,
            "repeat_factor": 1.5,
            "tier_coverage": {
                "3": {
                    "eval_bearing_trials": 2,
                    "question_result_rows": 160,
                    "distinct_journal_question_keys": 120,
                    "pool_question_keys": 300,
                    "distinct_vs_pool_pct": 40.0,
                }
            },
        },
    )

    section = report_mod.p0_2_amendment_bundle_section(
        restart=restart,
        ds_e1=ds_e1,
        journal_rows=[
            {
                "trial_id": 1315,
                "oracle_adequacy": {
                    "control_attestation": {
                        "status": "passed",
                        "enabled": True,
                        "eligible_for_evidence": False,
                        "controls_seen": {"known_good": 1, "known_bad": 1},
                        "suites": ["humaneval"],
                    }
                },
            }
        ],
        eval_coverage=eval_coverage,
    )

    assert section.key == "p0_2_amendment_bundle_inputs"
    assert section.status == "ready"
    assert section.blockers == []
    assert section.details["operator_signing_required"] is True
    assert section.details["rate_axis_status"] == "ready"
    assert section.details["control_attestation_status"] == "passed"
    assert section.details["eval_discriminability_status"] == "ok"
    assert section.details["t3_hard_lane_status"] == "visible"
    assert section.details["ri10_canary_status"] == "ready"
    assert section.details["evidence_gaps"] == []


def test_p0_2_amendment_bundle_section_is_advisory_attention() -> None:
    restart = report_mod.GateSection(
        key="w4_w6_restart_cutover",
        status="blocked",
        summary="blocked",
        blockers=["rate axis below threshold"],
        details={
            "w8_latest_combined_E": 1.1,
            "w8_latest_required_E": 20.0,
            "w8_latest_seq_state": "seq_accumulating",
            "w8_latest_fresh_eval": False,
        },
    )
    ds_e1 = report_mod.GateSection(
        key="ds_e1_dynamic_stack",
        status="blocked",
        summary="blocked",
        blockers=["ri10_canary: insufficient"],
        details={
            "section_statuses": {"ri10_canary": "insufficient_data"},
            "ri10_telemetry_collection_blocker": "canary_arm_volume_insufficient",
        },
    )
    eval_coverage = report_mod.GateSection(
        key="eval_task_coverage",
        status="attention",
        summary="low",
        blockers=[],
        details={
            "coverage_status": "low_coverage",
            "tier_coverage": {"3": {"eval_bearing_trials": 0}},
        },
    )

    section = report_mod.p0_2_amendment_bundle_section(
        restart=restart,
        ds_e1=ds_e1,
        journal_rows=[],
        eval_coverage=eval_coverage,
    )

    assert section.status == "attention"
    assert section.blockers == []
    assert section.details["rate_axis_status"] == "below_required"
    assert section.details["control_attestation_status"] == "missing"
    assert section.details["eval_discriminability_status"] == "low_coverage"
    assert section.details["t3_hard_lane_status"] == "missing"
    assert section.details["ri10_canary_status"] == "insufficient_data"
    assert section.details["evidence_gaps"] == [
        "rate_axis_below_required",
        "control_attestation_missing",
        "eval_discriminability_low_coverage",
        "t3_hard_lane_coverage_missing",
        "ri10_canary_insufficient_data",
    ]


def test_eval_task_coverage_does_not_block_fable_readiness(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
xmas_routing:
  mode: "enforce"
  winner_table_path: "orchestration/xmas_winner_table.yaml"
  require_complete_table: true
""",
        encoding="utf-8",
    )
    table = tmp_path / "xmas_winner_table.yaml"
    table.write_text("placeholder: true\n", encoding="utf-8")
    ab_root = tmp_path / "xmas_live_ab"
    run = ab_root / "run1"
    run.mkdir(parents=True)
    (run / "summary.json").write_text(
        """
{
  "decision": {"status": "promote_candidate", "blockers": []},
  "xmas_policy": "incumbent_constrained_cheapfirst_v2"
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(report_mod, "validate_xmas_config", lambda path: [])
    monkeypatch.setattr(report_mod, "validate_xmas_table", lambda path, **kwargs: [])
    monkeypatch.setattr(
        report_mod,
        "build_restart_readiness_report",
        lambda state, rows, **kwargs: {
            "restart_ready": True,
            "blockers": [],
            "archive_authority": {},
            "snapshot_replay": {},
            "summary": {"w8_promotion_status": "finalized"},
        },
    )
    monkeypatch.setattr(
        report_mod,
        "build_w8_trajectory_report",
        lambda rows: {
            "status": "ok",
            "ok": True,
            "replay_concentration": {"warning": False},
        },
    )
    monkeypatch.setattr(
        report_mod,
        "build_a9_collection_status",
        lambda path: {"ready": True, "status": "ready", "blockers": []},
    )
    # Hermetic: a unit test must not read live process/port state. The DS-E1
    # clean-window and X-MAS quiet-window probes shell out to pgrep and connect
    # to a local port, so a live AutoPilot or llama-server would flip readiness.
    # Pin the process/port seams to an idle host.
    monkeypatch.setattr(report_mod, "_pgrep", lambda pattern: [])
    monkeypatch.setattr(report_mod, "_pgrep_exact", lambda name: [])
    monkeypatch.setattr(report_mod, "_tcp_port_accepting", lambda port, **kwargs: False)

    report = report_mod.build_model_gate_report(
        state={},
        journal_rows=[],
        phase_report={
            "ok": True,
            "status": "active",
            "pid": 123,
            "pid_alive": True,
            "trial_id": 1,
        },
        ds_e1_packet={"ready_for_profile_decision": True, "blockers": []},
        config_path=config,
        xmas_table_path=table,
        xmas_ab_root=ab_root,
        eval_task_coverage_report={
            "coverage": {
                "status": "low_coverage",
                "distinct_journal_question_keys": 20,
                "pool_stable_question_keys": 1000,
                "distinct_vs_pool_stable_upper_bound_pct": 2.0,
                "repeat_factor": 10.0,
            },
            "questions": {"suite_distinct_question_counts": {}},
        },
        include_tool_use_activation=False,
    )

    assert report["ready"] is True
    assert report["blockers"] == []
    assert report["summary"]["section_statuses"]["eval_task_coverage"] == "attention"
    assert (
        report["summary"]["section_statuses"]["p0_2_amendment_bundle_inputs"]
        == "attention"
    )
    assert report["summary"]["eval_task_coverage_status"] == "low_coverage"
    assert report["summary"]["p0_2_amendment_bundle_status"] == "attention"
    assert report["summary"]["p0_2_eval_discriminability_status"] == "low_coverage"


def test_phase_recovery_next_action_uses_current_code_preflight() -> None:
    phase = report_mod.GateSection(
        key="phase_health",
        status="blocked",
        summary="AutoPilot phase heartbeat is code_stale.",
        blockers=[
            "autopilot process predates runtime source changes: autopilot.py",
        ],
        details={
            "status": "code_stale",
            "phase": "dispatch_action",
            "pid": 1039446,
            "code_stale": True,
        },
    )

    actions = report_mod.build_next_actions([phase])

    assert actions == [
        {
            "key": "recover_autopilot_phase",
            "priority": "P0",
            "status": "blocked",
            "reason": (
                "AutoPilot phase health is not ready; do not trust "
                "evidence accrual until recovered."
            ),
            "blocked_by": [
                "autopilot process predates runtime source changes: autopilot.py",
            ],
            # Derived from the source's own constant: restating this literal is what let
            # the 2026-08-04 launcher rename ship a recovery command pointing at a
            # nonexistent file, in BOTH the source and the test that was meant to catch it.
            "command": (
                f"uv run python {report_mod.AUTHORITY_DAEMON_SCRIPT} --preflight"
            ),
            "follow_up": (
                "Use the preflight/advisor output as the recovery authority; "
                "if it reports wait_for_boundary, do not restart until the "
                "active trial reaches a safe boundary."
            ),
        }
    ]


def test_tool_use_next_action_requires_controlled_restart() -> None:
    phase = report_mod.GateSection(
        key="phase_health",
        status="ready",
        summary="active",
        blockers=[],
        details={"status": "active"},
    )
    tool_use = report_mod.GateSection(
        key="tool_use_activation",
        status="attention",
        summary="not active",
        blockers=[],
        details={
            "activation_gaps": [
                "autopilot_env_missing_AUTOPILOT_TOOL_SENTINELS",
                "api_env_missing_AUTOPILOT_TOOL_SENTINELS",
            ],
            "autopilot_tool_sentinels_enabled": False,
            "api_tool_sentinels_enabled": False,
            "api_tools_enabled": True,
            "api_repl_enabled": True,
            "latest_tool_metrics": {"trial_id": 1106, "total_tool_calls": 0},
        },
    )

    actions = report_mod.build_next_actions([phase, tool_use])

    assert actions == [
        {
            "key": "activate_tool_use_sentinel_lane",
            "priority": "P0",
            "status": "blocked",
            "reason": (
                "StrategyStore already exposes tool-use hints to the planner; "
                "the remaining gap is activating the API and AutoPilot "
                "tool-sentinel telemetry lane so tool use is measured."
            ),
            "requires": (
                "coordinated API reload plus AutoPilot restart at a trial "
                "boundary; this changes the active eval mix"
            ),
            "blocked_by": [
                "active AutoPilot process; wait for a controlled trial boundary"
            ],
            "evidence": {
                "activation_gaps": [
                    "autopilot_env_missing_AUTOPILOT_TOOL_SENTINELS",
                    "api_env_missing_AUTOPILOT_TOOL_SENTINELS",
                ],
                "autopilot_tool_sentinels_enabled": False,
                "api_tool_sentinels_enabled": False,
                "api_tools_enabled": True,
                "api_repl_enabled": True,
                "latest_tool_metrics": {
                    "trial_id": 1106,
                    "total_tool_calls": 0,
                },
                "recent_tool_metrics": None,
            },
            "command": (
                "At a controlled trial boundary, reload the orchestrator API "
                "with AUTOPILOT_TOOL_SENTINELS=1, restart AutoPilot with "
                f"uv run python {report_mod.AUTHORITY_DAEMON_SCRIPT} "
                "--max-trials 3000, "
                "then run AUTOPILOT_TOOL_SENTINELS=1 uv run python "
                "scripts/autopilot/gate3_tool_telemetry.py"
            ),
            "follow_up": report_mod.STRICT_MODEL_GATE_COMMAND,
        }
    ]


def test_tool_use_next_action_waits_for_journal_when_lane_active() -> None:
    phase = report_mod.GateSection(
        key="phase_health",
        status="ready",
        summary="active",
        blockers=[],
        details={"status": "active"},
    )
    tool_use = report_mod.GateSection(
        key="tool_use_activation",
        status="attention",
        summary="waiting for first journaled tool telemetry",
        blockers=[],
        details={
            "activation_gaps": ["latest_eval_total_tool_calls_zero"],
            "autopilot_tool_sentinels_enabled": True,
            "api_tool_sentinels_enabled": True,
            "api_tools_enabled": True,
            "api_repl_enabled": True,
            "latest_tool_metrics": {"trial_id": 1107, "total_tool_calls": 0},
            "recent_tool_metrics": None,
        },
    )
    ds_e1 = report_mod.GateSection(
        key="ds_e1_dynamic_stack",
        status="attention",
        summary="blocked",
        blockers=["kv missing"],
        details={},
    )

    actions = report_mod.build_next_actions([phase, tool_use, ds_e1])

    tool_action = actions[0]
    assert tool_action["key"] == "collect_tool_use_sentinel_journal_evidence"
    assert tool_action["status"] == "active"
    assert tool_action["blocked_by"] == []
    assert "sentinel-enabled AutoPilot eval finish" in tool_action["command"]
    assert actions[1]["key"] == "run_ds_e1_kv_measurements"


def test_phase_section_surfaces_eval_progress() -> None:
    section = report_mod.phase_section(
        {
            "ok": True,
            "status": "active",
            "trial_id": 902,
            "phase": "dispatch_action",
            "action_type": "deep_eval",
            "heartbeat_age_s": 4.0,
            "pid": 123,
            "pid_alive": True,
            "process_started_at_s": 1783021658.69,
            "require_current_code": True,
            "code_stale": True,
            "code_stale_paths": [{"path": "scripts/autopilot/autopilot.py"}],
            "eval_label": "T2",
            "eval_completed_questions": 200,
            "eval_total_questions": 500,
            "eval_correct_questions": 144,
            "eval_correct_pct": 72.0,
            "eval_concurrency": 1,
            "planner_hints_enabled": True,
            "seq_verdict_enabled": True,
            "w6_audit_accrual_enabled": True,
            "w6_audit_shadow_only": True,
            "w6_audit_n": "10",
            "w6_audit_every_n_trials": "1",
            "autopilot_planner_timeout": "600",
        }
    )

    assert section.status == "ready"
    assert "T2 200/500" in section.summary
    assert section.details["eval_completed_questions"] == 200
    assert section.details["eval_correct_pct"] == 72.0
    assert section.details["process_started_at_s"] == 1783021658.69
    assert section.details["require_current_code"] is True
    assert section.details["code_stale"] is True
    assert section.details["code_stale_paths"] == [
        {"path": "scripts/autopilot/autopilot.py"}
    ]
    assert section.details["planner_hints_enabled"] is True
    assert section.details["seq_verdict_enabled"] is True
    assert section.details["w6_audit_accrual_enabled"] is True
    assert section.details["w6_audit_n"] == "10"


def test_xmas_required_policy_hold_points_to_regression_diagnosis(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
xmas_routing:
  mode: "off"
  winner_table_path: "orchestration/xmas_winner_table.yaml"
  require_complete_table: true
""",
        encoding="utf-8",
    )
    table = tmp_path / "xmas_winner_table.yaml"
    table.write_text("placeholder: true\n", encoding="utf-8")
    ab_root = tmp_path / "xmas_live_ab"
    run = ab_root / "20260621T112005Z-constrained-policy"
    run.mkdir(parents=True)
    (run / "results.jsonl").write_text("{}\n", encoding="utf-8")
    (run / "summary.json").write_text(
        """
{
  "decision": {
    "status": "hold",
    "blockers": ["overall score delta -0.250 < required 0.050"]
  },
  "xmas_policy": "incumbent_constrained_cheapfirst_v2",
  "score_delta_xmas_minus_baseline": -0.25,
  "latency_ratio_xmas_over_baseline": 0.714
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(report_mod, "validate_xmas_config", lambda path: [])
    monkeypatch.setattr(
        report_mod, "validate_xmas_table", lambda path, **kwargs: []
    )

    section = report_mod.xmas_section(
        config_path=config,
        candidate_table_path=table,
        ab_root=ab_root,
        quiet_window={"ready": True, "blockers": []},
    )
    actions = report_mod.build_next_actions([section])

    assert section.status == "blocked"
    assert "latest X-MAS held-out A/B decision is hold" in section.blockers
    assert [action["key"] for action in actions] == [
        "diagnose_xmas_policy_regressions"
    ]
    action = actions[0]
    assert action["status"] == "ready"
    assert action["latest_ab_decision_status"] == "hold"
    assert action["latest_ab_score_delta"] == -0.25
    assert action["latest_ab_latency_ratio"] == 0.714
    assert action["latest_ab_results_path"] == str(run / "results.jsonl")
    assert "--summarize-results" in action["command"]
    assert str(run / "results.jsonl") in action["command"]


def test_ds_e1_section_surfaces_clean_window_blockers() -> None:
    section = report_mod.ds_e1_section(
        {
            "ready_for_profile_decision": False,
            "generated_at": "2026-06-20T00:00:00Z",
            "blockers": ["kv_size_measurements: missing"],
            "sections": [{"key": "kv_size_measurements", "status": "missing"}],
        },
        clean_window={
            "ready": False,
            "blockers": ["active AutoPilot process(es): 123 autopilot"],
        },
    )

    assert section.status == "blocked"
    assert section.blockers == ["kv_size_measurements: missing"]
    assert section.details["clean_window_ready"] is False
    assert section.details["clean_window_blockers"] == [
        "active AutoPilot process(es): 123 autopilot"
    ]


def test_w8_trajectory_section_surfaces_concentration_warning() -> None:
    section = report_mod.w8_trajectory_section(
        {
            "status": "progressing",
            "ok": True,
            "latest_trial_id": 1099,
            "snapshot_count": 155,
            "candidate_count": 41,
            "status_counts": {"active_recent_replay": 1},
            "open_requirements": ["replay_concentration_warning"],
            "recent_active_candidates": ["abc"],
            "replay_eligible_candidates": ["abc"],
            "recent_replay_eligible_candidates": ["abc"],
            "stale_accumulating_candidates": ["def", "ghi"],
            "replay_concentration": {
                "warning": True,
                "warning_reason": "recent replay evidence is concentrated",
                "top_active_candidate": "abc",
                "top_active_attempt_share": 1.0,
            },
        }
    )

    assert section.status == "blocked"
    assert section.blockers == [
        "replay_concentration_warning: recent replay evidence is concentrated"
    ]
    assert section.details["candidate_generation_required"] is False
    assert section.details["replay_eligible_candidates"] == ["abc"]
    assert section.details["stale_accumulating_candidate_count"] == 2
    assert section.details["replay_concentration"]["top_active_candidate"] == "abc"


def test_w8_trajectory_section_blocks_when_no_replay_eligible_candidate() -> None:
    section = report_mod.w8_trajectory_section(
        {
            "status": "stale_accumulating",
            "ok": False,
            "latest_trial_id": 1153,
            "snapshot_count": 8,
            "candidate_count": 2,
            "status_counts": {"active_recent_replay": 1, "stale_accumulating": 1},
            "open_requirements": [
                "no_replay_eligible_accumulating_candidate",
                "stale_accumulating_candidates_present",
            ],
            "recent_active_candidates": ["unreplayable-a"],
            "replay_eligible_candidates": [],
            "recent_replay_eligible_candidates": [],
            "stale_accumulating_candidates": ["stale-b"],
            "replay_concentration": {"warning": False},
        }
    )

    assert section.status == "blocked"
    assert section.summary == "W8 replay trajectory needs a replay-eligible candidate."
    assert section.blockers == [
        "w8_candidate_generation_required: no replay-eligible accumulating candidate"
    ]
    assert section.details["candidate_generation_required"] is True
    assert section.details["recent_active_candidates"] == ["unreplayable-a"]
    assert section.details["replay_eligible_candidates"] == []


def test_ds_e1_clean_window_report_surfaces_measurement_port(
    monkeypatch,
) -> None:
    monkeypatch.setattr(report_mod, "_pgrep", lambda pattern: [])
    monkeypatch.setattr(report_mod, "_pgrep_exact", lambda name: [])
    monkeypatch.setattr(report_mod, "_tcp_port_accepting", lambda port: True)

    report = report_mod.ds_e1_clean_window_report()

    assert report["ready"] is False
    assert report["measurement_port"] == 8194
    assert report["measurement_port_in_use"] is True
    assert report["blockers"] == [
        "measurement port 8194 is already accepting connections"
    ]


def test_xmas_section_accepts_promote_candidate_ab(monkeypatch, tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
xmas_routing:
  mode: "enforce"
  winner_table_path: "xmas_winner_table.yaml"
  require_complete_table: true
""",
        encoding="utf-8",
    )
    table = tmp_path / "xmas_winner_table.yaml"
    table.write_text("placeholder: true\n", encoding="utf-8")
    ab_root = tmp_path / "ab"
    run = ab_root / "run"
    run.mkdir(parents=True)
    (run / "summary.json").write_text(
        '{"decision": {"status": "promote_candidate", "blockers": []}, '
        '"xmas_policy": "incumbent_constrained_cheapfirst_v2"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(report_mod, "validate_xmas_config", lambda path: [])
    monkeypatch.setattr(report_mod, "validate_xmas_table", lambda path, **kwargs: [])

    section = report_mod.xmas_section(
        config_path=config,
        candidate_table_path=table,
        ab_root=ab_root,
        quiet_window={"ready": True, "blockers": []},
    )

    assert section.status == "ready"
    assert section.blockers == []
    assert section.details["latest_ab_decision_status"] == "promote_candidate"
    assert section.details["latest_ab_policy"] == (
        "incumbent_constrained_cheapfirst_v2"
    )
    assert section.details["latest_ab_ready"] is True


def test_xmas_section_promote_candidate_off_mode_waits_for_enablement(
    monkeypatch, tmp_path: Path
) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
xmas_routing:
  mode: "off"
  winner_table_path: "xmas_winner_table.yaml"
  require_complete_table: true
""",
        encoding="utf-8",
    )
    table = tmp_path / "xmas_winner_table.yaml"
    table.write_text("placeholder: true\n", encoding="utf-8")
    ab_root = tmp_path / "ab"
    run = ab_root / "run"
    run.mkdir(parents=True)
    (run / "summary.json").write_text(
        '{"decision": {"status": "promote_candidate", "blockers": []}, '
        '"xmas_policy": "incumbent_constrained_cheapfirst_v2"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(report_mod, "validate_xmas_config", lambda path: [])
    monkeypatch.setattr(report_mod, "validate_xmas_table", lambda path, **kwargs: [])

    section = report_mod.xmas_section(
        config_path=config,
        candidate_table_path=table,
        ab_root=ab_root,
        quiet_window={"ready": True, "blockers": []},
    )

    assert section.status == "blocked"
    assert section.blockers == ["xmas_routing.mode is off; enforce remains default-off"]
    assert section.details["latest_ab_ready"] is True
    assert section.details["latest_ab_decision_status"] == "promote_candidate"


def test_xmas_section_blocks_promote_candidate_from_legacy_policy(
    monkeypatch,
    tmp_path: Path,
) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        """
xmas_routing:
  mode: "enforce"
  winner_table_path: "xmas_winner_table.yaml"
  require_complete_table: true
""",
        encoding="utf-8",
    )
    table = tmp_path / "xmas_winner_table.yaml"
    table.write_text("placeholder: true\n", encoding="utf-8")
    ab_root = tmp_path / "ab"
    run = ab_root / "run"
    run.mkdir(parents=True)
    (run / "summary.json").write_text(
        '{"decision": {"status": "promote_candidate", "blockers": []}, '
        '"xmas_policy": "unknown_legacy"}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(report_mod, "validate_xmas_config", lambda path: [])
    monkeypatch.setattr(report_mod, "validate_xmas_table", lambda path, **kwargs: [])

    section = report_mod.xmas_section(
        config_path=config,
        candidate_table_path=table,
        ab_root=ab_root,
        quiet_window={"ready": True, "blockers": []},
    )

    assert section.status == "blocked"
    assert section.blockers == [
        "latest X-MAS held-out A/B policy is "
        "unknown_legacy; required incumbent_constrained_cheapfirst_v2"
    ]


def test_xmas_next_action_ready_when_only_evidence_is_missing() -> None:
    section = report_mod.GateSection(
        key="xmas_production_path",
        status="blocked",
        summary="blocked",
        blockers=["latest X-MAS held-out A/B decision is hold"],
        details={"quiet_window_ready": True, "quiet_window_blockers": []},
    )

    actions = report_mod.build_next_actions([section])

    assert actions == [
        {
            "key": "run_xmas_constrained_policy_ab",
            "priority": "P0",
            "status": "ready",
            "reason": (
                "X-MAS enforce needs a fresh held-out A/B carrying "
                "incumbent_constrained_cheapfirst_v2 and a promote_candidate verdict."
            ),
            "requires": (
                "attested quiet window; runner preflight refuses AutoPilot "
                "and competing benchmark coordinators"
            ),
            "blocked_by": [],
            "evidence_blockers": ["latest X-MAS held-out A/B decision is hold"],
            "prompt_manifest": (
                "benchmarks/results/runs/xmas_live_ab/"
                "20260618-heldout-resilient/prompts.jsonl"
            ),
            "required_policy": "incumbent_constrained_cheapfirst_v2",
            "command": (
                "cd /mnt/raid0/llm/epyc-orchestrator && "
                "uv run python scripts/benchmark/xmas_live_ab.py "
                "--prompts benchmarks/results/runs/xmas_live_ab/"
                "20260618-heldout-resilient/prompts.jsonl "
                "--reps 2 --host-quiet-confirmed "
                "--output benchmarks/results/runs/xmas_live_ab/"
                "$(date -u +%Y%m%dT%H%M%SZ)-constrained-policy"
            ),
        }
    ]


def test_xmas_next_action_enablement_when_repaired_ab_passed() -> None:
    section = report_mod.GateSection(
        key="xmas_production_path",
        status="blocked",
        summary="blocked",
        blockers=["xmas_routing.mode is off; enforce remains default-off"],
        details={
            "latest_ab_ready": True,
            "latest_ab_policy": "incumbent_constrained_cheapfirst_v2",
            "latest_ab_decision_status": "promote_candidate",
            "latest_ab_summary_path": "benchmarks/results/runs/xmas_live_ab/run/summary.json",
            "latest_ab_results_path": "benchmarks/results/runs/xmas_live_ab/run/results.jsonl",
            "latest_ab_score_delta": 0.1,
            "latest_ab_latency_ratio": 0.938,
        },
    )

    actions = report_mod.build_next_actions([section])

    assert len(actions) == 1
    action = actions[0]
    assert action["key"] == "decide_xmas_enforce_enablement"
    assert action["status"] == "ready"
    assert action["blocked_by"] == []
    assert action["evidence_blockers"] == [
        "xmas_routing.mode is off; enforce remains default-off"
    ]
    assert action["latest_ab_decision_status"] == "promote_candidate"
    assert action["required_policy"] == "incumbent_constrained_cheapfirst_v2"
    assert "--summarize-results benchmarks/results/runs/xmas_live_ab/run/results.jsonl" in action["command"]


def test_a9_next_action_ready_when_collection_window_clear() -> None:
    section = report_mod.GateSection(
        key="a9_pairwise_collection",
        status="ready",
        summary="ready",
        blockers=[],
        details={
            "ready": True,
            "status": "ready",
            "manifest_path": "/tmp/a9_manifest.json",
            "batch_count": 9,
            "post_collection_step_count": 7,
            "source_plan_decision": {"status": "expansion_plan_ready"},
        },
    )

    actions = report_mod.build_next_actions([section])

    assert len(actions) == 1
    action = actions[0]
    assert action["key"] == "run_a9_pairwise_collection_window"
    assert action["priority"] == "P1"
    assert action["status"] == "ready"
    assert action["blocked_by"] == []
    assert action["manifest"] == "/tmp/a9_manifest.json"
    assert action["batch_count"] == 9
    assert action["post_collection_step_count"] == 7
    assert action["source_plan_decision"] == {"status": "expansion_plan_ready"}
    assert "collect_offline_reward_pairwise_expanded_gap.sh" in action["command"]
    assert "offline_reward_pairwise_collection_status.py" in action["follow_up"]


def test_a9_section_marks_empty_manifest_attention(monkeypatch) -> None:
    contract_summary = Path("/tmp/missing_a9_contract_summary.json")
    monkeypatch.setattr(
        report_mod,
        "build_a9_collection_status",
        lambda path: {
            "ready": False,
            "status": "no_runnable_batches",
            "manifest_path": "/tmp/a9_manifest.json",
            "manifest_schema_version": "offline_reward_pairwise_collection_window.v1",
            "source_plan_decision": {"status": "expansion_plan_ready"},
            "batch_count": 0,
            "post_collection_step_count": 7,
            "autopilot_guard": {"refusal_exit_code": 75},
            "blockers": [],
            "warnings": ["manifest has no runnable collection batches"],
        },
    )

    section = report_mod.a9_collection_section(
        Path("/tmp/a9_manifest.json"),
        contract_summary_path=contract_summary,
        audit_target_ranker_summary_path=None,
        audit_target_direction_audit_path=None,
    )

    assert section.status == "attention"
    assert section.blockers == []
    assert section.details["status"] == "no_runnable_batches"
    assert section.details["warnings"] == [
        "manifest has no runnable collection batches"
    ]


def test_a9_section_surfaces_candidate_contract_decision(monkeypatch, tmp_path: Path) -> None:
    contract_summary = tmp_path / "candidate_contract_summary.json"
    source_reward_summary = tmp_path / "source_reward_diagnostic_summary.json"
    contract_summary.write_text(
        """
{
  "schema_version": "offline_reward_pairwise_contract_summary.v1",
  "coverage": {
    "pair_rows": 32,
    "cross_action_pair_rows": 32,
    "source_record_groups": 302
  },
  "decision": {
    "status": "insufficient_contrast",
    "recommended_next": "collect_more_within_task_positive_negative_contrasts",
    "runtime_gate_change_allowed": false
  }
}
""",
        encoding="utf-8",
    )
    source_reward_summary.write_text(
        """
{
  "schema_version": "offline_reward_source_reward_diagnostic_summary.v1",
  "coverage": {
    "pair_rows": 180,
    "cross_action_pair_rows": 180,
    "source_record_groups": 302
  },
  "decision": {
    "status": "contract_ready",
    "recommended_next": "decide whether A9 should train on source-q-reward pairwise labels",
    "runtime_gate_change_allowed": false
  },
  "diagnostic": {
    "score_source": "source_q_reward_passthrough",
    "independent_oracle": false,
    "diagnostic_only": true
  }
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        report_mod,
        "build_a9_collection_status",
        lambda path: {
            "ready": False,
            "status": "no_runnable_batches",
            "manifest_path": "/tmp/a9_manifest.json",
            "manifest_schema_version": "offline_reward_pairwise_collection_window.v1",
            "source_plan_decision": {"status": "expansion_plan_ready"},
            "batch_count": 0,
            "post_collection_step_count": 7,
            "autopilot_guard": {"refusal_exit_code": 75},
            "blockers": [],
            "warnings": ["manifest has no runnable collection batches"],
        },
    )

    section = report_mod.a9_collection_section(
        Path("/tmp/a9_manifest.json"),
        contract_summary_path=contract_summary,
        source_reward_diagnostic_summary_path=source_reward_summary,
        source_reward_ranker_summary_path=None,
        audit_target_ranker_summary_path=None,
        audit_target_direction_audit_path=None,
    )
    actions = report_mod.build_next_actions([section])

    assert section.status == "attention"
    assert "insufficient_contrast" in section.summary
    assert "source-reward diagnostic is contract_ready" in section.summary
    assert section.details["candidate_contract_decision"]["status"] == (
        "insufficient_contrast"
    )
    assert section.details["candidate_contract_coverage"]["pair_rows"] == 32
    assert section.details["source_reward_diagnostic_decision"]["status"] == (
        "contract_ready"
    )
    assert section.details["source_reward_diagnostic_coverage"]["pair_rows"] == 180
    action = actions[0]
    assert action["key"] == "revise_a9_reward_oracle_or_reference_source"
    assert action["candidate_contract_decision"]["status"] == "insufficient_contrast"
    assert action["candidate_contract_coverage"]["cross_action_pair_rows"] == 32
    assert action["source_reward_diagnostic_decision"]["status"] == "contract_ready"
    assert action["source_reward_diagnostic_coverage"]["cross_action_pair_rows"] == 180
    assert "source-q-reward diagnostic" in action["reason"]
    assert "not collection volume" in action["reason"]


def test_a9_next_action_preregisters_source_reward_target_when_ranker_ready(
    monkeypatch, tmp_path: Path
) -> None:
    contract_summary = tmp_path / "candidate_contract_summary.json"
    source_reward_summary = tmp_path / "source_reward_diagnostic_summary.json"
    source_ranker_summary = tmp_path / "source_reward_ranker_summary.json"
    contract_summary.write_text(
        """
{
  "coverage": {
    "pair_rows": 32,
    "cross_action_pair_rows": 32
  },
  "decision": {
    "status": "insufficient_contrast",
    "runtime_gate_change_allowed": false
  }
}
""",
        encoding="utf-8",
    )
    source_reward_summary.write_text(
        """
{
  "coverage": {
    "pair_rows": 180,
    "cross_action_pair_rows": 180
  },
  "decision": {
    "status": "contract_ready",
    "runtime_gate_change_allowed": false
  },
  "diagnostic": {
    "score_source": "source_q_reward_passthrough",
    "independent_oracle": false,
    "diagnostic_only": true
  }
}
""",
        encoding="utf-8",
    )
    source_ranker_summary.write_text(
        """
{
  "input": {
    "pair_rows": 180,
    "cross_action_pair_rows": 180
  },
  "aggregate": {
    "decision": {
      "status": "pairwise_ranker_signal",
      "best_family": "hist_gradient_boosting",
      "runtime_gate_change_allowed": false
    }
  },
  "cross_validation": {
    "decision": {
      "status": "pairwise_ranker_signal",
      "best_family": "hist_gradient_boosting",
      "runtime_gate_change_allowed": false
    }
  },
  "holdout_decision": {
    "status": "holdout_signal_consistent",
    "eligible_holdouts": 3,
    "passing_holdouts": 3,
    "runtime_gate_change_allowed": false
  }
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        report_mod,
        "build_a9_collection_status",
        lambda path: {
            "ready": False,
            "status": "no_runnable_batches",
            "manifest_path": "/tmp/a9_manifest.json",
            "manifest_schema_version": "offline_reward_pairwise_collection_window.v1",
            "source_plan_decision": {"status": "expansion_plan_ready"},
            "batch_count": 0,
            "post_collection_step_count": 7,
            "autopilot_guard": {"refusal_exit_code": 75},
            "blockers": [],
            "warnings": ["manifest has no runnable collection batches"],
        },
    )

    section = report_mod.a9_collection_section(
        Path("/tmp/a9_manifest.json"),
        contract_summary_path=contract_summary,
        source_reward_diagnostic_summary_path=source_reward_summary,
        source_reward_ranker_summary_path=source_ranker_summary,
        source_reward_target_contract_path=None,
        audit_target_ranker_summary_path=None,
        audit_target_direction_audit_path=None,
    )
    actions = report_mod.build_next_actions([section])

    assert "source-reward ranker is pairwise_ranker_signal" in section.summary
    assert len(actions) == 1
    action = actions[0]
    assert action["key"] == "preregister_a9_source_reward_pairwise_target"
    assert action["status"] == "active"
    assert action["blocked_by"] == []
    assert "not an independent oracle" in action["reason"]
    assert "target-contract decision" in action["reason"]
    assert action["source_reward_ranker_aggregate_decision"]["status"] == (
        "pairwise_ranker_signal"
    )
    assert action["source_reward_ranker_cv_decision"]["status"] == (
        "pairwise_ranker_signal"
    )
    assert action["source_reward_ranker_holdout_decision"]["status"] == (
        "holdout_signal_consistent"
    )
    assert action["source_reward_ranker_input"]["pair_rows"] == 180
    assert "runtime_gate_change_allowed=false" in action["command"]


def test_a9_preregistered_source_reward_target_suppresses_next_action(
    monkeypatch, tmp_path: Path
) -> None:
    contract_summary = tmp_path / "candidate_contract_summary.json"
    source_reward_summary = tmp_path / "source_reward_diagnostic_summary.json"
    source_ranker_summary = tmp_path / "source_reward_ranker_summary.json"
    source_target_contract = tmp_path / "source_reward_target_contract.json"
    contract_summary.write_text(
        """
{
  "coverage": {"pair_rows": 32, "cross_action_pair_rows": 32},
  "decision": {"status": "insufficient_contrast", "runtime_gate_change_allowed": false}
}
""",
        encoding="utf-8",
    )
    source_reward_summary.write_text(
        """
{
  "coverage": {"pair_rows": 180, "cross_action_pair_rows": 180},
  "decision": {"status": "contract_ready", "runtime_gate_change_allowed": false},
  "diagnostic": {"score_source": "source_q_reward_passthrough", "independent_oracle": false}
}
""",
        encoding="utf-8",
    )
    source_ranker_summary.write_text(
        """
{
  "input": {"pair_rows": 180, "cross_action_pair_rows": 180},
  "aggregate": {"decision": {"status": "pairwise_ranker_signal", "runtime_gate_change_allowed": false}},
  "cross_validation": {"decision": {"status": "pairwise_ranker_signal", "runtime_gate_change_allowed": false}},
  "holdout_decision": {"status": "holdout_signal_consistent", "runtime_gate_change_allowed": false}
}
""",
        encoding="utf-8",
    )
    source_target_contract.write_text(
        """
{
  "schema_version": "offline_reward_source_reward_pairwise_target_contract.v1",
  "status": "preregistered_offline_training_target",
  "target": {
    "name": "a9_source_q_reward_pairwise_training_target_v1",
    "runtime_gate_change_allowed": false
  }
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        report_mod,
        "build_a9_collection_status",
        lambda path: {
            "ready": False,
            "status": "no_runnable_batches",
            "manifest_path": "/tmp/a9_manifest.json",
            "manifest_schema_version": "offline_reward_pairwise_collection_window.v1",
            "source_plan_decision": {"status": "expansion_plan_ready"},
            "batch_count": 0,
            "post_collection_step_count": 7,
            "autopilot_guard": {"refusal_exit_code": 75},
            "blockers": [],
            "warnings": [],
        },
    )

    section = report_mod.a9_collection_section(
        Path("/tmp/a9_manifest.json"),
        contract_summary_path=contract_summary,
        source_reward_diagnostic_summary_path=source_reward_summary,
        source_reward_ranker_summary_path=source_ranker_summary,
        source_reward_target_contract_path=source_target_contract,
        audit_target_ranker_summary_path=None,
        audit_target_direction_audit_path=None,
    )

    assert "source-reward target contract is preregistered_offline_training_target" in (
        section.summary
    )
    assert section.status == "ready"
    assert "A9 pairwise source-acquisition window is closed" in section.summary
    assert section.details["source_reward_ranker_ready"] is True
    assert section.details["source_reward_target_preregistered"] is True
    assert section.details["source_reward_target_contract"]["status"] == (
        "preregistered_offline_training_target"
    )
    assert report_mod.build_next_actions([section]) == []


def test_a9_audit_target_holdout_gap_surfaces_after_source_target_preregistered(
    monkeypatch, tmp_path: Path
) -> None:
    contract_summary = tmp_path / "candidate_contract_summary.json"
    source_reward_summary = tmp_path / "source_reward_diagnostic_summary.json"
    source_ranker_summary = tmp_path / "source_reward_ranker_summary.json"
    source_target_contract = tmp_path / "source_reward_target_contract.json"
    audit_target_ranker = tmp_path / "audit_target_ranker_summary.json"
    audit_target_direction = tmp_path / "audit_target_direction_audit.json"
    contract_summary.write_text(
        """
{
  "coverage": {"pair_rows": 32, "cross_action_pair_rows": 32},
  "decision": {"status": "insufficient_contrast", "runtime_gate_change_allowed": false}
}
""",
        encoding="utf-8",
    )
    source_reward_summary.write_text(
        """
{
  "coverage": {"pair_rows": 180, "cross_action_pair_rows": 180},
  "decision": {"status": "contract_ready", "runtime_gate_change_allowed": false},
  "diagnostic": {"score_source": "source_q_reward_passthrough", "independent_oracle": false}
}
""",
        encoding="utf-8",
    )
    source_ranker_summary.write_text(
        """
{
  "input": {"pair_rows": 180, "cross_action_pair_rows": 180},
  "aggregate": {"decision": {"status": "pairwise_ranker_signal", "runtime_gate_change_allowed": false}},
  "cross_validation": {"decision": {"status": "pairwise_ranker_signal", "runtime_gate_change_allowed": false}},
  "holdout_decision": {"status": "holdout_signal_consistent", "runtime_gate_change_allowed": false}
}
""",
        encoding="utf-8",
    )
    source_target_contract.write_text(
        """
{
  "schema_version": "offline_reward_source_reward_pairwise_target_contract.v1",
  "status": "preregistered_offline_training_target",
  "target": {"runtime_gate_change_allowed": false}
}
""",
        encoding="utf-8",
    )
    audit_target_ranker.write_text(
        """
{
  "input": {"pair_rows": 6192, "cross_action_pair_rows": 4296},
  "aggregate": {"decision": {"status": "pairwise_ranker_signal", "runtime_gate_change_allowed": false}},
  "holdout_decision": {
    "status": "mixed_holdout_signal",
    "eligible_holdouts": 16,
    "passing_holdouts": 13,
    "blockers": [
      "source_family:seeding_eval:insufficient_pairwise_signal",
      "suite:general:insufficient_pairwise_signal"
    ],
    "runtime_gate_change_allowed": false
  }
}
""",
        encoding="utf-8",
    )
    audit_target_direction.write_text(
        """
{
  "decision": {
    "status": "preference_coverage_gaps_found",
    "runtime_gate_change_allowed": false
  },
  "collection_targets": [
    {"stratum_field": "source_family", "stratum_value": "seeding_eval"}
  ]
}
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        report_mod,
        "build_a9_collection_status",
        lambda path: {
            "ready": False,
            "status": "no_runnable_batches",
            "manifest_path": "/tmp/a9_manifest.json",
            "manifest_schema_version": "offline_reward_pairwise_collection_window.v1",
            "source_plan_decision": {"status": "expansion_plan_ready"},
            "batch_count": 0,
            "post_collection_step_count": 7,
            "autopilot_guard": {"refusal_exit_code": 75},
            "blockers": [],
            "warnings": [],
        },
    )

    section = report_mod.a9_collection_section(
        Path("/tmp/a9_manifest.json"),
        contract_summary_path=contract_summary,
        source_reward_diagnostic_summary_path=source_reward_summary,
        source_reward_ranker_summary_path=source_ranker_summary,
        source_reward_target_contract_path=source_target_contract,
        audit_target_ranker_summary_path=audit_target_ranker,
        audit_target_direction_audit_path=audit_target_direction,
    )
    actions = report_mod.build_next_actions([section])

    assert section.status == "ready"
    assert "audit-target ranker holdout is mixed_holdout_signal (13/16 passing)" in (
        section.summary
    )
    assert section.details["audit_target_ranker_holdout_decision"]["status"] == (
        "mixed_holdout_signal"
    )
    assert section.details["audit_target_collection_targets"] == [
        {"stratum_field": "source_family", "stratum_value": "seeding_eval"}
    ]
    assert [action["key"] for action in actions] == [
        "collect_a9_audit_target_pairwise_preferences"
    ]
    action = actions[0]
    assert action["priority"] == "P1"
    assert action["runtime_gate_change_allowed"] is False
    assert "source_family:seeding_eval:insufficient_pairwise_signal" in action["reason"]
    assert action["audit_target_collection_targets"] == [
        {"stratum_field": "source_family", "stratum_value": "seeding_eval"}
    ]


def test_a9_audit_target_action_surfaces_guarded_collection_manifest(
    monkeypatch, tmp_path: Path
) -> None:
    contract_summary = tmp_path / "candidate_contract_summary.json"
    source_reward_summary = tmp_path / "source_reward_diagnostic_summary.json"
    source_ranker_summary = tmp_path / "source_reward_ranker_summary.json"
    source_target_contract = tmp_path / "source_reward_target_contract.json"
    audit_target_ranker = tmp_path / "audit_target_ranker_summary.json"
    audit_target_direction = tmp_path / "audit_target_direction_audit.json"
    primary_manifest = tmp_path / "expanded_gap_manifest.json"
    audit_manifest = tmp_path / "audit_target_manifest.json"
    contract_summary.write_text(
        '{"coverage": {}, "decision": {"status": "insufficient_contrast"}}',
        encoding="utf-8",
    )
    source_reward_summary.write_text(
        '{"coverage": {}, "decision": {"status": "contract_ready"}}',
        encoding="utf-8",
    )
    source_ranker_summary.write_text(
        """
{
  "aggregate": {"decision": {"status": "pairwise_ranker_signal"}},
  "cross_validation": {"decision": {"status": "pairwise_ranker_signal"}},
  "holdout_decision": {"status": "holdout_signal_consistent"}
}
""",
        encoding="utf-8",
    )
    source_target_contract.write_text(
        '{"status": "preregistered_offline_training_target"}',
        encoding="utf-8",
    )
    audit_target_ranker.write_text(
        """
{
  "aggregate": {"decision": {"status": "pairwise_ranker_signal"}},
  "holdout_decision": {
    "status": "mixed_holdout_signal",
    "eligible_holdouts": 16,
    "passing_holdouts": 13,
    "blockers": ["suite:general:insufficient_pairwise_signal"]
  }
}
""",
        encoding="utf-8",
    )
    audit_target_direction.write_text(
        """
{
  "decision": {"status": "preference_coverage_gaps_found"},
  "collection_targets": [
    {"stratum_field": "suite", "stratum_value": "general"}
  ]
}
""",
        encoding="utf-8",
    )
    audit_manifest.write_text("{}", encoding="utf-8")

    def fake_status(path: Path) -> dict:
        if path == audit_manifest:
            return {
                "ready": False,
                "status": "blocked",
                "manifest_path": str(path),
                "manifest_schema_version": "offline_reward_pairwise_collection_window.v1",
                "source_plan_decision": {"status": "insufficient_non_overlapping_cross_action_candidates"},
                "batch_count": 4,
                "post_collection_step_count": 7,
                "autopilot_guard": {"refusal_exit_code": 75},
                "blockers": ["active AutoPilot process(es): 123 autopilot"],
                "warnings": [],
            }
        return {
            "ready": False,
            "status": "no_runnable_batches",
            "manifest_path": str(path),
            "manifest_schema_version": "offline_reward_pairwise_collection_window.v1",
            "source_plan_decision": {"status": "expansion_plan_ready"},
            "batch_count": 0,
            "post_collection_step_count": 7,
            "autopilot_guard": {"refusal_exit_code": 75},
            "blockers": [],
            "warnings": [],
        }

    monkeypatch.setattr(report_mod, "build_a9_collection_status", fake_status)

    section = report_mod.a9_collection_section(
        primary_manifest,
        contract_summary_path=contract_summary,
        source_reward_diagnostic_summary_path=source_reward_summary,
        source_reward_ranker_summary_path=source_ranker_summary,
        source_reward_target_contract_path=source_target_contract,
        audit_target_ranker_summary_path=audit_target_ranker,
        audit_target_direction_audit_path=audit_target_direction,
        audit_target_collection_manifest_path=audit_manifest,
    )
    actions = report_mod.build_next_actions([section])

    assert "audit-target collection window is blocked with 4 batch(es)" in section.summary
    assert section.details["audit_target_collection_status"]["batch_count"] == 4
    action = actions[0]
    assert action["key"] == "collect_a9_audit_target_pairwise_preferences"
    assert action["status"] == "blocked"
    assert action["audit_target_collection_batch_count"] == 4
    assert action["blocked_by"] == ["active AutoPilot process(es): 123 autopilot"]
    assert "collect_offline_reward_pairwise_audit_target.sh" in action["command"]


def test_a9_next_action_switches_to_oracle_design_when_no_batches() -> None:
    section = report_mod.GateSection(
        key="a9_pairwise_collection",
        status="attention",
        summary="no batches",
        blockers=[],
        details={
            "ready": False,
            "status": "no_runnable_batches",
            "manifest_path": "/tmp/a9_manifest.json",
            "batch_count": 0,
            "post_collection_step_count": 7,
            "source_plan_decision": {"status": "expansion_plan_ready"},
        },
    )

    actions = report_mod.build_next_actions([section])

    assert len(actions) == 1
    action = actions[0]
    assert action["key"] == "revise_a9_reward_oracle_or_reference_source"
    assert action["priority"] == "P1"
    assert action["status"] == "active"
    assert action["blocked_by"] == []
    assert action["batch_count"] == 0
    assert "current collection script" in action["follow_up"]


def test_w8_next_action_when_restart_ready_without_promotion_finalization() -> None:
    sections = [
        report_mod.GateSection(
            key="phase_health",
            status="ready",
            summary="active",
            blockers=[],
            details={"status": "active"},
        ),
        report_mod.GateSection(
            key="w4_w6_restart_cutover",
            status="ready",
            summary="ready",
            blockers=[],
            details={
                "w8_promotion_status": "pending_fresh_eval",
                "w8_open_requirements": [
                    "pending_fresh_eval_queued",
                    "combined_E_below_required",
                    "fresh_promotion_eval_required",
                ],
                "w8_pending_candidate": "candidate-a",
                "w8_pending_source_trial_id": 41,
                "w8_pending_attempts": 1,
                "w8_last_blocked_reason": None,
                "w8_latest_seq_trial_id": 40,
                "w8_latest_combined_E": 32.0,
                "w8_latest_required_E": 100.0,
                "w8_latest_fresh_eval": False,
                "w8_latest_baseline_reference_state": "fresh",
            },
        ),
    ]

    actions = report_mod.build_next_actions(sections)

    assert actions[0]["key"] == "collect_w8_promotion_eval_evidence"
    assert actions[0]["status"] == "active"
    assert actions[0]["evidence"]["w8_promotion_status"] == "pending_fresh_eval"
    assert actions[0]["evidence"]["open_requirements"] == [
        "pending_fresh_eval_queued",
        "combined_E_below_required",
        "fresh_promotion_eval_required",
    ]
    assert actions[0]["evidence"]["pending_candidate"] == "candidate-a"
    assert actions[0]["evidence"]["latest_seq_trial_id"] == 40
    assert actions[0]["evidence"]["latest_combined_E"] == 32.0
    assert actions[0]["evidence"]["latest_required_E"] == 100.0
    assert actions[0]["evidence"]["latest_fresh_eval"] is False
    assert actions[0]["evidence"]["latest_baseline_reference_state"] == "fresh"


def test_w8_next_action_surfaces_candidate_generation_requirement() -> None:
    sections = [
        report_mod.GateSection(
            key="phase_health",
            status="ready",
            summary="active",
            blockers=[],
            details={"status": "active"},
        ),
        report_mod.GateSection(
            key="w4_w6_restart_cutover",
            status="ready",
            summary="ready",
            blockers=[],
            details={
                "w8_promotion_status": "none",
                "w8_open_requirements": [
                    "combined_E_below_required",
                    "fresh_promotion_eval_required",
                    "no_recent_multi_observation_accumulating_candidate",
                    "seq_confirmation_required",
                ],
                "w8_latest_seq_trial_id": 1120,
                "w8_latest_candidate": "ec17bc71c6472ae4",
                "w8_latest_combined_E": 0.98638,
                "w8_latest_required_E": 100.0,
                "w8_latest_fresh_eval": False,
            },
        ),
        report_mod.w8_trajectory_section(
            {
                "status": "evidence_bound",
                "ok": False,
                "latest_trial_id": 1120,
                "snapshot_count": 170,
                "candidate_count": 49,
                "status_counts": {"excluded": 6, "refuted": 3, "reverted": 40},
                "terminal_reason_counts": {
                    "Suite 'general' regression: -1.800 "
                    "(threshold: -1.500; n_result=5, n_baseline=2)": 40
                },
                "dominant_terminal_reason": {
                    "reason": "Suite 'general' regression: -1.800 "
                    "(threshold: -1.500; n_result=5, n_baseline=2)",
                    "count": 40,
                    "status": "reverted",
                    "candidate": "ec17bc71c6472ae4",
                    "latest_trial_id": 1120,
                    "details": {
                        "kind": "suite_regression",
                        "suite": "general",
                        "delta": -1.8,
                        "threshold": -1.5,
                        "n_result": 5,
                        "n_baseline": 2,
                    },
                    "baseline_sample_warning": True,
                },
                "open_requirements": [
                    "no_recent_multi_observation_accumulating_candidate"
                ],
                "recent_active_candidates": [],
                "replay_eligible_candidates": [],
                "recent_replay_eligible_candidates": [],
                "stale_accumulating_candidates": [],
                "replay_concentration": {"warning": False},
            }
        ),
    ]

    actions = report_mod.build_next_actions(sections)

    assert actions[0]["key"] == "collect_w8_promotion_eval_evidence"
    assert "new keepable candidate" in actions[0]["reason"]
    assert "Dominant terminal blocker: 40 candidate(s)" in actions[0]["reason"]
    assert actions[0]["evidence"]["candidate_generation_required"] is True
    assert actions[0]["evidence"]["candidate_status_counts"] == {
        "excluded": 6,
        "refuted": 3,
        "reverted": 40,
    }
    assert actions[0]["evidence"]["dominant_terminal_reason"][
        "baseline_sample_warning"
    ] is True
    assert actions[0]["evidence"]["recent_active_candidates"] == []


def test_quiet_window_process_matcher_ignores_script_names_in_prompts() -> None:
    planner_line = (
        "123 claude -p Use scripts/benchmark/seed_specialist_routing.py "
        "only when the clean window is approved"
    )
    real_line = (
        "456 uv run python scripts/benchmark/seed_specialist_routing.py "
        "--dry-run"
    )

    assert not report_mod._process_line_matches_pattern(
        planner_line,
        "seed_specialist_routing.py",
    )
    assert report_mod._process_line_matches_pattern(
        real_line,
        "seed_specialist_routing.py",
    )


def test_render_markdown_surfaces_section_details() -> None:
    rendered = report_mod.render_markdown(
        {
            "ready": False,
            "blockers": ["gate: blocked"],
            "next_actions": [
                {
                    "key": "run_gate",
                    "priority": "P0",
                    "status": "blocked",
                    "reason": "needs evidence",
                    "blocked_by": ["window busy"],
                    "command": "python3 gate.py --strict",
                }
            ],
            "sections": [
                {
                    "key": "gate",
                    "status": "blocked",
                    "summary": "blocked",
                    "blockers": ["blocked"],
                    "details": {"count": 1},
                }
            ],
        }
    )

    assert "# Fable5 Gate Report" in rendered
    assert "Ready: false" in rendered
    assert "- gate: blocked" in rendered
    assert "## Next Actions" in rendered
    assert "### run_gate" in rendered
    assert "- Command: `python3 gate.py --strict`" in rendered
    assert "### gate" in rendered
    assert '`count`: 1' in rendered


def test_cli_strict_returns_one_when_gate_blocks(tmp_path: Path, monkeypatch, capsys) -> None:
    state = tmp_path / "state.json"
    journal = tmp_path / "journal.jsonl"
    phase = tmp_path / "phase.json"
    state.write_text('{"trial_counter": 1}\n', encoding="utf-8")
    journal.write_text("", encoding="utf-8")
    phase.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(report_mod, "_load_jsonl", lambda path: [])
    phase_kwargs = {}

    def fake_phase_health(**kwargs):
        phase_kwargs.update(kwargs)
        return {"ok": False, "blockers": ["stale"]}

    monkeypatch.setattr(report_mod, "build_phase_health_report", fake_phase_health)
    monkeypatch.setattr(report_mod, "build_ds_e1_packet", lambda: {"ready_for_profile_decision": True, "blockers": [], "sections": []})
    monkeypatch.setattr(
        report_mod,
        "build_model_gate_report",
        lambda **kwargs: {
            "ready": False,
            "blockers": ["phase_health: stale"],
            "sections": [],
        },
    )

    rc = report_mod.main(
        [
            "--state",
            str(state),
            "--journal",
            str(journal),
            "--phase",
            str(phase),
            "--json",
            "--strict",
        ]
    )

    assert rc == 1
    assert phase_kwargs["require_current_code"] is True
    assert "phase_health: stale" in capsys.readouterr().out


def test_cli_writes_json_and_markdown_outputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    state = tmp_path / "state.json"
    journal = tmp_path / "journal.jsonl"
    phase = tmp_path / "phase.json"
    out_json = tmp_path / "reports" / "fable5_gate.json"
    out_md = tmp_path / "reports" / "fable5_gate.md"
    state.write_text('{"trial_counter": 1}\n', encoding="utf-8")
    journal.write_text("", encoding="utf-8")
    phase.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(report_mod, "_load_jsonl", lambda path: [])
    monkeypatch.setattr(
        report_mod,
        "build_phase_health_report",
        lambda **kwargs: {"ok": False, "blockers": ["stale"]},
    )
    monkeypatch.setattr(
        report_mod,
        "build_ds_e1_packet",
        lambda: {"ready_for_profile_decision": True, "blockers": [], "sections": []},
    )
    monkeypatch.setattr(
        report_mod,
        "build_model_gate_report",
        lambda **kwargs: {
            "ready": False,
            "blockers": ["phase_health: stale"],
            "next_actions": [],
            "sections": [
                {
                    "key": "phase_health",
                    "status": "blocked",
                    "summary": "stale",
                    "blockers": ["stale"],
                    "details": {},
                }
            ],
        },
    )

    rc = report_mod.main(
        [
            "--state",
            str(state),
            "--journal",
            str(journal),
            "--phase",
            str(phase),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
            "--strict",
        ]
    )

    assert rc == 1
    assert "# Fable5 Gate Report" in capsys.readouterr().out
    assert '"ready": false' in out_json.read_text(encoding="utf-8")
    assert "- phase_health: stale" in out_md.read_text(encoding="utf-8")
