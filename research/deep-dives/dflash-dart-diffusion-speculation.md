# Deep Dive: DFlash & DART — Block Diffusion Speculative Decoding

**Date**: 2026-03-17
**Intake**: intake-158 (DFlash, arxiv:2602.06036), intake-159 (DART, arxiv:2601.19278)
**Question**: Can we reverse-engineer DFlash/DART for GGUF/llama.cpp?

## Executive Summary

**Yes, the drafter architectures are portable to llama.cpp.** Both are standard transformers (5-layer for DFlash, 1-layer for DART) with shared embeddings that could be converted to GGUF. The engineering is non-trivial but feasible.

**However, they will NOT help for Qwen3.5-35B-A3B.** The verification bottleneck is identical to MTP-1 Step 7 (0.56x). 75% Delta Net recurrent layers process tokens sequentially — verifying 16 draft tokens costs ~16x single decode, far exceeding any drafting speedup.

**They COULD help for dense models** (Qwen2.5-32B, Llama-3, Mistral) where multi-token verification scales near-O(1) via parallel KV processing. DFlash's single-pass 16-token drafting with τ=6.49 acceptance is significantly better than our current external drafters.

## Technique Analysis

### DFlash Architecture

| Component | Detail |
|-----------|--------|
| Drafter size | 0.5B params (Qwen3.5-35B-A3B), 1B params (Qwen3-8B) |
| Layers | 5 transformer blocks (8 for Qwen3-Coder) |
| Shared weights | Token embedding + LM head frozen from target |
| Block size | 16 tokens (10 for LLaMA) |
| Drafting | Single forward pass, all 16 tokens in parallel |
| Conditioning | Hidden states from 5 uniformly-sampled target layers → concat → FC projection → injected into drafter KV projections at every layer |
| Attention | Sparse: bidirectional within blocks, causal to prefix (Flex Attention) |
| Training | 800K samples, cross-entropy with position-weighted exponential decay, AdamW lr=6e-4, 6 epochs |
| Acceptance τ | 6.49 tokens (Qwen3-8B greedy), 5.48 (temp=1) |

**Key insight**: DFlash's cost is O(1) in draft length — `T_draft = t_parallel` (constant) vs EAGLE-3's `T_draft = γ · t_step` (linear). This is why 5 layers producing 16 tokens beats EAGLE-3's 1 layer producing 8 tokens.

### DART Architecture

| Component | Detail |
|-----------|--------|
| Drafter size | Single transformer decoder layer + FC projection |
| Conditioning | Hidden states from 3 intermediate target layers → concat → FC |
| Drafting | Single forward pass, parallel logits for d positions |
| Tree pruning | N-gram-enforced (3-gram trie from Dolma, 43.5GB disk, 100GB RAM) |
| Acceptance τ | 3.67-3.76 (Qwen3-14B/32B), 4.08 (LLaMA2-7B) |
| Draft latency | 1.5ms draft + 2ms tree prune = 3.5ms total |
| Training | 280K samples (ShareGPT + UltraChat), position-aware KL divergence with γ=0.6 decay |

**Key insight**: DART trades drafter quality (1 layer, lower τ) for extreme drafting speed (3.5ms) + N-gram-boosted tree diversity (τ improves +0.5-0.7 from pruning). The 100GB trie is a practical constraint — acceptable on inference servers but heavy for our setup.

## llama.cpp Portability Assessment

### What's Portable (Moderate Engineering)

#### 1. Drafter GGUF Conversion — FEASIBLE

Both drafters are standard transformers. Conversion path:

```
DFlash:  5 transformer layers + FC fusion layer → GGUF
DART:    1 transformer layer + FC projection     → GGUF
```

- Shared embedding + LM head: point to target model's tensors (already done for MTP)
- DFlash: ~0.5B params → Q4_K_M ~300MB. DART: ~100M params → Q4_K_M ~60MB
- `convert_hf_to_gguf.py` needs a new model class, but the tensor layout is standard
- Precedent: MTP GGUF conversion (Steps 1-4) solved the same shared-weight problem

**Effort**: ~3 days for conversion + loading. Well-understood from MTP work.

#### 2. Single-Pass Parallel Drafting — FEASIBLE

The drafter produces 16 tokens in one forward pass. This is essentially a prefill operation:
- Input: prefix tokens (verified) + 15 mask tokens
- Output: logits at all 16 positions
- CPU handles this fine — it's a single batched forward through a tiny model
- No sequential decode dependency — pure batch matmul

On a 0.5B model with Q4_K_M, expect ~1-3ms per draft round on EPYC 9655 (extrapolating from 0.5B drafter throughput).

**Effort**: ~2 days. Reuse `common_speculative` draft infrastructure.

#### 3. Standard Verification — ALREADY EXISTS

Verification is standard rejection sampling — accept tokens until first mismatch. `common_speculative` already implements this for tree and linear speculation.

**Effort**: Zero — reuse existing code.

### What Requires New Infrastructure

#### 4. Per-Layer Hidden State Extraction — MODERATE

Both DFlash and DART condition on hidden states from specific target model layers. llama.cpp currently does NOT expose intermediate hidden states — only final logits and embeddings.

**Required API**:
```c
// New: extract hidden state from layer `il` after last decode
const float * llama_get_hidden_state(
    struct llama_context * ctx,
    int32_t il        // layer index
);
```

**Implementation approach**:
- During target model forward pass, hook into `llm_graph_context::build_layer()` to save intermediate `cur` tensors
- Allocate per-layer hidden state buffers in `llama_context` (similar to `logits` buffer)
- DFlash needs 5 layers, DART needs 3 — only save what's configured
- Memory cost: 5 × hidden_dim × n_tokens × sizeof(float) ≈ 5 × 4096 × 1 × 4 = 80KB per decode (negligible)

**Complications**:
- Must tap AFTER layer norm but BEFORE attention (pre-norm hidden state)
- Graph must be modified to copy these tensors out — currently intermediate results are freed
- `ggml_graph_compute()` frees intermediates; need to mark extraction points as graph outputs

**Effort**: ~5 days. Most invasive change — touches `llama-graph.cpp`, `llama-context.cpp`, possibly `ggml` backend to preserve intermediate tensors.

**Precedent**: MTP Step 6 solved a similar problem — caching pre-norm hidden state for the MTP layer. That approach cached ONE hidden state; this would generalize to N configurable layer taps.

#### 5. Block-Sparse Attention in Drafter — MODERATE-HARD

DFlash uses sparse attention: bidirectional within 16-token blocks, causal to prefix context. This is NOT standard causal attention.

**Options**:
a. **Custom attention mask** — pass a precomputed attention mask tensor. llama.cpp attention implementations assume causal masking. Would need a per-model attention mode enum.
b. **Separate prefill of block tokens** — treat the 16 mask positions as a "prefill" where each attends to prefix + all block positions. This might work with existing infrastructure if we set up KV cache correctly.
c. **Ignore bidirectional within block** — use standard causal masking. Quality may degrade but DFlash may still work (paper doesn't explicitly test causal-only inference).

**Effort**: Option (c) is 0 days (just try it). Option (b) is ~3 days. Option (a) is ~7 days.

#### 6. Target Feature Injection into Drafter KV — MODERATE

DFlash's unique mechanism: target hidden states are fused via FC layer, then injected as persistent KV entries in the drafter's attention. This is NOT standard cross-attention — it modifies the Key and Value projections directly.

**Implementation**:
- After extracting target hidden states (step 4), run FC fusion (one matmul)
- For each drafter layer: add fused features as additional KV entries before block tokens
- This is similar to prefix caching — the fused features act like a "soft prefix"

**Alternative**: Concatenate fused features as token embeddings (like EAGLE does). Simpler but may lose quality since DFlash specifically injects into KV space.

**Effort**: ~3 days for KV injection, ~1 day for embedding concatenation fallback.

### Implementation Cost Summary

| Component | Effort | Risk | Precedent |
|-----------|--------|------|-----------|
| GGUF conversion | 3 days | Low | MTP Steps 1-4 |
| Parallel drafting | 2 days | Low | common_speculative |
| Verification | 0 days | None | Existing |
| Hidden state extraction | 5 days | Medium | MTP Step 6 (partial) |
| Block-sparse attention | 0-7 days | Medium | Try causal-only first |
| KV injection | 3 days | Medium | Novel for llama.cpp |
| **Total** | **13-20 days** | | |

## The Verification Wall: Why This Doesn't Help Qwen3.5

MTP-1 Step 7 confirmed the fundamental limitation:

| Batch Size | Decode Latency | Cost vs Single |
|------------|---------------|----------------|
| 1 token | ~220ms | 1.0x |
| 2 tokens | 560-816ms | 2.5-3.7x |
| 16 tokens (projected) | ~3500ms | ~16x |

**Root cause**: 30/40 layers in Qwen3.5-35B-A3B are Delta Net (gated linear attention). Recurrent layers process tokens **sequentially** regardless of batch size. A 16-token verification batch runs each token through each recurrent layer one at a time.

DFlash's GPU speedup works because:
- GPU attention layers verify N tokens in O(1) via batched KV matmul
- GPU recurrent state isn't the bottleneck (Qwen3.5 on GPU uses parallel scan)

llama.cpp on CPU:
- Dense attention layers: verification of N tokens is near-O(1) (parallel with OpenMP)
- Delta Net recurrent layers: verification of N tokens is O(N) (serial state updates)
- 75% of layers are recurrent → overall verification ≈ O(N)

**This kills ALL draft-verify approaches on hybrid recurrent models**, not just DFlash:
- Tree speculation: -53% to -66% (Approaches 0, A, C)
- MTP-1: 0.56x (Step 7)
- DFlash (projected): ~0.3x (16 tokens at ~16x cost, τ=6.49 → effective ~0.4 tokens/round)

## Where DFlash IS Viable: Dense & Pure MoE Models on llama.cpp

For dense (attention-only) and pure MoE models, multi-token verification scales near-O(1):

| Model | Role | Architecture | Verification N=16 | DFlash Projected |
|-------|------|-------------|-------------------|-----------------|
| Qwen3.5-35B-A3B | (none currently) | 75% recurrent | ~16x | NOT VIABLE |
| Qwen3-Coder-30B-A3B | frontdoor | Pure MoE | ~1.2-1.5x | **VIABLE (~2-4x)** |
| Qwen2.5-Coder-32B | coder_escalation | Dense | ~1.1-1.3x | **VIABLE (~3-5x)** |
| Qwen3-235B-A22B | architect_general | Pure MoE | ~1.2-1.5x | **VIABLE (~2-4x)** |
| Qwen3-Coder-480B-A35B | architect_coding | Pure MoE | ~1.2-1.5x | **VIABLE (~2-4x)** |
| Llama-3.1-70B | (reference) | Dense | ~1.1-1.3x | **VIABLE (~3-5x)** |

**Every model currently in our production orchestration stack is eligible.**
Only the Qwen3.5 hybrid models (not in production roles) are blocked by recurrent verification.

Projected speedups assume:
- τ ≈ 6 tokens accepted per round (DFlash paper reports 6.49 on GPU)
- Draft cost ~3ms (0.5B model, single pass)
- Verification overhead ~1.2x for dense (from our SpecExec profiling: f16 1.69x at N=64, Q4_K_M ~1.1x at N=16)

### Model Size and DFlash Benefit

DFlash benefits scale with target size. Larger targets have higher verification-to-draft ratio, so O(1) drafting gives proportionally more benefit:
- **480B architect_coding**: Highest absolute gain — single decode ~500-800ms, DFlash draft ~3ms
- **235B architect_general**: Second highest — single decode ~300-500ms
- **32B coder_escalation**: Still strong — draft cost is small fraction of verification
- **30B frontdoor**: Good — highest volume role, even modest speedup has large aggregate impact
- **<14B models**: Diminishing returns — decode is fast enough that draft overhead fraction grows

### Parallel Recurrent Verification via NUMA Isolation (Hybrid Model Reopener)

For Qwen3.5-35B-A3B, the verification bottleneck is sequential recurrent state updates *within a single sequence*. But if verification paths are run as **separate sequences on isolated NUMA nodes**, each with their own model copy and independent recurrent state:

- N NUMA nodes × 1 token each (parallel) vs 1 node × N tokens (serial)
- Individual throughput lower but aggregate throughput potentially higher (confirmed by prior concurrent execution tests on small models)
- Each node needs its own model copy (~20GB Q4_K_M per copy)
- 4 NUMA nodes × 20GB = 80GB total for 4-path parallel verification

This is essentially Approach A (per-path replay) but at the process level with NUMA isolation instead of within a single `llama_decode()` call. The prior testing showed aggregate throughput gains from concurrent execution — if verification of 4 draft tokens across 4 NUMA nodes completes in ~1.2x single-decode time (instead of 4x serial), DFlash with τ=6.49 on Qwen3.5 becomes interesting again.

**Open question**: What was the individual-vs-aggregate throughput ratio in prior concurrent tests? If 4 concurrent processes give >2.5x aggregate throughput, NUMA-parallel DFlash verification could be net-positive on hybrid models.

This would be **significantly faster than our current external drafter approach** (Qwen2.5-Coder-0.5B at 185 t/s, acceptance ~40-60%, linear speculation).

## DFlash vs DART: Which to Port?

| Dimension | DFlash | DART |
|-----------|--------|------|
| Drafter quality (τ) | 6.49 | 3.67-3.76 |
| Drafter params | 0.5B | ~0.1B |
| Draft latency | ~3ms (est. CPU) | ~1.5ms GPU (+ 2ms N-gram lookup) |
| Extra memory | ~300MB GGUF | ~60MB GGUF + 100GB N-gram trie |
| Hidden state taps | 5 layers | 3 layers |
| Attention complexity | Block-sparse (harder) | Causal (easier) |
| Weights available | Qwen3.5, Qwen3, LLaMA, gpt-oss | Not published for Qwen3.5 |
| Training recipe | "Coming soon" | Published |

**Note on N-gram trie**: 100GB is feasible on our EPYC setup (768GB+ RAM). DART's "N-gram" is a 3-gram trie from the Dolma corpus — standard corpus-frequency lookup, orthogonal to prompt-lookup speculation. Our code corpus could serve as a domain-specific N-gram source for code tasks (higher acceptance on code tokens), though the general trie already covers code vocabulary.

**Recommendation: DFlash first.**
- Higher acceptance (6.49 vs 3.76) = more tokens per round = bigger speedup — this is the dominant factor
- DFlash has published weights for our target models (Qwen3.5, Qwen3, Qwen3-Coder)
- Block-sparse attention can be tested with causal fallback first
- DART's training recipe is useful reference for when DFlash publishes theirs

## DFlash + Tree Speculation: Composable and Multiplicative

DFlash and tree speculation are fully composable and their benefits are multiplicative, not additive.

**How it works**: DFlash's single forward pass produces logits at all 16 positions. Instead of taking only the greedy (top-1) token at each position (linear speculation), take top-k at each position to build a tree:

```
Linear DFlash: [pos1_top1] → [pos2_top1] → ... → [pos16_top1]  (one path)
Tree DFlash:   [pos1_top1, pos1_top2] → [pos2_top1, pos2_top2] → ... (branching tree)
```

Tree verification then accepts the longest matching path through the tree.

**Key advantage**: In standard tree speculation, building the tree requires N sequential autoregressive draft passes (EAGLE-3 does this). DFlash builds the ENTIRE tree in a single parallel forward pass — the tree construction cost is O(1), same as linear.

**Projected impact**:
- Linear DFlash on dense models: 2-4x
- Tree bonus on large architect models (from our SpecExec data): 2-5% additional accepted tokens
- Combined: 2-4x × 1.02-1.05 = 2.04-4.2x
- For architect_general (235B): tree speculation showed f16 +15.8% at 256 candidates
- If DFlash tree achieves similar tree bonus: 2-4x × 1.15 = 2.3-4.6x

The tree bonus is larger for larger models (more verification headroom) and for tasks with higher branching (code, math). For the architect models (235B, 480B), this compound effect could be significant.

## Recommended Actions

### Action A: DFlash Port for Production Stack (HIGH PRIORITY)

**Scope**: Port DFlash drafter to llama.cpp for ALL production models (frontdoor, coder_escalation, architect_general, architect_coding). Every production model is dense or pure MoE — all are eligible.

**Priority order** (by impact):
1. **architect_general** (Qwen3-235B-A22B) — highest absolute gain, slowest model
2. **architect_coding** (Qwen3-Coder-480B-A35B) — similar, even larger
3. **coder_escalation** (Qwen2.5-Coder-32B) — dense, best verification scaling
4. **frontdoor** (Qwen3-Coder-30B-A3B) — highest volume, moderate per-request gain

**Steps**:
1. Download `z-lab/Qwen3-8B-DFlash-b16` weights, inspect `config.json` and tensor names (smallest model, fastest iteration)
2. Write `convert_hf_to_gguf.py` model class for DFlash drafter (shared embed/lm_head)
3. Implement `llama_get_hidden_state()` API — generalize MTP Step 6's hidden state caching to N configurable layer taps
4. Build DFlash graph in new `src/models/dflash.cpp` — 5-layer transformer with KV injection
5. Try causal-only attention first (skip block-sparse)
6. Wire into `common_speculative` as draft source — both linear and tree modes
7. Benchmark on Qwen3-Coder-30B-A3B (frontdoor, quickest to test): acceptance rate + net throughput vs baseline and vs current 0.75B external drafter
8. If positive: benchmark on architect_general (235B) with tree verification

**Estimated effort**: 13-15 days
**Expected outcome**: 2-4x throughput on dense/MoE production models (vs current ~1.3x with external drafter). With tree mode on architect models: potentially 2.3-4.6x.

### Action B: NUMA-Parallel Verification Benchmark (MEDIUM PRIORITY — reopens hybrid)

**Scope**: Test whether NUMA-isolated concurrent verification can break the sequential recurrent bottleneck on Qwen3.5-35B-A3B.

**Steps**:
1. Baseline: single-process single-token decode throughput
2. Run 2/4/8 concurrent single-token decodes, each pinned to separate NUMA node via `numactl`
3. Measure aggregate throughput vs individual throughput
4. If aggregate/N > 0.6x individual: project DFlash viability (τ=6.49, N-parallel verification)
5. If viable: design NUMA-aware verification API (`llama_verify_parallel()`)

**Estimated effort**: 2-3 days for benchmark, 5+ days for API if viable
**Expected outcome**: Determines if NUMA parallelism can reopen speculation for hybrid recurrent models, potentially reviving MTP-1 and DFlash on Qwen3.5.

### Action C: Chapter 10 Update

Add DFlash/DART as a new paradigm family in Chapter 10 (Advanced Speculative Decoding):
- Section: "Block Diffusion Drafting (DFlash, DART, SpecDiff)"
- Key distinction from EAGLE/tree: O(1) draft cost vs O(N) autoregressive
- Key distinction from MTP: external trained drafter vs model-native head
- DFlash + tree: composable, multiplicative benefits
- Limitation: requires per-layer hidden state extraction from target

### Action D: Track Training Recipe

DFlash repo states "We will also open-source the training recipe soon." When available, this enables training DFlash drafters for ANY model — not just the ones z-lab has published. Combined with Action A's llama.cpp infrastructure, this would give us DFlash for every model in the registry. DART's published training recipe is useful reference in the meantime.

## References

- DFlash paper: arxiv:2602.06036
- DFlash code: https://github.com/z-lab/dflash
- DFlash weights: https://huggingface.co/z-lab/Qwen3.5-35B-A3B-DFlash (0.5B)
- DART paper: arxiv:2601.19278
- EAGLE-3: arxiv:2503.01840
- MTP-1 findings: `handoffs/completed/mtp-speculative-decoding.md` (Step 7, 0.56x)
- SpecExec profiling: `docs/experiments/specexec-verification-profile.md`
- Verification scaling data: `data/specexec/` (Q4_K_M 4-5x at N=64, f16 1.69x)
