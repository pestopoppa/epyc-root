"""Capture scoped AutoPilot diagnostic fixtures; grade unchanged originals off host."""
from __future__ import annotations
import hashlib, importlib.metadata, json, os, platform, subprocess, sys, tomllib
from pathlib import Path, PurePosixPath

ROOT_CARRIER_PIN = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
APP_PIN = "15e5b52ec8941c8a46211d363cc9b6774813b30b"
SELECTIONS = ('tests/unit/test_failure_signatures.py::test_machine_identity_only_actual_failure_codes', 'tests/unit/test_failure_signatures.py::test_scope_is_explicit_and_missing_means_unknown', 'tests/unit/test_failure_signatures.py::test_total_prior_not_streak_and_churn_does_not_identify_failure', 'tests/unit/test_failure_signatures.py::test_trust_axes_never_count', 'tests/unit/test_failure_signatures.py::test_native_append_reload_and_no_legacy_backfill', 'tests/unit/test_failure_signatures.py::test_folded_history_recount_ignores_superseded_corruption', 'tests/unit/test_failure_signatures.py::test_compact_render_preserves_typed_and_unknown_negative_evidence', 'tests/unit/test_failure_signatures.py::test_invalid_schema_primitives_and_explicit_exclusion_stay_unknown', 'tests/unit/test_failure_signatures.py::test_record_unknown_fast_path_does_not_read_fold', 'tests/unit/test_failure_signatures.py::test_empty_prose_machine_failure_remains_visible_and_scope_disambiguates', 'tests/unit/test_failure_signatures.py::test_insight_render_folds_history_once', 'tests/unit/test_stm_generated_view.py::test_short_term_memory_refresh_rebuilds_from_folded_journal', 'tests/unit/test_stm_generated_view.py::test_render_generated_stm_excludes_superseded_corrupted_rows', 'tests/unit/test_stm_generated_view.py::test_render_generated_stm_excludes_learning_and_invalid_rows', 'tests/unit/test_stm_generated_view.py::test_render_generated_stm_uses_sanitized_failure_and_weak_suite_context', 'tests/unit/test_journal_prompt_sanitization.py::test_summary_text_sanitizes_legacy_scale_failure_analysis', 'tests/unit/test_journal_prompt_sanitization.py::test_insight_renderers_sanitize_legacy_scale_failure_analysis', 'tests/unit/test_journal_prompt_sanitization.py::test_current_scale_failure_analysis_is_preserved', 'tests/unit/test_experiment_journal_measurement.py::test_record_populates_the_tuple_and_it_survives_a_reload', 'tests/unit/test_experiment_journal_measurement.py::test_rows_written_before_the_hook_load_with_an_empty_tuple', 'tests/unit/test_experiment_journal_durability.py::test_append_path_writes_newline_terminated_parseable_rows')
EXPECTED_CASES = 21
CONFIG_NAMES = {
    "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini", "uv.lock",
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
}
APP_CONTEXTS = (
    "scripts/autopilot/autopilot.py", "scripts/autopilot/experiment_journal.py",
    "scripts/autopilot/stm_generated_view.py", "scripts/autopilot/short_term_memory.py",
    "scripts/autopilot/species/evolution_manager.py", "scripts/autopilot/context_budget.py",
    "scripts/autopilot/journal_shards.py", "src/autopilot_core/tier_specs.py",
    "src/trace/__init__.py", "src/trace/emit.py", "src/trace/store.py",
    "src/trace/query.py", "src/trace/harness_schema.py",
    "docs/autopilot/failure-signatures.md",
)
APP_CONFIG_EXTRAS = ()
WORKFLOW_PATH = ".github/workflows/ni08-failure-signatures-capture.yml"
LOCKED_FIXTURE_PACKAGES = {
    "pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
    "pluggy": "1.6.0", "Pygments": "2.20.0",
}
INSTALL_COMMAND = (
    "python -m pip install pytest==9.0.3 iniconfig==2.3.0 packaging==26.0 "
    "pluggy==1.6.0 Pygments==2.20.0"
)
INERT_KERNEL_OVERRIDES = {
    "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "/fixture/kernel-bin",
    "ORCHESTRATOR_PATHS_LLAMA_MTMD": "/fixture/llama-mtmd-cli",
    "ORCHESTRATOR_PATHS_LLAMA_SERVER": "/fixture/llama-server",
}

def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def require_clean(repo: Path, label: str) -> str:
    status = git(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError(f"{label} checkout is not clean: {status}")
    return git(repo, "rev-parse", "HEAD")

def regular_repo_file(repo: Path, name: str) -> Path:
    path = repo
    if path.is_symlink():
        raise RuntimeError(f"repository checkout is a symlink: {repo}")
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
        actual = importlib.metadata.version(name)
        if actual != expected:
            raise RuntimeError(f"{name} is {actual}, expected {expected}")

def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    recipe, carrier, app = (workspace / n for n in ("recipe", "carrier", "app"))
    repos = {"recipe": recipe, "carrier": carrier, "app": app}
    result = runner_temp / "ni08-failure-signatures-capture" / "result"
    result.mkdir(parents=True, exist_ok=True)
    status_path = result / "status.json"
    status = {"state": "preparing", "job": "failure-signatures-synthetic-capture", "exit_code": None}
    status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")
    try:
        if os.environ.get("NI08_RUNNER_CONTEXT") != "ubuntu-latest":
            raise RuntimeError("runner context differs from reviewed recipe")
        if os.environ.get("NI08_EXECUTION_CONTEXT") != "offline-native-journal-fixtures":
            raise RuntimeError("execution context differs from reviewed recipe")
        if platform.python_version() != "3.13.15":
            raise RuntimeError(f"Python runtime differs from pin: {platform.python_version()}")
        if os.environ.get("NI08_INSTALL_COMMAND") != INSTALL_COMMAND:
            raise RuntimeError("install command differs from reviewed recipe")
        for name, value in INERT_KERNEL_OVERRIDES.items():
            if os.environ.get(name) != value:
                raise RuntimeError(f"{name} differs from reviewed inert-kernel override")
        expected_pins = {
            "recipe": os.environ["GITHUB_SHA"],
            "carrier": ROOT_CARRIER_PIN,
            "app": APP_PIN,
        }
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
                "Selected fixtures import experiment_journal -> tier_specs/journal_shards, "
                "STM -> context_budget, and lazy journal trace emission -> src.trace "
                "store/query/harness_schema. These closures use only Python stdlib. "
                "The five pytest packages match pinned APP uv.lock. AutoPilot main and "
                "EvolutionManager producer/callers are read-bound source context, never imported. "
                "The existing carrier/adapter/shared grade uses stdlib and its own bound source."
            ),
            "isolation": (
                "Exact node selections use synthetic JournalEntry rows, temporary native "
                "TSV/JSONL/supersession ledgers and bounded rendering. No action dispatch, "
                "LLM/backend, endpoint, model, embedding, benchmark, kernel or serving process "
                "is invoked. Optional native trace emission is stdlib SQLite only, on hosted runner."
            ),
            "inert_kernel_overrides": INERT_KERNEL_OVERRIDES,
            "app_config_extras": [],
            "configuration_context": {
                "eager_app_data_reads": [],
                "synthetic_temp_inputs": "pytest tmp_path fixtures authored during selected cases",
                "kernel_path_use": "none; no kernel path opened or executed",
                "undeclared_dependency_completeness": "excluded from native proposition",
            },
            "environment": {key: os.environ.get(key) for key in (
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTHONDONTWRITEBYTECODE",
                "PYTHONHASHSEED", "PYTHONPATH", "PYTHONUNBUFFERED",
                "ORCHESTRATOR_MOCK_MODE", "ORCHESTRATOR_LOG_DIR",
                "ORCHESTRATOR_SERVING_CALLS_LOG", "ORCHESTRATOR_COHERENCE_JUDGE_LOG",
                *INERT_KERNEL_OVERRIDES,
            )},
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        junit, native_output = result / "original-junit.xml", result / "native"
        if junit.exists() or native_output.exists():
            raise RuntimeError("refusing to overwrite existing capture outputs")
        workflow = recipe / WORKFLOW_PATH
        if workflow.is_symlink() or not workflow.is_file():
            raise RuntimeError("declared recipe workflow is missing or not regular")
        app_context_paths = [regular_repo_file(app, relative) for relative in APP_CONTEXTS]
        app_config_paths = [regular_repo_file(app, relative) for relative in APP_CONFIG_EXTRAS]
        for relative in APP_CONFIG_EXTRAS:
            tree_entry = git(app, "ls-tree", "-r", "HEAD", "--", relative).split(maxsplit=1)
            if not tree_entry or tree_entry[0] != "100644":
                raise RuntimeError(f"APP config extra is not tracked as a regular file: {relative}")

        read_paths = [
            freeze, environment, workflow.absolute(),
            *tracked_python_config(recipe), *tracked_python_config(carrier),
            *tracked_python_config(app), *app_context_paths, *app_config_paths,
        ]
        producer_argv = [
            sys.executable, str(carrier / "scripts/ci/native_conformance.py"),
            "--cwd", str(app), "--junit", str(junit), "--output", str(native_output),
            "--repo", f"recipe={recipe}", "--repo", f"carrier={carrier}",
            "--repo", f"app={app}",
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
            status.update(
                state="capture_failed", exit_code=code or 1,
                native_metric=None, diagnostic="native receipt was not produced",
            )
            return code or 1
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        metric = receipt.get("fixture_execution_conformant")
        summary = receipt.get("summary") or {}
        counts = summary.get("counts") or {}
        case_gate = (
            counts.get("collected") == EXPECTED_CASES
            and counts.get("executed") == EXPECTED_CASES
            and counts.get("skipped") == 0
            and counts.get("failure") == 0
            and counts.get("error") == 0
        )
        # ANALYSIS only: re-open original receipt through existing carrier and shared grade.
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
        status.update(
            state="passed" if passed else "failed",
            exit_code=0 if passed else (code or 1),
            native_metric=metric,
            junit_counts=counts,
            expected_case_count=EXPECTED_CASES,
            all_cases_executed=case_gate,
        )
        return 0 if passed else (code or 1)
    except Exception as exc:
        status.update(state="capture_failed", exit_code=1, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        status_path.write_text(json.dumps(status, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
