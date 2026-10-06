"""Capture DCP ColGREP hit-span packing fixtures with native synthetic CI custody."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "8739c03486819aba2e59f9141bbf7ad977e26dbe"
SELECTION = "tests/unit/test_context_assembly.py"
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
APP_SOURCE_PATHS = (
    "src/context_assembly.py",
    "tests/unit/test_context_assembly.py",
)
RECIPE_WORKFLOW = ".github/workflows/ni07-dcp-hit-span.yml"
INSTALL_COMMAND = (
    "python -m pip install pytest==9.0.3 iniconfig==2.3.0 "
    "packaging==26.0 pluggy==1.6.0 Pygments==2.20.0"
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean_tracked(repo: Path, label: str) -> str:
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError(f"{label} checkout has tracked changes")
    return git(repo, "rev-parse", "HEAD")


def tracked_python_config(repo: Path) -> list[Path]:
    paths = []
    for name in git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines():
        rel = PurePosixPath(name)
        if rel.suffix == ".py" or rel.name in CONFIG_NAMES:
            path = repo / name
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"tracked input is not a regular file: {name}")
            paths.append(path.resolve())
    return paths


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / name for name in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni07-dcp-hit-span" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "dcp-hit-span", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ.get("NI07_RUNNER_CONTEXT") != "ubuntu-latest":
            raise ValueError("runner context differs from the reviewed recipe")
        if os.environ.get("NI07_EXECUTION_CONTEXT") != "offline-pure-candidate-fixtures":
            raise ValueError("execution context differs from the reviewed recipe")
        if sys.version_info[:3] != (3, 13, 15):
            raise ValueError(f"unexpected Python version: {sys.version}")
        expected_versions = {
            "pytest": "9.0.3", "iniconfig": "2.3.0",
            "packaging": "26.0", "pluggy": "1.6.0", "Pygments": "2.20.0",
        }
        for package, expected in expected_versions.items():
            if importlib.metadata.version(package) != expected:
                raise ValueError(f"{package} does not match pinned version {expected}")
        if os.environ.get("NI07_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise ValueError("dependency install command differs from the reviewed recipe")
        if os.environ.get("APP_PIN") != APP_PIN:
            raise ValueError("workflow APP pin differs from the reviewed source commit")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN:
            raise ValueError("workflow carrier pin differs from this capture source")

        pins = {name: require_clean_tracked(repo, name) for name, repo in repos.items()}
        if pins["recipe"] != os.environ.get("GITHUB_SHA"):
            raise ValueError("recipe checkout does not match GITHUB_SHA")
        if pins["app"] != APP_PIN:
            raise ValueError("APP checkout does not match its reviewed source commit")
        if pins["carrier"] != ROOT_CARRIER_PIN:
            raise ValueError("ROOT checkout does not match the reviewed native carrier")
        for rel in APP_SOURCE_PATHS:
            path = app / rel
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"required APP source is not a regular file: {rel}")
        capture_script = recipe / ".github/ci/ni07_dcp_hit_span_capture.py"
        workflow = recipe / RECIPE_WORKFLOW
        if not capture_script.is_file() or not workflow.is_file():
            raise ValueError("recipe capture script or workflow is missing")

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(
            subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"])
        )
        context = result / "context.json"
        context.write_text(
            json.dumps(
                {
                    "python": sys.version,
                    "platform": platform.platform(),
                    "runner_context": os.environ["NI07_RUNNER_CONTEXT"],
                    "execution_context": os.environ["NI07_EXECUTION_CONTEXT"],
                    "repositories": pins,
                    "selected_test": SELECTION,
                    "install_command": INSTALL_COMMAND,
                    "declared_dependencies": [f"{name}=={version}" for name, version in expected_versions.items()],
                    "dependency_basis": (
                        "The selected context assembly module imports pytest and otherwise "
                        "uses the standard library and repository module. Pytest 9.0.3 and "
                        "its four runtime dependencies match exact APP uv.lock resolutions. "
                        "The tests build in-memory Candidate objects; no model, index, file "
                        "reader, endpoint, or live context assembly is used."
                    ),
                    "environment": {
                        key: os.environ.get(key)
                        for key in (
                            "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE",
                            "PYTHONHASHSEED", "PYTHONPATH", "ORCHESTRATOR_MOCK_MODE",
                            "ORCHESTRATOR_LOG_DIR", "ORCHESTRATOR_SERVING_CALLS_LOG",
                            "ORCHESTRATOR_COHERENCE_JUDGE_LOG", "NI07_RUNNER_CONTEXT",
                            "NI07_EXECUTION_CONTEXT", "NI07_INSTALL_COMMAND",
                        )
                    },
                    "scope": (
                        "Pure Candidate fixtures verify that ColGREP entries with hit spans "
                        "retain only their existing FULL/SLICES mode ceiling or are excluded "
                        "with missing-evidence metadata, while spanless and non-ColGREP "
                        "fallbacks remain unchanged. No model, index, serving process, "
                        "quality score, or inference is run."
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        junit = result / "original-junit.xml"
        native_output = result / "native"
        if junit.exists() or native_output.exists():
            raise ValueError("refusing to overwrite existing capture output")

        read_paths = [
            freeze, context, workflow.resolve(), *tracked_python_config(recipe),
            *tracked_python_config(carrier), *tracked_python_config(app),
            *(app / rel for rel in APP_SOURCE_PATHS), capture_script.resolve(),
        ]
        native = carrier / "scripts/ci/native_conformance.py"
        producer_argv = [
            sys.executable, str(native), "--cwd", str(app), "--junit", str(junit),
            "--output", str(native_output), "--repo", f"recipe={recipe}",
            "--repo", f"carrier={carrier}", "--repo", f"app={app}",
        ]
        for path in dict.fromkeys(path.resolve() for path in read_paths):
            producer_argv.extend(["--read-path", str(path)])
        producer_argv.extend(["--select", SELECTION])
        command = [
            sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
            "-p", "no:cacheprovider", "-q", SELECTION, f"--junitxml={junit}",
        ]
        status.update(state="running", repositories=pins, selection=SELECTION)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer_argv, "--", *command], cwd=app)
        status.update(state="passed" if code == 0 else "failed", exit_code=code)
        return code
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
