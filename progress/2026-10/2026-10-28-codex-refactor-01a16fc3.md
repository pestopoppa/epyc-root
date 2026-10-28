# 2026-10-28 — codex-refactor-01a16fc3

## M4 architect CPU calibration launcher preflight

The M4 architect calibration launcher and job were prepared under `/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-full-fold-ready-20261028/cpu-calibration/`. The source was already enrolled on root `main` at `54bafae1`; this checkpoint records the validated preflight only. No inference, model load, warmup, or memory calibration was run.

| Area | Evidence / result |
|---|---|
| Launcher dry-run | `dryrun/f3c771eff16f09b9a7ab3063984b82122b42598939449276/pass.json`: `validated-m4-architect-calibration-before-load`; test child reaped; sampled utility RSS peak 83,960 KiB against 4,194,304 KiB utility limit. |
| Real entry preflight | Owner-authorized q1 pair `26-27`, OMP=1; entry boundary passed and child reaped. This does not establish normal-affinity coverage. |
| Role matrix | Final check passed: 10 roles / 12 native entries; full scope, production t96, shared MTP vs request metadata, vision mmproj, and half topology. Best-recipe proof remains unbound. |
| Resource claim | No inference or model run. The 512 GiB value is the declared sampled-RSS budget, not an OS hard cap; calibration remains pending. |

Task files are in the external scratch root above, not copied into the root repository. The row draft still identifies the source item as BACKLOG; no index row was changed in this checkpoint. Next action is to use the owner-approved CPU window for the calibration run, collect sampled-memory evidence, then update the owning row and handoff with the measured result.
