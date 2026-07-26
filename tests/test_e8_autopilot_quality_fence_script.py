"""Black-box coverage for the human-only E8 quality-fence transaction."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh"
ORCH_SOURCE = Path("/mnt/raid0/llm/epyc-orchestrator")
V8_HEAD = "67a433bf45a8a091d83b4ea0b32ff0735fd51800"


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _commit_repo(path: Path, paths: list[str]) -> None:
    _run(["git", "init", "-q"], cwd=path)
    _run(["git", "config", "user.email", "test@example.invalid"], cwd=path)
    _run(["git", "config", "user.name", "E8 transaction test"], cwd=path)
    _run(["git", "add", *paths], cwd=path)
    _run(["git", "commit", "-qm", "fixture"], cwd=path)


def _fixture(
    tmp_path: Path, *, fail_project_tests: bool = False
) -> tuple[Path, Path, dict[str, str]]:
    root = tmp_path / "root"
    orch = tmp_path / "orchestrator"
    prod = tmp_path / "production"
    bins = tmp_path / "bin"
    (root / "artifacts/operator").mkdir(parents=True)
    (orch / "orchestration").mkdir(parents=True)
    (orch / ".venv/bin").mkdir(parents=True)
    bins.mkdir()

    target_script = (
        root / "artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh"
    )
    shutil.copy2(SCRIPT, target_script)
    _commit_repo(
        root, ["artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh"]
    )

    eras = """eras:
  - id: E7-eval-instrument
    from: \"2026-07-21T10:30:00Z\"
    scope: eval_quality
    note: existing quality era
  - id: E8-autopilot-speed
    from: \"2026-07-25T18:38:43Z\"
    scope: autopilot_speed
    note: existing speed era

known_dead_instrument_items:
  - { suite: test, qids: [], cause: fixture }
"""
    state = {
        "active_instrument_eras": {"autopilot_speed": "E8-autopilot-speed"},
        "baseline_state": {"eval_quality_era": "E7-eval-instrument"},
        "frontier_rerun_required": {"required": True},
        "pareto_exclude_before_ts": 1785004723.0,
    }
    (orch / "orchestration/instrument_eras.yaml").write_text(eras)
    (orch / "orchestration/autopilot_state.json").write_text(
        json.dumps(state, indent=2) + "\n"
    )
    (orch / "orchestration/instrument_eras.yaml").chmod(0o600)
    (orch / "orchestration/autopilot_state.json").chmod(0o640)
    (orch / "scripts").symlink_to(ORCH_SOURCE / "scripts", target_is_directory=True)
    (orch / "src").symlink_to(ORCH_SOURCE / "src", target_is_directory=True)
    (orch / "tests").symlink_to(ORCH_SOURCE / "tests", target_is_directory=True)
    python = orch / ".venv/bin/python"
    if fail_project_tests:
        python.write_text(
            "#!/bin/bash\n"
            "if [[ \"${1:-}\" == '-m' && \"${2:-}\" == 'pytest' ]]; then exit 91; fi\n"
            f'exec {ORCH_SOURCE}/.venv/bin/python "$@"\n'
        )
        python.chmod(0o755)
    else:
        python.write_text(f'#!/bin/bash\nexec {ORCH_SOURCE}/.venv/bin/python "$@"\n')
        python.chmod(0o755)
    _commit_repo(
        orch,
        ["orchestration/instrument_eras.yaml", "orchestration/autopilot_state.json"],
    )

    git = bins / "git"
    git.write_text(
        "#!/bin/bash\n"
        'if [[ "${1:-}" == \'-C\' && "${2:-}" == "$EPYC_PROD" ]]; then\n'
        '  case "${3:-}" in\n'
        "    branch) printf 'production-consolidated-v8\\n'; exit 0 ;;\n"
        f"    rev-parse) printf '{V8_HEAD}\\n'; exit 0 ;;\n"
        "    diff) exit 0 ;;\n"
        "  esac\n"
        "fi\n"
        'exec /usr/bin/git "$@"\n'
    )
    curl = bins / "curl"
    curl.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' \'{"status":"ok","models_loaded":6,"backend_probes":{"a":{"ok":true},"b":{"ok":true},"c":{"ok":true},"d":{"ok":true},"e":{"ok":true},"f":{"ok":true}}}\'\n'
    )
    pgrep = bins / "pgrep"
    pgrep.write_text("#!/bin/sh\nexit 1\n")
    for executable in (git, curl, pgrep):
        executable.chmod(0o755)

    env = {
        **os.environ,
        "EPYC_ROOT": str(root),
        "EPYC_ORCH": str(orch),
        "EPYC_PROD": str(prod),
        "PATH": f"{bins}:{os.environ['PATH']}",
    }
    return root, orch, env


def _attest(root: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(
                root
                / "artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.sh"
            ),
            "--attest",
            "RATIFY-E8-AUTOPILOT-QUALITY-FENCE",
        ],
        env=env,
        capture_output=True,
        text=True,
    )


def test_e8_quality_fence_script_inserts_a_top_level_era_in_an_isolated_fixture(
    tmp_path: Path,
) -> None:
    root, orch, env = _fixture(tmp_path)

    result = _attest(root, env)

    assert result.returncode == 0, result.stderr
    registry = yaml.safe_load((orch / "orchestration/instrument_eras.yaml").read_text())
    e8_rows = [
        row
        for row in registry["eras"]
        if row.get("id") == "E8" and row.get("scope") == "eval_quality"
    ]
    assert len(e8_rows) == 1
    assert registry["known_dead_instrument_items"] == [
        {"suite": "test", "qids": [], "cause": "fixture"}
    ]
    state = json.loads((orch / "orchestration/autopilot_state.json").read_text())
    assert state["active_instrument_eras"]["eval_quality"] == "E8"
    assert state["baseline_state"]["eval_quality_era"] == "E7-eval-instrument"
    assert (orch / "orchestration/instrument_eras.yaml").stat().st_mode & 0o777 == 0o600
    assert (orch / "orchestration/autopilot_state.json").stat().st_mode & 0o777 == 0o640
    assert (
        root / "artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.json"
    ).is_file()


def test_e8_quality_fence_script_restores_both_preimages_after_postwrite_failure(
    tmp_path: Path,
) -> None:
    root, orch, env = _fixture(tmp_path, fail_project_tests=True)
    eras_path = orch / "orchestration/instrument_eras.yaml"
    state_path = orch / "orchestration/autopilot_state.json"
    original_eras = eras_path.read_text()
    original_state = state_path.read_text()

    result = _attest(root, env)

    assert result.returncode != 0
    assert "restoring E8 quality-fence preimages" in result.stderr
    assert eras_path.read_text() == original_eras
    assert state_path.read_text() == original_state
    assert eras_path.stat().st_mode & 0o777 == 0o600
    assert state_path.stat().st_mode & 0o777 == 0o640
    assert not (
        root / "artifacts/operator/ratify_e8_autopilot_quality_fence_20260726.json"
    ).exists()
    rolled_back = list(
        (root / "artifacts/operator").glob(
            "e8-autopilot-quality-fence-20260726.rolled-back.*"
        )
    )
    assert len(rolled_back) == 1
    assert (rolled_back[0] / "instrument_eras.yaml.before").read_text() == original_eras
    assert (
        rolled_back[0] / "autopilot_state.json.before"
    ).read_text() == original_state
