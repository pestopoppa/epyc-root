# Intra-Process Tensor-Parallel Decode Across CCDs

**Status**: COMPACTED 2026-05-28 - reference + revalidation-gated only; no CPU1 work without a new workload/topology trigger.
**Created**: 2026-04-23
**Updated**: 2026-05-28
**Priority**: MEDIUM when dormant; HIGH only after the reopen checklist passes
**Categories**: hardware_optimization, inference_serving, local_inference
**Parent index**: [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md), [inference-acceleration-index.md](inference-acceleration-index.md)
**Completed ledger**: [intra-process-tensor-parallel-decode-completed-through-2026-05-28.md](../completed/intra-process-tensor-parallel-decode-completed-through-2026-05-28.md)

## Executor Start Here

This handoff is active as a reference and reopen gate, not as an implementation queue. Do not restart Phase 1.3 v2 or CPU1 tensor-parallel work unless a new trigger is explicitly stated and CPU20-compliant profiling proves locality/barrier dominance again.

## Reopen Checklist

- [ ] State the new trigger: 2-socket hardware, NPS/L3aaN topology change, multi-tenant workload, prefill-heavy serving, or another concrete reason single-session saturation matters again.
- [ ] Run [cpu-benchmark-rigor-and-revalidation.md](cpu-benchmark-rigor-and-revalidation.md) before making any throughput claim.
- [ ] Reproduce the current canonical baseline for the target model/topology.
- [ ] Prove the bottleneck is locality/barrier dominated, not DRAM-channel dominated or model-architecture limited.
- [ ] Choose the smallest next action: archive, profiling probe, Phase 1.3 v2 warm-up/page-locality work, or a redesigned TP path.

## Dependency Forks

| Finding | Next action |
|---|---|
| No new trigger | Leave dormant as a reference; keep indices clear that CPU1 is revalidation-gated. |
| CPU20 profile shows DRAM-channel or architecture ceiling | Do not implement TP; redirect to the relevant CPU/kernel or workload-shaping handoff. |
| CPU20 profile shows locality/barrier dominance | Open a narrow implementation task and copy only the needed evidence from the completed ledger. |
| New hardware/topology invalidates prior NPS4 findings | Re-run the canonical baseline and update this handoff before code changes. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Phase 0/1 CPU TP feasibility | Historical GO signal was later narrowed by canonical NPS4 methodology. | [completed ledger](../completed/intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |
| Barrier-only and CCD-pool probes | Mixed/limited; useful as negative evidence and method reference. | [completed ledger](../completed/intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |
| NPS2/NPS4 and Phase 1.3 v1 evidence | Preserved; later index framing says CPU1-specific levers are exhausted for current single-user NPS4 decode. | [completed ledger](../completed/intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |
| Phase 1.3 v2 design | Preserved as a possible reopen path, not a current default task. | [completed ledger](../completed/intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/llama.cpp/ggml/src/ggml-cpu/`
- `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/`
- [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md)
- [single-instance-system-tuning.md](single-instance-system-tuning.md)
- [large-moe-expert-parallelism.md](large-moe-expert-parallelism.md)

## Reporting Instructions

If reopened, update this file first with the trigger, baseline command, and bottleneck proof. Then update [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md), [inference-acceleration-index.md](inference-acceleration-index.md), and the progress log with the exact decision.
