# LFM2 / LFM2.5 Family (Liquid AI) — Deep Dive

**Date**: 2026-05-29
**Intakes**: intake-650 (Liquid blog), intake-651 (HF model card / GGUF), intake-652 (complete-library catalog), intake-653 (arXiv:2511.23404 LFM2 Technical Report)
**Trigger**: post-intake deep dive to validate/revise the `adopt_component` + "drafter candidate" framing.
**Verdict outcome**: TWO material corrections — (1) NOT a drafter (vocab mismatch), standalone-only; (2) `lfm2moe` already merged in our llama.cpp HEAD but no production gap → 651 downgraded adopt_component → worth_investigating.

## Q1 — Drafter viability: NO. Standalone-only. (biggest skim error)

Project Chapter 01 (`docs/chapters/01-speculative-decoding.md`) states the hard rule: spec-dec "requires **exact tokenizer compatibility** between draft and target — same vocabulary size, identical special tokens, same tokenizer type. Same model family is NOT enough." LFM2.5 ships its **own 128K BPE vocab** (`LiquidAI/LFM2-Tokenizer`, registered in `convert_hf_to_gguf.py` with pretok hash `169bf02...`, pretok name `"lfm2"`), built by doubling LFM2's own 65K→128K — not a Qwen transplant despite cosmetic ChatML-like `<|im_start|>`/`<|im_end|>` tokens. Our targets use entirely different tokenizers: Qwen3.6 (frontdoor/coder), gemma4-26B-A4B (worker_general, Gemma SentencePiece ~256K), Qwen3.5-122B (architect), Qwen3-Next-80B (ingest). Vocab mismatch → ~0% acceptance (same failure already documented for the Qwen3-Coder BOS mismatch and DeepSeek-Distill 152,064 vs 151,936 cases). Cross-tokenizer spec-dec exists in the literature (see `2026-05-27-cross-tokenizer-specdec-and-mtp.md`) but is lossy, not implemented in our fork, and unjustified for a model with no other edge. Separately, **all current production spec-dec is self-speculation** (gemma4 MTP in the worker via ik_llama.cpp PR #1744; REAP+`--draft` for Qwen-Next) — there is no external-small-drafter slot to fill regardless. **Strike "drafter" from intake-650/651.**

## Q2 — llama.cpp `lfm2moe` support: REAL and MERGED in our HEAD

Verified in the local clone `/mnt/raid0/llm/llama.cpp` (HEAD `ee4818f30`, production-consolidated-v5, 2026-05-22):
- `LLM_ARCH_LFM2` and `LLM_ARCH_LFM2MOE` in `src/llama-arch.h` / `.cpp` (`"lfm2moe"`)
- `LLM_TYPE_8B_A1B` and `LLM_TYPE_24B_A2B` in `src/llama-model.h`
- build/dispatch branches in `src/llama-model.cpp`
- converter `@ModelBase.register("Lfm2MoeForCausalLM")` in `convert_hf_to_gguf.py`

Merge provenance: upstream PR **#16464** "support LiquidAI LFM2-MoE hybrid model" + follow-ups (#18132 missing-tensors fix, #18105, #17548), tool-call/chat-template (#16763, #21242, #21508), LFM2.5 tokenizer (#19687) — all ancestors of our HEAD. **Arch + converter support is present in our fork and no port is expected** — but this is a static source-tree check; a one-token GGUF smoke-load has NOT been run, so "loads" is "should load," not "verified to load." Opposite of the Ling-Linear/Lightning-Attention situation (which needed a custom port). Official GGUF (`LiquidAI/LFM2.5-8B-A1B-GGUF`): Q4_0 4.84 GB, **Q4_K_M 5.16 GB**, Q5_K_M 6.03 GB, Q6_K 6.96 GB, Q8_0 9.01 GB, F16/BF16 16.9 GB.

## Q3 — Architecture novelty: genuinely LOW (intake-653 correct)

The tech report (arXiv:2511.23404) self-discloses the gated short-conv block is "closely related to the short-range components that appear inside many recent efficient sequence blocks (Mamba, Hyena, Griffin)." LIV (Linear Input-Varying) double-gated short conv = input-dependent multiplicative gating (gates B, C) around a depthwise conv — a recombination of known primitives, not a new operator. The **real contribution is the hardware-in-the-loop NAS finding**: under fixed edge latency/memory budgets at 350M–2.6B params / 32K context, short-conv + a few GQA layers matches or beats full SSM/linear-attention hybrids on decode latency + peak memory. That's an empirical/systems result, not architectural novelty → **low confirmed**.

## Q4 — "No SSM needed" vs Ling-Linear (intake-503) / Minimax-01: no contradiction; regime boundary is sound

The report is explicit: the claim is scoped to "the **on-device regime** at 350M–2.6B params with 32K context," and "does not claim SSMs/linear-attention are generally unnecessary — only that their benefits diminish under strict edge latency constraints." Ling-Linear's win is the *opposite* regime — large (16B–104B), long-context reasoning, where linear attention's constant-memory recurrence pays off. The two **bound each other's regime cleanly**; neither refutes the other. (Caveat: the LFM2.5-8B-A1B product is 131K ctx / 8.3B total, above the report's NAS regime, but its block design is inherited from the small-model NAS, so the regime caveat applies to the design provenance.) This is the one genuinely reusable insight for the sub-quadratic-attention survey.

## Q5 — License lfm1.0 ("LFM Open License v1.0")

Apache-2.0-based, no copyleft; permits use/modify/fine-tune/redistribute (attribution + license inclusion + documented modifications); fine-tunes may stay proprietary. One restriction: **free commercial use capped at orgs <$10M annual revenue**; above requires a separate agreement. Per `feedback_license_not_a_blocker` (non-commercial self-hosted), this is a **non-blocker** — characterize as "source-available / restricted-commercial," NOT fully open like Apache/MIT.

## Q6 — Independent corroboration & the AA-Omniscience gap

Release corroborated by third parties (MarkTechPost 2026-05-28; Suprmind hallucination roundup; llama.cpp tool-call fix #21242). The **63.47% Non-Hallucination vs Granite-4.0-H-Tiny 6.38% / Qwen3.5-4B 16.99%** gap is real but explainable, NOT a benchmarking error: Liquid added an RL stage with an **avg@k abstention reward** that trains the model to *refuse* questions outside its reliable knowledge. AA-Omniscience Non-Hallucination rewards abstention, so an abstention-tuned model scores high on *that axis* — but **Accuracy is only 8.67 and the Index is −24.70 (negative)**. The headline is "knows when to say 'I don't know,'" not "knows more." Calibrated-abstention, not knowledge-superiority. No widespread quality/loading complaints surfaced (old "unknown architecture lfm2moe" errors predate #16464).

## Q7 — Quality tier vs worker_general (gemma4-26B-A4B)

LFM2.5 = 1.5B-active / 8.3B-total — far smaller than gemma4-26B-A4B (4B-active / 26B-total, 76.5 t/s solo, +18pp tool_compliance after the 2026-05-08 swap). LFM2.5 benches (IFEval 91.84, MATH500 88.76, AIME25 42.53, BFCLv4 48.50) are strong for a 1.5B-active **edge** model but below our worker tier. **No current production role has a gap it fills**: frontdoor/coder = Qwen3.6, worker = gemma4 MTP, architect = Qwen3.5-122B, ingest = Qwen3-Next-80B. Conceivable niches — a "cheap-first" pre-worker tier or a router/triage stage — are already served (MLP routing controller 92% val acc; BGE embedder) or not in the consolidated stack plan. On a BW-bound EPYC CPU the active-param advantage that matters on edge devices is muted.

## Revision outcome

| Intake | Field | Old → New | Reason |
|--------|-------|-----------|--------|
| 650 | relevance | high → medium | No production gap; standalone-only, not a drafter |
| 650 | credibility | 1 → 2 | First-party vendor blog, corroborated + reproducible claims |
| 651 | verdict | adopt_component → worth_investigating | llama.cpp support real but no role to deploy into; drafter rationale dead |
| 651 | relevance | high → medium | Align with 650 |
| 652 | credibility | null → 2 | Official vendor docs, read + corroborated |
| 653 | (all) | KEEP | novelty low / credibility 2 / relevance medium / worth_investigating — regime-boundary insight retains medium |

## Recommended next actions

- **No deployment, no port, no bench.** `lfm2moe` arch support is present in our HEAD (static source-tree check; not yet smoke-loaded); nothing to build, no production gap. Do not queue a llama-bench run (respects `feedback_no_concurrent_inference` — no role to justify it). If a role ever opens, the first cheap step is a one-token GGUF load test to confirm "support present" → "actually loads."
- **Strike "drafter"** from the LFM2 intake/handoff notes; record the vocab-mismatch reason inline so the claim isn't resurrected.
- Keep the **regime-boundary cross-reference** (LFM2 small/short-ctx conv-wins ⟷ Ling-Linear large/long-ctx linear-attn-wins) in `multiscreen-attention-evaluation.md` / `ling-linear-lightning-attention-hybrid.md` — the one reusable insight.
- **If** a "cheap-first worker" or "edge-companion / on-device" role is ever opened (per `project_stack_simplification`, `feedback_dont_dismiss_creative_uses`), reconsider LFM2.5-8B-A1B Q4_K_M (5.16 GB) as a standalone candidate — its calibrated-abstention behavior could suit a router/triage stage that must reliably say "escalate / I don't know." Flag to user, don't dismiss.
