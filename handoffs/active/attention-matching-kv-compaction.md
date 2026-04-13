# Attention Matching KV Compaction

**Status**: active — deep-dive complete, implementation planning
**Created**: 2026-04-13 (via research intake)
**Updated**: 2026-04-13 (deep-dive completed)
**Categories**: kv_cache_optimization, inference_serving

## Current Work — Resume Here

### What's Done (2026-04-13)

Research intake processed 4 entries. Deep-dive completed for all (see `research/deep-dives/kv-compaction-attention-matching-cluster.md`):
- **intake-351 (Attention Matching)**: CONFIRMED new_opportunity. 10x near-lossless on narrative QA, HighestAttnKeys-fast in ~14s. Coding untested.
- **intake-350 (Latent Briefing)**: DOWNGRADED to not_applicable. PGD beta and Ridge C2 are no-ops (wrong optimization target, V_full ignored). Cross-model claim misleading. Do NOT use as reference.
- **intake-352 (KVCOMM)**: DOWNGRADED to not_applicable. Triple hard blocker (same-model requirement, prefill-only, no llama.cpp path).
- **intake-353 (LRAgent)**: Confirmed not_applicable (LoRA-specific).

### State

Implementation planning phase. Two-track approach: Python prototype for validation, then llama.cpp native integration.

## Objective

Implement Attention Matching KV compaction for our llama.cpp stack. Target: 10x KV compression on Qwen2.5-Coder-32B coding contexts with minimal quality loss. HighestAttnKeys-fast variant as starting point.

## Why This Matters for EPYC

At 256K context, Qwen2.5-Coder-32B KV cache at f16 is ~64 GB. With Hadamard q4_0: ~16 GB. With 10x AM compaction on top: **~1.6 GB**. This is the difference between "one slot maximum" and "multiple concurrent slots."

AM compaction is orthogonal to quantization — both can stack. Combined theoretical ceiling: 10x (compaction) x 4x (q4_0) = **~40x KV memory reduction**.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-351 | Fast KV Compaction via Attention Matching | high | new_opportunity |
| intake-350 | Latent Briefing (repo) | low | not_applicable (broken corrections) |
| intake-352 | KVCOMM (NeurIPS'25) | low | not_applicable (triple hard blocker) |
| intake-353 | LRAgent | low | not_applicable (LoRA-specific) |

## Key Technical Details

**Attention Matching formulation** (2602.16284, Zweiger, Fu, Guo, Yoon Kim — MIT):

The compact cache (C_k, beta, C_v) must reproduce two properties for any future query:
1. **Attention output**: weighted-value sum each block produces
2. **Attention mass**: total unnormalized attention weight the block receives

Decomposition into closed-form subproblems (no gradient descent):
1. Select compact keys C_k from original key subset (RMS-heuristic or OMP)
2. Fit bias beta via NNLS to match attention mass
3. Fit values C_v via OLS to match attention outputs

**Published results (Qwen3-4B)**:

| Compression | QuALITY Acc | LongHealth Acc | Notes |
|---|---|---|---|
| 1x (full) | 72.1% | ~70% | Baseline |
| 10x | ~71% | ~65% | Near-lossless narrative, moderate info-dense degradation |
| 50x | ~71% (OMP) | ~55% | Information-dense degrades significantly |

**Online compaction (AIME)**: 2048 physical KV + 6x 50% compaction = 8192 effective = 13/30 (matches uncompacted 8192).

**vs Expected Attention (triattention handoff S1)**: AM outperforms KVzip at all ratios, especially 20x+. Gap narrows at 5-10x. Expected Attention simpler to implement (pure selection, no attention biases).

## Implementation Plan

### Track 1: Python Prototype (validation)

| Step | Task | Effort | Dependency |
|---|---|---|---|
| P1 | Port HighestAttnKeys-fast from adamzweiger/compaction to our eval harness | LOW | None |
| P2 | Run on Qwen2.5-Coder-32B coding benchmarks (LongCodeBench if available, else our eval suite) | MEDIUM | P1 |
| P3 | Compare quality vs Expected Attention (S1) at 5x, 10x, 20x | MEDIUM | P1 + triattention S1 |
| P4 | Test AM + Hadamard q4_0 stacking — quality under dual compression | MEDIUM | P2 |

### Track 2: llama.cpp Native Integration

| Step | Task | Effort | Dependency |
|---|---|---|---|
| L1 | Add per-token attention bias to llama.cpp attention kernel (`score[j] += beta[j]`) | MEDIUM | None (can start immediately) |
| L2 | KV cache metadata: logical length (RoPE positions) vs physical length (actual entries) | MEDIUM | L1 |
| L3 | llama-server API: endpoint to load pre-compacted KV into a slot | MEDIUM | L2 |
| L4 | Full ggml NNLS+OLS implementation for online compaction (no Python preprocessing) | HIGH | L1-L3 proven |

L1-L3 enable Python-compacted KV to be served by llama-server. L4 makes compaction native (online, no external preprocessing).

### Decision Gates

- **Gate 1 (after P2)**: IF 10x compression preserves >95% quality on coding tasks THEN proceed to L1-L3.
- **Gate 2 (after P3)**: IF AM at 10x significantly outperforms Expected Attention at 10x THEN AM is the primary path. ELSE Expected Attention (simpler) may be sufficient.
- **Gate 3 (after L3)**: IF Python preprocessing + llama-server decode works end-to-end THEN deploy. L4 (full ggml) is an optimization, not a blocker.

## Relationship to Existing Work

- **triattention-kv-selection.md**: Token selection (which tokens to keep). AM could replace selection at high compression, or compose. S1 (Expected Attention) is the comparison target at 5-10x.
- **kv-cache-quantization.md** (completed): Quantization (how tokens are stored). Orthogonal — stacking untested but theoretically multiplicative.
- **llama.cpp #20037**: Community RFC for full ggml implementation. We can move faster with Track 2 hybrid approach (Python compaction + C++ decode).

## Compression Stacking Analysis

AM compaction is orthogonal to our other KV compression layers:

| Stack | Compression | KV for 256K Qwen2.5-Coder-32B | Notes |
|---|---|---|---|
| Baseline (f16) | 1x | 64 GB | Current without optimization |
| Hadamard q4_0 (deployed) | 4x | 16 GB | Production today |
| + AM Compaction (10x) | 40x | 1.6 GB | Quant compresses representation, AM compresses token count |
| + Block Masking (Memento, 3x) | 120x | ~530 MB | Memento removes reasoning blocks, AM compacts survivors |

**Why these stack**: Each operates on a different dimension:
- **Quantization**: HOW each KV entry is stored (precision)
- **AM Compaction**: HOW MANY entries exist (latent-space reduction with fitted biases/values)
- **Block Masking**: WHICH semantic blocks survive (reasoning chain pruning)

Token selection (Expected Attention, TriAttention) is **redundant** with AM — AM constructs better compact representations than keeping original tokens. No benefit from stacking.

**Online compaction** (compact-in-place during generation) composes with all layers. If live KV is quantized + block-masked, AM compaction dequantizes for scoring, fits compact (K,β,V), re-quantizes. The AIME result (6 consecutive 50% compactions preserving reasoning) validates this pattern.

**Key unknown**: Quality cliff under triple compression. Each layer claims minimal individual loss, but combined degradation may be multiplicative. P4 tests dual (AM + quant). Triple-stack testing is a separate gate.

## Open Questions

- Does AM's 10x quality hold on Qwen2.5-Coder-32B coding contexts? (Coding benchmarks NOT tested in paper)
- How does AM interact with Hadamard KV quantization? (Hadamard preserves norms but beta scaling may interact)
- At what compression ratio does the crossover happen where AM beats Expected Attention?
- Is 10x the right target for coding, or should we aim lower (5x) for safety?

## CPU Feasibility

The paper is GPU-only (PyTorch CUDA) but the algorithm has no GPU-parallel dependency:
- **RMS scoring**: Element-wise ops on attention weights. Standard inference forward pass.
- **NNLS for beta**: Iterative projected gradient on small matrices (t x t, where t = kept positions per head). 2.2s on H200; estimated 10-20s on EPYC with AVX-512. LAPACK `dnnls` or hand-rolled.
- **OLS for values**: Cholesky solve `(X'X)^{-1}X'Y`. 1.8s on H200; estimated 5-10s on CPU. LAPACK `dpotrs`.
- **Decode bias**: `score[j] += beta[j]` — one `_mm512_add_ps` per 16 positions. Negligible vs memory-bandwidth-bound attention.

Small dense matrices from NNLS/OLS fit in L2 cache. Our EPYC 384MB L3 is overkill. The 2.2s H200 NNLS timing is likely dominated by CUDA kernel launch overhead, not compute. CPU may actually be faster for these small linear algebra subproblems.

## Known Limitations

- OMP variant requires minutes per compaction (HighestAttnKeys-fast at ~14s is the practical choice)
- Information-dense content degrades faster than narrative at same compression
- Coding benchmarks completely untested in the paper (our validation is novel)
- Per-token biases require attention kernel modification (not a standard feature in any inference engine)

## Key Files

| Path | Purpose |
|------|---------|
| `research/deep-dives/kv-compaction-attention-matching-cluster.md` | Full deep-dive analysis (4 entries, all findings) |
| Reference: github.com/adamzweiger/compaction | Paper author's full Python implementation |
| Reference: llama.cpp #20037 | Community tracking of ggml implementation |

## Notes

The paradigm shift: token selection operates in token space (keep/evict), compaction operates in latent space (construct new representations). The closed-form decomposition (NNLS+OLS) makes this practical. At 10x, HighestAttnKeys-fast gives near-lossless quality in seconds. At 20x+, AM is the only viable approach (all token-selection methods degrade significantly).

Online compaction (repeated 50% compactions preserving reasoning state) opens a second use case: extending effective context beyond physical KV cache limits during long generation.
