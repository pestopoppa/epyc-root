# 2026-11-11 autokernel progress

## Done
- C11 iqk FA compile-on A/B (`c11-iqkfa-ab-cpu-20261111`): verdict ON_DROPPED, filed pass, box C11-IQKFA-COMPILE-ON-AB ticked (8fbc04808).
- INF-86 checkpoint spacing (`inf86-ckpt-spacing-20261111`): PARTIAL, ~30% wasted-token cut (cms8192 -> cms512). Residual analysis (ANALYSIS.md, no runs): ~75% of the measured waste is the unavoidable SSM suffix after an edited older turn; cms512 removes 71% (16K) / 99% (64K) of the avoidable spacing term. Operator chose both the cms512 stack-change and the template/byte-identical fix; subagents in flight. New boxes INF-86-CMS512 and INF-86-TEMPLATE in hybrid-checkpoint-prompt-reuse.md.
- C11 skinny accept-nondeterminism decision: `c11-skinny-det2-gpu-20261111` filed fail; C11-SKINNY-DET closed (15ef79ee4).
- C10 Q38FN floor r5 (`ak-c10-q38fn-floor-r5-20261111`): serving 1.963% suspect, 64k 0.703% clean, FUTILITY_NOISY_NOT_REGISTERED; operator accept script written (8fa7b645b), not yet run, box open.
- race-eqv r6 (`race-eqv-gpu-r6-20261111`): not ended; blocked by the inf85 quiet-host drain. Pipeline is deploying the cap-backfill-at-T fix (operator D9-acked).

## Filing audit (2026-11-10/11)
Filed this wrap-up: ak-c10-q38fn-floor-r3 (inconclusive), r4 (inconclusive), r5 (fail), ak-mmq-h10b-dense-ctxstate-bracket-20261110-r2 (inconclusive, STOPPED duplicate of the filed pass). Boxes AK-C10-Q38FN-FLOOR and AK-MMQ-H10b stay open (floor registration pending operator script; H10b has further arms). UNFILED-ENDED 7 = 4 autokernel (above) + 3 operator-adhoc-ops-20261105 rows (pip02-r36-english-run-20261107, vidya-kvq-v10-sweep-20261107, vidya-r234-native-sweep-20261104), not filed here.
