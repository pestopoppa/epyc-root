# Handoff: HSD + Hierarchical Self-Speculation

**Status**: ready
**Created**: 2026-03-07
**Blocked by**: None (specexec-verification-profiling completed 2026-03-10)
**Blocks**: tree-speculation-numa-drafting

## Objective

Implement three improvements to speculative decoding:
1. **HSD verification algorithm** — capped branch resampling at rejection point (+3-7% accepted tokens)
2. **Layer-skip self-speculation benchmarking** — evaluate `--n-layer-exit` for SWIFT-like self-speculation (never benchmarked)
3. **Hierarchical speculative decoding** — intermediate verification layers (HiSpec pattern)

All C++ changes go to `llama.cpp-experimental` first → validate → cherry-pick to `production-consolidated-v2`.

### Upstream Empirical Data (from specexec-verification-profiling, 2026-03-10)

Key findings that parameterize this handoff:

1. **Verification cost is NOT near-flat for Q4_K_M models**: 4-5x cost growth from N=1 to N=64. Only f16 models show near-flat (1.69x). Dequantization compute overhead prevents pure bandwidth-bound regime on CPU.
2. **Linear K=16 is already optimal**: Throughput flat from K=16 to K=256 (acceptance rate decay neutralizes). No benefit from simply increasing `--draft-max`.
3. **Draft model speed varies 4x**: Qwen3.5-0.8B is unexpectedly slow (44 t/s) vs Qwen2.5-Coder-0.5B (185 t/s). Drafter selection critical.
4. **f16 targets are the sweet spot for tree/HSD speculation**: Near-flat verification means tree verification of 64 nodes costs ~1.7x (vs ~4-5x for Q4_K_M). Combined with f16's inherently better quality, **prioritize f16 target models** for tree speculation — they get the most throughput gain AND quality benefit.
5. **Tree speculation estimated gain**: 1.5-2.5x over linear K=16 for Q4_K_M, potentially 3-4x for f16 targets.

Full data: `epyc-inference-research/docs/experiments/specexec-verification-profile.md`

## Background

### HSD (Hierarchical Speculative Decoding — verification improvement)
Current `common_sampler_sample_and_accept_n()` does linear scan: accept tokens while target agrees, reject at first disagreement. HSD adds capped branch resampling at the rejection point, potentially recovering 1 additional token per sequence. Small change, confined to sampling code.

### Layer-skip
Patches #5 and #6 (`b5e11afb0`, `42e7d627f`) were successfully cherry-picked to `production-consolidated-v2` during the upstream rebase (completed 2026-03-03). The feature adds `--n-layer-exit` for Qwen2, Qwen3, Qwen3-MoE, Qwen3-VL-MoE, and Qwen3-Next model builders. It has **never been benchmarked for self-speculation** — included as a feature but no handoff or progress entry shows it was ever tested.

### Hierarchical speculation
Uses layer-skip as an intermediate verifier: draft → cheap intermediate check at layer N/4 → full verification only for tokens passing intermediate check. Reduces wasted full-model compute on bad draft tokens.

## Existing Infrastructure

### llama.cpp layer-skip (already on production-consolidated-v2)
- `--n-layer-exit N` flag: registered in `common/arg.cpp:1281`, wired via `common.cpp:1371`
- Supported architectures: Qwen2, Qwen3, Qwen3-MoE, Qwen3-VL-MoE, Qwen3-Next (commits b5e11afb0, 42e7d627f)
- Available to server (via `common_params_parse` in `tools/server/server.cpp:73`)
- Branch policy documented in `BRANCH_RULES.md`: experimental worktree → validate → cherry-pick to production

### Benchmark scripts (reuse for Phase 2)
| Script | Path | Reuse |
|--------|------|-------|
| `bench_tree_speculation.sh` | `epyc-inference-research/scripts/benchmark/` | Tree param sweep — adapt for layer-exit sweep |
| `run_benchmark.py` | `epyc-inference-research/scripts/benchmark/` | Unified runner with acceptance_rate tracking |
| `sidecar_benchmark.py` | `epyc-inference-research/scripts/benchmark/` | Server-mode benchmark with draft_n/draft_n_accepted |
| `output_parser.py` | `epyc-inference-research/scripts/lib/` | `parse_acceptance_rate()`, `parse_timings()` |

Note: `run_draft_discovery.sh` is NOT reusable for self-speculation (requires different draft and target models). Phase 2 needs a new thin script or adapt `bench_tree_speculation.sh`.

### Orchestrator speculation wiring (for Phase 4)
- `orchestrator_stack.py:779-798` already handles `speculative_decoding` acceleration type with `-md` and `--draft-max`
- `orchestrator_stack.py:714-721` hardcodes explore worker spec decode (draft model + K=24 + lookup)
- New acceleration types (`self_speculation`, `hierarchical_speculation`) should follow the same `accel.type` dispatch pattern

## Phase 1 — HSD Capped Branch Resampling

**Target function**: `common_sampler_sample_and_accept_n()` in `common/sampling.cpp`
**Call site**: `server-context.cpp` (search: `common_sampler_sample_and_accept_n`; currently line 2891, may shift with upstream changes)

Current behavior:
```
for each draft token:
  if target agrees → accept
  else → reject, stop, resample from target distribution
```

HSD modification:
```
for each draft token:
  if target agrees → accept
  else →
    compute branch divergence probability
    apply capped resampling (bounded probability correction)
    if resampled token matches draft → accept one more token
    break and resample from adjusted distribution
```

**Files changed**:
- `llama.cpp/common/sampling.cpp` — core algorithm change
- `llama.cpp/common/sampling.h` — signature changes if needed (unlikely)

No call-site changes required. The function signature and return semantics stay the same.

**Branch**: `llama.cpp-experimental` → `feature/hsd-verification` → validate → cherry-pick to `production-consolidated-v2`

**Validation**: Compare accepted token counts (before/after) on test prompts. Expected: +3-7% improvement in average accepted tokens per speculation round.

## Phase 2 — Layer-Skip Self-Speculation Benchmarking

Test the SWIFT-like self-speculation pattern using existing `--n-layer-exit` infrastructure:

```bash
# Same model as both target and draft, draft exits early
llama-server -m Qwen3.5-9B-Q4_K_M.gguf \
  -md Qwen3.5-9B-Q4_K_M.gguf \
  --n-layer-exit-draft 16 --draft-max 16 -t 96
```

**Sweep `--n-layer-exit-draft`** at different fractions of total layers:

| Model | Total Layers | 1/4 | 1/3 | 1/2 |
|-------|-------------|-----|-----|-----|
| Qwen3.5-9B | 32 | 8 | 11 | 16 |
| Qwen3.5-27B | 64 | 16 | 21 | 32 |

**Compare against baselines**:
- No speculation (baseline)
- External draft (Qwen3.5-0.8B)
- Prompt lookup only
- Self-spec at each exit depth

**Metrics**: tokens/s, acceptance rate, memory usage (self-spec avoids loading a second model).

**Prompts**: Use standard benchmark questions from `question_pool.py`
(`/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/question_pool.py`).
Select 20 prompts spanning `coder` and `thinking` suites for reproducibility.

### `--n-layer-exit-draft` Implementation Spec (prerequisite for Phase 2)

The example command above uses `--n-layer-exit-draft` which **does not yet exist**. Only `--n-layer-exit` exists
(registered in `arg.cpp:1281`), and it IS available in the server (via `common_params_parse` in `server.cpp:73`),
but it applies to the main model context only. For self-speculation, the draft context needs a SEPARATE layer-exit
depth while the target runs all layers.

**Code path** (4 files, ~15 LOC total):

1. `common/common.h:379` — add field:
   `int32_t n_layer_exit_draft = 0; // layer exit for draft context (self-speculation)`

2. `common/arg.cpp` — register new flag after line 1287:
   `{"--n-layer-exit-draft"}, "N", ... params.n_layer_exit_draft = value;`

3. `tools/server/server-context.cpp:670-697` — in the draft params setup block:
   After `auto params_dft = params_base;` (line 670), override:
   `if (params_base.n_layer_exit_draft > 0) params_dft.n_layer_exit = params_base.n_layer_exit_draft;`
   This makes `common_context_params_to_llama(params_dft)` (line 697) pick up the draft-specific exit depth.

4. `common/common.cpp:1371` — no change needed (already wires `params.n_layer_exit` → `cparams.n_layer_exit`)

**Key insight**: `params_dft` is a copy of `params_base` (line 670), so overriding `params_dft.n_layer_exit`
before `common_context_params_to_llama(params_dft)` at line 697 is sufficient. The main model context
is created separately and keeps its own `n_layer_exit` (0 = all layers).

**Branch**: implement on `llama.cpp-experimental` per BRANCH_RULES.md, validate, cherry-pick.

## Phase 3 — Hierarchical Speculation (HiSpec-Style)

Implement intermediate verification using layer-skip. This is the HiSpec pattern from Chapter 10 Section 2.1, lines 135-171 (Kumar et al., Oct 2025).

Related Chapter 10 sections:
- Phase 1 (HSD): Section 2.2, lines 156-173 (Zhou et al., arXiv:2601.05724)
- Phase 2 (Layer-skip): Section 3.2, lines 191-197 (Elhoushi et al., arXiv:2404.16710)
- Phase 3 (HiSpec): Section 2.1, lines 135-171 (Kumar et al., Oct 2025)
- Comparison: SWIFT (Section 3.3, lines 199-205)

### Algorithm

1. **Draft K tokens** (via small external draft or self-speculation from Phase 2)
2. **Intermediate verify at layer N/4** — cheap filter using layer-skip
   - Run draft tokens through target model but exit at layer N/4
   - Compare intermediate logits against draft tokens
   - Accept tokens where intermediate model agrees (~69% expected)
3. **Buffer tentatively accepted tokens** (batch size N_i ≈ 4)
4. **Full verify** only for tokens passing intermediate check

### Implementation

Modify the speculation loop in `server-context.cpp`:

```
Current:  draft(K) → full_verify(K) → accept/reject
HiSpec:   draft(K) → intermediate_verify(K, exit=N/4) → full_verify(K_filtered) → accept/reject
```

The intermediate verification reuses the layer-skip infrastructure — same model, just different exit point. No additional model loading.

**Files changed**:
- `llama.cpp/tools/server/server-context.cpp` — intermediate verification loop
- Reuses existing layer-skip infrastructure (no new model loading code)

**Validation**:
- Intermediate filter correctly passes tokens that full model accepts
- Intermediate filter rejects tokens that full model would reject (reduced wasted compute)
- End-to-end throughput improvement measured

## Phase 4 — Orchestrator Integration

### Model registry
Add new acceleration types to per-model `acceleration:` blocks in `epyc-inference-research/orchestration/model_registry.yaml` (following the existing `type: speculative_decoding` pattern, NOT a new top-level section):

```yaml
# Per-model example (same pattern as existing speculative_decoding entries):
qwen35-9b:
  acceleration:
    type: self_speculation
    n_layer_exit_draft: 16
    draft_max: 16

qwen35-27b:
  acceleration:
    type: hierarchical_speculation
    n_layer_exit_draft: 16
    hierarchical_spec: true
    draft_max: 16
```

### Launch flags
`epyc-orchestrator/scripts/server/orchestrator_stack.py` — handle new flags:
- `--n-layer-exit-draft N` for self-speculation
- `--hierarchical-spec` for intermediate verification mode

### Feature flags
`epyc-orchestrator/src/features.py` — add:
- `self_speculation`: default off
- `hierarchical_speculation`: default off

## Validation Checklist

- [ ] HSD: measurable improvement in accepted tokens on test prompts (+3-7%)
- [ ] Layer-skip self-spec: benchmark table (speed + acceptance) across exit depths
- [ ] Hierarchical: intermediate verification filters correctly, end-to-end throughput measured
- [ ] Server flag `--n-layer-exit-draft` works (added if missing)
- [ ] Orchestrator integration: new acceleration types, launch flags, feature flags
- [ ] All results published in research docs

## Files

| Action | File | Repo |
|--------|------|------|
| Modify | `common/sampling.cpp` | llama.cpp-experimental |
| Modify | `common/sampling.h` (if needed) | llama.cpp-experimental |
| Modify | `tools/server/server.cpp` (if flag missing) | llama.cpp-experimental |
| Modify | `tools/server/server-context.cpp` | llama.cpp-experimental |
| Modify | `scripts/server/orchestrator_stack.py` | epyc-orchestrator |
| Modify | `src/features.py` | epyc-orchestrator |
| Modify | `orchestration/model_registry.yaml` | epyc-inference-research |
| Create | `data/hsd/` (directory for benchmark CSV output) | epyc-inference-research |
| Create | Benchmark results in `docs/experiments/` (dir exists) | epyc-inference-research |

## Code Change Policy

All C++ changes → `llama.cpp-experimental` first → validate → cherry-pick to `production-consolidated-v2`.

## Conflict Analysis

No conflicts with active handoffs. Layer-skip code is already on `production-consolidated-v2` and is not being modified by any other handoff.

## Closeout

Update `logs/agent_audit.log`, `progress/2026-03/YYYY-MM-DD.md`, this handoff status, Chapter 10 with empirical results.
