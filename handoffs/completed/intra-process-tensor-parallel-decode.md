# Intra-Process Tensor-Parallel Decode Across CCDs

> # ✅ CLOSED 2026-09-14 — INVESTIGATION CONCLUDED; DORMANT REOPEN GATE, NOT AN OPEN TASK.
>
> **Reason.** This page held **0 open checkboxes and 5 guarded ones** — a per-reopen *procedure*, not a
> task list (auditor note 2026-07-29). No topology or workload trigger arrived between the 2026-05-28
> compaction and today, and the index row's `Next action` had read "reopen only if tensor-parallel decode
> is reconsidered" unchanged since the 2026-07-26 staleness review. Two consecutive reviews with an
> unchanged blocker means it was never blocked. A dormant reopen gate is not an outstanding TODO, so it
> leaves the active queue. **The gate itself is NOT lifted:** the reopen checklist and its dependency
> forks are reproduced in the banner of
> [`intra-process-tensor-parallel-decode-completed-through-2026-05-28.md`](intra-process-tensor-parallel-decode-completed-through-2026-05-28.md),
> which is now the authoritative record. Do not restart Phase 1.3 v2 or any CPU1 tensor-parallel work
> without reading it.
>
> **Where the live work went.** CPU decode is
> [`cpu-decode-roofline-program.md`](../active/cpu-decode-roofline-program.md) (INF-70), which reached the
> same verdict from the other side: this host's CPU decode is barrier/op-count bound and the per-CCD
> levers are measured out.

**Status**: CLOSED 2026-09-14 · COMPACTED 2026-05-28 - reference + revalidation-gated only; no CPU1 work without a new workload/topology trigger.
**Created**: 2026-04-23
**Updated**: 2026-07-26
**Priority**: MEDIUM when dormant; HIGH only after the reopen checklist passes
**Categories**: hardware_optimization, inference_serving, local_inference
**Parent index**: [inference-research-index.md](../active/inference-research-index.md), [inference-research-index.md](../active/inference-research-index.md)
**Completed ledger**: [intra-process-tensor-parallel-decode-completed-through-2026-05-28.md](intra-process-tensor-parallel-decode-completed-through-2026-05-28.md)

## 2026-07-26 Staleness Review

No topology or workload trigger has been established since compaction. The
[inference-acceleration index](../active/inference-research-index.md) still makes
fresh topology/workload proof a prerequisite, so this handoff remains a
dormant reopen gate rather than an implementation queue.

## Executor Start Here

This handoff is active as a reference and reopen gate, not as an implementation queue. Do not restart Phase 1.3 v2 or CPU1 tensor-parallel work unless a new trigger is explicitly stated and CPU20-compliant profiling proves locality/barrier dominance again.

## Reopen Checklist

> **⚠ THESE BOXES ARE UNCHECKED BY DESIGN — DO NOT DISPATCH OR FLIP THEM.**
> This is a **per-reopen procedure**, not a task list. Every `- [ ]` below is a step to be executed *if and when this work is reopened*, so it has no completion
> state outside one. Flipping any of them asserts that a repeating procedure is permanently
> done, and the next reader inherits a checklist that reads as already-executed — so the step
> silently stops being run.
>
> Noted 2026-07-29 by `auditor` during a sweep of `handoffs/active/` prompted by the automated
> backlog sweep classifying steps like these as dispatchable `none`-lane work. It is additionally conditional on a reopen trigger that has not occurred, so the boxes are not merely repeating — they are not yet applicable at all.


- [ ] State the new trigger: 2-socket hardware, NPS/L3aaN topology change, multi-tenant workload, prefill-heavy serving, or another concrete reason single-session saturation matters again.
- [ ] Apply the `/workspace/MEASUREMENT.md` P-BENCH protocols (historical CPU20 record: [cpu-benchmark-rigor-and-revalidation.md](cpu-benchmark-rigor-and-revalidation.md)) before making any throughput claim.
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
| Phase 0/1 CPU TP feasibility | Historical GO signal was later narrowed by canonical NPS4 methodology. | [completed ledger](intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |
| Barrier-only and CCD-pool probes | Mixed/limited; useful as negative evidence and method reference. | [completed ledger](intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |
| NPS2/NPS4 and Phase 1.3 v1 evidence | Preserved; later index framing says CPU1-specific levers are exhausted for current single-user NPS4 decode. | [completed ledger](intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |
| Phase 1.3 v2 design | Preserved as a possible reopen path, not a current default task. | [completed ledger](intra-process-tensor-parallel-decode-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/llama.cpp/ggml/src/ggml-cpu/`
- `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/`
- [inference-research-index.md](../active/inference-research-index.md)
- [single-instance-system-tuning.md](single-instance-system-tuning.md) (archived 2026-06-12)
- [large-moe-expert-parallelism.md](../active/large-moe-expert-parallelism.md)

## Reporting Instructions

If reopened, update this file first with the trigger, baseline command, and bottleneck proof. Then update [inference-research-index.md](../active/inference-research-index.md), [inference-research-index.md](../active/inference-research-index.md), and the progress log with the exact decision.
