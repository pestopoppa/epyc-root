# YaRN-128K MI210 R10 READY preparation — 2026-10-31

## Scope

This is a compact operational wrap of the accepted R10 READY preparation. It is not the 120-pair scientific result, does not regrade earlier observations, and does not arm or start the scheduler row.

## READY publication

- Row: `yarn-128k-mi210-sol-r10-20261031`
- State: `READY_PUBLISHED_NOT_ARMED_KEEPER_EXPIRED`.
- READY manifest SHA-256: `e1ded3666e394f9e41935f839a2b9f7036d15d26f013bed13eb4e1343e443866`.
- Frozen source manifest SHA-256: `4075cf8bde308ef64ef32a28f15e5d385cbe24eccb0db30c85de9538f2f09ae1`.
- Actual final-source native smoke: 103,311 prompt tokens; 238.221 s normal smoke wall. Conservative normal claim bound: 254.528 s. The separate cutoff record is 33.951 s native plus launcher cleanup, with a conservative claim bound of 50.536 s; it is not combined with the normal native runtime.
- The native smoke used the private v10 view; mapped HIP library SHA-256 `f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079`. Production kernel/store state was not modified.
- Source/PID/birth/maps/KFD/VRAM, result-writer, cleanup, actual public PID, publisher-control, and current/grant checks are represented in the referenced qualification and control evidence. The original 120-pair plan and McNemar inputs remain unchanged.

## Repair and prior attempt

R10 reproduced the actual summary-writer regression model-free: the old R9 path failed at `verify` with `NameError` after its 103,311-token native request completed in 216.026 s. R10 binds the returned linkage-preflight stdout and writes the exact value into the summary; the old path fails and repaired path passes. The publisher was repaired out-of-band to use the existing `native_source_sha256` field; qualified source/native records were not changed and no additional native rerun was made for that publisher repair. The earlier R9 request is recorded as a failed attempt and was not regraded.

## Scheduler state and limits

The READY row is not armed. The keeper log records exit at 06:01:04Z after `STOP_AT=06:00Z`; no armed manifest, canonical shared row, grant, or GPU queue entry exists. The scheduler owner must continue or restart the expired keeper. NI did not write shared FILLERS/queue/grant state and did not restart or edit writers. Do not repeat native work or call the row ARMED while that external condition remains.

The full 120-pair cohort is not complete. The active YaRN task remains open; do not tick its scientific checkbox. G16 greedy preparation continues separately.

## Evidence pointers and hashes

The READY manifest is `/mnt/raid0/llm/tmp/compute-flags/ready/yarn-128k-mi210-sol-r10-20261031.json`; publication state is `/mnt/raid0/llm/tmp/compute-flags/codex-channels/NI-YARN128-SOL-R10-PUBLICATION.json`. The compact hash inventory is in `EVIDENCE.sha256`. Source qualification material remains in `/mnt/raid0/llm/tmp/codex-ni-yarn128-cutoff-sol-20261031/packet-r10/review-evidence/`; the 29 GB model and 91 MB runtime are intentionally not copied here.

## Prepared handoff insertion (MAIN applies)

`handoff.patch` is a valid unified diff for one scoped preparation sub-bullet under `YARN-128K-MI210`. It leaves the parent checkbox open and records the external keeper outage as the next-action dependency. `ARTIFACTS.sha256` covers the compact README and proposed patch; `EVIDENCE.sha256` remains the unchanged inventory of source-evidence hashes. The owning session applies it and refreshes the generated index state.
