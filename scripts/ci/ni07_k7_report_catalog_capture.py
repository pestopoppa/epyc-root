"""Capture the selected offline K7 report dependency fixture with native custody."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

SELECTION = "tests/unit/test_kb_rag_eval.py"
CONFIG_NAMES = {
    "pyproject.toml",
    "pytest.ini",
    "setup.cfg",
    "tox.ini",
    "uv.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
}
APP_INPUTS = (
    "scripts/kb_rag/eval_k7.py",
    "tests/unit/test_kb_rag_eval.py",
)


def tracked_inputs(repo: Path):
    names = (
        subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"])
        .decode()
        .split("\0")
    )
    for name in names:
        if not name:
            continue
        path = repo / name
        if path.suffix.lower() == ".py" or path.name in CONFIG_NAMES:
            if not path.is_file():
                raise RuntimeError(f"tracked declared input is missing: {path}")
            yield path.resolve()


def git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / name for name in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni07-k7-report" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "k7-report-catalog", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if git_head(app) != os.environ["APP_PIN"]:
            raise RuntimeError("APP checkout does not match its reviewed pin")
        if git_head(carrier) != os.environ["ROOT_CARRIER_PIN"]:
            raise RuntimeError("ROOT carrier checkout does not match its reviewed pin")
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
                    "app_pin": os.environ["APP_PIN"],
                    "root_carrier_pin": os.environ["ROOT_CARRIER_PIN"],
                    "recipe_pin": git_head(recipe),
                    "install_command": os.environ["NI07_K7_INSTALL_COMMAND"],
                    "declared_dependencies": [
                        "pytest==8.4.2",
                        "numpy==2.3.2",
                        "PyYAML==6.0.2",
                    ],
                    "dependency_basis": (
                        "pytest executes the selected module; numpy is imported by the K7 "
                        "evaluation retrieval module and encoder seams; PyYAML is the "
                        "declared KB-RAG configuration dependency. No ONNX session or "
                        "model endpoint is initialized by the selected offline fixture."
                    ),
                    "selected_test": SELECTION,
                    "environment": {
                        key: os.environ.get(key)
                        for key in (
                            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                            "PYTHONDONTWRITEBYTECODE",
                            "PYTHONPATH",
                            "PYTHONHASHSEED",
                            "ORCHESTRATOR_MOCK_MODE",
                            "ORCHESTRATOR_LOG_DIR",
                            "ORCHESTRATOR_SERVING_CALLS_LOG",
                            "ORCHESTRATOR_COHERENCE_JUDGE_LOG",
                            "KB_RAG_QUERY_LENGTH_LOG",
                        )
                    },
                    "isolation": (
                        "temporary SQLite catalogs and temporary report files; query_fn is "
                        "fake; encoder loading is trapped; no corpus, ONNX session, model "
                        "HTTP, inference, benchmark, or K7 execution."
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
            recipe / ".github/workflows/ni07-k7-report-catalog.yml",
        ]
        for repo in repos.values():
            read_paths.extend(tracked_inputs(repo))
        for name in APP_INPUTS:
            path = app / name
            if not path.is_file():
                raise RuntimeError(f"selected APP source is missing: {path}")
            read_paths.append(path.resolve())

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
        status.update(
            state="capture_failed",
            exit_code=1,
            error=f"{type(exc).__name__}: {exc}",
        )
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
