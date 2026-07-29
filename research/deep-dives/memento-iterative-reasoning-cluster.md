# Deep Dive: Memento & Iterative Reasoning Compression Cluster

**Date**: 2026-04-09
**Intake IDs**: intake-289 (Memento), intake-290 (OpenMementos), intake-291 (Rowboat), intake-292 (InftyThink), intake-293 (InftyThink+), intake-294 (Accordion-Thinking)

---

## Executive Summary

Six entries forming two clusters:

**Cluster A — Iterative Reasoning Compression** (intake-289, 290, 292, 293, 294): A family of techniques that train models to segment their own reasoning into blocks, compress each block into a dense summary, and continue reasoning from summaries alone. Memento is the strongest entry (dual information stream via KV retention, 2-3x peak KV reduction, RL-enabled accuracy recovery). InftyThink (ICLR 2026) and Accordion-Thinking are the key predecessors; InftyThink+ adds RL. All four address the same fundamental bottleneck: unbounded reasoning chains consume linear KV cache and quadratic attention cost.

**Cluster B — Agent Knowledge Graph** (intake-291): Rowboat is a reference implementation for knowledge-graph-backed agent memory with MCP integration. Tangentially related to our agent architecture work.

---

## Cluster A: Iterative Reasoning Compression

### Comparative Architecture Analysis

| Feature | InftyThink | InftyThink+ | Accordion-Thinking | Memento |
|---------|------------|-------------|-------------------|---------|
| **Context rebuild** | Text-level restart (separate gen calls) | Text-level restart | Text-level, single-pass mid-generation | In-engine KV masking (single gen call) |
| **KV retention** | No — discards KV + text | No — discards KV + text | No — discards KV + text | **Yes — retains memento KV states** |
| **Training** | SFT only | SFT + trajectory-level RL | SFT cold-start + GRPO RL | SFT (2-stage) + CISPO RL |
| **Boundary learning** | Fixed η parameter | RL-learned adaptive | RL-learned dynamic | LLM-scored boundaries + algorithmic optimization |
| **Model scales** | 1.5B–32B | 1.5B, 4B | 4B, 7B | 8B, 14B, 32B (+ 7B Olmo) |
| **Compression ratio** | ~2x context per iteration | ~2x context per iteration | |si| << |di| per step | ~6x trace-level (1150→194 tokens/block) |
| **Throughput gain** | Reduced latency (30-40%) | Reduced latency (30-70%) | 3x throughput on 48GB GPU | 1.75x throughput on B200 |
| **Dual stream** | No | No | No | **15pp accuracy drop without KV channel** |
| **Venue/status** | ICLR 2026 | arXiv Feb 2026 | arXiv Feb 2026 | arXiv 2026, Microsoft Research |

### The Dual Information Stream: Key Differentiator

Memento's most important finding is that KV cache states computed while a block is visible carry **implicit information** beyond what the summary text captures. This was demonstrated via:

1. **KV Ablation**: Recomputing memento KVs without block context drops AIME24 accuracy from 66.1% → 50.8% (-15.3pp). Same text, different KV states, massive accuracy difference.

2. **Probing Experiment**: Injecting a random 5-digit passcode into a masked block, then probing downstream memento KV states:
   - **Direct** (memento that attended to block): 60-70% recovery (vs 10% chance)
   - **Masked** (memento that never attended to block): 23-27% recovery — information propagates through memento chain
   - **Causal control** (memento before block): 10% (chance) — confirms signal is real
   - Signal concentrates in **deeper layers** (26.5% at layer 36 vs 10.8% at layer 4 for Qwen3-8B)

3. **Toy transformer validation**: 4-layer model shows same pattern — 24.9% masked accuracy, signal decays over distance but persists up to 7 hops. Channel is **architectural, not learned**.

**EPYC Implication**: This means text-level compression (InftyThink, Accordion-Thinking, and our context-folding) has a fundamental 15pp ceiling vs. KV-retaining approaches. For reasoning-heavy workloads, KV masking is strictly superior to context restarting. However, our production stack uses llama.cpp (not vLLM), so we'd need to implement block masking there.

### Detailed Benchmark Comparison

#### Memento — Across Model Families

| Model | Benchmark | Base | Control | Memento | Mem+RL | Δ Mem vs Ctrl | Peak KV ratio |
|-------|-----------|------|---------|---------|--------|---------------|---------------|
| Qwen3-8B | AIME'26 | 66.8 | 64.7 | 57.3 | 64.9 | -7.4 / +0.2 | 0.39x |
| Qwen3-8B | MATH-500 | 90.5 | 89.7 | 90.1 | 91.0 | +0.4 / +1.3 | 0.47x |
| Qwen3-8B | GPQA-D | 61.4 | 57.8 | 55.8 | 62.9 | -2.0 / +5.1 | 0.35x |
| Qwen3-8B | LCB v6 | 73.1 | 70.0 | 66.5 | 68.8 | -3.5 / -1.2 | 0.32x |
| Phi-4-r 14B | AIME'26 | 71.7 | 69.8 | 67.6 | — | -2.2 | 0.38x |
| Phi-4-r 14B | GPQA-D | 64.1 | 64.1 | 61.6 | — | -2.5 | 0.38x |
| Qwen3-32B | AIME'26 | 75.2 | 74.1 | 72.6 | — | -1.5 | 0.44x |
| Qwen3-32B | MATH-500 | 91.9 | 91.8 | 91.1 | — | -0.7 | 0.47x |
| Qwen3-32B | GPQA-D | 65.9 | 64.6 | 62.1 | — | -2.5 | 0.44x |
| Olmo-3 7B | AIME'26 | 67.9 | 59.8 | 55.4 | — | -4.4 | 0.91x* |

*Olmo-3 has sliding-window attention (24/32 layers), limiting KV savings to 8 full-attention layers.

Key observations:
- **MATH-500 is near-lossless** across all models (gap <1pp)
- **Competition math is hardest** — 2-7pp drops, consistent with reasoning compression literature
- **Scale helps**: -6.3pp average at 8B → -3.5pp at 32B
- **RL recovers**: Qwen3-8B Mem+RL matches or beats Control on 3/5 benchmarks
- **Majority voting at k=3 recovers base accuracy** even without RL — gap is consistency, not capability

#### InftyThink+ — Best Results (DeepSeek-R1-Distill-Qwen-1.5B)

| Setting | MATH500 | AIME24 | AIME25 | GPQA-D | Avg |
|---------|---------|--------|--------|--------|-----|
| Vanilla SFT | 86.2 | 26.7 | 24.5 | 29.4 | 41.7 |
| Vanilla + RL | 89.6 | 38.8 | 31.0 | 29.8 | 47.3 |
| InftyThink+ SFT | 86.5 | 29.5 | 27.9 | 32.3 | 44.1 |
| InftyThink+ RL (task) | **91.6** | **50.9** | **35.8** | **37.5** | **54.0** |
| InftyThink+ RL (task+efficiency) | 90.0 | 44.0 | 32.9 | 35.5 | 50.6 |

- +21pp on AIME24 vs SFT baseline — the largest single improvement in this cluster
- Task+efficiency RL trades 3.4pp accuracy for 60-70% latency reduction
- Latency: 77.6s → 48.4s average (task+efficiency RL vs SFT)
- Training speedup: 25-40% faster RL steps than vanilla

#### Accordion-Thinking — Best Results (Qwen2.5-Math-7B)

| Method | AIME24 | AIME25 | MATH500 | AMC | Minerva | Macro |
|--------|--------|--------|---------|-----|---------|-------|
| Zero-RL Unfold | 25.8 | 18.1 | 82.2 | 58.9 | 37.8 | 44.6 |
| Cold-Start Fold | 23.0 | 23.1 | 82.3 | 62.4 | 37.6 | 45.7 |
| Fold-RL Fold | 31.3 | 26.9 | 89.9 | 73.8 | 42.0 | 52.7 |
| Mix-RL Fold | **32.2** | **28.3** | 89.6 | 71.9 | 41.8 | **52.8** |

- Fold-RL **matches** Unfold-RL accuracy (52.7 vs 52.2 macro) — gap vanishes with RL
- Throughput: 5,888 tok/s Fold vs 1,483 tok/s Unfold on 48GB GPU (**4x**)
- Works on both 4B and 7B models

### Opportunity Analysis: What We Missed in Initial Intake

#### Opportunity 1: Memento's Coverage Analysis — Capability vs Consistency Gap

The Memento paper shows **pass@64 Jaccard similarity of 96.4%** between Base and Memento solved sets. The accuracy drop is a **consistency problem**, not a capability loss. This means:
- **For our stack**: At k=3 majority voting, Memento recovers base accuracy. Our orchestrator already supports multi-generation voting (`short-m@k` from intake-129). Combining Memento KV savings + m@k voting would give 2-3x KV reduction with ZERO accuracy cost.
- **Action**: If/when we deploy Memento-style models, integrate with existing `short-m@k` infrastructure rather than relying solely on RL to close the gap.

#### Opportunity 2: Block Length Capping During RL

Memento's RL uses a **7K token block cap** to prevent the model from learning to generate fewer, longer blocks (which undermines KV savings). This is directly analogous to our **reasoning length alarm** (Action 9 in reasoning-compression.md) — `_check_reasoning_length_alarm()` cancels and re-generates when `<think>` exceeds 1.5x band budget. The Memento paper validates this approach from the RL training perspective: without block caps, models learn to subvert compression.

#### Opportunity 3: InftyThink+'s Efficiency Reward — Controllable Reasoning Budget

InftyThink+ introduces a **quadratic efficiency reward**: `R_eff = (1 - (n_i - 1)/φ)²`, combined multiplicatively with task reward. This means:
- Correct solutions get efficiency bonus for using fewer iterations
- Incorrect solutions always get 0 (no premature termination incentive)
- Controls the accuracy-latency tradeoff continuously

**EPYC mapping**: This maps directly to our **difficulty-band adaptive token budgets** (Action 5 in reasoning-compression.md). The efficiency reward could parameterize our band budgets: easy→1 iteration, medium→3, hard→5. Currently we use regex-based difficulty signals; InftyThink+'s approach learns this from rewards.

#### Opportunity 4: Accordion-Thinking's Fold/Unfold Toggle

Accordion-Thinking provides a **runtime inference toggle** between compressed (Fold) and full (Unfold) modes. Same model, same weights, user chooses at request time. After RL training, **accuracy gap vanishes** — Fold matches Unfold.

**EPYC mapping**: This is the ideal interface for our routing layer. Route easy problems to Fold (3-4x throughput), hard problems to Unfold (max accuracy). The difficulty signal from our `difficulty_signal.py` classifier becomes the toggle selector. Zero accuracy cost on easy problems, full accuracy on hard ones.

#### Opportunity 5: InftyThink+'s When/How/Continue Ablation

InftyThink+ demonstrates three learned capabilities:
1. **When to compress** (Table 2): Adaptive timing beats Fixed/Random by 2-3pp after RL
2. **How to compress** (Table 3): After RL, internal summaries outperform external (GPT-4) summaries — the model learns summary strategy coupled to its own reasoning
3. **How to continue** (Figure 2): InftyThink+ models are better at leveraging their own summaries than vanilla models

**EPYC implication**: Our context-folding Phase 2 uses an external model (`worker_explore` 7B) for consolidation. InftyThink+'s finding that RL-trained internal summarization beats external summarization suggests we should eventually move summarization into the reasoning model itself, not delegate to a separate summarizer. This is a Phase 3+ consideration.

#### Opportunity 6: OpenMementos Data Pipeline as Context-Folding Training Data

The OpenMementos 5-stage pipeline (sentence splitting → boundary scoring → segmentation → summary generation → iterative refinement) is directly applicable to generating training data for our context-folding system. Specifically:

- **Boundary scoring rubric** (0-3 scale) maps to our consolidation trigger decisions
- **Iterative judge refinement** (28% → 92% pass rate, 0-10 rubric with 6 dimensions) validates our Phase 2 summarizer quality assessment approach
- **The 228K dataset itself** (MIT licensed) could be used if we fine-tune models for context-aware summarization

#### Opportunity 7: Memento + KV Quantization Composition

Memento reduces **which** KV entries exist (attention span compression). Our Hadamard+q4_0 reduces **how** each KV entry is stored (precision compression). These are orthogonal:

| Layer | Compression | Deployed? |
|-------|-------------|-----------|
| KV selection (TriAttention/Expected Attention) | Keep fewer tokens based on importance scoring | Evaluating (triattention-kv-selection.md) |
| KV quantization (Hadamard+q4_0) | Compress each token's KV to lower precision | **Production** (`b51c905`) |
| Block masking (Memento) | Remove entire reasoning blocks, retain only summaries | **New opportunity** |

Theoretical stacking: Memento 2-3x × Hadamard q4_0 2x × Selection 10x = **40-60x KV reduction**. Even conservative estimates (Memento 2x × q4_0 2x = 4x) would be transformative for our 256K context scenarios.

#### Opportunity 8: Memento's vLLM Implementation as Reference for llama.cpp

Memento's vLLM fork operates "purely at the Python level" — extends V1 engine to physically remove masked tokens from KV cache. Works with vanilla FlashAttention and FlashInfer kernels.

For llama.cpp port, the key operations are:
1. **Track block boundaries** via special tokens (`<|block_start|>`, `<|block_end|>`, `<|summary_start|>`, `<|summary_end|>`)
2. **After `<|summary_end|>`**: mark preceding block's KV entries for eviction
3. **KV eviction**: physically remove marked entries (already partially supported by llama.cpp's `llama_kv_self_seq_rm()`)
4. **Attention masking**: ensure evicted tokens don't participate in future attention (already the default behavior after removal)

Our **hybrid-precision buffer** work in `kv-cache-quantization.md` (ISWA pattern, split attention, eviction from recent→old) is architecturally similar. Block masking is actually simpler — it's straight eviction, no demotion.

**Critical path**: llama.cpp v3 upstream PR #21038 already auto-enables Walsh-Hadamard rotation. If v3 upstream also lands KV eviction API improvements (tracked in `llama-cpp-v3-upstream-rebuild.md`), block masking becomes a thin layer on top.

#### Opportunity 9: Serving Throughput Implications

Memento achieves 1.75x higher throughput (4,290 vs 2,447 tok/s) on a single B200 GPU at full concurrency. The mechanism: block masking **frees KV cache entries as blocks complete**, allowing the engine to maintain higher batch sizes. Vanilla vLLM becomes KV-cache-bound and plateaus.

For our stack (llama.cpp, single-user, 192 threads): the throughput gain mechanism is different. We're not batching, but KV cache reduction means:
- **Longer contexts fit**: 256K context with 2x KV reduction = fits in memory that previously couldn't
- **Faster generation at long contexts**: KV attention is memory-bandwidth-bound; 2x less KV = 2x less memory traffic = faster generation
- **NUMA implications**: Smaller KV cache may fit entirely in a single NUMA node's memory, avoiding cross-node access

### Failure Modes and Risks

1. **Memento's excessive generation failure** (Figure 5c): Block masking can induce 3x more tokens on some problems, increasing total memory-time cost. The model "forgets" previous dead ends and re-explores. Block length capping mitigates but doesn't eliminate.

2. **Sliding-window architecture penalty**: Olmo-3 (24/32 layers sliding window) sees only 0.85-0.93x KV savings. Our production Qwen2.5-Coder-32B uses full attention (all 64 layers), so this doesn't apply to us. But if we adopt hybrid SSM models in the future, Memento's value diminishes.

3. **SFT quality degradation**: The SFT control runs (training on OpenThoughts without block annotations) show accuracy drops even without Memento. Any SFT on already-trained reasoning models has inherent risk.

4. **Implementation complexity**: vLLM fork is "installable as a simple patch" but llama.cpp port would be a non-trivial engineering effort. Need to validate against our production binary.

---

## Cluster B: Rowboat Knowledge Graph Agent

### Architecture Summary

Rowboat operates as three independent apps:
- **Desktop (Electron)**: Local-first Markdown storage at `~/.rowboat/`, syncs Gmail/Calendar/Fireflies every 5-30 min
- **Web (Next.js + MongoDB + Redis + Qdrant)**: Team workflow orchestration with SSE streaming
- **CLI**: Headless automation

Knowledge graph: Plain Markdown files with wiki-links (`[[Person Name]]`) in entity-organized directories (People/, Organizations/, Projects/, Topics/). Graph builder polls every 30s, processes in batches of 10 via `note_creation` agent.

Agent workflow: Configurable agents with `type: conversation|pipeline|post_process|escalation`, tools via MCP servers + Composio, OpenAI Agents SDK for orchestration.

### Opportunities for EPYC

1. **Knowledge graph as agent memory**: Rowboat's Markdown+backlinks approach is simpler than our session compaction pipeline. Could inform a human-readable persistent memory layer for our orchestrator that survives across sessions (vs. our current session_log which is ephemeral).

2. **MCP integration patterns**: Rowboat's tool routing (`Router → MCP client → external server → results → agent`) maps to our hermes-outer-shell MCP integration. Their `config/mcp.json` schema could be adapted.

3. **Desktop/CLI architecture split**: Their Electron desktop + CLI headless pattern matches our hermes-agent frontend + CLI autopilot split.

4. **Limitations**: No quantization, no local model optimization, no inference parameter tuning. Vercel AI SDK abstraction hides model details. Not useful for inference optimization.

### Relevance Assessment: MEDIUM-LOW

Rowboat is a product, not research. No novel techniques. Useful as reference architecture for:
- hermes-agent MCP integration patterns
- Knowledge-graph-backed agent memory design
- Open-source orchestrator market positioning (complements our gap analysis in `open_source_orchestrator.md`)

---

## Updated Opportunity Matrix

| # | Opportunity | Source | EPYC Impact | Effort | Priority |
|---|-----------|--------|-------------|--------|----------|
| 1 | Memento + m@k voting = zero-accuracy-cost KV reduction | intake-289 | HIGH — 2-3x KV savings with no accuracy drop | Requires Memento model + llama.cpp block masking | HIGH |
| 2 | Fold/Unfold toggle via difficulty routing | intake-294 | HIGH — 3-4x throughput on easy, full accuracy on hard | Requires Accordion-style training or Memento model | HIGH |
| 3 | OpenMementos data pipeline for context-folding training data | intake-290 | MEDIUM — validated approach for Phase 2/3 data generation | Low — adapt existing pipeline | MEDIUM |
| 4 | Efficiency reward for reasoning budget control | intake-293 | MEDIUM — learned difficulty adaptation replacing regex heuristic | Requires RL training infrastructure | MEDIUM |
| 5 | KV masking + quantization + selection stacking | intake-289 + existing | HIGH — theoretical 4-60x KV reduction | Complex — needs all three layers working | MEDIUM (long-term) |
| 6 | llama.cpp block masking via existing KV eviction API | intake-289 | HIGH — enables all Memento benefits on our stack | Non-trivial but builds on ISWA work | MEDIUM |
| 7 | Internal summarizer (self-compression) > external summarizer | intake-293 | LOW (for now) — Phase 3+ consideration for context-folding | Requires model fine-tuning | LOW |
| 8 | Rowboat MCP patterns for hermes-outer-shell | intake-291 | LOW — reference architecture only | Low effort | LOW |
| 9 | Block length capping validates reasoning alarm approach | intake-289 | VALIDATION — confirms Action 9 design is correct | Already implemented | DONE |

## Recommended Action Plan

### Immediate (no new infrastructure needed)

1. **Update context-folding-progressive.md Phase 2** with OpenMementos' iterative judge-refinement approach as validation evidence (28%→92% pass rate confirms our methodology)
2. **Add Accordion-Thinking's Fold/Unfold concept to reasoning-compression.md** as a Tier 2.5 approach — same model, inference-time toggle via difficulty routing
3. **Cross-reference InftyThink+'s efficiency reward with difficulty_signal.py** — evaluate whether learned iteration budgets could replace or supplement regex-based difficulty bands

### Medium-term (requires some infrastructure)

4. **Prototype llama.cpp block masking** using existing `llama_kv_self_seq_rm()` API. Start with manual block boundary insertion (special tokens) and test KV eviction behavior on Qwen3 models. This is the critical path to Memento deployment.
5. **Evaluate OpenMementos as fine-tuning data** — can we SFT a Qwen3-32B GGUF on a subset to learn block-memento format? Test with LoRA to minimize compute.

### Long-term (requires significant investment)

6. **Full Memento deployment**: llama.cpp block masking + SFT on OpenMementos + RL fine-tuning + integration with m@k voting. Target: 2-3x KV reduction at zero accuracy cost.
7. **Triple-stack KV compression**: Memento block masking + Hadamard q4_0 quantization + Expected Attention selection. This is the theoretical ceiling for KV optimization.
