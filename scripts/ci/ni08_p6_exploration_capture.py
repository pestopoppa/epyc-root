"""Capture HS-4 P6 source-control cases through the existing native CI carrier."""
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

APP_PIN = "10075e6cb559d7e8ce3e1f1251b4a63bc78ec2c8"
ROOT_BASE_PIN = "928a740464d041ece312b0f23c0dee5f31e891e6"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PYTHON_PIN = "3.13.15"
TASK = "handoffs/active/harness-selection-and-integration.md"
TASK_SHA256 = "34cdeb153c28ff730af0702b2753309c3b1a3407e15431c61ab5a897b284c2c7"
TABLE = "scripts/vidya/adapters/README.md"
TABLE_SHA256 = "139ef409529f02b987dcd4dbd850320d415ee073de1fd9aba9bdf444464b67e1"
CONTRACT = "docs/design/hs4-p6-shared-exploration-source-contract-20261006.md"
CONTRACT_SHA256 = "55a60effecef7f4bd3c5023080975282133f0bd2512cb41e4482c823b9a6c164"
APP_LOCK_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
APP_SOURCES = {
    "src/repl_environment/exploration_core.py": "4f203b7ab59ad6467ade8d5cd3540fb203ca9b047620749f36a780adbb0ad310",
    "src/repl_environment/file_exploration.py": "acbc97ce8bdf043f3c3d1762b004bb22a78e62fb2af0bdc7fa5ba35b423128db",
    "src/repl_environment/combined_ops.py": "1e14b56f56169eaa12eebc1f8906352ec04a424554b4133fe1f2c64c3834e0b5",
    "tests/unit/test_exploration_core.py": "1d91b96ac1210dc049300464fd775933beea2fbc928486fcaa2f1df16cbc9a01",
}
TEST_FILE = "tests/unit/test_exploration_core.py"
EXPECTED_CASES = "scripts/ci/ni08_p6_exploration_expected_cases.json"
REQUIREMENTS = "scripts/ci/ni08_p6_exploration_requirements.txt"
WORKFLOW = ".github/workflows/ni08-p6-exploration-capture.yml"
RUNNER = "scripts/ci/ni08_p6_exploration_capture.py"
RESULT_NAME = "ni08-p6-exploration"
RUNNER_CONTEXT = "ubuntu-24.04"
EXECUTION_CONTEXT = "hs4-p6-source-controls-no-catalog-or-inference"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-p6-exploration/venv" && '
    '"$RUNNER_TEMP/ni08-p6-exploration/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r "
    "recipe/scripts/ci/ni08_p6_exploration_requirements.txt"
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
CASE_IDENTITIES = tuple(
    ("tests.unit.test_exploration_core", name) for name in (
        "test_explicit_root_refuses_symlink_escape_and_file_size_overrun",
        "test_bounded_exploration_refuses_fifo_without_reading",
        "test_character_pages_keep_crlf_and_negative_offset_behavior",
        "test_grep_reports_true_total_and_keeps_bounded_matches",
        "test_legacy_options_preserve_long_lines_many_context_lines_and_splitlines",
        "test_unbounded_character_page_keeps_legacy_crlf_offsets",
        "test_regex_error_order_and_empty_pattern_options_are_explicit",
        "test_repl_grep_adapter_keeps_configured_count_full_lines_and_context",
        "test_peek_and_combined_adapters_keep_crlf_case_and_blank_context",
        "test_existing_request_scope_and_knowledge_fence_admission_stays_before_adapter_reads",
        "test_outline_and_line_range_are_read_only_bounded_views",
    )
)


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


def tracked_source_context(repo: Path) -> list[Path]:
    paths = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if name and (name.endswith(".py") or PurePosixPath(name).name in CONFIG_NAMES):
            paths.append(tracked_file(repo, name))
    return paths


def hash_regular_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"original evidence is missing, nonregular, or symlinked: {path}")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"original evidence is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_requirements(app: Path, requirements: Path) -> dict[str, str]:
    lock_path = tracked_file(app, "uv.lock")
    lock_bytes = lock_path.read_bytes()
    if hashlib.sha256(lock_bytes).hexdigest() != APP_LOCK_SHA256:
        raise RuntimeError("APP uv.lock differs from the reviewed dependency pin")
    lock = tomllib.loads(lock_bytes.decode("utf-8"))
    records = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    text = requirements.read_text(encoding="utf-8")
    versions: dict[str, str] = {}
    declared: dict[str, set[str]] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\s]+)", stripped)
        if match:
            current = match.group(1).lower().replace("_", "-")
            versions[current] = match.group(2)
            declared[current] = set()
        if current:
            declared[current].update(re.findall(r"--hash=sha256:([0-9a-f]{64})", stripped))
    if len(versions) != 48:
        raise RuntimeError("reviewed APP locked dependency closure must contain exactly 48 packages")
    for name, version in versions.items():
        row = records.get(name)
        if not row or row["version"] != version:
            raise RuntimeError(f"{name} version differs from APP uv.lock")
        allowed = {wheel["hash"].removeprefix("sha256:") for wheel in row.get("wheels", [])}
        if not allowed or declared.get(name) != allowed:
            raise RuntimeError(f"{name} wheel hashes differ from the complete APP-locked wheel set")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from the reviewed pin")
    return versions


def source_context(repo: Path) -> list[Path]:
    return [path for path in tracked_source_context(repo)]


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / label for label in ("recipe", "carrier", "app"))
    result = runner_temp / RESULT_NAME / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        expected_env = {
            "P6_RUNNER_CONTEXT": RUNNER_CONTEXT,
            "P6_EXECUTION_CONTEXT": EXECUTION_CONTEXT,
            "P6_INSTALL_COMMAND": INSTALL_COMMAND,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        for key, value in expected_env.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from the reviewed recipe")
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        expected_venv = (runner_temp / RESULT_NAME / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected_venv:
            raise RuntimeError("capture interpreter is not the reviewed isolated venv")

        pins = {"recipe": git(recipe, "rev-parse", "HEAD"),
                "carrier": git(carrier, "rev-parse", "HEAD"),
                "app": git(app, "rev-parse", "HEAD")}
        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER_PIN, "app": APP_PIN}
        for label, repo in (("recipe", recipe), ("carrier", carrier), ("app", app)):
            if pins[label] != expected_pins[label]:
                raise RuntimeError(f"{label} checkout differs from reviewed Git pin")
            if git(repo, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeError(f"{label} checkout is not clean")
        if git(recipe, "merge-base", "--is-ancestor", ROOT_BASE_PIN, "HEAD") != "":
            raise RuntimeError("ROOT recipe checkout is not descended from the reviewed ROOT source pin")
        if os.environ.get("APP_PIN") != APP_PIN or os.environ.get("ROOT_CARRIER_PIN") != CARRIER_PIN:
            raise RuntimeError("workflow APP or carrier pin differs")

        workflow = tracked_file(recipe, WORKFLOW)
        runner = tracked_file(recipe, RUNNER)
        manifest_path = tracked_file(recipe, EXPECTED_CASES)
        requirements = tracked_file(recipe, REQUIREMENTS)
        task_path = tracked_file(recipe, TASK)
        table_path = tracked_file(recipe, TABLE)
        contract_path = tracked_file(recipe, CONTRACT)
        if hashlib.sha256(task_path.read_bytes()).hexdigest() != TASK_SHA256:
            raise RuntimeError("ROOT HS-4 task bytes differ from reviewed source")
        if hashlib.sha256(table_path.read_bytes()).hexdigest() != TABLE_SHA256:
            raise RuntimeError("ROOT source-table bytes differ from reviewed enrollment")
        if hashlib.sha256(contract_path.read_bytes()).hexdigest() != CONTRACT_SHA256:
            raise RuntimeError("ROOT P6 source contract differs from reviewed bytes")
        if hashlib.sha256(requirements.read_bytes()).hexdigest() != "d01fcf5418bdf185397dca1b049abcc16463d410f0943125b8d6fd2d8ced1404":
            raise RuntimeError("hash-locked dependency requirements differ from reviewed file")

        test_path = tracked_file(app, TEST_FILE)
        source_paths = {name: tracked_file(app, name) for name in APP_SOURCES}
        for name, path in source_paths.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != APP_SOURCES[name]:
                raise RuntimeError(f"APP source differs from reviewed hash: {name}")
        package_versions = verify_requirements(app, requirements)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = [(item.get("classname"), item.get("name")) for item in manifest.get("cases", [])]
        tree = ast.parse(test_path.read_text(encoding="utf-8"), filename=TEST_FILE)
        ast_tests = [(CASE_IDENTITIES[0][0], node.name) for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
        if (manifest.get("source_commit") != APP_PIN or manifest.get("test_file") != TEST_FILE
                or manifest.get("test_file_sha256") != APP_SOURCES[TEST_FILE]
                or manifest.get("count") != len(CASE_IDENTITIES)
                or tuple(expected) != CASE_IDENTITIES or Counter(ast_tests) != Counter(CASE_IDENTITIES)):
            raise RuntimeError("static selected-case identities differ from source AST or reviewed manifest")

        install_log = result / "dependency-install.log"
        if install_log.is_symlink() or not install_log.is_file():
            raise RuntimeError("dependency installer log is missing or nonregular")
        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "root_base_pin": ROOT_BASE_PIN, "runner_context": RUNNER_CONTEXT,
            "execution_context": EXECUTION_CONTEXT, "install_command": expected_env["P6_INSTALL_COMMAND"],
            "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
            "dependency_lock_sha256": hashlib.sha256(tracked_file(app, "uv.lock").read_bytes()).hexdigest(),
            "dependency_install_log_sha256": hashlib.sha256(install_log.read_bytes()).hexdigest(),
            "dependency_versions": package_versions, "expected_case_count": len(CASE_IDENTITIES),
            "expected_case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "task": {"path": TASK, "sha256": TASK_SHA256},
            "source_table": {"path": TABLE, "sha256": TABLE_SHA256},
            "source_contract": {"path": CONTRACT, "sha256": CONTRACT_SHA256},
            "pytest_plugin_autoload": "disabled", "bytecode_writes": "disabled", "python_hash_seed": "0",
            "isolation": "Synthetic temporary-file controls exercise bounded reads and existing REPL adapters. The request-scope control uses a fake REPL instance with the actual REPLEnvironment path-admission method; external fence response is a fixture sentinel. No MCP registration/catalog edit, live search, model, endpoint, GPU, or inference is exercised.",
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        junit = result / "original-junit.xml"
        native = result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite native outputs")
        app_context = source_context(app)
        recipe_context = source_context(recipe)
        carrier_inputs = [tracked_file(carrier, path) for path in CARRIER_READS]
        read_paths = [workflow, runner, manifest_path, requirements, task_path, table_path, contract_path,
                      *recipe_context, *app_context, *carrier_inputs, *source_paths.values(),
                      tracked_file(app, "uv.lock"), install_log, freeze, environment]
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(app), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"app={app}"]
        for path in dict.fromkeys(item.resolve() for item in read_paths):
            producer.extend(("--read-path", str(path)))
        producer.extend(("--select", TEST_FILE))
        command = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(app),
                   "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider", "-q",
                   TEST_FILE, f"--junitxml={junit}"]
        status.update(state="running", repositories=pins, selected_test_count=len(CASE_IDENTITIES))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        capture_env = dict(os.environ, PYTHONPATH=str(app))
        exit_code = subprocess.call([*producer, "--", *command], cwd=app, env=capture_env)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=exit_code or 1,
                          diagnostic="native carrier did not produce a receipt")
            return exit_code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        rows = summary.get("cases") or []
        actual = [(row.get("classname"), row.get("name")) for row in rows]
        cases_ok = (Counter(actual) == Counter(CASE_IDENTITIES) and len(actual) == len(CASE_IDENTITIES)
                    and counts.get("collected") == len(CASE_IDENTITIES)
                    and counts.get("executed") == len(CASE_IDENTITIES)
                    and counts.get("skipped") == 0 and counts.get("failure") == 0 and counts.get("error") == 0)
        explicit_originals = [*read_paths, install_log, freeze, environment, junit, receipt_path]

        def original_paths() -> list[Path]:
            native_originals = list(native.rglob("*"))
            if any(path.is_symlink() for path in native_originals):
                raise RuntimeError("native output tree contains a symlink")
            return list(dict.fromkeys([
                *explicit_originals, *(path for path in native_originals if path.is_file())
            ]))

        original_inputs = original_paths()
        originals_before = {str(path): hash_regular_file(path) for path in original_inputs}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        projected_rows = native_rows(receipt_path)
        if len(projected_rows) != 1:
            raise RuntimeError("original native receipt projection is not unique")
        claim = project_ci_conformance(projected_rows[0])
        quality, trust, reasons = grade(claim)
        original_inputs_after = original_paths()
        originals_after = {str(path): hash_regular_file(path) for path in original_inputs_after}
        if [str(path) for path in original_inputs_after] != [str(path) for path in original_inputs]:
            raise RuntimeError("shared-grade analysis changed original evidence membership")
        if originals_after != originals_before:
            raise RuntimeError("shared-grade analysis changed an original input or native output")
        with (result / "shared-grade.json").open("x", encoding="utf-8") as handle:
            json.dump({
                "kind": "analysis_of_existing_native_receipt",
                "original_hashes_before": originals_before,
                "original_hashes_after": originals_after,
                "measurement_id": claim.measurement_id,
                "source_kind": claim.source_kind,
                "binding_kind": claim.binding_kind,
                "grade": {"Q": quality, "T": trust, "reasons": reasons},
                "new_grade_authored": False,
            }, handle, indent=2, sort_keys=True)
            handle.write("\n")
        grade_ok = (quality, trust) == ("Judged", "Located")
        metric = receipt.get("fixture_execution_conformant")
        passed = exit_code == 0 and metric is True and cases_ok and grade_ok
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (exit_code or 1),
                      native_fixture_conformance=metric, junit_counts=counts,
                      exact_case_set=cases_ok, expected_case_count=len(CASE_IDENTITIES),
                      shared_grade={"Q": quality, "T": trust, "accepted": grade_ok,
                                    "original_native_receipt": True})
        return 0 if passed else (exit_code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
