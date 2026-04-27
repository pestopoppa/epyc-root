# CPU Kernel Env-Flag Inventory — 2026-04-26

**Repo**: `/mnt/raid0/llm/llama.cpp-experimental` (`feature/cpu-ep-inter-process` HEAD `43c65b926`)
**Purpose**: classify every env-gated knob the experimental kernel has accumulated across CPU1, CPU2, CPU15 work, so Phase I (production-consolidated-v5 cherry-pick) knows what's safe to default-on, what stays default-off, and what should be stripped.

## Inventory at a glance

| Flag | Default | Class | File:line |
|------|---------|-------|-----------|
| `GGML_CCD_POOLS` | off | needs verification | ggml-cpu.c:3831 |
| `GGML_NUMA_WEIGHTS` | off | needs verification | llama-mmap.cpp:471, llama-model-loader.cpp:1548 |
| `GGML_CCD_WORK_DIST` | off | needs verification | ggml-cpu.c:1531, 3610 |
| `GGML_BARRIER_LOCAL_BETWEEN_OPS` | off | needs verification | ggml-cpu.c:3606 |
| `GGML_BARRIER_STRICT` | off | diagnostic | ggml-cpu.c:701 |
| `GGML_NUMA_WARMUP_CCD` | off | diagnostic | llama-model-loader.cpp:1555, 1665, 1766 |
| `GGML_NUMA_WARMUP_PHYS_PER_CCD` | off | diagnostic | llama-model-loader.cpp:1560 |
| `GGML_NUMA_WARMUP_MIN_BYTES` | off | diagnostic | llama-model-loader.cpp:1585 |
| `GGML_RMS_NORM_PARALLEL` | off | experimental (net-negative) | ops.cpp:3761 |
| `GGML_GDN_K_PER_HEAD` | off | experimental (no current effect) | ops.cpp:11062 |
| `GGML_EXPERT_CCD_SHARDING` | off | superseded | ggml-cpu.c:1986 |
| `GGML_Q8_0_8X8` | off | opt-in optimization | repack.cpp:4944 |
| `GGML_Q8_0_8X8_AVX` | off | opt-in optimization | arch/x86/repack.cpp:1550 |
| `GGML_Q6_K_8X8_AVX` | off | **production-ready opt-in (PPL bit-exact 32-chunk on Coder-30B + REAP-246B, 2026-04-28)** | arch/x86/repack.cpp:1789 |
| **`GGML_NUMA_REPACK_INTERLEAVE`** | **on** | **kill-switch (CPU2 mbind)** | repack.cpp:5024 |
| `GGML_NUMA_MIRROR` (compile flag, not env) | off (compile-time) | research/decisive-negative on single-socket NPS4 (CPU25) | ggml.h:733, repack.cpp guarded sections |
| `GGML_EP_ROLE` | off | EP control plane | ggml-ep-bootstrap.cpp:114 |
| `GGML_EP_N_INSTANCES` | off | EP control plane | ggml-ep-bootstrap.cpp:124 |
| `GGML_EP_NUMA_PIN` | off | EP control plane | ggml-ep-bootstrap.cpp:177 |
| `GGML_EP_MASTER_ALL_NODES` | off | EP control plane | ggml-ep-bootstrap.cpp:184 |
| `GGML_EP_SHARD` | off | EP feature | ggml-ep-shard.cpp:78 |
| `GGML_EP_WORKER_DRONE` | off | EP feature | ggml-cpu.c:1671, 2259 |
| `GGML_EP_MASTER_PARK` | off | EP feature | ggml-cpu.c:1688 |

**Behavior changes that activate on every multi-NUMA host (no model-level opt-in):**

- `repack.cpp` mbind(MPOL_INTERLEAVE) on every CPU_REPACK buffer ≥ 1 MiB. Introduced by `e84a5c82f` for the CPU2 AVX-512BW kernel; activates regardless of whether `GGML_Q8_0_8X8_AVX=1` is set. **Now gated by `GGML_NUMA_REPACK_INTERLEAVE` (default ON, set `=0` to disable)** so the behavior can be measured in isolation and rolled back per-deployment if needed.

## Detail per class

### CPU1 stack — per-flag classification after P3 isolation (2026-04-26)

**P3 (per-flag isolation on Coder-30B Q4_K_M and Qwen3.6-35B Q8_0)** revealed the instability is **exclusively `GGML_NUMA_WEIGHTS=1`**. The other 3 flags are safe individually and stable in combination.

| Flag | Coder-30B Q4_K_M | Qwen3.6-35B Q8_0 | Verdict |
|------|-------------------|-------------------|---------|
| canonical (none) | 43.37 ± 0.10 | 14.63 ± 0.01 | reference |
| `GGML_CCD_POOLS=1` only | 43.44 ± 0.06 | (small effect) | **safe, stable** |
| `GGML_NUMA_WEIGHTS=1` only | **20-33 ± 19-22** | **8-9 ± 4-5** | **UNSTABLE — DEPRECATED** |
| `GGML_CCD_WORK_DIST=1` only | 43.66 ± 0.18 | (small effect) | **safe, stable** |
| `GGML_BARRIER_LOCAL_BETWEEN_OPS=1` only | 43.88 ± 0.15 | (small effect) | **safe, stable** |
| 3-flag stack (no NW) | 44.15 ± 0.13 | 14.39 ± 0.03 | **+1.8% / parity, stable** |
| Full 4-flag stack (with NW) | 33-42 ± 13-18 | 8-12 ± 2-4 | **broken by NW** |

#### Sub-flag detail

- `GGML_CCD_POOLS=1` (ggml-cpu.c:3831): per-CCD threadpool partitioning. **Production-safe.**
- `GGML_NUMA_WEIGHTS=1` (llama-mmap.cpp:471, llama-model-loader.cpp:1548): originally process-wide `set_mempolicy(MPOL_INTERLEAVE)` before mmap. **Fixed 2026-04-26 in commit `8cb04da9d`** to use per-region `mbind()` (correct scope), but the underlying `MPOL_INTERLEAVE` mechanism remains unstable on shared file-cache multi-NUMA hosts. **DEPRECATED — do not enable in production.** Future work: replace with private anon mmap + custom file-load, or mlock+mbind+MOVE_PAGES for deterministic placement.
- `GGML_CCD_WORK_DIST=1` (ggml-cpu.c:1531, 3610): per-CCD expert work distribution. **Production-safe.**
- `GGML_BARRIER_LOCAL_BETWEEN_OPS=1` (ggml-cpu.c:3606): CCD-local 2-level barrier. **Production-safe.**

**Recommended CPU1 stack for production** (after P3): `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` (no NUMA_WEIGHTS). +1.8% on Coder-30B Q4_K_M, parity on Qwen3.6-35B Q8_0, **stable**. Default-OFF until v5 audit confirms PPL bit-identical on the full lineup.

### diagnostic (always-off, useful for debugging)

- `GGML_BARRIER_STRICT=1` — forces strict serialization on the barrier path. Used to rule out memory-ordering bugs.
- `GGML_NUMA_WARMUP_CCD=1` — explicit per-CCD warmup pass when loading a model. Useful for debugging the first-touch placement during MPOL_INTERLEAVE.
- `GGML_NUMA_WARMUP_PHYS_PER_CCD=N` — number of physical cores per CCD to use during warmup (tuning).
- `GGML_NUMA_WARMUP_MIN_BYTES=N` — minimum tensor size before per-CCD warmup applies.

Recommendation: keep default-off, document.

### experimental (default-off; falsified or net-negative)

- `GGML_RMS_NORM_PARALLEL=1` (ops.cpp:3761): parallel inner-axis reduction in rms_norm. Tested net-negative when default-on. Keep gated for future research; do not default-on.
- `GGML_GDN_K_PER_HEAD=N` (ops.cpp:11062): gated_delta_net K-axis sub-chunking. Tested net-zero (no current effect). Keep for future research.
- `GGML_EXPERT_CCD_SHARDING=1` (ggml-cpu.c:1986): CPU15 Phase 1 intra-process expert sharding. Superseded by Phase 3 inter-process EP. Strip in v5 OR keep gated default-off for fallback.

### opt-in optimization (CPU2)

- `GGML_Q8_0_8X8=1` (repack.cpp:4944): activate the 8x8 Q8_0 repack scaffold. Default-off because the kernel only wins on 1-thread workloads (+31.8%) and is BW-saturated at 12-96t (+1-3%). Production benefit is narrow.
- `GGML_Q8_0_8X8_AVX=1` (arch/x86/repack.cpp:1550): activate the AVX-512BW 8x8 GEMV kernel. Same default-off rationale.

### kill-switch (CPU2 mbind) — added 2026-04-26

- `GGML_NUMA_REPACK_INTERLEAVE=0` (repack.cpp:5024): disable the unconditional `mbind(MPOL_INTERLEAVE)` on CPU_REPACK buffers ≥ 1 MiB. **Default ON** for backward compatibility with the post-`e84a5c82f` behavior.

**Why default-on**: measured 2026-04-26 with kill-switch:

| Model | mbind ON (default) | mbind OFF | Δ |
|-------|--------------------|-----------|----|
| Qwen3.6-35B-A3B Q8_0 | **14.63 ± 0.01** | 13.76 ± 1.78 | mbind = **+6% AND stabilizing** |
| REAP-246B-A35B Q4_K_M | 6.85 ± 0.01 | 6.91 ± 0.01 | mbind = -0.9% (small loss on Q4_K_M) |

The mbind is a clear win on Q8_0 (the CPU2 target — both faster *and* much more stable) and a minor wash on Q4_K_M. Default ON is correct. Set `=0` only when (a) measuring the baseline impact of the mbind itself, (b) running an alternative NUMA strategy (per-CCD bind, replication), or (c) diagnosing a regression and need to rule the mbind out.

A startup `GGML_LOG_INFO` is emitted when `GGML_NUMA_REPACK_INTERLEAVE=0` is set, so the disabled state is visible in server logs without grepping the source.

**Q4_K_M Note**: Q4_K_M models use CPU_REPACK too (REAP-246B was observed with a 110 GB CPU_REPACK buffer at load), so the env var affects them — the kill-switch is not a Q8_0-only knob. Q4_K_M just doesn't see a perf benefit from the mbind.

### EP family (CPU15 Phase 3.2 inter-process)

All seven flags default-off. Together control inter-process Expert Parallelism:

- `GGML_EP_ROLE` ∈ `{master, worker}` — set automatically by ggml-ep-bootstrap; users typically don't set it.
- `GGML_EP_N_INSTANCES=N` — total number of EP instances (master + workers).
- `GGML_EP_NUMA_PIN=1` — pin each instance to its NUMA node (typically 1 instance per node on NPS4 = 4-way EP).
- `GGML_EP_MASTER_ALL_NODES=1` — master keeps full DRAM bandwidth (no NUMA pinning); workers pin to their node.
- `GGML_EP_SHARD=1` — each instance holds 1/N of expert weights (saves N× memory).
- `GGML_EP_WORKER_DRONE=1` — workers skip non-MoE ops; master broadcasts src1+ids only.
- `GGML_EP_MASTER_PARK=1` — master parker threads skip MoE expert loop to avoid oversubscription.

**Phase 3.2 (g.1) state**: PPL bit-identical on Qwen3.6-35B-A3B Q8_0 with N=2 drone+shard. +17% honest baseline (vs canonical no-flags). Other production models (Coder-30B, Next-80B, REAP-246B, gemma-4-26B-A4B-it) regress or are at parity.

**Recommendation**: cherry-pick all 7 flags into v5 default-off. Production routing wires them on for the frontdoor (Qwen3.6-35B-A3B) only, via orchestrator config (Phase L).

## Cherry-pick plan for v5 (refines plan Phase I)

### Definitely cherry-pick

- All CPU1 commits **(default-off, NOT default-on)**: `a64d27dee`, `218325a14`, `61b00eb53`, `4f7f8bac4`, `04abecd13`, `d922314cc`, `0ade7bd4d`, `69b4c3fa4`, `9407a167e`, `315f891b0`, `c24a6c801`, `acb1bbdd7`. Stack remains gated for opt-in research/future work.
- CPU2 AVX-512BW kernel `1d18efce3` (default-off via `GGML_Q8_0_8X8_AVX`).
- CPU15 EP family `aa6476ab0` → `43c65b926` (default-off via env vars).
- Diagnostic flags `GGML_BARRIER_STRICT`, `GGML_NUMA_WARMUP_*` (default-off).

### Build-time toolchain choices for v5 (NEW 2026-04-28 — CPU11 + CPU12, with LTO and libomp-BOLT extensions)

Build-time decisions are not env-flags; they are baked into the `llama-server` binary at compile time. As of 2026-04-28:

| Lever | Class | v5 cherry-pick | Coder-30B | Q8 frontdoor | REAP-246B | Dense 27B | Bundle |
|---|---|---|---|---|---|---|---|
| **clang-20 + libomp + `-march=znver5`** | runtime + codegen | **Universal** | +6.4% baseline | +0.8% | −0.8% | −1.7% (within noise) | `2026-04-28-cpu21-libomp-chunks/` + `2026-04-28-cpu-cross-architecture-sanity/` |
| **+ PGO** (`-fprofile-instr-use=merged.profdata`) | codegen | **Universal** | +3.2% | +6.6% | +1.3% | +2.4% | `2026-04-28-cpu11-pgo/` |
| **+ LTO** (`-DGGML_LTO=ON`) | codegen | **NOT cherry-picked** | −1.0% within noise | n/m | n/m | n/m | `2026-04-28-cpu12-bolt-libomp/` |
| **+ BOLT-libggml** (`llvm-bolt-20 -reorder-blocks=ext-tsp ...`) | layout | **Per-role only on Coder-30B** | +2.1% (60.54 t/s) | −1.2% | −0.1% | −0.9% | `2026-04-28-cpu12-bolt/` |
| **+ BOLT-libomp** (custom libomp from LLVM 20.1.8 src + `llvm-bolt-20`) | layout | **NOT cherry-picked** (inconclusive under noise) | no signal | n/m | n/m | n/m | `2026-04-28-cpu12-bolt-libomp/` |

Total compounded gain on Coder-30B Q4_K_M tg32 vs original gcc+libgomp+no-march `build/`: **+25.4% / 60.54 t/s** with the full clang+libomp+znver5+PGO+BOLT stack. PPL bit-exact at every step (chunk-12 final estimate 11.1146 ± 0.62405 unchanged through PGO and BOLT).

**v5 deployment recommendation**:
- **Default production binary**: clang + libomp + `-march=znver5` + PGO. Universal positive on all 4 model classes; PPL bit-exact; no runtime config changes.
- **Optional per-role binary**: PGO + BOLT for the dedicated Coder-30B-A3B-Instruct role. Adds +2.1% to 60.54 t/s ceiling. Do NOT use as universal binary (cross-model regressions).

Build environment additions (one-time):
- `apt install clang-20 libomp5-20 libclang-rt-20-dev llvm-20 linux-tools-common linux-tools-generic`
- ~30-min PGO profile-and-rebuild cycle; ~10-min BOLT collect-and-rewrite cycle per profile

### Cherry-pick with modification

- `e84a5c82f` (repack mbind): the unconditional mbind needs a kill-switch env var. Add `GGML_NUMA_REPACK_INTERLEAVE` (default ON for backward-compat with current behavior, but allow `=0` to disable). Phase H PPL gates verify correctness; if perf-neutral on the production lineup, leave default-on. If any regression observed, flip default-off.

### Skip (revert chain)

- `b2154f3f3`, `9ea5b40e8` (CPU1 op-fusion infra + Phase 2) — already reverted on the experimental branch by `138b26cd4`, `c34aac61b`. Skip the original commits AND their reverts; they cancel out.

### Skip (research-only, default-off)

- `ba1c23900` (gated_delta_net sub-chunking) — no current effect; not worth carrying.
- `0467a5c17` (rms_norm parallel) — net-negative; not worth carrying.

### Skip (superseded)

- CPU15 Phase 1+2 intra-process: `8d0428a97`, `c98c0123c`, `9ccb00245` — superseded by Phase 3.2 inter-process EP.

## Open questions for the audit gate

1. **Why is the CPU1 stack unstable today?** Hypotheses: (a) kernel page-allocator state under fragmentation, (b) interaction with CPU2 mbind, (c) interaction with new threadpool init paths from CPU15. Phase D's bottleneck profile may shed light.
2. **Is `e84a5c82f` mbind safe across architectures?** Q4_K_M models bypass CPU_REPACK, so they're unaffected. But what about K-quants on Zen 5 (Q5_K, Q6_K, Q8_0)? Need PPL gates.
3. **Should `GGML_EP_*` ever default-on?** Recommendation: never. Always opt-in via orchestrator deployment.mode.

## Cross-references

- Plan: `~/.claude/plans/glistening-toasting-snail.md`
- Companion: `handoffs/active/cpu-optimization-thesis-pause-2026-04-26.md`
- Phase B+C results: `progress/2026-04/2026-04-26.md` (commit `1fd9c2c`)
- CPU2 kernel handoff: `handoffs/active/cpu-shape-specialized-gemv-decode.md`
- CPU15 EP handoff: `handoffs/active/large-moe-expert-parallelism.md`
- CPU1 baseline analysis: memory `project_cpu1_phase13_v1.md`, `project_cpu1_software_levers_exhausted.md`
