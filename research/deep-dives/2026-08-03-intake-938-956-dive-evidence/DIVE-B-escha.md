# DIVE-B — Escha (intake-945, 946; 956 context) — ROLE CANDIDATE ASSESSMENT

## VERDICT
- worker_general: **CONDITIONAL** — NO to Escha's artifact, YES to the experiment it motivates.
- architect_critic: **NO** — closed by OUR OWN decision-grade evidence, not Escha's.

## THE TRAP (biggest finding — affects any future low-bit choice)
frozen v8 `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:73-74`:
    static_assert(!iqk_typeA_supported(GGML_TYPE_Q2_K));
    static_assert(!iqk_typeA_supported(GGML_TYPE_Q3_K));
**Q2_K and Q3_K are the ONLY two K-quant types EXCLUDED from iqk.** IQ2_XXS/IQ2_XS/IQ2_S/
IQ3_XXS/IQ3_S/IQ4_XS are all whitelisted (lines 64-65).
=> `UD-Q2_K_XL` (12.3GB) is the size-matched "reproduce Escha" pick and is the WORST choice:
   it puts Q2_K/Q3_K in the ROUTED EXPERTS, i.e. the bandwidth-dominant bulk, silently forfeiting iqk.
   **`UD-IQ3_XXS` (13.2GB) is the correct arm.**
CLAUDE.md's "supported K/legacy quants plus IQ2/IQ3 and IQ4_XS" is accurate but CONCEALS this.

## THE ACTIONABLE PATH (what Stage 1 missed)
Qwen3.6-35B-A3B is ~3B active vs gemma4's ~4B, is ALREADY live in the frozen kernel
(LLM_ARCH_QWEN35MOE, src/llama-arch.h:47, src/models/qwen35moe.cpp, mtp_on_hybrid_qwen35
at llama-model.cpp:2100), and we ALREADY serve it at Q8 on frontdoor/coder_escalation.
unsloth/Qwen3.6-35B-A3B-GGUF already publishes:
  UD-IQ1_M 10GB · UD-IQ2_XXS 10.8 · UD-Q2_K_XL 12.3 · **UD-IQ3_XXS 13.2** · UD-Q3_K_M 16.6
  · UD-Q3_K_XL 16.8 · UD-IQ4_XS 17.7 · UD-Q4_K_M 22.1 · Q8_0 36.9
IQ2_XXS (10.8) and IQ3_XXS (13.2) are BOTH UNDER worker_general's existing ram_gb: 16 budget.

## BUT THE BAR IS HIGH
gemma4-26B-A4B fully optimized: **126.2 / 96.7 / 82.9 t/s**
35B-A3B at Q8 with the same composed `ngram-mod,draft-mtp` recipe: **69.89 t/s**
=> the low-bit build must deliver ~1.8x bandwidth-to-speed conversion JUST TO TIE.
Counter-evidence on file (tq3): TurboQuant 573 vs q4_0 1279 t/s — FEWER BITS RAN 2.2x SLOWER
because dequant did not vectorize. So this is a real risk, not a formality.

## MTP LOSS RISK
Our production GGUF has **753 tensors vs stock's 733** — 20 nextn/MTP tensors; frontdoor
deliberately moved onto the MTP file 2026-08-01. unsloth low-bit files derive from STOCK and
have NO MTP block => `draft-mtp` falls out of the composed recipe.
Mitigation without touching the frozen tree: `build/bin/llama-quantize` and `build/bin/llama-imatrix`
are ALREADY BUILT — requantize our own MTP GGUF and keep the 20 tensors.

## architect_critic: CLOSED BY OUR OWN EVIDENCE
- Qwen3.5-122B at UD-IQ2_M on C-CRAB P-REV-1 reviewer slice: **FR 58.3%** (over-rejecting hard
  accepts) vs incumbent UD-Q4_K_M's FA 45.8% / FR 41.7%. Low-bit does NOT preserve critic
  CALIBRATION — it shifts it hard.
- Qwen3.6-27B dense Q8_0 (ZERO quant damage) over-approved on the same slice:
  **FA 54.2%, AUC 0.503** — a smaller Qwen is ALREADY FALSIFIED as a critic before quantization.
- Escha measured **NO calibration metric of any kind** (no ECE/AUC/Brier/accept-reject/hard negatives);
  all six axes are accuracy-style.

## CLAIM VERIFICATION
1. Retention table CONFIRMED verbatim (MMLU-Pro 82.3->80.9 98.3%; MATH-500 91.2->93.8 102.9%;
   GPQA-D 74.7->77.8 104.2%; LCB v6 67.0->62.6 93.4%; BFCL-AST 88.2->88.9 100.8%;
   RULER 89.4->89.9 100.5%; mean 82.1->82.3). Baseline FP8, 35.0GB vs 12.3GB.
2. Truncation confound CONFIRMED and does NOT invalidate retention. Arithmetic self-consistent:
   0.139x49.5 + 0.861x86.0 = 80.93 ~ 80.9 OK. Near-symmetric (13.9% vs FP8 13.0%) so biases BOTH
   arms down. Back-solved gap on COMPLETED answers ~1.2pp, marginally NARROWER than the 1.4pp headline.
3. "int8 lossless" CONFIRMED as resting on ONE boolq comparison (88.38 vs 88.04) — and 88.38 is the
   SAME CELL as the Commonsense-6 boolq entry, one measurement doing double duty. Restate as
   "indistinguishable on a single saturated benchmark, delta 0.34pp".
4. Coding gap **PARTIAL — direction corroborated, MAGNITUDE UNRESOLVED.** The card applies an
   ASYMMETRIC noise standard: calls GPQA +3.1 at n=198 an "effective tie" citing +-5pp instability,
   but calls LCB -4.4 at SMALLER n=182 "the one clear 2-bit gap". -4.4pp on n=182 = 8 questions;
   unpaired binomial SE ~5.0pp => ~0.9 sigma. No CIs anywhere. NOTE the asymmetry is
   ANTI-self-serving (makes their product look worse), so it supports the card's honesty.
5. Serving levers CONFIRMED but NOT TRANSFERABLE — CUDA/SGLang artifacts (launch-bound eager MoE;
   RADIX=0 is an SGLang prefix-cache trade with no llama.cpp analogue).
6. Context **RESOLVED — serving cap, not loss.** CTXLEN 32768 is a recipe default ("Raise once the
   defaults work"); RULER evaluated across 8k/32k/64k/128k. Card never claims to retain native window.
   File as "serving-recipe default, evaluated to 128k, 262K untested" — removes the implied
   conflict with intake-387.
7. Third-party evaluation **NOT-FOUND.** 5 HF discussion threads are all community REQUESTS,
   including "Additional Benchmarks & KL Divergence vs. Base Model". The X post RESTATES the org's
   own numbers and inflates to "12 benchmarks" by counting Commonsense-6 sub-tasks.

## THINKING-MODE FINDING (materially weakens applicability)
ALL six headline axes are thinking-ON. The ONLY thinking-OFF evidence is Commonsense-6
(boolq/piqa/arc-e/arc-c/hellaswag/winogrande, 76.06 vs 75.10) — six SATURATED multiple-choice tasks.
worker_general would run enable_thinking=false, so for our intended use the evidence base collapses.

## CORROBORATION THAT IS OURS, NOT THEIRS
intake-861 / arXiv 2505.02390 already records that 2-bit erodes REASONING while KNOWLEDGE holds ~99%.
Escha's six-axis ordering independently matches that shape exactly (knowledge 98.3, commonsense ~101,
long-context 100.5, tool-use 100.8, **code 93.4**). Different org, model, quantizer, same ordering.
It does NOT say a 2-bit 35B-A3B is good; it says WHERE TO LOOK FIRST.

## ENTRY DISPOSITIONS
- intake-946: dive-verified core + PARTIAL OVERTURN on the -4.4 coding magnitude
  (record direction-corroborated / magnitude-unresolved). Methodology-discipline note UPHELD.
- intake-945: NO CHANGE — Stage-1 recommendation against diving was CORRECT.
- intake-956: unchanged, still correctly blocked; relevance now LOWER — the practical path runs
  through unsloth's published GGUFs, so reverse-engineering eschamoe bears on nothing we would do.

## LEDGER
D1 speed kill-gate: UD-IQ3_XXS (NOT UD-Q2_K_XL) vs gemma4 126.2 t/s -> TASK,
   intake-derived-work-2026-07-25.md (alongside existing ID-29 worker_general speed row)
D2 code-weighted paired judge-free McNemar A/B, quant-only, IF D1 passes -> TASK, same handoff.
   REQUIRES OPERATOR INFERENCE APPROVAL. coder_escalation already supplies Q8 control + harness.
D3 MTP preservation: requantize our own MTP GGUF w/ already-built llama-quantize + llama-imatrix
   -> TASK, same handoff
D4 first CPU measurement of an IQ-quant MoE (all our IQ2/IQ3 data is GPU-resident)
   -> TASK, iqk-iquant-enablement.md
D5 CLAUDE.md iqk phrasing conceals the Q2_K/Q3_K exclusion -> FLAG ONLY, governance edit needs operator
D6 adopt eschamoe/runtime -> DECLINE (unchanged)
D7 CUDA-graph/radix levers -> DECLINE (runtime-specific)
D8 architect_critic via low-bit 35B-A3B -> DECLINE, closed by our own reviewer evidence

## PROCESS NOTE (correcting MY brief)
architect_critic appears in stack_templates/default.yaml only as a COMMENT at line 103; the role
block resolves from the derived registry. The role FACTS I gave were right; the
"verified from default.yaml" provenance was imprecise. Both DIVE-A and DIVE-B flagged it.
