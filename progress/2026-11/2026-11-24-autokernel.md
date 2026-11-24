# 2026-11-24 autokernel: overnight push, 20:00Z 11-23 to 07:20Z 11-24 (operator-invoked /wrap-up)

Hashes are from `git log origin/main --after='2026-11-23 19:30'` on root and research unless marked
(orch = epyc-orchestrator, llama = fork branch in `/mnt/raid0/llm/llama.cpp`).

## C20 gates, and the move to C21

| Gate | Result | Where |
|---|---|---|
| QDEC CPU | PASS | `678eb9788` |
| A3B GPU served | PASS: np4-mtp 1.114 vs C18 with H15 on (+11.4 %), np1-mtp 1.009 | `3c191fde8` |
| CPU decode r4 | PASS (owner-adjusted by a pre-data note, triple 0 excluded because a co-granted calibration row contaminated its C18 arm): geomean 0.997 [0.985, 1.009], triples 1-7 | `8a710619b` |
| 27B GPU | speed +7 % (geomean 1.0716), KLD 0, but identity FAIL (spec-vs-nospec 339 < C18 365) | `1fa91bc61` |
| Margin capture | REAL_DEFECT by the pre-registered rule, but C20 and C18 diverge at equal rates (7/8 vs 7/8, p 0.77) | `b0d27a7e1` |

What the margin capture showed: the fixed 0.19 / 0.38 nat identity bands are miscalibrated, because C18 exceeds
them against itself. A band has to come from the reference build, measured in the same row. Lesson recorded as
the memory `feedback_derive_identity_bands_in_row`.

C21 (`98ff8a42a` = C20 + fused tree GDN + V2 RRS + DTREE-B auto controller) is the promotion candidate
(`505fe66bb`); C20 is superseded. Manifest V11-145 is on main (`f92258fe8`). C21 gates published:
`c21-fold-gpu`, `c21-fold-a3b-gpu`, `c21-fold-cpu`, `c21-fold-qdec-cpu` (all -20261124) and
`c21-gpu27b-identity-r2-20261124`, which uses one server per store x mode x path group (8 servers instead of
128, about 68 min).

## Tree drafting (27B sampled)

- V2 + GDN deciding row `cb412ba1f`: T1.0 GAIN (T10 +6.1 %, T12 +7.2 %, T16 +8.8 %); T0.3 NULL.
- The earlier sampled row was invalid (wrong verifier commit).
- DTREE-GDN-BATCH stays unticked until the C21 fold lands; the untick is `d172d9eed`.
- Confirmation row `ak-c21-tree-official-gpu-20261124` runs at official sampling.

## Official sampling

- Audit: no served role ran at vendor sampling. Registry temperatures were 0.0 to 0.3, and the backend hardcoded
  top_k 40, repetition 1.1, min_p 0.05.
- Package RATIFY-OFFICIAL-SAMPLING-20261124 (`a289fdb3c`) was signed and applied: research `fb4dca72e`, orch
  `00ef9f47` + `28aee6e9`. The shared orchestrator clone was fast-forwarded with operator approval; API reloaded 07:02Z.
- Canonical recipes use official sampling: research `a97e27f15`.
- Serving proof is blocked on one external event: the stack is down by operator choice. The offline check passed
  for every role except vision_escalation; a follow-up package is in preparation. Box AK-OFFSAMP-GARBAGE
  (`92d302e9c`) holds the garbage-check rows.

## Closed or dropped

| Item | Verdict | Where |
|---|---|---|
| A3B expert dedup (MMID dedup) | DROP | `629012dad` |
| AK-MMQ-SK2 | CLOSE (no KEEP_CANDIDATE; arm A within +-0.0033, arm B slower). Box stays open: the step-2 shape census is not filed | `629012dad` |
| GDN gate-fold | futility (saves -0.867 ms vs floor 0.6). Box stays open: done-when names a 27B e2e verdict that the pre-registered futility rule skipped | `629012dad` |
| POSINV test | FAIL on q4_K and f32 (ROCm, DET=1); box stays open | `629012dad`, `92437f2da` |
| Draft sharpen (27B DFlash2) | CLOSE, holdout V*/V0 1.000 at T0.3, 1.007 at T1.0 | `847801385` |
| CAFE-3 | DROP at THROUGHPUT_NONE; static p-min 0.75 stays | `a23399eb3`, `6ed573182` |
| gvfattn split sweep | below the 1.5x bar (S26 1.172x at kv32768) | `3124ca5b9` |
| gvfattn LDS cut | below bar (1.21x at kv32768 nb8 q8_0, 1.62x at kv8192) | `4b53d92c6` |
| Router chunk | KEEP, folded into C20 (np4 MMVF_CHUNK=8 B/A 1.0817) | `497f13679` |
| SPEC-STALE-1 | cache fix works (39/39 vs 21/39 stale); text check REAL under the miscalibrated bands | `893b08734` |

The 1.5x gvfattn bar had no derivation, so AUTO_TUNE was built (llama `069c343f9`) and the served row
`ak-gvfattn-served-gpu-20261124` was published.

## Tooling

- Provisional-estimate lint fix `24a5fb417`; claim default and lint gaps `667b0529f`; `start_new_session` removal
  `7edd5d77b` (job servers stay in the job's session; `kill_tree` reaps by pid).
- A lint/template agent deployed SMOKE-NO-MEASURE and SELFTEST-MISSING as FAIL, plus server reuse by default
  (`cba16d6dd`; SMOKE-NO-MEASURE later back to warn-only in `f9d96affb`, and `3a8c1a743` accepts
  `smoke/smoke_measure.json`).
- pipeline-mgmt keeper fixes: quiet-serial (`5bd499aec`), B8 revert (`4814a9b70`), declared-threads width fix (`748318efb`).

## Process lessons (memories)

- No blocking question overnight: updated `feedback_no_blocking_question_unattended`.
- Publish with the deployed `publish_row.py`: existing `feedback_publish_with_deployed_rowflow`.
- New: `feedback_server_reuse_default_few_fresh_servers`, `feedback_never_run_job_without_selftest_handler`
  (origin: an accidental unclaimed C20 r3 run at 23:29Z), `feedback_derive_identity_bands_in_row`.

## Checkbox sync

No new tick. Every candidate failed its own done-when: MMQ-SK2 (census unfiled), GDN-GATE-FOLD (no 27B e2e verdict),
GGML-DET-POSINV-TEST (not green on ROCm), CAFE-3 parent (P9 not passed), DTREE-GDN-BATCH (waits for the C21 fold),
SPEC-STALE-1 and AK-GVFATTN-LONGCTX (open work remains). Already ticked by their agents: AK-A3B-VERIFY-DEDUP,
AK-A3B-VERIFY-CHUNK-SERVED, SPEC-DRAFT-SHARPEN, CAFE-3-CTRL-CPU.

Next: autokernel. Verify the C21 gate rows and the official-sampling confirmation row when the stack is back up.

---

# Second wrap-up, 07:20Z to evening (operator-invoked /wrap-up)

Hashes are root or research `origin/main` unless marked (llama = fork branch in `/mnt/raid0/llm/llama.cpp`).

## C21 gates (filed this wrap-up through `file_result.py`)

| Row | Verdict | Numbers |
|---|---|---|
| `c21-fold-cpu-20261124-r4` | PASS | geomean 1.011 [0.995, 1.028], 8 pairs, 3 concurrent membind streams; quality reused from r2 (27B KLD 0, Q38FN KLD 0, CH-33 NO_DEFECT) |
| `c21-fold-gpu-20261124-r4` | FAIL as filed (CORRECTNESS REAL_DEFECT, Flash-Next hybrid cell), read as no regression | speed not run in r4; reused r2 speed is PASS: greedy np1 tok/s C21/C18 P2 1.132, P3 1.121, D1 1.016, geomean 1.089; 27B KLD -0.0, top-1 100 % |
| `c21-nospec-determinism-gpu-20261124` | FUTILITY_NO_REGRESSION | 6 reps per arm, P3 code28k: C21 A/A median first-divergence pos 120, C18 110; C18 forks as much as C21, nothing to bisect. Box `C21-NOSPEC-DETERMINISM` ticked |
| `c21-fold-gpu-27b-stepc-20261124-r3` | PASS | 27B at the registry :8083 argv: 0/36 hard forks (0/15 in A/A), both builds deterministic |
| `c21-gpu27b-identity-r3-20261124` | PASS | Q38FN hybrid logits and fast paths; divergent units C21 18 vs C18 19 (Fisher p 0.794) |

Limit worth stating plainly: no served-config C21-vs-C18 speed number exists. Every speed visit is greedy np1.
`c21-fold-a3b-gpu-20261124` has not run (smoke only), so `C19-FOLD-GATES` (retitled to the C21 gates) stays open.

Operator rulings:

- No separate C21 promotion. All lever keeps go into one C22 consolidation, then a single fold gate, then the promotion
  package, then the reboot. The AK hold stays until after the reboot.
- Futility looks on every row. No training until roofline parity. No C22 advancement until every lever row is filed.
- Decisions: q8_0 KV for the 27B (q4_0 revisited after its row); the 27B gate stays at KLD <= 0.003; the anchor guard
  stays unconditional; the R18-D 27B re-run keeps the clock band (`7f464d857`).

## Lever rows

17 rows (`/mnt/raid0/llm/tmp/ak-lever-rows-20261124.txt`) built, published and queued, no verdicts yet: 27B tail fuse, A3B router
fuse, MMVF fixes, i8gemm SOL, 27B attn-KV concat, 27B actquant fuse, stochastic-accept gap, MMID N10 and UB ceiling, gvfattn
served r4, SPEC-STALE-1 DF2 np2 bands, DF2 np4 parity reuse, Q38FN draft window (CPU), fold KLD floor, DF2 point mass,
SPEC-BSAMP, GDN pscale ROCm tests. Fork branches (llama): `llama.cpp-experimental-c22-*` (mmvf-fixes, qkv-concat, mmq-h3,
mmids, actquant-fuse, cpu-levers, df2pm-bsamp, draftwin, stoch-accept), `...-27b-tail-fuse-20261124`,
`...-a3b-router-fuse-20261124`, `ak/cpu-nt-weight-stream-20261124` (`325ca8e8e`).

## Row-robustness RCA

`/mnt/raid0/llm/tmp/ak-row-robustness-rca-20261124/RCA.md`: 20 of 22 rows were hand-copied `job.py`, and nothing bound a row's
server argv to the served registry (stepc took three publishes to reach the :8083 recipe). F1/F2 landed as `a89b7a151`
(`mk_ak_row` v2: one generator, harness helpers, registry-derived argv) under the operator's D9 ack. Pipeline-mgmt keeper
fixes live at `04d7dff44`; the reservation queue (EASY backfill) ships in shadow at `49f6a9f17` / `eb643ac37`.

## Intake and loop

- intake-ak-1124 Stage 4 `801631795`: 27 boxes, 40 entries intake-2867..2906. Census parity references are sourced
  (`266658d9f`, `56b522bcd`); seeds 20 to 26 are committed (`167862d26`, `0172069d6`, `5dc1f5817`) and NOT installed.
- Loop evaluator (research): futility looks default on (`3b9903ca2`, `8ede9ee20`), NPLAN (`87d620544`), KEEPTIME
  (`9da82199c`), QUARTERS membind plus concurrent streams (`1dbdf2572`, `e86b805ae`, `94f8a4078`). Loop code budget raised,
  signed (`c5517782a`).
- Fold-gate STEP C replaces the first-divergence floor (`fe7847609`); census and bandwidth surfaces (`4694d7c35`,
  `928172ab7`); FOLD-CENSUS-1 merge-tree census (`4a65c11f5`).

## Process lessons (memories)

- Existing, confirmed present: `feedback_no_c22_fold_until_all_rows_filed`, `project_ak_hold_until_c22_and_reboot`,
  `feedback_publish_successor_before_stopping`, `feedback_no_training_until_kernels_at_roofline_parity`.
- New: `feedback_check_served_registry_argv_before_any_row`, `feedback_quiet_whole_host_row_blocked_by_any_load`.
  Updated: `feedback_watch_smoke_failures_not_just_ends` (re-arm the smoke-FAIL watcher after each batch; verify its list file is not empty).

## Checkbox sync (this wrap-up)

Result ticks: 1 (`C21-NOSPEC-DETERMINISM`, `[belief: cc]`, FUTILITY_NO_REGRESSION). Result notes without a tick under
`C19-FOLD-GATES` (retitled C21 gates): cpu-r4 PASS, gpu-r4, stepc-r3 PASS, identity-r3 PASS; the box's done-when (all gate
rows filed) is not met because the A3B row has not run. Already ticked earlier today by their owners and not touched:
`FOLD-GATE-SPEC-CORRECTNESS-V2`, `FOLD-CENSUS-1`, `C19-SPEC-STALE-1-FOLD`, `SPEC-DRAFT-SHARPEN`, `CAFE-3-CTRL-CPU`.
The 17 lever rows have no verdicts, so no lever box is ticked.

Next: autokernel. File each lever row as it ends (futility looks on), then C22 consolidation only after every lever row is filed.
