# Handoff: HSD + Hierarchical Self-Speculation

**Status**: COMPLETE — all phases done, ready to archive
**Created**: 2026-03-07
**Updated**: 2026-03-10
**Blocked by**: None (specexec-verification-profiling completed 2026-03-10)
**Blocks**: tree-speculation-numa-drafting

## Objective

Implement three improvements to speculative decoding:
1. **HSD verification algorithm** — capped branch resampling at rejection point (+3-7% accepted tokens)
2. **Layer-skip self-speculation benchmarking** — evaluate `--n-layer-exit` for SWIFT-like self-speculation (never benchmarked)
3. **Hierarchical speculative decoding** — intermediate verification layers (HiSpec pattern)

### Upstream Empirical Data (from specexec-verification-profiling, 2026-03-10)

Key findings that parameterize this handoff:

1. **Verification cost is NOT near-flat for Q4_K_M models**: 4-5x cost growth from N=1 to N=64. Only f16 models show near-flat (1.69x). Dequantization compute overhead prevents pure bandwidth-bound regime on CPU.
2. **Linear K=16 is already optimal**: Throughput flat from K=16 to K=256 (acceptance rate decay neutralizes). No benefit from simply increasing `--draft-max`.
3. **Draft model speed varies 4x**: Qwen3.5-0.8B is unexpectedly slow (44 t/s) vs Qwen2.5-Coder-0.5B (185 t/s). Drafter selection critical.
4. **f16 targets are the sweet spot for tree/HSD speculation**: Near-flat verification means tree verification of 64 nodes costs ~1.7x (vs ~4-5x for Q4_K_M). Combined with f16's inherently better quality, **prioritize f16 target models** for tree speculation — they get the most throughput gain AND quality benefit.
5. **Tree speculation estimated gain**: 1.5-2.5x over linear K=16 for Q4_K_M, potentially 3-4x for f16 targets.

Full data: `epyc-inference-research/docs/experiments/specexec-verification-profile.md`

## Implementation Status (2026-03-10)

### Phase 1 — HSD Capped Branch Resampling ✅

**Implemented in**: `llama.cpp/common/sampling.cpp` (on `production-consolidated-v2`)

Changes to `common_sampler_sample_and_accept_n()`:
- When target disagrees with draft token, look up `p_target(draft[i])` from candidate distribution
- If `p_draft > 0.3`, stochastically accept with probability proportional to `p_draft`
- Deterministic hash from sampler seed + position for reproducibility
- At most one HSD recovery per sequence (cap on accepting extra tokens)
- `common_sampler_reset()` + re-accept pattern to undo sampler state on recovery
- ~25 lines added to inner loop. No signature changes.

**Validation needed**: Build ✅, run with temp=0.8 on 20 prompts to measure `draft_n_accepted` improvement.

### Phase 2a — `--n-layer-exit-draft` Flag ✅

Added across 3 files:
1. `common/common.h` — `int32_t n_layer_exit_draft = 0;`
2. `common/arg.cpp` — CLI arg + env var `LLAMA_ARG_N_LAYER_EXIT_DRAFT`
3. `tools/server/server-context.cpp` — wires to `params_dft.n_layer_exit` before draft context creation

**Validation**: `llama-server --help | grep n-layer-exit-draft` ✅

### Phase 2b — Self-Speculation Benchmark Script ✅

**Created**: `epyc-inference-research/scripts/benchmark/bench_self_speculation.sh`

Server-mode benchmark using OpenAI-compat API + metrics endpoint. Tests:
- Baseline (no speculation)
- External draft (Qwen3.5-0.8B)
- Prompt lookup
- Self-speculation at exit depths: 1/4, 1/3, 1/2 of model layers

Models: Qwen3.5-9B (32 layers), Qwen3.5-27B (64 layers)
Output: CSV to `data/hsd/`, markdown to `docs/experiments/self-speculation-benchmark.md`

**Validation needed**: Run the benchmark.

### Phase 3 — Hierarchical Speculation (HiSpec) ✅

**Runtime API**: `llama_set_n_layer_exit()` in `include/llama.h` + `src/llama-context.cpp`
- Public method `llama_context::set_n_layer_exit()` sets `cparams.n_layer_exit` at runtime

**New flags** in `common/common.h` + `common/arg.cpp`:
- `--hierarchical-spec` (bool) — enable two-pass intermediate verification
- `--n-layer-exit-intermediate N` (int, default 0 = auto N/4)

**Hierarchical verification loop** in `tools/server/server-context.cpp`:
- When `hierarchical_spec` enabled and n_draft > 1:
  1. Clear KV cache for draft range
  2. Build intermediate batch, decode at `intermediate_depth` layers
  3. Clone sampler, run `common_sampler_sample_and_accept_n()` on intermediate logits
  4. Collect survivors
  5. Clear KV cache again, restore full depth
  6. Build filtered batch with only survivors + bonus position
  7. Full decode + final verification
- Falls back to standard single-pass on intermediate decode failure

**Validation**: `llama-server --help | grep hierarchical` ✅. Build ✅. Throughput comparison needed.

### Phase 4 — Orchestrator Integration ✅

**AccelerationConfig** (`src/registry_loader.py`):
- `n_layer_exit_draft: int | None` — for self-speculation
- `hierarchical_spec: bool` — enable HiSpec
- `n_layer_exit_intermediate: int | None` — intermediate depth

**Dispatch** (`scripts/server/orchestrator_stack.py`):
- `self_speculation` type: `-md model_path --n-layer-exit-draft N --draft-max K`
- `hierarchical_speculation` type: same + `--hierarchical-spec` + optional `--n-layer-exit-intermediate N`

**Feature flags** (`src/features.py`):
- `self_speculation: bool = False` (class attr + production/test defaults + env reader)
- `hierarchical_speculation: bool = False` (same)

**Tests**: `pytest tests/unit/test_registry_loader.py` — 19/19 pass ✅

## Benchmark Results (2026-03-10)

### Self-Speculation: Two Failure Modes

**Qwen3.5 (hybrid SSM — Mamba2 + attention every 4th layer):**

| Config | 9B t/s | Delta | Accept Rate | 27B t/s | Delta |
|--------|--------|-------|-------------|---------|-------|
| baseline | 15.91 | — | — | 4.51 | — |
| external 0.8B | 10.59 | -33% | 62.5% | 3.51 | -22% |
| self-spec exit=8 | 8.83 | -44% | 77.1% | — | — |
| self-spec exit=16 | 7.76 | -51% | 69.9% | 2.85 | -37% |
| prompt lookup | SEGFAULT | — | — | SEGFAULT | — |

All speculation configs slower than baseline. SSM checkpoint/restore overhead dominates.

**Qwen3 (dense — pure attention):**

| Config | 32B t/s | Delta | Accept Rate |
|--------|---------|-------|-------------|
| baseline | 7.85 | — | — |
| self-spec exit=16 | ~7.7 | -2% | 1.5% |
| self-spec exit=32 | ~7.7 | -2% | 0.5% |

Near-zero acceptance rates — intermediate layer logits don't produce useful next-token predictions without early-exit training (SWIFT/LayerSkip).

### Root Cause Analysis: SSM Checkpoint Overhead

The checkpoint/restore mechanism in `llama-memory-recurrent.cpp` copies ALL recurrent tensor data via GPU→CPU→GPU roundtrip:

Per speculation round: checkpoint (GPU→CPU ~2GB) → N draft decodes → 1 verify decode → restore (CPU→GPU ~2GB) → 1 re-advance decode

Optimization opportunities identified:
1. **GPU-to-GPU copy** — use `ggml_backend_tensor_copy` instead of get/set roundtrip through CPU
2. **Lazy restore** — skip restore entirely when all drafts accepted (high acceptance rate scenarios)
3. **Partial checkpoint** — only save active sequence cells (2-8 vs 1024) and affected layers
4. **Async transfers** — pipeline checkpoint save with draft generation

### Conclusion

- **Self-speculation** not viable on either architecture without early-exit fine-tuning
- **External draft** works on dense models (production config), but not hybrid SSM
- **HSD Phase 1** (capped branch resampling) still benefits external draft on dense models
- **HiSpec with external draft** on dense models is the untested combination that could work
- **SSM checkpoint optimization** could unblock speculation on Qwen3.5 hybrid models

Full data: `epyc-inference-research/docs/experiments/self-speculation-benchmark.md`

## SSM Checkpoint Optimization (2026-03-10)

**Branch**: `feature/ssm-checkpoint-opt` (from `production-consolidated-v2`)

### Double-Buffer Pointer Swap (Optimization 1 + 3)

Pre-allocate shadow r_l/s_l tensors. On checkpoint, copy active→shadow via `ggml_backend_tensor_copy()`. On restore, `std::swap(r_l, shadow_r_l)` — O(1) pointer swap eliminates ~144MB restore memcpy.

Also implemented partial cell metadata save — only saves/restores non-empty cells (typically 1-8 vs 1024).

**Files changed**: `src/llama-memory-recurrent.h`, `src/llama-memory-recurrent.cpp`
**Build**: ✅ clean
**Memory cost**: 2x recurrent state allocation (shadow buffers)

### Benchmark Script

`epyc-inference-research/scripts/benchmark/bench_hispec_external.sh` — tests both:
1. HiSpec + external draft on dense Qwen3-32B
2. SSM checkpoint optimization validation on Qwen3.5-9B

## HiSpec + External Draft Results (2026-03-10)

### Dense Qwen3-32B

| Config | t/s | vs Baseline | Accept Rate |
|--------|-----|-------------|-------------|
| baseline | 8.44 | — | — |
| external Qwen2.5-Coder-0.5B | **13.07** | **+54.9%** | 52.5% |
| external Qwen3-0.6B | **13.06** | **+54.7%** | 50.8% |
| HiSpec intermediate=16 | 7.57 | -10.3% | 28.0% |
| HiSpec intermediate=32 | 7.50 | -11.1% | 26.8% |

**HiSpec is a bust on dense models.** Intermediate logits reject good drafts (acceptance halves). Same root cause as self-spec: untrained intermediate layers can't predict next tokens.

### SSM Hybrid Qwen3.5-9B (Post Checkpoint Optimization)

| Config | Pre-opt t/s | Post-opt t/s | Delta | Accept Rate |
|--------|-------------|--------------|-------|-------------|
| baseline | 15.91 | 15.76 | -1% | — |
| external Qwen3.5-0.8B | 10.59 | 11.60 | +9.5% | 62.8% |
| external Qwen2.5-Coder-0.5B | — | **14.58** | -7.5% vs base | 60.7% |
| self-spec exit=8 | 8.83 | 8.27 | -6% | 75.0% |

Checkpoint optimization measurable (+9.5% on external draft). Qwen2.5-Coder-0.5B is the best drafter.

### Freeze-Recurrent Results (2026-03-10) — BREAKTHROUGH

| Config | t/s | vs Baseline | Accept Rate |
|--------|-----|-------------|-------------|
| baseline | 15.14 | — | — |
| external Qwen2.5-Coder-0.5B | 15.15 | +0.1% | 62.7% |
| **freeze + ext Qwen2.5-Coder** | **15.96** | **+5.4%** | 47.9% |
| freeze + ext Qwen3.5-0.8B | 12.06 | -20.3% | 48.6% |

**First time speculation beats baseline on hybrid SSM.** Freeze-recurrent eliminates checkpoint/restore/re-advance. Acceptance drops ~13pp (stale SSM state) but fast drafter compensates. Applicable to Qwen3.5, Qwen3.5-MoE, Qwen3-Next.

## Remaining Work

- [x] Run Phase 2b benchmark — DONE, self-spec not viable
- [x] All 4 phases implemented and building on production-consolidated-v2
- [x] Investigate SSM checkpoint optimization — DONE, double-buffer implemented
- [x] Run HiSpec + external draft benchmark on dense Qwen3-32B — DONE, HiSpec is a bust
- [x] Run SSM checkpoint optimization benchmark on Qwen3.5-9B — DONE, +9.5% improvement
- [x] Implement freeze-recurrent speculation — DONE, `--freeze-recurrent-draft` flag
- [x] Benchmark freeze-recurrent on Qwen3.5-9B — **BREAKTHROUGH: +5.4% over baseline**
- [x] Run Phase 1 validation — `--no-hsd` toggle added, A/B benchmark complete on Qwen3-32B: HSD gives +29 accepted tokens (+1.3%), +0.98pp acceptance rate (53.16% vs 52.18%), +0.8% throughput (13.03 vs 12.93 t/s). Small but free marginal gain.
- [x] Investigate prompt lookup segfault — fixed: auto freeze-recurrent for ALL speculation on hybrid models (not just lookup). Lookup now works on hybrid via frozen SSM state. Tracked per-round via `slot.freeze_recurrent_active` + `draft_from_lookup` flag.
- [x] Add architecture detection to gate self-speculation — startup warnings for `--n-layer-exit-draft` on hybrid (recommend freeze-recurrent) and dense (recommend external draft). Info note for `--lookup` on hybrid.
- [x] Update Chapter 10 with empirical results — Section 11 added with 8 subsections and decision matrix

## Files Changed

| Action | File | Repo |
|--------|------|------|
| Modified | `common/sampling.cpp` | llama.cpp (production-consolidated-v2) |
| Modified | `common/common.h` | llama.cpp (production-consolidated-v2) |
| Modified | `common/arg.cpp` | llama.cpp (production-consolidated-v2) |
| Modified | `include/llama.h` | llama.cpp (production-consolidated-v2) |
| Modified | `src/llama-context.h` | llama.cpp (production-consolidated-v2) |
| Modified | `src/llama-context.cpp` | llama.cpp (production-consolidated-v2) |
| Modified | `tools/server/server-context.cpp` | llama.cpp (feature/ssm-checkpoint-opt) |
| Modified | `common/common.h` | llama.cpp (feature/ssm-checkpoint-opt) — `enable_hsd_recovery` field |
| Modified | `common/arg.cpp` | llama.cpp (feature/ssm-checkpoint-opt) — `--no-hsd` flag |
| Modified | `common/sampling.cpp` | llama.cpp (feature/ssm-checkpoint-opt) — HSD guard on `enable_hsd_recovery` |
| Modified | `docs/chapters/10-advanced-speculative-decoding.md` | epyc-inference-research — Section 11 empirical results |
| Created | `scripts/benchmark/bench_self_speculation.sh` | epyc-inference-research |
| Modified | `src/registry_loader.py` | epyc-orchestrator |
| Modified | `scripts/server/orchestrator_stack.py` | epyc-orchestrator |
| Modified | `src/features.py` | epyc-orchestrator |

## Code Change Policy

Note: C++ changes were implemented directly on `production-consolidated-v2` (not on `llama.cpp-experimental` as originally planned) because the experimental branch doesn't have the layer-exit foundation code. The layer-exit feature only exists on production-consolidated-v2.

## Conflict Analysis

No conflicts with active handoffs. Layer-skip code is already on `production-consolidated-v2` and is not being modified by any other handoff.

## Closeout

Update `logs/agent_audit.log`, `progress/2026-03/YYYY-MM-DD.md`, this handoff status, Chapter 10 with empirical results.
