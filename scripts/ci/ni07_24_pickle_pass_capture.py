"""Capture signed-pickle checkpoint transport regressions with native custody."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

SELECTIONS = (
    "tests/unit/test_persister.py",
    "tests/unit/test_repl_executor.py",
    "tests/unit/test_safe_pickle.py",
)
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock"}
APP_CONTEXTS = (
    "src/api/routes/chat_pipeline/repl_executor.py",
    "src/session/persister.py",
    "src/repl_environment/safe_pickle.py",
    "src/repl_environment/state.py",
    "src/session/models.py",
    "src/session/sqlite_store.py",
    *SELECTIONS,
)
LOCKED_FIXTURE_PACKAGES = {
    'pytest': '9.0.3',
    'pytest-asyncio': '1.3.0',
    'numpy': '2.4.4',
    'PyYAML': '6.0.3',
    'jsonschema': '4.26.0',
    'httpx': '0.28.1',
    'pydantic': '2.13.0',
    'pydantic-settings': '2.13.1',
    'fastapi': '0.135.3',
    'starlette': '1.0.0',
    'anyio': '4.13.0',
    'pydantic-graph': '1.80.0',
    'langgraph': '1.1.6',
    'langgraph-checkpoint-sqlite': '3.0.3',
    'networkx': '3.6.1',
    'scikit-learn': '1.8.0',
    'faiss-cpu': '1.13.2',
    'onnxruntime': '1.26.0',
    'tokenizers': '0.22.2',
    'Pillow': '12.2.0',
    'mcp': '1.27.0',
    'psutil': '7.2.2',
    'requests': '2.33.1',
    'rich': '15.0.0',
    'markdown-it-py': '4.0.0',
    'sse-starlette': '3.3.4',
    'cachetools': '7.0.5',
    'langchain-core': '1.2.28',
    'attrs': '26.1.0',
    'iniconfig': '2.3.0',
    'packaging': '26.0',
    'pluggy': '1.6.0',
    'Pygments': '2.20.0',
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
    result = runner_temp / "ni07-24-pickle-pass" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "pickle-pass", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ["NI07_RUNNER_CONTEXT"] != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
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
                        "Application dependencies are installed by frozen uv.lock sync; pytest and pytest-asyncio "
                        "are installed at exact lock versions with their exact lock closure."
                    ),
                    "selected_tests": list(SELECTIONS),
                    "environment": {
                        key: os.environ.get(key)
                        for key in (
                            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                            "PYTHONDONTWRITEBYTECODE",
                            "PYTHONHASHSEED",
                            "PYTHONPATH",
                            "PYTHONUNBUFFERED",
                            "ORCHESTRATOR_SESSION_HMAC_KEY",
                        )
                    },
                    "isolation": (
                        "Injected string bodies and callbacks only; no model, tokenizer, "
                        "GitNexus, benchmark, server, inference or backend execution."
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
            recipe / ".github/workflows/ni07-24-pickle-pass.yml",
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
        for name in SELECTIONS:
            argv.extend(["--select", name])
        command = [
            sys.executable,
            "-m",
            "pytest",
            "--noconftest",
            "-o",
            "addopts=",
            "-p",
            "pytest_asyncio.plugin",
            "-p",
            "no:cacheprovider",
            "-q",
            *SELECTIONS,
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
