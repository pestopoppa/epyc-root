# 2026-11-22 — autokernel (operator-invoked /wrap-up)

Source: handback ledger `/mnt/raid0/llm/tmp/autokernel-handback-ledger-20261120.md`, entries 2026-11-21 ~22:1xZ to 2026-11-22 23:4xZ. SHAs below were cross-checked against origin/main (root and research) where they are root or research commits; `74c18e2d8` / `1b83c6967` / `57a935901` are llama.cpp fork commits.

## Headline outcomes

| Track | Outcome | Evidence |
|---|---|---|
| DTREE (tree drafting) | **PARKED.** tree-on-V5I r4 FAIL_CORRECTNESS, T12/L 0.924, T16/L 0.963. Phase r2 shows the tree overhead sits in the target forward (T12 +6.0 ms, T16 +9.7 ms; draft/pre/post ~0). V5I matmul slope is 0.17 ms/row, so the remaining ~1.5 ms per extra row is GDN/FA/mask inside the forward. Reopen trigger refined in the handoff | root e69add193, df125f816, 81934b309 |
| GPU-RESIDENT-ROUND-2 | Slices 2a/2c/2d/2e/2f-kround all NO_WIN on speed and CPU (2f identity PASS). Acceptance "gains" in 2a/2d were a pooled-binomial CI harness artifact; the distribution gate is now trajectory-permutation chi-square | root e69add193 |
| C18 composite `74c18e2d8` | Folds split16 (A3B np4 ms/round 0.8318 [0.827,0.837], ~1.21x, clean preregistered r4), FAROWS-INPLACE (r3 1.0728 [1.0657,1.0799]), Q8_1 reuse (A3B-mtp +3.0%), RS-REPLAY auto. GPU 27B gate PASS (ppl_rel 4e-7) and CPU r2 PASS (bit-identical). **A3B gate pending.** Must not promote until the C10 fusion-loop bisect clears it | kernel-champion-and-promotion.md C18-FOLD-GATES |
| C10 GPU fusion loop | Q38FN GPU greedy on C12 loops past pos ~256 (BASE acc 0.05 vs NOATOM 0.70). No production exposure (v10 lacks the paths; Q38FN served on CPU). Suspect AK-H15 (`ak-fused.cu:445`). Bisect row `ak-c10-fusion-bisect-20261122` prepared (ledger 22:5xZ says published) | autokernel-loop.md C10-GPU-FUSION-LOOP-BISECT |
| V5I 27B stack change | Operator SIGNED RATIFY-V5I-27B-Q8MF-20261122; receipt on main. No-op until v11 (v10 lacks V5I) | artifacts/operator/stack-change-v5i-27b-q8mf-20261122 |
| Nondeterminism | determ-knob r2 KEEP_DETERMINISTIC: OFF A/A 7/16 diverge on fresh servers, ON 0/16 at 2.415x cost. Root cause = float atomics (V5 MF split half-tiles + mmq-q8-skinny). Test-gate use only | docs/design/spec-decode-run-nondeterminism-20261122.md |
| Bandwidth census | GPU + CPU census, seeds, :8100 panel, profiling standard; deterministic `census_update` hook in ak_runend step 4 live | root b44ef8852 (operator-run D9 script, rebased + pushed) |
| Research intake (lpr) | Stage 4 filed. INK2-MINI-1 GO CPU-first; Inkling deferred until after v11 (boxes INK2-PORT-1a..2c wired, partial GGUF deleted) | root 365010031, 08e031e00 |
| SPEC-STALE-1 | CPU fixes ported (stop-word parity 13/20 -> 20/20, EOG tail 48 -> 0); DF2 GPU parity row filed; C19 fold box added | root c3514dddc, f46781787 |
| splitkv (Q38FN draft) | r8 DROP on the speed clause (+3.2%, CI upper 1.0364 <= 1.0415 floor). Track closed | root 7b526cbc2 |
| AK loop backlog | WP1-5, P1-P5, AKU waves 1-3 (06l3 restart recovery, operation_settlement default ON), lint-fail 40 -> 2, loop suite GREEN (7135 passed) | research 936d29423, b2178cc6a, d4e25a3e2; root ff93a9099 |

## Other filed results (2026-11-22)
- I8GEMM per-channel port FUTILITY_OP (0.821x; 68.5 vs 83.3 TFLOP/s). Profiling standard must pick GB/s vs TFLOP/s by arithmetic intensity.
- AK-ASM-T1 harness r3 FAIL (fmoe id1024 spill memory-faults; classifier mislabeled it vacuous).
- QDEC IQ3Q6 r2 KEEP (0 failing IQ3_XXS cases vs anchor 7).
- PFXC-SAVE-1: saves are 0.9% of TTFT P95; restore transfer count is the bigger lever (PFXC-SAVE-2).
- Q38FN CPU verify already reuses weights; real CPU lever is 1-row dense bandwidth (47% of the 129.9 GB/s quarter ceiling).
- RS-REPLAY qwen4exp "defect" was MTP nondeterminism; allowlist re-add `efbd547c4` (C18-REPLAY-Q4X-ALLOW).

## Incidents / lessons
- Orchestrator lane commit 8fd386d0 briefly pushed to orchestrator main, reverted f8c313fb, no reload.
- STOP on a server-driving job produced a false FUTILITY_INPUT (ea-pool r2); auto-filed inconclusive. Harnesses must not judge STOPped runs.
- Single-sample OFF2==OFF identity gates are unsound under GPU atomics; new protocol: fresh server, N>=8 x R>=3 A/A.
- Shared-scratchpad commit-message clobbering recurred; commits now use files inside the worktree.

## Operator pending
- Consolidated AK-loop code-budget ratchet package (first package REFUSED at postflight, stale vs AKU waves; split agent building one package vs current main).
- Planner prompt `expected_outcome` review (research a2a247f15); TYPED-PLANNER-S1 tick on UNDETERMINED yield is questionable -> reopen decision.
- OP-AKU-BIND (gates AKU-06l4).
- C18 promotion stays operator-only, after A3B gate + C10 bisect.
