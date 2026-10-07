#!/usr/bin/env python3
"""Capture source-only SMT sibling-overlap controls through the existing verifier."""
from __future__ import annotations

import collections
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tomllib
import re

ROOT = Path(__file__).resolve().parents[2]
APP_PIN = "3e34eaeca079c440f31b2f26710fd09790544cc9"
ROOT_READS = (
    ".github/workflows/ssbench-smt-native.yml",
    "scripts/ci/ssbench_native_capture.py",
    "scripts/ci/ssbench_expected_cases.json",
    "scripts/ci/ssbench_requirements.txt",
    "scripts/ci/ssbench_package_versions.json",
    "scripts/ci/ni08_source_context.py",
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/README.md",
    "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/measurement_record.py",
    "scripts/vidya/canonical.py", "scripts/vidya/frames.py", "scripts/vidya/lattice.py",
    "handoffs/active/vidya-belief-substrate-program.md",
    "handoffs/active/standardized-stack-update-pipeline-finalization.md",
)
APP_READS = (
    "scripts/server/bench_core_claim.py", "scripts/server/fleet_markers.py",
    "scripts/server/orchestrator_stack.py", "scripts/server/realized_fleet.py",
    "scripts/server/runtime_facts_manifest.py", "scripts/server/stack_checkpoint.py",
    "scripts/server/stack_commands.py", "scripts/server/stack_docker.py",
    "scripts/server/stack_env.py", "scripts/server/stack_health.py",
    "scripts/server/stack_host.py", "scripts/server/stack_log_banner.py",
    "scripts/server/stack_manifest.py", "scripts/server/stack_numa.py",
    "scripts/server/stack_numa_evict.py", "scripts/server/stack_numa_mode.py",
    "scripts/server/stack_paths.py", "scripts/server/stack_prewarm.py",
    "scripts/server/stack_processes.py", "scripts/server/stack_runtime.py",
    "scripts/server/stack_state.py", "src/config/__init__.py", "src/config/models.py",
    "src/config/validation.py", "src/env_parsing.py", "src/registry/kernel_paths.py",
    "src/registry/stack_priors.py", "src/registry_loader.py", "src/roles.py",
    "src/services/worker_pool.py", "tests/__init__.py", "tests/unit/__init__.py",
    "tests/unit/test_bench_core_claim.py", "tests/unit/test_bench_core_claim_api_layer.py",
)


def write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def regular_bytes(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"declared capture input is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)


def snapshots(paths: list[Path]) -> dict[str, dict[str, object]]:
    return {str(path): {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for path in paths for data in [regular_bytes(path)]}


def native_tree_snapshot(directory: Path) -> dict[str, dict[str, object]]:
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"symlink appeared in result artifact tree: {path}")
        relative = path.relative_to(directory).as_posix()
        if relative == "status.json":
            continue
        if path.is_dir():
            result[relative + "/"] = {"kind": "directory"}
            continue
        data = regular_bytes(path)
        result[relative] = {"kind": "regular_file", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return result


def source_context(app: Path, path: Path) -> None:
    command = [sys.executable, str(ROOT / "scripts/ci/ni08_source_context.py"),
               "--repo", f"root={ROOT}", "--repo", f"app={app}", "--output", str(path)]
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"source-context generation failed: {result.stdout[-2000:]}")


def load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("ssbench_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the existing native verifier carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def app_dynamic_config_inputs(app: Path) -> list[Path]:
    # Conservative complete source/config envelope closes eager and lazy import inputs.
    listing = subprocess.check_output(["git", "-C", str(app), "ls-tree", "-r", APP_PIN], text=True)
    selected = []
    for entry in listing.splitlines():
        identity, name = entry.split("\t", 1)
        mode, kind, _blob = identity.split()
        path = Path(name)
        if mode not in {"100644", "100755"} or kind != "blob":
            continue
        if (name == "registry.yaml" or name == "pyproject.toml"
                or (path.parts[0] in {"src", "scripts", "orchestration"} and path.suffix == ".py")
                or (path.parts[0] in {"config", "prompts"} and path.suffix.lower() in {".yaml", ".yml", ".json", ".toml", ".md", ".txt"})):
            selected.append(app / name)
    return selected


def verify_locked_wheels(app: Path) -> None:
    PACKAGES = json.loads(regular_bytes(ROOT / "scripts/ci/ssbench_package_versions.json"))["versions"]
    requirements = ROOT / "scripts/ci/ssbench_requirements.txt"
    if subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD:uv.lock"], text=True).strip() != "ef2306018773ff9a1e80389970d92f66fcf8d5b7":
        raise RuntimeError("APP lock blob differs from the dependency source used for wheel selection")
    lock = tomllib.loads(regular_bytes(app / "uv.lock").decode("utf-8"))
    locked = {row["name"].lower().replace("_", "-"): row for row in lock["package"]}
    declared: dict[str, dict[str, object]] = {}
    current = None
    for line in regular_bytes(requirements).decode("utf-8").splitlines():
        row = line.strip()
        if not row or row.startswith("#"):
            continue
        if not line[:1].isspace():
            if not row.endswith("\\"):
                raise RuntimeError("exact requirement row lacks a continuation")
            match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)", row[:-1].rstrip())
            if not match:
                raise RuntimeError("invalid exact package row in hash-locked requirements")
            current = match.group(1).lower().replace("_", "-")
            declared[current] = {"version": match.group(2), "hashes": set()}
        else:
            match = re.fullmatch(r"--hash=sha256:([0-9a-f]{64})", row.removesuffix("\\").rstrip())
            if not match or current is None:
                raise RuntimeError("invalid or orphan wheel hash in requirements")
            declared[current]["hashes"].add(match.group(1))
    if set(declared) != {name.lower() for name in PACKAGES}:
        raise RuntimeError("requirements package set differs from the tested import closure")
    for name, version in PACKAGES.items():
        key = name.lower().replace("_", "-")
        package = locked.get(key)
        if not package or package["version"] != version or declared[key]["version"] != version:
            raise RuntimeError(f"locked package version differs: {name}=={version}")
        compatible = {
            wheel["hash"].removeprefix("sha256:") for wheel in package.get("wheels", [])
        }
        if not compatible or declared[key]["hashes"] != compatible:
            raise RuntimeError(f"requirements wheel hashes differ from APP lock: {name}")


ABSENT_BINARY_OVERRIDES = {
    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "llama-server",
    "ORCHESTRATOR_PATHS_LLAMA_MTMD": "mtmd-cli",
    "ORCHESTRATOR_PATHS_LLAMA_SERVER": "llama-server-wrapper",
}

def absent_binary_context(runner_temp: Path) -> dict[str, str]:
    context = {}
    if os.environ.get("ORCHESTRATOR_MOCK_MODE") != "1":
        raise RuntimeError("synthetic APP imports require explicit mock mode")
    for key, name in ABSENT_BINARY_OVERRIDES.items():
        expected = runner_temp / "ssbench" / "absent-binaries" / name
        if os.environ.get(key) != str(expected) or os.path.lexists(expected):
            raise RuntimeError(f"absent mock binary binding differs: {key}")
        context[key] = str(expected)
    return context

def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: ssbench_native_capture.py APP_ROOT RESULT_DIR")
    app, result = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1" or os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise RuntimeError("pytest autoload/bytecode controls differ")
    if os.environ.get("PYTEST_ADDOPTS", "") or os.environ.get("PYTEST_PLUGINS", ""):
        raise RuntimeError("inherited pytest options/plugins must be empty")
    if not os.environ.get("GITHUB_SHA") or subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip() != os.environ["GITHUB_SHA"]:
        raise RuntimeError("ROOT recipe differs from triggering commit")
    runner_temp_value = os.environ.get("RUNNER_TEMP")
    if not runner_temp_value:
        raise RuntimeError("RUNNER_TEMP is required for this bounded hosted capture")
    runner_temp = Path(runner_temp_value).resolve()
    if Path(sys.prefix).resolve() != (runner_temp / "ssbench" / "venv").resolve():
        raise RuntimeError("capture is not running from the isolated RUNNER_TEMP virtualenv")
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.13.15":
        raise RuntimeError("capture requires the accepted CPython 3.13.15 runner")
    if os.environ.get("APP_PIN") != APP_PIN:
        raise RuntimeError("workflow APP_PIN differs from the bound APP source")
    app_commit = subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"], text=True).strip()
    if app_commit != APP_PIN:
        raise RuntimeError("APP checkout differs from the reviewed test/source pin")
    if result != runner_temp / "ssbench" / "result" or not result.is_dir() or not (result / "status.json").is_file() or os.path.lexists(result / "native"):
        raise RuntimeError("result envelope absent or native output not fresh")
    absent_binaries = absent_binary_context(runner_temp)
    install_log = result / "dependency-install.log"
    requirement_file = ROOT / "scripts/ci/ssbench_requirements.txt"
    verify_locked_wheels(app)
    installed = subprocess.run([sys.executable, "-m", "pip", "install", "--require-hashes",
                                "--no-deps", "--only-binary=:all:", "-r", str(requirement_file)],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, check=False)
    write_once(install_log, installed.stdout.encode())
    if installed.returncode:
        raise RuntimeError(f"locked binary-wheel installation failed: {installed.returncode}")
    expected_versions = json.loads(regular_bytes(ROOT / "scripts/ci/ssbench_package_versions.json"))
    versions = expected_versions.get("versions") if expected_versions.get("schema") == "epyc.ssbench.package_versions/v1" else None
    if not isinstance(versions, dict):
        raise RuntimeError("invalid locked package version manifest")
    actual = {name: importlib.metadata.version(name) for name in versions}
    if actual != versions:
        raise RuntimeError("installed packages differ from exact APP uv.lock closure")
    env = {"python": sys.version, "python_version": platform.python_version(),
           "platform": platform.platform(), "app_pin": APP_PIN, "packages": actual,
           "mock_mode": os.environ["ORCHESTRATOR_MOCK_MODE"], "absent_binary_overrides": absent_binaries}
    write_once(result / "environment.json",
               (json.dumps(env, sort_keys=True, separators=(",", ":")) + "\n").encode())
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    if freeze.returncode:
        raise RuntimeError("cannot capture isolated pip inventory")
    write_once(result / "pip-freeze.txt", freeze.stdout.encode())
    context = result / "source-context.json"
    source_context(app, context)
    junit = result / "selected.junit.xml"
    receipt_dir = result / "native"
    expected = json.loads(regular_bytes(ROOT / "scripts/ci/ssbench_expected_cases.json"))
    if len(expected.get("cases", [])) != 81:
        raise RuntimeError("the frozen exact-case manifest is not the reviewed 81-case scope")
    command = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null",
               "--rootdir", str(app), "--import-mode=importlib", "-o", "addopts=", "-p", "no:cacheprovider",
               "-p", "pytest_asyncio.plugin", "-q", f"--junitxml={junit}",
               "tests/unit/test_bench_core_claim.py",
               "tests/unit/test_bench_core_claim_api_layer.py"]
    read_paths = [ROOT / item for item in ROOT_READS] + [app / item for item in APP_READS]
    read_paths += app_dynamic_config_inputs(app) + [app / "uv.lock", context,
                    result / "environment.json", install_log, result / "pip-freeze.txt"]
    read_paths = list(dict.fromkeys(path.resolve() for path in read_paths))
    source_before_capture = snapshots(read_paths)
    carrier = load_carrier()
    record = carrier.capture_fixture_execution(
        argv=command, cwd=app, junit=junit, output=receipt_dir,
        repositories={"root": ROOT, "app": app}, read_paths=read_paths,
        selections=["tests/unit/test_bench_core_claim.py",
                    "tests/unit/test_bench_core_claim_api_layer.py"])
    summary = record.get("summary")
    if not isinstance(summary, dict) or not isinstance(summary.get("cases"), list) or not isinstance(summary.get("counts"), dict):
        raise RuntimeError("native receipt does not have a valid original-JUnit summary")
    expected_ids = [(row["classname"], row["name"]) for row in expected["cases"]]
    actual_ids = [(row["classname"], row["name"]) for row in summary["cases"]]
    if (len(actual_ids) != len(set(actual_ids)) or collections.Counter(actual_ids) != collections.Counter(expected_ids)
            or summary["counts"].get("collected") != 81 or summary["counts"].get("executed") != 81):
        raise RuntimeError("native JUnit identities/counts differ from the exact 81-case source manifest")
    if absent_binary_context(runner_temp) != absent_binaries:
        raise RuntimeError("absent mock binary context changed during capture")
    source_before = snapshots(read_paths)
    if source_before != source_before_capture:
        raise RuntimeError("source/readset bytes changed during execution")
    native_before = native_tree_snapshot(result)
    junit_before = hashlib.sha256(regular_bytes(junit)).hexdigest()
    sys.path.insert(0, str(ROOT / "scripts/vidya"))
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade
    rows = native_rows(str(receipt_dir / "receipt.json"))
    if len(rows) != 1:
        raise RuntimeError("the existing CI adapter did not project exactly one row")
    claim = project_ci_conformance(rows[0])
    judgment = grade(claim)
    if absent_binary_context(runner_temp) != absent_binaries:
        raise RuntimeError("absent mock binary context changed during shared grade")
    source_after = snapshots(read_paths)
    native_after = native_tree_snapshot(result)
    junit_after = hashlib.sha256(regular_bytes(junit)).hexdigest()
    if source_before != source_after or native_before != native_after or junit_before != junit_after:
        raise RuntimeError("source inputs or original capture custody changed during shared grade")
    check = {"receipt": str(receipt_dir / "receipt.json"), "case_count": 81,
             "grade": list(judgment), "claim_value": claim.value,
             "fixture_execution_conformant": record.get("fixture_execution_conformant"),
             "original_counts": summary["counts"], "absent_binary_overrides": absent_binaries,
             "scope": "synthetic source-level SMT sibling/topology/placement controls",
             "source_inputs_before_capture": source_before_capture, "source_inputs_before": source_before, "source_inputs_after": source_after,
             "native_tree_before": native_before, "native_tree_after": native_after,
             "junit_sha256_before": junit_before, "junit_sha256_after": junit_after}
    write_once(result / "shared-grade-check.json",
               (json.dumps(check, sort_keys=True, separators=(",", ":")) + "\n").encode())
    print(json.dumps(check, sort_keys=True))
    return 0 if record.get("fixture_execution_conformant") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
