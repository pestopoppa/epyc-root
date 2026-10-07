"""Capture SCG-TEST-LOGDIR through the pinned native receipt carrier.

Execution is intended for the isolated hosted workflow only. The wrapper itself does not
import APP or invoke a main trial producer; pytest imports only the selected synthetic
controls and their ordinary import closure. No live process, model, endpoint, API lifespan, or trial producer is touched.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import shlex
import subprocess
import sys
import stat
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

APP_PIN = "0816f7b3e537d2815f0e35076785b489282b8f9b"
ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
ROOT_SOURCE_PIN = "954145a1b722feff4b1b1bc3ee0896d857b13606"
ROOT_TASKS = {
    "scripts/vidya/adapters/README.md",
    "handoffs/active/vidya-belief-substrate-program.md",
}
ROOT_TASK_IDS = {"VB-SCG-TEST-LOGDIR-CONFORMANCE"}
SELECTIONS = ["tests/unit/test_progress_logger_interaction.py"]
REQUIREMENTS = "scripts/ci/scg_test_logdir_test_requirements.txt"
READSET_MAP = "scripts/ci/scg_test_logdir_source_readset.json"
WORKFLOW = ".github/workflows/scg-test-logdir-source-capture.yml"
DRIVER = "scripts/ci/scg_test_logdir_capture.py"
PYTHON_VERSION = "3.13.15"
LOCKED_PACKAGES = {
    'annotated-doc': '0.0.4',
    'annotated-types': '0.7.0',
    'anyio': '4.13.0',
    'attrs': '26.1.0',
    'certifi': '2026.2.25',
    'charset-normalizer': '3.4.7',
    'colorama': '0.4.6',
    'fastapi': '0.135.3',
    'h11': '0.16.0',
    'httpcore': '1.0.9',
    'httpx': '0.28.1',
    'idna': '3.11',
    'iniconfig': '2.3.0',
    'jsonpatch': '1.33',
    'jsonpointer': '3.1.1',
    'jsonschema': '4.26.0',
    'jsonschema-specifications': '2025.9.1',
    'langchain-core': '1.2.28',
    'langgraph': '1.1.6',
    'langgraph-checkpoint': '4.0.1',
    'langgraph-prebuilt': '1.0.9',
    'langgraph-sdk': '0.3.13',
    'langsmith': '0.7.30',
    'logfire-api': '4.32.0',
    'numpy': '2.4.4',
    'orjson': '3.11.8',
    'ormsgpack': '1.12.2',
    'packaging': '26.0',
    'pluggy': '1.6.0',
    'pydantic': '2.13.0',
    'pydantic-core': '2.46.0',
    'pydantic-graph': '1.80.0',
    'pygments': '2.20.0',
    'pytest': '9.0.3',
    'pyyaml': '6.0.3',
    'referencing': '0.37.0',
    'requests': '2.33.1',
    'requests-toolbelt': '1.0.0',
    'rpds-py': '0.30.0',
    'starlette': '1.0.0',
    'tenacity': '9.1.4',
    'typing-extensions': '4.15.0',
    'typing-inspection': '0.4.2',
    'urllib3': '2.6.3',
    'uuid-utils': '0.14.1',
    'xxhash': '3.6.0',
    'zstandard': '0.25.0',
}
EXPECTED_CONTEXT = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTEST_ADDOPTS": "", "PYTEST_PLUGINS": "",
    "PYTHONHASHSEED": "0", "ORCHESTRATOR_MOCK_MODE": "1",
    "ORCHESTRATOR_LOG_DIR": "/dev/null", "ORCHESTRATOR_SERVING_CALLS_LOG": "off",
    "ORCHESTRATOR_COHERENCE_JUDGE_LOG": "off",
}
ABSENT_BINARY_OVERRIDES = {
    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "llama-cpp-bin",
    "ORCHESTRATOR_PATHS_LLAMA_MTMD": "llama-mtmd-cli",
    "ORCHESTRATOR_PATHS_LLAMA_SERVER": "llama-server",
}


def _stat_identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def regular_bytes_nofollow(path: Path) -> bytes:
    """Read one regular, single-link file through no-follow directory descriptors."""
    absolute = Path(os.path.abspath(path))
    parts = absolute.parts
    if not parts or parts[0] != os.sep:
        raise RuntimeError(f"source path is not absolute: {path}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    directory_flags = flags | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(os.sep, directory_flags)
    try:
        for component in parts[1:-1]:
            before = os.stat(component, dir_fd=directory_fd, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise RuntimeError(f"non-directory or symlink in source path: {path}")
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            after = os.fstat(next_fd)
            current = os.stat(component, dir_fd=directory_fd, follow_symlinks=False)
            if _stat_identity(before) != _stat_identity(after) or _stat_identity(after) != _stat_identity(current):
                os.close(next_fd)
                raise RuntimeError(f"source parent changed while opening: {path}")
            os.close(directory_fd)
            directory_fd = next_fd
        leaf = parts[-1]
        before = os.stat(leaf, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"captured input is not a single-link regular file: {path}")
        file_fd = os.open(leaf, flags | nofollow, dir_fd=directory_fd)
        try:
            opened = os.fstat(file_fd)
            if _stat_identity(before) != _stat_identity(opened):
                raise RuntimeError(f"file identity changed while opening: {path}")
            chunks = []
            while True:
                block = os.read(file_fd, 1024 * 1024)
                if not block:
                    break
                chunks.append(block)
            after = os.fstat(file_fd)
            current = os.stat(leaf, dir_fd=directory_fd, follow_symlinks=False)
            if _stat_identity(opened) != _stat_identity(after) or _stat_identity(after) != _stat_identity(current):
                raise RuntimeError(f"file changed while reading: {path}")
            return b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        os.close(directory_fd)


def sha256(path: Path) -> str:
    return hashlib.sha256(regular_bytes_nofollow(path)).hexdigest()


def file_set_digest(paths: list[Path]) -> dict[str, str]:
    snapshot = {}
    for path in paths:
        lexical = Path(os.path.abspath(path))
        snapshot[str(lexical)] = sha256(lexical)
    return snapshot


def result_tree_snapshot(root: Path) -> dict[str, object]:
    root = Path(os.path.abspath(root))
    root_info = os.lstat(root)
    if not stat.S_ISDIR(root_info.st_mode):
        raise RuntimeError(f"result root is not a real directory: {root}")
    entries: dict[str, dict[str, object]] = {".": {"kind": "directory", "identity": _stat_identity(root_info)}}

    def visit(directory: Path, rel_dir: PurePosixPath) -> None:
        before = os.lstat(directory)
        if not stat.S_ISDIR(before.st_mode):
            raise RuntimeError(f"result directory changed type: {directory}")
        with os.scandir(directory) as iterator:
            children = sorted(list(iterator), key=lambda item: item.name)
        for entry in children:
            rel = (rel_dir / entry.name).as_posix()
            child = directory / entry.name
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(child)
                after_link = os.lstat(child)
                if _stat_identity(info) != _stat_identity(after_link):
                    raise RuntimeError(f"result symlink changed while inventorying: {rel}")
                entries[rel] = {"kind": "symlink", "identity": _stat_identity(info),
                                "target": target,
                                "target_sha256": hashlib.sha256(os.fsencode(target)).hexdigest()}
            elif stat.S_ISDIR(info.st_mode):
                entries[rel] = {"kind": "directory", "identity": _stat_identity(info)}
                visit(child, rel_dir / entry.name)
            elif stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise RuntimeError(f"hard-linked result file refused: {rel}")
                digest = sha256(child)
                after_read = os.lstat(child)
                if _stat_identity(info) != _stat_identity(after_read):
                    raise RuntimeError(f"result file changed while inventorying: {rel}")
                entries[rel] = {"kind": "regular_file", "identity": _stat_identity(info),
                                "sha256": digest}
            else:
                raise RuntimeError(f"special file refused in result inventory: {rel}")
        after = os.lstat(directory)
        if _stat_identity(before) != _stat_identity(after):
            raise RuntimeError(f"result directory changed while inventorying: {directory}")

    visit(root, PurePosixPath("."))
    return {"entries": entries, "exact_status_exclusion": str(root.parent / "status.json")}


def verify_absent_binary_overrides(runner_temp: Path) -> dict[str, str]:
    expected = {}
    for key, leaf in ABSENT_BINARY_OVERRIDES.items():
        value = os.environ.get(key, "")
        path = runner_temp / "scg-test-logdir" / "absent-binaries" / leaf
        if value != str(path) or path.exists() or path.is_symlink():
            raise RuntimeError(f"{key} must name its exact absent Runner.Temp fixture")
        expected[key] = value
    return expected


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def verify_identity(repo: Path, expected: str, label: str) -> None:
    actual = git(repo, "rev-parse", "HEAD")
    if actual != expected:
        raise RuntimeError(f"{label} revision mismatch: expected {expected}, got {actual}")
    if git(repo, "status", "--porcelain"):
        raise RuntimeError(f"{label} checkout contains tracked or untracked modifications")


def source_paths_from_git_tree(repo: Path) -> dict[str, str]:
    """Complete typed tracked Python/config input set for the pinned clean checkout."""
    raw = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-r", "-z", "HEAD"])
    selected: dict[str, str] = {}
    config_names = {
        "uv.lock", "poetry.lock", "Pipfile.lock", "package.json", "package-lock.json",
        "yarn.lock", "pnpm-lock.yaml", "pytest.ini", "tox.ini", "setup.cfg",
        "mypy.ini", ".coveragerc", "scg_test_logdir_test_requirements.txt",
    }
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode = metadata.split(b" ", 1)[0]
        if mode == b"160000":
            continue
        relative = os.fsdecode(raw_path)
        name = Path(relative).name
        suffix = Path(relative).suffix.lower()
        if (suffix in {".py", ".yaml", ".yml", ".toml"}
                or relative.startswith("config/")
                or name in config_names
                or (name.startswith("requirements") and suffix == ".txt")):
            selected[relative] = mode.decode("ascii")
    return selected


def verify_complete_file_records(repo: Path, records: list[dict], label: str) -> None:
    declared: dict[str, str] = {}
    for item in records:
        if not isinstance(item, dict):
            raise RuntimeError(f"{label} readset contains a non-object record")
        relative = item.get("path")
        mode = item.get("git_mode")
        if (not isinstance(relative, str) or not relative or relative.startswith("/")
                or PurePosixPath(relative).as_posix() != relative
                or any(part in {"", ".", ".."} for part in relative.split("/"))):
            raise RuntimeError(f"{label} readset has a non-normalized path")
        if relative in declared:
            raise RuntimeError(f"{label} readset has a duplicate path: {relative}")
        if not isinstance(mode, str) or mode not in {"100644", "100755", "120000"}:
            raise RuntimeError(f"{label} readset has an unsupported Git mode: {relative}")
        declared[relative] = mode
    actual = source_paths_from_git_tree(repo)
    if declared != actual:
        missing = sorted(set(actual) - set(declared))[:5]
        extra = sorted(set(declared) - set(actual))[:5]
        mismatched = sorted(path for path in set(actual) & set(declared)
                            if actual[path] != declared[path])[:5]
        raise RuntimeError(
            f"{label} typed readset differs (missing={missing}, extra={extra}, mode={mismatched})"
        )


def recipe_manifest_digest(records: list[dict]) -> str:
    normalized = []
    for item in records:
        normalized.append({key: item[key] for key in
                           ("path", "git_mode", "sha256", "symlink_target") if key in item})
    normalized.sort(key=lambda item: item["path"])
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_file_records(repo: Path, records: list[dict], label: str) -> list[Path]:
    paths = []
    modes = source_paths_from_git_tree(repo)
    for item in records:
        relative = item.get("path")
        expected = item.get("sha256")
        expected_mode = item.get("git_mode")
        if not isinstance(relative, str) or not relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise RuntimeError(f"invalid {label} readset path")
        if not isinstance(expected, str) or len(expected) != 64:
            raise RuntimeError(f"invalid {label} readset digest for {relative}")
        source = repo / relative
        if modes.get(relative) != expected_mode:
            raise RuntimeError(f"{label} Git mode differs: {relative}")
        if source.is_symlink():
            if expected_mode != "120000":
                raise RuntimeError(f"{label} symlink Git mode mismatch: {relative}")
            target = item.get("symlink_target")
            if not isinstance(target, str) or os.readlink(source) != target:
                raise RuntimeError(f"{label} tracked symlink target mismatch: {relative}")
            link_digest = hashlib.sha256(os.fsencode(target)).hexdigest()
            if link_digest != expected:
                raise RuntimeError(f"{label} tracked symlink digest mismatch: {relative}")
            # The tracked link is source identity, but its external target is not imported
            # into this isolated fixture readset.
            continue
        info = os.lstat(source)
        observed_mode = "100755" if info.st_mode & 0o111 else "100644"
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or observed_mode != expected_mode or sha256(source) != expected):
            raise RuntimeError(f"{label} source digest mismatch: {relative}")
        paths.append(Path(os.path.abspath(source)))
    if not paths:
        raise RuntimeError(f"empty {label} readset")
    return paths


def verify_requirements(recipe: Path, app: Path, source_map: dict) -> None:
    expected = source_map.get("test_dependency_versions_from_uv_lock")
    expected_hashes = source_map.get("test_dependency_artifact_hashes_from_uv_lock")
    if not isinstance(expected, dict) or not expected or not isinstance(expected_hashes, dict):
        raise RuntimeError("source map has no exact locked test dependency set")
    if expected != LOCKED_PACKAGES:
        raise RuntimeError("driver locked package set differs from exact source map")
    observed = {}
    current = ""
    for raw in (recipe / REQUIREMENTS).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        current += " " + (line[:-1].strip() if continued else line)
        if continued:
            continue
        tokens = shlex.split(current)
        current = ""
        if not tokens or tokens[0].count("==") != 1:
            raise RuntimeError("test requirements must be exact package==version pins")
        package, version = tokens[0].split("==")
        artifact_hashes = sorted(token.removeprefix("--hash=") for token in tokens[1:])
        if any(not value.startswith("sha256:") for value in artifact_hashes):
            raise RuntimeError("requirements contain an unsupported artifact hash")
        if package.lower() in observed:
            raise RuntimeError("duplicate exact dependency requirement")
        observed[package.lower()] = {"version": version, "hashes": artifact_hashes}
    if current:
        raise RuntimeError("unterminated exact dependency requirement")
    versions = {name: item["version"] for name, item in observed.items()}
    if {name.lower(): version for name, version in expected.items()} != versions:
        raise RuntimeError("requirements differ from the exact APP uv.lock versions")
    if {name.lower(): sorted(values) for name, values in expected_hashes.items()} != {
        name: item["hashes"] for name, item in observed.items()
    }:
        raise RuntimeError("requirements artifact hashes differ from the exact APP uv.lock")
    lock_path = app / "uv.lock"
    if sha256(lock_path) != source_map.get("app_uv_lock_sha256"):
        raise RuntimeError("APP uv.lock digest differs from the source map")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    for name, version in expected.items():
        package = next((item for item in lock.get("package", [])
                        if str(item.get("name", "")).lower() == name.lower()), None)
        if package is None or package.get("version") != version:
            raise RuntimeError(f"test dependency {name} version differs from APP uv.lock")
        hashes = sorted({item["hash"] for item in package.get("wheels", []) if item.get("hash")})
        if hashes != sorted(expected_hashes.get(name, [])):
            raise RuntimeError(f"test dependency {name} artifact hashes differ from APP uv.lock")


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush(); os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def replace_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".new")
    if temporary.exists() or temporary.is_symlink():
        raise RuntimeError(f"custody update temp path already exists: {temporary}")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)


def verify_runtime() -> None:
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("reviewed Linux x86_64 runtime differs")
    if Path(sys.prefix).resolve() != Path(os.environ["RUNNER_TEMP"]).resolve() / "scg-test-logdir-venv" or sys.prefix == sys.base_prefix:
        raise RuntimeError("reviewed isolated venv prefix differs")
    if platform.python_implementation() != "CPython" or platform.python_version() != PYTHON_VERSION:
        raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
    for package, expected in LOCKED_PACKAGES.items():
        actual = importlib.metadata.version(package)
        if actual != expected:
            raise RuntimeError(f"installed {package} differs from pin: {actual}")


def validate_original_junit(path: Path, record: dict, expected_cases: list[dict]) -> dict:
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    expected = {(item["classname"], item["name"]) for item in expected_cases}
    actual = [(case.get("classname", ""), case.get("name", "")) for case in cases]
    if len(actual) != len(expected) or len(set(actual)) != len(actual) or set(actual) != expected:
        raise RuntimeError("original JUnit identities differ from the four-case exact source-derived manifest")
    modules = sorted({classname for classname, _ in expected})
    suite_counts = {name: {"collected": 0, "passed": 0, "skipped": 0, "failure": 0, "error": 0}
                    for name in modules}
    for case in cases:
        classname = case.get("classname", "")
        if classname not in suite_counts:
            raise RuntimeError(f"original JUnit contains an unselected module: {classname}")
        suite_counts[classname]["collected"] += 1
        status = next((name for name in ("failure", "error", "skipped")
                       if case.find(name) is not None), "passed")
        suite_counts[classname][status] += 1
        if status != "passed":
            raise RuntimeError("original JUnit contains a failed, errored, or skipped case")
    if any(counts["collected"] == 0 for counts in suite_counts.values()):
        raise RuntimeError("original JUnit omitted a selected module")
    summary = record.get("summary") or {}
    counts = summary.get("counts") or {}
    if (counts.get("collected") != len(cases) or counts.get("executed") != len(cases)
            or counts.get("skipped") != 0 or counts.get("failure") != 0 or counts.get("error") != 0):
        raise RuntimeError("native receipt aggregate counts disagree with selected original JUnit")
    return {"case_count": len(cases), "suite_case_counts": suite_counts}


def load_native_carrier(carrier: Path):
    source = carrier / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("scg_test_logdir_native_conformance", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pinned native receipt carrier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def grade_original_receipt(carrier: Path, receipt: Path) -> dict:
    # Existing source adapter and shared grade are used only on the hosted runner.
    sys.path.insert(0, str(carrier))
    sys.path.insert(0, str(carrier / "scripts/vidya"))
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade
    rows = native_rows(receipt)
    if len(rows) != 1:
        raise RuntimeError("existing native adapter did not yield exactly one original receipt row")
    claim = project_ci_conformance(rows[0])
    quality, traceability, reasons = grade(claim)
    if (quality, traceability) != ("Judged", "Located"):
        raise RuntimeError("fixture observation did not retain its existing observation grade")
    return {"adapter": "vidya.adapters.ci_conformance/v1", "quality": quality,
            "traceability": traceability, "reasons": reasons,
            "measurement_id": claim.measurement_id}


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, root_source, app = (workspace / name for name in
                                         ("recipe", "carrier", "root-source", "app"))
    run_root = runner_temp / "scg-test-logdir"
    result = run_root / "result"
    result.mkdir(parents=True, exist_ok=True)
    (result / "tmp").mkdir(exist_ok=True)
    status_path = run_root / "status.json"
    status = {"state": "preparing", "job": "scg-test-logdir-synthetic-controls", "exit_code": None}
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    read_paths = []
    custody_path = run_root / "capture-custody.json"
    custody = {"schema": "epyc.scg_test_logdir.capture_custody.v1", "state": "setup", "grade_attempted": False}
    try:
        if "__MAIN_" in APP_PIN or "__MAIN_" in ROOT_SOURCE_PIN:
            raise RuntimeError("MAIN enrollment/source pins must be rebound before any hosted capture")
        verify_runtime()
        if os.environ.get("SCG_LOGDIR_RUNNER_CONTEXT") != "ubuntu-24.04":
            raise RuntimeError("runner context differs from reviewed hosted recipe")
        if os.environ.get("SCG_LOGDIR_EXECUTION_CONTEXT") != "offline-synthetic-pytest-progress-log-destination-control":
            raise RuntimeError("execution context differs from reviewed hosted recipe")
        for key, expected in EXPECTED_CONTEXT.items():
            if os.environ.get(key) != expected:
                raise RuntimeError(f"{key} differs from reviewed isolated-runner context")
        absent_binary_overrides = verify_absent_binary_overrides(runner_temp)
        verify_identity(carrier, ROOT_CARRIER_PIN, "native capture carrier")
        verify_identity(root_source, ROOT_SOURCE_PIN, "ROOT enrollment source")
        verify_identity(app, APP_PIN, "APP source")
        recipe_pin = os.environ.get("RECIPE_PIN", "")
        if (recipe_pin != os.environ.get("GITHUB_SHA")
                or os.environ.get("GITHUB_REF") != "refs/heads/codex/scg-test-logdir-source-capture-20261007"
                or os.environ.get("GITHUB_EVENT_NAME") != "push"):
            raise RuntimeError("exact GitHub recipe SHA/literal branch push differs")
        if not recipe_pin:
            raise RuntimeError("workflow did not bind its exact recipe revision")
        verify_identity(recipe, recipe_pin, "workflow recipe")
        source_map_path = recipe / READSET_MAP
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        if source_map.get("schema") != "epyc.scg_test_logdir.source_readset.v1":
            raise RuntimeError("unsupported NI08 source/readset map")
        if source_map.get("app_revision") != APP_PIN or source_map.get("carrier_revision") != ROOT_CARRIER_PIN:
            raise RuntimeError("source/readset map revisions disagree with workflow pins")
        if source_map.get("root_source_revision") != ROOT_SOURCE_PIN:
            raise RuntimeError("source/readset map ROOT task pin differs from workflow")
        if source_map.get("selections") != SELECTIONS:
            raise RuntimeError("source/readset map selection differs from runner selection")

        task_rows = source_map.get("root_tasks", [])
        task_paths = [row.get("path") for row in task_rows if isinstance(row, dict)]
        if (len(task_paths) != len(task_rows) or len(task_paths) != len(set(task_paths))
                or set(task_paths) != ROOT_TASKS
                or set(source_map.get("root_task_ids", [])) != ROOT_TASK_IDS):
            raise RuntimeError("source map does not bind the exact SCG-TEST-LOGDIR task identity")
        root_task_inputs = []
        for row in task_rows:
            source = root_source / row["path"]
            if (source.is_symlink() or not source.is_file() or sha256(source) != row.get("sha256")
                    or git(root_source, "ls-tree", "HEAD", "--", row["path"]).split(" ", 1)[0]
                    != row.get("git_mode")):
                raise RuntimeError(f"ROOT task source digest differs: {row.get('path')}")
            root_task_inputs.append(source.resolve())
        root_context_inputs = []
        expected_enrollments = source_map.get("expected_enrollment_ids", [])
        if expected_enrollments != ["VB-SCG-TEST-LOGDIR-CONFORMANCE"]:
            raise RuntimeError("source map does not bind the exact SCG-TEST-LOGDIR enrollment")
        root_context_rows = source_map.get("root_contexts", [])
        context_paths = [row.get("path") for row in root_context_rows]
        if (len(context_paths) != len(root_context_rows) or len(context_paths) != len(set(context_paths))
                or set(context_paths) != {
                "scripts/vidya/adapters/README.md",
                "handoffs/active/vidya-belief-substrate-program.md"}):
            raise RuntimeError("source map does not bind the exact enrollment table and task context")
        for row in root_context_rows:
            source = root_source / row["path"]
            if (source.is_symlink() or not source.is_file() or sha256(source) != row.get("sha256")
                    or git(root_source, "ls-tree", "HEAD", "--", row["path"]).split(" ", 1)[0]
                    != row.get("git_mode")):
                raise RuntimeError(f"ROOT enrollment context digest differs: {row.get('path')}")
            contents = source.read_text(encoding="utf-8")
            if any(enrollment not in contents for enrollment in expected_enrollments):
                raise RuntimeError(f"ROOT enrollment ID absent from context: {row.get('path')}")
            root_context_inputs.append(source.resolve())

        verify_complete_file_records(app, source_map.get("app_files", []), "APP")
        verify_complete_file_records(carrier, source_map.get("carrier_files", []), "carrier")
        verify_complete_file_records(recipe, source_map.get("recipe_files", []), "recipe")
        if (source_map.get("recipe_map_self_exclusion") != "scripts/ci/scg_test_logdir_source_readset.json"
                or source_map.get("recipe_manifest_sha256")
                != recipe_manifest_digest(source_map.get("recipe_files", []))):
            raise RuntimeError("exact recipe manifest digest/self-exclusion binding mismatch")
        app_inputs = verify_file_records(app, source_map.get("app_files", []), "APP")
        carrier_inputs = verify_file_records(carrier, source_map.get("carrier_files", []), "carrier")
        recipe_inputs = verify_file_records(recipe, source_map.get("recipe_files", []), "recipe")
        if source_map.get("app_tracked_python_config_count") != len(source_map.get("app_files", [])):
            raise RuntimeError("APP tracked Python/config population differs from source map count")
        if source_map.get("carrier_tracked_python_config_count") != len(source_map.get("carrier_files", [])):
            raise RuntimeError("carrier tracked Python/config population differs from source map count")
        if source_map.get("recipe_tracked_python_config_count") != len(source_map.get("recipe_files", [])):
            raise RuntimeError("recipe tracked Python/config population differs from source map count")
        verify_requirements(recipe, app, source_map)
        carrier_script = carrier / "scripts/ci/native_conformance.py"
        carrier_hash = source_map.get("carrier_native_conformance_sha256")
        if not carrier_script.is_file() or sha256(carrier_script) != carrier_hash:
            raise RuntimeError("pinned native receipt source digest mismatch")
        if not source_map.get("expected_cases") or len(source_map["expected_cases"]) != 4:
            raise RuntimeError("source map must bind exactly four unchanged selected JUnit case identities")

        environment_path = result / "environment.json"
        freeze_path = result / "pip-freeze.txt"
        installer_log_path = result / "dependency-install.log"
        if not installer_log_path.is_file() or installer_log_path.is_symlink():
            raise RuntimeError("exact dependency install log is missing or not a regular file")
        with freeze_path.open("xb") as handle:
            handle.write(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = {
            "schema": "epyc.scg_test_logdir.hosted_environment.v1",
            "python": sys.version,
            "python_version": platform.python_version(),
            "installed_packages": {name: importlib.metadata.version(name) for name in LOCKED_PACKAGES},
            "pip_freeze_sha256": sha256(freeze_path),
            "platform": platform.platform(),
            "runner_context": os.environ.get("SCG_LOGDIR_RUNNER_CONTEXT", ""),
            "execution_context": os.environ.get("SCG_LOGDIR_EXECUTION_CONTEXT", ""),
            "pytest_pythonpath": os.pathsep.join((str(recipe / "scripts/ci"), str(app), str(app / "scripts/server"), str(app / "scripts/autopilot"))),
            "expected_cases_path": str(source_map_path),
            "app_revision": APP_PIN,
            "carrier_revision": ROOT_CARRIER_PIN,
            "root_source_revision": ROOT_SOURCE_PIN,
            "recipe_revision": recipe_pin,
            "app_uv_lock_sha256": source_map["app_uv_lock_sha256"],
            "requirements_sha256": sha256(recipe / REQUIREMENTS),
            "dependency_install_log_sha256": sha256(installer_log_path),
            "install_command": str(runner_temp / "scg-test-logdir-venv" / "bin" / "python") + " -m pip install --no-deps --only-binary=:all: --require-hashes -r recipe/" + REQUIREMENTS,
            "test_child_environment": "env -i allowlist; PYTHONPATH/PYTEST_* and ORCHESTRATOR_* all explicitly recorded",
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_ADDOPTS", "PYTEST_PLUGINS",
                "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED",
                "SCG_LOGDIR_EXECUTION_CONTEXT",
                "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_LOG_DIR",
                "ORCHESTRATOR_SERVING_CALLS_LOG", "ORCHESTRATOR_COHERENCE_JUDGE_LOG",
                *ABSENT_BINARY_OVERRIDES,
            )},
            "limits": [
                "actual root tests/conftest.py remains enabled; no collection-time writer is manufactured",
                "synthetic pytest tmp_path fixtures only",
                "no inference, model, endpoint, live runtime, or application lifespan",
                "no APP checkout writes; bytecode/cache disabled",
            ],
        }
        write_json(environment_path, environment)

        junit = result / "junit.xml"
        capture_dir = result / "native"
        pytest_argv = [
            sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(app),
            "--import-mode=importlib", "-p", "no:cacheprovider",
            "-p", "scg_test_logdir_pytest_probe", "--setup-show",
            "-q", "-o", "addopts=",
            f"--junitxml={junit}", "--basetemp", str(result / "pytest-tmp"), *SELECTIONS,
        ]
        # The capture child receives only the reviewed runner environment. In particular,
        # setup-python's ambient loader variables and any worker shell state are excluded.
        env = {
            "PATH": os.pathsep.join((str(Path(sys.executable).parent), "/usr/bin", "/bin")),
            "HOME": str(run_root / "home"),
            "TMPDIR": str(result / "tmp"),
            "CI": "true",
            "GITHUB_RUN_ID": os.environ.get("GITHUB_RUN_ID", ""),
            "GITHUB_JOB": os.environ.get("GITHUB_JOB", ""),
            "GITHUB_RUN_ATTEMPT": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "PYTHONPATH": environment["pytest_pythonpath"],
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTEST_ADDOPTS": "",
            "PYTEST_PLUGINS": "",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONUNBUFFERED": "1",
            "PYTHONNOUSERSITE": "1",
            "SCG_LOGDIR_RUNNER_CONTEXT": "ubuntu-24.04",
            "SCG_LOGDIR_EXECUTION_CONTEXT": "offline-synthetic-pytest-progress-log-destination-control",
            "SCG_LOGDIR_EXPECTED_CASES": str(source_map_path),
            "ORCHESTRATOR_MOCK_MODE": "1",
            "ORCHESTRATOR_LOG_DIR": "/dev/null",
            "ORCHESTRATOR_SERVING_CALLS_LOG": "off",
            "ORCHESTRATOR_COHERENCE_JUDGE_LOG": "off",
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_WORKSPACE": str(workspace),
        }
        env.update(absent_binary_overrides)
        (run_root / "home").mkdir(parents=True, exist_ok=True)
        (result / "tmp").mkdir(parents=True, exist_ok=True)
        read_paths = [
            source_map_path, app / "uv.lock",
            recipe / WORKFLOW, recipe / DRIVER,
            recipe / REQUIREMENTS, recipe / "scripts/ci/scg_test_logdir_pytest_probe.py",
            environment_path, freeze_path, installer_log_path,
            carrier_script, *root_task_inputs, *root_context_inputs, *recipe_inputs, *app_inputs,
            *carrier_inputs,
        ]
        input_before = file_set_digest(list(dict.fromkeys(read_paths)))
        result_before_capture = result_tree_snapshot(result)
        status.update({"state": "running", "selection_count": len(SELECTIONS)})
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        custody.update(state="before_native_capture", input_before=input_before,
                       result_tree_before_capture=result_before_capture, native_record=None)
        write_json(custody_path, custody)
        carrier_api = load_native_carrier(carrier)
        inherited = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(env)
            record = carrier_api.capture_fixture_execution(
                argv=pytest_argv, cwd=app, junit=junit, output=capture_dir,
                repositories={"recipe": recipe, "carrier": carrier,
                              "root_source": root_source, "app": app},
                read_paths=list(dict.fromkeys(read_paths)), selections=SELECTIONS,
            )
        finally:
            os.environ.clear()
            os.environ.update(inherited)
        receipt_path = capture_dir / "receipt.json"
        custody_path = run_root / "capture-custody.json"
        custody = {
            "schema": "epyc.scg_test_logdir.capture_custody.v1",
            "state": "native_capture_returned",
            "native_record": record,
            "input_before": input_before,
            "result_tree_before_capture": result_before_capture,
            "capture_outcome": record.get("fixture_execution_conformant"),
            "grade_attempted": False,
        }
        replace_json(custody_path, custody)
        status.update({"state": "captured", "native_metric": record.get("metric"),
                       "native_value": record.get("fixture_execution_conformant")})
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        input_after_capture = file_set_digest(list(dict.fromkeys(read_paths)))
        result_after_capture = result_tree_snapshot(result)
        custody.update(input_after_capture=input_after_capture,
                       result_tree_after_capture=result_after_capture)
        replace_json(custody_path, custody)
        if input_after_capture != input_before:
            custody.update(state="capture_refused_source_changed",
                           refusal="declared source/readset changed during capture")
            replace_json(custody_path, custody)
            status.update(state="capture_refused", error=custody["refusal"])
            return 1
        try:
            reopened, receipt_seal = carrier_api.read_receipt(receipt_path)
            receipt_file_sha_before_grade = sha256(receipt_path)
        except Exception as exc:
            custody.update(state="capture_refused_receipt_invalid",
                           refusal=f"{type(exc).__name__}: {exc}")
            replace_json(custody_path, custody)
            status.update(state="capture_refused", error=custody["refusal"])
            return 1
        custody.update(receipt=reopened, receipt_file_sha256=receipt_file_sha_before_grade,
                       receipt_seal=receipt_seal)
        if reopened.get("fixture_execution_conformant") is not True:
            custody.update(state="capture_refused_native_false_or_null",
                           refusal="native fixture outcome was not true; no grade attempted")
            replace_json(custody_path, custody)
            status.update(state="capture_refused", error=custody["refusal"],
                          native_value=reopened.get("fixture_execution_conformant"))
            return 1
        command_log = capture_dir / "command.log"
        command_text = regular_bytes_nofollow(command_log).decode("utf-8", errors="replace")
        if "_restore_progress_log_override_after_suite" not in command_text:
            custody.update(state="capture_refused_conftest_missing",
                           refusal="pytest output does not prove actual conftest fixture ran")
            replace_json(custody_path, custody)
            status.update(state="capture_refused", error=custody["refusal"])
            return 1
        if "SCG_LOGDIR_CONFTST_TEARDOWN=PASS" not in command_text:
            custody.update(state="capture_refused_teardown_not_restored",
                           refusal="conftest teardown did not restore prior environment")
            replace_json(custody_path, custody)
            status.update(state="capture_refused", error=custody["refusal"])
            return 1
        try:
            case_facts = validate_original_junit(junit, reopened, source_map["expected_cases"])
        except Exception as exc:
            custody.update(state="capture_refused_junit_invalid",
                           refusal=f"{type(exc).__name__}: {exc}")
            replace_json(custody_path, custody)
            status.update(state="capture_refused", error=custody["refusal"])
            return 1
        original_tree_before = result_tree_snapshot(result)
        custody.update(state="native_true_pregrade", result_tree_before_grade=original_tree_before,
                       grade_attempted=True)
        replace_json(custody_path, custody)
        shared_grade = grade_original_receipt(carrier, receipt_path)
        reopened_after, receipt_seal_after_grade = carrier_api.read_receipt(receipt_path)
        original_tree_after = result_tree_snapshot(result)
        input_after_grade = file_set_digest(list(dict.fromkeys(read_paths)))
        receipt_file_sha_after_grade = sha256(receipt_path)
        verify_absent_binary_overrides(runner_temp)
        if (original_tree_before != original_tree_after or input_before != input_after_capture
                or input_before != input_after_grade or reopened_after != reopened
                or receipt_seal_after_grade != receipt_seal
                or receipt_file_sha_before_grade != receipt_file_sha_after_grade):
            custody.update(state="grade_refused_custody_changed",
                           input_after_grade=input_after_grade,
                           result_tree_after_grade=original_tree_after,
                           receipt_file_sha_after_grade=receipt_file_sha_after_grade,
                           refusal="original source/result/receipt changed during native shared-grade read")
            replace_json(custody_path, custody)
            status.update(state="grade_refused", error=custody["refusal"])
            return 1
        shared_grade["source_custody"] = {
            "schema": "epyc.scg_test_logdir.source_custody.v1",
            "input_before": input_before,
            "input_after_capture": input_after_capture,
            "input_after_grade": input_after_grade,
            "result_tree_before_capture": result_before_capture,
            "result_tree_after_capture": result_after_capture,
            "result_tree_before_grade": original_tree_before,
            "result_tree_after_grade": original_tree_after,
            "receipt_file_sha256": receipt_file_sha_before_grade,
            "receipt_seal": receipt_seal,
            "receipt_seal_after_grade": receipt_seal_after_grade,
            "absent_binary_overrides": absent_binary_overrides,
            "enrollment_ids": expected_enrollments,
        }
        write_json(run_root / "shared-grade.json", shared_grade)
        custody.update(state="graded", input_after_grade=input_after_grade,
                       result_tree_before_grade=original_tree_before,
                       result_tree_after_grade=original_tree_after,
                       receipt_file_sha_after_grade=receipt_file_sha_after_grade,
                       receipt_seal_after_grade=receipt_seal_after_grade,
                       shared_grade=shared_grade)
        replace_json(custody_path, custody)
        status.update(state="passed", exit_code=0, native_receipt="native/receipt.json",
                      junit="junit.xml", source_readset="native/receipt.json#readset",
                      native_metric=reopened["metric"], native_value=reopened["fixture_execution_conformant"],
                      counts=reopened["summary"]["counts"], cases=case_facts,
                      shared_grade={"quality": shared_grade["quality"],
                                    "traceability": shared_grade["traceability"]})
        return 0
    except Exception as exc:
        errors = {}
        snapshots = {}
        for source in dict.fromkeys(read_paths):
            try: snapshots[str(source)] = sha256(source)
            except Exception as snapshot_error: errors[str(source)] = f"{type(snapshot_error).__name__}: {snapshot_error}"
        custody.update(state="exception", error=f"{type(exc).__name__}: {exc}",
                       input_after_exception=snapshots, input_snapshot_errors=errors)
        try: custody["result_tree_after_exception"] = result_tree_snapshot(result)
        except Exception as snapshot_error: custody["result_snapshot_error"] = f"{type(snapshot_error).__name__}: {snapshot_error}"
        try:
            if custody_path.exists(): replace_json(custody_path, custody)
            else: write_json(custody_path, custody)
        except Exception as custody_error: status["custody_error"] = f"{type(custody_error).__name__}: {custody_error}"
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
