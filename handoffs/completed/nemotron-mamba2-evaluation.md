# Nemotron-Cascade 2 (Mamba2 MoE) — Production Evaluation

**Status**: EVALUATION COMPLETE — **NO DEPLOYMENT ACTION**. Fast (40.9 t/s single-inst, 51.1 agg at 2×48t) but 69% quality vs worker's 78%. Instruction precision 42% disqualifies from any role requiring format compliance. Strong on math (87%) and planning/agentic (90%) but worker already covers these at similar speed with better overall quality.
**Created**: 2026-03-28
**Updated**: 2026-03-29
**Priority**: CLOSED — no deployment action, GGUF retained for reference
**Blocked by**: Nothing
**Blocks**: Nothing
**Related**: [`ssm-hybrid-acceleration.md`](ssm-hybrid-acceleration.md), [`inference-acceleration-index.md`](inference-acceleration-index.md), [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md)

---

## Motivation

Colleague field report (intake-237) benchmarked Nemotron-Cascade 2 (Mamba2 30B-A3B) vs our production frontdoor Qwen3.5-35B-A3B (Delta Net) on RTX 3090:

| Model | Architecture | GPU Speed | Context Range | Flags |
|-------|-------------|-----------|---------------|-------|
| Nemotron-Cascade 2 (30B-A3B) | Mamba2 hybrid MoE | **187 t/s** | 4K-625K flat | `-ngl 99 -np 1` |
| Qwen3.5-35B-A3B | Delta Net hybrid MoE | **112 t/s** | 4K-262K flat | `-ngl 99 -np 1 -c 262144 --cache-type-k q8_0 --cache-type-v q8_0` |

- **67% speed advantage** for Mamba2 at same active parameter count (3B)
- Nemotron needs **no KV cache flags** — auto-allocates 625K context
- Both show **flat (context-independent) generation speed**
- Nemotron quality: IMO gold (35pts), AIME 92.4, IOI gold (439.3), ICPC gold (10/12)

**Key question**: Does the GPU speed advantage translate to our EPYC 9655 CPU stack?

---

## Architecture Comparison

| Property | Qwen3.5-35B-A3B (Delta Net) | Nemotron-Cascade 2 (Mamba2) |
|----------|----------------------------|------------------------------|
| Total params | 35B | 30B |
| Active params | ~3B (MoE) | ~3B (MoE) |
| Recurrent type | Delta Net (gated linear attention) | Mamba2 (selective SSM) |
| Recurrent fraction | 75% (30/40 layers) | ~75% (hybrid) |
| Attention layers | 25% (10/40) | ~25% (interleaved) |
| Expert count | 256 × 512 FFN | MoE (details in arxiv 2603.19220) |
| Context window | 262K | 262K (paper), 625K demonstrated |
| SSM state size | ~62 MiB (Delta Net outer-product) | TBD (Mamba2 discrete state) |
| llama.cpp arch | `delta-net-base.cpp` | `nemotron-h.cpp` → `mamba-base.cpp` |
| SSM op | Custom Delta Net recurrence | `ggml_ssm_scan()` |
| License | Apache 2.0 | NVIDIA Open Model License |

### Why CPU Performance May Differ From GPU

On GPU, Mamba2's parallel scan is highly efficient (hardware-friendly). On CPU:
- Mamba2's `ggml_ssm_scan()` runs sequentially per token (same as Delta Net)
- The recurrent state update costs differ: Mamba2 discrete state vs Delta Net outer-product
- MoE routing overhead depends on expert granularity (unknown for Nemotron vs Qwen3.5's 256×512)
- NUMA sensitivity pattern may differ — Qwen3.5-35B-A3B showed 6.9x with 4×48t due to low active params

**The GPU advantage may partially survive on CPU** if Mamba2's recurrent state update is cheaper than Delta Net's, but it could also evaporate if the bottleneck is the same (sequential recurrent layers dominating).

---

## llama.cpp Support Status

**FULLY SUPPORTED.** Verified 2026-03-28:

| Aspect | Status | Details |
|--------|--------|---------|
| Mamba2 layer | ✅ | `build_mamba2_layer()` in `src/models/mamba-base.cpp` |
| Mamba2 MoE arch | ✅ | `LLM_ARCH_NEMOTRON_H_MOE` in `src/models/nemotron-h.cpp` |
| GGUF conversion | ✅ | Automatic from HuggingFace metadata |
| Known issues | ✅ Resolved | Issue #20570 (assertion error) fixed, closed 2026-03-15 |
| Our fork | ✅ | `/mnt/raid0/llm/llama.cpp` has full Nemotron-H support |

### Available GGUFs

| Source | Quantizations | Notes |
|--------|--------------|-------|
| `bartowski/nvidia_Nemotron-Cascade-2-30B-A3B-GGUF` | Multiple | Trusted community converter |
| `mradermacher/Nemotron-Cascade-2-30B-A3B-GGUF` | Static quants | |
| `mradermacher/Nemotron-Cascade-2-30B-A3B-i1-GGUF` | imatrix quants | Preferred for quality |

**Target quant**: Q4_K_M (matches our Qwen3.5-35B-A3B production config). Estimated size: ~17-19 GB.

---

## Evaluation Plan

### Phase 1: Download & Smoke Test — COMPLETE (2026-03-28)

Downloaded `bartowski/nvidia_Nemotron-Cascade-2-30B-A3B-GGUF` Q4_K_M.

```
/mnt/raid0/llm/models/nemotron-cascade-2/nvidia_Nemotron-Cascade-2-30B-A3B-Q4_K_M.gguf  (24 GB)
```

**Smoke test results:**
- Arch: `nemotron_h_moe` — loads correctly, 52 layers, 31.58B params
- 128 experts, 6 active per token, 1 shared expert (FFN 3712)
- Only **6 attention layers** out of 52 (layers 5, 12, 19, 26, 33, 42) — **88% Mamba2** (vs Qwen3.5's 75% Delta Net)
- KV cache: 24 MB (tiny — only 6 attention layers × 2 KV heads each)
- Mamba2 recurrent state: 190 MB (d_inner=4096, d_state=128, 8 groups)
- Tokenizer: `tekken` (Mistral-family) — **NOT compatible with Qwen drafters**
- Output: high quality code generation, thinking tags present
- File size: 23.02 GiB (6.26 BPW) — **4 GB larger than Qwen3.5-35B Q4_K_M (20 GB)**

### Phase 2: CPU Benchmark — Head-to-Head vs Qwen3.5-35B-A3B — COMPLETE (2026-03-28)

All tests on EPYC 9655 (192 threads, 2 NUMA nodes × 96 cores), Q4_K_M. 512 max_tokens, 10 samples per config (3 warmup).

| Test | Config | Nemotron t/s | Qwen3.5 t/s | Delta | Notes |
|------|--------|-------------|-------------|-------|-------|
| A: 192t interleave | `numactl --interleave=all -t 192` | **19.4** | 7.25 | **+167%** | High variance (16.7-24.9) |
| B: 96t node0 | `taskset -c 0-95 -t 96` | **38.7** | 13.39 | **+189%** | Very consistent (36.8-39.2) |
| C: 48t quarter | `taskset -c 0-47 -t 48` | **40.6** | ~12.4 | **+227%** | Best single-instance config |
| D: NUMA 4-way | 4×48t concurrent | **41.7 agg** | 49.7 agg | **-16%** | Per-instance: ~10 t/s (down from 40.6) |

**NUMA Scaling Analysis (8 rounds per config, 2 warmup):**

| Config | N | Agg t/s | Per-inst t/s | Efficiency | Notes |
|--------|---|---------|-------------|------------|-------|
| 1×48t (baseline) | 1 | 40.9 | 40.9 | 100% | Very consistent (40.2-41.1) |
| **2×48t (same NUMA node)** | 2 | **51.1** | 25.6 | 63% | **Best aggregate — beats Qwen3.5 4×48t (49.7)** |
| 2×96t (cross-NUMA) | 2 | 35.6 | 17.8 | 43% | Wild variance (21-53 t/s), cross-NUMA kills perf |
| 4×48t (all quarters) | 4 | 40.6 | 10.2 | 25% | Compounds intra + cross-NUMA contention |

**Key findings:**

1. **Single-instance: Nemotron dominates.** 3.3x faster than Qwen3.5 at 48t. Mamba2 is significantly more compute-efficient on CPU — fewer attention layers (6 vs 10), smaller KV cache (24 MB vs ~640 MB).

2. **2×48t is the sweet spot.** Two instances on the same NUMA node yield **51.1 t/s aggregate** — beating Qwen3.5's 4×48t (49.7 t/s) while using **only half the CPU cores**. The other 96 cores are free for architect/coder models.

3. **Cross-NUMA is the killer, not instance count.** 2×48t same-NUMA (51.1) vs 2×96t cross-NUMA (35.6) — same instance count, 43% less throughput. The mmap'd model copies fight over cross-NUMA memory access. The 4-way config compounds both intra-NUMA and cross-NUMA contention.

4. **Why Qwen3.5 scales better at 4-way**: Qwen3.5 at 12.4 t/s per instance demands ~3x less memory bandwidth than Nemotron at 40.6 t/s. At 4 instances, Qwen3.5 needs ~50 t/s worth of bandwidth vs Nemotron needing ~160 t/s. The bandwidth ceiling catches Nemotron but not Qwen3.5.

5. **Speculation NOT viable**: Tokenizer is `tekken` (Mistral-family), incompatible with all Qwen drafters. No Nemotron-family draft models at 0.5-1B scale.

**Verdict: FRONTDOOR CANDIDATE with 2×48t deployment.** Deploy 2 instances on one NUMA node (cores 0-47 + 48-95) with round-robin routing. Aggregate throughput 51.1 t/s beats Qwen3.5's 49.7 t/s. Frees 96 cores (NUMA node 1) for architect/coder models — potentially a net stack improvement. **Pending: quality benchmark (Phase 3).**

**Data**: `epyc-inference-research/data/nemotron_cascade2/`

### Phase 3: Quality Benchmark — RESPONSES COLLECTED (2026-03-28), JUDGING PENDING

Ran `run_benchmark.py --model nemotron_cascade_2 --server-mode --force`. 59 tests completed (1 context overflow at 80K tokens, 3 lookup UTF-8 errors — irrelevant). Responses saved to `benchmarks/results/runs/20260326_150453/nemotron_cascade_2_baseline.json`.

**Response statistics (no truncation, full generation):**

| Suite | Questions | Avg Tokens | Avg t/s |
|-------|-----------|-----------|---------|
| math | 10 | 2089 | 38.5 |
| general | 10 | 2696 | 38.4 |
| coder | 10 | 3032 | 38.5 |
| instruction_precision | 11 | 320 | 39.1 |
| agentic | 10 | 990 | 38.8 |
| long_context | 8 | 2546 | 33.7 |

**Qualitative spot-check**: Responses appear high quality — math uses proper LaTeX + complex analysis proofs, coder tackles ABA problem with detailed fix, agentic produces structured JSON tool calls. No truncation issues (unlike REAP-25B which was limited to 256 tokens).

**Claude-as-Judge scores (2026-03-29):**

| Suite | Nemotron | Qwen3.5 (frontdoor) | REAP-246B | Notes |
|-------|----------|---------------------|-----------|-------|
| agentic | **27/30 (90%)** | 27/30 (90%) | 27/30 (90%) | Tied — all three excel |
| coder | 24/30 (80%) | **25/30 (83%)** | 21/30 (70%) | Nemotron close to Qwen3.5 |
| general | 21/30 (70%) | **27/30 (90%)** | 18/30 (60%) | Nemotron weak — hallucinations on JSON/compare tasks |
| instruction_precision | 14/33 (42%) | **25/33 (76%)** | 20/33 (61%) | **Nemotron's worst suite** — fails to follow simple constraints (NONE, self-referential, meta-instruction) |
| math | **26/30 (87%)** | 20/30 (67%) | 25/30 (83%) | **Nemotron's best** — beats both on math. Qwen3.5 truncated heavily on math. |
| long_context | 11/24 (46%) | — | — | Hallucinations on multi-hop/contradiction tasks. Not tested on other models. |
| **TOTAL** | **123/177 (69%)** | **151/183 (83%)** | **132/183 (72%)** | |
| **Pass (≥2)** | **42/59 (71%)** | **50/61 (82%)** | **47/61 (77%)** | |

**Key quality issues:**
1. **Instruction precision is catastrophic (42%)** — model frequently ignores simple format instructions (output NONE, no extra text, execute bracketed instructions). It deliberates about constraints instead of following them. This is a dealbreaker for frontdoor use where format compliance is critical for tool-call routing.
2. **General knowledge weaker (70% vs 90%)** — hallucinates on JSON extraction (generates new people not in prompt), gets stuck deliberating on synthesis/scheduling tasks.
3. **Math is excellent (87% vs 67%)** — best of all three models. Produces complete proofs where Qwen3.5 truncated.
4. **Agentic is tied at 90%** — strong tool-call generation, correct JSON formatting.
5. **Long-context is poor (46%)** — hallucinates scenarios instead of analyzing provided documents on T2-T3 difficulty questions.

**Comparison vs worker (Qwen3-Coder-30B-A3B, the try-cheap-first candidate):**

| Suite | Nemotron | Worker (30B-A3B) | Delta |
|-------|----------|------------------|-------|
| agentic | 90% | **93%** | -3pp |
| coder | 80% | **100%** | -20pp |
| general | 70% | **77%** | -7pp |
| instruction_precision | 42% | **73%** | -31pp |
| math | 87% | 87% | tied |
| thinking | — | **100%** | — |
| **TOTAL** | **69%** | **78%** | **-9pp** |

Worker dominates: 9pp better overall, perfect coder (100%), 31pp better instruction precision, and similar speed (39.1 vs 40.9 t/s single-instance). Worker also scales to 4×48t (~156 t/s aggregate) and supports speculative decoding.

**Final verdict: NO deployment action.** Nemotron does not replace any current stack role:
- **Not frontdoor**: 69% vs 83% quality, 42% instruction precision disqualifying
- **Not worker**: 69% vs 78% quality, coder 80% vs 100%, similar speed
- **Not math specialist**: tied with worker at 87%, but worker has 100% coder + 100% thinking as bonus
- **Agentic/planning strength (90%)** is real but worker matches at 93%

The core weakness is **deliberation instead of execution** — Nemotron analyzes constraints and instructions rather than following them, wasting tokens on meta-reasoning. This manifests as 42% instruction precision and hallucinations on general/long-context tasks where it generates its own scenarios instead of processing provided content.

### Phase 4: Production Viability Assessment

If Phases 2-3 show Nemotron is competitive:
1. Memory footprint comparison (Q4_K_M size, RSS, mmap behavior)
2. MoE acceleration compatibility (`--moe-n-expert` override)
3. Speculation compatibility (freeze-recurrent, external draft)
4. NUMA sensitivity pattern (does it show the same 6.9x as Qwen3.5-35B-A3B?)
5. Context window behavior at 32K, 64K, 128K
6. Batch inference behavior (does Mamba2 have the same batched-verify wall as Delta Net?)

### Phase 5: Stack Replacement Decision

Decision matrix (2026-03-29, final with quality scores):

| Factor | Weight | Qwen3.5-35B-A3B (4×48t) | Nemotron-Cascade 2 (2×48t) | Winner |
|--------|--------|--------------------------|---------------------------|--------|
| CPU throughput (production) | 0.30 | 49.7 t/s (4×48t) | **51.1 t/s (2×48t)** | **Nemotron** |
| Quality (benchmark suite) | 0.30 | **83% (151/183)** | 69% (123/177) | **Qwen3.5** |
| Instruction compliance | — | **76%** | 42% | **Qwen3.5** (dealbreaker) |
| Memory footprint | 0.10 | 20 GB × 4 = 80 GB mmap | **24 GB × 2 = 48 GB mmap** | **Nemotron** |
| CPU cores used | — | 192 (all) | **96 (half)** | **Nemotron** |
| Context handling | 0.10 | 262K (needs q8_0 KV) | **625K (no KV flags)** | **Nemotron** |
| Speculation compat | 0.10 | freeze-recurrent +5.4% | none (tekken tokenizer) | **Qwen3.5** |
| License compatibility | 0.10 | **Apache 2.0** | NVIDIA Open Model | **Qwen3.5** |

**Result: NO DEPLOYMENT ACTION.** Does not replace any stack role. Worker (Qwen3-Coder-30B-A3B) is 9pp better quality at similar speed with 4×48t NUMA scaling and spec decode support. GGUF retained at `/mnt/raid0/llm/models/nemotron-cascade-2/` for future reference.

**Architectural takeaway**: Mamba2 is compute-efficient on CPU (3.3x faster single-instance than Delta Net) but bandwidth-hungry under concurrent load. The 2×48t sweet spot (51.1 t/s on one NUMA node) is a useful deployment pattern if a future Mamba2 model has better instruction-following quality.

---

## Speculation Implications

**Scaling analysis reveals 2×48t as optimal.** Nemotron's NUMA degradation is specifically a **cross-NUMA** problem, not a multi-instance problem. Two instances on the same NUMA node retain 63% efficiency (25.6 t/s each), while cross-NUMA drops to 43% (17.8 t/s). The 4-way config compounds both.

The 2×48t deployment (51.1 t/s aggregate on one NUMA node) is viable and **beats Qwen3.5's 4×48t** (49.7 t/s on all cores). This changes the architecture: instead of spreading frontdoor across the whole machine, dedicate one NUMA node to frontdoor and free the other for heavy models.

Speculation remains blocked: `tekken` tokenizer incompatible with Qwen drafters, no Nemotron-family draft models at 0.5-1B.

**Conclusion**: Mamba2's compute efficiency advantage survives on CPU when deployed within a single NUMA node. The key insight is to **match deployment topology to the model's bandwidth profile** rather than defaulting to maximum parallelism.

---

## References

- arxiv 2603.19220 — Nemotron-Cascade 2 paper (NVIDIA, released 2026-03-19)
- intake-237 — Field report: GPU benchmark comparison
- intake-238 — Paper intake entry
- [NVIDIA Research page](https://research.nvidia.com/labs/nemotron/nemotron-cascade-2/)
- GitHub: ggml-org/llama.cpp issue #20570 (Mamba2 assertion fix, resolved)
- GitHub: ggml-org/llama.cpp PR #15507 (Nemotron-H architecture support)
