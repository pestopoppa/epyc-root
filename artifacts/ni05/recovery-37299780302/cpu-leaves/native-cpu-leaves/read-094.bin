"""Phase 6b — In-flight trial marker + crash recovery tests.

Per handoffs/active/autopilot-exogenous-restart-resilience.md Phase 6b
verification gate. Covers:

  1. No marker present → no-op (trial_counter unchanged, state untouched
     besides the marker field itself).
  2. Case (a): in_flight_trial.trial_id == journal_max
     → trial DID land in the journal before the crash. The recovery
     code must:
       - bump trial_counter to max(current, journal_max + 1)
       - clear the marker
       - NOT write a placeholder
  3. Case (b): in_flight_trial.trial_id > journal_max
     → trial died before journal.record. The recovery code must:
       - write an AUTOPILOT_KILLED placeholder JournalEntry tagged
         bug_corrupted_by=autopilot_killed_mid_trial
       - bump trial_counter to prior_tid + 1
       - clear the marker
  4. `_maybe_reimport_pareto_from_journal` helper:
       - skips bug_corrupted entries
       - skips entries already in the archive (no double-count)
       - re-imports a valid entry when missing
       - skips silently when no JournalEntry matches the trial_id
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from pareto_archive import ParetoArchive, ParetoEntry  # noqa: E402
from src.autopilot_core.journal_reconstruction import (  # noqa: E402
    reconstruct_archive_from_journal_rows,
)


# ───────── fixtures ──────────


@pytest.fixture
def journal(tmp_path: Path) -> ExperimentJournal:
    return ExperimentJournal(journal_dir=tmp_path / "journal")


@pytest.fixture
def archive(tmp_path: Path) -> ParetoArchive:
    return ParetoArchive(state_path=tmp_path / "archive.json")


def _make_entry(
    trial_id: int,
    *,
    quality: float = 0.7,
    speed: float = 40.0,
    cost: float = 0.3,
    reliability: float = 0.9,
    bug_corrupted_by: str = "",
    species: str = "test_species",
    eval_details: dict[str, Any] | None = None,
) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp="2026-05-24T00:00:00Z",
        species=species,
        action_type="seed_batch",
        tier=2,
        quality=quality,
        speed=speed,
        cost=cost,
        reliability=reliability,
        pareto_status="frontier",
        eval_details=eval_details or {},
        bug_corrupted_by=bug_corrupted_by,
    )


def test_archive_for_read_command_defaults_to_journal_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeJournal:
        def all_entries(self):
            return [_make_entry(1, quality=1.4, speed=40.0)]

        def supersession_events(self):
            return []

    monkeypatch.setattr(autopilot, "load_state", lambda: {})

    archive, source = autopilot._archive_for_read_command(journal=FakeJournal())

    assert source == autopilot.ARCHIVE_SOURCE_JOURNAL_ALL
    assert archive.read_only is True
    assert [entry.trial_id for entry in archive.frontier(tier=2)] == [1]


def test_archive_for_read_command_explicit_state_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    monkeypatch.setattr(autopilot, "ParetoArchive", lambda: sentinel)

    archive, source = autopilot._archive_for_read_command(
        journal=object(),
        source=autopilot.ARCHIVE_SOURCE_STATE,
    )

    assert archive is sentinel
    assert source == autopilot.ARCHIVE_SOURCE_STATE


def test_archive_for_read_command_can_use_journal_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeJournal:
        def all_entries(self):
            return [
                _make_entry(1, quality=1.4, speed=40.0),
                _make_entry(2, quality=1.5, speed=45.0),
            ]

        def supersession_events(self):
            return []

    monkeypatch.setattr(autopilot, "load_state", lambda: {})

    archive, source = autopilot._archive_for_read_command(
        journal=FakeJournal(),
        source=autopilot.ARCHIVE_SOURCE_JOURNAL_ALL,
    )

    assert source == autopilot.ARCHIVE_SOURCE_JOURNAL_ALL
    assert archive.read_only is True
    assert [entry.trial_id for entry in archive.frontier(tier=2)] == [2]


def test_journal_archive_authority_uses_current_snapshot(
    journal: ExperimentJournal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.4, speed=40.0))
    rows = autopilot._journal_rows_for_archive(journal)
    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)
    assert archive is not None
    journal.append_journal_snapshot_event(
        through_trial_id=1,
        snapshot={"archive": archive},
        policy_version="unit-policy-v1",
        actor="unit-test",
    )
    called_full_replay = False

    def _fail_full_replay(*args, **kwargs):
        nonlocal called_full_replay
        called_full_replay = True
        raise AssertionError("current verified snapshot should satisfy authority")

    monkeypatch.setattr(autopilot, "reconstruct_archive_from_journal_rows", _fail_full_replay)

    payload = autopilot._journal_archive_payload_for_authority(journal)

    assert payload == archive
    assert called_full_replay is False


def test_journal_archive_authority_rejects_snapshot_from_other_objective_policy(
    journal: ExperimentJournal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.4, speed=40.0))
    rows = autopilot._journal_rows_for_archive(journal)
    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)
    assert archive is not None
    journal.append_journal_snapshot_event(
        through_trial_id=1,
        snapshot={"archive": archive},
        policy_version="unit-policy-v1",
        actor="unit-test",
    )
    sentinel = {"objective_policy": autopilot.RATE_4D_OBJECTIVE_POLICY, "all_entries": []}
    calls: list[str] = []

    def _full_replay(*args, **kwargs):
        calls.append(kwargs["objective_policy"])
        return sentinel

    monkeypatch.setattr(autopilot, "reconstruct_archive_from_journal_rows", _full_replay)

    payload = autopilot._journal_archive_payload_for_authority(
        journal, objective_policy=autopilot.RATE_4D_OBJECTIVE_POLICY
    )

    assert payload == sentinel
    assert calls == [autopilot.RATE_4D_OBJECTIVE_POLICY]


def test_autopilot_start_fails_closed_until_execution_instrument_is_ratified() -> None:
    with pytest.raises(RuntimeError, match="not ratified"):
        autopilot._assert_eval_execution_instrument_state(
            {
                "pareto_objective_policy": "task_rate_4d_v1",
                "eval_execution_instrument_id": "serial-v1",
            }
        )

    autopilot._assert_eval_execution_instrument_state(
        {
            "pareto_objective_policy": autopilot.RATE_4D_OBJECTIVE_POLICY,
            "eval_execution_instrument_id": autopilot.EVAL_EXECUTION_INSTRUMENT_ID,
        }
    )


def test_journal_archive_authority_folds_safe_snapshot_tail(
    journal: ExperimentJournal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.4, speed=40.0))
    rows = autopilot._journal_rows_for_archive(journal)
    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)
    assert archive is not None
    journal.append_journal_snapshot_event(
        through_trial_id=1,
        snapshot={"archive": archive},
        policy_version="unit-policy-v1",
        actor="unit-test",
    )
    journal.record(_make_entry(2, quality=1.5, speed=45.0))
    called_full_replay = False

    def _fail_full_replay(*args, **kwargs):
        nonlocal called_full_replay
        called_full_replay = True
        raise AssertionError("safe tail should fold without full replay fallback")

    monkeypatch.setattr(autopilot, "reconstruct_archive_from_journal_rows", _fail_full_replay)

    payload = autopilot._journal_archive_payload_for_authority(journal)

    assert called_full_replay is False
    assert payload is not None
    assert payload["journal_max_trial_id"] == 2


def test_journal_archive_authority_replays_full_journal_when_tail_needs_prefix(
    journal: ExperimentJournal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.4, speed=40.0))
    rows = autopilot._journal_rows_for_archive(journal)
    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)
    assert archive is not None
    journal.append_journal_snapshot_event(
        through_trial_id=1,
        snapshot={"archive": archive},
        policy_version="unit-policy-v1",
        actor="unit-test",
    )
    journal.record(_make_entry(
        2,
        quality=1.5,
        speed=45.0,
        eval_details={
            "learning_exclusion": {
                "by": "seq_accumulating",
                "reason": "unit-test sequential accumulation",
            }
        },
    ))
    calls: list[int] = []

    def _full_replay(rows_arg, *args, **kwargs):
        rows_list = list(rows_arg)
        calls.append(len(rows_list))
        return reconstruct_archive_from_journal_rows(rows_list, *args, **kwargs)

    monkeypatch.setattr(autopilot, "reconstruct_archive_from_journal_rows", _full_replay)

    payload = autopilot._journal_archive_payload_for_authority(journal)

    assert calls
    assert payload is not None
    assert payload["journal_max_trial_id"] == 2


def test_archive_for_read_command_falls_back_when_journal_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EmptyJournal:
        def all_entries(self):
            return []

        def supersession_events(self):
            return []

    monkeypatch.setattr(autopilot, "load_state", lambda: {})

    archive, source = autopilot._archive_for_read_command(
        journal=EmptyJournal(),
        source=autopilot.ARCHIVE_SOURCE_JOURNAL_CURRENT_RUN,
    )

    assert archive.read_only is True
    assert archive.frontier() == []
    assert source == "journal-current-run->empty-fallback"
    assert source != "journal-current-run->state-empty-fallback"


def test_cmd_plot_uses_journal_archive_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeJournal:
        def all_entries(self):
            return [_make_entry(1, quality=1.4, speed=40.0)]

        def supersession_events(self):
            return []

    def _state_archive_should_not_load():
        raise AssertionError("cmd_plot must not load legacy state archive directly")

    captured: dict[str, object] = {}

    def _generate_all_plots(archive, journal, td_errors, *, raise_on_error):
        captured["archive"] = archive
        captured["journal"] = journal
        captured["td_errors"] = td_errors
        captured["raise_on_error"] = raise_on_error
        return []

    monkeypatch.setattr(autopilot, "ExperimentJournal", FakeJournal)
    monkeypatch.setattr(autopilot, "ParetoArchive", _state_archive_should_not_load)
    monkeypatch.setattr(autopilot, "load_state", lambda: {"td_errors": [0.25]})
    monkeypatch.setattr(autopilot, "generate_all_plots", _generate_all_plots)

    autopilot.cmd_plot(SimpleNamespace(archive_source=autopilot.ARCHIVE_SOURCE_JOURNAL_ALL))

    archive = captured["archive"]
    assert archive.read_only is True
    assert [entry.trial_id for entry in archive.frontier(tier=2)] == [1]
    assert isinstance(captured["journal"], FakeJournal)
    assert captured["td_errors"] == [(0, 0.25)]
    assert captured["raise_on_error"] is True


def test_cmd_plot_accepts_explicit_archive_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_archive = object()
    captured: dict[str, object] = {}

    class FakeJournal:
        pass

    def _archive_for_read_command(journal, *, source):
        captured["journal_arg"] = journal
        captured["source_arg"] = source
        return sentinel_archive, source

    def _generate_all_plots(archive, journal, td_errors, *, raise_on_error):
        captured["archive"] = archive
        captured["journal"] = journal
        captured["td_errors"] = td_errors
        captured["raise_on_error"] = raise_on_error
        return []

    monkeypatch.setattr(autopilot, "ExperimentJournal", FakeJournal)
    monkeypatch.setattr(autopilot, "_archive_for_read_command", _archive_for_read_command)
    monkeypatch.setattr(autopilot, "load_state", lambda: {"td_errors": []})
    monkeypatch.setattr(autopilot, "generate_all_plots", _generate_all_plots)

    autopilot.cmd_plot(
        SimpleNamespace(archive_source=autopilot.ARCHIVE_SOURCE_JOURNAL_CURRENT_RUN)
    )

    assert isinstance(captured["journal_arg"], FakeJournal)
    assert captured["source_arg"] == autopilot.ARCHIVE_SOURCE_JOURNAL_CURRENT_RUN
    assert captured["archive"] is sentinel_archive
    assert isinstance(captured["journal"], FakeJournal)
    assert captured["td_errors"] == []
    assert captured["raise_on_error"] is True


def test_cmd_digest_accepts_explicit_archive_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel_archive = object()
    captured: dict[str, object] = {}
    saved_states: list[dict[str, object]] = []

    class FakeJournal:
        pass

    class FakeSwarm:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class FakeLab:
        pass

    def _archive_for_read_command(journal, *, source):
        captured["journal_arg"] = journal
        captured["source_arg"] = source
        return sentinel_archive, source

    def _generate_digest(**kwargs):
        captured.update(kwargs)
        return Path("/tmp/autopilot-digest.md")

    monkeypatch.setattr(autopilot, "ExperimentJournal", FakeJournal)
    monkeypatch.setattr(autopilot, "_archive_for_read_command", _archive_for_read_command)
    monkeypatch.setattr(autopilot, "NumericSwarm", FakeSwarm)
    monkeypatch.setattr(autopilot, "StructuralLab", FakeLab)
    monkeypatch.setattr(autopilot, "generate_digest", _generate_digest)
    monkeypatch.setattr(autopilot, "load_state", lambda: {"trial_counter": 12})
    monkeypatch.setattr(autopilot, "save_state", lambda state: saved_states.append(dict(state)))

    autopilot.cmd_digest(
        SimpleNamespace(
            no_state_update=True,
            archive_source=autopilot.ARCHIVE_SOURCE_STATE,
            output_root="/tmp/autopilot-digest-smoke",
        )
    )

    assert isinstance(captured["journal_arg"], FakeJournal)
    assert captured["source_arg"] == autopilot.ARCHIVE_SOURCE_STATE
    assert captured["archive"] is sentinel_archive
    assert captured["archive_source"] == autopilot.ARCHIVE_SOURCE_STATE
    assert captured["output_root"] == Path("/tmp/autopilot-digest-smoke")
    assert isinstance(captured["swarm"], FakeSwarm)
    assert captured["swarm"].kwargs == {"epoch_label": None}
    assert isinstance(captured["lab"], FakeLab)
    assert saved_states == []


def test_append_baseline_promotion_event_only_for_updated_baseline(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    eval_result = autopilot.EvalResult(
        tier=1,
        quality=1.8,
        speed=42.0,
        cost=0.4,
        reliability=0.95,
        n_questions=50,
    )
    rejected = SimpleNamespace(
        updated=False,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="not updated",
        proof={},
    )

    assert autopilot._append_baseline_promotion_event(
        journal=journal,
        baseline_update=rejected,
        eval_result=eval_result,
        source_trial_id=8,
        pareto_status="frontier",
        baseline_state={},
    ) is None
    assert journal.baseline_promotion_events() == []

    accepted = SimpleNamespace(
        updated=True,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
    )

    event = autopilot._append_baseline_promotion_event(
        journal=journal,
        baseline_update=accepted,
        eval_result=eval_result,
        source_trial_id=8,
        pareto_status="frontier",
        baseline_state={"baselines_by_tier": {"1": 1.8}},
    )

    assert event is not None
    assert event["source_trial_id"] == 8
    assert event["result_metrics"]["pareto_status"] == "frontier"
    assert journal.baseline_promotion_events() == [event]


def test_baseline_promotion_summary_reports_no_events(journal: ExperimentJournal) -> None:
    lines = autopilot._baseline_promotion_summary_lines({}, journal)

    assert lines == [
        "Baseline promotion events: 0",
        "Baseline ledger state: no promotion events",
        "Baseline fold cutover dry-run: not_ready",
        "Baseline fold blocker: no baseline promotion events; YAML remains cold-start seed",
    ]


def test_baseline_promotion_summary_compares_latest_event_to_state(
    journal: ExperimentJournal,
) -> None:
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )

    lines = autopilot._baseline_promotion_summary_lines(
        {"baseline_state": {"baselines_by_tier": {"1": 1.8}}},
        journal,
    )

    assert lines[0] == "Baseline promotion events: 1"
    assert lines[1].startswith("Latest baseline event: trial #8 T1 1.500 -> 1.800 at ")
    assert lines[2] == "Baseline ledger state status: match"


def test_baseline_promotion_summary_reports_state_drift(
    journal: ExperimentJournal,
) -> None:
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )

    lines = autopilot._baseline_promotion_summary_lines(
        {"baseline_state": {"baselines_by_tier": {"1": 1.7}}},
        journal,
    )

    assert lines[2] == "Baseline ledger state status: drift"


def test_merge_external_control_fields_preserves_operator_pause() -> None:
    state = {
        "trial_counter": 42,
        "paused": False,
        "in_flight_trial": {"trial_id": 41},
    }
    disk_state = {
        "trial_counter": 999,
        "paused": True,
        "_in_cache_flush": True,
        "in_flight_trial": None,
    }

    changed = autopilot._merge_external_control_fields(state, disk_state)

    assert changed == ["paused", "_in_cache_flush"]
    assert state["paused"] is True
    assert state["_in_cache_flush"] is True
    # Do not merge counters or WAL metadata from disk into the live trial state.
    assert state["trial_counter"] == 42
    assert state["in_flight_trial"] == {"trial_id": 41}


def test_merge_external_control_fields_noops_without_control_fields() -> None:
    state = {"trial_counter": 42, "paused": False}

    changed = autopilot._merge_external_control_fields(
        state,
        {"trial_counter": 999, "in_flight_trial": None},
    )

    assert changed == []
    assert state == {"trial_counter": 42, "paused": False}


def test_startup_archive_sync_removes_cached_state_archive(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    journal.record(_make_entry(1, quality=1.1))
    journal.record(_make_entry(2, quality=1.2))
    state = {
        "trial_counter": 3,
        "pareto_archive": {
            "frontier": [],
            "all_entries": [],
            "hypervolume_history": [],
        },
    }

    changed = autopilot._sync_startup_archive_from_journal_authority(
        state, journal, archive,
    )

    assert changed is True
    assert "pareto_archive" not in state
    assert [entry.trial_id for entry in archive.frontier(tier=2)] == [2]


def test_startup_archive_sync_skips_deliberate_empty_frontier_rebase(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    journal.record(_make_entry(1, quality=1.1))
    state = {
        "trial_counter": 3,
        "_allow_empty_frontier_rebase": True,
        "pareto_archive": {
            "frontier": [],
            "all_entries": [],
            "hypervolume_history": [],
        },
    }

    changed = autopilot._sync_startup_archive_from_journal_authority(
        state, journal, archive,
    )

    assert changed is False
    assert state["pareto_archive"]["all_entries"] == []


def test_empty_current_era_bootstrap_keeps_rebase_flag_until_a_point_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EmptyArchive:
        def tiers(self) -> list[int]:
            return []

        def frontier_size(self, _tier: int) -> int:
            return 0

    monkeypatch.setattr(autopilot, "ParetoArchive", lambda: EmptyArchive())
    state = {
        "_allow_empty_frontier_rebase": True,
        "e8_empty_frontier_bootstrap": {"status": "active"},
    }

    archive, rebase_completed = autopilot._startup_archive_from_current_era_payload(
        state,
        None,
    )

    assert isinstance(archive, EmptyArchive)
    assert rebase_completed is False
    assert state["_allow_empty_frontier_rebase"] is True
    assert state["e8_empty_frontier_bootstrap"]["status"] == "active"


def test_restart_after_first_current_era_point_loads_payload_and_clears_rebase(
    journal: ExperimentJournal,
) -> None:
    journal.record(_make_entry(1, quality=1.2))
    payload = autopilot._journal_archive_payload_for_authority(journal)
    assert payload is not None
    state = {
        "_allow_empty_frontier_rebase": True,
        "e8_empty_frontier_bootstrap": {
            "status": "active",
            "required_clear_condition": (
                "next AutoPilot startup observes at least one current-era Pareto point"
            ),
        },
    }

    archive, rebase_completed = autopilot._startup_archive_from_current_era_payload(
        state,
        payload,
    )

    assert [entry.trial_id for entry in archive.frontier(tier=2)] == [1]
    assert rebase_completed is True
    assert "_allow_empty_frontier_rebase" not in state
    assert state["e8_empty_frontier_bootstrap"] == {
        "status": "completed",
        "required_clear_condition": (
            "next AutoPilot startup observes at least one current-era Pareto point"
        ),
        "completion_condition": (
            "next AutoPilot startup observed at least one current-era Pareto point"
        ),
    }


def test_resource_lane_bootstrap_marker_completes_without_reusing_e8_marker(
    journal: ExperimentJournal,
) -> None:
    journal.record(_make_entry(1, quality=1.2))
    payload = autopilot._journal_archive_payload_for_authority(journal)
    assert payload is not None
    state = {
        "_allow_empty_frontier_rebase": True,
        "eval_instrument_empty_frontier_bootstrap": {"status": "pending"},
        "e8_empty_frontier_bootstrap": {"status": "completed"},
    }

    _archive, rebase_completed = autopilot._startup_archive_from_current_era_payload(
        state, payload
    )

    assert rebase_completed is True
    assert state["eval_instrument_empty_frontier_bootstrap"]["status"] == "completed"
    assert state["e8_empty_frontier_bootstrap"]["status"] == "completed"


def test_save_state_with_journal_archive_authority_removes_state_cache(
    journal: ExperimentJournal,
    archive: ParetoArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.1))
    journal.record(_make_entry(2, quality=1.2))
    state = {
        "trial_counter": 3,
        "pareto_archive": {
            "frontier": [],
            "all_entries": [],
            "hypervolume_history": [],
        },
    }
    saved: list[dict] = []

    monkeypatch.setattr(autopilot, "save_state", lambda updated: saved.append(dict(updated)))
    assert not hasattr(archive, "save")

    used_journal = autopilot._save_state_with_journal_archive_authority(
        state,
        journal,
        archive,
        context="unit-test",
    )

    assert used_journal is True
    assert "pareto_archive" not in state
    assert [entry.trial_id for entry in archive.frontier(tier=2)] == [2]
    assert saved and "pareto_archive" not in saved[-1]


def test_save_state_with_empty_journal_does_not_write_legacy_archive(
    journal: ExperimentJournal,
    archive: ParetoArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        "trial_counter": 0,
        "paused": False,
    }
    saved: list[dict] = []

    monkeypatch.setattr(autopilot, "save_state", lambda updated: saved.append(dict(updated)))
    assert not hasattr(archive, "save")

    used_journal = autopilot._save_state_with_journal_archive_authority(
        state,
        journal,
        archive,
        context="unit-test-empty-journal",
    )

    assert used_journal is False
    assert saved == [{"trial_counter": 0, "paused": False}]
    assert "pareto_archive" not in state


def test_save_state_with_journal_authority_removes_baseline_cache(
    journal: ExperimentJournal,
    archive: ParetoArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.1))
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )
    state = {
        "trial_counter": 9,
        "baseline_ledger_authority_enabled": True,
        "baseline_state": {"baselines_by_tier": {"1": 1.8}},
    }
    saved: list[dict] = []

    # Baseline authority is now fail-closed behind operator consent; grant it here.
    monkeypatch.setattr(
        "src.autopilot_core.baseline_ledger.authority_consent", lambda *a, **k: True
    )
    monkeypatch.setattr(autopilot, "save_state", lambda updated: saved.append(dict(updated)))
    assert not hasattr(archive, "save")

    used_journal = autopilot._save_state_with_journal_archive_authority(
        state,
        journal,
        archive,
        context="unit-test",
    )

    assert used_journal is True
    assert "baseline_state" not in state
    assert saved and "baseline_state" not in saved[-1]


def test_save_state_with_journal_authority_requires_baseline_enable_flag(
    journal: ExperimentJournal,
    archive: ParetoArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.1))
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )
    state = {
        "trial_counter": 9,
        "baseline_state": {"baselines_by_tier": {"1": 1.8}},
    }
    saved: list[dict] = []

    monkeypatch.setattr(autopilot, "save_state", lambda updated: saved.append(dict(updated)))

    used_journal = autopilot._save_state_with_journal_archive_authority(
        state,
        journal,
        archive,
        context="unit-test",
    )

    assert used_journal is True
    assert state["baseline_state"] == {"baselines_by_tier": {"1": 1.8}}
    assert saved and saved[-1]["baseline_state"] == {"baselines_by_tier": {"1": 1.8}}


def test_save_state_with_journal_authority_keeps_drifted_baseline_cache(
    journal: ExperimentJournal,
    archive: ParetoArchive,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.record(_make_entry(1, quality=1.1))
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )
    state = {
        "trial_counter": 9,
        "baseline_state": {"baselines_by_tier": {"1": 1.7}},
    }
    saved: list[dict] = []

    monkeypatch.setattr(autopilot, "save_state", lambda updated: saved.append(dict(updated)))
    assert not hasattr(archive, "save")

    used_journal = autopilot._save_state_with_journal_archive_authority(
        state,
        journal,
        archive,
        context="unit-test",
    )

    assert used_journal is True
    assert state["baseline_state"] == {"baselines_by_tier": {"1": 1.7}}
    assert saved[-1]["baseline_state"] == {"baselines_by_tier": {"1": 1.7}}


def test_startup_baseline_prefers_state_cache_when_present(
    journal: ExperimentJournal,
) -> None:
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )

    baseline_state = autopilot._baseline_state_for_startup_gate(
        {"baseline_state": {"baselines_by_tier": {"1": 1.7}}},
        journal,
    )

    assert baseline_state == {"baselines_by_tier": {"1": 1.7}}


def test_startup_baseline_uses_cutover_ready_ledger_when_cache_absent(
    journal: ExperimentJournal,
) -> None:
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state={"baselines_by_tier": {"1": 1.8}},
        actor="unit-test",
    )

    baseline_state = autopilot._baseline_state_for_startup_gate({}, journal)

    assert baseline_state == {"baselines_by_tier": {"1": 1.8}}


def test_startup_baseline_falls_back_when_ledger_not_ready(
    journal: ExperimentJournal,
) -> None:
    journal.append_baseline_promotion_event(
        source_trial_id=8,
        tier=1,
        previous_quality=1.5,
        new_quality=1.8,
        reason="accepted",
        proof={"matrix_status": "ok"},
        result_metrics={"quality": 1.8},
        baseline_state=None,  # type: ignore[arg-type]
        actor="unit-test",
    )

    baseline_state = autopilot._baseline_state_for_startup_gate({}, journal)

    assert baseline_state == {}


def test_save_state_drops_pause_reason_when_unpaused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(autopilot, "STATE_PATH", tmp_path / "state.json")
    state = {
        "trial_counter": 42,
        "paused": False,
        "pause_reason": "stale quarantine reason",
    }

    autopilot.save_state(state)

    assert "pause_reason" not in state
    assert "pause_reason" not in autopilot.load_state()


def test_save_state_preserves_pause_reason_when_paused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(autopilot, "STATE_PATH", tmp_path / "state.json")
    state = {
        "trial_counter": 42,
        "paused": True,
        "pause_reason": "operator pause",
    }

    autopilot.save_state(state)

    assert autopilot.load_state()["pause_reason"] == "operator pause"


def test_resume_clears_skip_loop_latch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(autopilot, "STATE_PATH", tmp_path / "state.json")
    autopilot.save_state(
        {
            "trial_counter": 882,
            "paused": True,
            "_dispatch_deficiency": "skip_action_loop",
            "consecutive_skip_actions": 4,
            "last_invalid_action": {"type": "numeric_trial", "surface": "memrl_retrieval"},
            "last_invalid_reason": "action blacklisted",
            "last_invalid_status": "invalid",
            "pause_reason": "operator review",
        }
    )

    autopilot.cmd_resume(argparse.Namespace())

    state = autopilot.load_state()
    assert state["paused"] is False
    assert state["consecutive_skip_actions"] == 0
    assert state["last_invalid_action"] is None
    assert state["last_invalid_reason"] is None
    assert state["last_invalid_status"] is None
    assert "_dispatch_deficiency" not in state
    assert "pause_reason" not in state


# ───────── _recover_from_in_flight_trial ──────────


def test_recovery_no_marker_is_noop(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    state = {"in_flight_trial": None, "trial_counter": 5}
    new_counter = autopilot._recover_from_in_flight_trial(
        state, journal, archive, trial_counter=5,
    )
    assert new_counter == 5
    assert state["in_flight_trial"] is None
    assert state["trial_counter"] == 5
    # No placeholder created
    assert journal.next_trial_id() == 0


def test_recovery_case_a_journal_advanced_bumps_counter(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    """journal_max >= prior_tid → trial recorded; bump counter, no placeholder."""
    # Set up: journal has trial 7 already recorded
    journal.record(_make_entry(trial_id=7, quality=0.8))
    state = {
        "in_flight_trial": {
            "trial_id": 7,
            "action": {"type": "seed_batch"},
            "host_pid": 999,
            "host_started_at": 1000.0,
        },
        "trial_counter": 7,
    }
    new_counter = autopilot._recover_from_in_flight_trial(
        state, journal, archive, trial_counter=7,
    )
    # Counter bumped past the journaled trial
    assert new_counter == 8
    assert state["trial_counter"] == 8
    # Marker cleared
    assert state["in_flight_trial"] is None
    # No placeholder added (still just trial 7)
    assert journal.next_trial_id() == 8
    entries = journal.all_entries()
    assert len(entries) == 1
    assert entries[0].trial_id == 7
    assert entries[0].bug_corrupted_by == ""  # original entry untouched


def test_recovery_case_b_no_journal_writes_placeholder(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    """journal_max < prior_tid → died before record; write placeholder."""
    # Journal has trial 5 but in_flight claims trial 6 was running
    journal.record(_make_entry(trial_id=5))
    state = {
        "in_flight_trial": {
            "trial_id": 6,
            "action": {"type": "prompt_mutation"},
            "host_pid": 111,
            "host_started_at": 2000.0,
        },
        "trial_counter": 6,
    }
    new_counter = autopilot._recover_from_in_flight_trial(
        state, journal, archive, trial_counter=6,
    )
    assert new_counter == 7
    assert state["trial_counter"] == 7
    assert state["in_flight_trial"] is None
    # Placeholder must be present
    entries = journal.all_entries()
    placeholder = next((e for e in entries if e.trial_id == 6), None)
    assert placeholder is not None
    assert placeholder.bug_corrupted_by == "autopilot_killed_mid_trial"
    assert placeholder.deficiency_category == "autopilot_killed_mid_trial"
    assert placeholder.species == "(killed)"
    assert placeholder.action_type == "prompt_mutation"
    assert placeholder.pareto_status == "dominated"
    # Quality/speed/cost/reliability are all zero (no eval evidence)
    assert placeholder.quality == 0.0
    assert placeholder.speed == 0.0


def test_recovery_case_a_counter_never_decreases(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    """If trial_counter is already past journal_max, leave it alone."""
    journal.record(_make_entry(trial_id=3))
    state = {
        "in_flight_trial": {
            "trial_id": 3,
            "action": {"type": "seed_batch"},
            "host_pid": 1,
            "host_started_at": 0.0,
        },
        "trial_counter": 20,
    }
    new_counter = autopilot._recover_from_in_flight_trial(
        state, journal, archive, trial_counter=20,
    )
    assert new_counter == 20
    assert state["trial_counter"] == 20


def test_recovery_case_b_counter_never_decreases(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    """A stale marker cannot move a previously advanced counter backward."""
    journal.record(_make_entry(trial_id=3))
    state = {
        "in_flight_trial": {
            "trial_id": 4,
            "action": {"type": "deep_eval", "tier": 2},
            "host_pid": 1,
            "host_started_at": 0.0,
        },
        "trial_counter": 20,
    }
    new_counter = autopilot._recover_from_in_flight_trial(
        state, journal, archive, trial_counter=20,
    )
    assert new_counter == 20
    assert state["trial_counter"] == 20
    assert state["in_flight_trial"] is None


def test_recovery_placeholder_append_failure_keeps_marker(
    journal: ExperimentJournal, archive: ParetoArchive, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Never erase the only recovery marker when the journal append fails."""
    state = {
        "in_flight_trial": {
            "trial_id": 6,
            "action": {"type": "deep_eval", "tier": 2},
            "host_pid": 111,
            "host_started_at": 2000.0,
        },
        "trial_counter": 6,
    }

    def fail_record(_entry: JournalEntry) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr(journal, "record", fail_record)
    with pytest.raises(RuntimeError, match="trial 6"):
        autopilot._recover_from_in_flight_trial(
            state, journal, archive, trial_counter=6,
        )
    assert state["in_flight_trial"]["trial_id"] == 6
    assert state["trial_counter"] == 6


def test_recovery_idempotent_after_first_call(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    """Calling recovery a second time with cleared marker is a no-op."""
    journal.record(_make_entry(trial_id=4))
    state = {
        "in_flight_trial": {
            "trial_id": 4,
            "action": {"type": "seed_batch"},
            "host_pid": 1,
            "host_started_at": 0.0,
        },
        "trial_counter": 4,
    }
    counter1 = autopilot._recover_from_in_flight_trial(
        state, journal, archive, trial_counter=4,
    )
    # Second call: marker is now None, must be a no-op
    counter2 = autopilot._recover_from_in_flight_trial(
        state, journal, archive, trial_counter=counter1,
    )
    assert counter1 == counter2 == 5


# ───────── _maybe_reimport_pareto_from_journal ──────────


def test_reimport_skips_bug_corrupted_entry(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    journal.record(_make_entry(trial_id=2, bug_corrupted_by="autopilot_killed_mid_trial"))
    result = autopilot._maybe_reimport_pareto_from_journal(archive, journal, 2)
    assert result is False
    assert len(archive._all_entries) == 0


def test_reimport_skips_superseded_bug_corrupted_entry(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    journal.record(_make_entry(trial_id=12))
    journal.append_supersession_event(
        target_trial_ids=[12],
        fields={"bug_corrupted_by": "resource_contention"},
        reason="contention window",
        policy_version="supersession-v1",
        actor="unit-test",
    )

    result = autopilot._maybe_reimport_pareto_from_journal(archive, journal, 12)

    assert result is False
    assert len(archive._all_entries) == 0
    assert journal.all_entries()[0].bug_corrupted_by == ""


def test_reimport_skips_when_already_in_archive(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    journal.record(_make_entry(trial_id=3))
    # Pre-populate the archive with this trial id
    archive.update(ParetoEntry(trial_id=3, objectives=(0.7, 40.0, -0.3, 0.9), eval_tier=2))
    before = len(archive._all_entries)
    result = autopilot._maybe_reimport_pareto_from_journal(archive, journal, 3)
    assert result is False
    assert len(archive._all_entries) == before  # no duplicate


def test_reimport_returns_false_when_no_journal_entry(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    # Journal is empty
    result = autopilot._maybe_reimport_pareto_from_journal(archive, journal, 99)
    assert result is False
    assert len(archive._all_entries) == 0


def test_reimport_adds_missing_valid_entry(
    journal: ExperimentJournal, archive: ParetoArchive
) -> None:
    """Reproduces handoff Section 5.7 corruption window: journal advanced,
    archive missed the save. Reimport should add the entry to the archive."""
    journal.record(_make_entry(
        trial_id=42, quality=0.85, speed=55.0, cost=0.25, reliability=0.95,
    ))
    assert len(archive._all_entries) == 0
    result = autopilot._maybe_reimport_pareto_from_journal(archive, journal, 42)
    assert result is True
    assert len(archive._all_entries) == 1
    re_imported = archive._all_entries[0]
    assert re_imported.trial_id == 42
    # Convention check: ParetoEntry.objectives uses (quality, speed, -cost, reliability)
    assert re_imported.objectives == (0.85, 55.0, -0.25, 0.95)


def test_reimport_does_not_persist_archive_before_journal_authority_sync(
    journal: ExperimentJournal,
    archive: ParetoArchive,
) -> None:
    journal.record(_make_entry(trial_id=43))
    assert not hasattr(archive, "save")

    assert autopilot._maybe_reimport_pareto_from_journal(archive, journal, 43) is True
    assert [entry.trial_id for entry in archive._all_entries] == [43]
