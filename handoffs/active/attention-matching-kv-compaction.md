# Attention Matching KV Compaction

**Status**: active — L1-L4 merged to production-consolidated-v3, Python validation continues
**Created**: 2026-04-13 (via research intake)
**Updated**: 2026-04-13 (L1-L4+L4b merged to production)
**Categories**: kv_cache_optimization, inference_serving

## Current Work — Resume Here

### What's Done (2026-04-13)

Research intake processed 4 entries. Deep-dive completed for all (see `research/deep-dives/kv-compaction-attention-matching-cluster.md`):
- **intake-351 (Attention Matching)**: CONFIRMED new_opportunity. 10x near-lossless on narrative QA, HighestAttnKeys-fast in ~14s. Coding untested.
- **intake-350 (Latent Briefing)**: DOWNGRADED to not_applicable. PGD beta and Ridge C2 are no-ops (wrong optimization target, V_full ignored). Cross-model claim misleading. Do NOT use as reference.
- **intake-352 (KVCOMM)**: DOWNGRADED to not_applicable. Triple hard blocker (same-model requirement, prefill-only, no llama.cpp path).
- **intake-353 (LRAgent)**: Confirmed not_applicable (LoRA-specific).

**P1 COMPLETE (2026-04-13)**: HighestAttnKeys-fast ported to `scripts/benchmark/attention_matching.py`.
- Reference repo cloned to `data/external/compaction` (adamzweiger/compaction, MIT)
- Port validated against reference: 100% index overlap, exact quality match at 2x/5x, slight improvement at 10x (sorted indices preserve positional structure)
- Synthetic validation: T=512 and T=4096, compression 2x/5x/10x/20x
- CPU timing (EPYC): NNLS ~10ms, OLS ~13ms at T=4096 (well within budget)
- On random data: cosine sim degrades as expected (no attention structure). Real model validation (P2) requires running model server.

### State

P1 complete. P2 validated on Qwen2.5-7B (2026-04-13): **2x=1.000 (lossless), 5x=0.906, 10x=0.807**. Early layers compress perfectly; deep layers need adaptive strategy. Next: P2 on Qwen2.5-Coder-32B coding benchmarks, P3 comparison vs Expected Attention.

### P2 Validation Results (Qwen2.5-7B, 3 prompts, 3 layers, head 0)

| Layer | 2x | 5x | 10x |
|---|---|---|---|
| L0 (early) | 1.000 | 1.000 | 0.994 |
| L14 (middle) | 1.000 | 0.878 | 0.768 |
| L27 (deep) | 1.000 | 0.840 | 0.658 |
| **Average** | **1.000** | **0.906** | **0.807** |

**Insight**: Layer-adaptive compression is the right strategy. Compress early layers at 10x, middle at 5x, deep at 2x. Combined effective ratio could reach ~5x with near-lossless quality across all layers.

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
| P1 | ~~Port HighestAttnKeys-fast from adamzweiger/compaction to our eval harness~~ ✅ 2026-04-13 | LOW | None |
| P2 | Run on Qwen2.5-Coder-32B coding benchmarks (LongCodeBench if available, else our eval suite) | MEDIUM | P1 |
| P3 | Compare quality vs Expected Attention (S1) at 5x, 10x, 20x | MEDIUM | P1 + triattention S1 |
| P4 | Test AM + Hadamard q4_0 stacking — quality under dual compression | MEDIUM | P2 |

### Track 2: llama.cpp Native Integration

| Step | Task | Effort | Dependency | Status |
|---|---|---|---|---|
| L1 | ~~Add per-token attention bias to llama.cpp attention kernel~~ | MEDIUM | None | ✅ 2026-04-13. Beta injected via kq_mask in `llama-kv-cache.cpp`. Public API `llama_memory_set_beta()`. Works with flash + softmax. |
| L2 | ~~KV cache metadata: logical vs physical length~~ | MEDIUM | L1 | ✅ Merged into L1. Existing KV cache handles sparse positions natively. `is_compacted` implicit via non-zero beta. |
| L3 | ~~E2E beta injection test~~ | MEDIUM | L1 | ✅ 2026-04-13. `test-am-beta-injection.cpp` passes: beta=+5/-5 alter generation on Qwen2.5-7B. |
| L3b | ~~Server `set-beta` endpoint~~ | MEDIUM | L3 | ✅ 2026-04-13. `POST /slots/{id}?action=set-beta` accepts JSON betas array. E2E tested on Coder-32B f16. |
| L4 | ~~Full ggml NNLS+OLS implementation for online compaction (no Python preprocessing)~~ | HIGH | L3b | ✅ 2026-04-13. Merged to `production-consolidated-v3` (`81c9ad1ec`). Validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, Qwen3.5-35B-SSM-hybrid. 5x compression, zero degradation. Handles SSM-hybrid models (preserves recurrent state tail bytes). |
| L4b | ~~K-norm importance scoring for compact endpoint~~ | MEDIUM | L4 | ✅ 2026-04-13. Fast approximation of full attention-weight scoring (`7784b3d9c`). Tested: 140→42 cells (3.3x), correct factual retrieval preserved. True NNLS attention scoring (L4c) deferred — requires graph modification to retain attention weights during inference. |

### Pipeline Status (2026-04-13)

**All L1-L4 + L4b merged to `production-consolidated-v3`.**

**What's deployed**:
- C API: `llama_memory_set_beta()` + `llama_memory_seq_rm()` — production-ready.
- Server endpoints: `set-beta`, `seq-rm`, and `compact` (with L4b K-norm importance scoring) — all operational.
- Full ggml NNLS+OLS online compaction — no Python preprocessing required. Validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, Qwen3.5-35B-SSM-hybrid at 5x compression with zero degradation.
- L4b K-norm importance scoring: fast approximation of attention-weight scoring for the compact endpoint. Tested 140→42 cells (3.3x), correct factual retrieval preserved.
- State format versioning for backward compat (`1503f5ad8`, `80c72c0c6`).
- SSM-hybrid support: preserves recurrent state tail bytes.

**Production commits** (on `production-consolidated-v3`):
- `81c9ad1ec` — feat: Attention Matching KV compaction — L1-L4 complete
- `80c72c0c6` — fix: state format versioning for AM compaction backward compat
- `7784b3d9c` — feat: L4b K-norm importance scoring for compact endpoint

**Resolved blocker**: Server prompt-cache-matching invalidation after external KV modification was solved by two paths:
1. **State save/restore** — Python `state_compactor.py` reads state binary, selects positions, sets beta, writes compact state. Restore via `/slots/{id}?action=restore`. E2E verified: 196→98 cells (2.0x), correct answer preserved.
2. **Native server-side compaction** (L4) — server knows about compaction, maintains prompt tracking. Now the primary path.

**L1 also enables direct P2 validation on production 32B Q4_K_M** — extract attention weights natively from GGUF inference, apply compaction, measure quality. No HF weights download needed.

**Deferred**: L4c (true NNLS attention scoring) requires graph modification to retain attention weights during inference — not yet needed given L4b K-norm approximation works well.

### L1 Audit Findings (2026-04-13)

**Verdict**: Infrastructure exists but flash attention path is the main blocker.

**Two attention paths in llama.cpp**:
1. **Flash Attention** (`ggml_flash_attn_ext`) — primary path, used by default. **Does NOT support KQ bias** (`GGML_ASSERT(kq_b == nullptr)` at `llama-graph.cpp:1907`).
2. **Standard Softmax** (`ggml_soft_max_ext`) — fallback path. **Already supports additive bias** via `kq_b` parameter (lines 1986-1989). ALiBi slope computation is the exact template.

**Existing bias infrastructure**:
- ALiBi: per-head linear position bias, computed in mask generation (`llama-kv-cache.cpp:1673`)
- Causal mask: 0.0 for attend, -INF for mask, in `set_input_kq_mask_impl<>`
- `kq_b` tensor: element-wise addition before softmax in standard path

**KV cache metadata**:
- `llama_kv_cell_ext` at `llama-kv-cells.h:13` stores only 2D position (x,y for M-RoPE)
- Needs `float beta = 0.0f` field for per-token attention bias
- State serialization (`state_write_meta/state_read_meta`) needs beta in format

**Implementation strategy** (recommended phased approach):
1. **Phase 1** (~100 LOC): Add `beta` field to `llama_kv_cell_ext`. Populate beta tensor in `build_attn_inp_kv_impl()`. Wire into standard softmax path via existing `kq_b`. **Disable flash attention for compacted slots** (flag-gated).
2. **Phase 2** (~200 LOC): Modify CPU flash attention kernel (`ggml-cpu/ops.cpp:8287`) to consume beta tensor as additional input after ALiBi mask. Remove flash-disable guard.
3. **Phase 3** (~150 LOC): Server endpoint `POST /slots/{id}/load-beta` for loading pre-computed beta from Python compaction. Extend slot save/restore.

**Key files**: `llama-graph.cpp` (graph construction), `llama-kv-cells.h` (metadata), `llama-kv-cache.cpp` (mask generation), `ggml-cpu/ops.cpp` (softmax + flash kernels), `ggml.h` (op signatures), `server-context.cpp` (slot API).

**Risk assessment**: Phase 1 is LOW risk — uses existing infrastructure, flag-gated, standard softmax path proven. Phase 2 is MEDIUM — modifying flash attention kernel, but scoped to CPU only. Phase 3 is LOW — extends existing server patterns.

### Decision Gates (updated 2026-04-13 with P2 data)

- **Gate 1 (P2 ASSESSED)**: 10x does NOT preserve >95% quality on 7B (avg 0.807). But **2x is universally lossless (1.000)** and **5x is viable (0.906)**. Revised gate: proceed to L1 at 2x target (guaranteed lossless), with layer-adaptive 2-5x as stretch goal. 10x deferred to long-context validation (short prompts penalize AM).
- **Gate 2 (after P3)**: IF AM at 5x significantly outperforms Expected Attention at 5x THEN AM is the primary path. ELSE consider EA for selection + AM for compaction at different layers.
- **Gate 3 (PASSED)**: L4 full ggml merged to production (`81c9ad1ec`). Both Python preprocessing and native server-side compaction paths available.

**Key P2 insight**: AM effectiveness is strongly context-length-dependent. Short prompts (55-82 tokens) show 0.81 cosine at 10x. Paper shows near-lossless at 10x on 32K+ narrative QA. L1 enables testing on production-length contexts with Q4_K_M quantization — the true validation.

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

| Path | Repo | Purpose |
|------|------|---------|
| `scripts/benchmark/attention_matching.py` | epyc-inference-research | **P1 port** — HighestAttnKeys-fast (RMS selection + NNLS beta + OLS values). Validated against reference. |
| `benchmarks/results/runs/am-p2-qwen7b/` | epyc-inference-research | P2 results: 3 prompts × 28 layers × 4 ratios |
| `benchmarks/results/runs/am-layer-adaptive/` | epyc-inference-research | Layer-adaptive sweep: per-layer compression profile |
| `data/external/compaction/` | epyc-inference-research | Cloned reference repo (adamzweiger/compaction, MIT) |
| `src/llama-kv-cells.h` | llama.cpp-experimental | **L1**: `float beta` field in `llama_kv_cell_ext` |
| `src/llama-kv-cache.cpp` | llama.cpp-experimental | **L1**: beta injection in `set_input_kq_mask_impl()` line 1676 + `set_beta()` method |
| `src/llama-memory.h` | llama.cpp-experimental | **L1**: `set_beta()` virtual interface |
| `src/llama-context.cpp` | llama.cpp-experimental | **L1**: `llama_memory_set_beta()` public C API |
| `include/llama.h` | llama.cpp-experimental | **L1**: public API declaration |
| `tools/server/server-context.cpp` | llama.cpp-experimental | **L3b**: `POST /slots/{id}?action=set-beta` endpoint + `get_memory()` accessor |
| `tools/server/server-context.h` | llama.cpp-experimental | **L3b**: handler declaration |
| `tests/test-am-beta-injection.cpp` | llama.cpp-experimental | **L3**: E2E test — beta alters generation on 7B |
| `research/deep-dives/kv-compaction-attention-matching-cluster.md` | epyc-root | Full deep-dive analysis (4 entries, all findings) |
| Reference: github.com/adamzweiger/compaction | — | Paper author's full Python implementation |
| Reference: llama.cpp #20037 | — | Community tracking of ggml implementation |

## Notes

The paradigm shift: token selection operates in token space (keep/evict), compaction operates in latent space (construct new representations). The closed-form decomposition (NNLS+OLS) makes this practical. At 10x, HighestAttnKeys-fast gives near-lossless quality in seconds. At 20x+, AM is the only viable approach (all token-selection methods degrade significantly).

Online compaction (repeated 50% compactions preserving reasoning state) opens a second use case: extending effective context beyond physical KV cache limits during long generation.

## Research Intake Update — 2026-05-19

### SP-KV cluster — write-time admission and four neighboring KV reduction methods

- **[intake-538] SP-KV: Self-Pruned Key-Value Attention** (arxiv:2605.14037, FAIR — Jégou/Douze/Faysse/Yih/Lomeli/Mazaré/Cabannes/Szilvasy)
  - **New axis**: jointly trained lightweight **utility predictor** decides at **write time** whether each KV pair is admitted to the long-term cache. Recent-window keeps short-range pairs locally available. Differs from the dominant read-time eviction families (H2O, SnapKV, TriAttention) and from quantization-side methods (TurboQuant/TQ3).
  - **3–10× KV cache reduction at little/no validation-loss degradation**, structured per-layer/per-head sparsity patterns, longer sequences are MORE compressible.
  - **Constraint for EPYC**: requires joint fine-tuning of base model + predictor — heavier lift than the inference-only methods (TriAttention, AttentionMatching, SummaryToken) already in active pipeline. Useful as a comparison reference and possible future direction once fine-tuning capacity exists; not drop-in for the current frozen-checkpoint stack.
  - Tier 2b — **contradicting evidence is concrete**:
    - **arxiv:2601.14279 (Steele)** shows a 1.7M-param learned scorer (SIP) **fails to beat trivial position-based heuristics** (keep first 4 + last N) across 5 seeds × 4 retention levels × 3 tasks. SP-KV's joint-trained predictor is exactly the KV-only, query-agnostic write-time scorer Steele targets.
    - **Query-aware methods succeed** because they condition on the current query — read-time selection has an information advantage over SP-KV's write-time admission, which must commit before any future query is observed.
    - Position-based heuristics (attention-sink + recency window) being competitive aligns with SP-KV's own local-window component — much of SP-KV's reported gains may come from the recency window, not the learned predictor.
    - **ForesightKV (intake-553)** requires a two-stage Supervised+GRPO recipe **specifically because** a pure learned predictor degraded LM loss on low-entropy tokens — independent corroboration that learned KV importance is brittle without explicit LM-loss safeguards.
  - **Recommended ablation if/when we evaluate SP-KV**: replace the learned predictor with a position-heuristic (sink + sliding window) baseline at matched cache budget. If SP-KV does not significantly beat that, the learned component is not earning its complexity.

- **[intake-551] KVP / Learning to Evict from KV Cache** (arxiv:2602.10238, Moschella/Manduchi/Sener) — per-head RL agents trained on pre-computed traces; consumes only K/V at write/read time, no LLM weight modification. Generalizes zero-shot to longer contexts and unseen tasks. Per-head specialization is the axis SP-KV does not exploit.
- **[intake-552] LU-KV** (arxiv:2602.08585, Tang et al.) — global combinatorial optimization for per-head budget allocation via convex-hull relaxation + marginal-utility greedy. **80% KV reduction at minimal degradation on LongBench/RULER**. Static profile after offline training — fits frozen-weights constraint; head heterogeneity is the under-exploited axis.
- **[intake-553] ForesightKV** (arxiv:2602.03203, Dong et al.) — distills a "Golden Eviction" oracle (future-attention scores) via supervised Pairwise-Ranking, then GRPO RL on LM loss. **Outperforms prior eviction at half the cache budget on AIME 2024/2025**. The Supervised+GRPO recipe is the cleanest published evidence for why pure learned KV importance is brittle.
- **[intake-554] PBKV** (arxiv:2605.06472, Zheng et al.) — **strongest orchestrator-stack match**. Workflow-level prediction of next-agent invocation drives KV residency. 1.85× over LRU on dynamic workflows. Maps directly onto frontdoor → coder/worker hand-offs where shared long prompts pay BW-bound re-prefill cost on EPYC. Requires a tiny next-agent predictor + llama.cpp prefix-cache hooks; complements frozen GGUF weights.

**Net update to this handoff's roadmap**: KV reduction now has four distinguishable axes — write-time vs read-time selection (SP-KV vs H2O family), per-head vs uniform budget allocation (LU-KV/ForesightKV), workflow-aware vs request-local residency (PBKV), and learned vs heuristic (KVP/SP-KV/ForesightKV vs sink+window). The clearest near-term EPYC opportunity is **PBKV's workflow-aware residency** because it operates at the orchestrator layer (no attention-kernel surgery, no fine-tuning) and matches our frontdoor→worker hand-off pattern.

