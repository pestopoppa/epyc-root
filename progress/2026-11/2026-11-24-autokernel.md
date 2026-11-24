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
