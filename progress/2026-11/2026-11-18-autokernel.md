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
