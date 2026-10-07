"""Capture the two work-payload bound source modules through the unchanged native carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import ast
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
from collections import Counter

APP_PIN = "926d90c95ca452636d59b7edd343abd8bcae81d2"
CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PACKAGES = {
    "annotated-doc": "0.0.4", "annotated-types": "0.7.0", "anyio": "4.13.0",
    "attrs": "26.1.0", "certifi": "2026.2.25", "charset-normalizer": "3.4.7",
    "faiss-cpu": "1.13.2", "fastapi": "0.135.3", "h11": "0.16.0",
    "httpcore": "1.0.9", "httpx": "0.28.1", "idna": "3.11",
    "iniconfig": "2.3.0", "jsonpatch": "1.33", "jsonpointer": "3.1.1",
    "jsonschema": "4.26.0", "jsonschema-specifications": "2025.9.1",
    "langchain-core": "1.2.28", "langgraph": "1.1.6",
    "langgraph-checkpoint": "4.0.1", "langgraph-prebuilt": "1.0.9",
    "langgraph-sdk": "0.3.13", "langsmith": "0.7.30", "logfire-api": "4.32.0",
    "numpy": "2.4.4", "orjson": "3.11.8", "ormsgpack": "1.12.2",
    "packaging": "26.0", "pluggy": "1.6.0", "pydantic": "2.13.0",
    "pydantic-core": "2.46.0", "pydantic-graph": "1.80.0", "pygments": "2.20.0",
    "pytest": "9.0.3", "pyyaml": "6.0.3", "python-multipart": "0.0.26",
    "referencing": "0.37.0",
    "requests": "2.33.1", "requests-toolbelt": "1.0.0", "rpds-py": "0.30.0",
    "scipy": "1.17.1", "starlette": "1.0.0", "tenacity": "9.1.4",
    "typing-extensions": "4.15.0", "typing-inspection": "0.4.2",
    "urllib3": "2.6.3", "uuid-utils": "0.14.1", "xxhash": "3.6.0",
    "zstandard": "0.25.0",
}
INSTALL_REQUIREMENTS = "scripts/ci/m11_work_cap_requirements.txt"
INSTALL = (
    'python -m venv "$RUNNER_TEMP/m11-work-cap/venv" && '
    '"$RUNNER_TEMP/m11-work-cap/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r recipe/scripts/ci/m11_work_cap_requirements.txt"
)
CONFIG_NAMES = {"pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
                "requirements.txt", "requirements-dev.txt", "requirements-test.txt"}
APP_CONFIG_EXTRAS = (
    "orchestration/model_registry.yaml",
    "orchestration/model_descriptors.yaml",
    "orchestration/derived/stack_priors.yaml",
    "orchestration/derived/duration_baselines_by_role.json",
    "orchestration/workload_model.yaml",
)
ROOT_SOURCE_PIN = "0da62ca1cb484f54f0e58dc514f10cd61b9ac001"
ROOT_TASK = "handoffs/active/episodic-memory-integrity.md"
ROOT_TASK_SHA256 = "2a871cf1e187ec1355e8a1edd221a777acfe53013ac2c1973fae6d7137cd0721"
ROOT_VB_TABLE = "scripts/vidya/adapters/README.md"
ROOT_VB_TABLE_SHA256 = "037fd24d69fb2f541fa7eae5bc40ae95f10075e00d60d7267950789c91d169e3"
TEST_FILES = (
    "tests/unit/test_memory_record.py",
    "tests/unit/test_episodic_work_payload.py",
)
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


def regular_file(repo: Path, relative: str) -> Path:
    path = repo
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared input traverses symlink: {relative}")
    if not path.is_file():
        raise RuntimeError(f"declared input missing or nonregular: {relative}")
    row = git(repo, "ls-tree", "HEAD", "--", relative).split("\t", 1)[0].split()
    if not row or row[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a tracked regular Git file: {relative}")
    return path.absolute()


def output_file(directory: Path, name: str) -> Path:
    path = directory / name
    if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError(f"generated input is missing or nonregular: {path}")
    return path.absolute()


def tracked_sources(repo: Path) -> list[Path]:
    result = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if not name:
            continue
        rel = PurePosixPath(name)
        if rel.suffix == ".py" or rel.name in CONFIG_NAMES:
            result.append(regular_file(repo, name))
    return result


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
        identity = lambda row: (row.st_dev, row.st_ino, row.st_size,
                                row.st_mtime_ns, row.st_ctime_ns)
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
    unique = {str(path.absolute()): path for path in paths}
    return {name: hash_regular(unique[name]) for name in sorted(unique)}


def manifest_digest(manifest: dict[str, str]) -> str:
    data = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def ast_cases(path: Path) -> list[dict[str, str | None]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    cases: list[dict[str, str | None]] = []

    def visit(nodes, classes=()):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                visit(node.body, classes + (node.name,))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                cases.append({"path": str(path.relative_to(path.parents[2])),
                              "class": ".".join(classes) if classes else None,
                              "name": node.name})

    visit(tree.body)
    return cases


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / n for n in ("recipe", "carrier", "app"))
    result = temp / "m11-work-cap" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
    try:
        if os.environ.get("M11_WORK_CAP_RUNNER_CONTEXT") != "ubuntu-24.04":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("M11_WORK_CAP_EXECUTION_CONTEXT") != "offline-work-payload-fixtures-temp-sqlite-faiss-fake-embeddings-no-model":
            raise RuntimeError("execution context differs from reviewed recipe")
        if os.environ.get("M11_WORK_CAP_INSTALL_COMMAND") != INSTALL:
            raise RuntimeError("install command differs from reviewed recipe")
        for name in ("ORCHESTRATOR_PATHS_LLAMA_CPP_BIN",
                     "ORCHESTRATOR_PATHS_LLAMA_MTMD",
                     "ORCHESTRATOR_PATHS_LLAMA_SERVER"):
            value = Path(os.environ[name]).resolve()
            if value.exists() or value.parent != temp / "m11-work-cap" / "absent":
                raise RuntimeError(f"unexpected non-absent kernel path override: {name}")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        expected_venv = (Path(os.environ["RUNNER_TEMP"]) / "m11-work-cap" / "venv").resolve()
        if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != expected_venv:
            raise RuntimeError("capture interpreter is not the reviewed isolated venv")
        pins = {"recipe": git(recipe, "rev-parse", "HEAD"),
                "carrier": git(carrier, "rev-parse", "HEAD"),
                "app": git(app, "rev-parse", "HEAD"),
                "root_task_source": ROOT_SOURCE_PIN}
        git(recipe, "merge-base", "--is-ancestor", ROOT_SOURCE_PIN, "HEAD")
        expected = {"recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER_PIN, "app": APP_PIN}
        for key, repo in (("recipe", recipe), ("carrier", carrier), ("app", app)):
            if pins[key] != expected[key]:
                raise RuntimeError(f"{key} checkout differs from exact pin")
            if git(repo, "status", "--porcelain", "--untracked-files=all"):
                raise RuntimeError(f"{key} checkout is not clean")
        if (os.environ.get("APP_PIN") != APP_PIN
                or os.environ.get("ROOT_CARRIER_PIN") != CARRIER_PIN
                or os.environ.get("ROOT_SOURCE_PIN") != ROOT_SOURCE_PIN):
            raise RuntimeError("workflow source or carrier pin differs")
        lock = tomllib.loads(regular_file(app, "uv.lock").read_text(encoding="utf-8"))
        locked = {p["name"].lower(): p for p in lock["package"]}
        requirements_path = regular_file(recipe, INSTALL_REQUIREMENTS)
        requirements_text = requirements_path.read_text(encoding="utf-8")
        requirement_versions = dict(re.findall(
            r"(?m)^([A-Za-z0-9_.-]+)==([^\s]+)", requirements_text
        ))
        normalized_requirements = {name.lower().replace("_", "-"): version
                                   for name, version in requirement_versions.items()}
        if normalized_requirements != PACKAGES:
            raise RuntimeError("requirements package/version set differs from the 49-package APP closure")
        declared_wheels = {}
        current_package = None
        for line in requirements_text.splitlines():
            stripped = line.strip()
            match = re.match(r"^([A-Za-z0-9_.-]+)==", stripped)
            if match:
                current_package = match.group(1).lower().replace("_", "-")
                declared_wheels[current_package] = set()
            if current_package is not None:
                declared_wheels[current_package].update(
                    re.findall(r"--hash=sha256:([0-9a-f]{64})", stripped)
                )
        expected_wheels = {}
        for name, version in PACKAGES.items():
            record = locked.get(name.lower())
            if not record or record["version"] != version:
                raise RuntimeError(f"{name} version differs from APP uv.lock")
            wheel_hashes = {
                wheel["hash"].removeprefix("sha256:")
                for wheel in record.get("wheels", [])
            }
            if not wheel_hashes:
                raise RuntimeError(f"{name} has no wheel in APP uv.lock")
            expected_wheels[name] = wheel_hashes
            for wheel_hash in wheel_hashes:
                if f"--hash=sha256:{wheel_hash}" not in requirements_text:
                    raise RuntimeError(f"hash-locked requirements omit a locked wheel for {name}")
            if importlib.metadata.version(name) != version:
                raise RuntimeError(f"installed {name} differs from reviewed pin")
        if declared_wheels != expected_wheels:
            raise RuntimeError("requirements wheel hashes differ from the exact APP-locked per-package wheel set")

        manifest_path = regular_file(recipe, "scripts/ci/m11_work_cap_expected_cases.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_commit") != APP_PIN or manifest.get("count") != 41:
            raise RuntimeError("expected-case manifest pin/count differs")
        cases = manifest["cases"]
        if len(cases) != 41 or len({(c["path"], c.get("class", ""), c["name"]) for c in cases}) != 41:
            raise RuntimeError("expected-case manifest is incomplete or duplicated")
        actual_cases = []
        for relative in TEST_FILES:
            actual_cases.extend(ast_cases(regular_file(app, relative)))
        identity = lambda row: (row["path"], row.get("class"), row["name"])
        if Counter(map(identity, actual_cases)) != Counter(map(identity, cases)):
            raise RuntimeError("exact full-module AST cases differ from the frozen manifest")
        selections = []
        expected_junit = set()
        for case in cases:
            module = case["path"][:-3].replace("/", ".")
            cls = case.get("class")
            selections.append(f"{case['path']}::{cls + '::' if cls else ''}{case['name']}")
            expected_junit.add((f"{module}.{cls}" if cls else module, case["name"]))

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        install_log = output_file(result, "dependency-install.log")
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(), "repositories": pins,
            "runner_context": os.environ["M11_WORK_CAP_RUNNER_CONTEXT"],
            "execution_context": os.environ["M11_WORK_CAP_EXECUTION_CONTEXT"],
            "selection_count": len(selections), "selections": selections,
            "expected_case_count": 41, "expected_case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "install_command": INSTALL, "requirements_path": INSTALL_REQUIREMENTS,
            "requirements_sha256": hashlib.sha256(requirements_path.read_bytes()).hexdigest(),
            "dependency_install_log_sha256": hashlib.sha256(install_log.read_bytes()).hexdigest(),
            "declared_dependencies": PACKAGES,
            "dependency_basis": "Reuse the previously reviewed 49-package Linux/Python 3.13.15 APP uv.lock closure for the actual memory/work-payload modules, including the `src.api.routes.chat_pipeline.telemetry` end-to-end path and exercised FAISS storage. All wheels are hash-locked, installed with --no-deps --only-binary=:all:, and the native readset binds requirements, uv.lock, pip-freeze, and dependency-install.log. Tests use deterministic fake embeddings and temporary SQLite/FAISS stores; no model-serving or ONNX runtime package is installed.",
            "runtime_data_inputs": list(APP_CONFIG_EXTRAS),
            "root_source_commit": ROOT_SOURCE_PIN,
            "root_task_source": {"path": ROOT_TASK, "sha256": ROOT_TASK_SHA256},
            "root_vb_source_table": {"path": ROOT_VB_TABLE, "sha256": ROOT_VB_TABLE_SHA256},
            "kernel_path_overrides": {name: os.environ[name] for name in (
                "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN", "ORCHESTRATOR_PATHS_LLAMA_MTMD",
                "ORCHESTRATOR_PATHS_LLAMA_SERVER")},
            "isolation": "The two complete selected modules use deterministic fake embedders and temporary SQLite/FAISS stores. No model, ONNX, endpoint, GPU, serving process, live corpus store, or inference is invoked.",
            "pytest_environment": {k: os.environ.get(k) for k in ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED", "PYTHONPATH", "PYTHONUNBUFFERED")}
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite capture outputs")
        workflow = regular_file(recipe, ".github/workflows/m11-work-cap-capture.yml")
        runner = regular_file(recipe, "scripts/ci/m11_work_cap_capture.py")
        root_task = regular_file(recipe, ROOT_TASK)
        root_vb_table = regular_file(recipe, ROOT_VB_TABLE)
        if hash_regular(root_task) != ROOT_TASK_SHA256:
            raise RuntimeError("ROOT M11_WORK_CAP task bytes differ from the reviewed pin")
        if hash_regular(root_vb_table) != ROOT_VB_TABLE_SHA256:
            raise RuntimeError("ROOT M11_WORK_CAP source-table bytes differ from the reviewed pin")
        app_config_paths = [regular_file(app, name) for name in APP_CONFIG_EXTRAS]
        for relative in APP_CONFIG_EXTRAS:
            mode = git(app, "ls-tree", "HEAD", "--", relative).split(maxsplit=1)
            if not mode or mode[0] != "100644":
                raise RuntimeError(f"APP runtime data is not a tracked regular file: {relative}")
        carrier_inputs = [regular_file(carrier, name) for name in CARRIER_READS]
        read_paths = [workflow, runner, manifest_path, requirements_path, install_log, freeze,
                      environment, root_task, root_vb_table, *app_config_paths,
                      *tracked_sources(recipe), *tracked_sources(app), *carrier_inputs]
        producer_inputs_before = file_manifest(read_paths)
        input_readset_path = result / "producer-input-readset.json"
        input_readset_path.write_text(json.dumps({
            "kind": "pre-execution-source-input-hashes",
            "count": len(producer_inputs_before),
            "sha256": manifest_digest(producer_inputs_before),
            "inputs": producer_inputs_before,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        command = [sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
                   "-c", "/dev/null", "--rootdir", str(app), "-p", "no:cacheprovider",
                   "-q", *selections, f"--junitxml={junit}"]
        producer = [sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
                    "--cwd", str(app), "--junit", str(junit), "--output", str(native),
                    "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"app={app}"]
        for path in dict.fromkeys(p.resolve() for p in read_paths):
            producer.extend(("--read-path", str(path)))
        for selection in TEST_FILES:
            producer.extend(("--select", selection))
        status.update(state="running", repositories=pins, selection_count=len(selections))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
        execution_env = dict(os.environ, PYTHONPATH=str(app))
        exit_code = subprocess.call([*producer, "--", *command], cwd=app, env=execution_env)
        producer_inputs_after = file_manifest(read_paths)
        if producer_inputs_after != producer_inputs_before:
            raise RuntimeError("producer inputs changed during native capture")
        if not junit.is_file() or not (native / "receipt.json").is_file():
            status.update(state="capture_failed", exit_code=exit_code or 1, diagnostic="missing original JUnit or native receipt")
            return exit_code or 1
        root = ET.parse(junit).getroot()
        observed = [(item.get("classname", ""), item.get("name", "")) for item in root.iter("testcase")]
        counts = {"collected": len(observed), "unique": len(set(observed)),
                  "expected": len(expected_junit), "missing": sorted(expected_junit - set(observed)),
                  "unexpected": sorted(set(observed) - expected_junit)}
        receipt_path = native / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        summary = receipt.get("summary")
        native_counts = (summary or {}).get("counts") or {}
        native_cases = (summary or {}).get("cases") or []
        expected_set = Counter(expected_junit)
        junit_set = Counter(observed)
        junit_ok = junit_set == expected_set and len(observed) == 41
        native_set = Counter((row.get("classname", ""), row.get("name", ""))
                             for row in native_cases)
        native_ok = (native_set == expected_set and len(native_cases) == 41
                     and native_counts.get("collected") == 41
                     and native_counts.get("executed") == 41
                     and native_counts.get("skipped") == 0
                     and native_counts.get("failure") == 0
                     and native_counts.get("error") == 0
                     and receipt.get("fixture_execution_conformant") is True)
        status.update(state="grading", exit_code=exit_code, junit_identity_check=counts,
                      native_counts=native_counts)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")
        before = inventory(result)
        if not before or "shared-grade.json" in before:
            raise RuntimeError("fresh result tree is empty or already contains a grade")
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("native receipt projection is not exactly one row")
        claim = project_ci_conformance(rows[0])
        quality, time_grade, reasons = grade(claim)
        grade_record = {"measurement_id": claim.measurement_id, "source_kind": claim.source_kind,
                        "binding_kind": claim.binding_kind, "Q": quality, "T": time_grade,
                        "reasons": reasons, "interpretation": "shared carrier grade only; fixture conformance is not product or scientific evidence"}
        if (quality, time_grade) != ("Judged", "Located"):
            raise RuntimeError("shared carrier grade differs from accepted fixture expectation")
        producer_inputs_after_grade = file_manifest(read_paths)
        if producer_inputs_after_grade != producer_inputs_before:
            raise RuntimeError("producer inputs changed during shared-grade analysis")
        after = inventory(result)
        if after != before:
            raise RuntimeError("shared-grade projection changed result-tree membership or bytes")
        grade_record["original_before_sha256"] = before
        grade_record["original_after_sha256"] = after
        grade_record["producer_input_sha256_before"] = manifest_digest(producer_inputs_before)
        grade_record["producer_input_sha256_after"] = manifest_digest(producer_inputs_after_grade)
        with (result / "shared-grade.json").open("x", encoding="utf-8") as handle:
            json.dump(grade_record, handle, sort_keys=True, indent=2)
            handle.write("\n")
        all_pass = (exit_code == 0 and junit_ok and native_ok
                    and (quality, time_grade) == ("Judged", "Located"))
        status.update(state="passed" if all_pass else "failed", exit_code=0 if all_pass else (exit_code or 1),
                      junit_identity_check=counts, native_summary=summary,
                      fixture_execution_conformant=receipt.get("fixture_execution_conformant"))
        return 0 if all_pass else (exit_code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
