"""Capture selected CS-13/15 native SQLite-store controls under the shared carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
ROOT_CONTEXT_PIN = "0da62ca1cb484f54f0e58dc514f10cd61b9ac001"
SOURCE_PIN = "6e8ef922f0a7214efc5443807142f193a7711870"
APP_PIN = "94a6e8d41ec7d3f7a122f66bad53aa673d401d8a"
PYTHON_PIN = "3.13.15"
WORKFLOW = ".github/workflows/vb-cs15-store-native.yml"
DRIVER = "scripts/ci/vb_cs15_store_native_capture.py"
REQUIREMENTS = "scripts/ci/vb_cs15_store_native_requirements.txt"
CASES = "scripts/ci/vb_cs15_store_cases.json"
TASK = "handoffs/active/conversation-stack.md"
SOURCE_TABLE = "scripts/vidya/adapters/README.md"
VB_PROGRAM = "handoffs/active/vidya-belief-substrate-program.md"
SELECTIONS = (
    "tests/unit/test_session_conversation_messages.py",
    "tests/unit/test_session_protocol.py",
    "tests/unit/test_session_lease.py::test_writes_are_fenced_and_reads_are_not",
)
LOCKED = {
    "pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
    "pluggy": "1.6.0", "pygments": "2.20.0", "numpy": "2.4.4",
    "pyyaml": "6.0.3", "pydantic": "2.13.0", "pydantic-core": "2.46.0",
    "pydantic-settings": "2.13.1", "annotated-types": "0.7.0",
    "typing-extensions": "4.15.0", "typing-inspection": "0.4.2",
    "python-dotenv": "1.2.2",
}
EXPECTED_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1", "PYTEST_ADDOPTS": "",
    "PYTEST_PLUGINS": "",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def identity(repo: Path, expected: str, label: str) -> None:
    if git(repo, "rev-parse", "HEAD") != expected:
        raise RuntimeError(f"{label} revision mismatch")
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"{label} has tracked modifications")


def tracked(repo: Path, relative: str) -> Path:
    path = repo / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"declared input is not a regular file: {relative}")
    entry = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(entry) < 3 or entry[1] != "blob" or entry[0] not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a tracked regular blob: {relative}")
    return path.resolve()


def blob(repo: Path, relative: str) -> str:
    fields = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(fields) < 3 or fields[1] != "blob":
        raise RuntimeError(f"missing source blob: {relative}")
    return fields[2]


def verify_lock(app: Path, req: Path) -> dict[str, str]:
    lock = tomllib.loads((app / "uv.lock").read_text(encoding="utf-8"))
    packages = {item["name"].lower(): item for item in lock["package"]}
    text = req.read_text(encoding="utf-8")
    found = {}
    for name, version in LOCKED.items():
        item = packages.get(name)
        if not item or item["version"] != version:
            raise RuntimeError(f"APP uv.lock does not pin {name}=={version}")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from APP lock")
        wheels = {w["hash"] for w in item.get("wheels", [])}
        if not wheels or not all(value in text for value in wheels):
            raise RuntimeError(f"requirements do not retain all APP wheel hashes for {name}")
        found[name] = version
    req_names = {line.split("==", 1)[0].strip().lower().replace("_", "-")
                 for line in text.splitlines()
                 if "==" in line and not line.lstrip().startswith("#")}
    if req_names != {name.replace("_", "-") for name in LOCKED}:
        raise RuntimeError("requirements package set differs from the reviewed exact closure")
    return found


def expected_cases(path: Path) -> set[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("schema") != "epyc.vb.cs15_store.selected_cases.v1"
            or data.get("source_commit") != SOURCE_PIN or data.get("count") != 31):
        raise RuntimeError("selected case manifest schema, source, or count differs")
    provenance = data.get("provenance") or {}
    if any(provenance.get(key) is not False for key in
           ("test_bodies_executed", "test_modules_imported", "module_level_code_executed")):
        raise RuntimeError("case manifest lacks static-only provenance")
    rows = data.get("cases")
    if not isinstance(rows, list) or len(rows) != 31:
        raise RuntimeError("selected case list is incomplete")
    pairs = {(x.get("classname"), x.get("name")) for x in rows
             if isinstance(x, dict) and x.get("nodeid")}
    if len(pairs) != 31:
        raise RuntimeError("selected case identities are malformed or duplicated")
    return pairs


def verify_junit(path: Path, native: dict, expected: set[tuple[str, str]]) -> dict:
    root = ET.parse(path).getroot()
    cases = [(item.attrib.get("classname", ""), item.attrib.get("name", ""))
             for item in root.iter("testcase")]
    counts = native["summary"]["counts"]
    if (set(cases) != expected or len(cases) != 31 or len(set(cases)) != 31
            or counts.get("collected") != 31 or counts.get("executed") != 31
            or counts.get("skipped") != 0 or counts.get("failure") != 0
            or counts.get("error") != 0 or native.get("fixture_execution_conformant") is not True):
        raise RuntimeError("original JUnit/native summary differs from exact reviewed case set")
    return {"count": len(cases), "identities": [list(x) for x in cases], "counts": counts}


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    result = Path(os.environ["RUNNER_TEMP"]).resolve() / "vb-cs15-store" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "cs15-store-native-conformance", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError("Python version differs from reviewed recipe")
        for key, value in EXPECTED_ENV.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from reviewed recipe")
        if "ORCHESTRATOR_STACK_NUMA_MODE" in os.environ:
            raise RuntimeError("runner supplied an unreviewed stack NUMA mode")
        recipe, source, carrier, app, context = (workspace / name for name in
                                                 ("recipe", "source", "carrier", "app", "context"))
        recipe_pin = os.environ.get("RECIPE_PIN", "")
        if not recipe_pin:
            raise RuntimeError("workflow did not bind exact recipe revision")
        identity(recipe, recipe_pin, "recipe")
        identity(source, SOURCE_PIN, "APP source")
        identity(carrier, ROOT_PIN, "native carrier")
        identity(app, APP_PIN, "APP lock source")
        identity(context, ROOT_CONTEXT_PIN, "published enrollment context")
        pins = {"recipe": recipe_pin, "source": SOURCE_PIN, "carrier": ROOT_PIN,
                "app_lock": APP_PIN, "context": ROOT_CONTEXT_PIN}
        cases_file, requirements = tracked(recipe, CASES), tracked(recipe, REQUIREMENTS)
        lock = tracked(app, "uv.lock")
        package_versions = verify_lock(app, requirements)
        selected = expected_cases(cases_file)
        source_map = json.loads(cases_file.read_text(encoding="utf-8"))["source_files"]
        if len(source_map) != 438:
            raise RuntimeError("static source manifest has unexpected file count")
        source_paths = []
        manifest_rows = []
        for relative, expected in sorted(source_map.items()):
            path = tracked(source, relative)
            if blob(source, relative) != expected["git_blob"] or digest(path) != expected["sha256"]:
                raise RuntimeError(f"frozen source blob/hash mismatch: {relative}")
            source_paths.append(path)
            manifest_rows.append({"repository": "source", "pin": SOURCE_PIN, "path": relative,
                                  "git_blob": expected["git_blob"], "sha256": expected["sha256"]})
        contexts = (("context", TASK), ("context", SOURCE_TABLE), ("context", VB_PROGRAM))
        context_paths = []
        for label, relative in contexts:
            path = tracked(context, relative)
            context_paths.append(path)
            manifest_rows.append({"repository": label, "pin": git(context, "rev-parse", "HEAD"),
                                  "path": relative, "git_blob": blob(context, relative),
                                  "sha256": digest(path)})
        carrier_names = (
            "scripts/ci/native_conformance.py", "scripts/vidya/adapters/ci_conformance.py",
            "scripts/vidya/claim_tuple.py", "scripts/vidya/lattice.py",
            "scripts/vidya/frames.py", "scripts/vidya/canonical.py",
        )
        carrier_paths = [tracked(carrier, name) for name in carrier_names]
        workflow = tracked(recipe, WORKFLOW)
        driver = tracked(recipe, DRIVER)
        source_manifest = result / "source-manifest.json"
        source_manifest.write_text(json.dumps({"schema": "epyc.vb.cs15_store.source_manifest.v1",
                                               "repositories": pins, "inputs": manifest_rows},
                                              sort_keys=True, indent=2) + "\n", encoding="utf-8")
        pre_status = result / "pre-status.json"
        if not pre_status.is_file():
            raise RuntimeError("immutable setup pre-status is missing")
        junit, native_dir = result / "original-junit.xml", result / "native"
        read_paths = [workflow, driver, requirements, cases_file, lock, source_manifest, pre_status,
                      *source_paths, *context_paths, *carrier_paths]
        pytest_argv = [sys.executable, "-m", "pytest", "-c", "/dev/null", "--noconftest",
                       "--rootdir", str(source), "--import-mode=importlib", "-p", "no:cacheprovider",
                       "-o", "addopts=", "-q", *SELECTIONS, f"--junitxml={junit}"]
        os.environ["PYTHONPATH"] = str(source)
        status.update(state="running", repositories=pins, selected_case_count=31)
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        from importlib.util import module_from_spec, spec_from_file_location
        carrier_file = tracked(carrier, "scripts/ci/native_conformance.py")
        spec = spec_from_file_location("pinned_native_conformance", carrier_file)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load pinned carrier source")
        api = module_from_spec(spec)
        sys.modules[spec.name] = api
        spec.loader.exec_module(api)
        record = api.capture_fixture_execution(
            argv=pytest_argv, cwd=source, junit=junit, output=native_dir,
            repositories={"recipe": recipe, "source": source, "carrier": carrier,
                           "app": app, "context": context},
            read_paths=list(dict.fromkeys(x.resolve() for x in read_paths)), selections=SELECTIONS)
        receipt_path = native_dir / "receipt.json"
        native, receipt_sha = api.read_receipt(receipt_path)
        cases = verify_junit(junit, native, selected)
        originals = [path for path in native_dir.rglob("*") if path.is_file()]
        originals.extend((junit, source_manifest, pre_status))
        before = {str(path): digest(path) for path in originals}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("native carrier adapter did not project one receipt")
        claim = project_ci_conformance(rows[0])
        quality, traceability, reasons = grade(claim)
        after = {str(path): digest(path) for path in originals}
        reopened, reopened_sha = api.read_receipt(receipt_path)
        if before != after or reopened != native or reopened_sha != receipt_sha:
            raise RuntimeError("native originals changed during shared-grade review")
        if (quality, traceability) != ("Judged", "Located"):
            raise RuntimeError("original native conformance did not retain expected shared grade")
        (result / "shared-grade.json").write_text(json.dumps({
            "kind": "original_native_receipt_only", "fixture_rerun": False,
            "grade": {"Q": quality, "T": traceability, "reasons": reasons},
            "measurement_id": claim.measurement_id, "receipt_sha256": receipt_sha,
            "original_artifact_hashes_before": before, "original_artifact_hashes_after": after,
        }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        status.update(state="passed", exit_code=0, native_receipt="native/receipt.json",
                      junit="original-junit.xml", cases=cases,
                      shared_grade={"Q": quality, "T": traceability})
        return 0
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
