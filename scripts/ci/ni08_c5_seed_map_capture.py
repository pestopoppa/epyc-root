"""Capture only the offline C5 seed/provider join conformance suite."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

RESEARCH_PIN = "7aafbbae7fe33f4a7e5527c6d6df2823b4d02cc6"
ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
PYTHON_PIN = "3.13.15"
SELECTIONS = (
    "scripts/kernel_rnd/autokernel/test_c5_seed_corpus.py",
    "scripts/kernel_rnd/autokernel/test_c5_rocm_oracle.py",
)
EXPECTED_CASES = 27
EXPECTED_CASES_PATH = "scripts/ci/ni08_c5_seed_map_expected_cases.json"
LOCKED_PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3",
}
INSTALL_REQUIREMENTS = "scripts/ci/ni08_c5_seed_map_capture_requirements.txt"
INSTALL_COMMAND = (
    "python -m pip install --require-hashes -r "
    "recipe/scripts/ci/ni08_c5_seed_map_capture_requirements.txt"
)
WORKFLOW = ".github/workflows/ni08-c5-seed-map-capture.yml"
APP_LOCK = "uv.lock"
TASK_SOURCE = "handoffs/active/agentic-rocm-kernel-authoring.md"
TASK_SOURCE_SHA256 = "c7b5d6f96cd7ab53ab99e0c6ff8621f743e79d0354e99a5cf06461aa283a96ba"

RESEARCH_READS = (
    *SELECTIONS,
    "pyproject.toml",
    "scripts/kernel_rnd/autokernel/__init__.py",
    "scripts/kernel_rnd/autokernel/c5_seed_corpus.py",
    "scripts/kernel_rnd/autokernel/c5_seed_corpus.json",
    "scripts/kernel_rnd/autokernel/c5_rocm_oracle.py",
    "scripts/kernel_rnd/autokernel/c5_rocm_oracle.json",
    "scripts/kernel_rnd/autokernel/schemas.py",
    "scripts/kernel_rnd/autokernel/controller/__init__.py",
    "scripts/kernel_rnd/autokernel/controller/authoring_contract.py",
    "scripts/kernel_rnd/autokernel/controller/do_not_repeat.py",
    "scripts/kernel_rnd/autokernel/controller/hypotheses.py",
    "scripts/kernel_rnd/autokernel/controller/shared.py",
    "scripts/kernel_rnd/autokernel/evaluator/__init__.py",
    "scripts/kernel_rnd/autokernel/evaluator/api.py",
    "scripts/kernel_rnd/autokernel/evaluator/devices.py",
    "scripts/kernel_rnd/autokernel/journal.py",
    "scripts/kernel_rnd/autokernel/resource/__init__.py",
    "scripts/kernel_rnd/autokernel/resource/device_claim.py",
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
    if mode not in {"100644", "100755"}:
        raise RuntimeError(f"declared read is not a tracked regular file: {name}")
    return path.absolute()


def verify_dependencies(app: Path, requirements: Path) -> None:
    lock = tomllib.loads((app / APP_LOCK).read_text(encoding="utf-8"))
    locked = {item["name"].lower(): item for item in lock["package"]}
    hashes: dict[str, list[str]] = {}
    for name, version in LOCKED_PACKAGES.items():
        record = locked.get(name)
        if not record or record["version"] != version:
            raise RuntimeError(f"{name} differs from the pinned APP uv.lock")
        wheels = [wheel["hash"] for wheel in record.get("wheels", [])]
        if not wheels or any(not digest.startswith("sha256:") for digest in wheels):
            raise RuntimeError(f"{name} has no complete wheel hashes in APP uv.lock")
        if importlib.metadata.version(name) != version:
            raise RuntimeError(f"installed {name} differs from {version}")
        hashes[name] = sorted(wheels)
    text = requirements.read_text(encoding="utf-8")
    for name, version in LOCKED_PACKAGES.items():
        if f"{name}=={version}" not in text and f"{name.title()}=={version}" not in text:
            raise RuntimeError(f"requirements hashlock omits {name}=={version}")
        for digest in hashes[name]:
            if digest not in text:
                raise RuntimeError(f"requirements hashlock omits an APP wheel for {name}")


def native_files(directory: Path) -> list[Path]:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("native output is missing or is not a regular directory")
    files: list[Path] = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("native output contains a symlink")
        if path.is_file():
            files.append(path)
        elif not path.is_dir():
            raise RuntimeError("native output contains a non-regular member")
    return files


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app, research = (
        workspace / name for name in ("recipe", "carrier", "app", "research")
    )
    repos = {"recipe": recipe, "carrier": carrier, "app": app, "research": research}
    result = runner_temp / "ni08-c5-seed-map-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status: dict[str, Any] = {
        "state": "preparing", "job": "c5-seed-map-capture", "exit_code": None,
    }
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("NI08_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        expected_env = {
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
        for key, value in expected_env.items():
            if os.environ.get(key) != value:
                raise RuntimeError(f"{key} differs from reviewed recipe")
        pins = {name: require_clean(repo, name) for name, repo in repos.items()}
        expected = {
            "recipe": os.environ["GITHUB_SHA"], "carrier": ROOT_CARRIER_PIN,
            "app": APP_PIN, "research": RESEARCH_PIN,
        }
        if pins != expected:
            raise RuntimeError(f"repository pins differ: {pins}")
        for key, expected_pin in (("ROOT_CARRIER_PIN", ROOT_CARRIER_PIN),
                                  ("APP_PIN", APP_PIN),
                                  ("RESEARCH_PIN", RESEARCH_PIN)):
            if os.environ.get(key) != expected_pin:
                raise RuntimeError(f"workflow {key} differs from reviewed pin")

        recipe_reads = [regular_repo_file(recipe, name) for name in (
            WORKFLOW, INSTALL_REQUIREMENTS, EXPECTED_CASES_PATH, TASK_SOURCE,
        )]
        runner = regular_repo_file(recipe, "scripts/ci/ni08_c5_seed_map_capture.py")
        research_reads = [regular_repo_file(research, name) for name in RESEARCH_READS]
        carrier_reads = [regular_repo_file(carrier, name) for name in CARRIER_READS]
        app_lock = regular_repo_file(app, APP_LOCK)
        requirements = regular_repo_file(recipe, INSTALL_REQUIREMENTS)
        task_source = regular_repo_file(recipe, TASK_SOURCE)
        if hashlib.sha256(task_source.read_bytes()).hexdigest() != TASK_SOURCE_SHA256:
            raise RuntimeError("ROOT task source bytes differ from the reviewed pin")
        verify_dependencies(app, requirements)

        manifest = json.loads(
            regular_repo_file(recipe, EXPECTED_CASES_PATH).read_text(encoding="utf-8")
        )
        provenance = manifest.get("provenance") or {}
        expected_case_rows = manifest.get("cases")
        expected_identities = [
            (row.get("classname"), row.get("name")) for row in expected_case_rows or []
        ]
        if (manifest.get("count") != EXPECTED_CASES
                or len(expected_identities) != EXPECTED_CASES
                or len(set(expected_identities)) != EXPECTED_CASES
                or any(not all(identity) for identity in expected_identities)
                or provenance.get("source_commit") != RESEARCH_PIN
                or provenance.get("identity_derivation") is None
                or provenance.get("test_modules_imported") is not False
                or provenance.get("module_level_code_executed") is not False
                or provenance.get("test_bodies_executed") is not False):
            raise RuntimeError("frozen static AST-derived case manifest is invalid")
        source_hashes = provenance.get("source_paths_sha256") or {}
        if set(source_hashes) != set(SELECTIONS):
            raise RuntimeError("case manifest source hash set differs from selected modules")
        for selection in SELECTIONS:
            actual = hashlib.sha256(regular_repo_file(research, selection).read_bytes()).hexdigest()
            if actual != source_hashes[selection]:
                raise RuntimeError(f"case manifest source hash differs: {selection}")

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output(
            [sys.executable, "-m", "pip", "freeze", "--all"]
        ))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version,
            "platform": platform.platform(),
            "repositories": pins,
            "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES,
            "case_identity_source": "static AST manifest; exact expanded JUnit multiset checked after execution",
            "task_source": {"repo": "recipe", "path": TASK_SOURCE,
                            "sha256": TASK_SOURCE_SHA256},
            "dependency_lock": {"repo": "app", "pin": APP_PIN, "path": APP_LOCK,
                                "sha256": hashlib.sha256(app_lock.read_bytes()).hexdigest()},
            "dependency_set": LOCKED_PACKAGES,
            "pytest_plugin_autoload": os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"],
            "bytecode_writes": os.environ["PYTHONDONTWRITEBYTECODE"],
            "python_hash_seed": os.environ["PYTHONHASHSEED"],
            "dependency_basis": "Two selected offline unittest modules use pytest and Python standard library only; wheel versions and hashes are checked against pinned APP uv.lock.",
            "scope": "Persisted seed/provider ID join, metadata validation, and synthetic offline refusal controls only. No SOL provider execution, inference, GPU, kernel build, benchmark, model, or measured correctness/timing/promotion claim.",
            "import_closure_note": "The context test imports controller.authoring_contract, which necessarily runs controller/__init__.py and imports do_not_repeat/hypotheses plus their local import closure. Test bodies do not call those storage/claim APIs, provider runners, OpenCode/model clients, GPU paths, or external commands; the C5 compile-plan tests mock the actual provider audit and driver renderer.",
            "historical_policy_boundary": "Historical authority digest c8cec... is not present in available ROOT history; metadata tests explicitly disable byte verification in scoped mocks. Production default verification remains enabled and has separate positive, tamper, symlink, hardlink, and deterministic missing-bytes refusal controls.",
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite existing capture outputs")
        read_paths = [*recipe_reads, runner, *research_reads, *carrier_reads,
                      app_lock, requirements, freeze, environment]
        producer_argv = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(research), "--junit", str(junit), "--output", str(native),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
            "--repo", f"app={app}", "--repo", f"research={research}",
        ]
        for path in dict.fromkeys(item.resolve() for item in read_paths):
            producer_argv.extend(["--read-path", str(path)])
        for selection in SELECTIONS:
            producer_argv.extend(["--select", selection])
        command = [
            sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
            "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}",
        ]
        status.update(state="running", repositories=pins, selections=list(SELECTIONS))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer_argv, "--", *command], cwd=research)
        receipt_path = native / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1,
                          diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        counts = (receipt.get("summary") or {}).get("counts") or {}
        observed_rows = (receipt.get("summary") or {}).get("cases") or []
        observed_identities = [(row.get("classname"), row.get("name")) for row in observed_rows]
        identities_match = (
            len(observed_identities) == EXPECTED_CASES
            and len(set(observed_identities)) == EXPECTED_CASES
            and Counter(observed_identities) == Counter(expected_identities)
        )
        cases_ok = (
            counts.get("collected") == EXPECTED_CASES
            and counts.get("executed") == EXPECTED_CASES
            and counts.get("skipped") == 0
            and counts.get("failure") == 0
            and counts.get("error") == 0
            and identities_match
        )

        originals = [*native_files(native), junit, freeze, environment]
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        sys.path.insert(0, str(carrier))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        analysis: dict[str, Any] = {
            "kind": "analysis_of_existing_fixture_receipt",
            "native_original_hashes": before,
            "repositories": pins,
            "fixture_rerun": False,
            "new_native_receipt_authored_by_analysis": False,
            "metric": metric,
            "grade": None,
        }
        if len(rows) != 1:
            raise RuntimeError("original receipt projection is not exactly one row")
        claim = project_ci_conformance(rows[0])
        q, t, reasons = grade(claim)
        analysis.update(
            measurement_id=claim.measurement_id,
            source_kind=claim.source_kind,
            binding_kind=claim.binding_kind,
            grade={"Q": q, "T": t, "reasons": reasons},
        )
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        if before != after:
            raise RuntimeError("shared-grade analysis changed an original")
        with (result / "shared-grade.json").open("x", encoding="utf-8") as handle:
            json.dump(analysis, handle, indent=2, sort_keys=True)
            handle.write("\n")
        passed = code == 0 and metric is True and cases_ok
        status.update(
            state="passed" if passed else "failed",
            exit_code=0 if passed else (code or 1),
            native_metric=metric,
            junit_counts=counts,
            expected_case_count=EXPECTED_CASES,
            all_cases_executed=cases_ok,
            shared_grade_recorded=True,
        )
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
