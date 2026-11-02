# Attention Matching KV Compaction

> **Fold destination** (BRF-T1-F15, BRF-T1-1, route 1a, 2026-11-02): absorbs 3 handoff(s) as `## Track:` sections at the end of this file (`multiscreen-attention-evaluation.md`, `streaming-llm-baseline.md`, `triattention-kv-selection.md`). The body above the first track is the former `attention-matching-kv-compaction.md`.

**Status**: active, refreshed 2026-06-19 — L1-L4+L4b merged; evidence refresh remains open
**Created**: 2026-04-13 (via research intake)
**Updated**: 2026-11-01 (KV-1 source-log audit partial result; exact router-key and launch identity gaps remain)
**Categories**: kv_cache_optimization, inference_serving
**Scratch**: `/mnt/raid0/llm/tmp/refactor-kv1-20261101/` · worktrees: `/mnt/raid0/llm/worktrees/refactor-kv1-*/`

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

P1 complete. P2 validated on Qwen2.5-7B (2026-04-13): **2x=1.000 (lossless), 5x=0.906, 10x=0.807**. Early layers compress perfectly; deep layers need adaptive strategy.

**2026-06-19 wrap-up review**: keep this handoff active. Native L1-L4+L4b production work is done, but no new Attention Matching rollout decision should be made from the April Qwen2.5-only premise. The next useful evidence gate is a current-stack refresh against production long-context/coding traffic, including the current Qwen3.6-era stack and any live Coder-32B comparison still relevant to the workload. Do not load additional models during unrelated clean measurement windows; queue this for the next approved inference window.

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
| P2 | Refresh against current production long-context/coding workload, including Qwen3.6-era stack and any still-relevant Coder-32B coding comparison | MEDIUM | P1 |
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
- **Still (intake-708, arXiv 2606.07878)** — the published *amortized-synthesis* challenger to the deployed *selection* path. Tracked in summary-token-attention-readiness.md (GPU-CPT-gated, no public code as of 2026-06-05). NB: our deployed default compactor is Expected-Attention (TriAttention); even the AM path here is selection+beta, not synthesis, so Still has no deployed synthesis counterpart to benchmark today. (This handoff/experiment still say 'production-consolidated-v3'; production is now v5 — functionality carried forward across rebases.)

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

## Progress checklist

- [x] P1 port HighestAttnKeys-fast + L1-L4/L4b native llama.cpp integration merged (81c9ad1ec, 7784b3d9c) ✅
- [ ] P2 refresh validation against current-stack long-context/coding workload (Qwen3.6-era + Coder-32B), inference-window-gated
- [ ] P3 compare AM quality vs Expected Attention at 5x/10x/20x
- [ ] P4 test AM + Hadamard q4_0 stacking quality under dual compression
- [ ] Deferred L4c: true NNLS attention scoring (graph modification) - not yet needed

## Prefix-cache ownership and the 2026-08-20 intake findings

**Ownership gap, filed here because nothing else owns it.** No ACTIVE handoff owns `PrefixRouter`
or the orchestrator prefix-cache path. The original owner, `handoffs/archived/radix-attention.md`,
is ARCHIVED "VERIFIED 2026-01-09" with its Next Steps stopping at *"Integration testing with live
llama-server"* — i.e. the integration was never done. `repl-turn-efficiency.md` touches
`PrefixRouter` only incidentally (both boxes ticked, compacted). Adopting the rows below is what
closes that gap; re-home them if a better owner appears.

Evidence: intake-1196#record (KVFlow, dive-overturned), intake-1207 (SGLang Rust tree-core cluster).

**Already fixed in this pass (2026-08-20), recorded so the reasoning is not re-derived:**

- [x] **KV-0a — Every KV slot save was failing; fixed.** ✅ 2026-08-20 `prefix_cache.py` built the filename with `os.path.join(...)`,
  producing a `/`-containing string; llama-server rejects those via
  `fs_validate_filename(allow_subdirs=false)` before it concatenates `--slot-save-path`. Proof it
  never worked: the 75 retained slot artifacts on disk are **all** `kv_migrate_*` from the sibling
  `concurrency_aware.py` path, and there are **zero** `slot_<id>_<hash>.bin` files anywhere. Fixed by
  emitting a bare filename (`_slot_state_filename`, mirroring `concurrency_aware._slot_filename`).
  Two compounding defects fixed alongside: the restore path did a **client-side** `os.path.exists()`
  on a **server-side** filename, and both backend methods caught `httpx.RequestError`, which does
  **not** cover `HTTPStatusError` — so a 4xx propagated instead of returning `False` as documented.
- [x] **KV-0b — Roles sharing one llama-server were evicting each other; fixed.** ✅ 2026-08-20 Under `shared_with`, several roles
  resolve to one physical server, but the legacy loop built a **separate `PrefixRouter` per role**,
  each allocating `id_slot` in `[0, num_slots)` from its own private LRU — so two roles both emitted
  `id_slot=0` and silently clobbered each other, unobservably. Now one router per physical URL
  (`_router_for`), matching the shape the fleet layer already had. 3 regression tests added.
- [x] **KV-0c — `radix_cache.py` deleted** (480 lines + shim). ✅ 2026-08-20 Verified dead: its only two importers were the
  file importing itself. It also carried an unexercised stale-slot bug and a docstring claiming path
  compression it did not implement. 20 tests that exercised the unwired module went with it — green
  tests over dead code manufacture exactly the false confidence this handoff exists to avoid.

**Open rows:**

- [ ] **KV-1 — Count DISTINCT hot prefixes per window against resolved slot count, per role and per
  shared server, from existing logs. ZERO INFERENCE.** This gates everything below. Production
  `num_slots` is **2**; `coder_primary` and `coder_escalation` both declare `slots: 1`. **At slots=1
  there is no eviction order to improve**, and at 2 it is a coin flip. This gate has now been named
  in two consecutive passes (intake-1182's dive, then intake-1196#record) with an unchanged blocker — by
  the CLAUDE.md recurrence check that is proof it was never blocked. Do it before anything else here.
  - Partial zero-inference result, 2026-11-01: see [KV-1 prefix working-set audit](../../docs/reports/kv1-prefix-working-set-audit-20261101.md). The log contains 130 rows, 125 dispatched with fingerprints (98 at `c2048`, 27 shorter), and five undispatched rows without fingerprints. Grouping by launch ID where available, one 8083 launch shared across two roles had a `c2048` distinct-prefix upper bound of 4 against 2 slots. Other endpoints lack launch IDs, so their per-port results cannot establish physical-server grouping. There was no `coder_primary` traffic. The logged `c2048` fingerprint does not identify exact router-key counts: records fingerprint the raw caller wire prefix, while `PrefixRouter` canonicalizes and hashes its first 256 characters. KV-1 remains open.
  - [ ] **KV-1a — Record a privacy-preserving hash of the exact canonical PrefixRouter key and immutable server launch identity in serving records, then rerun KV-1 on a complete window.** Retain no raw prompt or canonical key.
- [x] **KV-2 — Pass `role` and `session_id` into `PrefixRouter.get_slot_for_prompt`.** ✅ 2026-10-29 [belief: cc] [source: epyc-orchestrator@9c507dfff650aa1999b9e5816fc4c8216fb5bd45; test: epyc-orchestrator/tests/unit/test_prefix_cache.py] Both are
  already present at the call site (`model_server.py:91` requires `role`;
  `inference.py:755-767` attaches the session id) and the router receives **only prompt text**; role
  is consulted at exactly one hardcoded frontdoor-REPL bypass. We are discarding for free the
  identity signal KVFlow had to invent a client-ID scheme to recover.
  Landed on orchestrator main as `9c507dfff650aa1999b9e5816fc4c8216fb5bd45`: both inference paths
  pass identity; slot metadata records the latest caller on hits/misses and clears on reuse/clear.
  Shared-prefix matching, LRU and default-off pinning are unchanged. 63 tests passed; five live-server
  cases skipped. Full make gates stopped at missing shellcheck; no runtime reload or model call.
- [ ] **KV-3 — Evaluate switching to llama.cpp's NATIVE token-level LCP slot selection.** It is
  strictly better than a 256-char SHA-256 exact match, already shipped, and currently **overridden**
  rather than off: `slot_prompt_similarity` defaults to `0.1f`, but our explicit `id_slot` takes
  tier-one priority ahead of it (`server-context.cpp:1541` before `:1549`). Config + call-site
  change, no kernel work. **Gated on KV-1 and on the shared-router fix having landed.** Note our
  Python hit-rate counter is a proxy for a quantity it does not measure — `n_past` is decided in C++.
- [ ] **KV-4 — If KV-1 shows working set > slot count, THEN consider workflow-aware eviction.**
  Replace the LRU victim choice with an argmax over steps-to-execution, sourced from the delegation
  DAG that already exists (`parallel_step_executor.py:75` `compute_waves()` — the wave index **is** a
  steps-to-execution value, already cycle-checked; `routes/delegate.py:86-98` enumerates the whole
  plan at `dry_run=True` for zero LLM calls). **Record the ceiling on the row: 1.11×**, which is
  KVFlow's own eviction-only ablation on an H100; the other 1.18× comes from prefetching we cannot
  port (llama-server slot restore is on the shared task loop and a failed restore is destructive).
  **NOT the RLM tree and NOT the autopilot loop** — neither materialises children in advance.
- [x] **KV-6 — Measure `canonicalize_prompt` before optimising anything downstream of it.** ✅ 2026-10-29 — measurement from 2026-10-29, archived by ROOT `f3b55734266efb2a92a51c6f90d68141b278a440`, [native timing and replay](../../artifacts/compute/codex3-kv6-canonicalize-20261031/SHA256SUMS). [belief: cc] It makes
  - 2026-10-31 prior-work hygiene only, **excluded from today’s code quota**. The work predates today; evidence filing or verification is not a new implementation. See [operator tick audit](../../artifacts/compute/codex3-tick-audit-20261031/tick-audit-20261031.md). [no-belief: quota-accounting correction]
  SEVEN full-length passes (3 string scans + 4 `re.sub`) over prompts of tens of KB and then
  **discards everything past char 256**. At the original filing it had not been measured: grepping both prefix-cache
  files for timing primitives returns 3 hits, all docstring prose, zero code. Cheap to instrument,
  and it may dominate the routing cost the rest of this section is trying to improve.
  2026-10-31 archival note, no quota credit. [belief: cc] Retained 2026-10-29 shared-host synthetic R6 timing (CPUs 30–31, nine batches per shape, 4,014 timed calls): at 256/10,000/100,000/1,000,000 input characters, plain median wall time per call was 0.0076/0.2786/2.8303/31.0525 ms and mixed date/UUID/newline median was 0.0073/0.2419/2.4110/24.2662 ms. Raw nine-batch distributions and calls are retained; these are not process CPU times, production latency or throughput. Original source file SHA-256 `8f075d9dd5716abb7838be75779c57c4031663a58eebbfd080efff0f39e929cb` differs from current ORCH `9ca85117` file SHA `964a1fd427aeb31adc8b0bb54b42a08c0d6a58d0547d5ea12bcc8bb45dca2536`, but the exact function source SHA `060c526d3f239d08628d3a9dda20a18efbcac55245269baab08ebedc7a5d9a8b` and eight synthetic outputs independently match. The default serving path bypasses this opt-in router; no downstream optimization follows from these timings alone. [Raw and replay evidence](../../artifacts/compute/codex3-kv6-canonicalize-20261031/SHA256SUMS). The existing `VB-INF05-KV6-TIMING-WRITE` remains open; no original measurement warrant was retrofitted. [belief: cc]
- [ ] **KV-7 — Price the prefix-cache interaction BEFORE adopting any prefix+sliding mask.** The
  intake-864 long-OUTPUT ruling applies; vLLM disables prefix caching under this mask, and
  Appendix A confirms prefill is NOT reduced — so the mask's saving is decode-side only while the
  cost is a disabled prefix cache. Gated on KV-1 and KV-6 (a working-set count and a
  `canonicalize_prompt` measurement are both inputs to the price). intake-1315#00, intake-1315#record.
  - *Selection-class note (2026-09-07)*: selection-class KV methods buy **zero** KV memory (8.38MB
    on-device, identical to full attention, because they hold the FULL cache) and therefore cannot
    serve this handoff's 10× KV-**memory** objective at all — they leave the candidate set.
    `intake-1334#05`.
- [x] **KV-5 — Correct `wiki/kv-cache.md`** ✅ 2026-08-20 (done in the wrap-up wiki sweep) so KVFlow is named as the ORIGIN of workflow-aware KV
  residency, with its own venue (NeurIPS 2025), its own 1.11× ablation and its Apache-2.0
  implementation — not solely as the denominator of PBKV's self-reported 1.26×. Note also that 1.26×
  **on static workflows** means KVFlow retains most of the gain on declared topologies, which is
  exactly what our delegation path is; filing it as "beaten" inverts the reading for our own use case.

## Track: multiscreen-attention-evaluation
<!-- gate: none -->

> Folded from `handoffs/active/multiscreen-attention-evaluation.md` @ `e1a5e5226974` on 2026-11-02 (BRF-T1-F15, route 1a, operator D1/D5; retired row INF-42 → INF-05). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Multiscreen Attention — Evaluation for EPYC Inference

**Status**: ACTIVE — G1 CLOSED 2026-10-24 (no long-context recall drop to 128K on the frontdoor; ceiling result, see G1 RESULT); remaining rows open
**Created**: 2026-04-04 (via research intake)
**Updated**: 2026-10-24 (G1 finished on the MI210 path; previous: 2026-08-27 recovery at 161/200)
**Categories**: kv_cache, inference_serving, ssm_hybrid
**Scope note**: This handoff expanded beyond Multiscreen evaluation into a comprehensive sub-quadratic attention mechanism survey. Multiscreen-specific evaluation is Section 1. Log-Linear GDN readiness tracked in [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).

#### Start here — 2026-10-24

G1 is CLOSED (see the G1 RESULT under [Tasks](#tasks)): 100% recall at every length to 128K and 9/9 at 256K on the frontdoor, q8_0 KV equal to f16. That is a ceiling result on a needle task, so it rules out collapse-scale amnesia but does not bound subtler loss. The remaining open rows in this handoff are the next work; the architecture watch below is historical context.

#### Historical survey status — 2026-04-21

Backburner survey — awaiting pretrained weight releases for the prioritized architectures (Diff Attn V2, MoBA, Multiscreen). No upstream movement detected since 2026-04-14 survey. Section 1 (Multiscreen evaluation) remains gated on Section 2 priority items shipping weights first.

#### Objective

Evaluate the Multiscreen architecture (arXiv:2604.01178) as a potential next-generation attention mechanism for EPYC inference. Multiscreen replaces softmax attention with absolute query-key screening, achieving 40% parameter savings and 2.3-3.2x latency reduction at 100K contexts.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-256 | Screening Is Enough — Multiscreen Architecture | high | new_opportunity |
| intake-464 | FlashAttention-3 (arXiv:2407.08608) | medium | worth_investigating — canonical Hopper attention paper (added 2026-04-26). DGX Spark prep + CPU producer/consumer thread-split analog candidate. |

#### Key Claims to Verify

- 40% parameter savings at comparable validation loss
- 2.3-3.2x inference latency reduction at 100K context
- Near-perfect retrieval at context lengths far beyond training
- Stable training at learning rates where Transformers diverge

#### Relevance to EPYC

1. **vs Delta Net**: Our Qwen3.5 hybrid models use Delta Net (gated linear attention). Multiscreen preserves the attention paradigm but makes it sub-quadratic — potentially compatible with existing KV cache and speculation infrastructure (unlike Delta Net which broke all tree speculation)
2. **Parameter efficiency**: 40% fewer parameters for same quality would shift model selection calculus — smaller models could replace larger ones
3. **Long context**: Our models degrade at long context; Multiscreen claims stable performance beyond training length
4. **llama.cpp compatibility**: Key blocker — no GGUF support exists. Would require implementing screening mechanism in ggml

#### Open Questions

- Will any major model provider (Google, Meta, Qwen) adopt Multiscreen architecture?
- Can screening be implemented efficiently in ggml/llama.cpp?
- Is the 2.3-3.2x speedup achievable on CPU (EPYC) or only GPU?
- How does Multiscreen interact with KV cache quantization (Hadamard)?
- Does screening mechanism support speculative decoding?

#### Blockers

- No pretrained Multiscreen models available for download
- No GGUF/llama.cpp implementation exists
- Paper is very new (April 2026) — needs community validation

#### Notes

This is a WATCH item, not an implementation item. Monitor for:
1. Community reproduction of results
2. Model releases using Multiscreen architecture
3. llama.cpp PRs implementing screening mechanism

#### Expanded Attention Mechanism Cluster (2026-04-12 research intake)

Three additional cross-head attention mechanisms identified during deep-dive. Together with Multiscreen, these form a 2025-2026 cluster of alternatives to standard MHA. All require pretraining — no retrofit possible.

| Mechanism | Intake | FlashAttention | Key Benefit | EPYC Notes |
|-----------|--------|----------------|-------------|------------|
| **IHA** (Interleaved Head Attention) | intake-333 | YES (mixes before attention) | +112% RULER at 16K multi-key retrieval. MHA ⊂ IHA strictly. | **Priority watch** — FlashAttention-compat is key for our llama.cpp stack |
| **MEA** (Explicit Multi-head Attention) | intake-342 | YES (HLC on K/V) | 50% KV cache reduction via virtual heads. GroupNorm critical. | KV compression directly useful for memory-constrained inference |
| **KHA** (Knocking-Heads Attention) | intake-343 | YES (absorbed at inference) | **Zero inference overhead** (linear variant absorbed into projections). V-only interaction. | Prefer KHA-trained models when available — zero cost at inference |

**Ranking for EPYC**: IHA (most expressive, FlashAttention-compat) > MEA (KV compression bonus) > KHA (zero inference cost, but lower expressivity) > Multiscreen (most radical, no implementations)

**Monitor for**: GGUF implementations of models trained with any of these mechanisms. None currently available.

---

#### Literature Survey: Sub-Quadratic Attention for CPU Inference (2025-2026)

Compiled 2026-04-14. Target: AMD EPYC 9655 (192 threads), all-CPU inference via llama.cpp.

##### 1. Mechanisms Requiring Pretraining (Architecture Changes)

**Native Sparse Attention (NSA)** — DeepSeek, Feb 2025 (arXiv:2502.11089)
ACL 2025 Best Paper. Three parallel branches: compressed attention (coarse), selected attention (fine-grained), sliding window (local). Sub-quadratic scaling; substantial speedups on 64K sequences. Foundation for DeepSeek V3.2's DSA. vLLM/SGLang have GPU kernel support (SM90+ only). No llama.cpp support; GPU-centric design (block-sparse CUDA kernels).
- CPU applicability: **low** (hardware-aligned to GPU tensor cores)
- llama.cpp compat: **unlikely** without major porting
- Verdict: **monitor_only** — wait for CPU-friendly reformulation

**MoBA (Mixture of Block Attention)** — MoonshotAI, Feb 2025 (arXiv:2502.13189)
Applies MoE routing to attention blocks. Queries dynamically select relevant KV blocks. 6.5x prefill speedup at 1M tokens, 16x at 10M. Llama-8B-1M-MoBA model exists (128K-1M context). Deployed in Kimi production. FlashMoBA kernel achieves 14.7x over FA2 for small blocks. Open source: github.com/MoonshotAI/MoBA.
- CPU applicability: **medium** (block-sparse structure amenable to CPU, but kernels are CUDA)
- llama.cpp compat: **possible** — standard transformer weights, block selection could be implemented in ggml
- Verdict: **worth_investigating** — Llama-8B-1M-MoBA model could be converted to GGUF for testing

**Differential Transformer V2** — Microsoft, 2026 (HuggingFace blog)
Computes attention as difference of two softmax maps, canceling noise. V2 matches baseline decoding speed, uses standard FlashAttention (no custom kernels). 0.02-0.03 lower loss at 1T tokens. Needs ~65% of baseline params/tokens for equivalent quality.
- CPU applicability: **high** (standard attention ops, just doubled query heads with subtraction)
- llama.cpp compat: **possible** — requires new head-pairing logic in ggml, but ops are standard
- Verdict: **worth_investigating** — FlashAttention compatibility makes ggml port feasible

**Multiscreen** — Apr 2026 (arXiv:2604.01178)
Replaces softmax with absolute query-key screening. 40% param savings, 2.3-3.2x latency reduction at 100K. Very new (2 weeks old); no reproductions, no community benchmarks, no implementations outside the paper. No models available.
- CPU applicability: **unknown** (screening op simplicity suggests potential, but unverified)
- llama.cpp compat: **unlikely** near-term — requires novel ggml op
- Verdict: **monitor_only** — too early, no artifacts to test

##### 2. Training-Free / Retrofit Methods (Apply to Existing Models)

**CSAttention (Centroid-Scoring)** — Apr 2026 (arXiv:2604.08584)
Training-free sparse attention for reusable contexts. Pre-computes centroid scores offline, applies sparse selection at decode time. 4.6x speedup at 128K context over best accurate baseline. GPU-optimized score accumulation.
- CPU applicability: **low** (GPU-friendly design, prefill/decode split less relevant for CPU)
- llama.cpp compat: **possible** but niche — most useful for batched GPU serving
- Verdict: **monitor_only**

**HiP Attention** — 2024 (arXiv:2406.09827)
Hierarchical pruning of attention scores, sub-quadratic. Older but more mature. Applicable as drop-in during inference.
- CPU applicability: **medium** (pruning reduces compute, but overhead of hierarchy unclear on CPU)
- llama.cpp compat: **possible**
- Verdict: **monitor_only**

##### 3. llama.cpp Attention Support Status (as of Apr 2026)

| Feature | Status |
|---------|--------|
| GQA (Grouped Query Attention) | **Supported** — default for Llama 3, Mistral, Qwen |
| MQA (Multi-Query Attention) | **Supported** |
| Flash Attention (CPU) | **Limited** — no improvement for text gen (memory-bound); helps prefill. Head size 64/128 only |
| Sliding Window Attention | **Partial** — basic SWA works; interleaved SWA (Gemma 2/3) is open issue #12637 |
| MLA (Multi-head Latent Attention) | **Supported** — for DeepSeek V2/V3 models |
| NSA / MoBA / Diff Attention | **Not supported** — no PRs found |
| Multiscreen | **Not supported** — no implementations anywhere |

##### 4. KV Cache Compatibility Assessment

| Mechanism | KV quant (q4/q8 + Hadamard) | Speculative decoding | KV eviction |
|-----------|----------------------------|---------------------|-------------|
| NSA | Incompatible (custom KV layout) | Unknown | Built-in (sparse selection) |
| MoBA | Compatible (standard KV, sparse routing) | Likely compatible | Compatible (block-level eviction natural) |
| Diff Attn V2 | Compatible (standard KV) | Compatible (standard decode loop) | Compatible |
| Multiscreen | Unknown (novel KV access pattern) | Unknown | Unknown |
| CSAttention | Compatible (standard KV) | Incompatible (offline prefill assumption) | N/A (own sparsity) |

##### 5. Priority Ranking for EPYC CPU Inference (REVISED 2026-04-29 PM)

1. **DSA (DeepSeek V3.2 + GLM-5.1)** — **TOP PRIORITY (active)**. PR #21149 by fairydreaming is an active draft with CPU/CUDA/Vulkan backends working. Tracked in [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) with three contribution sub-tracks (D1 smoke test, D2 prompt-processing follow-on PR, D3 AVX-512BW indexer). 2-models-for-1 leverage.
2. **Lightning Attention (Ant Group Ring-mini/flash-linear-2.0)** — **v1 PORT COMPLETE; ROLE DECISION ACTIVE**. Tracked in [`lightning-attention-port.md`](model-evaluation-queue.md#track-lightning-attention-port). Existing `GGML_OP_GATED_LINEAR_ATTN` path reached coherent Ring-mini Q4_K_M decode; live work is production role selection and profile-gated follow-up, not another port.
3. **Diff Attn V2** — Highest priority among "awaiting pretrained" mechanisms. Standard ops, FlashAttention-compatible, no custom kernels. When pretrained models ship, GGUF conversion should work with minor ggml additions. KV cache and speculation compatible.
4. **MiMo-V2-Flash** — Already supported in upstream llama.cpp (PR #18328 merged Dec 2025). Sizing-blocked (309B/15B-active estimates ~10 t/s on EPYC, below deployment threshold), but MTP-as-drafter pattern is independently transferable. Track PR #22493 (V2.5) — if it ships smaller, becomes immediately deployable.
5. **MoBA** — Llama-8B-1M-MoBA exists now. Block-sparse structure could be implemented in ggml. Standard KV layout preserved. Test GGUF conversion of existing model.
6. **IHA/MEA/KHA** (from existing stub) — FlashAttention-compatible variants that preserve standard inference stack.
7. **Summary-Token cluster (KSA + GSA)** — Readiness tracker only. [`summary-token-attention-readiness.md`](model-evaluation-queue.md#track-summary-token-attention-readiness). All require CPT; gated on checkpoint release or GPU acquisition.
8. **NSA** — Monitor only for CPU. GPU-aligned design; wait for CPU-friendly derivative.
9. **Multiscreen** — Monitor only. No artifacts, no reproductions, too early.

##### Key Finding

No sub-quadratic attention mechanism has a llama.cpp implementation today, but **we have full fork control** (`production-consolidated-v3`) and can implement custom ggml ops.

##### Custom ggml Implementation Feasibility

| | Diff Attn V2 | MoBA | Multiscreen |
|---|---|---|---|
| **Spec clarity** | Yes (full pseudocode) | Yes (open-source code) | Partial (no ref impl) |
| **New ggml ops** | 0 (all ops exist) | 2 (top-k, online softmax merge) | 2-3 (TanhNorm, trim-square, cos mask) |
| **Patch size** | ~200-400 LOC | ~500-800 LOC | ~800-1200 LOC |
| **Models available** | No (Microsoft pending) | No (requires cont. training from Llama) | No |
| **Risk** | Low | Medium | High |

**Diff Attn V2 implementation path** (priority #1):
- Q projected to 2h heads (doubled), K/V remain standard
- After standard FlashAttention: split outputs into even/odd pairs per GQA group
- `out = attn1 - sigmoid(lambda) * attn2` where lambda is a small W_lambda projection (d_model → h)
- Changes: GGUF converter (new W_lambda tensor), model loader, attention forward pass
- All ops already exist in ggml (matmul, softmax, sigmoid, subtract, multiply, strided view)
- **Can build now, test when models ship**

**MoBA implementation path** (priority #2):
- Router scores blocks by `dot(q, mean(K_block))`, selects top-k + causal block
- Full attention on selected blocks, results combine via online softmax
- Needs two new primitives: top-k selection, online softmax merge
- Performance gains demonstrated at 1M+ tokens — unclear benefit at our 8K-32K range

**Multiscreen** — monitor only. No reference implementation, partial spec, high risk.

#### Research Intake Update — 2026-04-14

##### New Related Research
- **[intake-354] "Memory Caching: RNNs with Growing Memory"** (arxiv:2602.24281)
  - Relevance: Bridges fixed-memory RNNs (O(L)) and quadratic Transformers (O(L²)) via cached state checkpoints. Maps the growing-memory RNN design space (O(L) fixed → O(NL) segmented → O(L²) full attention)
  - Key technique: Gated Residual Memory (GRM) — input-dependent gating over cached segment checkpoints. Also: Sparse Selective Caching (MoE-style top-k checkpoint retrieval)
  - Reported results: +12.8pp S-NIAH-2 on Titans at 16K; +20pp SWDE/FDA retrieval; 0.9 ppl improvement at 760M scale
  - Delta from current approach: Training-time modification only. **Deep dive correction**: state copy is ~5% of speculation round-trip cost (50-100ms); the real bottleneck is 220ms/token sequential verification through 30 Delta Net layers. MC's segmented caching would save ~25-50ms against ~1320ms verification for 6 tokens — marginal. Value is architectural context, not a practical optimization path for current models.

- **[intake-356] "Log-Linear Attention"** (arxiv:2506.04761) — **HIGH RELEVANCE**
  - Relevance: **ICLR 2026** paper applying log-linear complexity directly to Gated DeltaNet (75% of our production stack). Authored by Songlin Yang (DeltaNet creator) + Tri Dao (FlashAttention creator) + Yoon Kim
  - Key technique: Replaces fixed-size hidden state with logarithmically growing set of hidden states; O(L log L) complexity; <0.4% parameter overhead
  - Reported results: Log-Linear Gated DeltaNet outperforms standard Gated DeltaNet in perplexity and reasoning benchmarks; outperforms layer-matched Transformer across all metrics
  - EPYC inference impact: (1) State size 4-10x reduction (~2GB → ~200-500MB) enables sequential replay approach for speculation; (2) O(log L) growth makes 1M+ context feasible on same hardware; (3) matmul-rich form maps to existing ggml infrastructure — no GPU-centric sparse kernels needed
  - Reference implementation: github.com/HanGuo97/log-linear-attention (278 stars, Python/Triton, training-only)
  - llama.cpp effort: ~2-3 weeks (new model variant class, new ggml ops, GGUF metadata). Blocked on pretrained model availability.

##### Updated Priority Ranking (incorporating deep dive)

1. **Diff Attn V2** — Highest near-term priority. All ops exist in ggml, can build now. Standard attention models.
2. **Log-Linear Gated DeltaNet** — Highest strategic priority for EPYC specifically. Directly upgrades 75% of our production stack's architecture. CPU-friendly (matmul-rich, no sparse kernels). Blocked on pretrained models. Tracked in: [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).
3. **MoBA** — Existing model available for GGUF testing. Benefit unclear at our 8K-32K context range.
4. **IHA/MEA/KHA** — FlashAttention-compatible, standard inference stack preserved.
5. **NSA** — GPU-only. Monitor.
6. **Multiscreen** — Too early. Monitor.

#### Research Intake Update — 2026-04-28

##### New Related Research

- **[intake-488] "Speculative Decoding with Mamba (companion to 'The Mamba in the Llama')"** (github.com/itsdaniele/speculative_mamba; arxiv:2408.15237)
  - Relevance: Pure-Mamba target + Mamba draft spec-dec (mamba-2.8b target, mamba-130m draft). Closest existing reference for SSM-on-SSM speculation, but our hybrid SSM targets (Qwen3.5, Qwen3-Next) use Delta-Net not Mamba2.
  - Key technique: K-step lookahead drafting with frozen recurrent state; CUDA-graph-on-draft to amortize launch overhead.
  - Reported results: ~68% acceptance on a single English-prose example with K=3, fp16 (anecdotal, not benchmarked).
  - Delta from current approach: CUDA-only, pure-Mamba (not Delta-Net hybrid) — no kernel ports to llama.cpp CPU. Verdict: not_applicable for current EPYC hardware.

- **[intake-489] "SpecMamba: Accelerating Mamba Inference on FPGA with Speculative Decoding"** (arxiv:2509.19873)
  - Relevance: First FPGA accelerator co-designing Mamba SSM with spec-dec; algorithmic core (memory-aware hybrid backtracking for SSM hidden-state rollback) addresses the central pain point that has blocked spec-dec on hybrid SSMs in our stack.
  - Key technique: Memory-aware hybrid backtracking + FIFO-based tree verification with tiling + parallel-linear/serial-SSM dataflow.
  - Reported results: 2.27× over GPU baseline, 2.85× over prior FPGA Mamba (LightMamba), 5.41× higher energy efficiency vs GPU on AMD Versal VHK158/VCK190.
  - Delta from current approach: FPGA hardware-bound; no CPU port path. Filed for awareness — confirms SSM-rollback is the right algorithmic frame for if/when hybrid-SSM spec-dec is reopened.

- **[intake-490] "Hybrid Models Meet SGLang: More than Full Attention"** (pytorch.org blog, Dec 2025)
  - Relevance: Engineering recipe for serving hybrid SSM+attention models with prefix caching + spec-dec. Multiscreen-class architectures with linear-attention layers face the same KV-pool-vs-state-pool sizing problem that this blog catalogs. Verdict: **adopt_patterns**.
  - Key technique: HybridReqToTokenPool, HybridLinearKVPool (skip KV alloc for linear layers), MambaRadixCache (hybrid prefix-tree), Elastic Memory Pool via CUDA VMM, EAGLE/MTP rollback over SSM state.
  - Reported results: 324.57 tok/s with 4.231 avg acceptance length on Qwen3-Next-80B-A3B-FP8 (H200, bs=1, MTP-4 + topk=4 + draft_tokens=8).
  - Delta from current approach: Pure CUDA-/H200-targeted; kernels do not port to llama.cpp CPU. Architectural lessons (per-layer skip-KV remap, elastic Mamba/KV pool, in-place-state rollback workaround) are directly applicable when scoping llama.cpp-side support for hybrid SSM serving.
  - Caveats (Tier 2b): per-request memcpy cost for in-place state snapshots not benchmarked; agentic-workload cache pressure (sgl-project/sglang #20144) — Mamba states can be 1000× larger than KV states and trigger evictions; multi-tenant numbers under contention not published.

- **[intake-491] "Mamba Drafters for Speculative Decoding"** (arxiv:2506.01206; Findings of EMNLP 2025)
  - Relevance: External Mamba drafter for Transformer target — constant-memory drafter that beats Pythia drafters of equal/larger size at long context. Worth investigating whether the principle generalizes to hybrid-SSM targets in our stack.
  - Key technique: Mamba-130M external drafter + MAB-optimized tree-shape selector for test-time tree-search drafting.
  - Reported results: GSM-8K 149.46 tok/s (vs Pythia-410M 119.67); MT-Bench accept length 3.91 (vs EAGLE 3.85); LongBench 8k accept length 2.80 with throughput preserved while Transformer drafters degrade.
  - Delta from current approach: SSM-drafter-for-Transformer-target principle is novel for our stack; MAB tree-shape selector is immediately applicable to existing tree spec-dec infra without the SSM piece. Caveats: Mamba hidden-state backtracking limitation; tree verification requires workarounds; hyperparameter-sensitive.

#### Research Intake Update — 2026-04-29

##### New Related Research

- **[intake-502] "Kwai Summary Attention Technical Report"** (arxiv:2604.24432, Kuaishou OneRec team, submitted 2026-04-27 — full extraction via local LightOnOCR pipeline 2026-04-29) → **READINESS TRACKER**: [`summary-token-attention-readiness.md`](model-evaluation-queue.md#track-summary-token-attention-readiness) (joint with intake-507 GSA)
  - Relevance: Architectural sub-quadratic attention in the Section-1 cluster (NSA / MoBA / Diff Attn V2 / Multiscreen / Log-Linear GDN). "Intermediate path" between Full attention (linear KV, quadratic compute) and minimal-KV linear-attention (constant state): maintains linear KV growth but compresses historical context into learnable summary tokens at chunk size k=8. Complexity O(n/k).
  - Key technique: Summary tokens injected at chunk boundaries; summary tokens see only their own chunk; text tokens see local **Sliding Chunk Attention** (SCA — chunk-aligned, distinct from token-level SWA) plus distant summary tokens. Hybrid-KSA = 3:1 KSA-to-Full layer ratio. Decode KV cache uses contiguous-tensor layout (Current Chunk + Sliding Chunk Text + Summary Token Buffer) avoiding gather/concat in hot path.
  - **Open-source training scripts released**: [github.com/Kuaishou-OneRec/KSA](https://github.com/Kuaishou-OneRec/KSA). No model checkpoints yet.
  - Reported results (CPT setting, init from Qwen3-4B-base, 85B tokens):
    - RULER-4K **92.97**, RULER-32K **86.65**, RULER-128K **71.67** — Hybrid-KSA wins all lengths
    - RULER-128K: Hybrid-KSA beats Full by **+5.81**, beats Hybrid-SWA by **+5.40**
    - MMLU 70.73 / CMMLU 73.29 (vs Full 71.83 / 75.00; Hybrid-Linear collapses to 64.33 / 68.41)
    - MBPP 62.20 — best across all configs **including Full**
    - NIAH-128K: Multivalue **98.75 vs Full 88.12 (+10.63)**, VT **90.50 vs 60.50 (+30.00)**, FWE **65.84 vs 51.66 (+14.18)**, SQuAD **42.50 vs 30.00 (+12.50)**
  - Reported results (from-scratch, 1.9B params, 400B tokens at 8K→32K→64K→128K):
    - RULER-128K: Hybrid-KSA **65.35 vs Full 48.75 (+16.60)**, vs Hybrid-GDN 59.87 (+5.48), vs Hybrid-SWA 56.64 (+8.71)
    - GSM8K **59.14 vs Full 48.29 (+10.85)**, MATH **36.92 vs Full 23.38 (+13.54)**
    - HumanEval **31.71** (best), MBPP **36.40** (best); average across all benchmarks: Hybrid-KSA **54.80 vs Full 49.44**
    - End-of-training loss: Hybrid-KSA **1.524** < Hybrid-GDN 1.534 < Hybrid-SWA 1.550 < Full 1.572
  - Inference efficiency (Figure 10): KV cache at 128K **7.5 GB vs Full 18.6 GB (2.5× smaller)**. Decode throughput at 16K: **1.06× Full** (Hybrid-SWA 0.73×, Hybrid-Ring-Linear 0.81× — KSA is the only sub-quadratic baseline that does NOT lose decode speed).
  - Per-token KV cache cost (Table 1, h=128 d=128 g=8 d_c=512 d_r=64): KSA at k=8 → **12.5%** of MHA size (8× compression); **KSA + GQA → 0.78%** (~128× compression); **KSA + MLA → 0.22%** (~455× compression). Composability with GQA / MLA is fully orthogonal.
  - Ablations (Table 7): default N=128 chunks, S=8 chunk size, KSA:Full=3:1 ratio. N>128 yields diminishing returns at long context (RULER-64K drops to 65.73 at N=256 vs 76.35 at N=128). S=32 best for general reasoning, S=8 best for long-context.
  - **Three-stage CPT recipe** (genuinely actionable, even decoupled from KSA): (1) summary token adaptation with layer-wise MSE + distribution-wise KL distillation from full-attention teacher; (2) parameter annealing via λ-schedule that interpolates independent summary weights into shared LLM weights, then drops them; (3) staged sequence-length extension (32K→64K→128K). Read for ideas if/when we run our own continual-pretraining work.
  - Delta from current approach: Same architectural blocker class as Multiscreen/MoBA/NSA — needs pretraining or full CPT. CPT is feasible with released scripts BUT compute-bound (no CPU path; ~85B tokens). On EPYC today: monitor only. Distinct from our deployed retrofit methods (AM compaction, Expected Attention) which work on pretrained transformers without architecture change. Closest training-time cousin: **Log-Linear GDN** (intake-356, sub-linear state growth) — both are "intermediate path" architectures with matmul-rich CPU-friendly forms.
  - Tier 2b caveats: (1) authors' own ablations show N=256 hurts long-context — chunk count is workload-dependent; (2) Hybrid-Linear baseline collapse on MMLU confirms general criticism that fixed-size linear state loses general capability — KSA mitigates this with growing summary state but is still in the same lineage; (3) no head-to-head comparison vs MoBA / NSA / Diff Attn V2 / Log-Linear GDN — only vs Hybrid-GDN (standard, not log-linear); (4) generalization to LongBench-v2 / non-RULER tasks not reported; (5) numbers entirely self-claimed, no third-party reproduction (paper is 2 days old).
  - Verdict: **monitor_only** (worth_investigating). Slot below Multiscreen in priority for *EPYC actionability* but **above** Multiscreen for *training-recipe value* (CPT distillation pattern is reusable). No new handoff stub — fits this section. Activation gates: (a) Kuaishou releases pretrained checkpoint, OR (b) llama.cpp port emerges, OR (c) GPU acquisition unlocks running their CPT recipe ourselves.
  - Adjacent paper surfaced during expansion (NOT yet ingested): **arxiv:2604.20920 "Forget, Then Recall: Learnable Compression and Selective Unfolding via Gist Sparse Attention"** — closest conceptual analog ("gist tokens" = "summary tokens" same paradigm, also April 2026). Recommend separate intake invocation if the cluster is to be expanded.

##### Same-day expansion (2026-04-29) — 3 sibling papers ingested via Tier 1 reference-chasing from intake-502

- **[intake-503] "Every Attention Matters: An Efficient Hybrid Architecture for Long-Context Reasoning"** (arxiv:2510.19338, Ling Team / Ant Group, October 2025) → **v1 PORT COMPLETE; ROLE DECISION ACTIVE** tracked in [`lightning-attention-port.md`](model-evaluation-queue.md#track-lightning-attention-port) (completed details preserved in its completed ledger)
  - Relevance: **HIGH**. Hybrid Lightning-Attention + softmax architecture with empirically-tuned linear:softmax ratios (M=4 for 16B Ring-mini, M=7 for 104B Ring-flash). Direct competitor framing to KSA's hybrid-KSA. Open weights on HuggingFace + open-source FP8 LingHe kernels.
  - Key claim: ~1/10 inference cost vs 32B dense; AIME-25 86.51% / GPQA-D 74.49% (Ring-flash). Training efficiency +50% via FP8 LingHe.
  - Caveats: pure linear attention underperforms on recall-heavy tasks (authors acknowledge); BF16 KV-state precision drift requires FP32 accumulation in recurrent path — non-trivial in our quantized KV path; performance brittle to decay-coefficient choice; **NO RULER/NIAH/LongBench results published** — long-context claims rest on indirect reasoning benchmarks.
  - **Active-port verdict (UPDATED 2026-05-28)**: prior framing "no llama.cpp kernel today, defer adoption" was wrong — `GGML_OP_GATED_LINEAR_ATTN` already exists in our experimental fork (`ggml/src/ggml-cpu/ops.cpp:10605`); Lightning Attention is mechanically a constant-`g` GLA. v1 port completed and reached coherent Ring-mini Q4_K_M decode. Ring-mini remains active only for role decision, broader quality, same-family drafter, and profile-gated L5 follow-up.
  - Credibility: 4. Open-weight + open-kernel release at industrial scale.

- **[intake-505] "MiMo-V2-Flash Technical Report"** (arxiv:2601.02780, Xiaomi LLM-Core Team, January 2026)
  - Relevance: **MEDIUM**. 309B total / 15B active MoE with hybrid 5:1 SWA-to-Global ratio (128-token window) + learnable attention-sink bias. ~6× KV cache + attention compute reduction at matched quality across 32K-256K. **MTP head as spec-decoding drafter** is the most directly transferable finding (3.6 acceptance length, 2.6× speedup, mirrors DeepSeek-MTP).
  - Key claim: 73.4% SWE-Bench Verified, 71.7% Multilingual; NIAH-Multi 96.7% at 256K with 128-token SWA window.
  - Caveats: 309B too large for our stack at FP/BF16 (Q4 ~155 GB feasible only with heavy KV compression); 5:1 SWA + sink-bias scheme not in llama.cpp; community reports inconsistent instruction-following / unreliable tool-calling; 15B-active knowledge-capacity ceiling vs DeepSeek-V3.2/Kimi-K2; authors caveat "preliminary" architectural exploration; reward-hacking documented on SWE-Bench (Appendix B).
  - Verdict: **worth_investigating** — Tier-1 read for the attention/KV handoffs; MTP-as-drafter pattern reusable. Not adopt_component (model too large + custom attention not in llama.cpp), not new_opportunity (no novel mechanism we'd port wholesale).
  - Credibility: 3. Open-weight release + open repo (github.com/XiaomiMiMo/MiMo-V2-Flash).

- **[intake-506] "DeepSeek-V3.2: Pushing the Frontier of Open Large Language Models"** (arxiv:2512.02556, DeepSeek-AI, December 2025) — **CRITICAL CROSS-REFERENCE: KSA explicitly cites V3.2 as following "the same first-principle of sequence-level KV-cache compression"** → **ACTIVE TRACKER**: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) (PR #21149 stabilization + 3 contribution sub-tracks)
  - Relevance: **MEDIUM** (capped by hardware blockers, not by intellectual relevance — this is one of the most important entries in the cluster).
  - Technique: **DeepSeek Sparse Attention (DSA)** — two-stage attention combining a Lightning Indexer (FP8, head-weighted scoring, block-64 quantized key cache) with fine-grained top-k=2048 token selection on top of MLA. Changes core attention cost from O(L²) to ~O(L·k). MLA + DSA composition (MLA-DSA) is orthogonal: MLA compresses per-token KV dim, DSA selects which tokens to attend.
  - Key claim: V3.2-Exp matches V3.1-Terminus on GSM8K/GPQA-Diamond (vLLM validation); V3.2-Speciale claims gold-medal at IMO 2025 + IOI 2025, comparable to GPT-5 / Gemini-3.0-Pro on reasoning.
  - Caveats: (1) llama.cpp DSA forward-pass kernel does NOT exist — indexer tensors load but C++ falls back to dense MLA, erasing speedup (same blocker as GLM-MoE-DSA, PR#19460 merged dense-only); (2) FP8 block-quantized key cache is CPU-unfriendly compute pattern; (3) RoPE-in-indexer implementation discrepancy reported in early versions; (4) V3.2-Exp slightly regresses on Humanity's Last Exam vs V3.1; (5) DSA top-k=2048 is fixed hyperparameter — generalization to short-context/non-retrieval workloads not characterized; (6) 671B-class MoE — Q4_K_M ~380 GB only feasible local quant.
  - Verdict: **worth_investigating** — high-leverage monitor target. Three reasons: (a) we already have V3.2 chat template upstreamed in our fork (`../completed/llama-cpp-fork-rebase.md` commit 1c0d9081f); (b) any DSA implementation effort simultaneously unlocks GLM-5/5.1; (c) cross-reference target for KSA + GLM-MoE-DSA work. Action: track llama.cpp DSA indexer PR as highest-leverage external event.
  - Credibility: **5** (highest in this expansion). Open-weight + DeepSeek track record + KSA cites + GLM-5 cites.

##### Sibling not_applicable (recorded for completeness)

- **[intake-504] "LongCat-Flash-Thinking-2601"** (arxiv:2601.16725, Meituan, January 2026) — 560B MoE with ~27B active; Domain-parallel expert training + DORA RL framework + Heavy Thinking. **Not applicable** for EPYC: 560B too large for our 1.1 TB CPU even at 27B active; no quantization/kernel/serving contribution; Heavy Thinking and DORA are training-side techniques. Logged for completeness — no handoff updates from this entry.

##### Late-day expansion (2026-04-29 PM) — Gist Sparse Attention (closest KSA sibling)

- **[intake-507] "Forget, Then Recall: Learnable Compression and Selective Unfolding via Gist Sparse Attention"** (arxiv:2604.20920, Mao / Li / Fox — Stanford, April 2026) → **READINESS TRACKER**: [`summary-token-attention-readiness.md`](model-evaluation-queue.md#track-summary-token-attention-readiness) (joint with intake-502 KSA)
  - Position: same April-2026 gist-token cluster as KSA (intake-502), but distinct mechanism. Where KSA keeps **all** summary tokens visible to text, GSA hard-selects **top-k chunks** and "unfolds" them to restore the raw KV pairs alongside the gists. Unselected chunks are entirely invisible — a sharper compression/fidelity trade-off.
  - Hierarchical variant **H-GSA** (gist-of-gist) achieves **log-linear decode complexity** — the only mechanism in this cluster that scales naturally to 1M+ context on EPYC's 1.1 TB RAM headroom.
  - Reported wins at high compression: LongBench at 32× → GSA 44.07 vs ActivationBeacon 38.30 (+5.77). RAG with KV-cache reuse on Llama3.2-1B at 8× → GSA 48.07 vs KVLink 41.20 (+6.87). 8× finetuned: GSA on some HotpotQA tasks **surpasses Full-FT** (selective unfolding as inductive bias filtering distractors).
  - Code released: github.com/yuzhenmao/gist-sparse-attention. Tested only on Qwen2-7B and Llama3.2-1B (no 30B+, no MoE, no RULER beyond passkey).
  - Caveats: Stage 1 CPT REQUIRED; no zero-shot retrofit; Selective Unfolding's hard top-k starves the model on queries needing many-chunks-weakly retrieval (KSA's persistent-summary fallback handles this softer); hardware-efficiency caveat — irregular memory access at decode erases theoretical FLOP savings on real GPUs and is even worse on CPU without KSA's contiguous-tensor decode layout.
  - **vs KSA mechanism summary**: KSA = persistent summaries, all visible, soft compression. GSA = hard top-k + selective unfolding, restores raw on selected, sharp trade-off. Different points in the same design space.
  - Verdict: **monitor_only** alongside KSA. Activation gates identical: (a) checkpoint released on a model we serve, OR (b) GPU compute path for CPT, OR (c) llama.cpp general support for dynamic top-k chunk masking + raw-KV restoration. No new handoff stub.

#### Research Intake Update — 2026-05-22

##### New Related Research

- **[intake-598] "HRM-Text: Efficient Pretraining Beyond Scaling"** (arxiv:2605.20613, Sapient Intelligence + MIT, submitted 2026-05-20)
  - Relevance: First application of the **Hierarchical Recurrent Model** (dual-timescale fast/slow recurrent) to general text pretraining — extends the puzzle-domain HRM lineage (intake-584 HRM, intake-585 mechanistic critique, intake-583 TRM, intake-582 GRAM) into LM territory. Architecturally adjacent to the recurrent / sub-quadratic cluster this handoff tracks (Multiscreen, MoBA, NSA, Log-Linear GDN, KSA, GSA). Same gating pattern as **Ouro [intake-332]**: non-transformer recurrent architecture, weights public, but no llama.cpp path.
  - Key technique: Slow strategic + fast execution recurrent layers; **MagicNorm** (forward/backward horizon asymmetry under TBPTT); **warmup deep credit assignment** (progressive BPTT depth 2→5 steps); **task-completion / response-only loss** on instruction-response pairs with PrefixLM bidirectional attention masking; `<think>...</think>` content stripped pre-training.
  - Reported results — HRM-Text 1.15B: MMLU **60.7%** (Llama3.2-3B 58.0%), ARC-C **81.9%** (Qwen3.5-2B 81.0%), GSM8K **84.5%** (Llama3.2-3B 77.7%), DROP **82.2%** (Gemma3-4B 60.1%), MATH **56.2%** (Ouro-1.4B 22.4%). Trained on ~40B effective tokens (100-900× fewer) at ~$1,500 H100 cost (96-432× less) than the comparators' scaling-law targets. **Open weights** at huggingface.co/sapientinc/HRM-Text-1B; **code** at github.com/sapientinc/HRM-Text (FSDP2 training scaffold, eval, ckpt conversion).
  - Delta from current approach: Distinct from this handoff's primary cluster — HRM-Text is **recurrent**, not sub-quadratic attention. The architectural blocker class is the same (no llama.cpp path; transformers-library CPU inference is the only short-term option), so the monitoring/eval framework here applies, but the architectural lineage is HRM/TRM/GRAM/Ouro, not Multiscreen/MoBA/NSA/KSA/GSA. Recorded here because the handoff's stated scope is the broader "sub-quadratic / non-transformer architecture evaluation" survey (see scope note in header) and there is no dedicated recurrent-LM evaluation handoff today.
  - **Contradicting evidence** (recorded in intake-598; significant): (1) **apples-to-oranges supervision-regime comparison** — HRM-Text trains on instruction-response pairs with task-completion loss (closer to instruction-tuned than base pretrained), but the 100-900× efficiency headline is quoted vs *base* Llama3.2-3B / Qwen3.5-2B / Gemma3-4B; a matched comparison vs the *Instruct* checkpoints is the eval that would settle the claim; (2) `<think>...</think>` stripping plausibly biases toward final-answer-only benchmarks, which is exactly the reported eval suite; (3) authors self-disclose "residual contamination may still persist" with no quantitative leakage probe; (4) "April 2026 independent verification" cited in Sapient marketing predates the paper's 2026-05-20 arXiv submission — provenance unclear; (5) no peer review yet.

##### Recommended Actions

These are the deep-dive actions queued from intake-598 — slotted here because this handoff already coordinates the "evaluate a candidate non-transformer architecture before any production move" pattern across Multiscreen, KSA, GSA, Lightning-Attention, DSA.

- [ ] **HRM-1**: Pull `huggingface.co/sapientinc/HRM-Text-1B` and run a **fair head-to-head against `Qwen3.5-1.7B-Instruct`** on our benchmark suite (MMLU, ARC-C, GSM8K, MATH, DROP — the same reported suite, plus our REPL/tool benchmark for cross-coverage). The apples-to-oranges concern is the headline-killer; resolve it before any downstream decision. Inference path: transformers-library CPU (no llama.cpp option today). Effort: low — public weights, public eval scripts, runs on EPYC CPU at maybe 5-10 t/s like Ouro. Owner: TBD. **Gates**: HRM-2, HRM-3.
- [ ] **HRM-2**: Decide explicitly whether HRM-Text architecture warrants **llama.cpp investment** (custom dual-timescale recurrent kernels in our fork) versus accepting **transformers-library CPU inference** at lower t/s for a cheap-draft / cheap-specialist role. Same decision shape we hit with Ouro [intake-332] and Log-Linear GDN (see [`log-linear-gated-deltanet-readiness.md`](log-linear-gated-deltanet-readiness.md)) — if HRM-Text and Ouro share enough recurrent infrastructure, one llama.cpp investment could unlock both. Tie-in: if HRM-1 collapses the headline efficiency, HRM-2 auto-resolves to "no investment". **Gated by**: HRM-1 result.
- [ ] **HRM-3**: **Defer any production-side role assignment** (cheap-first worker, draft, specialist) until HRM-1 lands. The 100-900× claim is too dependent on the supervision-regime comparison framing to drive deployment decisions without a fair eval — same posture this handoff takes for Multiscreen / KSA / GSA / DSA pending checkpoint or kernel availability.

##### Activation Gates

- HRM-1 result is the primary gate. Two outcomes:
  - **(A) Headline survives matched-supervision eval** (HRM-Text-1B competitive with Qwen3.5-1.7B-Instruct on our suite): promote to a dedicated readiness handoff alongside `log-linear-gated-deltanet-readiness.md`, schedule HRM-2 llama.cpp decision, consider transformers-library CPU deployment as a cheap-specialist short-circuit.
  - **(B) Headline collapses** (HRM-Text-1B underperforms Qwen3.5-1.7B-Instruct once both are on instruction-tuned footing): close HRM-2/HRM-3, downgrade intake-598 verdict from `worth_investigating` to `not_applicable` with the calibration result recorded.

#### Research Intake Update — 2026-05-29

##### New Related Research — LFM2 / LFM2.5 family (Liquid AI)

> **Updated 2026-05-29 after deep dive** → `research/deep-dives/lfm2-lfm25-family-deep-dive.md`. Two corrections to the initial skim are folded in below: (1) it is **NOT a drafter**; (2) `lfm2moe` is **already merged in our llama.cpp HEAD**, but no production role has a gap it fills, so intake-651 was downgraded `adopt_component → worth_investigating`.

- **[intake-651] LFM2.5-8B-A1B** (HuggingFace model card, `LiquidAI/LFM2.5-8B-A1B`, license `lfm1.0`) — **worth_investigating; standalone-only, NOT a drafter**
  - 8.3B total / **1.5B active** hybrid MoE: 24 layers = 18 double-gated **LIV (Linear Input-Varying) short-conv** layers + 6 **GQA** attention layers, 32 experts / Top-k=4. 131K context, **own 128K `lfm2` BPE vocab**.
  - **`lfm2moe` support is already MERGED in our llama.cpp HEAD** (`LLM_ARCH_LFM2MOE`, `LLM_TYPE_8B_A1B`, `Lfm2MoeForCausalLM`; upstream PR #16464 + follow-ups, all ancestors of `production-consolidated-v5`). Official GGUF `LiquidAI/LFM2.5-8B-A1B-GGUF`, Q4_K_M = 5.16 GB. **Support is present and no port is expected** (arch + converter merged; not yet smoke-loaded with a local GGUF) — opposite of the Ling-Linear/Lightning-Attention situation, which needed a custom port.
  - **Not a drafter** (struck): its own 128K `lfm2` vocab is incompatible with every production target tokenizer (Qwen3.6 frontdoor/coder, gemma4 ~256K worker), and spec-dec requires exact tokenizer match (chapter 01); all production spec-dec is self-speculation (gemma4 MTP / REAP+draft) anyway — no external-drafter slot. Realistically a cheaper/lower-quality **standalone** tier; no current role (frontdoor/coder=Qwen3.6, worker=gemma4 MTP, architect=Qwen3.5-122B, ingest=Qwen3-Next-80B) has a gap it fills.
- **[intake-650] LFM2.5-8B-A1B announcement** (Liquid AI blog) and **[intake-652]** Liquid complete model library (catalog: LFM2.5-1.2B/350M dense, VL/Audio multimodal, sub-1.2B Nanos incl. **LFM2-ColBERT-350M** retrieval + Extract/RAG specialists).
- **[intake-653] "LFM2 Technical Report"** (arXiv:2511.23404, Liquid AI) — discovered via expansion.
  - **Relevance to THIS handoff is the one reusable insight**: the report's central NAS finding is that a **minimal conv+GQA hybrid is sufficient on-device, and adding SSM / linear-attention operators does NOT improve aggregate quality** there. This appears to conflict with the "linear-attention/SSM hybrids win" thesis tracked here and in `log-linear-gated-deltanet-readiness.md` / intake-503 (Ling-Linear) / Minimax-01 — **but the deep dive confirms it is a clean regime boundary, not a refutation**.
  - **Reconciliation (confirmed against the paper text)**: the report explicitly scopes the claim to "the **on-device regime at 350M–2.6B params with 32K context**" and states it "does not claim SSMs/linear-attention are generally unnecessary — only that their benefits diminish under strict edge latency constraints." Ling-Linear/Minimax wins are the opposite regime (16B–104B, long-context 100K+). The two **bound each other's regime**. Vendor-sourced; headline CPU t/s are Apple M5 Max / Ryzen AI Max+ (146–253), **NOT EPYC 9655**.

##### Next Actions

- [ ] **LFM2-1 (revised)**: **No bench, no port, no deployment.** `lfm2moe` arch support is present in our HEAD (not yet smoke-loaded) and there is no production gap — do not queue a llama-bench run (respects `feedback_no_concurrent_inference`: no role to justify it). Revisit ONLY if a "cheap-first worker" / "edge-companion" / router-triage role is opened (per `project_stack_simplification`, `feedback_dont_dismiss_creative_uses`) — then evaluate LFM2.5-8B-A1B Q4_K_M (5.16 GB) as a **standalone** candidate; its calibrated-abstention behavior (the 63.47 AA-Omniscience non-hallucination is an RL avg@k *abstention* artifact, paired Accuracy 8.67 / Index −24.70 — NOT a knowledge win) could suit a triage stage that must reliably say "escalate / I don't know."
- [x] **LFM2-2 (done 2026-05-29)**: Recorded LFM2's "minimal conv+GQA beats SSM-hybrid on-device" finding as a **regime boundary** (above) — does NOT override intake-503/Minimax long-context findings (different scale/context regime). `LFM2-ColBERT-350M` (intake-652) flagged to [`internal-kb-rag.md`](knowledge-pipelines.md) embedder-choice question as a candidate late-interaction reranker — **with the caveat that it is PyLate/PLAID-only (NOT GGUF/llama.cpp/ONNX), so a PyLate-path eval candidate, not a drop-in for the existing GTE-ModernColBERT/MaxSim plumbing.**


#### Research Intake Update — 2026-07-14

##### New Related Research
- **[intake-813] "Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories"** (arxiv:2606.03979 — Behrouz, Hashemi, Mirrokni; Titans-family)
  - Relevance: medium — same author line already tracked here (Behrouz/Titans; cf. intake-354). Introduces a periodic **"sleep"** phase that consolidates fragile in-context memory into stable parametric knowledge via a **Continuum Memory System** + Self-Knowledge Seeding, with catastrophic-forgetting control by parameter expansion/(de)activation.
  - Key technique: the **Hope** architecture (Titans-family self-modifying deep-memory model); multi-stage consolidation claims monotonically improving continual learning; near-perfect BABILong to 10M tokens.
  - Reported results: AIME-24 79.2 / AIME-25 69.0 (Qwen3-8B + Sleep); ARC few-shot 80% vs SEAL 72.5%.
  - Delta from current approach: this is a **training-time custom architecture** (RL rewards, GKD, parameter expansion) with **no OSS implementation and no llama.cpp/CPU path** — architectural signal for the sub-quadratic/Titans line, not a portable or benchable component. Verdict: worth_investigating. (NB: the paper's "SEAL" = MIT Self-Adapting LMs, a name-collision with the repo's SEAL control vectors — unrelated.)

##### Monitoring note (no action, no checkbox)
intake-813 is tracked as a continuation of the Behrouz/Titans architecture line (with intake-354); **no bench/port/checkbox** — architectural monitoring only, consistent with the LFM2 "no bench, no port" discipline above and the corpus anti-bloat posture (cf. intake-798 "deliberately no checkboxes added"). Revisit only if a Titans-family artifact becomes OSS/llama.cpp-loadable AND a production gap opens.

#### Research Intake Update — 2026-07-20 (revised same day after deep dive)

> The first version of this section credited R-SWA as a novel attention variant. A prior-art review overturned that. Superseded text removed; the corrected assessment follows.

##### **[intake-864] "Unlimited OCR Works"** (arxiv:2606.23050, Baidu, 2026-06-22, MIT) — **rebranded prior art, no action**

**Mechanism (verified, §3.4.1):** `N(t) = P ∪ D_n(t)` where `P = {1..L_m}` is a globally-visible prefix (visual tokens + prompt) and `D_n(t)` is a causal sliding window of width `n=128` over the decode region. KV cache is bounded at `L_m + n`. All decoder layers use it — no interleaved full-attention layers, unlike Gemma-2/3 or Llama-4 iRoPE.

**This is not new.** It is the Λ-mask, under a new name:

| Prior work | Relation |
|---|---|
| Longformer (2004.05150), ETC (2004.08483), BigBird (2007.14062) | sliding window + **global attention on task-specific tokens**, explicitly including the prompt segment. R-SWA = the causal specialisation with random blocks = 0 and global set = prefix. |
| LM-Infinite (2308.16137) | named the **Λ-shaped mask**: leading tokens globally visible + local window. Training-free. |
| StreamingLLM (2309.17453, ICLR'24) | attention sinks — R-SWA is **StreamingLLM with k = \|prompt+image\| instead of k=4**, with the mask trained in. |
| TrOCR / Donut / Nougat encoder-decoder | decoder cross-attends all encoder outputs + self-attends generated text. For an OCR model this is the most damning framing: R-SWA re-derives cross-attention + a windowed decoder inside a decoder-only mask. |

**The paper cites none of it.** All 35 references are OCR/VLM/infrastructure; grep for `longformer|bigbird|streaming|sink|infinite` returns zero hits. Its related-work section claims *"current models all see it [the KV cache] grow continuously with decoding contexts"* — false as written, and it is the load-bearing novelty claim.

**Evidence quality is weak.** The word "ablation" does not appear in the paper. The +6.22 headline vs DeepSeek-OCR confounds the mask with 4,000 continued-training steps and ~2M new labelled samples; there is no vanilla-SWA run and no window-size sweep. The 35%-faster claim is measured at **prefill length 10** (§6, explicit) — with `L_m=10` the mechanism degenerates to near-pure SWA, its maximum-advantage case; in the paper's own 10K-visual-token regime the compute advantage largely evaporates and only the memory advantage survives.

**What is actually real:** the narrower empirical finding that a **128-token self-window suffices for reference-grounded transcription** — the global set carries the meaning, the window only carries a cursor. Prior Λ-mask work kept 1K–4K windows and treated the sink as a numerical-stability hack. That inversion is a legitimate contribution, as are the FA4 `mask_mod` / FlexAttention / Triton kernels. It is an engineering result, not an architectural one.

##### Why this is not a lever for us (no bench, no port, no checkbox)

1. **Wrong axis.** R-SWA is a long-**output** optimisation. Our long-context pressure is long **input** (RAG, agent history, document prefills) where `T ≪ L_m`, so the bounded-decode-cache saving is ~nothing — while costing prefix caching (vLLM disables prefix caching for this model outright: *"R-SWA decode-phase KV is not a pure causal function of the prefix"*).
2. **Agentic loops break it structurally.** Tool results arrive mid-generation and are semantically reference material, so they must join the resident prefix — `L_m` then grows unboundedly and the constant-cache property evaporates.
3. **We already have the generic version.** llama.cpp `--keep` / context-shift has provided resident-prefix + sliding-window-over-generation semantics since 2023 (eviction with RoPE re-indexing rather than a mask). No engine exposes R-SWA as a general attention type; vLLM gates it behind the model config, and llama.cpp PR #24975 is hard-wired to `deepseek2-ocr`.
4. **It needs a decoding-time crutch.** Every port ships `no_repeat_ngram_size=35` / DRY to stop the model looping — the predicted failure of a 128-token self-window, unmentioned in the paper. Its own long-horizon metric (Distinct-35) is a repetition metric.
5. **Direct collision with our MTP line.** PR #24975 documents that speculative/lookahead multi-token decode **never latches** and silently falls back to full causal, plus it bumps `LLAMA_SESSION_VERSION`/`LLAMA_STATE_SEQ_VERSION` and forces F32 V-cache. Draft, 0 maintainer reviews in 4 weeks.

**Better comparison point for text**, if the long-output regime ever matters to us: **KARA** (arxiv:2607.01237, 2026-07) keeps the prefix intact and *adaptively compresses* the generated window instead of hard-truncating it, and is training-free — the right shape for CoT/reasoning, where distant self-reference actually matters. Worth its own intake if we revisit.

#### Research Intake Update — 2026-08-22 (Stage-2b, intake-1287#record / intake-1281#record)

Compute classes: **Z** zero-compute, **G** compute-gated (names the measurement, the owning handoff,
and the result that opens the gate), **B** blocked-on.

##### STANDING HAZARD — CoT-SFT breaks long-range recall in hybrid linear-attention models

**This is not a SALA note. It applies to any hybrid we post-train or fine-tune, and our production
frontdoor is one: Qwen3.6-35B-A3B, 30 Gated DeltaNet + 10 full attention.**

`arXiv:2606.11052`, *"Attention Amnesia in Hybrid LLMs: When CoT Fine-Tuning Breaks Long-Range Recall,
and How to Fix It"* (Zhou, Zhu, Xu, Li, Chen, Wang, Guo; v1 2026-06-09). Abstract, verified at the
primary source by the dive: CoT-SFT *"systematically degrades long-context recall in hybrid
linear-attention models… For example, HypeNet-9B on NIAH-S2@256K decreases from 67.2 % to 9.4 %."* The
proposed fix, **QK-Restore**, is **training-free**: restore only `W_Q` and `W_K` from the pre-SFT
checkpoint. Independence is mixed but favourable — mostly external, though one author is also a SALA
co-author and HyPE's first author, so it reads as genuine post-hoc self-critique rather than a rival's
attack.

**Why it is a hazard for us and not a curiosity.** The damage is invisible to every instrument we
routinely run: it is a *recall* failure at *long* context produced by a *post-training* step, and our
standing quality case is perplexity plus short-context evals. Perplexity does not move. The frontdoor
is a 256K-context serving role. Nothing in the repo has ever measured it. `G1` below closes that, and
needs no port, no new model and no SALA.

**Scope note, so the hazard is neither over- nor under-claimed.** The 67.2 → 9.4 figure is HypeNet-9B,
not our model, and third-party numbers gate nothing here (MEASUREMENT.md). It is a reason to
*measure*, and the measurement is cheap. `arXiv:2606.11052` is a **hop-4 source and is not ingested**;
it reaches us through intake-1287#record, whose diver verified the abstract at the primary source.
Recommend it for a wave 3.

##### The strongest published argument AGAINST replacing our 10 full-attention layers with sparse ones

Pair the hazard above with `arXiv:2606.15378`, *"Rethinking the Role of Efficient Attention in Hybrid
Architectures"* (Qiao, Xu, Xiao, Su, Zhou, Chen, Xu, Han, Liu). Abstract, verified: **"long-range
retrieval is mainly carried by full attention, whereas efficient attention shapes its optimization
trajectory"**, plus **"different hybrids eventually converge to comparable long-context performance
under sufficient training"** and a named **"Large-Window Laziness"** effect in which larger SWA windows
*delay the formation of retrieval heads in the full-attention layers*.

Three things make this unusually strong as a counter-argument, and one weakens it:

1. **Seven of its nine authors are SALA co-authors.** It is same-lab, and it is adversarial to SALA's
   own premise — SALA has no full attention above 8,192 tokens (`sparse_config.dense_len`). A finding
   that cuts against the authors' own product is worth more than one that flatters it.
2. It directly contradicts the architectural move the SALA branch proposes for us: our 10 full-
   attention layers are, on this account, *where the long-range retrieval lives*. Replacing them with
   sparse ones spends exactly the resource the paper says does the work.
3. Its second quote also deflates SALA's specific recipe: if hybrids converge under sufficient
   training, the 1:3 ratio is not what produces the result — and SALA ablates that ratio nowhere.
4. **Weakening it:** it is an abstract-level reading (the dive verified the abstract, not the body),
   and same-lab provenance cuts both ways.

**Consequence, recorded so it is not re-derived:** the "swap the dense minority for a sparse minority"
direction is **argued against by the closest available literature, including its own proponents'
lab** — before any throughput question is even reached. That ordering matters: `B8` in
[lightning-attention-port.md](model-evaluation-queue.md#track-lightning-attention-port) is gated on numerical correctness, and this
row says that even a clean correctness result does not make the architectural swap attractive.
See also the fifth GDN branch-map row in
[log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).

##### Tasks

- [x] **G1 (G) — the CoT-SFT amnesia probe, on our own production model.** *Highest-value compute row
      of the wave: no port, no new model, no SALA, no training.*
      **RESULT 2026-10-24 (3c4ca599; filler `inf42-g1-gpu`, MI210, production v10 store `gpu-20260921-ffc1bac82`, residency proven every chunk at 38 GiB; `/mnt/raid0/llm/tmp/inf42-g1-20261023/gpu/VERDICT.txt`): FINAL GATE CLOSED.** Frontdoor Qwen3.6-35B-A3B-MTP Q8_0, greedy, seed 42, `cache_prompt=false`. q8_0 KV: **100% recall at 4K, 32K, 64K and 128K (50/50 each, every depth 0.1-0.9)** and 9/9 at the 256K diagnostic; mean drop vs 4K 0.0 pp, CI [0.0, 0.0] at every length. f16-KV control: 100% at 4K and at 128K (drop 0.0 pp), so q8_0 KV costs nothing here. **Caveat: ceiling on the whole grid.** The probe shows no amnesia on this needle task, but it cannot rank configurations or bound a subtler long-context loss; a harder probe (multi-hop or distractor-dense) would be the next step if one is needed. The f16 phase first ended rc=7 as a FALSE failure (empty chunk gated for residency, 4K trial seeded with the 256K estimate); fixed in `jobs/g1_lib.sh` and `jobs/g1_gpu_job.sh` before the 10-24 grant.
      - 2026-10-28: drop vs 4K control (q8_0 KV, paired 95% bootstrap CI) vs predeclared gate '>= 10 pp below the 4K control at 32K/64K/128K, CI excluding zero, surviving f16 control' → measured 0.0 pp, CI [0.0, 0.0] at 32K/64K/128K (50/50 each; 4K 50/50), 256K diagnostic 9/9, f16 control 4K and 128K 100% → capability (gate CLOSED, no defect; ceiling result, cannot bound subtler loss). Covers the gate fully (the 2026-08-27 PAUSED note is superseded: all 36 unscored 128K trials, f16 control and 256K were run on the MI210). Box already ticked. Evidence: /mnt/raid0/llm/tmp/inf42-g1-20261023/gpu/VERDICT.txt. [belief: cc]

      - [x] **Recover the live G1 execution without discarding persisted recall evidence.** ✅
        2026-08-27 — checkpointed 161 scored trials, captured logs/scripts/session provenance,
        quiesced the malformed half-instance launch, and resumed the first missing trial under a
        held full-machine claim. Terminated only the stuck session's captured wait/monitor children,
        then used OpenCode's displayed two-Escape interrupt confirmation to return its parent turn
        to an idle, operator-steerable composer; detached experiment daemons were untouched.

      - [x] **Fence the post-G1 compute handoff.** Before treating lock release as safe, re-resolve
        the identities of the legacy INF-40 lease waiter (`3847760`, deadline ~15:03Z) and EVL-08
        lease waiter (`3999604`, deadline ~15:57Z) and confirm they expired or were deliberately
        quiesced. Preserve the authoritative queued `inf40-moespec-bsweep` region-lock job
        (`774647`), which should acquire only after G1 releases `q0`–`q3`. PIDs are checkpoint
        identities, not reusable names; verify PID/start/cmdline at action time.
        - *(2026-10-24, 3c4ca599.)* Obsolete and closed: none of `3847760`, `3999604`, `774647` exists any more (`ps` 2026-10-24), and G1 was finished on the MI210 GPU path under filler grants, not by releasing a held `q0`-`q3` claim.

      **Live execution checkpoint — 2026-08-27 07:46Z.** The initial launcher copied the 48-thread
      `:8080`/`:8180` serving-half argv but omitted that shape's CPU affinity, memory policy and
      canonical environment. Trials 1–161 were preserved as individually scored JSON records (all
      161 exact-match hits); the interrupted, unpersisted trial 162 is being rerun. The continuation
      uses the solo-batch/full production CPU shape: `-t 96`, `taskset -c 0-95`,
      `numactl --interleave=all`, canonical OMP variables and `GGML_IQK=1`, under a held four-region
      `region-lock`. This probe measures recall, not speed: phase-A scores remain evidence, while
      elapsed-time/throughput fields must be stratified across the explicit recipe boundary. The
      checkpoint, logs, original scripts, sanitized OpenCode transcript, process manifest, hashes
      and takeover provenance are under
      `/mnt/raid0/llm/epyc-inference-research/data/frontdoor-amnesia-g1-checkpoints/20260827T074200Z-pre-corrected-resume/`.

      **Wrap-up checkpoint — 2026-08-27 10:56Z.** Q8 is 163/200 persisted and 163/163 exact-match;
      the active 128K trial was 75% through prompt processing. The corrected wrapper still holds
      the authoritative `q0`–`q3` region-lock and advisory lease and remains autonomous through
      Q8, the required f16 control, summarization, verified cleanup and lock release. The original
      OpenCode owner subsequently completed two operator follow-up turns and is now idle and
      responsive with no child processes, so the takeover session requires no further steering.
      One throughput caveat remains: although the live process carries `-t 96`, CPUs `0-95`,
      `numactl --interleave=all`, the canonical OMP environment and `GGML_IQK=1`, a live-window
      `numastat` sample still placed 32.28/41.89 GiB (~77%) on node 3. This does not change the
      recall evidence, but no timing field from this phase is authoritative; INF-43 T5 / N25 P2-3
      already owns the multi-node locality gate and tolerance decision.

      **Measurement.** RULER **S-NIAH-2** — essay haystack, single numeric magic value, question asks
      for the value — on the production frontdoor artifact
      `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf` (30 GDN + 10 full attention), at context
      lengths **4K (control) / 32K / 64K / 128K**. Grid: 5 needle depths {0.1, 0.25, 0.5, 0.75, 0.9} ×
      10 samples = **50 trials per length, 200 total**. Exact-match on the magic value. **Persist per
      question** — each persisted unit is a drain point.

      **The 4K control arm is not optional**: the gate is stated as a *comparison against short
      context*, so without it there is nothing to compare to and the row cannot be scored.

      **Harness — already on disk, no new tooling.** `epyc-inference-research`
      `scripts/benchmark/long_context_adapters.py` ships both halves (read read-only 2026-08-23):
      `NeedleAdapter` (`suite_name = "needle_parameterized"`) carries the Paul Graham essay corpus and
      takes `context_lengths` and `needle_positions` as constructor arguments — the 128K arm is a
      parameter, its default list merely stops at 65536; `RULERAdapter` carries the key/value needle
      sentence, question framing and `exact_match` scoring but builds its haystack from synthetic
      `wordNNNN` noise, which is an S-NIAH-**1** shape. **S-NIAH-2 is `NeedleAdapter`'s essay haystack
      with `RULERAdapter`'s numeric needle** — a composition, not a new harness.

      **Server configuration — three deviations from production argv, each mandatory and each for a
      stated reason.**
      1. **`-np 1 -c 262144`.** The `:8070` frontdoor runs `-np 4 -c 262144`, i.e. **65,536 tokens per
         slot** — the 128K arm *cannot run there at all*. Verified from `/proc` 2026-08-23: PID 2052930
         (`:8070`) is `-np 4`; PIDs 2195076 (`:8080`) and 2195842 (`:8180`) are `-np 1 -c 262144`.
         Those two serve live traffic — **do not restart a frontdoor half to obtain this**; stand up a
         dedicated instance on a free port, and coordinate with whichever session owns the compute
         plane (reload ownership sits with the owning session, not with the requester).
      2. **`--spec-type none`.** Production runs `--spec-type draft-mtp --spec-draft-n-max 4`. Whether
         multi-token verification is byte-exact is precisely the open question DF2-6 owns; it must not
         ride inside a recall measurement.
      3. **`cache_prompt=false`**, greedy (`temperature 0`), **seed 42**. A needle sweep that reuses
         prefix cache across trials measures the cache, not the model.
      Everything else stays at production values — `--reasoning off`, the terse chat template,
      `-ub 8192`, `--flash-attn on`, `--mlock --no-mmap`, `--device none`.

      **The KV-quantization control is not optional either.** Production is `-ctk q8_0 -ctv q8_0`, and
      "quantized KV damaged long-context recall" predicts the same sign as "CoT-SFT damaged
      long-context recall". So: run the full grid at production `q8_0/q8_0`, then re-run **the 4K
      control plus the shortest length at which a drop appears** at `-ctk f16 -ctv f16`. If the drop
      survives f16 KV it is not a KV-quant artifact. This is a *control*; it is not a re-opening of the
      KV axis, which `G2`–`G5` in
      [tq3-quantization-evaluation.md](quantization-and-low-bit.md#track-tq3-quantization-evaluation) own.

      **Gate — what opens it.** A recall score **materially below the same probe at short context**,
      made operational as: **≥ 10 percentage points below the 4K control at any of 32K / 64K / 128K,
      with the paired 95 % bootstrap CI over needle placements excluding zero**, and surviving the
      f16-KV control. At 50 trials per cell the binomial SE near p ≈ 0.9 is ≈ 4.2 pp, so 10 pp is
      ≈ 2.4 SE; the published effect (67.2 → 9.4, i.e. 57.8 pp) is 5.8× the threshold, so the gate is
      not straining to detect the phenomenon it was written for. *Report the per-length curve and the
      per-depth breakdown, never a single aggregate* — a depth-localised failure is a different defect
      from a uniform one and the aggregate hides both.

      **If the gate opens this is a PRODUCTION DEFECT, not a research curiosity.** The frontdoor is a
      256K-context serving role that would then be unable to recall at half that. Escalate to the
      operator with the curve; do not file it to a research backlog.

      **What the probe can and cannot attribute — state this in the write-up.** It measures the
      *symptom* on the deployed artifact. It cannot attribute the symptom to CoT-SFT, because that
      needs a pre-SFT checkpoint and **no Base `Qwen3.6-35B-A3B` GGUF is on disk** (checked
      `/mnt/raid0/llm/models/` 2026-08-23: `Qwen3.6-35B-A3B-MTP-Q8_0.gguf`,
      `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`, `qwen3.5-35b-a3b-seal-concise.gguf` — no Base). **The gate does
      not need attribution**: a 256K role that cannot recall at 128K is a defect whatever caused it.
      Attribution *and* the published training-free remedy (QK-Restore restores `W_Q`/`W_K` from the
      pre-SFT checkpoint) both need the Base weights — acquiring them is the named prerequisite for any
      **remediation** row, and is deliberately **not** a prerequisite for this probe.

      **Optional fourth arm, only if 32K/64K/128K come back clean:** 256K. The published collapse is
      at 256K, and `-c 262144` has the room on an `-np 1` instance. Named as optional so a clean
      three-length result is not mistaken for a clean *sweep*.

      **Owner:** this handoff — chosen over
      [eval-tower-verification.md](eval-tower-program.md) because eval-tower's subject is the
      verification *tower* (confidence/logprob passthrough, calibration, ECE/AUC, judge validity,
      rubrics) and its rows are `EV-N` infrastructure items, whereas this is an architecture-hazard
      probe on a hybrid attention stack — the exact subject this handoff surveys, and it sits directly
      under the hazard record it tests. If the probe later needs to become a standing suite rather than
      a one-off, *that* is an eval-tower row.
      Both compute planes were held by other sessions through this wave — **filed, not run.**
      *(2026-08-26/27 — RUN, then **PAUSED BY OPERATOR 2026-08-27**: 163/200 Q8 trials persisted at
      `epyc-inference-research/data/frontdoor-amnesia-g1-2026-08-25/q8/trials/` — 4K 50/50, 32K 50/50,
      64K 50/50, 128K 13/13, all 100% — **no recall drop at any measured length; the gate is NOT
      opening at ≤128K**. The decisive paper-regime arm (256K) was not run: operator decision that the
      marginal value (no remediation path without the pre-SFT Base checkpoint; GPU owned by another
      session) did not justify the ~week of exclusive compute. Checkpoint + resume plan:
      `…/frontdoor-amnesia-g1-2026-08-25/PAUSED-2026-08-27.md`. Resume = finish 128K (37 trials),
      f16-KV control, then a small 256K diagnostic (5–10 trials — sufficient for the published-scale
      effect) on GPU when free.)*
- [x] **Z12 (Z) — can GDN-2's `b_proj` / `w_proj` be low-rank factorized?** Static analysis only: rank
      budget, parameter arithmetic, precedent. **The full-rank choice is what produces the entire
      +12.5 % active-parameter objection to GDN-2, and the paper gives no justification for it.**
      The precedent is in our own tree: Kimi Linear already factorizes its decay projection, and we
      carry the tensors for it — `LLM_TENSOR_SSM_F_A` / `LLM_TENSOR_SSM_F_B` at
      `src/llama-arch.h:473-474` ("kimi: forget gate projection A / B"), mapped to
      `blk.{bid}.ssm_f_a` / `ssm_f_b` in `gguf-py/gguf/constants.py:1239-1240`. Verified read-only at
      `0db32c06e3e5`, 2026-08-23. **Informs `B9`** in
      [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md); validating that
      a low-rank gate *retains the reported gain* is compute-gated and belongs to whoever runs B9(b),
      not here. No inference, no GPU — **executable now** (intake-1281#record). ✅ 2026-08-25 — analysis
      note complete: `epyc-inference-research/docs/gdn2-low-rank-static-analysis-2026-08-25.md`
      (rank/parameter arithmetic + Kimi-Linear precedent; see the note for the verdict and what the
      B9 compute gate would need).
  - **Untracked-evidence note 2026-09-16 (sub-closure-fix; annotation only):** the cited `epyc-inference-research/docs/gdn2-low-rank-static-analysis-2026-08-25.md` is **untracked** in the research shared clone (`git status`: `??`) and is on no ref, yet it informs B9. The owner should commit it. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md`.
  - [x] **Z12-COMMIT — commit `docs/gdn2-low-rank-static-analysis-2026-08-25.md` in epyc-inference-research.** ✅ 2026-10-31 — Research `f0d7449f827171be6f0e5f02ce92467b724a09e1`; [verification](../../artifacts/compute/codex3-z12-preservation-20261031/VERIFY.json). [no-belief: historical document preservation; scientific claims not revalidated]
        A verbatim copy (sha256 `5c3f5a42…d792`) is in `/mnt/raid0/llm/backups/preserve-20260916/`. Filed 2026-09-17.

## Track: streaming-llm-baseline
<!-- gate: none -->

> Folded from `handoffs/active/streaming-llm-baseline.md` @ `e1a5e5226974` on 2026-11-02 (BRF-T1-F15, route 1a, operator D1/D5; retired row INF-51 → INF-05). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### StreamingLLM Baseline for KV Reduction Cluster

**Status**: current-v7 source surface, CPU mechanical smoke, and pre-v7 floor/admission sweep recorded; no KV cluster admitted from the floor. Full 4-axis research sweep remains open.
**Created**: 2026-05-19 (post-KV-admission-cluster deep-dive)
**Categories**: kv_cache, context_extension, hardware_optimization
**Priority**: MEDIUM (gate for the entire May 2026 KV-reduction cluster — must land before PBKV/LU-KV/KVP/ForesightKV/SP-KV prioritization is meaningful)
**Depends on**: `../completed/llama-cpp-fork-rebase.md` (KV-cache abstraction), `attention-matching-kv-compaction.md`
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-kv-admission-cluster.md`](../../research/deep-dives/2026-05-19-kv-admission-cluster.md)

#### Objective

Land a clean **StreamingLLM (attention sink + sliding window)** baseline in our llama.cpp fork (`epyc-llama`) to measure the **easy-floor** that any KV reduction method must beat. Without this floor, the relative gains claimed by the May 2026 KV cluster (SP-KV / KVP / LU-KV / ForesightKV / PBKV) cannot be evaluated against the simplest possible competing technique.

**2026-06-13 implementation checkpoint**: `llama.cpp` commit `632ce0f92` adds a low-invasive scaffold using the existing server context-shift path rather than patching core KV tensor layout. `--kv-streaming-sink` / `--kv-streaming-window` are exposed in `llama-cli` and `llama-server`, per-request JSON accepts `kv_streaming_sink` / `kv_streaming_window`, and middle eviction is performed with the existing `llama_memory_seq_rm` + `llama_memory_seq_add` sequence-shift mechanism. Defaults are disabled, preserving existing behavior until explicitly enabled.

**2026-07-18 current-v7 evidence checkpoint**: commits `111bff89d` (streaming KV context controls) and `cf051d3e1` (completion surface) are pushed to `fork/experimental-v7-refresh-20260716`. The root checkpoint commit is `d6bdd4da`, with main merge `45d8e09` already recorded.

- Clean rebuilt Qwable Q8 MI210 artifact: `/mnt/raid0/llm/epyc-inference-research/data/model_admission_throughput/qwable_q8_mi210_llama_bench_20260718T220220Z_rebuilt_cf051d3e1`.
- `bench.json` rows: prompt-only `p512` `2101.214398 t/s`; `tg128` `99.172708 t/s`; combined `pg2048/1024` `avg_ts` `266.820398`; `pg8192/1024` `avg_ts` `602.11996`; `pg32768/512` `avg_ts` `1252.673664`. These `pg` values are `llama-bench` combined prompt+generation `avg_ts`, not isolated decode.
- A prior first run self-reported stale `build_commit=41ae83402` and is superseded by the clean rebuilt artifact.
- CPU mechanical smoke: `/mnt/raid0/llm/epyc-inference-research/data/streamingllm_floor/streamingllm_qwen06_completion_cpu_floor_20260718T2200Z/summary.md` records baseline context-shift decode `319` tokens at `105.57 t/s` and StreamingLLM decode `319` tokens at `103.10 t/s`.
- Both lanes passed mechanical smoke but failed prompt-quality checks. This is not an admission or performance claim. The failed `streamingllm_qwen06_cpu_floor_20260718T215438Z` artifact is excluded; its oversized stdout was removed by main.

**2026-07-20 pre-v7 floor/admission sweep**: inference-research adds
`scripts/benchmark/streamingllm_floor_sweep.py` plus focused tests and artifact
`/mnt/raid0/llm/epyc-inference-research/data/streamingllm_floor/streamingllm_qwen17_q8_cpu_sweep_20260720Tlive/summary.json`.
The sweep used Qwen3-1.7B Q8 CPU-only, `-c 384`, `-n 768`, context-shift
baseline plus sink/window clusters `8:128`, `16:192`, and `32:256`. All four
arms exited `0`, crossed the runtime context, and decoded about `31 t/s`, but
all failed the prompt-quality/final-marker floor and no streaming arm improved
speed materially over baseline (`0.990x` to `1.011x`). Admission decision:
`admit_cluster=false`, reason `no_streaming_cluster_passed_quality_and_speed_floor`.
This closes the pre-v7 "is there a simple KV admission cluster to admit now?"
question negatively; it does not close the broader 4-axis KV research program.

#### Why This is a Cluster-Wide Gate

The deep-dive surfaced a structural gap: **of the 5 papers in the cluster, only KVP (intake-551) explicitly compares to StreamingLLM**. Without an internal floor:
- LU-KV's "80% KV reduction at minimal degradation" claim is unanchored — what does sink + window already achieve?
- SP-KV is empirically refuted (Steele arxiv:2601.14279) precisely because position-based heuristics (sink + last-N) match learned scorers — but we have no internal data point.
- PBKV's 1.85× over LRU doesn't tell us how much of that gain is from being smarter than naïve LRU vs being smarter than sink + window.

Landing the floor first **changes the rank-order** of the cluster priorities, possibly demoting attention-kernel methods (LU-KV / KVP / ForesightKV) in favor of orchestrator-layer methods (PBKV) that compose with sink + window rather than replace it.

#### Research Context

| Intake ID | Title | Relevance | Notes |
|-----------|-------|-----------|-------|
| intake-538 | SP-KV (arxiv:2605.14037) — write-time admission | medium | empirically refuted by Steele's sink+window floor (arxiv:2601.14279) — this spike validates that refutation on our hardware |
| intake-551 | KVP (arxiv:2602.10238) — per-head RL eviction | high | only cluster paper that compares to StreamingLLM |
| intake-552 | LU-KV (arxiv:2602.08585) — global combinatorial per-head budget | medium | frozen-weights compatible; needs the floor to be meaningful |
| intake-553 | ForesightKV (arxiv:2602.03203) — oracle distillation + GRPO | high | needs floor + requires FT infra (deferred) |
| intake-554 | PBKV (arxiv:2605.06472) — workflow-aware residency | high | orchestrator-layer; composes with sink+window |
| intake-1327 | StreamingLLM (arxiv:2309.17453) | anchor | Anchor paper for this handoff finally has an entry: `intake-1327#record`. Stage-1 only — the SL-1…SL-4 amendments in its notes are unverified and are NOT filed. |
| 2026-09-07 expansion (stage1-unverified) | SWA window floor: SWAA (arxiv:2512.10411); Cabannes et al., ICLR 2026, *Short window attention enables long-term memorization* | high | Pointer only, no claims — both bear on the PS-1 window floor. `intake-1340#record` |
| 2026-09-07 expansion (stage1-unverified) | Query-aware SELECTION-based sparse attention: TidalDecode (arxiv:2410.05076), Quest (arxiv:2406.10774), SeerAttention-r (arxiv:2506.08889) | medium | Pointer only, no claims — structural coverage gap for the KV cluster; see also `triattention-kv-selection.md`. `intake-1334#record` |

#### Spike Plan (single phase)

##### StreamingLLM patch in `epyc-llama` (~200 LoC, 1 nightshift sweep)

**Mechanism**: keep the first K_sink tokens permanently (attention sink), keep a sliding window of the last K_win tokens, evict everything in between. Standard implementation: `K_sink = 4`, `K_win = 1024–4096` tunable.

**Steps**:
1. **DONE 2026-06-13**: Add disabled-by-default sink + window policy through server context-shift (`llama_memory_seq_rm` / `llama_memory_seq_add`) plus CLI and per-request controls.
2. **PENDING**: Bench sweep on:
   - **Long-context retrieval** (S-NIAH or RULER subset)
   - **Long-context reasoning** (LongBench or a coder-trace subset)
   - **Multi-session dialogue** (existing autopilot eval-tower trace samples)
   - 3 cache budgets: 25%, 50%, 75% of full KV
   - 2 models: gemma4-26B-A4B Q4_K_M (worker_general production), coder-30B Q4_K_M

**Success criteria**:
- StreamingLLM at 50% budget loses ≤10% accuracy vs full-KV on long-context reasoning
- StreamingLLM at 25% budget loses ≤25% on the same — establishes the noisy floor

**Binding design constraints — rewritten 2026-09-07 (the criteria above have no power statement and no eviction-regime statement):**

- **Generation length is the independent variable.** Every arm must GENERATE ≫ W (target **≥ 4×W**) or it does not test the mask; state each cell's eviction regime explicitly. Priced at the measured **~31 t/s** for Qwen3-1.7B Q8 CPU (2026-07-20 sweep): one 4×W generation is ~9 min @W=4096, ~18 min @W=8192, ~35 min @W=16384. **Run W ∈ {2048, 4096, 8192}; W=16384 is GPU-only or dropped.** `intake-1334#00`
- **Context sizing rule.** `server-context.cpp` computes `n_discard = n_left − window` with `n_left ≈ n_ctx − n_keep`, so `-c = prefix + W` collapses the discard to one token per shift. Use **`-c = prefix + W + chunk`** and sweep `chunk`. `intake-1315#record` (local finding, verified in our tree).
- **Benchmark + power, tension resolved.** MATH500 is power-adequate (stderr ~1.0) but its traces average ~5K generated tokens, so at W=4096 it evicts almost nothing; AIME (15–17K generated) stresses the mask but has 30 problems (avg@64 stderr 6.7–7.8 pp). **Resolution: pool AIME-24 + AIME-25 with avg@k and a stated detectable effect size, and RETAIN W=2048** — it is the only MATH500 arm actually in the eviction regime, i.e. the most informative point on the power-adequate benchmark, not the least. This **reverses** the earlier "DROP W=2048". `intake-1315#02`, `intake-1334#02`.
- **Falsifiable workload split.** Short-context/dialogue arms pass the ≤10% floor at every K_win ∈ {1024, 2048, 4096}; long-context retrieval arms fail it. **A split result IS the finding, not an inconclusive sweep.** Add a training-free sink+window control arm. `intake-1340#00`.
- **Instrument mismatch — do not compare across it.** The literature masks at every position including prefill; frozen v9 evicts only inside the context-shift branch and rejects a prompt of `n_ctx` or more outright (`server-context.cpp:3227-3235`); no runtime `n_swa` override exists (`common/arg.cpp:1491/:1501/:1512`). The long-INPUT retrieval arm therefore measures **full-attention prefill + streaming decode** — a different and strictly stronger method than SWA — and its numbers must never be set against a published S-NIAH table. `intake-1340#04`.
- **Reporting rule (sweep-local convention, NOT a policy amendment).** Paired recovery ratio = student score / the **same** teacher, reported per model per workload, **never pooled** across differing model sets. Promoting this convention to `agents/shared/MEASUREMENT_POLICY.md` would be an operator decision package, not a session write. `intake-1340#record`.
- **Accuracy first, speed second**: a speed null is not a refutation on weight-bandwidth-bound CPU decode.

**Gate criteria for cluster prioritization**:
- If StreamingLLM at 50% budget already preserves ≥95% accuracy on our representative workloads, **demote LU-KV / KVP / ForesightKV** — their incremental gain over the floor is too small to justify the kernel work.
- If StreamingLLM degrades significantly at 50% budget, **promote LU-KV** as the next-priority attention-kernel method (it's the only frozen-weights compatible candidate in the cluster).
- Either way, **PBKV stays prioritized** because it operates at the orchestrator layer and composes with sink + window rather than competing.

**Dev cost**: code scaffold landed as 60 insertions / 2 deletions in `epyc-llama` commit `632ce0f92`.
**Compute cost**: 1 nightshift (~8 hours) for the 4-axis sweep (3 budgets × 2 models × 4 workloads). Requires `feedback_no_concurrent_inference` per-bench approval per sweep cell.

#### Non-Goals

- **No fine-tuning**: StreamingLLM is purely inference-time, no model surgery.
- **No KV quantization changes**: orthogonal to `kv-cache-quantization.md` (completed); StreamingLLM operates on the *selection* axis, not the *precision* axis.
- **No comparison to TriAttention / AttentionMatching**: those are already in flight under their own handoffs; this spike establishes a NEW (sink+window) baseline they should also be measured against in a follow-up.

#### Failure Modes to Watch

- **Sink-token attention drift on quantized models**: position-based methods can interact badly with Q4_K_M KV quantization if the sink tokens hit different quant blocks than the window tokens. Sweep both Q4_K_M and F16 KV cache configs to disambiguate.
- **Sliding-window edge effects**: long-context reasoning may need the sink + window combination tuned per workload (coder traces are different from dialogue). Report per-workload sweep results, not just averages.
- **Per-head heterogeneity hidden by uniform sink+window**: LU-KV's whole pitch is that different heads have different temporal patterns. If sink+window already wins, that pitch is undercut — but if some heads degrade catastrophically under uniform sink+window, LU-KV's per-head budget allocation has demonstrable value. Track per-head attention entropy in the sweep.

#### Open Questions for User

1. **K_sink, K_win defaults**: StreamingLLM paper uses 4 + 1024. For our coder/frontdoor traces (often 5-10 K tokens of context), the window should likely be larger. Sweep K_win ∈ {1024, 2048, 4096} per workload?
2. **Quantization scope**: include or skip the F16 KV-cache baseline? F16 isolates the algorithm from quant interaction but doubles the sweep size. Recommend: include F16 only on the smallest model (gemma4-26B-A4B is 26B; running F16 KV adds ~2 GB per slot — feasible).
3. **PBKV order-of-operations**: should this StreamingLLM baseline land BEFORE the PBKV spike (per the deep-dive recommendation), or in parallel? Sequential is safer but adds 1-2 weeks to PBKV's start.

#### References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-kv-admission-cluster.md`
- StreamingLLM paper: `https://arxiv.org/abs/2309.17453` (Xiao et al., ICLR 2024)
- StreamingLLM reference impl: `https://github.com/mit-han-lab/streaming-llm`
- Steele falsification (sink+window beats learned scoring): `https://arxiv.org/abs/2601.14279`
- Related handoffs: `attention-matching-kv-compaction.md`, `triattention-kv-selection.md`, `summary-token-attention-readiness.md`, `multiscreen-attention-evaluation.md`, `../completed/llama-cpp-fork-rebase.md`

#### Research Intake Update — 2026-09-07

- **Table-4 efficiency ruling for the whole KV-reduction cluster**: at a 2K budget / 16K context, sink+window matches the best selection method on FLOPs (1.05M), global-to-shared transfer (1.04MB) and kernel latency (20.1 µs) at **1/8th** the on-device memory (1.04MB vs 8.38MB) — and every selection-class method holds the FULL cache. This reduces the PS-1 question to a single axis (accuracy) and removes selection-class methods from `attention-matching-kv-compaction.md`'s candidate set, whose objective is 10× KV **memory** reduction. `intake-1334#05`.
- **PS-2 CLOSED, no task filed**: our context-shift path is Reset-PE (`seq_rm` + `seq_add -n_discard`); the source reports the difference insignificant and recovered Figure 14 puts Reset PE ahead at 4 of 5 budgets within one SE. intake-1327's closure confirmed. `intake-1315#record`.
- **Three numeric corrections carried against the source**, so the sweep session does not re-quote them: Table 1's 128K cell is the vanilla-SWA value (11.26×, not 11.7×); W=16384 does **not** match full attention (28.74 vs 31.14, first match at W=32768); the "seconds" axis is **derived**, nothing was timed. `intake-1315#record`.

#### Note 2026-10-21 — V11-098 context-shift check (wrap-up 3c4ca599-c)

The hybrid/recurrent `can_shift` guard (V11-098, `experimental/hybrid-cache-reuse-guard-20261021` @ `8b08c9f25`, pending fold, not in production) turns server `--context-shift` off on hybrid and pure-recurrent models, where it used to be enabled and shift attention KV against a stale recurrent state. The impact check found no production reliance on context shift: the default is off, and a context overflow without it is loud (the request errors; nothing is silently dropped). This sweep is not affected: it ran dense Qwen3-1.7B Q8 (a dense model still reports `can_shift` 1), so the StreamingLLM sink+window path through context shift is unchanged.

#### Progress checklist

- [x] StreamingLLM sink+window scaffold landed in epyc-llama (commit 632ce0f92, disabled by default) ✅
- [x] Current-v7 source/build surface reconciled at `111bff89d` + `cf051d3e1` on `fork/experimental-v7-refresh-20260716` ✅ 2026-07-18
- [x] CPU mechanical smoke completed for baseline and StreamingLLM lanes; both passed mechanics but failed prompt-quality, so no admission/performance claim ✅ 2026-07-18
- [x] Pre-v7 floor/admission sweep completed on Qwen3-1.7B Q8 CPU-only: all arms exited cleanly, no sink/window cluster passed quality+speed floor, and no KV cluster is admitted before v7 promotion ✅ 2026-07-20
- [ ] Run 4-axis inference sweep: 3 workloads (retrieval/reasoning/dialogue) x 3 budgets (25/50/75%) x 2 models — *(2026-08-25: 72-cell design + daemon built and launched by the INF-51 churn session — 3 workloads × 3 budgets × 3 K_win {1024,2048,4096} × 2 models + 6 full-KV baselines + 12 gemma4 F16 controls; harness extended from streamingllm_floor_sweep.py; SWA finding: gemma4 needs `--swa-full` on v9 or context-shift silently disables. Zero cells completed — lease/region held by inf42-g1; daemon reconciled 2026-08-27, relaunch gated on q0-q3 release.)*
  - Sweep design REWRITTEN 2026-09-07 — before any cell runs, re-read § Spike Plan → *Binding design constraints* (generation ≥4×W, `-c = prefix + W + chunk`, W ∈ {2048,4096,8192} with W=2048 RETAINED, AIME-24+25 pooling, workload-split hypothesis + sink+window control arm, instrument-mismatch rule, paired-recovery reporting) and § Research Intake Update — 2026-09-07. Box unchanged; the design under it is not.
- [ ] Evaluate success criteria (<=10% loss at 50% budget, <=25% at 25%) per-workload, track per-head attention entropy
- [ ] Apply cluster-prioritization gate: demote LU-KV/KVP/ForesightKV or promote LU-KV based on floor
- [x] Resolve user questions: K_sink/K_win sweep values, F16 KV scope, PBKV order-of-operations ✅ 2026-08-25 — **operator decisions**: (1) full K_win sweep {1024, 2048, 4096} — 54 streaming cells; (2) F16 KV control on gemma4 only (smallest model); (3) PBKV runs in parallel — no sequential gate (lease/region serialization prevents concurrency poisoning; no PBKV spike currently in flight, so the floor still lands first de facto)

## Track: triattention-kv-selection
<!-- gate: none -->

> Folded from `handoffs/active/triattention-kv-selection.md` @ `e1a5e5226974` on 2026-11-02 (BRF-T1-F15, route 1a, operator D1/D5; retired row INF-56 → INF-05). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### KV Cache Selection/Eviction - Expected Attention Active Work

**Status**: COMPACTED 2026-05-28 - Expected Attention deployed; active only for S8 autopilot profiles and S9 auto-trigger.
**Created**: 2026-04-08
**Updated**: 2026-07-26
**Priority**: MEDIUM
**Categories**: kv_cache, inference_serving, memory_bandwidth
**Parent index**: [inference-research-index.md](inference-research-index.md)
**Completed ledger**: [triattention-kv-selection-deployment-completed-through-2026-05-28.md](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md)

#### 2026-07-26 Staleness Review

S8 remains explicitly scheduled in the
[bulk-inference campaign](eval-tower-program.md#track-bulk-inference-campaign), and S9/S3 remain
dependent on S8 evidence. No profile sweep or auto-trigger decision was
completed by this review, so all open task states remain unchanged.

#### Executor Start Here

Expected Attention is already the production path. Do not reopen S1/S4/S5/S6/S7 as if this were still an evaluation stub. The current implementation work is role-profile exploration for autopilot, then orchestrator auto-trigger wiring once stable profiles exist.

#### Outstanding Tasks

- [ ] **S8 autopilot exploration**: sweep `keep_ratio` and `layer_weights` per production role; persist Pareto profiles with quality, speed, cost, and reliability axes.
- [ ] **S8-c recency reservation (third S8 axis)**: add keep_recent / recency_ratio to llama_kv_compress_params, protect the last N positions the way n_sink protects the first, plumb through slot_action, sweep alongside keep_ratio and layer_weights. Today src/llama-kv-compress.h has n_sink but no recency field and src/llama-kv-compress.cpp:326/334 ranks every position from n_sink to n_kv purely on score (server keep_first defaults to 8) — the configuration a direct experiment says improves recall and STILL FAILS on reasoning, fixed by reserving ~25% of the kept budget for recent positions. ~20 lines, no kernel work. Experimental branch only — v9 is FROZEN. intake-1334#02
- [ ] **S8-d (record, no work)**: our Expected Attention path is already cross-head/cross-layer UNIFIED — llama_kv_compress_score returns one per-position score vector aggregated across attention layers with layer_weights — the property the LessIsMore argument says is essential for reasoning; independent corroboration of a choice we made for other reasons. Two transfer limits: we evict irrecoverably at a slot boundary while selection re-selects from a complete cache every step (so a bad recency reservation costs us more), and selection buys ZERO KV memory while eviction buys 8×. intake-1334#01, intake-1334#04
- [ ] **PS-5 unclaimed design (log only)**: prefix + heavy-hitter hybrid — proposed in Appendix G.3 and explicitly not run there; we ship both halves. intake-1315#record
- [ ] **S9 orchestrator auto-trigger**: blocked until S8 produces stable role profiles. Wire learned profiles, not hardcoded defaults.
- [ ] **S2 TriAttention concentration validation**: optional comparator only; no longer blocks Expected Attention deployment.
- [ ] **S3 selection plus quantization stacking**: reopen after S8 only if stacked compression is a production need. Otherwise evaluate Attention Matching or another high-compression path first.

*Research-context pointer (2026-09-07 intake expansion, stage1-unverified, no claims):* query-aware SELECTION-based sparse attention — TidalDecode (arxiv:2410.05076), Quest (arxiv:2406.10774), SeerAttention-r (arxiv:2506.08889). Structural coverage gap for this cluster; see also `streaming-llm-baseline.md` § Research Context. `intake-1334#record`

#### Minimal S8 Artifact

S8 preparation (2026-11-02): the existing Expected Attention evaluator uses a
separate KVPress path, so it cannot establish profiles for the deployed server.
Prepare a paired server-slot sweep with matched uncompacted continuations, a
role workload and an explicit quality and reliability decision rule before
publishing a compute row. Establish actual slot/cache continuity and binary
identity as part of that preparation. The existing `keep_ratio` and
`layer_weights` axes can be explored before S8-c; recency needs an experimental
kernel candidate. PS-5 above is a design record, not a GPU run.

```text
Role:
Model:
Context/workload:
keep_ratio candidates:
layer_weight candidates:
Pareto winner:
Quality delta:
Speed/cost delta:
Reliability notes:
```

#### Dependency Forks

| Outcome | Next action |
|---|---|
| S8 finds stable per-role profiles | Promote S9 orchestrator auto-trigger wiring and update the relevant model/role registry. |
| S8 profiles vary heavily by prompt or model | Keep manual/autopilot-exploration mode; do not hardcode defaults in orchestrator. |
| S8 quality loss is unacceptable at useful ratios | Close auto-trigger path for now and retain manual compaction only. |
| Production needs higher compression than Expected Attention provides | Reopen S3 stacking or compare Attention Matching before adding more kernel complexity. |

#### Completed Scope

*2026-09-07*: the cross-head/cross-layer unification landed under S4/S7 has independent external corroboration — recorded as **S8-d** in § Outstanding Tasks, not re-opened here. `intake-1334#01`, `intake-1334#04`.

| Scope | Result | Ledger |
|---|---|---|
| S4 kernel port | Complete in `llama-kv-compress.h/.cpp`; production kernel commit `4babc8fe3`. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S1 PPL at 50% | PASS: Qwen3-1.7B 0.86 and Qwen3.5-35B 1.096, under the 1.10 gate. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S5 multi-ratio sweep | 90-75 identical, 50 safe, 25 aggressive, 10 cliff. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S6 server integration | `/slots/{id}?action=compact&scorer=expected_attention` landed. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |
| S7 autopilot integration | `kv_compress.py`, `slot_compact`, and `program.md` Tier 4.5 landed. | [completed ledger](../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md) |

#### Key Files

- `/mnt/raid0/llm/llama.cpp/llama-kv-compress.h`
- `/mnt/raid0/llm/llama.cpp/llama-kv-compress.cpp`
- `/mnt/raid0/llm/epyc-orchestrator/src/`
- `/mnt/raid0/llm/epyc-orchestrator/program.md`
- `/mnt/raid0/llm/epyc-inference-research/`
- `research/deep-dives/triattention-kv-selection-cluster.md`

#### Reporting Instructions

After S8 runs, update this handoff with the artifact fields above and the decision on S9. If S9 opens, update [inference-research-index.md](inference-research-index.md), [routing-and-optimization-index.md](routing-and-optimization-index.md) if autopilot behavior changes, and [master-handoff-index.md](master-handoff-index.md).
