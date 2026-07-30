# BEP-2 / DCP-6 Falsification Harness

**Status**: COMPACTED 2026-05-28 - BEP-2 remediation complete; DCP-6 offline replay closed 2026-06-12 and DCP-6a repair code landed on the live orchestrator branch at `2e2e0d3`. The live API launch marker already includes `2e2e0d3` and the reload/attestation primitive (`756c96b`), but the 2026-06-19 running-state attestation is caveated by deleted llama-server executables, feature-flag intent diffs, and missing `AUTOPILOT_TOOL_SENTINELS` on the API parent. The remaining J7 gate is now an operationally clean host-quiet attestation plus the inference run, not a code-provenance reload. Optional J8 provenance remains.
**Created**: 2026-05-26
**Updated**: 2026-07-06
**Priority**: MEDIUM
**Parent index**: [master-handoff-index.md](master-handoff-index.md), [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Completed ledger**: [bep-dcp-falsification-harness-completed-through-2026-05-28.md](../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md)

## Executor Start Here

The original BEP-2 read-loop blocker is remediated by the default-off `force_mode="edit"` edit transaction path. Do not rerun the full BEP harness build unless the batch-edit-vs-interleaved comparison is still valuable on its own. DCP-6 is the live independent evaluation path after DCP-4 advisory attach.

## Outstanding Tasks

- [x] **DCP-6 offline replay**: CLOSED 2026-06-12. Scratch/task-root replay over 5 historical BEP tasks confirmed bundles read task files, not orchestrator files; all 7 existing required files were selected and budgets 500/1000/2000 all fit.
- [x] **DCP-6a content-depth/freshness repair**: branch `fix/dcp6a-context-depth-current` commit `530128b7` changes task-root search/packing so tiny task files are included as full files or padded slices instead of one-line snippets, and populates manifest `content_sha256`. Equivalent code landed on the current live branch at `2e2e0d3`. Focused current-lineage tests: 30 passed after landing.
- [x] **DCP-6b J7 runner safety prep**: ✅ 2026-07-06. Orchestrator `7c84f102` corrects `scripts/benchmark/dcp_j7_ab.py` so default mode is no-inference stub/schema validation; live inference now requires explicit `--real --host-quiet-confirmed` and still refuses while AutoPilot is running. Stub artifact `benchmarks/results/runs/dcp_j7/stub-20260706T033205Z/` validates the result schema and records the expected insufficient decision (`missing_latency_delta`, `quality_not_scored`).
- [ ] **DCP-6 deploy attestation + inference gate**: launch-code provenance is satisfied (`server_launch_git_sha=eeb8cce`, ancestor of `2e2e0d3` and `756c96b`; current API `git_sha=27e09a1`). Orchestrator `670aab4` records the 2026-06-19 `dcp6a-deploy-boundary-check` attestation with GitNexus drift clean and all 6 API workers sampled, but it is not a clean deploy gate because llama-server executable paths are deleted, feature-flag intent diffs remain, and `AUTOPILOT_TOOL_SENTINELS` is absent from the API parent env. Clear those operational attestation warnings at the next host-quiet boundary, then run inference and record top-up rate, token overhead, and success deltas.
- [ ] **J8 optional provenance**: run the legacy batch-edit vs interleaved-REPL A/B only if the batch-edit path itself still needs a keep/kill result. It is no longer a blocker for multi-file coding completion.
- [x] **Cross-handoff cleanup**: keep production rollout decisions in [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md), not here. ✅ 2026-07-29 — this handoff records DCP/BEP evidence and gates only; the multi-file capability handoff owns any rollout decision.

## Dependency Forks

| Outcome | Next action |
|---|---|
| DCP-6a code is landed but the launch marker predates `2e2e0d3` | Reload at a clean boundary; do not mutate loaded-code provenance or inference measurements mid-run. |
| Launch marker includes `2e2e0d3` but running-state attestation is caveated | Fix/restart into a clean attested state before treating J7 as production-grade evidence. |
| DCP-6a code is deployed and running-state attestation is clean | Proceed to host-quiet inference gate. |
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
| DCP-6a branch replay + current landing | Branch `fix/dcp6a-context-depth-current` (`530128b7`) passed focused tests and replayed at budgets 500/1000/2000 with 100% file coverage, 100% line coverage, and 0 missing hashes; equivalent code landed on the live branch at `2e2e0d3` with focused current tests passing. | `/mnt/raid0/llm/tmp/dcp6a_current_offline_replay_20260612/summary.json` |
| DCP-6a launch-code provenance check | Live API reported `git_sha=27e09a1` and `server_launch_git_sha=eeb8cce`; `eeb8cce` includes both `2e2e0d3` and `756c96b`. Orchestrator `670aab4` records a caveated running-state attestation: graph drift clean and all 6 API workers sampled, but not a clean inference gate because of deleted llama-server binaries, flag intent diffs, and missing tool-sentinel env. | `/mnt/raid0/llm/epyc-orchestrator/orchestration/attestation/latest.md` |
| DCP-6b runner safety prep | Orchestrator `7c84f102` makes no-inference stub mode the default, keeps real inference behind explicit `--real --host-quiet-confirmed`, and records a fresh schema-only artifact. | `/mnt/raid0/llm/epyc-orchestrator/benchmarks/results/runs/dcp_j7/stub-20260706T033205Z/summary.json` |

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
