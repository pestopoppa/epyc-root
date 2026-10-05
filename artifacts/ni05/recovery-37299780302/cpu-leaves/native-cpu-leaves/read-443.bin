"""Tests for the read-only/default journal snapshot builder."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from journal_snapshot_create import (  # noqa: E402
    append_archive_snapshot,
    build_archive_snapshot,
)
from src.autopilot_core.journal_snapshot_replay import (  # noqa: E402
    build_snapshot_replay_diagnostic,
)


def _entry(trial_id: int, *, quality: float = 1.0) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp=f"2026-06-14T00:00:0{trial_id}Z",
        species="unit",
        action_type="seed_batch",
        tier=1,
        quality=quality,
        speed=40.0,
        cost=0.2,
        reliability=0.9,
        pareto_status="frontier",
    )


def _rows_with_events(journal: ExperimentJournal) -> list[dict]:
    rows = [asdict(entry) for entry in journal.all_entries()]
    rows.extend(journal.ledger_events())
    return rows


def test_build_archive_snapshot_dry_run_does_not_write(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1, quality=1.2))

    result = build_archive_snapshot(journal)

    assert result.status == "ready"
    assert result.through_trial_id == 1
    assert result.trial_count == 1
    assert result.ledger_event_count == 0
    assert result.snapshot is not None
    assert "archive" in result.snapshot
    assert result.snapshot["replay_state"]["version"] == "representative-replay-state-v1"
    assert journal.journal_snapshot_events() == []


def test_append_archive_snapshot_round_trips_as_valid_replay_prefix(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1, quality=1.2))
    journal.record(_entry(2, quality=1.1))

    result = build_archive_snapshot(journal)
    event = append_archive_snapshot(journal, result, actor="unit-test")

    assert event["through_trial_id"] == 2
    assert len(event["snapshot_hash"]) == 64
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.journal_snapshot_events() == [event]

    diagnostic = build_snapshot_replay_diagnostic(
        _rows_with_events(reloaded),
        reloaded.ledger_events(),
    )
    assert diagnostic.status == "archive_prefix_match"
    assert diagnostic.hash_status == "match"


def test_build_archive_snapshot_refuses_duplicate_without_force(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))
    first = build_archive_snapshot(journal)
    event = append_archive_snapshot(journal, first, actor="unit-test")

    duplicate = build_archive_snapshot(journal)
    forced = build_archive_snapshot(journal, force=True)

    assert duplicate.status == "up_to_date"
    assert duplicate.parent_snapshot_hash == event["snapshot_hash"]
    assert forced.status == "ready"
    assert forced.parent_snapshot_hash == event["snapshot_hash"]


def test_append_archive_snapshot_rejects_non_ready_result(tmp_path: Path) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    result = build_archive_snapshot(journal)

    assert result.status == "no_trials"
    with pytest.raises(ValueError, match="not appendable"):
        append_archive_snapshot(journal, result)
