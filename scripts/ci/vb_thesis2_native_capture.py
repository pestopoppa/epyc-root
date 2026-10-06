"""Capture selected UFH-13 synthetic adapter controls with the pinned native carrier."""
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
SOURCE_PIN = "9891c1979d4580512aeb6451850b8bd0dca86055"
APP_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
RESEARCH_PIN = "1bace97dc655ab5896291b4571781e53b821d9a3"
PYTHON_PIN = "3.13.15"
WORKFLOW = ".github/workflows/vb-thesis2-native-conformance.yml"
DRIVER = "scripts/ci/vb_thesis2_native_capture.py"
REQUIREMENTS = "scripts/ci/vb_thesis2_native_requirements.txt"
CASES = "scripts/ci/vb_thesis2_native_cases.json"
RESEARCH_SCORE = "scripts/benchmark/thesis_ufh13/score.py"
SELECTIONS = (
    "tests/vidya/test_ufh13_thesis_adapter.py",
    "tests/vidya/test_ingest_sources.py::test_every_source_is_a_cli_choice_and_the_literal_list_does_not_drift",
    "tests/vidya/test_ingest_sources.py::test_every_source_has_an_end_to_end_fixture_or_a_named_exemption",
    "tests/vidya/test_ingest_sources.py::test_source_ingests_a_fixture_end_to_end[ufh13-thesis-measurement]",
)
LOCKED = {
    "pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
    "pluggy": "1.6.0", "pygments": "2.20.0", "pyyaml": "6.0.3",
}
EXPECTED_ENV = {
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1",
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
    actual = git(repo, "rev-parse", "HEAD")
    if actual != expected:
        raise RuntimeError(f"{label} revision mismatch: expected {expected}, got {actual}")
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"{label} has tracked modifications")


def tracked(repo: Path, relative: str) -> Path:
    path = repo / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"declared input is not a regular file: {relative}")
    mode = git(repo, "ls-tree", "HEAD", "--", relative).split(maxsplit=1)[0]
    if mode not in {"100644", "100755"}:
        raise RuntimeError(f"declared input is not a tracked regular file: {relative}")
    return path.resolve()


def git_blob(repo: Path, relative: str) -> str:
    entry = git(repo, "ls-tree", "HEAD", "--", relative).split()
    if len(entry) < 3 or entry[1] != "blob":
        raise RuntimeError(f"declared source has no Git blob identity: {relative}")
    return entry[2]


def verify_lock(app: Path, requirements: Path) -> dict[str, str]:
    lock = tomllib.loads((app / "uv.lock").read_text(encoding="utf-8"))
    packages = {item["name"].lower(): item for item in lock["package"]}
    parsed: dict[str, str] = {}
    for name, version in LOCKED.items():
        item = packages.get(name)
        if not item or item["version"] != version:
            raise RuntimeError(f"APP uv.lock does not pin {name}=={version}")
        lock_hashes = {wheel["hash"] for wheel in item.get("wheels", [])}
        if not lock_hashes:
            raise RuntimeError(f"APP uv.lock has no wheel hashes for {name}")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from APP lock")
        parsed[name] = version
    text = requirements.read_text(encoding="utf-8")
    for name, version in LOCKED.items():
        record = packages[name]
        line_name = "PyYAML" if name == "pyyaml" else ("Pygments" if name == "pygments" else name)
        if f"{line_name}=={version}" not in text and f"{name}=={version}" not in text:
            raise RuntimeError(f"requirements omit locked {name}=={version}")
        # The exact Ubuntu/Python 3.13 wheel used here must be represented in the lock.
        wheels = [wheel["hash"] for wheel in record.get("wheels", [])]
        if not any(value in text for value in wheels):
            raise RuntimeError(f"requirements do not pin an APP wheel hash for {name}")
    return parsed


def expected_cases(recipe: Path) -> set[tuple[str, str]]:
    data = json.loads(tracked(recipe, CASES).read_text(encoding="utf-8"))
    if data.get("schema") != "epyc.ufh13_thesis.selected_cases.v1":
        raise RuntimeError("unexpected selected-case manifest schema")
    if data.get("source_commit") != "9891c1979d4580512aeb6451850b8bd0dca86055":
        raise RuntimeError("selected-case manifest source pin differs")
    provenance = data.get("provenance") or {}
    if (provenance.get("test_bodies_executed") is not False
            or provenance.get("test_modules_imported") is not False
            or provenance.get("module_level_code_executed") is not False):
        raise RuntimeError("case manifest provenance is not static-only")
    source_hashes = provenance.get("source_paths_sha256") or {}
    if set(source_hashes) != {
            "tests/vidya/test_ufh13_thesis_adapter.py",
            "tests/vidya/test_ingest_sources.py"}:
        raise RuntimeError("case manifest does not pin both selected test sources")
    rows = data.get("cases")
    if not isinstance(rows, list) or len(rows) != 29:
        raise RuntimeError("selected-case manifest does not contain the 29 reviewed cases")
    pairs = {(row[0], row[1]) for row in rows if isinstance(row, list) and len(row) == 2}
    if len(pairs) != 29:
        raise RuntimeError("selected-case manifest has malformed or duplicate identities")
    return pairs


def verify_junit(path: Path, native: dict, expected: set[tuple[str, str]]) -> dict:
    root = ET.parse(path).getroot()
    cases = []
    for node in root.iter("testcase"):
        cases.append((node.attrib.get("classname", ""), node.attrib.get("name", "")))
    counts = native["summary"]["counts"]
    if (set(cases) != expected or len(cases) != 29 or len(set(cases)) != 29
            or counts.get("collected") != 29 or counts.get("executed") != 29
            or counts.get("skipped") != 0 or counts.get("failure") != 0
            or counts.get("error") != 0 or native.get("fixture_execution_conformant") is not True):
        raise RuntimeError("original JUnit/native summary differs from exact reviewed case set")
    return {"count": len(cases), "identities": [list(x) for x in cases], "counts": counts}


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    result = Path(os.environ["RUNNER_TEMP"]).resolve() / "vb-thesis2" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status: dict = {"state": "preparing", "job": "ufh13-thesis-native-conformance",
                    "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError("Python version differs from reviewed recipe")
        for key, value in EXPECTED_ENV.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from reviewed recipe")
        recipe, source, carrier, app, research = (workspace / x for x in
                                                  ("recipe", "source", "carrier", "app", "research"))
        recipe_pin = os.environ.get("RECIPE_PIN", "")
        if not recipe_pin:
            raise RuntimeError("workflow did not bind exact recipe revision")
        identity(recipe, recipe_pin, "recipe")
        identity(source, SOURCE_PIN, "thesis source")
        identity(carrier, ROOT_PIN, "carrier")
        identity(app, APP_PIN, "APP lock source")
        identity(research, RESEARCH_PIN, "UFH-13 producer source")
        pins = {"recipe": recipe_pin, "source": SOURCE_PIN, "carrier": ROOT_PIN, "app": APP_PIN,
                "research": RESEARCH_PIN}
        cases_file = tracked(recipe, CASES)
        expected = expected_cases(recipe)
        req = tracked(recipe, REQUIREMENTS)
        lock = tracked(app, "uv.lock")
        requirements = verify_lock(app, req)
        source_commit = "1bace97dc655ab5896291b4571781e53b821d9a3"
        score = tracked(research, RESEARCH_SCORE)
        if digest(score) != "544c1277d1eb00e9f685e40490385644573417f813a9989dacff83a7cdb4350f":
            raise RuntimeError("pinned UFH-13 producer source digest differs")

        # Explicit selected import/read closure: the two selected test modules, thesis fixture
        # and adapter, dispatcher/CLI/core modules and the currently registered source modules.
        root_names = {
            *SELECTIONS[:1],
            "tests/__init__.py",
            "tests/vidya/test_ingest_sources.py",
            "tests/vidya/ufh13_thesis_fixtures.py",
            "handoffs/active/vidya-belief-substrate-program.md",
            "scripts/vidya/adapters/README.md",
            "scripts/vidya/adapters/ufh13_thesis.py",
            "scripts/vidya/adapters/__init__.py",
            "scripts/vidya/claim_tuple.py", "scripts/vidya/cli.py",
            "scripts/vidya/ingest_sources.py", "scripts/vidya/ledger.py",
            "scripts/vidya/canonical.py", "scripts/vidya/checkpoint.py",
            "scripts/vidya/fold.py", "scripts/vidya/frames.py",
            "scripts/vidya/lattice.py", "pytest.ini",
        }
        root_reads = [tracked(source, name) for name in sorted(root_names)]
        source_hashes = json.loads(cases_file.read_text(encoding="utf-8"))[
            "provenance"]["source_paths_sha256"]
        for relative, expected_hash in source_hashes.items():
            if digest(tracked(source, relative)) != expected_hash:
                raise RuntimeError(f"selected test source changed: {relative}")
        carrier_names = (
            "scripts/ci/native_conformance.py",
            "scripts/vidya/adapters/ci_conformance.py",
            "scripts/vidya/claim_tuple.py", "scripts/vidya/lattice.py",
            "scripts/vidya/frames.py", "scripts/vidya/canonical.py",
        )
        carrier_reads = [tracked(carrier, name) for name in carrier_names]
        workflow = tracked(recipe, WORKFLOW)
        driver = tracked(recipe, DRIVER)
        junit, native_dir = result / "original-junit.xml", result / "native"
        environment = {
            "schema": "epyc.ufh13_thesis.native_environment.v1",
            "python": sys.version, "python_version": platform.python_version(),
            "platform": platform.platform(), "repositories": pins,
            "app_uv_lock_sha256": digest(lock), "requirements_sha256": digest(req),
            "locked_import_closure": requirements,
            "selections": list(SELECTIONS), "case_manifest_sha256": digest(cases_file),
            "producer_source": {"repo": "research", "commit": source_commit,
                                "path": RESEARCH_SCORE, "sha256": digest(score)},
            "environment": {k: os.environ.get(k) for k in EXPECTED_ENV},
            "scope": ["synthetic temporary fixtures only", "no model or inference",
                      "no live producer run", "no benchmark", "no score-data read"],
        }
        env_path = result / "environment.json"
        env_path.write_text(json.dumps(environment, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        freeze_path = result / "pip-freeze.txt"
        freeze_path.write_bytes(subprocess.check_output([sys.executable, "-m", "pip",
                                                         "freeze", "--all"]))
        source_manifest_path = result / "source-manifest.json"
        manifest_rows = []
        for label, repo, paths in (
                ("source", source, root_reads), ("carrier", carrier, carrier_reads),
                ("recipe", recipe, [workflow, driver, req, cases_file]),
                ("app", app, [lock]), ("research", research, [score])):
            for path in paths:
                relative = path.relative_to(repo.resolve()).as_posix()
                manifest_rows.append({"repository": label, "pin": pins[label],
                                      "path": relative, "git_blob": git_blob(repo, relative),
                                      "sha256": digest(path)})
        source_manifest_path.write_text(json.dumps({
            "schema": "epyc.ufh13_thesis.source_manifest.v1",
            "repositories": pins, "inputs": manifest_rows,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        pre_status_path = result / "pre-status.json"
        if not pre_status_path.is_file():
            raise RuntimeError("workflow's immutable setup pre-status artifact is missing")
        read_paths = [workflow, driver, req, cases_file, lock, score, env_path, freeze_path,
                      source_manifest_path, pre_status_path, *root_reads, *carrier_reads]
        pytest_argv = [sys.executable, "-m", "pytest", "--noconftest", "-p",
                       "no:cacheprovider", "-o", "addopts=", "-q", *SELECTIONS,
                       f"--junitxml={junit}"]
        os.environ["PYTHONPATH"] = str(source)
        os.environ["UFH13_RESEARCH_ROOT"] = str(research)
        status.update(state="running", repositories=pins, selected_case_count=29)
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
            repositories={"recipe": recipe, "source": source, "carrier": carrier, "app": app,
                          "research": research},
            read_paths=list(dict.fromkeys(x.resolve() for x in read_paths)),
            selections=SELECTIONS,
        )
        receipt_path = native_dir / "receipt.json"
        native, receipt_sha = api.read_receipt(receipt_path)
        cases = verify_junit(junit, native, expected)
        originals = [p for p in native_dir.rglob("*") if p.is_file()]
        originals.extend((junit, env_path, freeze_path, source_manifest_path, pre_status_path))
        before = {str(p): digest(p) for p in originals}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        if len(rows) != 1:
            raise RuntimeError("existing native carrier adapter did not project exactly one receipt")
        claim = project_ci_conformance(rows[0])
        quality, traceability, reasons = grade(claim)
        after = {str(p): digest(p) for p in originals}
        reopened, reopened_sha = api.read_receipt(receipt_path)
        if before != after or reopened != native or reopened_sha != receipt_sha:
            raise RuntimeError("original artifacts changed during native shared-grade review")
        if (quality, traceability) != ("Judged", "Located"):
            raise RuntimeError("original-only native conformance grade differs from expected")
        grade_record = {"kind": "original_native_receipt_only", "fixture_rerun": False,
                        "grade": {"Q": quality, "T": traceability, "reasons": reasons},
                        "measurement_id": claim.measurement_id,
                        "receipt_sha256": receipt_sha,
                        "original_artifact_hashes_before": before,
                        "original_artifact_hashes_after": after}
        (result / "shared-grade.json").write_text(
            json.dumps(grade_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        status.update(state="passed", exit_code=0, native_receipt="native/receipt.json",
                      junit="original-junit.xml", cases=cases,
                      shared_grade={"Q": quality, "T": traceability})
        return 0
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
