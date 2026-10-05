from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
import planner_roster  # type: ignore[import-not-found]  # noqa: E402
from src.autopilot_core.authority_consent import SEQ_P0_2_BRIDGE_CONSENT  # noqa: E402


def test_startup_attestation_reports_gate_env_and_config_hash(monkeypatch, tmp_path) -> None:
    grant = tmp_path / "consent.json"
    grant.write_text(json.dumps({SEQ_P0_2_BRIDGE_CONSENT: "allow"}), encoding="utf-8")
    monkeypatch.setenv("AUTOPILOT_AUTHORITY_CONSENT_PATH", str(grant))
    for key, value in autopilot.AUTOPILOT_REQUIRED_GATE_ENV.items():
        monkeypatch.setenv(key, value)
    for key, value in planner_roster.apply_roster({}, planner_roster.DEFAULT_ROSTER).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AUTOPILOT_PLANNER_SPEND_BREAKER", "0")

    payload = autopilot._startup_attestation_payload()

    assert payload["missing_or_mismatch"] == {}
    assert len(payload["config_hash"]) == 64
    assert payload["gate_env"]["AUTOPILOT_TOOL_SENTINELS"] == "1"
    assert payload["gate_env"]["AUTOPILOT_PLANNER_PRIMARY"] == "codex"
    assert payload["gate_env"]["AUTOPILOT_PLANNER_MODE"] == "draft_critique"
    assert payload["gate_env"]["AUTOPILOT_PLANNER_CRITIQUE_POLICY"] == "always"
    assert payload["gate_env"]["AUTOPILOT_CODEX_MODEL"] == "gpt-5.6-sol"
    assert payload["gate_env"]["AUTOPILOT_CODEX_CRITIC_MODEL"] == "gpt-5.6-terra"
    assert payload["gate_env"]["AUTOPILOT_PLANNER_SPEND_BREAKER"] == "0"
    assert payload["p0_2_bridge"]["enabled"] is True


def test_startup_attestation_marks_bare_start_gate_gaps(monkeypatch) -> None:
    for key in autopilot.AUTOPILOT_REQUIRED_GATE_ENV:
        monkeypatch.delenv(key, raising=False)

    payload = autopilot._startup_attestation_payload()

    assert set(payload["missing_or_mismatch"]) == set(autopilot.AUTOPILOT_REQUIRED_GATE_ENV)


def test_startup_attestation_marks_spend_breaker_on_as_mismatch(monkeypatch) -> None:
    for key, value in autopilot.AUTOPILOT_REQUIRED_GATE_ENV.items():
        monkeypatch.setenv(key, value)
    for key, value in planner_roster.apply_roster({}, planner_roster.DEFAULT_ROSTER).items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("AUTOPILOT_PLANNER_SPEND_BREAKER", "1")

    payload = autopilot._startup_attestation_payload()

    assert payload["missing_or_mismatch"] == {
        "AUTOPILOT_PLANNER_SPEND_BREAKER": {"expected": "0", "actual": "1"}
    }


def test_cmd_start_refuses_bare_start_before_lock(monkeypatch, tmp_path, capsys) -> None:
    for key in autopilot.AUTOPILOT_REQUIRED_GATE_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(autopilot, "LOCK_PATH", tmp_path / ".autopilot.lock")
    monkeypatch.setattr(
        autopilot.fcntl,
        "flock",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("lock should not be taken")),
    )
    monkeypatch.setattr(
        autopilot,
        "run_loop",
        lambda **_k: (_ for _ in ()).throw(AssertionError("loop should not start")),
    )

    args = argparse.Namespace(max_trials=1, dry_run=False, no_controller=True, tui=False)
    with pytest.raises(SystemExit) as exc:
        autopilot.cmd_start(args)

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "AutoPilot authority gate env mismatch" in err
    assert "start_authority_daemon.py" in err
    assert "AUTOPILOT_SEQ_VERDICT" in err
