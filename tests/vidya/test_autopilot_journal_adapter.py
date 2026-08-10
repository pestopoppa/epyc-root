"""SC6 read half: grade the tuple the autopilot recorded about itself.

The end-to-end test here writes a journal with the ORCHESTRATOR's real `ExperimentJournal.record()`
and reads it back with this adapter. A fixture hand-built in the shape I imagine the writer uses
would pass while the two halves disagreed — the write and read sides were authored in the same
sitting, which is exactly when that mistake is easiest to make and hardest to see.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import autopilot_journal as apj  # noqa: E402

ORCH = ROOT / "repos" / "epyc-orchestrator"


def write_journal(tmp_path: Path, rows: list[dict]) -> Path:
    d = tmp_path / apj.ORCH_REL / "orchestration"
    d.mkdir(parents=True)
    (d / "autopilot_journal.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows))
    return tmp_path


def row(trial_id=1, **over):
    base = {
        "trial_id": trial_id, "timestamp": "2026-08-12T10:00:00+00:00", "species": "s",
        "action_type": "numeric_trial", "quality": 0.5, "speed": 1.0, "cost": 2.0,
        "measurement": {
            "protocol_id": "autopilot/metric-v1+harness-v1", "reps": 30,
            "reps_basis": "scored:quality_denominator", "date": "2026-08-12",
            "attestation": {"locator": "autopilot_journal.jsonl#trial-1",
                            "sha256": "a" * 64, "git_tag": "autopilot/trial-1"},
        },
    }
    base.update(over)
    return base


# --- what is read, and what is refused ----------------------------------------------------

def test_a_row_without_a_tuple_is_skipped_not_backfilled(tmp_path):
    """Every trial before 2026-08-10 predates the hook; inventing provenance for them is the bug."""
    r = row()
    del r["measurement"]
    assert list(apj.iter_measured_rows(write_journal(tmp_path, [r]))) == []


def test_a_capture_error_row_is_skipped(tmp_path):
    r = row(measurement={"capture_error": "RuntimeError: boom"})
    assert list(apj.iter_measured_rows(write_journal(tmp_path, [r]))) == []


def test_ledger_events_are_not_trials(tmp_path):
    root = write_journal(tmp_path, [{"type": "supersession", "measurement": {"protocol_id": "x"}}])
    assert list(apj.iter_measured_rows(root)) == []


def test_a_torn_line_does_not_abort_the_scan(tmp_path):
    d = tmp_path / apj.ORCH_REL / "orchestration"
    d.mkdir(parents=True)
    (d / "autopilot_journal.jsonl").write_text(
        json.dumps(row(1)) + "\n{partial" + "\n" + json.dumps(row(2)) + "\n")
    assert len(list(apj.iter_measured_rows(tmp_path))) == 2


# --- identity ------------------------------------------------------------------------------

def test_trial_ids_from_different_shards_do_not_collide(tmp_path):
    """Trial ids restart per shard, so the bare id is not unique across a rotated journal."""
    d = tmp_path / apj.ORCH_REL / "orchestration"
    d.mkdir(parents=True)
    (d / "autopilot_journal.jsonl").write_text(json.dumps(row(7)) + "\n")
    (d / "autopilot_journal_1.jsonl").write_text(json.dumps(row(7)) + "\n")
    ids = {f["assertion"]["claim_id"]
           for shard, r in apj.iter_measured_rows(tmp_path)
           for f in apj.frames_for_row(shard, r, as_of="t")
           if f["frame_type"].endswith("claim_proposed/v1")}
    assert len(ids) == 2, "two shards collapsed into one claim"


# --- grading -------------------------------------------------------------------------------

def test_a_full_tuple_with_the_shard_on_disk_reaches_attested(tmp_path):
    root = write_journal(tmp_path, [row()])
    shard, r = next(apj.iter_measured_rows(root))
    from measurement_record import grade
    rec = apj.as_record(shard, r)
    # `as_record` builds a repo-relative path; point the grader at this fixture tree.
    import measurement_record
    orig, measurement_record.REPO_ROOT = measurement_record.REPO_ROOT, root
    try:
        assert grade(rec)[:2] == ("Witnessed", "Attested")
    finally:
        measurement_record.REPO_ROOT = orig


def test_a_missing_protocol_makes_it_an_observation(tmp_path):
    r = row(measurement={**row()["measurement"], "protocol_id": ""})
    shard, got = next(apj.iter_measured_rows(write_journal(tmp_path, [r])))
    sup = [f for f in apj.frames_for_row(shard, got, as_of="t")
           if f["frame_type"].endswith("evidence_supports_claim/v1")][0]
    assert sup["assertion"]["grade"]["Q"] == "Judged"


def test_an_attempted_denominator_is_flagged_in_the_reasons(tmp_path):
    r = row(measurement={**row()["measurement"], "reps_basis": "attempted:total", "reps": 55})
    shard, got = next(apj.iter_measured_rows(write_journal(tmp_path, [r])))
    sup = [f for f in apj.frames_for_row(shard, got, as_of="t")
           if f["frame_type"].endswith("evidence_supports_claim/v1")][0]
    assert any("ATTEMPTED" in x for x in sup["provenance"]["grade_reasons"])


def test_a_trial_is_always_a_candidate(tmp_path):
    """A trial is a proposed change being measured — never the standing baseline or an optimum."""
    shard, r = next(apj.iter_measured_rows(write_journal(tmp_path, [row()])))
    assert apj.as_record(shard, r)["category"] == "CANDIDATE"


# --- the write and read halves actually agree ---------------------------------------------

@pytest.mark.skipif(not (ORCH / "scripts" / "autopilot" / "experiment_journal.py").exists(),
                    reason="orchestrator repo not present")
def test_end_to_end_against_the_real_writer(tmp_path, monkeypatch):
    sys.path.insert(0, str(ORCH / "scripts" / "autopilot"))
    from experiment_journal import ExperimentJournal, JournalEntry

    d = tmp_path / apj.ORCH_REL / "orchestration"
    d.mkdir(parents=True)
    ExperimentJournal(journal_dir=d).record(JournalEntry(
        trial_id=1, timestamp="2026-08-12T10:00:00+00:00", species="s",
        action_type="numeric_trial", tier=1, quality=0.5, speed=1.0, cost=2.0,
        reliability=0.9, pareto_status="candidate",
        harness_metrics={"schema_version": 1},
        eval_details={"details": {"quality_denominator": 30}}))

    measured = list(apj.iter_measured_rows(tmp_path))
    assert len(measured) == 1, "the adapter could not read what the writer produced"
    shard, r = measured[0]
    rec = apj.as_record(shard, r)
    assert rec["protocol_id"] == "autopilot/metric-v1+harness-v1"
    assert (rec["reps"], rec["reps_basis"]) == (30, "scored:quality_denominator")
    assert len(rec["attestation"]["sha256"]) == 64

    import measurement_record
    orig, measurement_record.REPO_ROOT = measurement_record.REPO_ROOT, tmp_path
    try:
        assert measurement_record.grade(rec)[:2] == ("Witnessed", "Attested")
    finally:
        measurement_record.REPO_ROOT = orig
