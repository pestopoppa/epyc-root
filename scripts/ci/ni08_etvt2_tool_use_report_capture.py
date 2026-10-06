"""Capture the exact ETV-T2 synthetic test cohort through the existing carrier."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "5c7333daf92cb1b1131abdbb3be733a0b4851163"
SELECTIONS = (
    "tests/unit/test_tool_use_divergence_report.py::test_report_counts_only_known_attempted_scoreable_rows",
    "tests/unit/test_tool_use_divergence_report.py::test_no_known_attempted_scored_rows_has_no_rate",
    "tests/unit/test_tool_use_divergence_report.py::test_malformed_rows_traces_and_scores_remain_visible",
    "tests/unit/test_tool_use_divergence_report.py::test_batch_completion_requires_one_matching_complete_marker",
    "tests/unit/test_tool_use_divergence_report.py::test_empty_input_and_known_no_call_do_not_create_zero_divergence_claim",
    "tests/unit/test_tool_use_divergence_report.py::test_cli_accepts_no_paths",
    "tests/unit/test_tool_use_divergence_report.py::test_arms_and_batches_remain_separate_and_paths_are_deduplicated",
    "tests/unit/test_tool_use_divergence_report.py::test_duplicate_keys_nonfinite_unidentified_and_nonobject_rows_taint_completion",
    "tests/unit/test_tool_use_divergence_report.py::test_unreadable_and_invalid_utf8_inputs_are_reported",
    "tests/unit/test_tool_use_divergence_report.py::test_unidentified_batch_keys_are_not_collapsed_and_mark_file_partial",
    "tests/unit/test_tool_use_divergence_report.py::test_markdown_cells_escape_pipes_and_newlines",
)
EXPECTED_CASES = 11
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
APP_CONTEXTS = (
    "scripts/autopilot/tool_use_divergence_report.py",
    "tests/unit/test_tool_use_divergence_report.py",
    "scripts/autopilot/eval_tower.py",
)
APP_CONFIG_EXTRAS = ()
WORKFLOW_PATH = ".github/workflows/ni08-etvt2-tool-use-report-capture.yml"
LOCKED_FIXTURE_PACKAGES = {
    "pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
    "pluggy": "1.6.0", "Pygments": "2.20.0",
}
INSTALL_COMMAND = (
    "python -m pip install pytest==9.0.3 iniconfig==2.3.0 packaging==26.0 "
    "pluggy==1.6.0 Pygments==2.20.0"
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
    return path.absolute()


def tracked_python_config(repo: Path) -> list[Path]:
    paths = []
    for name in git(repo, "ls-files", "-z").split("\0"):
        if not name:
            continue
        relative = PurePosixPath(name)
        if relative.suffix == ".py" or relative.name in CONFIG_NAMES:
            paths.append(regular_repo_file(repo, name))
    return paths


def verify_locked_packages(app: Path) -> None:
    lock = tomllib.loads((app / "uv.lock").read_text(encoding="utf-8"))
    locked = {item["name"].lower(): item["version"] for item in lock["package"]}
    for name, expected in LOCKED_FIXTURE_PACKAGES.items():
        if locked.get(name.lower()) != expected:
            raise RuntimeError(f"{name} differs from pinned APP uv.lock")
        if importlib.metadata.version(name) != expected:
            raise RuntimeError(f"{name} differs from reviewed test dependency pin")


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / n for n in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni08-etvt2-tool-use-report-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "etvt2-tool-use-report-synthetic-capture", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ.get("NI08_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("NI08_EXECUTION_CONTEXT") != "offline-native-tool-use-jsonl-fixtures":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("NI08_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        expected_pins = {"recipe": os.environ["GITHUB_SHA"], "carrier": ROOT_CARRIER_PIN, "app": APP_PIN}
        pins = {}
        for name, repo in repos.items():
            pins[name] = require_clean(repo, name)
            if pins[name] != expected_pins[name]:
                raise RuntimeError(f"{name} checkout differs from reviewed pin")
        if os.environ.get("ROOT_CARRIER_PIN") != ROOT_CARRIER_PIN:
            raise RuntimeError("workflow carrier pin differs from reviewed carrier")
        if os.environ.get("APP_PIN") != APP_PIN:
            raise RuntimeError("workflow APP pin differs from reviewed source")
        verify_locked_packages(app)

        freeze = result / "pip-freeze.txt"
        freeze.write_bytes(subprocess.check_output([sys.executable, "-m", "pip", "freeze", "--all"]))
        environment = result / "environment.json"
        environment.write_text(json.dumps({
            "python": sys.version, "platform": platform.platform(),
            "runner_context": os.environ["NI08_RUNNER_CONTEXT"],
            "execution_context": os.environ["NI08_EXECUTION_CONTEXT"],
            "repositories": pins, "selections": list(SELECTIONS),
            "expected_case_count": EXPECTED_CASES, "install_command": INSTALL_COMMAND,
            "declared_dependencies": LOCKED_FIXTURE_PACKAGES,
            "dependency_basis": (
                "The selected report module and its JSONL fixtures use Python stdlib; "
                "pytest and its four runtime dependencies are exact APP uv.lock entries. "
                "The eval_tower producer is captured as read-bound context and is not imported."
            ),
            "isolation": (
                "Exact node selections operate on temporary synthetic JSONL rows, exercise "
                "the report CLI, and perform no inference, scoring service, benchmark, "
                "server, or live artifact read. This receipt records fixture-test execution "
                "only; it does not claim representative tool-use quality or gate authority."
            ),
            "app_config_extras": [],
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit, native_output = result / "original-junit.xml", result / "native"
        if junit.exists() or native_output.exists():
            raise RuntimeError("refusing to overwrite existing capture outputs")
        workflow = regular_repo_file(recipe, WORKFLOW_PATH)
        app_context_paths = [regular_repo_file(app, relative) for relative in APP_CONTEXTS]
        app_config_paths = [regular_repo_file(app, relative) for relative in APP_CONFIG_EXTRAS]
        read_paths = [
            freeze, environment, workflow,
            *tracked_python_config(recipe), *tracked_python_config(carrier),
            *tracked_python_config(app), *app_context_paths, *app_config_paths,
        ]
        producer_argv = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(app), "--junit", str(junit), "--output", str(native_output),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}", "--repo", f"app={app}",
        ]
        for path in dict.fromkeys(path.resolve() for path in read_paths):
            producer_argv.extend(["--read-path", str(path)])
        for selection in SELECTIONS:
            producer_argv.extend(["--select", selection])
        command = [
            sys.executable, "-m", "pytest", "--noconftest", "-o", "addopts=",
            "-p", "no:cacheprovider", "-q", *SELECTIONS, f"--junitxml={junit}",
        ]
        status.update(state="running", repositories=pins, selections=list(SELECTIONS))
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
        code = subprocess.call([*producer_argv, "--", *command], cwd=app)
        receipt_path = native_output / "receipt.json"
        if not receipt_path.is_file():
            status.update(state="capture_failed", exit_code=code or 1,
                          diagnostic="native receipt was not produced")
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        counts = (receipt.get("summary") or {}).get("counts") or {}
        case_gate = (
            counts.get("collected") == EXPECTED_CASES
            and counts.get("executed") == EXPECTED_CASES
            and counts.get("skipped") == 0
            and counts.get("failure") == 0
            and counts.get("error") == 0
        )
        originals = [*sorted(native_output.iterdir()), junit, freeze, environment]
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt_path)
        analysis = {
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
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in originals}
        if after != before:
            raise RuntimeError("shared-grade analysis changed an original")
        with (result / "shared-grade.json").open("x") as handle:
            json.dump(analysis, handle, indent=2, sort_keys=True)
            handle.write("\n")
        passed = code == 0 and metric is True and case_gate
        status.update(state="passed" if passed else "failed",
                      exit_code=0 if passed else (code or 1), native_metric=metric,
                      junit_counts=counts, expected_case_count=EXPECTED_CASES,
                      all_cases_executed=case_gate)
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1,
                      error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
