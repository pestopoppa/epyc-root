#!/usr/bin/env python3
"""Capture bounded RTG02 source-only tests through the existing native carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
APP_PIN = "ceb3ea84feba2dbc654987e3bc2ec12fb061f177"
ROOT_READS = (
    ".github/workflows/rtg02-native-conformance.yml",
    "scripts/ci/rtg02_run_native_capture.py",
    "scripts/ci/rtg02-expected-cases.json",
    "scripts/ci/rtg02-hosted-requirements.txt",
    "scripts/ci/ni08_source_context.py",
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/adapters/README.md",
    "scripts/vidya/claim_tuple.py",
    "handoffs/active/vidya-belief-substrate-program.md",
)
APP_READS = (
    "pyproject.toml",
    "scripts/autopilot/core_v2_select.py",
    "scripts/autopilot/experiment_journal.py",
    "scripts/autopilot/journal_shards.py",
    "scripts/benchmark/debug_scorer.py",
    "src/__init__.py",
    "src/autopilot_core/__init__.py",
    "src/autopilot_core/action_identity.py",
    "src/autopilot_core/journal_reconstruction.py",
    "src/autopilot_core/learning_exclusions.py",
    "src/autopilot_core/measurement_guards.py",
    "src/autopilot_core/multitier_decision.py",
    "src/autopilot_core/pareto_math.py",
    "src/autopilot_core/rlvr_tiers.py",
    "src/autopilot_core/sequential_verdict.py",
    "src/autopilot_core/tier_specs.py",
    "tests/conftest.py",
    "tests/unit/test_core_pool_vacuous_oracle.py",
    "uv.lock",
)


def _write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def _install_locked_minimal_set(run_dir: Path) -> tuple[Path, Path]:
    requirements = ROOT / "scripts/ci/rtg02-hosted-requirements.txt"
    log_path = run_dir / "dependency-install.log"
    command = [sys.executable, "-m", "pip", "install", "--require-hashes",
               "--no-deps", "--only-binary=:all:", "-r", str(requirements)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    _write_once(log_path, result.stdout.encode("utf-8"))
    if result.returncode:
        raise RuntimeError(f"locked dependency installation failed: {result.returncode}")
    packages = {"colorama": "0.4.6", "iniconfig": "2.3.0", "packaging": "26.0",
                "pluggy": "1.6.0", "Pygments": "2.20.0", "pytest": "9.0.3"}
    installed = {name: importlib.metadata.version(name) for name in packages}
    if installed != packages:
        raise RuntimeError(f"installed runner package versions differ: {installed}")
    environment = {
        "python": sys.version,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "packages": installed,
    }
    env_path = run_dir / "environment.json"
    _write_once(env_path, (json.dumps(environment, sort_keys=True, separators=(",", ":"))
                           + "\n").encode("utf-8"))
    return log_path, env_path


def _load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("rtg02_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the pinned native conformance carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _source_context(app_root: Path, output: Path) -> Path:
    manifest = output / "source-context.json"
    command = [sys.executable, str(ROOT / "scripts/ci/ni08_source_context.py"),
               "--repo", f"root={ROOT}", "--repo", f"app={app_root}",
               "--output", str(manifest)]
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"source context generation failed: {result.stdout[-2000:]}")
    return manifest


def _exact_cases(record: dict, expected: list[dict]) -> bool:
    summary = record.get("summary")
    if not isinstance(summary, dict):
        return False
    cases = summary.get("cases")
    counts = summary.get("counts")
    if not isinstance(cases, list) or not isinstance(counts, dict):
        return False
    wanted = [(item.get("classname"), item.get("name")) for item in expected]
    if any(not isinstance(cls, str) or not isinstance(name, str) for cls, name in wanted):
        return False
    if len(set(wanted)) != len(wanted):
        return False
    if any(not isinstance(item, dict) or not isinstance(item.get("classname"), str)
           or not isinstance(item.get("name"), str) for item in cases):
        return False
    actual = [(item["classname"], item["name"]) for item in cases]
    expected_counts = {"passed": len(expected), "failure": 0, "error": 0,
                       "skipped": 0, "collected": len(expected), "executed": len(expected)}
    return len(actual) == len(wanted) and sorted(actual) == sorted(wanted) and counts == expected_counts


def _artifact_snapshot(paths: tuple[Path, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        if path.is_dir():
            for leaf in sorted(path.rglob("*")):
                if leaf.is_file() and not leaf.is_symlink():
                    result[str(leaf)] = hashlib.sha256(leaf.read_bytes()).hexdigest()
        elif path.is_file() and not path.is_symlink():
            result[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            result[str(path)] = "absent-or-nonregular"
    return result


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: rtg02_run_native_capture.py APP_ROOT FRESH_RESULT_DIR")
    app_root = Path(sys.argv[1]).resolve()
    run_dir = Path(sys.argv[2]).resolve()
    if not run_dir.is_relative_to(Path(os.environ["RUNNER_TEMP"]).resolve()):
        raise SystemExit("result directory must be under RUNNER_TEMP")
    if run_dir.exists():
        raise SystemExit("result directory already exists; preserve old captures")
    run_dir.mkdir(mode=0o700, parents=True)
    app_commit = subprocess.check_output(
        ["git", "-C", str(app_root), "rev-parse", "HEAD"], text=True).strip()
    if app_commit != APP_PIN:
        raise SystemExit(f"APP checkout must equal reviewed source pin {APP_PIN}")
    install_log, environment = _install_locked_minimal_set(run_dir)
    manifest = _source_context(app_root, run_dir)
    cases_path = ROOT / "scripts/ci/rtg02-expected-cases.json"
    expected_document = json.loads(cases_path.read_bytes())
    expected = expected_document.get("root") if expected_document.get("schema") == "epyc.rtg02.expected_cases/v1" else None
    if not isinstance(expected, list) or len(expected) != 23:
        raise RuntimeError("expected-case manifest must contain all 23 reviewed identities")
    nodeids = [item["nodeid"] for item in expected]
    if any(not isinstance(nodeid, str) or not nodeid.startswith("tests/unit/") for nodeid in nodeids):
        raise RuntimeError("expected-case node IDs must be bounded APP unit tests")
    if len(set(nodeids)) != len(nodeids):
        raise RuntimeError("duplicate selected case node ID")

    os.environ.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                       "PYTHONDONTWRITEBYTECODE": "1",
                       "PYTHONHASHSEED": "0",
                       "PYTHONUNBUFFERED": "1"})
    reads = ([ROOT / name for name in ROOT_READS]
             + [app_root / name for name in APP_READS]
             + [manifest, install_log, environment])
    junit = run_dir / "app-original-junit.xml"
    native_output = run_dir / "app-native"
    venv = (Path(os.environ["RUNNER_TEMP"]) / "rtg02-native" / "venv").resolve()
    if Path(sys.prefix).resolve() != venv:
        raise RuntimeError("pytest must run from the isolated RTG02 capture virtualenv")
    argv = [sys.executable, "-m", "pytest", "-q", "--noconftest",
            "-c", "/dev/null", f"--rootdir={app_root}", "-o", "addopts=",
            "-p", "no:cacheprovider", f"--junitxml={junit}", *nodeids]
    carrier = _load_carrier()
    record = carrier.capture_fixture_execution(
        argv=argv, cwd=app_root, junit=junit, output=native_output,
        repositories={"root": str(ROOT), "app": str(app_root)},
        read_paths=reads, selections=nodeids,
    )
    exact = _exact_cases(record, expected)
    execution_ok = record.get("fixture_execution_conformant") is True and exact
    sharedgrade_inputs = (native_output, junit, manifest, environment, install_log)
    before = _artifact_snapshot(sharedgrade_inputs)
    grades = {}
    grade_error = ""
    if execution_ok:
        try:
            sys.path.insert(0, str(ROOT))
            sys.path.insert(0, str(ROOT / "scripts/vidya"))
            from adapters.ci_conformance import native_rows, project_ci_conformance
            from claim_tuple import grade
            native = native_rows(native_output / "receipt.json")
            if len(native) != 1:
                raise RuntimeError("RTG02 receipt did not yield exactly one shared-verifier tuple")
            q, t, _reasons = grade(project_ci_conformance(native[0]))
            grades = {"Q": q, "T": t}
            if (q, t) != ("Judged", "Located"):
                raise RuntimeError("existing shared-verifier grade differs from its ceiling")
        except Exception as exc:
            grade_error = f"{type(exc).__name__}: {exc}"
    after = _artifact_snapshot(sharedgrade_inputs)
    validation = {
        "schema": "epyc.rtg02.hosted_validation/v1",
        "app_commit_expected": APP_PIN,
        "selected_case_count": len(expected),
        "exact_selected_cases": exact,
        "summary_present": isinstance(record.get("summary"), dict),
        "summary_counts": record.get("summary", {}).get("counts")
            if isinstance(record.get("summary"), dict) else None,
        "fixture_execution_conformant": record.get("fixture_execution_conformant"),
        "receipt_sha256": record.get("receipt_sha256"),
        "shared_verifier_grade": grades,
        "shared_verifier_error": grade_error,
        "original_hashes_before_sharedgrade": before,
        "original_hashes_after_sharedgrade": after,
        "sharedgrade_inputs_unchanged": before == after,
        "scope": "synthetic source-only; no inference, code execution scorer, LLM/math verifier, pool rebuild, or grading change",
    }
    _write_once(run_dir / "validation.json",
                (json.dumps(validation, sort_keys=True, separators=(",", ":")) + "\n").encode())
    if not execution_ok or not validation["sharedgrade_inputs_unchanged"] or grade_error:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
