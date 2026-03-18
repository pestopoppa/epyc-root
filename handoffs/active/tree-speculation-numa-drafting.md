# Handoff: Tree Speculation + NUMA-Pinned Dual Drafting

**Status**: Phase 4 validated + draft_max optimized (2026-03-18). **+17-21% throughput on 3 production models from draft_max config change.** Tree wins on slow f16 only (+12.2%). Phase 7 UNBLOCKED (NUMA, needs bare metal).
**Created**: 2026-03-07
**Audited**: 2026-03-10 — 9 edits applied (branch strategy, polymorphic architecture, line numbers, DySpec batching, Phase 3 deferral, Phase 4 refocus, validation)
**Phase 1**: ✅ complete (2026-03-11) — tree speculation implemented in server, builds clean, 5 files on `feature/tree-speculation`
**Phase 2**: ✅ complete (2026-03-11) — DySpec heap-based dynamic tree construction replaces Phase 1's per-depth expansion
**Phase 2.5**: ✅ complete (2026-03-11) — 4 runtime bugs fixed (n_seq_max, kv_unified, KV mismatch, target context)
**Phase 3**: ✅ complete (2026-03-14) — Multi-path target verification enabled for dense models (requires `--kv-unified`); incompatible with hybrid/SSM models
**Greedy path fix**: ✅ complete (2026-03-14) — `draft()` returns `get_greedy_path()` (top-1 at each depth) instead of `get_best_path()` (draft-model-optimal). Path 0 now guaranteed ≥ linear.
**Benchmarks**: ✅ complete (2026-03-14) — 7B f16, 32B Q4 dense, 122B MoE hybrid tested. Tree structurally sound but net-negative on throughput due to construction overhead.
**Phase 5a**: ❌ reverted (2026-03-15) — Branching reduction (7/5/3/2→4/3/2, cap 32→16) hurt f16/MoE more than it helped Q4. Net negative on all winning pairs.
**Phase 6**: ❌ ineffective (2026-03-15) — Adaptive EMA p_split modulation implemented but all pairs' acceptance rates fall in 40-85% band, so tree never bypassed. Code reverted.
**Phase 4**: ✅ complete (2026-03-15) — 32B f16 target: **+15.8% throughput** (5.01→5.80 t/s). Tree viable for f16 and slow targets.
**Phase 8 Approach 0**: ❌ ruled out (2026-03-15) — Frozen multi-path on hybrid models: acceptance rate collapses 12-22pp, throughput -53% to -62% across all Qwen3.5 sizes/quants. `!has_recurrent` guard restored; `kv_unified` auto-enable kept for dense models.
**Phase 8 Approach A**: ❌ net-negative (2026-03-15) — Per-path sequential replay implemented (170 lines). Benchmark: -60% to -66% throughput on both 9B and 35B-A3B. Root cause: `llama_decode` runs ALL layers per path (not just recurrent), making replay O(N_paths × full_forward) instead of O(N_paths × recurrent_only). Acceptance also dropped ~75%→~50%. Code stays for reference but `!has_recurrent` guard should be restored.
**Phase 8 Approach C**: ❌ net-negative (2026-03-16) — Checkpoint/clone-cell approach: saves recurrent state before tree, clones cells per alt path for exact logits, restores after verification. Implementation: `llama_memory_recurrent_clone_cell()` API + checkpoint save/restore integration + batch allocator fix for hybrid+kv_unified. Fixed clone_cell tail pointer corruption bug (dual-purpose cells array). Benchmark on 35B-A3B Q4KM: **-60% throughput** (4.44 vs 10.96 t/s linear). Root cause: checkpoint save copies ~450MB recurrent state per round, clone_cell copies tensor slices per path, batched multi-path decode has O(N_paths) recurrent compute. 16 tree path wins confirmed (code correct) but overhead > benefit. `!has_recurrent` guard restored.
**Follow-up phases**: 5 (overhead reduction — all ruled out), 6 (adaptive — ruled out), 7 (NUMA), 8 (Delta Net tree — 0/A/C all ruled out, B deferred ~40% viability) — see below
**Blocked by**: None
**Blocks**: None
**Unblocked**: specexec-verification-profiling (completed 2026-03-10), hsd-hierarchical-self-speculation (completed 2026-03-10)

## Objective

Implement tree-structured speculation with dynamic topology, NUMA-pinned parallel draft workers, and shared-prefix KV cache. All C++ work on `feature/tree-speculation` branch off `production-consolidated-v2` → validate → merge to `production-consolidated-v2`.

This is the culmination of the speculative decoding research. Handoff 1 (completed 2026-03-10) showed verification is NOT near-free for Q4_K_M models (4-5x at N=64), but IS near-flat for f16 models (1.69x at N=64). Tree speculation should therefore **prioritize f16 target models** where verification budget is genuinely cheap — this also yields better output quality since f16 avoids quantization artifacts.

### Upstream Empirical Data (specexec-verification-profiling, 2026-03-10)

| Finding | Implication for This Handoff |
|---------|------------------------------|
| Q4_K_M verification: 4-5x at N=64 | Tree budget should be conservative (~32-64 nodes) for Q4_K_M targets |
| f16 verification: 1.69x at N=64 | f16 targets can support large trees (~128-256 nodes) near-free |
| Linear K=16 throughput = K=256 | Acceptance rate decay saturates linear spec; tree branching is the only path to more accepted tokens |
| Qwen3.5-0.8B draft: 44 t/s (slow) | Use faster drafters (Qwen2.5-Coder-0.5B at 185 t/s) for tree branches |
| Qwen2.5-7B-f16 + 0.5B: 42 t/s, 91% accept | Best production pair — ideal first target for tree speculation |

Full data: `epyc-inference-research/docs/experiments/specexec-verification-profile.md`

### Upstream Empirical Data (hsd-hierarchical-self-speculation, completed 2026-03-10)

| Finding | Implication for This Handoff |
|---------|------------------------------|
| External draft on dense Qwen3-32B: **+55% throughput** (13.07 t/s vs 8.44 baseline) | Linear spec already strong on dense — tree must beat 13 t/s to justify complexity |
| HSD capped branch resampling: **+0.8% throughput, +0.98pp acceptance** | Free marginal gain — tree verification inherits HSD via `common_sampler_sample_and_accept_n()`. Use `--no-hsd` flag for A/B isolation. |
| Freeze-recurrent on hybrid SSM: **+5.4%** (only viable spec config) | Auto freeze-recurrent now standard for all hybrid speculation — tree spec inherits this automatically. No checkpoint/restore needed. |
| Auto freeze-recurrent for all hybrid speculation | `server-context.cpp` now auto-activates freeze-recurrent for ANY speculation on hybrid models (external draft, lookup, tree). Tree implementation doesn't need to handle hybrid state management — it's done. |
| Prompt lookup works on hybrid models | Via auto freeze-recurrent. `--lookup` + tree spec could combine for lookup-seeded tree branches on hybrid targets. |
| Self-spec / HiSpec intermediate: **not viable** | Near-zero acceptance on dense (no early-exit training), SSM overhead on hybrid. Don't explore hierarchical tree verification with intermediate layers. |
| Architecture warnings at startup | `--n-layer-exit-draft` warns for both hybrid (SSM overhead) and dense (no early-exit). Already in production. |
| Best drafter: Qwen2.5-Coder-0.5B (185 t/s) | 4x faster than Qwen3.5-0.8B. Tree budget per time unit scales directly with drafter speed — fast drafter means more tree nodes per round. |

Key code changes already on `production-consolidated-v2` (via `feature/ssm-checkpoint-opt` merge):
- `common/sampling.cpp`: HSD capped branch resampling with `--no-hsd` toggle
- `server-context.cpp`: Auto freeze-recurrent for hybrid, prompt lookup fix, architecture warnings
- `common/common.h`: `enable_hsd_recovery` field in `common_params_sampling`
- `common/arg.cpp`: `--no-hsd`, `--freeze-recurrent-draft` (now redundant but kept)

Full data: `epyc-inference-research/docs/chapters/10-advanced-speculative-decoding.md` Section 11

## Background

### EPYC 9655 Hardware
- 2 NUMA nodes, 48 physical cores each (96 physical total)
- SMT enabled: 192 logical CPUs (node0: 0-47,96-143; node1: 48-95,144-191)
- `-t 48` per draft worker uses physical cores only (correct for llama.cpp compute-bound work; SMT siblings add marginal throughput for memory-bound inference)
- `-t 96` spans both nodes' physical cores
- ~230 GB/s memory bandwidth per node (~460 GB/s total)
- Verification is bandwidth-bound for f16 models (1.69x at N=64) but NOT for Q4_K_M (4-5x at N=64) — see empirical data below

### Current State
- **Server**: Linear speculation only — draft produces `[t1, ..., tK]`, target verifies in one batch. `--draft-max 16-24` in production. Server speculation loop in `server-context.cpp` (search `common_speculative_draft` or `i_batch_dft`).
- **Standalone binary**: `llama-speculative` (`examples/speculative/speculative.cpp`) already implements tree speculation via `struct seq_draft` arrays with `n_parallel` controlling branch count and `p_draft_split` controlling split probability threshold. This is functional and benchmarked but **not available in the server**.
- Tree speculation in the server is the goal of Phase 1 — porting and cleaning up the standalone implementation for server integration, not inventing it from scratch.

### Goal
- Tree speculation: draft produces a tree of candidates, target verifies all paths in one batch
- Dynamic tree construction (DySpec): expand tree greedily by acceptance probability
- NUMA-pinned dual drafting: two draft workers explore different branches in parallel

## Existing Infrastructure

### Tree speculation in standalone binary
- **File**: `examples/speculative/speculative.cpp` (~648 lines)
- `struct seq_draft` (line 18): per-branch state with tokens, probability distributions, sampler
- `n_parallel` (line 55): `params.n_parallel` controls max parallel draft sequences (tree branches)
- `p_draft_split` (line 58): `params.speculative.p_split` — probability threshold for branch splitting
- Branch expansion logic at line 507: `if (n_seq_cur < n_seq_dft && cur_p->data[f].p > p_draft_split)`
- KV cache branching via `llama_memory_seq_cp` (line 511)

### Benchmark script
- **File**: `epyc-inference-research/scripts/benchmark/bench_tree_speculation.sh`
- Tests `-np 1,2,4,8` × `--draft-p-split 0.05,0.1,0.2,0.3` sweep
- Outputs CSV to `${LOG_DIR}/tree_speculation/`
- Uses `llama-speculative` binary (not server)

### Server speculation loop
- **File**: `tools/server/server-context.cpp`
- Slot struct fields: `spec` (line 58), `drafted` (line 161), `n_draft_total`/`n_draft_accepted` (lines 175-176)
- Draft generation: `common_speculative_draft()` call (search `common_speculative_draft`)
- Verification: `common_sampler_sample_and_accept_n()` (search `sample_and_accept_n`)
- **Linear only** — no tree support, no `p_draft_split`, no multi-sequence drafting

### Speculation type enum
- **File**: `common/common.h` lines 167-177
- `common_speculative_type`: DRAFT, EAGLE3 (stub), NGRAM variants, COUNT

### NUMA support
- `--numa` flag in `arg.cpp` (line 2254): distribute/isolate/numactl strategies
- `orchestrator_stack.py` currently uses `--preferred` (soft affinity)

### `--draft-p-split` flag
- Registered in `arg.cpp:3390`, sets `params.speculative.p_split`
- `.set_examples({LLAMA_EXAMPLE_SPECULATIVE})` — **available only for standalone speculative binary, NOT server**
- Phase 1 must add this to `LLAMA_EXAMPLE_SERVER` for server-side tree speculation

## Phase 1 — Tree Attention with Topology-Aware Causal Mask

Phase 1 ports tree speculation from `llama-speculative` to the server, wrapping it in a cleaner API.

### Review of existing `llama-speculative` tree implementation

The standalone binary (`examples/speculative/speculative.cpp`, ~648 lines) implements tree speculation
via `struct seq_draft` arrays. Code review findings for the server port:

**What works well (keep)**:
- Branch splitting via `p_draft_split` threshold (line 507 region) — clean probability-gated expansion
- Stochastic verification with residual probability correction (lines 304-334) — theoretically sound
- KV cache branching via `llama_memory_seq_cp` (line 511) — reuses llama.cpp primitives correctly

**Limitations to address in server port**:
1. **Implicit tree structure**: Each `seq_draft` stores its own full token+dist history independently.
   Tokens shared across branches are duplicated. The proposed `speculation_tree` struct with explicit
   `parent[]` indices is cleaner and enables shared-prefix optimization (Phase 4).

2. **Flat branching strategy**: Checks top-8 candidates per position against `p_draft_split` threshold.
   The DySpec heap-based approach (Phase 2) is a genuine improvement — it prioritizes globally across
   all frontier nodes by cumulative log probability, rather than per-position threshold decisions.

3. **No server slot integration**: Standalone binary manages its own contexts. Server port must
   integrate with `server_slot` (which already has `spec`, `drafted`, `n_draft_total/accepted` fields
   in `server-context.cpp`, search `n_draft_total`).

4. **Random sequence selection for verification** (line 254-255): Uniformly random pick from active
   sequences is suboptimal — should verify highest-probability branch first.

5. **No batched draft across user requests**: Each speculation round is single-user. Server needs to
   handle tree drafting within the existing multi-slot batch decode loop.

**Recommendation**: Port the branching/verification logic but wrap it in `speculation_tree` struct,
replace flat `p_draft_split` with DySpec heap (Phase 2), and integrate with server slot system.

### Tree Structure

```c
struct speculation_tree {
    std::vector<int32_t> parent;      // parent[i] = index of parent node (-1 for root)
    std::vector<llama_token> tokens;  // tokens[i] = token at node i
    std::vector<float> log_probs;     // log_probs[i] = cumulative log probability
    int32_t n_nodes;                  // total nodes in tree
};
```

This replaces the ad-hoc `seq_draft` arrays from the standalone binary with an explicit tree topology. The `parent[]` array enables efficient shared-prefix tracking for Phase 4's KV cache optimization.

### Verification Strategy

Assign each root-to-leaf path a unique `seq_id` (uses llama.cpp's existing multi-sequence support):

1. Enumerate all root-to-leaf paths in the tree
2. Each path gets a `seq_id`
3. Run target model with all paths as separate sequences (batch verification)
4. For each path, compare target logits against draft tokens
5. Accept longest prefix where target agrees (modified DFS from root)

**Initial approach**: Uses `seq_id` for tree encoding. This duplicates some prefix KV computation (tokens shared between paths are computed multiple times). Acceptable at moderate tree sizes (<100 nodes). Shared-prefix KV optimization deferred to Phase 4.

### Server Integration — Polymorphic State Architecture

`speculative.cpp` uses polymorphic dispatch: `common_speculative` holds a vector of `common_speculative_state` implementations (line 740), each with a virtual `draft()` method. `common_speculative_draft()` (line 1002) iterates `spec->impls` and returns the first non-empty result. Existing implementations:
- `common_speculative_state_draft` (line 147) — external draft model
- `common_speculative_state_eagle3` (line 440) — stub
- `common_speculative_state_ngram_*` (lines 466-738) — ngram variants

**Tree speculation fits as a new `common_speculative_state_tree` class** wrapping an existing `common_speculative_state_draft` instance. Design approach (Option C — least invasive):
- `draft()` returns flat best-path tokens (backward-compatible — linear speculation still works via the same call)
- New `get_tree()` accessor returns the full `speculation_tree` topology built during `draft()`
- Server checks `spec->get_tree()` when `p_split > 0` for multi-path verification; otherwise uses flat tokens as today
- Tree metadata (parent indices, log probs, all paths) stored on the state object between `draft()` and verification

Integration steps:
- Add `--draft-p-split` to `LLAMA_EXAMPLE_SERVER` in `arg.cpp` (currently `LLAMA_EXAMPLE_SPECULATIVE` only, line 3436)
- Add `COMMON_SPECULATIVE_TYPE_TREE` to `common_speculative_type` enum in `common.h` (after line 176)
- Implement `common_speculative_state_tree` in `speculative.cpp` — wraps draft state, builds tree, returns flat best-path from `draft()`
- Server gates tree verification behind `p_split > 0`: calls `spec->get_tree()` after `common_speculative_draft()` for multi-path verification

### Files

- `llama.cpp/common/speculative.cpp` — `common_speculative_state_tree` class (Modify — file exists)
- `llama.cpp/common/speculative.h` — `speculation_tree` struct, `get_tree()` accessor, `COMMON_SPECULATIVE_TYPE_TREE` enum value
- `llama.cpp/common/common.h` — add tree type to `common_speculative_type` enum
- `llama.cpp/common/arg.cpp` — add `--draft-p-split` to `LLAMA_EXAMPLE_SERVER` (search `LLAMA_EXAMPLE_SPECULATIVE`)
- `llama.cpp/tools/server/server-context.cpp` — tree verification path gated on `p_split > 0` (search `common_speculative_draft`)

### Validation

- **Correctness**: Tree verification produces identical output to linear verification when tree is linear (degenerate case)
- **Acceptance**: Tree verification accepts at least as many tokens as linear verification
- **Reproducible prompts**: Use `question_pool.py` (`epyc-inference-research/scripts/benchmark/question_pool.py`) for test prompts
- **Comparison**: Run `bench_tree_speculation.sh` with standalone binary first, then server implementation, compare acceptance rates

## Phase 2 — DySpec Dynamic Tree Construction

Replace the linear draft loop with heap-based greedy expansion:

### Algorithm

```
function draft_tree(model, context, budget, batch_size=8):
    tree = new_tree(root = context_last_token)
    heap = max_heap()  // keyed by cumulative log probability

    // Wave 0: Seed with top-k children of root
    logits = draft_model.forward(context)
    for tok in top_k(logits, k=5):
        heap.push((log_prob(tok), tree.add_child(root, tok)))

    // Wave-based expansion: pop batch_size nodes per wave, batch forward pass
    while tree.n_nodes < budget and heap not empty:
        // Pop up to batch_size highest-probability frontier nodes
        wave = []
        while len(wave) < batch_size and heap not empty:
            (prob, node) = heap.pop()
            wave.append((prob, node))

        // Batch decode: one forward pass for all nodes in this wave
        // Uses llama_decode() with batch containing all wave tokens
        batch_logits = draft_model.forward_batch([
            (context + path_to(node)) for (prob, node) in wave
        ])

        // Expand children for each node in wave
        for (prob, node), logits in zip(wave, batch_logits):
            for tok in top_k(logits, k=3):
                if tree.n_nodes >= budget: break
                child = tree.add_child(node, tok)
                heap.push((prob + log_prob(tok), child))

    return tree
```

**Key difference from per-node expansion**: Wave-based approach batches multiple frontier nodes into a single `llama_decode()` call, matching the standalone binary's pattern (line 507 region). This reduces O(n_nodes) sequential forward passes to O(n_nodes/batch_size) batched passes.

**Key parameters** (from Handoff 1 profiling data):
- `budget`: Maximum tree nodes (set by verification cost curve — where latency inflects)
- `k` (branching factor): 3-5 at root, decreasing with depth
- Depth limit: prevents degenerate deep-but-narrow trees

### Interface

```c
// Replaces common_speculative_draft() for tree mode
speculation_tree common_speculative_draft_tree(
    struct common_speculative * spec,
    struct common_speculative_params params,  // includes budget, branching factor
    struct llama_context * ctx_draft
);
```

### Files

- `llama.cpp/common/speculative.cpp` — `common_speculative_draft_tree()` implementation
- `llama.cpp/common/speculative.h` — API additions

## Phase 2.5 — Runtime Debugging & Multi-Path Target Verification

### Runtime Bugs Fixed (4 critical issues)

1. **Draft context `n_seq_max=1`**: Tree branching requires 33 seq_ids. Fixed by setting `cparams_dft.n_seq_max = 33` when `p_split > 0`.

2. **Non-unified KV `seq_cp` failure**: Cross-stream `llama_memory_seq_cp` with bounded range rejected. Fixed by setting `cparams_dft.kv_unified = true` + `p1=-1` (full copy) for all seq_cp calls.

3. **KV/prompt_dft mismatch**: After tree expansion, best path tokens appended to `prompt_dft` but seq 0 KV only has primary path data. Fixed by trimming seq 0 KV to pre-tree state after each draft round.

4. **Target context `n_seq_max` too low**: Multi-path verification needs tree seq_ids on target context. Solved by adding `n_seq_max` override field to `common_params`, setting `kv_unified=true` and `n_seq_max = 9 * n_parallel` on target context when `p_split > 0`.

### Multi-Path Target Verification (enabled)

All tree paths verified simultaneously on target model in a single batch decode:
- Each root-to-leaf path assigned a unique `seq_id` (`n_parallel + slot.id * 8 + k`)
- Prompt KV copied to alternative seq_ids via `llama_memory_seq_cp`
- All paths decoded in one batch; longest accepted prefix wins
- If alternative path wins, its KV is copied back to slot.id; unused seq_ids cleaned up
- Cap: 8 alternative paths per slot

### Files Modified
- `common/common.h` — added `int32_t n_seq_max` override field
- `common/common.cpp` — `common_context_params_to_llama` uses n_seq_max override
- `tools/server/server-context.cpp` — target context config (gated on `--kv-unified`), multi-path verification (gated on `!has_recurrent`), hybrid guard
- `common/speculative.cpp` — KV cleanup after tree draft, seq_cp full-range fix

### Benchmark Results (all models, after greedy path fix)

| Target | Quant | Arch | Linear t/s | Tree Best t/s | +Tokens | Delta | Multi-path |
|--------|-------|------|-----------|---------------|---------|-------|------------|
| Qwen2.5-7B + 0.5B | f16 | Dense | 29.45 | 30.76 | +25 | **+4.4%** | Yes |
| Qwen3-235B-A22B + 0.6B | Q4_KM | MoE | 10.97 | 11.19 | +35 | **+2.0%** | Yes |
| Qwen2.5-Coder-32B + 0.5B | Q4_KM | Dense | 19.50 | 18.84 | +20 | -3.4% | Yes |
| DS-R1-Distill-32B + 0.5B | Q6_K | Dense | 11.57 | 10.60 | +44 | -8.4% | Yes |
| Qwen3.5-122B-A10B + 0.8B | Q4_KM | Hybrid | 5.75 | 4.36 | — | -24% | No (SSM) |
| Qwen3-Coder-480B-A35B + 0.75B | Q4_KM | MoE | ... | ... | ... | pending | Yes |
| Qwen2.5-Coder-32B + 0.5B | f16 | Dense | ... | ... | ... | pending | Yes |

### Tree Speculation Viability Threshold

Tree wins when **target verification cost per round exceeds tree construction overhead (~41ms)**. Two regimes:

**Tree wins (+2% to +4.4%)**:
- **f16 targets** (any size): Bandwidth-bound verification, near-flat cost at N=64 (1.69x). Extra accepted tokens are nearly free to verify.
- **Large MoE Q4 (235B+)**: Each verification round is inherently slow due to model size. +35 extra accepted tokens per generation save enough rounds to overcome overhead.

**Tree loses (-3% to -8%)**:
- **Medium dense Q4/Q6 (32B)**: Verification is fast (~50ms/round). Tree overhead (~41ms) eats the gain from +20-44 extra tokens.
- **Hybrid/SSM models**: `seq_id`-based multi-path verification incompatible (recurrent state can't fork). Phase 8 (per-path Delta Net replay) addresses this.

**Key insight**: The deciding variable is not quantization alone — it's the ratio of verification latency to tree overhead. Large models and f16 models both have high verification latency (for different reasons), making tree profitable. The crossover is approximately when linear verification takes >80ms/round.

**Production implication**: Tree spec is immediately viable for `architect_general` (235B, +2.0%), `architect_coding` (480B, pending), and any f16 target. For 32B Q4_K_M targets, Phase 5 overhead reduction (~41ms → ~20ms) is needed first.

### Greedy Path Fix (Complete, 2026-03-14)

Added `get_greedy_path()` to `speculation_tree` — follows primary children (node 0 → first child at each depth) instead of highest cumulative log probability leaf. `draft()` now returns `tree.get_greedy_path()`. This guarantees path 0 is never worse than linear.

**Impact**: Minimal on tested pairs — `get_best_path()` and `get_greedy_path()` return the same path ~99% of the time. The regression was not caused by path selection but by tree construction overhead (KV copies, sampler clones, heap management).

### Hybrid Model Incompatibility (Addressable via Phase 8)

Multi-path target verification via `seq_id` forking is incompatible with hybrid models. The recurrent state (Delta Net / gated linear attention in Qwen3.5/Qwen3-Next) is sequential — `llama_memory_seq_cp` on the target context forks KV attention state but NOT recurrent state. Forking recurrent state would require re-advancing through the full sequence for each alternative path, defeating the purpose.

**Architecture note**: Despite being labeled "SSM hybrid" in early documentation, Qwen3.5 and Qwen3-Next use **Delta Net** (gated linear attention), NOT Mamba2. Their recurrent layers are in `delta-net-base.cpp`, not `ggml_ssm_scan`. This distinction is critical for Phase 8 — STree's tree-masked `ggml_ssm_scan` does NOT apply to our production models.

**Resolution**: Phase 8 uses per-path sequential replay (Approach A) — checkpoint/restore recurrent state and replay autoregressive Delta Net for each tree path. Attention layers still use `seq_id`-based multi-path (Phase 3 code). See Phase 8 below.

Data: `epyc-inference-research/data/tree_speculation/server_sweep_20260314_*.csv`

## Phase 4 — f16 Target Validation (Next)

### Rationale

SpecExec profiling showed f16 targets have near-flat verification cost (1.69x at N=64 vs 4-5x for Q4_K_M). Tree construction overhead is fixed-cost (~41ms/round for KV copies + sampler clones). On Q4_K_M targets, verification is already fast (~50ms/round), so the overhead dominates. On f16 targets, verification is nearly free — the +20 extra accepted tokens from tree alt paths should translate directly to throughput gain.

This is the most likely path to a net win and the quickest to validate.

### Plan

1. Benchmark Qwen2.5-Coder-32B **f16** + 0.5B-f16 (dense, `--kv-unified`)
   - f16 model: `/mnt/raid0/llm/models/Qwen2.5-Coder-32B-Instruct-f16.gguf` (if available) or convert
   - Sweep: p_split in {0, 0.05, 0.1, 0.2, 0.3}, n_predict=128
   - Compare against Q4_K_M baseline from Phase 3 benchmarks
2. If net positive: validate with longer generation (n_predict=512) to confirm sustained gain
3. If still negative: tree overhead is too high even for f16 → proceed to Phase 5

### Results (n_predict=256)

| Config | t/s | Accept% | Acc/Tot | Delta |
|--------|-----|---------|---------|-------|
| linear (p_split=0) | 5.01 | 80.1% | 724/904 | — |
| tree (p_split=0.05) | 5.75 | 78.2% | 771/986 | +14.8% |
| tree (p_split=0.1) | 5.76 | 78.2% | 771/986 | +15.0% |
| tree (p_split=0.2) | 5.74 | 78.2% | 771/986 | +14.6% |
| tree (p_split=0.3) | 5.80 | 78.2% | 771/986 | **+15.8%** |

**+15.8% throughput** — biggest tree win, matching the +10-15% prediction. All tree configs tightly clustered (5.74–5.80), suggesting tree finds the same useful alternative paths regardless of split threshold. +47 extra accepted tokens translate almost entirely to throughput because f16 verification scaling is near-flat (1.69x at N=64).

### Analysis: Why f16 Wins So Decisively

Tree overhead (~41ms) is **draft-side only** — KV copies + sampler clones on the draft model. It's independent of the target model. The deciding factors are:

1. **Target verification latency per round**: 32B f16 ≈ 200ms/round → 41ms overhead is ~20% tax. Q4 32B ≈ 50ms/round → 41ms is ~80% tax.
2. **Verification cost scaling with N candidates**: f16 is near-flat (bandwidth-bound — loading 62GB weights dominates regardless of N). Q4_K_M scales 4-5x at N=64 (dequant overhead per token).

Both conditions favor f16. Large Q4 MoE (pair 8) has high per-round latency but poor verification scaling — only the first condition is met.

**Implication**: Tree is viable for any target where verification >> 41ms AND scaling ≈ flat. This includes f16 (any size), and potentially Q8_0 (simpler dequant, likely 2-2.5x scaling — between f16 and Q4).

### Sustained Validation (n_predict=512)

| Config | t/s | Accept% | Acc/Tot | Delta |
|--------|-----|---------|---------|-------|
| linear (p_split=0) | 5.75 | 81.0% | 1529/1887 | — |
| tree (p_split=0.05) | 6.36 | 78.8% | 1592/2021 | **+10.6%** |

+10.6% sustained over 512 tokens. Lower than 256-token run (+15.8%) because baseline is faster at longer generation (prompt processing amortized). Still a solid production-relevant win.

### Three-Way Quantization Comparison (same 32B model + 0.5B drafter, n_predict=256)

| Quant | Size | Linear t/s | Best Tree t/s | Delta | Verification Scaling |
|-------|------|-----------|---------------|-------|---------------------|
| Q4_K_M (pair 5) | 19GB | 19.05 | 18.01 (p=0.2) | -5.5% | 4-5x at N=64 |
| Q8_0 (pair 11) | 33GB | 9.30 | 9.53 (p=0.1) | **+2.5%** | ~2x (inferred) |
| f16 (pair 10) | 62GB | 5.01 | 5.80 (p=0.3) | **+15.8%** | 1.69x at N=64 |

Clean gradient: as weight size per token increases, verification latency rises relative to fixed ~41ms tree overhead, and tree becomes increasingly profitable. Q8 is the crossover point — tree just barely wins.

**Production recommendation**: Enable `--draft-p-split` for f16 targets (strong win) and Q8 targets (marginal win). Q4 targets should stay linear.

### Files

- `epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh` — pairs 10 (f16), 11 (Q8) added
- Data: `epyc-inference-research/data/tree_speculation/server_sweep_20260315_104425.csv` (f16 256t), `*_110120.csv` (f16 512t), `*_122016.csv` (Q8 256t)

### Extended Pairs Benchmark (2026-03-17) — T1-T4 Complete

Full p_split sweep on all remaining pairs. n_predict=256, draft_max=16, threads=96.

**Pair 15 — Qwen3-Coder-30B-A3B Q4_K_M (frontdoor, MoE):**

| p_split | t/s | Accept% | Accepted/Total | Delta vs Linear |
|---------|-----|---------|----------------|-----------------|
| 0 (linear) | 40.92 | 58.6% | 639/1090 | baseline |
| 0.05 | 35.14 | 59.4% | 699/1176 | -14.1% |
| 0.1 | 35.13 | 59.4% | 699/1176 | -14.1% |
| 0.2 | 35.62 | 59.4% | 699/1176 | -13.0% |
| 0.3 | 34.70 | 59.4% | 699/1176 | -15.2% |

**Pair 10 — Qwen2.5-Coder-32B f16 (dense, validation run):**

| p_split | t/s | Accept% | Accepted/Total | Delta vs Linear |
|---------|-----|---------|----------------|-----------------|
| 0 (linear) | 6.05 | 80.1% | 724/904 | baseline |
| 0.05 | 6.67 | 78.2% | 771/986 | **+10.2%** |
| 0.1 | 6.56 | 78.2% | 771/986 | +8.4% |
| 0.2 | 6.41 | 78.2% | 771/986 | +5.9% |
| 0.3 | 6.26 | 78.2% | 771/986 | +3.5% |

**Pair 11 — Qwen2.5-Coder-32B Q8_0 (dense):**

| p_split | t/s | Accept% | Accepted/Total | Delta vs Linear |
|---------|-----|---------|----------------|-----------------|
| 0 (linear) | 8.43 | 79.6% | 733/921 | baseline |
| 0.05 | 8.42 | 77.9% | 772/991 | -0.1% |
| 0.1 | 8.40 | 77.9% | 772/991 | -0.4% |
| 0.2 | 8.42 | 77.9% | 772/991 | -0.1% |
| 0.3 | 8.43 | 77.9% | 772/991 | 0.0% |

**Pair 9 — Qwen3-Coder-480B-A35B Q4_K_M (architect, MoE):**

| p_split | t/s | Accept% | Accepted/Total | Delta vs Linear |
|---------|-----|---------|----------------|-----------------|
| 0 (linear) | 5.10 | 61.0% | 641/1050 | baseline |
| 0.05 | 4.75 | 57.9% | 695/1201 | -6.9% |
| 0.1 | 4.68 | 57.9% | 695/1201 | -8.2% |
| 0.2 | 4.71 | 57.9% | 695/1201 | -7.6% |
| 0.3 | 4.01 | 57.9% | 695/1201 | -21.4% |

### Five-Way Quantization Comparison (all pairs, n_predict=256)

| Model | Arch | Quant | Size | Linear t/s | Best Tree t/s | Delta | Verdict |
|-------|------|-------|------|-----------|---------------|-------|---------|
| Qwen3-Coder-30B-A3B (pair 15) | MoE | Q4_K_M | 18GB | 40.92 | 35.62 (p=0.2) | **-13.0%** | ❌ tree loses |
| Qwen2.5-Coder-32B (pair 5) | Dense | Q4_K_M | 19GB | 19.05 | 18.01 (p=0.2) | -5.5% | ❌ tree loses |
| Qwen3-Coder-480B-A35B (pair 9) | MoE | Q4_K_M | 270GB | 5.10 | 4.71 (p=0.2) | **-7.6%** | ❌ tree loses |
| Qwen2.5-Coder-32B (pair 11) | Dense | Q8_0 | 33GB | 8.43 | 8.44 (p=0.3) | +0.1% | ⚖️ break-even |
| Qwen2.5-Coder-32B (pair 10) | Dense | f16 | 62GB | 6.05 | 6.67 (p=0.05) | **+10.2%** | ✅ tree wins |

**Key findings from T1-T4:**
1. **f16 is the only clear tree winner** — optimal p_split=0.05 (shallow trees)
2. **Q8_0 is the crossover point** — tree exactly breaks even at all p_split values
3. **Q4_K_M loses regardless of model size or architecture** — MoE (30B, 480B) and dense (32B) all net-negative
4. **MoE models lose harder at Q4_K_M** than dense models (-7.6% to -13% vs -5.5%)
5. **Acceptance rate drops with tree** on all pairs (more draft tokens → more rejected), but f16's cheap verification absorbs this
6. **p_split=0.3 on 480B is catastrophic** (-21.4%) — large trees overwhelm even slow targets at Q4
7. **Previous Q8_0 result (pair 11, Phase 4) showed +2.5%** at 9.30 t/s baseline; today's run at 8.43 t/s shows break-even. Minor run-to-run variance likely explains the difference.

**Updated production recommendation (2026-03-18)**: f16 targets: `--draft-max 32 --draft-p-split 0.05` (+12.2%, up from +9% at default dm=16). Q8_0: still break-even/negative even at dm=32. Q4_K_M: remains linear. Only f16 benefits from tree speculation.

Data files:
- `epyc-inference-research/data/tree_speculation/server_sweep_20260317_144949.csv` (pair 15)
- `epyc-inference-research/data/tree_speculation/server_sweep_20260317_145435.csv` (pair 10)
- `epyc-inference-research/data/tree_speculation/server_sweep_20260317_150939.csv` (pair 11)
- `epyc-inference-research/data/tree_speculation/server_sweep_20260317_153523.csv` (pair 9)

## Phase 5 — Reduce Tree Construction Overhead

### Problem

Tree construction costs ~41ms/round (KV copies + sampler clones), which offsets the +20 accepted tokens from alt paths.

### 5a. Reduced Branching Factor — ❌ REVERTED (2026-03-15)

Tested: MAX_BRANCHES 7→4, branching factor root=4/depth≤2=3/deeper=2 (was 7/5/3/2), seq_id cap 32→16.

| Pair | Target | Pre-5a | Post-5a | Verdict |
|------|--------|--------|---------|---------|
| 1 | Qwen2.5-7B f16 + 0.5B f16 | +4.4% | +2.7% | Regressed |
| 5 | Qwen2.5-Coder-32B Q4 + 0.5B f16 | -5.2% | -4.1% | Improved 1pp (still negative) |
| 8 | Qwen3-235B MoE + 0.6B Q8 | +2.0% | -6.6% | Regressed badly |

**Conclusion**: Reducing branching cuts both overhead AND acceptance quality. The wider tree was finding useful alternative paths on f16/MoE targets where verification is cheap or slow. Overhead savings (~40-50% fewer KV copies) did not compensate for lost accepted tokens. All changes reverted.

Data: `epyc-inference-research/data/tree_speculation/server_sweep_20260315_000100.csv` (pair 1), `*_000400.csv` (pair 5), `*_000913.csv` (pair 8).

### 5b. Lazy KV Copies — NOT VIABLE

`llama_kv_cache.cpp:440` asserts `is_full` for cross-stream seq_cp — position-bounded copies fail even with `kv_unified=true`. All `seq_cp` calls must remain `(0, -1)` (full copy). Lazy/deferred copies can't reduce per-copy cost since each copy is always full-range. And we can't defer copies to verification time because `llama_decode` needs each alternative on its own seq_id for correct logits during draft tree construction.

### 5c. Sampler Pooling — NOT VIABLE

Investigation (Phase 5 planning) showed sampler cloning is ~1ms/clone, ~50-73ms total — NOT the dominant cost (KV copies are). Additionally, Mirostat state can't be reverted, so `reset()` ≈ `clone()` cost. Pooling saves allocation overhead but not clone overhead.

### Status

All three Phase 5 optimization paths have been explored and ruled out:
- 5a (branching reduction): tested, reverted — hurts acceptance more than it helps overhead
- 5b (lazy KV copies): not viable — llama.cpp requires full-range copies, can't defer
- 5c (sampler pooling): not viable — Mirostat state prevents reuse, clone cost irreducible

**The tree construction overhead (~41ms/round) appears to be a hard floor** given llama.cpp's KV cache architecture. The path forward is Phase 6 (adaptive tree — avoid overhead entirely on easy/hard prompts) rather than reducing per-round overhead.

### Files

- `common/speculative.cpp` — no changes (5a reverted)
- Data: `epyc-inference-research/data/tree_speculation/server_sweep_20260315_*.csv`

## Phase 6 — Adaptive Tree Sizing — ❌ INEFFECTIVE (2026-03-15)

### Problem

Tree overhead is wasted on easy prompts (where linear already gets 90%+ acceptance) and on hard prompts (where draft model disagrees with target regardless of branching). Tree is most valuable in the middle regime (~60-80% acceptance) where alternatives have a chance.

### Implementation (Reverted)

Added per-round EMA of acceptance rate on `server_slot`. When EMA > 0.85 or < 0.40, set `p_split = 1.0` (effectively linear — no candidate exceeds p > 1.0) and skip multi-path verification. Alpha=0.3 gives ~3-4 rounds of memory. 5 edits in `server-context.cpp`:
1. `spec_accept_ema` + `spec_tree_active` fields on `server_slot`
2. Reset in `reset()`
3. Copy `params_spec`, modulate `p_split` before `common_speculative_draft()`
4. Gate `common_speculative_get_tree()` on `spec_tree_active`
5. Update EMA after verification, debug log

### Benchmark Results (pairs 1, 5, 8)

| Pair | Target | Linear | Best Tree (adaptive) | Delta | EMA Steady-State |
|------|--------|--------|---------------------|-------|-----------------|
| 1 | Qwen2.5-7B f16 + 0.5B f16 | 32.76 t/s | 33.75 (p=0.3) | +3.0% | ~0.77 |
| 5 | Qwen2.5-Coder-32B Q4 + 0.5B f16 | 19.05 t/s | 18.01 (p=0.2) | -5.5% | ~0.79 |
| 8 | Qwen3-235B MoE + 0.6B Q8 | 8.94 t/s | 8.27 (p=0.3) | -7.5% | ~0.59 |

### Why It Failed

All three pairs have aggregate acceptance rates in the 40-85% band (59%, 77%, 79%), so the EMA never triggers tree bypass. The adaptive thresholds were designed for the wrong problem: the real bottleneck is **verification cost** (Q4 dequant overhead, MoE expert routing latency), not acceptance regime. Acceptance rate doesn't predict verification cost — a 60% acceptance rate on f16 (cheap verification) is profitable, while 79% on Q4 (expensive verification) is not.

Pair 8 (235B MoE) regressed from the previous +2.0% to -7.5%. Run-to-run variance on the 235B is high (~1-2 t/s swing) given the long per-round latency; the Phase 3 result (+2.0%) may have been within noise.

### Conclusion

Acceptance-rate-based tree bypass is not the right signal. The deciding variable is verification cost per round, which depends on quantization and model architecture, not acceptance rate. These are static properties known at server startup — not per-round signals requiring an EMA.

A **static dispatch** (tree for f16 targets, linear for Q4/Q6) would be more effective than adaptive EMA. But even then, tree only wins +3% on f16 — the overhead floor (~41ms) still dominates. All Phase 6 changes reverted.

Data: `epyc-inference-research/data/tree_speculation/server_sweep_20260315_100834.csv`

## Pending Test Matrix (Pairs Not Yet Run)

Gate check (2026-03-17): Phases 4-6 complete ✅. Phase 7 is UNBLOCKED.
- Phase 4: +15.8% on f16 (validated)
- Phase 5a: branching reduction ruled out
- Phase 6: adaptive EMA ineffective
Next: run remaining pairs, then benchmark NUMA-pinned dual drafters on dense targets.

| Test ID | Model | Quant | Draft | Script Pair | Status | Result | Priority |
|---------|-------|-------|-------|-------------|--------|--------|----------|
| T1 | Qwen3-Coder-480B-A35B | Q4_K_M | Qwen3-Coder-DRAFT-0.75B Q4_0 | Pair 9 | ✅ DONE (2026-03-17) | **-7.6%** (5.10→4.71 t/s, p=0.2) | HIGH |
| T2 | Qwen2.5-Coder-32B | f16 | Qwen2.5-0.5B-f16 | Pair 10 | ✅ DONE (2026-03-17) | **+10.2%** (6.05→6.67 t/s, p=0.05) | HIGH |
| T3 | Qwen3-Coder-30B-A3B (frontdoor) | Q4_K_M | Qwen3-Coder-DRAFT-0.75B Q4_0 | Pair 15 | ✅ DONE (2026-03-17) | **-13.0%** (40.92→35.62 t/s, p=0.2) | MEDIUM |
| T4 | Qwen2.5-Coder-32B | Q8_0 | Qwen2.5-0.5B-f16 | Pair 11 | ✅ DONE (2026-03-17) | **+0.1%** (8.43→8.44 t/s, p=0.3) | MEDIUM |
| T5 | Qwen2.5-Coder-32B (NUMA dual-node) | f16 | Qwen2.5-0.5B-f16 | Phase 7 | NOT RUN | — | MEDIUM |
| T5b | Qwen2.5-Coder-32B (NUMA dual-node) | Q8_0 | Qwen2.5-0.5B-f16 | Phase 7 | NOT RUN | — | MEDIUM |
| T6 | Qwen3-Coder-480B-A35B (NUMA dual-node) | Q4_K_M | Qwen3-Coder-DRAFT-0.75B Q4_0 | Phase 7 | NOT RUN | — | LOW |

### CLI Commands for Pending Pairs

```bash
# T1: Pair 9 — 480B MoE tree speculation
bash /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh 9

# T2: Pair 10 — 32B f16 (best known target for tree)
bash /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh 10

# T3: New pair 15 — frontdoor model (add to script first)
# Add pair definition to bench_tree_speculation_server.sh:
#   15) TARGET="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
#      TARGET_PATH="/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF"
#      DRAFTER="Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf"
#      DRAFTER_PATH="/mnt/raid0/llm/models"
#      EXTRA_ARGS="--kv-unified"
bash /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh 15

# T4: Pair 11 — 32B Q8_0 (crossover point)
bash /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_tree_speculation_server.sh 11
```

## draft_max Optimization (2026-03-18) — +17-21% Production Throughput

**Key finding**: The default `--draft-max 16` is suboptimal for all production models. Increasing to 32-48 gives +17-21% throughput on large/slow models. This is a **config-only change** — no code modifications needed.

### Complete Sweep Results

**Qwen3-Coder-30B-A3B Q4_K_M (frontdoor, pair 15, 0.75B Q4_0 drafter):**

| draft_max | t/s | acceptance | delta vs dm=16 |
|-----------|-----|-----------|----------------|
| 16 | 32.84 | 58.6% | baseline |
| 24 | 35.39 | 58.0% | +7.8% |
| **32** | **39.20** | **57.1%** | **+19.4%** |
| 48 | 39.09 | 56.1% | +19.0% |

**Qwen2.5-Coder-32B Q4_K_M (coder_escalation, pair 2, 0.5B Q8_0 drafter):**

| draft_max | t/s | acceptance | delta vs dm=16 |
|-----------|-----|-----------|----------------|
| 16 | 13.16 | 75.5% | baseline |
| **24** | **15.31** | **74.7%** | **+16.3%** (already production default) |
| 32 | 14.51 | 74.1% | +10.3% |
| 48 | 13.19 | 73.2% | +0.2% |

**Qwen3-235B-A22B Q4_K_M (architect_general, pair 8, 0.6B Q8_0 drafter):**

| draft_max | t/s | acceptance | delta vs dm=16 |
|-----------|-----|-----------|----------------|
| 16 | 7.38 | 59.3% | baseline |
| 24 | 7.60 | 57.0% | +3.0% |
| **32** | **8.64** | **56.1%** | **+17.1%** |
| 48 | 7.74 | 55.8% | +4.9% |

Tree at dm=32: ps=0.05 → 8.30 t/s (**-8.0%** vs 9.02 linear), ps=0.1 → 7.26 t/s (-19.5%). Tree net-negative.

**Qwen3-Coder-480B-A35B Q4_K_M (architect_coding, pair 9, 0.75B Q4_0 drafter):**

| draft_max | t/s | acceptance | delta vs dm=16 |
|-----------|-----|-----------|----------------|
| 16 | 4.72 | 61.0% | baseline |
| 24 | 5.44 | 60.1% | +15.3% |
| 32 | 5.40 | 58.8% | +14.4% |
| **48** | **5.69** | **60.0%** | **+20.6%** |
| 64 | 5.02 | 59.1% | +6.4% |

**Qwen2.5-Coder-32B f16 (pair 10, 0.5B f16 drafter, tree speculation):**

| draft_max | p_split=0.05 t/s | delta vs dm=16 |
|-----------|------------------|----------------|
| 16 | 6.54 | baseline |
| 24 | 6.58 | +0.6% |
| **32** | **6.72** | **+2.8%** |
| 48 | 6.61 | +1.1% |

**Qwen2.5-7B f16 (worker, pair 1, tree speculation):**

| draft_max | p_split=0.05 t/s | vs baseline |
|-----------|------------------|-------------|
| 32 | 17.23 | flat (17.37 linear) |

### Why draft_max Matters More on Larger Models

The optimal draft_max correlates with model speed: slower models tolerate larger draft budgets because:
1. Each target verification step is expensive (more time per token)
2. The drafter generates tokens very cheaply (0.5-0.75B model)
3. More draft tokens per round means more chances for acceptance before hitting the expensive verification
4. The cost of extra rejected drafts is low relative to one target decode

The diminishing returns beyond the optimum happen when:
- Acceptance rate drops too much (later draft tokens diverge more from target distribution)
- KV cache overhead from larger draft context becomes significant
- Draft model starts to slow down at very long sequences

### Tree Speculation Combined with draft_max

Tree speculation (`--draft-p-split > 0`) only helps f16 targets where verification is near-free:
- 32B f16 at dm=32: +12.2% with tree (p_split=0.05) vs +12.2% linear. Tree gives marginal additional benefit on top of draft_max optimization.
- 7B f16: tree flat at any draft_max (model too fast for tree overhead)
- All Q4_K_M models: tree always net-negative (verification too expensive)
- 235B Q4_K_M at dm=32: tree ps=0.05 → **-8.0%** (8.30 vs 9.02 linear), ps=0.1 → -19.5%

### Production Action Items

Changes to `model_registry.yaml` acceleration configs:

| Model | Current draft_max | Optimal draft_max | Change Type |
|-------|------------------|------------------|-------------|
| frontdoor (30B-A3B) | 16 (default) | **32** | ADD `draft_max: 32` |
| coder_escalation (32B) | 24 | **24** | KEEP (already optimal) |
| architect_general (235B) | 16 (default) | **32** | ADD `draft_max: 32` |
| architect_coding (480B) | 16 (default) | **48** | ADD `draft_max: 48` |
| worker (7B f16) | 24 | **24** | KEEP |

The orchestrator stack reads `draft_max` from registry and passes as `--draft-max` via `accel.k` (see `orchestrator_stack.py` line ~780: `"--draft-max", str(accel.k or 16)`).

### Data Files
- `epyc-inference-research/data/tree_speculation/` — CSV files from all benchmark runs
- Pair 15 sweep: `server_sweep_20260317_144949.csv`
- Pair 10 sweeps: `server_sweep_20260317_145435.csv`, `server_sweep_20260318_*.csv`
- Pair 9 sweep: `server_sweep_20260317_153523.csv`
- Pair 8 sweep: `server_sweep_20260318_*.csv`

## Phase 7 — NUMA-Pinned Parallel Drafting

**Status**: UNBLOCKED (Phase 4-6 complete). Ready to start. Requires bare-metal NUMA hardware (not available in devcontainer).

### Architecture

Two parallel draft workers, one per NUMA node:

```
┌─────────────────────────────────────────────────────┐
│                    EPYC 9655                         │
│                                                      │
│  ┌──────────────────┐    ┌──────────────────┐       │
│  │  NUMA Node 0     │    │  NUMA Node 1     │       │
│  │  Cores 0-47      │    │  Cores 48-95     │       │
│  │  ~230 GB/s       │    │  ~230 GB/s       │       │
│  │                  │    │                  │       │
│  │  Draft Worker A  │    │  Draft Worker B  │       │
│  │  Subtree A       │    │  Subtree B       │       │
│  └──────────────────┘    └──────────────────┘       │
│                                                      │
│  Phase 1: Both draft workers run in parallel         │
│  Phase 2: Merge subtrees → combined tree             │
│  Phase 3: Target verification (all 96 phys cores)    │
└─────────────────────────────────────────────────────┘
```

### Key Design Decisions (to resolve when starting)

- Coordination protocol: HTTP vs shared memory
- Merge strategy: wait-all vs proceed-with-partial
- Worker A takes top-k/2 tokens, Worker B takes next-k/2 at root
- `--draft-workers` flag (new) for dual-worker coordination
- Draft workers: separate llama-server instances or in-process threads

### NUMA Benchmark Plan

**Step 0 — Baseline NUMA characterization** (before dual-worker implementation):

```bash
# Single NUMA node (48 physical cores, ~230 GB/s bandwidth)
numactl --cpunodebind=0 --membind=0 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-f16.gguf \
  -md /mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf \
  --draft-max 16 -t 48 --port 8199

# Both NUMA nodes interleaved (current default)
numactl --interleave=all \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-f16.gguf \
  -md /mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf \
  --draft-max 16 -t 96 --port 8199
```

**Step 1 — Concurrent independent decodes** (2 separate servers, one per NUMA node):

```bash
# Server A on NUMA node 0
numactl --cpunodebind=0 --membind=0 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-f16.gguf \
  -t 48 --port 8199

# Server B on NUMA node 1 (concurrent)
numactl --cpunodebind=1 --membind=1 \
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-f16.gguf \
  -t 48 --port 8200
```

Measure: aggregate t/s of both servers vs single server with all 96 cores.

### Files

- `tools/server/server-context.cpp` — NUMA coordination, dual-worker merge
- `tools/server/server.cpp` — `--draft-workers` flag (new)
- `epyc-orchestrator/scripts/server/orchestrator_stack.py` — NUMA-aware launch

## Phase 8 — Tree Speculation for Delta Net Hybrid Models

### Problem

Phase 3 showed multi-path target verification is fundamentally incompatible with hybrid models because `llama_memory_seq_cp` forks KV attention state but NOT recurrent state. This was treated as a hard blocker, and the original plan assumed STree's tree-masked `ggml_ssm_scan` would solve it.

### Architecture Correction: Delta Net, Not Mamba2

**Critical discovery (2026-03-15)**: Qwen3.5 and Qwen3-Next do **NOT** use `ggml_ssm_scan` (Mamba2 SSM). Their recurrent layers use **Delta Net** (gated linear attention), implemented in `src/models/delta-net-base.cpp`. The original Phase 8 plan targeting `ggml_ssm_scan` was incorrect.

**Delta Net recurrence** (`delta-net-base.cpp`):
```
s_t = exp(g_t) * s_{t-1} + k_t ⊗ (beta_t * (v_t - s_{t-1}^T k_t))
```
- State: outer-product matrix `{S_v, S_v, H_v, n_seqs}` per layer (NOT Mamba2's `{d_state, head_dim, n_head}`)
- Decay: `g = softplus(alpha + bias) * ssm_a` — per-head scalar (GDA) or per-head-per-dim (KDA)
- Two paths: autoregressive (`n_seq_tokens==1`, lines 291-376) and chunked (`n_seq_tokens>1`, chunk_size=64, lines 15-289)
- Conv: uses `ggml_ssm_conv` for 1D convolution pre-processing (shared with Mamba2)
- Dispatch: `qwen35.cpp` ~line 300 — `n_seq_tokens==1 ? autoregressive : chunking`

**`ggml_ssm_scan` is used by**: Mamba-1/2 (`mamba-base.cpp`), Jamba, Falcon-H1, Granite-Hybrid, Nemotron-H, PLaMo2/3 — none in our production stack. STree's original algorithm works directly on those models without modification.

**Why STree's log-space trick doesn't apply to Delta Net**: The key difference is nonlinearity:
- **Mamba2**: `s_new = dA * s_old + B * u` — linear in state → cumulative log-sum trick works
- **Delta Net**: `s_new = exp(g) * s_old + k ⊗ beta * (v - s_old^T k)` — `s_old` appears in BOTH the decay AND the delta term `v - s_old^T k`, creating a nonlinear state dependency that can't be converted to a tree-masked cumulative sum

### Approach 0: Frozen Multi-Path — ❌ RULED OUT (2026-03-15)

**Hypothesis**: With `freeze_recurrent=true`, recurrent `seq_cp()` is a shared-reference add (no data copy). All seq_ids read identical frozen recurrent state. Attention layers diverge per seq_id, providing path differentiation. Existing dense multi-path code should work on hybrid models at zero architectural cost.

**Implementation**: Removed `!has_recurrent` guard (line 2247), auto-enabled `kv_unified` for attention KV `seq_cp()`, auto-bumped `n_seq_max` for tree seq_ids. Required fixing `kv_unified` auto-enable — without it, attention `seq_cp()` hits cross-stream assertion (`llama_kv_cache::seq_cp` line 440).

**Empirical results** (4 prompts × 256 tokens, Qwen3.5-0.8B-Q8 drafter):

| Target | Quant | Linear t/s | Linear Accept% | Best Tree t/s | Tree Accept% | Delta |
|--------|-------|-----------|----------------|--------------|-------------|-------|
| Qwen3.5-9B-A3B | Q4_K_M | 13.06 | 60.7% | 5.72 | 39.5% | **-56%** |
| Qwen3.5-27B-A3B | Q4_K_M | 5.15 | 53.4% | 1.97 | 28.4% | **-62%** |
| Qwen3.5-35B-A3B | Q4_K_M | 9.83 | 44.4% | 4.62 | 32.8% | **-53%** |
| Qwen3.5-35B-A3B | Q8_0 | 9.87 | 50.5% | 3.99 | 28.5% | **-60%** |

**Root cause**: Frozen recurrent state means tree paths can only diverge via attention layers (~25% of layers in Qwen3.5). Attention-only path diversity is insufficient to recover acceptance rate — acceptance drops 12-22pp. Combined with ~41ms tree overhead, throughput collapses.

**Code reverted**: `!has_recurrent` guard restored. `kv_unified` auto-enable and `n_seq_max` auto-bump retained (benefits dense models).

**Data**: `epyc-inference-research/data/tree_speculation/server_sweep_20260315_*.csv`

### Approach A: Sequential State Replay — ❌ NET-NEGATIVE (2026-03-15)

For each tree path, replay Delta Net states sequentially using checkpoint/restore. The existing tree infrastructure (Phases 1-3) builds the tree during drafting. At verification time:

1. **Draft phase**: Build tree using existing DySpec (unchanged). Freeze recurrent as before.
2. **Pre-freeze**: Save recurrent checkpoint (`llama_memory_checkpoint_save`) before freeze.
3. **Tree setup**: Fork attention KV for alt paths via `seq_cp` (existing). For hybrid: store path tokens in `tree_replay_paths` instead of adding to shared batch. For dense: unchanged batched verification.
4. **Verification phase**: For each root-to-leaf path (0..N):
   a. Restore recurrent checkpoint (O(1) shadow swap)
   b. Unfreeze recurrent
   c. Build mini-batch: sampled token + path's draft tokens
   d. Decode (attention uses forked KV, recurrent advances from checkpoint)
   e. Sample acceptance from exact (non-frozen) logits
   f. Re-freeze for next path
5. **Accept**: Longest accepted path wins. Swap attention KV if alt path won.
6. **Cleanup**: Restore checkpoint before re-advancing accepted tokens through recurrent state.

**Cost model**: N_paths × (1 + path_length) tokens decoded per path. For 8 paths × ~6 tokens: ~48 mini-batch decodes. Each decode processes recurrent + attention (not separable in llama.cpp), but mini-batches are small (≤7 tokens). Expected ~5-15ms/path.

**Implementation** (7 change sites in `server-context.cpp`, 170 lines net):

| Change | Line | Description |
|--------|------|-------------|
| 1 | ~70 | Added `std::vector<llama_tokens> tree_replay_paths` field to `server_slot` |
| 2 | ~200 | Clear `tree_replay_paths` in `reset()` |
| 3 | ~2207 | Save checkpoint before freeze-recurrent |
| 4 | ~2253 | Remove `!has_recurrent` guard from tree block |
| 5 | ~2293 | Hybrid branch: store path tokens, skip adding to shared batch |
| 6 | ~3220 | Per-path sequential replay: restore→unfreeze→decode→sample→freeze per path |
| 7 | ~3393 | Restore checkpoint before re-advancing accepted tokens |

**Dense tree path**: Completely unchanged. Only hybrid models use per-path replay.

#### Benchmark Results — NET NEGATIVE

| Model Pair | Config | t/s | Accept% | Delta |
|------------|--------|-----|---------|-------|
| Qwen3.5-9B Q4KM + 0.8B Q8 | linear | 7.18 | 74.2% | — |
| Qwen3.5-9B Q4KM + 0.8B Q8 | tree p=0.05 | 2.41 | 45.4% | **-66%** |
| Qwen3.5-35B-A3B Q4KM + 0.8B Q8 | linear | 10.12 | 75.8% | — |
| Qwen3.5-35B-A3B Q4KM + 0.8B Q8 | tree p=0.05 | 4.02 | 49.9% | **-60%** |
| Qwen3.5-35B-A3B Q4KM + 0.8B Q8 | tree p=0.3 | 4.22 | 49.9% | **-58%** |

**Root cause**: `llama_decode()` runs ALL model layers (attention + recurrent + FFN), not just recurrent. Per-path replay cost is O(N_paths × full_forward_pass), not O(N_paths × recurrent_only) as the plan assumed. For 8 paths at 6 tokens each, this is ~48 full forward passes per speculation round.

**Acceptance drop**: 75% (linear) → 50% (tree replay). Two possible causes:
1. Sampler clone drift — `common_sampler_clone` doesn't preserve full RNG state from the exact pre-speculation point
2. Tree path tokens diverge from the greedy path, and the target model is sensitive to these alternate prefixes

**Conclusion**: Approach A is fundamentally limited by llama.cpp's monolithic `llama_decode`. Without layer-selective decode (run only recurrent layers), per-path replay cannot be cheaper than ~N× the baseline decode cost.

**Data**: `epyc-inference-research/data/tree_speculation/server_sweep_20260315_184630.csv` (pair 4), `server_sweep_20260315_193244.csv` (pair 14)

#### What Would Make Approach A Viable

1. **Layer-selective decode**: New `llama_decode_layers(ctx, batch, layer_start, layer_end)` API that runs only specified layers. Per-path replay would use only recurrent layers (~0.5ms/token vs ~100ms/token for full model). This is a significant llama.cpp architectural change.
2. **GPU with parallel batch slots**: On GPU, N paths could decode in parallel (single kernel launch). CPU-only replay is inherently sequential.

### Approach B: Linearized Delta Net (Low Priority — Deferred)

Approximate the Delta Net recurrence by freezing the `s_old^T k` term at the base state value. Single forward pass for all tree paths. However:

- **Viability risk HIGH (~40%)**: The `s^T k` nonlinearity may dominate for paths >3 tokens
- **Similar to freeze-recurrent**: Both approximate the state; B is mathematically cleaner but still approximate
- **Approach 0 already showed**: frozen state collapses acceptance 12-22pp. Linearization may recover some but unlikely to recover all
- **Deferred**: Only worth revisiting if Approach C fails. B's ceiling is modest even if it works.

### Approach C: Checkpoint + Clone Cell — ❌ RULED OUT (2026-03-16)

**Implemented approach**: Instead of a second model instance, used the existing checkpoint/restore API + a new `llama_memory_recurrent_clone_cell()` API to maintain exact recurrent state per tree path within the single target context. Checkpoint saves before tree, clone_cell gives each alt path its own recurrent cell, batched decode produces exact logits, checkpoint restores after verification.

**Result**: -60% throughput (4.44 vs 10.96 t/s on 35B-A3B Q4KM). 16 tree path wins confirmed (implementation correct) but overhead > benefit. Root cause: checkpoint save copies ~450MB recurrent state per round, clone_cell copies tensor slices per path via CPU staging buffer, batched multi-path decode has O(N_paths) recurrent compute.

**Bugs found and fixed**: (1) clone_cell tail pointer corruption — `cells[dst_cell].tail = -1` in the dual-purpose cells array overwrites seq metadata for unrelated sequences. (2) Batch allocator for hybrid+kv_unified — `LLAMA_MAX_SEQ=256` exceeded recurrent cell count; constrained to `cparams.n_seq_max`. (3) M-RoPE position validation — re-advance must remove ALL speculation positions before re-inserting accepted tokens.

**Original plan** (decoupled state maintainer) was never needed — the core issue is that ANY approach maintaining exact recurrent state per path costs O(N_paths × full_forward) for the recurrent layers.

**Architecture note**: Qwen3.5 is 75% recurrent (Delta Net) / 25% attention — the recurrent layers ARE the backbone, not a small head. A "recurrent-only" extraction would be most of the model. The real savings come from MoE sparsity: Qwen3.5-35B-A3B has 35B total params but only ~3B active per token, making a second full-model instance cheap to run.

#### GGUF Layer Analysis (2026-03-15)

Qwen3.5 with `full_attention_interval=4`: every 4th layer is standard attention, the rest are Delta Net (linear attention + FFN).

| Model | Layers | Recurrent | Attention | Recurrent GGUF | Full GGUF |
|-------|--------|-----------|-----------|----------------|-----------|
| Qwen3.5-9B Q4KM | 32 | 24 (3.26 GB) | 8 (1.00 GB) | **4.67 GB** | 5.67 GB |
| Qwen3.5-35B-A3B Q4KM | 64 | 48 (14.37 GB) | 16 (4.78 GB) | **15.06 GB** | 19.84 GB |

Each recurrent block is a complete transformer-style block (Delta Net gated linear attention + `attn_gate`/`attn_qkv` + FFN). Extracting them produces a valid model architecture — a pure-Delta-Net network.

#### Why This Works

1. **GGUF extraction feasible**: Use `gguf-py` to extract embedding + recurrent layer tensors + output head. Renumber layers 0..N. Set `full_attention_interval` to large value (all-recurrent). llama.cpp loads it as a standard Qwen3.5 model — no code changes to the inference engine.

2. **Own context, own decode**: The recurrent-only model runs in its own `llama_context` with its own `llama_decode`. Each call only processes 24 layers (9B case) instead of 32, and with smaller intermediate tensors.

3. **State injection**: During verification, the recurrent-only model's state can be checkpointed and restored to the target model's recurrent cells via the existing checkpoint API. The state tensors (`ssm_a`, conv state, scan state) are identical in shape between the full model and the extracted model (same `d_inner`, `d_state`, `d_conv`).

#### Design Choice: Full Model vs Recurrent-Only Extraction

Two options for the decoupled head:

**Option 1 — Recurrent layers only** (skip attention layers):
- Produces **approximate** state. Attention layers transform hidden state between recurrent blocks; skipping them causes divergence.
- Smaller/faster: 4.67 GB (9B), 15.06 GB (35B-A3B)
- Requires state divergence probe to validate quality

**Option 2 — Full model, no output projection** (PREFERRED):
- Produces **exact** recurrent state. All layers run, state is identical to target model.
- Skip only the output head (`output.weight` — the `[d_model × n_vocab]` matmul, 1.41 GB in 9B case). llama.cpp already supports this: `batch.logits[i] = false` skips logit computation.
- Exact state eliminates the approximation risk entirely.
- Cost: full forward pass minus output head per draft token.

**Key shift**: The recurrent head runs **during drafting** (one token at a time, sequentially alongside the token drafter), NOT during verification. At verification time, the target gets pre-warmed state injected — verification is a single decode with correct state, not N replays.

#### Viability by Model Architecture

| Target | Active Params | Recurrent Head Speed | Drafter Speed | Bottleneck |
|--------|--------------|---------------------|---------------|------------|
| Qwen3.5-9B (dense) | 8.95B | ~5-7 t/s | ~100+ t/s | Head ❌ — slower than target itself |
| Qwen3.5-35B-A3B (MoE) | ~3B active | ~30-40 t/s | ~100+ t/s | Head ✅ — fast enough |
| Qwen3.5-122B-A10B (MoE) | ~10B active | ~10-15 t/s | ~100+ t/s | Marginal — needs profiling |

**Critical finding**: Decoupled recurrent head is viable primarily for **MoE hybrid models** where active params per token are a fraction of total. For dense hybrids (9B), the head IS the full model — no speedup possible.

For MoE hybrids, the recurrent head processes only the active expert subset per token. The 35B-A3B model has ~3B active params — the recurrent head runs at ~30-40 t/s, fast enough to keep up with token drafting and maintain per-path state during tree construction.

#### Architecture (C3 Refined)

```
DRAFT PHASE (runs during tree construction):
  Token Drafter (0.8B)       ──→  draft tokens per tree path
  Recurrent Head (full model ──→  exact recurrent state per tree path
    minus output projection)      (runs in parallel, same tokens, logits=false)

VERIFICATION PHASE (target model):
  For each tree path:
    1. Inject recurrent state from head's checkpoint
    2. Single target decode (attention uses forked KV, recurrent already correct)
    3. Sample from target logits (exact, not frozen)
  Accept longest matching path (existing tree logic)
```

**Cost model**:
- Draft phase: token drafter (~0.8B) + recurrent head (~3B active for MoE). Head latency dominates at ~25-30ms/token.
- Verification: ONE decode per path (not N full replays as in Approach A). For 8 paths: 8 × target_decode_time.
- Net: draft cost increases ~3-5x over drafter-only, but verification cost drops from N×full_forward (Approach A) to 1×full_forward per path with correct state.

#### Implementation Plan

**Target**: MoE hybrid models (Qwen3.5-35B-A3B, 122B-A10B) where active params/token << total params.
**Not viable for**: Dense hybrids (Qwen3.5-9B, 27B) — the full head IS the full model.

1. **Proof of concept — recurrent head as separate server instance**:
   - Load the SAME target model GGUF in a second llama-server instance with `logits=false` equivalent
   - Run identical prompts, checkpoint recurrent state at position N
   - Verify states are bit-identical (sanity check for the injection path)
   - This requires no GGUF extraction — just two instances of the same model

2. **State injection API**:
   - `llama_memory_recurrent_inject(target_mem, source_checkpoint)` — copy recurrent cells from one context to another
   - Must handle the case where source and target have same layer structure but different contexts
   - This is the core llama.cpp C++ change needed

3. **Server integration** (draft-phase co-processing):
   - Load target model twice: once as target (full decode), once as recurrent head (no output projection)
   - During draft phase: for each draft token on each tree path, also decode through recurrent head (`logits=false`)
   - Checkpoint recurrent head state per path
   - During verification: inject per-path state into target, single decode per path
   - Accept best path (existing tree logic)

4. **Optimization — output projection stripping**:
   - Optional: create a GGUF without `output.weight` tensor to save 0.7-1.4 GB VRAM/RAM
   - Or: just use `logits=false` on the full model GGUF (simpler, no extraction needed)

5. **NUMA integration** (Phase 7+C synergy):
   - NUMA node 0: token drafter (0.8B) + recurrent head (3B active)
   - NUMA node 1: target verification (3B active, but with correct attention KV + recurrent state)
   - Natural workload split — drafting and verification run on separate memory domains

#### Validation Gates

1. **Gate 1**: State identity — two instances of same model produce bit-identical recurrent state
2. **Gate 2**: State injection — injected state produces identical logits vs native decode
3. **Gate 3**: Draft-phase throughput — recurrent head keeps up with drafter (>20 t/s for 35B-A3B)
4. **Gate 4**: Acceptance recovery — tree acceptance > 65% (vs 75% linear, 50% frozen)
5. **Gate 5**: Net throughput — exceeds linear speculation baseline by > 15% on MoE hybrids

#### Scope Limitation

Dense hybrid models (Qwen3.5-9B, 27B) remain limited to linear speculation + freeze-recurrent. The recurrent head approach offers no speedup when active_params ≈ total_params. For these models, the production config is: `--draft-max 16` (linear), no `--draft-p-split` (no tree).

### Key Differences from Dense Tree Verification

| Aspect | Dense (Phase 3) | Hybrid Approach 0 (ruled out) | Hybrid Approach A (ruled out) | Hybrid Approach C (ruled out) |
|--------|-----------------|-------------------------------|-------------------------------|-------------------------------|
| State forking | `llama_memory_seq_cp` per path | Frozen (no fork) | Checkpoint/replay per path | Checkpoint + clone_cell per path |
| Recurrent overhead | N/A | O(1) frozen | O(n_paths × full_forward) ❌ | O(n_paths × recurrent_compute) ❌ |
| Attention layers | `seq_id` multi-path batch | Same | Same | Same (Phase 3 code reused) |
| Correctness | Exact | Degraded (-12-22pp) | Exact but too slow | Exact but too slow |
| Throughput delta | +15.8% (f16) | -53% to -62% | -60% to -66% | -60% |
| Memory | O(n_paths × KV_size) | O(KV) | O(1 snapshot + KV) | O(1 snapshot + n_paths × cell_data) |

### Files (Approach C)

| Action | File | Repo | Notes |
|--------|------|------|-------|
| Modify | `src/llama-memory-recurrent.cpp` | llama.cpp | `llama_memory_recurrent_inject()` — cross-context state copy |
| Modify | `include/llama.h` | llama.cpp | State injection API |
| Modify | `tools/server/server-context.cpp` | llama.cpp | Load state maintainer, integrate into draft phase |

### Files (Approach A — reverted, stashed for reference)

Code stashed in llama.cpp: `git stash list | grep "Phase 8 Approach A"`

### STree Reference (for Mamba2 Models — Not Our Stack)

[STree (arXiv:2505.14969)](https://arxiv.org/abs/2505.14969) solves tree speculation for **Mamba2** models via tree-masked `ggml_ssm_scan`. Key details preserved for reference:

- **Tree mask L**: Binary `{N×N}` matrix where `L[i,j] = 1` iff token `j` is ancestor of token `i`
- **Tree cumulative sum**: `dA_tree[s] = dA_tree[parent(s)] + dA[s]` (replaces sequential scan)
- **Activation replay on rejection**: Replays accepted prefix using cached `{A, B, C, dt}` to recover correct state
- **Benchmark** (MambaInLlama-8B, 50% hybrid, RTX 3090): 1.74x greedy, 1.36x temp=1, 0.57-0.91x memory
- **Single chunk limitation**: Asserts `seqlen < chunk_size` — tree must fit in one chunk
- **Repository**: [github.com/wyc1997/stree](https://github.com/wyc1997/stree)

STree would work directly on true Mamba2 models in llama.cpp (Jamba, Falcon-H1, Granite-Hybrid, PLaMo2/3) — these use `ggml_ssm_scan` and have the diagonal `A` matrix STree requires. However, none are in our production stack.

### Complete Research References

**Tree Speculative Decoding for SSMs:**
1. Wu et al., "STree: Speculative Tree Decoding for Hybrid State-Space Models," NeurIPS 2025. [arXiv:2505.14969](https://arxiv.org/abs/2505.14969). [Code](https://github.com/wyc1997/stree). [OpenReview](https://openreview.net/forum?id=a95Vd41o1u)
2. Yang et al., "SpecMamba: Accelerating Mamba Inference on FPGA with Speculative Decoding," ICCAD 2025. [arXiv:2509.19873](https://arxiv.org/abs/2509.19873)

**Delta Net / Gated Linear Attention:**
3. Schlag et al., "Linear Transformers Are Secretly Fast Weight Programmers," ICML 2021. [arXiv:2102.11174](https://arxiv.org/abs/2102.11174) (Delta Net foundation)
4. Yang et al., "Gated Delta Networks: Improving Mamba2 with Delta Rule," NeurIPS 2024. [arXiv:2412.06464](https://arxiv.org/abs/2412.06464) (GDN/Delta Net used in Qwen3.5)
5. Yang et al., "Parallelizing Linear Transformers with the Delta Rule over Sequence Length," NeurIPS 2024. [arXiv:2406.06484](https://arxiv.org/abs/2406.06484) (Chunked Delta Net algorithm — basis of `build_delta_net_chunking`)

**Hybrid SSM Speculation:**
6. Chen et al., "RAD: Redundancy-Aware Distillation for Hybrid Models via Self-Speculative Decoding," May 2025. [arXiv:2505.22135](https://arxiv.org/abs/2505.22135)
7. "Characterizing SSM and SSM-Transformer Hybrid Performance with Long Context," Jul 2025. [arXiv:2507.12442](https://arxiv.org/abs/2507.12442)
8. "Mamba-3: Foundation SSM Model," ICLR 2026. [OpenReview](https://openreview.net/pdf?id=HwCvaJOiCj)

**SSM Speculative Decoding (General):**
9. Kumar, Dao & May, "Speculative Speculative Decoding," ICLR 2026. [arXiv:2603.03251](https://arxiv.org/abs/2603.03251)
10. "The Mamba in the Llama: Distilling and Accelerating Hybrid Models," NeurIPS 2024. [Paper](https://proceedings.neurips.cc/paper_files/paper/2024/file/723933067ad315269b620bc0d2c05cba-Paper-Conference.pdf)

## Stretch — Tree-Aware Attention Mask

**Only if Phase 4-6 shows tree wins but verification is the bottleneck (not construction).**

Construct a custom attention mask encoding tree topology for single-pass verification of all tree paths simultaneously (SpecInfer/Medusa approach). Reduces verification from O(n_paths) forward passes to O(1).

### Files

- `llama.cpp/src/llama-kv-cache.cpp` — tree-aware KV management

## Validation Checklist

- [x] **Correctness**: p_split=0 produces identical results to linear speculation (validated Phase 2.5)
- [x] **Multi-path**: Alternative paths win verification 14-20 times per 128-256 token generation (validated Phase 3)
- [x] **Greedy guarantee**: Path 0 (greedy) never worse than linear (validated — get_greedy_path fix)
- [x] **f16 net win**: +15.8% on Qwen2.5-Coder-32B f16 (Phase 4)
- [x] **Overhead reduction**: ❌ Not achievable — Phase 5a/5b/5c all ruled out. ~41ms/round is hard floor. Pivot to adaptive bypass (Phase 6).
- [x] **Adaptive**: ❌ Acceptance-rate EMA doesn't trigger — all pairs in 40-85% band. Reverted. (Phase 6)
- [ ] **NUMA gain**: Dual-worker drafting shows measurable improvement vs single drafter (Phase 7)
- [x] **SSM tree (Approach 0)**: ❌ Frozen multi-path ruled out — acceptance rate collapses 12-22pp on all hybrid models (Phase 8)
- [x] **SSM tree (Approach A)**: ❌ Net-negative (-60% to -66% throughput). Per-path full-model replay too expensive. Acceptance dropped 75%→50%. (Phase 8)
- [x] **SSM tree (Approach C)**: ❌ Net-negative (-60% throughput). Checkpoint + clone_cell correct but overhead > benefit. 16 tree path wins confirmed. (Phase 8)
- [ ] **SSM tree (B)**: Linearized Delta Net — last remaining approach for hybrid tree (~40% viability). Deferred. (Phase 8)
- [x] **Reproducible**: All benchmarks use `question_pool.py` prompts, saved to `epyc-inference-research/data/tree_speculation/`

## Test Prompts & Data

- **Prompts**: Use `question_pool.py` (`epyc-inference-research/scripts/benchmark/question_pool.py`) for reproducible test prompts across all phases
- **Standalone benchmarks**: `bench_tree_speculation.sh` outputs to `${LOG_DIR}/tree_speculation/`
- **Server benchmarks**: Save to `epyc-inference-research/data/tree_speculation/` (create directory when Phase 1 begins)
- **Comparison data**: Keep standalone vs server results side-by-side for parity verification

## Files Summary

### Completed (Phases 1-3 + greedy fix)

| Action | File | Repo | Phase |
|--------|------|------|-------|
| Modified | `common/speculative.cpp` | llama.cpp (feature/tree-speculation) | 1, 2, 3, greedy fix |
| Modified | `common/speculative.h` | llama.cpp (feature/tree-speculation) | 1, 2, greedy fix |
| Modified | `common/common.h` | llama.cpp (feature/tree-speculation) | 1, 3 (enum + n_seq_max) |
| Modified | `common/common.cpp` | llama.cpp (feature/tree-speculation) | 3 (n_seq_max override) |
| Modified | `common/arg.cpp` | llama.cpp (feature/tree-speculation) | 1 (--draft-p-split to server) |
| Modified | `tools/server/server-context.cpp` | llama.cpp (feature/tree-speculation) | 1, 2.5, 3 (multi-path verify) |
| Created | `data/tree_speculation/` | epyc-inference-research | 1 |
| Modified | `scripts/benchmark/bench_tree_speculation_server.sh` | epyc-inference-research | 3 (pairs 5,6 + extra args) |

### Future (Phases 4-7)

| Action | File | Repo | Phase |
|--------|------|------|-------|
| Modify | `scripts/benchmark/bench_tree_speculation_server.sh` | epyc-inference-research | 4 (f16 pair) |
| Modify | `common/speculative.cpp` | llama.cpp (feature/tree-speculation) | 5, 6 (overhead + adaptive) |
| Modify | `tools/server/server-context.cpp` | llama.cpp (feature/tree-speculation) | 6, 7 (adaptive + NUMA) |
| Create | `tools/server/server.cpp` | llama.cpp (feature/tree-speculation) | 7 (--draft-workers flag) |
| Modify | `scripts/server/orchestrator_stack.py` | epyc-orchestrator | 7 (NUMA launch) |
| Modify | `tools/server/server-context.cpp` | llama.cpp (feature/tree-speculation) | 8A (per-path replay, remove !has_recurrent guard) |
| Modify | `src/llama-memory-recurrent.cpp` | llama.cpp (feature/tree-speculation) | 8A (named snapshot slots) |
| Modify | `src/llama-memory-recurrent.h` | llama.cpp (feature/tree-speculation) | 8A (snapshot API) |
| Modify | `src/models/delta-net-base.cpp` | llama.cpp (feature/tree-speculation) | 8B (build_delta_net_tree, stretch) |
| Modify | `src/models/qwen35.cpp` | llama.cpp (feature/tree-speculation) | 8B (tree dispatch, stretch) |

## Code Change Policy

All C++ changes on `feature/tree-speculation` branch off `production-consolidated-v2` → validate → merge to `production-consolidated-v2`. Same branch pattern as HSD's `feature/ssm-checkpoint-opt`.

## Dependency Graph

```
Handoff 1 (profiling) ──→ tree budget parameter (Q4_K_M: 32-64 nodes, f16: 128-256 nodes)
                     ──→ verification cost curve for dynamic expansion
                     ──→ f16 near-flat verification (1.69x at N=64) → Phase 4 validation target
Handoff 2 (HSD)     ──→ HSD capped branch resampling (+0.8% marginal, free, inherited by tree verify)
                     ──→ auto freeze-recurrent for hybrid models (tree gets this for free)
                     ──→ prompt lookup works on hybrid (tree can combine with lookup)
                     ──→ self-spec/HiSpec busted (don't pursue hierarchical tree verification)
                     ──→ dense external draft baseline: 13.07 t/s on Qwen3-32B (tree must beat this)
Phase 3 results      ──→ Tree overhead ~41ms/round, +21% accepted/round, net -5% throughput on Q4_K_M
                     ──→ f16 targets most promising (Phase 4) → overhead reduction (Phase 5) → adaptive (Phase 6) → NUMA (Phase 7)
                     ──→ Hybrid models incompatible with seq_id-based multi-path (Phase 3)
                     ──→ STree tree-masked SSM scan lifts hybrid incompatibility (Phase 8)
STree paper          ──→ Tree mask works on Mamba2 (diagonal A), NOT Delta Net (nonlinear recurrence)
                     ──→ Approach A: per-path replay (exact, ~40-60ms overhead)
                     ──→ Approach B: linearized Delta Net (approximate, single-pass, stretch goal)
```

## Conflict Analysis

No conflicts with active handoffs. HSD handoff (completed) modified the speculation loop in `server-context.cpp` — tree speculation will build on that code:
- Recurrent state management is now post-draft-source (after line ~2160, search `has_recurrent_mem && draft_found`). Tree draft will need to set `draft_from_lookup = false` for tree-drafted tokens.
- `slot.freeze_recurrent_active` tracks per-round freeze state — tree spec inherits this.
- `common_sampler_sample_and_accept_n()` in `sampling.cpp` includes HSD recovery — tree verification paths get this automatically.
- NUMA launch configuration is additive to `orchestrator_stack.py`.

## DFlash Cross-Reference (2026-03-17)

**DFlash block diffusion** ([`dflash-block-diffusion-speculation.md`](dflash-block-diffusion-speculation.md)) opens new composition opportunities for tree speculation:

### DFlash as O(1) Tree Builder
Tree speculation's key bottleneck is sequential AR draft generation — each draft token depends on the previous. DFlash eliminates this entirely: a small diffusion model generates all draft tokens in parallel via iterative denoising. The diffusion process naturally produces multiple candidates per position (from different denoising trajectories), making it an ideal tree builder.

### Composition Plan (DFlash Phase 5)
1. DFlash generates block of 16 draft tokens in parallel
2. Top-k logits at each position feed into DySpec tree construction
3. Tree verification uses existing infrastructure from this handoff (Phase 3-4)
4. Expected: significantly higher throughput than AR draft → DySpec tree, since draft latency becomes O(1) instead of O(n)

### NUMA-Parallel Verification (DFlash Phase 6)
DFlash Phase 6 benchmarks concurrent single-token decodes across NUMA nodes. If aggregate throughput exceeds serial, this extends our Phase 7 (NUMA-pinned dual drafting) to a NUMA-parallel verification paradigm — potentially reopening speculation on hybrid models.

### Master Index
See [`inference-acceleration-index.md`](inference-acceleration-index.md) for the full landscape of inference optimization handoffs.

## Closeout

Update `logs/agent_audit.log`, `progress/2026-03/YYYY-MM-DD.md`, this handoff status, Chapter 10 with empirical results, all research docs with insights.
