from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "benchmark" / "j12_think_loop_probe.py"

spec = importlib.util.spec_from_file_location("j12_think_loop_probe", MODULE_PATH)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
sys.modules["j12_think_loop_probe"] = probe
spec.loader.exec_module(probe)


def test_failure_mode_classifiers_detect_j12_revert_triggers() -> None:
    assert probe.think_leak("<think>I should reason here</think> final")
    assert probe.think_leak("&lt;think&gt;hidden&lt;/think&gt; final")
    assert probe.known_wait_reference_loop("Wait, I found a reference. Wait, I found a reference.")
    assert probe.repetition_loop("alpha beta gamma " * 8)
    assert probe.expected_match("The answer is 5 cents.", ("0.05", "5 cent"))


def test_failure_mode_classifiers_ignore_normal_answers() -> None:
    answer = "Use a shadow phase, then flip the flag after validation."
    assert not probe.think_leak(answer)
    assert not probe.known_wait_reference_loop(answer)
    assert not probe.repetition_loop(answer)
    assert probe.expected_match(answer, ("shadow", "flag"))


def test_summarize_counts_role_failures(tmp_path: Path) -> None:
    rows = [
        {
            "role": "architect_general",
            "task_id": "code_01",
            "expect_match": True,
            "empty": False,
            "error_answer": False,
            "think_leak": False,
            "known_wait_reference_loop": False,
            "repetition_loop": False,
            "elapsed_s": 1.0,
            "tokens_generated": 10,
        },
        {
            "role": "architect_general",
            "task_id": "code_02",
            "expect_match": False,
            "empty": True,
            "error_answer": True,
            "think_leak": True,
            "known_wait_reference_loop": False,
            "repetition_loop": False,
            "elapsed_s": 3.0,
            "tokens_generated": 0,
        },
    ]

    summary = probe.summarize(rows, stamp="unit", artifact_jsonl=tmp_path / "rows.jsonl")

    role = summary["roles"]["architect_general"]
    assert role["n"] == 2
    assert role["expect_matches"] == 1
    assert role["empty"] == 1
    assert role["error_answers"] == 1
    assert role["think_leaks"] == 1
    assert role["miss_task_ids"] == ["code_02"]
    assert role["failed_task_ids"] == ["code_02"]
    assert role["avg_elapsed_s"] == 2.0
    assert role["avg_tokens_generated"] == 5.0


def test_dry_run_reports_roles_without_clean_window(monkeypatch, capsys) -> None:
    monkeypatch.setattr(probe, "live_role_primary_ports", lambda _roles: {"frontdoor": 8070})

    rc = probe.main(["--dry-run", "--roles", "frontdoor", "--task-limit", "2"])

    captured = capsys.readouterr()
    assert rc == 0
    assert '"dry_run": true' in captured.out
    assert '"task_count": 2' in captured.out


def test_real_run_requires_clean_window(monkeypatch, capsys) -> None:
    monkeypatch.setattr(probe, "live_role_primary_ports", lambda _roles: {"frontdoor": 8070})

    rc = probe.main(["--roles", "frontdoor", "--task-limit", "1"])

    captured = capsys.readouterr()
    assert rc == 2
    assert "confirm-clean-window" in captured.err


def test_active_autopilot_refuses_claim_run(monkeypatch, capsys) -> None:
    monkeypatch.setattr(probe, "live_role_primary_ports", lambda _roles: {"frontdoor": 8070})
    monkeypatch.setattr(probe, "_active_autopilot", lambda: True)

    rc = probe.main(["--roles", "frontdoor", "--task-limit", "1", "--confirm-clean-window"])

    captured = capsys.readouterr()
    assert rc == 75
    assert "AutoPilot appears active" in captured.err


def test_active_autopilot_detector_uses_pgrep(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0)

    monkeypatch.setattr(probe.subprocess, "run", fake_run)

    assert probe._active_autopilot() is True
    assert calls == [["pgrep", "-f", "scripts/autopilot/autopilot.py start"]]
