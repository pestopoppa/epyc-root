# Expected-Attention hybrid-27B eviction audit — 2026-11-20

**Verdict: one pre-fix qualification is VOID; six retained corrected record groups
have positive eviction counts; four legacy/deployment/admission record groups
have no recorded hybrid-27B count.** These are inventory groups, not independent
replications. [belief: cc]

The audit asks which earlier qwen35 / Qwen3.8-27B Expected-Attention (EA) claims
actually removed positions. Larger `n_evicted` means more removed positions; it
is an operation check, not a quality metric. Zero invalidates an EA compression
measurement. Missing counts are **not-recorded**, never inferred zero or positive.
The audit stops when the located retained results are classified; no model or
benchmark was run, and no historical run-level warrant was reconstructed.

## Inventory

| Record group | Classification | Count evidence |
|---|---|---|
| pre-fix-AM-PORT-2-qualification | void | reported n_evicted=0 |
| AM-PORT-2 | evicted>0 | 32 records; 23300–24940 evicted |
| AM-PORT-2-smoke | evicted>0 | 1 records; 2377–2377 evicted |
| AM-PORT-2-r2 | evicted>0 | 28 records; 23192–25993 evicted |
| AM-PORT-2-r2-smoke | evicted>0 | 1 records; 2377–2377 evicted |
| AM-PORT-2B-smoke | evicted>0 | 1 records; 2377–2377 evicted |
| AM-PORT-2B-ladder | evicted>0 | 32 records; 5825–6234 evicted |
| legacy-four-model-production-validation | not-recorded | no hybrid-27B counter |
| legacy-deployment-ledger | not-recorded | no hybrid-27B counter |
| KV-admission-and-fallback-summary | not-recorded | no hybrid-27B counter |
| S8-deployed-path-premise | not-recorded | no hybrid-27B counter |

The linked [machine-readable audit](ea-27b-evict-audit-20261120.json) gives each
source path and its SHA-256, with git blobs for root documents. Files remain in
their original repositories/scratch locations; only derived classifications and
counts are recorded here.

## Conclusions and corrections

- **Pre-fix GPU smoke: void.** Kernel commit
  `c9f2e34cea7a0e9ddac5ad7b2088bf06b56ee1db` records `n_evicted 0` in its
  contemporaneous diagnosis. Its `src/llama-kv-compress.cpp` blob is
  `8a01f9223a151b3bbe3b48b2de50ac8d6b52e1ba`. It fixes the hybrid layer/head
  geometry and partial RoPE interpretation. The original raw zero-eviction reply
  is not separately retained: the later smoke reused the output path. The
  committed reported zero suffices to void this exposure; it is not a newly
  recovered raw measurement. Earlier quality or memory-savings claims cannot
  be rescued from that no-op.
- **Corrected 5x result remains valid as an eviction experiment.** The first
  STOPPED run contributes 32 EA items; r2 contributes 28 distinct items. Their
  union covers all 60 item ids exactly once, all with positive eviction counts
  and aligned continuations; EA accuracy is 0/60. The repeated qualification
  records are not additional 32K items. This is evidence of poor quality under
  this recipe, not a no-op or evidence about faithful Attention Matching.
- **Corrected ratio ladder remains valid.** All 32 EA items at keep_ratio 0.8
  evict 5,825–6,234 positions, with 1/32 correct. The first and corrected r2
  filings share the same native data. The 5x point is reused, and EA 0.5/0.33
  arms did not run. `n_beta_set=0` is normal for EA and is distinct from zero
  evictions. No safe EA ratio was established; the existing fold/caller guard
  remains in force.
- **Legacy deployment and admission statements are not hybrid-27B evidence.**
  The April 8/8 aggregate does not bind a qwen35-27B count; its named PPL ratios
  belong to 1.7B and 35B. KV-admission/cache-credit success and removal of a
  compaction fallback likewise supply no hybrid-27B count. The owning
  long-context handoff now explicitly marks the deployed-path efficacy premise
  `[moved]`/unverified and the original zero-eviction qualification void.

## Search coverage and limits

Search terms were `expected[- _]attention`, `n_evicted`, `slot_compact`, and
`action=compact`. Discovery covered root handoff/domain decision records,
reports/design docs, historical progress, wiki pointers, retained root JSON
results, the research benchmark/results and compaction docs, orchestrator
reports/autopilot state, current ready manifests and filed verdicts, and retained
AM-PORT and KVU/C6 result/launcher locations. Filename-led searches excluded
source/build/external copies. This is an audit of located retained records;
it does not attest that unlogged historical calls never occurred. Such calls
remain not-recorded, rather than being promoted to measurements.

Relevant exclusions prevent false attribution:

- S1's research `ea_s1_results.json` is a dry-run scaffold on Qwen2.5-7B.
- S8-c API/recency results target Qwen3-1.7B, not hybrid 27B.
- Archived v6 F2/F3 records report 487/972 evictions but do not bind that count
  to qwen35-27B; retain their own test scope, not a 27B transfer claim.
- The research compaction guide describes key-norm selection plus constant beta
  (AM-lite), including a 32B memory table. It is not a measured 27B EA result.
- UFH14-A4/A4a post-compaction records concern textual summarization/prompt
  restoration and `cache_n`, not EA selection; their failed paired treatment
  supplies no EA n_evicted. Do not void unrelated cache-credit measurements.
- Admission and checkpoint eviction counters are not EA position-eviction
  counters. No earlier retained hybrid-27B EA admission-series counter was found.

Evidence is a committed-conclusion observation (`cc`) over existing records.
The audit neither invents a ClaimTuple for those runs nor creates a new
measurement producer. Existing AM-PORT-2/2B quality verdicts, native-window gates,
and production-kernel freeze are unchanged.
