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
EXPECTED_APP_COMMIT = "cfcf3768716de888a971bf66489397f5b91241df"
NODEIDS = (
    "tests/vidya/test_analysis_producer_roundtrip.py::test_actual_mf_producer_snapshot_round_trips_through_root_adapter",
    "tests/vidya/test_analysis_producer_roundtrip.py::test_actual_eval_producer_snapshot_round_trips_with_native_reps",
    "tests/vidya/test_analysis_report_adapters.py::test_immutable_input_snapshot_is_required_and_rechecked",
    "tests/vidya/test_analysis_report_adapters.py::test_mf_cached_metric_key_must_match_native_selection",
    "tests/vidya/test_analysis_report_adapters.py::test_snapshot_path_escape_is_refused",
    "tests/vidya/test_analysis_report_adapters.py::test_external_input_original_locator_is_metadata_only",
    "tests/vidya/test_analysis_report_adapters.py::test_zero_denominator_rate_is_omitted_while_defined_rates_remain",
    "tests/vidya/test_analysis_report_adapters.py::test_eval_run_spread_with_one_eligible_run_is_omitted_even_if_cached_flag_is_false",
    "tests/vidya/test_analysis_report_adapters.py::test_eval_metric_reps_use_each_native_denominator",
    "tests/vidya/test_analysis_report_adapters.py::test_eval_cached_suite_and_metric_must_match_bound_report",
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

ROOT_READS = (
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

    junit = capture_root / "original-junit.xml"
    native_output = capture_root / "native"
    argv = [sys.executable, "-m", "pytest", "-q", f"--junitxml={junit}", *NODEIDS]
    reads = ([ROOT / name for name in ROOT_READS] + [app_root / name for name in APP_READS]
             + [manifest, install_log, capture_root / "environment.json"])
    os.environ["EPYC_ORCHESTRATOR_SOURCE_ROOT"] = str(app_root)
    os.environ["NI08_NATIVE_FIXTURE_CAPTURE_DIR"] = str(ROOT / "ni08-native-fixtures")
    carrier = _load_native_carrier()
    record = carrier.capture_fixture_execution(
        argv=argv, cwd=ROOT, junit=junit, output=native_output,
        repositories={"root": str(ROOT), "app": str(app_root)},
        read_paths=reads, selections=list(NODEIDS),
        generated_output_paths=["ni08-native-fixtures/mf-bundle.zip",
                                "ni08-native-fixtures/eval-bundle.zip"])
    cases = record.get("summary", {}).get("cases", [])
    expected_names = [node.rsplit("::", 1)[1] for node in NODEIDS]
    actual_names = [case["name"] for case in cases]
    counts = record.get("summary", {}).get("counts", {})
    exact_cases = (len(cases) == len(NODEIDS) and sorted(actual_names) == sorted(expected_names)
                   and counts == {"passed": len(NODEIDS), "failure": 0, "error": 0,
                                  "skipped": 0, "collected": len(NODEIDS),
                                  "executed": len(NODEIDS)})
    validation = {"schema": "epyc.ni08.hosted_validation/v1",
                  "receipt_sha256": record["receipt_sha256"],
                  "fixture_execution_conformant": record["fixture_execution_conformant"],
                  "exact_selected_cases": exact_cases, "case_count": len(cases)}
    if record["fixture_execution_conformant"] is True and exact_cases:
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT / "scripts/vidya"))
        from adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        native = native_rows(native_output / "receipt.json")
        if len(native) != 1:
            raise RuntimeError("conformant native receipt did not yield exactly one tuple")
        q, t, _reasons = grade(project_ci_conformance(native[0]))
        validation["shared_verifier_grade"] = {"Q": q, "T": t}
        if (q, t) != ("Judged", "Located"):
            raise RuntimeError("fixture receipt grade differs from existing verifier ceiling")
    _write_once(capture_root / "validation.json",
                (json.dumps(validation, sort_keys=True, separators=(",", ":")) + "\n").encode())
    if record["fixture_execution_conformant"] is not True or not exact_cases:
        raise SystemExit("native fixture capture is nonconformant; original artifacts retained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
