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
            raise RuntimeError(f"symlink appeared in native artifact tree: {path}")
        if path.is_file():
            data = regular_bytes(path)
            result[str(path.relative_to(directory))] = {
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
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
    # Config/registry files are source inputs to eager imports. Read only regular tracked blobs
    # declared by the exact APP commit; the carrier then binds their actual checkout bytes.
    listing = subprocess.check_output(["git", "-C", str(app), "ls-tree", "-r", "--name-only", APP_PIN], text=True)
    selected = []
    for name in listing.splitlines():
        path = Path(name)
        if name == "registry.yaml" or (path.parts and path.parts[0] == "config"
                and path.suffix.lower() in {".yaml", ".yml", ".json", ".toml"}):
            selected.append(app / name)
    return selected


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: ssbench_native_capture.py APP_ROOT RESULT_DIR")
    app, result = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
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
    if not result.is_relative_to(runner_temp) or os.path.lexists(result):
        raise RuntimeError("result directory must be fresh and contained beneath RUNNER_TEMP")
    result.mkdir(parents=True, exist_ok=False)
    install_log = result / "dependency-install.log"
    requirement_file = ROOT / "scripts/ci/ssbench_requirements.txt"
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
           "platform": platform.platform(), "app_pin": APP_PIN, "packages": actual}
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
               "--rootdir", str(app), "-o", "addopts=", "-p", "no:cacheprovider",
               "-p", "pytest_asyncio.plugin", "-q", f"--junitxml={junit}",
               "tests/unit/test_bench_core_claim.py",
               "tests/unit/test_bench_core_claim_api_layer.py"]
    read_paths = [ROOT / item for item in ROOT_READS] + [app / item for item in APP_READS]
    read_paths += app_dynamic_config_inputs(app) + [app / "uv.lock", context,
                    result / "environment.json", install_log, result / "pip-freeze.txt"]
    if len({p.resolve() for p in read_paths}) != len(read_paths):
        raise RuntimeError("duplicate source-read paths in bounded capture")
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
            or summary["counts"] != {"collected": 81, "executed": 81, "passed": 81,
                                     "failure": 0, "error": 0, "skipped": 0}):
        raise RuntimeError("native JUnit identities/counts differ from the exact 81-case source manifest")
    if record.get("fixture_execution_conformant") is not True:
        raise RuntimeError("existing native verifier did not produce a conformant receipt")
    source_before = snapshots(read_paths)
    native_before = native_tree_snapshot(receipt_dir)
    junit_before = hashlib.sha256(regular_bytes(junit)).hexdigest()
    sys.path.insert(0, str(ROOT / "scripts/vidya"))
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade
    rows = native_rows(str(receipt_dir / "receipt.json"))
    if len(rows) != 1:
        raise RuntimeError("the existing CI adapter did not project exactly one row")
    judgment = grade(project_ci_conformance(rows[0]))
    if judgment[0:2] != ("Judged", "Located"):
        raise RuntimeError("shared ClaimTuple.grade did not return Judged/Located")
    source_after = snapshots(read_paths)
    native_after = native_tree_snapshot(receipt_dir)
    junit_after = hashlib.sha256(regular_bytes(junit)).hexdigest()
    if source_before != source_after or native_before != native_after or junit_before != junit_after:
        raise RuntimeError("source inputs or original capture custody changed during shared grade")
    check = {"receipt": str(receipt_dir / "receipt.json"), "case_count": 81,
             "grade": judgment[0], "location": judgment[1],
             "scope": "synthetic source-level SMT sibling/topology/placement controls",
             "source_inputs_before": source_before, "source_inputs_after": source_after,
             "native_tree_before": native_before, "native_tree_after": native_after,
             "junit_sha256_before": junit_before, "junit_sha256_after": junit_after}
    write_once(result / "shared-grade-check.json",
               (json.dumps(check, sort_keys=True, separators=(",", ":")) + "\n").encode())
    print(json.dumps(check, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
