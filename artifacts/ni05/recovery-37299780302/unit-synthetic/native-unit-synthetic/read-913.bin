from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.autopilot import w8_promotion_trajectory_report


def _row(
    trial_id: int,
    candidate: str,
    *,
    action_type: str = "numeric_trial",
    config_snapshot: dict | None = None,
    combined: float = 0.95,
    e_quality: float = 1.1,
    state: str = "accumulating",
    k: int = 1,
    fresh_eval: bool = False,
    confirmed: bool = False,
    finalized: bool = False,
    keep_revert_decision: str = "",
    failure_analysis: str = "",
) -> dict:
    if config_snapshot is None:
        if action_type == "numeric_trial":
            config_snapshot = {
                "type": "numeric_trial",
                "surface": "monitor",
                "params": {"temperature": 0.7},
            }
        elif action_type == "structural_experiment":
            config_snapshot = {"type": "structural_experiment", "flags": {"x": True}}
        else:
            config_snapshot = {"type": action_type}
    return {
        "trial_id": trial_id,
        "action_type": action_type,
        "config_snapshot": config_snapshot,
        "quality": 2.1,
        "keep_revert_decision": keep_revert_decision,
        "failure_analysis": failure_analysis,
        "seq": {
            "candidate": candidate,
            "state": state,
            "confirmed": confirmed,
            "baseline_promotion_combined_E": combined,
            "baseline_promotion_required_E": 100.0,
            "baseline_promotion_fresh_eval": fresh_eval,
            "baseline_promotion_finalized": finalized,
            "baseline_reference_state": "fresh",
            "E_quality": e_quality,
            "E_rate_noninf": combined,
            "k": k,
            "r_eff": 30,
        },
    }


def test_report_identifies_recent_replay_progress() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(10, "candidate-a", combined=0.91, k=1),
            _row(12, "candidate-a", combined=0.93, k=2),
            _row(13, "candidate-b", combined=0.88, k=1),
        ],
        stale_trials=3,
    )

    assert report["status"] == "progressing"
    assert report["ok"] is True
    assert report["recent_active_candidates"] == ["candidate-a"]
    assert report["replay_eligible_candidates"] == ["candidate-a"]
    assert report["recent_replay_eligible_candidates"] == ["candidate-a"]
    trajectory = report["trajectories"][0]
    assert trajectory["candidate"] == "candidate-a"
    assert trajectory["status"] == "active_recent_replay"
    assert trajectory["replay_eligible"] is True
    assert trajectory["replay_blocker"] is None
    assert trajectory["attempts"] == 2
    assert trajectory["combined_E_delta"] == 0.02
    assert report["replay_concentration"]["warning"] is False


def test_report_flags_stale_accumulating_candidates() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(1, "candidate-a", combined=0.91, k=1),
            _row(20, "candidate-b", combined=0.92, state="refuted", k=12),
        ],
        stale_trials=5,
    )

    assert report["status"] == "stale_accumulating"
    assert report["ok"] is False
    assert report["stale_accumulating_candidates"] == ["candidate-a"]
    assert "stale_accumulating_candidates_present" in report["open_requirements"]
    assert (
        "no_recent_replay_eligible_accumulating_candidate"
        in report["open_requirements"]
    )


def test_report_flags_concentrated_replay_attempts() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(1, "stale-a", combined=0.91, k=1),
            _row(10, "candidate-a", combined=0.91, k=1),
            _row(12, "candidate-a", combined=0.92, k=2),
            _row(13, "candidate-a", combined=0.93, k=3),
        ],
        stale_trials=4,
    )

    concentration = report["replay_concentration"]
    assert report["status"] == "progressing"
    assert concentration["warning"] is True
    assert concentration["top_active_candidate"] == "candidate-a"
    assert concentration["top_active_attempt_share"] == 1.0
    assert concentration["stale_accumulating_count"] == 1
    assert "replay_concentration_warning" in report["open_requirements"]
    assert "Replay Concentration" in w8_promotion_trajectory_report.render_markdown(report)


def test_report_flags_active_recent_but_no_replay_eligible_candidates() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(10, "candidate-a", combined=0.91, e_quality=0.99, k=1),
            _row(12, "candidate-a", combined=0.93, e_quality=0.99, k=2),
            _row(13, "candidate-b", action_type="seed_batch", combined=0.95, k=2),
            _row(14, "candidate-b", action_type="seed_batch", combined=0.96, k=3),
        ],
        stale_trials=5,
    )

    assert report["status"] == "evidence_bound"
    assert report["ok"] is False
    assert report["recent_active_candidates"] == ["candidate-b", "candidate-a"]
    assert report["replay_eligible_candidates"] == []
    assert report["recent_replay_eligible_candidates"] == []
    assert report["replay_blockers"] == {
        "candidate-a": "E_quality_below_replay_floor",
        "candidate-b": "unreplayable_action=seed_batch",
    }
    assert "no_replay_eligible_accumulating_candidate" in report["open_requirements"]
    markdown = w8_promotion_trajectory_report.render_markdown(report)
    assert "Replay eligibility" in markdown
    assert "E_quality_below_replay_floor" in markdown
    assert "unreplayable_action=seed_batch" in markdown


def test_report_rejects_empty_numeric_trial_params_as_unreplayable() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(
                10,
                "candidate-a",
                config_snapshot={
                    "type": "numeric_trial",
                    "surface": "monitor",
                    "params": {},
                },
                combined=0.95,
                k=3,
            )
        ],
        stale_trials=5,
    )

    assert report["status"] == "evidence_bound"
    assert report["replay_eligible_candidates"] == []
    assert report["replay_blockers"] == {
        "candidate-a": "candidate numeric_trial lacks replayable applied params"
    }
    assert "no_replay_eligible_accumulating_candidate" in report["open_requirements"]


def test_report_accepts_materialized_multi_param_numeric_candidate() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(
                10,
                "candidate-optuna",
                config_snapshot={
                    "type": "numeric_trial",
                    "surface": "memrl_retrieval",
                    "params": {
                        "memrl_retrieval.q_weight": 0.61,
                        "memrl_retrieval.semantic_k": 25,
                        "memrl_retrieval.prior_strength": 0.43,
                    },
                },
                combined=0.95,
                e_quality=1.05,
                k=2,
            )
        ],
        stale_trials=5,
    )

    assert report["status"] == "progressing"
    assert report["replay_eligible_candidates"] == ["candidate-optuna"]
    assert report["recent_replay_eligible_candidates"] == ["candidate-optuna"]
    assert report["replay_blockers"] == {}
    assert "no_replay_eligible_accumulating_candidate" not in report["open_requirements"]


def test_report_does_not_treat_unreplayable_old_numeric_candidate_as_stale() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(
                1,
                "old-unreplayable",
                config_snapshot={
                    "type": "numeric_trial",
                    "surface": "monitor",
                    "params": {},
                },
                combined=0.95,
                k=1,
            ),
            _row(20, "current-replayable", combined=0.91, k=1),
        ],
        stale_trials=5,
    )

    assert report["status"] == "progressing"
    assert report["ok"] is True
    assert report["replay_eligible_candidates"] == ["current-replayable"]
    assert report["recent_replay_eligible_candidates"] == ["current-replayable"]
    assert report["stale_accumulating_candidates"] == []
    assert "stale_accumulating_candidates_present" not in report["open_requirements"]
    assert "replay_concentration_warning" not in report["open_requirements"]
    assert report["replay_concentration"]["warning"] is False
    assert report["replay_blockers"] == {
        "old-unreplayable": "candidate numeric_trial lacks replayable applied params"
    }


def test_report_excludes_latest_reverted_candidate_from_active_replay() -> None:
    violation = (
        "VIOLATIONS:\n"
        "  - Suite 'general' regression: -1.800 "
        "(threshold: -1.500; n_result=5, n_baseline=2)"
    )
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(10, "candidate-a", combined=0.91, k=1),
            _row(
                12,
                "candidate-a",
                combined=0.93,
                k=2,
                keep_revert_decision="revert",
                failure_analysis=violation,
            ),
            _row(
                11,
                "candidate-c",
                combined=0.92,
                k=1,
                keep_revert_decision="revert",
                failure_analysis=violation,
            ),
            _row(13, "candidate-b", combined=0.88, state="refuted", k=12),
        ],
        stale_trials=5,
    )

    statuses = {item["candidate"]: item["status"] for item in report["trajectories"]}
    assert statuses["candidate-a"] == "reverted"
    assert report["recent_active_candidates"] == []
    assert report["status_counts"]["reverted"] == 2
    dominant = report["dominant_terminal_reason"]
    assert dominant["reason"] == (
        "Suite 'general' regression: -1.800 "
        "(threshold: -1.500; n_result=5, n_baseline=2)"
    )
    assert dominant["details"] == {
        "kind": "suite_regression",
        "suite": "general",
        "delta": -1.8,
        "threshold": -1.5,
        "n_result": 5,
        "n_baseline": 2,
    }
    assert dominant["baseline_sample_warning"] is True
    assert "Terminal Candidate Reasons" in w8_promotion_trajectory_report.render_markdown(
        report
    )
    assert "no_recent_multi_observation_accumulating_candidate" in report[
        "open_requirements"
    ]


def test_report_counts_benign_seq_accumulating_exclusion_as_active_replay() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(20, "candidate-a", combined=0.91, k=1),
            _row(
                21,
                "candidate-a",
                combined=0.92,
                k=2,
                keep_revert_decision="excluded",
            ),
        ],
        stale_trials=5,
    )

    assert report["status"] == "progressing"
    assert report["ok"] is True
    assert report["recent_active_candidates"] == ["candidate-a"]
    trajectory = report["trajectories"][0]
    assert trajectory["status"] == "active_recent_replay"
    assert trajectory["latest_keep_revert_decision"] == "excluded"
    assert "no_recent_multi_observation_accumulating_candidate" not in report[
        "open_requirements"
    ]


def test_report_classifies_refuted_and_finalized_candidates() -> None:
    report = w8_promotion_trajectory_report.build_w8_trajectory_report(
        [
            _row(1, "candidate-a", state="refuted", k=12),
            _row(2, "candidate-b", state="confirmed", confirmed=True, finalized=True),
        ]
    )

    statuses = {item["candidate"]: item["status"] for item in report["trajectories"]}
    assert statuses == {
        "candidate-a": "refuted",
        "candidate-b": "finalized",
    }


def test_main_writes_json_and_markdown_outputs(tmp_path: Path, capsys) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    journal.write_text(
        "\n".join(
            [
                json.dumps(_row(10, "candidate-a", combined=0.91, k=1)),
                json.dumps(_row(11, "candidate-a", combined=0.92, k=2)),
            ]
        )
        + "\n"
    )
    out_json = tmp_path / "reports" / "w8.json"
    out_md = tmp_path / "reports" / "w8.md"

    code = w8_promotion_trajectory_report.main(
        [
            "--journal",
            str(journal),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
            "--strict",
        ]
    )

    assert code == 0
    stdout = capsys.readouterr().out
    assert "Status: progressing" in stdout
    assert json.loads(out_json.read_text())["status"] == "progressing"
    assert "candidate-a" in out_md.read_text()


def test_direct_cli_execution_from_repo_root(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    journal.write_text(
        json.dumps(_row(1, "candidate-a", k=1))
        + "\n"
        + json.dumps(_row(2, "candidate-a", k=2))
        + "\n"
    )
    repo_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [
            sys.executable,
            "scripts/autopilot/w8_promotion_trajectory_report.py",
            "--journal",
            str(journal),
            "--json",
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )

    report = json.loads(result.stdout)
    assert report["candidate_count"] == 1
    assert report["status"] == "progressing"
