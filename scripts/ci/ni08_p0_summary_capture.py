"""Capture the four offline HS-19d.P0 descriptive-summary controls natively."""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import tomllib

APP_PIN = "224fbf991f7b68aa6466ecbaf829a336c20d5f5c"
ROOT_SOURCE_PIN = "4295ff6255576d97822661857990b89087e3bcd9"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PYTHON_PIN = "3.13.15"
ROOT_TASK = "handoffs/active/harness-selection-and-integration.md"
ROOT_TASK_SHA256 = "34cdeb153c28ff730af0702b2753309c3b1a3407e15431c61ab5a897b284c2c7"
ROOT_VB_TABLE = "scripts/vidya/adapters/README.md"
ROOT_VB_TABLE_SHA256 = "d7fc2995af0003a38c93c15a4676a61599cc1df47e9dc4ff0a3852b9e8deb474"
ROOT_VERDICT = "artifacts/harness/hs19a-20260927/verdict.json"
ROOT_VERDICT_SHA256 = "7b6b8eedbd316b947529022839471602059dc807d9b9b4105732f7f606ef29f6"
ROOT_VERDICT_BLOB = "1d7f109f153333b34a5a0eb455546d572dd2240a"
APP_LOCK = "uv.lock"
APP_LOCK_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
TEST_FILE = "tests/unit/test_hs19d_p0_descriptive_summary.py"
SOURCE_FILE = "scripts/harness_p0/hs19d_p0_summary.py"
EXPECTED_CASES = "scripts/ci/ni08_p0_summary_expected_cases.json"
REQUIREMENTS = "scripts/ci/ni08_p0_summary_requirements.txt"
WORKFLOW = ".github/workflows/ni08-p0-descriptive-summary-capture.yml"
RUNNER = "scripts/ci/ni08_p0_summary_capture.py"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-p0-summary/venv" && '
    '"$RUNNER_TEMP/ni08-p0-summary/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r "
    "recipe/scripts/ci/ni08_p0_summary_requirements.txt"
)
RUNNER_CONTEXT = "ubuntu-24.04"
EXECUTION_CONTEXT = "pytest-pinned-verdict-summary-no-inference"
LOCKED_PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3",
}
CASE_IDENTITIES = (
    ("tests.unit.test_hs19d_p0_descriptive_summary", "test_summary_projects_counts_without_exporting_private_detail_or_claims"),
    ("tests.unit.test_hs19d_p0_descriptive_summary", "test_missing_count_is_unknown_not_zero_and_failed_summary_is_not_promoted"),
    ("tests.unit.test_hs19d_p0_descriptive_summary", "test_pinned_source_loader_refuses_byte_drift_and_symlink"),
    ("tests.unit.test_hs19d_p0_descriptive_summary", "test_actual_pinned_root_verdict_projects_only_sanitized_counts"),
)
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
CARRIER_READS = (
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/canonical.py",
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"{label} checkout is not clean")
    return git(repo, "rev-parse", "HEAD")


def regular_repo_file(repo: Path, relative: str) -> Path:
    path = repo
    for part in PurePosixPath(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared input traverses symlink: {relative}")
    if not path.is_file():
        raise RuntimeError(f"declared input missing or nonregular: {relative}")
    mode = git(repo, "ls-tree", "HEAD", "--", relative).split(maxsplit=1)
    if not mode or mode[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a tracked regular file: {relative}")
    return path.absolute()


def tracked_source_context(repo: Path) -> list[Path]:
    paths = []
    for entry in git(repo, "ls-files", "-z").split("\0"):
        if not entry:
            continue
        name = PurePosixPath(entry).name
        if entry.endswith(".py") or name in CONFIG_NAMES:
            paths.append(regular_repo_file(repo, entry))
    return paths


def verify_requirements(app: Path, requirements: Path) -> None:
    lock_path = regular_repo_file(app, APP_LOCK)
    if hashlib.sha256(lock_path.read_bytes()).hexdigest() != APP_LOCK_SHA256:
        raise RuntimeError("APP uv.lock differs from the reviewed pin")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    locked = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    text = requirements.read_text(encoding="utf-8")
    declared: dict[str, set[str]] = {}
    current = None
    versions = {}
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", stripped)
        if match:
            current = match.group(1).lower().replace("_", "-")
            versions[current] = match.group(2)
            declared[current] = set()
        if current:
            declared[current].update(re.findall(r"--hash=sha256:([0-9a-f]{64})", stripped))
    if versions != LOCKED_PACKAGES:
        raise RuntimeError("requirements package/version set differs from reviewed five-package closure")
    for name, version in LOCKED_PACKAGES.items():
        record = locked.get(name)
        if not record or record["version"] != version:
            raise RuntimeError(f"{name} differs from the pinned APP uv.lock")
        wheel_hashes = {item["hash"].removeprefix("sha256:") for item in record.get("wheels", [])}
        if not wheel_hashes or declared.get(name) != wheel_hashes:
            raise RuntimeError(f"requirements do not bind the complete APP wheel set for {name}")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from the reviewed pin")


def native_files(directory: Path) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*") if path.is_file() and not path.is_symlink())


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app, root_source = (workspace / name for name in
                                         ("recipe", "carrier", "app", "root-source"))
    result = runner_temp / "ni08-p0-summary" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        expected_env = {
            "P0_RUNNER_CONTEXT": RUNNER_CONTEXT,
            "P0_EXECUTION_CONTEXT": EXECUTION_CONTEXT,
            "P0_INSTALL_COMMAND": INSTALL_COMMAND,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        for key, expected in expected_env.items():
            if os.environ.get(key) != expected:
                raise RuntimeError(f"{key} differs from reviewed recipe")
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        expected_venv = (runner_temp / "ni08-p0-summary" / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected_venv:
            raise RuntimeError("capture interpreter is not the reviewed isolated venv")

        pins = {
            "recipe": require_clean(recipe, "recipe"),
            "carrier": require_clean(carrier, "carrier"),
            "app": require_clean(app, "app"),
            "root_source": require_clean(root_source, "root-source"),
        }
        expected_pins = {
            "recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER_PIN,
            "app": APP_PIN, "root_source": ROOT_SOURCE_PIN,
        }
        if pins != expected_pins:
            raise RuntimeError("checked-out repository pins differ from the reviewed values")
        for key, value in (("APP_PIN", APP_PIN), ("ROOT_SOURCE_PIN", ROOT_SOURCE_PIN),
                           ("ROOT_CARRIER_PIN", CARRIER_PIN)):
            if os.environ.get(key) != value:
                raise RuntimeError(f"workflow {key} differs from reviewed pin")

        root_env = os.environ.get("HS19D_ROOT_CHECKOUT")
        if not root_env or Path(root_env).resolve() != root_source.resolve():
            raise RuntimeError("HS19D_ROOT_CHECKOUT does not point to the separately pinned ROOT checkout")
        root_verdict = regular_repo_file(root_source, ROOT_VERDICT)
        verdict_bytes = root_verdict.read_bytes()
        git_blob = hashlib.sha1(f"blob {len(verdict_bytes)}\0".encode("ascii") + verdict_bytes).hexdigest()
        if hashlib.sha256(verdict_bytes).hexdigest() != ROOT_VERDICT_SHA256 or git_blob != ROOT_VERDICT_BLOB:
            raise RuntimeError("pinned ROOT verdict artifact differs from reviewed Git blob/SHA256")

        workflow = regular_repo_file(recipe, WORKFLOW)
        runner = regular_repo_file(recipe, RUNNER)
        manifest_path = regular_repo_file(recipe, EXPECTED_CASES)
        requirements = regular_repo_file(recipe, REQUIREMENTS)
        task_path = regular_repo_file(recipe, ROOT_TASK)
        table_path = regular_repo_file(recipe, ROOT_VB_TABLE)
        if hashlib.sha256(task_path.read_bytes()).hexdigest() != ROOT_TASK_SHA256:
            raise RuntimeError("ROOT P0 task text differs from the reviewed identity")
        if hashlib.sha256(table_path.read_bytes()).hexdigest() != ROOT_VB_TABLE_SHA256:
            raise RuntimeError("ROOT source table differs from the reviewed identity")

        test_path = regular_repo_file(app, TEST_FILE)
        source_path = regular_repo_file(app, SOURCE_FILE)
        if hashlib.sha256(test_path.read_bytes()).hexdigest() != "909197ee4ff423bff5b2b0d9e2d76c541b0eb9d1be9c78f86b1aff914c74b798":
            raise RuntimeError("APP test source differs from the reviewed source pin")
        if hashlib.sha256(source_path.read_bytes()).hexdigest() != "d8ddc15cf8e6e2fc21a984b8c929ab1b771282132df45fa79708518b3ae25045":
            raise RuntimeError("APP helper source differs from the reviewed source pin")
        verify_requirements(app, requirements)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_cases = [(case["classname"], case["name"]) for case in manifest.get("cases", [])]
        if (manifest.get("app_commit") != APP_PIN or manifest.get("count") != 4
                or len(expected_cases) != 4 or len(set(expected_cases)) != 4
                or tuple(expected_cases) != CASE_IDENTITIES):
            raise RuntimeError("static four-case manifest is incomplete, duplicated, or drifted")
        if manifest.get("test_file_sha256") != hashlib.sha256(test_path.read_bytes()).hexdigest():
            raise RuntimeError("test manifest source hash mismatch")
        if manifest.get("source_file_sha256") != hashlib.sha256(source_path.read_bytes()).hexdigest():
            raise RuntimeError("source manifest helper hash mismatch")

        app_context = tracked_source_context(app)
        root_context = tracked_source_context(recipe)
        carrier_reads = [regular_repo_file(carrier, name) for name in CARRIER_READS]
        app_lock = regular_repo_file(app, APP_LOCK)
        pip_freeze = result / "pip-freeze.txt"
        pip_freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        install_log = result / "dependency-install.log"
        if install_log.is_symlink() or not install_log.is_file():
            raise RuntimeError("dependency installer log is missing or nonregular")
        environment_path = result / "environment.json"
        environment_path.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "runner_context": RUNNER_CONTEXT, "execution_context": EXECUTION_CONTEXT,
            "install_command": INSTALL_COMMAND,
            "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
            "dependency_install_log_sha256": hashlib.sha256(install_log.read_bytes()).hexdigest(),
            "dependency_lock": {"repo": "app", "path": APP_LOCK, "sha256": hashlib.sha256(app_lock.read_bytes()).hexdigest()},
            "dependency_set": LOCKED_PACKAGES,
            "expected_case_count": 4, "expected_case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "expected_junit_identities": [{"classname": cls, "name": name} for cls, name in CASE_IDENTITIES],
            "root_verdict": {"repo": "root_source", "path": ROOT_VERDICT, "git_blob": ROOT_VERDICT_BLOB, "sha256": ROOT_VERDICT_SHA256},
            "root_task": {"path": ROOT_TASK, "sha256": ROOT_TASK_SHA256},
            "root_vb_table": {"path": ROOT_VB_TABLE, "sha256": ROOT_VB_TABLE_SHA256},
            "source_context_counts": {"recipe": len(root_context), "app": len(app_context)},
            "isolation": "Four offline tests exercise only the pinned verdict projection and synthetic loader controls. The separately pinned ROOT checkout is read-only input. No model, endpoint, tap log, live probe, or inference is involved.",
            "pytest_plugin_autoload": "disabled", "bytecode_writes": "disabled", "python_hash_seed": "0",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit = result / "original-junit.xml"
        native = result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite capture outputs")
        read_paths = [workflow, runner, manifest_path, requirements, task_path, table_path,
                      *root_context, *app_context, *carrier_reads, root_verdict, app_lock,
                      test_path, source_path, install_log, pip_freeze, environment_path]
        producer = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(app), "--junit", str(junit), "--output", str(native),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
            "--repo", f"app={app}", "--repo", f"root_source={root_source}",
        ]
        for input_path in dict.fromkeys(path.resolve() for path in read_paths):
            producer.extend(["--read-path", str(input_path)])
        producer.extend(["--select", TEST_FILE])
        command = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(app),
                   "--noconftest", "-o", "addopts=",
                   "-p", "no:cacheprovider", "-q", TEST_FILE, f"--junitxml={junit}"]
        status.update(state="running", repositories=pins, selection=TEST_FILE, expected_cases=4)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        capture_env = dict(os.environ, HS19D_ROOT_CHECKOUT=str(root_source))
        code = subprocess.call([*producer, "--", *command], cwd=app, env=capture_env)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1, diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        case_rows = summary.get("cases") or []
        actual_cases = [(row.get("classname"), row.get("name")) for row in case_rows]
        cases_ok = (
            counts.get("collected") == 4 and counts.get("executed") == 4
            and counts.get("skipped") == 0 and counts.get("failure") == 0
            and counts.get("error") == 0 and len(actual_cases) == 4
            and len(set(actual_cases)) == 4
            and Counter(actual_cases) == Counter(CASE_IDENTITIES)
        )
        originals = [*native_files(native), junit, pip_freeze, environment_path, install_log, requirements]
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        sys.path.insert(0, str(carrier))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade

        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("original native receipt does not project to exactly one conformance row")
        claim = project_ci_conformance(rows[0])
        q, t, reasons = grade(claim)
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        if before != after:
            raise RuntimeError("shared-grade analysis changed an original capture input")
        grade_path = result / "shared-grade.json"
        with grade_path.open("x", encoding="utf-8") as handle:
            json.dump({
                "kind": "analysis_of_existing_fixture_receipt", "fixture_rerun": False,
                "new_native_receipt_authored_by_analysis": False, "repositories": pins,
                "original_before_sha256": before, "original_after_sha256": after,
                "measurement_id": claim.measurement_id, "source_kind": claim.source_kind,
                "binding_kind": claim.binding_kind, "grade": {"Q": q, "T": t, "reasons": reasons},
            }, handle, indent=2, sort_keys=True)
            handle.write("\n")
        grade_ok = q == "Judged" and t == "Located"
        passed = code == 0 and metric is True and cases_ok and grade_ok
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (code or 1),
                      native_metric=metric, junit_counts=counts, expected_case_count=4,
                      all_cases_executed=cases_ok, shared_grade_recorded=True,
                      shared_grade_acceptance=grade_ok,
                      shared_grade={"Q": q, "T": t, "reasons": reasons})
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
