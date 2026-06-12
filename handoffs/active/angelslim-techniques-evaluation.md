# AngelSlim Techniques Evaluation — Sub-2-Bit Quantization + Reasoning Speculative-Exit

**Status**: stub
**Created**: 2026-05-21 (via research intake)
**Categories**: quantization, hardware_optimization, speculative_decoding, context_management
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`tq3-quantization-evaluation.md`](tq3-quantization-evaluation.md), [`llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) (archived 2026-06-12), [`per-request-reasoning-budget.md`](per-request-reasoning-budget.md), [`reasoning-compression.md`](reasoning-compression.md)

## Objective

Cherry-pick the portable techniques from Tencent's AngelSlim toolkit (intake-590) — Sherry 1.25-bit weight quantization (intake-591), SpecExit speculative early-exit (intake-592), Tequila ternary QAT (intake-593), DAQ delta-aware PTQ (intake-594) — and evaluate each independently against the EPYC stack. Do NOT adopt AngelSlim wholesale: the toolkit is vLLM/SGLang/transformers-first, the license posture is inconsistent between the GitHub repo and the arxiv paper (custom proprietary vs CC-BY-4.0), and the runtime focus is GPU.

## Important Scope Correction (2026-05-21)

**Sherry is a QAT method (training-time), not a PTQ.** This was overstated in the initial intake. Applying Sherry to an arbitrary post-trained worker requires ~10B tokens of QAT training on UltraFineWeb-style data — we have no infrastructure for this (CPU-inference-only operating regime per `feedback_experimental_repo`). The STQ1_0 llama.cpp kernel (PR #22836) is generic inference and can decode any Sherry-QAT'd weights, but **today the only public Sherry-QAT'd weights are Hy-MT1.5-1.8B and HY-1.8B-2bit (both 1.8B Hunyuan class)**. No Sherry-QAT'd Qwen3.6, gemma4-26B-A4B, Qwen3.5-122B-A10B, or Qwen3-Next-80B exists.

**Practical implication**: real adoption is gated on Tencent (or somebody) releasing Sherry-QAT'd checkpoints of a base model we actually run. Until then, the action is: (a) bench the existing 1.8B reference artefact to validate the kernel works on EPYC, (b) read the Sherry paper for whether the recipe could in principle be applied without full pretraining, (c) wait. Tequila has the same QAT-gating limitation. Only SpecExit and DAQ are PTQ-style / no-training-required.

## User Direction (2026-05-21)

This stub exists because the user explicitly framed Hy-MT2 itself as "useful specialist model... but maybe overkill given existing multilingual coverage." Per their selection: **focus expansion on AngelSlim 1.25-bit + IFMTBench, NOT on the translation models themselves**. The translation weights are deferred; the quantization recipe + kernel + early-exit method are the load-bearing artefacts.

## Research Context

| Intake ID | Title | Category | Verdict |
|-----------|-------|----------|---------|
| intake-586 | Hy-MT2 GitHub repo | training_distillation, quantization | worth_investigating (narrow: 1.8B-1.25bit as ingest tool only) |
| intake-590 | AngelSlim toolkit (arxiv:2602.21233) | quantization, spec-dec, hw-opt | worth_investigating (cherry-pick, do not adopt wholesale) |
| intake-591 | Sherry 1.25-bit ternary quant (arxiv:2601.07892, ACL 2026) | quantization | worth_investigating (highest priority) |
| intake-592 | SpecExit speculative early-exit (arxiv:2509.24248) | speculative_decoding | worth_investigating |
| intake-593 | Tequila trapping-free ternary QAT (arxiv:2509.23809) | quantization | worth_investigating (deferred — training-time) |
| intake-594 | DAQ delta-aware PTQ (arxiv:2603.22324) | quantization | worth_investigating (deferred — sub-4-bit only) |

## Open Questions

### Track 1: Sherry / STQ1_0 kernel
- Does Sherry's 10% speedup on Intel i7-14700HX (laptop class, 2-channel DDR5) transfer to EPYC 9655 (96-core, 12-channel DDR5)? Sherry's bottleneck framing is ALU/SIMD; our CPU-decode bottleneck is DRAM bandwidth (per `feedback_cpu_decode_bw_bound`).
- Has llama.cpp PR #22836 (STQ1_0 kernel) landed yet? If yes, rebuild our fork and llama-bench AngelSlim/Hy-MT1.5-1.8B-1.25bit-GGUF on EPYC.
- Does the Sherry recipe scale beyond 3B params? Sherry paper explicitly caps eval at 3B. Production EPYC workers are 26-122B class.
- Does Sherry's QAT step apply to existing post-trained Tencent open weights (Qwen3.6, gemma4-26B-A4B), or does it require training from scratch?

### Track 2: SpecExit early-exit
- Which base models was SpecExit tested on? Abstract does not specify (likely Qwen / DeepSeek-R1 class — Tencent author affiliation).
- How does SpecExit's hidden-state-derived exit signal compare against CGR (intake-566, certainty-guided probability probe) and dynamic-early-exit (arxiv:2504.15895)? All three are no-fine-tune dynamic-thinking-budget methods.
- Is SpecExit's claimed 2.5x speedup additive to our existing spec-dec setup, or does it require a specific verifier configuration? (Critical given `project_slot_promotion_shelved` — vanilla SD was net-negative on Qwen3.6 + Qwen3-1.7B drafter at bs=1.)

### Track 3: Tequila + DAQ (deferred)
- Tequila is a QAT method — adoption blocked on either Tencent-released QAT-Tequila checkpoints of an EPYC-stack base, or in-house QAT cycle. Not actionable today.
- DAQ targets sub-4-bit recovery of post-training capabilities. Our Q4_K_M baseline survives post-training deltas. DAQ becomes relevant only if/when we move to Q3_K_M / Q2_K.

## Adoption Sequence

1. **Block on PR #22836** — monitor `https://github.com/ggml-org/llama.cpp/pull/22836` (STQ1_0 kernel). When it merges or stabilizes, rebuild our fork with STQ1_0 enabled. Watch consolidated on [`tq3-quantization-evaluation.md`](tq3-quantization-evaluation.md) (2026-06-12; formerly tracked on `llama-cpp-kernel-push-rebase`, now archived).
2. **Bench Hy-MT2-1.8B-1.25bit-GGUF** — once STQ1_0 lands, llama-bench the 1.25-bit reference artefact on EPYC 9655 (NPS4, canonical baseline protocol per `feedback_canonical_baseline_protocol`). Verify the 1.5x decode speedup claim under our BW-bound regime. **Weights already on disk at `/mnt/raid0/llm/models/hy-mt2-1.8b/1.25bit/Hy-MT2-1.8B-1.25Bit.gguf`** (440 MiB, downloaded 2026-05-21 alongside the Q4_K_M and 2bit fallbacks; the multilingual ingest quality-gap test in [[internal-kb-rag]] uses the Q4_K_M variant since it works today).
3. **Read SpecExit full paper** — OpenReview link in intake-592; compare against intake-566 (CGR) on the same reasoning benchmarks if any overlap is feasible.
4. **Defer Tequila + DAQ** — no QAT cycle today, no sub-4-bit deployment today.

## Notes

- The Hy-MT2 translation models themselves are NOT the adoption target. Optional 1.8B-1.25-bit at 440 MB may live as a research-intake-pipeline tool for foreign-language snippets per intake-586's narrow framing.
- AngelSlim ships Eagle3 speculative decoding — known technique, not a fresh AngelSlim contribution. Tracked via existing spec-dec entries.
- IFMTBench (instruction-following MT eval, ships with Hy-MT2 release) is a methodology reference — its prompt-types taxonomy (terminology preservation, style adaptation, delimiter preservation, JSON/XML structured translation) may inform [[tool-output-compression]] / instruction-compliance eval suite expansion.
- License inconsistency between AngelSlim GitHub README (custom Tencent license) and arxiv 2602.21233 (CC-BY-4.0): resolve before any code adoption. The llama.cpp STQ1_0 PR #22836 sidesteps this by going through llama.cpp's MIT-licensed upstream.

## Reporting Instructions

- When PR #22836 lands: update this stub with merge commit + benchmark numbers; flip status from `stub` to `in_progress`.
- When EPYC bench of 1.8B-1.25bit-GGUF completes: record numbers in `progress/2026-MM/` and update this stub.
- When SpecExit head-to-head vs CGR is run: log results and update [[per-request-reasoning-budget]] + this stub.
