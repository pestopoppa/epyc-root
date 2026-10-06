#!/usr/bin/env python3
"""Capture bounded prospective RAW-anchor controls with the existing native carrier."""
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
APP_LOCK_PIN = "cfcf3768716de888a971bf66489397f5b91241df"
ROOT_READS = (
    ".github/workflows/vb-raw-anchor-native.yml",
    "scripts/ci/run_vb_raw_anchor_capture.py",
    "scripts/ci/vb_raw_anchor_expected_cases.json",
    "scripts/ci/vb_raw_anchor_requirements.txt",
    "scripts/ci/ni08_source_context.py",
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/README.md",
    "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/adapters/research_intake.py",
    "scripts/vidya/alias_candidates.py",
    "scripts/vidya/canonical.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/fold.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/impact.py",
    "scripts/vidya/intake_assertion_kinds.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/machine_anchor.py",
    "scripts/vidya/raw_anchor_store.py",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/vidya/test_impact_coverage_anchor_level.py",
    "tests/vidya/test_raw_anchor_store.py",
    "tests/vidya/test_vidya_alias.py",
    "tests/vidya/test_vidya_machine_anchor.py",
    "pyproject.toml",
    "handoffs/active/vidya-belief-substrate-program.md",
)
APP_READS = ("uv.lock",)


def _write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def _install_locked_minimal_set(run_dir: Path) -> tuple[Path, Path]:
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.13.15":
        raise RuntimeError("capture requires the accepted CPython 3.13.15 runner")
    requirements = ROOT / "scripts/ci/vb_raw_anchor_requirements.txt"
    log_path = run_dir / "dependency-install.log"
    command = [sys.executable, "-m", "pip", "install", "--require-hashes",
               "--no-deps", "--only-binary=:all:", "-r", str(requirements)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    _write_once(log_path, result.stdout.encode("utf-8"))
    if result.returncode:
        raise RuntimeError(f"locked dependency installation failed: {result.returncode}")
    packages = {"colorama": "0.4.6", "iniconfig": "2.3.0", "packaging": "26.0",
                "pluggy": "1.6.0", "Pygments": "2.20.0", "pytest": "9.0.3",
                "PyYAML": "6.0.3"}
    installed = {name: importlib.metadata.version(name) for name in packages}
    if installed != packages:
        raise RuntimeError(f"installed runner package versions differ: {installed}")
    environment = {"python": sys.version, "python_version": platform.python_version(),
                   "platform": platform.platform(), "packages": installed}
    env_path = run_dir / "environment.json"
    _write_once(env_path, (json.dumps(environment, sort_keys=True, separators=(",", ":"))
                           + "\n").encode("utf-8"))
    return log_path, env_path


def _load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("vb_raw_anchor_native_conformance", path)
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
    cases, counts = summary.get("cases"), summary.get("counts")
    if not isinstance(cases, list) or not isinstance(counts, dict):
        return False
    wanted = [(item.get("classname"), item.get("name")) for item in expected]
    if (any(not isinstance(cls, str) or not isinstance(name, str) for cls, name in wanted)
            or len(set(wanted)) != len(wanted)):
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
        raise SystemExit("usage: run_vb_raw_anchor_capture.py APP_LOCK_ROOT FRESH_RESULT_DIR")
    app_root = Path(sys.argv[1]).resolve()
    run_dir = Path(sys.argv[2]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not run_dir.is_relative_to(runner_temp):
        raise SystemExit("result directory must be under RUNNER_TEMP")
    if run_dir.exists():
        raise SystemExit("result directory already exists; preserve old captures")
    run_dir.mkdir(mode=0o700, parents=True)
    app_commit = subprocess.check_output(
        ["git", "-C", str(app_root), "rev-parse", "HEAD"], text=True).strip()
    if app_commit != APP_LOCK_PIN:
        raise SystemExit(f"APP lock checkout must equal pinned source {APP_LOCK_PIN}")
    install_log, environment = _install_locked_minimal_set(run_dir)
    manifest = _source_context(app_root, run_dir)
    cases_path = ROOT / "scripts/ci/vb_raw_anchor_expected_cases.json"
    expected_document = json.loads(cases_path.read_bytes())
    expected = (expected_document.get("root")
                if expected_document.get("schema") == "epyc.vb_raw_anchor.expected_cases/v1"
                else None)
    if not isinstance(expected, list) or len(expected) != 51:
        raise RuntimeError("expected-case manifest must contain all 51 reviewed identities")
    nodeids = []
    for item in expected:
        classname, name = item.get("classname"), item.get("name")
        if not isinstance(classname, str) or not classname.startswith("tests.vidya."):
            raise RuntimeError("expected class must be a selected ROOT Vidya test module")
        if not isinstance(name, str) or not name:
            raise RuntimeError("expected JUnit test name must be nonempty")
        test_path = classname.replace(".", "/") + ".py"
        nodeids.append(f"{test_path}::{name}")
    if len(set(nodeids)) != len(nodeids):
        raise RuntimeError("duplicate selected case node ID")
    os.environ.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                       "PYTHONDONTWRITEBYTECODE": "1",
                       "PYTHONHASHSEED": "0",
                       "PYTHONUNBUFFERED": "1"})
    venv = (Path(os.environ["RUNNER_TEMP"]) / "vb-raw-anchor" / "venv").resolve()
    if Path(sys.prefix).resolve() != venv:
        raise RuntimeError("pytest must run from the isolated RAW-anchor capture virtualenv")
    reads = ([ROOT / name for name in ROOT_READS]
             + [app_root / name for name in APP_READS]
             + [manifest, install_log, environment])
    junit = run_dir / "original-junit.xml"
    native_output = run_dir / "native"
    argv = [sys.executable, "-m", "pytest", "-q", "--noconftest",
            "-c", "/dev/null", f"--rootdir={ROOT}", "-o", "addopts=",
            "-p", "no:cacheprovider", f"--junitxml={junit}", *nodeids]
    record = _load_carrier().capture_fixture_execution(
        argv=argv, cwd=ROOT, junit=junit, output=native_output,
        repositories={"root": str(ROOT), "app": str(app_root)},
        read_paths=reads, selections=nodeids,
    )
    exact = _exact_cases(record, expected)
    execution_ok = record.get("fixture_execution_conformant") is True and exact
    sharedgrade_inputs = (native_output, junit, manifest, environment, install_log)
    before = _artifact_snapshot(sharedgrade_inputs)
    grades, grade_error = {}, ""
    if execution_ok:
        try:
            sys.path.insert(0, str(ROOT))
            sys.path.insert(0, str(ROOT / "scripts/vidya"))
            from adapters.ci_conformance import native_rows, project_ci_conformance
            from claim_tuple import grade
            native = native_rows(native_output / "receipt.json")
            if len(native) != 1:
                raise RuntimeError("RAW anchor receipt did not yield exactly one shared-verifier tuple")
            q, t, _reasons = grade(project_ci_conformance(native[0]))
            grades = {"Q": q, "T": t}
            if (q, t) != ("Judged", "Located"):
                raise RuntimeError("existing shared-verifier grade differs from its ceiling")
        except Exception as exc:
            grade_error = f"{type(exc).__name__}: {exc}"
    after = _artifact_snapshot(sharedgrade_inputs)
    validation = {
        "schema": "epyc.vb_raw_anchor.hosted_validation/v1",
        "app_lock_commit_expected": APP_LOCK_PIN,
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
        "scope": "synthetic source-only; no live fetch, canonical intake/ledger write, old-anchor backfill, inference, or new grading rule",
    }
    _write_once(run_dir / "validation.json",
                (json.dumps(validation, sort_keys=True, separators=(",", ":")) + "\n").encode())
    if not execution_ok or not validation["sharedgrade_inputs_unchanged"] or grade_error:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
