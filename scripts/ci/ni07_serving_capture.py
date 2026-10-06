"""Capture the selected VB-SERVE-TIMING-1 fixture run with source custody."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

SELECTIONS = [
    "tests/vidya/test_serving_call_adapter.py",
    "tests/vidya/test_ingest_sources.py",
]
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"}


def tracked_inputs(repo: Path):
    names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().split("\0")
    for name in names:
        if not name:
            continue
        path = repo / name
        if path.suffix.lower() == ".py" or path.name in CONFIG_NAMES:
            if not path.is_file():
                raise RuntimeError(f"tracked declared input is missing: {path}")
            yield path.resolve()


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    root, app, recipe = workspace / "root", workspace / "app", workspace / "recipe"
    result = runner_temp / "ni07-serving" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "vb-serve-timing1", "exit_code": None}
    status_path.write_text(json.dumps(status, indent=2) + "\n")
    try:
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        env = {
            "python": sys.version,
            "platform": platform.platform(),
            "root_pin": os.environ["ROOT_PIN"],
            "app_pin": os.environ["APP_PIN"],
            "serving_calls_source_sha256": os.environ["EPYC_SERVING_CALLS_SOURCE_SHA256"],
            "install_command": os.environ["NI07_INSTALL_COMMAND"],
            "declared_test_dependencies": ["pytest==8.4.2", "PyYAML==6.0.2"],
            "dependency_review": "static import closure of the two selected tests, all registered file adapters, and their fixture modules; stdlib plus pytest and PyYAML only",
            "selected_tests": SELECTIONS,
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH",
                "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_LOG_DIR",
                "ORCHESTRATOR_SERVING_CALLS_LOG", "ORCHESTRATOR_COHERENCE_JUDGE_LOG",
                "EPYC_ORCHESTRATOR_ROOT", "EPYC_SERVING_CALLS_SOURCE_SHA256",
            )},
            "isolation": "temporary JSONL/records only; no model, server, inference, or live log read",
        }
        environment = result / "environment.json"
        environment.write_text(json.dumps(env, indent=2, sort_keys=True) + "\n")
        junit = result / "original-junit.xml"
        if junit.exists():
            raise RuntimeError("JUnit must not exist before execution")
        command = [sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
                   "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}"]
        read_paths = [freeze, environment, Path(__file__).resolve(),
                      recipe / ".github/workflows/ni07-serving.yml"]
        repos = {"root": root, "app": app, "recipe": recipe}
        for repo in repos.values():
            read_paths.extend(tracked_inputs(repo))
        read_paths.extend(root / selected for selected in SELECTIONS)
        capture = [sys.executable, str(root / "scripts/ci/native_conformance.py"),
                   "--cwd", str(root), "--junit", str(junit), "--output", str(result / "native")]
        for name, repo in repos.items():
            capture.extend(["--repo", f"{name}={repo}"])
        for path in dict.fromkeys(read_paths):
            capture.extend(["--read-path", str(path)])
        for selected in SELECTIONS:
            capture.extend(["--select", selected])
        status.update(state="running")
        status_path.write_text(json.dumps(status, indent=2) + "\n")
        exit_code = subprocess.call([*capture, "--", *command], cwd=root)
        status.update(state="passed" if exit_code == 0 else "failed", exit_code=exit_code)
        return exit_code
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
