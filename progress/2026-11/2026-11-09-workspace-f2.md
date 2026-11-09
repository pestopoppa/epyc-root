# 2026-11-09 workspace-f2: RTG-22 non-inference backlog audit and landing

## Problem
RTG-22 (`handoffs/active/engineering-hygiene-backlog.md`) had 115 open boxes and a next action written on 10-29. The shared clone was 78 commits behind origin/main, so the audit ran against origin/main.

## Findings
- Grant writers are retired, so LOOP-10 was obsolete. A final sweep refuted a planned LOOP-11 closure (a refusal still orphans pollers) and narrowed LOOP-12 and LOOP-58.
- AFC-P5.E3 had finished on 11-07 but was never filed because its owner session had ended.
- `76d21aa9f` (research, 08-25) silently reverted the NIB2-58a linkage gates; the rescue branch held the only copy of two preflights.
- Independent review before landing caught four real defects: a campaign `.env` ageing out of worktree protection, `update-ref HEAD`/`--stdin` passing the new guard, `close-lane` substring matching, and a `NameError` in the restored gate.

## Landed
| Repo | Work |
|---|---|
| root | CI fixes (LOOP-54 F1, most of LOOP-57), kernel-store custody check, worktree_gate per-repo bases, guards (first push, update-ref, regen gate), LR-11, NIB2-88, LOOP-37, LOOP-39, backup_loop_state, backup_retention, scratch lease allocate, disk archives |
| research | Both Qwen3-4B-Thinking-2507 registry rows deprecated, graveyard row; NIB2-58a gates restored |

## Results
AFC-P5.E3, n=30 per metric, one run, v10 CPU kernel 10303 ffc1bac82, suite v2. Qwen3.6-35B-A3B-MTP-Q8_0 and Qwen3.8-27B-Q8_0: mild, medium and aggressive all KEEP (no detectable loss). Qwen3.8-Flash-Next-UD-IQ4_XS: INCONCLUSIVE, about 20 blanked replies scored as fails; rerun row `afc-p5e3-n30-q38_flash-r2-20261109` queued.

## Decisions (operator)
Refactor track waits for the production kernel promotion and AutoPilot relaunch. OP-AK-HOLD kept. W3 moved to `autopilot-program.md`. Website launch held. BK-3 weekly. C6-17, R18 re-pin and store strays to AutoKernel. Rowflow2, LOOP-11/12/38/58, five-lane test, CORE-BARE and filing tooling to Pipeline.

## Named blockers
- CI green: operator applies `artifacts/operator/staged/ratification-exemptions-add-20261109.json`.
- LOOP-21/22 live, BK-1/2/4: host-side steps, the script lives outside this container.
- HF token rotation: operator.
- EVL-29 archive: Flash rerun result.
- NIB2-77 removal: 7-day idle, about 11-16.
