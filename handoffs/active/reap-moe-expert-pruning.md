# REAP — MoE Expert Pruning Evaluation

**Status**: PHASE 1-2 + 2b(363B) COMPLETE. 25B: 39.6 t/s, 66% quality. 363B: 6.54 t/s (93% of 480B, not compelling). 246B conversion pending.
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
| Qwen3.5 hybrid? | NOT supported by REAP repo — only pure MoE layers | REAP repo deep dive |

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

#### REAP-246B (50% pruned) — PENDING

FP8 safetensors only, needs GGUF conversion. ~130 GB estimated at Q4_K_M (vs 250 GB unpruned). This is the more interesting test — 120 GB savings could enable concurrent large-model deployment.

```bash
# Download (run from host)
huggingface-cli download cerebras/Qwen3-Coder-REAP-246B-A35B-FP8 \
  --local-dir /mnt/raid0/llm/models/Qwen3-Coder-REAP-246B-A35B-FP8

# Convert to GGUF Q4_K_M
cd /mnt/raid0/llm/llama.cpp
python3 convert_hf_to_gguf.py /mnt/raid0/llm/models/Qwen3-Coder-REAP-246B-A35B-FP8 --outtype q4_k_m
```

**Evaluation plan:** Same 9-step pipeline as Phase 2b above.

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
