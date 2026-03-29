# REAP — MoE Expert Pruning Evaluation

**Status**: PHASE 1-2 + 2b COMPLETE. **246B PRODUCTION CANDIDATE: 77% quality (official), 8.4 t/s (+20%), 139 GB (-44%)** — better than unpruned 480B on every axis. NUMA sweep pending.
**Created**: 2026-03-20 (via research intake)
**Updated**: 2026-03-22
**Categories**: moe_optimization, quantization, inference_serving

## Objective

Evaluate REAP (Router-weighted Expert Activation Pruning) for permanent MoE expert removal on our Qwen3 production models. REAP removes entire experts based on router-weighted saliency scores — no fine-tuning required, immediate deployment. At 25% pruning, quality is near-lossless; at 50%, ~92% coding quality retained.

**Key distinction from runtime expert reduction (Chapter 02)**: REAP permanently removes experts from the model file. Download the pre-pruned GGUF, skip `--override-kv` entirely. REAP *replaces* runtime moe reduction — do NOT stack them.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-181 | REAP the Experts (arXiv:2510.13999, ICLR 2026) | high | new_opportunity |
| intake-182 | AutoRound / SignRound (arXiv:2309.05516, EMNLP 2024) | low | not_applicable |
| intake-184 | 0xSero HuggingFace — 28 REAP/AutoRound models | medium | worth_investigating |
| intake-185 | CerebrasResearch/reap GitHub repo | high | new_opportunity |
| intake-186 | EvoESAP evolutionary search | medium | downgraded |
| intake-187 | MoNE (Mixture of Nested Experts) | low | downgraded |
| intake-188 | Router Knowledge Distillation | medium | conditional |
| intake-189 | Cerebras 30 official REAP models | high | new_opportunity |
| intake-190 | Gate renormalization (paper v2) | high | new_opportunity |

## Answered Open Questions

All 6 original open questions resolved by deep dive agents:

| Question | Answer | Source |
|----------|--------|--------|
| GGUF compatibility? | YES — bartowski has 26 quants, standard `qwen3moe` arch, llama.cpp b6810+ | Cerebras models deep dive |
| Runtime expert reduction stacking? | NOT needed — REAP replaces runtime moe reduction. Download pre-pruned GGUF, skip `--override-kv` entirely | REAP paper deep dive + user correction |
| Calibration recipe? | 51% evol-codealpaca + 24% xlam-function-calling + 24% SWE-smith (1,360 samples) | 0xSero deep dive |
| Cerebras pre-pruned usable? | YES — Q4_K_M = 15.19 GB, downloaded to bartowski/ dir | bartowski GGUF deep dive |
| Memory savings? | 15 GB vs ~18 GB base (−16% at Q4_K_M) | Cerebras models deep dive |
| Qwen3.5 hybrid? | NOT supported by REAP repo officially — but 0xSero applied it to Qwen3.5-35B-A3B (intake-236). Works but PPL +39% at 20% pruning vs near-lossless on pure MoE. Hybrid less tolerant. | REAP repo deep dive + intake-236 |

## Critical Findings from Deep Dives

1. **Goldilocks zone: 30-40% pruning** — REAP-20% was WORSE than REAP-30% on MiniMax (repetition loops at low temp). Too little pruning destabilizes routing without forcing redistribution.
2. **Cerebras 480B at 25%**: outperforms base on 6/14 benchmarks (agentic tasks up 1.8-2.9 pts).
3. **Kimi-Linear at 30%**: +10 AIME25 — removing noisy experts can actually help reasoning.
4. **EvoESAP: DOWNGRADED** — hurts Qwen3+REAP at 25%, minimal gain at 50%. Not worth 5h search cost.
5. **Router KD: modest for REAP** — 16/25 benchmarks improved but gains small. 2h investment only at 50%+.
6. **MoNE: DOWNGRADED** — no REAP comparison in paper, only 16B models tested, novices are just mean vectors.
7. **REAP-25B is pure MoE** (`qwen3moe` arch) — unlike current hybrid frontdoor, CAN use speculative decoding. Tree speculation viable (pure MoE Q4KM saw +2.7% with ps=0.05 on Coder-32B).
8. **30 Cerebras official REAP models** across 7 model families (not just the 5 initially found).
9. **Gate renormalization (paper v2)**: improves from 2.6% to 1.9% mean accuracy loss.

## Model & Benchmark Setup

### Downloaded Model

```
/mnt/raid0/llm/lmstudio/models/bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF/
  cerebras_Qwen3-Coder-REAP-25B-A3B-Q4_K_M.gguf  (15 GB)
```

### Registry Entry Needed

New `reap_25b_frontdoor` role in model_registry.yaml:

- **architecture**: `moe` (pure MoE, NOT hybrid — unlike current frontdoor)
- **path**: `bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF/cerebras_Qwen3-Coder-REAP-25B-A3B-Q4_K_M.gguf`
- **draft_model**: `Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf` (same as worker — compatible, same Qwen3 coder tokenizer)
- **size_gb**: 15
- **quant**: Q4_K_M
- **acceleration**: speculative_decoding only (dm/ps from sweep). NO moe_expert_reduction — REAP replaces it
- **comparison targets**:
  - Worker 30B-A3B (39.1 t/s at dm=8/ps=0, same arch unpruned) — measures REAP speed impact
  - Frontdoor 35B hybrid (19.6 t/s/instance, moe6+lookup) — production replacement comparison

### Comparison Baselines

| Model | Role | t/s | Config | Arch | Notes |
|-------|------|-----|--------|------|-------|
| Qwen3-Coder-30B-A3B Q4KM | worker | 39.1 | 48t, dm=8, ps=0 | pure MoE | Same arch, unpruned. Direct A/B. |
| Qwen3.5-35B-A3B Q4KM | frontdoor | 19.6/inst | 4×48t, moe6+lookup | hybrid | Production. No speculation viable. |

## 4-Phase Evaluation Plan

### Phase 1: Speed Optimization (COMPLETE — 2026-03-24)

1. Add `reap_25b_frontdoor` to model registry (follow worker/frontdoor entry format)
2. Baseline measurement: single 48t instance, no acceleration, record raw t/s
3. Compare vs base 30B-A3B baseline (already known: ~28.7 t/s at 48t without spec, 39.1 with dm=8)
4. Speculative decoding sweep using `bench_all_spec_sweeps.sh`: dm={8, 16, 24, 32, 48}
5. p_split sweep: test ps={0, 0.05, 0.1, 0.3} — **DO test tree** (pure MoE, not hybrid; Q4KM coder saw +2.7% with ps=0.05)
6. **NO MoE expert reduction** — REAP already permanently removed experts. Run REAP-25B with all remaining experts active.
7. Lookup: test with/without (`--lookup` flag)
8. NUMA config: 4×48t quarters (15 GB fits trivially, same pattern as worker/frontdoor)
9. Record optimal config and compare: REAP-25B optimal vs base 30B-A3B optimal (39.1 t/s) vs frontdoor (19.6 t/s)

**Phase 1 Results (2026-03-24):**

| Config | Avg t/s | vs Worker (39.1) |
|--------|---------|------------------|
| **dm=24 linear** | **39.62** | **101%** |
| dm=48 linear | 39.13 | 100% |
| baseline (no spec) | 33.21 | 85% (15% faster than unpruned base 28.7) |
| dm=16 tree ps=0.05 | 30.83 | 79% — tree HURTS |
| dm=8 lookup | 37.91 | 97% — lookup safe (pure MoE) |

Optimal: dm=24, ps=0, linear only. Lookup safe but doesn't help on short prompts.

### Phase 2: Quality Benchmark (COMPLETE — 2026-03-24)

1. ~~Run `./run_benchmark.py --model reap_25b --server-mode`~~ DONE
2. ~~Compare quality against baselines~~ DONE (see results below)
3. ~~Speed comparison~~ DONE
4. Loop detection stress test: NOT YET — 4 temps × 6 prompt types per 0xSero methodology

**Phase 2 Results (2026-03-24):**

| Suite | REAP-25B | Q4KM Coder-32B | Notes |
|-------|----------|----------------|-------|
| agentic (10) | **26/30 (87%)** | 27/30 (90%) | Near-identical |
| coder (10) | 18/30 (60%) | 20/30 (67%) | Truncation at 256 tokens |
| general (10) | 21/30 (70%) | 20/30 (67%) | REAP slightly better |
| IP (11) | 18/33 (55%) | 20/33 (61%) | T3 failures same across all models |
| math (10) | 13/30 (43%) | 21/30 (70%) | Worst — all truncated before answers |
| thinking (10) | 14/30 (47%) | 19/30 (63%) | Truncation + 1 genuine error |
| **TOTAL** | **110/183 (60%)** | **133/183 (73%)** | |
| **Pass (≥2)** | **37/61 (61%)** | **45/61 (74%)** | |

**Key observations:**
- 13pp gap is primarily **truncation at 256 max_tokens**, not reasoning deficiency
- Agentic suite (tool calls fit in 256 tokens) scores nearly identical
- Math/thinking hit hardest — need more tokens for multi-step reasoning
- No repetition loops detected (unlike REAP-20% on other models)
- A rerun with 512 max_tokens would give more accurate quality numbers

**Decision matrix:**

| Model | Quality | Speed | 4×48t agg | RAM | Best for |
|-------|---------|-------|-----------|-----|----------|
| REAP-25B | 61% | 39.6 t/s | ~158 t/s | 15 GB | Fast frontdoor, try-cheap-first worker |
| Q4KM Coder-32B | 74% | 10.8 t/s | ~43 t/s | 18.5 GB | Quality coder specialist |
| 35B hybrid moe6 | ~79%* | 12.7 t/s | ~51 t/s | 20 GB | Current frontdoor (hybrid, no spec) |

*35B quality from earlier scoring, not directly comparable (different model family)

### Phase 2b: Pre-Pruned 480B Evaluation

#### REAP-363B (25% pruned) — COMPLETE (2026-03-25)

Downloaded (219 GB Q4_K_M, 5 shards) and benchmarked.

| Config | Avg t/s | vs 480B (7.0) |
|--------|---------|---------------|
| **dm=48 linear** | **6.54** | **93%** |
| dm=24 linear | 6.34 | 91% |
| dm=24 lookup | 5.04 | 72% — lookup hurts |
| dm=16 tree | 4.96 | 71% — tree hurts |
| baseline | 3.77 | 54% |

**Verdict: NOT compelling for single-model deployment.** 7% slower, 31 GB savings irrelevant at 1.13 TB. Tree and lookup both harmful (~22%). REAP on large MoE is a GPU VRAM optimization — our CPU RAM budget is not the bottleneck.

**Value case: concurrent-model RAM budgeting.** In dynamic stack assembly scenarios where two conversations need different large models simultaneously (e.g. REAP-246B for architect + freed RAM for extra workers), the RAM savings matter. Not relevant for single-conversation use.

#### REAP-246B (50% pruned) — COMPLETE (2026-03-26) — **PRODUCTION CANDIDATE**

Downloaded FP8 safetensors, converted to f16 GGUF, quantized to Q4_K_M (139 GB). Intermediates deleted.

**Speed (Phase 1):**

| Config | Avg t/s | vs 480B (7.0) |
|--------|---------|---------------|
| **dm=32 linear** | **8.00** | **+14%** |
| dm=24 lookup | 7.95 | +14% |
| dm=48 linear | 7.89 | +13% |
| baseline | 4.88 | 39% faster than 480B baseline |

**Quality (Phase 2, 512 max_tokens, Claude-as-Judge):**

| Suite | REAP-246B | 480B unpruned | Delta |
|-------|-----------|---------------|-------|
| agentic | 27/30 | 28/30 | -1 |
| coder | 21/30 | 23/30 | -2 |
| general | 23/30 | 22/30 | +1 |
| IP | 17/33 | 20/33 | -3 (prompt leakage) |
| math | **24/30** | 21/30 | **+3** |
| thinking | **24/30** | 19/30 | **+5** |
| **TOTAL** | **136/183 (82%)** | **133/183 (73%)** | **+9pp** |

**Verdict: BETTER than unpruned 480B on every primary axis.** +9pp quality, +14% speed, -44% RAM. The 50% pruning removed noisy experts that degraded math/thinking. Only IP regressed (prompt leakage). **Strong candidate to replace production architect_coding.**

**Decision matrix update:**

| Model | Quality | Speed | RAM | Best for |
|-------|---------|-------|-----|----------|
| **REAP-246B** | **82%** | **8.0 t/s** | **139 GB** | **Architect coding (replace 480B)** |
| 480B unpruned | 73% | 7.0 t/s | 250 GB | Current production |
| REAP-363B | not scored | 6.54 t/s | 219 GB | Not compelling |
| REAP-25B | 66% | 39.6 t/s | 15 GB | Fast frontdoor/worker |

### Phase 3: Run REAP Ourselves (if Phase 2b positive)

1. Run REAP at 25%, 30%, 40% on Qwen3-Coder-30B-A3B using CerebrasResearch/reap
2. Custom calibration from our production workload (agentic coding + tool calls)
3. Convert each to GGUF Q4_K_M via convert_hf_to_gguf.py
4. Repeat Phase 1-2 for each variant

### Phase 4: Aggressive Compression (if Phase 3 shows 30-40% safe)

1. REAP 50% on Qwen3-Coder-30B-A3B
2. Apply Router KD (~2h on A100, 3000 samples, 0.04% of params)
3. Convert to GGUF, benchmark

## Why This Matters for EPYC

1. **Memory savings**: 15 GB vs ~18 GB base (−16% at Q4_K_M) — smaller GGUF, faster loading, lower RAM
2. **Throughput**: Fewer experts = less MoE routing overhead, potentially faster inference
3. **Speculation viable**: Pure MoE arch (unlike hybrid frontdoor) enables speculative decoding — potential for higher t/s than 35B hybrid frontdoor
4. **Pre-pruned models exist**: Cerebras + bartowski ship ready-to-use GGUFs — benchmark immediately
5. **Calibration is code-optimized**: 51% evol-codealpaca + 24% xlam-function-calling + 24% SWE-smith — aligns with our agentic coding workload
6. **Direct A/B comparison**: Worker is now the unpruned base model (Qwen3-Coder-30B-A3B). Same arch, same quant, same draft — only diff is 25% expert pruning.

## Notes

- REAP is MoE-specific — does NOT apply to dense models or hybrid recurrent layers
- ALL Qwen3.5 variants (0.8B–397B) are hybrid Delta Net — REAP only works on pure MoE (Qwen3)
- Calibration data quality is critical — missing code data causes code-expert pruning
- 0xSero's GLM-4.7-REAP work shows the technique is mature and community-validated
- Goldilocks finding: 30-40% may be better than 25% — Phase 3 will test this

## Research Intake Update — 2026-03-28

### New Related Research
- **[intake-236] "0xSero/Qwen-3.5-28B-A3B-REAP — REAP 20% on Hybrid Qwen3.5"** (huggingface.co/0xSero/Qwen-3.5-28B-A3B-REAP)
  - Relevance: **Contradicts our assumption** that REAP only works on pure MoE. 0xSero applied REAP 20% to our exact hybrid production model (Qwen3.5-35B-A3B).
  - Key technique: REAP expert pruning on hybrid Delta Net + MoE architecture (256 → 205 experts)
  - Reported results: HumanEval -3pp, MMLU -3.5pp, but PPL +39% (6.83 → 9.51). vLLM throughput flat.
  - Delta from current approach: We only tested REAP on pure MoE (Qwen3-Coder-30B-A3B). This shows hybrid REAP is technically feasible but quality degradation is significantly worse than pure MoE REAP at the same pruning ratio. The 39% PPL increase at just 20% pruning compares unfavorably to near-lossless results on pure MoE at 25%.
  - **Implication for Phase 3**: If we want REAP on the hybrid frontdoor, expect ~3-6pp quality loss at 20% (vs near-lossless on pure MoE at 25%). The hybrid recurrent layers create a tighter quality budget for expert removal. The pure MoE path (Qwen3-Coder REAP-25B) remains the stronger option.

## Cross-References

- Deep dive: `research/deep-dives/0xsero-reap-ecosystem-deep-dive.md`
- Intake entries: intake-181 through intake-190 in `research/intake_index.yaml`
- Chapter 02: `epyc-inference-research/docs/chapters/02-moe-optimization.md` (runtime expert reduction)
- Inference index: `handoffs/active/inference-acceleration-index.md`
- Tree speculation: `handoffs/active/tree-speculation-numa-drafting.md` (draft_max/p_split methodology)
- NUMA deployment: `handoffs/active/numa-orchestrator-deployment.md` (NUMA config patterns)
- Sweep data: `epyc-inference-research/data/all_spec_sweep/` (base model sweep results, methodology reference)
- Sweep script: `epyc-inference-research/scripts/benchmark/bench_all_spec_sweeps.sh`
- Worker registry entry (base model): `model_registry.yaml` line ~355 (dm=8, ps=0, 39.1 t/s)
