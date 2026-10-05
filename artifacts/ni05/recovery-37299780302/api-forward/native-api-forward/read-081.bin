"""HLE-4 observe-only metric plumbing tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from safety_gate import EvalResult  # noqa: E402


def test_eval_result_carries_hle_observe_only_fields() -> None:
    result = EvalResult(
        tier=1,
        quality=0.75,
        speed=20.0,
        cost=0.2,
        reliability=0.95,
        core_id="core_v2",
        metric_schema_version=1,
        harness_metrics={
            "execution_fidelity": {
                "score": 0.8,
                "evidence_event_ids": [101, 102],
                "confidence": 0.7,
            }
        },
        oracle_adequacy={
            "sentinel_python": {
                "oracle_type": "unit_test",
                "deterministic": True,
                "known_blind_spots": ["does_not_check_latency"],
            }
        },
    )

    assert result.metric_schema_version == 1
    assert result.core_id == "core_v2"
    assert result.harness_metrics["execution_fidelity"]["score"] == 0.8
    assert result.oracle_adequacy["sentinel_python"]["deterministic"] is True


def test_eval_result_grep_lines_emit_core_id() -> None:
    result = EvalResult(
        tier=1,
        quality=0.75,
        speed=20.0,
        cost=0.2,
        reliability=0.95,
        core_id="core_v2",
    )

    assert "METRIC core_id: core_v2" in result.to_grep_lines()


def test_eval_result_grep_lines_emit_report_only_rlvr_reward() -> None:
    # FULL provenance is now TWO stamps, not one:
    #   * EV-CONF (audit, 2026-07-21): calibration+discrimination require
    #     details['confidence_is_real']=True.
    #   * ESC-7 Option A (operator-granted 2026-07-23): they are additionally
    #     decision-capable for the CODE domain only, read from
    #     details['scoring_method'] — math geomean confidence measured
    #     ANTI-discriminative (AUROC 0.401/0.411 across both E7c arms, length
    #     confounding), so non-code rows stay observational.
    # With both stamps the full composition reproduces the original 0.8375:
    #   0.65*0.8(acc) + 0.20*0.9(rel) + 0.10*0.95(cal) + 0.05*0.85(disc)
    result = EvalResult(
        tier=1,
        quality=2.4,
        speed=20.0,
        cost=0.2,
        reliability=0.9,
        ece=0.05,
        auroc=0.85,
        details={"confidence_is_real": True, "scoring_method": "code_execution"},
    )

    lines = result.to_grep_lines()

    assert "METRIC rlvr_policy: ap27_rlvr_tier_reward_v1" in lines
    assert "METRIC rlvr_signal: calibrated_continuous" in lines
    assert "METRIC rlvr_reward: 0.837500" in lines
    assert "METRIC rlvr_ready: 1" in lines
    assert "METRIC rlvr_blockers:" not in lines


def test_eval_result_grep_lines_rlvr_zeroes_calibration_outside_the_code_domain() -> None:
    # ESC-7 Option A, the half nothing covered: confidence provenance is REAL
    # but the row was scored by a non-code method, so calibration AND
    # discrimination are zeroed and the row is observational-only. Same fixture
    # as above minus the code-domain stamp -> the 0.095+0.0425 calibration and
    # discrimination credit disappears and 0.8375 drops to 0.70.
    result = EvalResult(
        tier=1,
        quality=2.4,
        speed=20.0,
        cost=0.2,
        reliability=0.9,
        ece=0.05,
        auroc=0.85,
        details={"confidence_is_real": True, "scoring_method": "llm_judge"},
    )

    lines = result.to_grep_lines()

    assert "METRIC rlvr_reward: 0.700000" in lines
    assert "METRIC rlvr_ready: 0" in lines
    assert "METRIC rlvr_blockers: calibration_domain_observational" in lines


def test_eval_result_grep_lines_rlvr_fails_closed_without_confidence_provenance() -> None:
    # Same fixture WITHOUT the provenance flag: calibration+discrimination are
    # zeroed (0.65*acc + 0.20*rel only) and the confidence_not_real blocker
    # emits — stub/legacy rows can never earn calibration credit (EV-CONF).
    result = EvalResult(
        tier=1,
        quality=2.4,
        speed=20.0,
        cost=0.2,
        reliability=0.9,
        ece=0.05,
        auroc=0.85,
    )

    lines = result.to_grep_lines()

    assert "METRIC rlvr_reward: 0.700000" in lines
    assert "METRIC rlvr_ready: 0" in lines
    assert "METRIC rlvr_blockers: confidence_not_real" in lines


def test_journal_round_trips_hle_fields_in_jsonl(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    entry = JournalEntry(
        trial_id=7,
        timestamp="2026-05-27T00:00:00Z",
        species="hle-observe",
        action_type="observe_only",
        tier=1,
        quality=0.75,
        speed=20.0,
        cost=0.2,
        reliability=0.95,
        pareto_status="candidate",
        eval_details={
            "question_results": [
                {
                    "qid": "q-stable",
                    "suite": "general",
                    "correct": True,
                    "latency_ms": 123,
                    "tools_used": 0,
                }
            ]
        },
        metric_schema_version=1,
        harness_metrics={"planning_stability": {"score": 0.6, "evidence_event_ids": [42]}},
        oracle_adequacy={
            "coding_sentinel": {"oracle_type": "pytest", "deterministic": True},
            "control_attestation": {
                "metric_version": "w5-control-pair-report-v1",
                "observe_only": True,
                "status": "passed",
            },
        },
        seq={
            "candidate": "fp-a",
            "core_id": "core_v1",
            "z": 0.25,
            "z_rate": 0.1,
            "state": "accumulating",
            "policy_version": "seq-v1",
        },
    )

    journal.record(entry)

    raw = json.loads((tmp_path / "autopilot_journal.jsonl").read_text().splitlines()[0])
    assert raw["metric_schema_version"] == 1
    assert raw["eval_details"]["question_results"][0]["qid"] == "q-stable"
    assert raw["harness_metrics"]["planning_stability"]["score"] == 0.6
    assert raw["oracle_adequacy"]["coding_sentinel"]["oracle_type"] == "pytest"
    assert raw["oracle_adequacy"]["control_attestation"]["status"] == "passed"
    assert raw["seq"]["candidate"] == "fp-a"
    assert raw["seq"]["z_rate"] == 0.1

    reloaded = ExperimentJournal(journal_dir=tmp_path)
    loaded = reloaded.all_entries()[0]
    assert loaded.metric_schema_version == 1
    assert loaded.harness_metrics == entry.harness_metrics
    assert loaded.oracle_adequacy == entry.oracle_adequacy
    assert loaded.eval_details["question_results"][0]["qid"] == "q-stable"
    assert loaded.seq == entry.seq


def test_journal_loads_hle_fields_from_legacy_eval_details(tmp_path: Path) -> None:
    (tmp_path / "autopilot_journal.jsonl").write_text(
        json.dumps(
            {
                "trial_id": 3,
                "timestamp": "2026-05-27T00:00:00Z",
                "species": "legacy",
                "action_type": "observe_only",
                "tier": 1,
                "quality": 0.5,
                "speed": 10.0,
                "cost": 0.4,
                "reliability": 0.9,
                "pareto_status": "dominated",
                "eval_details": {
                    "metric_schema_version": 1,
                    "harness_metrics": {"memory_coherence": {"score": 0.9}},
                    "oracle_adequacy": {"qa": {"oracle_type": "exact_match"}},
                },
            }
        )
        + "\n"
    )

    loaded = ExperimentJournal(journal_dir=tmp_path).all_entries()[0]

    assert loaded.metric_schema_version == 1
    assert loaded.harness_metrics == {"memory_coherence": {"score": 0.9}}
    assert loaded.oracle_adequacy == {"qa": {"oracle_type": "exact_match"}}
