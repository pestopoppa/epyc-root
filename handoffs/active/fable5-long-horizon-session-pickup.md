# Fable5 Long-Horizon Session Pickup

**Status**: LIVE PICKUP — focused continuity note for the current autonomous Fable5 follow-through. This is not a replacement for the owning handoffs; it points the next session at the transient state that progress logs and indices do not capture cleanly.
**Created**: 2026-06-15
**Last verified**: 2026-06-15T09:59:00Z
**Primary owners**: [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md), [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md), [master-handoff-index.md](master-handoff-index.md)

## Resume First

1. Verify the active AutoPilot posture before starting any planner/inference work:

   ```bash
   cd /mnt/raid0/llm/epyc-orchestrator
   jq '{trial_counter, paused, in_flight_trial}' orchestration/autopilot_state.json
   pgrep -af 'core_v2_calibrate.py|scripts/autopilot/autopilot.py'
   ```

   Last verified state: PID `2730020` is a detached current-code AutoPilot W6
   shadow-audit run (`--max-trials 832`), `trial_counter=825`, `paused=false`,
   `in_flight_trial.trial_id=825`. Trial `825` is a `memrl_retrieval`
   `numeric_trial`. Archive authority is aligned. W6 audit rows have landed for
   trials `#822-#824` (`audit_block_report.py`: `trial_count=704`,
   `audited_trial_count=3`, core `94/150`, audit `18/30`,
   `delta_audit_minus_core=-0.080`, overfit divergences `0`).

2. Re-run the five-row selector from `/tmp` if you need to inspect the candidate/core shape:

   ```bash
   mkdir -p /tmp/epyc-core-v2/core_v2_calibration_20260615T003043Z_plus_ext2
   uv run python scripts/autopilot/core_v2_select.py \
     --journal /mnt/raid0/llm/tmp/core_v2_calibration/core_v2_calibration_20260615T003043Z.jsonl \
     --journal /mnt/raid0/llm/tmp/core_v2_calibration/core_v2_calibration_ext2_20260615T050124Z.jsonl \
     --out-core /tmp/epyc-core-v2/core_v2_calibration_20260615T003043Z_plus_ext2/core_v2.candidate.jsonl \
     --report-json /tmp/epyc-core-v2/core_v2_calibration_20260615T003043Z_plus_ext2/core_v2_selection.report.json \
     --core-id core_v2_preview_5rows \
     --target-size 40 \
     --min-attempts 2
   jq '{selected_count, eligible_items, shortfall, unresolved_selected_count, parameters}' \
     /tmp/epyc-core-v2/core_v2_calibration_20260615T003043Z_plus_ext2/core_v2_selection.report.json
   ```

## Current Live State

- AutoPilot PID `2730020` is still alive under the detached max-trials-832 W6
  shadow-audit run. Completed W6 live rows:
  - `#822`: q/s/r=`1.920/26.779/0.920`, dominated/excluded as
    `reproduction_confirmed`; code-mutation extraction failed, so no code patch
    was applied.
  - `#823`: q/s/r=`1.860/28.787/0.920`, dominated/excluded as
    `reproduction_confirmed`; `memrl_retrieval` numeric trial.
  - `#824`: q/s/r=`1.860/25.286/0.920`, dominated/excluded as `mad_noise`;
    `ure_uncertainty_shadow_log=false` structural experiment.
- Current state at last verification: `trial_counter=825`, `paused=false`,
  `in_flight_trial.trial_id=825`; trial `825` is a `memrl_retrieval` numeric
  trial.
- Trial `822` was a `code_mutation` proposal for `src/tool_policy.py`; the
  planner-side code mutation failed to extract a patch (`Claude CLI rc=1`), so
  no code patch was applied. Orchestrator git dirt remained limited to runtime
  `scripts/autopilot/short_term_memory.md`.
- Stale paused `autopilot.py` processes from the 2026-06-14 restart window were killed and verified absent before the fresh launch.
- Fresh AutoPilot run was launched from current code with W6 shadow-only audit
  enabled (`AUTOPILOT_W6_AUDIT_SHADOW_ONLY=1`) and `--max-trials 832`;
  `setsid` was required so the command-runner did not reap the process after the
  launcher shell exited.
- Completed extension: `core_v2_calibration_ext2_20260615T050124Z`
  - command: `uv run python scripts/autopilot/core_v2_calibrate.py --calibration-id core_v2_calibration_ext2_20260615T050124Z --out-jsonl /mnt/raid0/llm/tmp/core_v2_calibration/core_v2_calibration_ext2_20260615T050124Z.jsonl --n 300 --repeats 2 --seed 4242 --trial-id-base 900003`
  - repeat 1/2 complete: trial `900003`, q=`2.060`, r=`0.920`, `n=300`
  - repeat 2/2 complete: trial `900004`, q=`2.100`, r=`0.957`, `n=300`
- Base calibration: `core_v2_calibration_20260615T003043Z`, three 300-question same-seed rows:
  - q/r `2.090/0.947`, `2.100/0.950`, `2.050/0.933`
  - strict selector no-go: `selected_count=21`, `target_size=40`, `shortfall=19`, unresolved `0`
  - durable no-go report in `epyc-orchestrator` commit `3037ec2`: `orchestration/reports/core_v2_selection_core_v2_calibration_20260615T003043Z.no_go.json`
- Five-row selector result: `selected_count=33`, `target_size=40`, `shortfall=7`, `unresolved_selected_count=0`; no `benchmarks/prompts/core_v2.jsonl` was promoted.
- Durable five-row no-go report in `epyc-orchestrator` commit `8db5292`: `orchestration/reports/core_v2_selection_core_v2_calibration_20260615T003043Z_plus_ext2.no_go.json`
- W6 live-tree no-inference check passed, and a standalone plumbing probe wrote one audited row without mutating AutoPilot state:
  - focused pytest `7 passed, 15 deselected`
  - current-journal read-only report: `trial_count=701`, `audited_trial_count=0`
  - standalone probe `w6_audit_plumbing_20260615T082700Z`: `trial_id=910010`, `n_questions=7`, partition counts `core=5`, `audit=2`, reliability `1.000`; report in `epyc-orchestrator` `orchestration/reports/w6_audit_plumbing_20260615T082700Z.{json,md}`
  - follow-up Orchestrator `a4d510a` makes future W6 audit rows shadow-only by default (`AUTOPILOT_W6_AUDIT_SHADOW_ONLY=1` unless explicitly set to `0`): audit rows stay in `question_results`/reports but decision metrics remain paired-core-only
  - AutoPilot state remained `trial_counter=822`, `paused=true`, `in_flight_trial=null`
- Generated stack metadata was regenerated from source/derived inputs and stack preflight passed `11/11` after launch.
- Archive authority was repaired from journal authority and archive-preflight passed `11/11`.
- Orchestrator `51268f7` fixed a startup archive-authority hazard: direct
  `autopilot.py start` now repairs state archive drift from the append-only
  journal before lifecycle saves. Validation: py_compile, ruff, focused startup
  tests, 58 archive/recovery/preflight tests, no-trial start/shutdown, and full
  AutoPilot preflight `11/11`.
- W6 live-tree row collection is attached to the detached max-trials-832 run
  under shadow-only audit posture. Trials `#822-#824` produced the first three
  real live audit rows: `audit_block_report.py` totals `core=94/150`
  (`1.880`), `audit=18/30` (`1.800`), `delta_audit_minus_core=-0.080`, and
  overfit divergences `0`. This proves live shadow collection is working, but
  remains an early sample rather than a policy acceptance or instrument-era
  decision.

For future W6 live collection, verify stack and archive gates before resuming any planning. Stale 2026-06-14 processes are cleared; keep the fresh max-trials-832 posture unless explicitly overridden.

## Promotion Gate

Promote a `benchmarks/prompts/core_v2.jsonl` only if all of these hold on the selector report:

- `selected_count == parameters.target_size`
- `shortfall == 0`
- `unresolved_selected_count == 0`
- candidate core metadata row has `__core_metadata__ == true`
- candidate `selected_count` equals non-metadata row count

The five-row selector is still short. **Operational decision 2026-06-15**: do not promote `core_v2`, do not silently lower the target, and do not spend another repeat on this lineage in the current window. W5 remains open/no-go with the strict target intact. Reopen only if one of these is intentionally chosen and documented:

- run a new calibration lineage or additional same-seed repeats when the CPU serving stack is clean enough to justify the inference cost; or
- lower the target with a new `core_id` and documented rationale for why a smaller designed core is acceptable.

## Completed In This Run

- Gate-3 functional parallelism was validated for tool-plumbing only, excluding throughput/planner evidence.
- Orchestrator `7c25def` added the `gate3-tool-telemetry` launch profile, env hints, tests, and runbook note.
- W5 3x300 base calibration completed and produced a strict no-go.
- Orchestrator `3037ec2` recorded the W5 no-go selector artifact.
- W5 2x300 extension completed; five-row selector improved to `33/40` but still no-go.
- Orchestrator `8db5292` recorded the extended five-row no-go selector artifact.
- Root `c86a49d` updated progress, the evidence-plane instrument handoff, and the master index with the first no-go; `b027a67` recorded the extended no-go; `f40c74a` recorded the W6 audit baseline check. Current useful commits still anchored by orchestrator `086f4da` and `a4d510a` and root `3312189`, `6815a06`, `6e0e0ee`.
- W6 standalone plumbing probe completed with partitioned core/audit rows and `audit_block_report.py` output; this is W6 mechanics evidence only, not an AutoPilot deployment/cutover row.
- Orchestrator `a4d510a` added the W6 shadow-only guard so live audit collection can journal audit rows without rotating the paired-core decision metric by default.
- AutoPilot trial `822` journaled the first real W6 shadow-audit row
  (`core=32/50`, `audit=7/10`, `delta=+0.180`, overfit divergences `0`) while
  remaining dominated/excluded as `reproduction_confirmed`; follow-up rows
  `#823-#824` brought the batch to `audited_trial_count=3`, core `94/150`,
  audit `18/30`, `delta=-0.080`, overfit divergences `0`; the detached run is
  still alive at `trial_counter=825`, with follow-on trial `825` in flight.
- Generated stack metadata refresh and both stack/authority preflight checks are
  now passing at `11/11`; orchestrator `1bd9563` refreshed stack generated
  metadata and `51268f7` hardens startup archive authority.
- Root `2ebfd3c` added this pickup handoff, and root `64a4430` recorded the full wrap-up routine notes.
- Root and Orchestrator GitNexus indexes were current after the latest commits at the time of each checkpoint.

## Next High-ROI Queue

1. W5 is held open/no-go: no `core_v2` promotion, no smaller fallback core, no more repeats in this window.
2. If W5 later promotes, run focused core-file validation and update `instrument_eras.yaml` only when an era/promotion decision is actually made.
3. Keep monitoring PID `2730020` for additional W6 audit rows or exit. The first
   real row landed on trial `822`, but W6 needs multiple clean rows before any
   overfit/generalization acceptance claim. The current audit cadence is every
   trial (`AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS=1`) with shadow-only decision
   metrics.
4. Then resume Fable5 Queue 2 clean-window work in order: E2/E1 batched-decode measurement, shape-keyed contention bracket, J2/J3 migration probe, J12/THINK-ABL, DCP-6a attested reload, J10 shadow collection.
5. Use inference-free gaps for repo hygiene: Orchestrator `archived_backups/`, `orchestration/optuna_study.db.bak-quarantine786-20260613_093831`, and runtime `scripts/autopilot/short_term_memory.md`.

## Do Not

- Do not start a second AutoPilot while PID `2730020` is alive.
- Do not resume any stale `autopilot.py` process in place; verify stale-process cleanup before any fresh W6 live window.
- Do not treat dashboard inference as AutoPilot unless `autopilot_state.json` and `logs/autopilot.log` contradict the paused state.
- Do not promote a partial `core_v2` target without a new `core_id` and explicit handoff/progress rationale.
- Do not run full `/wrap-up` pruning/wiki compilation unless the operator explicitly asks for `/wrap-up`.
