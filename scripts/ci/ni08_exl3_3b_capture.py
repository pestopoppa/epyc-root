"""Capture the complete EXL3-3B synthetic source-control suite via the shared carrier."""
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

ROOT_SOURCE_PIN = "94e7d72a8448c3b77189b77dbb5cdd5d4ccfadbc"
RESEARCH_PIN = "94821e731d65569ab6afd9e89bfecb5ecc812fbd"
APP_PIN = "a4132e57c96edb78088dedcfb7eb315497ef28db"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PYTHON_PIN = "3.13.15"
TASK = "handoffs/active/exl3-cpu-mi210-implementation.md"
TASK_SHA256 = "820b493c2af3e680dd6aa53f538a44ff7005cfbbd6ae01138fbfe68402d4320d"
TABLE = "scripts/vidya/adapters/README.md"
TABLE_SHA256 = "6d40b265db904c89994b97ed52f404409360c1a5aad67cd7798eb24e1ad61a8e"
APP_LOCK_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
REQUIREMENTS = "scripts/ci/ni08_exl3_3b_requirements.txt"
MANIFEST = "scripts/ci/ni08_exl3_3b_expected_cases.json"
WORKFLOW = ".github/workflows/ni08-exl3-3b-capture.yml"
RUNNER = "scripts/ci/ni08_exl3_3b_capture.py"
RESULT_NAME = "ni08-exl3-3b"
RUNNER_CONTEXT = "ubuntu-24.04"
EXECUTION_CONTEXT = "exl3-3b-source-controls-synthetic-no-device-or-claim"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-exl3-3b/venv" && '
    '"$RUNNER_TEMP/ni08-exl3-3b/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r "
    "recipe/scripts/ci/ni08_exl3_3b_requirements.txt"
)
TEST_FILE = "scripts/kernel_rnd/exl3_gfx90a/test_claimed_run.py"
RESEARCH_SOURCES = {
    "scripts/kernel_rnd/exl3_gfx90a/claimed_run.py": "833d9d8dde2bd2868ff67d8a90c595f2ca91bc2a931ba7d1aebffef405a58f7e",
    TEST_FILE: "cb2ad9aef83c4d46c0aff412c1d6de4166de681308f6ea25b9f7db715a0a3047",
}
PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3", "pyyaml": "6.0.3",
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
        raise RuntimeError(f"declared input is not a tracked regular Git file: {relative}")
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


def inventory(root: Path) -> dict[str, str]:
    """Bind every result-tree entry, including directories; reject links/special files."""
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError(f"result root is missing, not a directory, or symlinked: {root}")
    found: dict[str, str] = {".": "directory"}

    def walk(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            path = Path(entry.path)
            mode = entry.stat(follow_symlinks=False).st_mode
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"result tree contains symlink: {path}")
            if stat.S_ISDIR(mode):
                found[relative + "/"] = "directory"
                walk(path)
            elif stat.S_ISREG(mode):
                found[relative] = hash_regular(path)
            else:
                raise RuntimeError(f"result tree contains a special file: {path}")

    walk(root)
    return found


def file_manifest(paths: list[Path]) -> dict[str, str]:
    """Hash every declared producer input through a no-follow regular-file descriptor."""
    unique = {str(path.absolute()): path for path in paths}
    return {name: hash_regular(unique[name]) for name in sorted(unique)}


def manifest_digest(manifest: dict[str, str]) -> str:
    data = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def requirements_map(text: str) -> tuple[dict[str, str], dict[str, set[str]]]:
    versions: dict[str, str] = {}
    hashes: dict[str, set[str]] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", stripped)
        if match:
            current = match.group(1).lower().replace("_", "-")
            if current in versions:
                raise RuntimeError(f"duplicate package entry: {current}")
            versions[current] = match.group(2)
            hashes[current] = set()
        if current:
            hashes[current].update(re.findall(r"--hash=sha256:([0-9a-f]{64})", stripped))
    return versions, hashes


def verify_lock(app: Path, requirements: Path) -> dict[str, str]:
    lock_path = tracked_file(app, "uv.lock")
    lock_bytes = lock_path.read_bytes()
    if hashlib.sha256(lock_bytes).hexdigest() != APP_LOCK_SHA256:
        raise RuntimeError("pinned APP uv.lock differs from reviewed bytes")
    records = {row["name"].lower().replace("_", "-"): row
               for row in tomllib.loads(lock_bytes.decode("utf-8"))["package"]}
    versions, declared_hashes = requirements_map(requirements.read_text(encoding="utf-8"))
    if versions != PACKAGES or set(declared_hashes) != set(PACKAGES):
        raise RuntimeError("requirements are not the reviewed minimal package closure")
    for name, version in PACKAGES.items():
        row = records.get(name)
        if not row or row["version"] != version:
            raise RuntimeError(f"{name} version differs from the pinned APP lock")
        wheel_hashes = {item["hash"].removeprefix("sha256:") for item in row.get("wheels", [])}
        if not wheel_hashes or declared_hashes[name] != wheel_hashes:
            raise RuntimeError(f"{name} wheel hashes differ from the full locked wheel set")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from the reviewed pin")
    return versions


def ast_cases(path: Path) -> list[dict[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=TEST_FILE)
    cases = []
    module = ".".join(PurePosixPath(TEST_FILE).with_suffix("").parts)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for member in node.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name.startswith("test_"):
                cases.append({"classname": f"{module}.{node.name}", "name": member.name})
    return cases


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, research, app = (workspace / name for name in ("recipe", "carrier", "research", "app"))
    run_root = temp / RESULT_NAME
    result = run_root / "result"
    status_path = run_root / "status.json"
    result.mkdir(parents=True, exist_ok=True)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        env_expected = {
            "EXL3_RUNNER_CONTEXT": RUNNER_CONTEXT,
            "EXL3_EXECUTION_CONTEXT": EXECUTION_CONTEXT,
            "EXL3_INSTALL_COMMAND": INSTALL_COMMAND,
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
        pins = {key: git(repo, "rev-parse", "HEAD") for key, repo in repos.items()}
        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER_PIN,
                         "research": RESEARCH_PIN, "app": APP_PIN}
        for key, repo in repos.items():
            if pins[key] != expected_pins[key]:
                raise RuntimeError(f"{key} checkout differs from the exact pin")
            if git(repo, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeError(f"{key} checkout is not clean")
        if git(recipe, "merge-base", "--is-ancestor", ROOT_SOURCE_PIN, "HEAD") != "":
            raise RuntimeError("ROOT recipe is not descended from the enrolled source pin")
        if os.environ.get("RESEARCH_PIN") != RESEARCH_PIN or os.environ.get("ROOT_CARRIER_PIN") != CARRIER_PIN:
            raise RuntimeError("workflow source or carrier pin differs")

        workflow = tracked_file(recipe, WORKFLOW)
        runner = tracked_file(recipe, RUNNER)
        manifest_path = tracked_file(recipe, MANIFEST)
        requirements = tracked_file(recipe, REQUIREMENTS)
        task_path = tracked_file(recipe, TASK)
        table_path = tracked_file(recipe, TABLE)
        if hashlib.sha256(task_path.read_bytes()).hexdigest() != TASK_SHA256:
            raise RuntimeError("ROOT EXL3 task bytes differ from enrolled source")
        if hashlib.sha256(table_path.read_bytes()).hexdigest() != TABLE_SHA256:
            raise RuntimeError("ROOT source-table bytes differ from enrolled source")
        if hashlib.sha256(requirements.read_bytes()).hexdigest() != "9547b9f2bdba872c7e6d1df8154f4df98a434f8b185aa5054a0d1562bd3deda9":
            raise RuntimeError("minimal hash-locked requirements differ from reviewed bytes")

        source_files = {name: tracked_file(research, name) for name in RESEARCH_SOURCES}
        for name, path in source_files.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != RESEARCH_SOURCES[name]:
                raise RuntimeError(f"Research source differs from reviewed hash: {name}")
        package_versions = verify_lock(app, requirements)
        case_rows = ast_cases(source_files[TEST_FILE])
        expected_document = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_cases = expected_document.get("cases")
        if (expected_document.get("source_commit") != RESEARCH_PIN
                or expected_document.get("test_file") != TEST_FILE
                or expected_document.get("test_file_sha256") != RESEARCH_SOURCES[TEST_FILE]
                or expected_document.get("count") != 39
                or len(case_rows) != 39
                or Counter((r["classname"], r["name"]) for r in case_rows)
                != Counter((r.get("classname"), r.get("name")) for r in expected_cases or [])):
            raise RuntimeError("exact full-module AST case identities differ from the frozen manifest")

        install_log = result / "dependency-install.log"
        if install_log.is_symlink() or not install_log.is_file():
            raise RuntimeError("dependency installer log is missing or nonregular")
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "root_source_pin": ROOT_SOURCE_PIN, "runner_context": RUNNER_CONTEXT,
            "execution_context": EXECUTION_CONTEXT, "install_command": INSTALL_COMMAND,
            "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
            "app_uv_lock_sha256": APP_LOCK_SHA256, "dependency_install_log_sha256": hash_regular(install_log),
            "dependency_versions": package_versions, "expected_cases": case_rows,
            "expected_case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "root_task": {"path": TASK, "sha256": TASK_SHA256},
            "source_table": {"path": TABLE, "sha256": TABLE_SHA256},
            "pytest_plugin_autoload": "disabled", "pytest_config": "/dev/null",
            "pycache": "disabled", "hash_seed": "0",
            "temporary_test_root": "/mnt/raid0/llm/tmp (created on runner only)",
            "static_exercised_scope": "The selected module imports its local claimed_run.py and PyYAML. Its tests use standard-library mocks/temp files; session_bus is injected as a fake module, KFD/residency and claim paths are mocked, and no HIP process, device, kernel, model or physical claim is started.",
            "dependency_closure": "Minimal six-package pytest+PyYAML test/runtime closure, verified against exact APP uv.lock wheel hashes; no source distributions or dependency resolution.",
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        junit = result / "original-junit.xml"
        native = result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite capture outputs")
        carrier_inputs = [tracked_file(carrier, name) for name in CARRIER_READS]
        read_paths = [workflow, runner, manifest_path, requirements, task_path, table_path,
                      *source_files.values(), tracked_file(app, "uv.lock"), install_log,
                      freeze, environment, *carrier_inputs]
        producer_inputs_before = file_manifest(read_paths)
        input_readset_path = result / "producer-input-readset.json"
        if input_readset_path.exists() or input_readset_path.is_symlink():
            raise RuntimeError("refusing to overwrite producer input readset")
        input_readset_path.write_text(json.dumps({
            "kind": "pre-execution-source-input-hashes",
            "count": len(producer_inputs_before),
            "sha256": manifest_digest(producer_inputs_before),
            "inputs": producer_inputs_before,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        # Run the complete pinned module: some JUnit class/method identities contain
        # pytest-specific nodeid syntax and must not be reconstructed as selectors.
        selections = [TEST_FILE]
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(research), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
                    "--repo", f"research={research}", "--repo", f"app={app}"]
        for path in dict.fromkeys(p.resolve() for p in read_paths):
            producer.extend(("--read-path", str(path)))
        producer.extend(("--select", TEST_FILE))
        command = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(research),
                   "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider", "-q",
                   *selections, f"--junitxml={junit}"]
        status.update(state="running", repositories=pins, expected_case_count=39)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        execution_env = dict(os.environ, PYTHONPATH=str(research))
        exit_code = subprocess.call([*producer, "--", *command], cwd=research, env=execution_env)
        producer_inputs_after = file_manifest(read_paths)
        if producer_inputs_after != producer_inputs_before:
            raise RuntimeError("producer inputs changed during native capture")
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file() or not junit.is_file():
            status.update(state="capture_failed", exit_code=exit_code or 1,
                          diagnostic="native receipt or original JUnit missing")
            return exit_code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        summary = receipt.get("summary") or {}
        native_cases = summary.get("cases") or []
        native_counts = summary.get("counts") or {}
        expected_set = Counter((row["classname"], row["name"]) for row in case_rows)
        native_set = Counter((row.get("classname"), row.get("name")) for row in native_cases)
        junit_root = ET.parse(junit).getroot()
        junit_cases = [(row.get("classname", ""), row.get("name", ""))
                       for row in junit_root.iter("testcase")]
        junit_ok = Counter(junit_cases) == expected_set and len(junit_cases) == 39
        native_ok = (native_set == expected_set and len(native_cases) == 39
                     and native_counts.get("collected") == 39 and native_counts.get("executed") == 39
                     and native_counts.get("skipped") == 0 and native_counts.get("failure") == 0
                     and native_counts.get("error") == 0 and receipt.get("fixture_execution_conformant") is True)

        # Capture the full fresh result-tree membership/bytes before grading.
        before = inventory(result)
        if not before or "shared-grade.json" in before:
            raise RuntimeError("fresh result tree is empty or already contains a grade")
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("original native receipt projection is not exactly one row")
        claim = project_ci_conformance(rows[0])
        quality, trust, reasons = grade(claim)
        producer_inputs_after_grade = file_manifest(read_paths)
        if producer_inputs_after_grade != producer_inputs_before:
            raise RuntimeError("producer inputs changed during shared-grade analysis")
        after = inventory(result)
        if after != before:
            raise RuntimeError("shared-grade projection changed result-tree membership or bytes")
        grade_ok = (quality, trust) == ("Judged", "Located")
        grade_record = {
            "kind": "analysis_of_existing_native_receipt", "measurement_id": claim.measurement_id,
            "source_kind": claim.source_kind, "binding_kind": claim.binding_kind,
            "grade": {"Q": quality, "T": trust, "reasons": reasons},
            "new_grade_authored": False, "original_hashes_before": before,
            "original_hashes_after": after,
            "producer_input_count": len(producer_inputs_before),
            "producer_input_sha256_before": manifest_digest(producer_inputs_before),
            "producer_input_sha256_after": manifest_digest(producer_inputs_after_grade),
        }
        (result / "shared-grade.json").write_text(
            json.dumps(grade_record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        passed = (exit_code == 0 and junit_ok and native_ok and grade_ok)
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (exit_code or 1),
                      junit_counts={"collected": len(junit_cases), "expected": 39,
                                    "exact_case_set": junit_ok},
                      native_counts=native_counts, fixture_execution_conformant=receipt.get("fixture_execution_conformant"),
                      shared_grade={"Q": quality, "T": trust, "accepted": grade_ok})
        return 0 if passed else (exit_code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
