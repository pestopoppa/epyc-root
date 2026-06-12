# BEP-2 / DCP-6 Falsification Harness

**Status**: COMPACTED 2026-05-28 - BEP-2 remediation complete; DCP-6 offline replay closed 2026-06-12 with DCP-6a repair required before inference; optional J8 provenance remains.
**Created**: 2026-05-26
**Updated**: 2026-06-12
**Priority**: MEDIUM
**Parent index**: [master-handoff-index.md](master-handoff-index.md), [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Completed ledger**: [bep-dcp-falsification-harness-completed-through-2026-05-28.md](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md)

## Executor Start Here

The original BEP-2 read-loop blocker is remediated by the default-off `force_mode="edit"` edit transaction path. Do not rerun the full BEP harness build unless the batch-edit-vs-interleaved comparison is still valuable on its own. DCP-6 is the live independent evaluation path after DCP-4 advisory attach.

## Outstanding Tasks

- [x] **DCP-6 offline replay**: CLOSED 2026-06-12. Scratch/task-root replay over 5 historical BEP tasks confirmed bundles read task files, not orchestrator files; all 7 existing required files were selected and budgets 500/1000/2000 all fit.
- [ ] **DCP-6a content-depth/freshness repair**: before inference, change task-root search/packing so tiny task files are included as full files or padded slices instead of one-line snippets, and populate manifest `content_sha256`.
- [ ] **DCP-6 replay rerun + inference gate**: rerun the offline replay after DCP-6a; only then use a host-quiet window for inference and record top-up rate, token overhead, and success deltas.
- [ ] **J8 optional provenance**: run the legacy batch-edit vs interleaved-REPL A/B only if the batch-edit path itself still needs a keep/kill result. It is no longer a blocker for multi-file coding completion.
- [ ] **Cross-handoff cleanup**: keep production rollout decisions in [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md), not here.

## Dependency Forks

| Outcome | Next action |
|---|---|
| DCP-6 offline replay selects correct files but shallow content or missing freshness metadata | Fix DCP-6a before any inference. |
| DCP-6 repaired replay passes task-root, bundle correctness, content-depth, and freshness metadata | Proceed to host-quiet inference gate. |
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
| DCP-6 offline replay | Passed scratch-root/file-selection/budget correctness over 5 historical BEP tasks at budgets 500/1000/2000; exposed DCP-6a shallow-slice/hash blocker before inference. | `/mnt/raid0/llm/tmp/dcp6_offline_replay_20260612/summary.json` |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/edit_transaction.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/repl_environment/task_root.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/context_discovery.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/bep_ab.py`
- [delegation-context-preassembly.md](delegation-context-preassembly.md)
- [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md)
- [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md)
- [bulk-inference-campaign.md](bulk-inference-campaign.md)

## Reporting Instructions

For DCP-6, update this handoff, [delegation-context-preassembly.md](delegation-context-preassembly.md), [bulk-inference-campaign.md](bulk-inference-campaign.md), and the progress log with the replay/inference commands, metrics, and decision. For J8, explicitly state whether the run is provenance-only and whether it changes any production recommendation.
