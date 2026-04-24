# Orchestrator Rework Notes — NPS4 48×4t Concurrent Production Deployment

**Status**: NOTES-ONLY (no implementation yet)
**Created**: 2026-04-24 post-NPS4-reboot session
**Owner**: follow-up after CPU1 Phase 1.3 evaluation completes
**Parent**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)

## Why this file exists

User request 2026-04-24: "orchestrator work is not an issue. We'll tackle that bridge when we get there. Just make notes along the way so we don't have to rediscover complications from scratch again."

Running notes on what would be needed to deploy 48×4t concurrent under NPS4 as a production option. Add to this file as discoveries accumulate.

## Measured opportunity (from post-NPS4 re-bench)

| Layout | 30B-A3B Q4 aggregate (t/s) |
|---|---|
| 4×48t NPS4-native (1 inst/node) | 36.17 |
| 4×24t phys-only NPS4-native | 37.12 |
| **48×4t NPS4-native** | **104.35** |
| NPS2 4×48t baseline (est.) | ~45-50 |

48×4t under NPS4 with strict per-node `membind` + 12 instances per NUMA node (each 2 phys + 2 SMT cores) = **~3× current production aggregate** on the worker model.

## Concrete orchestrator changes required

### 1. Instance multiplicity per role

Current config: `orchestrator_stack.py` launches 1–4 `llama-server` instances per role (frontdoor 4, coder 4, worker 1, architects 2).

48×4t pattern requires: 48 tiny instances per model, each pinned to a 2-phys + 2-SMT cpuset bound to one NUMA node.

- Need to decide per-role how to slice: frontdoor 48 tiny instances? Or 12 per node mixed across roles?
- Per-role instance ceiling was soft-capped around 4 historically for latency reasons; 48× breaks that assumption.

### 2. CPU-set and NUMA-node scheduling

Each instance needs:
- `numactl --membind=<node>` (4 values rotated)
- `taskset -c "<phys_lo>-<phys_hi>,<smt_lo>-<smt_hi>"` (2 phys + 2 SMT contiguous)
- `--threads 4`

Current code in `orchestrator_stack.py` builds cpuset via NPS2-aware layout (48 phys per node). Needs NPS-aware template using:

```
node 0: phys 0-23,   SMT 96-119
node 1: phys 24-47,  SMT 120-143
node 2: phys 48-71,  SMT 144-167
node 3: phys 72-95,  SMT 168-191
```

Instance `i` with `i ∈ [0,48)`:
- node = i / 12
- j = i % 12
- phys_base = node * 24 + j * 2
- SMT_base = 96 + node * 24 + j * 2
- cpuset = `{phys_base}-{phys_base+1},{SMT_base}-{SMT_base+1}`

### 3. Port assignment

48 distinct listening ports per role × N roles. Current scheme usually reserves a block per role (e.g. 8080–8083 for frontdoor). Bump to 48-wide blocks.

### 4. Router dispatch

Currently the router distributes across ~4 backends using a round-robin or least-loaded policy. At 48 backends:
- Round-robin still works but health-checks scale
- Connection-pool sizing: each client holds N connections per role — at 48 that's 48 × N total

### 5. Memory budget

Each instance holds the model in RAM. With `mmap` (not `mlock`), kernel page cache deduplicates file-backed pages across instances on the SAME node. BUT with `membind`, each instance's first-touch can land pages differently. Need to verify dedup actually happens — if NOT, 48 × 17 GB = 816 GB RAM for worker alone. With dedup: 1 × 17 GB reused.

**Open question**: does `mbind` + shared mmap dedupe across instances on the same node? Tested indirectly during NPS4 48×4t bench — `free -g` stayed low, suggesting dedup works — but confirm explicitly before deployment.

### 6. Single-user latency vs aggregate throughput trade-off

Per-instance throughput at 48×4t = 2.4 t/s (104 / 48 on 30B-A3B Q4). That's an unacceptable single-user latency for interactive use.

Orchestrator needs a TIERED routing policy:
- **Cold or first request**: route to a larger single-instance backend (single-node 24t) for low latency
- **Under load**: spill to 48×4t concurrent pool for aggregate throughput
- **Idle period**: scale down concurrent pool to save core utilization / power

This is a significant policy change — closer to autoscaler logic than current static config.

### 7. Model load time

Launching 48 × llama-server instances serially with model load = ~48 × 10s = 8 minutes. Parallel launch deadlocks on mmap mlock per memory `feedback_sequential_model_loading.md` (concurrent mlock crashes).

Without mlock, parallel launch should work. But mmap page-fault storms may contend. Need staged launch — e.g. 4 parallel, wait for healthy, next 4, etc.

### 8. Speculative decoding and draft routing

Current routing uses draft/target pairs (frontdoor+draft, coder+draft). Each 48×4t pool member needs its own draft OR a shared draft server:
- 48 drafts = 48 × 1GB draft models = 48 GB per role
- Shared draft pool (4-8 instances) + routing layer

Open design question.

### 9. Quarter scheduler

`feedback_numa_concurrency_complexity.md` notes that quarter-scheduling needs dedicated design. 48×4t is another step beyond.

### 10. Health checks and restart

Current health-check is per-instance curl of `/health`. At 48 instances that's 48 curls per cycle. Restart scenario: if one crashes, respawn it without disrupting the others (already handled, just higher rate).

## Open design questions

1. Does kernel dedupe mmap across same-node `mbind`'d instances? (Critical — determines RAM budget)
2. Latency-aware routing policy (spill to concurrent pool only under load)?
3. Single-node (24t) vs concurrent (48×4t) vs mixed — which per role?
4. Draft model: per-instance vs shared pool?
5. Staged launch to avoid mmap contention?
6. What happens to request cancellation at 4 threads (shorter cancellation windows)?

## References to revisit when implementing

- `epyc-orchestrator/scripts/server/orchestrator_stack.py` — current stack launcher
- `epyc-orchestrator/orchestration/model_registry.yaml` — current role/numa_config
- `feedback_mmap_numa_sharing.md` (memory) — `--mlock + numactl --membind` pattern
- `feedback_sequential_model_loading.md` (memory) — no parallel model load
- `feedback_numa_concurrency_complexity.md` (memory) — quarter scheduler complexity
- `handoffs/active/dynamic-stack-concurrency.md` — related aggregate-throughput work
- `data/cpu_optimization/2026-04-24-nps4/concurrent/` — measured per-instance numbers

## Changelog
- 2026-04-24 — created; initial notes from 48×4t NPS4 measurement session
