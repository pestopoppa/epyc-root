# CPU15 — Large-MoE Expert Parallelism Disposition

**Status**: COMPACTED 2026-05-28. Phase 0-3 implementation/evidence history moved to the completed ledger. Current state: EP machinery is bit-correct and useful as default-off experimental infrastructure, but the production throughput claim was downgraded after canonical-baseline correction. Do not enable EP in production without a fresh CPU20-compliant canonical matrix.
**Priority**: MEDIUM as a guarded reopen target; not an active production rollout.
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Completed ledger**: [`../completed/large-moe-expert-parallelism-completed-through-2026-05-28.md`](../completed/large-moe-expert-parallelism-completed-through-2026-05-28.md)
**Updated**: 2026-05-28

## Start Here

The critical correction is that historical EP wins were polluted by baseline choice. The live rule is:

1. Treat every pre-2026-04-26 EP throughput claim as historical unless it was re-run against the proper canonical baseline.
2. Compare `canonical-no-EP` vs `canonical-config-change` vs `canonical+EP`; do not compare EP to warmed `mmap=1`, stale `--numa distribute`, or ad hoc references.
3. If EP delta is <=3% or within noise, leave all `GGML_EP_*` flags default-off and do not wire orchestrator routing.
4. For >150B models, use CPU24's conclusion first: the limiting class is memory-stalled compute kernels, not aggregate DRAM saturation, so EP is not the default next lever.

## Current Verdict

| Scope | Current interpretation | Action |
|-------|------------------------|--------|
| Qwen3.6/Qwen3.5 35B frontdoor-class EP | Earlier +17%/+100% claims are downgraded; proper cold canonical result is about +1.6%, i.e. noise. | Do not production-enable without a fresh CPU20 matrix showing a stable material delta. |
| REAP-246B / MiniMax >150B class | Earlier catastrophic EP regression partly came from sub-baseline comparisons; proper canonical EP is neutral or not useful. CPU24 shows baseline bottleneck is compute-kernel memory stall, not aggregate BW. | Keep single-instance routing. Reopen only with a new bottleneck proof. |
| EP implementation | Dispatcher/bootstrap/shard/drone/eager-warm paths are bit-correct behind flags. | Keep as experimental default-off infrastructure; strip or quarantine only through the env-flag inventory process. |
| L3-as-NUMA retest | L3aaN evaluation regressed broadly and does not fix CPU15's bottleneck class. | Do not retest for CPU15 without a new user-approved topology campaign. |

## Outstanding Tasks

- [ ] **CPU15-DISP — Reconcile deployment-facing docs**: keep `cpu-inference-optimization-index.md`, `cpu-kernel-env-flags-inventory.md`, `../completed/nps-reboot-runbook.md` (archived 2026-06-12), and MoE-Spec cross-refs aligned with the downgraded EP verdict. No document should claim EP is production-wired for frontdoor without a current CPU20 canonical matrix.
- [ ] **CPU15-REVAL — Fresh canonical matrix if reopening**: before enabling EP anywhere, run:
  - baseline canonical no-EP;
  - canonical config change without EP;
  - canonical + EP flags;
  - at least 3 reps, CPU20 process hygiene, recorded build/commit/env, and PPL/quality gate.
- [ ] **CPU15-ROOT — Bottleneck proof before new mechanism work**: if pursuing >150B again, start from CPU24/perf-record evidence and show why the proposed mechanism attacks memory-stalled compute kernels. Do not restart 2DH/all-to-all or L3aaN just because EP history exists.
- [ ] **CPU15-UPSTREAM — Upstream only after positive target**: upstream `ep_dispatcher` or EP hooks only if a CPU20 canonical target demonstrates stable gain. General bugfixes such as repack/mbind fixes belong in the kernel/env-flag inventory, not this handoff.
- [ ] **CPU15-MOESPEC — Compatibility note**: if MoE-Spec modifies expert dispatch on a model where EP is experimentally enabled, mask/budget selection must happen before EP broadcast so all workers see the same expert IDs.

## Dependency Graph

```text
CPU20 protocol
    -> CPU15-REVAL
        -> production EP decision
        -> optional upstream PR decision

CPU24 attribution + perf-record proof
    -> CPU15-ROOT
        -> any >150B EP/2DH/L3aaN reopen

MoE-Spec Phase 0
    -> CPU15-MOESPEC compatibility check only if both features target same model
```

## Reopen Triggers

| Trigger | Required mitigation |
|---------|---------------------|
| New production model has MoE expert topology unlike Qwen3.6/REAP/MiniMax | Run CPU15-REVAL first; no extrapolation from old class heuristics. |
| Multi-tenant workload makes single-stream EP less relevant than aggregate concurrency | Prefer dynamic-stack / NUMA 4-way concurrency; do not use CPU15 as the default answer. |
| Profiling shows sync/all-to-all >25% of cycles on a target | Reconsider CPU19/Tutel 2DH; otherwise keep it deprioritized. |
| Model dispatch path changes via MoE-Spec | Re-run correctness/throughput with EP flags off and on; budgeted expert IDs must be deterministic across workers. |

## Key Files

| Repo | Path | Purpose |
|------|------|---------|
| epyc-llama | `ggml/src/ggml-cpu/ggml-cpu.c` | `mul_mat_id` EP/drone/shard hook sites |
| epyc-llama | `ggml/src/ggml-cpu/ep-dispatcher.cpp` | shared-memory dispatcher implementation |
| epyc-llama | `ggml/src/ggml-cpu/ggml-ep-bootstrap.cpp` | env-var master/worker bootstrap |
| epyc-llama | `ggml/src/ggml-cpu/ggml-ep-shard.cpp` | expert shard/eager-warm infrastructure |
| epyc-root | `handoffs/active/cpu-kernel-env-flags-inventory.md` | deployment status for `GGML_EP_*` flags |
| epyc-root | `handoffs/completed/cpu-uncore-fabric-attribution.md` | CPU24 bottleneck attribution |

## Completed Scope

| Scope | Outcome | Evidence |
|-------|---------|----------|
| Phase 0 large-MoE baseline | REAP-246B and MiniMax measured; D1 failed the "large MoE alone solves it" threshold. | [completed ledger](../completed/large-moe-expert-parallelism-completed-through-2026-05-28.md) |
| Phase 1 intra-process per-CCD EP | Bit-correct, default-off, no meaningful throughput gain; file-backed `mbind` too weak. | [completed ledger](../completed/large-moe-expert-parallelism-completed-through-2026-05-28.md) |
| Phase 2 anonymous expert copies | Bit-correct, but static modulo sharding regressed; load imbalance/dispatch policy problem. | [completed ledger](../completed/large-moe-expert-parallelism-completed-through-2026-05-28.md) |
| Phase 3 inter-process EP | Dispatcher/bootstrap/shard/drone/eager-warm landed and bit-correct; throughput claims downgraded under honest baselines. | [completed ledger](../completed/large-moe-expert-parallelism-completed-through-2026-05-28.md) |
| CPU24 attribution | Baseline >150B bottleneck classified as memory-stalled compute kernels, not aggregate DDR saturation. | [`../completed/cpu-uncore-fabric-attribution.md`](../completed/cpu-uncore-fabric-attribution.md) |

## Reporting Instructions

- Update this file and [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) after any CPU15 revalidation.
- If EP is left default-off after a re-run, record the negative result explicitly; do not leave stale "candidate production route" text in indices.
- If a `GGML_EP_*` flag disposition changes, update [`cpu-kernel-env-flags-inventory.md`](cpu-kernel-env-flags-inventory.md) in the same commit.
