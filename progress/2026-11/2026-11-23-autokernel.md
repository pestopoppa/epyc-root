# 2026-11-23 — autokernel (covers 2026-11-22 20:00Z → 2026-11-23 ~09:30Z)

Operator-invoked `/wrap-up`. Sources: handback ledger `/mnt/raid0/llm/tmp/autokernel-handback-ledger-20261120.md`
(entries through 23:4xZ on 11-22), root/research git logs, filed handoff boxes. Every verdict below is already
filed in its owning handoff; this is the roll-up.

## Kernel results

| Item | Verdict | Key number | Where |
|---|---|---|---|
| C10 / AK-H15 | RESOLVED | C12 lacks `fb1cd406f`; C17/C18 clean (reject 14 on every Q38FN layer, H15 never runs) | kernel-champion-and-promotion.md C19-AK-H15-* |
| Fused GDN r3 (`GGML_HIP_GDN_FUSED`, `e2b1f54f3`) | KEEP | T12 K=12 F32 1.55x, 8-row min 1.43x, K=T 830-915 GB/s | autokernel-loop.md GDN-FUSED-VARIANT-R3 |
| GDN column-width dispatch | KEEP | np1 F32 S_v128 1.16x, worst cell 0.97 | GDN-COLWIDTH-DISPATCH |
| GDN served gate (27B DF2, `70935a234`) | KEEP np1 + np2 | np1 t-CI [1.011,1.023] (+1.7%); np2 [1.039,1.052] (+4.6% CI-mid) | GDN-FUSED-SERVED-GATE(-NP2) |
| GPU device tree accept (`a33427896`) | KEEP | post T12/T16 0.43 ms; T16 at linear parity | speculative-decoding.md DTREE-DEVICE-TREE-ACCEPT |
| DTREE ROWCOST / HOST-GAP | ANSWERED | GDN largest per row (T8->16 +0.311 ms/row); host gap = post-phase logits copy | DTREE-ROWCOST-GDN, DTREE-HOST-GAP |
| CPU argmax tie | BUG, fix on fork | last-max on ties, 825/930 mismatches; fix first-max `a33427896` | C19-CPU-ARGMAX-TIE-FIX |
| IQ3_XXS QDEC on C18 CPU | DEFECT | C18 lacks `17d092de0`; C19 fold box | AKX-ALL-31.QDEC-C19-IQ3XXS-FOLD |
| Q8IP permute (`e1a591c4a`) | mechanism fix, speed NEUTRAL | 1.020 [0.994,1.046]; C19 default-off | AK-BW-27B-DRAFT-Q8IP-PERMUTE |
| BF16 drafter | hipBLAS 144 GB/s; MMVF cap 8 1.125x | still 0.824x Q8_0 REF; DF2-11 precisions all slower | DF2-11-* |
| G3 KV trace | done | q8_0 GQA_NATIVE in gv_fattn; q4_0 n7 full dequant | G3-KTRACE-* |
| AK-PM-12 | done | cap 3.356x vs measured 1.4982 TB/s peak | AK-PM-12-S4 |
| CPU quarter-24t ceiling | MEASURED 112.9 GB/s | replaces derived 129.9; census re-ranked (research 37d878a0b) | AK-CPU-CEIL-MEASURED (ticked here) |
| Q38FN d32k GEMV slowdown | CONTENTION artefact | quiet d32k 78-92 GB/s | AK-Q38FN-CPU-D32K-GEMV-SLOWDOWN |
| A3B shared expert (CPU) | LOSS_LOCALISED | `ffn_down_shexp` 2-row tiles at N=2/3; SMALLN NO_KEEP; Q0_RM4 r3/r4 contended, r5 prepared | AK-CPU-A3B-SHEXP-* |
| MMID gate+up fuse (Q38FN IQ3_S CPU) | withdrawn | -5.3% every pair, served divergence | AK-Q38FN-CPU-MMID-GATEUP-FUSE |
| Q4X replay re-allow | FAIL identity (np4) | phase C ON 31 vs OFF2 23; bisect box opened | Q4X-FIX-AA-R7, C18-REPLAY-Q4X-CONC-BISECT |
| C19 | assembled `a6a32c135` | gate rows prepared (27B GPU, A3B GPU, CPU, QDEC) | C19-FOLD-GATES |

Operator ratifications landed: P-KLD-1 (MEASUREMENT.md Annex V, `db1b26251`) and the consolidated loop
code-budget package (`8976ff721`).

## Process lessons
- Servers launched by a row die on every exit path (`trap ... EXIT`); an orphaned server blocked E5.
- Never re-seal or hand-edit a sealed row's `spec.json`; clone, regenerate SOURCE.sha256, republish with `supersedes`.
- Never chain worktree removal or branch deletion after a push; verify PUSH VERIFIED first.
- pgrep/pkill are banned; kill only captured PIDs.
- Gate small served effects on a paired t-CI, not the max-deviation band; key identity gates to the OFF modal hash.

## AutoKernel journal / planner ingest (operator ask)
Research `b4b451eec`: program.md *Learnings 2026-11-23*, 9 new `seeds/negatives.json` do-not-repeat records,
`seeds/hypotheses/23-ak-harvest-20261123.md` (DTREE-GDN-BATCH, ACTQUANT-FUSE, ATTN-KV-CONCAT, A3B router,
Q0_RM4, Q4X concurrent bisect). Offline canary (seed.install into a scratch store + program.md +
retired_mechanisms + archive.recall): all 21 sampled items present on at least one planner surface. Gap boxed:
AK-CENSUS-UPDATE-SHAPES (census_update.apply parses none of this session's RESULT shapes; owner Pipeline).
[belief: cc]

## pipeline-mgmt: AKU-17 and AKU-18 (loop-infra boxes, operator ruling 2026-11-23)

- AKU-17: research `3f49fb474`, `5b34a1c71`. `loop/cpu_fold_record.py` derives `accumulator-bundle.cpu.<recipe>.<hash8>.json` from kept experiment rows (effect, floor, floor unit, contention, statistic read from the row, none invented). The v11 manifest cites 20 kept rows across three campaign stores; all 20 resolve into 4 bundles (`data/aku17-cpu-bundles-20261123/`), every magnitude `provisional`, contention `unproven` (new label; never settles). Recipe name alone collided across two recipe hashes, so bundles are keyed name.hash8.
- AKU-18: research `1be8120bf` (contract `loop/accumulator_surfaces.py`, fail-closed fire decision mirroring `accumulate.gate_trigger`; estimate fires on cadence only), root `3ac61766c` (hub panel `accumulator_surfaces`, `/api/accumulator_surfaces` + `/health`, card inside `akflow-sec`). The record is published by CLI to `/mnt/raid0/llm/tmp/ak-accumulator-surfaces/`; both surfaces read `cannot_decide` because no calibrated serving floor was passed, which is the fail-closed answer, not a verdict. Hub verified on :8100.

## Evening wrap-up (operator-invoked /wrap-up, 2026-11-23)

The session's results were filed in handoffs by subagents. This wrap-up checked each one against origin/main `62dc7d5ea` and filled the two gaps it found.

| Area | Result | Where |
|---|---|---|
| C19 A3B GPU gate r2 | INCONCLUSIVE on A3B-mtp. np4 at 1.20 is diagnostic only (unserved, no spec). The mtp attribution is UNATTRIBUTED (~0.9 %, not GDN-fused). A later r3 attributed the loss to H15 (`5671b53b8`). | kernel-champion-and-promotion.md C19-FOLD-GATES (`8a97c7cf0`, `328e96218`) |
| C19 27B GPU gate r2 | FAIL in phase 0: heap corruption in test-dtree-device-accept on ROCm, 2 of 8 runs. The ASan diagnostic is pending. C19 is not promotable. Fork commits `37c3322d0` (K1 default 0), `bafa9cf28`, `ea14b3cd7`. | `30f8adc44` |
| C20 fold candidates | GGML_Q0_RM4: +9.5/+10.4 % at N=2/3, default-on candidate (`9cc0611d7`). GDNPROJ_FUSE: +0.87 % decode, default off (`148f56bbb`). SPEC-DISTS-TRUNC (`3cc4ab91b`): served A/B running. | kernel-champion-and-promotion.md |
| Spec decode | DICE replay: sampled trees gain +7-11 % acceptance, and DICE selection adds nothing. The sampled-tree v1 LOSS was invalid because no siblings were drafted (`78c415e19`). A3B is parked on verify cost. v2 (`8bbc8a26e`) is built and held for the 27B replay. CAFE-1-SERVED-T p-min 0.5 is a KEEP (+22/+28 % at one CPU quarter); the stack package was signed (`62dc7d5ea`). SPEC-COUPLE-MTP-1 is futile. The greedy re-tests (`da6e2f5ae`) leave most parks standing. | speculative-decoding.md, autokernel-loop.md |
| Identity/noise | SPEC-ID-NOISE-1 on CPU and GPU: a single request on the same server is deterministic, while batched and DFlash2 cross-launch runs diverge on near-ties, so judge identity by margin. Ragged rollback is clean on both devices. Position in the batch has no effect on CPU, and on GPU only with deterministic mode off; batch SIZE breaks invariance. Q4X R9 is FAIL_CORRECTNESS on a single event inside cross-server noise (`3bf33fa6c`); Q4X-REPLAY-VS-SNAPSHOT is queued (`665238796`). | speculative-decoding.md |
| Other | GDN gate-fold built (`0dd6e71de`), 13/13 correct, A/B queued (note added here). MMID-MF: futility. lineage_capture wired (`121ab3bba`). intake-ak-1123 Stage 4 applied plus rev1 and OD-1..5. AK-TEMP-AXIS audit handed to Pipeline. 9 dead modules deleted (`c87401f58`). LOOP-79 superseded by AKU (operator). Infra: run helper + lint (D9 acks `a6ac0a157`), quiet-host gate (QUIET-RESERVE, then QUIET-SERIAL one per socket), light claims, disk hardening. 28.5 GB reclaimed with operator approval. | — |

Gaps filled by this wrap-up: a note on the GDN gate-fold build under AK-BW-GDN-GATE-FOLD, and a note on the sampled-tree v2 build held under SPEC-DTREE-ACCEPT-GAP.

Lessons were recorded in research program.md (*Learnings 2026-11-23 evening*) and in memory:
1. Do not trust an offline replay's baseline until it reproduces the measured served acceptance.
2. A STOP ending is terminal; use `rowflow resume` when the row supports it.
3. Quiet rows must be mutually exclusive, because they contaminate each other (CAFE-1 r1 was contaminated by r9).
4. GPU speculative decoding is not reproducible across launches, so identity gates use margin classes.
5. Never quote a one-quarter CPU tok/s figure as a served number.

Next: autokernel. Run the C19 27B ASan diagnostic, file the SPEC-DISTS-TRUNC served A/B, and run the 27B DFlash2 replay before v2.

## Overnight push, 19:00-20:00Z (operator-invoked /wrap-up; E5 deferred to tomorrow by the operator)

| Item | Result | Where |
|---|---|---|
| SPEC-ID-GATE-1 | Ticked. Protocol doc `docs/guides/agent-workflows/spec-identity-gate-protocol.md`. | `ff2ac0710` |
| SPEC-PIT.1 | Gate module landed (research `608c7050a`, `ea27de554`). Server `pit_probs` flag on fork `21bd77019` (store `cpu-20261123-21bd77019-specpit`). Row t1p100 passed its smoke and is held; t1p095 and t4p095 are prepared for tomorrow. Cost note: MTP ON 7.0 versus OFF 10.2 tok/s at top_k 0. | `c346926f8` |
| 27B DICE replay | PROJECTED_LOSS: V1/V0 is 1.02-1.07 against break-evens 1.10/1.26/1.34. SPEC-DTREE-ACCEPT-GAP ticked. The 27B tree is parked on verify cost. | `affe2a601`, research `8f9ab7256`, `76df2d6fa` |
| A3B GPU p-min | DROP, -13 % / -9 %. | `6e0c2da7c` |
| A3B verify-cost analysis | `/mnt/raid0/llm/tmp/ak-a3b-verify-cost-20261123/ANALYSIS.md`. The router-chunk knob is on fork `b582006fe`/`09c67f530`; 3 GPU rows published. | pointer `89254c8b8`, boxes `1cebc0adc` |
| COPYSPEC-WIDTH | Already folded into C19. G3-longctx repaired and passed. | `741c4ac0d`, `861a83bb0` |
| DTREE-GDN-BATCH | Batching is not the lever. The fused-tree port is `a78cc156f`/`4db0106be`/`2d5afc217`; its row is republished. | `898968ef3` |
| Failure audit | `/mnt/raid0/llm/tmp/ak-failure-audit-20261123/REPORT.md`. AK half done; the pipeline half is in progress. | `0de4e80ed` |
| r10 Q4X replay gate | FAIL_CORRECTNESS, so the re-allow is excluded from C20. | `0679dbbf3` |
| DSpine served-T | DROP; research negatives filed. | `bcd7810d0`, `f4c50dbc2` |
| CAFE-3 | Controller on fork `ebc8e7ed2`; row published and smoke-passed. | box `21e00d77d` |
| gv_fattn | Occupancy analysis and box; split-sweep row `ak-gvfattn-splits-gpu-20261123`. | `c9165f7fb` |
| AK-MMQ-SK2 | Built; its row passed its smoke. | autokernel-loop.md |
| Build window 19:32Z | Quiet rows were STOPped because QUIET-RESERVE starved the build claims; the pipeline is adding a build priority lane. Lesson recorded in memory. | — |
| C20 | Assembly and gates in progress: fold-cpu inc/c19 fix, QDEC seal-rewrite cause. | kernel-champion-and-promotion.md |

Checkbox sync: SPEC-ID-GATE-1 and SPEC-DTREE-ACCEPT-GAP were already ticked by their agents; the boxes for SPEC-PIT.1, CAFE-3, AK-MMQ-SK2, DTREE-GDN-BATCH and AK-GVFATTN-LONGCTX stay open because their rows have not produced verdicts, so no new tick was written here.

Next: autokernel. Run the held SPEC-PIT t1p100/t1p095/t4p095 rows, then the C19 27B ASan diagnostic.

## 20:45Z — CAFE-3-CTRL-CPU r2 filed fail (DROP at THROUGHPUT_NONE)

Row ak-cafe3-cpu-20261123-r2 (rerun of ak-cafe3-cpu-20261123, rc=0 complete 20:41:37Z): 30 of 30 TIME visits ran (5 blocks x C/S/Sr x T0.3/1.0); 30 DIST visits not run (stop-on-futility). Quiet-guard clean (one unit, b3 T1.0 S, needed 3 tries; refs 50.0/53.5 < floor 81.8, cleared). Controller ON vs static p-min 0.75 aggregate tok/s: T0.3 23.63 vs 26.30 (-10.17%, A/A Sr -0.88%, floor 24.1%); T1.0 24.79 vs 22.31 (+11.12%, A/A Sr +10.36%, floor 65.6%). Gate (aggregate >= 1.0 + A/A floor at both T) not met at either T: DROP / THROUGHPUT_NONE. Filed fail (filed_by autokernel). The filing tool refused the box tick (done-when also names the original row id and gate() verdicts, which a DROP before DIST never produces); box left open. RESULT /mnt/raid0/llm/tmp/ak-cafe3-cpu-20261123-r2/out/RESULT.json. [no-belief: filing record; conclusion is in RESULT.json]
