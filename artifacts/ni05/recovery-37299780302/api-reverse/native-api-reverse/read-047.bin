"""AP-57 (operator ruled B, 2026-09-17): journal the speed-axis reseed.

RTG-02 made ``SafetyGate.update_baseline`` re-anchor the SPEED axis (``frontdoor_speed`` +
``autopilot_speed_era``) on the eval-quality re-baseline refusal path. That is a real
``baseline_state`` write, but ``_append_baseline_promotion_event`` returned early for
``updated=False``, so the reseed had no append-only receipt: it could not be audited, and a
ledger fold replayed the state WITHOUT it. These tests fail on the pre-AP-57 code.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
from experiment_journal import (  # type: ignore[import-not-found]  # noqa: E402
    SPEED_AXIS_RESEED_EVENT_TYPE,
    ExperimentJournal,
)
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]  # noqa: E402
from src.autopilot_core.baseline_ledger import (  # noqa: E402
    format_baseline_ledger_summary,
    reconcile_baseline_ledger,
)
from src.autopilot_core.tier_specs import DEFAULT_FRONTIER_TIER  # noqa: E402

_QUALITY_ERA = "E16-eval-instrument"
_SPEED_ERA = "E9-autopilot-speed"
_OLD_SPEED_ERA = "E8-autopilot-speed"


def _result(speed: float = 42.0) -> EvalResult:
    return EvalResult(
        tier=DEFAULT_FRONTIER_TIER,
        quality=2.5,
        speed=speed,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": 2.5},
        per_suite_counts={"coder": 10},
        n_questions=50,
        speed_metric_mode="aggregate_batch_tps",
    )


def _held_gate(tmp_path, monkeypatch) -> SafetyGate:
    g = SafetyGate(
        baseline_path=tmp_path / "absent.yaml",
        eval_quality_era=_QUALITY_ERA,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={
            "eval_quality_era": "E8-eval-instrument",
            "autopilot_speed_era": _OLD_SPEED_ERA,
        },
    )
    g.baseline.frontdoor_speed = 100.0
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "ok", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    return g


def _reseed_outcome(tmp_path, monkeypatch):
    g = _held_gate(tmp_path, monkeypatch)
    outcome = g.update_baseline(_result(), source_trial_id=7)
    assert outcome.updated is False and outcome.speed_reseeded is True
    return g, outcome


def _append(journal, outcome, g, *, trial=7, run_manifest=None):
    return autopilot._append_baseline_promotion_event(
        journal=journal,
        baseline_update=outcome,
        eval_result=_result(),
        source_trial_id=trial,
        pareto_status="frontier",
        baseline_state=g.baseline.to_state_dict(),
        infra_fingerprint={"host": "h"},
        run_manifest=run_manifest,
    )


def test_gate_result_carries_the_reseed_provenance(tmp_path, monkeypatch):
    _, outcome = _reseed_outcome(tmp_path, monkeypatch)
    assert outcome.speed_reseed == {
        "tier": DEFAULT_FRONTIER_TIER,
        "previous_speed": pytest.approx(100.0),
        "new_speed": pytest.approx(42.0),
        "previous_speed_era": _OLD_SPEED_ERA,
        "new_speed_era": _SPEED_ERA,
    }


def test_no_reseed_means_empty_provenance(tmp_path, monkeypatch):
    g = SafetyGate(
        baseline_path=tmp_path / "absent.yaml",
        eval_quality_era=_QUALITY_ERA,
        baseline_state={"eval_quality_era": "E8-eval-instrument"},
    )
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "ok", {"x": 1}))
    outcome = g.update_baseline(_result(), source_trial_id=1)
    assert outcome.speed_reseeded is False
    assert outcome.speed_reseed == {}


def test_reseed_on_quality_refusal_appends_a_receipt(tmp_path, monkeypatch):
    g, outcome = _reseed_outcome(tmp_path, monkeypatch)
    journal = ExperimentJournal(journal_dir=tmp_path / "j")
    manifest = {"schema_version": 1, "manifest_sha256": "abc123"}

    event = _append(journal, outcome, g, run_manifest=manifest)

    assert event is not None, "pre-AP-57 the updated=False early return wrote nothing"
    assert event["type"] == SPEED_AXIS_RESEED_EVENT_TYPE
    assert event["source_trial_id"] == 7
    assert event["previous_speed"] == pytest.approx(100.0)
    assert event["new_speed"] == pytest.approx(42.0)
    assert event["previous_speed_era"] == _OLD_SPEED_ERA
    assert event["new_speed_era"] == _SPEED_ERA
    assert event["reason"] == "quality_refusal"
    assert event["refusal_reason"] == "quality_rebaseline_required"
    assert event["run_manifest_sha256"] == "abc123"
    assert event["eval_quality_era"] == "E8-eval-instrument"
    assert event["timestamp"]
    assert event["baseline_state"]["frontdoor_speed"] == pytest.approx(42.0)
    assert event["infra_fingerprint"] == {"host": "h"}
    # durable, and never counted as a promotion
    reloaded = ExperimentJournal(journal_dir=tmp_path / "j")
    assert reloaded.speed_axis_reseed_events() == [event]
    assert reloaded.baseline_promotion_events() == []
    assert reloaded.baseline_ledger_events() == [event]


def test_reseed_receipt_is_idempotent_per_trial(tmp_path, monkeypatch):
    g, outcome = _reseed_outcome(tmp_path, monkeypatch)
    journal = ExperimentJournal(journal_dir=tmp_path / "j")
    first = _append(journal, outcome, g)
    second = _append(journal, outcome, g)
    assert second == first
    assert len(ExperimentJournal(journal_dir=tmp_path / "j").speed_axis_reseed_events()) == 1
    _append(journal, outcome, g, trial=8)
    assert len(journal.speed_axis_reseed_events()) == 2


def test_plain_refusal_still_writes_nothing(tmp_path):
    from safety_gate import BaselineUpdateResult  # type: ignore[import-not-found]

    journal = ExperimentJournal(journal_dir=tmp_path)
    refused = BaselineUpdateResult(False, "not better", DEFAULT_FRONTIER_TIER, 2.0, 1.9)
    assert autopilot._append_baseline_promotion_event(
        journal=journal,
        baseline_update=refused,
        eval_result=_result(),
        source_trial_id=3,
        pareto_status="dominated",
        baseline_state={},
    ) is None
    assert journal.ledger_events() == []


class _FailingJournal(ExperimentJournal):
    def append_ledger_event(self, event):  # noqa: D401
        raise OSError("disk full")


def test_failed_receipt_is_loud_and_flags_state_but_keeps_state_write(
    tmp_path, monkeypatch, caplog
):
    g, outcome = _reseed_outcome(tmp_path, monkeypatch)
    state: dict = {"in_flight_trial": {"trial_id": 7, "run_manifest": {"manifest_sha256": "d"}}}
    baseline_state = g.baseline.to_state_dict()
    state["baseline_state"] = baseline_state

    with caplog.at_level(logging.WARNING, logger=autopilot.log.name):
        event = autopilot._journal_baseline_ledger_event(
            state,
            journal=_FailingJournal(journal_dir=tmp_path / "bad"),
            baseline_update=outcome,
            eval_result=_result(),
            source_trial_id=7,
            pareto_status="frontier",
            baseline_state=baseline_state,
        )

    assert event is None
    assert any("Speed-axis reseed event append FAILED" in r.message for r in caplog.records)
    flag = state[autopilot.SPEED_AXIS_RESEED_JOURNAL_ERROR_KEY]
    assert flag["trial_id"] == 7 and "disk full" in flag["error"]
    assert state["baseline_state"]["frontdoor_speed"] == pytest.approx(42.0)

    # a later successful receipt clears the flag, and carries the in-flight manifest digest
    good = ExperimentJournal(journal_dir=tmp_path / "good")
    event = autopilot._journal_baseline_ledger_event(
        state,
        journal=good,
        baseline_update=outcome,
        eval_result=_result(),
        source_trial_id=7,
        pareto_status="frontier",
        baseline_state=baseline_state,
    )
    assert event is not None and event["run_manifest_sha256"] == "d"
    assert autopilot.SPEED_AXIS_RESEED_JOURNAL_ERROR_KEY not in state


def test_ledger_fold_replays_the_reseed(tmp_path, monkeypatch):
    g, outcome = _reseed_outcome(tmp_path, monkeypatch)
    journal = ExperimentJournal(journal_dir=tmp_path / "j")
    before = dict(g.baseline.to_state_dict(), frontdoor_speed=100.0,
                  autopilot_speed_era=_OLD_SPEED_ERA)
    journal.append_baseline_promotion_event(
        source_trial_id=5,
        tier=DEFAULT_FRONTIER_TIER,
        previous_quality=None,
        new_quality=2.0,
        reason="seed",
        proof={},
        result_metrics={},
        baseline_state=before,
        actor="unit-test",
    )
    _append(journal, outcome, g)
    live = g.baseline.to_state_dict()

    rec = reconcile_baseline_ledger(journal.baseline_ledger_events(), live)
    assert rec.status == "match", "the fold must include the reseed snapshot"
    assert rec.folded_state["frontdoor_speed"] == pytest.approx(42.0)
    assert rec.folded_state["autopilot_speed_era"] == _SPEED_ERA
    assert rec.event_count == 2 and rec.reseed_event_count == 1

    # the full journal row stream (what report/system-card callers pass) folds the same way
    assert reconcile_baseline_ledger(journal.ledger_events(), live).status == "match"

    lines = format_baseline_ledger_summary(rec)
    assert lines[0] == "Baseline promotion events: 1 (+1 speed-axis reseed(s))"
    assert lines[1].startswith("Latest baseline event: speed-axis reseed trial #7 ")

    # the startup path seeds the gate from the fold, reseed included
    assert autopilot._baseline_state_for_startup_gate({}, journal)["frontdoor_speed"] == (
        pytest.approx(42.0)
    )


def test_reseed_alone_is_not_a_reconstructable_baseline(tmp_path, monkeypatch):
    g, outcome = _reseed_outcome(tmp_path, monkeypatch)
    journal = ExperimentJournal(journal_dir=tmp_path / "j")
    _append(journal, outcome, g)
    rec = reconcile_baseline_ledger(journal.baseline_ledger_events(), None)
    assert rec.status == "no_events"
    assert rec.cutover_ready is False


def test_journal_mismatch_rolls_the_reseed_back(tmp_path, monkeypatch):
    import copy

    g = _held_gate(tmp_path, monkeypatch)
    before = copy.deepcopy(g.baseline)
    outcome = g.update_baseline(_result(), source_trial_id=7)
    assert g.baseline.frontdoor_speed == pytest.approx(42.0)
    monkeypatch.setattr(autopilot, "_provisional_row_mismatch", lambda p, r: ["trial_id"])

    rolled = autopilot._reconcile_promotion_with_journal(g, outcome, before, {}, {}, 7)

    assert rolled.speed_reseeded is False and rolled.speed_reseed == {}
    assert g.baseline.frontdoor_speed == pytest.approx(100.0)
    assert g.baseline.autopilot_speed_era == _OLD_SPEED_ERA
    journal = ExperimentJournal(journal_dir=tmp_path / "j")
    assert _append(journal, rolled, g) is None
