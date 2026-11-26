# 2026-11-26 — autokernel (operator-invoked wrap-up, session 2026-11-25..26)

## C22 composite: READY TO SIGN (promotion is operator-only, not done)

- Branch `llama.cpp-experimental-c22-composite-20261125` @ `b1e1864cb`. Its tree equals `ce6fcbbde`, and the stores are built from that: `cpu-20261126-ce6fcbbde-c22-composite` and `gpu-20261126-ce6fcbbde-c22-composite` (version 10748). kernel_coverage PASSes for v10->C22 and C21->C22.
- Package: `/mnt/raid0/llm/tmp/ak-c22-composite-build-20261125/RATIFY-C22-PACKAGE.md`. Frozen keep list: `/mnt/raid0/llm/tmp/c22-keep-list-FROZEN-20261125.md` (18 fold rows plus one serving-config item).

| Gate | Row | Verdict |
|---|---|---|
| G-27B r5 | ak-c22-composite-gate-27b-gpu-20261126-r5 | KEEP x1.121. The I8PC_ONLY arm (the served env) is x1.128 [1.108, 1.147], KLD 0.0009. The lossless part is +5.2 % |
| G-Q38FN | ak-c22-composite-gate-q38fn-cpu-20261126 | KEEP x1.109 (lossless part +6.7 %) |
| G-A3B | ak-c22-composite-gate-a3b-cpu-20261126 | stopped at the futility look, x0.992 [0.924, 1.066]. No gain and no regression, so the knobs stay off for A3B. Filed WITHDRAWN |
| Draft window confirm r2 | ak-c22-q38fn-draftwin-confirm-cpu-20261126-r2 | KEEP by operator ruling. 7 clean blocks at x1.204-1.219. Block 8 is excluded as keeper-placement contamination. The harness verdict was FUTILITY_HARNESS_AA |
| DRAFTVOCAB quality r3 | ak-q38fn-draftvocab-quality-cpu-20261126-r3 | KEEP. OFF 83/100, noise arm 82, DV 82 |

- Operator decisions (2026-11-26 ~06:25Z): the DEVHANDOFF fold (C22[9]-[10]) is confirmed. The equal-quality rule for lossy CPU levers (KLD <= 1.5x the order-only arm) is confirmed. Serve WITHOUT q8wp (`GGML_HIP_Q8W8`); its code stays in, default-off.

## Production receipt S1-r2 (27B np4, ~8.4k-token prompts, sequential requests)

| Arm | Decode tok/s | Prefill tok/s | Acceptance |
|---|---|---|---|
| v10 | 45.9 | 517.5 | 0.416 |
| C21 | 69.1 | 603.7 | 0.415 |
| C22 | 68.8 | 631.6 | 0.404 |

On this workload C22 ≈ C21: decode is 0.996, and both are about x1.49-1.51 over v10. The G-27B +12.8 % is single-stream np1 ms/round and does not carry over to this workload. Short, coding and mixed prompts are not measured. The S1-r3 breakdown re-run waits on the operator's choice.

## Lever-row filing audit (lever list `/mnt/raid0/llm/tmp/ak-lever-rows-20261124.txt`)

- I checked every id on the list against `compute-flags/filing-done`. Only one ended row was unfiled: `ak-q38fn-cpu-gemv2-gate-20261125-r4`. I filed it today as **fail** (native FAIL_CORRECTNESS: DRAFTVOCAB greedy output differs from OFF on prompts 0, 1 and 3; witness clean; no timing). I ran it with `--no-reclaim` because it is an ak-q38fn gate row. The lever was then gated on served quality instead (DRAFTVOCAB quality r3 KEEP).
- Unfiled and not ended (no manifest, smoke-terminal only): api-trace, ub-deepctx r1, prodcfg a3b/q38fn/vl30b cpu, draftwin-confirm r1, q8lean r1, calib-shrink r1, pando r1, gemv2-gate r1, gemv2-d32k r1/r2, hostdepth-gate, draftvocab-quality r1, nongemv d1k r1/r7 and d32k r1. Each of these failed its smoke and a later rN superseded it, so none is a result to file.
- Still running or queued, so not filed: ak-c22-prodcfg-a3b-gpu-20261126-r2, ak-c22-prodcfg-quality-a3b-cpu-20261126 (and its r2), ak-c22-prodcfg-quality-q38fn-cpu-20261126-r2, ak-gpu-cpuload-contam-20261124-r2, ak-pernuma-contam-cpu-20261124-r3. ak-opperf-cal-27b-gpu-20261125-r3 has a STOP file and no end record.

## Negative results (journal: research `program.md` "Learnings 2026-11-26" + `akm-c22-misc-1126-nulls`)

- Pando r4: FAIL_CORRECTNESS. Output differs on prompts 5-7, so Pando is lossy.
- Fast CPU top-k (TOPK_SELECT=2): KLD 0.0389 against a bound of 0.003 (A/A 0.000). It is lossy, so only the exact mode 1 is folded.
- ub2048 and ub1024 at deep context are both SCREENED_RISK on max stall: 27.2 s vs 15.3 s, and 20.7 s vs 16.3 s. Serving stays at ub512.
- q8lean (-31 %), q8wt (-4.5 %), knee-batch (flat), DET1 / DET2 (-6 % / -3 %): already ticked and journaled on 2026-11-25.
- A3B composite: no gain (x0.992).
- RF7: `ak-c22-vattn-rf7-op-gpu-20261125` filed FAIL_CORRECTNESS_TBO, with no op GB/s. The PREC=2 rerun `ak-c22-vattn-rf7-op-gpu-20261126` died in smoke (FUTILITY_HARNESS_SERVER, KeyError 'input'). The brief's "RF7 strike 2, KLD 0.039" has no artifact on disk for RF7; 0.039 is the fast top-k KLD. VATTN-ROOFLINE-5 therefore stays open.

## Harness lessons (notes, not new rules)

- **Smoke budgets:** several smokes died on "smoke budget exceeded" (prodcfg q38fn/vl30b, draftwin-confirm r1, gemv2-d32k, draftvocab-quality r1). Size `smoke.budget_s` to the real prompt length.
- **Witness in unit:** the knob witness must come from the unit's own log. q8lean r1, gemv2 r1 and nongemv r1 failed FUTILITY_HARNESS_WITNESS because the knob was absent in their unit.
- **Smoke identity prompt length:** long identity prompts overran the smoke budget. Use a short identity prompt in the smoke and the long one in the row.
- **Keeper placement contamination:** the keeper placed 4 prodcfg CPU smokes beside the quiet draftwin row at 09:22Z, and OFF2 fell to 0.876. Pipeline confirmed this; cx73 fixes it.
- **served_quality parser** and **op-gate** fixes were needed before the quality and RF7 rows could run.
- **Per-arm stores:** each arm must name its own store; a shared store cannot witness the knob-off baseline.

## Handoffs

- Ticked (belief cc): AK-Q38FN-CPU-GEMV2-GATE, Q38FN-CPU-GEMV2-FIX-1, SERVED-27B-UB-DEEPCTX-1, SERVED-27B-UB1024-1, Q8-SERVED-DEV-SELECT-1, Q8-SERVED-DEV-INJECT-1, C22-COMPOSITE-SERVED-GATE, GPU-27B-LONGCTX-SECOND-NONDET.
- Notes only, boxes stay open: AK-Q38FN-CPU-NONGEMV-GATE (d32k r6 filed `partial`, empty RESULT) and AK-Q38FN-DRAFTWIN-C22 (it ticks when C22 is signed).
- Added: GPU-27B-SKINNY-SPLITK-DETERMINISM-1 (kv-cache-program) and C22-RATIFY-SIGN [operator-decision] (kernel-champion-and-promotion).
- Follow-ups (not boxed, box cap D9): S1-r3 production breakdown re-run (short, coding and mixed prompts; v10 / C21 / C22 decode, prefill and acceptance), which waits on the operator choice recorded in the RATIFY-C22 package.

Next: operator — sign or reject RATIFY-C22, and choose whether to run S1-r3.
