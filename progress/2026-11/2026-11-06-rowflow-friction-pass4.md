# 2026-11-06 — keeper friction pass-4 fixes (operator-adhoc-ops-20261105, emergency deploy)

## Problem
Pass 4 of `docs/reports/coordination/keeper-friction-review-20261105.md` (18f4555e5): 88 % of dry-run FAIL records and
smoke-fail alerts in 2026-11-04..06 carried no information — one unchanged `--precond-cmd` refused 171 times (one per
tick, 478 false vs 3 real), 11/11 `rc=14 launcher pid dead` FAILs were rows that had already completed, and the
IDLE-HELD / OVER-DECLARED checks judged GPU-token grants by CPU % (43/72 flags false; a running GPU harness warned 30+ times).

## Changes (frozen keeper `scripts/coordination/rowflow/rowflow.py`, operator-authorised emergency)
- fix 1 `PRECOND_PARK_ONCE`: `precond_park()` parks the row at the first precond refusal (checked BEFORE the `armed`
  branch of `_status_raw`, which is why the live poller kept it re-admitted); retry only on launcher/manifest sha change
  or `rowflow.py unpark <id>` (`UNPARK.json`, honoured by `arm_fails_since_pass`).
- fix 2 `COMPLETE_BEFORE_RC14`: `terminal_success()` (`.complete` or `.ended rc=0 reason=complete`) checked before
  arming and after a refused admission → `COMPLETE <id>` line, no FAIL, no alert.
- fix 3 `GPU_IDLE_BY_DEVICE`: `gpu_grant_busy()` (own KFD clients via `gpu_occupancy()` + device busy % from the
  existing `hostutil` sample) replaces CPU % for GPU-token grants in `idle_held()` and `status()`; idle only after
  `GPU_IDLE_SAMPLES`=2 quiet samples; `busy_flag(gpu=True)` → None.
- Tests: `tests/test_rowflow_friction_pass4.py` (22, incl. 3 negative controls), replay scenarios `p4-*` (6) and
  per-flag negative controls in `tests/replay/test_replay_gate.py`; harness hooks `blob["admit"]`, `blob["kfd_own"]`.
- rowflow2 mirror + GPU grant ordering: see the commit body.

## Deploy
`deploy_rowflow.sh --emergency "operator 2026-11-06: friction pass-4 fixes (refusal terminal-once, complete!=rc14, GPU idle by KFD/VRAM)"`
— sha and verification recorded in `compute-flags/bin/rowflow/DEPLOYED.json` (`emergency_log`).
