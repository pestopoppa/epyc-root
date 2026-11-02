"""Capture the bounded INF-41 S-20 server-only fallback source controls."""
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
import stat
import sys
import tomllib

APP_PIN = "ee345dc972ef4e798841aad41a141f649482ed35"
ROOT_SOURCE_PIN = "94e7d72a8448c3b77189b77dbb5cdd5d4ccfadbc"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PYTHON_PIN = "3.13.15"
ROOT_TASK = "handoffs/active/multimodal-pipeline.md"
ROOT_TASK_SHA256 = "3b017b8af7d501e61c6d781013609c88e7dda8e356bb0afe6c30439430953525"
ROOT_TASK_BLOB = "76cc1c6b3e33c9c3ccf615559a0af3c349e818b9"
ROOT_VB_TABLE = "scripts/vidya/adapters/README.md"
ROOT_VB_TABLE_SHA256 = "6d40b265db904c89994b97ed52f404409360c1a5aad67cd7798eb24e1ad61a8e"
ROOT_VB_TABLE_BLOB = "3703b0d6afb743f61caec421b6f3a91132067ab1"
APP_LOCK = "uv.lock"
APP_LOCK_SHA256 = "7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3"
TEST_FILE = "tests/unit/test_chat_vision.py"
SOURCE_FILE = "src/api/routes/chat_vision.py"
EXPECTED_CASES = "scripts/ci/ni08_inf41_s20_expected_cases.json"
REQUIREMENTS = "scripts/ci/ni08_inf41_s20_requirements.txt"
WORKFLOW = ".github/workflows/ni08-inf41-s20-capture.yml"
RUNNER = "scripts/ci/ni08_inf41_s20_capture.py"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-inf41-s20/venv" && '
    '"$RUNNER_TEMP/ni08-inf41-s20/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r "
    "recipe/scripts/ci/ni08_inf41_s20_requirements.txt"
)
RUNNER_CONTEXT = "ubuntu-24.04"
EXECUTION_CONTEXT = "pytest-chat-vision-server-only-fallback-source-controls-no-inference"
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
                "requirements.txt", "requirements-dev.txt", "requirements-test.txt"}
APP_DATA_FILES = (
    "orchestration/model_registry.yaml",
    "orchestration/tool_registry.yaml",
)
CARRIER_READS = (
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/canonical.py",
)
CASE_IDENTITIES = (
    ("tests.unit.test_chat_vision.TestHandleVisionRequest",
     "test_server_only_refuses_without_legacy_vision_request[server-False]"),
    ("tests.unit.test_chat_vision.TestHandleVisionRequest",
     "test_server_only_refuses_without_legacy_vision_request[auto-True]"),
    ("tests.unit.test_chat_vision.TestHandleVisionRequest",
     "test_server_only_refuses_without_legacy_vision_request[cli-True]"),
    ("tests.unit.test_chat_vision.TestHandleVisionRequest",
     "test_server_only_refuses_without_legacy_vision_request[malformed-True]"),
    ("tests.unit.test_chat_vision.TestHandleVisionRequest",
     "test_server_only_refuses_without_legacy_vision_request[None-True]"),
)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def require_clean(repo: Path, label: str) -> str:
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"{label} checkout has tracked changes")
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
        if entry and (entry.endswith(".py") or PurePosixPath(entry).name in CONFIG_NAMES):
            paths.append(regular_repo_file(repo, entry))
    return paths


def requirement_closure(requirements: Path, app: Path) -> dict[str, str]:
    lock_path = regular_repo_file(app, APP_LOCK)
    if hashlib.sha256(lock_path.read_bytes()).hexdigest() != APP_LOCK_SHA256:
        raise RuntimeError("APP uv.lock differs from reviewed pin")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    locked = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    versions: dict[str, str] = {}
    declared: dict[str, set[str]] = {}
    current = None
    for line in requirements.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^\\\s]+)", line.strip())
        if match:
            current = match.group(1).lower().replace("_", "-")
            versions[current] = match.group(2)
            declared[current] = set()
        if current:
            declared[current].update(re.findall(r"--hash=sha256:([0-9a-f]{64})", line))
    if not versions:
        raise RuntimeError("locked requirements are empty")
    for name, version in versions.items():
        record = locked.get(name)
        if not record or record["version"] != version:
            raise RuntimeError(f"{name} differs from pinned APP uv.lock")
        wheel_hashes = {item["hash"].removeprefix("sha256:") for item in record.get("wheels", [])}
        if not wheel_hashes or declared[name] != wheel_hashes:
            raise RuntimeError(f"requirements do not bind all APP wheel hashes for {name}")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from locked version")
    return versions


def native_files(directory: Path) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("native evidence tree is missing, non-directory, or symlinked")
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"native evidence tree contains a symlink: {path}")
        if path.is_dir():
            continue
        if not path.is_file() or not stat.S_ISREG(path.lstat().st_mode):
            raise RuntimeError(f"native evidence tree contains a nonregular entry: {path}")
        files.append(path)
    return files


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


def manifest_digest(manifest: dict[str, str]) -> str:
    data = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def result_tree_manifest(root: Path) -> dict[str, str]:
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode):
        raise RuntimeError(f"result root is missing, not a directory, or symlinked: {root}")
    found: dict[str, str] = {".": "directory"}

    def walk(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name):
            path = Path(entry.path)
            mode = entry.stat(follow_symlinks=False).st_mode
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                raise RuntimeError(f"result tree contains a symlink: {path}")
            if stat.S_ISDIR(mode):
                found[relative + "/"] = "directory"
                walk(path)
            elif stat.S_ISREG(mode):
                found[relative] = hash_regular(path)
            else:
                raise RuntimeError(f"result tree contains a special file: {path}")

    walk(root)
    return found


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app, root_source = (workspace / name for name in
                                         ("recipe", "carrier", "app", "root-source"))
    result = runner_temp / "ni08-inf41-s20" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result.parent / "status.json"
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        expected_env = {
            "INF41_RUNNER_CONTEXT": RUNNER_CONTEXT,
            "INF41_EXECUTION_CONTEXT": EXECUTION_CONTEXT,
            "INF41_INSTALL_COMMAND": INSTALL_COMMAND,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": str(
                runner_temp / "ni08-inf41-s20" / "absent" / "cpu"),
            "ORCHESTRATOR_PATHS_LLAMA_MTMD": str(
                runner_temp / "ni08-inf41-s20" / "absent" / "llama-mtmd-cli"),
            "ORCHESTRATOR_PATHS_LLAMA_SERVER": str(
                runner_temp / "ni08-inf41-s20" / "absent" / "llama-server"),
        }
        for key, value in expected_env.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from reviewed recipe")
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        expected_venv = (runner_temp / "ni08-inf41-s20" / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected_venv:
            raise RuntimeError("capture interpreter is not the reviewed isolated venv")

        pins = {"recipe": require_clean(recipe, "recipe"),
                "carrier": require_clean(carrier, "carrier"),
                "app": require_clean(app, "app"),
                "root_source": require_clean(root_source, "root-source")}
        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER_PIN,
                         "app": APP_PIN, "root_source": ROOT_SOURCE_PIN}
        if pins != expected_pins:
            raise RuntimeError("checked-out repository pins differ from reviewed values")
        for key, value in (("APP_PIN", APP_PIN), ("ROOT_SOURCE_PIN", ROOT_SOURCE_PIN),
                           ("ROOT_CARRIER_PIN", CARRIER_PIN)):
            if os.environ.get(key) != value:
                raise RuntimeError(f"workflow {key} differs from reviewed pin")

        workflow = regular_repo_file(recipe, WORKFLOW)
        runner = regular_repo_file(recipe, RUNNER)
        manifest_path = regular_repo_file(recipe, EXPECTED_CASES)
        requirements_path = regular_repo_file(recipe, REQUIREMENTS)
        task_path = regular_repo_file(root_source, ROOT_TASK)
        table_path = regular_repo_file(root_source, ROOT_VB_TABLE)
        if hashlib.sha256(task_path.read_bytes()).hexdigest() != ROOT_TASK_SHA256:
            raise RuntimeError("ROOT S-20 task bytes differ from reviewed identity")
        if hashlib.sha1(b"blob %d\0" % len(task_path.read_bytes()) + task_path.read_bytes()).hexdigest() != ROOT_TASK_BLOB:
            raise RuntimeError("ROOT S-20 task Git blob differs from reviewed identity")
        if hashlib.sha256(table_path.read_bytes()).hexdigest() != ROOT_VB_TABLE_SHA256:
            raise RuntimeError("ROOT source table bytes differ from reviewed identity")
        if hashlib.sha1(b"blob %d\0" % len(table_path.read_bytes()) + table_path.read_bytes()).hexdigest() != ROOT_VB_TABLE_BLOB:
            raise RuntimeError("ROOT source table Git blob differs from reviewed identity")

        test_path = regular_repo_file(app, TEST_FILE)
        source_path = regular_repo_file(app, SOURCE_FILE)
        if hashlib.sha256(test_path.read_bytes()).hexdigest() != "5a877f05add279516fe313c25536a6a35032aff2e506a5a9b41315dd3f1dd6a2":
            raise RuntimeError("APP test bytes differ from reviewed source pin")
        if hashlib.sha256(source_path.read_bytes()).hexdigest() != "4230bee86a02a11dad7b9be02a8e13ec8a55f553bc02dffa91dbf0f8130a4bde":
            raise RuntimeError("APP route bytes differ from reviewed source pin")
        lock_path = regular_repo_file(app, APP_LOCK)
        packages = requirement_closure(requirements_path, app)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_cases = [(case["classname"], case["name"]) for case in manifest.get("cases", [])]
        if (manifest.get("app_commit") != APP_PIN or manifest.get("count") != len(CASE_IDENTITIES)
                or tuple(expected_cases) != CASE_IDENTITIES or len(set(expected_cases)) != len(expected_cases)):
            raise RuntimeError("static five-case manifest is incomplete or drifted")
        if manifest.get("test_file_sha256") != hashlib.sha256(test_path.read_bytes()).hexdigest():
            raise RuntimeError("case manifest test source hash mismatch")
        if manifest.get("source_file_sha256") != hashlib.sha256(source_path.read_bytes()).hexdigest():
            raise RuntimeError("case manifest route source hash mismatch")

        app_context = tracked_source_context(app)
        app_inputs = [regular_repo_file(app, name) for name in APP_DATA_FILES]
        recipe_context = tracked_source_context(recipe)
        carrier_reads = [regular_repo_file(carrier, name) for name in CARRIER_READS]
        pip_freeze = result / "pip-freeze.txt"
        pip_freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        install_log = result / "dependency-install.log"
        if not install_log.is_file() or install_log.is_symlink():
            raise RuntimeError("dependency installer log is missing/nonregular")
        environment_path = result / "environment.json"
        environment_path.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "runner_context": RUNNER_CONTEXT, "execution_context": EXECUTION_CONTEXT,
            "install_command": INSTALL_COMMAND,
            "requirements_sha256": hashlib.sha256(requirements_path.read_bytes()).hexdigest(),
            "dependency_install_log_sha256": hashlib.sha256(install_log.read_bytes()).hexdigest(),
            "dependency_lock": {"repo": "app", "path": APP_LOCK,
                                "sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest()},
            "dependency_packages": packages,
            "expected_case_count": len(CASE_IDENTITIES),
            "expected_case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "expected_junit_identities": [{"classname": c, "name": n} for c, n in CASE_IDENTITIES],
            "root_task": {"repo": "root_source", "path": ROOT_TASK, "git_blob": ROOT_TASK_BLOB,
                          "sha256": ROOT_TASK_SHA256},
            "root_vb_table": {"repo": "root_source", "path": ROOT_VB_TABLE,
                              "git_blob": ROOT_VB_TABLE_BLOB, "sha256": ROOT_VB_TABLE_SHA256},
            "source_context_counts": {"recipe": len(recipe_context), "app": len(app_context)},
            "app_explicit_runtime_inputs": APP_DATA_FILES,
            "isolation": "Only five explicit server-only fallback controls; test replaces HTTP/OCR clients, performs no CLI/model call, and forbids live vision endpoints. No inference, live service, or latency acceptance.",
            "pytest_plugins": ["pytest_asyncio.plugin"], "conftest_autoload": "disabled",
            "bytecode_writes": "disabled", "python_hash_seed": "0",
            "kernel_path_overrides": {
                key: expected_env[key] for key in (
                    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN",
                    "ORCHESTRATOR_PATHS_LLAMA_MTMD",
                    "ORCHESTRATOR_PATHS_LLAMA_SERVER",
                )
            },
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit = result / "original-junit.xml"
        native = result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite native capture outputs")
        read_paths = [workflow, runner, manifest_path, requirements_path, task_path, table_path,
                      *recipe_context, *app_context, *app_inputs, *carrier_reads, lock_path,
                      test_path, source_path, install_log, pip_freeze, environment_path]
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
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(app), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
                    "--repo", f"app={app}", "--repo", f"root_source={root_source}"]
        for input_path in dict.fromkeys(path.resolve() for path in read_paths):
            producer.extend(["--read-path", str(input_path)])
        for classname, name in CASE_IDENTITIES:
            producer.extend(["--select", f"{classname}::{name}"])
        confcut = runner_temp / "ni08-inf41-s20" / "empty-conf"
        confcut.mkdir(parents=True, exist_ok=True)
        node_id = f"{TEST_FILE}::TestHandleVisionRequest::test_server_only_refuses_without_legacy_vision_request"
        command = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--rootdir", str(app),
                   "--noconftest", "-o", "addopts=", "-p", "no:cacheprovider",
                   "-p", "pytest_asyncio.plugin", "--asyncio-mode=auto", "-q", node_id,
                   f"--junitxml={junit}"]
        status.update(state="running", repositories=pins, selection=node_id,
                      expected_case_count=len(CASE_IDENTITIES))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        capture_env = dict(os.environ, PYTHONPATH=str(app),
                           ORCHESTRATOR_PATHS_PROJECT_ROOT=str(app),
                           ORCHESTRATOR_PATHS_REGISTRY_PATH=str(app / "orchestration/model_registry.yaml"),
                           ORCHESTRATOR_PATHS_TOOL_REGISTRY_PATH=str(app / "orchestration/tool_registry.yaml"),
                           ORCHESTRATOR_PATHS_STACK_PRIORS_PATH=str(app / "orchestration/derived/stack_priors.yaml"))
        code = subprocess.call([*producer, "--", *command], cwd=app, env=capture_env)
        producer_inputs_after = file_manifest(read_paths)
        if producer_inputs_after != producer_inputs_before:
            raise RuntimeError("producer inputs changed during native capture")
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1,
                          diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        cases = summary.get("cases") or []
        identities = [(row.get("classname"), row.get("name")) for row in cases]
        cases_ok = (counts.get("collected") == 5 and counts.get("executed") == 5
                    and counts.get("skipped") == 0 and counts.get("failure") == 0
                    and counts.get("error") == 0 and len(identities) == 5
                    and len(set(identities)) == 5
                    and Counter(identities) == Counter(CASE_IDENTITIES))

        original_native = native_files(native)
        original_names = [path.relative_to(native).as_posix() for path in original_native]
        originals = [*original_native, junit, pip_freeze, environment_path, install_log, requirements_path]
        before = file_manifest(originals)
        tree_before = result_tree_manifest(result)
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("original native receipt did not project to exactly one conformance row")
        claim = project_ci_conformance(rows[0])
        q, t, reasons = grade(claim)
        producer_inputs_after_grade = file_manifest(read_paths)
        if producer_inputs_after_grade != producer_inputs_before:
            raise RuntimeError("producer inputs changed during shared-grade analysis")
        after_native = native_files(native)
        after_names = [path.relative_to(native).as_posix() for path in after_native]
        after_paths = [*after_native, junit, pip_freeze, environment_path, install_log, requirements_path]
        after = file_manifest(after_paths)
        if before != after or original_names != after_names:
            raise RuntimeError("shared-grade analysis changed original capture inputs or membership")
        tree_after = result_tree_manifest(result)
        if tree_before != tree_after:
            raise RuntimeError("shared-grade analysis changed full result-tree membership or bytes")
        grade_path = result / "shared-grade.json"
        with grade_path.open("x", encoding="utf-8") as handle:
            json.dump({"kind": "analysis_of_existing_fixture_receipt", "fixture_rerun": False,
                       "new_native_receipt_authored_by_analysis": False, "repositories": pins,
                       "original_before_sha256": before, "original_after_sha256": after,
                       "result_tree_before_sha256": tree_before,
                       "result_tree_after_sha256": tree_after,
                       "producer_input_count": len(producer_inputs_before),
                       "producer_input_sha256_before": manifest_digest(producer_inputs_before),
                       "producer_input_sha256_after": manifest_digest(producer_inputs_after_grade),
                       "measurement_id": claim.measurement_id, "source_kind": claim.source_kind,
                       "binding_kind": claim.binding_kind,
                       "grade": {"Q": q, "T": t, "reasons": reasons}},
                      handle, indent=2, sort_keys=True)
            handle.write("\n")
        grade_ok = q == "Judged" and t == "Located"
        passed = code == 0 and metric is True and cases_ok and grade_ok
        status.update(state="passed" if passed else "failed", exit_code=0 if passed else (code or 1),
                      native_metric=metric, junit_counts=counts, expected_case_count=5,
                      all_cases_executed=cases_ok, shared_grade_acceptance=grade_ok,
                      shared_grade={"Q": q, "T": t, "reasons": reasons})
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
