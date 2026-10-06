"""Capture the approved bounded MF-VBS2 original fixtures on a hosted runner only.

This producer intentionally has no local-dispatch mode. The workflow invoking it
captures only a reviewed source commit on a hosted runner.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
import traceback

ROOT_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "c0263f8c36f3042e9a8145d03dfda63952ade199"
APP_BLOBS = {
    "src/graph/helpers.py": "64e8fb412a42c608d07c1880593a905dff82e2bc",
    "src/batch_edit_parse.py": "1a917c9691238414730945436f00fbb2aae42f17",
    "src/batch_edit.py": "2cacb2bc056043d1fa691fd0255c2801cfcee127",
    "src/batch_edit_runner.py": "3fcebbf7a7d9438be2889cbcc4c5ce2bbbb90a6a",
    "tests/unit/test_graph_helpers_batch_edit.py": "ed05a963cff15fdda0ee444fcc92894b73354025",
    "pyproject.toml": "b4fe6ccada3a1aee3e08aa860045a78d8b85c7b1",
    "uv.lock": "ef2306018773ff9a1e80389970d92f66fcf8d5b7",
}
ROOT_BLOBS = {
    "scripts/ci/native_conformance.py": "d2d7bd90f86cffa23c51db803288641c5c6fe461",
    "scripts/vidya/adapters/ci_conformance.py": "b5a521ef4debe7ad105830f5fa27bbf9c2168dcd",
    "scripts/vidya/claim_tuple.py": "309af769e45245fd1452482eb2e0592a86a4a79f",
}
SELECTIONS = [
    "tests/unit/test_graph_helpers_batch_edit.py::test_flag_off_returns_none_even_with_valid_patchset",
    "tests/unit/test_graph_helpers_batch_edit.py::test_verify_failure_does_not_promote",
    "tests/unit/test_graph_helpers_batch_edit.py::test_verify_command_uses_full_tree_sandbox",
    "tests/unit/test_graph_helpers_batch_edit.py::test_verifier_label_uses_the_command_snapshot",
    "tests/unit/test_graph_helpers_batch_edit.py::test_syntax_only_success_is_not_described_as_acceptance_verified",
    "tests/unit/test_graph_helpers_batch_edit.py::test_verify_command_failure_does_not_promote",
    "tests/unit/test_graph_helpers_batch_edit.py::test_stale_base_does_not_promote",
    "tests/unit/test_graph_helpers_batch_edit.py::test_telemetry_distinguishes_absent_vs_malformed",
    "tests/unit/test_graph_helpers_batch_edit.py::test_telemetry_records_applied_and_verify_failed",
]


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def checked_tree(repo: Path, commit: str, blobs: dict[str, str]) -> None:
    if git(repo, "rev-parse", "HEAD") != commit:
        raise RuntimeError(f"unexpected repository revision for {repo}")
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError(f"tracked worktree is dirty: {repo}")
    for rel, expected in blobs.items():
        if git(repo, "rev-parse", f"HEAD:{rel}") != expected:
            raise RuntimeError(f"source fingerprint mismatch: {repo}/{rel}")
        if not (repo / rel).is_file():
            raise RuntimeError(f"declared source is missing: {repo}/{rel}")


def module_from_file(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pinned source: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_lock_pinned_test_dependencies(app: Path, venv_python: Path) -> tuple[str, list[Path]]:
    """Install the exact pytest closure from uv.lock, without implicit dependencies."""
    lock_path = app / "uv.lock"
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    locked = {
        item["name"].lower().replace("_", "-"): item["version"]
        for item in lock.get("package", [])
    }
    # The APP's locked pytest closure on the pinned Ubuntu 24.04 / Python 3.13.15
    # runner. Conditional typing-extensions edge is excluded by the lock marker.
    closure = {
        "iniconfig": "2.3.0", "packaging": "26.0", "pluggy": "1.6.0",
        "pygments": "2.20.0", "pytest": "9.0.3", "pytest-asyncio": "1.3.0",
    }
    if sys.version_info[:3] != (3, 13, 15):
        raise RuntimeError("capture runner must use Python 3.13.15")
    for name, version in closure.items():
        if locked.get(name) != version:
            raise RuntimeError(f"APP uv.lock dependency pin changed: {name}")
    lines = [f"{name}=={version}" for name, version in sorted(closure.items())]
    install_file = Path(os.environ["RUNNER_TEMP"]) / "mf-vbs2-requirements.txt"
    install_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [str(venv_python), "-m", "pip", "install", "--disable-pip-version-check",
               "--no-deps", "-r", str(install_file)]
    subprocess.run(command, check=True)
    import importlib.metadata
    for name, version in closure.items():
        actual = importlib.metadata.version(name)
        if actual != version:
            raise RuntimeError(f"installed test dependency mismatch: {name}=={actual}, expected {version}")
    installed = subprocess.check_output([str(venv_python), "-m", "pip", "freeze", "--all"], text=True)
    freeze_path = Path(os.environ["RUNNER_TEMP"]) / "mf-vbs2-pip-freeze.txt"
    freeze_path.write_text(installed, encoding="utf-8")
    return " ".join(command), [install_file, freeze_path]


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    recipe = workspace / "recipe"
    carrier = workspace / "carrier"
    app = workspace / "app"
    result = Path(os.environ["RUNNER_TEMP"]) / "ni08-mf-vbs2" / "result"
    work = Path(os.environ["RUNNER_TEMP"]) / "ni08-mf-vbs2" / "work"
    result.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "exit_code": None}
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    try:
        checked_tree(recipe, os.environ["GITHUB_SHA"], {
            "scripts/ci/mf_vbs2_capture.py": git(recipe, "rev-parse", f"HEAD:scripts/ci/mf_vbs2_capture.py"),
            "scripts/ci/mf_vbs2_ast_fixture.py": git(recipe, "rev-parse", f"HEAD:scripts/ci/mf_vbs2_ast_fixture.py"),
            "scripts/ci/mf-vbs2-native-fixtures.md": git(recipe, "rev-parse", f"HEAD:scripts/ci/mf-vbs2-native-fixtures.md"),
            ".github/workflows/mf-vbs2-native-fixtures.yml": git(recipe, "rev-parse", f"HEAD:.github/workflows/mf-vbs2-native-fixtures.yml"),
        })
        checked_tree(carrier, ROOT_PIN, ROOT_BLOBS)
        checked_tree(app, APP_PIN, APP_BLOBS)
        python_bin = Path(sys.executable)
        install_command, install_artifacts = install_lock_pinned_test_dependencies(app, python_bin)

        bootstrap_path = recipe / "scripts/ci/mf_vbs2_ast_fixture.py"
        test_path = work / "test_mf_vbs2_selected_original.py"
        os.environ["MF_VBS2_APP_ROOT"] = str(app)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        os.environ.pop("ORCHESTRATOR_BATCH_EDIT_VERIFY_CMD", None)
        os.environ.pop("ORCHESTRATOR_BATCH_EDIT_VERIFY_TIMEOUT_SEC", None)
        os.environ["PYTHONPATH"] = os.pathsep.join(
            [str(recipe / "scripts/ci"), str(app), os.environ.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        bootstrap = module_from_file("mf_vbs2_ast_fixture", bootstrap_path)
        selected = bootstrap.extract_original_tests(app, test_path)
        junit = work / "junit.xml"
        native_output = result / "native"
        if junit.exists() or native_output.exists():
            raise RuntimeError("capture paths must be fresh; no old-run reuse")

        native_path = carrier / "scripts/ci/native_conformance.py"
        native = module_from_file("mf_vbs2_native_conformance", native_path)
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        adapter = module_from_file(
            "mf_vbs2_ci_conformance_adapter", carrier / "scripts/vidya/adapters/ci_conformance.py"
        )
        claim_tuple = sys.modules["claim_tuple"]
        env = {
            "python": sys.version,
            "platform": platform.platform(),
            "install_command": install_command,
            "installed_packages_sha256": file_digest(install_artifacts[1]),
            "reproducibility": "pytest and pytest-asyncio plus their dependency closure are installed from exact APP uv.lock package pins; installed package freeze is retained",
            "isolation": "AST-extracted original selected test bodies; exact APP parser/core/runner modules; only src.features and task-root request-scope/import edges are stubbed; _record_session_turn is stubbed by original autouse fixture; no graph import, model, API, process, runtime or benchmark",
            "child_environment": {
                name: os.environ.get(name) for name in (
                    "MF_VBS2_APP_ROOT", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
                    "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "ORCHESTRATOR_BATCH_EDIT_VERIFY_CMD",
                    "ORCHESTRATOR_BATCH_EDIT_VERIFY_TIMEOUT_SEC",
                )
            },
        }
        env_path = result / "environment.json"
        env_path.write_text(json.dumps(env, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        # Bind every tracked Python/source-config input by path, mode and Git blob ID.
        # This includes adapter imports; the immutable Git tree plus the captured
        # manifest makes the wider source context reviewable without copying data files.
        context = []
        selector = "*.py *.pyi *.toml *.yaml *.yml *.ini *.cfg *.lock *.json"
        for label, repo in (("recipe", recipe), ("carrier", carrier), ("app", app)):
            entries = git(repo, "ls-files", "--stage", "--", *selector.split()).splitlines()
            context.extend(f"{label}\t{line}" for line in entries)
        context_path = result / "tracked-source-config-context.tsv"
        context_path.write_text("\n".join(sorted(context)) + "\n", encoding="utf-8")
        read_paths = [
            recipe / ".github/workflows/mf-vbs2-native-fixtures.yml",
            recipe / "scripts/ci/mf_vbs2_capture.py",
            bootstrap_path,
            recipe / "scripts/ci/mf-vbs2-native-fixtures.md",
            carrier / "scripts/ci/native_conformance.py",
            carrier / "scripts/vidya/adapters/ci_conformance.py",
            carrier / "scripts/vidya/claim_tuple.py",
            app / "uv.lock",
            app / "pyproject.toml",
            app / "src/graph/helpers.py",
            app / "src/batch_edit_parse.py",
            app / "src/batch_edit.py",
            app / "src/batch_edit_runner.py",
            app / "tests/unit/test_graph_helpers_batch_edit.py",
            test_path,
            env_path,
            context_path,
            *install_artifacts,
        ]
        argv = [
            str(python_bin), "-m", "pytest", "-o", "addopts=", "--noconftest",
            "-p", "no:cacheprovider", "-p", "pytest_asyncio.plugin", "-q",
            f"--junitxml={junit}", str(test_path),
        ]
        status.update(state="running")
        status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        record = native.capture_fixture_execution(
            argv=argv,
            cwd=work,
            junit=junit,
            output=native_output,
            repositories={"recipe": recipe, "carrier": carrier, "orchestrator": app},
            read_paths=read_paths,
            selections=selected,
        )

        expected_names = [selection.rsplit("::", 1)[1] for selection in SELECTIONS]
        cases = record.get("summary", {}).get("cases", [])
        counts = record.get("summary", {}).get("counts", {})
        expected_identities = [("test_mf_vbs2_selected_original", name) for name in expected_names]
        actual_identities = [(case.get("classname"), case.get("name")) for case in cases]
        expected_counts = {"passed": 9, "failure": 0, "error": 0,
                           "skipped": 0, "collected": 9, "executed": 9}
        if actual_identities != expected_identities or counts != expected_counts:
            raise RuntimeError(f"native result is not exactly the selected nine: identities={actual_identities!r}, counts={counts!r}")

        original_paths = sorted(path for path in native_output.rglob("*") if path.is_file())
        originals_before = {str(path.relative_to(native_output)): file_digest(path) for path in original_paths}
        rows = adapter.native_rows(native_output / "receipt.json")
        grade_result = None
        if len(rows) == 1:
            tuple_value = adapter.project_ci_conformance(rows[0])
            grade_result = claim_tuple.grade(tuple_value)
        if len(rows) != 1 or not grade_result or grade_result[0] != "Judged" or grade_result[1] != "Located":
            raise RuntimeError(f"expected exactly one shared-grade Judged/Located row; rows={len(rows)}, grade={grade_result!r}")
        originals_after = {str(path.relative_to(native_output)): file_digest(path)
                           for path in sorted(path for path in native_output.rglob("*") if path.is_file())}
        if originals_before != originals_after:
            raise RuntimeError("shared-grade analysis changed an original captured artifact")
        analysis = {
            "scope": "prospective selected MF-VBS2 fixture observation only",
            "native_rows": len(rows),
            "expected_case_names": expected_names,
            "expected_case_identities": expected_identities,
            "actual_case_identities": actual_identities,
            "counts": counts,
            "shared_grade": grade_result,
            "original_artifact_sha256_before": originals_before,
            "original_artifact_sha256_after": originals_after,
            "originals_unchanged": True,
            "claim_limit": "No full graph/app claim, no owner-command safety claim, no semantic postcondition execution, no runtime/API/deployment claim, no model quality or performance warrant.",
        }
        (result / "shared-grade-analysis.json").write_text(
            json.dumps(analysis, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        status.update(
            state="passed" if record["fixture_execution_conformant"] is True else "failed",
            exit_code=record["exit_code"],
            conformant=record["fixture_execution_conformant"],
            receipt_sha256=record["receipt_sha256"],
        )
        return 0 if status["state"] == "passed" else 1
    except Exception as exc:  # retained so the hosted artifact explains setup/readset failures
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
