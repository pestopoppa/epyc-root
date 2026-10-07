"""Capture two F-08 command-gate controls and a bounded AST mutation witness."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from typing import Any

BASE_PIN = "51d2ad01e5dafc6a47b28902e0600730844eff06"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_LOCK_PIN = "94a6e8d41ec7d3f7a122f66bad53aa673d401d8a"
PYTHON_PIN = "3.13.15"
WORKFLOW = ".github/workflows/rtg48-aud11-f08-native.yml"
DRIVER = "scripts/ci/rtg48_aud11_f08_capture.py"
CASES = "scripts/ci/rtg48_aud11_f08_cases.json"
REQUIREMENTS = "scripts/ci/vb_thesis2_native_requirements.txt"
TASK = "handoffs/active/coordinator-role-failure-modes-and-refactor.md"
TEST_MODULE = "tests/coordination/test_mech_column_audit.py"
TEST_NAMES = (
    "test_f08_cmd_nudge_refuses_recent_own_nudge_at_production_gate",
    "test_f08_cmd_nudge_dry_run_allows_elapsed_interval_positive_control",
)
SELECTIONS = tuple(f"{TEST_MODULE}::{name}" for name in TEST_NAMES)
PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3", "pyyaml": "6.0.3",
}
EXPECTED_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1",
    "PYTEST_ADDOPTS": "", "PYTEST_PLUGINS": "",
}
SOURCE_BLOBS = {
    TASK: "e1da85c26e28709c33bfa1d61347e4335ae0ede7",
    "tests/__init__.py": "d9dba47dc8443eb0ba816114a1bd64d5a5db2078",
    TEST_MODULE: "f61ff268d898482b7cbbecd388c65d4ee468a8dd",
    "scripts/coordination/backlog_row_check.py": "d6de35bb46c0b8effa1cd79790eba49593be8d17",
    "scripts/handoffs/index_state.py": "14a1a98daa988ab10d65ef07731daaade2664959",
    "scripts/coordination/tmux_adapter.py": "4ba92286cec07442e12092a44b509efa97e294de",
    "scripts/coordination/session_bus.py": "60502a803c424c2fa3e833a8afba76360743ff86",
    REQUIREMENTS: "66b049f0d7c2b207b35f22ab383a8d91da25f4c0",
}
APP_LOCK_BLOBS = {
    "pyproject.toml": "b4fe6ccada3a1aee3e08aa860045a78d8b85c7b1",
    "uv.lock": "ef2306018773ff9a1e80389970d92f66fcf8d5b7",
}
CARRIER_BLOBS = {
    "scripts/ci/native_conformance.py": "d2d7bd90f86cffa23c51db803288641c5c6fe461",
    "scripts/vidya/adapters/ci_conformance.py": "b5a521ef4debe7ad105830f5fa27bbf9c2168dcd",
    "scripts/vidya/claim_tuple.py": "309af769e45245fd1452482eb2e0592a86a4a79f",
    "scripts/vidya/lattice.py": "de0f8cf3d4e3e9c27238e6311622b63c7f8edd01",
    "scripts/vidya/frames.py": "47e485d913271b72c9aaf1d9dfb526294ef0fd14",
    "scripts/vidya/canonical.py": "e7c93a39804c3e1cf8107f7801c8c32a23f0b45b",
}
MUTANT_COPY_PATHS = tuple(SOURCE_BLOBS) + (
    "scripts/ci/rtg48_aud11_f08_cases.json",
    "scripts/ci/rtg48_aud11_f08_capture.py",
    WORKFLOW,
)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, expected: str, label: str) -> None:
    actual = git(repo, "rev-parse", "HEAD")
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if actual != expected or status:
        raise RuntimeError(f"{label} identity/cleanliness mismatch: {actual} {status!r}")


def tracked(repo: Path, relative: str) -> Path:
    path = repo / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"declared read is not a regular file: {relative}")
    fields = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(fields) < 3 or fields[0] not in {"100644", "100755"} or fields[1] != "blob":
        raise RuntimeError(f"declared read is not a tracked file: {relative}")
    return path.resolve()


def verify_blobs(repo: Path, expected: dict[str, str], label: str) -> dict[str, dict[str, str]]:
    result = {}
    for relative, blob in expected.items():
        path = tracked(repo, relative)
        actual = git(repo, "rev-parse", f"HEAD:{relative}")
        if actual != blob:
            raise RuntimeError(f"{label} blob changed: {relative}")
        result[relative] = {"git_blob": actual, "sha256": digest(path)}
    return result


def verify_lock(app: Path, requirements: Path, python: Path) -> dict[str, str]:
    lock = tomllib.loads(tracked(app, "uv.lock").read_text(encoding="utf-8"))
    packages = {item["name"].lower().replace("_", "-"): item for item in lock["package"]}
    text = requirements.read_text(encoding="utf-8")
    declared: dict[str, dict[str, Any]] = {}
    current = None
    import re
    for line in text.splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if not line[:1].isspace():
            if not value.endswith("\\"):
                raise RuntimeError("dependency row is not exact and continued")
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", value[:-1].rstrip())
            if not match:
                raise RuntimeError("dependency row is not an exact version pin")
            current = match.group(1).lower().replace("_", "-")
            if current in declared:
                raise RuntimeError(f"duplicate dependency: {current}")
            declared[current] = {"version": match.group(2), "hashes": set()}
        else:
            if current is None:
                raise RuntimeError("orphan dependency hash")
            match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", value.removesuffix("\\").rstrip())
            if not match:
                raise RuntimeError("dependency has a malformed hash")
            if match.group(1) in declared[current]["hashes"]:
                raise RuntimeError(f"duplicate dependency hash: {current}")
            declared[current]["hashes"].add(match.group(1))
    if set(declared) != set(PACKAGES):
        raise RuntimeError("requirements package set differs from the six-package closure")
    installed = json.loads(subprocess.check_output([
        str(python), "-c",
        "import importlib.metadata,json;print(json.dumps({n:importlib.metadata.version(n) "
        "for n in ('iniconfig','packaging','pluggy','pygments','pytest','pyyaml')}))",
    ], text=True))
    versions = {}
    for name, version in PACKAGES.items():
        row = packages.get(name)
        if row is None or row["version"] != version or declared[name]["version"] != version:
            raise RuntimeError(f"APP lock and requirements differ for {name}=={version}")
        wheels = {
            wheel["hash"].removeprefix("sha256:")
            for wheel in row.get("wheels", [])
            if (wheel["url"].lower().endswith("-py3-none-any.whl")
                or ("cp313-cp313-manylinux" in wheel["url"].lower()
                    and "x86_64" in wheel["url"].lower()))
        }
        if not wheels or declared[name]["hashes"] != wheels:
            raise RuntimeError(f"wheel hashes are not the exact Ubuntu/Python set for {name}")
        if installed.get(name) != version:
            raise RuntimeError(f"installed dependency differs: {name}=={version}")
        versions[name] = version
    return versions


def selected_case_ids(source: Path) -> list[str]:
    path = tracked(source, TEST_MODULE)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=TEST_MODULE)
    found = {node.name for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name in TEST_NAMES}
    if found != set(TEST_NAMES):
        raise RuntimeError("one or more selected test functions is absent from the pinned AST")
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in found:
            if any(isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                   and dec.func.attr == "parametrize" for dec in node.decorator_list):
                raise RuntimeError("selected function has an unbound parametrization")
    return list(SELECTIONS)


def artifact_files(root: Path) -> list[Path]:
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("native artifact directory is missing or unsafe")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("native artifact contains a symlink")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise RuntimeError("native artifact contains a non-file member")
    return files


def snapshot_paths(paths: list[Path]) -> dict[str, dict[str, Any]]:
    snapshot = {}
    for path in dict.fromkeys(paths):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"declared input is not a stable regular file: {path}")
        resolved = path.resolve(strict=True)
        data = resolved.read_bytes()
        snapshot[str(resolved)] = {"sha256": digest_bytes(data), "bytes": len(data)}
    return snapshot


def snapshot_tree(root: Path) -> dict[str, Any]:
    files = artifact_files(root)
    directories = sorted(str(path.relative_to(root)) for path in root.rglob("*")
                         if path.is_dir())
    return {
        "directories": directories,
        "files": {str(path.relative_to(root)): {
            "sha256": digest(path), "bytes": path.stat().st_size} for path in files},
    }


def junit_rows(path: Path) -> list[dict[str, str]]:
    root = ET.parse(path).getroot()
    rows = []
    for node in root.iter("testcase"):
        status = next((tag for tag in ("failure", "error", "skipped")
                       if node.find(tag) is not None), "passed")
        rows.append({"classname": node.get("classname", ""),
                     "name": node.get("name", ""), "status": status})
    return rows


def expected_rows(manifest: dict) -> list[dict[str, str]]:
    return [{"classname": row["classname"], "name": row["name"], "status": "passed"}
            for row in manifest["cases"]]


def mutate_exact_gate(source_bytes: bytes) -> tuple[bytes, dict[str, Any]]:
    text = source_bytes.decode("utf-8")
    tree = ast.parse(text, filename="scripts/coordination/tmux_adapter.py")
    expected = ast.parse(
        'p["seconds_since_last_nudge"] is not None and '
        'p["seconds_since_last_nudge"] < args.min_interval_s', mode="eval").body
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "cmd_nudge"]
    if len(functions) != 1:
        raise RuntimeError("production cmd_nudge AST identity is ambiguous")
    matches = [node for node in ast.walk(functions[0])
               if isinstance(node, ast.If) and ast.dump(node.test) == ast.dump(expected)]
    if len(matches) != 1:
        raise RuntimeError("expected interval predicate is absent or ambiguous")
    node = matches[0]
    if node.test.lineno != node.test.end_lineno:
        raise RuntimeError("interval predicate unexpectedly spans source lines")
    lines = source_bytes.splitlines(keepends=True)
    start = sum(len(line) for line in lines[:node.test.lineno - 1]) + node.test.col_offset
    end = sum(len(line) for line in lines[:node.test.end_lineno - 1]) + node.test.end_col_offset
    before = source_bytes[start:end]
    if ast.dump(ast.parse(before.decode("utf-8"), mode="eval").body) != ast.dump(expected):
        raise RuntimeError("AST byte span does not encode the exact guarded predicate")
    mutated = source_bytes[:start] + b"False" + source_bytes[end:]
    after_tree = ast.parse(mutated.decode("utf-8"), filename="mutated tmux_adapter.py")
    after_function = next(node for node in after_tree.body
                          if isinstance(node, ast.FunctionDef) and node.name == "cmd_nudge")
    if any(isinstance(node, ast.If) and ast.dump(node.test) == ast.dump(expected)
           for node in ast.walk(after_function)):
        raise RuntimeError("mutated AST still contains the nudge interval predicate")
    return mutated, {"function": "cmd_nudge", "line": node.lineno,
                     "predicate_ast_sha256": digest_bytes(ast.dump(expected).encode()),
                     "original_expression_sha256": digest_bytes(before),
                     "replacement": "False", "source_offset_bytes": start}


def run_mutation_control(source: Path, result: Path, python: Path,
                         manifest: dict, root_inputs: dict[str, dict[str, str]]) -> dict[str, Any]:
    evidence = result / "mutation-evidence"
    if evidence.exists():
        raise RuntimeError("mutation evidence path already exists")
    evidence.mkdir()
    mutant_root = evidence / "mutant-source"
    if mutant_root.exists():
        raise RuntimeError("mutation source path already exists")
    mutant_root.mkdir(parents=True)
    copied_inputs = []
    for relative in MUTANT_COPY_PATHS:
        original = tracked(source, relative)
        target = mutant_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        copied_inputs.append({
            "path": relative,
            "source_git_blob": git(source, "rev-parse", f"HEAD:{relative}"),
            "sha256": digest(target),
            "bytes": target.stat().st_size,
        })
    write_json(evidence / "copied-inputs.json", {
        "schema": "epyc.rtg48_aud11_f08.mutation_inputs.v1",
        "source_commit": git(source, "rev-parse", "HEAD"), "files": copied_inputs,
    })
    adapter_relative = "scripts/coordination/tmux_adapter.py"
    adapter_path = mutant_root / adapter_relative
    original_adapter = adapter_path.read_bytes()
    mutated, mutation = mutate_exact_gate(original_adapter)
    adapter_path.write_bytes(mutated)
    (evidence / "original-tmux_adapter.py").write_bytes(original_adapter)
    (evidence / "mutated-tmux_adapter.py").write_bytes(mutated)
    if digest_bytes(original_adapter) != root_inputs[adapter_relative]["sha256"]:
        raise RuntimeError("mutant input differs from pinned source readset")
    env = dict(os.environ)
    env.update(EXPECTED_ENV)
    env["PYTHONPATH"] = str(mutant_root)
    env["EPYC_BUS_ROOT"] = str(Path(os.environ["RUNNER_TEMP"]) / "rtg48-aud11" / "empty-bus")
    for case in manifest["cases"]:
        if case["expected"] != "passed":
            raise RuntimeError("baseline manifest contains a nonpassing selected case")
    junit = result / "mutation-junit.xml"
    log = result / "mutation-command.log"
    if junit.exists() or log.exists():
        raise RuntimeError("mutation outputs are not fresh")
    argv = [str(python), "-m", "pytest", "-c", "/dev/null", "--noconftest",
            f"--rootdir={mutant_root}", "--import-mode=importlib", "-o", "addopts=",
            "-p", "no:cacheprovider", "-q"]
    argv.extend(f"{mutant_root / TEST_MODULE}::{name}" for name in TEST_NAMES)
    argv.append(f"--junitxml={junit}")
    completed = subprocess.run(argv, cwd=mutant_root, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.write_bytes(completed.stdout)
    rows = junit_rows(junit)
    observed = {(row["name"], row["status"]) for row in rows}
    expected = {
        (TEST_NAMES[0], "failure"),
        (TEST_NAMES[1], "passed"),
    }
    passed = completed.returncode == 1 and len(rows) == 2 and observed == expected
    report = {
        "schema": "epyc.rtg48_aud11_f08.mutation_control.v1",
        "purpose": "off-host synthetic control that disabling the exact production interval predicate is detected",
        "production_source_pin": git(source, "rev-parse", "HEAD"),
        "original_adapter_sha256": digest_bytes(original_adapter),
        "mutated_adapter_sha256": digest_bytes(mutated),
        "mutation": mutation,
        "evidence": {
            "original_adapter_bytes": str((evidence / "original-tmux_adapter.py").relative_to(result)),
            "mutated_adapter_bytes": str((evidence / "mutated-tmux_adapter.py").relative_to(result)),
            "mutant_source_adapter": str(adapter_path.relative_to(result)),
            "copied_input_manifest": {
                "path": str((evidence / "copied-inputs.json").relative_to(result)),
                "sha256": digest(evidence / "copied-inputs.json"),
            },
            "junit": {"path": str(junit.relative_to(result)), "sha256": digest(junit)},
            "log": {"path": str(log.relative_to(result)), "sha256": digest(log)},
        },
        "argv": argv,
        "exit_code": completed.returncode,
        "expected_junit": sorted([list(item) for item in expected]),
        "observed_junit": sorted([row["name"], row["status"]] for row in rows),
        "control_passed": passed,
        "limits": ["temporary copied fixture tree only", "no real tmux", "no bus reads or writes",
                   "no host process inspection or signaling", "dry-run command path only"],
    }
    write_json(result / "mutation-control.json", report)
    if not passed:
        raise RuntimeError("AST predicate-disable control did not fail only the recent-nudge refusal test")
    return report


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    source, carrier, app_lock = (workspace / name for name in ("source", "carrier", "app-lock"))
    result = Path(os.environ["RUNNER_TEMP"]).resolve() / "rtg48-aud11" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status: dict[str, Any] = {"state": "preparing", "job": "rtg48-aud11-f08-native",
                              "exit_code": None}
    write_json(status_path, status)
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError("runner Python differs from reviewed 3.13.15 pin")
        for name, expected in EXPECTED_ENV.items():
            if os.environ.get(name) != expected:
                raise RuntimeError(f"workflow environment differs: {name}")
        root_pin = os.environ.get("GITHUB_SHA", "")
        if not root_pin or git(source, "rev-parse", "HEAD") != root_pin:
            raise RuntimeError("source/recipe checkout does not equal the triggering GitHub commit")
        if git(source, "merge-base", BASE_PIN, "HEAD") != BASE_PIN:
            raise RuntimeError("source/recipe commit does not descend from the reviewed ROOT pin")
        history = git(source, "rev-list", "--parents", f"{BASE_PIN}..HEAD").splitlines()
        if len(history) != 2 or any(len(row.split()) != 2 for row in history):
            raise RuntimeError("recipe must be exactly two normal commits beyond the reviewed ROOT pin")
        changed = set(git(source, "diff", "--name-only", f"{BASE_PIN}..HEAD").splitlines())
        expected_changed = {WORKFLOW, DRIVER, CASES, TEST_MODULE}
        if changed != expected_changed:
            raise RuntimeError(f"recipe branch has unexpected source changes: {sorted(changed)}")
        require_clean(source, root_pin, "ROOT source/recipe")
        require_clean(carrier, CARRIER_PIN, "native carrier")
        require_clean(app_lock, APP_LOCK_PIN, "APP lock")
        pins = {"source": root_pin, "recipe": root_pin, "carrier": CARRIER_PIN,
                "app_lock": APP_LOCK_PIN}
        root_inputs = verify_blobs(source, SOURCE_BLOBS, "ROOT source")
        recipe_inputs = {}
        for relative in (WORKFLOW, DRIVER, CASES):
            path = tracked(source, relative)
            recipe_inputs[relative] = {
                "git_blob": git(source, "rev-parse", f"HEAD:{relative}"),
                "sha256": digest(path),
            }
        app_inputs = verify_blobs(app_lock, APP_LOCK_BLOBS, "APP lock")
        carrier_inputs = verify_blobs(carrier, CARRIER_BLOBS, "native carrier")
        case_path = tracked(source, CASES)
        manifest = json.loads(case_path.read_text(encoding="utf-8"))
        if (manifest.get("schema") != "epyc.rtg48_aud11_f08.selected_cases.v1"
                or manifest.get("source_base_commit") != BASE_PIN
                or manifest.get("static_derivation") != {
                    "module_level_code_executed": False,
                    "test_bodies_executed": False,
                    "test_module_imported": False}
                or [row.get("nodeid") for row in manifest.get("cases", [])] != list(SELECTIONS)):
            raise RuntimeError("static case manifest does not equal the reviewed source identity")
        if selected_case_ids(source) != list(SELECTIONS):
            raise RuntimeError("selected node IDs differ from exact AST identities")
        for row in manifest["cases"]:
            if row.get("classname") != "tests.coordination.test_mech_column_audit":
                raise RuntimeError("JUnit class identity differs from frozen source-root path")

        requirement_path = tracked(source, REQUIREMENTS)
        lock = tracked(app_lock, "uv.lock")
        venv = Path(os.environ["RUNNER_TEMP"]).resolve() / "rtg48-aud11" / "venv"
        if venv.exists():
            raise RuntimeError("isolated venv path already exists")
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        python = venv / "bin" / "python"
        install_log = result / "pip-install.log"
        install = subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check",
             "--only-binary=:all:", "--no-deps", "--require-hashes", "-r", str(requirement_path)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        install_log.write_bytes(install.stdout)
        if install.returncode != 0:
            status.update(state="dependency_install_failed", exit_code=install.returncode)
            return install.returncode
        dependency_versions = verify_lock(app_lock, requirement_path, python)
        freeze_path = result / "pip-freeze.txt"
        freeze_path.write_bytes(subprocess.check_output([str(python), "-m", "pip", "freeze", "--all"]))
        workflow = tracked(source, WORKFLOW)
        driver = tracked(source, DRIVER)
        source_manifest = result / "source-manifest.json"
        input_groups = {"source": root_inputs, "app_lock": app_inputs,
                        "carrier": carrier_inputs}
        write_json(source_manifest, {
            "schema": "epyc.rtg48_aud11_f08.source_manifest.v1",
            "repositories": pins, "inputs": input_groups,
            "recipe_files": recipe_inputs,
        })
        environment = result / "environment.json"
        write_json(environment, {
            "schema": "epyc.rtg48_aud11_f08.environment.v1",
            "python": sys.version, "python_version": platform.python_version(),
            "platform": platform.platform(), "repositories": pins,
            "requirements_sha256": digest(requirement_path),
            "app_uv_lock_sha256": digest(lock), "dependency_versions": dependency_versions,
            "selected_nodes": list(SELECTIONS), "case_manifest_sha256": digest(case_path),
            "workflow_sha256": digest(workflow), "capture_driver_sha256": digest(driver),
            "environment": {key: os.environ.get(key) for key in EXPECTED_ENV},
            "EPYC_BUS_ROOT": os.environ.get("EPYC_BUS_ROOT"),
            "isolation": ["two explicitly selected synthetic command controls",
                          "config and probe are injected", "dry-run positive path",
                          "no real tmux, bus access, process probe, or send-key"],
        })
        pre_status = result / "pre-status.json"
        if not pre_status.is_file() or json.loads(pre_status.read_text(encoding="utf-8")) != {
                "state": "setup_pending", "job": "rtg48-aud11-f08-native", "exit_code": None}:
            raise RuntimeError("workflow pre-status is missing or modified")
        os.environ["PYTHONPATH"] = str(source)
        os.environ["EPYC_BUS_ROOT"] = str(Path(os.environ["RUNNER_TEMP"]) / "rtg48-aud11" / "empty-bus")
        argv = [str(python), "-m", "pytest", "-c", "/dev/null", "--noconftest",
                f"--rootdir={source}", "--import-mode=importlib", "-o", "addopts=",
                "-p", "no:cacheprovider", "-q"]
        argv.extend(f"{source / TEST_MODULE}::{name}" for name in TEST_NAMES)
        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("native capture output path is not fresh")
        argv.append(f"--junitxml={junit}")
        read_paths = [tracked(source, name) for name in (
            WORKFLOW, DRIVER, CASES, TASK, TEST_MODULE, "tests/__init__.py",
            "scripts/coordination/backlog_row_check.py", "scripts/handoffs/index_state.py",
            "scripts/coordination/tmux_adapter.py", "scripts/coordination/session_bus.py",
            REQUIREMENTS)]
        read_paths.extend(tracked(app_lock, name) for name in APP_LOCK_BLOBS)
        read_paths.extend(tracked(carrier, name) for name in CARRIER_BLOBS)
        read_paths.extend((case_path, requirement_path, lock, source_manifest, environment,
                           freeze_path, install_log, pre_status))
        producer = [str(python), str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(source), "--junit", str(junit), "--output", str(native),
                    "--repo", f"source={source}", "--repo", f"recipe={source}",
                    "--repo", f"carrier={carrier}", "--repo", f"app_lock={app_lock}"]
        for path in dict.fromkeys(item.resolve() for item in read_paths):
            producer.extend(("--read-path", str(path)))
        for selection in SELECTIONS:
            producer.extend(("--select", selection))
        status.update(state="running", repositories=pins, selected_cases=list(SELECTIONS))
        write_json(status_path, status)
        native_result = subprocess.run([*producer, "--", *argv], cwd=source,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not (native / "receipt.json").is_file() or not junit.is_file():
            raise RuntimeError("native carrier did not preserve its receipt and JUnit")
        receipt_path = native / "receipt.json"
        receipt_before = receipt_path.read_bytes()
        receipt = json.loads(receipt_before)
        expected = expected_rows(manifest)
        summary = receipt.get("summary") or {}
        actual = summary.get("cases") or []
        counts = summary.get("counts") or {}
        identity_ok = Counter((row.get("classname"), row.get("name"), row.get("status"))
                              for row in actual) == Counter((row["classname"], row["name"], row["status"])
                                                            for row in expected)
        count_ok = counts == {"passed": 2, "failure": 0, "error": 0,
                              "skipped": 0, "collected": 2, "executed": 2}
        junit_ok = junit_rows(junit) == expected
        native_files_before = artifact_files(native)
        generated_before = snapshot_tree(result)
        readset_before = snapshot_paths(read_paths)
        originals_before = [*native_files_before, junit, source_manifest, environment, freeze_path,
                            install_log, pre_status]
        membership_before = sorted(str(p.relative_to(result)) for p in originals_before)
        hashes_before = {str(p.relative_to(result)): digest(p) for p in originals_before}
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
                grade_result = grade(project_ci_conformance(rows[0]))
        except Exception as exc:
            grade_error = f"{type(exc).__name__}: {exc}"
        native_files_after = artifact_files(native)
        generated_after = snapshot_tree(result)
        readset_after = snapshot_paths(read_paths)
        originals_after = [*native_files_after, junit, source_manifest, environment, freeze_path,
                           install_log, pre_status]
        membership_after = sorted(str(p.relative_to(result)) for p in originals_after)
        hashes_after = {str(p.relative_to(result)): digest(p) for p in originals_after}
        receipt_after = receipt_path.read_bytes()
        membership_unchanged = membership_before == membership_after
        bytes_unchanged = hashes_before == hashes_after
        receipt_unchanged = receipt_before == receipt_after
        generated_unchanged = generated_before == generated_after
        readset_unchanged = readset_before == readset_after
        grade_tuple = grade_result[:2] if isinstance(grade_result, tuple) else None
        grade_ok = grade_tuple == ("Judged", "Located")
        analysis = {
            "schema": "epyc.rtg48_aud11_f08.native_analysis.v1",
            "scope": "two selected synthetic cmd_nudge controls only",
            "carrier_exit_code": native_result.returncode, "native_receipt": receipt,
            "expected_cases": expected, "observed_cases": actual,
            "junit_identities_and_statuses_match": junit_ok,
            "native_identity_match": identity_ok, "native_counts_match": count_ok,
            "shared_grade_actual_qt": list(grade_tuple) if grade_tuple else None,
            "shared_grade_expected_qt": ["Judged", "Located"], "shared_grade_matches": grade_ok,
            "shared_grade_row_count": len(rows), "shared_grade_error": grade_error,
            "original_membership_before_grade": membership_before,
            "original_membership_after_grade": membership_after,
            "original_membership_unchanged": membership_unchanged,
            "original_sha256_before_grade": hashes_before,
            "original_sha256_after_grade": hashes_after,
            "original_bytes_unchanged": bytes_unchanged,
            "original_receipt_bytes_unchanged": receipt_unchanged,
            "generated_tree_before_grade": generated_before,
            "generated_tree_after_grade": generated_after,
            "generated_tree_unchanged": generated_unchanged,
            "actual_read_paths_before_grade": readset_before,
            "actual_read_paths_after_grade": readset_after,
            "actual_read_paths_unchanged": readset_unchanged,
        }
        write_json(result / "shared-grade-analysis.json", analysis)
        if not (native_result.returncode == 0
                and receipt.get("fixture_execution_conformant") is True
                and identity_ok and count_ok and junit_ok and len(rows) == 1 and grade_ok
                and grade_error is None and membership_unchanged and bytes_unchanged
                and receipt_unchanged and generated_unchanged and readset_unchanged):
            status.update(state="native_or_grade_failed", exit_code=native_result.returncode,
                          shared_grade_qt=list(grade_tuple) if grade_tuple else None)
            return 1

        mutation = run_mutation_control(source, result, python, manifest, root_inputs)
        status.update(state="passed", exit_code=0, native_receipt="native/receipt.json",
                      receipt_sha256=digest(receipt_path), exact_case_set=True,
                      shared_grade_qt=list(grade_tuple), mutation_control=mutation["control_passed"])
        return 0
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        write_json(status_path, status)


if __name__ == "__main__":
    raise SystemExit(main())
