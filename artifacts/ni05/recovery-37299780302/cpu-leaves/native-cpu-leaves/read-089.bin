from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "autopilot"
sys.path.insert(0, str(_ROOT))

import phase_status  # noqa: E402
from phase_status import (  # noqa: E402
    AsyncTaskRunner,
    PhaseTracker,
    build_phase_health_report,
    format_phase_health_report,
)


def test_phase_tracker_writes_snapshot_and_jsonl(tmp_path):
    snapshot = tmp_path / "phase.json"
    events = tmp_path / "phase.jsonl"
    tracker = PhaseTracker(path=snapshot, events_path=events)

    tracker.set("planner_prompt_build", trial_id=7, idle_reason="building")
    payload = json.loads(snapshot.read_text())

    assert payload["phase"] == "planner_prompt_build"
    assert payload["trial_id"] == 7
    assert payload["idle_reason"] == "building"
    assert payload["pid"] > 0
    assert events.read_text().strip()


def test_async_task_runner_sync_fallback():
    runner = AsyncTaskRunner(enabled=False)

    result = runner.submit("add", lambda a, b: a + b, 2, 3)

    assert result == 5


def test_phase_health_report_accepts_fresh_alive_heartbeat(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 894,
                "action_type": "deep_eval",
                "eval_label": "T2",
                "eval_completed_questions": 200,
                "eval_total_questions": 500,
                "eval_correct_questions": 144,
                "eval_correct_pct": 72.0,
                "eval_concurrency": 1,
                "updated_at": 100.0,
                "updated_at_iso": "2026-06-20T12:13:13+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr("phase_status._read_process_env_flags", lambda pid: {})

    report = build_phase_health_report(path=snapshot, now=120.0, stale_after_s=60.0)

    assert report["ok"] is True
    assert report["status"] == "active"
    assert report["heartbeat_age_s"] == 20.0
    assert report["pid_alive"] is True
    assert report["trial_id"] == 894
    assert report["eval_completed_questions"] == 200
    assert report["eval_total_questions"] == 500
    assert report["w6_audit_accrual_enabled"] is None
    formatted = "\n".join(format_phase_health_report(report))
    assert "Status: active" in formatted
    assert "Eval progress: 200/500 (72% correct)" in formatted


def test_phase_health_report_surfaces_runtime_source_drift_without_blocking(
    tmp_path, monkeypatch
):
    snapshot = tmp_path / "phase.json"
    source = tmp_path / "actions.py"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 1055,
                "action_type": "numeric_trial",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    source.write_text("# changed after start\n", encoding="utf-8")
    source_mtime = 75.0
    os.utime(source, (source_mtime, source_mtime))
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr("phase_status._read_process_env_flags", lambda pid: {})
    monkeypatch.setattr("phase_status._process_started_at_s", lambda pid: 50.0)
    monkeypatch.setattr("phase_status._tail_eval_progress", lambda *a, **k: None)

    report = build_phase_health_report(
        path=snapshot,
        source_paths=[source],
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["ok"] is True
    assert report["status"] == "active"
    assert report["process_started_at_s"] == 50.0
    assert report["code_stale"] is True
    assert report["code_stale_paths"][0]["path"] == str(source)
    assert report["blockers"] == []
    formatted = "\n".join(format_phase_health_report(report))
    assert "Runtime source stale: True" in formatted
    assert "Runtime Source Drift" in formatted


def test_phase_health_report_can_block_on_runtime_source_drift(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    source = tmp_path / "eval_tower.py"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 1055,
                "action_type": "numeric_trial",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    source.write_text("# changed after start\n", encoding="utf-8")
    os.utime(source, (80.0, 80.0))
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr("phase_status._read_process_env_flags", lambda pid: {})
    monkeypatch.setattr("phase_status._process_started_at_s", lambda pid: 50.0)
    monkeypatch.setattr("phase_status._tail_eval_progress", lambda *a, **k: None)

    report = build_phase_health_report(
        path=snapshot,
        source_paths=[source],
        require_current_code=True,
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["ok"] is False
    assert report["status"] == "code_stale"
    assert report["blockers"] == [
        "autopilot process predates runtime source changes: eval_tower.py"
    ]


def test_phase_health_report_surfaces_outcome_stall_without_blocking_by_default(
    tmp_path,
    monkeypatch,
):
    snapshot = tmp_path / "phase.json"
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "trial_id": 1,
                        "timestamp": "2026-07-05T00:00:00+00:00",
                        "action_type": "numeric_trial",
                        "pareto_status": "frontier",
                        "keep_revert_decision": "keep",
                    }
                ),
                json.dumps(
                    {
                        "trial_id": 20,
                        "timestamp": "2026-07-05T01:00:00+00:00",
                        "action_type": "numeric_trial",
                        "pareto_status": "dominated",
                        "keep_revert_decision": "revert",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 21,
                "action_type": "numeric_trial",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(
        path=snapshot,
        journal_dir=journal_dir,
        max_trials_since_frontier=10,
        max_trials_since_promotion=10,
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["ok"] is True
    assert report["status"] == "active"
    assert report["blockers"] == []
    assert report["outcome_progress"]["status"] == "attention"
    assert report["outcome_progress"]["latest_trial_id"] == 20
    assert report["outcome_progress"]["trials_since_frontier"] == 19
    assert report["outcome_progress"]["trials_since_promotion"] is None
    assert report["outcome_progress"]["rates"]["keepable_rate"] == {
        "count": 1,
        "total": 2,
        "rate": 0.5,
    }
    assert report["outcome_progress"]["rates"]["regression_per_active_trial"] == {
        "count": 0,
        "total": 2,
        "rate": 0.0,
    }
    assert report["outcome_progress"]["rates"]["promotions_per_100_active_trials"] == {
        "count": 0,
        "total": 2,
        "per_100": 0.0,
    }
    formatted = "\n".join(format_phase_health_report(report))
    assert "Outcome progress status: attention" in formatted
    assert "frontier admission stale" in formatted
    assert "regression_per_active_trial=0.0" in formatted
    assert "promotions_per_100_active_trials=0.0" in formatted


def test_phase_health_outcome_rates_report_regressions_and_promotions_per_active_trial(
    tmp_path,
    monkeypatch,
):
    snapshot = tmp_path / "phase.json"
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "trial_id": 10,
                        "timestamp": "2026-07-05T00:10:00+00:00",
                        "action_type": "numeric_trial",
                        "pareto_status": "frontier",
                        "keep_revert_decision": "keep",
                    }
                ),
                json.dumps(
                    {
                        "trial_id": 11,
                        "timestamp": "2026-07-05T00:11:00+00:00",
                        "action_type": "prompt_mutation",
                        "pareto_status": "dominated",
                        "keep_revert_decision": "revert",
                        "deficiency_category": "regression",
                        "failure_analysis": "VIOLATIONS: regression vs baseline",
                    }
                ),
                json.dumps(
                    {
                        "trial_id": 12,
                        "timestamp": "2026-07-05T00:12:00+00:00",
                        "action_type": "structural_experiment",
                        "outcome_status": "invalid",
                        "pareto_status": "dominated",
                        "deficiency_category": "regression",
                    }
                ),
                json.dumps(
                    {
                        "type": "baseline_promotion",
                        "source_trial_id": 11,
                        "timestamp": "2026-07-05T00:13:00+00:00",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 13,
                "action_type": "numeric_trial",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(
        path=snapshot,
        journal_dir=journal_dir,
        recent_window_trials=10,
        now=120.0,
        stale_after_s=60.0,
    )

    rates = report["outcome_progress"]["rates"]
    assert rates["active_trial_count"] == 2
    assert rates["regression_per_active_trial"] == {
        "count": 1,
        "total": 2,
        "rate": 0.5,
    }
    assert rates["promotions_per_100_active_trials"] == {
        "count": 1,
        "total": 2,
        "per_100": 50.0,
    }


def test_phase_health_report_can_block_on_outcome_stall(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    (journal_dir / "autopilot_journal.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "trial_id": trial_id,
                    "timestamp": f"2026-07-05T00:{trial_id:02d}:00+00:00",
                    "action_type": "numeric_trial",
                    "pareto_status": "frontier" if trial_id == 1 else "dominated",
                    "keep_revert_decision": "revert",
                }
            )
            for trial_id in range(1, 13)
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 13,
                "action_type": "numeric_trial",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(
        path=snapshot,
        journal_dir=journal_dir,
        require_outcome_progress=True,
        max_trials_since_frontier=5,
        max_trials_since_promotion=5,
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["ok"] is False
    assert report["status"] == "outcome_stalled"
    assert report["require_outcome_progress"] is True
    assert report["blockers"] == [
        "outcome progress stalled: frontier admission stale: "
        "11 trial(s) since frontier > 5",
        "outcome progress stalled: no baseline promotion observed across "
        "12 trial(s)",
    ]


def test_phase_health_default_runtime_sources_include_planner_and_seeding_modules():
    checked = {path.name for path in phase_status.AUTOPILOT_RUNTIME_SOURCE_PATHS}

    assert "controller_io.py" in checked
    assert "planner_coordinator.py" in checked
    assert "planner_providers.py" in checked
    assert "experiment_journal.py" in checked
    assert "state_store.py" in checked
    assert "seeder.py" in checked
    assert "seeding_eval.py" in checked
    assert "seeding_scoring.py" in checked
    assert "debug_scorer.py" in checked
    assert "strategy_store.py" in checked
    assert "knowledge_distiller.py" in checked
    assert "evolution_manager.py" in checked
    assert "planner_evidence.py" in checked


def test_phase_health_report_exposes_allowlisted_autopilot_env_flags(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 983,
                "action_type": "seed_batch",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr(
        "phase_status._read_process_env_flags",
        lambda pid: {
            "AUTOPILOT_PLANNER_HINTS": "1",
            "AUTOPILOT_SEQ_VERDICT": "1",
            "AUTOPILOT_SEQ_P0_2_BRIDGE": "1",
            "AUTOPILOT_TOOL_SENTINELS": "1",
            "AUTOPILOT_STEPPING_STONES": "1",
            "AUTOPILOT_PLANNER_PRIMARY": "local_ingest",
            "AUTOPILOT_PLANNER_CRITIC": "local_frontdoor",
            "AUTOPILOT_PLANNER_CRITIC_FALLBACK": "claude",
            "AUTOPILOT_PLANNER_SPEND_BREAKER": "0",
            "AUTOPILOT_W6_AUDIT_BLOCK": "1",
            "AUTOPILOT_W6_AUDIT_N": "10",
            "AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS": "1",
            "AUTOPILOT_W6_AUDIT_SHADOW_ONLY": "1",
            "AUTOPILOT_PLANNER_TIMEOUT": "600",
        },
    )

    report = build_phase_health_report(path=snapshot, now=120.0, stale_after_s=60.0)

    assert report["ok"] is True
    assert report["planner_hints_enabled"] is True
    assert report["seq_verdict_enabled"] is True
    assert report["seq_p0_2_bridge_env_enabled"] is True
    assert report["tool_sentinels_enabled"] is True
    assert report["stepping_stones_enabled"] is True
    assert report["planner_primary"] == "local_ingest"
    assert report["planner_critic"] == "local_frontdoor"
    assert report["planner_critic_fallback"] == "claude"
    assert report["planner_spend_breaker_enabled"] is False
    assert report["w6_audit_accrual_enabled"] is True
    assert report["w6_audit_shadow_only"] is True
    assert report["w6_audit_n"] == "10"
    assert report["w6_audit_every_n_trials"] == "1"
    assert report["autopilot_planner_timeout"] == "600"
    assert set(report["autopilot_env_flags"]) == {
        "AUTOPILOT_PLANNER_HINTS",
        "AUTOPILOT_SEQ_VERDICT",
        "AUTOPILOT_SEQ_P0_2_BRIDGE",
        "AUTOPILOT_TOOL_SENTINELS",
        "AUTOPILOT_STEPPING_STONES",
        "AUTOPILOT_PLANNER_PRIMARY",
        "AUTOPILOT_PLANNER_CRITIC",
        "AUTOPILOT_PLANNER_CRITIC_FALLBACK",
        "AUTOPILOT_PLANNER_SPEND_BREAKER",
        "AUTOPILOT_W6_AUDIT_BLOCK",
        "AUTOPILOT_W6_AUDIT_N",
        "AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS",
        "AUTOPILOT_W6_AUDIT_SHADOW_ONLY",
        "AUTOPILOT_PLANNER_TIMEOUT",
    }
    formatted = "\n".join(format_phase_health_report(report))
    assert "Planner hints env: True" in formatted
    assert "Seq verdict env: True" in formatted
    assert "Seq P0.2 bridge env: True" in formatted
    assert "Tool sentinels env: True" in formatted
    assert "Stepping stones env: True" in formatted
    assert "Planner providers: primary=local_ingest, critic=local_frontdoor, fallback=claude" in formatted
    assert "Planner spend breaker env: False" in formatted
    assert "W6 audit env: True (shadow_only=True, n=10, every_n=1)" in formatted
    assert "Planner timeout env: 600" in formatted


def test_phase_health_report_tails_eval_progress_when_heartbeat_lacks_counters(
    tmp_path, monkeypatch
):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 902,
                "action_type": "deep_eval",
                "updated_at": 100.0,
                "updated_at_iso": "2026-06-20T12:13:13+00:00",
            }
        ),
        encoding="utf-8",
    )
    log_path = tmp_path / "autopilot.log"
    log_path.write_text(
        "\n".join(
            [
                '2026-06-20 19:14:09 [autopilot] INFO: Trial 902: {"type": "deep_eval"}',
                "2026-06-20 19:29:11 [autopilot.eval] INFO: T2 progress: 50/500 (78% correct)",
                "2026-06-20 21:43:41 [autopilot.eval] INFO: T2 progress: 400/500 (70% correct)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(
        path=snapshot,
        log_path=log_path,
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["ok"] is True
    assert report["eval_label"] == "T2"
    assert report["eval_completed_questions"] == 400
    assert report["eval_total_questions"] == 500
    assert report["eval_correct_pct"] == 70.0
    assert report["eval_progress_source"] == "log_tail"
    formatted = "\n".join(format_phase_health_report(report))
    assert "Eval progress: 400/500 (70% correct)" in formatted


def test_phase_health_report_tails_t3_eval_progress(tmp_path, monkeypatch):
    """The T3 expert/hard lane emits `T3 progress:` lines — the tail parser must
    pick them up (regression guard for the old `T[12]` hardcode)."""
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 903,
                "action_type": "deep_eval",
                "updated_at": 100.0,
                "updated_at_iso": "2026-07-04T12:13:13+00:00",
            }
        ),
        encoding="utf-8",
    )
    log_path = tmp_path / "autopilot.log"
    log_path.write_text(
        "\n".join(
            [
                '2026-07-04 19:14:09 [autopilot] INFO: Trial 903: {"type": "deep_eval"}',
                "2026-07-04 19:29:11 [autopilot.eval] INFO: T3 progress: 40/160 (55% correct)",
                "2026-07-04 21:43:41 [autopilot.eval] INFO: T3 progress: 120/160 (58% correct)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(
        path=snapshot,
        log_path=log_path,
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["ok"] is True
    assert report["eval_label"] == "T3"
    assert report["eval_completed_questions"] == 120
    assert report["eval_total_questions"] == 160
    assert report["eval_correct_pct"] == 58.0
    assert report["eval_progress_source"] == "log_tail"


def test_phase_health_report_tails_numeric_trial_progress_from_recent_tmp_log(
    tmp_path, monkeypatch
):
    snapshot = tmp_path / "autopilot_phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 916,
                "action_type": "numeric_trial",
                "updated_at": 100.0,
                "updated_at_iso": "2026-06-21T03:33:26+00:00",
            }
        ),
        encoding="utf-8",
    )
    default_log = tmp_path / "logs" / "autopilot.log"
    default_log.parent.mkdir()
    default_log.write_text(
        "\n".join(
            [
                '2026-06-21 03:22:19 [autopilot] INFO: Trial 915: {"type": "seed_batch"}',
                "2026-06-21 03:22:18 [autopilot.eval] INFO: T1 progress: 60/60 (67% correct)",
            ]
        ),
        encoding="utf-8",
    )
    tmp_log_dir = tmp_path / "tmp"
    tmp_log_dir.mkdir()
    redirected_log = tmp_log_dir / "autopilot_w4w6_codex_pair.log"
    redirected_log.write_text(
        "\n".join(
            [
                '2026-06-21 03:22:56 [autopilot] INFO: Trial 916: {"type": "numeric_trial"}',
                "2026-06-21 03:27:14 [autopilot.eval] INFO: T1 progress: 10/60 (100% correct)",
                "2026-06-21 03:33:26 [autopilot.eval] INFO: T1 progress: 40/60 (70% correct)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr("phase_status.PHASE_PATH", snapshot)
    monkeypatch.setattr("phase_status.DEFAULT_AUTOPILOT_LOG_PATH", default_log)
    monkeypatch.setattr("phase_status.DEFAULT_TMP_AUTOPILOT_LOG_DIR", tmp_log_dir)

    report = build_phase_health_report(path=snapshot, now=120.0, stale_after_s=60.0)

    assert report["ok"] is True
    assert report["action_type"] == "numeric_trial"
    assert report["eval_label"] == "T1"
    assert report["eval_completed_questions"] == 40
    assert report["eval_total_questions"] == 60
    assert report["eval_correct_pct"] == 70.0
    assert report["eval_progress_source"] == "log_tail"
    assert report["eval_progress_log_path"] == str(redirected_log)


def test_phase_health_report_does_not_tail_other_trial_progress(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 903,
                "action_type": "deep_eval",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    log_path = tmp_path / "autopilot.log"
    log_path.write_text(
        "\n".join(
            [
                '2026-06-20 19:14:09 [autopilot] INFO: Trial 902: {"type": "deep_eval"}',
                "2026-06-20 21:43:41 [autopilot.eval] INFO: T2 progress: 400/500 (70% correct)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(
        path=snapshot,
        log_path=log_path,
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["ok"] is True
    assert report["eval_completed_questions"] is None
    assert report.get("eval_progress_source") is None


def test_phase_health_report_keeps_heartbeat_eval_progress_over_log_tail(
    tmp_path, monkeypatch
):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "dispatch_action",
                "pid": 123,
                "trial_id": 902,
                "action_type": "deep_eval",
                "eval_label": "T1",
                "eval_completed_questions": 10,
                "eval_total_questions": 60,
                "eval_correct_pct": 100.0,
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    log_path = tmp_path / "autopilot.log"
    log_path.write_text(
        "\n".join(
            [
                '2026-06-20 19:14:09 [autopilot] INFO: Trial 902: {"type": "deep_eval"}',
                "2026-06-20 21:43:41 [autopilot.eval] INFO: T2 progress: 400/500 (70% correct)",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(
        path=snapshot,
        log_path=log_path,
        now=120.0,
        stale_after_s=60.0,
    )

    assert report["eval_label"] == "T1"
    assert report["eval_completed_questions"] == 10
    assert report["eval_total_questions"] == 60
    assert report["eval_correct_pct"] == 100.0
    assert report.get("eval_progress_source") is None


def test_phase_health_report_blocks_stale_heartbeat(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps({"phase": "dispatch_action", "pid": 123, "updated_at": 100.0}),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)

    report = build_phase_health_report(path=snapshot, now=1001.0, stale_after_s=900.0)

    assert report["ok"] is False
    assert report["status"] == "stale"
    assert report["blockers"] == ["phase heartbeat is stale: 901.0s > 900.0s"]


def test_phase_health_report_blocks_dead_pid(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps({"phase": "dispatch_action", "pid": 123, "updated_at": 100.0}),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: False)

    report = build_phase_health_report(path=snapshot, now=120.0, stale_after_s=900.0)

    assert report["ok"] is False
    assert report["status"] == "pid_dead"
    assert report["blockers"] == ["phase heartbeat pid is not alive: 123"]


def test_phase_health_report_accepts_stopped_dead_pid(tmp_path, monkeypatch):
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "stopped",
                "pid": 123,
                "reason": "autopilot process exiting",
                "updated_at": 100.0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: False)

    report = build_phase_health_report(path=snapshot, now=5000.0, stale_after_s=900.0)

    assert report["ok"] is True
    assert report["status"] == "stopped"
    assert report["pid_alive"] is False
    assert report["blockers"] == []


def test_phase_health_report_handles_missing_file(tmp_path):
    report = build_phase_health_report(
        path=tmp_path / "missing.json",
        now=120.0,
        stale_after_s=900.0,
    )

    assert report["ok"] is False
    assert report["status"] == "missing"
    assert "missing or unreadable" in report["blockers"][0]


# ── Orchestrator health-check escalation ────────────────────────────────────
# The retry branch in autopilot._run_loop_inner sleeps and continues forever on a
# dead API (operator ruling 2026-08-12: keep retrying, do NOT latch off). These
# pin the "loud" half of that bargain.


class _FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _tracker(escalate_after: int = 30, clock=None):
    from phase_status import HealthEscalationTracker

    return HealthEscalationTracker(escalate_after=escalate_after, now=clock or _FakeClock())


def test_health_escalation_does_not_fire_below_threshold():
    tracker = _tracker(escalate_after=30)

    updates = [tracker.record_failure() for _ in range(29)]

    assert all(not u.escalated_now for u in updates)
    assert all(not u.escalated for u in updates)
    assert tracker.consecutive == 29
    assert tracker.escalated is False
    assert updates[-1].phase_fields["health_escalated"] is False
    assert updates[-1].phase_fields["health_consecutive_failures"] == 29


def test_health_escalation_fires_at_threshold():
    clock = _FakeClock()
    tracker = _tracker(escalate_after=30, clock=clock)

    for _ in range(29):
        tracker.record_failure()
        clock.advance(12.0)
    assert tracker.escalated is False

    update = tracker.record_failure()

    assert update.escalated_now is True
    assert update.escalated is True
    assert update.consecutive == 30
    assert tracker.escalated is True
    assert update.phase_fields["health_escalated"] is True
    assert update.phase_fields["health_escalate_after"] == 30
    # 29 failures * 12s of wall clock elapsed before the 30th.
    assert update.unhealthy_for_s == 348.0
    assert "30 consecutive health checks" in update.message


def test_health_escalation_fires_once_not_every_iteration():
    tracker = _tracker(escalate_after=5)

    updates = [tracker.record_failure() for _ in range(40)]

    fired = [i for i, u in enumerate(updates) if u.escalated_now]
    assert fired == [4], "escalation must be edge-triggered, once per episode"
    # It stays escalated for the rest of the episode even though it stops shouting.
    assert all(u.escalated for u in updates[4:])
    assert all(u.message == "" for u in updates[5:])


def test_health_escalation_clears_on_recovery():
    clock = _FakeClock()
    tracker = _tracker(escalate_after=5, clock=clock)
    for _ in range(7):
        tracker.record_failure()
        clock.advance(12.0)
    assert tracker.escalated is True

    recovery = tracker.record_success()

    assert recovery is not None
    assert recovery.recovered is True
    assert tracker.escalated is False
    assert tracker.consecutive == 0
    assert tracker.first_failure_at is None
    assert recovery.phase_fields["health_escalated"] is False
    assert recovery.phase_fields["health_escalation_cleared"] is True
    assert recovery.phase_fields["health_recovered_after_failures"] == 7
    assert "RECOVERED" in recovery.message


def test_health_escalation_recovery_is_silent_when_nothing_was_wrong():
    tracker = _tracker(escalate_after=5)

    # The healthy steady state must not publish a recovery event every iteration.
    assert tracker.record_success() is None
    assert tracker.record_success() is None


def test_health_escalation_recovery_below_threshold_clears_without_alarm():
    tracker = _tracker(escalate_after=30)
    for _ in range(3):
        tracker.record_failure()

    recovery = tracker.record_success()

    assert recovery is not None
    assert recovery.recovered is False, "never escalated, so nothing to retract"
    assert recovery.message == ""
    assert "health_escalation_cleared" not in recovery.phase_fields
    assert tracker.consecutive == 0


def test_health_escalation_rearms_for_a_second_episode():
    tracker = _tracker(escalate_after=3)
    for _ in range(3):
        tracker.record_failure()
    tracker.record_success()

    second = [tracker.record_failure() for _ in range(3)]

    assert [u.escalated_now for u in second] == [False, False, True]


def _escalated_heartbeat(**overrides):
    payload = {
        "phase": "health_backoff",
        "pid": 123,
        "trial_id": 894,
        "idle_reason": "orchestrator unhealthy",
        "failure_reason": "connection_refused",
        "health_consecutive_failures": 30,
        "health_escalate_after": 30,
        "health_unhealthy_for_s": 361.4,
        "health_escalated": True,
        "updated_at": 100.0,
        "updated_at_iso": "2026-08-12T12:13:13+00:00",
    }
    payload.update(overrides)
    return payload


def test_phase_health_report_flags_an_escalated_spin(tmp_path, monkeypatch):
    """A fresh heartbeat is not proof of progress when the loop is retrying."""
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(json.dumps(_escalated_heartbeat()), encoding="utf-8")
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr("phase_status._read_process_env_flags", lambda pid: {})

    report = build_phase_health_report(path=snapshot, now=120.0, stale_after_s=60.0)

    assert report["ok"] is False
    assert report["status"] == "health_escalated"
    assert report["health_escalated"] is True
    assert report["health_consecutive_failures"] == 30
    blocker = "\n".join(report["blockers"])
    assert "orchestrator health-check escalated" in blocker
    assert "30 consecutive failures" in blocker
    assert "connection_refused" in blocker
    formatted = "\n".join(format_phase_health_report(report))
    assert "Status: health_escalated" in formatted
    assert "Health escalation: True" in formatted


def test_phase_health_report_stays_active_while_below_threshold(tmp_path, monkeypatch):
    """Retrying is normal; only the escalation is an alarm."""
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            _escalated_heartbeat(health_escalated=False, health_consecutive_failures=4)
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr("phase_status._read_process_env_flags", lambda pid: {})

    report = build_phase_health_report(path=snapshot, now=120.0, stale_after_s=60.0)

    assert report["ok"] is True
    assert report["status"] == "active"
    assert report["health_escalated"] is False
    assert not report["blockers"]


def test_phase_health_report_clears_once_the_loop_publishes_recovery(tmp_path, monkeypatch):
    """The alarm must visibly reset, or nobody trusts it."""
    snapshot = tmp_path / "phase.json"
    snapshot.write_text(
        json.dumps(
            {
                "phase": "health_recovered",
                "pid": 123,
                "trial_id": 894,
                "health_consecutive_failures": 0,
                "health_escalated": False,
                "health_escalation_cleared": True,
                "health_recovered_after_failures": 31,
                "updated_at": 100.0,
                "updated_at_iso": "2026-08-12T12:20:13+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase_status._process_exists", lambda pid: True)
    monkeypatch.setattr("phase_status._read_process_env_flags", lambda pid: {})

    report = build_phase_health_report(path=snapshot, now=120.0, stale_after_s=60.0)

    assert report["ok"] is True
    assert report["status"] == "active"
    assert report["health_escalated"] is False
    assert not report["blockers"]


def test_phase_tracker_publishes_escalation_fields_the_report_reads(tmp_path):
    """Producer/reader contract: the field names must actually line up."""
    from phase_status import HealthEscalationTracker

    snapshot = tmp_path / "phase.json"
    events = tmp_path / "phase.jsonl"
    tracker = PhaseTracker(path=snapshot, events_path=events)
    escalation = HealthEscalationTracker(escalate_after=2, now=_FakeClock())
    escalation.record_failure()
    update = escalation.record_failure()
    assert update.escalated_now is True

    tracker.set(
        "health_backoff",
        trial_id=894,
        failure_reason="connection_refused",
        **update.phase_fields,
    )
    report = build_phase_health_report(
        path=snapshot,
        now=json.loads(snapshot.read_text())["updated_at"] + 1.0,
        stale_after_s=60.0,
    )

    assert report["status"] == "health_escalated"
    assert report["ok"] is False


# ── Loop wiring ─────────────────────────────────────────────────────────────
# The tracker above is only useful if autopilot._run_loop_inner actually drives
# it. That function is a ~2000-line loop that cannot be invoked in a unit test,
# so the call sites are pinned by source inspection. Without these, deleting the
# record_failure() call restores the original silent spin with every other test
# in this file still green.


def _autopilot_module():
    import autopilot

    return autopilot


def test_autopilot_loop_uses_the_shared_escalation_tracker():
    import phase_status as ps

    autopilot = _autopilot_module()

    assert autopilot.HealthEscalationTracker is ps.HealthEscalationTracker
    assert autopilot.HEALTH_ESCALATE_AFTER == ps.DEFAULT_HEALTH_ESCALATE_AFTER == 30


def test_autopilot_health_escalate_after_is_env_overridable(monkeypatch):
    autopilot = _autopilot_module()

    monkeypatch.setenv("AUTOPILOT_HEALTH_ESCALATE_AFTER", "7")
    assert autopilot._env_int("AUTOPILOT_HEALTH_ESCALATE_AFTER", 30) == 7
    # A nonsense value must not disable the alarm by making it unreachable.
    monkeypatch.setenv("AUTOPILOT_HEALTH_ESCALATE_AFTER", "nonsense")
    assert autopilot._env_int("AUTOPILOT_HEALTH_ESCALATE_AFTER", 30) == 30
    monkeypatch.setenv("AUTOPILOT_HEALTH_ESCALATE_AFTER", "0")
    assert autopilot._env_int("AUTOPILOT_HEALTH_ESCALATE_AFTER", 30) == 1


def test_autopilot_retry_branch_drives_the_escalation_tracker():
    import inspect

    autopilot = _autopilot_module()
    source = inspect.getsource(autopilot._run_loop_inner)

    assert "HealthEscalationTracker(escalate_after=HEALTH_ESCALATE_AFTER)" in source
    assert "health_escalation.record_failure()" in source
    assert "health_escalation.record_success()" in source
    # The escalation must reach the heartbeat, which is the only thing the
    # dashboard and the restart advisor can see.
    assert "**_escalation.phase_fields" in source
    assert "**_recovery.phase_fields" in source


def test_autopilot_retry_branch_still_retries_forever():
    """Operator ruling 2026-08-12: escalate loudly, do NOT latch off."""
    import inspect

    autopilot = _autopilot_module()
    source = inspect.getsource(autopilot._run_loop_inner)
    branch = source.split("Orchestrator unhealthy")[1].split("# Check preflight")[0]

    assert "time.sleep(HEALTH_BACKOFF_S)" in branch
    assert "continue" in branch
    # No halt latch, no self-pause, no exit on the health path.
    assert 'state["paused"] = True' not in branch
    assert "_dispatch_deficiency" not in branch
    assert "break" not in branch
    assert "sys.exit" not in branch
