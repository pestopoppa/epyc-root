from __future__ import annotations

import sys

from scripts.autopilot import scrub_journal
from scripts.autopilot.experiment_journal import JournalEntry


def _record_trial(journal_dir, trial_id: int = 1) -> None:
    journal = scrub_journal.ExperimentJournal(journal_dir=journal_dir)
    journal.record(
        JournalEntry(
            trial_id=trial_id,
            timestamp="2026-06-13T00:00:00+00:00",
            species="seeder",
            action_type="seed_batch",
            tier=1,
            quality=1.0,
            speed=10.0,
            cost=0.5,
            reliability=1.0,
            pareto_status="dominated",
        )
    )


def test_scrub_defaults_to_append_only_supersession_event(
    tmp_path,
    monkeypatch,
) -> None:
    _record_trial(tmp_path)
    monkeypatch.setattr(scrub_journal, "_autopilot_running_pids", lambda: [])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scrub_journal.py",
            "--journal-dir",
            str(tmp_path),
            "--commit-sha",
            "resource_contention",
            "--reason",
            "contention window",
            "--trial-id-min",
            "1",
            "--trial-id-max",
            "1",
        ],
    )

    assert scrub_journal.main() == 0

    reloaded = scrub_journal.ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.all_entries()[0].bug_corrupted_by == ""
    assert reloaded.supersession_events()[0]["fields"] == {
        "bug_corrupted_by": "resource_contention",
        "bug_corrupted_reason": "contention window",
    }
    assert reloaded.trustworthiness_score()["corrupted_by"] == {
        "resource_contention": 1
    }


def test_scrub_rejects_retired_rewrite_in_place_flag(tmp_path, monkeypatch) -> None:
    _record_trial(tmp_path)
    monkeypatch.setattr(scrub_journal, "_autopilot_running_pids", lambda: [])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "scrub_journal.py",
            "--journal-dir",
            str(tmp_path),
            "--commit-sha",
            "legacy",
            "--reason",
            "legacy rewrite",
            "--trial-id-min",
            "1",
            "--trial-id-max",
            "1",
            "--rewrite-in-place",
        ],
    )

    try:
        scrub_journal.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should always reject the retired flag
        raise AssertionError("--rewrite-in-place was unexpectedly accepted")

    reloaded = scrub_journal.ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.all_entries()[0].bug_corrupted_by == ""
    assert reloaded.supersession_events() == []
