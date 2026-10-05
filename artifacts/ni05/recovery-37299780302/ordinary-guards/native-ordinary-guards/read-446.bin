"""Tests for append-only AutoPilot journal supersession events."""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(AUTOPILOT_DIR))

from experiment_journal import (
    BASELINE_PROMOTION_EVENT_TYPE,
    ExperimentJournal,
    JOURNAL_SNAPSHOT_EVENT_TYPE,
    JournalEntry,
    ROLE_RESTART_BOUNDARY_EVENT_TYPE,
)
from src.autopilot_core.journal_reconstruction import reconstruct_archive_from_journal_rows


def _entry(trial_id: int) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp=f"2026-06-13T00:00:{trial_id:02d}+00:00",
        species="seeder",
        action_type="seed_batch",
        tier=1,
        quality=1.0,
        speed=10.0,
        cost=0.5,
        reliability=1.0,
        pareto_status="dominated",
    )


def test_supersession_event_round_trips_without_counting_as_trial(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))

    event = journal.append_supersession_event(
        target_trial_ids=[1],
        fields={"bug_corrupted_by": "abc123"},
        reason="test event",
        policy_version="supersession-v1",
        actor="unit-test",
    )

    assert event["type"] == "supersession"
    assert journal.count() == 1
    assert journal.next_trial_id() == 2

    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.count() == 1
    assert reloaded.next_trial_id() == 2
    assert reloaded.supersession_events() == [event]


def test_baseline_promotion_event_round_trips_without_counting_as_trial(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(7))

    event = journal.append_baseline_promotion_event(
        source_trial_id=7,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="test promotion",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8, "speed": 42.0},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )

    assert event["type"] == BASELINE_PROMOTION_EVENT_TYPE
    assert event["source_trial_id"] == 7
    assert event["baseline_state"]["baselines_by_tier"]["1"] == 1.8
    assert journal.count() == 1
    assert journal.next_trial_id() == 8

    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.count() == 1
    assert reloaded.next_trial_id() == 8
    assert reloaded.baseline_promotion_events() == [event]
    assert reloaded.ledger_events(BASELINE_PROMOTION_EVENT_TYPE) == [event]
    assert reloaded.supersession_events() == []


def test_baseline_promotion_event_does_not_affect_archive_reconstruction(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))
    journal.append_baseline_promotion_event(
        source_trial_id=1,
        tier=1,
        previous_quality=0.8,
        new_quality=1.0,
        reason="test promotion",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.0},
        baseline_state={"baselines_by_tier": {"1": 1.0}},
        actor="unit-test",
    )
    rows = [asdict(entry) for entry in journal.all_entries()]
    rows.extend(journal.ledger_events())

    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)

    assert archive is not None
    assert [entry["trial_id"] for entry in archive["all_entries"]] == [1]
    assert archive["supersessions"] == {
        "events_applied": 0,
        "target_trial_ids": [],
        "field_names": [],
    }


def test_journal_snapshot_event_round_trips_without_counting_as_trial(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(9))
    snapshot = {
        "archive": {"frontier": [9]},
        "baseline": {"baselines_by_tier": {"1": 1.8}},
    }

    event = journal.append_journal_snapshot_event(
        through_trial_id=9,
        snapshot=snapshot,
        policy_version="unit-policy-v1",
        actor="unit-test",
        parent_snapshot_hash="parent-hash",
    )

    assert event["type"] == JOURNAL_SNAPSHOT_EVENT_TYPE
    assert event["through_trial_id"] == 9
    assert event["snapshot"] == snapshot
    assert event["parent_snapshot_hash"] == "parent-hash"
    assert len(event["snapshot_hash"]) == 64
    assert journal.count() == 1
    assert journal.next_trial_id() == 10

    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.count() == 1
    assert reloaded.next_trial_id() == 10
    assert reloaded.journal_snapshot_events() == [event]
    assert reloaded.latest_journal_snapshot_event() == event
    assert reloaded.supersession_events() == []


def test_role_restart_boundary_event_round_trips_without_counting_as_trial(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(11))

    event = journal.append_role_restart_boundary_event(
        role="frontdoor",
        affected_roles=["frontdoor", "coder_escalation"],
        env_keys=["ORCHESTRATOR_FRONTDOOR_REPL_NON_TOOL_N_TOKENS"],
        registry_override_keys=[],
        status="ok",
        rollback_status="",
        reason="shadow role restart",
        actor="unit-test",
        boundary_trial_id=11,
        command="orchestrator_stack.py reload frontdoor",
    )

    assert event["type"] == ROLE_RESTART_BOUNDARY_EVENT_TYPE
    assert event["role"] == "frontdoor"
    assert event["affected_roles"] == ["frontdoor", "coder_escalation"]
    assert event["boundary_trial_id"] == 11
    assert event["env_keys"] == ["ORCHESTRATOR_FRONTDOOR_REPL_NON_TOOL_N_TOKENS"]
    assert event["policy_version"] == "role-restart-boundary-v1"
    assert journal.count() == 1
    assert journal.next_trial_id() == 12

    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.count() == 1
    assert reloaded.next_trial_id() == 12
    assert reloaded.role_restart_boundary_events() == [event]
    assert reloaded.ledger_events(ROLE_RESTART_BOUNDARY_EVENT_TYPE) == [event]


def test_role_restart_boundary_event_does_not_affect_archive_reconstruction(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))
    journal.append_role_restart_boundary_event(
        role="worker_general",
        affected_roles=["worker_general"],
        env_keys=["ORCHESTRATOR_WORKER_CALL_BUDGET_CAP"],
        registry_override_keys=[],
        status="error",
        rollback_status="ok",
        reason="rollback test",
        actor="unit-test",
        boundary_trial_id=1,
    )
    rows = [asdict(entry) for entry in journal.all_entries()]
    rows.extend(journal.ledger_events())

    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)

    assert archive is not None
    assert [entry["trial_id"] for entry in archive["all_entries"]] == [1]
    assert archive["supersessions"] == {
        "events_applied": 0,
        "target_trial_ids": [],
        "field_names": [],
    }


def test_matching_trial_ids_does_not_mutate_entries(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))
    journal.record(_entry(2))

    matched = journal.matching_trial_ids(trial_id_min=2)

    assert matched == [2]
    assert [entry.bug_corrupted_by for entry in journal.all_entries()] == ["", ""]


def test_reconstruction_folds_supersession_events_without_mutating_trials(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))
    dominant = _entry(2)
    dominant.quality = 2.0
    dominant.speed = 99.0
    journal.record(dominant)
    journal.append_supersession_event(
        target_trial_ids=[2],
        fields={
            "bug_corrupted_by": "resource_contention",
            "bug_corrupted_reason": "synthetic contention window",
        },
        reason="synthetic contention window",
        policy_version="supersession-v1",
        actor="unit-test",
    )
    rows = [asdict(entry) for entry in journal.all_entries()]
    rows.extend(journal.supersession_events())

    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)

    assert archive is not None
    assert [entry["trial_id"] for entry in archive["frontier"]] == [1]
    assert archive["exclusions"]["bug_corrupted"] == {"count": 1, "max_trial_id": 2}
    assert archive["supersessions"] == {
        "events_applied": 1,
        "target_trial_ids": [2],
        "field_names": ["bug_corrupted_by", "bug_corrupted_reason"],
    }
    assert journal.all_entries()[1].bug_corrupted_by == ""


def test_runtime_prompt_views_fold_supersession_events_without_mutating_trials(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    trusted = _entry(1)
    trusted.pareto_status = "frontier"
    trusted.hypothesis = "trusted signal"
    journal.record(trusted)
    contaminated = _entry(2)
    contaminated.pareto_status = "frontier"
    contaminated.quality = 2.0
    contaminated.hypothesis = "contaminated signal"
    journal.record(contaminated)
    journal.append_supersession_event(
        target_trial_ids=[2],
        fields={
            "bug_corrupted_by": "resource_contention",
            "bug_corrupted_reason": "synthetic contention window",
        },
        reason="synthetic contention window",
        policy_version="supersession-v1",
        actor="unit-test",
    )

    folded = journal.entries_with_supersessions()

    assert journal.all_entries()[1].bug_corrupted_by == ""
    assert folded[1].bug_corrupted_by == "resource_contention"
    assert [entry.trial_id for entry in journal.trustworthy_entries()] == [1]
    assert journal.trustworthiness_score()["corrupted_by"] == {
        "resource_contention": 1
    }
    summary = journal.summary_text()
    assert "#2 [seeder/seed_batch] CORRUPTED_BY=resource_contention" in summary
    assert "q=2.000" not in summary
    insights = journal.insights_text()
    assert "#1" in insights
    assert "#2" not in insights


def test_recent_failures_excludes_superseded_bug_corrupted_by_default(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    trusted = _entry(1)
    trusted.species = "prompt_forge"
    trusted.failure_analysis = "trusted failure"
    journal.record(trusted)
    contaminated = _entry(2)
    contaminated.species = "prompt_forge"
    contaminated.failure_analysis = "contaminated failure"
    journal.record(contaminated)
    journal.append_supersession_event(
        target_trial_ids=[2],
        fields={"bug_corrupted_by": "resource_contention"},
        reason="contention window",
        policy_version="supersession-v1",
        actor="unit-test",
    )

    safe = journal.recent_failures(species="prompt_forge", n=5)
    raw = journal.recent_failures(
        species="prompt_forge",
        n=5,
        exclude_bug_corrupted=False,
    )

    assert [entry.trial_id for entry in safe] == [1]
    assert [entry.trial_id for entry in raw] == [1, 2]
