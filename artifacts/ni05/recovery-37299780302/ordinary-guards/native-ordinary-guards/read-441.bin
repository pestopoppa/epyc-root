"""W3 rotation snapshots: each closing journal segment is chained with a snapshot row,
and rebuild = latest snapshot + tail fold equals a full fold of the whole journal.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import experiment_journal as ej  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from src.autopilot_core.journal_reconstruction import (  # noqa: E402
    reconstruct_archive_from_journal_rows,
)
from src.autopilot_core.journal_snapshot_replay import (  # noqa: E402
    archive_payload_from_verified_snapshot,
    build_snapshot_replay_diagnostic,
    verify_snapshot_chain,
)

T0 = datetime(2026, 6, 14, tzinfo=timezone.utc)

# Sparse trial ids straddle two rotations (segment 0 -> 1 -> 2) without writing
# thousands of rows; objectives vary so the frontier genuinely moves in the tail.
FIXTURE = [
    (995, 1.10, 40.0), (996, 1.30, 38.0), (997, 1.05, 44.0), (998, 1.20, 30.0), (999, 1.35, 35.0),
    (1000, 1.40, 36.0), (1001, 1.00, 50.0), (1002, 1.25, 41.0), (1003, 1.45, 20.0),
    (1995, 1.50, 34.0), (1996, 1.38, 45.0), (1997, 0.90, 60.0),
    (2000, 1.55, 33.0), (2001, 1.42, 47.0), (2002, 1.60, 25.0), (2003, 1.33, 52.0),
]


def _entry(trial_id: int, quality: float, speed: float) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp=(T0 + timedelta(minutes=trial_id)).isoformat(),
        species="unit",
        action_type="structural_experiment",
        tier=1,
        quality=quality,
        speed=speed,
        cost=0.2,
        reliability=0.9,
        pareto_status="frontier",
        config_snapshot={"type": "structural_experiment", "flags": {f"f{trial_id % 7}": True}},
    )


def _rows(journal: ExperimentJournal) -> list[dict]:
    rows = [asdict(e) for e in journal.all_entries()]
    rows.extend(journal.ledger_events())
    return rows


def _full_fold(rows: list[dict]) -> dict:
    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)
    assert archive is not None
    return archive


def _canon(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


@pytest.fixture
def journal(tmp_path: Path) -> ExperimentJournal:
    j = ExperimentJournal(journal_dir=tmp_path)
    for trial_id, quality, speed in FIXTURE:
        j.record(_entry(trial_id, quality, speed))
    return j


def test_each_rotation_appends_one_chained_snapshot_to_the_closing_shard(journal, tmp_path):
    events = journal.journal_snapshot_events()
    assert [e["through_trial_id"] for e in events] == [999, 1997]
    assert events[0]["parent_snapshot_hash"] == ""
    assert events[1]["parent_snapshot_hash"] == events[0]["snapshot_hash"]
    assert events[0]["policy_version"] == ej.SEGMENT_SNAPSHOT_POLICY_VERSION
    assert events[0]["actor"] == "experiment_journal.segment_rollover"
    assert events[0]["snapshot"]["segment"] == {
        "batch": 0, "shard": "autopilot_journal.jsonl", "first_trial_id": 995,
        "last_trial_id": 999, "trial_count": 5, "next_trial_id": 1000,
    }
    assert events[1]["snapshot"]["segment"]["batch"] == 1
    assert events[1]["snapshot"]["segment"]["trial_count"] == 7

    # the snapshot row is the last row of the shard it closes
    shard0 = (tmp_path / "autopilot_journal.jsonl").read_text().splitlines()
    shard1 = (tmp_path / "autopilot_journal_1.jsonl").read_text().splitlines()
    assert json.loads(shard0[-1])["type"] == ej.JOURNAL_SNAPSHOT_EVENT_TYPE
    assert json.loads(shard1[-1])["type"] == ej.JOURNAL_SNAPSHOT_EVENT_TYPE
    assert "trial_id" not in json.loads(shard1[-1])

    chain = verify_snapshot_chain(ExperimentJournal(journal_dir=tmp_path).ledger_events())
    assert chain["status"] == "ok"
    assert chain["length"] == 2
    assert chain["head_through_trial_id"] == 1997


def test_segment_snapshots_do_not_count_as_trials(journal, tmp_path):
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.count() == len(FIXTURE)
    assert reloaded.next_trial_id() == 2004


def test_rebuild_from_snapshot_plus_tail_equals_full_fold(journal, tmp_path):
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    rows = _rows(reloaded)
    events = reloaded.ledger_events()

    diagnostic = build_snapshot_replay_diagnostic(rows, events)
    assert diagnostic.hash_status == "match"
    assert diagnostic.bounded_replay_readiness == "tail_unverified"
    assert diagnostic.tail_trial_count == 4  # trials 2000-2003

    rebuilt = archive_payload_from_verified_snapshot(rows, events)
    assert rebuilt is not None
    assert _canon(rebuilt) == _canon(_full_fold(rows))


def test_rebuild_equals_full_fold_with_tail_supersession(journal, tmp_path):
    journal.append_supersession_event(
        target_trial_ids=[2002],
        fields={"bug_corrupted_by": "deadbeef", "bug_corrupted_reason": "unit"},
        reason="unit tail supersession",
        policy_version="unit",
        actor="unit-test",
    )
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    rows = _rows(reloaded)
    rebuilt = archive_payload_from_verified_snapshot(rows, reloaded.ledger_events())
    full = _full_fold(rows)
    assert rebuilt is not None
    assert _canon(rebuilt) == _canon(full)
    assert 2002 not in {e.get("trial_id") for e in full.get("entries", [])}


def test_snapshot_prefix_equals_full_fold_of_its_prefix(journal, tmp_path):
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    rows = _rows(reloaded)
    last = reloaded.latest_journal_snapshot_event()
    prefix = [r for r in rows if r.get("trial_id") is None or r["trial_id"] <= 1997]
    assert _canon(last["snapshot"]["archive"]) == _canon(_full_fold(
        [r for r in prefix if r.get("type") != ej.JOURNAL_SNAPSHOT_EVENT_TYPE]
    ))


def test_no_duplicate_snapshot_when_segment_already_covered(tmp_path):
    j = ExperimentJournal(journal_dir=tmp_path)
    j.record(_entry(998, 1.0, 40.0))
    j.record(_entry(999, 1.1, 41.0))
    from journal_snapshot_create import append_archive_snapshot, build_archive_snapshot

    append_archive_snapshot(j, build_archive_snapshot(j), actor="operator")
    j.record(_entry(1000, 1.2, 39.0))
    assert [e["actor"] for e in j.journal_snapshot_events()] == ["operator"]


def test_disabled_or_failing_snapshot_never_blocks_recording(tmp_path, monkeypatch):
    off = ExperimentJournal(journal_dir=tmp_path / "off", segment_snapshots=False)
    off.record(_entry(999, 1.0, 40.0))
    off.record(_entry(1000, 1.1, 41.0))
    assert off.journal_snapshot_events() == []

    import scripts.autopilot.journal_snapshot_create as journal_snapshot_create

    def boom(*_a, **_k):
        raise RuntimeError("replay exploded")

    monkeypatch.setattr(journal_snapshot_create, "build_archive_snapshot", boom)
    j = ExperimentJournal(journal_dir=tmp_path / "boom")
    j.record(_entry(999, 1.0, 40.0))
    j.record(_entry(1000, 1.1, 41.0))
    assert j.count() == 2
    assert j.journal_snapshot_events() == []


def test_chain_verifier_detects_broken_parent_and_tampered_hash(journal, tmp_path):
    events = ExperimentJournal(journal_dir=tmp_path).ledger_events()
    broken = [dict(e) for e in events]
    broken[1]["parent_snapshot_hash"] = "0" * 64
    defects = {b["defect"] for b in verify_snapshot_chain(broken)["breaks"]}
    assert defects == {"parent_mismatch", "hash_mismatch"}

    tampered = [dict(e) for e in events]
    tampered[0] = dict(tampered[0], snapshot={**tampered[0]["snapshot"], "extra": 1})
    result = verify_snapshot_chain(tampered)
    assert result["status"] == "broken"
    assert result["breaks"][0] == {"position": 0, "defect": "hash_mismatch"}
    assert verify_snapshot_chain([])["status"] == "no_snapshots"


# ── authority consumption must respect the era scope a snapshot was folded under ──


def test_authority_ignores_snapshot_folded_without_live_epoch_exclusion(journal, monkeypatch):
    import autopilot

    rows = autopilot._journal_rows_for_archive(journal)
    calls: list = []
    real = autopilot.reconstruct_archive_from_journal_rows

    def spy(*args, **kwargs):
        calls.append(kwargs.get("exclude_before_ts"))
        return real(*args, **kwargs)

    monkeypatch.setattr(autopilot, "reconstruct_archive_from_journal_rows", spy)
    epoch = (T0 + timedelta(minutes=1996)).timestamp()
    scoped = autopilot._journal_archive_payload_for_authority(journal, exclude_before_ts=epoch)
    assert calls == [epoch]  # full replay under the live scope, not the unscoped snapshot
    assert {e["trial_id"] for e in scoped["all_entries"]} >= {2000}
    assert min(e["trial_id"] for e in scoped["all_entries"]) >= 1996

    calls.clear()
    unscoped = autopilot._journal_archive_payload_for_authority(journal)
    assert calls == []  # snapshot + tail fold satisfied authority
    assert _canon(unscoped) == _canon(_full_fold(rows))


def test_snapshot_scope_matcher():
    import autopilot

    match = autopilot._snapshot_scope_matches
    assert match({"exclusions": {}}, exclude_before_ts=None, deinflate_before_ts=None, deinflate_factor=1.0)
    assert not match({"exclusions": {}}, exclude_before_ts=5.0, deinflate_before_ts=None, deinflate_factor=1.0)
    assert match({"exclusions": {"exclude_before_ts": 5}}, exclude_before_ts=5.0,
                 deinflate_before_ts=None, deinflate_factor=1.0)
    assert not match({"exclusions": {"exclude_before_ts": 5}}, exclude_before_ts=None,
                     deinflate_before_ts=None, deinflate_factor=1.0)
    assert not match({"exclusions": {}}, exclude_before_ts=None, deinflate_before_ts=1.0,
                     deinflate_factor=0.5)


# ── scoped segment snapshots (live epoch exclusion) ───────────────────────────

EPOCH = (T0 + timedelta(minutes=1996)).timestamp()


@pytest.fixture
def scoped_journal(tmp_path: Path) -> ExperimentJournal:
    from src.autopilot_core.tier_specs import LEGACY_OBJECTIVE_POLICY

    j = ExperimentJournal(journal_dir=tmp_path)
    j.segment_snapshot_scope = {
        "objective_policy": LEGACY_OBJECTIVE_POLICY,
        "exclude_before_ts": EPOCH,
    }
    for trial_id, quality, speed in FIXTURE:
        j.record(_entry(trial_id, quality, speed))
    return j


def test_scoped_snapshot_records_scope_and_verifies_under_it(scoped_journal, tmp_path):
    last = scoped_journal.latest_journal_snapshot_event()
    assert last["snapshot"]["archive"]["exclusions"]["exclude_before_ts"] == EPOCH
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    rows = _rows(reloaded)
    diagnostic = build_snapshot_replay_diagnostic(rows, reloaded.ledger_events())
    assert diagnostic.status == "archive_prefix_match"
    assert diagnostic.bounded_replay_readiness == "tail_unverified"
    rebuilt = archive_payload_from_verified_snapshot(rows, reloaded.ledger_events())
    full = reconstruct_archive_from_journal_rows(
        rows, None, current_run_only=False, exclude_before_ts=EPOCH
    )
    assert _canon(rebuilt) == _canon(full)


def test_authority_consumes_scoped_snapshot_under_matching_scope(scoped_journal, monkeypatch):
    import autopilot

    calls: list = []
    real = autopilot.reconstruct_archive_from_journal_rows

    def spy(*args, **kwargs):
        calls.append(kwargs.get("exclude_before_ts"))
        return real(*args, **kwargs)

    monkeypatch.setattr(autopilot, "reconstruct_archive_from_journal_rows", spy)
    payload = autopilot._journal_archive_payload_for_authority(
        scoped_journal, exclude_before_ts=EPOCH
    )
    assert calls == []
    assert min(e["trial_id"] for e in payload["all_entries"]) >= 1996
    # a different live scope falls back to the full replay
    autopilot._journal_archive_payload_for_authority(scoped_journal)
    assert calls == [None]


def test_pre_epoch_tail_row_forces_full_replay(tmp_path):
    from src.autopilot_core.tier_specs import LEGACY_OBJECTIVE_POLICY

    j = ExperimentJournal(journal_dir=tmp_path)
    j.segment_snapshot_scope = {"objective_policy": LEGACY_OBJECTIVE_POLICY,
                                "exclude_before_ts": EPOCH}
    j.record(_entry(1995, 1.2, 40.0))
    late = _entry(1997, 1.3, 41.0)
    late.timestamp = (T0 + timedelta(minutes=1997)).isoformat()
    j.record(late)
    early_tail = _entry(2000, 1.4, 42.0)
    early_tail.timestamp = (T0 + timedelta(minutes=10)).isoformat()  # before the epoch
    j.record(early_tail)
    rows = _rows(j)
    assert archive_payload_from_verified_snapshot(rows, j.ledger_events()) is None


def test_scope_sync_follows_state_and_disables_under_deinflation(tmp_path):
    import autopilot

    j = ExperimentJournal(journal_dir=tmp_path)
    autopilot._sync_segment_snapshot_scope(j, {
        "pareto_exclude_before_ts": 123.0,
        "pareto_objective_policy": "legacy_4d_v1",
    })
    assert j.segment_snapshot_scope == {"objective_policy": "legacy_4d_v1",
                                        "exclude_before_ts": 123.0}
    assert j.segment_snapshots is True
    autopilot._sync_segment_snapshot_scope(j, {
        "pareto_epoch_ts": 100.0, "pareto_pre_epoch_speed_factor": 0.5,
    })
    assert j.segment_snapshots is False
