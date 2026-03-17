# Handoff: SSM Hybrid Acceleration

**Status**: ALL SELF-ACCELERATION APPROACHES EXHAUSTED. Phase 5 (MTP-1) has 78.5% acceptance but speculation loop yields 0.56x (SLOWER) due to 2-token batch costing 3-4x single decode on hybrid recurrent. See `handoffs/completed/mtp-speculative-decoding.md`.
**Created**: 2026-03-15
**Updated**: 2026-03-17
**Blocked by**: None — phases are independently pursuable
**Blocks**: None
**Related**: tree-speculation-numa-drafting (Phase 8 covers STree, orthogonal to this handoff)

## Objective

Explore SSM-specific optimization avenues beyond tree speculation. The hybrid SSM models (Qwen3.5-35B-A3B, Qwen3-Next-80B-A3B) are powerful quality-wise but have limited acceleration options — currently only MoE expert reduction and prompt lookup (recently unblocked). This handoff investigates techniques that exploit SSM architecture properties rather than fighting them.

## Background

### Current SSM Optimization State

| Technique | Status | Gain | Notes |
|-----------|--------|------|-------|
| MoE expert reduction | Production | +21-42% | Only optimization active for Qwen3-Next-80B |
| Prompt lookup (via freeze-recurrent) | Unblocked (2026-03-15) | +30-42% est. | Registry constraint removed, auto freeze-recurrent validated |
| External draft + freeze-recurrent | Validated, not in prod | +5.4% | Only with fast drafter (>150 t/s). Qwen2.5-Coder-0.5B at 185 t/s |
| External draft + checkpoint | Conditional go | +56% code only | Net negative on general text. 1.56x on code (92% accept) |
| Self-speculation (layer exit) | Failed | -44% to -51% | SSM checkpoint overhead dominates |
| HiSpec intermediate | Failed | -10% to -11% | Intermediate logits untrained |
| Tree speculation (frozen multi-path) | Failed on hybrid | -53% to -62% | Acceptance collapses 12-22pp from frozen recurrent |
| Tree speculation (per-path replay) | Failed on hybrid | -60% to -66% | `llama_decode` runs ALL layers per path. O(N_paths × full_forward) |
| Tree speculation (checkpoint + clone_cell) | Failed on hybrid | -59.5% | Checkpoint save (~450MB) + clone per path overhead exceeds tree benefit |
| Attention-only draft (skip recurrent) | Failed on hybrid | -49% | Near-zero acceptance: 10 attn layers alone produce incoherent output |
| MoE self-draft (1 expert) | Failed on pure MoE | -50% | 2.9% acceptance: 1/8 experts produces categorically different output |
| MoE self-draft (2 experts) | Failed on pure MoE | -28% | 55% acceptance, but 2→8 expert speedup too small to overcome overhead |

### Key Architecture Properties

**Important**: Despite being labeled "SSM hybrid" in some documentation, Qwen3.5 and Qwen3-Next use **Delta Net** (gated linear attention), NOT Mamba2. Their recurrent layers are implemented in `src/models/delta-net-base.cpp` using the delta rule recurrence: `s_t = exp(g_t) * s_{t-1} + k_t ⊗ beta_t * (v_t - s_{t-1}^T k_t)`. They do NOT use `ggml_ssm_scan`. The term "recurrent" is accurate; "Mamba" is not.

1. **Small fixed-size state** (~62 MiB for Qwen3.5-35B) vs KV cache that grows with context
2. **Sequential state compression** — each token's contribution is folded into the state irreversibly
3. **Hybrid architecture** — 75% Delta Net (gated linear attention) layers + 25% attention (Qwen3.5-35B: 30 recurrent + 10 attention out of 40 total)
4. **MoE routing** — expert count is independently tunable per context
5. **`moe_n_expert_override`** already in llama.cpp cparams — infrastructure for per-context expert control exists

## Phase 1 — MoE Self-Drafting

**Status**: NOT VIABLE. Step 0 raw speedup promising (1.79x on 235B), but end-to-end acceptance too low (2.9% at 1-expert, 55% at 2-expert). Net throughput always negative.

### Step 0 Empirical Results (2026-03-16)

All tests: 96 threads, EPYC 9655, Q4_K_M quantization. `ignore_eos=true` for consistent token counts.

**Model A — Qwen3.5-35B-A3B (hybrid SSM+MoE, 256 experts, expert FFN 512)**

| Active Experts | Avg t/s | Speedup | Delta |
|----------------|---------|---------|-------|
| 8 (default)    | 10.99   | 1.00x   | —     |
| 4              | 11.67   | 1.06x   | +6.2% |
| 2              | 12.48   | 1.14x   | +13.6% |
| 1              | 12.93   | 1.18x   | +17.7% |

NOT VIABLE. 256 experts × 512 FFN = extremely fine-grained. MoE compute is tiny relative to 30 Delta Net recurrent layers (75% of model).

### Research Intake Update — 2026-03-17

#### New Related Research
- **[intake-158] "DFlash: Block Diffusion for Flash Speculative Decoding"** (arxiv:2602.06036)
  - Relevance: Targets Qwen3.5-35B-A3B with block diffusion drafting — 2.4-2.8x on B200 GPU
  - Key technique: Parallel token generation via denoising diffusion, conditioned on target model context
  - Delta from our approach: GPU-only (SGLang/vLLM), no llama.cpp/GGUF/CPU path. Validates model is spec-decode friendly. Our MTP-1 (78.5% acceptance) remains the viable CPU path. DFlash's existence strengthens the case for MTP Step 7 — the model architecture is known to cooperate well with draft-verify paradigms across multiple approaches.

**Model B — Qwen3-Coder-30B-A3B (pure MoE, 128 experts, expert FFN 768)**

| Active Experts | Avg t/s | Speedup | Delta |
|----------------|---------|---------|-------|
| 8 (default)    | 42.81   | 1.00x   | —     |
| 4              | 49.64   | 1.16x   | +16.0% |
| 2              | 57.22   | 1.34x   | +33.7% |
| 1              | 57.84   | 1.35x   | +35.1% |

VIABLE (1.35x). Note: 2→1 experts gives only +0.01x — bottleneck shifts to attention/shared-FFN at 2 experts.

**Model C — Qwen3-235B-A22B (pure MoE, 128 experts, expert FFN 1536)**

| Active Experts | Avg t/s | Speedup | Delta |
|----------------|---------|---------|-------|
| 8 (default)    | 9.38    | 1.00x   | —     |
| 1              | 16.76   | 1.79x   | +78.8% |

HIGHLY VIABLE (1.79x, stdev 0.01). Larger expert FFN (1536 vs 768) means MoE compute is a bigger fraction of total.

**Analysis**: MoE self-draft viability correlates with expert FFN size and model architecture:

| Model | Expert FFN | Total Experts | Recurrent Layers | 1-Expert Speedup | Viable? |
|-------|-----------|---------------|-------------------|------------------|---------|
| Qwen3.5-35B-A3B | 512 | 256 | 30/40 (75%) | 1.18x | NO |
| Qwen3-Coder-30B-A3B | 768 | 128 | 0/48 (0%) | 1.35x | YES |
| Qwen3-235B-A22B | 1536 | 128 | 0/94 (0%) | 1.79x | YES |

**Step 0 conclusion**: Raw per-token speedup promising on pure MoE (1.35-1.79x), not on hybrid (1.18x).

### Step 1 Acceptance Results (2026-03-16)

End-to-end speculation on Qwen3-235B-A22B Q4_K_M. Linear speculation (tree forced off — target n_seq_max=1 incompatible). 96 threads, EPYC 9655, 200 tokens/run, 5 runs/config.

| Config | Avg t/s | vs Baseline | Accept% | Drafted | Accepted |
|--------|---------|-------------|---------|---------|----------|
| Baseline (no spec) | 8.97 | 1.00x | N/A | N/A | N/A |
| 1 expert, draft_max=8 | 4.50 | 0.50x | 2.9% | 1141 | 33 |
| 1 expert, draft_max=16 | 4.65 | 0.52x | 5.5% | 1151 | 63 |
| 2 experts, draft_max=8 | 6.47 | 0.72x | 55.4% | 903 | 500 |
| 2 experts, draft_max=16 | 6.31 | 0.70x | 53.6% | 928 | 497 |

**Root cause analysis**:
- **1-expert (2.9% acceptance)**: Reducing from 8→1 active experts doesn't make the model "slightly dumber" — it produces **categorically different** token distributions. Expert routing IS the model's core decision mechanism. With different expert counts, the models diverge.
- **2-expert (55% acceptance)**: Decent acceptance, but the 2→8 expert raw speedup (~1.35x from Step 0) is too small. Draft cycle: 8 tokens at 1.35x speed = 5.9 target-token-times. Verify = ~1. Total ~6.9, producing ~5.4 tokens (55% × 8 + 1). Net: 5.4/6.9 = 0.78 tokens/target-time, worse than baseline (1.0).
- **The trap**: Step 0 raw throughput (1.79x at 1-expert) looked viable, but acceptance and draft overhead analysis were needed. Self-draft with expert reduction is fundamentally flawed: the draft-to-target quality gap scales with the speedup gap.

**Conclusion**: MoE self-draft is **NOT VIABLE** on any tested model. The 1-expert draft is too cheap (low quality), the 2-expert draft is too expensive (low speedup). There is no sweet spot.

### Concept

Use the **same model** as both target and draft. Draft context runs with reduced experts (1-2), verification runs with full experts (8). No second model to load. No SSM state forking because it's the same model — the SSM state stays correct because all layers (including SSM) execute in both draft and verify passes. Only the MoE routing quality changes.

This is conceptually identical to self-speculation via layer-skip, except instead of skipping layers you skip experts. The key advantage for SSM hybrids: SSM state is never stale, never needs checkpointing, never needs freezing.

### Why This Works on Pure MoE but Not Hybrid SSM

- `moe_n_expert_override` already exists in `llama-cparams.h` — infrastructure works correctly
- `--moe-n-expert` flag available to ALL tools (no `.set_examples()` restriction)
- **Pure MoE (Qwen3-235B)**: 1.79x — expert FFN 1536, MoE is a large fraction of compute
- **Pure MoE (Qwen3-Coder-30B)**: 1.35x — expert FFN 768, viable but bottlenecks at 2 experts
- **Hybrid SSM (Qwen3.5-35B)**: 1.18x — expert FFN 512, 75% of model is recurrent (not MoE)
- The key factor is `(expert_ffn × n_experts_saved) / total_model_flops` — hybrid models have most compute in non-MoE recurrent layers

### Implementation (Completed 2026-03-16)

**Approach**: Create a second `llama_context` from the same target model with `moe_n_expert_override=N`. Weights shared via mmap — only KV cache + recurrent state + compute buffers duplicated. Piggybacks on the existing `common_speculative` infrastructure (draft generation, tree construction, verification all handled).

Files changed:

| File | Change |
|------|--------|
| `common/common.h` | Added `moe_n_expert_draft` field to `common_params_speculative` |
| `common/arg.cpp` | Added `--moe-n-expert-draft` flag |
| `common/speculative.cpp:1362` | Changed `has_draft` check from `mparams_dft.path.empty()` to `model_dft != nullptr` |
| `tools/server/server-context.cpp:~740` | Self-draft context creation block (after external draft block) |
| `tools/server/server-context.cpp:~595` | Added `moe_self_draft_active` flag to prevent double-free |

Usage: `llama-server -m model.gguf --moe-n-expert-draft 1 --draft-max 8`

### Benchmark Plan

**Step 0 — Viability check** (before speculation benchmarks):
```bash
# Full experts (baseline)
llama-server -m Qwen3.5-35B-A3B-UD-Q4_K_M.gguf -t 96 --port 8199
# 1 expert
llama-server -m Qwen3.5-35B-A3B-UD-Q4_K_M.gguf -t 96 --port 8199 --moe-n-expert 1
```
If speedup < 1.3x, MoE layers are too small a fraction → approach not viable.

**Step 1 — A/B benchmark**:
- Baseline: no speculation (target only)
- Self-draft 1 expert: `--moe-n-expert-draft 1 --draft-max 8`
- Self-draft 2 experts: `--moe-n-expert-draft 2 --draft-max 8`
- External draft (Qwen3.5-0.8B): `--md Qwen3.5-0.8B-Q8_0.gguf --draft-max 8`

**Step 2 — Correctness**: Temperature 0, compare output with/without self-draft — should be identical.

**Step 3 — Memory**: Verify second context adds only KV cache + recurrent (~70-80 MiB), not full model weight duplication.

### Expected Outcome

- 1-expert draft: ~4x faster draft, unknown acceptance
- 2-expert draft: ~2x faster draft, likely higher acceptance
- If acceptance > 50% with 1-expert: net positive even without external draft
- **Combinable with freeze-recurrent external draft**: MoE self-draft for SSM layers, external draft for diversity

### Risk

| Risk | Severity | Mitigation |
|------|----------|------------|
| MoE layers too small fraction → speedup < 1.3x | MEDIUM | Step 0 baseline kills early if not viable |
| 1-expert acceptance too low | MEDIUM | Try 2 experts. Combinable with tree for more candidates |
| Draft context memory overhead too large | LOW | Same model mmap → only state duplicated (~70 MiB). Use small n_ctx for draft |

## Phase 2 — Conv-Only Checkpoint (DEFERRED — Incorrect Premise)

**Status**: Deferred / unlikely. Analysis below.

### Why This Phase Is Not Viable

This phase was based on an incorrect premise — that `r_l` = "conv state" and `s_l` = "scan state" (Mamba2 terminology). But Qwen3.5 uses **Delta Net**, not Mamba2:

- `r_l` tensors: part of gated linear attention recurrence (NOT a convolution buffer)
- `s_l` tensors: Delta Net outer-product state matrix
- Both are tightly coupled in the Delta Net recurrence: `s = exp(g) * s_old + k ⊗ beta * (v - s_old^T k)`

More importantly, `freeze_recurrent` already freezes BOTH `r_l` and `s_l` at **zero overhead** (just a flag check in the graph builder). Conv-only checkpoint would add ~0.1ms overhead for a partial save that provides no benefit — the acceptance loss comes from stale Delta Net state, and there IS no separate conv state in Delta Net models.

### Original Concept (Preserved for Reference)

The recurrent checkpoint approach saves ALL recurrent state (~62 MiB). Idea was to checkpoint/restore only conv state (~2.8 MiB, ~0.1ms) and freeze scan state. But since both `r_l` and `s_l` are part of the same Delta Net recurrence (not separate conv + scan paths), partial checkpointing cannot improve over full freeze.

## Phase 3 — Attention-Only Drafting for Hybrid Models

**Status**: NOT VIABLE. Implemented and benchmarked 2026-03-16. 0.51x throughput (~49% slower than baseline).

### Concept

Qwen3.5-35B-A3B has 10 attention layers (every 4th layer: 0, 4, 8, ..., 36) out of 40 total. Run ONLY the attention layers as a cheap "draft model" — skip all 30 Delta Net (gated linear attention) layers during drafting. The full model (all 40 layers) verifies.

### Empirical Results (2026-03-16)

Qwen3.5-35B-A3B-abliterated Q4_K_S, 96 threads, EPYC 9655, linear speculation (tree incompatible with hybrid memory).

| Config | Avg t/s | vs Baseline |
|--------|---------|-------------|
| Baseline (no speculation) | 14.52 | 1.00x |
| --skip-recurrent-draft --draft-max 4 | 7.35 | 0.51x |
| --skip-recurrent-draft --draft-max 8 | 7.47 | 0.51x |
| --skip-recurrent-draft --draft-max 16 | 7.60 | 0.52x |

**Root cause**: Near-zero acceptance rate. The 10 attention layers without 30 Delta Net layers produce incoherent output (sample: "2+2 = 2+2+4"). Draft tokens are essentially random — almost every draft token is rejected, so the verification overhead is pure waste.

**Tree speculation**: Crashes in sampler during tree-mode drafting (hybrid memory context incompatible with multi-sequence tree construction). Forced to linear-only via guard in server-context.cpp.

### Implementation (Complete, kept for potential future use on other architectures)

Files changed:

| File | Change |
|------|--------|
| `src/llama-cparams.h` | Added `skip_recurrent` field |
| `include/llama.h` | Added `skip_recurrent` to `llama_context_params` |
| `src/llama-context.cpp` | Wire through default params and cparams init |
| `src/models/qwen35moe.cpp` | Skip recurrent layers via `continue` in layer loop |
| `src/llama-graph.cpp` | Skip recurrent inputs in `build_inp_mem_hybrid()`, guard `set_input()` and `can_reuse()` |
| `common/common.h` | Added `skip_recurrent_draft` field |
| `common/arg.cpp` | Added `--skip-recurrent-draft` flag |
| `tools/server/server-context.cpp` | Self-draft context creation + tree guard (force linear) |

Usage: `llama-server -m model.gguf --skip-recurrent-draft --draft-max 8`

### Why This Failed

The risk assessment was correct — 75% of the model's capacity is in the Delta Net layers. Unlike dense transformers where skipping non-adjacent layers preserves some signal, Qwen3.5's architecture places recurrent layers between EVERY pair of attention layers. Removing them eliminates the model's primary context mechanism.

**Conclusion**: Attention-only drafting is not viable for Qwen3.5-style hybrid models. The Delta Net layers are not "optional" — they are the backbone of the model's token-to-token context tracking.

## Phase 4 — NUMA-Aware Prefill Pipelining for Delta Net Recurrent

**Status**: UNBLOCKED (Phases 1, 3 complete ✅). Deferred — infrastructure-heavy, prefill-only benefit.

Gate check (2026-03-17): Phases 1, 3, 5 complete. Phase 4 is UNBLOCKED.
- Phase 1: MoE self-draft NOT VIABLE (all configs)
- Phase 3: Attention-only NOT VIABLE (0.51x)
- Phase 5: MTP-1 NOT VIABLE on hybrid (0.56x, 78.5% acceptance wasted)
Next: benchmark NUMA prefill pipelining on Qwen3-Next-80B-A3B (ingest_long_context).

### Concept

Delta Net recurrent models have a unique property: the recurrent state is a **fixed-size summary** (~62 MiB) regardless of context length. For long-context workloads (Qwen3-Next at 32K context), prefill is the bottleneck. Unlike attention models (where KV cache grows linearly with context and must be accessible to all future tokens), recurrent state can be **pipelined**:

```
NUMA Node 0: Process tokens 0-16K → produce state_16K (62 MiB)
  ↓ transfer state_16K (~62 MiB, ~0.3ms at 200 GB/s cross-NUMA)
NUMA Node 1: Process tokens 16K-32K starting from state_16K → produce state_32K
```

For attention layers in the hybrid model, the KV cache for tokens 0-16K must still be accessible — but it can stay on Node 0 and be served via cross-NUMA reads (slower but only for attention layers, which are 25% of the model).

### Expected Outcome

Prefill speedup proportional to the Delta Net layer fraction. For Qwen3.5-35B-A3B (75% recurrent):
- Recurrent prefill: ~2x from pipelining (2 NUMA nodes in parallel)
- Attention prefill: ~1x (still needs sequential access to prior KV)
- Net: ~1.5x prefill speedup

Most valuable for Qwen3-Next-80B as `ingest_long_context` with 32K contexts.

### Implementation

1. Partition prefill tokens into NUMA-node-sized chunks
2. Process Delta Net recurrent layers in pipeline: Node 0 does chunk 1, hands off state, Node 1 does chunk 2
3. Process attention layers with cross-NUMA KV access
4. Coordinate via shared memory (state handoff between nodes)

### Files

| Action | File | Repo |
|--------|------|------|
| Modify | `tools/server/server-context.cpp` | llama.cpp |
| Modify | `src/llama-context.cpp` | llama.cpp |
| Modify | `scripts/server/orchestrator_stack.py` | epyc-orchestrator |

### NUMA Prefill Benchmark Plan

**Test model**: Qwen3-Next-80B-A3B Q4_K_M (~46 GB, production `ingest_long_context`)
**Context lengths**: 8K, 16K, 32K (production range)
**Metrics**: prefill tokens/sec, time-to-first-token (TTFT)

```bash
# NUMA interleaved (current default)
numactl --interleave=all \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf \
  -t 96 --port 8199

# NUMA node-pinned (node 0 only — will it fit in ~230GB single-node memory?)
numactl --cpunodebind=0 --membind=0 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf \
  -t 48 --port 8199
```

Send test prompts at varying context lengths:
```bash
for ctx in 8192 16384 32768; do
  python3 -c "
import requests, time
prompt = 'x ' * $ctx
t0 = time.time()
r = requests.post('http://localhost:8199/v1/chat/completions', json={
    'model': 'default', 'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 1, 'temperature': 0
})
print(f'ctx={$ctx} TTFT={time.time()-t0:.2f}s')
"
done
```

### NUMA-Parallel Verification Test Matrix

Cross-reference with DFlash Phase 6. Tests concurrent single-token decodes across NUMA nodes to assess whether NUMA parallelism can reopen draft-verify paradigms on hybrid models.

| Config | Concurrent Decodes | NUMA Binding | Model | Expected Outcome |
|--------|-------------------|-------------|-------|-----------------|
| Baseline | 1 | interleave=all, 96 threads | Qwen3.5-35B-A3B Q4_K_M (19 GB) | ~11 t/s (known) |
| NUMA-0 | 1 | node 0 only, 48 threads | Qwen3.5-35B-A3B Q4_K_M | ~6-8 t/s (half bandwidth) |
| Dual-NUMA | 2 (one per node) | node 0 + node 1, 48 threads each | Qwen3.5-35B-A3B Q4_K_M | ~12-16 t/s aggregate? |
| Quad-NUMA | 4 (two per node) | 2×node0 + 2×node1, 24 threads each | Qwen3.5-35B-A3B Q4_K_M | bandwidth-limited? |

```bash
# Baseline: single decode, interleaved
numactl --interleave=all \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/bartowski/Qwen3.5-35B-A3B-abliterated-GGUF/Qwen3.5-35B-A3B-abliterated-Q4_K_M.gguf \
  -t 96 --port 8199

# Dual-NUMA: two servers, one per node (model fits in single node at 19GB)
numactl --cpunodebind=0 --membind=0 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/bartowski/Qwen3.5-35B-A3B-abliterated-GGUF/Qwen3.5-35B-A3B-abliterated-Q4_K_M.gguf \
  -t 48 --port 8199 &

numactl --cpunodebind=1 --membind=1 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/bartowski/Qwen3.5-35B-A3B-abliterated-GGUF/Qwen3.5-35B-A3B-abliterated-Q4_K_M.gguf \
  -t 48 --port 8200 &

# Send concurrent requests to both and measure aggregate t/s
```

**If aggregate dual-NUMA > 1.5× single baseline**: NUMA-parallel verification becomes viable — each node verifies one draft token independently, bypassing the batched verification wall.

### Risk

Medium-high. Requires deep changes to the prefill pipeline. Cross-NUMA coordination adds complexity. Most valuable for long-context prefill, less impact on generation.

## Priority & Dependencies

```
Phase 1 (MoE self-draft) ──→ NOT VIABLE. 2.9% acceptance (1-expert), 55% (2-expert). Net throughput always negative.
Phase 2 (conv-only ckpt) ──→ DEFERRED — incorrect premise for Delta Net architecture
Phase 3 (attn-only draft) ──→ NOT VIABLE — 0.51x throughput. Near-zero acceptance rate.
Phase 4 (NUMA prefill)   ──→ Deferred. Infrastructure-heavy, prefill-only benefit.
Phase 5 (MTP heads)      ──→ NOT VIABLE — 78.5% acceptance but 0.56x throughput. 2-token batch = 3-4x single decode on hybrid.
```

**State of self-draft acceleration**: ALL self-drafting approaches exhausted across both hybrid and pure MoE:
- MoE expert reduction: 1.18x hybrid / 0.50-0.72x with speculation
- Attention-only: 0.51x
- Layer exit (HSD): -44% to -51%
- Tree speculation (3 variants): -53% to -66%
- MoE self-draft (1-expert): -50% (2.9% acceptance)
- MoE self-draft (2-expert): -28% (55% acceptance, insufficient speedup)
- MTP-1 speculation: 0.56x (78.5% acceptance, but 2-token batch = 3-4x single decode)

**Fundamental limitation**: 75% Delta Net recurrent layers process tokens sequentially regardless of batch size. Multi-token verification batches cost N × single-token decode, making ALL draft-verify paradigms net-negative on hybrid models.

**Remaining acceleration paths** (non-speculation):
1. External draft + freeze-recurrent (+5.4% validated)
2. Prompt lookup
3. NUMA-aware prefill pipelining (Phase 4, deferred)

## Validation Checklist

- [x] **MoE self-draft Step 0**: Qwen3.5-35B-A3B hybrid: 1.18x — NOT VIABLE (recurrent layers dominate)
- [x] **MoE self-draft Step 0**: Qwen3-Coder-30B-A3B pure MoE: 1.35x — VIABLE
- [x] **MoE self-draft Step 0**: Qwen3-235B-A22B pure MoE: 1.79x — HIGHLY VIABLE
- [x] **MoE self-draft Step 1**: Acceptance measured on Qwen3-235B: 1-expert 2.9%, 2-expert 55%. Net 0.50-0.72x — NOT VIABLE
- [x] **MoE self-draft Step 2**: Net throughput NEGATIVE on all configs (best: 0.72x with 2-expert)
- [x] **MTP heads (Phase 5) Steps 1-6**: Conversion, loading, forward pass, validation complete. 78.5% exact-match (Q4_K_M), 78.9% (Q8_0), 97.7-99.2% top-5.
- [x] **MTP heads (Phase 5) Step 7**: Speculation loop implemented. 0.56x baseline — NOT VIABLE on hybrid (2-token batch = 3-4x single decode).
- [x] **Attention-only draft**: 0.51x throughput on Qwen3.5-35B-A3B — NOT VIABLE (near-zero acceptance)
- [ ] All results published in research docs

## Code Change Policy

- Phases 1-3: Changes on `feature/tree-speculation` branch (or new feature branch) off `production-consolidated-v2`
- Phase 4: Separate feature branch (deep infrastructure change)
- All validate → merge to `production-consolidated-v2`

## Conflict Analysis

No conflicts with tree-speculation handoff (that handoff's Phase 8 covers STree, which is tree-level SSM support — complementary, not overlapping). No conflicts with other active handoffs.

## References

- [STree: Speculative Tree Decoding for Hybrid State-Space Models](https://arxiv.org/abs/2505.14969) — tree-level SSM support (covered in tree-speculation Phase 8)
- [RAD: Redundancy-Aware Distillation for Hybrid Models](https://arxiv.org/abs/2505.22135) — identifies redundant attention layers via self-speculative decoding
- [SpecMamba: Accelerating Mamba Inference on FPGA](https://arxiv.org/pdf/2509.19873) — FPGA-focused but relevant algorithmic insights
- Completed handoff: `ssm-checkpoint-speculation.md` — full checkpoint implementation details
- Completed handoff: `hsd-hierarchical-self-speculation.md` — freeze-recurrent validation data

## Research Intake Update — 2026-03-16

### New Related Research
- **[intake-152] "Qwen3.5 Serving Recipe"** (docs.vllm.ai)
  - Relevance: Production configuration insights for the same Qwen3.5 hybrid architecture we're optimizing on llama.cpp
  - Key technique: **MTP-1 speculative decoding** — uses model-native Multi-Token Prediction heads as draft source (1 speculative token/step). Fundamentally different from our self-draft attempts — MTP heads were co-trained with the model specifically for multi-token prediction, bypassing the recurrent state forking problem entirely
  - Delta from current approach: All our self-draft approaches failed on Qwen3.5 hybrid AND pure MoE (expert reduction 0.50-0.72x with speculation, attention-only -49%, layer exit -44% to -51%, tree -53% to -66%). MTP heads are the most promising remaining path.
  - **Qwen3.5 HF checkpoint MTP status (audited 2026-03-16)**: **MTP weights ARE present.** `text_config.mtp_num_hidden_layers=1`, `mtp_use_dedicated_embeddings=False`. **785 MTP tensors** in safetensors: 1 full transformer layer (self_attn QKV+O + 256 MoE experts + shared expert + norms) + projection head (`mtp.fc`, `mtp.pre_fc_norm_embedding`, `mtp.pre_fc_norm_hidden`, `mtp.norm`).
  - **llama.cpp GGUF conversion**: `Qwen3NextModel.modify_tensors()` at line 4497 **STRIPS all MTP tensors**: `if name.startswith("mtp"): return`. All existing GGUF files lack MTP weights.
  - **llama.cpp inference**: `llama_layer_nextn` struct exists with 6 tensor types. GGUF keys defined. Forward pass skips nextn layers. GLM4_MOE and BailingMoe2 have partial conversion (remaps `mtp.*` to extra layers). Inference NOT implemented for any architecture.
  - **BailingMoe2 reference**: `convert_hf_to_gguf.py:9410-9427` has working MTP conversion that remaps `mtp.layers.{L}` → `model.layers.{L+num_hidden_layers}` and shared tensors (fc, norms) to all nextn layer slots.
  - **Action plan (Phase 5)**:
    1. Un-strip MTP from Qwen3.5 converter (model `Qwen3NextModel.modify_tensors`, follow BailingMoe2 pattern)
    2. Add `mtp_num_hidden_layers` to GGUF metadata
    3. Re-convert Qwen3.5-35B-A3B with MTP weights preserved
    4. Implement MTP-1 forward pass: run MTP layer on last hidden state → predict next token → use as draft
    5. Wire into `common_speculative` as self-draft source (no external model needed)
  - Additional insights: text-only mode optimization (skip vision encoder for throughput), hybrid cache alignment (recurrent state needs special handling, graph capture size limits), prefix caching explicitly experimental for hybrids (confirms our recurrent state invalidation challenge), YaRN RoPE for >262K context

## DFlash Cross-Reference (2026-03-17)

**DFlash block diffusion** ([`dflash-block-diffusion-speculation.md`](dflash-block-diffusion-speculation.md)) introduces a potential hybrid reopener via NUMA-parallel verification:

- DFlash Phase 6 benchmarks concurrent single-token decodes across NUMA nodes on Qwen3.5-35B-A3B
- If aggregate throughput from parallel independent decodes exceeds serial throughput, this reopens MTP-1 (78.5% acceptance), DFlash, and tree speculation on hybrid models
- Each NUMA node would verify one draft token independently — bypassing the batched verification wall that blocked all prior approaches
- See [`inference-acceleration-index.md`](inference-acceleration-index.md) for the full inference optimization landscape

## Phase 5 — MTP-1 Speculative Decoding (NOT VIABLE on Hybrid)

**Status**: CLOSED. 78.5% acceptance excellent, but speculation loop 0.56x baseline. See `handoffs/completed/mtp-speculative-decoding.md`.

### Step 6 Validation Results (2026-03-17)

MTP-1 forward pass validated against target model's next-token ground truth. Tested across quantizations on Qwen3.5-35B-A3B, EPYC 9655.

| Quantization | Exact Match (Top-1) | Top-5 Match | Notes |
|-------------|--------------------:|------------:|-------|
| Q4_K_M      | 78.5%               | 97.7%       | Production quantization |
| Q8_0        | 78.9%               | 99.2%       | Near-lossless quantization |

78.5% exact-match acceptance is exceptionally strong for a single-head draft source — comparable to high-quality external draft models, but with zero additional memory for a separate model. Top-5 accuracy above 97% across both quantizations confirms the MTP head's output distribution closely tracks the main model.

### Token Alignment Bug (Fixed)

The MTP head was trained with a specific input convention: `embed(token_{n+1}) + hidden_state(n)`. The initial implementation incorrectly used `hidden_state(n+1)` for both components, producing misaligned predictions (~40% acceptance).

**Fix**: Cache the hidden state from the previous forward pass and feed it alongside the current token's embedding into the MTP projection layers. The MTP forward pass now uses:
- `enorm(embed(current_token))` — embedding of the token being predicted FROM
- `hnorm(cached_hidden_state)` — hidden state from the PREVIOUS position

After the fix, acceptance jumped from ~40% to 78.5% (Q4_K_M), confirming the training convention match.

### Step 7 Results — Speculation Loop (2026-03-17)

Implemented standalone MTP speculation loop (`tools/mtp-speculation/`). New APIs: `LLM_GRAPH_TYPE_MTP_EVAL`, `llama_decode_mtp()`.

| Operation | Latency | Notes |
|-----------|---------|-------|
| MTP eval (decode_mtp) | ~10ms | 5% of full decode — excellent |
| Single-token decode | ~220ms | Baseline |
| 2-token verify batch | 560-816ms | 3-4x single decode |

**Result**: 0.56x baseline. Draft acceptance 70.3%, but 2-token batch cost dominates. With 70% acceptance: ~710ms/round for 1.7 tokens vs ~374ms for equivalent single decodes.

**Root cause**: Same fundamental limitation as tree speculation — 75% Delta Net recurrent layers process tokens sequentially regardless of batch size. This makes ALL draft-verify paradigms net-negative on Qwen3.5 hybrid.

**Would work on non-recurrent models**: On pure attention architectures (e.g. Qwen2.5, Llama), 2-token batch ≈ 1.05x single decode cost, so 78.5% acceptance would yield ~1.5x speedup. Note: Qwen3.5-27B is also hybrid Delta Net (3:1 recurrent:attention) — same limitation applies despite being dense FFN (not MoE).

## Closeout

Update `logs/agent_audit.log`, `progress/2026-03/YYYY-MM-DD.md`, this handoff status, Chapter 10 with empirical results.
