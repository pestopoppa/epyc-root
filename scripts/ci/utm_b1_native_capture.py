"""Capture the selected UTM-B1 registrar/navigation controls with the shared carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import stat
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
ROOT_CONTEXT_PIN = "f018782258f65118019a555f6832125f25646f11"
SOURCE_PIN = "286bf88520728bdd54d9dc21d527b7436a51533f"
APP_PIN = "94a6e8d41ec7d3f7a122f66bad53aa673d401d8a"
PYTHON_PIN = "3.13.15"
WORKFLOW = ".github/workflows/vb-utm-b1-native.yml"
DRIVER = "scripts/ci/utm_b1_native_capture.py"
REQUIREMENTS = "scripts/ci/utm_b1_native_requirements.txt"
CASES = "scripts/ci/utm_b1_native_cases.json"
TASK = "handoffs/active/unified-trace-memory-service.md"
SOURCE_TABLE = "scripts/vidya/adapters/README.md"
VB_PROGRAM = "handoffs/active/vidya-belief-substrate-program.md"
ENROLLED_CONTEXT = {
    TASK: (
        "**UTM-B1-SOURCE — prepare the existing read-only trace navigation registrar and synthetic MCP/SQLite controls.**",
        "Actual off-host FastMCP schema/defaults and synthetic SQLite navigation controls through VB-UTM-B1-CONFORMANCE.",
    ),
    SOURCE_TABLE: (
        "| Read-only trace MCP registration source controls | existing native CI verifier |",
        "VB-UTM-B1-CONFORMANCE; source proposal pending MAIN binding",
    ),
    VB_PROGRAM: (
        "**VB-UTM-B1-CONFORMANCE — bind read-only trace MCP registrar source controls prospectively.**",
        "Actual off-host FastMCP dotted-name/schema/defaults and synthetic SQLite navigation",
    ),
}
SELECTIONS = (
    "tests/unit/test_trace_mcp_tools.py::test_default_orchestrator_catalog_does_not_activate_candidate_tools",
    "tests/unit/test_trace_mcp_tools.py::test_opt_in_registration_exposes_dotted_names_and_exact_optional_schemas",
    "tests/unit/test_trace_mcp_tools.py::test_fastmcp_calls_reach_existing_navigation_against_synthetic_sqlite",
    "tests/unit/test_trace_navigation.py::test_search_records_uses_existing_fts_store",
    "tests/unit/test_trace_navigation.py::test_get_records_preserves_requested_order_and_dedups",
)
LOCKED = {
    'aiofile': '3.11.1', 'annotated-types': '0.7.0', 'anyio': '4.13.0',
    'attrs': '26.1.0', 'authlib': '1.7.2', 'beartype': '0.22.9',
    'cachetools': '7.0.5', 'caio': '0.9.25', 'certifi': '2026.2.25',
    'cffi': '2.0.0', 'click': '8.3.2', 'cryptography': '46.0.7',
    'cyclopts': '4.16.1', 'dnspython': '2.8.0', 'docstring-parser': '0.18.0',
    'email-validator': '2.3.0', 'exceptiongroup': '1.3.1', 'fastmcp': '3.3.1',
    'fastmcp-slim': '3.3.1', 'griffelib': '2.0.2', 'h11': '0.16.0',
    'httpcore': '1.0.9', 'httpx': '0.28.1', 'httpx-sse': '0.4.3',
    'idna': '3.11', 'iniconfig': '2.3.0', 'jaraco-classes': '3.4.0',
    'jaraco-context': '6.1.2', 'jaraco-functools': '4.5.0', 'jeepney': '0.9.0',
    'joserfc': '1.6.8', 'jsonref': '1.1.0', 'jsonschema': '4.26.0',
    'jsonschema-path': '0.5.0', 'jsonschema-specifications': '2025.9.1', 'keyring': '25.7.0',
    'markdown-it-py': '4.0.0', 'mcp': '1.27.0', 'mdurl': '0.1.2',
    'more-itertools': '11.1.0', 'openapi-pydantic': '0.5.1', 'opentelemetry-api': '1.42.1',
    'packaging': '26.0', 'pathable': '0.6.0', 'platformdirs': '4.10.0',
    'pluggy': '1.6.0', 'py-key-value-aio': '0.4.5', 'pycparser': '3.0',
    'pydantic': '2.13.0', 'pydantic-core': '2.46.0', 'pydantic-settings': '2.13.1',
    'pygments': '2.20.0', 'pyjwt': '2.12.1', 'pyperclip': '1.11.0',
    'pytest': '9.0.3', 'python-dotenv': '1.2.2', 'python-multipart': '0.0.26',
    'pyyaml': '6.0.3', 'referencing': '0.37.0', 'rich': '15.0.0',
    'rich-rst': '2.0.1', 'rpds-py': '0.30.0', 'secretstorage': '3.5.0',
    'sse-starlette': '3.3.4', 'starlette': '1.0.0', 'typing-extensions': '4.15.0',
    'typing-inspection': '0.4.2', 'uncalled-for': '0.3.2', 'uvicorn': '0.44.0',
    'watchfiles': '1.2.0', 'websockets': '16.0',
}
EXPECTED_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1", "PYTEST_ADDOPTS": "",
    "PYTEST_PLUGINS": "", "ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS": "1",
    "ORCHESTRATOR_MOCK_MODE": "1",
}


def expected_isolated_path_env(runner_temp: str) -> dict[str, str]:
    root = Path(runner_temp) / "vb-utm-b1" / "absent"
    return {
        "ORCHESTRATOR_PATHS_LLM_ROOT": str(Path(runner_temp) / "isolated-llm"),
        "TMPDIR": str(Path(runner_temp) / "isolated-tmp"),
        "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": str(root / "cpu"),
        "ORCHESTRATOR_PATHS_LLAMA_MTMD": str(root / "llama-mtmd-cli"),
        "ORCHESTRATOR_PATHS_LLAMA_SERVER": str(root / "llama-server"),
    }


def digest(path: Path) -> str:
    h = hashlib.sha256()
    flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
             | getattr(os, "O_NONBLOCK", 0))
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"custody input is not a single-link regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                h.update(block)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise RuntimeError(f"custody input changed while reading: {path}")
    finally:
        os.close(fd)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def identity(repo: Path, expected: str, label: str) -> None:
    if git(repo, "rev-parse", "HEAD") != expected:
        raise RuntimeError(f"{label} revision mismatch")
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"{label} has tracked modifications")


def tracked(repo: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts):
        raise RuntimeError(f"declared input path is not normalized: {relative}")
    path = repo
    for index, part in enumerate(rel.parts):
        path = path / part
        try:
            info = path.lstat()
        except OSError as exc:
            raise RuntimeError(f"declared input is missing: {relative}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"declared input traverses a symlink: {relative}")
        if index < len(rel.parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"declared input parent is not a directory: {relative}")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RuntimeError(f"declared input is not a single-link regular file: {relative}")
    entry = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(entry) < 3 or entry[1] != "blob" or entry[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a tracked regular blob: {relative}")
    return path


def read_text(path: Path) -> str:
    flags = (os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
             | getattr(os, "O_NONBLOCK", 0))
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"input is not a single-link regular file: {path}")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            content = stream.read()
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise RuntimeError(f"input changed while reading: {path}")
        return content
    finally:
        os.close(fd)


def snapshot_tree(root: Path, *, omit: set[str] = frozenset()) -> dict[str, str]:
    info = root.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"result tree root is not a real directory: {root}")
    found: dict[str, str] = {}
    stack = [(root, "")]
    while stack:
        directory, prefix = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                rel = f"{prefix}/{entry.name}" if prefix else entry.name
                if rel in omit:
                    continue
                entry_path = directory / entry.name
                item = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(item.st_mode):
                    raise RuntimeError(f"result tree contains a symlink: {rel}")
                if stat.S_ISDIR(item.st_mode):
                    found[f"{rel}/"] = "directory"
                    stack.append((entry_path, rel))
                elif stat.S_ISREG(item.st_mode) and item.st_nlink == 1:
                    found[rel] = digest(entry_path)
                else:
                    raise RuntimeError(f"result tree contains a non-regular entry: {rel}")
    return found


def blob(repo: Path, relative: str) -> str:
    fields = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(fields) < 3 or fields[1] != "blob":
        raise RuntimeError(f"missing source blob: {relative}")
    return fields[2]


def verify_lock(lock_path: Path, requirements: Path, dependency_packages: dict) -> dict[str, str]:
    lock = tomllib.loads(read_text(lock_path))
    lock_packages = {item["name"].lower().replace("_", "-"): item for item in lock["package"]}
    lines = read_text(requirements).splitlines()
    required: dict[str, tuple[str, set[str]]] = {}
    name = version = None
    hashes: set[str] = set()
    def save() -> None:
        if name is not None:
            if name in required:
                raise RuntimeError(f"duplicate requirement: {name}")
            required[name] = (version or "", set(hashes))
    import re
    for line in lines:
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^ \\\n]+)", line)
        if match:
            save()
            name = match.group(1).lower().replace("_", "-")
            version = match.group(2)
            hashes = set()
        hashes.update(re.findall(r"--hash=sha256:([0-9a-f]{64})", line))
    save()
    expected_names = {key.lower().replace("_", "-") for key in dependency_packages}
    if set(required) != expected_names or expected_names != set(LOCKED):
        raise RuntimeError("requirements package set differs from reviewed dependency closure")
    installed = {}
    for name, metadata in dependency_packages.items():
        normalized = name.lower().replace("_", "-")
        version = metadata.get("version")
        expected_wheels = set(metadata.get("wheel_hashes", []))
        lock_item = lock_packages.get(normalized)
        if not lock_item or lock_item.get("version") != version or LOCKED.get(normalized) != version:
            raise RuntimeError(f"APP uv.lock differs for {name}=={version}")
        lock_wheels = {wheel.get("hash", "").removeprefix("sha256:")
                       for wheel in lock_item.get("wheels", [])}
        if not expected_wheels or expected_wheels != lock_wheels:
            raise RuntimeError(f"full wheel hash set differs from APP lock: {name}")
        declared_version, declared_hashes = required[normalized]
        if declared_version != version or declared_hashes != expected_wheels:
            raise RuntimeError(f"requirements differ from manifest wheel closure: {name}")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from APP lock")
        installed[name] = version
    return installed


def expected_cases(path: Path) -> tuple[dict, set[tuple[str, str]]]:
    data = json.loads(read_text(path))
    if (data.get("schema") != "epyc.utm_b1.native_selected_cases.v1"
            or data.get("source_commit") != SOURCE_PIN or data.get("count") != 5):
        raise RuntimeError("UTM-B1 selected-case manifest schema/source/count differs")
    provenance = data.get("provenance") or {}
    if any(provenance.get(key) is not False for key in
           ("test_bodies_executed", "test_modules_imported", "module_level_code_executed")):
        raise RuntimeError("case manifest does not attest static-only identity extraction")
    rows = data.get("cases")
    if not isinstance(rows, list) or len(rows) != 5:
        raise RuntimeError("selected case list is incomplete")
    pairs = {(row.get("classname"), row.get("name")) for row in rows
             if isinstance(row, dict) and isinstance(row.get("nodeid"), str)}
    if len(pairs) != 5 or tuple(row["nodeid"] for row in rows) != SELECTIONS:
        raise RuntimeError("selected case identities differ from frozen driver constants")
    return data, pairs


def verify_junit(path: Path, native: dict, expected: set[tuple[str, str]]) -> dict:
    root = ET.fromstring(read_text(path))
    cases = [(item.attrib.get("classname", ""), item.attrib.get("name", ""))
             for item in root.iter("testcase")]
    summary = native.get("summary")
    if not isinstance(summary, dict) or not isinstance(summary.get("counts"), dict):
        raise RuntimeError("native receipt has no case summary; result remains ungraded")
    counts = summary["counts"]
    if (set(cases) != expected or len(cases) != 5 or len(set(cases)) != 5
            or counts.get("collected") != 5 or counts.get("executed") != 5
            or counts.get("skipped") != 0 or counts.get("failure") != 0
            or counts.get("error") != 0 or native.get("fixture_execution_conformant") is not True):
        raise RuntimeError("original JUnit/native summary differs from exact reviewed cases")
    return {"count": len(cases), "identities": [list(case) for case in cases], "counts": counts}


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    result = Path(os.environ["RUNNER_TEMP"]).resolve() / "vb-utm-b1" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "utm-b1-native-conformance", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError("Python version differs from reviewed recipe")
        for key, value in EXPECTED_ENV.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from reviewed recipe")
        isolated = expected_isolated_path_env(os.environ["RUNNER_TEMP"])
        for key, value in isolated.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from isolated runner bootstrap")
        for key in ("ORCHESTRATOR_PATHS_LLAMA_CPP_BIN", "ORCHESTRATOR_PATHS_LLAMA_MTMD",
                    "ORCHESTRATOR_PATHS_LLAMA_SERVER"):
            if os.path.lexists(os.environ[key]):
                raise RuntimeError(f"isolated binary override unexpectedly exists: {key}")
        if "ORCHESTRATOR_STACK_NUMA_MODE" in os.environ:
            raise RuntimeError("runner supplied an unreviewed stack NUMA mode")
        recipe, source, carrier, app, context = (workspace / name for name in
                                                 ("recipe", "source", "carrier", "app", "context"))
        recipe_pin = os.environ.get("RECIPE_PIN", "")
        if not recipe_pin:
            raise RuntimeError("workflow did not bind exact recipe revision")
        identity(recipe, recipe_pin, "recipe")
        identity(source, SOURCE_PIN, "APP source")
        identity(carrier, ROOT_PIN, "native carrier")
        identity(app, APP_PIN, "APP lock source")
        identity(context, ROOT_CONTEXT_PIN, "published task and source-table context")
        pins = {"recipe": recipe_pin, "source": SOURCE_PIN, "carrier": ROOT_PIN,
                "app_lock": APP_PIN, "context": ROOT_CONTEXT_PIN}
        workflow = tracked(recipe, WORKFLOW)
        driver = tracked(recipe, DRIVER)
        cases_path = tracked(recipe, CASES)
        requirements = tracked(recipe, REQUIREMENTS)
        lock = tracked(app, "uv.lock")
        data, selected = expected_cases(cases_path)
        installed = verify_lock(lock, requirements, data["provenance"]["dependency_packages"])
        source_map = data.get("source_files") or {}
        if len(source_map) != 12:
            raise RuntimeError("source closure must bind the twelve reviewed APP files")
        source_paths, input_rows = [], []
        for relative, expected in sorted(source_map.items()):
            path = tracked(source, relative)
            if blob(source, relative) != expected["git_blob"] or digest(path) != expected["sha256"]:
                raise RuntimeError(f"frozen APP source blob/hash mismatch: {relative}")
            source_paths.append(path)
            input_rows.append({"repository": "source", "pin": SOURCE_PIN, "path": relative,
                               "git_blob": expected["git_blob"], "sha256": expected["sha256"]})
        context_specs = ((TASK, "task"), (SOURCE_TABLE, "source_table"), (VB_PROGRAM, "VB task"))
        context_paths = []
        for relative, label in context_specs:
            path = tracked(context, relative)
            content = read_text(path)
            missing_contract = [snippet for snippet in ENROLLED_CONTEXT[relative]
                                if snippet not in content]
            if missing_contract:
                raise RuntimeError(f"published {label} enrollment contract is absent")
            context_paths.append(path)
            input_rows.append({"repository": "context", "pin": ROOT_CONTEXT_PIN, "path": relative,
                               "git_blob": blob(context, relative), "sha256": digest(path),
                               "label": label})
        carrier_names = (
            "scripts/ci/native_conformance.py", "scripts/vidya/adapters/ci_conformance.py",
            "scripts/vidya/claim_tuple.py", "scripts/vidya/lattice.py",
            "scripts/vidya/frames.py", "scripts/vidya/canonical.py",
        )
        carrier_paths = [tracked(carrier, name) for name in carrier_names]
        for path in carrier_paths:
            relative = path.relative_to(carrier).as_posix()
            input_rows.append({"repository": "carrier", "pin": ROOT_PIN, "path": relative,
                               "git_blob": blob(carrier, relative), "sha256": digest(path)})
        input_rows.append({"repository": "app_lock", "pin": APP_PIN, "path": "uv.lock",
                           "git_blob": blob(app, "uv.lock"), "sha256": digest(lock)})
        source_manifest = result / "source-manifest.json"
        source_manifest.write_text(json.dumps({"schema": "epyc.vb.utm_b1.source_manifest.v1",
                                              "repositories": pins, "inputs": input_rows},
                                             sort_keys=True, indent=2) + "\n", encoding="utf-8")
        pre_status = result / "pre-status.json"
        if not pre_status.exists():
            raise RuntimeError("immutable setup pre-status is missing")
        pip_install, pip_freeze = result / "pip-install.log", result / "pip-freeze.txt"
        environment = result / "environment.json"
        observed = {**EXPECTED_ENV, **isolated}
        environment.write_text(json.dumps({
            "python_version": platform.python_version(), "python_executable": sys.executable,
            "venv_prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "installed_versions": installed, "expected_environment": observed,
            "observed_environment": {key: os.environ.get(key) for key in observed},
            "pytest_argv": ["python -m pytest", "-c /dev/null", "--noconftest",
                            "--rootdir=<source>", "--import-mode=importlib",
                            "-p no:cacheprovider", "-o addopts=", *SELECTIONS],
            "plugin_autoload_disabled": True, "conftest_disabled": True,
            "bytecode_disabled": True, "mcp_server_started": False,
            "live_trace_database_used": False,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        for path in (pre_status, pip_install, pip_freeze, environment):
            digest(path)
        junit, native_dir = result / "original-junit.xml", result / "native"
        read_paths = list(dict.fromkeys((workflow, driver, cases_path, requirements, lock,
                                         source_manifest, pre_status, pip_install, pip_freeze,
                                         environment, *source_paths, *context_paths, *carrier_paths)))
        pytest_argv = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--noconftest",
                       "--rootdir", str(source), "--import-mode=importlib", "-p", "no:cacheprovider",
                       "-o", "addopts=", "-q", *SELECTIONS, f"--junitxml={junit}"]
        os.environ["PYTHONPATH"] = str(source)
        status.update(state="running", repositories=pins, selected_case_count=5)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        from importlib.util import module_from_spec, spec_from_file_location
        carrier_file = tracked(carrier, "scripts/ci/native_conformance.py")
        spec = spec_from_file_location("pinned_native_conformance", carrier_file)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load pinned native carrier")
        api = module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        if (result / "shared-grade.json").exists():
            raise RuntimeError("unexpected shared-grade record before original evaluation")
        readset_before = {str(path): digest(path) for path in read_paths}
        api.capture_fixture_execution(
            argv=pytest_argv, cwd=source, junit=junit, output=native_dir,
            repositories={"recipe": recipe, "source": source, "carrier": carrier,
                          "app": app, "context": context},
            read_paths=read_paths, selections=SELECTIONS)
        result_before_grade = snapshot_tree(result, omit={"status.json"})
        readset_after_capture = {str(path): digest(path) for path in read_paths}
        receipt_path = native_dir / "receipt.json"
        native, receipt_sha = api.read_receipt(receipt_path)
        if native.get("fixture_execution_conformant") is not True:
            result_after = snapshot_tree(result, omit={"status.json"})
            readset_after = {str(path): digest(path) for path in read_paths}
            reopened, reopened_sha = api.read_receipt(receipt_path)
            if (result_before_grade != result_after or readset_before != readset_after_capture
                    or readset_after_capture != readset_after or reopened != native
                    or reopened_sha != receipt_sha):
                raise RuntimeError("failed native capture custody changed during review")
            status.update(state="capture_failed", exit_code=1,
                          fixture_execution_conformant=native.get("fixture_execution_conformant"),
                          native_summary=native.get("summary"), native_exit_code=native.get("exit_code"),
                          grade=None, error="native result is non-passing; preserved ungraded")
            return 1
        cases = verify_junit(junit, native, selected)
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("native carrier adapter did not project one receipt")
        claim = project_ci_conformance(rows[0])
        quality, traceability, reasons = grade(claim)
        result_after = snapshot_tree(result, omit={"status.json"})
        readset_after = {str(path): digest(path) for path in read_paths}
        reopened, reopened_sha = api.read_receipt(receipt_path)
        if (result_before_grade != result_after or readset_before != readset_after_capture
                or readset_after_capture != readset_after or reopened != native
                or reopened_sha != receipt_sha):
            raise RuntimeError("native result tree, source readset, or receipt changed during grade")
        if (quality, traceability) != ("Judged", "Located"):
            raise RuntimeError("original native conformance did not retain expected shared grade")
        (result / "shared-grade.json").write_text(json.dumps({
            "kind": "original_native_receipt_only", "fixture_rerun": False,
            "grade": {"Q": quality, "T": traceability, "reasons": reasons},
            "measurement_id": claim.measurement_id, "receipt_sha256": receipt_sha,
            "result_tree_hashes_before_grade": result_before_grade,
            "result_tree_hashes_after_grade": result_after,
            "source_readset_hashes_before": readset_before,
            "source_readset_hashes_after_capture": readset_after_capture,
            "source_readset_hashes_after_grade": readset_after,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        status.update(state="passed", exit_code=0, native_receipt="native/receipt.json",
                      junit="original-junit.xml", cases=cases,
                      shared_grade={"Q": quality, "T": traceability})
        return 0
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
