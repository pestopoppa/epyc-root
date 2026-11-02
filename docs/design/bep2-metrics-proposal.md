# BEP-2/J8 metrics implementation proposal

## Scope and current gap

This proposal targets `scripts/benchmark/bep_ab.py` in the orchestrator. The current driver emits a row only after a cell runs, returns early on API restart failure, records `_meta.prompt_tokens` only, and prints arm-level medians/proportions over whatever rows happen to exist. `_batch_edit_states` scrapes process log text since a byte offset; its counts have no per-attempt denominator or reliable row attribution. Those values cannot support the BEP-2 gate.

The implementation should preserve raw observations, make missingness explicit, and return `unevaluable` whenever coverage or required telemetry cannot support a gate. Do not backfill or estimate token usage from prompt characters, traces, turns, or model context.

## Row and matrix contract

At startup, reject `--reps < 1`, duplicate task IDs, and any task/solution ID mismatch before creating run artifacts. Freeze the planned cells as `(task_id, arm, repetition)` where repetition is the ABBA block-pair index, not the sequential block index. Persist the full plan and `expected_rows_per_arm` in `meta.json`.

Write exactly one JSONL result row for every planned cell, including failures. Add `repetition`, `attempt_status`, and nullable `error_type`; statuses should distinguish `completed`, `api_restart_failed`, `chat_failed`, and `verifier_failed` (with a stable category for other exceptions). If restarting an arm fails, write failure rows for every task in that block, then continue or terminate according to an explicit harness policy while preserving rows for all remaining planned cells as unavailable. Measurements on failed cells remain null; never convert missing outcomes into false quality or zero latency.

Add `_summarize_coverage(rows, planned_cells)` to detect missing and duplicate keys, expected and completed counts by arm, and exact `(task, repetition)` pair coverage. A matrix is complete only when every planned key appears exactly once and all compared cells have valid outcomes. Persist coverage in `summary.json`; any missing, duplicate, or invalid required cell makes the gate `unevaluable`.

## Paired metrics and decision rule

Replace the aggregate print-only block with `_summarize_metrics(rows, planned_cells)` and persist its output in machine-readable `summary.json`. Keep per-arm completed counts and quality proportions as descriptive context. The primary latency effect is computed within each valid matched `(task, repetition)` pair as `(off_latency - on_latency) / off_latency`; report the individual deltas, median paired delta, and valid-pair count. Exclude pairs with failed/missing latency or zero off latency, and make the gate unevaluable if required pair coverage is incomplete. Do not use the difference between arm medians as the paired estimate.

Quality effect is the paired difference in percentage points for the same matched cells (`100 * (on_pass - off_pass)`). Report the paired values, summary, and count. Any failed/missing verifier outcome is a coverage failure, not a quality fail. With the small deterministic task set, label results descriptive; do not invent confidence intervals or population claims.

The gate can be `proceed` only when the matrix is complete, the required latency and quality pairs are valid, and all required parse/apply telemetry is measurable; thresholds are median paired latency reduction >=15%, paired quality difference >= -1 percentage point, parse failure rate <=5%, and apply failure rate <=2%. Use `unevaluable` for incomplete coverage or missing required telemetry. For fully evaluable runs that do not pass, preserve the handoff's distinct harden/re-run and retire branches rather than collapsing them into one outcome; resolve overlapping boundary cases explicitly before a run. The decision rule remains the one in `handoffs/active/batched-edit-parallel-apply.md`.

## Token usage and missing-data semantics

In `_chat`, extract a structured `usage` object from documented response locations: `_meta` and standard response `usage`. Validate token values as nonnegative integers; distinguish absent/null from numeric zero and retain malformed-value diagnostics as unavailable, never coerce them to zero. Capture prompt, completion, and total token fields only when reported. Keep the existing `prompt_tokens` compatibility field only if it mirrors reported usage exactly.

For each token metric, report `reported_count`, `expected_count`, coverage fraction, and available per-arm/per-pair summaries. If a required protocol quantity (such as prefill/context/bundle cost) is not directly supplied, mark that metric unavailable and its gate `unevaluable`; do not substitute prompt token counts or estimate it from other data.

## Parse/apply telemetry

The benchmark must consume request-scoped events emitted where the batch-edit attempt is actually classified, ideally `helpers.py:_record_batch_edit_state` and the batch-edit runner. Each event needs a stable request/session identifier plus explicit `parse_status`, `apply_status`, and failure category. In the harness, collect only events attributable to the row's session; broad log slicing via `_batch_edit_states(log_mark)` is not decision-grade and should not feed rates.

Define `patch_attempts` as eligible batch-edit patch attempts. Emit per row `patch_attempts`, `parse_failures`, `apply_attempts`, and `apply_failures`; report both counts and rates. Parse failures are not apply attempts. Rates are null when the denominator is zero or unavailable. Missing event data is unavailable telemetry, never zero failures. If reliable request-scoped instrumentation is not available for J8, the parse/apply gates remain `unevaluable`. Stub output must identify `mode=stub` and must never claim inference or model parse/apply rates.

## Implementation seams and focused tests

1. In `main`, validate inputs and construct/persist planned cells before execution; make row emission exception-safe and ensure restart/API/chat/verifier failures retain their planned row.
2. Add pure helpers `_summarize_coverage`, `_paired_metric_summary` (or equivalent), `_extract_usage`, and `_summarize_metrics`; keep serialization separate from the calculation helpers.
3. Extend the row schema with repetition, status/error, structured usage, explicit parse/apply numerator-denominator fields, and retain raw trace/artifact references.
4. Add `tests/unit/test_bep_ab_metrics.py` (or extend `test_bep_canary.py`) for: complete/missing/duplicate/unpaired/incomplete-block coverage; paired latency and quality with an excluded failed pair and zero baseline; usage from `_meta` and `usage`, absent/null/zero/malformed/negative values with no fallback; parse/apply denominators, parse-failure exclusion, zero denominator null rates, and missing telemetry; restart/API/chat/verifier exception row persistence and JSONL schema; and stub mode unable to claim real inference or parse/apply rates.

No inference or measurements are introduced by this proposal. These are design and test seams only; implementation and test execution remain separate work.
