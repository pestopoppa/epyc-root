# S3-AKU-13: Goodharted-keep count at PROMOTE

Status: implementation contract only; no implementation, test execution, hardware result, promotion, or completion claim. Owner: research AutoKernel loop. Scope: S3-AKU-13 in `handoffs/active/autokernel-unified-surface-program.md`. Downstream: INF-75 AKX-P3b. This artifact changes no measurement policy or grading rule.

## Verified integration points

Read-only inspection on 2026-11-02 at research HEAD `99301fa149af86a6f9743d2b0405c9234ba39586`:

- `scripts/kernel_rnd/autokernel/loop/source_loo.py::execute_surface` validates retained original keep receipts, omits each keep from the full assembled tip, runs original correctness gates, then calls `serving.compare(full, omission)`. Its retained raw row carries original keep reference, keep ID, source/tree, target, comparison, floor and claim observations. Return values are content-addressed references, not promotion receipts.
- `surface_fold.py::ExperimentalKeepReceipt` retains `comparison` plus `comparison_digest`; `validate_original` binds retained patch/source ancestry. The comparison is not by itself proof of a keep-time **bench** effect: validate its native schema and provenance before using it. Existing `test_source_loo.py` even constructs a receipt with a deliberately nonmeasurement comparison fixture.
- `serial_run.py::_source_loo_result` reopens/checks row digests, target and assembled commit; `_record_completed_stage` stores results by validation subject; `_required_source_validation` derives required surfaces from enrolled production targets and retained keep authors. Existing shape checks are exact-key checks; adding summary fields requires explicit schema/validator migration.
- `run.py` around lines 5414–5489 plans promotion, writes `serving/bundle-<tip>.json`, archives the gate and then advances COR/resets the bundle. Source-LOO invocation is separately in the validate-source-LOO flow. These paths are not currently joined for this counter.
- `accumulate.py::Bundle.add_keep` stores mechanism IDs and the latest COR-vs-tip compounded bench measurement/reference. That latest reference is overwritten: it cannot reconstruct each original keep's marginal bench effect. Keep `accumulate.resolve` a pure planner; do not put artifact reads there.
- `serving.py::compare` computes `candidate_tok_s / anchor_tok_s - 1`; higher throughput is better. Here anchor is full bundle and candidate is omission. Existing `omission_disposition` uses nonregression/floor semantics; it is not the counter predicate.

## Proposed implementation contract

1. Persist the original bench decision effect when each keep is accepted. Bind it to the unique retained keep identity (keep ID, kept/parent commits, patch hash, original target), native comparison reference/digest, metric direction, unit, recipe/request identity and original measurement identities. Record native effect and units; show percent as `100 * effect` only for a native fractional effect. Never substitute the current compounded bundle estimate or an author-surface serving effect for the keep-time bench effect. If existing immutable evidence proves the original bench effect, join it by identity; otherwise mark unavailable with reason. Do not invent historical measurements or silently backfill a zero.
2. Add this original bench evidence beside every retained omission row, including invalid/inconclusive attempts. Preserve immutable raw comparison evidence and existing deletion authorization (`false`). A typed, versioned nested evidence block is preferable to enlarging reference-only structures without updating strict readers.
3. Before PROMOTE emission/COR mutation, obtain a validated matrix of every accumulated keep against the promoting serving surface and every required re-baselined surface, for this exact full bundle commit/tree and current COR epoch. Derive surface membership from authoritative roster/rebaseline receipts, not which results happen to be present. A rebaseline must be current and valid on its own harness; stale, failed or missing rebaseline does not prove coverage. Validate keep set equality, target/request/recipe identity, original comparison direction/unit, correctness gates, claim validity and content hashes. Duplicate or conflicting rows refuse; choose no favorable retry implicitly.
4. For each valid cell, `omission_at_least_as_fast = (omission_effect_fraction >= 0)` using the unrounded native serving throughput effect. Equality counts. Do not require decisiveness or a floor-sized gain; a positive subfloor effect still satisfies the stated predicate. Do not reinterpret an inconclusive row as neutral or false. Other future metrics must use their declared native direction; do not apply this formula to latency blindly.
5. Count **unique keeps**, with OR across included surfaces: `count = len({keep_id | any valid surface cell has omission_at_least_as_fast})`. Retain per-surface witnesses and each keep's original bench effect. The count is descriptive; it authorizes neither deletion, a new threshold, nor an automatic promotion veto based on its magnitude.
6. Emit one versioned summary in the promotion receipt and corresponding archive record **before** COR advances/bundle clears. Suggested fields: schema, bundle commit/tree, prior COR/epoch, expected keep IDs, surface identities, evidence references, per-keep rows (`keep_id`, `keep_time_bench`, surface witnesses, boolean), `goodharted_keep_count`, `coverage_complete`. Use an immutable referenced summary if necessary, but ensure both consumers expose count and reference. On missing/invalid coverage or missing keep-time evidence, retain a pending/refused diagnostic with count `null`; never emit an apparently complete zero or final PROMOTE. This proposed evidence-completeness behavior requires owner review; it does not establish a new numerical gate. Preserve completed raw attempts and make restart replay deterministic.

Illustrative complete summary fragment (synthetic values, not results):

```json
{
  "schema": "epyc.autokernel.goodharted_keeps.v1",
  "coverage_complete": true,
  "goodharted_keep_count": 2,
  "keeps": [
    {"keep_id": "A", "keep_time_bench_effect_fraction": 0.04,
     "omission_effect_by_surface": {"cpu": -0.02, "gpu": 0.001}, "goodharted": true},
    {"keep_id": "B", "keep_time_bench_effect_fraction": 0.02,
     "omission_effect_by_surface": {"cpu": 0.0, "gpu": 0.03}, "goodharted": true},
    {"keep_id": "C", "keep_time_bench_effect_fraction": 0.01,
     "omission_effect_by_surface": {"cpu": -0.001, "gpu": -0.02}, "goodharted": false}
  ]
}
```

The production record also needs all identity/evidence fields above; this fragment illustrates arithmetic only. A is counted despite a subfloor GPU gain, B once despite two nonnegative cells, C never. None of these examples establishes statistical significance.

## Acceptance tests for the code owner

Use fixture-only tests; mock native builds/launches as existing `test_source_loo.py` does. These tests are proposed, not run here.

| Placement | Required assertion |
|---|---|
| `test_source_loo.py` | Original per-keep bench effect/reference survives into each raw omission row and archive export; two keeps have distinct effects even when Bundle's latest compounded estimate differs. Invalid build/correctness/measurement rows preserve original evidence but never become valid positive cells. |
| Pure aggregation tests | Synthetic matrix above produces exactly 2; a keep positive on two surfaces counts once; exact zero counts; negative subfloor does not; positive subfloor counts even with `decisive=false`; empty/missing evidence never becomes zero. No use of rounded display percentages. |
| `test_serial_run.py` and schema tests | Required surface/keep cross-product is complete, includes promoting surface, and excludes unrelated stale historical surfaces. Reject changed digest, wrong commit/tree/epoch, target/recipe/request mismatch, duplicate/missing keep, conflicting retry, invalid numeric values (NaN/inf/bool), direction/unit mismatch, failed correctness and incomplete rebaseline. Exact-key reference readers retain their contract or migrate explicitly. |
| Promotion path integration test | Spy on record/archive/COR save/reset: complete evidence exposes the same count plus evidence reference in persisted gate and archive before mutation; pending/missing/tampered evidence retains diagnostic, leaves COR/bundle unchanged and cannot publish a PROMOTE headline. |
| Restart tests | Crash after retained matrix/summary but before COR change reopens the same digest and count without rerunning or counting a keep twice; stale summary after tip/roster/COR change refuses. Historical records without counter remain explicitly unknown. |
| Regression tests | Existing omission dispositions, nonregression floors, `deletion_authorized=false`, claim requirements, gate cadence and pure planner behavior remain unchanged. A nonzero complete count alone does not veto promotion. |

Suggested validation after implementation: run focused `test_source_loo.py`, `test_serial_run.py`, `test_accumulate.py` plus the existing tests covering the actual run.py promotion writer; then the owner's required committed-source suite. Report commands, source hashes and actual outcomes. No compute is needed to validate aggregation/record ordering. Live measurement remains a separately admitted owner operation.
