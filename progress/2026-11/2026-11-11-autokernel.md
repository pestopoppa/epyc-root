# 2026-11-11 autokernel progress

## Done
- C11 iqk FA compile-on A/B (`c11-iqkfa-ab-cpu-20261111`): verdict ON_DROPPED, filed pass, box C11-IQKFA-COMPILE-ON-AB ticked (8fbc04808).
- INF-86 checkpoint spacing (`inf86-ckpt-spacing-20261111`): PARTIAL, ~30% wasted-token cut (cms8192 -> cms512). Residual analysis (ANALYSIS.md, no runs): ~75% of the measured waste is the unavoidable SSM suffix after an edited older turn; cms512 removes 71% (16K) / 99% (64K) of the avoidable spacing term. Operator chose both the cms512 stack-change and the template/byte-identical fix; subagents in flight. New boxes INF-86-CMS512 and INF-86-TEMPLATE in hybrid-checkpoint-prompt-reuse.md.
- C11 skinny accept-nondeterminism decision: `c11-skinny-det2-gpu-20261111` filed fail; C11-SKINNY-DET closed (15ef79ee4).
- C10 Q38FN floor r5 (`ak-c10-q38fn-floor-r5-20261111`): serving 1.963% suspect, 64k 0.703% clean, FUTILITY_NOISY_NOT_REGISTERED; operator accept script written (8fa7b645b), not yet run, box open.
- race-eqv r6 (`race-eqv-gpu-r6-20261111`): not ended; blocked by the inf85 quiet-host drain. Pipeline is deploying the cap-backfill-at-T fix (operator D9-acked).

## Filing audit (2026-11-10/11)
Filed this wrap-up: ak-c10-q38fn-floor-r3 (inconclusive), r4 (inconclusive), r5 (fail), ak-mmq-h10b-dense-ctxstate-bracket-20261110-r2 (inconclusive, STOPPED duplicate of the filed pass). Boxes AK-C10-Q38FN-FLOOR and AK-MMQ-H10b stay open (floor registration pending operator script; H10b has further arms). UNFILED-ENDED 7 = 4 autokernel (above) + 3 operator-adhoc-ops-20261105 rows (pip02-r36-english-run-20261107, vidya-kvq-v10-sweep-20261107, vidya-r234-native-sweep-20261104), not filed here.
- 2026-11-11 operator exception for row `ak-q38fn-relianceproof-c10-20261110-r5` (operator decision tool 2026-11-11, covers r5 only): one AutoKernel loop turn on Q38FN UD-IQ4_XS CPU at C10 `7f1bd044b`, regions 0-95, for VB-REFOCUS-NONEMPTY-READ-PROOF only. The hold otherwise stays in force.

## Afternoon (wrap-up 2026-11-11b)
- **INF-86 residual analysis and operator choice.** The cms-spacing PARTIAL is a metric-baseline artifact (~75% of measured waste is the unavoidable SSM suffix). The operator chose BOTH fixes: cms512 and the byte-identical template fix.
- **cms512 landed, reload held.** research e3aac480b, orchestrator 9690f455. Reload is held by operator decision until live-probe row `inf86-cms512-live-probe-20261111` (3 models x 2 arms on real traffic, RELOAD_OK/HOLD per model) shows savings and memory fit. The row is queued (quarter, rank 40).
- **Template fix landed.** orchestrator 301cfb21 (client-mode replay keeps reasoning_content) + 8dbc2ffa (preserve_thinking for unpinned thinking roles, architect_general only). API reload pending by the owner.
- **C11 skinny accept-nondeterminism.** det2 (last-block-done split-K) was deterministic but geomean 0.496 vs C10; the operator accepted the nondeterminism, so C11-SKINNY-DET is closed.
- **iqk FA dropped** (`c11-iqkfa-ab-cpu-20261111`): geomean 0.993, pooled within the 1.96% floor; C11 keeps iqk FA OFF.
- **C6 wiring boxes closed** (INF48-C6-RESEAL-C9, INF48-C6-LIVE-PROOF). C6-PORT35186-REMEASURE and C6-FEATURES-DEFAULT-OFF stay open: rows `c6-port35186-remeasure-r2` and `c6-features-cpu-r4` are queued, not run.
- **ATT canary r4e PASS** plus the rc75 row `att-canary-rc75-gpu-20261111` (owner inf48-triage). Its smoke attempt ended rc75 at 14:20Z (`FAIL-1.json`); not an autokernel row, not filed here.
- **vLLM AITER rows.** r1 was killed (rc=143, 14:25Z) because its prep pulled a ~35 GB image inside the GPU grant; r2 pre-stages the image outside the grant and is queued. r1 is superseded and not filable (no manifest, no result).
- **Backlog sweep.** Queued autokernel rows (published, awaiting a keeper placement): ak-q38fn-relianceproof-c10-r5 (quiet-host, blocked by the 4 running afc-v3c rows until ~21:47Z), akx-all-31-native-cpu, c10-local-code28k-r1, c10-local-serving-profile-r1, inf86-cms512-live-probe, c6-features-cpu-r4, c6-port35186-remeasure-r2, race-eqv-gpu-r6, vllm-aiter-r2. Smoke-stage rc75 stops (no run, nothing to file): b3-gdn-bf16-c10, ak-asm-h13-hctail-gpu, akx-all-31-native-gpu. Blockers: quiet-host drain by workspace-f2 afc-v3c rows.
- **Code landed.** lp_common rewrite 5ae029c1b; C6-features control fix dde42f8d4; AKX-ALL-31 native producer; H13 `k_hc_combine_norm` kernel (branch `llama.cpp-experimental-h13-hctail-20261111` @ 2f65143e3, knob off by default). AK-ASM-H13-HCTAIL e2e threshold 1.03 -> 1.010 was set by the subagent from noise math and is NOT operator-confirmed (flagged in the box).
- **OP-AK-HOLD r5 exception** (one loop turn, Q38FN CPU, C10) recorded; **C10 floor ratified** by the operator (serving 1.963% suspect, 64k 0.703%).
- **INF-85 W3** ticked: three v10 P-BENCH-1 rows (57.01 / 25.59 / 84.42 tok/s). No public URL: epyc-web WEB-2 hold.
- **Keeper fixes by Pipeline:** cap-backfill 407666d71, same-id requeue eea000786.
- **Filing audit:** no autokernel row is ended-and-unfiled. UNFILED-ENDED are `inf45-judge79-q38-27b-20261111` and `rtg34-r1a-bench-claim-20261111` (owner pipeline-mgmt, not filed here).
