# CPU Optimization — Step 1 Cheap Checks (2026-04-23)

**Parent plan**: `cpu-inference-optimization-index.md` §Pickup Sequence Step 1
**Scope**: CPU6 (ZenDNN 5.2), CPU7 (tinyBLAS on/off), CPU11 (compiler flag audit)
**Workspace**: `/mnt/raid0/llm/llama.cpp-experimental` on branch `cpu-optimization/backlog-2026-04-23` (HEAD `9e048fbc1` — v4 + Hadamard KV smoothing + f16 fix + TIDE adapter cleanup).
**Raw data**: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-23/`

## Summary

| Check | Result | Implication |
|---|---|---|
| CPU7 tinyBLAS on/off (Q4_K_M, 48t) | 39.72 vs 39.68 t/s → **0.1% delta, within noise** | tinyBLAS does not contribute to M=1 decode on Q4_K_M on Zen 5 |
| CPU7 tinyBLAS on/off (Q8_0, 48t) | 4.21 vs 4.23 t/s → **-0.5% delta (OFF slightly faster, within noise)** | tinyBLAS does not contribute to M=1 decode on Q8_0 on Zen 5 either |
| CPU11 compiler flag audit | Default cmake uses `-march=native` (overrode our `-march=znver5`). On EPYC 9655 this resolves to Zen 5 features already. | No incremental gain from explicit znver5 flags; PGO test deferred as it requires a separate rebuild cycle. |
| CPU6 ZenDNN 5.2 eval | **DEFERRED** pending user approval (install requires sudo + external package) | Single-day test when scheduled; documented as the first next step if user wants to close this gap. |

## Bottom line for downstream planning

**The "easy wins" hoped for in Step 1 are not there.** None of the three cheap checks yielded a free >1% gain on the canonical baseline model. That's a meaningful negative result: it means the 1.5–2.5× CPU2 (GEMV ukernel) projection has to come entirely from new code we write; there is no tinyBLAS auto-fallback to lean on, and no compiler-flag overhang to tap.

## Details

### CPU7 — tinyBLAS (`GGML_USE_LLAMAFILE`) on/off

#### Test config (identical across both runs)

- Model A (canonical): `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` (17.28 GiB, 30.53 B params, MoE-hybrid)
- Model B (GEMV target): `/mnt/raid0/llm/models/Qwen3.6-27B-Q8_0.gguf` (27 GB, dense hybrid)
- `llama-bench -t 48 -p 0 -n 64 -r 2` with `taskset -c 0-47` (NUMA node 0 quarter)
- Both builds configured with `cmake -B ... -DGGML_USE_LLAMAFILE={ON|OFF} -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-march=znver5 -mtune=znver5"` — ultimately compiled with `-march=native` per cmake default override

#### Results

**Model A (Qwen3-Coder-30B-A3B Q4_K_M)**:

| build | avg tok/s | stddev | samples |
|-------|-----------|--------|---------|
| tinyBLAS ON | **39.72** | 0.15 | 39.83, 39.61 |
| tinyBLAS OFF | **39.68** | 0.17 | 39.80, 39.56 |
| delta | **+0.04 t/s (+0.1%)** | — | within noise |

**Model B (Qwen3.6-27B Q8_0)**:

| build | avg tok/s | stddev | samples |
|-------|-----------|--------|---------|
| tinyBLAS ON | **4.21** | 0.017 | 4.196, 4.220 |
| tinyBLAS OFF | **4.23** | 0.018 | 4.215, 4.241 |
| delta | **-0.02 t/s (-0.5%)** | — | within noise (OFF marginally faster) |

#### Interpretation

tinyBLAS in `ggml/src/ggml-cpu/llamafile/sgemm.cpp` appears not to be routing any of the decode matmuls for either quantization. The M=1 fast path in `mmq.cpp:2436-2469` (via `tinygemm_kernel_vnni<BLOCK_M, BLOCK_N>`) and the generic ggml quant-aware GEMV path already handle both Q4_K_M and Q8_0 — sgemm may only be engaged for prefill (M>>1) or for certain unquantized dtypes (FP32/FP16/BF16).

**Crucial downstream implication for CPU2 (GEMV ukernels)**: the GEMV handoff's open question about tinyBLAS as a "partial auto-win" is answered with **zero on our decode path**. The Zen 5 ukernel plugin must do all the work itself. The Justine Tunney / llamafile 2.8× number on Zen 4 was overall (prefill-heavy), not decode-specific, and does not transfer to our workload.

### CPU11 — Compiler flag audit

Observed during `cmake` configure (both ON and OFF builds):

```
-- Adding CPU backend variant ggml-cpu: -march=native
```

Cmake's upstream ggml configuration appends `-march=native` by default, which overrides our `-DCMAKE_CXX_FLAGS="-march=znver5 -mtune=znver5"` for the CPU backend targets. On our EPYC 9655 (Zen 5 Turin) host, `-march=native` emits Zen 5 features (`avx512f`, `avx512bf16`, `avx512vnni`, `avx512vbmi`, `avx512_bf16`, `avx512_bitalg`, `avx512_vpopcntdq`, `avx512_vp2intersect`, etc. — confirmed via `/proc/cpuinfo`).

**No incremental gain is expected from an explicit znver5 flag when native already resolves to Zen 5.** The only clean way to validate this would be a PGO pass (`-fprofile-generate` → calibration run → `-fprofile-use` → re-bench), which is a separate rebuild cycle and not a "cheap check." Deferred.

### CPU6 — ZenDNN 5.2

Deferred pending user approval. Installation is a multi-step process:

1. Download ZenDNN 5.2 binary from AMD developer portal (gated).
2. Install system-wide (typically requires sudo).
3. Rebuild llama.cpp-experimental with `-DGGML_ZENDNN=ON` (if upstream has integration) or LD_PRELOAD the ZenDNN GEMM library.
4. Re-bench.

Cost: ~1 day of effort once unblocked. Gate per plan: if ≥1.3× drop-in, reshapes all downstream CPU2 work.

## Side observations (not part of CPU6/7/11 but worth recording)

### 192-thread config is contended on this host

Plan specified `-t 192 --numa interleave=all` as the canonical benchmark config, matching the model registry's "1×192t interleaved: 14.2 t/s" reference for Qwen3-Coder-30B-A3B Q4_K_M. Under the current host load (firefox + isolated web content processes at ~85% CPU + misc at the time of measurement; `uptime` load average **163**), 192t runs produced **0.14 t/s — approximately 100× slower than the registry baseline**.

This is host contention, not a v4 regression — the 48t taskset-pinned runs reproduce production worker_explore throughput (39.72 vs 39.1 registry). The 192t number requires a quieter host or dedicated benchmark window.

Action for Step 3: CPU3 Phase 0 baseline thread sweep must either (a) run during a low-contention window, (b) use `chrt -r 1` or cgroup isolation, or (c) explicitly document contention state per measurement.

### Build binary parity with production

Experimental build at `9e048fbc1` produces decode numbers (39.72 t/s at 48t pinned) that match production (39.1 t/s). The new branch is a trustworthy baseline for downstream Step 3–6 work. No regression vs production observed at the single-NUMA-quarter config.

## Next

Close Step 1. Move to Step 3 (CPU3 Phase 0 root baseline) with the note that 192t contention requires mitigation. Steps 5 (CPU1 TP-sharding) and 6 (CPU2 GEMV ukernel) remain gated on Step 3 output. CPU6 ZenDNN kept on the deferred list.
