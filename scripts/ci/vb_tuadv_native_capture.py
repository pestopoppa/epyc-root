"""Capture the six approved TU-ADV-1 synthetic DTAP controls on GitHub Actions."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
import traceback
from typing import Any

SOURCE_PIN = "30a8665bcb69e7679173f026dc2dcf9549a6c7ca"
ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_LOCK_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
PYTHON_PIN = "3.13.15"
EXPECTED_CASES_PATH = "scripts/ci/vb_tuadv_native_cases.json"
REQUIREMENTS_PATH = "scripts/ci/vb_tuadv_native_requirements.txt"
WORKFLOW_PATH = ".github/workflows/vb-tuadv-native-conformance.yml"
DRIVER_PATH = "scripts/ci/vb_tuadv_native_capture.py"
TASK_PATH = "handoffs/active/vidya-belief-substrate-program.md"
TABLE_PATH = "scripts/vidya/adapters/README.md"
TASK_SHA256 = "ef6ee21caf36cb31f11638bd85d02ef8e9473877601424fcedc94fc0393a55ba"
TABLE_SHA256 = "b2ca24a53690daeda3b24732842517cd43c4e6b316f41ae745164a6751421ba6"
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
    "scripts/autopilot/evals/dtap/tests/test_adversarial_contract_fixtures.py": "792715678992a24c7b61787dc27d7cf934d5271b",
    "scripts/autopilot/evals/dtap/tests/test_tool_contract.py": "71b3dd2b5be07dd45b915bc8bece3522c3420999",
    "scripts/autopilot/evals/dtap/harness/__init__.py": "a1294e4f0af6e21b86c5d0bee46710b1dbf75b81",
    "scripts/autopilot/evals/dtap/harness/runner.py": "186f75e1206954af90e83df6a71f49dc2dcfa735",
    "scripts/autopilot/evals/dtap/harness/tool_contract.py": "65a2e5f4b90b6393f1d0c519123b9782febccfe5",
    "scripts/autopilot/evals/dtap/harness/endpoint.py": "9fa2adad3036bc90e3806d6a26177e899351460a",
    "scripts/autopilot/evals/dtap/harness/env_state.py": "9220c4969fd72e1b1bb29b13a5c58a245f4e0d94",
    "scripts/autopilot/evals/dtap/harness/failure_ledger.py": "aa5edb6fbd016069b3533869cec4d86a5e6e0a50",
    "scripts/autopilot/evals/dtap/harness/judge_guard.py": "3c1591ae7ea494b1da39fe40764ae647210b1fd2",
    "scripts/autopilot/evals/dtap/harness/outcomes.py": "ebda452563b29f046ba2f03639fc87f5521f493a",
    "scripts/autopilot/evals/dtap/harness/trace.py": "a1223e5aec960a8aed8321e3235c3e70cd1aed64",
    "scripts/autopilot/evals/dtap/harness/base_judge.py": "a4b2e7504faec13be1e8523d545a42e61237e07b",
    "scripts/autopilot/evals/dtap/harness/shims/__init__.py": "d05e12aaebd44a2fb042ecc96015e3dfade23b04",
    "scripts/autopilot/evals/dtap/harness/shims/finance.py": "5548c939dba4440eaf5b9d782a06e28454261d35",
    "scripts/autopilot/evals/dtap/harness/shims/gmail.py": "fceb529f286d4c1a5b3c1075193b2d8371ff6ca6",
    "scripts/autopilot/evals/dtap/harness/shims/paypal.py": "eb538ccfea12de50ba8e210d049f858f602a61df",
    "scripts/autopilot/evals/dtap/harness/shims/salesforce.py": "ba341ae79daf3188714f46dc362de92967c9b650",
    "scripts/autopilot/evals/dtap/harness/shims/slack.py": "c4e74ed319037607d1ccb09c2fe65c6a9c7b3e69",
    "scripts/autopilot/evals/dtap/harness/utils.py": "b90e059b0c70f5e50b1fc323657df854a39b2e17",
    "scripts/autopilot/evals/dtap/cases.json": "e95b9f13aca14cbc5e18c869f172e927ba3acfa4",
    "scripts/autopilot/evals/dtap/harness/tool_schemas.json": "db5946efd2c1bffbbc1a23ff2f085baf1b39c505",
    "scripts/autopilot/evals/dtap/fixtures/finance-benign-trade-execution-001.done.json": "08bd2ea80823d5381cbadf8e11f33b497e43b3fc",
    "scripts/autopilot/evals/dtap/judges/finance-benign-trade-execution-001/judge.py": "7106f7ce92b39987a08c57355322017100160253",
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
    "tests/test_adversarial_contract_fixtures.py::test_repeated_invalid_payload_is_typed_terminal_before_842_attempts",
    "tests/test_adversarial_contract_fixtures.py::test_privileged_oracle_and_skill_calls_are_independently_rejected[privileged-environment-read]",
    "tests/test_adversarial_contract_fixtures.py::test_privileged_oracle_and_skill_calls_are_independently_rejected[skill-reuse-write]",
    "tests/test_adversarial_contract_fixtures.py::test_privileged_and_skill_calls_are_rejected_atomically_as_one_response",
    "tests/test_adversarial_contract_fixtures.py::test_authorized_benign_tool_fixture_still_reaches_unchanged_judge",
    "tests/test_tool_contract.py::test_unknown_function_is_rejected_before_runner_records_accepted_call",
)
ROOT_CARRIER_READS = tuple(CARRIER_BLOBS)
EXPECTED_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1",
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
    versions = {}
    for name, version in PACKAGES.items():
        row = packages.get(name)
        if not row or row["version"] != version:
            raise RuntimeError(f"APP lock differs for {name}=={version}")
        listed = [item["hash"].removeprefix("sha256:") for item in row.get("wheels", [])]
        if not listed or not any(value in req_text for value in listed):
            raise RuntimeError(f"requirements omit every APP-locked wheel for {name}")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed package differs: {name}=={version}")
        req_name = {"pygments": "Pygments", "pyyaml": "PyYAML"}.get(name, name)
        if f"{req_name}=={version}" not in req_text and f"{name}=={version}" not in req_text:
            raise RuntimeError(f"requirements omit exact version {name}=={version}")
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
    path = source_root / "scripts/autopilot/evals/dtap" / relative
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
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
    if selected_names - set(found):
        raise RuntimeError(f"selected test function is absent from AST: {sorted(selected_names - set(found))}")
    if exact_module and set(found) != selected_names:
        raise RuntimeError(f"test module has unbound test functions: {sorted(set(found) - selected_names)}")
    nodes = []
    for name in sorted(found):
        for case_id in found[name]:
            suffix = f"[{case_id}]" if case_id else ""
            nodes.append(f"{relative}::{name}{suffix}")
    return nodes


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, source, app_lock = (workspace / name for name in
                                         ("recipe", "carrier", "source", "app-lock"))
    result = runner_temp / "vb-tuadv" / "result"
    work = runner_temp / "vb-tuadv" / "work"
    result.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=False)
    status_path = result / "status.json"
    status: dict[str, Any] = {"state": "preparing", "job": "tuadv-native-conformance",
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
        if (manifest.get("schema") != "epyc.vb_tuadv.native_selected_cases.v1"
                or manifest.get("source_commit") != SOURCE_PIN
                or manifest.get("count") != 6
                or provenance.get("identity_derivation") is None
                or provenance.get("test_modules_imported") is not False
                or provenance.get("module_level_code_executed") is not False
                or provenance.get("test_bodies_executed") is not False
                or set((provenance.get("source_paths_sha256") or {})) != set(APP_BLOBS) & {
                    "scripts/autopilot/evals/dtap/tests/test_adversarial_contract_fixtures.py",
                    "scripts/autopilot/evals/dtap/tests/test_tool_contract.py"}):
            raise RuntimeError("static selected-case manifest provenance is invalid")
        if [row.get("nodeid") for row in manifest.get("cases", [])] != list(SELECTED_NODES):
            raise RuntimeError("selected case node IDs differ from frozen recipe")
        expected_test_functions = {
            "tests/test_adversarial_contract_fixtures.py": {
                "test_repeated_invalid_payload_is_typed_terminal_before_842_attempts",
                "test_privileged_oracle_and_skill_calls_are_independently_rejected",
                "test_privileged_and_skill_calls_are_rejected_atomically_as_one_response",
                "test_authorized_benign_tool_fixture_still_reaches_unchanged_judge",
            },
            "tests/test_tool_contract.py": {
                "test_unknown_function_is_rejected_before_runner_records_accepted_call",
            },
        }
        ast_nodes = []
        for relative, names in expected_test_functions.items():
            ast_nodes.extend(ast_node_ids(
                source, relative, names,
                exact_module=relative == "tests/test_adversarial_contract_fixtures.py",
            ))
        if Counter(ast_nodes) != Counter(SELECTED_NODES):
            raise RuntimeError("static AST-derived expanded case set differs from reviewed six cases")
        for case in manifest["cases"]:
            relative = case["nodeid"].split("::", 1)[0]
            if case["classname"] != Path(relative).stem:
                raise RuntimeError("JUnit classname is not the DTAP-root-relative import identity")
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
            "schema": "epyc.vb_tuadv.source_manifest.v1", "repositories": pins,
            "recipe_inputs": recipe_inputs, "app_source_blobs": app_inputs,
            "app_lock_blobs": lock_inputs, "carrier_blobs": carrier_inputs,
        })
        environment = result / "environment.json"
        write_json(environment, {
            "schema": "epyc.vb_tuadv.native_environment.v1", "python": sys.version,
            "python_version": platform.python_version(), "platform": platform.platform(),
            "repositories": pins, "selections": list(SELECTED_NODES),
            "expected_cases": manifest["cases"], "dependency_versions": dependency_versions,
            "dependency_basis": "Exact six-package APP uv.lock closure; installed with pip --no-deps --require-hashes in isolated venv.",
            "settings": EXPECTED_ENV,
            "isolation": "Six synthetic/offline DTAP test cases only; no model, endpoint, network corpus, inference, benchmark, or live-host process/lock/proc observation.",
            "limits": ["no parent/global skill-store claim", "no grading ladder or scoring change",
                       "no attack rate or external 842-attempt trace reconstruction"],
        })

        dtap = source / "scripts/autopilot/evals/dtap"
        os.environ["PYTHONPATH"] = str(dtap)
        test_argv = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--noconftest",
                     f"--rootdir={dtap}", "--import-mode=importlib", "-o", "addopts=",
                     "-p", "no:cacheprovider", "-q"]
        for node in SELECTED_NODES:
            relative, test_id = node.split("::", 1)
            test_argv.append(f"{dtap / relative}::{test_id}")
        junit = result / "original-junit.xml"
        native = result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("capture output paths are not fresh")
        test_argv.append(f"--junitxml={junit}")

        read_paths = [tracked(recipe, name) for name in recipe_paths]
        read_paths.extend(tracked(source, name) for name in APP_BLOBS)
        read_paths.extend(tracked(app_lock, name) for name in APP_LOCK_BLOBS)
        read_paths.extend(tracked(carrier, name) for name in CARRIER_BLOBS)
        read_paths.extend((source_manifest, environment, pip_freeze))
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
        expected_counts = {"passed": 6, "failure": 0, "error": 0,
                           "skipped": 0, "collected": 6, "executed": 6}
        identity_ok = (len(actual_ids) == 6 and len(set(actual_ids)) == 6
                       and Counter(actual_ids) == Counter(expected_ids))
        counts_ok = counts == expected_counts

        originals = [*file_tree(native), junit, source_manifest, environment, pip_freeze,
                     result / "pre-status.json"]
        before = {str(path.relative_to(result)): digest(path) for path in originals}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        grade_result = None
        if len(rows) == 1:
            projected = project_ci_conformance(rows[0])
            grade_result = grade(projected)
        after = {str(path.relative_to(result)): digest(path) for path in originals}
        originals_unchanged = before == after
        analysis = {
            "schema": "epyc.vb_tuadv.native_analysis.v1", "scope": "six selected synthetic DTAP contract controls",
            "expected_identities": [list(item) for item in expected_ids],
            "observed_identities": [list(item) for item in actual_ids],
            "counts": counts, "identity_match": identity_ok,
            "fixture_execution_conformant": receipt.get("fixture_execution_conformant"),
            "command_exit_code": command_exit,
            "shared_grade": grade_result, "shared_grade_row_count": len(rows),
            "original_sha256_before_grade": before,
            "original_sha256_after_grade": after,
            "originals_unchanged": originals_unchanged,
            "limits": environment.read_text(encoding="utf-8"),
        }
        write_json(result / "shared-grade-analysis.json", analysis)
        passed = (command_exit == 0 and receipt.get("fixture_execution_conformant") is True
                  and identity_ok and counts_ok and originals_unchanged
                  and len(rows) == 1 and grade_result is not None)
        status.update(state="passed" if passed else "failed", exit_code=command_exit,
                      fixture_execution_conformant=receipt.get("fixture_execution_conformant"),
                      exact_case_set=identity_ok and counts_ok,
                      originals_unchanged_after_grade=originals_unchanged,
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
