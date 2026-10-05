from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
from src.autopilot_core.multitier_decision import (  # noqa: E402
    MULTITIER_POLICY_VERSION,
    build_tier_baseline_evidence,
)


class _Verdict:
    def __init__(self, passed: bool = True, *, seq=None, violations=None):
        self.passed = passed
        self.seq = seq
        self.violations = list(violations or [])

    def __bool__(self):
        return self.passed


def _result(*, tier: int, outcomes: dict[str, bool], suffix: str = ""):
    rows = [{"qid": qid, "correct": value} for qid, value in outcomes.items()]
    return SimpleNamespace(
        tier=tier,
        quality=3.0 * sum(outcomes.values()) / len(outcomes),
        reliability=1.0,
        core_id=f"core-t{tier}{suffix}",
        dataset_content_sha256=f"dataset-t{tier}",
        test_profile=f"profile-t{tier}",
        question_results=rows,
        details={},
    )


def _state(t2: dict[str, bool], t3: dict[str, bool]):
    return {
        autopilot.MULTITIER_BASELINE_STATE_KEY: {
            "policy_version": MULTITIER_POLICY_VERSION,
            "tiers": {
                "2": build_tier_baseline_evidence(_result(tier=2, outcomes=t2)),
                "3": build_tier_baseline_evidence(_result(tier=3, outcomes=t3)),
            },
        }
    }


@pytest.fixture(autouse=True)
def _enable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(autopilot, "MULTITIER_PROMOTION_ENABLED", True)
    monkeypatch.setattr(autopilot, "MULTITIER_MAX_ATTEMPTS_PER_TIER", 3)


def test_staged_candidate_runs_t2_then_t3_then_final_t1():
    t2 = {f"q{i}": i % 2 == 0 for i in range(100)}
    t3 = {f"h{i}": i % 3 == 0 for i in range(100)}
    state = _state(t2, t3)
    action = {"type": "numeric_trial", "surface": "routing", "params": {"routing.x": 1}}
    source = _result(tier=1, outcomes={f"c{i}": True for i in range(50)})
    pending = autopilot._start_multitier_validation(
        state,
        action=action,
        eval_result=source,
        verdict=_Verdict(),
        trial_counter=10,
    )
    assert pending["next_tier"] == 2

    forced, _, context = autopilot._maybe_force_multitier_due_action(
        state=state, blacklist=[], trial_counter=11
    )
    assert forced == {"type": "deep_eval", "tier": 2}
    assert context["stage"] == "tier_2"
    verdict = autopilot._record_multitier_validation_result(
        state,
        context=context,
        eval_result=_result(tier=2, outcomes=t2),
        verdict=_Verdict(),
        trial_counter=11,
    )
    assert verdict["status"] == "pass"
    assert state[autopilot.MULTITIER_PENDING_STATE_KEY]["next_tier"] == 3

    forced, _, context = autopilot._maybe_force_multitier_due_action(
        state=state, blacklist=[], trial_counter=12
    )
    assert forced == {"type": "deep_eval", "tier": 3}
    autopilot._record_multitier_validation_result(
        state,
        context=context,
        eval_result=_result(tier=3, outcomes=t3),
        verdict=_Verdict(),
        trial_counter=12,
    )
    assert state[autopilot.MULTITIER_PENDING_STATE_KEY]["next_tier"] == "final_t1"

    forced, _, context = autopilot._maybe_force_multitier_due_action(
        state=state, blacklist=[], trial_counter=13
    )
    assert forced == {"type": "deep_eval", "tier": 1}
    assert context["stage"] == "final_t1"


def test_higher_tier_regression_forces_production_best_rollback():
    incumbent = {f"q{i}": True for i in range(100)}
    state = _state(incumbent, incumbent)
    action = {"type": "numeric_trial", "surface": "routing", "params": {"routing.x": 1}}
    autopilot._start_multitier_validation(
        state,
        action=action,
        eval_result=_result(tier=1, outcomes={"c": True}),
        verdict=_Verdict(),
        trial_counter=20,
    )
    _, _, context = autopilot._maybe_force_multitier_due_action(
        state=state, blacklist=[], trial_counter=21
    )
    regressed = {f"q{i}": i >= 40 for i in range(100)}
    verdict = autopilot._record_multitier_validation_result(
        state,
        context=context,
        eval_result=_result(tier=2, outcomes=regressed),
        verdict=_Verdict(),
        trial_counter=21,
    )
    assert verdict["status"] == "regression"
    assert state["multitier_rollback_pending"] is True

    forced, rationale, context = autopilot._maybe_force_multitier_due_action(
        state=state, blacklist=[], trial_counter=22
    )
    assert forced == {"type": "rollback", "to_checkpoint": "production_best"}
    assert rationale["multitier_rollback"] is True
    assert context["stage"] == "rollback"


def test_successful_final_baseline_update_marks_candidate_accepted():
    state = _state({"q": True}, {"h": True})
    state[autopilot.MULTITIER_PENDING_STATE_KEY] = {
        "policy_version": MULTITIER_POLICY_VERSION,
        "status": "pending",
        "candidate": "abc",
        "candidate_action": {"type": "numeric_trial", "params": {"routing.x": 1}},
        "next_tier": "final_t1",
        "higher_tier_improvements": [3],
        "final_t1_attempts": 1,
    }
    autopilot._finish_multitier_promotion(
        state,
        baseline_update=SimpleNamespace(updated=True, reason="promoted"),
        trial_counter=30,
    )
    assert autopilot.MULTITIER_PENDING_STATE_KEY not in state
    assert state["multitier_last_accepted"]["candidate"] == "abc"
    assert state["multitier_last_event"]["higher_tier_improvements"] == [3]
    assert state["multitier_production_checkpoint_due"]["candidate"] == "abc"


def test_missing_higher_tier_baseline_prevents_staging():
    state = {}
    gate = SimpleNamespace(
        use_sequential=False,
        baseline=SimpleNamespace(quality_for_tier=lambda tier, strict=False: 1.0),
    )
    eligible, reason = autopilot._multitier_candidate_is_eligible(
        state=state,
        gate=gate,
        action={"type": "numeric_trial", "params": {"routing.x": 1}},
        eval_result=SimpleNamespace(tier=1, quality=1.5),
        verdict=_Verdict(),
        pareto_status="frontier",
    )
    assert eligible is False
    assert "missing matched incumbent baseline" in reason


def test_startup_fails_closed_without_ratified_bundle(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(autopilot, "load_state", lambda: {})

    with pytest.raises(RuntimeError, match="ratified state/baseline bundle is not ready"):
        autopilot._run_loop_inner(
            max_trials=1,
            dry_run=True,
            use_controller=False,
        )
