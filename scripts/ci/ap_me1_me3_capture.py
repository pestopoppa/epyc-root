"""Capture AP-ME1/3 synthetic controls through the pinned native receipt carrier.

Execution is intended for the isolated hosted workflow only. The wrapper itself does not
import APP or invoke a main trial producer; pytest imports only the selected synthetic
controls and their ordinary import closure. No live journal is touched.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import shlex
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
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
PYTHON_VERSION = "3.13.15"
LOCKED_PACKAGES = {"pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
                   "pluggy": "1.6.0", "Pygments": "2.20.0"}
EXPECTED_CONTEXT = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "ORCHESTRATOR_MOCK_MODE": "1",
    "ORCHESTRATOR_LOG_DIR": "/dev/null", "ORCHESTRATOR_SERVING_CALLS_LOG": "off",
    "ORCHESTRATOR_COHERENCE_JUDGE_LOG": "off",
    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "/fixture/kernel-bin",
    "ORCHESTRATOR_PATHS_LLAMA_MTMD": "/fixture/llama-mtmd-cli",
    "ORCHESTRATOR_PATHS_LLAMA_SERVER": "/fixture/llama-server",
}


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
        if source.is_symlink():
            target = item.get("symlink_target")
            if not isinstance(target, str) or os.readlink(source) != target:
                raise RuntimeError(f"{label} tracked symlink target mismatch: {relative}")
            link_digest = hashlib.sha256(os.fsencode(target)).hexdigest()
            if link_digest != expected:
                raise RuntimeError(f"{label} tracked symlink digest mismatch: {relative}")
            # The tracked link is source identity, but its external target is not imported
            # into this isolated fixture readset.
            continue
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


def verify_runtime() -> None:
    if platform.python_version() != PYTHON_VERSION:
        raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
    for package, expected in LOCKED_PACKAGES.items():
        actual = importlib.metadata.version(package)
        if actual != expected:
            raise RuntimeError(f"installed {package} differs from pin: {actual}")


def validate_original_junit(path: Path, record: dict, controls: list[dict]) -> dict:
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    new_cases = [case for case in cases
                 if case.get("classname", "").endswith("test_mutation_diagnostics")]
    expected = {item["case"] for item in controls}
    actual = [case.get("name", "") for case in new_cases]
    if len(actual) != 31 or len(set(actual)) != 31 or set(actual) != expected:
        raise RuntimeError("original JUnit does not contain exactly the 31 reviewed unique AP controls")
    suite_counts = {name: {"collected": 0, "passed": 0, "skipped": 0, "failure": 0, "error": 0}
                    for name in ("test_mutation_diagnostics", "test_failure_signatures",
                                 "test_behavior_signature", "test_bsv_observe")}
    for case in cases:
        classname = case.get("classname", "")
        module = next((name for name in suite_counts if classname.endswith(name)), None)
        if module is not None:
            suite_counts[module]["collected"] += 1
            status = next((name for name in ("failure", "error", "skipped")
                           if case.find(name) is not None), "passed")
            suite_counts[module][status] += 1
        if case.find("failure") is not None or case.find("error") is not None or case.find("skipped") is not None:
            raise RuntimeError("original JUnit contains a failed, errored, or skipped case")
    if any(counts["collected"] == 0 for counts in suite_counts.values()):
        raise RuntimeError("original JUnit omitted a selected compatibility suite")
    summary = record.get("summary") or {}
    counts = summary.get("counts") or {}
    if (counts.get("collected") != len(cases) or counts.get("executed") != len(cases)
            or counts.get("skipped") != 0 or counts.get("failure") != 0 or counts.get("error") != 0):
        raise RuntimeError("native receipt aggregate counts disagree with selected original JUnit")
    return {"case_count": len(cases), "new_ap_case_count": len(actual),
            "suite_case_counts": suite_counts}


def load_native_carrier(carrier: Path):
    source = carrier / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("ap_me1_me3_native_conformance", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load pinned native receipt carrier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def grade_original_receipt(carrier: Path, receipt: Path) -> dict:
    # Existing source adapter and shared grade are used only on the hosted runner.
    sys.path.insert(0, str(carrier))
    sys.path.insert(0, str(carrier / "scripts/vidya"))
    from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
    from claim_tuple import grade
    rows = native_rows(receipt)
    if len(rows) != 1:
        raise RuntimeError("existing native adapter did not yield exactly one original receipt row")
    claim = project_ci_conformance(rows[0])
    quality, traceability, reasons = grade(claim)
    if (quality, traceability) != ("Judged", "Located"):
        raise RuntimeError("fixture observation did not retain its existing observation grade")
    return {"adapter": "vidya.adapters.ci_conformance/v1", "quality": quality,
            "traceability": traceability, "reasons": reasons,
            "measurement_id": claim.measurement_id}


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
        verify_runtime()
        if os.environ.get("AP_ME1_ME3_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed hosted recipe")
        if os.environ.get("AP_ME1_ME3_EXECUTION_CONTEXT") != "offline-native-journal-fixtures":
            raise RuntimeError("execution context differs from reviewed hosted recipe")
        for key, expected in EXPECTED_CONTEXT.items():
            if os.environ.get(key) != expected:
                raise RuntimeError(f"{key} differs from reviewed isolated-runner context")
        verify_identity(carrier, ROOT_CARRIER_PIN, "native capture carrier")
        verify_identity(app, APP_PIN, "APP source")
        recipe_pin = os.environ.get("RECIPE_PIN", "")
        if not recipe_pin:
            raise RuntimeError("workflow did not bind its exact recipe revision")
        verify_identity(recipe, recipe_pin, "workflow recipe")
        source_map_path = recipe / READSET_MAP
        source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
        if source_map.get("schema") != "epyc.ap_me1_me3.source_readset.v2":
            raise RuntimeError("unsupported AP source/readset map")
        if source_map.get("app_revision") != APP_PIN or source_map.get("carrier_revision") != ROOT_CARRIER_PIN:
            raise RuntimeError("source/readset map revisions disagree with workflow pins")
        if source_map.get("selections") != SELECTIONS:
            raise RuntimeError("source/readset map selection differs from runner selection")

        app_inputs = verify_file_records(app, source_map.get("app_files", []), "APP")
        carrier_inputs = verify_file_records(carrier, source_map.get("carrier_files", []), "carrier")
        recipe_inputs = verify_file_records(recipe, source_map.get("recipe_files", []), "recipe")
        if source_map.get("app_tracked_python_config_count") != len(source_map.get("app_files", [])):
            raise RuntimeError("APP tracked Python/config population differs from source map count")
        if source_map.get("carrier_tracked_python_config_count") != len(source_map.get("carrier_files", [])):
            raise RuntimeError("carrier tracked Python/config population differs from source map count")
        if source_map.get("recipe_tracked_python_config_count") != len(source_map.get("recipe_files", [])):
            raise RuntimeError("recipe tracked Python/config population differs from source map count")
        verify_requirements(recipe, app, source_map)
        carrier_script = carrier / "scripts/ci/native_conformance.py"
        carrier_hash = source_map.get("carrier_native_conformance_sha256")
        if not carrier_script.is_file() or sha256(carrier_script) != carrier_hash:
            raise RuntimeError("pinned native receipt source digest mismatch")
        if not source_map.get("controls") or len(source_map["controls"]) != 31:
            raise RuntimeError("source map must bind exactly 31 new AP controls")

        environment_path = result / "environment.json"
        freeze_path = result / "pip-freeze.txt"
        with freeze_path.open("xb") as handle:
            handle.write(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = {
            "schema": "epyc.ap_me1_me3.hosted_environment.v1",
            "python": sys.version,
            "python_version": platform.python_version(),
            "installed_packages": {name: importlib.metadata.version(name) for name in LOCKED_PACKAGES},
            "pip_freeze_sha256": sha256(freeze_path),
            "platform": platform.platform(),
            "runner_context": os.environ.get("AP_ME1_ME3_RUNNER_CONTEXT", ""),
            "execution_context": os.environ.get("AP_ME1_ME3_EXECUTION_CONTEXT", ""),
            "pytest_pythonpath": os.pathsep.join((str(recipe / "scripts/ci"), str(app))),
            "app_revision": APP_PIN,
            "carrier_revision": ROOT_CARRIER_PIN,
            "recipe_revision": recipe_pin,
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
            "-p", "no:cacheprovider", "-p", "ap_me1_me3_case_guard", "-q", "-o", "addopts=",
            f"--junitxml={junit}", *SELECTIONS,
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = environment["pytest_pythonpath"]
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        read_paths = [
            source_map_path.resolve(), (recipe / WORKFLOW).resolve(),
            (recipe / DRIVER).resolve(), (recipe / CASE_GUARD).resolve(),
            (recipe / REQUIREMENTS).resolve(), environment_path.resolve(), freeze_path.resolve(),
            carrier_script.resolve(), *recipe_inputs, *app_inputs,
            *carrier_inputs,
        ]
        status.update({"state": "running", "selection_count": len(SELECTIONS)})
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        carrier_api = load_native_carrier(carrier)
        inherited = {key: os.environ.get(key) for key in (
            "PYTHONPATH", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE")}
        try:
            os.environ.update({key: env[key] for key in inherited})
            record = carrier_api.capture_fixture_execution(
                argv=pytest_argv, cwd=app, junit=junit, output=capture_dir,
                repositories={"recipe": recipe, "carrier": carrier, "app": app},
                read_paths=list(dict.fromkeys(read_paths)), selections=SELECTIONS,
            )
        finally:
            for key, value in inherited.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        receipt_path = capture_dir / "receipt.json"
        reopened, _receipt_sha = carrier_api.read_receipt(receipt_path)
        if reopened.get("fixture_execution_conformant") is not True:
            raise RuntimeError("native carrier did not confirm successful fixture execution")
        case_facts = validate_original_junit(junit, reopened, source_map["controls"])
        originals = [path for path in capture_dir.iterdir() if path.is_file()]
        originals.extend((junit, freeze_path, environment_path))
        before = {str(path): sha256(path) for path in originals}
        shared_grade = grade_original_receipt(carrier, receipt_path)
        reopened_after, _ = carrier_api.read_receipt(receipt_path)
        after = {str(path): sha256(path) for path in originals}
        if before != after or reopened_after != reopened:
            raise RuntimeError("original receipt/artifacts changed during native shared-grade read")
        write_json(result / "shared-grade.json", shared_grade)
        status.update(state="passed", exit_code=0, native_receipt="native/receipt.json",
                      junit="junit.xml", source_readset="native/receipt.json#readset",
                      native_metric=reopened["metric"], native_value=reopened["fixture_execution_conformant"],
                      counts=reopened["summary"]["counts"], cases=case_facts,
                      shared_grade={"quality": shared_grade["quality"],
                                    "traceability": shared_grade["traceability"]})
        return 0
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
