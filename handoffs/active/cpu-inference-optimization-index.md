# CPU Inference Optimization — Unimplemented Performance Backlog

**Purpose**: Single discovery point for ALL remaining unimplemented CPU decode/prefill throughput techniques on our EPYC 9655 Turin hardware. Techniques that are deployed or concluded-not-viable live elsewhere (see `inference-acceleration-index.md`). This index is the **forward-looking backlog** — every lever that could still add single-instance or aggregate throughput and has not been either shipped or ruled out.

**Scope boundary**: CPU decode/prefill throughput on local EPYC 9655 single-socket hardware. Excludes: GPU levers (see `gpu-acceleration-path.md`), routing/orchestration (see `routing-and-optimization-index.md`), quality/eval (see `research-evaluation-index.md`).

**Created**: 2026-04-23 (after single-vs-aggregate throughput discussion revealed several uncharted single-instance levers with no tracking home)
**Updated**: 2026-04-23
**Parent**: [`inference-acceleration-index.md`](inference-acceleration-index.md)

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

- [ ] **CPU1 — HIGH** Intra-process tensor-parallel decode (CCD sharding + comm-hiding) → see `intra-process-tensor-parallel-decode.md`. Highest single lever; 2–5× single-instance decode. Interacts with CPU2, CPU3.
- [ ] **CPU2 — HIGH** Shape-specialized GEMV microkernels for Zen 5 → see `cpu-shape-specialized-gemv-decode.md`. 1.5–2.5× single-instance decode. Composes multiplicatively with CPU1.
- [ ] **CPU3 — HIGH** System-level tuning (NPS mode, hugepages, barrier, IRQ, SMT) → see `single-instance-system-tuning.md`. 15–40% alone; a prerequisite for the full CPU1 gain under NPS4/L3aaN.
- [ ] **CPU4 — MED** Per-CCD hierarchical sync primitive (part of CPU3 Phase 3, also a prerequisite for CPU1 Phase 2). 10–30% barrier cost reduction at 192t.
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

Items CPU1–CPU8 are the active backlog. CPU9–CPU14 are watchlist items; pursue only when higher-priority work is gated.

---

## Handoff Landscape

| ID | Handoff / work | Status | Priority | Gain target | Blocks / blocked by |
|----|---------------|--------|----------|-------------|---------------------|
| CPU1 | [`intra-process-tensor-parallel-decode.md`](intra-process-tensor-parallel-decode.md) | stub | HIGH | 2–5× single-instance | Blocked by CPU3 Phase 0; Phase 3 blocked by CPU3 Phase 2 (BIOS reboot) |
| CPU2 | [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) | stub | HIGH (MED per current row) | 1.5–2.5× single-instance | Phase 0 profiling overlaps with CPU1 Phase 0; composes with CPU1 |
| CPU3 | [`single-instance-system-tuning.md`](single-instance-system-tuning.md) | stub | HIGH | 15–40% alone; gating multiplier for CPU1 | Phase 2 requires reboot; coordinates with CPU1 Phase 3 |
| CPU4 | Per-CCD sync primitive | stub (part of CPU3 Phase 3) | MED | 10–30% barrier cost | Prerequisite for CPU1 Phase 2 |
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
