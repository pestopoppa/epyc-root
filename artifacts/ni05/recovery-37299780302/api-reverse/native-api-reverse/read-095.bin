from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "autopilot" / "autopilot_restart_advisor.py"
spec = importlib.util.spec_from_file_location("autopilot_restart_advisor", SCRIPT)
assert spec is not None and spec.loader is not None
advisor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(advisor)


def _phase_report(**overrides):
    report = {
        "ok": True,
        "status": "active",
        "phase": "loop_start",
        "pid": 123,
        "pid_alive": True,
        "trial_id": 1185,
        "action_type": "numeric_trial",
        "idle_reason": "",
        "code_stale": False,
        "blockers": [],
    }
    report.update(overrides)
    return report


def test_restart_advice_no_action_when_runtime_current() -> None:
    advice = advisor.build_restart_advice(_phase_report(code_stale=False))

    assert advice["status"] == "no_action"
    assert advice["restart_needed"] is False
    assert advice["safe_to_restart_now"] is False
    assert advice["pid_age_verified_landed"] is True


def test_restart_advice_waits_for_active_eval_boundary() -> None:
    advice = advisor.build_restart_advice(
        _phase_report(
            ok=False,
            status="code_stale",
            phase="dispatch_action",
            idle_reason="evaluating question",
            code_stale=True,
            blockers=["autopilot process predates runtime source changes: autopilot.py"],
        )
    )

    assert advice["status"] == "wait_for_boundary"
    assert advice["restart_needed"] is True
    assert advice["safe_to_restart_now"] is False
    assert advice["stop_command"] == []
    assert advice["pid_age_verified_landed"] is False


def test_restart_advice_recommends_restart_at_loop_boundary() -> None:
    advice = advisor.build_restart_advice(
        _phase_report(
            ok=False,
            status="code_stale",
            phase="loop_start",
            code_stale=True,
            blockers=["autopilot process predates runtime source changes: autopilot.py"],
        )
    )

    assert advice["status"] == "restart_recommended"
    assert advice["restart_needed"] is True
    assert advice["safe_to_restart_now"] is True
    assert advice["stop_command"] == ["kill", "-TERM", "123"]
    assert advice["start_command"][-1] == "3000"
    assert advice["pid_age_verified_landed"] is False


def test_restart_advice_honors_explicit_max_trials_override() -> None:
    advice = advisor.build_restart_advice(
        _phase_report(status="pid_dead", phase="stopped", pid_alive=False),
        max_trials=2000,
    )

    assert advice["start_command"][-1] == "2000"


def test_restart_advice_recommends_start_when_pid_dead() -> None:
    advice = advisor.build_restart_advice(
        _phase_report(status="pid_dead", phase="dispatch_action", pid_alive=False)
    )

    assert advice["status"] == "restart_recommended"
    assert advice["restart_needed"] is True
    assert advice["safe_to_restart_now"] is True


def test_restart_advice_manual_attention_when_heartbeat_missing() -> None:
    advice = advisor.build_restart_advice(
        {
            "ok": False,
            "status": "missing",
            "blockers": ["phase heartbeat missing or unreadable"],
        }
    )

    assert advice["ok"] is False
    assert advice["status"] == "manual_attention"
    assert advice["blockers"] == ["phase heartbeat missing or unreadable"]
    assert advice["pid_age_verified_landed"] is False
