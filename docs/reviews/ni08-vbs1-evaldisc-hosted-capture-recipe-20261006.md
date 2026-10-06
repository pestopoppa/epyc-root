# NI08 prospective report adapter hosted capture recipe

Status: **prepared for MAIN review; not dispatched**. This is a bounded synthetic source-wiring
control. It does not assert corpus behavior, evaluator quality, inference, performance, or adoption.

## Exact source proposals

The APP source is based on current published APP `81663c30177fb567b91df3ef9615060c8d018ab6`.
The prepared APP proposal tip is `cfcf3768716de888a971bf66489397f5b91241df`; its source/test
changes are private. The APP producer and package source hashes are:

| APP tracked path | SHA-256 |
|---|---|
| `scripts/analysis/mf_vbs1_verify_before_stop.py` | `7463afeab66a20c274314e5f0a85472e271dc7e12e10f052b874039d4c0b44da` |
| `scripts/analysis/eval_suite_discriminability.py` | `6e3e8e688b74b857d7023e10361ca5c13334f8facbb69cae6a37c3df1648de35` |
| `src/llm_primitives/stat_tests.py` | `d0886ef1b32498475d804b9597347d2934b3dc0553224c0443a98654436af2dc` |
| `src/llm_primitives/__init__.py` | `cdee7bcf079e3023de6da551cd376e9e6db339d0ac52853eba054e3d3d6ccff9` |
| `uv.lock` | `7eae6b0447832155673e18f0e9f849fd4a65e3eb5839bf85f4165b13a4b06ca3` |

ROOT is the isolated proposal branch `codex/ni08-vbs1-evaldisc-wire-root-20261006`; its current
reviewed source base is current published ROOT `621eed0927a1cae6bbcdfb73155ec91dff607153`,
including `b6279387f` and its checkpointed SC80 source changes. This isolated branch contains only
the source proposal and its capture recipe on top of that published source base. The exact final
ROOT capture commit and manifest digest are recorded in the capture's pre-dispatch source map; do
not substitute the ignored ledger or other workspace state.

The exact producer bytes above are loaded from an isolated temporary APP checkout by
`test_analysis_producer_roundtrip.py`. The test verifies those bytes before import. It now pins
`src/llm_primitives/__init__.py` too; that package file was previously copied without an equality
check. The APP writer receives only synthetic in-memory rows and synthetic JSONL input bytes. It
does not open the BEP corpus, a real question ledger, traces, or an evaluation run.

ROOT critical source/test/carrier pins at the recipe's current pre-recipe commit are:

| ROOT tracked path | SHA-256 |
|---|---|
| `scripts/ci/native_conformance.py` | `2b8c63121e1472d10849224911ee8f4035b7f758ce1aefca7c766e2de263aa0e` |
| `scripts/ci/ni08_source_context.py` | `d163ead4f47619c7ce4a18f99e3e0ff4216922918e9fa06ca6eaec042a03b7df` |
| `scripts/ci/ni08_run_hosted_capture.py` | `91ef11008b36297b4c3953a084e2d6c0f93607de243c1d064e466a7a382ddc24` |
| `.github/workflows/ni08-vbs1-evaldisc-native.yml` | `42ce7d77daf6bf6d404c5cf96be358157e073382f703a5859074b16e766712d2` |
| `scripts/ci/ni08-hosted-requirements.txt` | `90450957d13a67f2ff9f4e4a969b0ade0ec08ae556ad05540ca0887491b7bb58` |
| `scripts/vidya/adapters/ci_conformance.py` | `aceba149c1b3386e2edd0f8ce5b0bd6bb1d4489d0fe3b3275f8984050aeeb19c` |
| `scripts/vidya/adapters/_analysis_report_provenance.py` | `15014d0ded8685d79428b2d82a2f661a09eca2cef89548d5bbc2bd028baaa12e` |
| `scripts/vidya/adapters/verify_before_stop.py` | `31e54f1bd0531b3830338ced032ff6a62ac14ceb1c2ec2f9440d635e80960049` |
| `scripts/vidya/adapters/eval_suite_discriminability.py` | `8f8aa67c3ab87d263061b1f4d9e5266e15f5038695e61b56e314debfda76afd1` |
| `scripts/vidya/claim_tuple.py` | `058749d2a1ce3487672e85cc5a18fd352b6f17e741a47d7f48bb55be278f4bfe` |
| `scripts/vidya/ingest_sources.py` | `a0df31d8a4dd1189dab7e5c7dae70f247268b063217dcdbccd8fb1fae4cf6eaf` |
| `scripts/vidya/cli.py` | `b2aa0b86eea6dc10e943b781dea8b7323e24976b7b57cb02d3a6c528f9ba4a7a` |
| `scripts/vidya/citation_gate.py` | `14bcad1be3ea81496abe7f92403eeb0a99b5f4d26ee55fe9d633ece5a78bb8e0` |
| `scripts/vidya/wiki_dependents.py` | `023feb86f1bd8611ef405504fb9ff815578e0ceaf59376cc8281bdc745c208e2` |
| `scripts/vidya/canonical.py` | `cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434` |
| `scripts/vidya/lattice.py` | `a889442eecf1887f5d5a4a1193dc0d7760efb668cf31cda21e1d226ec8b24da2` |
| `scripts/vidya/fold.py` | `f22dfc750d55c6fbc01cc0b56847f5684417221af5b392e7da7a8d46b2ec2cab` |
| `scripts/vidya/gate.py` | `01a87a9927d4553e2008bdeed7a04728515ba49a885082cfbc7bcfcb2cd91b6b` |
| `scripts/vidya/frames.py` | `f47f148218ae99d54c51b322bf4f3b0632d4458e49572843f5ed4aa424d15749` |
| `scripts/vidya/ledger.py` | `552689d03bf14e11c5e0fee98ba3ab37c43f280751f098ed265cff843b337b09` |
| `tests/conftest.py` | `e600504b4edfec57fce0a4c1e2fd6d217e2726c6261d502bad30afc8dd17eb7a` |
| `tests/vidya/test_analysis_producer_roundtrip.py` | `15d2a863cc6f1bd343e55b48d5fdd11cf398ba1c0d1b9d985019fdb75eba4c09` |
| `tests/vidya/test_analysis_report_adapters.py` | `599940fd515469f3c1be2e064a81970956b8c8fb737bc0c34f1d77132dc901d2` |
| `tests/vidya/test_citation_gate.py` | `48c2326df76b93828f7ef5680589b8616e0e33c53d5fadf50b67e83ef3e8d439` |
| `tests/vidya/test_claim_tuple.py` | `93a01202da69951afd170d61f527abd7e21c52853d8f6c429ccf5265aa4b2a6b` |
| `tests/vidya/test_ingest_sources.py` | `b8ba17a255997189b8119468c730b9830ff1d059da77e92148206deabfbd90d1` |
| APP `tests/test_analysis_report_provenance.py` | `f9becce57813ff7bb04f8c74d46aec1e566f194be069f0343bbcff7324ece1be` |
| APP `tests/test_analysis_report_snapshot_sealing.py` | `7a89576ec674bf94c2764f5bc997784a4abce736e8f2609c27d4b621820e423c` |
| APP `tests/test_eval_suite_discriminability.py` | `9d2f4b78d1d288ea80a9f920c5d0764cad4b0060a56764dfd61e1b975ec5a591` |
| APP `tests/unit/test_stat_tests.py` | `a512050a8fe09694ec058acaab66657dc80adca57a5f826aade8aa1a7db81850` |

## Minimal locked runner environment

Use CPython `3.13.15`, Linux x86_64, and install only the requirements in
`scripts/ci/ni08-hosted-requirements.txt` with pip `--require-hashes`. The exact PyYAML wheel is
from APP `uv.lock`: `PyYAML==6.0.3`, SHA-256
`0f29edc409a6392443abf94b9cf89ce99889a1dd5376d94316ae5145dfedd5d6`. The requirements file also
pins pytest `9.0.3` and its Linux-independent runtime dependencies to hashes in the same APP lock.
It is a hosted-fixture-only install set; the source environment remains the APP lock above.

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
bind every listed source/config blob. The explicit readset also binds the exact source, test,
fixture, grading and carrier files below.

## Bounded selected cases

Run these exact, non-wildcard ROOT pytest node IDs; write JUnit and command output only under a fresh
directory outside both checkouts:

```text
tests/vidya/test_analysis_producer_roundtrip.py::test_actual_mf_producer_snapshot_round_trips_through_root_adapter
tests/vidya/test_analysis_producer_roundtrip.py::test_actual_eval_producer_snapshot_round_trips_with_native_reps
tests/vidya/test_analysis_report_adapters.py::test_immutable_input_snapshot_is_required_and_rechecked
tests/vidya/test_analysis_report_adapters.py::test_mf_cached_metric_key_must_match_native_selection
tests/vidya/test_analysis_report_adapters.py::test_snapshot_path_escape_is_refused
tests/vidya/test_analysis_report_adapters.py::test_external_input_original_locator_is_metadata_only
tests/vidya/test_analysis_report_adapters.py::test_zero_denominator_rate_is_omitted_while_defined_rates_remain
tests/vidya/test_analysis_report_adapters.py::test_eval_run_spread_with_one_eligible_run_is_omitted_even_if_cached_flag_is_false
tests/vidya/test_analysis_report_adapters.py::test_eval_metric_reps_use_each_native_denominator
tests/vidya/test_analysis_report_adapters.py::test_eval_cached_suite_and_metric_must_match_bound_report
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
are these 24 named node IDs; require exactly 24 collected, executed, and passed, with zero skips,
failures, or errors.

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

The exact-branch workflow `.github/workflows/ni08-vbs1-evaldisc-native.yml` checks out its own
commit and the pinned APP source, initializes a retained status artifact before setup, creates a
Python 3.13.15 virtual environment, and uploads the result directory even after a failed capture.
The driver installs the hashlocked minimal dependency file and records package versions/install-log
digest, writes the Git-object source-context manifest, and calls the existing ROOT
`scripts/ci/native_conformance.py` carrier once for APP tests and once for ROOT tests. Each carrier
receipt binds both clean Git SHAs, runner Python, exact selected identities, JUnit bytes, command
output, dependency/source-context manifest, explicit source/test/grade/carrier readset, and terminal
status. The driver sets
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
