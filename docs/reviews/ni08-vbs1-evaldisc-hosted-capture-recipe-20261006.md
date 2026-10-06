# NI08 prospective report adapter hosted capture recipe

Status: **APP source proposal published; two failed capture attempts preserved; corrected ROOT/recipe source is in private review preparation**.
This is a bounded synthetic source-wiring control. It does not assert corpus behavior, evaluator quality, inference, performance, or adoption.

## Exact source proposals

The APP source is based on current published APP `81663c30177fb567b91df3ef9615060c8d018ab6`.
The prepared APP proposal tip is `cfcf3768716de888a971bf66489397f5b91241df`, published for review at
[branch `codex/ni08-analysis-writers-cfcf-source-20261006`](https://github.com/pestopoppa/epyc-orchestrator/tree/codex/ni08-analysis-writers-cfcf-source-20261006).
It remains unmerged. The APP producer and package source hashes are:

| APP tracked path | SHA-256 |
|---|---|
| `scripts/analysis/mf_vbs1_verify_before_stop.py` | `7463afeab66a20c274314e5f0a85472e271dc7e12e10f052b874039d4c0b44da` |
| `scripts/analysis/eval_suite_discriminability.py` | `6e3e8e688b74b857d7023e10361ca5c13334f8facbb69cae6a37c3df1648de35` |
| `src/llm_primitives/stat_tests.py` | `d0886ef1b32498475d804b9597347d2934b3dc0553224c0443a98654436af2dc` |
| `src/llm_primitives/__init__.py` | `cdee7bcf079e3023de6da551cd376e9e6db339d0ac52853eba054e3d3d6ccff9` |
| `uv.lock` | `7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3` |

ROOT is the isolated proposal branch `codex/ni08-vbs1-evaldisc-wire-root-20261006`. It is a normal
merge descendant of current source-owner ROOT `810fda4eee53401dcd923ec19ea1208e4020b888`, retaining
the accepted SC80 source, UFH13 reader and the current source-table/handoff registrations. The
proposal commits then add the capture source corrections. The exact final ROOT capture commit and
manifest digest are recorded in the capture's pre-dispatch source map; do not substitute the
ignored ledger or other workspace state.

The first hosted attempt (ROOT `e923ec553771b342b0c3836d7f865bfdd5b85dab`, run
`37544337444`) failed during the exact APP checkout because the pinned object had not yet been
published to the public remote. Setup stopped before Python setup or capture; its original status
artifact is retained at `/mnt/raid0/llm/tmp/ni08-vbs1-capture-37544337444` and has no native
result. The second attempt (ROOT `f759a23db280ed927b1f70a16187cfab6f7a1d04`, run
`37544676995`) reached the selected controls but is nonconformant and preserved unchanged at
`/mnt/raid0/llm/tmp/ni08-vbs1-capture-37544676995`. ROOT reported 29/38 passed and 9 failures;
APP collection stopped with exit 4 and no summary. The original 97-member artifact is retained,
including the JUnit files and failed receipts. The APP failure exposed an incomplete copied source
closure and missing locked imports; ROOT failures exposed two `NameError`s. The driver also raised
an `AttributeError` while validating the APP's null summary. None of these artifacts is a passing
capture or a shared-grade acceptance.

The synthetic round-trip fixture statically follows module-time imports from both APP writers and
`src.llm_primitives.stat_tests`, including imports in module-level conditionals, package
initializers, and compatibility shims. The first hosted attempt exposed that the APP
`src/model_server.py` shim redirects to `src.inference.model_server`; that package and its
`src/registry_loader.py` shim's target module were missing from the synthetic copy. The corrected
fixture includes those four real files and their recursively checked local imports, for a
44-file producer import closure, with each byte SHA-pinned to APP
`cfcf3768716de888a971bf66489397f5b91241df`.
It copies the actual package initializer and `src.llm_primitives.config` dependencies; it does not
substitute fake package files. The APP writer receives only synthetic in-memory rows and synthetic
JSONL input bytes. It does not open the BEP corpus, a real question ledger, traces, or an evaluation
run. The selected APP tests and producers have a 62-file module-time local-source closure; it is
explicitly included in the APP carrier readset, alongside the lock and deliberately excluded
conftest. Third-party roots are `httpx`, `pydantic`, `pydantic-settings`, PyYAML and the stat-test
module's `scikit-learn`; the hosted requirements pin these roots and their applicable APP-lock
transitive dependencies.

The exact current ROOT and APP file identities are carried by the generated Git-object source-context manifest and the explicit readset in `scripts/ci/ni08_run_hosted_capture.py`; this recipe does not duplicate a pin table that could drift from the commit being captured. The final pre-dispatch map records each read path, Git blob, byte count and SHA-256.

## Minimal locked runner environment

Use CPython `3.13.15`, Linux x86_64, and install only the requirements in
`scripts/ci/ni08-hosted-requirements.txt` with pip `--require-hashes`. The APP dependency lock is
bound to its exact `uv.lock` bytes above. The exact PyYAML wheel is
from APP `uv.lock`: `PyYAML==6.0.3`, SHA-256
`0f29edc409a6392443abf94b9cf89ce99889a1dd5376d94316ae5145dfedd5d6`. The requirements file also
pins pytest `9.0.3`, the producer import roots (`httpx`, `pydantic`, `pydantic-settings`, PyYAML),
the selected stat-test import (`scikit-learn`), pytest's `colorama` dependency, and their minimal
Python-3.13 dependency closure to hashes in the same APP lock. The runner records and checks each
installed version. It is a hosted-fixture-only install set; the source environment remains the APP
lock above.

Before pytest, generate one source-context manifest outside both checkouts:

```bash
python3 scripts/ci/ni08_source_context.py \
  --repo root="$ROOT" --repo app="$APP" \
  --output "$CAPTURE/source-context.json"
```

The generator reads Git objects at each clean HEAD, not worktree data. It records only paths, blob
IDs, byte counts, and SHA-256 for tracked Python, Python stubs, shell, TOML/lock, YAML, INI, CFG, and named code
configuration JSON files. It excludes logs, generated reports, raw datasets, run directories and
other JSON data. The capture request binds the manifest itself as a read-path; its Git identities
bind every listed source/config blob. The explicit readset also binds the exact workflow bytes plus
source, test, fixture, grading and carrier files below.

## Bounded selected cases

Run these exact, non-wildcard ROOT pytest node IDs; write JUnit and command output only under a fresh
directory outside both checkouts:

```text
tests/vidya/test_analysis_producer_roundtrip.py::test_actual_mf_producer_snapshot_round_trips_through_root_adapter
tests/vidya/test_analysis_producer_roundtrip.py::test_actual_eval_producer_snapshot_round_trips_with_native_reps
tests/vidya/test_analysis_report_adapters.py::test_immutable_input_snapshot_is_required_and_rechecked
tests/vidya/test_analysis_report_adapters.py::test_report_bytes_and_retained_inputs_are_reverified_at_projection
tests/vidya/test_analysis_report_adapters.py::test_mf_cached_metric_key_must_match_native_selection
tests/vidya/test_analysis_report_adapters.py::test_identity_free_legacy_report_is_refused
tests/vidya/test_analysis_report_adapters.py::test_unknown_native_fields_are_refused
tests/vidya/test_analysis_report_adapters.py::test_category_must_be_producer_authored_diagnostic_baseline
tests/vidya/test_analysis_report_adapters.py::test_producer_source_changes_preserve_snapshot_bound_historical_rows
tests/vidya/test_analysis_report_adapters.py::test_snapshot_path_escape_is_refused
tests/vidya/test_analysis_report_adapters.py::test_external_input_original_locator_is_metadata_only
tests/vidya/test_analysis_report_adapters.py::test_zero_denominator_rate_is_omitted_while_defined_rates_remain
tests/vidya/test_analysis_report_adapters.py::test_unbound_mf_scope_fields_cannot_be_supplied_by_report_envelope
tests/vidya/test_analysis_report_adapters.py::test_eval_metric_reps_use_each_native_denominator
tests/vidya/test_analysis_report_adapters.py::test_eval_cached_suite_and_metric_must_match_bound_report
tests/vidya/test_analysis_report_adapters.py::test_cli_dispatch_uses_shared_grade_only
tests/vidya/test_citation_gate.py::test_precise_in_range_but_uningested_claim_stays_unknown
tests/vidya/test_citation_gate.py::test_precise_out_of_range_claim_is_blocking_dangling
tests/vidya/test_citation_gate.py::test_out_of_range_claim_is_dangling_even_if_ledger_has_forged_matching_id
tests/vidya/test_citation_gate.py::test_zero_claim_entry_marks_precise_zero_dangling
tests/vidya/test_citation_gate.py::test_malformed_key_claims_count_preserves_unknown
tests/vidya/test_citation_gate.py::test_key_claim_count_reader_preserves_malformed_and_duplicate_as_unknown
tests/vidya/test_citation_gate.py::test_duplicate_yaml_key_in_entry_is_unknown_not_last_value
tests/vidya/test_citation_gate.py::test_unhashable_yaml_mapping_key_preserves_unknown_counts
tests/vidya/test_citation_gate.py::test_cite_check_cli_keeps_in_range_uningested_unknown_nonblocking
tests/vidya/test_citation_gate.py::test_cite_check_cli_blocks_out_of_range_claim
tests/vidya/test_claim_tuple.py::test_category_must_be_one_of_autokernels_three
tests/vidya/test_claim_tuple.py::test_each_source_class_has_exactly_one_ladder
tests/vidya/test_ingest_sources.py::test_every_source_is_a_cli_choice_and_the_literal_list_does_not_drift
tests/vidya/test_ingest_sources.py::test_every_dispatched_adapter_declares_its_authority
```

The two actual-writer tests call APP `load_trajectories` / `summarize` / `_seal_report` and
`load_rows` / `build_report` / `_seal_report`, then ROOT `native_rows`, projection, CLI ingestion,
and `claim_tuple.grade()`. They assert resulting ledger support grades equal the one shared grader.
The other ROOT cases cover retained input/source snapshots, path escape, cached-native binding, external
input locators, native denominators, report category/schema, citation bounds including a forged
matching ledger ID, and CLI `unknown` exit 0 versus `dangling` exit 3. Expected collected identities
are the expanded `(classname, name)` pairs in `scripts/ci/ni08-hosted-expected-cases.json`: 38 ROOT
cases from the 31 selected node IDs, including both cases for each of seven parameterized functions.
Require an exact pair multiset and exactly 38 collected, executed, and passed, with zero skips,
failures, or errors. The selected APP IDs expand to 20 cases and use the same exact-pair check. The
case-identity JSON is an explicit native readset input; parameterized ROOT controls have stable
pytest `ids=` values while assertions and fixture behavior remain unchanged.

Run this exact APP test selection separately from the APP checkout to cover the actual writer and
its existing controls:

```text
tests/test_analysis_report_provenance.py::test_mf_vbs_manifest_hashes_the_same_bytes_it_parsed
tests/test_analysis_report_provenance.py::test_eval_discriminability_manifest_hashes_the_same_bytes_it_parsed
tests/test_analysis_report_provenance.py::test_mf_vbs_edited_call_bearing_numerator_uses_intersection
tests/test_analysis_report_provenance.py::test_mf_vbs_zero_denominators_are_unknown_json_values
tests/test_analysis_report_snapshot_sealing.py::test_snapshots_are_private_and_identical_paths_deduplicate[_seal_eval]
tests/test_analysis_report_snapshot_sealing.py::test_snapshots_are_private_and_identical_paths_deduplicate[_seal_mf]
tests/test_analysis_report_snapshot_sealing.py::test_conflicting_duplicate_input_path_refuses_without_overwriting[_seal_eval]
tests/test_analysis_report_snapshot_sealing.py::test_conflicting_duplicate_input_path_refuses_without_overwriting[_seal_mf]
tests/test_analysis_report_snapshot_sealing.py::test_existing_snapshot_mismatch_refuses_instead_of_replacing[_seal_eval]
tests/test_analysis_report_snapshot_sealing.py::test_existing_snapshot_mismatch_refuses_instead_of_replacing[_seal_mf]
tests/test_analysis_report_snapshot_sealing.py::test_symlinked_snapshot_root_is_refused_without_chmod_target[_seal_eval]
tests/test_analysis_report_snapshot_sealing.py::test_symlinked_snapshot_root_is_refused_without_chmod_target[_seal_mf]
tests/test_eval_suite_discriminability.py::test_error_rows_excluded_from_brittleness_flip
tests/test_eval_suite_discriminability.py::test_error_dominated_run_excluded_from_run_spread
tests/test_eval_suite_discriminability.py::test_error_dominated_gate_is_configurable
tests/test_eval_suite_discriminability.py::test_brittleness_unmeasured_single_run
tests/test_eval_suite_discriminability.py::test_cli_main_writes_report
tests/unit/test_stat_tests.py::test_wilson_degenerate_denominator
tests/unit/test_stat_tests.py::test_wilson_published_values
tests/unit/test_stat_tests.py::test_calibration_metric_bundle_concrete_values
```

The APP selection binds the same-byte parse/write boundary, edit/execution intersection and strict
unknown denominators; it also exercises private snapshots, duplicate-path idempotence, conflicting
bytes, retained snapshot mismatch and symlink refusal for both producers. Error-row filtering,
one-run unknown stability and existing confidence-interval regressions remain covered. Require
exactly 20 APP cases collected, executed and passed, with zero skips, failures or errors. The APP
JUnit identity includes pytest's exact `_seal_eval` and `_seal_mf` parameter IDs. The APP invocation
uses `--noconftest`: source inspection shows these selected leaf tests need only pytest's built-in
`tmp_path` and local helpers, while APP `tests/conftest.py` eagerly imports API/backend state and
autouse fixtures unrelated to these pure producer/statistics controls. Its exact bytes are included
in the native readset to bind this deliberate exclusion. Plugin autoload remains disabled; the
selected tests need no conftest fixture, backend, model, or runtime path.

## Capture and grade boundary

The exact-branch workflow `.github/workflows/ni08-vbs1-evaldisc-native.yml` is triggered by a push
to its declared proposal branch without a path filter. This allows a workflow-only successor commit
to produce the capture event; the job body, APP pin, runner, selected tests, readset and artifact
retention are unchanged. It checks out its own
commit and the pinned APP source, initializes a retained status artifact before setup, creates a
Python 3.13.15 virtual environment, and uploads the result directory even after a failed capture.
The driver installs the hashlocked minimal dependency file and records package versions/install-log
digest, writes the Git-object source-context manifest, and calls the existing ROOT
`scripts/ci/native_conformance.py` carrier once for APP tests and once for ROOT tests. Each carrier
receipt binds both clean Git SHAs, runner Python, exact selected identities, JUnit bytes, command
output, dependency/source-context manifest, explicit source/test/grade/carrier readset, and terminal
status. Before shared grading, the driver hashes the original APP and ROOT native directories, both
original JUnit files, both generated synthetic bundles, source-context manifest and locked
environment; it hashes the same paths again afterward. Any change invalidates validation. This
before/after manifest checks integrity and never rewrites or reseals original receipts. The driver sets
`EPYC_ORCHESTRATOR_SOURCE_ROOT="$APP"` and asks the carrier to attach exactly two generated-output
bundles: `ni08-native-fixtures/mf-bundle.zip` and `ni08-native-fixtures/eval-bundle.zip`. Each
contains the synthetic raw inputs, producer-authored report, report-adjacent input/source snapshots,
and a per-member hash manifest. The driver refuses an existing generated-output directory so these
outputs cannot overwrite a prior capture. It requires exactly one existing `ci_conformance`
projection per receipt, both graded `Judged/Located` through the same `claim_tuple.grade()` function.
No new grader or carrier is introduced.

The test itself verifies each measurement projection through `claim_tuple.grade()` and actual CLI
ingestion. The receipt, if conformant, can separately be checked through the existing
`scripts/vidya/adapters/ci_conformance.py` projection and shared verifier `claim_tuple.grade()`;
that is a bounded test-execution observation (`Judged/Located`), not a measurement finding.
Any native capture must retain its original JUnit, command log, execution request, readset members,
receipt and disposable ledger together. Do not publish raw generated synthetic fixtures as model,
corpus, evaluator-quality, or historical measurement evidence.

No test, package install, project import, pytest collection, carrier execution, workflow dispatch,
or host interaction was performed while preparing this recipe.
