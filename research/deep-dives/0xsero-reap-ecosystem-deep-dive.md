# 0xSero & REAP Ecosystem — Deep Dive

**Status**: active
**Created**: 2026-03-21
**Intake IDs**: intake-181, intake-183, intake-184, intake-185, intake-186, intake-187, intake-188, intake-189, intake-190

## Scope

Deep dive on the full REAP ecosystem: the technique (Cerebras), the tooling (CerebrasResearch/reap), the community practitioner (0xSero / Sybil Solutions), the pre-pruned models (Cerebras official + bartowski GGUFs), and the extending papers (EvoESAP, Router KD, MoNE).

Excludes intake-182 (AutoRound / SignRound) — not relevant for our llama.cpp/GGUF stack.

---

## 1. REAP Core Technique (intake-181)

**Paper**: "REAP the Experts: Why Pruning Prevails for One-Shot MoE Compression"
**Citation**: arXiv:2510.13999, ICLR 2026
**Authors**: Lasby, Lazarevich, Sinnadurai, Lie, Ioannou, Thangarasa (Cerebras Systems)

### Algorithm

```
For each MoE layer:
  1. Forward calibration data (128-512 samples)
  2. Record expert activations and router gate values
  3. Score each expert: S_j = (1/|X_j|) * Σ[ g_j(x) * ||f_j(x)||_2 ]
     - g_j(x) = router gate value for expert j on input x
     - f_j(x) = expert output activation
     - |X_j| = number of tokens routed to expert j
  4. Rank experts by saliency score
  5. Remove lowest-scoring N% uniformly across all layers
```

One-shot, no fine-tuning, no gradient computation. Output is a standard HuggingFace checkpoint with fewer experts per MoE layer.

### Why Pruning Beats Merging (Theorem 1)

Merging experts (HC-SMoE, M-SMoE) creates a single expert from multiple experts. This introduces **irreducible error** proportional to `Var[r(x)]` (router policy variability) because the merged expert loses the router's ability to produce different outputs for different inputs.

Pruning preserves surviving experts unchanged → router's input-dependent control is maintained.

Evidence at 50% compression on creative writing:
- REAP: 0.718 accuracy
- HC-SMoE (merge): 0.008 accuracy (catastrophic)
- M-SMoE (merge): 0.725 accuracy (competitive on this metric, but PCA shows subspace collapse)

### Calibration Data is Critical

If calibration data lacks code → code-specialized experts appear unused → pruned → coding ability destroyed.

**0xSero's recipe** (validated across GLM-4.7, MiniMax-M2.1):
- 51% evol-codealpaca (code generation)
- 24% xlam-function-calling-60k (tool use)
- 24% SWE-smith-trajectories (agentic coding)
- Total: 1,360 samples

**Cerebras official recipe** for Qwen3-Coder:
- evol-codealpaca + XLAM function-calling + SWE-smith trajectories
- Exact proportions not published but similar focus

**For our stack**: We should build a calibration set from our actual production workload — agentic coding, tool calls, multi-turn conversations from the orchestrator.

### Quality Benchmarks

#### 25% Pruning (Near-Lossless)

| Model | Benchmark | Baseline | REAP-25% | Delta |
|-------|-----------|----------|----------|-------|
| Qwen3-Coder-30B→25B | HumanEval | 92.1 | 94.5 | **+2.4** |
| Qwen3-Coder-30B→25B | HumanEval+ | 87.8 | 89.0 | +1.2 |
| Qwen3-Coder-30B→25B | MBPP | 87.6 | 87.3 | -0.3 |
| Qwen3-Coder-30B→25B | LiveCodeBench | 35.2 | 35.2 | 0.0 |
| Qwen3-Coder-30B→25B | BFCL-v3 | 63.2 | 62.2 | -1.0 |
| MiniMax-M2 230B→172B | HumanEval | 93.9 | 93.9 | 0.0 |
| MiniMax-M2 230B→172B | AIME25 | 76.7 | 83.3 | **+6.6** |

Paper-wide mean at 25%: **-2.8% on coding** (near-lossless).

#### 50% Pruning

| Model | Task | REAP | HC-SMoE | M-SMoE |
|-------|------|------|---------|--------|
| Qwen3-30B-A3B | Coding | 0.557 | 0.379 | 0.413 |
| Qwen3-30B-A3B | Math | 0.875 | 0.728 | 0.831 |
| Qwen3-30B-A3B | Creative | 0.718 | 0.008 | 0.725 |
| Qwen3-Coder-480B | Coding retained | 97.6% | — | — |
| Qwen3-Coder-480B | SWE-Bench retained | 96.7% | — | — |

Paper-wide mean at 50%: **-8.0% on coding**.

### Practical Ceiling

- 25% = safe, near-lossless
- 50% = viable with quality trade-off, dramatically better than merging
- 80%+ = broken (0xSero's Kimi-K2.5 72-expert variant self-described as broken weights)

---

## 2. CerebrasResearch/reap Repository (intake-185)

**URL**: https://github.com/CerebrasResearch/reap
**License**: Apache 2.0

### Supported Architectures

Qwen3-Coder-480B, Qwen3-Coder-30B, Qwen3-30B-A3B, GLM-4.6, GLM-4.5-Air, Mixtral-8x7B, Kimi-K2, Kimi-Linear, Llama-4-Scout-17B, MiniMax-M2, DeepSeek-V3.2, ERNIE models.

Adding new models: map model attribute names in `src/reap/model_util.py`.

### Relevance for Us

Could run REAP ourselves on:
- Qwen3-Coder-30B-A3B (frontdoor) — already supported
- Qwen3-235B-A22B (architect_general) — likely supported (Qwen3 family)
- Qwen3-Coder-480B-A35B (architect_coding) — explicitly supported
- Qwen3.5-35B-A3B (hybrid) — MoE layers only, may need model_util mapping

---

## 3. Cerebras Pre-Pruned Models (intake-186)

### Qwen3-Coder-REAP-25B-A3B

- 128 → 103 experts (20% pruning)
- 25B total / 3B active per token
- 48 layers, 262K context (1M with YaRN)
- Architecture: `qwen3moe` (standard, no custom code)
- Apache 2.0

### Qwen3-Coder-REAP-246B-A35B-FP8

- 50% pruning of 480B (160 → 80 experts)
- Retains ~98% HumanEval (93.9 vs 95.1)
- FP8 format (GPU-oriented, not for llama.cpp)

---

## 4. bartowski GGUF Quants (intake-187)

**URL**: https://huggingface.co/bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF

**This is the fastest path to evaluation.**

| Quant | Size | Notes |
|-------|------|-------|
| Q4_K_M | 15.2 GB | Primary target for benchmarking |
| Q8_0 | 26.5 GB | Higher quality reference |
| BF16 | 49.8 GB | Full precision |

- Requires llama.cpp b6810+
- Standard `qwen3moe` architecture
- Compatible with LM Studio, Ollama, Jan, llama-server
- 31 quant variants total

### Size Comparison (estimated)

| Model | Q4_K_M Size | Active Params |
|-------|-------------|---------------|
| Qwen3-Coder-30B-A3B (base) | ~18 GB | 3B |
| Qwen3-Coder-REAP-25B-A3B | 15.2 GB | 3B |
| Delta | **-2.8 GB (-16%)** | Same |

Active params unchanged (same 8 experts selected per token, each expert same size). Total model smaller because 25 experts deleted.

---

## 5. 0xSero / Sybil Solutions (intake-183, intake-184)

### Profile

- **GitHub**: 196 repos, "Orchestrator" at Sybil Solutions
- **HuggingFace**: 28 models, 9 datasets, 216 followers
- **Focus**: Applying REAP + AutoRound to large MoE models
- **Compute sponsor**: Prime Intellect (8x H200 cluster)
- **Not the REAP author** — community practitioner

### Model Inventory Summary

| Category | Count | Base Model | Techniques |
|----------|-------|------------|------------|
| GLM-4.7 REAP (BF16) | 5 | zai/glm-4.7 (358B) | REAP 30-50% at 5% increments |
| GLM-4.7 REAP + W4A16 | 3 | zai/glm-4.7 | REAP 40-50% + AutoRound INT4 |
| GLM-4.6 REAP + W4A16 | 1 | zai-org/GLM-4.6-FP8 | REAP 40% + AutoRound |
| GLM-4.7 EXL3 | 1 | zai-org/GLM-4.7 | EXL3 3bpw (no REAP) |
| Kimi-K2.5 PRISM+REAP | 1 | moonshotai/Kimi-K2.5 | PRISM + REAP 81% (BROKEN) |
| DeepSeek-V3.2 REAP | 1 | DeepSeek-V3.2 | REAP + W3A16 |
| MiniMax-M2.1 REAP | 2 | MiniMaxAI/MiniMax-M2.1 | REAP 30-40% |
| INTELLECT-3 REAP | 1 | PrimeIntellect/INTELLECT-3 | REAP 50% |
| Nemotron-3 Super | 5 | NVIDIA Nemotron-3-Super-120B | REAP 25-50% + AutoRound (all DRAFT) |
| GLM-4.7-Flash fine-tunes | 5 | GLM-4.7-Flash (30B) | SFT, DPO, GRPO, tools |
| NousCoder-14B fine-tunes | 3 | NousResearch/NousCoder-14B | QLoRA SFT |

### Key Artifacts to Study

1. **GLM-4.7 REAP sweep** (30/35/40/45/50%) — systematic quality degradation curve at 5% increments
2. **Calibration datasets** — `glm47-reap-calibration-v2` (1,360 samples), `glm47-reap-calibration-code-func` (1,030 samples), `glm47-reap-calibration-mix` (999 samples) — different calibration mixes for different use cases
3. **MiniMax-M2.1 stress test methodology** — 24/24 tests passed at 30% and 40%, failed at 50%
4. **Double compression pipeline** — REAP 50% + AutoRound W4A16 = ~6.5x total compression (700GB → 92GB)
5. **Performance data** — GLM-4.7-REAP-218B-A32B-W4A16: 375 tok/s prefill, 38.5 tok/s gen on 8x RTX 3090

### Most Popular Model

`GLM-4.7-REAP-218B-A32B-W4A16` (212 HF likes, ~108 GB) — the "sweet spot" of 40% pruning + INT4 quant.

---

## 6. EvoESAP: Non-Uniform Expert Pruning (intake-188)

**Paper**: arXiv:2603.06003 (March 2026)

### Core Insight

REAP prunes uniformly — same percentage of experts removed from every layer. But different layers have different redundancy profiles. Some layers have many redundant experts, others have highly specialized experts that should be preserved.

EvoESAP:
1. Uses REAP (or any saliency metric) for **within-layer** expert ranking
2. Uses **evolutionary search** for **across-layer** budget allocation
3. Result: non-uniform pruning where some layers keep 90% of experts, others keep 30%

### Results

+19.6% on MATH-500 at 50% sparsity over uniform baselines. This is a significant quality recovery at aggressive compression levels.

### Relevance

- Not relevant at 25% pruning (already near-lossless)
- Highly relevant if we push to 50% — could recover most of the 8% quality loss
- Compatible with REAP as the base ranking criterion

---

## 7. Router Knowledge Distillation (intake-189)

**Paper**: arXiv:2603.02217 (February 2026)

### Problem

When REAP removes experts, the router is unchanged. But the router was trained with all 128 experts — it may still try to route tokens to patterns that no longer have matching experts. This "router-expert mismatch" wastes routing decisions.

### Solution

Lightweight distillation: train only the router weights of the pruned model to match the original model's next-token distribution. This is much cheaper than full fine-tuning (router is tiny vs expert FFNs).

### Relevance

- Larger gains on fine-grained MoEs (many small experts) — Qwen3's 128 experts is exactly this category
- Post-processing step after REAP, relatively cheap
- Most valuable at 50% pruning where routing mismatch is worst

---

## 8. MoNE: Novice Expert Replacement (intake-190)

**Paper**: arXiv:2507.00390 (ICLR 2026)

### Approach

Instead of removing experts entirely (REAP) or merging them (HC-SMoE), MoNE:
1. Identifies redundant experts via access frequency + output variance
2. Replaces them with tiny "novice" networks that approximate the original expert's output
3. Maintains model topology (same number of expert slots)

### Trade-offs vs REAP

| | REAP | MoNE |
|---|---|---|
| Memory savings | Full (expert weights removed) | Partial (novice weights smaller but present) |
| Quality | Near-lossless at 25% | 0.14 performance drop at 25% |
| Complexity | Simple (one-shot prune) | More complex (train novice networks) |
| Router change | None needed | None needed |

### Relevance

Lower priority for us — we want actual memory reduction (REAP). MoNE's novice weights still consume RAM. But worth tracking as the field evolves.

---

## Evaluation Plan

### Phase 1: Benchmark REAP-25B (immediate)

```
1. Download bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF Q4_K_M
2. Run via llama-server (check llama.cpp version ≥ b6810)
3. Benchmark with run_benchmark.py against base Qwen3-Coder-30B-A3B Q4_K_M
4. Compare: speed (t/s), quality (Claude-as-Judge 0-3), memory usage
```

### Phase 2: Stacking tests

```
1. REAP-25B + runtime expert reduction (--override-kv n_expert=4)
2. REAP-25B + NUMA 4-way (4×48t, should be trivial at 15 GB)
3. REAP-25B + draft_max 32
```

### Phase 3: Aggressive compression (if Phase 1 positive)

```
1. Run REAP ourselves at 50% on Qwen3-Coder-30B-A3B
2. Test with EvoESAP non-uniform allocation
3. Apply Router KD post-processing
4. Benchmark all variants
```

---

## References

| ID | URL | Type |
|----|-----|------|
| intake-181 | https://arxiv.org/abs/2510.13999 | REAP paper |
| intake-183 | https://github.com/0xsero | 0xSero GitHub |
| intake-184 | https://huggingface.co/0xSero | 0xSero HuggingFace |
| intake-185 | https://github.com/CerebrasResearch/reap | REAP repo |
| intake-186 | https://huggingface.co/cerebras/Qwen3-Coder-REAP-25B-A3B | Pre-pruned model |
| intake-187 | https://huggingface.co/bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF | GGUF quants |
| intake-188 | https://arxiv.org/abs/2603.06003 | EvoESAP paper |
| intake-189 | https://arxiv.org/abs/2603.02217 | Router KD paper |
| intake-190 | https://arxiv.org/abs/2507.00390 | MoNE paper |

---

## Deep Dive Findings (2026-03-21)

### Critical Discovery: The Goldilocks Zone (30-40% Pruning)

From 0xSero's MiniMax-M2.1 stress tests across 4 temps × 6 prompt types:

| Pruning | Experts Kept | Loops | Status |
|---------|-------------|-------|--------|
| REAP-20 | 204/256 | **1** | Deprecated |
| REAP-30 | 180/256 | 0 | Recommended |
| REAP-40 | 154/256 | 0 | Recommended |
| REAP-50 | 128/256 | **2** | Deprecated |

**Non-obvious**: 20% pruning was WORSE than 30%. Hypothesis: 20% removes just enough experts to destabilize routing without triggering clean redistribution, while 30% forces the router to fully adapt. Low temperature (0.0-0.2) exposes loop failures; temp ≥ 0.7 masks them. `math_word` prompts are most vulnerable.

### Cerebras REAP Model Inventory (30 models)

Cerebras has published **30 official REAP models** across 7 model families:

| Family | Models | Pruning Levels |
|--------|--------|---------------|
| Qwen3-Coder | 5 | 20% (30B→25B), 25%/50% (480B→363B/246B) |
| DeepSeek-V3.2 | 2 | 25%, 50% |
| Kimi-Linear | 1 | 30% |
| MiniMax M2/M2.1/M2.5 | 7 | 25%, 30%, 40% |
| GLM-4.5/4.6/4.7 | 12 | ~21%, ~26%, ~36% |
| Step-3.5-Flash | 2 | 25%, 40% |
| GLM-4.5-Air | 1 | unknown % |

Notable: 480B at 25% **outperforms base on 6/14 benchmarks** (tau2-bench all domains +1.8-2.9 pts).

### Qwen3-Coder-REAP-25B-A3B: Full Benchmarks

```
┌──────────────────────────────┬───────────┬──────────┬─────────┐
│ Benchmark                    │ Base 30B  │ REAP 25B │ Delta   │
├──────────────────────────────┼───────────┼──────────┼─────────┤
│ HumanEval                    │ 92.1      │ 94.5     │ +2.4    │
│ HumanEval+                   │ 87.8      │ 89.0     │ +1.2    │
│ MBPP                         │ 87.6      │ 87.3     │ -0.3    │
│ MBPP+                        │ 73.5      │ 72.8     │ -0.7    │
│ LiveCodeBench                │ 35.2      │ 35.2     │  0.0    │
│ BFCL-v3 Overall              │ 63.2      │ 62.2     │ -1.0    │
│ BFCL-v3 Multi-Turn           │ 29.6      │ 30.5     │ +0.9    │
│ tau2-bench Airline            │ 39.3      │ 40.7     │ +1.4    │
│ tau2-bench Retail             │ 62.6      │ 62.0     │ -0.6    │
└──────────────────────────────┴───────────┴──────────┴─────────┘
```

### bartowski GGUF Quants (26 variants)

| Quant | Size | Notes |
|-------|------|-------|
| BF16 | 49.76 GB | Full precision |
| Q8_0 | 26.46 GB | Max quant quality |
| Q6_K | 20.45 GB | RECOMMENDED |
| Q5_K_M | 17.72 GB | RECOMMENDED |
| **Q4_K_M** | **15.19 GB** | **Default, good quality — DOWNLOADED** |
| Q3_K_L | 11.90 GB | Low RAM option |
| Q2_K | 8.95 GB | Very low quality |

### REAP Repo: CLI & Practical Details

**Exact command for Qwen3-Coder-30B:**
```bash
bash experiments/pruning-cli.sh 0 \
    Qwen/Qwen3-Coder-30B-A3B-Instruct \
    reap 42 0.25 \
    theblackcat102/evol-codealpaca-v1 \
    false false false false false
```

**Qwen3.5 hybrid: NOT SUPPORTED.** Only `Qwen3MoeForCausalLM` in model registry. Would need custom model_util mapping, and only MoE layers (~25% of model) would be pruned.

**Output**: Standard HuggingFace safetensors → direct `convert_hf_to_gguf.py` works.
**Hardware**: `device_map="auto"`, ~1x 80GB GPU for 30B model.

### EvoESAP: Downgraded Relevance for Our Stack

For **Qwen3 + REAP specifically**, EvoESAP gains are negligible:
- 25%: EvoESAP **hurts** (Code Avg 0.580 vs 0.629 uniform REAP)
- 50%: Modest +0.010 Code Avg
- The headline +19.6% MATH-500 was ERNIE + Frequency criterion (weakest ranker)

REAP's uniform allocation is already near-optimal for Qwen3 architecture. EvoESAP adds 5h search cost for minimal gain.

### Router KD: Tested Directly on Our Model

Tested on Qwen3-30B-A3B at 62.5% retention (128→80 experts):
- 16/25 benchmarks improved after Router KD
- Gains are modest for REAP (already routes well)
- **Cost: ~2h on A100, 3000 samples, 0.04% of params updated**
- Much larger gains for weaker compression methods (CFES, MoBE)
- Fine-grained MoEs (128 experts = 1.43T routing combos) benefit most

**Verdict**: Not needed at 25% pruning. Worth 2h investment at 50%.

### MoNE: Lower Priority Than Initially Assessed

- Novices are constant vectors (mean expert output), not learned networks
- Memory savings essentially identical to REAP (expert FFN weights removed)
- **No REAP comparison in the paper** — only compared against RS, Angular, FLAP, MC-SMoE
- Only tested on models up to 16B
- The "0.14 drop at 25%" claim was not from this paper (correction)

### Calibration Data Recipe

**0xSero's validated recipe (1,360 samples):**

| Dataset | Samples | % | Purpose |
|---------|---------|---|---------|
| evol-codealpaca-v1 | 700 | 51% | Code generation |
| xlam-function-calling-60k | 330 | 24% | Tool/function calling |
| SWE-smith-trajectories | 330 | 24% | Agentic multi-turn |

**For our stack**: Should build custom calibration from production orchestrator workload (agentic coding + tool calls + multi-turn).

### Revised Evaluation Plan

Based on deep dive findings:

**Phase 1: Benchmark REAP-25B Q4_K_M** (READY — model downloaded)
```
1. Start llama-server with REAP-25B Q4_K_M (15.19 GB)
2. Run run_benchmark.py against base Qwen3-Coder-30B-A3B Q4_K_M
3. Compare: speed (t/s), quality (Claude-as-Judge 0-3)
4. Test at multiple temperatures (0.0, 0.3, 0.7) per 0xSero's methodology
```

**Phase 2: NUMA + Expert Reduction Stacking**
```
1. REAP-25B + NUMA 4-way (15 GB fits trivially in quarter-machine)
2. REAP-25B + runtime expert reduction (103→4 active)
3. Measure quality via Claude-as-Judge at each stacking level
```

**Phase 3: Run REAP Ourselves (if Phase 1 positive)**
```
1. Run REAP at 25%, 30%, 40% on Qwen3-Coder-30B-A3B
2. Use custom calibration from our production workload
3. Convert each to GGUF Q4_K_M
4. Benchmark all variants + loop detection stress test
```

**Phase 4: 50% + Router KD (if Phase 3 shows 30-40% is safe)**
```
1. REAP 50% on Qwen3-Coder-30B-A3B
2. Apply Router KD (~2h on A100, 3000 samples)
3. Convert to GGUF, benchmark
```
