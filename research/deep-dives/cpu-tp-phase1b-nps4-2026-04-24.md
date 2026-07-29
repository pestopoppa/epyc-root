# CPU1 TP-Sharding — Phase 1b NPS4 Re-bench (2026-04-24, later session)

**Status**: measurement complete — decision pending
**Predecessor**: `cpu-tp-phase1a-ccd-barrier-2026-04-24.md` (NPS2 ceiling analysis)
**Context**: after 2026-04-24 morning session concluded that Phase 1.0+1.1 under NPS2 cannot exceed ~5% due to uniform NUMA topology (distance 10/12), the user rebooted into NPS4 to test whether 4-way NUMA unlocks the TP-sharding projection (2-5× per the handoff).

## Method

Under NPS4: 4 nodes × 24 physical cores × 3 DDR channels. Re-ran the canonical benchmarks from `cpu-tp-phase1a-ccd-barrier-2026-04-24.md` plus new NPS4-native concurrent-split layouts. All raw data: `data/cpu_optimization/2026-04-24-nps4/`.

## Findings

### 1. CPU1 Phase 1.0+1.1 DOES deliver under NPS4 — but only with `interleave=all`

| Build/Config (96t, 30B-A3B Q4) | NPS2 | NPS4 |
|---|---|---|
| OMP flat | 47.17 | 21.03 |
| OMP + `interleave=all` | — | 25.35 |
| noOMP flat | 38.87 | 14.01 |
| noOMP + CCD pools (P1.0+1.1) | 44.85 | 15.07 |
| noOMP + CCD + `interleave=all` | — | **27.86** |

Gain vs OMP+interleave (which is the best non-CCD NPS4 layout): **+12.5%**. This meets the runbook's `>10%` gate to proceed with Phase 1.2/1.3.

Without explicit `interleave=all`, the model mmap gets first-touched to a single NUMA node (observed via `numastat`: ~18 GB on node 2 alone after a single bench run), leading to catastrophic 75%-remote-access ratios. CCD pools alone (no interleave) barely help (14.01 → 15.07) because the memory topology problem dominates the thread-scheduling fix.

### 2. Absolute performance regresses vs NPS2

Single-instance under NPS4 best layout = 27.86 vs NPS2 pre-reboot 44.85 (−38%). The 3-channel vs 6-channel per-node geometry and 4-domain directory coherency impose a fixed tax that software interleave does not fully erase.

### 3. Concurrent 48×4t NPS4-native is the new peak

With strict per-node `membind` and 12 instances per NUMA node:
- 30B-A3B Q4 aggregate: **104.35 t/s** (up from 4×48t's 36.17)
- Compare to pre-reboot NPS2 48×4t 35B-A3B Q8 = 135 t/s — the peak pattern survives NPS4 for suitable workloads.

This is "embarrassingly parallel" throughput: many small independent sessions each bound to one NUMA node. Requires orchestrator rework to deploy.

### 4. 4×48t production pattern regresses

Frontdoor 35B-A3B Q4 at 4×48t NPS4 = 37.74 t/s vs NPS2 registry ~50.8 (−26%). The production "quarter-socket per instance" pattern is worse under NPS4 — even though each quarter is now on its own NUMA node (better than NPS2's cross-node quarters), the 3-channel per-quarter BW constraint dominates.

### 5. Why `--interleave=all` under-delivers

Three independent causes contribute to the NPS4 single-instance regression:

1. **Remote-access ratio rises.** NPS4 interleave → each thread has 75% remote pages (3 of 4 non-local). NPS2 interleave → 50%. Identical aggregate BW, 1.5× hop-latency cycle cost.
2. **Within-node stripe halves.** Burst BW per thread for sequential access = 3 channels instead of 6. Interleave moves the *next* page, not the current one's channel count.
3. **Directory coherency overhead.** EPYC directory-based coherency across 4 domains has more lookup/snoop paths than 2.

Tested `numa_balancing=1` (20.42 t/s vs 21.03 with it off) — migration during active decode is net negative.

## Decision analysis

| Option | Effort | Single-inst | Production 4×48t | Peak concurrent | Risk |
|---|---|---|---|---|---|
| 1. Rollback to NPS2 | 1 reboot | 47 (restored) | 50.8 (restored) | ~135 (est.) | low |
| 2. Stay NPS4 + Phase 1.3 mbind | 2-3 days | ? (goal: ≥40) | ? | 104+ | medium |
| 3. Stay NPS4 + deploy 48×4t prod | orchestrator config | 28 | ~40 (orch-change) | 104 | latency↑↑ |
| 4. Reboot to L3aaN | 1 reboot | likely worse | likely worse | possibly higher | higher regression |

**Recommendation**: Option 2. Phase 1.3 NUMA-bound weight mbind is specifically designed for this topology — when each thread group accesses only local-node weights (via replicated mbind), the 3-channel BW limit becomes per-group, and 4 groups × 3 channels = 12 channels in parallel. Theoretical ceiling approaches NPS2 aggregate. If the measurement after Phase 1.3 shows ≥40 t/s single-instance, we keep NPS4 and bank the +12.5% CCD gain + the concurrent peak. If it stalls below 35, rollback to NPS2.

## Phase 1.3 implementation sketch

Weights at model load are mmap'd from the GGUF file as a single contiguous region, then first-touched by whichever thread faults them. Phase 1.3 replaces this with:

1. For each weight tensor, after mmap'ing, call `mbind(addr, len, MPOL_BIND, node_mask_all, ..., MPOL_MF_STRICT | MPOL_MF_MOVE)` with **interleave at a larger granularity** (e.g. stripe 16 MB chunks round-robin across nodes). Alternative: *replicate* hot weight tensors on all 4 nodes and have the scheduler pick the local copy.
2. Combine with `--mlock` to force pages resident where mbind placed them.
3. Gate by env var `GGML_NUMA_WEIGHTS=1`. Default off.
4. Requires `libnuma-dev` (already installed 2026-04-24 morning).
5. Interaction with CCD pools: Phase 1.2 (CCD-aware work distribution) is the scheduler side that picks the local weight copy.

Estimated effort: 2-3 days (Phase 1.3 alone) + 2-3 days (Phase 1.2 work distribution). Phase 1.2 is lower-impact alone; run after 1.3 lands.

## References

- `handoffs/active/nps-reboot-runbook.md` — full runbook and decision tree
- `handoffs/active/cpu-inference-optimization-index.md` — CPU1-14 backlog
- `handoffs/active/intra-process-tensor-parallel-decode.md` — CPU1 handoff
- Pre-reboot freeze: `data/cpu_optimization/pre-nps4-freeze/SUMMARY.md`
- Post-reboot data: `data/cpu_optimization/2026-04-24-nps4/SUMMARY.md`
