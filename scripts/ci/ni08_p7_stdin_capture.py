"""Capture the unchanged HS-4 P0.4/HS-19a/probe offline suites natively."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
PYTHON_PIN = "3.13.15"
NODE_PIN = "v22.18.0"
SELECTIONS = (
    "tests/harness/test_hs4_p04_acceptance.py",
    "tests/harness/test_hs19a_acceptance.py",
    "tests/harness/test_task_delegation_probe.py",
)
EXPECTED_CASES = 138
LOCKED_PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3",
}
INSTALL_REQUIREMENTS = "scripts/ci/ni08_p7_stdin_capture_requirements.txt"
INSTALL_COMMAND = (
    "python -m pip install --require-hashes -r "
    "recipe/scripts/ci/ni08_p7_stdin_capture_requirements.txt"
)
WORKFLOW = ".github/workflows/ni08-p7-stdin-capture.yml"
APP_LOCK = "uv.lock"

ROOT_READS = (
    *SELECTIONS,
    "scripts/harness/hs4_p04_acceptance.py",
    "scripts/harness/hs19a_acceptance.py",
    "scripts/harness/task_delegation_probe.py",
    "scripts/vidya/adapters/opencode_shell_run_capture.py",
    "scripts/vidya/canonical.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/lattice.py",
    "harness/opencode-plugin/config/opencode.env",
    "harness/opencode-plugin/config/opencode.jsonc.template",
    "harness/opencode-plugin/config/opencode.subagents.jsonc.template",
    "harness/opencode-plugin/scripts/lint-config.ts",
    "harness/opencode-plugin/src/config-lint.ts",
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


def require_clean(repo: Path, label: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"{label} checkout is not clean: {status}")
    return git(repo, "rev-parse", "HEAD")


def regular_repo_file(repo: Path, name: str) -> Path:
    path = repo
    for part in Path(name).parts:
        path = path / part
        if path.is_symlink():
            raise RuntimeError(f"declared read traverses a symlink: {name}")
    if not path.is_file():
        raise RuntimeError(f"declared read is missing or not a regular file: {name}")
    mode = git(repo, "ls-tree", "HEAD", "--", name).split(maxsplit=1)[0]
    if mode != "100644":
        raise RuntimeError(f"declared read is not a tracked regular file: {name}")
    return path.absolute()


def verify_dependencies(app: Path, requirements: Path) -> None:
    lock = tomllib.loads((app / APP_LOCK).read_text(encoding="utf-8"))
    locked = {item["name"].lower(): item for item in lock["package"]}
    hashes = {}
    for name, version in LOCKED_PACKAGES.items():
        record = locked.get(name)
        if not record or record["version"] != version:
            raise RuntimeError(f"{name} differs from the pinned APP uv.lock")
        wheels = [w["hash"] for w in record.get("wheels", [])]
        if not wheels or any(not h.startswith("sha256:") for h in wheels):
            raise RuntimeError(f"{name} has no complete wheel hashes in APP uv.lock")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from {version}")
        hashes[name] = sorted(wheels)
    text = requirements.read_text(encoding="utf-8")
    for name, versions in LOCKED_PACKAGES.items():
        if f"{name}=={versions}" not in text and f"{name.title()}=={versions}" not in text:
            raise RuntimeError(f"requirements hashlock omits {name}=={versions}")
        for digest in hashes[name]:
            if digest not in text:
                raise RuntimeError(f"requirements hashlock omits an APP wheel for {name}")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / n for n in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni08-p7-stdin-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status: dict[str, Any] = {"state": "preparing", "job": "hs4-p7-stdin-capture",
                              "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        node_version = subprocess.check_output(["node", "--version"], text=True).strip()
        if node_version != NODE_PIN:
            raise RuntimeError(f"Node runtime differs from pin: {node_version}")
        if os.environ.get("NI08_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        expected = {"recipe": os.environ["GITHUB_SHA"], "carrier": ROOT_CARRIER_PIN,
                    "app": APP_PIN}
        pins = {name: require_clean(repo, name) for name, repo in repos.items()}
        if pins != expected:
            raise RuntimeError(f"repository pins differ: {pins}")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN:
            raise RuntimeError("workflow carrier pin differs from reviewed carrier")
        if os.environ.get("APP_PIN") != APP_PIN:
            raise RuntimeError("workflow APP dependency-lock pin differs")
        root_reads = [regular_repo_file(recipe, p) for p in ROOT_READS]
        carrier_reads = [regular_repo_file(carrier, p) for p in CARRIER_READS]
        app_lock = regular_repo_file(app, APP_LOCK)
        requirements = regular_repo_file(recipe, INSTALL_REQUIREMENTS)
        workflow = regular_repo_file(recipe, WORKFLOW)
        verify_dependencies(app, requirements)

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "node": node_version, "platform": platform.platform(),
            "repositories": pins, "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES,
            "dependency_lock": {"repo": "app", "pin": APP_PIN, "path": APP_LOCK,
                                "sha256": hashlib.sha256(app_lock.read_bytes()).hexdigest()},
            "dependency_set": LOCKED_PACKAGES,
            "dependency_basis": (
                "Three exact ROOT harness test modules use pytest plus Python stdlib. Their only "
                "external executable is the OpenCode config linter, run by Node 22.18.0 from "
                "checked-in TypeScript sources with built-in type stripping; no npm "
                "install/build. Python package versions "
                "and wheel hashes are checked against the pinned APP uv.lock and the local "
                "requirements hashlock."
            ),
            "isolation": (
                "Only selected offline tests run. OpenCode, model/inference, orchestrator API, "
                "benchmarks, kernels, network requests, and live corpus are never invoked. "
                "Generated scripts use the test's bounded fake binaries or shell syntax check. "
                "Belief capture writes only under pytest temporary directories."
            ),
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite existing capture outputs")
        read_paths = [workflow, requirements, app_lock, *root_reads, *carrier_reads]
        producer_argv = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(recipe), "--junit", str(junit), "--output", str(native),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
            "--repo", f"app={app}",
        ]
        for path in dict.fromkeys(p.resolve() for p in read_paths):
            producer_argv.extend(["--read-path", str(path)])
        for selection in SELECTIONS:
            producer_argv.extend(["--select", selection])
        command = [sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
                   "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}"]
        status.update(state="running", repositories=pins, selections=list(SELECTIONS))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer_argv, "--", *command], cwd=recipe)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1,
                          diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        counts = (receipt.get("summary") or {}).get("counts") or {}
        cases_ok = (counts.get("collected") == EXPECTED_CASES
                    and counts.get("executed") == EXPECTED_CASES
                    and counts.get("skipped") == 0
                    and counts.get("failure") == 0 and counts.get("error") == 0)

        originals = [*sorted(native.iterdir()), junit, freeze, environment]
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        sys.path.insert(0, str(carrier))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        analysis: dict[str, Any] = {
            "kind": "analysis_of_existing_fixture_receipt",
            "native_original_hashes": before, "repositories": pins,
            "fixture_rerun": False, "new_native_receipt_authored_by_analysis": False,
            "metric": metric, "grade": None,
        }
        if rows:
            if len(rows) != 1:
                raise RuntimeError("original receipt projection is not unique")
            claim = project_ci_conformance(rows[0])
            q, t, reasons = grade(claim)
            analysis.update(measurement_id=claim.measurement_id, source_kind=claim.source_kind,
                            binding_kind=claim.binding_kind,
                            grade={"Q": q, "T": t, "reasons": reasons})
            if (q, t) != ("Judged", "Located"):
                raise RuntimeError("fixture observation grade differs from reviewed expectation")
        else:
            analysis["projection"] = "unknown native disposition; no claim or grade invented"
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
        if before != after:
            raise RuntimeError("shared-grade analysis changed an original")
        with (result / "shared-grade.json").open("x", encoding="utf-8") as handle:
            json.dump(analysis, handle, indent=2, sort_keys=True)
            handle.write("\n")
        passed = code == 0 and metric is True and cases_ok
        status.update(state="passed" if passed else "failed",
                      exit_code=0 if passed else (code or 1), native_metric=metric,
                      junit_counts=counts, expected_case_count=EXPECTED_CASES,
                      all_cases_executed=cases_ok)
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
