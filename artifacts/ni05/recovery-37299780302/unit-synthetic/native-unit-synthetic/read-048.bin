"""AP-63(a) (S3-AP-01): the AP-1510 run manifest and an explicit parent on journal rows.

Pins: the dispatch-bound manifest is copied from the in-flight WAL marker onto the
row (main loop, dispatcher skips, the AUTOPILOT_KILLED placeholder); a marker for
another trial, a legacy marker or no marker yields no manifest (never one built at
write time); legacy rows load with empty fields and are never back-filled; the
explicit parent is the newest same-species trial with a COMMITTED baseline
promotion, never a pending/uncommitted, bug-corrupted, other-species or later row.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # noqa: E402
from experiment_journal import (  # noqa: E402
    LINEAGE_HEURISTIC_RULE,
    LINEAGE_PARENT_RULE,
    ExperimentJournal,
    JournalEntry,
    SupersessionEvent,
    measurement_tuple,
    select_lineage_parent,
)
from pareto_archive import ParetoArchive  # noqa: E402
from run_manifest import build_run_manifest  # noqa: E402


def _entry(trial_id: int, species: str = "seeder", **kw) -> JournalEntry:
    base = dict(
        trial_id=trial_id,
        timestamp="2026-09-17T00:00:00+00:00",
        species=species,
        action_type="seed_batch",
        tier=1,
        quality=2.0,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
        pareto_status="frontier",
    )
    base.update(kw)
    return JournalEntry(**base)


def _promote(journal: ExperimentJournal, trial_id: int) -> None:
    journal.append_baseline_promotion_event(
        source_trial_id=trial_id,
        tier=1,
        previous_quality=1.0,
        new_quality=2.0,
        reason="test",
        proof={},
        result_metrics={},
        baseline_state={},
    )


@pytest.fixture
def journal(tmp_path: Path) -> ExperimentJournal:
    return ExperimentJournal(journal_dir=tmp_path / "journal", segment_snapshots=False)


@pytest.fixture
def manifest(tmp_path: Path) -> dict:
    src = tmp_path / "src.py"
    src.write_text("x = 1\n", encoding="utf-8")
    return build_run_manifest(
        source_paths={"autopilot": src},
        task={"type": "seed_batch"},
        evaluator={"class": "EvalTower", "url": "http://127.0.0.1:8000"},
    )


# ── manifest selection from the WAL marker ───────────────────────────────


def test_in_flight_manifest_is_copied_for_the_matching_trial(manifest):
    state = {"in_flight_trial": {"trial_id": 4, "run_manifest": manifest}}
    got = autopilot._in_flight_run_manifest(state, 4)
    assert got == manifest
    got["sources"] = {}
    assert state["in_flight_trial"]["run_manifest"] == manifest  # a copy, not an alias


@pytest.mark.parametrize(
    "marker",
    [
        None,  # never dispatched (pre-dispatch skip)
        {"trial_id": 5, "run_manifest": {"manifest_sha256": "x"}},  # another trial
        {"trial_id": 4},  # legacy marker
        {"trial_id": 4, "run_manifest": "not-a-dict"},
        {"trial_id": "garbage", "run_manifest": {"manifest_sha256": "x"}},
    ],
)
def test_no_manifest_is_invented(marker):
    assert autopilot._in_flight_run_manifest({"in_flight_trial": marker}, 4) == {}


# ── row round-trip, legacy load, claim tuple ─────────────────────────────


def test_row_round_trips_manifest_and_lineage(journal, tmp_path, manifest):
    lineage = {"rule": LINEAGE_PARENT_RULE, "parent_trial_id": None}
    journal.record(_entry(0, run_manifest=manifest, lineage=lineage))
    reloaded = ExperimentJournal(journal_dir=tmp_path / "journal", segment_snapshots=False)
    row = reloaded.all_entries()[0]
    assert row.run_manifest == manifest
    assert row.lineage == lineage
    assert row.measurement["run_manifest"] == manifest["manifest_sha256"]


def test_legacy_row_loads_empty_and_is_not_backfilled(journal, tmp_path):
    journal.record(_entry(0))
    jsonl = next((tmp_path / "journal").glob("*.jsonl"))
    rows = [json.loads(line) for line in jsonl.read_text().splitlines()]
    for row in rows:
        row.pop("run_manifest", None)
        row.pop("lineage", None)
    jsonl.write_text("".join(json.dumps(r) + "\n" for r in rows))
    reloaded = ExperimentJournal(journal_dir=tmp_path / "journal", segment_snapshots=False)
    row = reloaded.all_entries()[0]
    assert row.run_manifest == {}
    assert row.lineage == {}
    assert "run_manifest" not in measurement_tuple(row)


# ── explicit parent selection ────────────────────────────────────────────


def test_no_committed_promotion_means_no_parent(journal):
    journal.record(_entry(0))
    journal.record(_entry(1))
    lin = select_lineage_parent(journal, "seeder", before_trial_id=2)
    assert lin["parent_trial_id"] is None
    assert lin["rule"] == LINEAGE_PARENT_RULE
    # the legacy heuristic is recorded, but decides nothing
    assert lin["heuristic_rule"] == LINEAGE_HEURISTIC_RULE
    assert lin["heuristic_parent_trial_id"] == 1


def test_parent_is_newest_committed_same_species_promotion(journal):
    journal.record(_entry(0))
    _promote(journal, 0)
    journal.record(_entry(1))
    _promote(journal, 1)
    journal.record(_entry(2))  # later, unpromoted (e.g. pending_commit then crash)
    journal.record(_entry(3, species="numeric_swarm"))
    _promote(journal, 3)  # other species
    lin = select_lineage_parent(journal, "seeder", before_trial_id=4)
    assert lin["parent_trial_id"] == 1
    assert lin["parent_promotion_timestamp"]
    assert lin["heuristic_parent_trial_id"] == 2


def test_bug_corrupted_parent_is_skipped_including_by_supersession(journal):
    journal.record(_entry(0))
    _promote(journal, 0)
    journal.record(_entry(1, bug_corrupted_by="abc123"))
    _promote(journal, 1)
    journal.record(_entry(2))
    _promote(journal, 2)
    journal.append_ledger_event(
        {
            **SupersessionEvent(
                target_trial_ids=[2],
                fields={"bug_corrupted_by": "def456"},
                reason="test",
                policy_version="t",
                actor="test",
            ).__dict__
        }
    )
    lin = select_lineage_parent(journal, "seeder", before_trial_id=3)
    assert lin["parent_trial_id"] == 0


def test_trial_is_never_its_own_or_a_later_trials_child(journal):
    journal.record(_entry(0))
    _promote(journal, 0)
    journal.record(_entry(1))
    _promote(journal, 1)
    lin = select_lineage_parent(journal, "seeder", before_trial_id=1)
    assert lin["parent_trial_id"] == 0
    assert lin["heuristic_parent_trial_id"] == 0


def test_promotion_event_for_an_unjournaled_trial_is_ignored(journal):
    journal.record(_entry(0))
    _promote(journal, 0)
    _promote(journal, 9)  # no such row
    lin = select_lineage_parent(journal, "seeder", before_trial_id=10)
    assert lin["parent_trial_id"] == 0


# ── writers ──────────────────────────────────────────────────────────────


def test_skip_trial_row_carries_the_dispatch_manifest(journal, manifest):
    autopilot._record_skip_trial(
        journal, 0, {"type": "seed_batch"}, "seed_batch", "skipped", "why", 0,
        run_manifest=manifest,
    )
    assert journal.all_entries()[0].run_manifest == manifest


def test_skip_trial_without_manifest_stays_empty(journal):
    autopilot._record_skip_trial(
        journal, 0, {"type": "seed_batch"}, "seed_batch", "skipped", "why", 0,
    )
    assert journal.all_entries()[0].run_manifest == {}


def test_killed_placeholder_carries_the_marker_manifest(journal, tmp_path, manifest):
    archive = ParetoArchive(state_path=tmp_path / "archive.json")
    state = {
        "in_flight_trial": {
            "trial_id": 0,
            "action": {"type": "seed_batch"},
            "run_manifest": manifest,
            "host_pid": 1,
            "host_started_at": 1.0,
        },
        "trial_counter": 0,
    }
    autopilot._recover_from_in_flight_trial(state, journal, archive, trial_counter=0)
    row = journal.all_entries()[0]
    assert row.bug_corrupted_by == "autopilot_killed_mid_trial"
    assert row.run_manifest == manifest
    assert state["in_flight_trial"] is None


def test_main_loop_row_passes_manifest_and_lineage():
    source = Path(autopilot.__file__).read_text()
    body = source[source.index("def _run_loop_inner(") :]
    call = body[body.index("journal_entry = JournalEntry(") :]
    call = call[: call.index("journal.record(journal_entry)")]
    assert "run_manifest=_in_flight_run_manifest(state, trial_counter)" in call
    assert "lineage=trial_lineage" in call
    # the selection is computed before the row is journaled
    assert body.index("select_lineage_parent(") < body.index("journal.record(journal_entry)")
    # and the WAL marker is cleared only after the row is written
    assert body.index("journal.record(journal_entry)") < body.index(
        'state["in_flight_trial"] = None\n        _save_state_with_journal_archive_authority'
    )
