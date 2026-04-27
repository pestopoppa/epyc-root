# NUMA_MIRROR Fork Integration — vproxy-tools/llama.cpp port

**Status**: CLOSED 2026-04-27 — DECISIVE NEGATIVE on single-socket NPS4. Phases 0a/0b/1a/1b/1c all LANDED bit-exact in `/mnt/raid0/llm/llama.cpp-experimental` `feature/cpu-ep-inter-process`. **Phase 2 throughput gate FAILED**: −1.0% on Coder-30B Q4_K_M tg128, +0.6% on Qwen3.6-35B Q8 tg64 (both within run-to-run noise). Investigation closed; reopen only if a 2-socket configuration becomes relevant.
**Priority**: ~~HIGH~~ → **CLOSED**
**Categories**: hardware_optimization, inference_serving, numa_optimization
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Related**:
- [`cpu-uncore-fabric-attribution.md`](cpu-uncore-fabric-attribution.md) — CPU24 perf-record finding that motivated this work
- [`intra-process-tensor-parallel-decode.md`](intra-process-tensor-parallel-decode.md) — CPU1 P1.3 per-region mbind (DEPRECATED earlier; mirror would have superseded it)
- [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) — CPU15 EP per-node anon mmap (would have partially overlapped for MoE; mirror's failure leaves CPU15 in place)
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — CPU2 SIMD kernels read via `tensor_data()` after the accessor migration

---

## Cross-architecture coverage CLOSED 2026-04-28 (Phase 2.6)

Dense/hybrid Qwen3.6-27B Q8_0 measured: NUMA_MIRROR=4 vs baseline = 4.71 vs 4.77 (-1.3%, within noise). Confirms the Phase 2 negative result generalizes from MoE proxies to dense/hybrid. Hardware is DRAM-channel-bound for ALL architectures tested. **Closure language now reads**: "DECISIVE NEGATIVE on single-socket NPS4 — confirmed across MoE Q4_K_M sync-bound, MoE Q8_0 BW-bound, and dense/hybrid Q8_0 architectures." Reopen still requires 2-socket configuration. Bundle: `data/cpu_optimization/2026-04-28-cpu-cross-architecture-sanity/`.

---

## Commits

- `9b1dbf4dd` (Phase 0a): tensor_data()/tensor_set_data() accessor in ggml.h + 97 refs migrated in 5 read-only files (ggml.c, ggml-cpu.c, amx.cpp, mmq.cpp, kleidiai.cpp)
- `b9920cc44` (Phase 0b): 67 refs migrated in 6 files with writes/chained-pointers (ggml-backend.cpp, ggml-alloc.c, llama-model-loader.cpp, llama-kv-cache.cpp, llama-quant.cpp, ggml-backend-meta.cpp)
- `ca39cb80a` (Phase 1a): `data_per_node[GGML_NUMA_MAX_NODES]` field in `struct ggml_tensor`; `tensor_data()` reads `data_per_node[ggml_current_numa_node]`; `tensor_set_data()` writes ALL N identically; new `tensor_set_data_per_node(t, node, p)` API; `ggml_new_tensor_impl` populates the array. Built with `-DGGML_NUMA_MIRROR=4`, all replicas identical = no behavior change.
- `90a17af62` (Phase 1b): TLS setter at graph-compute entry. Each thread calls `getcpu(2)` after `set_numa_thread_affinity()` and writes the resulting node index to `ggml_current_numa_node`.
- `29a69599a` (Phase 1c): CPU_REPACK buffer-level mirror. Per-buffer side-table tracks N anon-mmap+mbind replicas; `init_tensor` fans out `data_per_node[]`, `set_tensor` (post-repack) copies primary→replicas, `free_buffer` cleans up. Migrated `forward_mul_mat` / `forward_mul_mat_id` (5 sites) in `repack.cpp` to `tensor_data()`. Trigger decoupled from `ggml_is_numa()` — fires whenever `GGML_NUMA_MIRROR>=2` (compile flag) and buffer ≥ 1 MiB.

## Files DEFERRED to Phase 0c

- `ggml/src/ggml-opt.cpp`: type collision on `ggml_opt_dataset.data` (NOT a ggml_tensor). Blanket sed unsafe; needs per-line distinction between tensor accesses and dataset member accesses. Training-path file, not on the perplexity/decode hot path; safe to defer indefinitely now that NUMA_MIRROR itself is closed.

## Phase 2 throughput results

Proper canonical: `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active taskset -c 0-95 numactl --interleave=all -t 96 -fa 1 -mmp 0`.

| Model | Quant | tg128 baseline (-march=znver5) | tg128 mirror=4 | Δ |
|---|---|---|---|---|
| Coder-30B-A3B | Q4_K_M | 48.16 ± 0.15 | 47.66 ± 0.04 | **−1.0%** (within noise) |
| Qwen3.6-35B-A3B | Q8_0 (tg64) | 23.30 ± 0.02 | 23.45 ± 0.02 | **+0.6%** (within noise) |

PPL bit-exact at 11.1215 ± 0.62430 with mirror=4 on Coder-30B Q4_K_M (chunk1 = 7.4537, byte-identical to znver5 baseline).

The mirror IS firing correctly: `cpu-repack-mirror: 13.1 GiB primary on node 0 + 3 node replicas (mirror=4)`. Threads correctly distribute (per the one-shot debug log captured during testing): cores 0–23 → node 0, 24–47 → node 1, 48–71 → node 2, 72–95 → node 3, with `getcpu(2)` reporting the matching node and `ggml_current_numa_node` set per thread. Each thread reads from its node's replica via `tensor_data()`.

**Phase 2 gate (≥ +25% on Coder-30B over 47.98 t/s): NOT MET** on the MoE proxies tested. Dense generalization measurement deferred to Phase 2.6 of the remediation plan.

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

## Memory feasibility for our 5 production models (NPS4, 4× replication, 1.1 TB host) — kept for the 2-socket reopen scenario

| Model | Quant | Single | × 4 nodes | Fits 1.1 TB? |
|-------|-------|-------:|----------:|:-:|
| Qwen3-Coder-30B-A3B | Q4_K_M | 17 GB | 68 GB | ✓ |
| Qwen3.6-35B-A3B | Q8_0 | 34 GB | 136 GB | ✓ |
| Qwen3-Next-80B-A3B | Q4_K_M | 45 GB | 180 GB | ✓ |
| **Qwen3-Coder-REAP-246B-A35B** | Q4_K_M | 138 GB | **552 GB** | ✓ (53% of 1.1 TB; tight, no co-resident large model) |
| gemma-4-26B-A4B-it | Q4_K_M | 16 GB | 64 GB | ✓ |

## Source: vproxy-tools/llama.cpp fork

Author: @wkgcass. Branch: `will-force-push`. Discussion: [ggml-org/llama.cpp #12289](https://github.com/ggml-org/llama.cpp/discussions/12289). Reference commit: [`9314286`](https://github.com/vproxy-tools/llama.cpp/commit/9314286) "a rough implementation of GGML_NUMA_MIRROR" (5 files, +217/−3). Their reported gains (+34% to +62%) were on 2-socket configurations.

## Disposition

**CLOSED** as decisive negative on this single-socket NPS4 hardware (MoE proxies tested; dense generalization measurement is the small remaining piece, deferred to remediation Phase 2.6). Production stack should NOT enable `GGML_NUMA_MIRROR`. The accessor migration (Phase 0a/0b/1a/1b) is preserved in the codebase as zero-overhead infrastructure (`tensor_data()` compiles to direct field access in default builds — pure no-op). The Phase 1c buffer-mirror code is preserved for any future hardware where fabric IS the binding constraint (2-socket EPYC, multi-package, GPU-CPU NUMA).

**Reopen only if** the deployment target shifts to a configuration with cross-SOCKET fabric (i.e., 2-socket EPYC), or if Phase 2.6 cross-architecture sanity finds an unexpected dense-only win.
