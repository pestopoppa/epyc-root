from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "benchmark" / "eval_batch_serving_activation_window.py"

spec = importlib.util.spec_from_file_location("eval_batch_serving_activation_window", MODULE_PATH)
assert spec is not None and spec.loader is not None
window = importlib.util.module_from_spec(spec)
sys.modules["eval_batch_serving_activation_window"] = window
spec.loader.exec_module(window)


def _healthy_preflight(*, autopilot_active: bool = False) -> dict:
    return {
        "api_health": {"ok": True},
        "eval_batch_frontdoor_health": {"ok": False},
        "autopilot_active": autopilot_active,
        "config_attest": {"all_sampled_workers_enabled": False},
        "activation_commands": [],
    }


def test_activation_plan_starts_only_eval_batch_frontdoor_by_default(tmp_path: Path) -> None:
    args = window.parse_args(["--output-dir", str(tmp_path)])
    plan = window.activation_plan(args, output_dir=tmp_path)

    start = plan["activation"][0]
    assert start.name == "start_eval_batch_frontdoor"
    assert " --only eval_batch_frontdoor" in start.display()
    assert " --include-warm " not in start.display()

    rollback = "\n".join(command.display() for command in plan["rollback"])
    assert "ORCHESTRATOR_FEATURE_EVAL_BATCH_SERVING=0" in rollback
    assert "stop eval_batch_frontdoor" in rollback


def test_plan_only_writes_no_execution_steps(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(window, "build_preflight", lambda _args: _healthy_preflight())

    args = window.parse_args(["--output-dir", str(tmp_path)])
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "plan_only"
    assert report["applied"] is False
    assert report["steps"] == []


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


def test_successful_apply_rolls_back_unless_keep_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(window, "build_preflight", lambda _args: _healthy_preflight())

    executed: list[str] = []

    def fake_run(command, *, timeout_s):
        executed.append(command.name)
        return window.StepResult(
            name=command.name,
            command=command.display(),
            returncode=0,
            elapsed_s=0.01,
            stdout_tail="",
            stderr_tail="",
        )

    monkeypatch.setattr(window, "run_command", fake_run)
    monkeypatch.setattr(
        window,
        "_load_probe_summary",
        lambda _output_dir: {"status": "smoke_passed", "decision_grade": True, "blockers": []},
    )

    args = window.parse_args(
        ["--apply", "--confirm-clean-window", "--output-dir", str(tmp_path)]
    )
    report, rc = window.build_report(args, output_dir=tmp_path)

    assert rc == 0
    assert report["status"] == "smoke_passed_rolled_back"
    assert executed == [
        "start_eval_batch_frontdoor",
        "reload_orchestrator_eval_batch_enabled",
        "smoke_probe",
        "rollback_reload_orchestrator_eval_batch_disabled",
        "rollback_stop_eval_batch_frontdoor",
    ]


def test_keep_enabled_skips_success_rollback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(window, "build_preflight", lambda _args: _healthy_preflight())

    executed: list[str] = []

    def fake_run(command, *, timeout_s):
        executed.append(command.name)
        return window.StepResult(
            name=command.name,
            command=command.display(),
            returncode=0,
            elapsed_s=0.01,
            stdout_tail="",
            stderr_tail="",
        )

    monkeypatch.setattr(window, "run_command", fake_run)
    monkeypatch.setattr(
        window,
        "_load_probe_summary",
        lambda _output_dir: {"status": "smoke_passed", "decision_grade": True, "blockers": []},
    )

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
    assert report["status"] == "smoke_passed_enabled_left_on"
    assert executed == [
        "start_eval_batch_frontdoor",
        "reload_orchestrator_eval_batch_enabled",
        "smoke_probe",
    ]
