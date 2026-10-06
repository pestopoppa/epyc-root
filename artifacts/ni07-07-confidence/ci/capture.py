#!/usr/bin/env python3
"""Capture exact APP fixtures through the pinned ROOT native carrier."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "b087a506317ba2422f5d14b790655e13e5ea032f"
SELECTION = "tests/unit/test_confidence_expectation.py"
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock"}
APP_GRADING_SPECS = (
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


def _tracked_python_and_config(repo: Path) -> set[Path]:
    names = (
        subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"])
        .decode()
        .split("\0")
    )
    selected: set[Path] = set()
    for name in names:
        if not name:
            continue
        relative = Path(name)
        if relative.suffix.lower() != ".py" and relative.name not in CONFIG_NAMES:
            continue
        path = repo / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"tracked source/config is not a regular file: {path}")
        selected.add(path.resolve())
    return selected


def _load_native_reader(conformance: Path):
    spec = importlib.util.spec_from_file_location(
        "ni07_native_conformance", conformance
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned native reader: {conformance}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        recipe_pin = os.environ["GITHUB_SHA"].lower()
        _pin(recipe, recipe_pin, "recipe")
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
                    "recipe_pin": recipe_pin,
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

        carrier_workflow = root / ".github/workflows/ni06.yml"
        recipe_workflow = recipe / ".github/workflows/ni07-07-rc10.yml"
        conformance = root / "scripts/ci/native_conformance.py"
        source_union = (
            _tracked_python_and_config(root)
            | _tracked_python_and_config(app)
            | _tracked_python_and_config(recipe)
        )
        declared = source_union | {
            carrier_workflow.resolve(),
            recipe_workflow.resolve(),
            conformance.resolve(),
            *[app / relative for relative in APP_GRADING_SPECS],
            freeze.resolve(),
            environment.resolve(),
        }
        if not carrier_workflow.is_file() or not recipe_workflow.is_file():
            raise RuntimeError("required carrier/recipe workflow is absent")
        declared = {path.resolve() for path in declared}

        repos = {"root": root, "app": app, "recipe": recipe}
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
        for path in sorted(declared, key=str):
            argv.extend(["--read-path", str(path)])
        argv.extend(
            [
                "--select",
                SELECTION,
                "--",
                sys.executable,
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "--noconftest",
                "-p",
                "no:cacheprovider",
                "-q",
                SELECTION,
                f"--junitxml={junit}",
            ]
        )

        status["state"] = "running"
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        exit_code = subprocess.call(argv, cwd=app)
        receipt_path = result / "native/receipt.json"
        if not receipt_path.is_file():
            raise RuntimeError("native carrier did not produce its original receipt")
        native = _load_native_reader(conformance)
        record, _ = native.read_receipt(receipt_path)
        actual_rows = record["readset"]
        actual_paths = [Path(item["name"]).resolve() for item in actual_rows]
        if len(actual_paths) != len(set(actual_paths)) or set(actual_paths) != declared:
            missing = sorted(map(str, declared - set(actual_paths)))
            extra = sorted(map(str, set(actual_paths) - declared))
            raise RuntimeError(
                f"native readset differs from exact source union: missing={missing}; extra={extra}"
            )
        expected_repos = {
            "root": ROOT_PIN,
            "app": APP_PIN,
            "recipe": recipe_pin,
        }
        if record["repositories"] != expected_repos or record["selections"] != [
            SELECTION
        ]:
            raise RuntimeError(
                "native receipt repository pins or test selection differ"
            )
        if exit_code == 0 and record["fixture_execution_conformant"] is not True:
            raise RuntimeError("zero exit contradicts native fixture receipt")
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
