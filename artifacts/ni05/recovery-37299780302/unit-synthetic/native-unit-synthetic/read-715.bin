from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "maintenance" / "routing_classifier_rollout_window.py"

spec = importlib.util.spec_from_file_location("routing_classifier_rollout_window", MODULE_PATH)
assert spec is not None and spec.loader is not None
window = importlib.util.module_from_spec(spec)
sys.modules["routing_classifier_rollout_window"] = window
spec.loader.exec_module(window)


def _healthy_preflight(*, autopilot_active: bool = False, weights_present: bool = True) -> dict:
    return {
        "api_url": "http://localhost:8000",
        "api_health": {"ok": True},
        "autopilot_active": autopilot_active,
        "weights_path": "/tmp/routing_classifier_weights.npz",
        "weights_present": weights_present,
        "config_attest": {
            "workers_seen": 1,
            "routing_classifier_by_pid": {"123": False},
            "routing_classifier_sources_by_pid": {"123": "default"},
            "all_sampled_workers_enabled": False,
            "any_sampled_worker_enabled": False,
        },
    }


def _step(name: str, ok: bool = True):
    stdout = ""
    if name.startswith("attest_"):
        stdout = '{"workers_seen": 1, "expected_diffs": []}\n'
    return window.StepResult(
        name=name,
        command=name,
        returncode=0 if ok else 2,
        elapsed_s=0.01,
        stdout_tail=stdout,
        stderr_tail="",
    )


def test_rollout_plan_verifies_reloads_attests_and_rolls_back(tmp_path: Path) -> None:
    args = window.parse_args(["--output-dir", str(tmp_path)])
    plan = window.rollout_plan(args)

    activation = [command.display() for command in plan["activation"]]
    rollback = [command.display() for command in plan["rollback"]]

    assert "verify_routing_wiring.py" in activation[0]
    assert "ORCHESTRATOR_FEATURE_ROUTING_CLASSIFIER=1" in activation[1]
    assert "reload orchestrator" in activation[1]
    assert "--expect routing_classifier=true" in activation[2]
    assert "ORCHESTRATOR_FEATURE_ROUTING_CLASSIFIER=0" in rollback[0]
    assert "--expect routing_classifier=false" in rollback[1]


def test_plan_only_writes_no_execution_steps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(window, "build_preflight", lambda _args: _healthy_preflight())

    args = window.parse_args(["--output-dir", str(tmp_path)])
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "plan_only"
    assert report["applied"] is False
    assert report["steps"] == []
    assert report["decision_grade"] is False


def test_apply_requires_clean_window(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(window, "build_preflight", lambda _args: _healthy_preflight())

    args = window.parse_args(["--apply", "--output-dir", str(tmp_path)])
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 2
    assert report["status"] == "blocked"
    assert "--apply requires --confirm-clean-window" in report["blockers"]


def test_apply_refuses_active_autopilot_by_default(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        window,
        "build_preflight",
        lambda _args: _healthy_preflight(autopilot_active=True),
    )

    args = window.parse_args(["--apply", "--confirm-clean-window", "--output-dir", str(tmp_path)])
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 75
    assert report["status"] == "blocked"
    assert "AutoPilot appears active" in report["blockers"][0]


def test_apply_requires_weights(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        window,
        "build_preflight",
        lambda _args: _healthy_preflight(weights_present=False),
    )

    args = window.parse_args(["--apply", "--confirm-clean-window", "--output-dir", str(tmp_path)])
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 2
    assert report["status"] == "blocked"
    assert "routing classifier weights are missing" in report["blockers"][0]


def test_successful_apply_rolls_back_unless_keep_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(window, "build_preflight", lambda _args: _healthy_preflight())

    executed: list[str] = []

    def fake_run(command, *, timeout_s):
        executed.append(command.name)
        return _step(command.name)

    monkeypatch.setattr(window, "run_command", fake_run)

    args = window.parse_args(
        ["--apply", "--confirm-clean-window", "--output-dir", str(tmp_path)]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "attestation_passed_rolled_back"
    assert report["rollout_attested"] is True
    assert executed == [
        "verify_routing_wiring",
        "reload_orchestrator_routing_classifier_enabled",
        "attest_routing_classifier_enabled",
        "reload_orchestrator_routing_classifier_disabled",
        "attest_routing_classifier_disabled",
    ]


def test_keep_enabled_skips_success_rollback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(window, "build_preflight", lambda _args: _healthy_preflight())

    executed: list[str] = []

    def fake_run(command, *, timeout_s):
        executed.append(command.name)
        return _step(command.name)

    monkeypatch.setattr(window, "run_command", fake_run)

    args = window.parse_args(
        [
            "--apply",
            "--confirm-clean-window",
            "--keep-enabled",
            "--output-dir",
            str(tmp_path),
        ]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "attestation_passed_enabled_left_on"
    assert report["rollout_attested"] is True
    assert executed == [
        "verify_routing_wiring",
        "reload_orchestrator_routing_classifier_enabled",
        "attest_routing_classifier_enabled",
    ]

