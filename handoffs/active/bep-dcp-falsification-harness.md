# BEP-2 / DCP-6 Falsification Harness

**Status**: COMPACTED 2026-05-28 - BEP-2 remediation complete; active work is DCP-6 plus optional J8 provenance.
**Created**: 2026-05-26
**Updated**: 2026-05-28
**Priority**: MEDIUM
**Parent index**: [master-handoff-index.md](master-handoff-index.md), [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Completed ledger**: [bep-dcp-falsification-harness-completed-through-2026-05-28.md](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md)

## Executor Start Here

The original BEP-2 read-loop blocker is remediated by the default-off `force_mode="edit"` edit transaction path. Do not rerun the full BEP harness build unless the batch-edit-vs-interleaved comparison is still valuable on its own. DCP-6 is the live independent evaluation path after DCP-4 advisory attach.

## Outstanding Tasks

- [ ] **DCP-6 offline replay**: build or run the delegation-context pre-assembly replay first, using scratch/task-root semantics where needed. Confirm the bundle reads task files, not orchestrator files.
- [ ] **DCP-6 inference gate**: only after offline replay passes and the operator approves a host-quiet window; record top-up rate, token overhead, and success deltas.
- [ ] **J8 optional provenance**: run the legacy batch-edit vs interleaved-REPL A/B only if the batch-edit path itself still needs a keep/kill result. It is no longer a blocker for multi-file coding completion.
- [ ] **Cross-handoff cleanup**: keep production rollout decisions in [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md), not here.

## Dependency Forks

| Outcome | Next action |
|---|---|
| DCP-6 offline replay fails task-root or bundle correctness | Fix the DCP harness before any inference. |
| DCP-6 inference improves success/top-up metrics within token budget | Promote DCP pre-assembly according to [delegation-context-preassembly.md](delegation-context-preassembly.md). |
| DCP-6 inference is neutral or regressive | Keep DCP advisory/default-off and document the failure mode. |
| J8 A/B is not needed | Leave J8 as optional provenance; do not spend host-quiet time. |
| J8 is run and batch-edit loses to edit transaction | Close BEP batch mode as superseded; keep edit transaction as the product path. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Phase 0 task-root surface audit | Complete. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |
| Phases 1/1b/1c/2/3 harness build | Complete and dry-run validated. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |
| BEP-2 read-loop investigation | Root cause corrected from model capability to protocol/tooling issue. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |
| BEP-2 remediation | Default-off `force_mode="edit"` edit transaction built, hardened, and validated; rollout tracked elsewhere. | [completed ledger](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/edit_transaction.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/task_root.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/bep_ab.py`
- [delegation-context-preassembly.md](delegation-context-preassembly.md)
- [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md)
- [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md)
- [bulk-inference-campaign.md](bulk-inference-campaign.md)

## Reporting Instructions

For DCP-6, update this handoff, [delegation-context-preassembly.md](delegation-context-preassembly.md), [bulk-inference-campaign.md](bulk-inference-campaign.md), and the progress log with the replay/inference commands, metrics, and decision. For J8, explicitly state whether the run is provenance-only and whether it changes any production recommendation.
