# Unified AutoKernel scoped completion — 2026-09-11

## Outcome

The existing AutoKernel loop now completed the requested monitored mixed CPU/GPU trial as
one serial owner. It alternated between the experimental GLM-5.3-Flash CPU target and the
production GPU serving target, settled all six batches and exited with no active child, no
failed target and no outstanding issued scheduler selection. No candidate was kept or
promoted, and no production kernel was modified.

## Observed defect and repair

The v5 recovery run exposed one concrete defect: restored GPU champion-of-record anchor
verification performed a third exact check without forwarding the explicit
`--allow-unverified-anchor` policy. That pre-claim refusal also left the issued scheduler
selection unsettled because it had no batch marker.

Research commit `3aa79c89` centralizes pre-claim verification, forwards the policy during
restored champion verification and publishes a scheduler marker for known pre-claim identity
failures. Seven focused tests passed; the combined relevant suite passed 136 tests plus three
subtests.

## Hardware and dry-run evidence

| Evidence | Result | SHA-256 |
|---|---|---|
| `/mnt/raid0/llm/tmp/aku-final-glm-gpu-20260911-v6-dry-run.log` | Exact mixed-roster dry run exited 0 without creating campaign state | `731a45f7b8c350a01820ebe5a6d2461cbbdb0ed58d60c778dae51dccc5e615f1` |
| `/mnt/raid0/llm/tmp/aku-final-glm-gpu-20260911-v6.log` | Final mixed CPU/GPU hardware campaign completed | `1a820aa9c433f79be32d80ae06223b3aa3c92a6195d03377091df451753f99eb` |
| `/mnt/raid0/llm/tmp/aku-final-glm-gpu-state-20260911-v6/serial-state.json` | `next_batch=6`, `active=null`, `failed_targets={}`, no issued selections | `40a1fa32ccf75ffef9e7f2056ef1d676df445b5acd2f12b042b6b81c26475265` |

The six v6 outcomes were: GPU `refused_at_formation`; GLM `measured_null`
(-3.360%); GLM `refused_at_formation`; GPU `planner_transient` because authoring returned
no changed paths; GLM `refused_at_formation`; GLM `measured_null` (-2.152%). Four v6 GLM
attempts plus the earlier valid v4 GLM measured-null (+0.186%) complete the requested five
GLM attempts. All measured effects remained below the applicable matched floor.

The final state contains ten accounted held-resource receipts and no unsettled scheduler
selection. Dedicated experimental GLM and GPU source trees remained clean. The frozen
production tree was not changed, built or promoted.

## Dashboard closure

ROOT commit `2e1dd002` makes terminal serial state an explicit dashboard producer instead of
misclassifying it as the legacy loop. Twenty focused and 139 combined relevant tests passed.
The exact port-8100 hub and its supervisor were restarted with
`AUTOKERNEL_LOOP_STORE_ROOT=/mnt/raid0/llm/tmp/aku-final-glm-gpu-state-20260911-v6`.
Live probes report `selected_producer=serial_router`, `serial_state=complete`, both retained
targets and the attributed champion capability record containing DFlash2 GPU serving and
Flash-Next/Qwen4Next CPU inference with native MTP.

## Scope boundary

This closes the operator-requested extension of the working loop: explicit CPU/GPU ownership,
candidate targeting, observed-failure repair, monitored GLM trial and reliable dashboard
projection. The handoff's broader proposed replacement-architecture tasks are not prerequisites
for operating this loop and were not treated as launch blockers.
