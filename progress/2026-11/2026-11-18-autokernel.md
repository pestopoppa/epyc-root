# 2026-11-18 autokernel wrap-up (since 633b2ce6b, 2026-11-17)

Roster id `autokernel`. Verdicts read from `/mnt/raid0/llm/tmp/compute-flags/filing-done/*.verdict.json` (filed by agent). Intakes Exstill (intake-2669..2673) and BLACKFURY (intake-2674) were wrapped up separately; see `progress/2026-11/2026-11-17-autokernel.md`.

## Filed results

| Row | Verdict | Meaning |
|---|---|---|
| inf75-c12-w5s-census r3 | pass | W5s whole-host census observed on C12; `requests_completed` counter still unexplained |
| c12-cpu-p3-quiet | pass, KEEP | C12 1.280x faster per P3 step vs v10 (CI95 1.238-1.323), P2 control 1.338; r5's 0.976 was noise; size provisional (KLD/top-1 near limits) |
| rka-verify-tile-cpu | pass | CPU half of RKA-VERIFY-TILE; GPU and A3B48-E2E rows in flight |
| q38p1-c13 r3 | inconclusive | Landlock fence denied the profiler eval file; r4 queued |
| c13-farows-sidechannel-gpu r2 | fail by rule | decode geomean 1.000; verify +9.5% (indicative). Operator: quiet verify row, r14 dropped (STOP touched) |
| inf86-slot-restore-ckpt-c13 | pass | slot checkpoint restore validated on C13; ships with v11 |
| ak-inf06-exact-regate | pass | INF06 exact lane live for CPU campaigns (research f9c8ca5c6) |
| ak-c12-greedy-aa-bisect r3 | NOT_LOCALIZED | not host threads, not split-K; r4 toggles GPU suspects |
| c13-q81-sum-overflow r3 | inconclusive | classifier bug (empty offender list); fix passes 30/30 near cases where C13 fails 10; r4 runs edge leg + timing |
| fa-bugfix-c13-confirm | pass, FOLD_READY | 240/240 all-masked, hs256 5/5, no regressions; operator: hold for C14 with q8_1 after q81 r4 passes |
| akx31-qdec r3 | fail | 2 real C12 CPU mul_mat defects (IQ3_XXS, Q6_K); other legs judge artifacts or out-of-domain |
| inf48-favec-tail | fail (futility) | no consistent gain at 64k-128k; identity gate invalid on GPU (A/A nondeterminism) |

## Code
- INF06 exact lane, live for CPU campaigns: research `f9c8ca5c6` and earlier.
- FAVEC tail-split candidate branch `a01b44adc`: closed as futility, not pursued.

## Handoff edits (this wrap-up)
- Ticked: INF48-FA-ALLMASK-NAN, INF48-FA-HS256-MMA-PRECISION (kernel-champion-and-promotion.md), INF48-FAVEC-TAIL (rocm-kernel-authoring.md), AKX-P0d-W5s-SUCCESSOR (autokernel-akx-program.md). INF06-EXACT-LANE, INF-86-SLOT-RESTORE-CHECKPOINTS and C12-CPU-FOLLOWON were already ticked by others.
- C14 fold decision recorded under INF48-FA-ALLMASK-NAN (INF-65).
- New boxes: AKX-ALL-31.QDEC-CPU-MULMAT, AKX-ALL-31.QDEC-JUDGE. Result notes added to EDGE-HIP-NONFINITE (q81 r3) and QDEC (r3).
- Next-action cells refreshed for INF-06, INF-65, INF-82, INF-83, INF-70, INF-86, INF-48.
- Lessons: compute-fillers.md "Lessons from 2026-11-17/18" (Landlock fence, fast residency polling, futility names offenders, GPU A-vs-A calibration).

## In flight (not filed)
c13-farows-sidechannel-verify-quiet-20261118, c13-q81-sum-overflow-gpu-20261118-r4, q38p1-c13-20261117-r4, ak-c12-greedy-aa-bisect-20261118-r4, rka-verify-tile-gpu-20261117, rka-verify-tile-a3b48-e2e-20261117, c6-admission-live-proof-r7 (manifest still in ready/).

## Wrap-up 2 (operator-invoked, later on 2026-11-18)

Verified every note against origin/main `6f5cf4b45`; only the gaps below were filed.

### Rows filed and verdicts

| Row | Verdict | Meaning / box |
|---|---|---|
| c14-fold-build-20261118 | pass (PREFLIGHT_PASS) | C14 `eee3da838` builds; CPU objects byte-identical to C13. C14-FA-FOLD stays open until c14-fold-gpu-20261118-r2 |
| c15-fold-build-20261118 | pass (PREFLIGHT_PASS) | C15 `b10f91e32` builds; CPU/GPU gates wait on C14's GPU gate |
| c13-q81-sum-overflow-v2-gpu-20261118 | fail (PERF_COST ~3.5%) | v2 fully correct but 3.5-4% slower on q4_K/q5_K n=16; noted under EDGE-HIP-NONFINITE |
| ak-c12-greedy-aa-bisect-20261118-r4 | pass, LOCALIZED_ALL | only all-toggles-off (ALL 0.904) restores A/A; no single cause; box open |
| c6-admission-live-proof-r7 | inconclusive (FUTILITY_CARRIER) | fixed in research `92ce851f4`; r8 published (rank 40) |
| rka-verify-tile-a3b48-e2e-20261117 | partial, NO_RECOMMENDATION keep D=4 | later found contaminated; RKA-A3B48-D-REMEASURE row -r2 published at 110 |
| akx31-qdec-cpu-iq3q6-fix-20261118 | fail | op fix correct (17d092de0), KLD identical; AKX-ALL-31.QDEC-CPU-MULMAT noted, not ticked |
| c13-farows-sidechannel-verify-quiet-20261118 | fail by rule | operator overrode as KEEP; C15-FAROWS-FOLD |
| rvp-ctr1-planner-ab-20261118 | fail | counters ON 16/24 vs OFF 19/24; RVP-CTR-1 ticked, `--gpu-counters` stays opt-in |
| inf48-gateup-cpu-prof-20261118 | NO_CANDIDATE | X 1.52%/1.25% < 2%; INF48-GATEUP-PROBE ticked |
| rka-a3b-n4-step-gpu-20261118 | futility | MMVQ_Q8_B4_ROWS knob does not move the n=3->4 step; trace row published (rank 20) |

### Rows queued / prepared
Published: c6-admission-live-proof-r8 (40), rka-a3b-n4-trace-gpu-20261118 (20), akx-all-13a-q38fn-threads-20261118-r2 (110), rka-a3b48-d-remeasure-20261118-r2 (110). Prepared, unpublished: c15-epi-q8-gpu, c15-lightning-idx-fix-gpu (HELD), c15 gv-bw, c15-cpu-fa-splitkv, c5-isa1-live-proof, c5-isa2-capture-replay, rvp-race2-executor, ch33 C15 same-tip.

### Operator decisions and findings
- AKX-ALL-13a re-scoped vs production `-t 96` (row -r2, rank 110). CH-19 not needed (hook live on C14, ceiling < 1%). FD-DIV-2 and FUSED-DECODE-ZERO-ROW already in C14 (source read). CH-33 folded `4265996a8`; CH-LB1.1 already present by content.
- DF2-BLOCK16 prep done (research `8798d2612`); operator: prep now, GPU later.
- Fused-q8 MMVQ STOP (`7ec57d0c9`, net ~0-1%); C15-EPI-Q8 is the live variant. C15 gv_fattn bandwidth diagnosis under C8-1-H17; AKX-ALL-24 split-KV candidate; C5-ISA-1 call-site wiring + counter witness; C5-ISA-2 replay tooling (`747434968`, `6decaeda4`); RVP-RACE-2 executor (`411061267`, `76d596923`); C11-GPUPROOF-ANSI-PARSE ticked `dec3334d9`.
- LIGHTNING_INDEXER fix `066e81796`: row prepared but HELD per the operator's priority rule (speed first; correctness only when it affects served models).
- v11-promotion-checklist HOLD (`4aa8d1ede`, `a1dac64df`) verified current; untouched.
- Rows withdrawn and republished at rank 110 because their host reservations idled the GPU.

### Lessons
Added to compute-fillers.md "Lessons from 2026-11-18": launcher-literal threads, rank multi-quarter rows low, IDLE-HELD is not utilisation, n<=128 for CDNA capture, rocprofv3 path, `-q -F` commit hook.

### Gaps filled this wrap-up
Notes added for c14/c15 fold-build PASS, c6 r8, 13a-r2, a3b48 -r2 and n4-trace published, Fused-q8 STOP, LIGHTNING hold, C5-ISA-2, RVP-RACE-2. No boxes ticked (all remaining boxes' questions are still open); no result ticks added, so belief-capture count is 0 cited / 0 cc / 0 declined, with every new note tagged `[no-belief: ...]`.
