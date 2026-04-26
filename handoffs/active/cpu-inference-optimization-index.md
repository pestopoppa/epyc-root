# CPU Inference Optimization — Unimplemented Performance Backlog

**Purpose**: Single discovery point for ALL remaining unimplemented CPU decode/prefill throughput techniques on our EPYC 9655 Turin hardware. Techniques that are deployed or concluded-not-viable live elsewhere (see `inference-acceleration-index.md`). This index is the **forward-looking backlog** — every lever that could still add single-instance or aggregate throughput and has not been either shipped or ruled out.

**Scope boundary**: CPU decode/prefill throughput on local EPYC 9655 single-socket hardware. Excludes: GPU levers (see `gpu-acceleration-path.md`), routing/orchestration (see `routing-and-optimization-index.md`), quality/eval (see `research-evaluation-index.md`).

**Created**: 2026-04-23 (after single-vs-aggregate throughput discussion revealed several uncharted single-instance levers with no tracking home)
**Updated**: 2026-04-23 (coordinated pickup plan initiated — see §Pickup Sequence below)
**Parent**: [`inference-acceleration-index.md`](inference-acceleration-index.md)

## ⚑ START HERE if resuming after NPS4 reboot

**Entry point hierarchy for a fresh agent session:**
1. `handoffs/active/master-handoff-index.md` (top-level — see row 27a/27 for CPU work)
2. **this file** (`cpu-inference-optimization-index.md`) — all 14 CPU tracks + current status
3. `handoffs/active/nps-reboot-runbook.md` — step-by-step post-reboot protocol

**Pre-reboot baseline freeze** (for regression detection): `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/pre-nps4-freeze/SUMMARY.md`

**State to re-establish immediately after reboot**:
- `sudo sysctl kernel.perf_event_paranoid=1`
- `sudo sysctl kernel.numa_balancing=0`
- `echo always | sudo tee /sys/kernel/mm/transparent_hugepage/enabled`
- `echo always | sudo tee /sys/kernel/mm/transparent_hugepage/defrag`

**Workspace** (untouched by reboot):
- `llama.cpp-experimental` on branch `cpu-optimization/backlog-2026-04-23` (HEAD `9e048fbc1`)
- Builds ready: `build-llamafile-on` (OMP production), `build-noomp` (with CPU1 Phase 1.0+1.1 code), `build-vnni-q8` (CPU2 falsified, safe to delete)
- Microbenches at `/mnt/raid0/llm/cpu-tp-prototype/`: `tp_gemv_bench`, `tp_gemv_numa_bench`
- libnuma-dev now installed in container (as of 2026-04-24) for Phase 1.3 work

**Tasks queued** (in TaskList): #12 (post-NPS4 re-bench + CPU1 decision), #13 (Phase 1.2 CCD work distribution), #14 (Phase 1.3 NUMA weight mbind), #11 (CPU4 sync primitive — NUMA-independent, can proceed regardless).

## NPS4 locked in — Phase 1.3 v1 landed 2026-04-24

NPS4 re-bench + Phase 1.3 v1 implementation completed 2026-04-24. User decision: Option 2 (stay on NPS4, implement Phase 1.3).

**Phase 1.3 v1**: env-gated `GGML_NUMA_WEIGHTS=1` in `llama-mmap.cpp`. `set_mempolicy(MPOL_INTERLEAVE)` before mmap + suppress `MAP_POPULATE`. Interacts correctly with kernel readahead (which bypasses per-region mbind).

**Clean-cache NPS4 results** (Qwen3-Coder-30B-A3B Q4, 96t):

| Config | t/s |
|---|---|
| noOMP flat (pre-Phase-1.3) | 14.53 |
| noOMP + CCD (Phase 1.0+1.1) | 15.45 |
| noOMP + NW=1 (Phase 1.3 alone) | **34.84** |
| noOMP + CCD + NW=1 (combined) | **39.59** |

- Phase 1.3 alone: **+140%** over flat
- Combined Phase 1.0+1.1+1.3: **+156%**
- **88% of NPS2 pre-reboot baseline** (44.85)
- Concurrent 48×4t peak 104 t/s still available under NPS4

**Still pending**: Phase 1.3 v2 (per-tensor stripe with large chunks — needs `init_mappings` awareness) and Phase 1.2 (CCD-aware `ith/nth` in `ggml_compute_forward_mul_mat`). Target: close the remaining 12% vs NPS2.

**Deferred by user**: L3-as-NUMA reboot (12-way) — revisit after NPS4 optimization is exhausted.

Deep-dive write-up: `research/deep-dives/cpu-tp-phase1b-nps4-2026-04-24.md`. Raw data: `data/cpu_optimization/2026-04-24-nps4/`. Orchestrator-rework notes: `orchestrator-nps4-48x4-notes.md`.

**Full runbook**: [`nps-reboot-runbook.md`](nps-reboot-runbook.md).

## Pickup Sequence (2026-04-23)

A coordinated pickup plan launched on 2026-04-23 covers 7 of the 14 backlog items (CPU1, CPU2, CPU3, CPU5, CPU6, CPU7, CPU11) in an ordered sequence; the remaining 7 are gated downstream or owned by other handoffs. Pre-Phase-0 audit resolved several open questions:

- **tinyBLAS IS already integrated into our fork** at `ggml/src/ggml-cpu/llamafile/sgemm.cpp` (MPL-2.0, gated by `GGML_USE_LLAMAFILE`) → CPU7 becomes an on/off measurement, not an integration task.
- **KleidiAI plugin already in fork** at `ggml/src/ggml-cpu/kleidiai/` → directly reusable template for CPU2's proposed `zen5-ukernels/` directory.
- **`perf` is NOT installed** on the host; Phase 0 profiling uses `GGML_PERF=1` + `rdtsc` + `/usr/bin/time -v` + `getrusage` fallbacks unless sudo install is approved.
- **All work in `/mnt/raid0/llm/llama.cpp-experimental`** on a fresh branch `cpu-optimization/backlog-2026-04-23` off `production-consolidated-v4`, so everything stays mergeable into a future v5.

Step order:

1. **Step 0** — handoff corrections + master-index registration (this update is part of it).
2. **Step 1** — three standalone cheap checks in parallel: CPU6 ZenDNN eval, CPU7 tinyBLAS on/off, CPU11 compiler flag audit. One shared write-up.
3. **Step 2** — re-anchor `llama.cpp-experimental` on fresh `production-consolidated-v4` (preserve existing `test-qwen36-upstream` state on an archive branch first).
4. **Step 3** — **CPU3 Phase 0 root baseline** (the dependency graph's root gate): system-state audit + thread sweep + per-op breakdown + barrier cost + effective BW. Gate: DeltaNet <40%, 48t <80% of 192t, BW <70% of roofline.
5. **Step 4** — CPU3 zero-reboot knob sweep (THP, numa_balancing, 1 GB hugepages = CPU5, IRQ affinity, `--numa` modes, decoupled threads). User-approval-gated on any `sudo sysctl`.
6. **Step 5** — **CPU1 Phase 0+1** TP-sharding single-layer prototype on Qwen3-Coder-30B-A3B MLP-up. Phase 0 gate: BW <60% roofline AND barrier cost >15%. Phase 1 gate: ≥1.3× on single layer.
7. **Step 6** — **CPU2 Phase 0+1** GEMV single-ukernel prototype on Qwen3.6-27B Q8_0 MLP-up (K=5120→N=27648). Phase 1 gate: ≥1.15× end-to-end.
8. **Step 7** — synthesis + user-facing downstream gate decisions (CPU1 Phase 2, CPU2 Phase 2, BIOS window, or shelve-in-favor-of-zero-reboot-wins).

The plan document is at `/home/node/.claude/plans/lets-pickup-handoffs-active-cpu-shape-sp-sunny-tower.md`. Status of each step is tracked via the TaskCreate/TaskList system in the active session.


---

## Agent Operating Instructions

Every agent working on CPU optimization work listed here MUST:

1. **Progress tracking**: update `progress/YYYY-MM/YYYY-MM-DD.md` after every significant step.
2. **Audit logging**: source `scripts/utils/agent_log.sh`; call `agent_task_start` / `agent_task_end` per task.
3. **Handoff updates**: update the specific child handoff's status as phases close.
4. **Index updates**: update the **Status** column in the table below when a handoff changes state (stub → investigation → Phase N → DEPLOYED / ABANDONED).
5. **Baseline-first discipline**: never change a system knob or ship a kernel change without first capturing a baseline measurement. Results that lack a baseline are not credible.
6. **Measure one lever at a time**: when stacking knobs, isolate each one's contribution. A 10% combined gain with unknown per-knob contribution is a landmine for future debugging.

---

## Prioritized Task List

Ordered by expected single-instance decode throughput gain × feasibility.

- [ ] **CPU1 — HIGH (top, NPS4 locked, Phase 1.4 shipped, software-level levers exhausted)** Intra-process tensor-parallel decode → see `intra-process-tensor-parallel-decode.md`. **Single-instance best 48.81 ± 0.08 t/s at 48 threads with `-fa 1`** (full stack: `GGML_CCD_POOLS=1 GGML_NUMA_WEIGHTS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1`). Phase 1.4 landed and PPL-verified. Post-Phase-1.4 perf profile: barrier 28%, GEMV 33.5%, other 38%. Concurrent teardown hang non-reproducible (closed; resolved by cpuset fixes `0ade7bd4d`+`69b4c3fa4`). **Op-fusion Phase 2 reverted (2026-04-24)** — was correct (PPL bit-exact) but throughput-neutral in both fa=0 and fa=1; attention-internal fusion is already done by `ggml_flash_attn_ext` so fusion infra had no remaining leverage target. Reverted as `c34aac61b` + `138b26cd4`. **GEMV VNNI probe (2026-04-24) also net-negative** — added AVX-512VNNI path to `ggml_gemv_q4_K_8x8_q8_K` (PPL bit-exact); throughput slightly regressed because on Zen 5 VPMADDUBSW runs at 2/cycle while VPDPBUSD is only 1/cycle, so AVX2 is actually better-matched to this CPU for Q4_K GEMV. Not committed. **All CPU-general software levers now exhausted on NPS4**; next meaningful gate is the **L3-as-NUMA BIOS reboot** (item 27b).
- [ ] **CPU2 — AVX-512BW kernel + NUMA fix LANDED 2026-04-24, production-viable** Shape-specialized GEMV microkernels → see `cpu-shape-specialized-gemv-decode.md`. Session 15 landed (commits `1d18efce3` + `e84a5c82f` + `ba1c23900` on branch `cpu-optimization/q8-8x8-avx512bw`): AVX-512BW 8x8 Q8_0 GEMV kernel (hot loop emits `vpmaddubsw`+`vpmaddwd`, deliberately bypassing the VNNI-auto-selecting helper — Zen 5 falsified VNNI twice already), plus auto-`mbind(MPOL_INTERLEAVE)` on the CPU_REPACK buffer when `ggml_is_numa()`, plus an env-gated `gated_delta_net` S_v sub-chunking refactor (default off — a probe that disproved DeltaNet as the bottleneck). **Final performance on Qwen3.6-27B-Q8_0** at 96t = 4.39 vs baseline 4.32 (+1.6%); at 1t = 1.12 vs 0.85 (+31.8%). PPL on Wikitext-2 = 6.6985 (preserved). **The 4.4 t/s ceiling is NOT memory-bandwidth** — only 26% of theoretical 460 GB/s vs Qwen2.5-Coder-32B dense at 41% on same hardware. Real bottleneck unidentified; next session should be a `GGML_PERF=1` profile, not more kernel work. **No env gates required** — auto-mbind runs automatically on multi-NUMA systems; the `GGML_Q8_0_8X8` + `GGML_Q8_0_8X8_AVX` flags remain default OFF for rollout caution. **Follow-ups**: profile-then-fix Qwen3.6-27B decode at 96t to find the real ceiling cause, Q6_K + Q5_K 8x8 kernels (Session 14 flagged both as dispatcher-NEON-only gaps, ~2× Q8_0 complexity for bit-split unpack), upstream the `mbind` fix (general bug affecting every multi-NUMA repacked quant).
- [ ] **CPU3 — HIGH** System-level tuning (NPS mode, hugepages, barrier, IRQ, SMT) → see `single-instance-system-tuning.md`. 15–40% alone; a prerequisite for the full CPU1 gain under NPS4/L3aaN. **Zero-reboot knobs partially applied 2026-04-23** (THP→always, numa_balancing=0, 1GB hugepages — net within noise on canonical baseline).
- [ ] **CPU4 — HIGH (promoted 2026-04-23)** Per-CCD hierarchical sync primitive (was part of CPU3 Phase 3). 32–45% of decode cycles measured in OpenMP barriers — standalone HIGH lever independent of CPU1. 10–30% barrier cost reduction at 192t.
- [ ] **CPU5 — MED** Explicit hugepages (1 GB) for weight mmap (part of CPU3 Phase 1). 5–15% on long decode runs.
- [ ] **CPU6 — MED** ZenDNN 5.2 evaluation on our stack (AMD-optimized drop-in). Claimed "200% vs prior"; not yet validated on llama.cpp. 1-day test.
- [ ] **CPU7 — MED** tinyBLAS / llamafile integration assessment. If already mergeable into our fork, unlocks part of CPU2 without a full from-scratch ukernel implementation.
- [ ] **CPU8 — MED** Weight replication per NUMA node for small models (part of CPU3 Phase 4). 10–30% in NPS4/L3aaN modes, conditional on CPU3 Phase 2.
- [ ] **CPU9 — LOW** Dense-weight sparsity exploitation (e.g., 2:4 structured sparsity if activation-aware pruning applies). Unexplored on CPU. Speculative; prior art is GPU.
- [ ] **CPU10 — LOW** Quantization format exploration beyond Q4_K_M — Q4_0 simpler ukernel, IQ3/IQ2/IQ4_XS quality floors. Overlaps with CPU2 open questions.
- [ ] **CPU11 — LOW** Compiler flag / tuning audit (`-march=znver5 -mtune=znver5 -mprefer-vector-width=512`, PGO, LTO, profile-guided rebuild of the llama.cpp fork).
- [ ] **CPU12 — LOW** ccache / BOLT / FDO-style post-link binary optimization of the llama-server binary.
- [ ] **CPU13 — LOW** Prefill-specific optimizations: paged attention RSS investigation (deferred from v3 rebuild), chunked prefill for long contexts.
- [ ] **CPU14 — LOW** Batched slot decode (`-np N --parallel`) benchmark suite — aggregate, not single-session. Partial overlap with dynamic-stack-concurrency; deserves its own baseline under the new stack.
- [ ] **CPU15 — HIGH (new 2026-04-24)** Large-MoE as primary target + expert parallelism → see [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md). Two linked tracks: (A) strategic reframe — target large sparse MoE (≥100B total, ≥10B activated, ≥64 experts) to exploit the hardware's RAM:BW ratio and the 2.13× concurrent-aggregate gap (48.81 → ~104 t/s); (B) expert-parallelism mechanism — shard experts across CCDs/NUMA nodes/processes to convert aggregate BW into single-stream throughput. Phase 0 is a cheap 4–6 h baseline (re-measure Qwen3-235B-A22B + 480B-A35B on current NPS4 + `GGML_NUMA_WEIGHTS=1` + AVX-512BW stack) that falsifies or opens the mechanism work. Expected gain 2–5× single-stream on large MoE. Contends with `orchestrator-nps4-48x4-notes.md` for NUMA topology — Decision Point D2 in the child handoff.

Items CPU1–CPU8 and CPU15 are the active backlog. CPU9–CPU14 are watchlist items; pursue only when higher-priority work is gated.

---

## Handoff Landscape

| ID | Handoff / work | Status | Priority | Gain target | Blocks / blocked by |
|----|---------------|--------|----------|-------------|---------------------|
| CPU1 | [`intra-process-tensor-parallel-decode.md`](intra-process-tensor-parallel-decode.md) | **Phase 1.3 v1 IMPLEMENTED 2026-04-24; NPS4 locked** | **HIGH (top, in flight)** | Phase 1.3 v1 alone +140%; with CPU1 P1.0+1.1 +156% vs baseline; 39.59 single-inst (88% NPS2) | Phase 1.3 v2 (per-tensor stripe, 2d) + Phase 1.2 (CCD work dist, 2-3d) next. |
| CPU2 | [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) | **Session 15 AVX-512BW 8x8 kernel + NUMA auto-mbind LANDED 2026-04-24** | production-viable | 1t: +31.8% ; 12-96t: +0.9-2.9% (BW-saturated ceiling) | Q6_K/Q5_K are the natural follow-ons (same NEON-only dispatcher gap, ~2× complexity) |
| CPU3 | [`single-instance-system-tuning.md`](single-instance-system-tuning.md) | **Phase 0 + zero-reboot knobs partial 2026-04-23** | HIGH | 15–40% alone; gating multiplier for CPU1 | Phase 2 requires reboot; coordinates with CPU1 Phase 3 |
| CPU4 | Per-CCD sync primitive | **Promoted 2026-04-23 based on 32-45% measured barrier cost** | **HIGH (standalone)** | 10–30% barrier cost reduction | Independent of CPU1; +16-22% end-to-end projected |
| CPU5 | 1 GB hugepages | stub (part of CPU3 Phase 1) | MED | 5–15% | Kernel boot param |
| CPU6 | ZenDNN 5.2 eval | not started | MED | Unknown; AMD claims up to 2× | 1-day test; low risk |
| CPU7 | tinyBLAS / llamafile integration | not started | MED | Partially supplants CPU2 | License + fork-merge check |
| CPU8 | Per-NUMA weight replication | stub (part of CPU3 Phase 4) | MED | 10–30% under NPS4/L3aaN | Conditional on CPU3 Phase 2 |
| CPU9 | Dense-weight sparsity | not started | LOW | Unknown | Research-stage; GPU prior art only |
| CPU10 | Sub-Q4 quant eval | partial (via glm51-reap, tq3 intake) | LOW | Per-model | Overlaps with quality handoffs |
| CPU11 | Compiler / PGO / LTO | not started | LOW | 1–5% | Low-risk; time investment |
| CPU12 | BOLT / FDO binary post-link | not started | LOW | 1–3% | Low-risk; mature tooling |
| CPU13 | Prefill optimizations | deferred (from v3 rebuild) | LOW | Prefill-specific | Not decode-critical |
| CPU14 | `--parallel` slot decode bench | not started | LOW | Aggregate only | Covered partially by `dynamic-stack-concurrency.md` |
| CPU15 | [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) | **Phase 3 COMPLETE 2026-04-26** — EP **+100% bit-exact PPL on Qwen3.6-35B-A3B**, +6% on gemma-26B-A4B; **REAP-246B confirmed REGRESSION** at -53% even with eager-warm + all flags (bandwidth-saturated >150B class doesn't benefit from EP on EPYC NPS4) | **HIGH** | Phase 3.0 IPC RTT 0.73 μs; Phase 3.1 library `f47bec4`; full Phase 3.2 stack a→h all live. **Production routing**: <50B MoE → EP N=2 drone+shard +100% bit-exact PPL; >150B MoE → stay single-instance --numa distribute. Phase 3.3 production wiring next session (env-var bootstrap simplifies launcher) | Phase 1/2 intra-process EP all D3-failed; Phase 3 inter-process beats single-instance on medium MoE; closes the bandwidth-math question on >150B class |

---

## Dependency Graph

```
                    ┌─────────────────────────┐
                    │ CPU3 Phase 0 baseline   │
                    │ (measure current state) │
                    └──────────┬──────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │ CPU3 Phase 1 │  │ CPU2 Phase 0 │  │ CPU1 Phase 0 │
     │ zero-reboot  │  │ feasibility  │  │ feasibility  │
     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
            │                 │                 │
            ▼                 ▼                 ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │ CPU3 Phase 2 │  │ CPU2 Phase 1 │  │ CPU1 Phase 1 │
     │ BIOS / reboot│  │ one-ukernel  │  │ single-layer │
     │ (NPS4/L3aaN) │  │ prototype    │  │ prototype    │
     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
            │                 │                 │
            ▼                 ▼                 ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │ CPU3 Phase 3 │  │ CPU2 Phase 2 │  │ CPU1 Phase 2 │
     │ sync primit. │──┤ full Qwen3.6 │  │ full model   │
     │ (= CPU4)     │  │ Q8 coverage  │  │ integration  │
     └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
            │                 │                 │
            ▼                 ▼                 ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
     │ CPU3 Phase 4 │  │ CPU2 Phase 3 │  │ CPU1 Phase 3 │
     │ weight repl. │  │ production   │  │ NPS4 / L3aaN │
     │ (= CPU8)     │  │ rollout      │  │ benchmark    │
     └──────────────┘  └──────────────┘  └──────┬───────┘
                                                │
                                                ▼
                                      ┌──────────────────┐
                                      │ CPU1 Phase 4     │
                                      │ production       │
                                      │ deployment       │
                                      └──────────────────┘
```

**Key dependencies**:
- Nothing starts without **CPU3 Phase 0 baseline**. Every other gate decision depends on knowing the current bandwidth / barrier-cost numbers.
- **CPU1 Phase 2** (full model TP) needs **CPU4** (sync primitive) to land first, or the global-barrier cost will eat the TP gain.
- **CPU1 Phase 3** (L3aaN benchmark) needs **CPU3 Phase 2** (BIOS change) to expose the NUMA topology TP wants.
- **CPU8** (weight replication) is conditional on NPS4/L3aaN being adopted (**CPU3 Phase 2 outcome**).

Standalone paths that don't need baseline:
- **CPU6** (ZenDNN eval) — 1-day test, no dependencies.
- **CPU7** (tinyBLAS check) — license/merge review, no dependencies.
- **CPU11** (compiler flag audit) — rebuild experiment, no dependencies.

---

## Cross-Cutting Concerns

### The 460 GB/s ceiling

Every CPU decode lever is bounded above by system memory bandwidth (~460 GB/s effective on EPYC 9655 12-channel DDR5-6000). A model's decode throughput ceiling is:

```
max_tokens_per_second = effective_BW (GB/s) / weights_read_per_token (GB)
```

For 30B-A3B Q4_K_M (16 GB): ceiling ≈ 28 t/s per socket if perfectly BW-utilized.
For dense 32B Q4_K_M (18.5 GB): ceiling ≈ 24 t/s.
For 27B Q8_0 (26.6 GB): ceiling ≈ 17 t/s.

Current measurements leave substantial headroom below these ceilings on single-instance (typically at 30–60% of ceiling). That headroom is what CPU1/CPU2/CPU3 are all competing to recover. No combination of levers can exceed the ceiling.

**What CAN exceed the ceiling**: per-token compute efficiencies that reduce weights_read_per_token — MoE active-expert sparsity (already deployed), KV compression (orthogonal, already handled), weight sparsity (CPU9 — speculative), speculative decoding (partially handled elsewhere).

### Composition matrix

| Lever | CPU1 TP | CPU2 ukernel | CPU3 tuning | KV work | Speculation |
|-------|---------|--------------|-------------|---------|-------------|
| CPU1 TP | — | ×multiplicative | ×multiplicative | orthogonal | ×multiplicative |
| CPU2 ukernel | ×mul | — | ×mul | orth | ×mul |
| CPU3 tuning | ×mul (prereq of part) | ×mul | — | orth | ×mul |
| KV work | orth | orth | orth | — | orth |
| Speculation | ×mul | ×mul | ×mul | orth | — |

The combined multiplier compounds until the 460 GB/s ceiling clips it. A realistic stack — CPU1 2.5× × CPU2 1.75× × CPU3 1.25× = 5.5× — would saturate the ceiling on most production models, at which point further gains must come from reducing weight reads (KV, speculation, sparsity).

### Interaction with multi-instance deployment

`dynamic-stack-concurrency.md` deploys NUMA 4-way aggregate throughput. Single-instance levers here do not replace that; they make each concurrent session individually faster. Production routing remains: single active session → full-speed instance; N concurrent → N quarter instances. TP sharding changes what "full-speed instance" means (faster) but does not change the routing architecture.

Under NPS4/L3aaN, the existing quarter-instance geometry shifts: instead of 4×48t instances on 2 NUMA nodes, we'd have 4×3-CCD instances on 4 nodes, or 12×1-CCD instances on 12 nodes. Re-benchmark required.

**CPU15 reframing (2026-04-24)**: the 2.13× concurrent-aggregate gap (single-instance 48.81 → concurrent ~104 t/s on 30B-A3B Q4_K_M) suggests the hardware's natural target is **large sparse MoE** with per-NUMA expert parallelism, not small dense / small hybrid MoE. CPU15 opens that axis: Phase 0 is a cheap re-measurement of Qwen3-235B-A22B + 480B-A35B on the current NPS4 stack; Phase 1+ implements per-CCD expert sharding in the llama.cpp fork. See [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md).

### BIOS / reboot budget

Reboots are expensive. Batch all BIOS investigations into single maintenance windows:

- **Window 1** (CPU3 Phase 2): NPS2 → NPS4, measure. If NPS4 doesn't help, revert.
- **Window 2** (conditional on Window 1 outcome): NPS4 → L3aaN, measure. Or NPS2 → L3aaN if NPS4 was revert.
- **Window 3** (conditional): SMT on/off toggle. Usually grouped with NPS change.
- **Window 4** (conditional): C-states disable. Grouped with SMT.

Coordinate all windows with user; document rollback per window.

### Fork vs upstream

All kernel-level work lives on the `production-consolidated-v3` / `v4` branches of our llama.cpp fork (see `llama-cpp-kernel-push-rebase.md`). Never modify production branches directly. Use `llama.cpp-experimental` worktree for development; upstream-ready changes get PR'd to ggml-org/llama.cpp (Phase 5 of CPU1, Phase 4 of CPU2).

### Measurement infrastructure

Baseline and progress measurements rely on:

- `llama-bench` from the fork's `build/bin/`.
- `perf stat` / `perf record` for uncore counters and hot-function profiling.
- AMD μProf (if installable) for IOD fabric counters.
- Benchmark data: save all results under `epyc-inference-research/data/cpu_optimization/<date>/`.

Baseline model for all comparisons (unless a handoff specifies otherwise): **Qwen3-Coder-30B-A3B Q4_K_M**. It's hybrid + MoE (representative of our stack), mid-size (measurable), and is the existing frontdoor/worker model so deployed perf is relevant.

---

## Cross-Cutting: What Is Already Deployed Or Concluded (Do Not Re-Attempt)

To save future agents from re-opening closed work:

| Technique | Final status | Where to read |
|-----------|--------------|---------------|
| NUMA 4-way multi-instance | DEPLOYED 2026-03-19 | `completed/numa-orchestrator-deployment.md` |
| `draft_max` = 32–48 | DEPLOYED 2026-03-18 | `inference-acceleration-index.md` |
| Tree speculation (dense f16) | DEPLOYED selectively | `completed/tree-speculation-numa-drafting.md` |
| DFlash block diffusion | NOT VIABLE on Q4_K_M | `completed/dflash-block-diffusion-speculation.md` |
| MTP-1 speculation | NOT VIABLE on hybrid | `completed/mtp-speculative-decoding.md` |
| Qwen3.5 hybrid self-acceleration | ALL 6 approaches net-negative | `completed/ssm-hybrid-acceleration.md` |
| TIDE calibration-router early exit | **DEPRECATED 2026-04-23** — projection quality unsolvable with linear or adapter MLP | `llama-cpp-kernel-push-rebase.md` |
| REAP MoE expert pruning | DEPLOYED — 246B replaces 480B | `completed/reap-moe-expert-pruning.md` |
| KV quantization (Hadamard + q4_0) | DEPLOYED | `completed/kv-cache-quantization.md` |
| KV compaction (AM) | PRODUCTION (L1–L4b merged) | `attention-matching-kv-compaction.md` |
| Performance governor | DEPLOYED | already-done, verify-only |
| mlock on production models | DEPLOYED | already-done, verify-only |

Anything not on this list OR in the active backlog above is either new research-stage intake (see `research/intake_index.yaml`) or orthogonal work (see sibling indices).

---

## Reporting Instructions

After completing any task listed here:

1. Update the **Status** column in the handoff landscape table above (stub → Phase N → DEPLOYED / ABANDONED).
2. Update the **child handoff's** status line and its phase tracker.
3. Update `inference-acceleration-index.md` landscape table if the change affects production.
4. Update `master-handoff-index.md` priority queue if the status change affects cross-domain priorities.
5. Update `progress/YYYY-MM/YYYY-MM-DD.md` with a brief writeup + links.
6. For successful deployments: extract findings into `wiki/hardware-optimization.md` or `wiki/inference-serving.md` as appropriate.
7. For falsifications: document the specific measurement that killed the lever, so future agents don't re-open it.

---

## Key File Locations

| Purpose | Location |
|---------|----------|
| llama.cpp fork production branch | `/mnt/raid0/llm/llama.cpp` (`production-consolidated-v3/v4`) |
| llama.cpp experimental worktree | `/mnt/raid0/llm/llama.cpp-experimental` |
| Benchmark scripts | `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/` |
| Model registry (full) | `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` |
| Orchestrator stack launcher | `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` |
| CPU optimization benchmark data | `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/` (create on first use) |
| GGML CPU backend source | `/mnt/raid0/llm/llama.cpp/ggml/src/ggml-cpu/` |
| GGML thread pool | `/mnt/raid0/llm/llama.cpp/ggml/src/ggml-threading.cpp` |
| Wiki hardware notes | `/mnt/raid0/llm/epyc-root/wiki/hardware-optimization.md` |
| Wiki inference serving | `/mnt/raid0/llm/epyc-root/wiki/inference-serving.md` |

---

## References

- Parent index: [`inference-acceleration-index.md`](inference-acceleration-index.md)
- Master entry point: [`master-handoff-index.md`](master-handoff-index.md)
- Routing/orchestration index: [`routing-and-optimization-index.md`](routing-and-optimization-index.md)
- GPU side (for composition planning): [`gpu-acceleration-path.md`](gpu-acceleration-path.md)
- Child handoffs: see landscape table above.

---

## Changelog

- 2026-04-23: Initial creation. CPU1/CPU2/CPU3 stubs populated; CPU4–CPU14 watchlist added.
- 2026-04-24: CPU15 added ([`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md)). Rationale: all CPU-general software levers exhausted on single-instance NPS4; the 2.13× concurrent-aggregate gap (48.81 → ~104 t/s) indicates large sparse MoE + expert parallelism is the next open axis. Multi-instance deployment section updated to reference CPU15.
- 2026-04-25: CPU15 Phase 3.2 a→e.2 added 8 commits on `llama.cpp-experimental:feature/cpu-ep-inter-process` plus 5 docs commits on `epyc-root:main`. **REVISED 2026-04-25 evening**: Phase 3.2(e.1) attempt revealed all 8 prior commits were inside `#ifndef GGML_USE_OPENMP` guards and stripped from the production build. Commit `e001b3eda` extracted inter-process EP from those guards; first honest measurement is no-flags EP path bit-exact at 19.4 t/s = 68% of single-instance baseline 28.5 t/s. `GGML_EP_WORKER_DRONE=1` and `GGML_EP_SHARD=1` were initially PPL-broken — root-caused to EP top block ordering AFTER the src1 quantization loop (workers' uninitialized src1 quantized into wdata before broadcast delivered correct data). **`ff6833b19` moved the EP top block before quantization with a barrier; drone + shard now bit-exact. EP N=2 + drone + shard = 30.3 t/s = 106% of single-instance baseline = +6% over baseline.** Architecture validated; PPL gate (f) on WikiText-2 + REAP-246B D3' gate (g) ≥+20% over 6.16 t/s are the remaining work.
- 2026-04-26: CPU15 Phase 3 COMPLETE. (g.1) eager parallel shard warm-up landed in `43c65b926` — collective `ggml_barrier`-coordinated parallel memcpy collapses ~250 ms single-threaded first-call cost on REAP-246B-class tensors to ~250 μs across all 96 master threads. Unblocked REAP-246B steady-state measurement: **−53% vs baseline (3.26 t/s vs 6.89)**. Master-all-nodes + park combo would not finish (master-parker spinning threads contend for cores with workers, per-tensor warm cost ~20 sec instead of 2 ms). Conclusion: EP doesn't help bandwidth-saturated >150B-class MoE on EPYC NPS4 — single-instance --numa distribute already saturates 100% of aggregate DDR bandwidth, partitioning divides bandwidth without recovering useful compute parallelism. **Production routing**: <50B MoE → EP N=2 drone+shard (+56-100% bit-exact); >150B MoE → single-instance. Phase 3.3 production wiring next session.
