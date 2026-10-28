# 2026-10-28 — M4 worker and vision CPU calibration launcher preflights

## Scope and source

This checkpoint covers the prospective worker/frontdoor and vision C5/M4 CPU memory-calibration launchers in `/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-full-fold-ready-20261028/{cpu-worker-calibration,cpu-vision-calibration}/`. Their source enrollments are present in commits `94244a456` (worker) and `213d37b67` (vision). The validation packet was sent to Claude; the task report says no acknowledgment has arrived.

## Validation evidence

Both launchers completed actual-entry, no-model dryruns that passed admission and stopped before the calibration effect. The worker receipt is `cpu-worker-calibration/dryrun/e293d6cde041b8f1e6a47b0b7a73e2c8eac0a213519fb676/pass.json` (`validated-m4-worker-calibration-before-load`, 04:18:01–04:18:04Z); the vision receipt is `cpu-vision-calibration/dryrun/69ff0c0c253c840e5f3afa9a0a49afb236b67b775cc9a4d9/pass.json` (`validated-m4-vision-calibration-before-load`, 04:20:16–04:20:19Z). The owner-side validator and synthetic fixtures also passed. Both receipts declare the two-core PF scope on CPUs 26–27 and explicitly leave normal-affinity coverage unproved.

The matching `entry.log`, `boundary.json`, and grant-ended receipts remain in each dryrun directory. Admission reported free memory of 168.03 GiB for worker and 167.27 GiB for vision, with the 512 GiB declared process budget. `DRYRUN_RESOURCES` shows cgroup memory `max` and RSS rlimit `[-1, -1]`; no sampled process RSS was recorded. This is launcher validation only: no model load, inference, memory calibration, sampled-memory result, peak claim, speed claim, or quality verdict was produced.

## CPU reservation overlap found during wrap-up

The HIL s1 CPU grant began at 04:11Z, before these dryrun attempts. The preserved logs show four actual-entry attempts on CPUs 26–27 after that time:

| Attempt | Start–end UTC | Result | Admission telemetry |
|---|---|---|---|
| Worker `d2db6921…` | 04:16:34–04:16:37 | rc=2; refused because source enrollment was absent or unverified | `free_gib=169.55`; `MemAvailable=1041 GiB` |
| Worker `e293d6cd…` | 04:18:01–04:18:04 | rc=0; stop-before-effect pass | `free_gib=168.03`; `MemAvailable=1038 GiB` |
| Vision `3fbe99ec…` | 04:19:47–04:19:50 | rc=2; refused because source enrollment was absent or unverified | `free_gib=166.98`; `MemAvailable=1040 GiB` |
| Vision `69ff0c0c…` | 04:20:16–04:20:19 | rc=0; stop-before-effect pass | `free_gib=167.27`; `MemAvailable=1039 GiB` |

All four logs say `gpu=0`, `affinity=[26,27]`, and `two-core-PF`; no model payload ran. The nonzero process time on the reserved pair is still a scheduling overlap, regardless of the stop-before-effect boundary. The root session was notified with exact log paths and telemetry. No further CPU preparation was started. Further work that uses CPUs 26–31 waits for the owner’s resolution of the 04:11 reservation overlap.

## Handoff and row state

The calibration tasks remain open because no model or memory-calibration run occurred. No handoff checkbox or index row was changed. The external `ROW-DRAFT.md` files remain drafts and still describe the work as BACKLOG / not ready; the owning session applies any row changes. The only next action is to resume scheduling after the owner resolves the stated CPU overlap, then run the authorized calibration and capture the required evidence.
