"""Capture synthetic eval sidecar persistence outcomes with native custody."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

SELECTION = "tests/unit/test_eval_tower_question_persistence.py"
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock"}
APP_CONTEXTS = (
    "scripts/autopilot/eval_tower.py",
    "tests/unit/test_eval_tower_question_persistence.py",
)
LOCKED_FIXTURE_PACKAGES = {
    "pytest": "9.0.3",
    "iniconfig": "2.3.0",
    "packaging": "26.0",
    "pluggy": "1.6.0",
    "Pygments": "2.20.0",
    "httpx": "0.28.1",
    "anyio": "4.13.0",
    "certifi": "2026.2.25",
    "h11": "0.16.0",
    "httpcore": "1.0.9",
    "idna": "3.11",
    "PyYAML": "6.0.3",
}


def git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def require_clean(repo: Path, label: str) -> None:
    status = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
        text=True,
    )
    if status.strip():
        raise RuntimeError(f"{label} checkout is not clean: {status.strip()}")


def tracked_inputs(repo: Path):
    names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"])
    for name in names.decode().split("\0"):
        if not name:
            continue
        path = repo / name
        if path.suffix.lower() == ".py" or path.name in CONFIG_NAMES:
            if not path.is_file():
                raise RuntimeError(f"tracked declared input is missing: {path}")
            yield path.resolve()


def verify_locked_packages(app: Path) -> None:
    lock = tomllib.loads((app / "uv.lock").read_text(encoding="utf-8"))
    locked = {item["name"].lower(): item["version"] for item in lock["package"]}
    for distribution, expected in LOCKED_FIXTURE_PACKAGES.items():
        if locked.get(distribution.lower()) != expected:
            raise RuntimeError(f"fixture dependency {distribution} differs from APP uv.lock")
        actual = importlib.metadata.version(distribution)
        if actual != expected:
            raise RuntimeError(
                f"fixture dependency {distribution} is {actual}, expected lock pin {expected}"
            )


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / name for name in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni07-25-eval-capture-status" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "eval-capture-status", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ["NI07_RUNNER_CONTEXT"] != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError("Python runtime differs from reviewed recipe pin")
        expected_pins = {
            "recipe": os.environ["GITHUB_SHA"],
            "carrier": os.environ["ROOT_CARRIER_PIN"],
            "app": os.environ["APP_PIN"],
        }
        for name, repo in repos.items():
            actual = git_head(repo)
            if actual != expected_pins[name]:
                raise RuntimeError(f"{name} checkout {actual} differs from pin {expected_pins[name]}")
            require_clean(repo, name)

        verify_locked_packages(app)
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
                    "runner_context": os.environ["NI07_RUNNER_CONTEXT"],
                    "recipe_pin": git_head(recipe),
                    "root_carrier_pin": git_head(carrier),
                    "app_pin": git_head(app),
                    "install_command": os.environ["NI07_INSTALL_COMMAND"],
                    "declared_dependencies": LOCKED_FIXTURE_PACKAGES,
                    "dependency_basis": (
                        "The selected module's Python import closure uses stdlib project modules, "
                        "httpx and PyYAML; pytest plus exact APP uv.lock versions for those "
                        "packages and pytest's fixture closure are installed."
                    ),
                    "selected_test": SELECTION,
                    "expected_case_count": 9,
                    "environment": {
                        key: os.environ.get(key)
                        for key in (
                            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                            "PYTHONDONTWRITEBYTECODE",
                            "PYTHONHASHSEED",
                            "PYTHONPATH",
                            "PYTHONUNBUFFERED",
                        )
                    },
                    "isolation": (
                        "Temporary-directory JSONL fixtures and monkeypatched local writer/eval "
                        "methods only; no model, tokenizer, HTTP request, benchmark, server, "
                        "inference or backend execution."
                    ),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        junit = result / "original-junit.xml"
        if junit.exists():
            raise RuntimeError("JUnit must not exist before execution")
        read_paths = [
            freeze,
            environment,
            Path(__file__).resolve(),
            recipe / ".github/workflows/ni07-25-eval-capture-status.yml",
        ]
        for repo in repos.values():
            read_paths.extend(tracked_inputs(repo))
        for name in APP_CONTEXTS:
            context = app / name
            if not context.is_file():
                raise RuntimeError(f"declared APP context is missing: {context}")
            read_paths.append(context.resolve())

        native = carrier / "scripts/ci/native_conformance.py"
        argv = [
            sys.executable,
            str(native),
            "--cwd",
            str(app),
            "--junit",
            str(junit),
            "--output",
            str(result / "native"),
        ]
        for name, repo in repos.items():
            argv.extend(["--repo", f"{name}={repo}"])
        for path in dict.fromkeys(read_paths):
            argv.extend(["--read-path", str(path)])
        argv.extend(["--select", SELECTION])
        command = [
            sys.executable,
            "-m",
            "pytest",
            "--noconftest",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "-q",
            SELECTION,
            f"--junitxml={junit}",
        ]
        status["state"] = "running"
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*argv, "--", *command], cwd=app)
        status.update(state="passed" if code == 0 else "failed", exit_code=code)
        return code
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
