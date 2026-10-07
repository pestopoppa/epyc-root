#!/usr/bin/env python3
"""Capture source-only AP62 invocation-log controls through the existing carrier."""
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
APP_PIN = "578865fb633d09839547a54f6bf9378b0b934dd6"
ROOT_READS = (
    ".github/workflows/ap62-invocation-log-native.yml",
    "scripts/ci/run_ap62_native_capture.py",
    "scripts/ci/ap62-expected-cases.json",
    "scripts/ci/ap62-app-source-readset.json",
    "scripts/ci/ap62-package-versions.json",
    "scripts/ci/ap62-hosted-requirements.txt",
    "scripts/ci/ni08_source_context.py",
    "scripts/ci/native_conformance.py",
    "docs/reviews/ni08-ap62-native-capture-recipe-20261006.md",
    "scripts/vidya/adapters/README.md",
    "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/claim_tuple.py",
    "tests/__init__.py",
    "handoffs/active/autopilot-continuous-optimization.md",
)


def _write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def _install(run_dir: Path) -> tuple[Path, Path, dict[str, str]]:
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.13.15":
        raise RuntimeError("capture requires the accepted CPython 3.13.15 runner")
    requirements = ROOT / "scripts/ci/ap62-hosted-requirements.txt"
    log = run_dir / "dependency-install.log"
    argv = [sys.executable, "-m", "pip", "install", "--require-hashes", "--no-deps",
            "--only-binary=:all:", "-r", str(requirements)]
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    _write_once(log, result.stdout.encode("utf-8"))
    if result.returncode:
        raise RuntimeError(f"locked wheel installation failed: {result.returncode}")
    expected = json.loads((ROOT / "scripts/ci/ap62-package-versions.json").read_bytes())
    if expected.get("schema") != "epyc.ap62.package_versions/v1" or not isinstance(expected.get("versions"), dict):
        raise RuntimeError("invalid dependency-version manifest")
    packages = expected["versions"]
    actual = {name: importlib.metadata.version(name) for name in packages}
    if actual != packages:
        raise RuntimeError("installed package versions differ from the pinned lock")
    api_path_overrides = {
        "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": str(run_dir / "absent-kernel-paths" / "llama-cpp-bin"),
        "ORCHESTRATOR_PATHS_LLAMA_MTMD": str(run_dir / "absent-kernel-paths" / "llama-mtmd-cli"),
        "ORCHESTRATOR_PATHS_LLAMA_SERVER": str(run_dir / "absent-kernel-paths" / "llama-server"),
    }
    if any(Path(value).exists() for value in api_path_overrides.values()):
        raise RuntimeError("API config placeholders unexpectedly resolve to filesystem paths")
    os.environ.update(api_path_overrides)
    environment = {"python": sys.version, "python_version": platform.python_version(),
                   "platform": platform.platform(), "packages": actual,
                   "api_config_path_overrides": api_path_overrides}
    env = run_dir / "environment.json"
    _write_once(env, (json.dumps(environment, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return log, env, actual


def _load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("ap62_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the pinned native carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _source_context(app_root: Path, output: Path) -> Path:
    manifest = output / "source-context.json"
    argv = [sys.executable, str(ROOT / "scripts/ci/ni08_source_context.py"),
            "--repo", f"root={ROOT}", "--repo", f"app={app_root}", "--output", str(manifest)]
    result = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"source context generation failed: {result.stdout[-2000:]}")
    return manifest


def _exact(record: dict, expected: list[dict]) -> bool:
    summary = record.get("summary")
    if not isinstance(summary, dict):
        return False
    cases, counts = summary.get("cases"), summary.get("counts")
    if not isinstance(cases, list) or not isinstance(counts, dict):
        return False
    wanted = [(x.get("classname"), x.get("name")) for x in expected]
    if any(not isinstance(a, str) or not isinstance(b, str) for a, b in wanted) or len(set(wanted)) != len(wanted):
        return False
    if any(not isinstance(x, dict) or not isinstance(x.get("classname"), str) or not isinstance(x.get("name"), str) for x in cases):
        return False
    actual = [(x["classname"], x["name"]) for x in cases]
    want_counts = {"passed": len(expected), "failure": 0, "error": 0, "skipped": 0,
                   "collected": len(expected), "executed": len(expected)}
    return len(actual) == len(wanted) and sorted(actual) == sorted(wanted) and counts == want_counts


def _snapshot(paths: tuple[Path, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        if path.is_dir():
            for leaf in sorted(path.rglob("*")):
                if leaf.is_file() and not leaf.is_symlink():
                    out[str(leaf)] = hashlib.sha256(leaf.read_bytes()).hexdigest()
        elif path.is_file() and not path.is_symlink():
            out[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            out[str(path)] = "absent-or-nonregular"
    return out


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_ap62_native_capture.py APP_ROOT FRESH_RESULT_DIR")
    app_root, run_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not run_dir.is_relative_to(runner_temp):
        raise SystemExit("result directory must be under RUNNER_TEMP")
    if run_dir.exists():
        raise SystemExit("result directory exists; preserve earlier captures")
    run_dir.mkdir(mode=0o700, parents=True)
    commit = subprocess.check_output(["git", "-C", str(app_root), "rev-parse", "HEAD"], text=True).strip()
    if commit != APP_PIN:
        raise SystemExit(f"APP checkout must equal reviewed source pin {APP_PIN}")
    if os.environ.get("ORCHESTRATOR_MOCK_MODE") != "1":
        raise SystemExit("the isolated source-only capture requires ORCHESTRATOR_MOCK_MODE=1")
    install_log, environment, _packages = _install(run_dir)
    manifest = _source_context(app_root, run_dir)
    readset_doc = json.loads((ROOT / "scripts/ci/ap62-app-source-readset.json").read_bytes())
    if readset_doc.get("schema") != "epyc.ap62.app_source_readset/v1" or readset_doc.get("app_commit") != APP_PIN:
        raise RuntimeError("APP source readset does not match reviewed commit")
    app_reads = readset_doc.get("paths")
    if not isinstance(app_reads, list) or len(app_reads) != 434 or len(set(app_reads)) != len(app_reads):
        raise RuntimeError("expected exact 434-path reviewed APP closure")
    for rel in app_reads:
        path = (app_root / rel).resolve()
        if not path.is_relative_to(app_root) or not path.is_file():
            raise RuntimeError("APP readset contains a missing or escaping source path")
    case_doc = json.loads((ROOT / "scripts/ci/ap62-expected-cases.json").read_bytes())
    expected = case_doc.get("app") if case_doc.get("schema") == "epyc.ap62.expected_cases/v1" else None
    if not isinstance(expected, list) or len(expected) != 14:
        raise RuntimeError("expected all 14 selected invocation-log controls")
    nodeids = [item.get("nodeid") for item in expected]
    if any(not isinstance(n, str) or not n.startswith("tests/unit/test_invocation_log_request_scope.py::") for n in nodeids):
        raise RuntimeError("case manifest contains an out-of-scope node ID")
    if len(set(nodeids)) != len(nodeids):
        raise RuntimeError("duplicate selected test case")
    os.environ.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
                       "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1", "ORCHESTRATOR_MOCK_MODE": "1"})
    reads = [ROOT / name for name in ROOT_READS] + [app_root / name for name in app_reads]
    reads += [manifest, install_log, environment]
    junit = run_dir / "app-original-junit.xml"
    output = run_dir / "app-native"
    venv = (runner_temp / "ap62-native" / "venv").resolve()
    if Path(sys.prefix).resolve() != venv:
        raise RuntimeError("pytest must run from the isolated AP62 capture virtualenv")
    argv = [sys.executable, "-m", "pytest", "-q", "--noconftest", "-c", "/dev/null",
            f"--rootdir={app_root}", "-o", "addopts=", "-p", "no:cacheprovider",
            f"--junitxml={junit}", *nodeids]
    record = _load_carrier().capture_fixture_execution(argv=argv, cwd=app_root, junit=junit,
        output=output, repositories={"root": str(ROOT), "app": str(app_root)},
        read_paths=reads, selections=nodeids)
    exact = _exact(record, expected)
    before = _snapshot((output, junit, manifest, install_log, environment))
    api_paths = json.loads(environment.read_bytes()).get("api_config_path_overrides", {})
    if not isinstance(api_paths, dict) or set(api_paths) != {
        "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN", "ORCHESTRATOR_PATHS_LLAMA_MTMD",
        "ORCHESTRATOR_PATHS_LLAMA_SERVER",
    }:
        raise RuntimeError("environment receipt lacks the exact API config placeholder set")
    placeholders_absent_after = all(not Path(value).exists() for value in api_paths.values())
    grades, grade_error = {}, ""
    if record.get("fixture_execution_conformant") is True and exact:
        try:
            sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts/vidya"))
            from adapters.ci_conformance import native_rows, project_ci_conformance
            from claim_tuple import grade
            native = native_rows(output / "receipt.json")
            if len(native) != 1:
                raise RuntimeError("AP62 receipt did not produce exactly one verifier tuple")
            q, t, _ = grade(project_ci_conformance(native[0]))
            grades = {"Q": q, "T": t}
            if (q, t) != ("Judged", "Located"):
                raise RuntimeError("existing shared verifier returned an unexpected ceiling")
        except Exception as exc:
            grade_error = f"{type(exc).__name__}: {exc}"
    after = _snapshot((output, junit, manifest, install_log, environment))
    validation = {"schema": "epyc.ap62.hosted_validation/v1", "app_commit": commit,
        "selected_case_count": len(expected), "exact_selected_cases": exact,
        "fixture_execution_conformant": record.get("fixture_execution_conformant"),
        "summary": record.get("summary"), "receipt_sha256": record.get("receipt_sha256"),
        "shared_verifier_grade": grades, "shared_verifier_error": grade_error,
        "input_hashes_before_sharedgrade": before, "input_hashes_after_sharedgrade": after,
        "sharedgrade_inputs_unchanged": before == after,
        "api_config_placeholders_absent_after_capture": placeholders_absent_after,
        "scope": "synthetic source-only controls; no live API/server, inference, production concurrency rate, or deployment claim"}
    _write_once(run_dir / "validation.json", (json.dumps(validation,sort_keys=True,separators=(",",":"))+'\n').encode())
    if (record.get("fixture_execution_conformant") is not True or not exact or before != after
            or not placeholders_absent_after or grade_error):
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
