"""Capture NI07-30 standalone guard fixtures with the reviewed native carrier."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "82e398da2478bfd9c3baaddbd0c6fb742d09dafa"
SELECTIONS = (
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_standalone_guard_uses_declared_mode_despite_ambient_and_fleet"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_standalone_guard_explicit_mode_overrides_declared_topology"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_standalone_guard_fails_closed_on_unresolvable_declared_mode"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_standalone_guard_rejects_invalid_explicit_mode_before_validation"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_special_cli_commands_bypass_standalone_numa_admission"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_launch_view_rejects_invalid_explicit_numa_mode_as_could_not_check"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_explicit_launch_numa_mode_bypasses_realized_fleet_probe"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_in_repo_source_pins_are_repo_relative_and_external_ones_absolute"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_relative_source_pin_resolves_against_guard_checkout_not_priors_dir"
    ),
    (
        "tests/unit/test_stack_change_guard.py::"
        "test_shipped_priors_and_descriptors_carry_no_checkout_absolute_pins"
    ),
    (
        "tests/unit/test_stack_change_pipeline.py::"
        "test_resolution_uses_declared_topology_and_ignores_ambient_env"
    ),
    (
        "tests/unit/test_stack_change_pipeline.py::"
        "test_resolution_explicit_mode_wins_and_says_it_is_not_production"
    ),
    "tests/unit/test_stack_change_pipeline.py::test_resolution_rejects_invalid_explicit_mode",
    (
        "tests/unit/test_stack_change_pipeline.py::"
        "test_resolution_without_declaration_fails_check_but_not_update"
    ),
)
EXPECTED_CASES = 20
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
APP_CONTEXTS = (
    "scripts/validate/stack_change_guard.py",
    "scripts/registry/stack_change_pipeline.py",
    "scripts/server/stack_manifest.py",
    "scripts/server/stack_numa.py",
    "scripts/server/stack_paths.py",
    "src/config/__init__.py",
    "src/config/models.py",
    "src/config/validation.py",
    "src/registry/model_descriptors.py",
    "src/registry/stack_priors.py",
    "src/runtime/inference_lock.py",
    "src/scheduling/device_model.py",
    "orchestration/repl_memory/q_scorer.py",
    "orchestration/repl_memory/embedder.py",
    "tests/unit/test_stack_change_guard.py",
    "tests/unit/test_stack_change_pipeline.py",
)
APP_CONFIG_EXTRAS = (
    "orchestration/model_registry.yaml",
    "orchestration/launch_manifest.yaml",
    "orchestration/stack_topology.yaml",
    "orchestration/derived/stack_priors.yaml",
    "orchestration/model_descriptors.yaml",
    "orchestration/gpu_shadow_lane_np_ceiling.yaml",
)
WORKFLOW_PATH = ".github/workflows/ni07-30-standalone-numa-capture.yml"
LOCKED_FIXTURE_PACKAGES = {
    "pytest": "9.0.3",
    "iniconfig": "2.3.0",
    "packaging": "26.0",
    "pluggy": "1.6.0",
    "Pygments": "2.20.0",
    "PyYAML": "6.0.3",
    "numpy": "2.4.4",
    "pydantic": "2.13.0",
    "pydantic-settings": "2.13.1",
    "pydantic-core": "2.46.0",
    "annotated-types": "0.7.0",
    "typing-inspection": "0.4.2",
    "python-dotenv": "1.2.2",
    "typing-extensions": "4.15.0",
}
INSTALL_COMMAND = (
    "python -m pip install pytest==9.0.3 iniconfig==2.3.0 packaging==26.0 "
    "pluggy==1.6.0 Pygments==2.20.0 PyYAML==6.0.3 numpy==2.4.4 "
    "pydantic==2.13.0 pydantic-settings==2.13.1 pydantic-core==2.46.0 "
    "annotated-types==0.7.0 typing-inspection==0.4.2 python-dotenv==1.2.2 "
    "typing-extensions==4.15.0"
)
INERT_OVERRIDES = {
    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "/fixture/kernel-bin",
    "ORCHESTRATOR_PATHS_LLAMA_MTMD": "/fixture/llama-mtmd-cli",
    "ORCHESTRATOR_PATHS_LLAMA_SERVER": "/fixture/llama-server",
    "ORCHESTRATOR_PATHS_PROJECT_ROOT": "",
    "ORCHESTRATOR_PATHS_LLM_ROOT": "",
    "ORCHESTRATOR_PATHS_MODELS_DIR": "",
    "ORCHESTRATOR_PATHS_MODEL_BASE": "",
    "ORCHESTRATOR_PATHS_LOG_DIR": "/dev/null",
    "ORCHESTRATOR_PATHS_CACHE_DIR": "",
    "ORCHESTRATOR_PATHS_TMP_DIR": "",
    "ORCHESTRATOR_PATHS_REGISTRY_PATH": "",
    "ORCHESTRATOR_MOCK_MODE": "1",
    "ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS": "1",
    "ORCHESTRATOR_LOG_DIR": "/dev/null",
    "ORCHESTRATOR_SERVING_CALLS_LOG": "off",
    "ORCHESTRATOR_COHERENCE_JUDGE_LOG": "off",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"{label} checkout is not clean: {status}")
    return git(repo, "rev-parse", "HEAD")


def regular_repo_file(repo: Path, name: str) -> Path:
    path = repo
    if path.is_symlink():
        raise RuntimeError(f"repository checkout is a symlink: {repo}")
    for part in Path(name).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared read traverses a symlink: {name}")
    if not path.is_file():
        raise RuntimeError(f"declared read is missing or not a regular file: {name}")
    return path.absolute()


def tracked_python_config(repo: Path) -> list[Path]:
    paths = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if not name:
            continue
        relative = PurePosixPath(name)
        if relative.suffix == ".py" or relative.name in CONFIG_NAMES:
            paths.append(regular_repo_file(repo, name))
    return paths


def verify_locked_packages(app: Path) -> None:
    lock = tomllib.loads((app / "uv.lock").read_text(encoding="utf-8"))
    locked = {item["name"].lower(): item["version"] for item in lock["package"]}
    for name, expected in LOCKED_FIXTURE_PACKAGES.items():
        if locked.get(name.lower()) != expected:
            raise RuntimeError(f"{name} differs from pinned APP uv.lock")
        actual = importlib.metadata.version(name)
        if actual != expected:
            raise RuntimeError(f"{name} is {actual}, expected {expected}")


def host_memory_context() -> dict[str, str | None]:
    try:
        lines = Path("/proc/meminfo").read_text(encoding="ascii").splitlines()
    except OSError as exc:
        return {"source": "/proc/meminfo", "memtotal_line": None, "read_error": str(exc)}
    line = next((item for item in lines if item.startswith("MemTotal:")), None)
    return {"source": "/proc/meminfo", "memtotal_line": line, "read_error": None}


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / name for name in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni07-30-standalone-numa-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "standalone-numa-synthetic", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ.get("NI07_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("NI07_EXECUTION_CONTEXT") != "offline-synthetic-guard-fixtures":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("NI07_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        for name, expected in INERT_OVERRIDES.items():
            if expected and os.environ.get(name) != expected:
                raise RuntimeError(f"{name} differs from reviewed inert override")
        expected_paths = {
            "ORCHESTRATOR_PATHS_PROJECT_ROOT": str(runner_temp / "ni07-30-inert-project"),
            "ORCHESTRATOR_PATHS_LLM_ROOT": str(runner_temp / "ni07-30-inert-llm"),
            "ORCHESTRATOR_PATHS_MODELS_DIR": str(runner_temp / "ni07-30-inert-models"),
            "ORCHESTRATOR_PATHS_MODEL_BASE": str(runner_temp / "ni07-30-inert-models"),
            "ORCHESTRATOR_PATHS_CACHE_DIR": str(runner_temp / "ni07-30-inert-cache"),
            "ORCHESTRATOR_PATHS_TMP_DIR": str(runner_temp / "ni07-30-inert-tmp"),
            "ORCHESTRATOR_PATHS_REGISTRY_PATH": str(app / "orchestration/model_registry.yaml"),
        }
        for name, expected in expected_paths.items():
            if os.environ.get(name) != expected:
                raise RuntimeError(f"{name} differs from reviewed inert path")
        for name, repo in repos.items():
            expected = {
                "recipe": os.environ["GITHUB_SHA"],
                "carrier": ROOT_CARRIER_PIN,
                "app": APP_PIN,
            }[name]
            if require_clean(repo, name) != expected:
                raise RuntimeError(f"{name} checkout differs from reviewed pin")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN:
            raise RuntimeError("workflow carrier pin differs from reviewed carrier")
        if os.environ.get("APP_PIN") != APP_PIN:
            raise RuntimeError("workflow APP pin differs from reviewed source")
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
                    "execution_context": os.environ["NI07_EXECUTION_CONTEXT"],
                    "repositories": {
                        name: git(repo, "rev-parse", "HEAD") for name, repo in repos.items()
                    },
                    "selections": list(SELECTIONS),
                    "expected_case_count": EXPECTED_CASES,
                    "install_command": INSTALL_COMMAND,
                    "declared_dependencies": LOCKED_FIXTURE_PACKAGES,
                    "dependency_basis": (
                        "The selected guard and pipeline test modules import PyYAML and pytest. "
                        "Importing stack_change_pipeline reaches q_scorer -> TaskEmbedder and "
                        "episodic_store, which require NumPy, then src.inference_lock -> "
                        "src.config, which imports pydantic-settings and its pinned closure. "
                        "All package versions are exact Python 3.13.15 APP uv.lock pins; "
                        "HTTP, JSON-schema and model-serving extras are not in this selected "
                        "top-level import closure."
                    ),
                    "isolation": (
                        "The five new cases use synthetic topology YAML, a fake validation "
                        "seam, and explicit ambient/fleet traps. The four pipeline controls "
                        "call only mode-resolution functions; they do not run update/check. "
                        "Two selected launch-helper controls import static stack_manifest "
                        "under a test-only fixture that intercepts only Path('/proc/meminfo') "
                        "during module import with synthetic 1 TiB MemTotal; other path reads "
                        "delegate unchanged, and the fixture removes the imported module and "
                        "package attribute at teardown while restoring any prior cache. The "
                        "same two tests redirect kernel_paths.PRODUCTION_ROOT to empty "
                        "tmp_path backend directories; real backend_dir validation runs, but "
                        "no executable is created, resolved, or invoked. "
                        "runner's physical /proc/meminfo is read separately "
                        "and recorded below as context, not substituted or asserted as a claim. "
                        "No LLMPrimitives instance/backend execution method, "
                        "endpoint, server, kernel, inference, or live network call is invoked. "
                        "Synthetic MemTotal is a test fixture only, not runner or production "
                        "capacity evidence."
                    ),
                    "app_contexts": list(APP_CONTEXTS),
                    "app_config_extras": list(APP_CONFIG_EXTRAS),
                    "eager_app_reads": [
                        {
                            "path": "orchestration/model_registry.yaml",
                            "reason": (
                                "config validation and stack_paths load registry runtime "
                                "defaults/timeouts; stack_manifest also reads the compiled "
                                "registry at import."
                            ),
                        },
                        {
                            "path": "orchestration/launch_manifest.yaml",
                            "reason": "stack_manifest loads launch declarations at import.",
                        },
                        {
                            "path": "orchestration/stack_topology.yaml",
                            "reason": "stack_numa loads NUMA declarations at import.",
                        },
                        {
                            "path": "orchestration/gpu_shadow_lane_np_ceiling.yaml",
                            "reason": (
                                "stack_manifest's import-time capacity check resolves "
                                "declared VRAM capacity."
                            ),
                        },
                        {
                            "path": "orchestration/derived/stack_priors.yaml",
                            "reason": "the selected portable-pin fixture opens the shipped priors.",
                        },
                        {
                            "path": "orchestration/model_descriptors.yaml",
                            "reason": (
                                "the selected portable-pin fixture opens shipped descriptors."
                            ),
                        },
                    ],
                    "non_eager_paths": [
                        {
                            "path": "orchestration/workload_model.yaml",
                            "reason": (
                                "src.workload_model defines the path, but selected tests do not "
                                "call infer_workload_class, which performs the YAML read."
                            ),
                        },
                        {
                            "path": "orchestrator_runtime_facts.json",
                            "reason": (
                                "no selected test calls get_config or ServerURLsConfig factories "
                                "that build runtime-fact defaults."
                            ),
                        },
                    ],
                    "runtime_contexts": {
                        "pip_freeze": "pip-freeze.txt",
                        "environment_and_host_context": "environment.json",
                        "host_meminfo": host_memory_context(),
                    },
                    "inert_overrides": INERT_OVERRIDES,
                    "resolved_inert_paths": expected_paths,
                    "environment": {
                        key: os.environ.get(key)
                        for key in (
                            "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
                            "PYTHONDONTWRITEBYTECODE",
                            "PYTHONHASHSEED",
                            "PYTHONPATH",
                            "PYTHONUNBUFFERED",
                            *INERT_OVERRIDES,
                        )
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        junit, native_output = result / "original-junit.xml", result / "native"
        if junit.exists() or native_output.exists():
            raise RuntimeError("refusing to overwrite existing capture outputs")
        workflow = recipe / WORKFLOW_PATH
        if workflow.is_symlink() or not workflow.is_file():
            raise RuntimeError("declared recipe workflow is missing or not regular")
        for relative in APP_CONTEXTS:
            regular_repo_file(app, relative)
        app_config_paths = [regular_repo_file(app, relative) for relative in APP_CONFIG_EXTRAS]
        for relative in APP_CONFIG_EXTRAS:
            tree_entry = git(app, "ls-tree", "-r", "HEAD", "--", relative).split(maxsplit=1)
            if not tree_entry or tree_entry[0] != "100644":
                raise RuntimeError(f"APP config extra is not tracked as a regular file: {relative}")

        read_paths = [
            freeze,
            environment,
            workflow.absolute(),
            *tracked_python_config(recipe),
            *tracked_python_config(carrier),
            *tracked_python_config(app),
            *(regular_repo_file(app, relative) for relative in APP_CONTEXTS),
            *app_config_paths,
        ]
        producer_argv = [
            sys.executable,
            str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd",
            str(app),
            "--junit",
            str(junit),
            "--output",
            str(native_output),
            "--repo",
            f"recipe={recipe}",
            "--repo",
            f"carrier={carrier}",
            "--repo",
            f"app={app}",
        ]
        for path in dict.fromkeys(path.resolve() for path in read_paths):
            producer_argv.extend(["--read-path", str(path)])
        for selection in SELECTIONS:
            producer_argv.extend(["--select", selection])

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
            *SELECTIONS,
            f"--junitxml={junit}",
        ]
        status.update(
            state="running",
            repositories={name: git(repo, "rev-parse", "HEAD") for name, repo in repos.items()},
            selections=list(SELECTIONS),
        )
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer_argv, "--", *command], cwd=app)
        receipt_path = native_output / "receipt.json"
        if not receipt_path.is_file():
            status.update(
                state="capture_failed",
                exit_code=code or 1,
                native_metric=None,
                diagnostic="native receipt was not produced",
            )
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        counts = (receipt.get("summary") or {}).get("counts") or {}
        all_cases = (
            counts.get("collected") == EXPECTED_CASES
            and counts.get("executed") == EXPECTED_CASES
            and counts.get("skipped") == 0
            and counts.get("failure") == 0
            and counts.get("error") == 0
        )
        passed = code == 0 and metric is True and all_cases
        status.update(
            state="passed" if passed else "failed",
            exit_code=0 if passed else (code or 1),
            native_metric=metric,
            junit_counts=counts,
            expected_case_count=EXPECTED_CASES,
            all_cases_executed=all_cases,
        )
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
