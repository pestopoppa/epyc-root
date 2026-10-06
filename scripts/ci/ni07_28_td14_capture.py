"""Capture TD-14 synthetic fixtures with the reviewed native CI carrier."""
from __future__ import annotations
import importlib.metadata, json, os, platform, subprocess, sys, tomllib
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "4dd914bb5a00d760e2e87c25069daef67305e9ba"
SELECTIONS = (
    "tests/unit/test_typed_decisions.py::TestQuestionInvariants::test_option_descriptions_are_optional_ordered_choice_metadata",
    "tests/unit/test_typed_decisions.py::TestQuestionInvariants::test_option_descriptions_reject_text_as_the_outer_sequence",
    "tests/unit/test_typed_decisions.py::TestQuestionInvariants::test_option_descriptions_reject_unordered_outer_containers",
    "tests/unit/test_typed_decisions.py::TestQuestionInvariants::test_option_descriptions_validate_kind_arity_and_content",
    "tests/unit/test_typed_decisions.py::TestQuestionInvariants::test_descriptions_do_not_change_resolved_choice_labels",
    "tests/unit/test_typed_decisions_measure.py::test_question_json_loader_preserves_optional_descriptions_and_legacy_default",
    "tests/unit/test_typed_decisions_measure.py::test_question_json_loader_rejects_string_as_description_sequence",
    "tests/unit/test_typed_decisions_native.py::TestPromptCueing::test_descriptions_are_label_bound_and_native_layout_roundtrips",
    "tests/unit/test_typed_decisions_native.py::TestPromptCueing::test_legacy_native_prompt_and_layout_omit_descriptions",
)
EXPECTED_CASES = 14
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
APP_CONTEXTS = (
    "src/typed_decisions/types.py", "src/typed_decisions/runner.py",
    "src/typed_decisions/native.py", "src/typed_decisions/measure.py",
    "src/typed_decisions/bench.py", "tests/unit/test_typed_decisions.py",
    "tests/unit/test_typed_decisions_measure.py",
    "tests/unit/test_typed_decisions_native.py",
)
APP_CONFIG_EXTRAS = (
    "orchestration/model_registry.yaml",
)
WORKFLOW_PATH = ".github/workflows/ni07-28-td14-capture.yml"
LOCKED_FIXTURE_PACKAGES = {
    "pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
    "pluggy": "1.6.0", "Pygments": "2.20.0", "httpx": "0.28.1",
    "anyio": "4.13.0", "certifi": "2026.2.25", "h11": "0.16.0",
    "httpcore": "1.0.9", "idna": "3.11", "jsonschema": "4.26.0",
    "attrs": "26.1.0", "jsonschema-specifications": "2025.9.1",
    "referencing": "0.37.0", "rpds-py": "0.30.0",
    "PyYAML": "6.0.3", "pydantic": "2.13.0", "pydantic-settings": "2.13.1",
    "pydantic-core": "2.46.0", "annotated-types": "0.7.0",
    "typing-inspection": "0.4.2", "python-dotenv": "1.2.2",
    "typing-extensions": "4.15.0",
}
INSTALL_COMMAND = (
    "python -m pip install pytest==9.0.3 iniconfig==2.3.0 packaging==26.0 "
    "pluggy==1.6.0 Pygments==2.20.0 httpx==0.28.1 anyio==4.13.0 "
    "certifi==2026.2.25 h11==0.16.0 httpcore==1.0.9 idna==3.11 "
    "jsonschema==4.26.0 attrs==26.1.0 jsonschema-specifications==2025.9.1 "
    "referencing==0.37.0 rpds-py==0.30.0 PyYAML==6.0.3 "
    "pydantic==2.13.0 pydantic-settings==2.13.1 pydantic-core==2.46.0 "
    "annotated-types==0.7.0 typing-inspection==0.4.2 python-dotenv==1.2.2 "
    "typing-extensions==4.15.0"
)
INERT_KERNEL_OVERRIDES = {
    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "/fixture/kernel-bin",
    "ORCHESTRATOR_PATHS_LLAMA_MTMD": "/fixture/llama-mtmd-cli",
    "ORCHESTRATOR_PATHS_LLAMA_SERVER": "/fixture/llama-server",
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

def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / n for n in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni07-28-td14-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "td14-synthetic-capture", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ.get("NI07_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("NI07_EXECUTION_CONTEXT") != "offline-fake-decision-fixtures":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("NI07_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        for name, value in INERT_KERNEL_OVERRIDES.items():
            if os.environ.get(name) != value:
                raise RuntimeError(f"{name} differs from reviewed inert-kernel override")
        expected_pins = {
            "recipe": os.environ["GITHUB_SHA"],
            "carrier": ROOT_CARRIER_PIN,
            "app": APP_PIN,
        }
        pins = {}
        for name, repo in repos.items():
            pins[name] = require_clean(repo, name)
            if pins[name] != expected_pins[name]:
                raise RuntimeError(f"{name} checkout differs from reviewed pin")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN:
            raise RuntimeError("workflow carrier pin differs from reviewed carrier")
        if os.environ.get("APP_PIN") != APP_PIN:
            raise RuntimeError("workflow APP pin differs from reviewed source")
        verify_locked_packages(app)

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(),
            "runner_context": os.environ["NI07_RUNNER_CONTEXT"],
            "execution_context": os.environ["NI07_EXECUTION_CONTEXT"],
            "repositories": pins, "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES, "install_command": INSTALL_COMMAND,
            "declared_dependencies": LOCKED_FIXTURE_PACKAGES,
            "dependency_basis": (
                "The selected test imports reach typed_decisions -> llm_primitives/__init__ "
                "-> primitives/inference -> backends/__init__ -> src.config, registry and "
                "workload modules. Their top-level closure uses httpx, jsonschema, PyYAML, "
                "pydantic, pydantic-settings and the listed runtime dependencies, plus pytest. "
                "These exact 24 pins are from the pinned APP uv.lock for Python 3.13.15."
            ),
            "isolation": (
                "Package initialization imports and defines LLMPrimitives and backend classes; "
                "the selected cases use canned primitives, a fake tokenizer, temporary JSON "
                "fixtures, and native prompt/layout helpers. No LLMPrimitives instance or "
                "backend is constructed, and no LLMPrimitives/backend execution method, "
                "endpoint, server, kernel, or inference is invoked. Exact node IDs exclude "
                "later native wire-stack tests."
            ),
            "inert_kernel_overrides": INERT_KERNEL_OVERRIDES,
            "app_config_extras": list(APP_CONFIG_EXTRAS),
            "configuration_context": {
                "eager_app_reads": [
                    {
                        "path": "orchestration/model_registry.yaml",
                        "reason": (
                            "src.config class defaults call _registry_runtime_value and "
                            "_registry_timeout during package initialization; both resolve "
                            "the same cached registry YAML from the APP checkout."
                        ),
                    }
                ],
                "non_eager_paths": [
                    {
                        "path": "orchestration/workload_model.yaml",
                        "reason": (
                            "src.workload_model defines this default path but does not load "
                            "the YAML until infer_workload_class is invoked; selected tests "
                            "do not construct LLMPrimitives or call that method."
                        ),
                    },
                    {
                        "path": "orchestration/derived/stack_priors.yaml",
                        "reason": (
                            "ServerURLsConfig default factories can read this path, but no "
                            "selected test constructs that config or calls get_config."
                        ),
                    },
                    {
                        "path": "orchestrator_runtime_facts.json",
                        "reason": (
                            "The runtime-facts reader is reached only while building "
                            "ServerURLsConfig defaults; selected tests do not build them."
                        ),
                    },
                ],
                "kernel_overrides": INERT_KERNEL_OVERRIDES,
                "kernel_path_use": "none; no kernel path is opened or executed",
            },
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE",
                "PYTHONHASHSEED", "PYTHONPATH", "PYTHONUNBUFFERED",
                "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_LOG_DIR",
                "ORCHESTRATOR_SERVING_CALLS_LOG", "ORCHESTRATOR_COHERENCE_JUDGE_LOG",
                *INERT_KERNEL_OVERRIDES,
            )},
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit, native_output = result / "original-junit.xml", result / "native"
        if junit.exists() or native_output.exists():
            raise RuntimeError("refusing to overwrite existing capture outputs")
        workflow = recipe / WORKFLOW_PATH
        if workflow.is_symlink() or not workflow.is_file():
            raise RuntimeError("declared recipe workflow is missing or not regular")
        app_context_paths = [regular_repo_file(app, relative) for relative in APP_CONTEXTS]
        app_config_paths = [regular_repo_file(app, relative) for relative in APP_CONFIG_EXTRAS]
        for relative in APP_CONFIG_EXTRAS:
            tree_entry = git(app, "ls-tree", "-r", "HEAD", "--", relative).split(maxsplit=1)
            if not tree_entry or tree_entry[0] != "100644":
                raise RuntimeError(f"APP config extra is not tracked as a regular file: {relative}")

        read_paths = [
            freeze, environment, workflow.absolute(),
            *tracked_python_config(recipe), *tracked_python_config(carrier),
            *tracked_python_config(app), *app_context_paths, *app_config_paths,
        ]
        producer_argv = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(app), "--junit", str(junit), "--output", str(native_output),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
            "--repo", f"app={app}",
        ]
        for path in dict.fromkeys(path.resolve() for path in read_paths):
            producer_argv.extend(["--read-path", str(path)])
        for selection in SELECTIONS:
            producer_argv.extend(["--select", selection])

        command = [
            sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
            "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}",
        ]
        status.update(state="running", repositories=pins, selections=list(SELECTIONS))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer_argv, "--", *command], cwd=app)
        receipt_path = native_output / "receipt.json"
        if not receipt_path.is_file():
            status.update(
                state="capture_failed", exit_code=code or 1,
                native_metric=None, diagnostic="native receipt was not produced",
            )
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        case_gate = (
            counts.get("collected") == EXPECTED_CASES
            and counts.get("executed") == EXPECTED_CASES
            and counts.get("skipped") == 0
            and counts.get("failure") == 0
            and counts.get("error") == 0
        )
        passed = code == 0 and metric is True and case_gate
        status.update(
            state="passed" if passed else "failed",
            exit_code=0 if passed else (code or 1),
            native_metric=metric,
            junit_counts=counts,
            expected_case_count=EXPECTED_CASES,
            all_cases_executed=case_gate,
        )
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
