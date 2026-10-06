"""Capture only C5 default policy-path verification controls."""
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

RESEARCH_PIN = "12f51c0e8b85f81576502377e0db9d678fbf1029"
ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "70096b763939a43409a1f1827ab633d62425a6c1"
PYTHON_PIN = "3.13.15"
SELECTIONS = (
    "scripts/kernel_rnd/autokernel/test_c5_seed_corpus.py",
    "scripts/kernel_rnd/autokernel/test_c5_rocm_oracle.py",
)
EXPECTED_CASES = 28
EXPECTED_CASES_PATH = "scripts/ci/ni08_c5_policy_path_expected_cases.json"
LOCKED_PACKAGES = {
    "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
    "pygments": "2.20.0", "pytest": "9.0.3",
}
INSTALL_REQUIREMENTS = "scripts/ci/ni08_c5_policy_path_capture_requirements.txt"
INSTALL_COMMAND = (
    'python -m venv "$RUNNER_TEMP/ni08-c5-policy-path-capture/venv" && '
    '"$RUNNER_TEMP/ni08-c5-policy-path-capture/venv/bin/python" -m pip install '
    "--require-hashes --no-deps --only-binary=:all: -r "
    "recipe/scripts/ci/ni08_c5_policy_path_capture_requirements.txt"
)
RUNNER_CONTEXT = "ubuntu-24.04"
SOURCE_CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
WORKFLOW = ".github/workflows/ni08-c5-policy-path-capture.yml"
VB_SOURCE_TABLE = "scripts/vidya/adapters/README.md"
VB_SOURCE_TABLE_SHA256 = "b2ca24a53690daeda3b24732842517cd43c4e6b316f41ae745164a6751421ba6"
EVIDENCE_SOURCE = "scripts/kernel_rnd/autokernel/evidence/c5-sol-bound-policy-20260815.md"
EVIDENCE_SOURCE_SHA256 = "c8cec57941b5c0954cd65b44719b984612d9c25094fce3e2ef4bcd42e8ec4f70"
APP_LOCK = "uv.lock"
TASK_SOURCE = "handoffs/active/agentic-rocm-kernel-authoring.md"
TASK_SOURCE_SHA256 = "2662c7de6ae64399805fc132b65b19a25ddd25e3de7fb021a973fedd383a77de"

RESEARCH_READS = (
    *SELECTIONS,
    "pyproject.toml",
    "scripts/kernel_rnd/autokernel/__init__.py",
    "scripts/kernel_rnd/autokernel/c5_seed_corpus.py",
    "scripts/kernel_rnd/autokernel/c5_seed_corpus.json",
    "scripts/kernel_rnd/autokernel/evidence/c5-sol-bound-policy-20260815.md",
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


def tracked_source_context(repo: Path) -> list[Path]:
    names = git(repo, "ls-files", "-z").split("\0")
    selected = []
    for name in names:
        if not name:
            continue
        relative = Path(name)
        if relative.suffix == ".py" or relative.name in SOURCE_CONFIG_NAMES:
            selected.append(regular_repo_file(repo, name))
    return selected


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
    result = runner_temp / "ni08-c5-policy-path-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status: dict[str, Any] = {
        "state": "preparing", "job": "c5-policy-path-capture", "exit_code": None,
    }
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if platform.python_version() != PYTHON_PIN:
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("C5_RUNNER_CONTEXT") != RUNNER_CONTEXT:
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("C5_INSTALL_COMMAND") != INSTALL_COMMAND:
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
            WORKFLOW, INSTALL_REQUIREMENTS, EXPECTED_CASES_PATH, TASK_SOURCE, VB_SOURCE_TABLE,
        )]
        runner = regular_repo_file(recipe, "scripts/ci/ni08_c5_policy_path_capture.py")
        research_reads = [regular_repo_file(research, name) for name in RESEARCH_READS]
        carrier_reads = [regular_repo_file(carrier, name) for name in CARRIER_READS]
        app_lock = regular_repo_file(app, APP_LOCK)
        requirements = regular_repo_file(recipe, INSTALL_REQUIREMENTS)
        task_source = regular_repo_file(recipe, TASK_SOURCE)
        if hashlib.sha256(task_source.read_bytes()).hexdigest() != TASK_SOURCE_SHA256:
            raise RuntimeError("ROOT task source bytes differ from the reviewed pin")
        vb_source_table = regular_repo_file(recipe, VB_SOURCE_TABLE)
        if hashlib.sha256(vb_source_table.read_bytes()).hexdigest() != VB_SOURCE_TABLE_SHA256:
            raise RuntimeError("ROOT VB source-table bytes differ from the reviewed pin")
        evidence_source = regular_repo_file(research, EVIDENCE_SOURCE)
        if hashlib.sha256(evidence_source.read_bytes()).hexdigest() != EVIDENCE_SOURCE_SHA256:
            raise RuntimeError("recovered C5 policy evidence bytes differ from the pinned authority")
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
        install_log = result / "dependency-install.log"
        if install_log.is_symlink() or not install_log.is_file():
            raise RuntimeError("dependency installer log is missing or nonregular")
        root_context = tracked_source_context(recipe)
        research_context = tracked_source_context(research)
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version,
            "platform": platform.platform(),
            "runner_context": RUNNER_CONTEXT,
            "install_command": INSTALL_COMMAND,
            "requirements_sha256": hashlib.sha256(requirements.read_bytes()).hexdigest(),
            "dependency_install_log_sha256": hashlib.sha256(install_log.read_bytes()).hexdigest(),
            "repositories": pins,
            "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES,
            "case_identity_source": "static AST manifest; exact expanded JUnit multiset checked after execution",
            "task_source": {"repo": "recipe", "path": TASK_SOURCE,
                            "sha256": TASK_SOURCE_SHA256},
            "vidya_source_table": {"repo": "recipe", "path": VB_SOURCE_TABLE,
                                   "sha256": VB_SOURCE_TABLE_SHA256},
            "historical_policy_artifact": {"repo": "research", "path": EVIDENCE_SOURCE,
                                           "sha256": EVIDENCE_SOURCE_SHA256},
            "dependency_lock": {"repo": "app", "pin": APP_PIN, "path": APP_LOCK,
                                "sha256": hashlib.sha256(app_lock.read_bytes()).hexdigest()},
            "dependency_set": LOCKED_PACKAGES,
            "pytest_plugin_autoload": os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"],
            "bytecode_writes": os.environ["PYTHONDONTWRITEBYTECODE"],
            "python_hash_seed": os.environ["PYTHONHASHSEED"],
            "dependency_basis": "Five exact pytest runtime packages from pinned APP uv.lock; installed in an isolated Python 3.13.15 venv with --require-hashes --no-deps --only-binary=:all:. The installer log, requirements file, APP uv.lock, pip-freeze, and full tracked ROOT/Research source/config context are in the native readset.",
            "scope": "Persisted seed/provider ID join, metadata validation, and synthetic offline refusal controls only. No SOL provider execution, inference, GPU, kernel build, benchmark, model, or measured correctness/timing/promotion claim.",
            "import_closure_note": "The context test imports controller.authoring_contract, which necessarily runs controller/__init__.py and imports do_not_repeat/hypotheses plus their local import closure. Test bodies do not call those storage/claim APIs, provider runners, OpenCode/model clients, GPU paths, or external commands; the C5 compile-plan tests mock the actual provider audit and driver renderer.",
            "historical_policy_boundary": "The exact pinned c8cec... policy bytes are included as a tracked Research source input. The selected tests exercise the actual default verified load and repo-relative tamper, missing-file, traversal, symlink and hardlink refusal controls; no policy claims or authority are changed.",
            "source_context": {"root_tracked_source_config_count": len(root_context),
                              "research_tracked_source_config_count": len(research_context)},
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit, native = result / "original-junit.xml", result / "native"
        if junit.exists() or native.exists():
            raise RuntimeError("refusing to overwrite existing capture outputs")
        read_paths = [*recipe_reads, runner, *root_context, *research_reads, *research_context,
                      *carrier_reads, app_lock, requirements, install_log, freeze, environment]
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

        originals = [*native_files(native), junit, freeze, environment, install_log, requirements]
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
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        analysis.update(
            original_before_sha256=before,
            original_after_sha256=after,
            measurement_id=claim.measurement_id,
            source_kind=claim.source_kind,
            binding_kind=claim.binding_kind,
            grade={"Q": q, "T": t, "reasons": reasons},
        )
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
