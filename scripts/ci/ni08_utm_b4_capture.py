"""Capture the complete synthetic Tulving/trace-FTS source-control suite."""
from __future__ import annotations

from collections import Counter
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET

ROOT_SOURCE_PIN = "e6488a02c5eddf4accccf82a96eb158f84526b97"
RESEARCH_PIN = "de02a21d88e006dd542b7a1a56bf8090a27de1f3"
APP_PIN = "e7e4ffc45164af5a4c66c438ecb1e98120efcf6a"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PYTHON_PIN = "3.13.15"
TASK = "handoffs/active/unified-trace-memory-service.md"
TASK_SHA256 = "34056965bda1505d30434450a5874fbf8c3a280c2630f5a3b6e9610527d02902"
CME_TASK = "handoffs/active/conversational-memory-eval-instrument.md"
CME_TASK_SHA256 = "e67a1f8ac3196f9a5bd5c138465d38f2bd5619d59b0d2355ea317db23befad85"
TABLE = "scripts/vidya/adapters/README.md"
TABLE_SHA256 = "28e772912368be799d5adaa11b78fc991ef96e9a0b615979906c411506c44792"
APP_LOCK_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
TEST_FILE = "scripts/benchmark/test_tulving_context_mode.py"
EXPECTED_CASES = "scripts/ci/ni08_utm_b4_expected_cases.json"
REQUIREMENTS = "scripts/ci/ni08_utm_b4_requirements.txt"
WORKFLOW = ".github/workflows/ni08-utm-b4-tulving-capture.yml"
RUNNER = "scripts/ci/ni08_utm_b4_capture.py"
RESULT_NAME = "ni08-utm-b4-tulving"
RUNNER_CONTEXT = "ubuntu-24.04"
EXECUTION_CONTEXT = "utm-b4-synthetic-tulving-fts5-no-model-or-embedding"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-utm-b4-tulving/venv" && '
    '"$RUNNER_TEMP/ni08-utm-b4-tulving/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r "
    "recipe/scripts/ci/ni08_utm_b4_requirements.txt"
)
RESEARCH_SOURCES = {
    TEST_FILE: "a53f38acbb890966317a7dbf0de9a076b552635992b25118b058f421e66b7c63",
    "scripts/benchmark/tulving_episodic_adapter.py": "d4cd093d8e1787a95931de6ba2aebfaad0ff2a149b2d5c8bee2f8e7f9f548a75",
    "scripts/benchmark/tulving_trace_retriever.py": "4036814bdfa9d0b93f8388fd01d1eeda55945b6959361e047c74acfe3eab972b",
    "scripts/benchmark/dataset_adapters.py": "0e170b23ec71ef688bf10ca0a7169a6ac29466979602502184819aa4b0abc210",
}
APP_SOURCES = {
    "src/trace/__init__.py": "d6978c32242961f757072076d161ac3def6f3c85f34f48280560bb0015f74356",
    "src/trace/navigation.py": "6af761095bfc8ced7f09045cbf634af48c8ffe9abc3174c61eff5d392267d886",
    "src/trace/query.py": "95311606a66c24be3cf430d7a986c40665e4ca7c172dd51d51d20e423a32fbd0",
    "src/trace/store.py": "47c3420f14808b5f25261471bc3e8f4923ef7a2f17622fbe46a21fec23091320",
    "src/trace/harness_schema.py": "a0251128d9a091a86b54def2021b052908e3baaa72966ca747437043bbc5384d",
}
PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "numpy": "2.4.4", "pandas": "3.0.2", "pyarrow": "24.0.0",
    "pygments": "2.20.0", "pytest": "9.0.3", "pyyaml": "6.0.3",
    "python-dateutil": "2.9.0.post0", "six": "1.17.0", "tzdata": "2026.1",
}
CARRIER_READS = (
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/canonical.py",
)
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
TRACE_PRIVATE_ROOT = "coordination/session-bus/session_bus.schema.json"


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def tracked_file(repo: Path, relative: str) -> Path:
    path = repo
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared input traverses symlink: {relative}")
    if not path.is_file():
        raise RuntimeError(f"declared input missing or nonregular: {relative}")
    row = git(repo, "ls-tree", "HEAD", "--", relative).split("\t", 1)[0].split()
    if not row or row[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not tracked regular Git file: {relative}")
    return path.absolute()


def hash_regular(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise RuntimeError(f"evidence cannot be opened safely: {path}: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"evidence is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read()
        after = os.fstat(fd)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns,
                                row.st_ctime_ns)
        if identity(before) != identity(after) or len(data) != after.st_size:
            raise RuntimeError(f"evidence changed while hashing: {path}")
        return hashlib.sha256(data).hexdigest()
    finally:
        os.close(fd)


def file_manifest(paths: list[Path]) -> dict[str, str]:
    unique = {str(path.absolute()): path for path in paths}
    return {name: hash_regular(unique[name]) for name in sorted(unique)}


def source_context(repo: Path) -> list[Path]:
    paths = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if name and (name.endswith(".py") or PurePosixPath(name).name in CONFIG_NAMES):
            paths.append(tracked_file(repo, name))
    return paths


def inventory(root: Path) -> dict[str, str]:
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError(f"result root is missing, not a directory, or symlinked: {root}")
    rows = {".": "directory"}

    def walk(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            path = Path(entry.path)
            mode = entry.stat(follow_symlinks=False).st_mode
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"result tree contains symlink: {path}")
            if stat.S_ISDIR(mode):
                rows[relative + "/"] = "directory"
                walk(path)
            elif stat.S_ISREG(mode):
                rows[relative] = hash_regular(path)
            else:
                raise RuntimeError(f"result tree contains special entry: {path}")

    walk(root)
    return rows


def verify_lock(app: Path, requirements: Path) -> dict[str, str]:
    lock_path = tracked_file(app, "uv.lock")
    lock_bytes = lock_path.read_bytes()
    if hashlib.sha256(lock_bytes).hexdigest() != APP_LOCK_SHA256:
        raise RuntimeError("APP uv.lock differs from reviewed dependency provenance")
    records = {row["name"].lower().replace("_", "-"): row
               for row in tomllib.loads(lock_bytes.decode("utf-8"))["package"]}
    versions: dict[str, str] = {}
    hashes: dict[str, set[str]] = {}
    current = None
    for line in requirements.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", line.strip())
        if match:
            current = match.group(1).lower().replace("_", "-")
            if current in versions:
                raise RuntimeError(f"duplicate dependency pin: {current}")
            versions[current] = match.group(2)
            hashes[current] = set()
        if current:
            hashes[current].update(re.findall(r"--hash=sha256:([0-9a-f]{64})", line))
    if versions != PACKAGES or set(hashes) != set(PACKAGES):
        raise RuntimeError("requirements differ from the reviewed minimal test closure")
    for name, version in PACKAGES.items():
        record = records.get(name)
        if not record or record["version"] != version:
            raise RuntimeError(f"{name} version differs from pinned APP lock")
        wheels = {item["hash"].removeprefix("sha256:") for item in record.get("wheels", [])}
        if not wheels or hashes[name] != wheels:
            raise RuntimeError(f"{name} hashes differ from complete APP-locked wheel set")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from locked version")
    return versions


def ast_cases(path: Path) -> list[dict[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=TEST_FILE)
    return [{"classname": Path(TEST_FILE).stem, "name": node.name}
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")]


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, research, app = (workspace / name for name in ("recipe", "carrier", "research", "app"))
    run_root, result = temp / RESULT_NAME, temp / RESULT_NAME / "result"
    status_path = run_root / "status.json"
    result.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        env_expected = {
            "UTM_B4_RUNNER_CONTEXT": RUNNER_CONTEXT,
            "UTM_B4_EXECUTION_CONTEXT": EXECUTION_CONTEXT,
            "UTM_B4_INSTALL_COMMAND": INSTALL_COMMAND,
            "EPYC_ORCHESTRATOR_ROOT": str(app),
            "TULVING_TRACE_DB_DIR": str(temp / RESULT_NAME / "trace-db"),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        for key, value in env_expected.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from the reviewed recipe")
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        expected_venv = (temp / RESULT_NAME / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected_venv:
            raise RuntimeError("capture interpreter is not the reviewed isolated venv")

        repos = {"recipe": recipe, "carrier": carrier, "research": research, "app": app}
        pins = {name: git(repo, "rev-parse", "HEAD") for name, repo in repos.items()}
        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER_PIN,
                         "research": RESEARCH_PIN, "app": APP_PIN}
        for name, repo in repos.items():
            if pins[name] != expected_pins[name]:
                raise RuntimeError(f"{name} checkout differs from exact pinned commit")
            if git(repo, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeError(f"{name} checkout is not clean")
        if git(recipe, "merge-base", "--is-ancestor", ROOT_SOURCE_PIN, "HEAD") != "":
            raise RuntimeError("recipe is not descended from enrolled ROOT source pin")

        workflow = tracked_file(recipe, WORKFLOW)
        runner = tracked_file(recipe, RUNNER)
        manifest_path = tracked_file(recipe, EXPECTED_CASES)
        requirements = tracked_file(recipe, REQUIREMENTS)
        task = tracked_file(recipe, TASK)
        cme_task = tracked_file(recipe, CME_TASK)
        table = tracked_file(recipe, TABLE)
        if hashlib.sha256(task.read_bytes()).hexdigest() != TASK_SHA256:
            raise RuntimeError("UTM-B4 task text differs from enrolled bytes")
        if hashlib.sha256(cme_task.read_bytes()).hexdigest() != CME_TASK_SHA256:
            raise RuntimeError("CME-4 source task differs from reviewed bytes")
        if hashlib.sha256(table.read_bytes()).hexdigest() != TABLE_SHA256:
            raise RuntimeError("source table differs from enrolled bytes")
        if hashlib.sha256(requirements.read_bytes()).hexdigest() != "846367fdcbeefc94c8920c0f12b7e08ecb29879cf429615d442fd8847d45cb83":
            raise RuntimeError("hash-locked requirements differ from reviewed bytes")

        research_files = {name: tracked_file(research, name) for name in RESEARCH_SOURCES}
        app_files = {name: tracked_file(app, name) for name in APP_SOURCES}
        for name, path in (*research_files.items(), *app_files.items()):
            if hashlib.sha256(path.read_bytes()).hexdigest() != (RESEARCH_SOURCES | APP_SOURCES)[name]:
                raise RuntimeError(f"source differs from reviewed hash: {name}")
        versions = verify_lock(app, requirements)
        cases = ast_cases(research_files[TEST_FILE])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest.get("cases") or []
        expected = Counter((item["classname"], item["name"]) for item in cases)
        manifested = Counter((item.get("classname"), item.get("name")) for item in rows)
        if (manifest.get("research_commit") != RESEARCH_PIN
                or manifest.get("test_file") != TEST_FILE
                or manifest.get("test_file_sha256") != RESEARCH_SOURCES[TEST_FILE]
                or manifest.get("count") != 23
                or len(cases) != 23 or manifested != expected or len(rows) != 23):
            raise RuntimeError("full-module AST cases differ from frozen exact manifest")

        install_log = result / "dependency-install.log"
        if install_log.is_symlink() or not install_log.is_file():
            raise RuntimeError("dependency install log is missing/nonregular")
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "runner_context": RUNNER_CONTEXT, "execution_context": EXECUTION_CONTEXT,
            "install_command": INSTALL_COMMAND, "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
            "app_uv_lock_sha256": APP_LOCK_SHA256, "dependency_versions": versions,
            "expected_case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "expected_cases": cases, "root_task": {"path": TASK, "sha256": TASK_SHA256},
            "cme4_task": {"path": CME_TASK, "sha256": CME_TASK_SHA256},
            "source_table": {"path": TABLE, "sha256": TABLE_SHA256},
            "pytest_plugin_autoload": "disabled", "pytest_config": "/dev/null",
            "pycache": "disabled", "hash_seed": "0",
            "trace_root": str(app), "trace_db_root": env_expected["TULVING_TRACE_DB_DIR"],
            "execution_scope": "Synthetic BOOK text + temporary SQLite/FTS5 database; all four trace-only cases required. No benchmark dataset, model, embedding service, network or production DB.",
            "dependency_closure": "The reviewed 12-package pytest/runtime closure, including NumPy, pandas and PyArrow, is verified against complete APP uv.lock wheel hashes.",
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite capture outputs")
        root_context, research_context, app_context = source_context(recipe), source_context(research), source_context(app)
        carrier_inputs = [tracked_file(carrier, name) for name in CARRIER_READS]
        read_paths = [workflow, runner, manifest_path, requirements, task, cme_task, table,
                      *root_context, *research_context, *app_context, *research_files.values(),
                      *app_files.values(), tracked_file(app, "uv.lock"), install_log, freeze,
                      environment, *carrier_inputs]
        producer_input_hashes = file_manifest(read_paths)
        source_readset_path = run_root / "source-readset.json"
        if source_readset_path.exists() or source_readset_path.is_symlink():
            raise RuntimeError("refusing to overwrite producer source readset")
        source_readset_path.write_text(json.dumps({
            "kind": "pre-execution_hashes_of_declared_native_read_paths",
            "sha256_by_absolute_path": producer_input_hashes,
            "path_count": len(producer_input_hashes),
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(research), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
                    "--repo", f"research={research}", "--repo", f"app={app}"]
        for path in dict.fromkeys(item.resolve() for item in read_paths):
            producer.extend(("--read-path", str(path)))
        selections = [f"{TEST_FILE}::{item['name']}" for item in cases]
        producer.extend(("--select", TEST_FILE))
        command = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(research),
                   "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider", "-q",
                   *selections, f"--junitxml={junit}"]
        status.update(state="running", repositories=pins, expected_case_count=23)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(research))
        exit_code = subprocess.call([*producer, "--", *command], cwd=research, env=env)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file() or not junit.is_file():
            status.update(state="capture_failed", exit_code=exit_code or 1,
                          diagnostic="native receipt or original JUnit missing")
            return exit_code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        native_cases = summary.get("cases") or []
        case_pairs = [(item.get("classname"), item.get("name")) for item in native_cases]
        expected_pairs = [(item["classname"], item["name"]) for item in cases]
        junit_cases = [(item.get("classname", ""), item.get("name", ""))
                       for item in ET.parse(junit).getroot().iter("testcase")]
        exact = Counter(case_pairs) == Counter(expected_pairs) == Counter(junit_cases)
        capture_ok = (exact and len(native_cases) == 23 and len(junit_cases) == 23
                      and counts.get("collected") == 23 and counts.get("executed") == 23
                      and counts.get("skipped") == 0 and counts.get("failure") == 0
                      and counts.get("error") == 0 and receipt.get("fixture_execution_conformant") is True)
        before = inventory(result)
        if not before or "shared-grade.json" in before:
            raise RuntimeError("fresh result tree is empty or already graded")
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        projected = native_rows(receipt_path)
        if len(projected) != 1:
            raise RuntimeError("native receipt does not project to exactly one shared row")
        claim = project_ci_conformance(projected[0])
        quality, trust, reasons = grade(claim)
        after = inventory(result)
        if before != after:
            raise RuntimeError("shared-grade analysis changed original result-tree membership or bytes")
        producer_input_after = file_manifest(read_paths)
        if producer_input_hashes != producer_input_after:
            raise RuntimeError("a declared producer source/read path changed during capture or grading")
        grade_ok = (quality, trust) == ("Judged", "Located")
        (result / "shared-grade.json").write_text(json.dumps({
            "kind": "analysis_of_existing_native_receipt", "measurement_id": claim.measurement_id,
            "source_kind": claim.source_kind, "binding_kind": claim.binding_kind,
            "grade": {"Q": quality, "T": trust, "reasons": reasons},
            "new_grade_authored": False, "original_hashes_before": before,
            "original_hashes_after": after,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        passed = exit_code == 0 and capture_ok and grade_ok
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (exit_code or 1),
                      junit_counts={"collected": len(junit_cases), "expected": 23, "exact_set": exact},
                      native_counts=counts, fixture_execution_conformant=receipt.get("fixture_execution_conformant"),
                      producer_readset_path=str(source_readset_path),
                      producer_readset_count=len(producer_input_hashes),
                      producer_readset_unchanged=True,
                      shared_grade={"Q": quality, "T": trust, "accepted": grade_ok})
        return 0 if passed else (exit_code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
