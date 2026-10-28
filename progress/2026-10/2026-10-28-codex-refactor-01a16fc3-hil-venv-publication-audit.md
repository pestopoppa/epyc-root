# 2026-10-28 — HIL shared-venv checkpoint publication audit correction

## Correct session identity

The correct root session holder for this task is `codex-refactor-01a16fc3`. In the first checkpoint publication, I mistakenly supplied `codex-ni-01a16d6b` to both canonical leases after inferring the identity from the roster. That inference was wrong. The captured lock and hook records truthfully preserve the ID supplied to them; they do not imply NI held the locks, authorized this task, or participated in its publication. This is an additive correction. No history is amended or force-pushed.

## Earlier publication operations

| Operation | Captured evidence | Outcome |
|---|---|---|
| Canonical `/workspace` wrapup lease acquire / release | `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/prep/lease-acquire/20261028T032325Z-3088711/command.log`; `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/prep/release-wrapup-lease/20261028T032845Z-3103877/command.log` | The logs record holder `codex-ni-01a16d6b`; release succeeded. |
| Canonical `/workspace` push lease acquire / release | `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/prep/push-lease-acquire/20261028T032708Z-3099489/command.log`; `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/prep/release-push-lease/20261028T032842Z-3103634/command.log` | The logs record holder `codex-ni-01a16d6b`; release succeeded. |
| Checkpoint branch push | `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/prep/branch-push/20261028T032717Z-3100088/command.log` | Commit `b3d488d99b7bc9fc0ec337b6d594456bd0d63989` was pushed without force to `codex/hil-venv-incident-20261028`. |
| Conflict-guarded promotion and ancestry verification | `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/prep/promotion/20261028T032754Z-3101213/command.log`; `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/prep/final-verification/20261028T032837Z-3103469/command.log` | Promotion advanced remote `main` from `d72d4efda22144628c6c99772f19e5c899f9faca` to `aa236068b71aaeeb73641b890fba931e37296bff`; final verification confirmed the checkpoint commit was reachable from the branch and promoted `main`. The promotion hook log records acceptance of the supplied NI holder identity. |

The promotion command's q1 wrapper returned 125 after printing the successful main SHA because the outer monitor also reported `root exited with owned descendants still running`; it reported `drained=True`. The particular descendant is not identified by the captured output. The detached promotion worktree path was absent afterwards. No inference is made about the descendant's identity or effect. The shared `/workspace` working-tree branch pointer was left untouched.

Both earlier leases are confirmed released. The now-unneeded mode-0600 token files remain intact at `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/wrapup-token.j023vco3/lease.token` and `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/push-token.4ZCn7REC/lease.token`. The tool guard rejected their removal; no bypass was attempted.

## Correction publication validation

This additive audit update uses the correct holder ID `codex-refactor-01a16fc3`. It changes only the existing root-owned HIL checkpoint's documentation link and adds this per-agent audit record; it changes no HIL source or enrollment, index row, or checkbox state. The M4 enrollment was already on `main` at `f5cf785322aff1fc86297dc76d788fc31beea0ec` before this private worktree was created.

`index_state.py` regeneration and `--check` ran under the canonical wrapup lease; `--check` exited 0 with 0 problems and reported that the master block was unchanged. Advisory output included two legacy `/running` scratch warnings and 129 handoffs with no `Scratch` field. README freshness completed without warnings. `scripts/vidya/cli.py sync --check` reported `ledger FRESH`, 2491 entries through `intake-2510`, lag 0. No model or GPU work was performed.

The first task scratch tree was removed only after its worktree was clean and landed; its remaining files were moved intact to `/mnt/raid0/llm/.trash/20261028-033000-hil-venv-incident-wrap/`. The two released tokens remain there as stated above.
