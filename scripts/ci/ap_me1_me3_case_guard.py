"""Pytest collection guard for the exact AP-ME1/3 synthetic controls.

This is a hosted-runner plugin, not a test or a project import. It ensures that
pytest actually collects all 31 reviewed new controls and each named compatibility
suite before native_conformance records the JUnit result.
"""
from __future__ import annotations

from pathlib import Path

EXPECTED_SINGLE = {
    "test_default_off_no_capture_or_history_io",
    "test_complete_unicode_metadata_no_raw_prompt_and_unknown_pins",
    "test_append_failure_reports_error_without_private_text",
    "test_dispatch_pins_require_matching_native_trial",
    "test_busy_author_capture_lock_is_typed_and_fake_author_still_runs",
    "test_native_anchor_deltas_jsonl_roundtrip_and_separate_bsv_policy",
    "test_suite_quality_proxy_pair_renders_proxy_label",
    "test_writer_and_reader_keep_question_and_proxy_anchor_classes_separate",
    "test_native_writer_unknown_scope_failed_verdict_and_disabled_no_mutation",
    "test_bsv_no_overlap_keeps_original_early_return",
    "test_real_crossover_context_caller_preserves_negative_evidence",
}
EXPECTED_PARAM = {
    "test_real_prompt_boundary_unchanged_and_capture_failure_cannot_mask_author": {
        "prompt", "code",
    },
    "test_pair_unknown_or_ineligible_never_reconstructs": {
        "scope", "anchor", "legacy", "corrupt", "excluded", "regression", "version",
        "scope_version_bool", "anchor_excluded", "bool_trial", "signature_bool_trial",
        "signature_shape", "stale_revision", "stale_era", "stale_infra",
        "stale_comparability", "missing_error_scope", "stale_error_scope_core",
    },
}
SELECTED_FILES = {
    "tests/unit/test_mutation_diagnostics.py",
    "tests/unit/test_failure_signatures.py",
    "tests/unit/test_behavior_signature.py",
    "tests/unit/test_bsv_observe.py",
}


def pytest_collection_finish(session):
    collected_files = set()
    actual_new = set()
    for item in session.items:
        path = Path(str(item.path)).as_posix()
        for selected in SELECTED_FILES:
            if path.endswith("/" + selected):
                collected_files.add(selected)
        if path.endswith("/tests/unit/test_mutation_diagnostics.py"):
            function = getattr(item, "originalname", item.name)
            callspec = getattr(item, "callspec", None)
            parameter = callspec.id if callspec is not None else None
            actual_new.add((function, parameter))

    expected_new = {(name, None) for name in EXPECTED_SINGLE}
    for name, parameter_ids in EXPECTED_PARAM.items():
        expected_new.update((name, parameter_id) for parameter_id in parameter_ids)
    problems = []
    if collected_files != SELECTED_FILES:
        problems.append(
            "selected compatibility-suite collection mismatch: "
            f"expected={sorted(SELECTED_FILES)} actual={sorted(collected_files)}"
        )
    if actual_new != expected_new:
        problems.append(
            "AP-ME1/3 control collection mismatch: "
            f"expected={sorted(expected_new)} actual={sorted(actual_new)}"
        )
    if problems:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            for problem in problems:
                reporter.write_line("AP-ME1/3 COLLECTION GUARD: " + problem, red=True)
        session.exitstatus = 1
