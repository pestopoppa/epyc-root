"""Hosted synthetic FW1 mocked graph authoring/routing execution through unchanged native CI grade."""
from __future__ import annotations
import ast
import collections
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
PYTHON_PIN = "3.13.15"
LOCK_SOURCE_COMMIT = "70096b763939a43409a1f1827ab633d62425a6c1"
LOCK_SOURCE_BLOB = "ef2306018773ff9a1e80389970d92f66fcf8d5b7"
SOURCE_COMMIT = "38d4ab72fe95ef7c1064d6574b3552a182023850"
CONTEXT_COMMIT = "83004c1137015a9fc8d0cf411e648432bc51a1c9"
CARRIER_COMMIT = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
PACKAGES = {'pyyaml': '6.0.3', 'pydantic-settings': '2.13.1', 'typing-inspection': '0.4.2', 'typing-extensions': '4.15.0', 'python-dotenv': '1.2.2', 'pydantic': '2.13.0', 'pydantic-core': '2.46.0', 'annotated-types': '0.7.0', 'pytest': '9.0.3', 'pygments': '2.20.0', 'pluggy': '1.6.0', 'packaging': '26.0', 'iniconfig': '2.3.0', 'colorama': '0.4.6', 'pydantic-graph': '1.80.0', 'logfire-api': '4.32.0', 'httpx': '0.28.1', 'idna': '3.11', 'httpcore': '1.0.9', 'h11': '0.16.0', 'certifi': '2026.2.25', 'anyio': '4.13.0', 'langgraph': '1.1.6', 'xxhash': '3.6.0', 'langgraph-sdk': '0.3.13', 'orjson': '3.11.8', 'langgraph-prebuilt': '1.0.9', 'langgraph-checkpoint': '4.0.1', 'ormsgpack': '1.12.2', 'langchain-core': '1.2.28', 'uuid-utils': '0.14.1', 'tenacity': '9.1.4', 'langsmith': '0.7.30', 'zstandard': '0.25.0', 'requests-toolbelt': '1.0.0', 'requests': '2.33.1', 'urllib3': '2.6.3', 'charset-normalizer': '3.4.7', 'jsonpatch': '1.33', 'jsonpointer': '3.1.1', 'jsonschema': '4.26.0', 'rpds-py': '0.30.0', 'referencing': '0.37.0', 'attrs': '26.1.0', 'jsonschema-specifications': '2025.9.1'}
WORKFLOW_INPUTS = (".github/workflows/fw1-mock-native.yml", "scripts/ci/fw1_mock_capture.py", "scripts/ci/fw1_mock_requirements.txt", "scripts/ci/fw1_mock_inputs.json")

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def verify_locked_packages(lock_source: Path, requirements: Path) -> dict[str, str]:
    if subprocess.check_output(["git", "-C", str(lock_source), "rev-parse", "HEAD"], text=True).strip() != LOCK_SOURCE_COMMIT:
        raise RuntimeError("APP pytest lock source commit differs from reviewed pin")
    if subprocess.check_output(["git", "-C", str(lock_source), "rev-parse", "HEAD:uv.lock"], text=True).strip() != LOCK_SOURCE_BLOB:
        raise RuntimeError("APP uv.lock blob differs from reviewed pin")
    if subprocess.check_output(["git", "-C", str(lock_source), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise RuntimeError("APP pytest lock checkout has tracked modifications")
    locked = {item["name"].lower(): item for item in tomllib.loads(
        (lock_source / "uv.lock").read_text(encoding="utf-8"))["package"]}
    text = requirements.read_text(encoding="utf-8")
    declared: dict[str, set[str]] = {}
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[:1].isspace():
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+) \\", stripped)
            if not match:
                raise RuntimeError("invalid exact requirement declaration")
            current = match.group(1).lower()
            if match.group(2) != PACKAGES.get(current):
                raise RuntimeError(f"requirements version differs for {current}")
            declared[current] = set()
        else:
            match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", stripped.removesuffix("\\").rstrip())
            if not match or current is None:
                raise RuntimeError("invalid or orphan package hash")
            declared[current].add(match.group(1))
    if set(declared) != set(PACKAGES):
        raise RuntimeError("requirements differ from the five-package selected closure")
    for name, version in PACKAGES.items():
        item = locked.get(name)
        if not item or item["version"] != version:
            raise RuntimeError(f"locked source does not pin {name}=={version}")
        wheel_hashes = {row["hash"].removeprefix("sha256:") for row in item.get("wheels", [])}
        if not wheel_hashes or declared[name] != wheel_hashes:
            raise RuntimeError(f"requirements hashes differ from the all locked wheels for {name}")
    installed = {name: importlib.metadata.version(name) for name in PACKAGES}
    if installed != PACKAGES:
        raise RuntimeError("installed package versions differ from the exact selected lock closure")
    return installed

def regular_bytes(path: Path) -> bytes:
    import stat
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"source/result input is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)

def source_snapshot(paths: list[Path]) -> dict[str, dict[str, object]]:
    return {str(path): {"bytes": len(data), "sha256": digest(data)}
            for path in paths for data in [regular_bytes(path)]}

def result_snapshot(root: Path) -> dict[str, dict[str, object]]:
    snapshot = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"result tree contains a symlink: {path}")
        relative = path.relative_to(root).as_posix()
        if relative == "status.json":
            continue
        if path.is_dir():
            snapshot[relative + "/"] = {"kind": "directory"}
            continue
        data = regular_bytes(path)
        snapshot[relative] = {"kind": "regular_file", "bytes": len(data), "sha256": digest(data)}
    return snapshot

def pinned(repo: Path, commit: str, label: str) -> None:
    if subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() != commit:
        raise RuntimeError(f"{label} HEAD differs from the reviewed pin")
    if subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"], text=True).strip():
        raise RuntimeError(f"{label} checkout is not clean")


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("usage: fw1_mock_capture.py APP_SOURCE CARRIER LOCK_SOURCE CONTEXT")
    source, carrier_root, lock_source, context = [Path(value).resolve() for value in sys.argv[1:]]
    if not os.environ.get("GITHUB_SHA"):
        raise RuntimeError("triggering recipe SHA is absent")
    for repo, commit, label in [(ROOT, os.environ["GITHUB_SHA"], "recipe"),
            (source, SOURCE_COMMIT, "ROOT source"),
            (carrier_root, CARRIER_COMMIT, "native carrier"), (context, CONTEXT_COMMIT, "enrollment context")]:
        pinned(repo, commit, label)
    if sys.version.split()[0] != PYTHON_PIN:
        raise RuntimeError("Python patch differs from the reviewed pin")
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1" or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise RuntimeError("pytest autoload and bytecode controls must be disabled")
    if os.environ.get("PYTEST_ADDOPTS", "") or os.environ.get("PYTEST_PLUGINS", ""):
        raise RuntimeError("inherited pytest options/plugins must be empty")
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if Path(sys.prefix).resolve() != runner_temp / "fw1-mock" / "venv":
        raise RuntimeError("capture must run inside the isolated runner virtualenv")
    result = runner_temp / "fw1-mock" / "result"
    if not result.is_dir() or not (result / "status.json").is_file() or os.path.lexists(result / "native"):
        raise RuntimeError("workflow result envelope absent or native output not fresh")
    absent_paths = {
        "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": str(runner_temp / "fw1-mock" / "absent-binaries" / "llama-server"),
        "ORCHESTRATOR_PATHS_LLAMA_MTMD": str(runner_temp / "fw1-mock" / "absent-binaries" / "mtmd-cli"),
        "ORCHESTRATOR_PATHS_LLAMA_SERVER": str(runner_temp / "fw1-mock" / "absent-binaries" / "llama-server-wrapper"),
    }
    if any(os.environ.get(key) != value or os.path.lexists(value) for key, value in absent_paths.items()):
        raise RuntimeError("three absent-binary config overrides differ or unexpectedly exist")
    installed = verify_locked_packages(lock_source, ROOT / "scripts/ci/fw1_mock_requirements.txt")
    manifest_path = ROOT / "scripts/ci/fw1_mock_inputs.json"
    manifest = json.loads(regular_bytes(manifest_path))
    if manifest["schema"] != "epyc.fw1.mock.inputs/v1":
        raise RuntimeError("source manifest schema differs")
    roots = {"source": source, "carrier": carrier_root, "context": context, "lock_source": lock_source}
    reads = [ROOT / name for name in WORKFLOW_INPUTS]
    for label, rows in manifest["inputs"].items():
        for row in rows:
            path = roots[label] / row["path"]
            data = regular_bytes(path)
            blob = subprocess.check_output(["git", "-C", str(roots[label]), "rev-parse", "HEAD:" + row["path"]], text=True).strip()
            if blob != row["blob"] or len(data) != row["bytes"] or digest(data) != row["sha256"]:
                raise RuntimeError(f"reviewed source binding differs: {label}/{row['path']}")
            reads.append(path)
    for relative in ("scripts/vidya/adapters/README.md", "handoffs/active/vidya-belief-substrate-program.md"):
        if "VB-FW1-MOCK-CONFORMANCE" not in (context / relative).read_text(encoding="utf-8"):
            raise RuntimeError("prospective FW1 source enrollment absent")
    environment = result / "environment.json"
    environment.write_text(json.dumps({"python": sys.version, "executable": sys.executable,
        "packages": installed, "absent_binary_overrides": absent_paths, "pytest_plugin_autoload": os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"],
        "bytecode_disabled": os.environ["PYTHONDONTWRITEBYTECODE"],
        "scope": "synthetic writer/reader fixtures only; injected mock worker/model emissions only; no production executor or model evidence"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.environ["PYTHONPATH"] = str(source)
    inputs = result / "source-context.json"
    inputs.write_text(json.dumps({"repositories": {key: str(value) for key, value in roots.items()},
        "source_manifest": manifest, "expected_cases": manifest["expected_cases"],
        "pytest_environment": {key: os.environ.get(key, "") for key in ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTHONDONTWRITEBYTECODE", "PYTHONPATH")}}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    reads += [environment, inputs, result / "install.log", result / "pip-freeze.txt"]
    reads = list(dict.fromkeys(path.resolve() for path in reads))
    before = source_snapshot(reads)
    before_result = result_snapshot(result)
    junit = result / "selected.xml"
    selections = manifest["selected_modules"]
    command = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null", "--rootdir", str(source),
        "--import-mode=importlib", "-o", "addopts=", "-p", "no:cacheprovider", "-q", f"--junitxml={junit}",
        *[str(source / name) for name in selections]]
    sys.path.insert(0, str(carrier_root))
    sys.path.insert(1, str(carrier_root / "scripts" / "vidya"))
    from scripts.ci import native_conformance as carrier
    if Path(carrier.__file__).resolve() != carrier_root / "scripts/ci/native_conformance.py":
        raise RuntimeError("native carrier import identity differs")
    record = carrier.capture_fixture_execution(argv=command, cwd=source, junit=junit, output=result / "native",
        repositories={"recipe": ROOT, **roots}, read_paths=reads, selections=selections)
    if any(os.environ.get(key) != value or os.path.lexists(value) for key, value in absent_paths.items()):
        raise RuntimeError("absent binary controls changed during test execution")
    after_capture = source_snapshot(reads)
    if after_capture != before:
        raise RuntimeError("source bytes changed during native execution")
    summary = record.get("summary")
    cases = summary.get("cases") if isinstance(summary, dict) else None
    expected = collections.Counter((row["classname"], row["name"]) for row in manifest["expected_cases"])
    if not isinstance(cases, list) or collections.Counter((row["classname"], row["name"]) for row in cases) != expected:
        (result / "native-outcome.json").write_text(json.dumps({"fixture_execution_conformant": None,
            "diagnostic": "native case identities differ from the ten-case manifest", "record_diagnostic": record.get("diagnostic"),
            "observed_cases": cases, "receipt": "native/receipt.json"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return 1
    before_grade_result = result_snapshot(result)
    from scripts.vidya.adapters import ci_conformance
    from claim_tuple import grade
    rows = ci_conformance.native_rows(result / "native/receipt.json")
    if len(rows) != 1:
        (result / "native-outcome.json").write_text(json.dumps({"fixture_execution_conformant": record.get("fixture_execution_conformant"),
            "diagnostic": "original receipt yielded no projectable row", "receipt": "native/receipt.json"}, sort_keys=True) + "\n", encoding="utf-8")
        return 1
    claim = ci_conformance.project_ci_conformance(rows[0])
    judgment = grade(claim)
    after_grade = source_snapshot(reads)
    after_grade_result = result_snapshot(result)
    if before != after_grade or before_grade_result != after_grade_result:
        raise RuntimeError("source or original result artifacts changed during shared grade")
    (result / "custody-snapshots.json").write_text(json.dumps({"source_before_capture": before,
        "source_after_capture": after_capture, "source_after_grade": after_grade,
        "result_before_capture": before_result, "result_before_grade": before_grade_result,
        "result_after_grade": after_grade_result, "excluded_mutable_status": "root status.json only"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (result / "shared-grade.json").write_text(json.dumps({"receipt_sha256": rows[0]["receipt_sha256"],
        "value": claim.value, "grade": list(judgment)}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"fixture_execution_conformant": record.get("fixture_execution_conformant"), "case_count": len(cases), "grade": list(judgment)}))
    return 0 if record.get("fixture_execution_conformant") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
