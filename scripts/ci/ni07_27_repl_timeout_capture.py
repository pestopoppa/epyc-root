"""Capture terminal REPL timeout regressions with native custody."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

SELECTIONS = (
    "tests/unit/test_persister.py",
    "tests/unit/test_repl_executor.py",
    "tests/unit/test_safe_pickle.py",
    "tests/unit/test_repl_environment.py::TestExecuteTimeout::test_alarm_timeout_marks_terminal_and_refuses_later_execute",
    "tests/unit/test_repl_environment.py::TestExecuteTimeout::test_structured_alarm_timeout_is_sticky",
    "tests/unit/test_repl_environment.py::TestExecuteTimeout::test_restricted_timeout_result_marks_terminal_without_executor_import",
    "tests/unit/test_graph_helpers.py::TestReplTimeoutTerminal::test_terminal_environment_stops_future_turn_before_llm_work",
    "tests/unit/test_graph_helpers.py::TestReplTimeoutTerminal::test_execute_turn_timeout_does_not_rescue_final_or_export_artifacts",
    "tests/unit/test_graph_helpers.py::TestReplTimeoutTerminal::test_late_worker_cannot_resume_execute_or_checkpoint",
)
SELECTED_FILES = tuple(dict.fromkeys(item.split("::", 1)[0] for item in SELECTIONS))
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock"}
APP_CONTEXTS = (
    "src/api/routes/chat_pipeline/repl_executor.py",
    "src/graph/helpers.py",
    "src/repl_environment/environment.py",
    "src/repl_environment/state.py",
    "src/repl_environment/types.py",
    "src/restricted_executor.py",
    "src/session/lease.py",
    "src/session/persister.py",
    "src/session/models.py",
    "src/session/sqlite_store.py",
    "orchestration/model_registry.yaml",
    "orchestration/tool_registry.yaml",
    "orchestration/derived/stack_priors.yaml",
    "orchestration/workload_model.yaml",
    *SELECTED_FILES,
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
EXPECTED_CASES = 123  # 117 NI24 cases, including safe_pickle parametrization, plus six timeout cases.
EXPECTED_PINS = {
    "app": "506acf51a060adc85e4c693221a2f50cd3342968",
    "carrier": "4c0c653baf1654c8c25c66433cf39c8faefd8e52",
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


def reject_symlink_components(repo: Path, name: str) -> Path:
    path = repo
    if path.is_symlink():
        raise RuntimeError(f"repository checkout is a symlink: {repo}")
    for part in Path(name).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"tracked input traverses a symlink: {name}")
    if not path.is_file():
        raise RuntimeError(f"tracked declared input is missing or not a file: {name}")
    return path.absolute()


def tracked_inputs(repo: Path):
    names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"])
    for name in names.decode().split("\0"):
        if not name:
            continue
        path = repo / name
        if path.suffix.lower() == ".py" or path.name in CONFIG_NAMES:
            yield reject_symlink_components(repo, name)


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
    result = runner_temp / "ni07-27-repl-timeout" / "result"
    result.mkdir(parents=True, exist_ok=True)
    runtime_context = result / "runtime-context"
    runtime_context.mkdir(parents=True, exist_ok=True)
    runtime_facts_fixture = runtime_context / "orchestrator_runtime_facts.json"
    runtime_facts_fixture.write_text('{}\n', encoding="utf-8")
    runtime_flags_fixture = result / "runtime-flags-fixture.json"
    runtime_flags_fixture.write_text('{"flags":{}}\n', encoding="utf-8")
    isolated_logs = result.parent / "logs"
    isolated_logs.mkdir(parents=True, exist_ok=True)
    os.environ["ORCHESTRATOR_RUNTIME_FLAGS_PATH"] = str(runtime_flags_fixture)
    os.environ["TMPDIR"] = str(runtime_context)
    os.environ["ORCHESTRATOR_PATHS_LLM_ROOT"] = str(runtime_context)
    os.environ["ORCHESTRATOR_PATHS_TMP_DIR"] = str(runtime_context)
    os.environ["ORCHESTRATOR_PATHS_LOG_DIR"] = str(isolated_logs)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "repl-timeout", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        for name, expected in EXPECTED_PINS.items():
            env_name = "APP_PIN" if name == "app" else "ROOT_CARRIER_PIN"
            if os.environ.get(env_name) != expected:
                raise RuntimeError(f"{env_name} differs from recipe-pinned {name} SHA")
        isolation = {
            "ORCHESTRATOR_MOCK_MODE": "1",
            "ORCHESTRATOR_SERVING_CALLS_LOG": "off",
            "ORCHESTRATOR_COHERENCE_JUDGE": "0",
            "ORCHESTRATOR_COHERENCE_JUDGE_LOG": "off",
            "ORCHESTRATOR_PATHS_PROJECT_ROOT": str(app),
        }
        for name, expected in isolation.items():
            if os.environ.get(name) != expected:
                raise RuntimeError(f"{name} is not set to reviewed isolated value {expected!r}")
        if os.environ["NI27_RUNNER_CONTEXT"] != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if sys.version_info[:3] != (3, 13, 15):
            raise RuntimeError(f"Python is {sys.version_info[:3]}, expected (3, 13, 15)")
        uv_version = subprocess.check_output(["uv", "--version"], text=True).strip()
        if not uv_version.startswith("uv 0.8.15"):
            raise RuntimeError(f"uv version is {uv_version!r}, expected uv 0.8.15")
        expected_pins = {
            "recipe": os.environ["GITHUB_SHA"],
            "carrier": EXPECTED_PINS["carrier"],
            "app": EXPECTED_PINS["app"],
        }
        for name, repo in repos.items():
            actual = git_head(repo)
            if actual != expected_pins[name]:
                raise RuntimeError(f"{name} checkout {actual} differs from pin {expected_pins[name]}")
            require_clean(repo, name)

        verify_locked_packages(app)
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(
            subprocess.check_output(
                ["uv", "pip", "freeze", "--python", sys.executable]
            )
        )
        environment = result / "environment.json"
        environment.write_text(
            json.dumps(
                {
                    "python": sys.version,
                    "uv_version": uv_version,
                    "platform": platform.platform(),
                    "runner_context": os.environ["NI27_RUNNER_CONTEXT"],
                    "recipe_pin": git_head(recipe),
                    "root_carrier_pin": git_head(carrier),
                    "app_pin": git_head(app),
                    "install_command": os.environ["NI27_INSTALL_COMMAND"],
                    "declared_dependencies": LOCKED_FIXTURE_PACKAGES,
                    "dependency_basis": (
                        "Application and graph dependencies (including pydantic-graph and langgraph) use frozen "
                        "uv.lock sync. pytest and pytest-asyncio plus their exact lock closure are explicit fixture "
                        "packages. networkx==3.6.1 is an explicit lock-pinned graph metadata fixture because the "
                        "base no-dev sync excludes its optional torch path. model_registry.yaml and tool_registry.yaml "
                        "plus derived stack priors and workload model are captured runtime contexts; runtime flags "
                        "use an empty offhost fixture, and runtime facts use an empty rejected-manifest fixture. "
                        "No sandbox/model extras are installed."
                    ),
                    "runtime_flags_fixture": str(runtime_flags_fixture),
                    "selected_tests": list(SELECTIONS),
                    "expected_collected_cases": EXPECTED_CASES,
                    "expected_skips": 0,
                    "environment": {
                        key: os.environ.get(key)
                        for key in (
                            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                            "PYTHONDONTWRITEBYTECODE",
                            "PYTHONHASHSEED",
                            "PYTHONPATH",
                            "PYTHONUNBUFFERED",
                            "ORCHESTRATOR_SESSION_HMAC_KEY",
                            "ORCHESTRATOR_RUNTIME_FLAGS_PATH",
                            "ORCHESTRATOR_MOCK_MODE",
                            "ORCHESTRATOR_SERVING_CALLS_LOG",
                            "ORCHESTRATOR_COHERENCE_JUDGE",
                            "ORCHESTRATOR_COHERENCE_JUDGE_LOG",
                            "ORCHESTRATOR_PATHS_PROJECT_ROOT",
                            "ORCHESTRATOR_PATHS_LLM_ROOT",
                            "ORCHESTRATOR_PATHS_TMP_DIR",
                            "ORCHESTRATOR_PATHS_LOG_DIR",
                            "TMPDIR",
                            "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN",
                            "ORCHESTRATOR_PATHS_LLAMA_MTMD",
                            "ORCHESTRATOR_PATHS_LLAMA_SERVER",
                        )
                    },
                    "isolation": (
                        "Timeout tests use fake LLM primitives and bounded threading Events. The late worker is "
                        "released and joined in a finally block; tests assert terminal execute/checkpoint refusal "
                        "and that timeout output neither FINAL-rescues nor exports existing artifacts. Restricted "
                        "timeout classification uses a small executor double; no RestrictedPython backend, real "
                        "models, embeddings, encoders, tokenizers, inference backend, server, benchmark or live "
                        "session is constructed or queried. SQLite session/lease tests use temporary files."
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
            runtime_flags_fixture,
            runtime_facts_fixture,
            Path(__file__).absolute(),
            reject_symlink_components(recipe, ".github/workflows/ni07-27-repl-timeout.yml"),
        ]
        for repo in repos.values():
            read_paths.extend(tracked_inputs(repo))
        for name in APP_CONTEXTS:
            read_paths.append(reject_symlink_components(app, name))

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
        if junit.is_file():
            root = ET.parse(junit).getroot()
            suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
            cases = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
            skipped = sum(int(suite.attrib.get("skipped", 0)) for suite in suites)
            status.update(collected_cases=cases, skipped_cases=skipped)
            if code == 0 and cases != EXPECTED_CASES:
                code = 1
                status["error"] = f"JUnit reports {cases} cases, expected {EXPECTED_CASES}"
            if code == 0 and skipped != 0:
                code = 1
                status["error"] = f"JUnit reports {skipped} skipped cases, expected zero"
        status.update(state="passed" if code == 0 else "failed", exit_code=code)
        return code
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
