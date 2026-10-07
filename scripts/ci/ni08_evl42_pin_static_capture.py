#!/usr/bin/env python3
"""Capture the exact synthetic EVL-42 static pin checker suite through the existing carrier."""
from __future__ import annotations

from collections import Counter
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import tomllib

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
ROOT_SOURCE_PIN = "99b3763078abd859026c8051e1c480b89a15ee72"
TASK_SHA256 = "990590b2b0a6cf806d6ac4af458dc909376f288d89dabfe40b9c18a21a5d3660"
TABLE_SHA256 = "382b9562bf61de76dfcca52addc9d880ed3a2ea846eda77100ec9eae75d088bd"
RESEARCH_PIN = "374cd7fa8599cd8198a48c0d2bd6dae54e7af946"
LOCK_SOURCE_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
LOCK_SOURCE_BLOB = "ef2306018773ff9a1e80389970d92f66fcf8d5b7"
LOCK_SOURCE_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
CASE_MANIFEST_SHA256 = "34366649c2b06dfed3f928def165c5e5d74fa775437660fbbaff01f132aa82c8"
REQUIREMENTS_SHA256 = "e10bd23d53c73d76ae3fdd231dfd28b177d777e8107f6f56762299002711512a"
RESEARCH_TEST_SHA256 = "5341325f343e91195f1b44fe574be6778e1b573ee71dd07f3deecd5818f42ae7"
RESEARCH_CHECKER_SHA256 = "351ee3fec5a8d3047f184203d45cbcd7bfdc88ca652923621eb9cbe5ff7a3798"
PYTHON_PIN = "3.13.15"
RESULT_NAME = "evl42-pin-static"
WORKFLOW = ".github/workflows/ni08-evl42-pin-static-capture.yml"
RUNNER = "scripts/ci/ni08_evl42_pin_static_capture.py"
CASE_MANIFEST = "scripts/ci/ni08_evl42_pin_static_cases.json"
REQUIREMENTS = "scripts/ci/ni08_evl42_pin_static_requirements.txt"
TASK = "handoffs/active/scoring-infra-standardization.md"
TABLE = "scripts/vidya/adapters/README.md"
RESEARCH_TEST = "scripts/benchmark/tests/test_pin_staleness.py"
RESEARCH_CHECKER = "scripts/benchmark/check_pin_staleness.py"
RESEARCH_CONFIG = ("pyproject.toml", "uv.lock")
CARRIER_FILES = (
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/canonical.py",
)
LOCKED_PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "Pygments": "2.20.0", "pytest": "9.0.3",
}
INSTALL_COMMAND = (
    "python -m venv \"$RUNNER_TEMP/evl42-pin-static-venv\" && "
    "\"$RUNNER_TEMP/evl42-pin-static-venv/bin/python\" -m pip install "
    "--disable-pip-version-check --require-hashes --no-deps --only-binary=:all: -r "
    "recipe/scripts/ci/ni08_evl42_pin_static_requirements.txt"
)
ENVIRONMENT = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    "PYTEST_ADDOPTS": "",
    "PYTEST_PLUGINS": "",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0",
    "PYTHONUNBUFFERED": "1",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str) -> str:
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError(f"{label} checkout is not clean")
    head = git(repo, "rev-parse", "HEAD")
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise RuntimeError(f"{label} HEAD is not a full Git commit")
    return head


def tracked_file(repo: Path, relative: str) -> Path:
    path = repo
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared input traverses a symlink: {relative}")
    if not path.is_file():
        raise RuntimeError(f"declared input is missing or nonregular: {relative}")
    row = git(repo, "ls-tree", "HEAD", "--", relative).split("\t", 1)[0].split()
    if not row or row[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a tracked regular file: {relative}")
    return path.absolute()


def hash_regular(path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError(f"captured input is not a single-link regular file: {path}")
        digest = hashlib.sha256()
        total = 0
        while True:
            data = os.read(fd, 1024 * 1024)
            if not data:
                break
            digest.update(data)
            total += len(data)
        after = os.fstat(fd)
        identity = lambda row: (row.st_dev, row.st_ino, row.st_mode, row.st_size,
                                row.st_nlink, row.st_mtime_ns, row.st_ctime_ns)
        if identity(before) != identity(after) or total != after.st_size:
            raise RuntimeError(f"captured input changed while hashing: {path}")
        named = path.lstat()
        if identity(after) != identity(named):
            raise RuntimeError(f"captured input path changed while hashing: {path}")
        return digest.hexdigest()
    finally:
        os.close(fd)


def inventory(root: Path) -> dict[str, str]:
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError("fresh result tree is not a real directory")
    found = {".": "directory"}

    def walk(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda row: row.name):
            path = Path(entry.path)
            mode = entry.stat(follow_symlinks=False).st_mode
            rel = path.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"result tree contains a symlink: {rel}")
            if stat.S_ISDIR(mode):
                found[rel + "/"] = "directory"
                walk(path)
            elif stat.S_ISREG(mode):
                found[rel] = hash_regular(path)
            else:
                raise RuntimeError(f"result tree contains a special file: {rel}")

    walk(root)
    return found


def _expected_cases(data: bytes) -> tuple[str, ...]:
    manifest = json.loads(data)
    if manifest.get("schema") != "ni08.evl42.pin_static_cases/v1":
        raise RuntimeError("case manifest schema mismatch")
    if (manifest.get("test_file") != RESEARCH_TEST
            or manifest.get("test_classname") != "scripts.benchmark.tests.test_pin_staleness"
            or manifest.get("case_count") != 8):
        raise RuntimeError("case manifest scope or count mismatch")
    names = manifest.get("cases")
    if not isinstance(names, list) or len(names) != 8 or len(set(names)) != 8:
        raise RuntimeError("case manifest must contain eight unique test functions")
    return tuple(f"{manifest['test_file']}::{name}" for name in names)


def verify_test_ast(source: bytes, selections: tuple[str, ...]) -> None:
    tree = ast.parse(source.decode("utf-8"), filename=RESEARCH_TEST)
    actual = [node.name for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
              and node.name.startswith("test_")]
    expected = [item.rsplit("::", 1)[1] for item in selections]
    if Counter(actual) != Counter(expected) or len(actual) != len(expected):
        raise RuntimeError("manifest differs from complete AST test-function inventory")


def verify_requirements(data: bytes, lock_data: bytes) -> None:
    """Require the exact minimal closure and every wheel in the pinned APP lock."""
    import re
    versions: dict[str, str] = {}
    hashes: dict[str, set[str]] = {}
    pending = ""
    for raw in data.decode("utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        pending += " " + (line[:-1].rstrip() if continued else line)
        if continued:
            continue
        match = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)==([^\s]+)\s+((?:--hash=sha256:[0-9a-f]{64}\s*)+)", pending)
        if not match:
            raise RuntimeError("malformed exact hash-locked requirement")
        name, version, wheel_tokens = match.groups()
        name = name.lower()
        if name in versions:
            raise RuntimeError("duplicate locked requirement")
        versions[name] = version
        hashes[name] = set(re.findall(r"--hash=sha256:([0-9a-f]{64})", wheel_tokens))
        pending = ""
    if pending:
        raise RuntimeError("dangling requirements continuation")
    expected_versions = {name.lower(): version for name, version in LOCKED_PACKAGES.items()}
    if versions != expected_versions:
        raise RuntimeError("dependency pins differ from reviewed minimal pytest closure")
    packages = {row["name"].lower(): row for row in tomllib.loads(lock_data.decode("utf-8"))["package"]}
    for name, version in expected_versions.items():
        package = packages.get(name)
        if not package or package.get("version") != version:
            raise RuntimeError(f"package/version absent from explicit lock source: {name}")
        expected_hashes = set()
        for wheel in package.get("wheels", []):
            value = wheel.get("hash", "")
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
                raise RuntimeError("pinned lock wheel lacks exact SHA-256")
            expected_hashes.add(value.removeprefix("sha256:"))
        if not expected_hashes or hashes[name] != expected_hashes:
            raise RuntimeError(f"requirements differ from ALL pinned lock wheels: {name}")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, research, lock_source = (workspace / name for name in ("recipe", "carrier", "research", "lock-source"))
    run_root = runner_temp / RESULT_NAME
    result = run_root / "result"
    status_path = run_root / "status.json"
    install_log_source = run_root / "dependency-install.log"
    status = {"state": "preparing", "job": "evl42-pin-static", "exit_code": None}
    if run_root.is_symlink() or not run_root.is_dir():
        raise RuntimeError("workflow did not create a private capture directory")
    if status_path.is_symlink() or not status_path.is_file():
        raise RuntimeError("workflow status record is missing or linked")
    result.mkdir(exist_ok=False)
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        expected_env = {**ENVIRONMENT,
                        "NI08_RUNNER_CONTEXT": "ubuntu-24.04",
                        "NI08_EXECUTION_CONTEXT": "evl42-static-synthetic-tests-no-repository-scan"}
        for key, value in expected_env.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from reviewed capture recipe")
        if os.environ.get("NI08_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("installation command differs from reviewed recipe")
        if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
            raise RuntimeError("runner must be Linux x86_64")
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        venv = (runner_temp / f"{RESULT_NAME}-venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != venv:
            raise RuntimeError("capture Python is not the reviewed isolated venv")

        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": ROOT_CARRIER_PIN,
                         "research": RESEARCH_PIN, "lock_source": LOCK_SOURCE_PIN}
        repositories = {"recipe": recipe, "carrier": carrier, "research": research, "lock_source": lock_source}
        pins = {name: require_clean(repo, name) for name, repo in repositories.items()}
        if pins != expected_pins:
            raise RuntimeError(f"checkout pins differ from reviewed source map: {pins}")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN:
            raise RuntimeError("workflow carrier pin differs")
        if os.environ.get("ROOT_SOURCE_PIN") != ROOT_SOURCE_PIN:
            raise RuntimeError("workflow ROOT source checkpoint differs")
        if os.environ.get("RESEARCH_PIN") != RESEARCH_PIN:
            raise RuntimeError("workflow Research pin differs")
        if os.environ.get("LOCK_SOURCE_PIN") != LOCK_SOURCE_PIN:
            raise RuntimeError("workflow lock source pin differs")
        for key, expected in (
            ("CASE_MANIFEST_SHA256", CASE_MANIFEST_SHA256),
            ("REQUIREMENTS_SHA256", REQUIREMENTS_SHA256),
            ("RESEARCH_TEST_SHA256", RESEARCH_TEST_SHA256),
            ("RESEARCH_CHECKER_SHA256", RESEARCH_CHECKER_SHA256),
        ):
            if os.environ.get(key) != expected:
                raise RuntimeError(f"{key} differs from the reviewed source map")
        if git(recipe, "merge-base", "--is-ancestor", ROOT_SOURCE_PIN, "HEAD") != "":
            raise RuntimeError("recipe does not descend from the enrolled ROOT source checkpoint")

        workflow = tracked_file(recipe, WORKFLOW)
        runner = tracked_file(recipe, RUNNER)
        manifest_path = tracked_file(recipe, CASE_MANIFEST)
        requirements_path = tracked_file(recipe, REQUIREMENTS)
        task_path = tracked_file(recipe, TASK)
        table_path = tracked_file(recipe, TABLE)
        if hash_regular(task_path) != TASK_SHA256 or hash_regular(table_path) != TABLE_SHA256:
            raise RuntimeError("enrolled EVL42 task or source-table bytes differ")
        test_path = tracked_file(research, RESEARCH_TEST)
        checker_path = tracked_file(research, RESEARCH_CHECKER)
        research_config = [tracked_file(research, name) for name in RESEARCH_CONFIG]
        manifest_bytes = hash_regular(manifest_path)
        manifest_payload = manifest_path.read_bytes()
        if manifest_bytes != CASE_MANIFEST_SHA256 or hashlib.sha256(manifest_payload).hexdigest() != manifest_bytes:
            raise RuntimeError("case manifest differs from reviewed bytes")
        selections = _expected_cases(manifest_payload)
        test_bytes = test_path.read_bytes()
        verify_test_ast(test_bytes, selections)
        requirement_bytes = requirements_path.read_bytes()
        lock_path = tracked_file(lock_source, "uv.lock")
        lock_bytes = lock_path.read_bytes()
        if (git(lock_source, "rev-parse", "HEAD:uv.lock") != LOCK_SOURCE_BLOB
                or hashlib.sha256(lock_bytes).hexdigest() != LOCK_SOURCE_SHA256):
            raise RuntimeError("explicit APP lock source bytes/blob differ")
        verify_requirements(requirement_bytes, lock_bytes)
        if hashlib.sha256(requirement_bytes).hexdigest() != REQUIREMENTS_SHA256:
            raise RuntimeError("requirements file differs from reviewed hash")
        if hashlib.sha256(test_bytes).hexdigest() != RESEARCH_TEST_SHA256:
            raise RuntimeError("Research test source differs from reviewed hash")
        if hashlib.sha256(checker_path.read_bytes()).hexdigest() != RESEARCH_CHECKER_SHA256:
            raise RuntimeError("Research checker source differs from reviewed hash")

        versions = {name: importlib.metadata.version(name) for name in LOCKED_PACKAGES}
        if versions != LOCKED_PACKAGES:
            raise RuntimeError("isolated pytest dependency versions differ from reviewed pins")
        freeze = run_root / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = run_root / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "runner_context": expected_env["NI08_RUNNER_CONTEXT"],
            "execution_context": expected_env["NI08_EXECUTION_CONTEXT"],
            "test_selections": list(selections), "expected_case_count": len(selections),
            "declared_dependencies": LOCKED_PACKAGES, "install_command": INSTALL_COMMAND,
            "pytest_isolation": "-c /dev/null, --rootdir Research checkout, --noconftest, "
                                "--import-mode=importlib, plugin autoload disabled, cache disabled",
            "scope": "synthetic temporary-Git/path fixtures only; no actual benchmark-tree scan, "
                     "model/artifact/raw trace reads, benchmark, inference, or pin refresh",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not install_log_source.is_file() or install_log_source.is_symlink():
            raise RuntimeError("dependency installation log is missing or linked")
        install_log = install_log_source
        if install_log.stat().st_size == 0:
            raise RuntimeError("dependency installation log is empty")

        carrier_paths = [tracked_file(carrier, relative) for relative in CARRIER_FILES]
        read_paths = [workflow, runner, manifest_path, requirements_path, task_path, table_path,
                      test_path, checker_path, *research_config, *carrier_paths, lock_path,
                      freeze, environment, install_log]
        read_paths = list(dict.fromkeys(path.resolve() for path in read_paths))
        if len(read_paths) != len(set(read_paths)):
            raise RuntimeError("duplicate normalized readset input")
        original_hashes_before = {str(path): hash_regular(path) for path in read_paths}

        argv = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(research),
                "--noconftest", "--import-mode=importlib", "-o", "addopts=",
                "-p", "no:cacheprovider", "-q", *selections,
                f"--junitxml={result / 'original-junit.xml'}"]
        capture_env = dict(os.environ)
        capture_env.update(ENVIRONMENT)
        capture_env["PYTHONPATH"] = str(research)
        native_output = result / "native"
        producer_argv = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                         "--cwd", str(research), "--junit", str(result / "original-junit.xml"),
                         "--output", str(native_output)]
        for label, repo in repositories.items():
            producer_argv.extend(["--repo", f"{label}={repo}"])
        for path in read_paths:
            producer_argv.extend(["--read-path", str(path)])
        for selection in selections:
            producer_argv.extend(["--select", selection])

        status.update(state="running", repositories=pins, selections=list(selections))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer_argv, "--", *argv], cwd=research, env=capture_env)
        receipt_path = native_output / "receipt.json"
        if not receipt_path.is_file():
            raise RuntimeError("native carrier did not produce an original receipt")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        actual_cases = [(row.get("classname"), row.get("name"))
                        for row in summary.get("cases") or []]
        expected_cases = [("scripts.benchmark.tests.test_pin_staleness", item.rsplit("::", 1)[1])
                          for item in selections]
        cases_ok = (Counter(actual_cases) == Counter(expected_cases)
                    and len(actual_cases) == len(expected_cases)
                    and counts.get("collected") == len(expected_cases)
                    and counts.get("executed") == len(expected_cases)
                    and counts.get("skipped") == 0
                    and counts.get("failure") == 0 and counts.get("error") == 0)
        result_before_grade = inventory(result)
        original_hashes_before_grade = {str(path): hash_regular(path) for path in read_paths}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        projected = native_rows(receipt_path)
        if len(projected) != 1:
            raise RuntimeError("original receipt did not produce exactly one existing CI projection")
        claim = project_ci_conformance(projected[0])
        quality, trust, reasons = grade(claim)
        result_after_grade = inventory(result)
        original_hashes_after_grade = {str(path): hash_regular(path) for path in read_paths}
        if result_before_grade != result_after_grade:
            raise RuntimeError("shared-grade projection changed the original result-tree membership or bytes")
        if original_hashes_before_grade != original_hashes_after_grade:
            raise RuntimeError("shared-grade projection changed a declared source/config original")
        if original_hashes_before != original_hashes_after_grade:
            raise RuntimeError("declared source/readset inputs changed during capture")
        grade_path = run_root / "shared-grade.json"
        with grade_path.open("x", encoding="utf-8") as handle:
            json.dump({"kind": "analysis_of_existing_native_receipt",
                       "original_result_tree_before_grade": result_before_grade,
                       "original_result_tree_after_grade": result_after_grade,
                       "original_source_hashes_before_grade": original_hashes_before_grade,
                       "original_source_hashes_after_grade": original_hashes_after_grade,
                       "measurement_id": claim.measurement_id,
                       "source_kind": claim.source_kind, "binding_kind": claim.binding_kind,
                       "grade": {"Q": quality, "T": trust, "reasons": reasons},
                       "new_grade_authored": False}, handle, indent=2, sort_keys=True)
            handle.write("\n")
        metric = receipt.get("fixture_execution_conformant")
        grade_ok = (quality, trust) == ("Judged", "Located")
        passed = code == 0 and metric is True and cases_ok and grade_ok
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (code or 1),
                      native_metric=metric, junit_counts=counts, exact_case_set=cases_ok,
                      expected_case_count=len(expected_cases),
                      shared_grade={"Q": quality, "T": trust, "accepted": grade_ok,
                                    "original_native_receipt": True})
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
