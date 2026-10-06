#!/usr/bin/env python3
"""Run the bounded NI08 synthetic APP-writer -> ROOT-adapter hosted capture."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_APP_COMMIT = "5caebd5f0a30b336a62114cd9c41b765392b07ea"
NODEIDS = (
    "tests/vidya/test_analysis_producer_roundtrip.py::test_actual_mf_producer_snapshot_round_trips_through_root_adapter",
    "tests/vidya/test_analysis_producer_roundtrip.py::test_actual_eval_producer_snapshot_round_trips_with_native_reps",
    "tests/vidya/test_analysis_report_adapters.py::test_immutable_input_snapshot_is_required_and_rechecked",
    "tests/vidya/test_analysis_report_adapters.py::test_report_bytes_and_retained_inputs_are_reverified_at_projection",
    "tests/vidya/test_analysis_report_adapters.py::test_mf_cached_metric_key_must_match_native_selection",
    "tests/vidya/test_analysis_report_adapters.py::test_identity_free_legacy_report_is_refused",
    "tests/vidya/test_analysis_report_adapters.py::test_unknown_native_fields_are_refused",
    "tests/vidya/test_analysis_report_adapters.py::test_category_must_be_producer_authored_diagnostic_baseline",
    "tests/vidya/test_analysis_report_adapters.py::test_producer_source_changes_preserve_snapshot_bound_historical_rows",
    "tests/vidya/test_analysis_report_adapters.py::test_snapshot_path_escape_is_refused",
    "tests/vidya/test_analysis_report_adapters.py::test_external_input_original_locator_is_metadata_only",
    "tests/vidya/test_analysis_report_adapters.py::test_zero_denominator_rate_is_omitted_while_defined_rates_remain",
    "tests/vidya/test_analysis_report_adapters.py::test_unbound_mf_scope_fields_cannot_be_supplied_by_report_envelope",
    "tests/vidya/test_analysis_report_adapters.py::test_eval_run_spread_with_one_eligible_run_is_omitted_even_if_cached_flag_is_false",
    "tests/vidya/test_analysis_report_adapters.py::test_eval_metric_reps_use_each_native_denominator",
    "tests/vidya/test_analysis_report_adapters.py::test_eval_cached_suite_and_metric_must_match_bound_report",
    "tests/vidya/test_analysis_report_adapters.py::test_cli_dispatch_uses_shared_grade_only",
    "tests/vidya/test_citation_gate.py::test_precise_in_range_but_uningested_claim_stays_unknown",
    "tests/vidya/test_citation_gate.py::test_precise_out_of_range_claim_is_blocking_dangling",
    "tests/vidya/test_citation_gate.py::test_out_of_range_claim_is_dangling_even_if_ledger_has_forged_matching_id",
    "tests/vidya/test_citation_gate.py::test_zero_claim_entry_marks_precise_zero_dangling",
    "tests/vidya/test_citation_gate.py::test_malformed_key_claims_count_preserves_unknown",
    "tests/vidya/test_citation_gate.py::test_key_claim_count_reader_preserves_malformed_and_duplicate_as_unknown",
    "tests/vidya/test_citation_gate.py::test_duplicate_yaml_key_in_entry_is_unknown_not_last_value",
    "tests/vidya/test_citation_gate.py::test_unhashable_yaml_mapping_key_preserves_unknown_counts",
    "tests/vidya/test_citation_gate.py::test_cite_check_cli_keeps_in_range_uningested_unknown_nonblocking",
    "tests/vidya/test_citation_gate.py::test_cite_check_cli_blocks_out_of_range_claim",
    "tests/vidya/test_claim_tuple.py::test_category_must_be_one_of_autokernels_three",
    "tests/vidya/test_claim_tuple.py::test_each_source_class_has_exactly_one_ladder",
    "tests/vidya/test_ingest_sources.py::test_every_source_is_a_cli_choice_and_the_literal_list_does_not_drift",
    "tests/vidya/test_ingest_sources.py::test_every_dispatched_adapter_declares_its_authority",
)
APP_NODEIDS = (
    "tests/test_analysis_report_provenance.py::test_mf_vbs_manifest_hashes_the_same_bytes_it_parsed",
    "tests/test_analysis_report_provenance.py::test_eval_discriminability_manifest_hashes_the_same_bytes_it_parsed",
    "tests/test_analysis_report_provenance.py::test_mf_vbs_edited_call_bearing_numerator_uses_intersection",
    "tests/test_analysis_report_provenance.py::test_mf_vbs_zero_denominators_are_unknown_json_values",
    "tests/test_analysis_report_snapshot_sealing.py::test_snapshots_are_private_and_identical_paths_deduplicate[_seal_eval]",
    "tests/test_analysis_report_snapshot_sealing.py::test_snapshots_are_private_and_identical_paths_deduplicate[_seal_mf]",
    "tests/test_analysis_report_snapshot_sealing.py::test_conflicting_duplicate_input_path_refuses_without_overwriting[_seal_eval]",
    "tests/test_analysis_report_snapshot_sealing.py::test_conflicting_duplicate_input_path_refuses_without_overwriting[_seal_mf]",
    "tests/test_analysis_report_snapshot_sealing.py::test_existing_snapshot_mismatch_refuses_instead_of_replacing[_seal_eval]",
    "tests/test_analysis_report_snapshot_sealing.py::test_existing_snapshot_mismatch_refuses_instead_of_replacing[_seal_mf]",
    "tests/test_analysis_report_snapshot_sealing.py::test_symlinked_snapshot_root_is_refused_without_chmod_target[_seal_eval]",
    "tests/test_analysis_report_snapshot_sealing.py::test_symlinked_snapshot_root_is_refused_without_chmod_target[_seal_mf]",
    "tests/test_eval_suite_discriminability.py::test_error_rows_excluded_from_brittleness_flip",
    "tests/test_eval_suite_discriminability.py::test_error_dominated_run_excluded_from_run_spread",
    "tests/test_eval_suite_discriminability.py::test_error_dominated_gate_is_configurable",
    "tests/test_eval_suite_discriminability.py::test_brittleness_unmeasured_single_run",
    "tests/test_eval_suite_discriminability.py::test_cli_main_writes_report",
    "tests/unit/test_stat_tests.py::test_wilson_degenerate_denominator",
    "tests/unit/test_stat_tests.py::test_wilson_published_values",
    "tests/unit/test_stat_tests.py::test_calibration_metric_bundle_concrete_values",
)

ROOT_READS = (
    ".github/workflows/ni08-vbs1-evaldisc-native.yml",
    "scripts/ci/ni08_run_hosted_capture.py",
    "scripts/ci/ni08_source_context.py",
    "scripts/ci/ni08-hosted-requirements.txt",
    "docs/reviews/ni08-vbs1-evaldisc-hosted-capture-recipe-20261006.md",
    "scripts/vidya/adapters/ci_conformance.py",
    "scripts/vidya/adapters/_analysis_report_provenance.py",
    "scripts/vidya/adapters/verify_before_stop.py",
    "scripts/vidya/adapters/eval_suite_discriminability.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/ingest_sources.py",
    "scripts/vidya/cli.py",
    "scripts/vidya/citation_gate.py",
    "scripts/vidya/wiki_dependents.py",
    "scripts/vidya/canonical.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/fold.py",
    "scripts/vidya/gate.py",
    "scripts/vidya/frames.py",
    "scripts/vidya/ledger.py",
    "tests/conftest.py",
    "tests/vidya/test_analysis_producer_roundtrip.py",
    "tests/vidya/test_analysis_report_adapters.py",
    "tests/vidya/test_citation_gate.py",
    "tests/vidya/test_claim_tuple.py",
    "tests/vidya/test_ingest_sources.py",
    "scripts/ci/native_conformance.py",
)
APP_READS = (
    "scripts/analysis/mf_vbs1_verify_before_stop.py",
    "scripts/analysis/eval_suite_discriminability.py",
    "src/llm_primitives/stat_tests.py",
    "src/llm_primitives/__init__.py",
    "uv.lock",
    "tests/test_analysis_report_provenance.py",
    "tests/test_analysis_report_snapshot_sealing.py",
    "tests/test_eval_suite_discriminability.py",
    "tests/unit/test_stat_tests.py",
    "tests/conftest.py",
)


def _write_once(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)


def _load_native_carrier():
    path = ROOT / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("ni08_native_conformance", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the pinned native conformance carrier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _context_manifest(app_root: Path, capture_root: Path) -> Path:
    output = capture_root / "source-context.json"
    command = [sys.executable, str(ROOT / "scripts/ci/ni08_source_context.py"),
               "--repo", f"root={ROOT}", "--repo", f"app={app_root}",
               "--output", str(output)]
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True)
    if completed.returncode:
        raise RuntimeError("source-context manifest generation failed")
    return output


def _artifact_snapshot(paths: tuple[Path, ...]) -> dict[str, str]:
    """Hash the original captured inputs without opening or resealing their receipts."""
    snapshot = {}
    for path in paths:
        if path.is_symlink():
            raise RuntimeError(f"captured source artifact became a symlink: {path.name}")
        if not path.exists():
            snapshot[str(path)] = "absent"
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_symlink():
                    raise RuntimeError(f"captured source artifact contains a symlink: {child.name}")
                if child.is_file():
                    snapshot[str(child)] = hashlib.sha256(child.read_bytes()).hexdigest()
                elif not child.is_dir():
                    raise RuntimeError(f"captured source artifact has a non-regular member: {child.name}")
        elif path.is_file():
            snapshot[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            raise RuntimeError(f"captured source artifact is not a regular file: {path.name}")
    return snapshot


def _install_locked_minimal_set(capture_root: Path) -> tuple[Path, str]:
    log_path = capture_root / "dependency-install.log"
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
               "--require-hashes", "-r", str(ROOT / "scripts/ci/ni08-hosted-requirements.txt")]
    completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True)
    _write_once(log_path, completed.stdout + b"\n--- stderr ---\n" + completed.stderr)
    if completed.returncode:
        raise RuntimeError("hash-locked hosted fixture dependency install failed")
    packages = {name: importlib.metadata.version(name) for name in
                ("pytest", "iniconfig", "packaging", "pluggy", "Pygments", "PyYAML")}
    if (sys.version_info[:3] != (3, 13, 15) or platform.system() != "Linux"
            or platform.machine().lower() not in {"x86_64", "amd64"}
            or packages != {"pytest": "9.0.3", "iniconfig": "2.3.0", "packaging": "26.0",
                            "pluggy": "1.6.0", "Pygments": "2.20.0", "PyYAML": "6.0.3"}):
        raise RuntimeError("hosted runtime or locked package versions differ from recipe")
    env = {"python": platform.python_version(), "system": platform.system(),
           "machine": platform.machine(), "packages": packages,
           "install_log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest()}
    _write_once(capture_root / "environment.json",
                (json.dumps(env, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return log_path, hashlib.sha256((capture_root / "environment.json").read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: ni08_run_hosted_capture.py APP_CHECKOUT FRESH_CAPTURE_DIR")
    app_root, capture_root = (Path(value).resolve() for value in sys.argv[1:])
    if not app_root.is_dir() or not capture_root.parent.is_dir() or os.path.lexists(capture_root):
        raise SystemExit("APP checkout must exist and capture directory must be fresh")
    app_commit = subprocess.check_output(
        ["git", "-C", str(app_root), "rev-parse", "HEAD"], text=True).strip()
    if app_commit != EXPECTED_APP_COMMIT:
        raise SystemExit(f"APP checkout pin mismatch: expected {EXPECTED_APP_COMMIT}")
    if os.path.lexists(ROOT / "ni08-native-fixtures"):
        raise SystemExit("synthetic generated-output directory already exists; use a fresh checkout")
    capture_root.mkdir(mode=0o700)
    install_log, _environment_sha = _install_locked_minimal_set(capture_root)
    manifest = _context_manifest(app_root, capture_root)

    os.environ.update({"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
                       "PYTHONDONTWRITEBYTECODE": "1",
                       "PYTHONHASHSEED": "0",
                       "PYTHONUNBUFFERED": "1"})
    os.environ["EPYC_ORCHESTRATOR_SOURCE_ROOT"] = str(app_root)
    os.environ["NI08_NATIVE_FIXTURE_CAPTURE_DIR"] = str(ROOT / "ni08-native-fixtures")
    reads = ([ROOT / name for name in ROOT_READS] + [app_root / name for name in APP_READS]
             + [manifest, install_log, capture_root / "environment.json"])
    carrier = _load_native_carrier()

    app_junit = capture_root / "app-original-junit.xml"
    app_native_output = capture_root / "app-native"
    app_argv = [sys.executable, "-m", "pytest", "-q", "--noconftest",
                f"--junitxml={app_junit}", *APP_NODEIDS]
    app_record = carrier.capture_fixture_execution(
        argv=app_argv, cwd=app_root, junit=app_junit, output=app_native_output,
        repositories={"root": str(ROOT), "app": str(app_root)},
        read_paths=reads, selections=list(APP_NODEIDS))

    junit = capture_root / "original-junit.xml"
    native_output = capture_root / "native"
    argv = [sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}", *NODEIDS]
    record = carrier.capture_fixture_execution(
        argv=argv, cwd=ROOT, junit=junit, output=native_output,
        repositories={"root": str(ROOT), "app": str(app_root)},
        read_paths=reads, selections=list(NODEIDS),
        generated_output_paths=["ni08-native-fixtures/mf-bundle.zip",
                                "ni08-native-fixtures/eval-bundle.zip"])
    sharedgrade_inputs = (
        app_native_output, native_output, app_junit, junit,
        ROOT / "ni08-native-fixtures/mf-bundle.zip",
        ROOT / "ni08-native-fixtures/eval-bundle.zip",
        manifest, capture_root / "environment.json",
    )
    before_sharedgrade = _artifact_snapshot(sharedgrade_inputs)
    def exact_cases(capture: dict, selections: tuple[str, ...]) -> bool:
        cases = capture.get("summary", {}).get("cases", [])
        expected_names = [node.rsplit("::", 1)[1] for node in selections]
        actual_names = [case["name"] for case in cases]
        counts = capture.get("summary", {}).get("counts", {})
        return (len(cases) == len(selections) and sorted(actual_names) == sorted(expected_names)
                and counts == {"passed": len(selections), "failure": 0, "error": 0,
                               "skipped": 0, "collected": len(selections),
                               "executed": len(selections)})

    app_exact = exact_cases(app_record, APP_NODEIDS)
    root_exact = exact_cases(record, NODEIDS)
    validation = {"schema": "epyc.ni08.hosted_validation/v1",
                  "app_receipt_sha256": app_record["receipt_sha256"],
                  "app_fixture_execution_conformant": app_record["fixture_execution_conformant"],
                  "app_exact_selected_cases": app_exact,
                  "app_case_count": len(app_record.get("summary", {}).get("cases", [])),
                  "root_receipt_sha256": record["receipt_sha256"],
                  "root_fixture_execution_conformant": record["fixture_execution_conformant"],
                  "root_exact_selected_cases": root_exact,
                  "root_case_count": len(record.get("summary", {}).get("cases", []))}
    captures_ok = (app_record["fixture_execution_conformant"] is True and app_exact
                   and record["fixture_execution_conformant"] is True and root_exact)
    grades = {}
    if captures_ok:
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT / "scripts/vidya"))
        from adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        for label, output in (("app", app_native_output), ("root", native_output)):
            native = native_rows(output / "receipt.json")
            if len(native) != 1:
                raise RuntimeError(f"{label} native receipt did not yield exactly one tuple")
            q, t, _reasons = grade(project_ci_conformance(native[0]))
            grades[label] = {"Q": q, "T": t}
            if (q, t) != ("Judged", "Located"):
                raise RuntimeError(f"{label} fixture receipt grade differs from existing ceiling")
    after_sharedgrade = _artifact_snapshot(sharedgrade_inputs)
    validation["shared_verifier_grades"] = grades
    validation["original_artifact_hashes_before_sharedgrade"] = before_sharedgrade
    validation["original_artifact_hashes_after_sharedgrade"] = after_sharedgrade
    validation["sharedgrade_inputs_unchanged"] = before_sharedgrade == after_sharedgrade
    if not validation["sharedgrade_inputs_unchanged"]:
        raise RuntimeError("shared grader changed an original native receipt, JUnit, bundle, or context")
    _write_once(capture_root / "validation.json",
                (json.dumps(validation, sort_keys=True, separators=(",", ":")) + "\n").encode())
    if not captures_ok:
        raise SystemExit("native fixture capture is nonconformant; original artifacts retained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
