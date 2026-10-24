# Stack-change package component (DRAFT): enable the decode-aware prefill budget on :8083

**Status:** DRAFT 2026-10-24. A component of the one v11 stack-change signature (no piecemeal reload). Not signable until the gates in section 4 pass. Nothing was applied, no server was started, no registry/topology yaml was edited. This is the KVU-16g-2 package edit; it is not a deploy.
**Owner task:** `KVU-16g-2` in [`kv-unified-stack-rollout.md`](../../handoffs/active/kv-unified-stack-rollout.md). Sibling component: [`eg2-embedder-adoption-stack-change-package.md`](eg2-embedder-adoption-stack-change-package.md). Assembled into the v11 kernel-promotion ratification by the promotion session (`kernel-promotion` step 8 hands to `stack-change`).
**Depends on:** manifest row V11-016 (`65d48a7a0` / champion `7052e26df`, flags default OFF) in [`llama-v11-manifest.md`](../reference/kernel-manifests/llama-v11-manifest.md); `KVU-16g-1` (the row-5c A/B score sheet); `PB-QCOST-1` in `gpu-serving-tie-in-program.md`.

## 1. Intent (phase 0)

```yaml
role: architect_critic            # :8083, MI210, Qwen3.8-27B Q8_0 + DFlash2 (--spec-type draft-dflash)
change: add two llama-server flags to the :8083 launch argv, nothing else
argv_add:
  --prefill-budget-decoding: <N>      # upper bound on prompt tokens per iteration while any slot is generating
  --prefill-budget-target-ms: <MS>    # adaptive budget, section 3
argv_unchanged: "-np 4 -c 393216 -b 512 -ub 512 --cache-ram 65536 --kv-unified (last observed launch, GPU-LEAK-1b note in gpu-serving-tie-in-program.md); re-read the live argv at phase 2"
requires_kernel: production-consolidated-v11 (or any build containing 7052e26df); v10 has no such flag
default_if_package_not_signed: both flags absent == feature OFF == previous behaviour
```

Flag semantics (read from `git -C /mnt/raid0/llm/llama.cpp show 7052e26df`, `common/arg.cpp`): `--prefill-budget-decoding N` caps prompt tokens per iteration (summed over prefilling slots) while any slot is in `SLOT_STATE_GENERATING`; with no slot generating, prompts still fill `n_batch`. `--prefill-budget-target-ms MS` sizes the budget from a smoothed cost per prompt token so an iteration with decoding slots takes about MS; floor 64 tokens; combines with `-decoding` as an upper bound. 0 or absent = off.

## 2. What the enable does and does not cover

- It covers decode-vs-prefill interference only. The budget returns 0 when no slot is generating (`pb_iter.n_generating == 0`, `98c0ce12a`), so it is not a fix for prefill-vs-prefill head-of-line blocking (DI-126). PB-HOL-1 measured it: with pb512 armed the short prompt above the long slot waited 83,352 ms vs 70,932 ms budget-off. Do not count this enable as covering DI-126.
- Dormant guard: if the KVU-16g A/B log shows the budget split across 4 or more prefilling slots at under 64 tokens each per iteration, file a minimum-effective-chunk rule on the experimental tree; no task before that trigger.

## 3. Choosing `--prefill-budget-target-ms` (SW-A2 / SW-A3 rider)

Rule: `target_ms = TPOT_target_ms - margin_ms`, where

- `margin_ms` is a ONE-SIDED margin equal to the held-out P99 absolute residual of the PB-QCOST-1 fit, never derived from the mean fit. Current number for the np4 shape (n = 4 generating slots): **211.2 ms/iter** (one-sided P99 under-prediction, confirm run 2026-10-23, `/mnt/raid0/llm/tmp/f8-launchers-20261023/pb-qcost-1-confirm/VERDICT.json`); the 2026-10-21 run gave 210.7 (leave-one-length-out 122.4). Grade **INDICATIVE** (harness path defect plus a sibling disturbance); the number is replaced by the PB-QCOST-1 `confirm-R` re-run, and this package takes the confirm-R value when it exists.
- `TPOT_target_ms` is the iteration-time target the stack wants for decoding slots at n = 4. It is NOT yet set: no document names it, and the decode-only step time at the production shape has to be read off the KVU-16g A/B log first. Placeholder until then; do not invent it.
- In llama-server every generating slot advances in one batch per iteration, so per-slot deadlines merged by min collapse to one global target. The host gap that GPU-ZOS-1 measures is subtracted from the same target.
- Take coefficients from the REFIT, never the frozen model (frozen held-out MAPE 12.84% at n = 1, 26.32% at n = 4; refit 3.1% / 3.3%). The refit's q coefficient is per-n (b = 1.166 ms/token at n = 1, 1.029 at n = 4), so the 0.9865 carried from the offline fit does not apply at n = 1.
- The update law `n' = n * target / t` converges only when the target exceeds the decode-only step time; a target below it floors at 64 tokens. Check `TPOT_target_ms - margin_ms` against the measured decode-only step before signing.

## 4. Gates (all must hold before the signature)

1. `KVU-16g-1` closed: per-arm table copied from `/mnt/raid0/llm/tmp/prefill-budget-20261004/` (run dirs `gpuab-20261004T145622Z`, `gpuab-20261004T172118Z`) into the handoff, scored against its done-when.
2. Decode-under-prefill ratio on the candidate at least the KVU-16g reading (x2.92 as quoted in the aggregate's candidate-W ledger; that figure is unverified until item 1 reads the score sheet), solo prefill within -4% to -14%.
3. OFF is byte-identical: the candidate launched without the flags produces identical greedy output to production v10 (presence gate for V11-016 plus the OFF identity run).
4. PB-QCOST-1 `confirm-R` done, so `margin_ms` is not INDICATIVE.
5. Launcher sets its own `LD_LIBRARY_PATH` and passes `verify_ggml_linkage.sh`; HIP residency proven (non-zero own-PID VRAM sampled during the run), per root CLAUDE.md.

## 5. Phases (stack-change skill)

- Phase 2 (topology/argv): edit the :8083 launch argv in `epyc-orchestrator` (`orchestration/stack_topology.yaml` and any launcher restating the argv; grep for `--kv-unified` to find every restatement) to add both flags with the section 3 values. One signature with the other v11 components.
- Phase 7-8 (bring up and prove): relaunch via `orchestrator_stack.py` (not by hand); prove with `prefill-budget: iter ...` lines in `llama-server-8083.log` (`decode_rows`, `budget`), and a short-prompt-under-long-prefill decode check.
- Rollback: remove both flags from the argv and relaunch; the previous behaviour is exactly restored (default 0 = off). No data migration.
