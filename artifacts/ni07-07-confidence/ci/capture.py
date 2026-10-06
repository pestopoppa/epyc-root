#!/usr/bin/env python3
"""Capture one exact APP fixture selection through the pinned ROOT carrier."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "b087a506317ba2422f5d14b790655e13e5ea032f"
SELECTION = "tests/unit/test_confidence_expectation.py"
APP_READSET = (
    "pyproject.toml",
    "src/__init__.py",
    "src/typed_decisions/__init__.py",
    "src/typed_decisions/types.py",
    "src/typed_decisions/confidence_expectation.py",
    "tests/unit/test_confidence_expectation.py",
    "orchestration/grading_specs/answer_quality.yaml",
    "orchestration/grading_specs/routing_optimality.yaml",
    "orchestration/grading_specs/synthesis_coherence.yaml",
)


def _git(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def _pin(path: Path, expected: str, label: str) -> None:
    actual = _git(path, "rev-parse", "HEAD")
    if actual != expected:
        raise RuntimeError(f"{label} pin mismatch: expected {expected}, got {actual}")
    if _git(path, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"{label} has tracked worktree changes")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    recipe = workspace / "recipe"
    root = workspace / "root"
    app = workspace / "app"
    result = Path(os.environ["RUNNER_TEMP"]) / "ni07-07" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status: dict[str, object] = {"state": "preparing", "exit_code": None}
    try:
        _pin(root, ROOT_PIN, "ROOT carrier")
        _pin(app, APP_PIN, "APP candidate")
        install_command = os.environ["NI07_RC10_INSTALL_COMMAND"]
        junit = result / "original-junit.xml"
        os.environ["NI07_RC10_APP_ROOT"] = str(app)
        os.environ["NI07_RC10_JUNIT_XML"] = str(junit)
        os.environ["PYTHONPATH"] = str(app)
        if junit.exists():
            raise RuntimeError("JUnit must be absent before producer starts")

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(
            subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"])
        )
        environment = result / "environment.json"
        environment.write_text(
            json.dumps(
                {
                    "python": sys.version,
                    "platform": platform.platform(),
                    "install_command": install_command,
                    "root_pin": ROOT_PIN,
                    "app_pin": APP_PIN,
                    "selection": SELECTION,
                    "environment": {
                        key: os.environ.get(key)
                        for key in (
                            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                            "PYTHONDONTWRITEBYTECODE",
                            "PYTHONHASHSEED",
                            "PYTHONPATH",
                            "PYTHONUNBUFFERED",
                            "NI07_RC10_APP_ROOT",
                            "NI07_RC10_JUNIT_XML",
                        )
                    },
                    "fixture_scope": "synthetic host arithmetic; no models, inference, corpus or ledger",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        harness = recipe / "artifacts/ni07-07-confidence/ci/reader_pytest.py"
        workflow = recipe / ".github/workflows/ni07-07-rc10.yml"
        conformance = root / "scripts/ci/native_conformance.py"
        inputs = [
            freeze,
            environment,
            Path(__file__).resolve(),
            harness,
            workflow,
            conformance,
            app / SELECTION,
            *(app / relative for relative in APP_READSET),
        ]
        repos = {"root": root, "recipe": recipe, "app": app}
        argv = [
            sys.executable,
            str(conformance),
            "--cwd",
            str(app),
            "--junit",
            str(junit),
            "--output",
            str(result / "native"),
        ]
        for label, repo in repos.items():
            argv.extend(["--repo", f"{label}={repo}"])
        for path in dict.fromkeys(inputs):
            argv.extend(["--read-path", str(path)])
        argv.extend(["--select", SELECTION, "--", sys.executable, str(harness)])
        status["state"] = "running"
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        exit_code = subprocess.call(argv, cwd=app)
        status.update(
            state="passed" if exit_code == 0 else "failed", exit_code=exit_code
        )
        return exit_code
    except Exception as exc:  # noqa: BLE001 - always retain capture/setup failure status
        status.update(
            state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}"
        )
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
