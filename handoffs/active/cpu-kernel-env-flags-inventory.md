# CPU Kernel Env-Flag Inventory — 2026-04-26 (updated 2026-04-30)

**Repo**: `/mnt/raid0/llm/llama.cpp-experimental` (`feature/cpu-ep-inter-process` HEAD `aed8c1e` post-2026-04-30 wrap-up; experimental branch HEAD `d45126db5` includes Phase 1.1 dispatcher v1)
**Purpose**: classify every env-gated knob the experimental kernel has accumulated across CPU1, CPU2, CPU15, slot-promotion work, so Phase I (production-consolidated-v5 cherry-pick) knows what's safe to default-on, what stays default-off, and what should be stripped.

---

## ⚑ CANONICAL PREREQUISITES (read before any env-flag is interpreted)

**Every recommendation in this document assumes the FULL canonical recipe is applied.** These are NOT per-knob opt-ins — they are the baseline runtime context that makes any other measurement meaningful. Without them, post-reboot inference is 3-4× degraded with high variance and ANY env-flag comparison below is poisoned.

```bash
# Mandatory env (lost on every reboot — re-apply per session)
sudo sysctl kernel.numa_balancing=0
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo always | sudo tee /sys/kernel/mm/transparent_hugepage/defrag

# Mandatory bench/server invocation prefix
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all -- taskset -c 0-95 \
  llama-bench -t 96 -fa 1 --mmap 0 [...]
```

**Why each piece is mandatory:**

| Knob | What breaks without it |
|---|---|
| `OMP_PROC_BIND=spread` | libomp threads cluster on a few cores or migrate; freq oscillation; barrier latency explodes |
| `OMP_PLACES=cores` | threads bind to logical CPUs (SMT siblings) instead of physical cores → 2 threads per core fight for execution units |
| `OMP_WAIT_POLICY=active` | threads sleep at OMP barriers → amd-pstate-epp demotes freq → re-wake latency on next op kills throughput. **Without this alone**: Coder-30B Q4_K_M post-reboot drops 17 → 48.8 t/s |
| `numactl --interleave=all` | `--mmap 0` reads model into one node's memory (first-touch by main thread). 96 threads then hammer 1 NUMA node's 3 DRAM channels (~85 GB/s peak under NPS4) instead of 4 nodes' 12 channels |
| `--mmap 0` | mmap=1 page-faults during decode on cold model memory; freq driver demotes during stalls. Confirmed ~3× slower than `--mmap 0` post-reboot. Note: `OMP_WAIT_POLICY=passive` is a deployment trap (-81.6% Coder-30B at 96 threads). |
| `numa_balancing=0` | kernel migrates pages mid-decode based on access patterns, thrashing under heavy multi-thread workload. Self-resets to default on each reboot — verify with `cat /proc/sys/kernel/numa_balancing` per session, do not trust the sysctl.d file. |
| `THP=always` (both `enabled` + `defrag`) | madvise mode (default) leaves model on 4 KB pages → TLB misses dominate → throughput tanks |

**Discovery context (2026-04-29)**: a post-reboot session showed apparent 3-4× regression vs warmed canonical 58.65 t/s. ~30 min were spent diagnosing thermal throttle / hardware degradation before identifying that the OMP env stack had been omitted. The canonical baseline-protocol memory documented this recipe; the inventory now reflects it as a hard prerequisite. Memory: `feedback_omp_env_stack_required.md`, `feedback_canonical_baseline_protocol.md`. Bundle: `data/cpu_optimization/2026-04-29-post-reboot-tripwire/`.

**Cold-boot canonical reference** (taskset -c 0-95 -t 96 -fa 1 --mmap 0 + OMP env + interleave=all):
- Coder-30B Q4_K_M tg32: ~47-49 t/s (canonical recovery; 58.65 reference is warmed-state after hours-to-days of uptime)
- Qwen3.6-35B Q8 tg32: ~23 t/s
- REAP-246B Q4 tg32: ~6.3 t/s

---

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
| `LLAMA_ARG_SPEC_NUMA_QUARTERS` (CLI: `--spec-numa-quarters K`) | 1 (off) | **closed via test 2026-04-30 — mechanism net-negative on Qwen3.6-35B + Qwen3-1.7B drafter; dispatcher v1 in tree disabled-by-default** | common/arg.cpp + tools/server/server-context.cpp |
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

## Per-Arch Deployment Matrix (2026-04-29/30 measurements)

> **Authoritative table** for "what env should I set for arch X?" Read by the v5 push agent when populating per-role config in `model_registry.yaml`. All measurements under FULL CANONICAL recipe (see Canonical Prerequisites section above) — adding any of the per-arch knobs below ON TOP of the canonical baseline.

Configs reference (env stack relative to canonical baseline):
- **c0** = canonical baseline (no extra env)
- **c1** = `GGML_CCD_POOLS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1` (CPU1 stack)
- **c2** = `GGML_NUMA_REPACK_INTERLEAVE=0` (kill auto-mbind)
- **c3** = c1 + c2 combined

| Arch class | Production model | Best config (decode) | Best config (prefill) | Notes | Source bundle |
|---|---|---|---|---|---|
| **MoE Q4_K_M (sync-bound)** | Coder-30B-A3B | c1 (CPU1 stack) +1.8% | not tested | CPU21 finding 2026-04-26; +1.8% on tg32. CPU22 work-stealing gate FAILED (-2.3%). | `2026-04-28-cpu21-libomp-chunks/` |
| **MoE Q4_K_M (DRAM-bound)** | REAP-246B-A35B | default v5 (no opt-in) | not tested | DRAM-saturated; CPU2 AVX-512BW Q6_K at +6% pp32 if quantized; CPU22 -0.8% (noise) | `2026-04-28-cpu22-work-stealing/` |
| **MoE Q8_0 (BW-bound frontdoor)** | Qwen3.6-35B-A3B | EP stack (per orchestrator wiring) | not tested | EP +17% honest baseline (g.1 = drone+shard, N=2); CPU22 -0.3% (noise) | `2026-04-26-asymmetry/` + EP bundles |
| **Hybrid SSM (dense, Mamba2+attn)** | Nemotron-9B-v2 | c2 (mbind off) +1.78% | **c3 +8.9% pp512** / +3.7% pp2048 | Strongest robust signal in re-validation campaign. **Worth opt-in for prefill-heavy workload.** | `2026-04-29-multi-arch-coverage-canonical/` + `2026-04-29-workload-shape-canonical/` |
| **Hybrid SSM (MoE)** | Qwen3-Next-80B-A3B | default v5 (no opt-in) | c3 +1.7% pp512 (within noise floor) | MoE structure (`mul_mat_id` per-token-varying expert subset) defeats CPU1's CCD-aware partitioning; +8.9% on Nemotron does NOT generalize | `2026-04-30-hybrid-ssm-next80b-followup/` |
| **Dense Q8** | Qwen3.6-27B Q8 | default v5 (CPU1 actively HURTS) | default v5 | All probed configs negative: c1=-4.7%, c2=-3.3%, c3=-1.6%. Do NOT enable CPU1 or mbind-off. | `2026-04-29-multi-arch-coverage-canonical/` |
| **Dense Q4_K_M** | gemma-4-31B Q4_K_M | default v5 (within noise) | default v5 | All probed configs within ±2% under tight Probe B measurement; "+3.9% c2" from multi-arch n=15 was baseline-drift artifact (gemma c0 std 6.4% CV) | `2026-04-29-multi-arch-coverage-canonical/` + `2026-04-29-workload-shape-canonical/` |

### Per-role v5 deployment recommendation (read by push-rebase agent)

When v5 ships and `model_registry.yaml` is updated, populate per-role env as follows:

```yaml
# Sketch — not yet committed to model_registry until v5 lands
roles:
  coder_explore:        # Coder-30B-A3B Q4_K_M
    binary_path: build_libomp_pgo_bolt/  # per-role BOLT (CPU12)
    env:
      GGML_CCD_POOLS: 1
      GGML_CCD_WORK_DIST: 1
      GGML_BARRIER_LOCAL_BETWEEN_OPS: 1
  frontdoor:            # Qwen3.6-35B-A3B Q8_0
    binary_path: build_libomp_pgo_use/   # universal PGO
    env:
      GGML_EP_N_INSTANCES: 2
      GGML_EP_NUMA_PIN: 1
      GGML_EP_MASTER_ALL_NODES: 1
      GGML_EP_WORKER_DRONE: 1
      GGML_EP_SHARD: 1
  architect_coding:     # REAP-246B-A35B Q4_K_M
    binary_path: build_libomp_pgo_use/
    moe_spec_budget: 40             # MoE-Spec validated for REAP at +13-16% pp32
  hybrid_dense_ssm:     # Nemotron-9B-v2 (if added to roster)
    binary_path: build_libomp_pgo_use/
    env:
      GGML_CCD_POOLS: 1
      GGML_CCD_WORK_DIST: 1
      GGML_BARRIER_LOCAL_BETWEEN_OPS: 1
      GGML_NUMA_REPACK_INTERLEAVE: 0  # mbind off
  # NO opt-in env for: Qwen3-Next-80B-A3B, Qwen3.6-27B Q8, gemma-31B Q4
  # All three perform best (or tie) at default v5 stack.
```

**ALL roles inherit the canonical prerequisites** (OMP env stack + numa_balancing=0 + THP=always + numactl --interleave=all + --mmap 0). Those are NOT per-role — they're host-level prereqs that orchestrator_stack.py must enforce on every llama-server launch.

**Status of the model_registry update**: **KERNEL PUSHED** — `production-consolidated-v5` tip `23bcd6aaf` pushed to GitHub on 2026-04-30. Production PGO and BOLT binaries built in `/mnt/raid0/llm/llama.cpp/` (see below). Model registry wiring (`binary_path` + env) is the next step; blocked on orchestrator-stack integration (not yet started). The push-rebase handoff (`llama-cpp-kernel-push-rebase.md`) will drive that phase.

**PGO/BOLT binary locations** (built 2026-04-30, `/mnt/raid0/llm/llama.cpp/`):

| Directory | Role | Key artifact |
|---|---|---|
| `build_libomp_pgo_use/` | Universal PGO — all roles except Coder-30B | `bin/llama-server`, `bin/libggml-cpu.so.0.9.11` |
| `build_libomp_pgo_bolt/bin_bolted/libggml-cpu.so.0.bolt` | Coder-30B per-role BOLT | Drop-in replacement for `libggml-cpu.so.0.9.11`; apply via `LD_PRELOAD` at launch |

---

## Cherry-pick plan for v5 (refines plan Phase I)

### Status of whitelisted tracks (2026-04-30 wrap-up)

Production-push readiness across the whitelisted experimental kernel work, ranked by status:

| Track | Whitelist status | Latest measurement | Production posture for v5 |
|---|---|---|---|
| **CPU1 stack (CCD_POOLS, CCD_WORK_DIST, BARRIER_LOCAL_BETWEEN_OPS)** | ✅ whitelisted (default-off) | +1.8% Coder-30B Q4_K_M; parity Q8 (P3 isolation 2026-04-26) | Cherry-pick all 12 commits gated default-off; NUMA_WEIGHTS DEPRECATED separately |
| **CPU2 AVX-512BW Q8_0 8x8 kernel** | ✅ whitelisted opt-in | +31.8% @ 1t; +1-3% @ 12-96t (BW-saturated) | Cherry-pick `1d18efce3` default-off via `GGML_Q8_0_8X8_AVX` |
| **CPU2 AVX-512BW Q6_K 8x8 kernel** | ✅ whitelisted opt-in | PPL bit-exact 32-chunk on Coder-30B + REAP-246B (2026-04-28) | Cherry-pick default-off via `GGML_Q6_K_8X8_AVX`; production-ready when activated |
| **CPU2 NUMA_REPACK_INTERLEAVE auto-mbind** | ✅ whitelisted **default-on** with kill-switch | +6% AND stabilizing on Q8; -0.9% on Q4_K_M (kill-switch isolation 2026-04-26) | Cherry-pick `e84a5c82f` modified to add `GGML_NUMA_REPACK_INTERLEAVE=0` kill-switch |
| **CPU15 inter-process EP (7 flags)** | ✅ whitelisted (default-off, orchestrator-wired for frontdoor) | Qwen3.6-35B-A3B Q8 +17% honest baseline (g.1 = drone+shard, N=2); REAP-246B regresses (-53%) | Cherry-pick `aa6476ab0` → `43c65b926`; production routing wires on for frontdoor only |
| **CPU11 PGO** (clang-20+libomp+znver5+PGO) | ✅ whitelisted **universal** | +1.3-6.6% across all 4 production model classes; PPL bit-exact | Default v5 production binary toolchain |
| **CPU12 BOLT-libggml** | ✅ whitelisted **per-role only** (Coder-30B) | +2.1% Coder-30B (60.54 t/s); -0.9 to -1.2% on Q8/dense | Per-role opt-in binary for Coder-30B-A3B-Instruct |
| **CPU12 BOLT-libomp** | ❌ NOT whitelisted (inconclusive under noise) | PPL bit-exact pipeline works; no throughput signal | Skip; reopen if noise floor improves |
| **CPU11 LTO** (`-DGGML_LTO=ON`) | ❌ NOT whitelisted | -1.0% within noise on Coder | Skip |
| **MoE-Spec verification budget (REAP=40)** | ✅ whitelisted (per-role opt-in) | REAP-246B B=40 +13-16% pp32 / +3% end-to-end (robust); Coder=NOT deployable (varies wildly) | Per-role registry integration RELEASED 2026-04-30 (slot-promotion gate cleared); MAB selector Phase 0 still pending for full release |
| **MAB tree-shape selector** | ⚠️ Phase 1 prototype not yet started | Phase 0 verdict written (intake-491 §3.2) | Drop-in over heap-spec for pure-MoE targets; pre-prod gate still blocks production push |
| **Slot-promotion dispatcher v1 (`--spec-numa-quarters K`)** | ❌ **NOT whitelisted; closed via test 2026-04-30** — mechanism net-negative on Qwen3.6-35B + Qwen3-1.7B (engaged 62× across sweep but primary won 60/62 = 97%; aux wins delivered just +1 marginal token; K=4=7.42 t/s vs K=1=11.40 t/s on canonical 3×2) | n/a | Stays in tree disabled-by-default; do NOT enable for production on this drafter/target pair; re-evaluate if drafter or target changes (handoff in `completed/`) |
| **CPU22 dynamic MoE load-balancing** | ❌ closed via test 2026-04-28 (gate FAILED) | -2.3% Coder, -0.3% Next-80B, -0.8% REAP at 5-rep proper canonical (verified 2026-04-29 evening Phase D under canonical: -0.89% Coder, +0.18% Next, -0.32% REAP — closure stands) | Skip global-tile-queue design; reopen criteria documented (token-to-expert rebalance + hybrid static+dynamic spillover designs untested) |
| **CPU4 op-coalesced barriers** | ❌ closed via test 2026-04-29 (gate not met) | Original "−19.7% Coder" was POISONED by missing OMP env baseline. Phase A re-test 2026-04-29 evening under canonical: **+0.19% NEUTRAL** on Coder. Patch is harmless, not regressive — gate ≥+5% still not met. MUL_MAT wdata race finding stands (correctness). | Stays in tree env-gated default-OFF (`GGML_BARRIER_COALESCE`). Allowlist excludes MUL_MAT/MUL_MAT_ID. Future work: extend allowlist beyond conservative set. |
| **CPU25 NUMA_MIRROR** | ❌ closed via test 2026-04-27 (DECISIVE NEGATIVE on single-socket NPS4) | -1.0% Coder, +0.6% Q8 (Phase 2 throughput gate) | Compile flag default-OFF; reopen ONLY for 2-socket configs |

**v5 cherry-pick scope summary (reconciled 2026-04-30 audit Phase 0)**: 8 CPU1 commits (KEEP) + 5 CPU1 commits STRIPPED with NUMA_WEIGHTS deletion; 1 CPU2 mbind kill-switch (already includes kill-switch — no modification); 2 CPU2 Q8_0 ukernel commits; 3 CPU2 Q6_K ukernel commits; 13 CPU15 EP family commits; 6 slot-promotion commits; 1 MoE-Spec budget commit; 1 CPU4 op-coalesced barriers commit. **Total KEEP = 35 commits**. Plus build-system commit (toolchain switch to clang-20+libomp+znver5+PGO) appended last. STRIPPED in addition to NUMA_WEIGHTS family: CPU22 work-stealing (`0bc793637`), rms_norm parallel (`383ec7345`), gated_delta_net (`c36e6ce3a`), CPU15 Phase 1+2 superseded (`ad97bef09`,`80b5da0e5`,`b0c0b3301`). All KEEP commits land default-off except `GGML_NUMA_REPACK_INTERLEAVE` (default-on with kill-switch). See "Cherry-pick scope — reconciled 2026-04-30" section below for full per-commit table.

### Cherry-pick scope — reconciled 2026-04-30 (v5 audit Phase 0)

**Reconciliation note**: the SHA list previously in this section was from a pre-rebase history snapshot and did not match the current `feature/cpu-ep-inter-process` branch. Below are the **verified current SHAs** present in `production-consolidated-v4..feature/cpu-ep-inter-process` (55 commits total, of which 4 are op-fusion + reverts that cancel out).

#### KEEP (cherry-pick into v5 in this dependency order)

**CPU1 stack** (gated default-off via `GGML_CCD_POOLS`, `GGML_CCD_WORK_DIST`, `GGML_BARRIER_LOCAL_BETWEEN_OPS`):

| Order | SHA | Description |
|---|---|---|
| 1 | `ea12c016b` | CPU1 P1.0+1.1: per-CCD 2-level barrier + CCD-aware cpumask |
| 2 | `dc99062fd` | CPU1 fix: CCD pinning respects process cpuset (was hanging under taskset) |
| 3 | `bcaa9f3cf` | CPU1 fix: tighten cpuset validation for CCD pinning |
| 4 | `06571e884` | CPU1 Lever A: ggml_barrier memory-order tightening |
| 5 | `4f07d701b` | CPU1 Lever B v1: CCD-local between-op barrier (env-gated) |
| 6 | `abc6c651f` | CPU1 Lever B revert: PPL-corrupting graph-level downgrade undone (keep cpuset fix) |
| 7 | `03a1c34f4` | CPU1 Phase 1.4 attempt complete: graph-level Lever B ruled out as unsafe |
| 8 | `40aa61a6a` | CPU1 Phase 1.4: axis-0-aligned element-wise ops + safe CCD-local barrier |

(8 commits — note the inventory's previous "12" overcounted by including 4 op-fusion + reverts that cancel.)

**CPU2 mbind kill-switch** (default-ON with `GGML_NUMA_REPACK_INTERLEAVE=0` to disable):

| Order | SHA | Description |
|---|---|---|
| 9 | `cb046ff58` | CPU2 kill-switch: GGML_NUMA_REPACK_INTERLEAVE=0 disables CPU_REPACK mbind |

(Replaces the prior `e84a5c82f` reference which was the pre-rebase SHA. The kill-switch is already in this commit; no further modification needed.)

**CPU2 Q8_0 8x8 AVX-512BW ukernel** (default-off via `GGML_Q8_0_8X8` + `GGML_Q8_0_8X8_AVX`):

| Order | SHA | Description |
|---|---|---|
| 10 | `1f8868307` | CPU2 Session 15: AVX-512BW 8x8 Q8_0 GEMV kernel |
| 11 | `af6701d00` | CPU2 Session 15 follow-up: NUMA interleave of CPU_REPACK + K-parallel activation quant |

(Replaces the prior `1d18efce3` reference. Both `GGML_Q8_0_8X8` (gateway) and `GGML_Q8_0_8X8_AVX` (SIMD path) flags are kept — they are at different layers, NOT redundant. See repack.cpp:5031 + arch/x86/repack.cpp:1550.)

**CPU2 Q6_K 8x8 AVX-512BW ukernel** (default-off via `GGML_Q6_K_8X8_AVX`):

| Order | SHA | Description |
|---|---|---|
| 12 | `a822d76b1` | CPU2 Session 16: Q6_K 8x8 AVX-512BW dispatcher scaffolding |
| 13 | `8d27e555f` | CPU2 Session 17: Q6_K 8x8 AVX-512BW SIMD body (PPL bit-exact 32-chunk on Coder-30B + REAP-246B) |
| 14 | `ba84ca407` | CPU2 Session 18: Q6_K T1 prefetch (+0.7%) |

**CPU15 inter-process EP family** (default-off via 7 env flags; orchestrator wires on for frontdoor only):

| Order | SHA | Description |
|---|---|---|
| 15 | `2e6709e66` | CPU15 P3.2(a): import ep_dispatcher into ggml-cpu |
| 16 | `486f8dbb2` | CPU15 P3.2(b+c): env-var-driven master/worker fork at ggml_cpu_init |
| 17 | `1e4524165` | CPU15 P3.2(d.0): wire IPC harness around ggml_compute_forward_mul_mat_id |
| 18 | `e86029a4d` | CPU15 P3.2(d.1.a): workers exit passive loop, sync in mul_mat_id |
| 19 | `9985bda65` | CPU15 P3.2(d.1.b): expert slicing + gather + sum-reduce + broadcast |
| 20 | `b424213cc` | CPU15 P3.2(d.1.c): NUMA-pin EP instances, one per node |
| 21 | `0ba338313` | CPU15 P3.2(e.0): worker drone mode — skip non-MoE ops, broadcast src1+ids |
| 22 | `ab622e898` | CPU15 P3.2(e.2): multi-node NUMA pinning per EP instance |
| 23 | `90b243198` | CPU15 P3.2(e.1) attempt: critical OPENMP-guard fix + shard manager |
| 24 | `b1248227d` | CPU15 P3.2(e.1) FIXED: move EP top block before src1 quantization |
| 25 | `93f97079e` | CPU15 P3.2(g.0): GGML_EP_MASTER_ALL_NODES — master keeps full bandwidth |
| 26 | `881f69681` | CPU15 P3.2(h): master phase-aware threading (env-gated) |
| 27 | `48650c5a8` | CPU15 P3.2(g.1): eager parallel shard warm-up |

(Replaces the prior `aa6476ab0` → `43c65b926` range which was pre-rebase.)

**CPU1 P1.3 fix** (per-region mbind correctness fix that landed AFTER the rest of the CPU1 stack — but since `GGML_NUMA_WEIGHTS` is being STRIPPED in v5 audit Phase 1, this commit is also dropped):

| ~~Order~~ | SHA | Description | Disposition |
|---|---|---|---|
| — | `ed77d5220` | CPU1 P1.3 fix: per-region mbind instead of process-wide set_mempolicy | **STRIPPED with NUMA_WEIGHTS code path** |

**Slot-promotion dispatcher** (default-off via CLI `--spec-numa-quarters K=1`):

| Order | SHA | Description |
|---|---|---|
| 28 | `a5c48050c` | slot-promotion P1.1 foundation: --spec-numa-quarters K + K target ctxs |
| 29 | `d056c1f20` | slot-promotion P1.1 foundation v3: CLI-surface-only after hybrid crash |
| 30 | `830c98c61` | slot-promotion P1.1: fix both blockers — foundation v4 active on hybrid |
| 31 | `3656223eb` | slot-promotion P1.1 foundation v5: K aux contexts active on hybrid |
| 32 | `64df7284b` | slot-promotion P1.1 dispatcher v0: pass-through wiring + state sync helper |
| 33 | `d45126db5` | slot-promotion P1.1 dispatcher v1: K-parallel verify functional, gate not met |

**MoE-Spec verification budget** (default-off via CLI `--moe-spec-budget`):

| Order | SHA | Description |
|---|---|---|
| 34 | `9db284ed7` | MoE-Spec (arXiv:2602.16052): per-batch top-B expert budget at MoE routing |

**CPU4 op-coalesced barriers** (default-off via `GGML_BARRIER_COALESCE`; allowlist excludes MUL_MAT/MUL_MAT_ID):

| Order | SHA | Description |
|---|---|---|
| 35 | `9f6191581` | CPU4 op-coalesced barriers (GGML_BARRIER_COALESCE) — gate not met but harmless |

**Diagnostic flags** (default-off): `GGML_BARRIER_STRICT`, `GGML_NUMA_WARMUP_CCD`, `GGML_NUMA_WARMUP_PHYS_PER_CCD`, `GGML_NUMA_WARMUP_MIN_BYTES`. These are part of the CPU1 commits above (no separate commits).

#### STRIP (delete code path entirely; do NOT cherry-pick)

| SHA | Description | Reason |
|---|---|---|
| `ed77d5220` | CPU1 P1.3 fix: per-region mbind | Underlying mechanism is `GGML_NUMA_WEIGHTS` — DEPRECATED unstable |
| `1fcc16d39` | CPU1 Lever A': per-NUMA-node weight replication (env-gated) | Same NUMA_WEIGHTS family — deprecated |
| `6efe765f9` | CPU1 P1.3 v2: per-CCD warmup touch pass | Same NUMA_WEIGHTS family — deprecated |
| `88d3d6dc5` | CPU1 P1.2 + P1.3 'local' mode scaffolding | Same NUMA_WEIGHTS family — deprecated |
| `e249ed5f1` | CPU1 P1.3 v1: set_mempolicy(MPOL_INTERLEAVE) | Original NUMA_WEIGHTS commit — deprecated |
| `383ec7345` | rms_norm: env-gated parallel inner-axis reduction | Net-negative, no reopen path |
| `c36e6ce3a` | gated_delta_net: env-gated S_v sub-chunking | "No current effect" |
| `ad97bef09` | CPU15 Phase 1a: per-CCD expert sharding work distribution | Superseded by Phase 3.2 inter-process EP |
| `80b5da0e5` | CPU15 Phase 1b: per-expert mbind to CCD-local NUMA node | Superseded by Phase 3.2 |
| `b0c0b3301` | CPU15 Phase 2: anonymous-mmap'd expert NUMA copies + mul_mat_id redirect | Superseded by Phase 3.2 |
| `0bc793637` | CPU22 work-stealing prototype | Closure-via-test failed (Phase D 2026-04-29 verified -0.89% Coder, +0.18% Next, -0.32% REAP under canonical) |

#### SKIP (revert chain — cancels out, do not carry)

| Pair | Description |
|---|---|
| `b980f1585` + `e104502f3` | CPU1 op-fusion infrastructure + revert |
| `bfd46e795` + `cd767ceb5` | CPU1 op-fusion Phase 2 + revert |

#### SKIP (closed via test 2026-04-27, decisive negative on single-socket NPS4)

| SHA | Description |
|---|---|
| `5becfd9ca` | NUMA_MIRROR Phase 0a: tensor_data() accessor + 97-ref migration |
| `b1baa6862` | NUMA_MIRROR Phase 0b: extend accessor migration to backend + loader |
| `61d2dedae` | NUMA_MIRROR Phase 1a: per-node pointer plumbing + TLS framework |
| `46733d078` | NUMA_MIRROR Phase 1b: TLS setter at graph-compute entry |
| `b7e0250f4` | NUMA_MIRROR Phase 1c: CPU_REPACK buffer mirror — DECISIVE NEGATIVE |

(Reopen criteria: 2-socket configs only. See `project_numa_mirror_scoped.md` memory.)

#### Cherry-pick total

**35 KEEP commits** + 11 STRIP (path deleted, not cherry-picked) + 4 op-fusion canceling + 5 NUMA_MIRROR skipped = **55** matches `production-consolidated-v4..feature/cpu-ep-inter-process` ✓

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

### Pre-rebase SHA → reconciled SHA mapping (for archival readers of older docs)

| Inventory's pre-rebase SHA | Reconciled current SHA(s) | Track |
|---|---|---|
| 12 CPU1 (`a64d27dee`…`acb1bbdd7`) | 8 KEEP + 5 STRIP listed above | CPU1 stack |
| `1d18efce3` | `1f8868307` + `af6701d00` | CPU2 Q8_0 8x8 ukernel |
| `e84a5c82f` | `cb046ff58` | CPU2 mbind kill-switch (already includes the kill-switch — no separate "modify" step needed) |
| `aa6476ab0` → `43c65b926` | `2e6709e66` … `48650c5a8` (13 commits) | CPU15 inter-process EP |
| `8d0428a97`, `c98c0123c`, `9ccb00245` | `ad97bef09`, `80b5da0e5`, `b0c0b3301` | CPU15 Phase 1+2 (STRIP) |
| `b2154f3f3` + `138b26cd4` revert; `9ea5b40e8` + `c34aac61b` revert | `b980f1585` + `e104502f3` revert; `bfd46e795` + `cd767ceb5` revert | CPU1 op-fusion (canceling) |
| `0467a5c17` | `383ec7345` | rms_norm parallel (STRIP) |
| `ba1c23900` | `c36e6ce3a` | gated_delta_net sub-chunking (STRIP) |

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
