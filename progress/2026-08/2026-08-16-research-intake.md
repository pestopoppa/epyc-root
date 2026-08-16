# 2026-08-16 — research-intake session

## Summary

Ran the first single-model GPU quant ladder plus the never-before-run quantized batched `-np` sweep,
and found that the low-bit decode cliff on MI210 is a **kernel register-pressure / occupancy cliff**,
not a bits-per-weight effect. Filed the finding, three falsifiable hypotheses and six tasks as §22 of
`autokernel-research-loop.md`, with a durable receipt under `artifacts/gpu-aux-baselines/`.

Also repaired a silently-broken wiki compile watermark that was making every compile see the entire
repo as new.

## The measurement

Goedel-Code-Prover-8B, 8 rungs from ONE f16 source, ONE quantizer — the frozen production
`llama-quantize` 10125 (`0db32c06e`). Ladder built 2026-08-15, measured 2026-08-16.

| rung | GB | tg128 t/s | eff GB/s | %HBM | pp512 t/s | VGPR | waves/SIMD |
|---|---:|---:|---:|---:|---:|---:|---:|
| f16     | 16.38 |  63.97 | 1047.9 | 73.1% | 2880.9 | — | — |
| Q8_0    |  8.70 |  99.09 |  862.5 | 60.2% | 2673.1 | 25 | 8 |
| Q6_K    |  6.72 |  90.05 |  605.1 | 42.2% | 2460.0 | 46 | 8 |
| Q5_K_M  |  5.85 | 100.93 |  590.0 | 41.2% | 2459.4 | 55 | 8 |
| Q4_K_M  |  5.02 | 108.75 |  546.1 | 38.1% | 2462.2 | 44 | 8 |
| **IQ4_XS** | 4.59 | **129.77** | 595.3 | 41.5% | 2440.9 | **64** | **8** |
| IQ3_XXS |  3.36 |  79.44 |  267.2 | 18.6% | 2398.5 | 71 | 6 |
| IQ2_XXS |  2.48 |  82.89 |  205.9 | 14.4% | 2468.1 | 78 | 6 |

**The partition is clean and it is not a bpw trend.** Every rung whose
`mul_mat_vec_q<_,1,true,false>` fits in ≤64 VGPR (8 waves/SIMD) decodes ≥90.05 t/s; both rungs above
64 VGPR (6 waves) decode ≤82.89 t/s — *while being 27–46% smaller*. Separation 7.17 t/s, no overlap.
IQ4_XS sits exactly on the 64-VGPR boundary and is the fastest rung on the ladder. Below it,
shrinking the model makes decode **absolutely slower**. Prefill is flat (2398–2881 t/s, 16.7%
spread), so the cliff is specific to the batch-1 GEMV path.

Batched sweep (S_TG t/s, B=1→32) settles a long-standing reasoned-but-unmeasured premise:

| ratio to IQ4_XS | B=1 | B=2 | B=4 | B=8 | B=16 | B=32 |
|---|---:|---:|---:|---:|---:|---:|
| Q4_K_M  | 0.85 | 0.76 | 0.82 | 1.07 | 0.95 | 0.99 |
| IQ3_XXS | 0.60 | 0.61 | 0.67 | 0.67 | 0.70 | 0.77 |
| IQ2_XXS | 0.66 | 0.68 | 0.77 | 0.71 | 0.82 | 0.88 |

**"Batching closes the dequant gap" is REFUTED as stated.** It closes for the 8-wave K-quants
(Q4_K_M → ~0.99) and leaves **12–23%** on the floor for the 6-wave IQ formats. A purely
per-weight-read cost amortizes away as B grows; a wave-slot ceiling does not.

## Root cause — and the process finding underneath it

The mechanism was **already on disk before the ladder ran**:

- `mi210-q8-dequant-gemv-roofline.md:12` established for Q8_0 that the gap is "achieved-bandwidth /
  occupancy, **NOT** dequant-compute".
- `artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md` published the per-quant VGPR table on
  2026-08-12 — IQ4_XS at exactly 64 → 8 waves, IQ3_XXS/IQ2_XXS at 71/78 → 6 waves.

Between them they *predicted* this knee four days early. Neither reached the AutoKernel loop's
catalogue: measured 2026-08-16, format mentions in `autokernel-research-loop.md` were **Q4_K 20,
IQ2 8, Q8_0 6, Q6_K 4, IQ3 3 — and IQ4_XS 0, Q5_K 0, IQ1 0.** The loop was aimed at the rungs on the
wrong side of its own knee. **The transferable defect is receipt-to-catalogue transfer, not the knee.**

Consequence for the lever set: the ranked IQ2/IQ3 items (`v_perm_b32` sign expansion / 437-instruction
excess, Q4_K branchless six-bit scale-min decoder, VGPR 78→64) are **occupancy levers, not
dequant-arithmetic levers**. The payoff is threshold-shaped, not linear — crossing under 64 VGPR
regains the 8th wave, and a reduction landing at 70 buys nothing. None of those items currently states
a register target, so none can presently be judged against the threshold that decides whether it pays.

## Changes made

| Repo | File | Change |
|---|---|---|
| epyc-root | `handoffs/active/autokernel-research-loop.md` | NEW §22 — finding, 3 hypotheses with falsifiers (AK-H-QL-1/2/3), 6 tasks (AK-QL-1…6), one recorded non-filing |
| epyc-root | `artifacts/gpu-aux-baselines/a10_quant_ladder_occupancy_knee_20260816.md` | NEW receipt |
| epyc-root | `artifacts/gpu-aux-baselines/ladder-results-20260816.jsonl` | NEW raw ladder data |
| epyc-root | `artifacts/gpu-aux-baselines/np_sweep-20260816.log` | NEW raw batched sweep |
| epyc-root | `artifacts/gpu-aux-baselines/a10_quant_ladder_MANIFEST_20260815.md` | NEW build manifest (copied durable) |
| epyc-root | `wiki/.last_compile` | RESTORED to `2026-08-13T08:55:55Z` (see below) |

## Second finding — the wiki compile watermark was silently destroyed

`wiki/.last_compile` was **missing**, so `compile_sources.py` reported **844 new sources** — the whole
repo. It is deliberately untracked (`f1717d80`, "actually untrack the four generated/runtime files"),
and the live `git clean` recorded in `82400787` (2026-08-16 10:57) is the most likely destroyer.

Reconstructed from the last genuine `--touch` commit (`5fcad5e3`, 2026-08-13 08:55:55Z, preceded by a
real compile at `05c97235` 08:31). Restored watermark → **844 drops to 51** genuinely-new sources.

**Why this mattered more than it looks.** `get_last_compile()` returns `0.0` on a missing *or*
unparseable watermark, so watermark loss is indistinguishable from "nothing ever compiled". The likely
next action by anyone hitting 844 is to `--touch` it forward, which silently skips every genuinely
uncompiled source — the exact silent knowledge loss the lease rule exists to prevent. Filed as a task
rather than fixed unilaterally, because the untracking was a deliberate hygiene decision taken three
times by another session.

## Corrections to my own earlier reporting this session

1. **The lever is occupancy, not "unpacking rather than float conversion".** I earlier framed the
   residual low-bit cost as VALU bit-unpacking work. Narrower: unpacking work matters *because it
   holds live registers*, and registers set waves/SIMD. That is why the payoff is threshold-shaped at
   64 VGPR rather than proportional to instructions saved.
2. **%HBM figures were ~7.4% low.** I divided GiB model sizes into a decimal-GB bandwidth. Corrected
   above (f16 73.1%, not 68.1%). The 1.0737 factor is constant across rungs, so the *shape* of the
   finding survived and only the absolute percentages moved — which is how a constant-factor error
   hides itself.
3. **The ladder MANIFEST's warning #2 is a units artifact.** It claims the pre-existing upstream
   Q4_K_M/Q8_0 "differ materially in size" from the ladder's — but it compares upstream in GiB against
   ladder in GB. Measured: same size both pairs. Its "do not substitute" instruction still stands on
   provenance grounds, just not for the reason it gives.

## Deferred, with named blockers

- **`main` ↔ `origin/main` reconciliation — operator decision.** Local `main` is 80 ahead / 111 behind
  `origin/main`. A test-merge in an isolated worktree produced **22 conflicting files** spanning five
  sessions' live work, including `agents/commands/wrap-up.md` (being actively rewritten by RTG-52),
  three handoff indices, and `wiki/source_manifest.json`. Resolving those would mean adjudicating
  between live implementations owned by other sessions and publishing their unpushed commits under my
  resolution. Left `main` untouched per the wrap-up's own conflict contract; work backed up to a
  dated branch instead.
- **`-np` sweep replication (AK-QL-3)** — filed, not run: needs a GPU window and the §9.3 T1a recipe.
  Not blocked on a decision; it is queued work with an owner.
