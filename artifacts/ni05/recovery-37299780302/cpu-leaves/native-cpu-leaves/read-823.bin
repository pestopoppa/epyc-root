from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "autopilot" / "start_authority_daemon.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("start_authority_daemon", SCRIPT)
assert spec is not None and spec.loader is not None
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_authority_env_forces_required_flags() -> None:
    env = launcher.authority_env(
        {
            "AUTOPILOT_TOOL_SENTINELS": "0",
            "AUTOPILOT_PLANNER_HINTS": "0",
            "KEEP": "value",
        }
    )

    assert env["KEEP"] == "value"
    assert env["AUTOPILOT_TOOL_SENTINELS"] == "1"
    assert env["AUTOPILOT_PLANNER_HINTS"] == "1"
    # Derived, not restated. The invariant is that the wrapper ENFORCES the authority
    # env, not that a particular switch is on: AUTOPILOT_SEQ_VERDICT is an operator
    # control (set to "0" on 2026-08-04 while SEQ-B was unreachable). Pinning the
    # literal made a deliberate operator flip look like a regression. A wrapper that
    # DROPS the key still fails here, which is what this test is for.
    assert env["AUTOPILOT_SEQ_VERDICT"] == launcher.AUTHORITY_ENV["AUTOPILOT_SEQ_VERDICT"]
    assert env["AUTOPILOT_SEQ_P0_2_BRIDGE"] == launcher.AUTHORITY_ENV["AUTOPILOT_SEQ_P0_2_BRIDGE"]
    assert env["AUTOPILOT_W6_AUDIT_BLOCK"] == "1"
    assert env["AUTOPILOT_PLANNER_TIMEOUT"] == "600"
    # The planner runs on local models by default; forcing the spend breaker on
    # has historically stopped AutoPilot even when no cloud spend was at risk.
    assert env["AUTOPILOT_PLANNER_SPEND_BREAKER"] == "0"


def test_authority_env_pins_the_ap55_gate_mode() -> None:
    """AP-55: the launcher pins the gate mode and the seed re-run knob, so an inherited
    shell variable can neither arm nor disarm them. Derived from AUTHORITY_ENV (the
    AP-55-ARM flip edits that dict), and both values must be ones the loop understands."""
    env = launcher.authority_env(
        {"AUTOPILOT_AP55_PROMOTION_GATE": "strict", "AUTOPILOT_AP55_SEED_RERUN": "yes"}
    )
    mode = launcher.AUTHORITY_ENV["AUTOPILOT_AP55_PROMOTION_GATE"]
    rerun = launcher.AUTHORITY_ENV["AUTOPILOT_AP55_SEED_RERUN"]
    assert env["AUTOPILOT_AP55_PROMOTION_GATE"] == mode
    assert env["AUTOPILOT_AP55_SEED_RERUN"] == rerun
    assert mode in {"shadow", "enforce", "strict"}
    assert rerun in {"0", "1"}


def test_authority_env_enforces_sealed_two_codex_zero_claude_roster() -> None:
    env = launcher.authority_env(
        {
            "AUTOPILOT_PLANNER_PRIMARY": "claude",
            "AUTOPILOT_PLANNER_MODE": "single",
            "AUTOPILOT_LOCAL_PLANNER_MAX_TOKENS": "4096",
        }
    )

    assert env["AUTOPILOT_PLANNER_PRIMARY"] == "codex"
    assert env["AUTOPILOT_PLANNER_CRITIC"] == "codex_critic"
    assert env["AUTOPILOT_PLANNER_CRITIC_FALLBACK"] == "none"
    assert env["AUTOPILOT_PLANNER_MODE"] == "draft_critique"
    assert env["AUTOPILOT_PLANNER_CRITIQUE_POLICY"] == "always"
    assert env["AUTOPILOT_CODEX_MODEL"] == "gpt-5.6-sol"
    assert env["AUTOPILOT_CODEX_EFFORT"] == "high"
    assert env["AUTOPILOT_CODEX_CRITIC_MODEL"] == "gpt-5.6-terra"
    assert env["AUTOPILOT_CODEX_CRITIC_EFFORT"] == "high"
    assert env["AUTOPILOT_PLANNER_ROSTER_POLICY_ACTIVE"] == "1"
    assert len(env["AUTOPILOT_PLANNER_ROSTER_SHA256"]) == 64
    assert env["AUTOPILOT_PLANNER_SPEND_BREAKER_PRIMARY"] == "local_frontdoor"
    assert env["AUTOPILOT_PLANNER_SPEND_BREAKER_CRITIC"] == "local_ingest"
    assert env["AUTOPILOT_LOCAL_PLANNER_ROLE"] == "ingest_long_context"
    assert env["AUTOPILOT_LOCAL_PLANNER_MODEL"] == "ingest_long_context"
    assert env["AUTOPILOT_LOCAL_PLANNER_TEMPERATURE"] == "0"
    assert env["AUTOPILOT_LOCAL_PLANNER_MAX_TOKENS"] == "4096"

    default_env = launcher.authority_env({})
    assert default_env["AUTOPILOT_PLANNER_PRIMARY"] == "codex"
    assert default_env["AUTOPILOT_PLANNER_CRITIC"] == "codex_critic"


def test_authority_env_sets_latest_repo_readiness_pickup(
    monkeypatch,
    tmp_path,
) -> None:
    older = tmp_path / "repo_readiness_autopilot_pickup_2026-07-03.json"
    newer = tmp_path / "repo_readiness_autopilot_pickup_2026-07-05.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launcher, "DEFAULT_REPO_READINESS_DIRS", (tmp_path,))

    env = launcher.authority_env({})

    assert env["AUTOPILOT_REPO_READINESS_PICKUP"] == str(newer)


def test_authority_env_preserves_explicit_repo_readiness_pickup(
    monkeypatch,
    tmp_path,
) -> None:
    generated = tmp_path / "repo_readiness_autopilot_pickup_2026-07-05.json"
    generated.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launcher, "DEFAULT_REPO_READINESS_DIRS", (tmp_path,))

    env = launcher.authority_env({"AUTOPILOT_REPO_READINESS_PICKUP": "/custom/pickup.json"})

    assert env["AUTOPILOT_REPO_READINESS_PICKUP"] == "/custom/pickup.json"


def test_build_command_uses_autopilot_start_and_default_trials(monkeypatch) -> None:
    monkeypatch.setattr(launcher, "python_executable", lambda: "/venv/bin/python3")

    command = launcher.build_command(3000)

    assert command == [
        "/venv/bin/python3",
        "scripts/autopilot/autopilot.py",
        "start",
        "--max-trials",
        "3000",
    ]


def test_build_supervisor_command_wraps_autopilot_child(monkeypatch) -> None:
    monkeypatch.setattr(launcher, "python_executable", lambda: "/venv/bin/python3")
    child = launcher.build_command(3000)

    command = launcher.build_supervisor_command(
        child,
        max_restarts=2,
        restart_delay_s=5.0,
    )

    assert command == [
        "/venv/bin/python3",
        "scripts/autopilot/autopilot_supervisor.py",
        "--max-restarts",
        "2",
        "--restart-delay-s",
        "5.0",
        "--",
        *child,
    ]


def test_dry_run_prints_authority_payload(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(launcher, "python_executable", lambda: "/venv/bin/python3")
    monkeypatch.setattr(launcher, "live_autopilot_processes", lambda: ["123 live"])

    rc = launcher.main(["--dry-run", "--log-dir", str(tmp_path), "--max-trials", "1234"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["child_command"] == [
        "/venv/bin/python3",
        "scripts/autopilot/autopilot.py",
        "start",
        "--max-trials",
        "1234",
    ]
    assert payload["command"] == [
        "/venv/bin/python3",
        "scripts/autopilot/autopilot_supervisor.py",
        "--max-restarts",
        "3",
        "--restart-delay-s",
        "30.0",
        "--",
        *payload["child_command"],
    ]
    assert payload["supervised"] is True
    assert payload["env"]["AUTOPILOT_TOOL_SENTINELS"] == "1"
    assert payload["env"]["AUTOPILOT_SEQ_VERDICT"] == launcher.AUTHORITY_ENV["AUTOPILOT_SEQ_VERDICT"]
    assert payload["env"]["AUTOPILOT_SEQ_P0_2_BRIDGE"] == launcher.AUTHORITY_ENV["AUTOPILOT_SEQ_P0_2_BRIDGE"]
    assert payload["env"]["AUTOPILOT_PLANNER_PRIMARY"] == "codex"
    assert payload["env"]["AUTOPILOT_PLANNER_CRITIC"] == "codex_critic"
    assert payload["env"]["AUTOPILOT_PLANNER_MODE"] == "draft_critique"
    assert payload["env"]["AUTOPILOT_PLANNER_CRITIQUE_POLICY"] == "always"
    assert payload["env"]["AUTOPILOT_CODEX_MODEL"] == "gpt-5.6-sol"
    assert payload["env"]["AUTOPILOT_CODEX_CRITIC_MODEL"] == "gpt-5.6-terra"
    assert len(payload["env"]["AUTOPILOT_PLANNER_ROSTER_SHA256"]) == 64
    assert payload["env"]["AUTOPILOT_PLANNER_ROSTER_PATH"].endswith(
        "codex2_no_claude_20260813.json"
    )
    assert payload["pid"] is None


def test_preflight_prints_restart_advice_without_starting(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setattr(
        launcher,
        "build_command",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not build")),
    )

    class FakeAdvisor:
        @staticmethod
        def build_restart_advice(report, *, max_trials):
            return {
                "advisor_version": "autopilot_restart_advisor.v1",
                "ok": True,
                "status": "restart_recommended",
                "restart_needed": True,
                "safe_to_restart_now": True,
                "reason": "unit",
                "blockers": [],
                "phase": report["phase"],
                "max_trials": max_trials,
                "pid_age_verified_landed": False,
            }

    class FakePhase:
        @staticmethod
        def build_phase_health_report(**kwargs):
            return {"phase": "loop_start", "require_current_code": kwargs["require_current_code"]}

    monkeypatch.setitem(sys.modules, "autopilot_restart_advisor", FakeAdvisor)
    monkeypatch.setitem(sys.modules, "phase_status", FakePhase)

    rc = launcher.main(["--preflight", "--log-dir", str(tmp_path), "--max-trials", "1234"])

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "restart_recommended"
    assert payload["phase"] == "loop_start"
    assert payload["max_trials"] == 1234


def test_preflight_exits_zero_only_for_pid_age_verified_landed(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    class FakeAdvisor:
        @staticmethod
        def build_restart_advice(report, *, max_trials):
            return {
                "advisor_version": "autopilot_restart_advisor.v1",
                "ok": True,
                "status": "no_action",
                "restart_needed": False,
                "safe_to_restart_now": False,
                "reason": "current",
                "blockers": [],
                "phase": report["phase"],
                "max_trials": max_trials,
                "pid_age_verified_landed": True,
            }

    class FakePhase:
        @staticmethod
        def build_phase_health_report(**kwargs):
            return {
                "phase": "planner_prompt_build",
                "require_current_code": kwargs["require_current_code"],
            }

    monkeypatch.setitem(sys.modules, "autopilot_restart_advisor", FakeAdvisor)
    monkeypatch.setitem(sys.modules, "phase_status", FakePhase)

    rc = launcher.main(["--preflight", "--log-dir", str(tmp_path), "--max-trials", "1234"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "no_action"
    assert payload["pid_age_verified_landed"] is True
