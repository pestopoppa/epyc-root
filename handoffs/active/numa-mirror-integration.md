# NUMA_MIRROR Fork Integration — vproxy-tools/llama.cpp port

**Status**: CLOSED 2026-04-27 — Phases 0a/0b/1a/1b/1c all LANDED and bit-exact. **Phase 2 throughput gate FAILED**: −1.0% on Coder-30B Q4_K_M tg128, +0.6% on Qwen3.6-35B Q8 tg64 (both within run-to-run noise). Investigation closed as **DECISIVE NEGATIVE on single-socket NPS4** because the hardware is DRAM-channel-bound, not fabric-bound — per-thread BW share is 4.79 GB/s regardless of NUMA placement. Reopen only if a 2-socket configuration becomes relevant.

**Commits**:
- `9b1dbf4dd` (Phase 0a): tensor_data()/tensor_set_data() accessor in ggml.h + 97 refs migrated in 5 read-only files (ggml.c, ggml-cpu.c, amx.cpp, mmq.cpp, kleidiai.cpp)
- `b9920cc44` (Phase 0b): 67 refs migrated in 6 files with writes/chained-pointers (ggml-backend.cpp, ggml-alloc.c, llama-model-loader.cpp, llama-kv-cache.cpp, llama-quant.cpp, ggml-backend-meta.cpp)
- `ca39cb80a` (Phase 1a): `data_per_node[GGML_NUMA_MAX_NODES]` field in `struct ggml_tensor`; `tensor_data()` reads `data_per_node[ggml_current_numa_node]`; `tensor_set_data()` writes ALL N identically; new `tensor_set_data_per_node(t, node, p)` API; `ggml_new_tensor_impl` populates the array. Built with `-DGGML_NUMA_MIRROR=4`, all replicas identical = no behavior change.
- `90a17af62` (Phase 1b): TLS setter at graph-compute entry. Each thread calls `getcpu(2)` after `set_numa_thread_affinity()` and writes the resulting node index to `ggml_current_numa_node`.
- `29a69599a` (Phase 1c): CPU_REPACK buffer-level mirror. Per-buffer side-table tracks N anon-mmap+mbind replicas; `init_tensor` fans out `data_per_node[]`, `set_tensor` (post-repack) copies primary→replicas, `free_buffer` cleans up. Migrated `forward_mul_mat` / `forward_mul_mat_id` (5 sites) in `repack.cpp` to `tensor_data()`. Trigger decoupled from `ggml_is_numa()` — fires whenever `GGML_NUMA_MIRROR>=2` (compile flag) and buffer ≥ 1 MiB.

**Validation**:
- Phase 0a/0b: PPL = 9.8567 ± 1.23745 (bit-exact, identical to pre-migration baseline). Coder-30B Q4_K_M throughput: 48.42 ± 0.06.
- Phase 1a: PPL chunks 1-12 on Coder-30B Q4_K_M: chunk1=7.4537, chunk12=11.1215, final=11.1215. **Identical byte-for-byte** to a clean `-march=znver5` non-mirror build (apples-to-apples baseline). Earlier "regression" vs the unflagged build was pure `-march=znver5` codegen drift in fp ops, not a mirror bug.
- Phase 1b: re-validated bit-exact after TLS setter wiring (chunk1=7.4537, final=11.1215, byte-identical to Phase 1a).

**Files DEFERRED to Phase 0c**:
- `ggml/src/ggml-opt.cpp`: type collision on `ggml_opt_dataset.data` (NOT a ggml_tensor). Blanket sed unsafe; needs per-line distinction between tensor accesses and dataset member accesses.

**Phase 1c LANDED 2026-04-27 (commit `29a69599a`)** — but the Phase 2 throughput gate FAILED.

## Phase 2 throughput results (proper canonical: `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active taskset -c 0-95 numactl --interleave=all -t 96 -fa 1 -mmp 0`)

| Model | Quant | tg128 baseline (-march=znver5) | tg128 mirror=4 | Δ |
|---|---|---|---|---|
| Coder-30B-A3B | Q4_K_M | 48.16 t/s | 47.66 t/s | **−1.0%** (within noise) |
| Qwen3.6-35B-A3B | Q8_0 | 23.30 t/s | 23.45 t/s | **+0.6%** (within noise) |

PPL bit-exact at 11.1215 ± 0.62430 with mirror=4 on Coder-30B Q4_K_M (chunk1 = 7.4537, byte-identical to znver5 baseline).

The mirror IS firing correctly: `cpu-repack-mirror: 13.1 GiB primary on node 0 + 3 node replicas (mirror=4)`. Threads correctly distribute (per the one-shot debug log captured during testing): cores 0–23 → node 0, 24–47 → node 1, 48–71 → node 2, 72–95 → node 3, with `getcpu(2)` reporting the matching node and `ggml_current_numa_node` set per thread. Each thread reads from its node's replica via `tensor_data()`.

**Phase 2 gate (≥ +25% on Coder-30B over 47.98 t/s): NOT MET.**

## Why Phase 1c does not deliver on this hardware

Single-socket NPS4 EPYC 9655 is **DRAM-channel-bound**, not fabric-bound, at 96-thread saturation:

- Total DRAM bandwidth: 460 GB/s (12 channels × DDR5-6000)
- Per-thread share at 96t: 460 / 96 = **4.79 GB/s/thread**
- With mirror, each NPS4 node has 3 channels (115.2 GB/s) and 24 threads → 115.2 / 24 = **4.79 GB/s/thread** — IDENTICAL

Mirroring shifts cross-NUMA reads to local reads, which would help only if the **fabric** (Infinity Fabric between CCDs / NUMA domains within the package) were the binding constraint. CPU24's perf-record at 96t showed compute kernels stalled on memory loads at 4.79 GB/s/thread, but that measurement could not distinguish fabric-stall from DRAM-channel-stall. **Phase 1c cleanly rules out the fabric-stall hypothesis** — every read is now local, and throughput is unchanged.

The vproxy-tools fork's reported gains (+62% QwQ-32B FP16, +34% DeepSeek-R1 671B Q8) were on **2-socket** 2× EPYC 9275F configurations where cross-SOCKET fabric (going through inter-package coherence links) IS substantially slower than DRAM channels. On single-socket NPS4 the intra-package fabric is fast enough that DRAM channels saturate first.

## Phase 1c implementation notes (kept for reference / future hardware)

The mirror code is correct, bit-exact, and useful infrastructure for any future hardware where fabric IS the binding constraint (2-socket EPYC, multi-package, GPU-CPU NUMA, etc.). It is left compile-time gated behind `GGML_NUMA_MIRROR=N`; default builds compile to a pure no-op.

Architecture (commit `29a69599a`):

1. `ggml/src/ggml-cpu/repack.cpp`: per-buffer side-table (`std::unordered_map<ggml_backend_buffer_t, cpu_repack_mirror>` under a mutex) tracks N replicas. Allocator re-mbinds primary to MPOL_BIND-node-0 (instead of MPOL_INTERLEAVE) and adds N-1 anon-mmap+mbind replicas.
2. `init_tensor` fans out `data_per_node[0..N-1]` to `(replica_n_base + tensor_offset)` for tensors whose data lies inside the buffer.
3. `set_tensor` (post-repack) copies the freshly-written tensor bytes from primary to each non-primary replica at the same offset.
4. `free_buffer` munmaps replicas and `ggml_aligned_free`s the primary.
5. `forward_mul_mat` / `forward_mul_mat_id` hot paths in `repack.cpp` (5 sites) migrated to `tensor_data()` so threads on nodes 1..3 read THEIR replica. Without this, Phase 1c regressed −45%.
6. Trigger decoupled from `ggml_is_numa()`: fires whenever `GGML_NUMA_MIRROR>=2` AND buffer ≥ 1 MiB. Works under `numactl --interleave=all + OMP_PROC_BIND=spread` (the proper canonical) — `--numa distribute` is NOT required and actually regresses the baseline at 96t.

What was NOT mirrored (deliberately, since Phase 1c results showed no win):
- File mmap (the ~4.3 GB of non-repacked tensors). Would have needed `llama_mmap::addr_per_node()` + a post-load tensor pointer fan-out in `llama-model-loader.cpp`.
- Plain CPU buffer (small, ~0.5–1 GB).
- KV / scratch / wdata buffers (intentionally — they stay on the single-pointer fallback).

If a future 2-socket reopen happens, those would extend the mirror. Note that hugepages are still not required: 4 KB anon pages with THP opportunistic 2 MB promotion is sufficient.

## Disposition

**CLOSED** as decisive negative on this hardware. Production stack should NOT enable `GGML_NUMA_MIRROR`. The accessor migration (Phase 0a/0b/1a/1b) is preserved in the codebase as zero-overhead infrastructure (`tensor_data()` compiles to direct field access in default builds). Reopen only if a 2-socket configuration becomes relevant.
**Priority**: **HIGH** — largest remaining concrete throughput lever after CPU1 software exhaustion + CPU2 SIMD work + CPU21 OMP affinity. Per CPU24 perf-record finding (compute kernels memory-stalled INSIDE on cross-NUMA loads at 96 threads with 4.8 GB/s/thread BW share), per-NUMA-node weight replication is the path to lift the per-thread BW ceiling.
**Categories**: hardware_optimization, inference_serving, numa_optimization
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Related**:
- [`cpu-uncore-fabric-attribution.md`](cpu-uncore-fabric-attribution.md) — CPU24 perf-record finding that motivates this work
- [`intra-process-tensor-parallel-decode.md`](intra-process-tensor-parallel-decode.md) — CPU1 P1.3 per-region mbind (CONFLICTS with mirror; mirror supersedes)
- [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) — CPU15 EP per-node anon mmap (PARTIAL OVERLAP for MoE; pick one)
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — CPU2 SIMD kernels read via `tensor->data` (need accessor migration)

## Background

CPU24 perf-record on REAP-246B Q4_K_M @ 96t (2026-04-26) showed 80% of cycles in compute kernels but with IPC 0.39 (vs Zen 5's peak ~5). The cores are physically inside the kernel functions but stalled waiting for memory loads — each cross-NUMA cache miss is ~150-250 cycles. With 96 threads sharing 460 GB/s aggregate DRAM = 4.8 GB/s/thread, per-thread bandwidth contention dominates.

`numactl --interleave=all` (the current proper canonical) distributes weight pages uniformly across all 4 NUMA nodes. Each thread accesses ~25% local + 75% remote. NUMA_MIRROR replaces interleave with **full per-node weight replication**: each NUMA node holds its own private copy of model weights → 100% local reads.

## Source: vproxy-tools/llama.cpp fork

Author: @wkgcass. Branch: `will-force-push`. Discussion: [ggml-org/llama.cpp #12289](https://github.com/ggml-org/llama.cpp/discussions/12289). Reference commit: [`9314286`](https://github.com/vproxy-tools/llama.cpp/commit/9314286) "a rough implementation of GGML_NUMA_MIRROR" (5 files, +217/−3).

### Mechanism

1. **Accessor migration**: `tensor->data` (raw pointer) → `tensor_data(t)` / `tensor_set_data(t, p)` in `ggml/include/ggml.h`. The accessor uses TLS `__thread int ggml_current_numa_node` to index into a per-node array of pointers.
2. **Thread→node binding**: at graph-compute entry in `ggml/src/ggml-cpu/ggml-cpu.c`, threads compute `ggml_current_numa_node = thread_id_to_node(my_id)`. User pins threads via `taskset`/`numactl`.
3. **Eager replication at model load** in `src/llama-mmap.cpp`: per-node `mmap("/dev/hugepages/llama-nodeN-*", MAP_SHARED|MAP_HUGETLB|MAP_POPULATE)` at fixed virtual addresses (`0x200000000000` node0, `0x400000000000` node1, +`0x200000000000` per node).
4. **Build**: `find_library(NUMA_LIBRARY numa)`, `-DGGML_NUMA_MIRROR=ON`, hugepage size `1073741824` (1 GB pages required).

### Reported results (upstream discussion)

Hardware: 2× EPYC 9275F, 2×12ch DDR5-6000, NPS1 (single-socket equivalents to our 9655):
- **QwQ-32B FP16**: 6.66 → **10.80 t/s (+62%)**
- **DeepSeek-R1 671B Q8** (MoE): 7.19 → **9.67 t/s (+34%)**

No upstream PR yet — remains in discussion phase. Author has follow-up commits (`f86568f` "auto numa selection and mem binding").

## Memory feasibility for our 5 production models (NPS4, 4× replication, 1.1 TB host)

| Model | Quant | Single | × 4 nodes | Fits 1.1 TB? |
|-------|-------|-------:|----------:|:-:|
| Qwen3-Coder-30B-A3B | Q4_K_M | 17 GB | 68 GB | ✓ |
| Qwen3.6-35B-A3B | Q8_0 | 34 GB | 136 GB | ✓ |
| Qwen3-Next-80B-A3B | Q4_K_M | 45 GB | 180 GB | ✓ |
| **Qwen3-Coder-REAP-246B-A35B** | Q4_K_M | 138 GB | **552 GB** | ✓ (53% of 1.1 TB; tight, no co-resident large model) |
| gemma-4-26B-A4B-it | Q4_K_M | 16 GB | 64 GB | ✓ |

All fit. REAP-246B is the constraining model — would consume ~half the RAM in mirror mode, leaving ~500 GB for KV/activations/EP buffers + other models.

## Integration effort estimate

Surface area in our `feature/cpu-ep-inter-process` tree: **189 `tensor->data` references in `ggml/src/` + 10 in `src/`**. Author quotes ~700 lines total for full integration.

Phase breakdown:
1. Accessor migration (4–6 h): mechanical sed + manual review of write-sites
2. mmap path port to `llama-mmap.cpp` + 1 GB hugepages plumbing (4–6 h)
3. TLS/thread-binding integration with existing `taskset`/numactl + CPU1 `mbind` (3–4 h)
4. 4-node generalization (vproxy hard-codes 2-node VAs at `0x200000000000` / `0x400000000000`) (2–3 h)
5. Test/bench/sweep across 5 models (4 h)

**Total: 1.5–2.5 engineer-days for a feature-flagged drop-in.**

Risk areas:
- Write-sites that mutate `tensor->data` mid-compute (KV cache, scratch buffers, RoPE freqs) MUST NOT be mirrored. Each must be audited.
- 1 GB hugepage reservation requires kernel boot param (`hugepagesz=1G hugepages=N`) — operational change.
- Operating-system-side tmpfs `/dev/hugepages` provisioning per node.

## Conflicts and overlaps with current stack

| Track | Status | Interaction |
|---|---|---|
| **CPU1 P1.3 per-region mbind** (`8cb04da9d`) | DEPRECATED already (instability) | DIRECT CONFLICT: mirror REPLACES interleave with replication. They are mutually exclusive. Mirror SUPERSEDES P1.3 for weights. |
| **CPU2 AVX-512BW kernels** (Q8_0, Q6_K) | LANDED | Neutral. Kernels read via `tensor_data()` once accessor migrated. CPU2 PPL bit-exact gates must be re-run after migration. |
| **CPU15 EP inter-process** | LANDED | PARTIAL OVERLAP for MoE: EP maintains per-node expert anon mmap (`9ccb00245`). NUMA_MIRROR makes EP redundant for MoE weights. Pick one for MoE; for dense models (gemma-26B, Qwen3.6-35B Q8) NUMA_MIRROR is the only mechanism. |
| **CPU21 OMP affinity stack** | LANDED | Neutral; thread-pinning required for either approach. |
| **CPU24 perf instrumentation** | DONE | Neutral; `tensor_data()` is a clean instrumentation point for fabric counters. |
| **--no-mmap / --mlock defaults** | active production behavior | INCOMPATIBLE — mirror requires mmap + hugepages. Needs separate code path. |

## Recommendation: PURSUE — partial scope, feature-flagged

This is the largest remaining concrete throughput lever after CPU1 software exhaustion (`project_cpu1_software_levers_exhausted.md`) + CPU2 SIMD work + CPU21 OMP affinity. The per-thread BW ceiling at 96t (~4.8 GB/s) is exactly what mirroring lifts. Reported gains (+34-62%) on similar EPYC hardware are credible.

### Concrete plan

1. **Phase 0 (1 day)**: Land accessor refactor (`tensor_data()`/`tensor_set_data()`) behind `GGML_NUMA_MIRROR=OFF` default — zero behavior change. Re-validate CPU2 bit-exact (Q6_K + Q8_0 PPL gates). This is a refactor commit only.
2. **Phase 1 (1 day)**: Port mmap-mirror path generalized to N=4 nodes; env-gated `GGML_NUMA_MIRROR=N` (N=2 or 4). Hugepages provisioning script in `scripts/`.
3. **Phase 2 (~half day)**: Bench gemma-26B Q4 + Coder-30B Q4_K_M first (smallest replication cost, fastest to test). Gate: **≥+25% decode vs current 47.98 t/s on Coder-30B** (~60 t/s target).
4. **Phase 3 (conditional, ~half day)**: If Phase 2 gate met, evaluate vs CPU15 EP for MoE on Qwen3.6-35B and Next-80B. Deprecate whichever loses head-to-head.
5. **Phase 4 (conditional)**: REAP-246B test only after single-model gain proven (REAP would need exclusive use of host RAM).

### Decision gates

- **Phase 2 gate**: ≥+25% on Coder-30B over current 47.98 t/s. Below this, it's not worth the operational complexity (1 GB hugepages, separate code path, mmap requirement).
- **Phase 3 gate** (vs CPU15 EP): for MoE models, NUMA_MIRROR must beat EP-with-shard or it's not worth keeping both mechanisms.
- **Quality gate**: PPL bit-exact required at every milestone.

## Open questions

1. Does mirror work cleanly with `--mlock`? The author's commits use `MAP_POPULATE` which is functionally similar but not identical.
2. How does mirror interact with `numa_balancing=0` (our current sysctl)? Should be neutral since pages are explicitly allocated via mbind in the mmap path.
3. KV cache placement: KV is dynamic + per-token; should NOT be mirrored. Each thread's KV access is local-to-its-node; that's fine because threads bind to nodes.
4. Activation buffer: short-lived, per-token allocations. Should NOT be mirrored.
5. What's the lazy-vs-eager replication trade-off? Eager (current vproxy approach) takes ~4× model load time; lazy (on-demand per node) avoids this but has first-touch latency on each new tensor access per node.

## Sources

- [GitHub Discussion #12289 — multi-NUMA inference tips](https://github.com/ggml-org/llama.cpp/discussions/12289)
- [vproxy-tools/llama.cpp@9314286](https://github.com/vproxy-tools/llama.cpp/commit/9314286) — initial GGML_NUMA_MIRROR commit
- [vproxy-tools/llama.cpp commits](https://github.com/vproxy-tools/llama.cpp/commits/will-force-push)
- [Issue #12444 — hugepages provisioning](https://github.com/ggml-org/llama.cpp/issues/12444)
- [Discussion #12303 — split-NUMA tradeoffs](https://github.com/ggml-org/llama.cpp/discussions/12303)
