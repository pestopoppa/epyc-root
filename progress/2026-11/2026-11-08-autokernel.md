# 2026-11-08 — autokernel (AutoKernel operator-invoked wrap-up, covers 2026-11-07..08)

No loop launch, no inference, no process management this session.

## Landed (all already pushed)

| Repo | Commits | What |
|---|---|---|
| research main | `091eb93b1..68ae80c80` | AKX-AUTO-4 calibration self-check (degraded block + spread vs prior floor), scratch-inventory allowlist, wired before both source-floor writes, abstains on rows without per-pair samples; `run.py` re-pinned. Box stays open: no clean floor exists yet. |
| research main | `09e9646f7`, `375972a63`, `f30243373`, `ae82f59da`, `7d1983baf` | SL-2 steps/s keep gate with acceptance guard (either-metric regression fails closed), SL-4 randomized legacy arm order + opt-in GPU C8 ~32k long-context cell; `run.py` re-pinned `7eec18fb…`; cpu_screen / runtime_arms / scratch test failures fixed. |
| research main | `079a656a1` | AK-HARVEST-5 planner paragraph. |
| research main | `d7581f993` | Harvest #9: the decode lever is q8_0-KV-specific; llama-bench cells on f16 KV misread it. |
| research main | `7a536f7fe` | Harvest #10: C8-FOLD3 FOLD_PASS on all clauses (fold3 `ab3fc54dc` is a qualified C8 candidate). Q2 draft length: np1 rises through the X=7 cap, np4 X3 ~ X7, n-max stays 7. |
| root | speculative-decoding.md, autokernel-loop.md | SL-2/SL-4 "Landed 2026-11-07" notes; harvest #5-#9 boxes (AK-TOOL-ANSI-ONE-STRIP, AK-BENCH-IDLE-GUARD, AK-HARVEST-5 ticked, AK-SERVING-LONGCTX-DECODE-ONLY, AK-BENCH-KV-TYPE-PIN). |

Harvest #11 seen (root `6345f9e66`, C8-4-H18 checkpoint): prefill 2.22x @128k, but its PPL unit ran on f16 KV with the q8_0 code-object path unmeasured. The q8_0 re-measure is Inference Research's (row `c8-h18-ppl-q8-20261108`). No planner change.

Harvest #11 program.md (research `bdb578307`, pushed): C8-5-H20 KEEP by operator decision (row verdict H20_NO_KEEP; 27B pp2048 1.0485). It folds as fold4 = fold3 + H20. The PPL ln-ratio ~0.0011 is a harness artifact; judge quality by KLD < 1e-3 plus top-1. Explicit decline, no AK box: AK's own `graph_kld_verdict` (`gates.py`) already gates on KLD + same-top, not ln_ratio, so the artifact cannot reach an AK verdict. [no-belief: decline]

## Verdicts

- SL-2 / SL-4: code landed, NO measurement yet. The M1 floor row (`ak-sl2-m1-floor-20261107`) is the first evidence; dry run PASSED 2026-11-08T01:17Z.
- AKX-AUTO-4: code landed; the Q38FN 6.528% replay-as-refused and a first accepted floor are not shown. Open.
- Full suite last run: 5 failed / 15 errors. `test_floor_registry_hardening::test_lib_registry_default_is_cwd_independent` is pre-existing. `test_validation_final_receipt` errors are load flakes (pass alone). The cpu_screen/runtime_arms/scratch failures were fixed in `7d1983baf`.

## Compute rows queued (none run by this session)

`ak-sl2-m1-floor-20261107` (grantable, awaiting keeper), `ak-surface-proof-a2-20261107`, `inf75-c7r-w3-halfb-census-20261107`, `ak-h5-verify-20261107`, `ak-build-mem-1-20261107`, `akx-lb3-2-cv6-pair-20261107-r2`, `df2-20-correct-20261107` (on ROWEXACT_PASS publish `/mnt/raid0/llm/tmp/df2-20-20261107/cost/spec.json`).

## Handoff edits this wrap-up

- autokernel-loop.md: new box AK-REGROWTH-BASELINE-3 (loop_code_budget_baseline.json entries for campaign_status.py, figure_lint.py, floor_selfcheck.py); cross-ref under AK-BENCH-KV-TYPE-PIN for the C8-4-H18 f16-KV PPL unit.
- speculative-decoding.md: new open sub-boxes SL-2-M1 and SL-4-LC; the two "IN FLIGHT, not landed" notes marked superseded; harvest #10/#11 note.
- autokernel-akx-program.md: AKX-AUTO-4 landed note (box open); the in-flight note is superseded.
- Already-existing open boxes confirmed, not duplicated: AKX-ALL-3 (line ~1125; merge of `ak/gpu-run1-20261004` is AKX-ALL-15c-2), AKX-ALL-1, AKX-ALL-13a, AKX-P1e.

## Deferred (named blockers)

- SL-2-M1 floor row: waits on the keeper grant (external event: compute calendar).
- C8-4-H18 q8_0 PPL re-measure: Inference Research's row.
