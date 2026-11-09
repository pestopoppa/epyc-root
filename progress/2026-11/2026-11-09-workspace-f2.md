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

## Dashboard Flow and supervision (afternoon)
**Problem.** The Flow panel read +208 while open boxes fell 2806 to 1516 in 7 days.
**Root cause.** Edits to existing open boxes counted as filings, declines and removals were ignored, and the timeline dated merged lanes on their merge day.
**Changes.** `build_handoff_timeline.py` is the only counter; the hub sums its rows; `hub_view` exposes the served commit and refresh failures; `index_regen.py` joined the pin list. Independent review confirmed 22 sampled commits and the 1263 removals on 11-03 as real retirements, and caught three page bugs fixed before landing.
**Incident.** The re-pin at 13:02 to 2c62d9458 lacked `observer_guard.sh` and `env.sh`, so every supervisor pass failed and the view froze until the third install at 14:28 (e4668444c). The pin list advice was incomplete.
**Results.** Hub live at e4668444c, 0 behind; today -87, 7d -1290. Root CI green from d69e5165d after R18 host-pin and pin-list test fixes. Exemptions ratified at a69312d5b by the operator.
**Open.** No gated regen logged yet (needs a commit burst). LOOP-21/22 and BK-1/2/4 need host steps. Flash rerun queued; EVL-29 stays listed until it files.

## Evening: dropped approvals and churn
The operator caught that approved LOOP-9, PII-NM-OFFSET and LR-13 had not been executed or reported, and that dispatching had stopped after two waves.
| Item | Result |
|---|---|
| LOOP-9 | Rebased onto the v3 keeper flow, ed3d95b81 |
| PII-NM-OFFSET | Narrow nm-row rule, 15 tests, 264cf91e9 |
| LR-13 | One new rule; ratify script needed the Operator-Ratified trailer, re-run pending |
| LR-10 | Orchestrator 3c01431a; 130 pass, one failure also on clean main |
| LOOP-27 | Proven by existing test file, 40 pass |
| LOOP-59 | Incident record docs/reference/kernel-store-incident-20261103.md |
| Backups | Host owner installed a corrected runbook (filesystem-agent 3918872): ai-sessions keep 2, opencode keep 3 per store, loop-state 04:45; restore test 24 DBs PASS, chain_ok PASS |
| NIB2-98 | Gate landed ac89176ab, opt-in until Pipeline wires launch |
| AFC-P5.E3 | Two models KEEP, Flash inconclusive, rerun queued |

The first host handoff had real errors (crontab owner, restore-test parsing, unsafe retention) that the host owner corrected. /workspace re-synced with reset --keep; duplicate commit saved at refs/backup/workspace-local-7adf739ae.

