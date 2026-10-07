#!/usr/bin/env python3
"""Capture SC78 mechanical anchor controls through the existing verifier carrier."""
from __future__ import annotations

import collections
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import stat
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
APP_PIN = "cfcf3768716de888a971bf66489397f5b91241df"
ROOT_READS = (
    ".github/workflows/sc78-numeric-anchor-native.yml",
    "scripts/ci/sc78_native_capture.py",
    "scripts/ci/sc78_expected_cases.json",
    "scripts/ci/sc78_hosted_requirements.txt",
    "scripts/ci/ni08_source_context.py",
    "scripts/ci/native_conformance.py",
    "scripts/vidya/adapters/README.md",
    "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/adapters/research_intake.py",
    "scripts/vidya/alias_candidates.py",
    "scripts/vidya/canonical.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/measurement_record.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/intake_assertion_kinds.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/machine_anchor.py",
    "scripts/vidya/raw_anchor_store.py",
    "tests/__init__.py",
    "tests/vidya/test_raw_anchor_store.py",
    "tests/vidya/test_research_intake_nonclaim_fixtures.py",
    "handoffs/active/vidya-belief-substrate-program.md",
)
PACKAGES = {"colorama": "0.4.6", "iniconfig": "2.3.0", "packaging": "26.0",
            "pluggy": "1.6.0", "Pygments": "2.20.0", "pytest": "9.0.3",
            "PyYAML": "6.0.3"}


def write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def source_context(app: Path, path: Path) -> None:
    command = [sys.executable, str(ROOT / "scripts/ci/ni08_source_context.py"),
               "--repo", f"root={ROOT}", "--repo", f"app={app}", "--output", str(path)]
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"source context failed: {result.stdout[-2000:]}")


def load_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("sc78_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing native verifier carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def regular_bytes(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"declared input is not a regular file: {path}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)


def snapshots(paths: list[Path]) -> dict[str, dict[str, object]]:
    result = {}
    for path in paths:
        data = regular_bytes(path)
        result[str(path)] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return result


def result_tree_snapshot(directory: Path) -> dict[str, dict[str, object]]:
    """Seal every original in the result tree across shared-grade analysis."""
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"symlink appeared in capture result tree: {path}")
        if path.is_dir():
            continue
        data = regular_bytes(path)
        result[str(path.relative_to(directory))] = {
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return result


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: sc78_native_capture.py APP_ROOT RESULT_DIR")
    app, result = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    runner_temp_value = os.environ.get("RUNNER_TEMP")
    if not runner_temp_value:
        raise RuntimeError("RUNNER_TEMP is required for isolated capture")
    runner_temp = Path(runner_temp_value).resolve()
    expected_venv = (runner_temp / "sc78" / "venv").resolve()
    if Path(sys.prefix).resolve() != expected_venv:
        raise RuntimeError("capture is not running from the isolated RUNNER_TEMP virtualenv")
    if platform.python_implementation() != "CPython" or platform.python_version() != "3.13.15":
        raise RuntimeError("capture requires the accepted CPython 3.13.15 runner")
    if os.environ.get("APP_PIN") != APP_PIN:
        raise RuntimeError("workflow APP_PIN differs from the source-bound lock revision")
    if subprocess.check_output(["git", "-C", str(app), "rev-parse", "HEAD"], text=True).strip() != APP_PIN:
        raise RuntimeError("APP lock checkout differs from the bound dependency source")
    if not result.is_relative_to(runner_temp) or os.path.lexists(result):
        raise RuntimeError("result directory must be fresh and contained under RUNNER_TEMP")
    requirements = ROOT / "scripts/ci/sc78_hosted_requirements.txt"
    install_log = result / "dependency-install.log"
    result.mkdir(parents=True, exist_ok=False)
    install = subprocess.run([sys.executable, "-m", "pip", "install", "--require-hashes",
                              "--no-deps", "--only-binary=:all:", "-r", str(requirements)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, check=False)
    write_once(install_log, install.stdout.encode())
    if install.returncode:
        raise RuntimeError(f"locked wheel installation failed: {install.returncode}")
    actual = {name: importlib.metadata.version(name) for name in PACKAGES}
    if actual != PACKAGES:
        raise RuntimeError("installed packages differ from pinned minimal test closure")
    environment = {"python": sys.version, "python_version": platform.python_version(),
                   "platform": platform.platform(), "packages": actual,
                   "app_pin": APP_PIN}
    write_once(result / "environment.json",
               (json.dumps(environment, sort_keys=True, separators=(",", ":")) + "\n").encode())
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    if freeze.returncode:
        raise RuntimeError("cannot record isolated environment package inventory")
    write_once(result / "pip-freeze.txt", freeze.stdout.encode())
    context = result / "source-context.json"
    source_context(app, context)
    junit = result / "selected.junit.xml"
    receipt_dir = result / "native"
    command = [sys.executable, "-m", "pytest", "--noconftest", "-c", "/dev/null", "--rootdir", str(ROOT),
               "-o", "addopts=", "-p", "no:cacheprovider", "-q", f"--junitxml={junit}", "tests/vidya/test_raw_anchor_store.py",
               "tests/vidya/test_research_intake_nonclaim_fixtures.py"]
    read_paths = [ROOT / item for item in ROOT_READS] + [app / "uv.lock", context,
                  result / "environment.json", install_log, result / "pip-freeze.txt"]
    carrier = load_carrier()
    record = carrier.capture_fixture_execution(
        argv=command, cwd=ROOT, junit=junit, output=receipt_dir,
        repositories={"root": ROOT, "app": app}, read_paths=read_paths,
        selections=["tests/vidya/test_raw_anchor_store.py",
                    "tests/vidya/test_research_intake_nonclaim_fixtures.py"])
    expected = json.loads(regular_bytes(ROOT / "scripts/ci/sc78_expected_cases.json"))
    summary = record.get("summary")
    if not isinstance(summary, dict) or not isinstance(summary.get("cases"), list) or not isinstance(summary.get("counts"), dict):
        raise RuntimeError("native receipt has no validated JUnit summary")
    wanted = [(row["classname"], row["name"]) for row in expected["cases"]]
    actual_cases = [(row["classname"], row["name"]) for row in summary["cases"]]
    if len(actual_cases) != len(set(actual_cases)):
        raise RuntimeError("native JUnit contains duplicate identities")
    counts = summary["counts"]
    if collections.Counter(actual_cases) != collections.Counter(wanted) or counts != {"collected": 23, "executed": 23, "passed": 23,
                                            "failure": 0, "error": 0, "skipped": 0}:
        raise RuntimeError("native JUnit identities/counts differ from the exact 23-case manifest")
    if record.get("fixture_execution_conformant") is not True:
        raise RuntimeError("existing fixture verifier did not produce a conformant receipt")
    source_before = snapshots(read_paths)
    originals_before = result_tree_snapshot(result)
    sys.path.insert(0, str(ROOT / "scripts/vidya"))
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade
    rows = native_rows(str(receipt_dir / "receipt.json"))
    if len(rows) != 1:
        raise RuntimeError("existing CI conformance adapter did not project one native row")
    judgment = grade(project_ci_conformance(rows[0]))
    if judgment[0:2] != ("Judged", "Located"):
        raise RuntimeError("existing shared ClaimTuple ladder did not return Judged/Located")
    source_after = snapshots(read_paths)
    originals_after = result_tree_snapshot(result)
    if source_before != source_after or originals_before != originals_after:
        raise RuntimeError("source inputs or original native/JUnit custody changed during shared grading")
    check = {"receipt": str(receipt_dir / "receipt.json"), "fixture_cases": 23,
             "grade": judgment[0], "location": judgment[1],
             "scope": "synthetic mechanical anchor fixtures only",
             "source_inputs_before": source_before, "source_inputs_after": source_after,
             "original_result_tree_before": originals_before,
             "original_result_tree_after": originals_after}
    write_once(result / "shared-grade-check.json",
               (json.dumps(check, sort_keys=True, separators=(",", ":")) + "\n").encode())
    print(json.dumps(check, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
