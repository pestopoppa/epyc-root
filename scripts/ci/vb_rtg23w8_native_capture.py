"""Capture RTG-23 W8 display and legacy-compatibility controls on GitHub Actions."""
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
import tomllib
import traceback
from typing import Any

SOURCE_PIN = "e94c2dc5f3129d150602bae1710cfa4c47f5e19b"
ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_LOCK_PIN = "94a6e8d41ec7d3f7a122f66bad53aa673d401d8a"
PYTHON_PIN = "3.13.15"
EXPECTED_CASES_PATH = "scripts/ci/vb_rtg23w8_native_cases.json"
REQUIREMENTS_PATH = "scripts/ci/vb_rtg23w8_native_requirements.txt"
WORKFLOW_PATH = ".github/workflows/vb-rtg23w8-native-conformance.yml"
DRIVER_PATH = "scripts/ci/vb_rtg23w8_native_capture.py"
TASK_PATH = "handoffs/active/objective-task-rate-goodput.md"
TABLE_PATH = "scripts/vidya/adapters/README.md"
TASK_SHA256 = "27deb9f4877ba8c9433c3035a5b3e92d9676055ebfde7b313ece1dfc653db4a4"
TABLE_SHA256 = "1ca5187bb0fabb729336c934e37bee3a3dc5e55abdb145238f365e2b044882f7"
APP_LOCK = "uv.lock"
APP_LOCK_BLOBS = {
    "pyproject.toml": "b4fe6ccada3a1aee3e08aa860045a78d8b85c7b1",
    "uv.lock": "ef2306018773ff9a1e80389970d92f66fcf8d5b7",
}
PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3", "pyyaml": "6.0.3",
}

APP_BLOBS = {
    'scripts/analysis/task_rate_goodput_replay.py': '5688fcab7766f12ac8ce9292fbcf852fc7d79cd0',
    'scripts/autopilot/journal_shards.py': '2430372f2d6f1cdba0503a82816a941f5e01e800',
    'scripts/autopilot/pareto_archive.py': '4ff3f53fb9b9bb744f4bcfdc5f926ac9a4dce228',
    'src/__init__.py': 'ff893046a8e7d2598657b950e9e41449f358d25f',
    'src/autopilot_core/__init__.py': '27c9fe394da9d9ea2f2f4b64d254bf99fa8aaa37',
    'src/autopilot_core/action_identity.py': 'de768dfce1199a1011a30d1db8db78ec5820e605',
    'src/autopilot_core/infra_fingerprint.py': '5673025fff54213490cc6eee12a91ab1645074e3',
    'src/autopilot_core/journal_reconstruction.py': '25e224dd700087aa4f8acc545c9505434df50bf7',
    'src/autopilot_core/learning_exclusions.py': '82adbc3dab68470570ec8fe0edf62d238ff8b093',
    'src/autopilot_core/measurement_guards.py': 'd01f62fdf7fe4ab31621ae3ff3483b68bf3ef1a6',
    'src/autopilot_core/multitier_decision.py': '5dce1594af423b7a91e7eec916741fb39de02854',
    'src/autopilot_core/pareto_math.py': '91f3e59e0918c93004ad4a4f61fe1d384eb48d78',
    'src/autopilot_core/planner_evidence.py': '40e5626e8fdeb4f236337b6ef46dc2fb42abb772',
    'src/autopilot_core/rlvr_tiers.py': '19d3813492f3b26807db22daad491fc1bf470e05',
    'src/autopilot_core/sequential_verdict.py': '5086b05f9e7517b1c8b7a9b3934f2b57da5f0356',
    'src/autopilot_core/tier_specs.py': 'ba47f3dd40b19521c4939a064493362c57ccc998',
    'src/bradley_terry.py': '80e0b5cd85fcca73e8cb27e0e8e3e98025539b9b',
    'src/registry/__init__.py': '287333a63889217a52c0082a7e316dc64670ee1f',
    'src/registry/kernel_paths.py': '6bb3dad23130a763dc4c456c7c432a9535536f30',
    'tests/__init__.py': 'd4839a6b14c11e64143d1d200c2d4733595ffc6c',
    'tests/unit/__init__.py': '4a5d26360bce3309c1d761d1529117cec7d42e40',
    'tests/unit/test_autopilot_core_contracts.py': '09603eb9ee5bf34305e79b429790fe9553f793ce',
    'tests/unit/test_planner_evidence.py': '48d4d9ee437ce0f4c052e4dc78a44bdbc71f757a',
    'tests/unit/test_task_rate_goodput_replay.py': '28b423aafb714c4b94baaeac991e42eb809b0106',
}
CARRIER_BLOBS = {
    "scripts/ci/native_conformance.py": "d2d7bd90f86cffa23c51db803288641c5c6fe461",
    "scripts/vidya/adapters/ci_conformance.py": "b5a521ef4debe7ad105830f5fa27bbf9c2168dcd",
    "scripts/vidya/claim_tuple.py": "309af769e45245fd1452482eb2e0592a86a4a79f",
    "scripts/vidya/lattice.py": "de0f8cf3d4e3e9c27238e6311622b63c7f8edd01",
    "scripts/vidya/frames.py": "47e485d913271b72c9aaf1d9dfb526294ef0fd14",
    "scripts/vidya/canonical.py": "e7c93a39804c3e1cf8107f7801c8c32a23f0b45b",
}
SELECTED_NODES = (
    "tests/unit/test_planner_evidence.py::test_unavailable_task_rate_renders_na_and_keeps_valid_values",
    "tests/unit/test_task_rate_goodput_replay.py::test_row_table_renders_unavailable_rate_as_na_and_preserves_measured_values",
    "tests/unit/test_autopilot_core_contracts.py::test_task_rate_shadow_objectives_from_journal_row",
)
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
    path = repo
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared source traverses a symlink: {relative}")
    if not path.is_file():
        raise RuntimeError(f"declared source is missing or not regular: {relative}")
    entry = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(entry) < 3 or entry[0] not in {"100644", "100755"} or entry[1] != "blob":
        raise RuntimeError(f"declared input is not a tracked regular blob: {relative}")
    return path.absolute()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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
    lock = tomllib.loads(app_lock.read_text(encoding="utf-8"))
    packages = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    req_text = requirements.read_text(encoding="utf-8")
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


def file_tree(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("native artifact directory is absent or not regular")
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("native artifact tree contains a symlink")
        if path.is_file():
            found.append(path)
        elif not path.is_dir():
            raise RuntimeError("native artifact tree contains a non-regular member")
    return found


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def ast_node_ids(source_root: Path, relative: str, selected_names: set[str],
                 *, exact_module: bool = False) -> list[str]:
    """Expand only statically named test functions and literal pytest ids."""
    path = source_root / relative
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
    recipe, carrier, source, app_lock = (workspace / name for name in
                                         ("recipe", "carrier", "source", "app-lock"))
    result = runner_temp / "vb-rtg23w8" / "result"
    work = runner_temp / "vb-rtg23w8" / "work"
    result.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=False)
    status_path = result / "status.json"
    status: dict[str, Any] = {"state": "preparing", "job": "rtg23w8-native-conformance",
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
        }
        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": ROOT_CARRIER_PIN,
                         "source": SOURCE_PIN, "app_lock": APP_LOCK_PIN}
        if pins != expected_pins:
            raise RuntimeError(f"repository identity differs from reviewed pins: {pins}")

        recipe_paths = [WORKFLOW_PATH, DRIVER_PATH, EXPECTED_CASES_PATH, REQUIREMENTS_PATH,
                        TASK_PATH, TABLE_PATH]
        recipe_inputs = {name: {"git_blob": git(recipe, "rev-parse", f"HEAD:{name}"),
                                "sha256": digest(tracked(recipe, name))}
                         for name in recipe_paths}
        for path, expected in ((TASK_PATH, TASK_SHA256), (TABLE_PATH, TABLE_SHA256)):
            if digest(tracked(recipe, path)) != expected:
                raise RuntimeError(f"ROOT810 task/table source changed: {path}")
        app_inputs = verify_blobs(source, SOURCE_PIN, APP_BLOBS, "APP source")
        lock_inputs = verify_blobs(app_lock, APP_LOCK_PIN, APP_LOCK_BLOBS, "APP lock")
        carrier_inputs = verify_blobs(carrier, ROOT_CARRIER_PIN, CARRIER_BLOBS, "ROOT carrier")

        cases_path = tracked(recipe, EXPECTED_CASES_PATH)
        manifest = json.loads(cases_path.read_text(encoding="utf-8"))
        provenance = manifest.get("provenance") or {}
        if (manifest.get("schema") != "epyc.vb_rtg23w8.native_selected_cases.v1"
                or manifest.get("source_commit") != SOURCE_PIN
                or manifest.get("count") != 3
                or provenance.get("identity_derivation") is None
                or provenance.get("test_modules_imported") is not False
                or provenance.get("module_level_code_executed") is not False
                or provenance.get("test_bodies_executed") is not False
                or set((provenance.get("source_paths_sha256") or {})) != set(APP_BLOBS)):
            raise RuntimeError("static selected-case manifest provenance is invalid")
        if [row.get("nodeid") for row in manifest.get("cases", [])] != list(SELECTED_NODES):
            raise RuntimeError("selected case node IDs differ from frozen recipe")
        expected_test_functions = {
            "tests/unit/test_planner_evidence.py": {
                "test_unavailable_task_rate_renders_na_and_keeps_valid_values",
            },
            "tests/unit/test_task_rate_goodput_replay.py": {
                "test_row_table_renders_unavailable_rate_as_na_and_preserves_measured_values",
            },
            "tests/unit/test_autopilot_core_contracts.py": {
                "test_task_rate_shadow_objectives_from_journal_row",
            },
        }
        ast_nodes = []
        for relative, names in expected_test_functions.items():
            ast_nodes.extend(ast_node_ids(
                source, relative, names,
                exact_module=False,
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
        pip_freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        source_manifest = result / "source-manifest.json"
        write_json(source_manifest, {
            "schema": "epyc.vb_rtg23w8.source_manifest.v1", "repositories": pins,
            "recipe_inputs": recipe_inputs, "app_source_blobs": app_inputs,
            "app_lock_blobs": lock_inputs, "carrier_blobs": carrier_inputs,
        })
        environment = result / "environment.json"
        write_json(environment, {
            "schema": "epyc.vb_rtg23w8.native_environment.v1", "python": sys.version,
            "python_version": platform.python_version(), "platform": platform.platform(),
            "repositories": pins, "selections": list(SELECTED_NODES),
            "expected_cases": manifest["cases"], "dependency_versions": dependency_versions,
            "dependency_basis": "The requirements package set and exact Ubuntu 24.04 / Python 3.13.15 compatible wheel hashes must equal the six-package subset derived from the pinned APP uv.lock; installed with --only-binary=:all: --no-deps --require-hashes in an isolated venv, with full installer output retained.",
            "settings": EXPECTED_ENV,
            "isolation": "Three deterministic journal-display and compatibility tests only; no live journal, model, inference, benchmark, or host-state read.",
            "limits": ["no objective, grading, or score change", "no live frontier or rate-improvement claim"],
        })

        dtap = source
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
        read_paths.extend(tracked(source, name) for name in APP_BLOBS)
        read_paths.extend(tracked(app_lock, name) for name in APP_LOCK_BLOBS)
        read_paths.extend(tracked(carrier, name) for name in CARRIER_BLOBS)
        pre_status = result / "pre-status.json"
        if not pre_status.is_file() or json.loads(pre_status.read_text(encoding="utf-8")) != {
                "state": "setup_pending", "job": "rtg23w8-native-conformance", "exit_code": None}:
            raise RuntimeError("workflow pre-status artifact is missing or changed")
        install_log = result / "pip-install.log"
        if not install_log.is_file():
            raise RuntimeError("pinned dependency installer log is missing")
        read_paths.extend((source_manifest, environment, pip_freeze, pre_status, install_log))
        producer_argv = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(work), "--junit", str(junit), "--output", str(native),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
            "--repo", f"source={source}", "--repo", f"app_lock={app_lock}",
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
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        expected_ids = [(row["classname"], row["name"]) for row in manifest["cases"]]
        cases = (receipt.get("summary") or {}).get("cases") or []
        actual_ids = [(row.get("classname"), row.get("name")) for row in cases]
        counts = (receipt.get("summary") or {}).get("counts") or {}
        expected_counts = {"passed": 3, "failure": 0, "error": 0,
                           "skipped": 0, "collected": 3, "executed": 3}
        identity_ok = (len(actual_ids) == 3 and len(set(actual_ids)) == 3
                       and Counter(actual_ids) == Counter(expected_ids))
        counts_ok = counts == expected_counts

        originals = [*file_tree(native), junit, source_manifest, environment, pip_freeze,
                     install_log,
                     result / "pre-status.json"]
        before_membership = sorted(str(path.relative_to(result)) for path in originals)
        before = {str(path.relative_to(result)): digest(path) for path in originals}
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
        after_originals = [*file_tree(native), junit, source_manifest, environment, pip_freeze,
                           install_log, result / "pre-status.json"]
        after_membership = sorted(str(path.relative_to(result)) for path in after_originals)
        after = {str(path.relative_to(result)): digest(path) for path in after_originals}
        originals_unchanged = before == after
        membership_unchanged = before_membership == after_membership
        expected_grade = ("Judged", "Located")
        actual_grade = grade_result[:2] if isinstance(grade_result, tuple) else None
        grade_ok = actual_grade == expected_grade
        analysis = {
            "schema": "epyc.vb_rtg23w8.native_analysis.v1", "scope": "three selected deterministic journal-display and compatibility controls",
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
            "originals_unchanged": originals_unchanged,
            "limits": environment.read_text(encoding="utf-8"),
        }
        write_json(result / "shared-grade-analysis.json", analysis)
        passed = (command_exit == 0 and receipt.get("fixture_execution_conformant") is True
                  and identity_ok and counts_ok and originals_unchanged and membership_unchanged
                  and len(rows) == 1 and grade_ok and grade_error is None)
        status.update(state="passed" if passed else "failed", exit_code=command_exit,
                      fixture_execution_conformant=receipt.get("fixture_execution_conformant"),
                      exact_case_set=identity_ok and counts_ok,
                      originals_unchanged_after_grade=originals_unchanged,
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
