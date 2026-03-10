# Handoff: Tree Speculation + NUMA-Pinned Dual Drafting

**Status**: blocked
**Created**: 2026-03-07
**Blocked by**: hsd-hierarchical-self-speculation (HSD verification for tree paths)
**Blocks**: None
**Unblocked**: specexec-verification-profiling (completed 2026-03-10 — tree budget parameters now available)

## Objective

Implement tree-structured speculation with dynamic topology, NUMA-pinned parallel draft workers, and shared-prefix KV cache. All C++ work in `llama.cpp-experimental` first → validate → cherry-pick to `production-consolidated-v2`.

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
- Slot struct fields: `spec` (line 58), `drafted` (line 157), `n_draft_total`/`n_draft_accepted` (lines 171-172)
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

### Server Integration

- Add `--draft-p-split` to `LLAMA_EXAMPLE_SERVER` in `arg.cpp` (currently `LLAMA_EXAMPLE_SPECULATIVE` only)
- Add `common_speculative_draft_tree()` alongside existing `common_speculative_draft()` in `common/speculative.cpp`
- Gate tree path behind `p_split > 0` — when set, use tree drafting; otherwise linear (backward compatible)

### Files

- `llama.cpp/common/speculative.cpp` — `common_speculative_draft_tree()`, tree verification
- `llama.cpp/common/speculative.h` — `speculation_tree` struct, API declarations
- `llama.cpp/common/arg.cpp` — add `--draft-p-split` to `LLAMA_EXAMPLE_SERVER` (search `LLAMA_EXAMPLE_SPECULATIVE`)
- `llama.cpp/tools/server/server-context.cpp` — integrate tree drafting in speculation loop (search `common_speculative_draft`)

### Validation

- **Correctness**: Tree verification produces identical output to linear verification when tree is linear (degenerate case)
- **Acceptance**: Tree verification accepts at least as many tokens as linear verification
- **Reproducible prompts**: Use `question_pool.py` (`epyc-inference-research/scripts/benchmark/question_pool.py`) for test prompts
- **Comparison**: Run `bench_tree_speculation.sh` with standalone binary first, then server implementation, compare acceptance rates

## Phase 2 — DySpec Dynamic Tree Construction

Replace the linear draft loop with heap-based greedy expansion:

### Algorithm

```
function draft_tree(model, context, budget):
    tree = new_tree(root = context_last_token)
    heap = max_heap()  // keyed by cumulative log probability

    // Seed with top-k children of root
    logits = draft_model.forward(context)
    for tok in top_k(logits, k=5):
        heap.push((log_prob(tok), tree.add_child(root, tok)))

    while tree.n_nodes < budget and heap not empty:
        (prob, node) = heap.pop()
        logits = draft_model.forward(context + path_to(node))
        for tok in top_k(logits, k=3):
            child = tree.add_child(node, tok)
            heap.push((prob + log_prob(tok), child))

    return tree
```

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

## Phase 3 — NUMA-Pinned Parallel Drafting

### Architecture

Two parallel draft workers, one per NUMA node:

```
┌─────────────────────────────────────────────────────┐
│                    EPYC 9655                         │
│                                                      │
│  ┌──────────────────┐    ┌──────────────────┐       │
│  │  NUMA Node 0     │    │  NUMA Node 1     │       │
│  │  Cores 0-47      │    │  Cores 48-95     │       │
│  │  (phys) +96-143  │    │  (phys) +144-191 │       │
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

### Draft Worker Coordination

- Workers explore **different branches** of the probability distribution
- Worker A takes top-k/2 tokens, Worker B takes next-k/2 tokens at root
- At deeper levels, each worker expands its own subtree independently
- Merge: concatenate subtrees, remap parent indices

### Launch Configuration

```bash
# Draft worker A (NUMA node 0, 48 physical cores)
numactl --cpunodebind=0 --membind=0 llama-server \
  -m draft_model.gguf -t 48 --port 8090

# Draft worker B (NUMA node 1, 48 physical cores)
numactl --cpunodebind=1 --membind=1 llama-server \
  -m draft_model.gguf -t 48 --port 8091

# Target (both NUMA nodes, all 96 physical cores)
# -t 96 uses physical cores only (not SMT siblings) — correct for compute-bound verification
numactl --interleave=all llama-server \
  -m target_model.gguf -t 96 --port 8080 \
  --draft-workers 8090,8091  # MUST IMPLEMENT: new flag for dual-worker coordination
```

**Note**: `--draft-workers` does not exist yet. Must be implemented as a new server flag in `tools/server/server.cpp` (search `add_opt` for flag registration pattern). Prerequisite: define coordination protocol (request/response over HTTP or shared memory). Same pattern as HSD's `--n-layer-exit-draft` — plan the flag, implement when Phase 3 begins.

### Server Changes

- `orchestrator_stack.py` — NUMA-aware launch with `numactl --membind` per draft worker
- `--threads-draft` already exists (`arg.cpp:3268`, search `threads-draft`); add `--draft-workers` for dual-worker coordination (**must implement**)
- Coordination protocol: simple request/response, workers return subtrees

### Files

- `llama.cpp/tools/server/server-context.cpp` — NUMA coordination, dual-worker merge (search `common_speculative_draft` for integration point)
- `llama.cpp/tools/server/server.cpp` — `--draft-workers` flag (new)
- `epyc-orchestrator/scripts/server/orchestrator_stack.py` — NUMA-aware dual-worker launch

## Phase 4 — Shared-Prefix KV Cache (Stretch)

**Only attempt if Phase 1-3 validation shows tree speculation wins and larger trees are needed.**

### Problem

With `seq_id` encoding, tokens shared between tree paths have their KV entries computed multiple times. For trees with 100+ nodes and significant prefix sharing, this is wasteful.

### Solution

Reference-counted KV entries for tree branches sharing common prefixes:

```c
struct kv_entry {
    llama_token token;
    int32_t ref_count;    // number of sequences using this entry
    // ... existing KV data
};
```

Copy-on-write at branch divergence points:
- Shared prefix: all paths share same KV entries (ref_count > 1)
- At divergence: new KV entry created for branching path, ref_count decremented on original

### Model Registry Integration

Per-model acceleration config follows existing `type: speculative_decoding` pattern:

```yaml
# In model_registry.yaml, per-model entry:
acceleration:
  type: speculative_decoding
  tree:
    enabled: true
    budget: 64              # max tree nodes (from Handoff 1 profiling)
    p_split: 0.1            # branch probability threshold
    branching_factor: 5     # root branching, decreases with depth
  numa:
    dual_draft: true
    worker_threads: 48      # per worker (physical cores per node)
```

### Files

- `llama.cpp/src/llama-kv-cache.cpp` — reference-counted KV entries, COW logic

### Risk

High complexity, may introduce subtle bugs in KV cache management. Defer unless clearly needed for performance.

## Validation Checklist

- [ ] **Correctness**: Tree verification produces identical output to linear verification (degenerate case test)
- [ ] **Acceptance**: Dynamic trees accept more tokens than linear sequences of same total size
- [ ] **NUMA gain**: Dual-worker drafting shows measurable throughput improvement vs single drafter
- [ ] **End-to-end**: Tree spec throughput vs linear spec vs baseline, published with plots
- [ ] **Memory**: Tree structures don't cause excessive memory allocation
- [ ] **All results published** in research docs with supporting plots
- [ ] **Reproducible**: All benchmarks use `question_pool.py` prompts, results saved to `epyc-inference-research/data/tree_speculation/`

## Test Prompts & Data

- **Prompts**: Use `question_pool.py` (`epyc-inference-research/scripts/benchmark/question_pool.py`) for reproducible test prompts across all phases
- **Standalone benchmarks**: `bench_tree_speculation.sh` outputs to `${LOG_DIR}/tree_speculation/`
- **Server benchmarks**: Save to `epyc-inference-research/data/tree_speculation/` (create directory when Phase 1 begins)
- **Comparison data**: Keep standalone vs server results side-by-side for parity verification

## Files Summary

| Action | File | Repo | Phase |
|--------|------|------|-------|
| Reference | `examples/speculative/speculative.cpp` | llama.cpp | — (existing tree impl) |
| Reference | `scripts/benchmark/bench_tree_speculation.sh` | epyc-inference-research | — (existing benchmark) |
| Create/Modify | `common/speculative.cpp` | llama.cpp-experimental | 1, 2 |
| Create/Modify | `common/speculative.h` | llama.cpp-experimental | 1, 2 |
| Modify | `common/arg.cpp` | llama.cpp-experimental | 1 (add `--draft-p-split` to server) |
| Modify | `tools/server/server-context.cpp` | llama.cpp-experimental | 1, 3 |
| Modify | `tools/server/server.cpp` | llama.cpp-experimental | 3 |
| Modify | `src/llama-kv-cache.cpp` | llama.cpp-experimental | 4 (stretch) |
| Modify | `scripts/server/orchestrator_stack.py` | epyc-orchestrator | 3 |
| Modify | `orchestration/model_registry.yaml` | epyc-inference-research | 4 |
| Create | `data/tree_speculation/` | epyc-inference-research | 1 |

## Code Change Policy

All C++ changes → `llama.cpp-experimental` first → validate → cherry-pick to `production-consolidated-v2`.

## Dependency Graph

```
Handoff 1 (profiling) ──→ tree budget parameter
                     ──→ verification cost curve for dynamic expansion
Handoff 2 (HSD)     ──→ improved verification algorithm for tree paths
                     ──→ layer-skip data for hierarchical tree verification
```

## Conflict Analysis

No conflicts with active handoffs. Tree speculation server integration touches the speculation loop in `server-context.cpp` (search `common_speculative_draft`) — coordinate with any other server-side speculation changes. NUMA launch configuration is additive to `orchestrator_stack.py`.

## Closeout

Update `logs/agent_audit.log`, `progress/2026-03/YYYY-MM-DD.md`, this handoff status, Chapter 10 with empirical results, all research docs with insights.
