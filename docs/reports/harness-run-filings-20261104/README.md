# Harness run filings — 2026-11-04

These filings apply the original row decision rules to run-phase evidence. Qualification smoke is excluded. The per-row directories preserve the original manifests, end receipts and native results with source digests in `EVIDENCE.json`. Analysis summaries are read-only projections; no historical measurement warrant was added.

## Quarter-native same-prefix probe — completed mechanism capture

`handoff-rte-pfx2-quarter-native-v3-20261102` completed at rc 0: five trials per arm, four native rows per trial, 60 request rows total. The prefix has 6,542 tokens, so the predeclared sibling hit threshold is 5,887.8 cached tokens. No sibling meets that threshold. Each hold-first-end trial has one sibling at 4,504 cached tokens (68.85% of the prefix); the other siblings miss. Uncached tokens are lower for hold-first-end in this fixed probe, without establishing a semantic-quality or feature-promotion result.

| Arm | Trials | Uncached tokens per trial | Sibling hits ≥90% | Client TTFT median (ms) | Client TTFT range (ms) |
|---|---:|---:|---:|---:|---:|
| simultaneous | 5 | 26208 | 0/15 | 56423.9 | 22731.0–89014.6 |
| hold_first_tok | 5 | 26208 | 0/15 | 32034.0 | 15513.1–47716.4 |
| hold_first_end | 5 | 21704 | 0/15 | 29734.0 | 9554.9–38034.0 |

TTFT rows are correlated within trials and timing is indicative: the host was shared with a GPU job. Lower uncached tokens and TTFT are better; higher cached-token counts are better. Native slot IDs cannot distinguish buffering from slot reuse without task IDs. All distributions and per-trial counts are in [the review](review-rte-20261104.json), with [original run header and result](rte/EVIDENCE.json). The original write-side sidecar has six records; its result/header hashes match and it used the original producer window. The original grant file is gone, so the booked envelope is not independently authenticated here and is not an elapsed-time claim. [Adapter evidence](rte-belief-verified.json).

## S4 Omega — partial/refused pilot filed at futility

`handoff-s4-omega-isolated-pilot-v2-20261102` returned rc 0 with the predeclared FUTILITY outcome. The denominator remains 16 pairs: 1 complete, 7 incomplete, 8 not run. Five incomplete baseline pairs hit no-progress/comment-only failure and two lacked a coder_escalation backend. All ten captured records have producer-reported owned-backend correlations and the process drain completed. Tool liveness is **NOT_MET**.

The one complete pair (`aime_2024-II-15`) failed scoring in both arms: baseline 3 turns / 8,405 native prompt tokens / 1,627 legacy generated tokens / 111.856 s; Omega 1 turn / 3,246 prompt tokens / 369 legacy generated tokens / 31.835 s. This single convenience-panel pair supports no efficacy, non-inferiority, deployment or placement conclusion. Native reported output counts are missing in all ten records and are not replaced by legacy counts. [Full count and reason projection](review-s4-b4a-20261104.json).

Seven original refused manifests and their native records were ingested through the enrolled S4 Omega adapter: 50 metric rows, 150 frames, no adapter refusals. This retains the native refused statuses. Source, suite, kernel, template and drain checks are recorded in [the ingestion receipt](s4-ingest-verified.json); model-edge identity relies on its prepublication receipt. The receipt's as-of midnight is a cutoff, not the approximately 07:15Z ingestion time. [Original manifests, records and source snapshots](s4/EVIDENCE.json).

## Private-copy migration — bounded rehearsal passed

`codex-ufh12-gs-private-v3-20261102` passed its bounded official rule, rc 0, `FULL_PRIVATE_APPLY_PARITY_PASS`: episodic rows 64,514 in and out; strategy rows 1,428 in and out; 16 production-client parity samples per store with minimum cosine 1.0 (threshold 0.99999); server reaped. This was a private-copy swap, with no production swap. Full G-S and REPL-EMB-2.11 remain open pending the approximately 500-query token-length/drift gate and remaining B1–B5/package gates. [Native evidence](gs/EVIDENCE.json), [scope review](review-gs-20261104.json).

## Shadow GitNexus receipts — failed attempt

`codex-ufh12-shadow-gnx-v1-20261102` ended rc 1. The admitted index succeeded at pinned `f58d0bf7668147b5aa142ade921b7b86ece35ec0`, but the first symbol context command failed because it omitted an explicit repository selector on a host with multiple indexed repositories. Its two partial source-scan records are not context or impact receipts. No impact-risk clearance or online-shadow completion follows. The successor must resolve the exact indexed repository and symbol identities, retain all four context/upstream-impact receipts, and stop/warn on HIGH or CRITICAL risk. [Native failure evidence](gnx/EVIDENCE.json).

## B4 cache window — incomplete, no baseline

`ufh14-b4a-window-8083-20261102` ended rc 75 with 140 dispatched calls and prefix-fingerprint coverage 1.0, below the required 200 calls. Only four calls report success; 136 are unsuccessful. The reported missed-prefill share 0.0252, hit-token share 0.9278, cold-large share 0.2923, six concurrent duplicates and zero eviction lines are descriptive and do not unblock B4a or justify a cache-RAM change. [Preserved calls and report](b4k/EVIDENCE.json). The failed generation outcomes need a diagnostic successor with explicit error and reasoning capture; workload changes must be declared before treating a new window as a baseline.

## Readied successors

`codex-ufh12-shadow-gnx-v2-20261104` is published with [smoke PASS](successors/gnx-PASS.json). The fix selects the exact indexed source path explicitly, checks symbol identities, separates qualification from official output, and records/stops on HIGH or CRITICAL impact. The row reuses the pinned index; smoke is a source-scan progress proof, not an impact verdict. Its [published manifest](successors/gnx-published.json) protects the shared source and successor packet until all rows with that scratch root are filed; the predecessor filing therefore does not permit early reclamation. REPL-EMB-2.3 remains open.

`ufh14-b4k-nothink-successor-20261104` is published with GPU smoke queued, as **diagnostic only**. It disables thinking, reduces generated output from 384 to 128 tokens, captures failure/reasoning details, and uses an independent pinned source worktree. Those workload changes prevent a B4a baseline or B4k completion claim until comparability is demonstrated. See [the successor scope](b4k-successor-result.json).

## Public custody layout

Public review summaries use the stable `rte/` and `s4/` archive locators rather than ephemeral nanosecond scratch directory names. These are derived summaries, not modified native records. The original RTE header is preserved byte-for-byte as `rte/RUN_HEADER.json.gz`; `EVIDENCE.json` carries both its native digest and compressed-file digest. Gzip round-trip equality was checked. Other native records, manifests and snapshots are unmodified. The commit scanner's long-digit findings were exclusively the clock-derived scratch directory IDs; no hook patterns or exemptions were changed.
