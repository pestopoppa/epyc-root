# KV-Quantization Decision Package — Qwen3.6-27B (architect_general, GPU)

**Prepared**: auditor, 2026-08-12, from `/mnt/raid0/llm/tmp/kvquant_results.json` (run
2026-07-31, 208 KB, raw data persisted, verdict never written — flagged independently by three
certification passes: T4-numa L889, T5-multimodal S-17, and the tranche synthesis).
**Grade**: OBSERVATION — single run, no protocol id, no era stamp, pre-dates tonight's era
rows. Prepares the decision; does not gate it.

## What was measured

Needle-retrieval probe on the 27B at `ctx=262144`, four KV-cache arms, 52 items each
(depths 8K/32K/90K/200K, begin/middle/end positions, 4 reps):

| arm | ctk/ctv | retrieval | decode t/s | prompt t/s | KV VRAM (peak−base) |
|---|---|---|---|---|---|
| R (reference) | f16/f16 | **51/52 = 98.1%** | 25.05 | 464.9 | **43.17 GiB** |
| A | q8_0/q8_0 | **51/52 = 98.1%** | 22.24 (−11.2%) | 458.6 | 36.63 GiB (−6.54) |
| B | q4_0/q4_0 | **51/52 = 98.1%** | 23.20 (−7.4%) | 456.9 | **32.63 GiB (−10.54)** |
| C | q8_0/q4_0 | 11/12 (INVALID) | 10.3 | 37.5 | not captured |

**The quality result is exact parity.** All three complete arms score identically at every
depth (8k 15/16, 32k 16/16, 90k 12/12, 200k 8/8), and the single miss is the **same item in
all three including f16** (entity "sentinel probe LV-47" answered with "XL-…" — an item/model
artifact, not a quant effect). On this probe, q4_0 KV is indistinguishable from f16 to 200K
depth. **Arm C is an aborted/degraded run** (12 items, one depth, 37 tok/s prompt vs ~460 in
the other arms — a different serving condition): it must NOT be read as "mixed KV failed"; it
never ran comparably.

## The tradeoff

q4_0/q4_0 buys **10.54 GiB of VRAM** at 262K ctx for **−7.4% decode** and no measured
retrieval loss. Context: the S-17 GPU budget audit recorded **1.40 GiB spare** at steady
state — KV headroom is the binding VRAM term on this card, and 10.5 GiB is transformative
(larger ctx, co-residency, or the shadow lane's own budget). Oddity worth knowing: q8_0 is
*slower* than q4_0 (dequant bandwidth), so q8 is dominated — the real choice is f16 vs q4_0.

## Options

- **A (recommended)** — adopt `q4_0/q4_0` KV for `architect_general`, spend the 10.5 GiB
  deliberately (name what it buys in the same change), accept −7.4% decode. Pair with a
  one-off reasoning-suite spot-check (the probe tests retrieval, not generation quality — the
  known gap in this evidence).
- **B** — keep f16: fastest decode, right call ONLY if VRAM is genuinely non-binding, which
  the 1.40 GiB spare figure contradicts.
- **C** — re-run under a named protocol with a quality arm before adopting: decision-grade
  path, costs an inference window, defensible if the role's outputs gate anything downstream.

**Recommendation: A, with the reasoning spot-check folded into the adoption change.** The
adoption itself is a stack-config change (registry + launch flags) — owner executes, operator
aware; this package is the evidence prep, not the change.

## Caveats (stated, not buried)

Retrieval parity ≠ full quality parity; single run, n=52/arm; observation-grade (no era
stamp — if adopted, the change note should carry the E9-cpu-kernel-era context even though
this is a GPU role, since the eval instrument era governs comparability); arm C
non-comparable; the 27B is `architect_general` post-W1 (GPU-resident) — this package does NOT
apply to `architect_critic` (122B, CPU) whose KV lives in RAM.
