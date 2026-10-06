"""Capture AP-ME1/3 synthetic controls through the pinned native receipt carrier.

Execution is intended for the isolated hosted workflow only. This source does not
import the APP, invoke a main trial producer, or touch any live journal.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

APP_PIN = "3dec5ccde33d9d1c1c8472187d581f5b5277ef74"
ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
SELECTIONS = [
    "tests/unit/test_mutation_diagnostics.py",
    "tests/unit/test_failure_signatures.py",
    "tests/unit/test_behavior_signature.py",
    "tests/unit/test_bsv_observe.py",
]
REQUIREMENTS = "scripts/ci/ap_me1_me3_test_requirements.txt"
READSET_MAP = "scripts/ci/ap_me1_me3_source_readset.json"
WORKFLOW = ".github/workflows/ap-me1-me3-capture.yml"
DRIVER = "scripts/ci/ap_me1_me3_capture.py"
CASE_GUARD = "scripts/ci/ap_me1_me3_case_guard.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def verify_identity(repo: Path, expected: str, label: str) -> None:
    actual = git(repo, "rev-parse", "HEAD")
    if actual != expected:
        raise RuntimeError(f"{label} revision mismatch: expected {expected}, got {actual}")
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"{label} checkout has tracked modifications")


def verify_file_records(repo: Path, records: list[dict], label: str) -> list[Path]:
    paths = []
    for item in records:
        relative = item.get("path")
        expected = item.get("sha256")
        if not isinstance(relative, str) or not relative or relative.startswith("/") or ".." in Path(relative).parts:
            raise RuntimeError(f"invalid {label} readset path")
        if not isinstance(expected, str) or len(expected) != 64:
            raise RuntimeError(f"invalid {label} readset digest for {relative}")
        source = repo / relative
        if not source.is_file() or sha256(source) != expected:
            raise RuntimeError(f"{label} source digest mismatch: {relative}")
        paths.append(source.resolve())
    if not paths:
        raise RuntimeError(f"empty {label} readset")
    return paths


def verify_requirements(recipe: Path, app: Path, source_map: dict) -> None:
    expected = source_map.get("test_dependency_versions_from_uv_lock")
    expected_hashes = source_map.get("test_dependency_artifact_hashes_from_uv_lock")
    if not isinstance(expected, dict) or not expected or not isinstance(expected_hashes, dict):
        raise RuntimeError("source map has no exact locked test dependency set")
    observed = {}
    current = ""
    for raw in (recipe / REQUIREMENTS).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        continued = line.endswith("\\")
        current += " " + (line[:-1].strip() if continued else line)
        if continued:
            continue
        tokens = shlex.split(current)
        current = ""
        if not tokens or tokens[0].count("==") != 1:
            raise RuntimeError("test requirements must be exact package==version pins")
        package, version = tokens[0].split("==")
        artifact_hashes = sorted(token.removeprefix("--hash=") for token in tokens[1:])
        if any(not value.startswith("sha256:") for value in artifact_hashes):
            raise RuntimeError("requirements contain an unsupported artifact hash")
        observed[package.lower()] = {"version": version, "hashes": artifact_hashes}
    if current:
        raise RuntimeError("unterminated exact dependency requirement")
    versions = {name: item["version"] for name, item in observed.items()}
    if {name.lower(): version for name, version in expected.items()} != versions:
        raise RuntimeError("requirements differ from the exact APP uv.lock versions")
    if {name.lower(): sorted(values) for name, values in expected_hashes.items()} != {
        name: item["hashes"] for name, item in observed.items()
    }:
        raise RuntimeError("requirements artifact hashes differ from the exact APP uv.lock")
    lock_path = app / "uv.lock"
    if sha256(lock_path) != source_map.get("app_uv_lock_sha256"):
        raise RuntimeError("APP uv.lock digest differs from the source map")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    for name, version in expected.items():
        package = next((item for item in lock.get("package", []) if item.get("name") == name), None)
        if package is None or package.get("version") != version:
            raise RuntimeError(f"test dependency {name} version differs from APP uv.lock")
        hashes = sorted({
            item["hash"] for item in [*package.get("wheels", []), *([package["sdist"]] if package.get("sdist") else [])]
            if item.get("hash")
        })
        if hashes != sorted(expected_hashes.get(name, [])):
            raise RuntimeError(f"test dependency {name} artifact hashes differ from APP uv.lock")


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / name for name in ("recipe", "carrier", "app"))
    result = runner_temp / "ap-me1-me3" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "ap-me1-me3-synthetic-controls", "exit_code": None}
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    try:
        verify_identity(carrier, ROOT_CARRIER_PIN, "native capture carrier")
        verify_identity(app, APP_PIN, "APP source")
        recipe_pin = os.environ.get("RECIPE_PIN", "")
        if not recipe_pin:
            raise RuntimeError("workflow did not bind its exact recipe revision")
        verify_identity(recipe, recipe_pin, "workflow recipe")
        source_map_path = recipe / READSET_MAP
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        if source_map.get("schema") != "epyc.ap_me1_me3.source_readset.v1":
            raise RuntimeError("unsupported AP source/readset map")
        if source_map.get("app_revision") != APP_PIN or source_map.get("carrier_revision") != ROOT_CARRIER_PIN:
            raise RuntimeError("source/readset map revisions disagree with workflow pins")
        if source_map.get("selections") != SELECTIONS:
            raise RuntimeError("source/readset map selection differs from runner selection")

        app_inputs = verify_file_records(app, source_map.get("app_files", []), "APP")
        recipe_inputs = verify_file_records(recipe, source_map.get("recipe_files", []), "recipe")
        verify_requirements(recipe, app, source_map)
        carrier_script = carrier / "scripts/ci/native_conformance.py"
        carrier_hash = source_map.get("carrier_native_conformance_sha256")
        if not carrier_script.is_file() or sha256(carrier_script) != carrier_hash:
            raise RuntimeError("pinned native receipt source digest mismatch")
        if not source_map.get("controls") or len(source_map["controls"]) != 31:
            raise RuntimeError("source map must bind exactly 31 new AP controls")

        environment_path = result / "environment.json"
        environment = {
            "schema": "epyc.ap_me1_me3.hosted_environment.v1",
            "python": sys.version,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "app_revision": APP_PIN,
            "app_uv_lock_sha256": source_map["app_uv_lock_sha256"],
            "requirements_sha256": sha256(recipe / REQUIREMENTS),
            "install_command": "python -m pip install --no-deps --require-hashes -r recipe/" + REQUIREMENTS,
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE", "PYTHONHASHSEED",
                "AP_ME1_ME3_EXECUTION_CONTEXT",
                "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_LOG_DIR",
                "ORCHESTRATOR_SERVING_CALLS_LOG", "ORCHESTRATOR_COHERENCE_JUDGE_LOG",
                "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN", "ORCHESTRATOR_PATHS_LLAMA_MTMD",
                "ORCHESTRATOR_PATHS_LLAMA_SERVER",
            )},
            "limits": [
                "synthetic pytest tmp_path fixtures only",
                "no inference, model, endpoint, live runtime, or main trial producer",
                "no APP checkout writes; bytecode/cache disabled",
            ],
        }
        write_json(environment_path, environment)

        junit = result / "junit.xml"
        capture_dir = result / "native"
        pytest_argv = [
            sys.executable, "-m", "pytest", "--noconftest",
            "-p", "no:cacheprovider", "-p", "ap_me1_me3_case_guard", "-q",
            f"--junitxml={junit}", *SELECTIONS,
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join((str(recipe / "scripts/ci"), str(app)))
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        capture_argv = [
            sys.executable, str(carrier_script),
            "--cwd", str(app), "--junit", str(junit), "--output", str(capture_dir),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"app={app}",
        ]
        read_paths = [
            source_map_path.resolve(), (recipe / WORKFLOW).resolve(),
            (recipe / DRIVER).resolve(), (recipe / CASE_GUARD).resolve(),
            (recipe / REQUIREMENTS).resolve(), environment_path.resolve(),
            *recipe_inputs, *app_inputs,
        ]
        for path in dict.fromkeys(read_paths):
            capture_argv.extend(("--read-path", str(path)))
        for selection in SELECTIONS:
            capture_argv.extend(("--select", selection))
        capture_argv.extend(("--", *pytest_argv))

        status.update({"state": "running", "selection_count": len(SELECTIONS)})
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        completed = subprocess.run(capture_argv, cwd=app, env=env, check=False)
        status.update(
            state="passed" if completed.returncode == 0 else "failed",
            exit_code=completed.returncode,
            native_receipt="native/receipt.json",
            junit="junit.xml",
            source_readset="native/receipt.json#readset",
        )
        return completed.returncode
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
