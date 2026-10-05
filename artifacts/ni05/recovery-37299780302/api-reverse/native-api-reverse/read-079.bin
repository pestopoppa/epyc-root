"""Autopilot quality-axis era fence: startup migration + evidence-read fence (defect #1/#2).

Covers the code-path state migration that seeds active_instrument_eras.eval_quality +
quality_epoch_ts / quality_exclude_before_ts, the strict/fail-closed epoch reader, and the
timestamp fence on the sequential-promotion evidence fold (rows straddling the boundary).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
import src.autopilot_core.instrument_era_guard as era_guard  # noqa: E402
from src.autopilot_core.instrument_era_guard import (  # noqa: E402
    INSTRUMENT_ERAS_ENV,
    E7_EVAL_INSTRUMENT_ERA_ID,
)

_E7_EPOCH = datetime(2026, 7, 21, 10, 30, tzinfo=timezone.utc).timestamp()

_POST = "2026-07-22T00:00:00Z"  # after the E7 boundary
_PRE = "2026-06-18T00:00:00Z"  # before the E7 boundary

_E7_REGISTRY = """
eras:
  - id: E7-eval-instrument
    from: "2026-07-21T10:30:00Z"
    scope: eval_quality
"""

_FUTURE_REGISTRY = """
eras:
  - id: E9-future
    from: "2099-01-01T00:00:00Z"
    scope: eval_quality
"""


def _write_registry(tmp_path: Path, body: str, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "instrument_eras.yaml"
    path.write_text(body)
    monkeypatch.setenv(INSTRUMENT_ERAS_ENV, str(path))
    return path


def _entry(trial_id: int, action: dict, *, correct: bool, timestamp: str) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp=timestamp,
        species="test",
        action_type=str(action.get("type") or "seed_batch"),
        tier=1,
        quality=3.0 if correct else 0.0,
        speed=10.0,
        cost=0.2,
        reliability=1.0,
        pareto_status="frontier",
        config_snapshot=dict(action),
        eval_details={
            "eval_wall_s": 1800.0,
            "question_results": [{"qid": "q1", "correct": correct}],
        },
        seq={},
        bug_corrupted_by="",
        outcome_status="ok",
    )


# ---- startup migration ----------------------------------------------------------------


def test_migration_seeds_fence_from_registry(tmp_path, monkeypatch) -> None:
    _write_registry(tmp_path, _E7_REGISTRY, monkeypatch)
    state: dict = {}
    changed = autopilot._migrate_eval_quality_era(state)
    assert changed is True
    assert state["active_instrument_eras"]["eval_quality"] == "E7-eval-instrument"
    assert state["quality_epoch_ts"] == _E7_EPOCH
    assert state["quality_exclude_before_ts"] == _E7_EPOCH


def test_migration_is_idempotent(tmp_path, monkeypatch) -> None:
    _write_registry(tmp_path, _E7_REGISTRY, monkeypatch)
    state: dict = {}
    assert autopilot._migrate_eval_quality_era(state) is True
    # Second run must not re-migrate (or clobber an operator-set era).
    assert autopilot._migrate_eval_quality_era(state) is False


def test_migration_preserves_existing_speed_era_key(tmp_path, monkeypatch) -> None:
    _write_registry(tmp_path, _E7_REGISTRY, monkeypatch)
    state: dict = {"active_instrument_eras": {"autopilot_speed": "E6-autopilot-speed"}}
    autopilot._migrate_eval_quality_era(state)
    eras = state["active_instrument_eras"]
    assert eras["autopilot_speed"] == "E6-autopilot-speed"
    assert eras["eval_quality"] == "E7-eval-instrument"


def test_migration_noop_when_no_era_active_yet(tmp_path, monkeypatch) -> None:
    # Registry present but its only eval_quality era opens in 2099 => unfenced today.
    _write_registry(tmp_path, _FUTURE_REGISTRY, monkeypatch)
    state: dict = {}
    assert autopilot._migrate_eval_quality_era(state) is False
    assert "active_instrument_eras" not in state or "eval_quality" not in state.get(
        "active_instrument_eras", {}
    )


def test_migration_falls_forward_to_the_last_recorded_era_when_registry_missing(
    tmp_path, monkeypatch
) -> None:
    """REPLACES test_migration_falls_forward_to_code_constant_when_registry_missing.

    That test asserted the fallback stamped E7_EVAL_INSTRUMENT_ERA_ID — i.e. its
    passing condition WAS the defect. The constant stopped tracking the live era at
    the v8 eval boundary on 2026-07-25 and eval_quality is now E16, so fencing there
    under-fenced by three weeks: every cross-instrument observation in that span read
    as in-era and was admitted to the quality decision plane. A guard whose green
    state requires the fail-open cannot survive the fix.

    The fallback now reads the last era the live system RECORDED, so it tracks every
    future cutover instead of needing a human to bump a literal.
    """
    monkeypatch.setenv(INSTRUMENT_ERAS_ENV, str(tmp_path / "absent.yaml"))
    recorded_epoch = _E7_EPOCH + 30 * 86400.0
    state_file = tmp_path / "autopilot_state.json"
    state_file.write_text(
        json.dumps(
            {
                "active_instrument_eras": {"eval_quality": "E16-some-later-era"},
                "quality_exclude_before_ts": recorded_epoch,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(era_guard, "AUTOPILOT_STATE_PATH", state_file)
    monkeypatch.setattr(autopilot.time, "time", lambda: recorded_epoch + 86400.0)

    state: dict = {}
    assert autopilot._migrate_eval_quality_era(state) is True
    assert state["active_instrument_eras"]["eval_quality"] == "E16-some-later-era"
    assert state["quality_exclude_before_ts"] == recorded_epoch
    # The stale constant must NOT be what it fenced on.
    assert state["active_instrument_eras"]["eval_quality"] != E7_EVAL_INSTRUMENT_ERA_ID


def test_migration_refuses_rather_than_substituting_a_stale_boundary(
    tmp_path, monkeypatch
) -> None:
    """No registry AND no recorded era => leave the axis unfenced, loudly.

    An unfenced quality axis is visibly wrong. A wrongly-fenced one looks correct,
    which is worse — it is the shape that let three weeks of cross-instrument
    evidence in without anyone noticing.
    """
    monkeypatch.setenv(INSTRUMENT_ERAS_ENV, str(tmp_path / "absent.yaml"))
    monkeypatch.setattr(era_guard, "AUTOPILOT_STATE_PATH", tmp_path / "absent-state.json")
    monkeypatch.setattr(autopilot.time, "time", lambda: _E7_EPOCH + 86400.0)
    state: dict = {}
    assert autopilot._migrate_eval_quality_era(state) is False
    assert "active_instrument_eras" not in state
    assert "quality_exclude_before_ts" not in state


def test_migration_defers_when_registry_missing_and_before_boundary(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(INSTRUMENT_ERAS_ENV, str(tmp_path / "absent.yaml"))
    monkeypatch.setattr(autopilot.time, "time", lambda: _E7_EPOCH - 86400.0)
    state: dict = {}
    assert autopilot._migrate_eval_quality_era(state) is False


# ---- strict epoch reader (fail-closed) ------------------------------------------------


def test_quality_epoch_params_returns_none_when_unfenced() -> None:
    assert autopilot._quality_epoch_params_from_state({}) == (None, None)


def test_quality_epoch_params_reads_era_and_ts() -> None:
    state = {
        "active_instrument_eras": {"eval_quality": "E7-eval-instrument"},
        "quality_exclude_before_ts": _E7_EPOCH,
    }
    era, ts = autopilot._quality_epoch_params_from_state(state)
    assert era == "E7-eval-instrument"
    assert ts == _E7_EPOCH


def test_quality_epoch_params_raises_when_era_declared_without_ts() -> None:
    state = {"active_instrument_eras": {"eval_quality": "E7-eval-instrument"}}
    with pytest.raises(ValueError):
        autopilot._quality_epoch_params_from_state(state)


# ---- evidence-read fence (rows straddling the boundary) --------------------------------


def test_seq_inputs_fence_excludes_pre_boundary_rows(tmp_path) -> None:
    action = {"type": "seed_batch", "n_questions": 10}
    journal = ExperimentJournal(journal_dir=tmp_path)
    # Pre-boundary frontier rows (WRONG) — priors that would drag the null profile down.
    for tid in (1, 2, 3):
        journal.record(_entry(tid, action, correct=False, timestamp=_PRE))
    # Post-boundary frontier rows (RIGHT).
    for tid in (4, 5, 6):
        journal.record(_entry(tid, action, correct=True, timestamp=_POST))

    fenced = autopilot._seq_inputs_for_trial(
        journal=journal, action=action, tier=1, quality_exclude_before_ts=_E7_EPOCH
    )
    unfenced = autopilot._seq_inputs_for_trial(journal=journal, action=action, tier=1)

    # Fenced: only the 3 post-boundary correct rows fold in => clean {"q1": 1.0}.
    assert fenced["baseline_profile"] == {"q1": pytest.approx(1.0)}
    # Unfenced: the pre-boundary wrong rows contaminate the mixture (mean over 6 rows).
    assert unfenced["baseline_profile"] == {"q1": pytest.approx(0.5)}


def test_seq_inputs_fence_marks_unavailable_when_too_few_post_boundary(tmp_path) -> None:
    action = {"type": "seed_batch", "n_questions": 10}
    journal = ExperimentJournal(journal_dir=tmp_path)
    for tid in (1, 2, 3):
        journal.record(_entry(tid, action, correct=True, timestamp=_PRE))  # priors
    journal.record(_entry(4, action, correct=True, timestamp=_POST))  # only 1 post-boundary

    fenced = autopilot._seq_inputs_for_trial(
        journal=journal, action=action, tier=1, quality_exclude_before_ts=_E7_EPOCH
    )
    # < SEQ_BASELINE_PROFILE_MIN_TRIALS post-boundary rows => profile UNAVAILABLE (empty),
    # so the gate's sequential path is skipped rather than run on a thin post-boundary mixture.
    assert fenced["baseline_profile"] == {}
