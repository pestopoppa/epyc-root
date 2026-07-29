"""Black-box coverage for the human-only E8 empty-frontier bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.sh"
ORCH_SOURCE = Path("/mnt/raid0/llm/epyc-orchestrator")
REVIEWED_ORCHESTRATOR_HEAD = "f3ba7e9d13891de368db0e3100d2357d18122aee"


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _commit_repo(path: Path, paths: list[str]) -> None:
    _run(["git", "init", "-q"], cwd=path)
    _run(["git", "config", "user.email", "test@example.invalid"], cwd=path)
    _run(["git", "config", "user.name", "E8 bootstrap test"], cwd=path)
    _run(["git", "add", *paths], cwd=path)
    _run(["git", "commit", "-qm", "fixture"], cwd=path)


def _fixture(tmp_path: Path, *, fail_after_write: bool = False) -> tuple[Path, Path, dict[str, str]]:
    root = tmp_path / "root"
    orch = tmp_path / "orchestrator"
    bins = tmp_path / "bin"
    (root / "artifacts/operator").mkdir(parents=True)
    (orch / "orchestration").mkdir(parents=True)
    (orch / ".venv/bin").mkdir(parents=True)
    bins.mkdir()

    eras = "eras: []\n"
    state = {
        "active_instrument_eras": {
            "autopilot_speed": "E8-autopilot-speed",
            "eval_quality": "E8",
        },
        "baseline_state": {"eval_quality_era": "E7-eval-instrument"},
        "frontier_rerun_required": {
            "required": True,
            "completed_numeric_trials": 0,
            "min_numeric_trials": 16,
        },
        "pareto_epoch_ts": 1785004723.0,
        "pareto_exclude_before_ts": 1785004723.0,
        "quality_epoch_ts": 1785004723.0,
        "quality_exclude_before_ts": 1785004723.0,
    }
    eras_path = orch / "orchestration/instrument_eras.yaml"
    state_path = orch / "orchestration/autopilot_state.json"
    eras_path.write_text(eras)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    (orch / "orchestration/autopilot_journal.jsonl").write_text("")
    (orch / "scripts").symlink_to(ORCH_SOURCE / "scripts", target_is_directory=True)
    (orch / "src").symlink_to(ORCH_SOURCE / "src", target_is_directory=True)
    _commit_repo(orch, ["orchestration/instrument_eras.yaml", "orchestration/autopilot_state.json"])

    quality_receipt = {
        "decision": "RATIFY-E8-AUTOPILOT-QUALITY-FENCE",
        "quality_era": {"id": "E8"},
        "sha256": {
            "autopilot_state": hashlib.sha256(state_path.read_bytes()).hexdigest(),
            "instrument_eras": hashlib.sha256(eras_path.read_bytes()).hexdigest(),
        },
    }
    quality_receipt_path = root / "artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.json"
    quality_receipt_path.write_text(json.dumps(quality_receipt, indent=2) + "\n")
    quality_receipt_sha = hashlib.sha256(quality_receipt_path.read_bytes()).hexdigest()

    target_script = root / "artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.sh"
    script_text = SCRIPT.read_text().replace(
        'E8_RECEIPT_SHA256="313a8129336ec4ad6149bfb04541cb5a2bacd79568e0ce06efdba9718b43437c"',
        f'E8_RECEIPT_SHA256="{quality_receipt_sha}"',
    )
    target_script.write_text(script_text)
    _commit_repo(root, ["artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.sh"])

    python = orch / ".venv/bin/python"
    if fail_after_write:
        count_file = tmp_path / "python-calls"
        python.write_text(
            "#!/bin/bash\n"
            f"count_file={count_file!s}\n"
            "count=$(cat \"$count_file\" 2>/dev/null || echo 0)\n"
            "count=$((count + 1)); printf '%s' \"$count\" >\"$count_file\"\n"
            "if [[ $count -eq 3 ]]; then exit 91; fi\n"
            f"exec {ORCH_SOURCE}/.venv/bin/python \"$@\"\n"
        )
    else:
        python.write_text(f'#!/bin/bash\nexec {ORCH_SOURCE}/.venv/bin/python "$@"\n')
    python.chmod(0o755)

    git = bins / "git"
    git.write_text(
        "#!/bin/bash\n"
        f'if [[ "${{1:-}}" == -C && "${{2:-}}" == "{orch}" && "${{3:-}}" == rev-parse ]]; then\n'
        f"  printf '{REVIEWED_ORCHESTRATOR_HEAD}\\n'\n"
        "  exit 0\n"
        "fi\n"
        'exec /usr/bin/git "$@"\n'
    )
    pgrep = bins / "pgrep"
    pgrep.write_text("#!/bin/sh\nexit 1\n")
    for executable in (git, pgrep):
        executable.chmod(0o755)

    env = {
        **os.environ,
        "EPYC_ROOT": str(root),
        "EPYC_ORCH": str(orch),
        "PATH": f"{bins}:{os.environ['PATH']}",
    }
    return root, orch, env


def _attest(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(root / "artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.sh"),
            "--attest",
            "RATIFY-E8-EMPTY-FRONTIER-BOOTSTRAP",
        ],
        env=env,
        capture_output=True,
        text=True,
    )


def _validate_only(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(root / "artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.sh"),
            "--validate-only",
        ],
        env=env,
        capture_output=True,
        text=True,
    )


def test_bootstrap_attestation_changes_only_the_durable_rebase_posture(tmp_path: Path) -> None:
    root, orch, env = _fixture(tmp_path)
    state_path = orch / "orchestration/autopilot_state.json"
    original_state = state_path.read_text()

    validate = _validate_only(root, env)
    assert validate.returncode == 0, validate.stderr
    assert state_path.read_text() == original_state
    assert not (root / "artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.json").exists()

    result = _attest(root, env)

    assert result.returncode == 0, result.stderr
    state = json.loads((orch / "orchestration/autopilot_state.json").read_text())
    assert state["_allow_empty_frontier_rebase"] is True
    assert state["e8_empty_frontier_bootstrap"]["status"] == "active"
    assert state["active_instrument_eras"]["eval_quality"] == "E8"
    receipt = json.loads(
        (root / "artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.json").read_text()
    )
    assert receipt["reviewed_orchestrator_head"] == REVIEWED_ORCHESTRATOR_HEAD
    assert receipt["state_delta"] == {
        "_allow_empty_frontier_rebase": True,
        "e8_empty_frontier_bootstrap": {
            "status": "active",
            "reason": "E8 current-era replay intentionally empty; permit fresh frontier bootstrap",
            "required_clear_condition": (
                "next AutoPilot startup observes at least one current-era Pareto point"
            ),
        },
    }

    repeat = _attest(root, env)
    assert repeat.returncode != 0
    assert "prior bootstrap transaction exists" in repeat.stderr


def test_bootstrap_rolls_back_state_when_postwrite_validation_fails(tmp_path: Path) -> None:
    root, orch, env = _fixture(tmp_path, fail_after_write=True)
    state_path = orch / "orchestration/autopilot_state.json"
    original_state = state_path.read_text()

    result = _attest(root, env)

    assert result.returncode != 0
    assert "state preimage restored" in result.stderr
    assert state_path.read_text() == original_state
    assert not (root / "artifacts/operator/ratify_e8_empty_frontier_bootstrap_20260726.json").exists()
    rolled_back = list(
        (root / "artifacts/operator").glob("e8-empty-frontier-bootstrap-20260726.rolled-back.*")
    )
    assert len(rolled_back) == 1
    assert (rolled_back[0] / "autopilot_state.json.before").read_text() == original_state
