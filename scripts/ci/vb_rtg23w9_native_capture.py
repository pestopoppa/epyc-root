"""Capture RTG-23 W9 full planner-evidence unit module on GitHub Actions."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import stat
import tomllib
import traceback
from typing import Any
from pathlib import PurePosixPath

SOURCE_PIN = "508bce0ef804d03caf761eb8807801e48dd327d4"
ROOT_CONTEXT_PIN = "0da62ca1cb484f54f0e58dc514f10cd61b9ac001"
ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_LOCK_PIN = "94a6e8d41ec7d3f7a122f66bad53aa673d401d8a"
PYTHON_PIN = "3.13.15"
EXPECTED_CASES_PATH = "scripts/ci/vb_rtg23w9_native_cases.json"
REQUIREMENTS_PATH = "scripts/ci/vb_rtg23w9_native_requirements.txt"
WORKFLOW_PATH = ".github/workflows/vb-rtg23w9-native-conformance.yml"
DRIVER_PATH = "scripts/ci/vb_rtg23w9_native_capture.py"
TASK_PATH = "handoffs/active/objective-task-rate-goodput.md"
TABLE_PATH = "scripts/vidya/adapters/README.md"
VB_PROGRAM_PATH = "handoffs/active/vidya-belief-substrate-program.md"
TASK_SHA256 = "447b955e6cd8aaffdd5b3e8d57d067370e137d800452924d3377d3a26b247ba9"
TABLE_SHA256 = "037fd24d69fb2f541fa7eae5bc40ae95f10075e00d60d7267950789c91d169e3"
VB_PROGRAM_SHA256 = "16dd6029f1678b49cadf483f15b33c272bedc3878a7f8fe267679c80fde354f6"
ROOT_CONTEXT_BLOBS = {
    TASK_PATH: "cf7b75ed98bd6f92a31f69fe57327e6fc03b6c30",
    TABLE_PATH: "800a6e04910394d0d0bcd9c54db537961d553208",
    VB_PROGRAM_PATH: "634ecfdc7f02e87a5d10831bab8773061603d4de",
}
APP_LOCK = "uv.lock"
APP_LOCK_BLOBS = {
    "pyproject.toml": "b4fe6ccada3a1aee3e08aa860045a78d8b85c7b1",
    "uv.lock": "ef2306018773ff9a1e80389970d92f66fcf8d5b7",
}
PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3", "pyyaml": "6.0.3",
}

APP_BLOBS = {'src/__init__.py': 'ff893046a8e7d2598657b950e9e41449f358d25f', 'src/autopilot_core/__init__.py': '27c9fe394da9d9ea2f2f4b64d254bf99fa8aaa37', 'src/autopilot_core/action_identity.py': 'de768dfce1199a1011a30d1db8db78ec5820e605', 'src/autopilot_core/infra_fingerprint.py': '5673025fff54213490cc6eee12a91ab1645074e3', 'src/autopilot_core/journal_reconstruction.py': '25e224dd700087aa4f8acc545c9505434df50bf7', 'src/autopilot_core/learning_exclusions.py': '82adbc3dab68470570ec8fe0edf62d238ff8b093', 'src/autopilot_core/measurement_guards.py': 'd01f62fdf7fe4ab31621ae3ff3483b68bf3ef1a6', 'src/autopilot_core/multitier_decision.py': '5dce1594af423b7a91e7eec916741fb39de02854', 'src/autopilot_core/pareto_math.py': '91f3e59e0918c93004ad4a4f61fe1d384eb48d78', 'src/autopilot_core/planner_evidence.py': '68f515cf1e89b49acace1f7469643441235f90cf', 'src/autopilot_core/rlvr_tiers.py': '19d3813492f3b26807db22daad491fc1bf470e05', 'src/autopilot_core/sequential_verdict.py': '5086b05f9e7517b1c8b7a9b3934f2b57da5f0356', 'src/autopilot_core/tier_specs.py': 'ba47f3dd40b19521c4939a064493362c57ccc998', 'src/registry/__init__.py': '287333a63889217a52c0082a7e316dc64670ee1f', 'src/registry/kernel_paths.py': '6bb3dad23130a763dc4c456c7c432a9535536f30', 'tests/__init__.py': 'd4839a6b14c11e64143d1d200c2d4733595ffc6c', 'tests/unit/__init__.py': '4a5d26360bce3309c1d761d1529117cec7d42e40', 'tests/unit/test_planner_evidence.py': '5f89516aaa694f95281bfc777de8b4aeb21cd3c9'}
CARRIER_BLOBS = {
    "scripts/ci/native_conformance.py": "d2d7bd90f86cffa23c51db803288641c5c6fe461",
    "scripts/vidya/adapters/ci_conformance.py": "b5a521ef4debe7ad105830f5fa27bbf9c2168dcd",
    "scripts/vidya/claim_tuple.py": "309af769e45245fd1452482eb2e0592a86a4a79f",
    "scripts/vidya/lattice.py": "de0f8cf3d4e3e9c27238e6311622b63c7f8edd01",
    "scripts/vidya/frames.py": "47e485d913271b72c9aaf1d9dfb526294ef0fd14",
    "scripts/vidya/canonical.py": "e7c93a39804c3e1cf8107f7801c8c32a23f0b45b",
}
SELECTED_NODES = tuple(['tests/unit/test_planner_evidence.py::test_candidate_blocks_include_question_diff_and_provenance', 'tests/unit/test_planner_evidence.py::test_corrupted_and_audit_only_rows_are_excluded', 'tests/unit/test_planner_evidence.py::test_dataclass_rows_are_normalized_at_boundary', 'tests/unit/test_planner_evidence.py::test_empty_evidence_section_is_stable', 'tests/unit/test_planner_evidence.py::test_missing_replay_e_values_remain_blocked_and_measured_zero_stays_below_floor', 'tests/unit/test_planner_evidence.py::test_provenance_distinguishes_missing_and_invalid_counters_from_measured_zero', 'tests/unit/test_planner_evidence.py::test_seq_rate_display_distinguishes_absent_invalid_zero_and_positive', 'tests/unit/test_planner_evidence.py::test_seq_rows_explain_seed_batch_is_not_w8_replayable', 'tests/unit/test_planner_evidence.py::test_seq_rows_fold_by_candidate_and_skip_malformed_z', 'tests/unit/test_planner_evidence.py::test_seq_rows_ignore_non_matching_core_ids', 'tests/unit/test_planner_evidence.py::test_seq_rows_mark_benign_excluded_accumulating_candidate_replayable', 'tests/unit/test_planner_evidence.py::test_seq_rows_mark_latest_reverted_candidate_not_replayable', 'tests/unit/test_planner_evidence.py::test_seq_rows_mark_terminal_excluded_candidate_not_replayable', 'tests/unit/test_planner_evidence.py::test_unavailable_task_rate_renders_na_and_keeps_valid_values', 'tests/unit/test_planner_evidence.py::test_vector_rows_collapse_by_behavioral_fingerprint', 'tests/unit/test_planner_evidence.py::test_w8_replay_pressure_blocks_vague_consult_gate_probe', 'tests/unit/test_planner_evidence.py::test_w8_replay_pressure_counts_concrete_consult_gate_probe_as_replayable', 'tests/unit/test_planner_evidence.py::test_w8_replay_pressure_counts_empty_numeric_params_as_blocked', 'tests/unit/test_planner_evidence.py::test_w8_replay_pressure_enforces_quality_floor', 'tests/unit/test_planner_evidence.py::test_w8_replay_pressure_names_structural_prune_as_unreplayable'])
ROOT_CARRIER_READS = tuple(CARRIER_BLOBS)
EXPECTED_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1",
    "PYTEST_ADDOPTS": "", "PYTEST_PLUGINS": "",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"{label} checkout is not clean: {status}")
    return git(repo, "rev-parse", "HEAD")


def tracked(repo: Path, relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if (not relative or "\\" in relative or parsed.is_absolute()
            or parsed.as_posix() != relative
            or any(part in {"", ".", ".."} for part in parsed.parts)):
        raise RuntimeError(f"declared source path is not normalized and relative: {relative}")
    path = repo
    for index, part in enumerate(parsed.parts):
        path = path / part
        try:
            info = path.lstat()
        except FileNotFoundError as exc:
            raise RuntimeError(f"declared source is missing: {relative}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"declared source traverses a symlink: {relative}")
        if index < len(parsed.parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"declared source parent is not a directory: {relative}")
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"declared source is missing or not regular: {relative}")
    entry = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(entry) < 3 or entry[0] not in {"100644", "100755"} or entry[1] != "blob":
        raise RuntimeError(f"declared input is not a tracked regular blob: {relative}")
    return path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"digest input is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                h.update(block)
    finally:
        os.close(fd)
    return h.hexdigest()


def read_text(path: Path) -> str:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"text input is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read().decode("utf-8")
    finally:
        os.close(fd)


def result_snapshot(root: Path) -> dict[str, dict[str, str]]:
    """Snapshot all files/directories under a fresh result, rejecting links/special files."""
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("result tree is not a regular directory")
    entries: dict[str, dict[str, str]] = {}

    def fail(error):
        raise error

    for current, directories, files in os.walk(root, topdown=True, followlinks=False,
                                                onerror=fail):
        base = Path(current)
        for name in sorted(directories):
            path = base / name
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise RuntimeError(f"result tree contains a link or non-directory: {path}")
            relative = path.relative_to(root).as_posix()
            if relative != "status.json":
                entries[relative] = {"kind": "directory"}
        for name in sorted(files):
            path = base / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise RuntimeError(f"result tree contains a link or non-regular member: {path}")
            relative = path.relative_to(root).as_posix()
            if relative != "status.json":
                entries[relative] = {"kind": "file", "sha256": digest(path)}
    return entries


def verify_blobs(repo: Path, expected_commit: str, blobs: dict[str, str], label: str) -> dict[str, dict[str, str]]:
    if git(repo, "rev-parse", "HEAD") != expected_commit:
        raise RuntimeError(f"{label} HEAD differs from frozen pin")
    rows = {}
    for relative, expected_blob in blobs.items():
        path = tracked(repo, relative)
        actual_blob = git(repo, "rev-parse", f"HEAD:{relative}")
        if actual_blob != expected_blob:
            raise RuntimeError(f"{label} Git blob differs: {relative}")
        rows[relative] = {"git_blob": actual_blob, "sha256": digest(path)}
    return rows


def verify_lock(app_lock: Path, requirements: Path) -> dict[str, str]:
    lock = tomllib.loads(read_text(app_lock))
    packages = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    req_text = read_text(requirements)
    declared: dict[str, dict[str, Any]] = {}
    current_name = None
    for line in req_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            if not stripped.endswith("\\"):
                raise RuntimeError("requirements package row is not a continuation")
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", stripped[:-1].rstrip())
            if not match:
                raise RuntimeError("requirements contain a non-exact package row")
            current_name = match.group(1).lower().replace("_", "-")
            if current_name in declared:
                raise RuntimeError(f"duplicate locked requirement: {current_name}")
            declared[current_name] = {"version": match.group(2), "hashes": set()}
        else:
            if current_name is None:
                raise RuntimeError("orphan continuation in requirements")
            hash_line = stripped.removesuffix("\\").rstrip()
            match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", hash_line)
            if not match:
                raise RuntimeError("requirements contain an invalid wheel hash")
            declared[current_name]["hashes"].add(match.group(1))
    if set(declared) != set(PACKAGES):
        raise RuntimeError("requirements package set differs from the reviewed six-package closure")
    versions = {}
    for name, version in PACKAGES.items():
        row = packages.get(name)
        if not row or row["version"] != version:
            raise RuntimeError(f"APP lock differs for {name}=={version}")
        compatible_wheels = {
            wheel["hash"].removeprefix("sha256:")
            for wheel in row.get("wheels", [])
            if (wheel["url"].lower().endswith("-py3-none-any.whl")
                or ("cp313-cp313-manylinux" in wheel["url"].lower()
                    and "x86_64" in wheel["url"].lower()))
        }
        if not compatible_wheels or declared[name]["hashes"] != compatible_wheels:
            raise RuntimeError(f"requirements wheel set differs from exact Ubuntu/Python wheel set for {name}")
        if declared[name]["version"] != version:
            raise RuntimeError(f"requirements pin differs for {name}=={version}")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed package differs: {name}=={version}")
        versions[name] = version
    return versions


def write_json(path: Path, value: Any) -> None:
    data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
    flags |= os.O_TRUNC if path.exists() else os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"JSON output is not a regular file: {path}")
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
    finally:
        os.close(fd)


def ast_node_ids(source_root: Path, relative: str, selected_names: set[str],
                 *, exact_module: bool = False) -> list[str]:
    """Expand only statically named test functions and literal pytest ids."""
    path = tracked(source_root, relative)
    tree = ast.parse(read_text(path), filename=str(path))
    found: dict[str, list[str]] = {}
    all_test_names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
            continue
        all_test_names.add(node.name)
        if node.name not in selected_names:
            continue
        parameter_ids: list[str] | None = None
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not (isinstance(func, ast.Attribute) and func.attr == "parametrize"):
                continue
            ids_node = next((item.value for item in decorator.keywords if item.arg == "ids"), None)
            values_node = decorator.args[1] if len(decorator.args) > 1 else None
            if ids_node is None or values_node is None:
                raise RuntimeError(f"selected parameterization lacks literal IDs: {relative}::{node.name}")
            ids_value = ast.literal_eval(ids_node)
            values_value = ast.literal_eval(values_node)
            if (not isinstance(ids_value, list) or not isinstance(values_value, list)
                    or len(ids_value) != len(values_value)
                    or any(not isinstance(value, str) for value in ids_value)):
                raise RuntimeError(f"parameter ids are not an exact literal list: {relative}::{node.name}")
            if parameter_ids is not None:
                raise RuntimeError(f"multiple parametrizations need manual case review: {relative}::{node.name}")
            parameter_ids = ids_value
        found[node.name] = parameter_ids or [""]
    if selected_names - all_test_names:
        raise RuntimeError(f"selected test function is absent from AST: {sorted(selected_names - all_test_names)}")
    if exact_module and all_test_names != selected_names:
        raise RuntimeError(f"test module has unbound test functions: {sorted(all_test_names - selected_names)}")
    nodes = []
    for name in sorted(selected_names):
        for case_id in found[name]:
            suffix = f"[{case_id}]" if case_id else ""
            nodes.append(f"{relative}::{name}{suffix}")
    return nodes


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, source, app_lock, root_context = (workspace / name for name in
                                                       ("recipe", "carrier", "source", "app-lock", "root-context"))
    result = runner_temp / "vb-rtg23w9" / "result"
    work = runner_temp / "vb-rtg23w9" / "work"
    result.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=False)
    status_path = result / "status.json"
    status: dict[str, Any] = {"state": "preparing", "job": "rtg23w9-native-conformance",
                              "exit_code": None}
    write_json(status_path, status)
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python differs from pin: {platform.python_version()}")
        for name, value in EXPECTED_ENV.items():
            if os.environ.get(name) != value:
                raise RuntimeError(f"{name} differs from reviewed recipe")
        if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
            raise RuntimeError("capture Python is not an isolated venv")

        pins = {
            "recipe": require_clean(recipe, "recipe"),
            "carrier": require_clean(carrier, "carrier"),
            "source": require_clean(source, "source"),
            "app_lock": require_clean(app_lock, "APP lock source"),
            "root_context": require_clean(root_context, "published ROOT context"),
        }
        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": ROOT_CARRIER_PIN,
                         "source": SOURCE_PIN, "app_lock": APP_LOCK_PIN,
                         "root_context": ROOT_CONTEXT_PIN}
        if pins != expected_pins:
            raise RuntimeError(f"repository identity differs from reviewed pins: {pins}")

        recipe_paths = [WORKFLOW_PATH, DRIVER_PATH, EXPECTED_CASES_PATH, REQUIREMENTS_PATH]
        recipe_inputs = {name: {"git_blob": git(recipe, "rev-parse", f"HEAD:{name}"),
                                "sha256": digest(tracked(recipe, name))}
                         for name in recipe_paths}
        root_context_inputs = verify_blobs(root_context, ROOT_CONTEXT_PIN, ROOT_CONTEXT_BLOBS,
                                           "published ROOT task/table context")
        for path, expected in ((TASK_PATH, TASK_SHA256), (TABLE_PATH, TABLE_SHA256),
                               (VB_PROGRAM_PATH, VB_PROGRAM_SHA256)):
            if digest(tracked(root_context, path)) != expected:
                raise RuntimeError(f"published ROOT task/table source changed: {path}")
        app_inputs = verify_blobs(source, SOURCE_PIN, APP_BLOBS, "APP source")
        lock_inputs = verify_blobs(app_lock, APP_LOCK_PIN, APP_LOCK_BLOBS, "APP lock")
        carrier_inputs = verify_blobs(carrier, ROOT_CARRIER_PIN, CARRIER_BLOBS, "ROOT carrier")

        cases_path = tracked(recipe, EXPECTED_CASES_PATH)
        manifest = json.loads(read_text(cases_path))
        provenance = manifest.get("provenance") or {}
        if (manifest.get("schema") != "epyc.vb_rtg23w9.native_selected_cases.v1"
                or manifest.get("source_commit") != SOURCE_PIN
                or manifest.get("count") != 20
                or provenance.get("identity_derivation") is None
                or provenance.get("test_modules_imported") is not False
                or provenance.get("module_level_code_executed") is not False
                or provenance.get("test_bodies_executed") is not False
                or set((provenance.get("source_paths_sha256") or {})) != set(APP_BLOBS)):
            raise RuntimeError("static selected-case manifest provenance is invalid")
        if [row.get("nodeid") for row in manifest.get("cases", [])] != list(SELECTED_NODES):
            raise RuntimeError("selected case node IDs differ from frozen recipe")
        expected_test_functions = {
            "tests/unit/test_planner_evidence.py": set(['test_candidate_blocks_include_question_diff_and_provenance', 'test_corrupted_and_audit_only_rows_are_excluded', 'test_dataclass_rows_are_normalized_at_boundary', 'test_empty_evidence_section_is_stable', 'test_missing_replay_e_values_remain_blocked_and_measured_zero_stays_below_floor', 'test_provenance_distinguishes_missing_and_invalid_counters_from_measured_zero', 'test_seq_rate_display_distinguishes_absent_invalid_zero_and_positive', 'test_seq_rows_explain_seed_batch_is_not_w8_replayable', 'test_seq_rows_fold_by_candidate_and_skip_malformed_z', 'test_seq_rows_ignore_non_matching_core_ids', 'test_seq_rows_mark_benign_excluded_accumulating_candidate_replayable', 'test_seq_rows_mark_latest_reverted_candidate_not_replayable', 'test_seq_rows_mark_terminal_excluded_candidate_not_replayable', 'test_unavailable_task_rate_renders_na_and_keeps_valid_values', 'test_vector_rows_collapse_by_behavioral_fingerprint', 'test_w8_replay_pressure_blocks_vague_consult_gate_probe', 'test_w8_replay_pressure_counts_concrete_consult_gate_probe_as_replayable', 'test_w8_replay_pressure_counts_empty_numeric_params_as_blocked', 'test_w8_replay_pressure_enforces_quality_floor', 'test_w8_replay_pressure_names_structural_prune_as_unreplayable']),
        }
        ast_nodes = []
        for relative, names in expected_test_functions.items():
            ast_nodes.extend(ast_node_ids(
                source, relative, names,
                exact_module=True,
            ))
        if Counter(ast_nodes) != Counter(SELECTED_NODES):
            raise RuntimeError("static AST-derived expanded case set differs from reviewed three cases")
        for case in manifest["cases"]:
            relative = case["nodeid"].split("::", 1)[0]
            expected_classname = "tests.unit." + Path(relative).stem
            if case["classname"] != expected_classname:
                raise RuntimeError("JUnit classname is not the source-root-relative package identity")
        source_hashes = provenance["source_paths_sha256"]
        for relative, expected in source_hashes.items():
            if digest(tracked(source, relative)) != expected:
                raise RuntimeError(f"selected APP test source SHA-256 differs: {relative}")

        requirements = tracked(recipe, REQUIREMENTS_PATH)
        app_lock_file = tracked(app_lock, APP_LOCK)
        dependency_versions = verify_lock(app_lock_file, requirements)
        pip_freeze = result / "pip-freeze.txt"
        install_log = result / "pip-install.log"
        if pip_freeze.is_symlink() or not pip_freeze.is_file():
            raise RuntimeError("workflow pip-freeze record is missing or not regular")
        if install_log.is_symlink() or not install_log.is_file():
            raise RuntimeError("workflow installer log is missing or not regular")
        pre_status = result / "pre-status.json"
        if (pre_status.is_symlink() or not pre_status.is_file()
                or json.loads(read_text(pre_status)) != {
                    "state": "setup_pending", "job": "rtg23w9-native-conformance", "exit_code": None
                }):
            raise RuntimeError("workflow pre-status artifact is missing or changed")
        initial_result = result_snapshot(result)
        if set(initial_result) != {"pre-status.json", "pip-install.log", "pip-freeze.txt"}:
            raise RuntimeError("result directory is not the expected fresh setup-only tree")
        environment = result / "environment.json"
        write_json(environment, {
            "schema": "epyc.vb_rtg23w9.native_environment.v1",
            "python": sys.version, "python_version": platform.python_version(),
            "platform": platform.platform(), "repositories": pins,
            "dependency_versions": dependency_versions,
            "app_uv_lock_sha256": digest(app_lock_file),
            "requirements_sha256": digest(requirements),
            "pip_freeze_sha256": digest(pip_freeze),
            "pip_install_log_sha256": digest(install_log),
            "environment_controls": {key: os.environ.get(key) for key in EXPECTED_ENV},
            "isolation_controls": {
                "venv_prefix": str(Path(sys.prefix).resolve()),
                "base_prefix": str(Path(sys.base_prefix).resolve()),
                "isolated_venv": Path(sys.prefix).resolve() != Path(sys.base_prefix).resolve(),
                "tmpdir": os.environ.get("TMPDIR"),
                "orchestrator_ignore_runtime_stack_facts": os.environ.get(
                    "ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS"),
                "orchestrator_mock_mode": os.environ.get("ORCHESTRATOR_MOCK_MODE"),
                "orchestrator_paths_llm_root": os.environ.get("ORCHESTRATOR_PATHS_LLM_ROOT"),
                "stack_numa_mode_absent": "ORCHESTRATOR_STACK_NUMA_MODE" not in os.environ,
            },
            "scope": "Synthetic session SQLite persistence/protocol and existing lease write-fencing controls only; no model or inference calls.",
        })
        source_manifest = result / "source-manifest.json"
        write_json(source_manifest, {
            "schema": "epyc.vb_rtg23w9.source_manifest.v1", "repositories": pins,
            "recipe_inputs": recipe_inputs, "app_source_blobs": app_inputs,
            "app_lock_blobs": lock_inputs, "carrier_blobs": carrier_inputs,
            "published_root_context_blobs": root_context_inputs,
        })
        os.environ["PYTHONPATH"] = str(source)
        test_argv = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--noconftest",
                     f"--rootdir={source}", "--import-mode=importlib", "-o", "addopts=",
                     "-p", "no:cacheprovider", "-q"]
        for node in SELECTED_NODES:
            relative, test_id = node.split("::", 1)
            test_argv.append(f"{source / relative}::{test_id}")
        junit = result / "original-junit.xml"
        native = result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("capture output paths are not fresh")
        test_argv.append(f"--junitxml={junit}")

        read_paths = [tracked(recipe, name) for name in recipe_paths]
        read_paths.extend(tracked(root_context, name) for name in ROOT_CONTEXT_BLOBS)
        read_paths.extend(tracked(source, name) for name in APP_BLOBS)
        read_paths.extend(tracked(app_lock, name) for name in APP_LOCK_BLOBS)
        read_paths.extend(tracked(carrier, name) for name in CARRIER_BLOBS)
        read_paths.extend((source_manifest, environment, pip_freeze, pre_status, install_log))
        source_readset_before = {str(path): digest(path)
                                 for path in dict.fromkeys(item for item in read_paths)}
        producer_argv = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(work), "--junit", str(junit), "--output", str(native),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
            "--repo", f"source={source}", "--repo", f"app_lock={app_lock}",
            "--repo", f"root_context={root_context}",
        ]
        for path in dict.fromkeys(item.resolve() for item in read_paths):
            producer_argv.extend(("--read-path", str(path)))
        for node in SELECTED_NODES:
            producer_argv.extend(("--select", node))
        status.update(state="running", repositories=pins, selections=list(SELECTED_NODES))
        write_json(status_path, status)
        command_exit = subprocess.call([*producer_argv, "--", *test_argv], cwd=work)

        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=command_exit or 1,
                          diagnostic="carrier did not produce a receipt")
            return command_exit or 1
        receipt = json.loads(read_text(receipt_path))
        expected_ids = [(row["classname"], row["name"]) for row in manifest["cases"]]
        cases = (receipt.get("summary") or {}).get("cases") or []
        actual_ids = [(row.get("classname"), row.get("name")) for row in cases]
        counts = (receipt.get("summary") or {}).get("counts") or {}
        expected_counts = {"passed": 20, "failure": 0, "error": 0,
                           "skipped": 0, "collected": 20, "executed": 20}
        identity_ok = (len(actual_ids) == 20 and len(set(actual_ids)) == 20
                       and Counter(actual_ids) == Counter(expected_ids))
        counts_ok = counts == expected_counts

        result_before = result_snapshot(result)
        before_membership = sorted(result_before)
        before = {name: row["sha256"] for name, row in result_before.items()
                  if row["kind"] == "file"}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        grade_error = None
        rows = ()
        grade_result = None
        try:
            from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
            from claim_tuple import grade
            rows = native_rows(receipt_path)
            if len(rows) == 1:
                projected = project_ci_conformance(rows[0])
                grade_result = grade(projected)
        except Exception as exc:
            grade_error = f"{type(exc).__name__}: {exc}"
        result_after = result_snapshot(result)
        after_membership = sorted(result_after)
        after = {name: row["sha256"] for name, row in result_after.items()
                 if row["kind"] == "file"}
        result_tree_unchanged = before == after
        membership_unchanged = before_membership == after_membership
        source_readset_after = {str(path): digest(path)
                                for path in dict.fromkeys(item for item in read_paths)}
        source_readset_unchanged = source_readset_before == source_readset_after
        expected_grade = ("Judged", "Located")
        actual_grade = grade_result[:2] if isinstance(grade_result, tuple) else None
        grade_ok = actual_grade == expected_grade
        analysis = {
            "schema": "epyc.vb_rtg23w9.native_analysis.v1", "scope": "the full 20-case planner-evidence unit module, including nullable display and fail-closed replay controls",
            "expected_identities": [list(item) for item in expected_ids],
            "observed_identities": [list(item) for item in actual_ids],
            "counts": counts, "identity_match": identity_ok,
            "fixture_execution_conformant": receipt.get("fixture_execution_conformant"),
            "command_exit_code": command_exit,
            "shared_grade": grade_result, "shared_grade_row_count": len(rows),
            "shared_grade_error": grade_error,
            "shared_grade_expected_qt": list(expected_grade),
            "shared_grade_matches_expected": grade_ok,
            "original_membership_before_grade": before_membership,
            "original_membership_after_grade": after_membership,
            "original_membership_unchanged": membership_unchanged,
            "original_sha256_before_grade": before,
            "original_sha256_after_grade": after,
            "result_tree_sha256_before_grade": before,
            "result_tree_sha256_after_grade": after,
            "result_tree_unchanged": result_tree_unchanged,
            "source_readset_sha256_before_grade": source_readset_before,
            "source_readset_sha256_after_grade": source_readset_after,
            "source_readset_unchanged": source_readset_unchanged,
            "status_file_excluded_from_snapshot": "status.json is finalized only after both snapshots.",
            "environment": json.loads(read_text(environment)),
        }
        write_json(result / "shared-grade-analysis.json", analysis)
        passed = (command_exit == 0 and receipt.get("fixture_execution_conformant") is True
                  and identity_ok and counts_ok and result_tree_unchanged and membership_unchanged
                  and source_readset_unchanged
                  and len(rows) == 1 and grade_ok and grade_error is None)
        status.update(state="passed" if passed else "failed", exit_code=command_exit,
                      fixture_execution_conformant=receipt.get("fixture_execution_conformant"),
                      exact_case_set=identity_ok and counts_ok,
                      result_tree_unchanged_after_grade=result_tree_unchanged,
                      source_readset_unchanged_after_grade=source_readset_unchanged,
                      original_membership_unchanged=membership_unchanged,
                      shared_grade={"Q": actual_grade[0], "T": actual_grade[1]} if actual_grade else None,
                      receipt_sha256=receipt.get("receipt_sha256"))
        return 0 if passed else 1
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        return 1
    finally:
        write_json(status_path, status)


if __name__ == "__main__":
    raise SystemExit(main())
