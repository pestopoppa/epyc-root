# CPU Inference Optimization — Unimplemented Performance Backlog

**Purpose**: Single discovery point for ALL remaining unimplemented CPU decode/prefill throughput techniques on our EPYC 9655 Turin hardware. Techniques that are deployed or concluded-not-viable live elsewhere (see `inference-acceleration-index.md`). This index is the **forward-looking backlog** — every lever that could still add single-instance or aggregate throughput and has not been either shipped or ruled out.

**Scope boundary**: CPU decode/prefill throughput on local EPYC 9655 single-socket hardware. Excludes: GPU levers (see `gpu-acceleration-path.md`), routing/orchestration (see `routing-and-optimization-index.md`), quality/eval (see `research-evaluation-index.md`).

**Created**: 2026-04-23 (after single-vs-aggregate throughput discussion revealed several uncharted single-instance levers with no tracking home)
**Updated**: 2026-04-27 evening (closure-inflation remediation per peer review: CPU25 NUMA_MIRROR Phase 2 gate FAILED & track CLOSED; CPU21/22/23/24 statuses corrected from premature closure to active-with-remediation; "software runway exhausted" framing narrowed; post-L3aaN-reboot block removed; MoE-Spec added as new track)
**Parent**: [`inference-acceleration-index.md`](inference-acceleration-index.md)

## ⚑⚑⚑⚑ COMPOUNDING-MATRIX FINDINGS 2026-04-26 evening — PRIOR WINS RE-MEASURED

The user-requested "verify lever compounding" methodology check (2026-04-26 evening) **falsified the central production-push hypothesis**. Most prior "wins" collapse to noise when re-measured against the proper cold-cache canonical (`--mmap 0 + numactl --interleave=all -t 96 -fa 1`) rather than the historic warmed mmap=1 reference.

### Re-measured optimization deltas

| Track | Historic claim (mmap=1 warmed ref) | Proper canonical Δ | Status |
|---|---|---|---|
| **CPU15 EP frontdoor (Qwen3.6 Q8_0)** | **+17%** (14.63→17.18) | **+1.6%** (20.81→21.15) | **DOWNGRADE — noise on proper baseline** |
| **CPU15 EP regression on REAP-246B** | **−47%** (6.85→3.65) | **0%** (5.94→5.92) | **DOWNGRADE — was sub-baseline artifact** |
| CPU2 auto-mbind on Q8_0 | +6% claimed | 0% — redundant with --interleave=all | DOWNGRADE — redundant |
| CPU1 3-flag stack (Coder-30B Q4) | +1.8% (warmed mmap=1) | +0.6% | DOWNGRADE — noise |
| CPU1 3-flag stack (Qwen3.6 Q8) | (small) | +1.7% | noise |
| CPU2 AVX-512BW Q8_0 kernel itself | +31.8% @ 1t | unchanged — kernel does compute | Unchanged (still real for SIMD) |

### The actual biggest win is the canonical config itself

| Model | Quant | Proper canonical | Warmed mmap=1 ref | Δ |
|---|---|---|---|---|
| **Qwen3.6-35B-A3B** | **Q8_0** | **20.81** | 14.63 | **+44%** |
| **gemma-4-26B-A4B** | **Q4_K_M** | **34.69** | 25.01 | **+39%** |
| Qwen3-Coder-30B-A3B | Q4_K_M | 42.27 | 43.57 | −3% (~equivalent) |
| Qwen3-Next-80B-A3B | Q4_K_M | 20.51 | 23.25 | −12% |
| Qwen3-Coder-REAP-246B-A35B | Q4_K_M | 5.94 | 6.85 | −13% |

For Q8_0 + gemma, **deploying `numactl --interleave=all` as the canonical config alone captures more than all the optimization code combined**. The earlier "Next-80B + REAP-246B prefer warmed mmap=1" framing turned out to be **a measurement artifact** (asymmetry investigation 2026-04-26 late evening, `data/cpu_optimization/2026-04-26-asymmetry/SUMMARY.md`): the historical 23.25 / 6.85 numbers required HOURS-to-DAYS of system uptime for numa_balancing to learn model-specific access patterns. 5-run warming doesn't reach those values. Cold `--interleave=all` reaches **89-100% of long-warmed performance immediately on every model** — the 5-13% gap to long-warmed is real but unreachable in practical timeframes. **`numactl --interleave=all` is the SINGLE canonical for all models. No model-specific config needed.** mmap mode (1 vs 0) is irrelevant when `--interleave=all` is active.

### Strategic implications

1. **Most "production-shippable wins" were sub-baseline artifacts** — the EP code is bit-correct but provides no measurable throughput on the proper canonical for Qwen3.6 and is neutral on REAP-246B (rather than catastrophically regressing).
2. **The L3aaN regression magnitudes** were also against the warmed mmap=1 baseline. Apples-to-apples NUMA-aware comparison: L3aaN best 29.42 vs NPS4 proper 42.27 = −30% on Coder. Revert decision unchanged but framing was inflated.
3. **Production deployment should be model-aware** — use proper canonical for Q8_0 + gemma; warmed mmap=1 path for Next-80B + REAP-246B. The orchestrator's per-model config should encode this.
4. **CPU24 attribution work simplifies**: there's no measurable EP regression on >150B to attribute when measured properly. The remaining open question is "what's the absolute ceiling for REAP-246B / what bottleneck class limits 5.94 t/s" rather than "why does EP regress".

Raw data: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-26-compounding/SUMMARY.md`. Documentation cascade: `feedback_canonical_baseline_protocol.md` (memory, extended in-place), `cpu-benchmark-rigor-and-revalidation.md` (CPU20 protocol revised), `large-moe-expert-parallelism.md` (CPU15 EP claim downgrade), `progress/2026-04/2026-04-26.md` (compounding section).

---

## ⚑⚑⚑ POST-REVERT VERIFIED 2026-04-26 — NPS4 hardware restored, with caveats

User completed BIOS revert to NPS4 on 2026-04-26 evening. Verification ran and surfaced **three critical findings** that refine all earlier 2026-04 CPU work. Read these before doing any benchmark.

### Verification result

- ✓ Topology: 4 nodes, distance 10/12 (NPS4 confirmed)
- ✓ Branch: `8cb04da9d` on `feature/cpu-ep-inter-process`
- ✓ Hardware BW restored — `--mmap 0 + numactl --interleave=all -t 96` gives **42.41 ± 0.23 t/s** on Coder-30B = within 2.7% of historical 43.57 ref
- ⚠️ Plain canonical `taskset -c 0-95 -t 96 -fa 1` gives only **22.92 ± 0.13** cold-cache (warms to 32.40 after 1 pass; eventually 43+ after long warming)

### Finding 1 — Canonical 43.57 was steady-state-after-warming, not cold-cache

The historical NPS4 reference number used as the L3aaN comparison anchor was measured after 1.5+ days of continuous benchmarking. From a fresh boot it's 22-23 t/s on plain canonical. The reason: with `mmap 1` (default), GGUF pages are placed by first-touch — `numactl --interleave=all` does NOT override file-cache placement. Reliable cold-cache configs:

| Config | Cold-cache result | Notes |
|---|---|---|
| `taskset -c 0-95 -t 96 -fa 1` | **22.92 ± 0.13** | warms slowly to 43+ over many passes |
| Same after 1 warmup pass | 32.40 ± 0.08 | improving |
| **`--mmap 0 + numactl --interleave=all -t 96 -fa 1`** | **42.41 ± 0.23** | **97% of warmed ref, no warming needed** |

**Implication for L3aaN comparison**: earlier in the day "L3aaN regresses 47%" used cold-vs-warmed comparison and was inflated. Apples-to-apples NUMA-aware comparison is L3aaN best (29.42 with `--interleave=all`) vs NPS4 best (42.41 with `--mmap 0 + --interleave=all`) = **L3aaN −30.6%**. Revert decision unchanged.

**Going forward**: use `--mmap 0 + numactl --interleave=all -t 96 -fa 1` as the cold-cache canonical config. Always label measurements with cache state (cold/warmed/steady-state).

### Finding 2 — NVMe RAID0 split across NUMA nodes 2 and 3 under NPS4

`/mnt/raid0` NVMes live on different nodes under NPS4 (same quadrant under L3aaN). RAID0 stripe IO is cross-node regardless of worker pinning. Single-node `numactl --cpunodebind=N --membind=N` cannot keep IO local. **Recommended**: `numactl --interleave=2,3 …` for RAID-heavy work; `numactl --interleave=all` for full-machine inference (covers weights + IO buffers). Memory entry: `project_raid_numa_split_nps4.md`.

### Finding 3 — `kernel.numa_balancing` self-resets to 0 despite sysctl.d

User confirmed: file intact, `systemd-sysctl` reports successful apply, runtime reads 0. Manual `echo 1 >` works briefly then flips back. Happens on plain NPS4 too — earlier "L3aaN-caused-it" hypothesis is invalidated. Real fix: oneshot service post-`systemd-sysctl`; left as open item. **Always check `cat /proc/sys/kernel/numa_balancing` per session — don't trust the file.** Memory entry: `feedback_numa_balancing_self_reset.md`.

### Forward path AFTER reading the above

- Phase H (PPL gates) is the next forward step on NPS4. Use `--mmap 0 + numactl --interleave=all -t 96 -fa 1` as the cold-cache reference for any Coder-30B comparison; reproduce 42.41 t/s before declaring any new optimization win.
- Phases I → J → K → L → M (v5 cherry-pick → audit → shadow → orchestration → rollout) per `cpu-optimization-thesis-pause-2026-04-26.md`.
- CPU16/17/18/19 backlog (disagg/Sarathi/MegaBlocks/Tutel ports) is independent of NUMA topology, can proceed in parallel.
- CPU20–CPU24 wave pipeline gates any new "exhausted/deployable" claim. Note CPU20 protocol now requires explicit cache-state labels (P5a).

### What was decided in this session — do NOT reopen without new mechanism

- **L3aaN is rejected** for this stack. Don't re-propose without integrating per-NUMA-node weight replication (vproxy-tools' GGML_NUMA_MIRROR fork) AND empirical evidence beating NPS4 best 42.41 on Coder-30B. The 12-rank concurrent-split (the literature's "designed-for L3aaN" pattern) regressed −35% vs NPS4 aggregate.
- **`GGML_NUMA_WEIGHTS=1` is DEPRECATED.** Use the 3-flag stable stack `CCD_POOLS + CCD_WORK_DIST + BARRIER_LOCAL_BETWEEN_OPS` (without NW) for opt-in research only.
- **EP frontdoor (+17% on Qwen3.6-35B Q8_0)** is the only confirmed production gain from CPU1+CPU2+CPU15 work; everything else is opt-in research.

### Memory references

- `project_l3aan_reverted.md` — full L3aaN result + literature integration
- `project_raid_numa_split_nps4.md` — NEW 2026-04-26 — RAID/NUMA split + interleave guidance
- `feedback_numa_balancing_self_reset.md` — NEW 2026-04-26 — sysctl drift caveat
- `feedback_canonical_baseline_protocol.md` (extended) — NEW empirical addendum on cold-vs-warmed
- `feedback_llama_bench_fa_default.md` — ALWAYS pass `-fa 1` explicitly

### Forward path AFTER step 6 passes

- **Phase H — PPL gates** is the next forward step. Per `cpu-kernel-env-flags-inventory.md` cherry-pick plan, run 32-chunk WikiText-2 PPL via `llama-perplexity` for each production model × {canonical, kill-switch off, CPU1 3-flag opt-in, EP-frontdoor (Qwen3.6 only)}. Bit-identical OR ≤1e-4 relative drift required for v5 ship.
- **Phase I → J → K → L → M** (v5 cherry-pick → audit → shadow → orchestration wiring → rollout) follow per `cpu-optimization-thesis-pause-2026-04-26.md` track plan.
- **CPU16/17/18/19 backlog** (disagg/Sarathi/MegaBlocks/Tutel ports from the 2026-04-26 research-intake batch) is independent of the NUMA topology and can proceed in parallel.
- **CPU20–CPU24 wave pipeline** (benchmark rigor → OpenMP matrix → uncore attribution → dynamic balancing → context regimes) gates any new "exhausted/deployable" claim per the audit policy.

### What was decided in this session — do NOT reopen without new mechanism

- **L3aaN is rejected for this stack.** Don't re-propose without first integrating per-NUMA-node weight replication (vproxy-tools' GGML_NUMA_MIRROR fork) AND an experiment showing it beats NPS4 peak 48.81 on Coder-30B. The 12-rank concurrent-split (the literature's "designed-for L3aaN" workload pattern) ALSO regressed −35% vs NPS4 aggregate — see `data/cpu_optimization/2026-04-26-l3aan/concurrent12/SUMMARY.md`.
- **`GGML_NUMA_WEIGHTS=1` is DEPRECATED.** Don't re-enable in production stacks. Use the 3-flag stable stack `CCD_POOLS + CCD_WORK_DIST + BARRIER_LOCAL_BETWEEN_OPS` (without NW) for opt-in research only.
- **EP frontdoor (+17% on Qwen3.6-35B Q8_0)** is the only confirmed production gain from CPU1+CPU2+CPU15 work; everything else is opt-in research.

### Memory references

- `project_l3aan_reverted.md` — full L3aaN result + literature integration
- `feedback_canonical_baseline_protocol.md` — `taskset -c 0-95 -t 96 -fa 1` + zombie check + 460 GB/s aggregate BW reference
- `feedback_llama_bench_fa_default.md` — ALWAYS pass `-fa 1` explicitly

---

## ⚑ L3aaN REVERTED 2026-04-26 evening — NPS4 is final

L3aaN evaluation completed. **Outcome: catastrophic regression across every measured config.** All 5 canonical production models regressed 30–52% vs NPS4 reference; the supposed BW-bound L3aaN target (Qwen3.6-35B Q8_0) regressed −44.5% canonical and −51.2% with the full EP stack (vs the +17.18 t/s reference). Decision: **revert to NPS4 via BIOS** (user-driven, ~30 min downtime).

L3aaN measurement table (canonical no-flags; full data in `progress/2026-04/2026-04-26.md`):

| Model | NPS4 | L3aaN canonical | L3aaN best (`--interleave=all`) | Δ best vs NPS4 |
|-------|------|-----------------|---------------------------------|----------------|
| Qwen3-Coder-30B-A3B Q4_K_M | 43.57 ± 0.10 | 23.07 ± 0.10 | 27.90 (96t) / **29.42** (24t) | **−32.5%** |
| Qwen3.6-35B-A3B Q8_0 | 14.63 ± 0.01 | 8.12 ± 0.01 | 8.32 ± 0.01 | **−43.1%** |
| Qwen3-Next-80B-A3B Q4_K_M | 23.25 ± 0.08 | 14.12 ± 0.05 | 15.93 ± 0.02 | **−31.5%** |
| REAP-246B-A35B Q4_K_M | 6.85 ± 0.01 | 3.30 ± 0.00 | 3.91 ± 0.02 | **−42.9%** |
| gemma-4-26B-A4B Q4_K_M | 25.01 ± 0.08 | 17.51 ± 0.04 | 18.62 ± 0.05 | **−25.6%** |
| Qwen3.6-35B Q8_0 + full EP | 17.18 (ref) | 8.39 ± 0.01 | (not retested at 12-way) | (canon −51%) |

Audit-driven supplemental sweep (post-canonical) tested: `GGML_NUMA_WEIGHTS=1` alone (+2%, deprecated), 3-flag stable stack `CCD_POOLS+CCD_WORK_DIST+BARRIER_LOCAL` (+2%, same as NPS4), `GGML_NUMA_REPACK_INTERLEAVE=0` kill-switch (neutral), `GGML_EP_N_INSTANCES=12` (neutral), `numactl --interleave=all` (largest lever: +13–21% on Q4_K_M models, +2.5% on Q8_0), thread sweep 96/48/24/12/8 (24t is the L3aaN sweet spot for Coder-30B), literature `--no-mmap + --numa distribute` recipe (matched `--interleave=all`, did not exceed). **Even the best stacked L3aaN config (Coder-30B 29.42 @ 24t with interleave) is −32.5% vs NPS4 single-instance reference 43.57, and −40% vs NPS4 documented peak 48.81.** Every production model still regresses 26–43% on best-known L3aaN config.

**12-rank concurrent-split aggregate (the L3aaN-designed workload pattern) was also measured**: 12 parallel `llama-bench` instances pinned per-CCD on Coder-30B Q4_K_M = **67.38 t/s aggregate vs NPS4 ~104 t/s = −35%**, with high per-instance variance (4 of 12 std > 3 t/s). HPC MPI ranks have private memory; llama.cpp inference shares the GGUF mmap, so pinning doesn't isolate weight reads.

Raw data: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-26-l3aan/`. After BIOS revert, canonical baselines should re-snap to the pre-reboot NPS4 reference (re-verify with the smoke-test command at the bottom of this block).

**Forward path post-revert**: Phase H (PPL gates) on NPS4. Then I → J → K → L → M. CPU16/CPU17/CPU18/CPU19 backlog (added 2026-04-26) is independent of NUMA topology and can proceed in parallel with the revert window.

## CPU25 — NUMA_MIRROR fork integration (CLOSED 2026-04-27, DECISIVE NEGATIVE)

Investigation complete. All 5 phases (0a, 0b, 1a, 1b, 1c) landed bit-exact on `feature/cpu-ep-inter-process` of `/mnt/raid0/llm/llama.cpp-experimental`. **Phase 2 throughput gate FAILED.**

| Model | Quant | tg128 baseline | tg128 mirror=4 | Δ |
|---|---|---|---|---|
| Coder-30B-A3B | Q4_K_M | 48.16 t/s | 47.66 t/s | **−1.0%** (within noise) |
| Qwen3.6-35B-A3B | Q8_0 | 23.30 t/s | 23.45 t/s | **+0.6%** (within noise) |

Phase 2 gate of ≥ +25% on Coder-30B was not met. Mirror is bit-exact PPL but does not deliver throughput.

**Root cause**: single-socket NPS4 EPYC 9655 is **DRAM-channel-bound**, not fabric-bound, at 96-thread saturation. Per-thread BW share is 460 GB/s ÷ 96 = 4.79 GB/s/thread regardless of NUMA placement. With mirror, each NPS4 node's 24 threads share 115 GB/s = identical 4.79 GB/s/thread. CPU24's perf-record memory-stall finding was correct but could not distinguish fabric-stall from DRAM-channel-stall; Phase 1c cleanly rules out the fabric-stall hypothesis. The vproxy-tools fork's reported +62%/+34% gains were on 2-socket configurations where cross-SOCKET fabric IS the binding constraint. **Reopen only if a 2-socket configuration becomes relevant.**

**Implementation kept for reference / future hardware** (Phase 1c is technically correct, infrastructure useful):
- `9b1dbf4dd` (0a) + `b9920cc44` (0b): `tensor_data()`/`tensor_set_data()` accessor + 164 refs migrated. Pure no-op in default builds.
- `ca39cb80a` (1a): `data_per_node[GGML_NUMA_MAX_NODES]` field + `tensor_set_data_per_node()` API.
- `90a17af62` (1b): TLS setter at graph-compute entry via `getcpu(2)`.
- `29a69599a` (1c): CPU_REPACK buffer-level mirror (per-buffer side-table tracks N anon-mmap+mbind replicas; init_tensor fans out per-node pointers, set_tensor copies primary→replicas after repack). Migrated `forward_mul_mat`/`forward_mul_mat_id` hot path (5 sites in `repack.cpp`) to `tensor_data()`.

**Disposition**: production stack should NOT enable `GGML_NUMA_MIRROR`. Default builds (no flag) compile to direct field access — zero overhead. Full handoff: [`numa-mirror-integration.md`](numa-mirror-integration.md).

## Entry point hierarchy for a fresh agent session

**(was "START HERE if resuming after L3aaN reboot" — superseded above; the entry list below remains accurate)**
1. `handoffs/active/master-handoff-index.md` (top-level — see row 27/27b for CPU work)
2. **this file** (`cpu-inference-optimization-index.md`) — CPU tracks + current status
3. `handoffs/active/nps-reboot-runbook.md` — **the "L3aaN evaluation plan — 2026-04-26 update" section is the post-reboot procedure**, with pre-reboot snapshot, decision matrix, and step-by-step
4. `progress/2026-04/2026-04-26.md` — full Phase A-G + P1-P4 narrative (today's session)
5. [`cpu-kernel-env-flags-inventory.md`](cpu-kernel-env-flags-inventory.md) — every env var classified
6. [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) — mandatory benchmark protocol + revalidation gate (CPU20)
7. [`cpu-openmp-runtime-scheduling-matrix.md`](cpu-openmp-runtime-scheduling-matrix.md) — Wave 1 runtime attribution matrix (CPU21)
8. [`cpu-uncore-fabric-attribution.md`](cpu-uncore-fabric-attribution.md) — Wave 1 >150B bottleneck attribution (CPU24)
9. [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md) — Wave 2 mechanism track (CPU22)
10. [`cpu-context-regime-coverage.md`](cpu-context-regime-coverage.md) — Wave 3 context/interference coverage (CPU23)
11. [`cpu-optimization-thesis-pause-2026-04-26.md`](cpu-optimization-thesis-pause-2026-04-26.md) — correction ledger for methodology/conclusion drift
12. [`orchestrator-nps4-48x4-notes.md`](orchestrator-nps4-48x4-notes.md) — concurrent topology reference (contention point for CPU15/CPU17 decisions)

**Current branch state** (post-NUMA_MIRROR closure 2026-04-27):
- `llama.cpp-experimental` on branch `feature/cpu-ep-inter-process` HEAD `29a69599a` — CPU2 SIMD wins, CPU15 EP P3.2 stack, CPU2 mbind kill-switch (`GGML_NUMA_REPACK_INTERLEAVE`, default ON), all NUMA_MIRROR Phase 0a/0b/1a/1b/1c (compile-flag-gated default-OFF, Phase 2 throughput gate FAILED for the reasons in `numa-mirror-integration.md`)
- Build: `/mnt/raid0/llm/llama.cpp-experimental/build/bin/` (default-flags, no NUMA_MIRROR), `/mnt/raid0/llm/llama.cpp-experimental/build_mirror/bin/` (`-DGGML_NUMA_MIRROR=4`), `/mnt/raid0/llm/llama.cpp-experimental/build_znver5/bin/` (`-march=znver5` non-mirror baseline)
- `LD_LIBRARY_PATH` MUST be prepended with the chosen build's `bin/` directory before benchmarks; system path has v4 production build first → "CPU backend not loaded" error otherwise

**Canonical baselines** (NPS4, proper canonical = `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active taskset -c 0-95 numactl --interleave=all -t 96 -fa 1 -mmp 0`, post-CPU21):

| Model | Quant | tg128 t/s ± std |
|-------|-------|-----------------|
| Qwen3-Coder-30B-A3B | Q4_K_M | 47.08-48.16 ± 0.04-0.15 |
| Qwen3.6-35B-A3B | Q8_0 | 23.04-23.30 ± 0.01-0.02 |
| Qwen3-Next-80B-A3B | Q4_K_M | ~22.15 (post-CPU21 estimate) |
| Qwen3-Coder-REAP-246B-A35B | Q4_K_M | 6.33 ± 0.00 |
| gemma-4-26B-A4B-it | Q4_K_M | ~38.59 (post-CPU21 estimate) |

**EP frontdoor honest delta** (Qwen3.6-35B-A3B Q8_0 with `GGML_EP_N_INSTANCES=2 GGML_EP_NUMA_PIN=1 GGML_EP_MASTER_ALL_NODES=1 GGML_EP_WORKER_DRONE=1 GGML_EP_SHARD=1`): +1.6% on proper canonical (was +17% on the earlier mmap=1 warmed reference; the larger figure was a baseline artifact per compounding-matrix). Bit-exact PPL preserved.

**Smoke-test command**:
```bash
LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build_znver5/bin \
  OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  taskset -c 0-95 numactl --interleave=all \
  /mnt/raid0/llm/llama.cpp-experimental/build_znver5/bin/llama-bench \
  -m /mnt/raid0/llm/lmstudio/models/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf \
  -t 96 -fa 1 -p 0 -n 128 -mmp 0 -r 3
# Expect 47-48 t/s on Coder-30B Q4_K_M (proper canonical)
```

**Earlier session's pre-NPS4 baseline freeze** (still on disk, lower-priority reference): `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/pre-nps4-freeze/SUMMARY.md`

**Tasks queued** (in TaskList): #12 (post-NPS4 re-bench + CPU1 decision), #13 (Phase 1.2 CCD work distribution), #14 (Phase 1.3 NUMA weight mbind), #11 (CPU4 sync primitive — NUMA-independent, can proceed regardless).

## ⚑ Methodology Hardening Gate (added 2026-04-26)

Before any new "exhausted" or "deployment-ready" claim, complete **CPU20** protocol and explicitly revalidate claims that were previously affected by:

- wrong baseline selection (`--numa distribute` vs canonical no-flags baseline)
- zombie-process contamination (`pgrep -af "llama"` not clean before benches)
- wrong shared-library resolution (v4 library loaded instead of experimental build)
- OpenMP preprocessor guard mistakes (code measured while compiled out)

Interpretation rule for the next session: claims from runs that violate the protocol are provisional and must be rerun before downstream decisions.

## Pipeline Waves (constructive flow across tracks)

Use this order so tracks compose instead of conflicting:

1. **Wave 0 — Integrity Gate**: CPU20 benchmark rigor + revalidation (must-pass)
2. **Wave 1 — Root-Cause Attribution**: CPU21 OpenMP runtime/scheduling matrix + CPU24 uncore/fabric attribution
3. **Wave 2 — Mechanism Work**: CPU22 dynamic MoE load balancing (only after Wave 1 identifies the dominant bottleneck class)
4. **Wave 3 — Regime Coverage**: CPU23 context matrix (2K/8K/32K + prefill/decode interference)
5. **Wave 4 — Existing Tracks Resume**: CPU1/CPU2/CPU15/CPU17/CPU18/CPU19 with revised evidence quality gates

## ⚑ NEW WORK ADDED 2026-04-26 (post research-intake batch — surface for fresh agent)

The 2026-04-26 research-intake batch (10 GPU-stack + 5 expansion entries, intake-458 to 472) added four CPU-applicable backlog items (CPU16–CPU19). These are independent of the L3aaN reboot — they can be picked up before, during, or after the reboot evaluation. Listed here so the post-reboot agent doesn't have to scroll the full backlog to find them.

| ID | Track | Source | Quick scope | Priority |
|----|-------|--------|-------------|----------|
| **CPU16** | NUMA prefill/decode disaggregation — feasibility (Phase 0 xGMI BW falsification gate) | DistServe (intake-459), Splitwise (intake-460), Mooncake (intake-472) + Tier 2b critique | Empirically measure xGMI sustained KV-cache-shaped transfer BW. If KV-transfer time at typical context lengths >10% of decode time, close stub. Otherwise prototype socket-level prompt/decode disagg. **Strong counter-evidence pre-recorded**. → [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md) | MEDIUM (feasibility-gated; could collapse to NOT-PURSUED) |
| **CPU17** | Sarathi-Serve / chunked-prefill evaluation on EPYC NUMA | Sarathi v1 (intake-469, superseded by intake-048 = Sarathi-Serve already_integrated upstream) | Sarathi-Serve achieves prefill/decode interference elimination WITHOUT KV migration — likely cheaper architectural win than CPU16 disagg. Test on llama-server with 4×48t NUMA shards: chunked-prefill enable + chunk size sweep. **Run before CPU16** if both are pursued. → [`sarathi-serve-cpu-evaluation.md`](sarathi-serve-cpu-evaluation.md) | MEDIUM-HIGH (if it works it likely obsoletes CPU16) |
| **CPU18** | MegaBlocks blocked-CSR-COO + transpose-indices port to CPU2 expert-GEMM | MegaBlocks (intake-467, adopt_patterns) | Port the **indexing scheme** (not the GPU kernel) into CPU2 AVX-512BW Q8_0 expert-GEMM path. Eliminates capacity-factor padding/dropping for CPU MoE expert dispatch. Compounds with the just-landed CPU2 +31.8% (1t) / +1-3% (12-96t) gains. | MEDIUM-HIGH |
| **CPU19** | Tutel 2DH (two-dimensional hierarchical) all-to-all port to CPU15 inter-process EP shared-memory ring | Tutel (intake-470, adopt_patterns) | Aggregate intra-CCD (or intra-NUMA) first, then inter-NUMA exchange. Target: reduce ~96 sync points/token to ~24. Directly addresses REAP-246B (-53%) and MiniMax-M2.7 (-23%) regression cause measured in CPU15 Phase 3.2. Compounds with CPU15's drone+shard. | MEDIUM-HIGH |

**One-line summary for fresh-session agent**: CPU16–CPU19 are the four CPU-applicable additions from the 2026-04-26 disagg / serving / MoE-engine intake batch. CPU17 (Sarathi-Serve) is the cheapest test and likely obsoletes CPU16. CPU18 + CPU19 are direct compounding plays on already-shipped CPU2/CPU15 work.

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

Ordered by expected single-instance decode throughput gain × feasibility, with the Wave-0 integrity gate first.

- [ ] **CPU20 — CRITICAL (new 2026-04-26)** Benchmark rigor + revalidation gate → see [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md). Canonicalize environment, process hygiene, cache-state protocol, and baseline policy before any new optimization claim. Re-run headline claims that were previously impacted by methodology drift.
- [ ] **CPU21 — HIGH (new 2026-04-26)** OpenMP runtime/scheduling matrix for sync-heavy Q4_K_M class → see [`cpu-openmp-runtime-scheduling-matrix.md`](cpu-openmp-runtime-scheduling-matrix.md). Compare libgomp/libomp, schedule/chunk policies, and affinity permutations before declaring sync-class software levers exhausted.
- [ ] **CPU24 — HIGH (new 2026-04-26)** REAP-class uncore/fabric counter attribution (IMC/channel/fabric/remote-miss) → see [`cpu-uncore-fabric-attribution.md`](cpu-uncore-fabric-attribution.md). Mandatory before closing >150B EP root-cause analysis.
- [ ] **CPU22 — HIGH (new 2026-04-26)** Dynamic MoE expert load balancing (work stealing/runtime rebalance) → see [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md). Follow-on to static-modulo sharding failures targeting structural expert-imbalance.
- [ ] **CPU23 — MEDIUM-HIGH (new 2026-04-26)** Full context-regime matrix (2K/8K/32K + long-prompt-mid-stream interference) → see [`cpu-context-regime-coverage.md`](cpu-context-regime-coverage.md). Prevents decode-only overgeneralization.
- [ ] **CPU1 — HIGH (top, NPS4 locked, Phase 1.4 shipped; CPU1-track-specific levers exhausted)** Intra-process tensor-parallel decode → see `intra-process-tensor-parallel-decode.md`. **Single-instance best 48.81 ± 0.08 t/s at 48 threads with `-fa 1`** (full stack: `GGML_CCD_POOLS=1 GGML_NUMA_WEIGHTS=1 GGML_CCD_WORK_DIST=1 GGML_BARRIER_LOCAL_BETWEEN_OPS=1`). Phase 1.4 landed and PPL-verified. Post-Phase-1.4 perf profile: barrier 28%, GEMV 33.5%, other 38%. Concurrent teardown hang non-reproducible (closed; resolved by cpuset fixes `0ade7bd4d`+`69b4c3fa4`). **Op-fusion Phase 2 reverted (2026-04-24)** — was correct (PPL bit-exact) but throughput-neutral in both fa=0 and fa=1; attention-internal fusion is already done by `ggml_flash_attn_ext` so fusion infra had no remaining leverage target. Reverted as `c34aac61b` + `138b26cd4`. **GEMV VNNI probe (2026-04-24) also net-negative** — added AVX-512VNNI path to `ggml_gemv_q4_K_8x8_q8_K` (PPL bit-exact); throughput slightly regressed because on Zen 5 VPMADDUBSW runs at 2/cycle while VPDPBUSD is only 1/cycle. Not committed. **The CPU1-track-specific levers are exhausted** (per memory `project_cpu1_software_levers_exhausted.md`); broader "CPU-general software runway exhausted" framing was over-generalized — see narrowing in CPU25 row (NUMA_MIRROR closure) and the open tracks list below. Next meaningful gates were L3-as-NUMA BIOS reboot (item 27b — REJECTED) and NUMA_MIRROR (item 27f — CLOSED NEGATIVE 2026-04-27).
- [ ] **CPU2 — AVX-512BW kernel + NUMA fix LANDED 2026-04-24, production-viable** Shape-specialized GEMV microkernels → see `cpu-shape-specialized-gemv-decode.md`. Session 15 landed (commits `1d18efce3` + `e84a5c82f` + `ba1c23900` on branch `cpu-optimization/q8-8x8-avx512bw`): AVX-512BW 8x8 Q8_0 GEMV kernel (hot loop emits `vpmaddubsw`+`vpmaddwd`, deliberately bypassing the VNNI-auto-selecting helper — Zen 5 falsified VNNI twice already), plus auto-`mbind(MPOL_INTERLEAVE)` on the CPU_REPACK buffer when `ggml_is_numa()`, plus an env-gated `gated_delta_net` S_v sub-chunking refactor (default off — a probe that disproved DeltaNet as the bottleneck). **Final performance on Qwen3.6-27B-Q8_0** at 96t = 4.39 vs baseline 4.32 (+1.6%); at 1t = 1.12 vs 0.85 (+31.8%). PPL on Wikitext-2 = 6.6985 (preserved). **The 4.4 t/s ceiling is NOT memory-bandwidth** — only 26% of theoretical 460 GB/s vs Qwen2.5-Coder-32B dense at 41% on same hardware. Real bottleneck unidentified; next session should be a `GGML_PERF=1` profile, not more kernel work. **No env gates required** — auto-mbind runs automatically on multi-NUMA systems; the `GGML_Q8_0_8X8` + `GGML_Q8_0_8X8_AVX` flags remain default OFF for rollout caution. **Follow-ups**: profile-then-fix Qwen3.6-27B decode at 96t to find the real ceiling cause, Q6_K + Q5_K 8x8 kernels (Session 14 flagged both as dispatcher-NEON-only gaps, ~2× Q8_0 complexity for bit-split unpack), upstream the `mbind` fix (general bug affecting every multi-NUMA repacked quant).
- [ ] **CPU3 — HIGH** System-level tuning (NPS mode, hugepages, barrier, IRQ, SMT) → see `single-instance-system-tuning.md`. 15–40% alone; a prerequisite for the full CPU1 gain under NPS4/L3aaN. **Zero-reboot knobs partially applied 2026-04-23** (THP→always, numa_balancing=0, 1GB hugepages — net within noise on canonical baseline).
- [ ] **CPU4 — COMPLETE (negative single-variant result, 2026-04-26)** Hierarchical OpenMP barrier variant tested and reverted (net-negative). Do not pursue further barrier-primitive surgery until CPU21 runtime matrix completes and confirms residual sync opportunity.
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
- [ ] **CPU15 — HIGH (new 2026-04-24)** Large-MoE as primary target + expert parallelism → see [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md). Two linked tracks: (A) strategic reframe — target large sparse MoE (≥100B total, ≥10B activated, ≥64 experts) to exploit the hardware's RAM:BW ratio and the 2.13× concurrent-aggregate gap (48.81 → ~104 t/s); (B) expert-parallelism mechanism — shard experts across CCDs/NUMA nodes/processes to convert aggregate BW into single-stream throughput. Phase 0 is a cheap 4–6 h baseline (re-measure Qwen3-235B-A22B + 480B-A35B on current NPS4 + `GGML_NUMA_WEIGHTS=1` + AVX-512BW stack) that falsifies or opens the mechanism work. Expected gain 2–5× single-stream on large MoE. Contends with `orchestrator-nps4-48x4-notes.md` for NUMA topology — Decision Point D2 in the child handoff. **Important correction**: >150B regressions observed so far are real, but aggregate-DDR saturation is not the proven root cause; CPU24 attribution remains open.
- [ ] **CPU16 — MEDIUM (new 2026-04-26, feasibility-gated)** NUMA-disaggregated prefill/decode → see [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md). Inspired by DistServe (intake-459), Splitwise (intake-460), Mooncake (intake-472). Phase 0: empirical xGMI sustained KV-cache-shaped transfer BW measurement. **Strong Tier 2b counter-evidence pre-recorded in stub**: disagg can REGRESS 20-30% on small/short workloads, EPYC xGMI ~64 GB/s vs NVLink ~900 GB/s makes KV-transfer tax proportionally worse, single-user CPU regime is the wrong regime. Phase 0 gate: if KV-transfer time at typical context lengths >10% of decode time, close stub. Likely obsoleted by CPU17 — pursue CPU17 first.
- [ ] **CPU17 — MEDIUM-HIGH (new 2026-04-26)** Sarathi-Serve / chunked-prefill evaluation on EPYC NUMA → see [`sarathi-serve-cpu-evaluation.md`](sarathi-serve-cpu-evaluation.md). Sarathi-Serve (intake-048, already_integrated upstream) achieves prefill/decode interference elimination WITHOUT KV migration — the cheaper architectural alternative to CPU16 disagg. Scope: enable chunked-prefill in llama-server, sweep chunk size on 4×48t NUMA shards, measure decode-stall reduction during long-prompt-mid-stream scenarios. Sarathi v1 (intake-469) authors explicitly note disagg "could be challenging in the absence of high-bandwidth interconnects" — this is the CPU-appropriate path. **If it works on our regime, it likely obsoletes CPU16**.
- [ ] **CPU18 — MEDIUM-HIGH (new 2026-04-26)** MegaBlocks blocked-CSR-COO + transpose-indices port to CPU2 expert-GEMM. MegaBlocks (intake-467) introduced dropless MoE via block-sparse grouped GEMM. The **indexing scheme** (blocked-CSR-COO + transpose indices) is the transferable artifact for CPU MoE expert dispatch — eliminates capacity-factor padding/dropping. Port into CPU2 AVX-512BW Q8_0 expert-GEMM path (cpu-shape-specialized-gemv-decode.md). Compounds with CPU2's just-landed +31.8% (1t) / +1-3% (12-96t) gains. NOT a GPU kernel port.
- [ ] **CPU19 — MEDIUM-HIGH (new 2026-04-26)** Tutel 2DH all-to-all port to CPU15 inter-process EP shared-memory ring. Tutel (intake-470) introduced two-dimensional hierarchical all-to-all that aggregates intra-node first, then inter-node exchange. Maps onto our 4-NUMA-node × 12-CCD topology. Target: reduce ~96 sync points/token to ~24 via intra-CCD combine first, then inter-NUMA exchange. Directly addresses CPU15 Phase 3 measured regression cause for REAP-246B (-53%) and MiniMax-M2.7 (-23%). Phase 3.4 candidate stub for [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md).

Primary active backlog is CPU20–CPU24 (wave pipeline), then CPU1/CPU2/CPU3/CPU15/CPU16–CPU19. CPU9–CPU14 remain watchlist items; pursue only when higher-priority work is gated.

---

## Handoff Landscape

| ID | Handoff / work | Status | Priority | Gain target | Blocks / blocked by |
|----|---------------|--------|----------|-------------|---------------------|
| CPU1 | [`intra-process-tensor-parallel-decode.md`](intra-process-tensor-parallel-decode.md) | **Phase 1.3 v1 IMPLEMENTED 2026-04-24; NPS4 locked** | **HIGH (top, in flight)** | Phase 1.3 v1 alone +140%; with CPU1 P1.0+1.1 +156% vs baseline; 39.59 single-inst (88% NPS2) | Phase 1.3 v2 (per-tensor stripe, 2d) + Phase 1.2 (CCD work dist, 2-3d) next. |
| CPU2 | [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) | **Session 15 AVX-512BW 8x8 kernel + NUMA auto-mbind LANDED 2026-04-24** | production-viable | 1t: +31.8% ; 12-96t: +0.9-2.9% (BW-saturated ceiling) | Q6_K/Q5_K are the natural follow-ons (same NEON-only dispatcher gap, ~2× complexity) |
| CPU3 | [`single-instance-system-tuning.md`](single-instance-system-tuning.md) | **Phase 0 + zero-reboot knobs partial 2026-04-23** | HIGH | 15–40% alone; gating multiplier for CPU1 | Phase 2 requires reboot; coordinates with CPU1 Phase 3 |
| CPU4 | [`cpu-hierarchical-barrier.md`](cpu-hierarchical-barrier.md) | **COMPLETE 2026-04-26 (negative for tested variant)** | MEDIUM (conditional reopen) | Falsified one custom barrier path; no deployable gain | Reopen only after CPU21 if runtime evidence still indicates sync headroom |
| CPU5 | 1 GB hugepages | DEPRIORITIZED (post-Phase-2.6 — DRAM channel-bound finding limits expected gain) | LOW | 5–15% but not MoE-class | Reopen if v5+1 explicitly evaluates long-context decode (kernel boot param required) |
| CPU6 | ZenDNN 5.2 eval | DEPRIORITIZED (CPU24 attribution shows compute kernels memory-stalled; ZenDNN's GEMM optimizations target compute-bound paths) | LOW | Unknown; AMD claims up to 2× but for GEMM-dominated workloads | Reopen only if v5+1 finds compute-bound regime change |
| CPU7 | tinyBLAS / llamafile integration | DEPRIORITIZED (CPU2's AVX-512BW + Q6_K SIMD already cover the primary CPU-GEMV gap) | LOW | Partially supplants CPU2 | Fork-merge complexity vs marginal gain (CPU2 already has the NEON-only-dispatcher gap closed for Q6_K) |
| CPU8 | Per-NUMA weight replication | ✅ **CLOSED** — superseded by CPU25 NUMA_MIRROR (DECISIVE NEGATIVE on single-socket NPS4) | n/a | Was 10-30% target; CPU25 found 0% on single-socket | Reopen ONLY for 2-socket configurations |
| CPU9 | Dense-weight sparsity | DEPRIORITIZED (research-stage; GPU prior art only; dense is least promising class per CPU24) | LOW | Unknown | Reopen if a quality-preserving sparsity method emerges |
| CPU10 | Sub-Q4 quant eval | partial (via glm51-reap, tq3 intake) | LOW | Per-model | Overlaps with quality handoffs |
| CPU11 | Compiler / PGO / LTO | ACTIVE (queued for v5+1) | MEDIUM (post-Phase-2.1 finding) | clang-20 + libomp + -march=znver5 already gives +6.4% on Coder-30B (Phase 2.1); PGO/LTO is the next compiler-level lever | Build env complexity; consider after v5 ships |
| CPU12 | BOLT / FDO binary post-link | ACTIVE (queued for v5+1) | LOW-MEDIUM | 1-3% (mature tooling); compounds with CPU11 PGO | Build env complexity; consider after v5 ships if CPU11 motivates |
| CPU13 | Prefill optimizations | DEPRIORITIZED (CPU23 Phase 2.2 confirmed long-context prefill scales nonlinearly but no specific kernel-level lever surfaced; chunked-prefill obsoleted by CPU17 single-user-no-signal closure) | LOW | Prefill-specific | Reopen if multi-tenant production becomes a goal |
| CPU14 | `--parallel` slot decode bench | DEPRIORITIZED (orchestrator concurrency deferred indefinitely per user direction post-NUMA_MIRROR closure; covered partially by existing `dynamic-stack-concurrency.md`) | LOW | Aggregate only | Reopen when Tier 2 (concurrency policy) un-defers |
| CPU15 | [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) | **Phase 3 COMPLETE 2026-04-26** — EP **+100% bit-exact PPL on Qwen3.6-35B-A3B**, +6% on gemma-26B-A4B; **REAP-246B confirmed REGRESSION** at -53% even with eager-warm + all flags | **HIGH** | Phase 3.0 IPC RTT 0.73 μs; Phase 3.1 library `f47bec4`; full Phase 3.2 stack a→h all live. **Production routing (current evidence)**: frontdoor-class Q8_0 can benefit; >150B class currently regresses and stays single-instance pending deeper attribution. | Phase 1/2 intra-process EP all D3-failed; Phase 3 inter-process beats single-instance on medium MoE; **root cause for >150B still open (see CPU24)** |
| CPU20 | [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) | **ACTIVE — backfill policy + Phase 2.5 backfills DONE 2026-04-28** | **CRITICAL** | Prevent invalid conclusions; enforce reproducible baselines | Gates all CPU tracks before new claims; ongoing protocol enforcement |
| CPU21 | [`cpu-openmp-runtime-scheduling-matrix.md`](cpu-openmp-runtime-scheduling-matrix.md) | **ACTIVE — Phase 2.1 COMPLETE 2026-04-28: libomp +6.4% on Coder-30B Q4_K_M (apples-to-apples)** | HIGH | Recover sync-class throughput; **major v5 cherry-pick implication** | clang-20 + libomp + -march=znver5 universal binary recommended for v5 |
| CPU22 | [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md) | **ACTIVE — work-stealing prototype upcoming (Phase 3 of remediation)** | HIGH | Address structural expert imbalance left by static modulo sharding; gain bounded by CPU24's 15% sync ceiling | Phase 3 binding gate ≥10% on 2 sync-bound models |
| CPU23 | [`cpu-context-regime-coverage.md`](cpu-context-regime-coverage.md) | **CLOSED 2026-04-28 for 3-proxy minimum-gate scope (Phase 2.2)** | MEDIUM-HIGH | Prevent decode-only overgeneralization | First-decode TTFT 9.6× amp on sync-bound MoE; steady-state continuous batching efficient on all 3 classes; full 5-model coverage explicitly deferred |
| CPU24 | [`cpu-uncore-fabric-attribution.md`](cpu-uncore-fabric-attribution.md) | **CLOSED 2026-04-28 (Phase 2.3) — attribution `compute_kernel_memory_stalled` confirmed across 4 architectural classes** | HIGH | Identify true bottleneck class | IPC 0.17-0.28 universal; striking new finding: dense is 3× more cache-efficient than MoE |
| CPU16 | [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md) | **STUB 2026-04-26** — qualified feasibility study, Tier 2b counter-evidence pre-recorded | MEDIUM (feasibility-gated) | TBD — Phase 0 falsification gate first | Likely obsoleted by CPU17 — pursue CPU17 first |
| CPU17 | [`sarathi-serve-cpu-evaluation.md`](sarathi-serve-cpu-evaluation.md) | **ACTIVE plan scaffold 2026-04-26** | MEDIUM-HIGH | Decode-stall reduction during long-prompt-mid-stream; targets CPU16 obsolescence | Feeds CPU23 regime matrix; inherits CPU20 protocol |
| CPU18 | MegaBlocks indexing port (line item; subsection of [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) on first session) | **PENDING — not started** | MEDIUM-HIGH | Padding-free CPU MoE expert dispatch; compounds with CPU2 wins | Compounds with CPU2 |
| CPU19 | Tutel 2DH port (line item; subsection of [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) Phase 3.4 on first session) | **DEPRIORITIZED — sync ceiling 15% per CPU24 caps gain at ~7-8% best-case** | MEDIUM-HIGH | ~96 → ~24 sync points/token target | Reopen only if CPU22 prototype indicates sync-share above 15% on a workload |
| CPU25 | [`numa-mirror-integration.md`](numa-mirror-integration.md) | **CLOSED 2026-04-27 — DECISIVE NEGATIVE on single-socket NPS4** | ~~HIGH~~ | Phase 1c LANDED bit-exact; Phase 2 throughput gate FAILED (-1.0% Coder-30B Q4_K_M, +0.6% Qwen3.6-35B Q8 — both noise) | Hardware is DRAM-channel-bound, not fabric-bound; reopen only on 2-socket configs |
| MoE-Spec | [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) | **NEW 2026-04-27 — handoff stub created** | MEDIUM | Budgeted-expert spec-dec verification: 5-15% claimed on Coder/REAP per arXiv 2602.16052 | Phase 4 of remediation plan creates the handoff; falsification probe TBD |

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

**Critique-integration dependencies (2026-04-26):**
- **CPU20** is the quality gate for all new claims. No optimization closure without protocol-compliant reruns.
- **CPU21 + CPU24** must precede any renewed "sync-class exhausted" or ">150B root cause closed" declaration.
- **CPU22** should not start until CPU21/CPU24 identify where imbalance dominates.
- **CPU23** must run before final class-level production guidance, to avoid decode-only bias.

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
- Protocol source of truth: [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) (CPU20).

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
- 2026-04-26: CPU16/CPU17/CPU18/CPU19 added from the 2026-04-26 research-intake batch (intake-458 through 472). CPU16 = NUMA prefill/decode disagg feasibility (with stub + pre-recorded Tier 2b counter-evidence). CPU17 = Sarathi-Serve chunked-prefill eval (likely obsoletes CPU16). CPU18 = MegaBlocks blocked-CSR-COO indexing port to CPU2. CPU19 = Tutel 2DH all-to-all port to CPU15. ⚑ START HERE block updated; Prioritized Task List + Handoff Landscape updated. New work is independent of the L3aaN reboot — can be picked up before/during/after.
- 2026-04-25: CPU15 Phase 3.2 a→e.2 added 8 commits on `llama.cpp-experimental:feature/cpu-ep-inter-process` plus 5 docs commits on `epyc-root:main`. **REVISED 2026-04-25 evening**: Phase 3.2(e.1) attempt revealed all 8 prior commits were inside `#ifndef GGML_USE_OPENMP` guards and stripped from the production build. Commit `e001b3eda` extracted inter-process EP from those guards; first honest measurement is no-flags EP path bit-exact at 19.4 t/s = 68% of single-instance baseline 28.5 t/s. `GGML_EP_WORKER_DRONE=1` and `GGML_EP_SHARD=1` were initially PPL-broken — root-caused to EP top block ordering AFTER the src1 quantization loop (workers' uninitialized src1 quantized into wdata before broadcast delivered correct data). **`ff6833b19` moved the EP top block before quantization with a barrier; drone + shard now bit-exact. EP N=2 + drone + shard = 30.3 t/s = 106% of single-instance baseline = +6% over baseline.** Architecture validated; PPL gate (f) on WikiText-2 + REAP-246B D3' gate (g) ≥+20% over 6.16 t/s are the remaining work.
- 2026-04-26: CPU15 Phase 3 COMPLETE. (g.1) eager parallel shard warm-up landed in `43c65b926` — collective `ggml_barrier`-coordinated parallel memcpy collapses ~250 ms single-threaded first-call cost on REAP-246B-class tensors to ~250 μs across all 96 master threads. Unblocked REAP-246B steady-state measurement: **−53% vs baseline (3.26 t/s vs 6.89)**. Master-all-nodes + park combo would not finish (master-parker spinning threads contend for cores with workers, per-tensor warm cost ~20 sec instead of 2 ms). Current conclusion: EP is a narrow win on frontdoor-class Q8_0; >150B-class remains regressive on measured configs. **Root-cause not closed by aggregate-bandwidth framing; attribution continues under CPU24.**
- 2026-04-26: Critique-integration pass added **CPU20–CPU24**. Wave-based flow now enforces: integrity gate → root-cause attribution → mechanism work → context-regime coverage before final deployment claims.
- 2026-04-26 (later): Added dedicated handoffs for **CPU21/CPU22/CPU23/CPU24** and re-framed CPU4 as a falsified single-variant track (not full sync-class closure). Updated landscape to link wave tracks directly.
