# Fable5 Long-Horizon Session Pickup

**Status**: LIVE PICKUP — focused continuity note for the current autonomous Fable5 follow-through. This is not a replacement for the owning handoffs; it points the next session at the transient state that progress logs and indices do not capture cleanly.
**Created**: 2026-06-15
**Last verified**: 2026-06-15T07:07:30Z
**Primary owners**: [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md), [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md), [master-handoff-index.md](master-handoff-index.md)

## Resume First

1. Verify whether the standalone W5 calibration extension is still running:

   ```bash
   cd /mnt/raid0/llm/epyc-orchestrator
   jq '{trial_counter, paused, in_flight_trial}' orchestration/autopilot_state.json
   pgrep -af 'core_v2_calibrate.py|scripts/autopilot/autopilot.py'
   EXT_ID=$(cat /mnt/raid0/llm/tmp/core_v2_calibration/latest_extension_id.txt)
   wc -l "/mnt/raid0/llm/tmp/core_v2_calibration/${EXT_ID}.jsonl"
   tail -n 20 "/mnt/raid0/llm/tmp/core_v2_calibration/${EXT_ID}.log"
   ```

2. If the extension is still running, do not start AutoPilot or CPU-heavy indexing. Low-impact log counters are safe:

   ```bash
   awk '/POST \/chat/ {total++} /POST \/chat.* 200 OK/ {ok++} /POST \/chat.* 504/ {to++} END {print "chat_total=" total " ok=" ok " timeout504=" to " approx_repeat5_total=" total-1200 " approx_repeat5_504=" to-60}' logs/orchestrator.log
   ```

3. When repeat 2/2 finishes, run selector across both calibration files into `/tmp` first:

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

- AutoPilot is paused, not actively exploring: `trial_counter=822`, `paused=true`, `in_flight_trial=null` at last verification.
- Dashboard inference is expected: it is the standalone W5 calibration extension, not AutoPilot.
- Running extension: `core_v2_calibration_ext2_20260615T050124Z`
  - command: `uv run python scripts/autopilot/core_v2_calibrate.py --calibration-id core_v2_calibration_ext2_20260615T050124Z --out-jsonl /mnt/raid0/llm/tmp/core_v2_calibration/core_v2_calibration_ext2_20260615T050124Z.jsonl --n 300 --repeats 2 --seed 4242 --trial-id-base 900003`
  - live PID at last verification: `2546189`
  - repeat 1/2 complete: trial `900003`, q=`2.060`, r=`0.920`, `n=300`
  - repeat 2/2 running: trial `900004`; approx `131/300` requests and `7` repeat-5 timeouts at last verification
- Base calibration: `core_v2_calibration_20260615T003043Z`, three 300-question same-seed rows:
  - q/r `2.090/0.947`, `2.100/0.950`, `2.050/0.933`
  - strict selector no-go: `selected_count=21`, `target_size=40`, `shortfall=19`, unresolved `0`
  - durable no-go report in `epyc-orchestrator` commit `3037ec2`: `orchestration/reports/core_v2_selection_core_v2_calibration_20260615T003043Z.no_go.json`
- Four-row preview after extension repeat 1 selected `29/40`, so finishing repeat 2 is justified.

## Promotion Gate

Promote a `benchmarks/prompts/core_v2.jsonl` only if all of these hold on the selector report:

- `selected_count == parameters.target_size`
- `shortfall == 0`
- `unresolved_selected_count == 0`
- candidate core metadata row has `__core_metadata__ == true`
- candidate `selected_count` equals non-metadata row count

If the five-row selector is still short, do not silently lower the target. Record a second no-go report and make an explicit W5 decision:

- run one more same-seed repeat if the expected new eligible count remains high enough; or
- lower the target with a new `core_id` and document why the smaller core is acceptable; or
- leave W5 open and move to the next Fable5 Queue-2 clean-window task.

## Completed In This Run

- Gate-3 functional parallelism was validated for tool-plumbing only, excluding throughput/planner evidence.
- Orchestrator `7c25def` added the `gate3-tool-telemetry` launch profile, env hints, tests, and runbook note.
- W5 3x300 base calibration completed and produced a strict no-go.
- Orchestrator `3037ec2` recorded the W5 no-go selector artifact.
- Root `c86a49d` updated progress, the evidence-plane instrument handoff, and the master index with the no-go.
- Root and Orchestrator GitNexus indexes were current after those commits.

## Next High-ROI Queue

1. Finish W5 extension and settle the `core_v2` promote/no-go decision.
2. If W5 promotes, run focused core-file validation and update `instrument_eras.yaml` only when an era/promotion decision is actually made.
3. If W5 remains short, record the no-go and move to W6 rotating-audit policy/default-off validation.
4. Then resume Fable5 Queue 2 clean-window work in order: E2/E1 batched-decode measurement, shape-keyed contention bracket, J2/J3 migration probe, J12/THINK-ABL, DCP-6a attested reload, J10 shadow collection.
5. Use inference-free gaps for repo hygiene: Orchestrator `archived_backups/`, `orchestration/optuna_study.db.bak-quarantine786-20260613_093831`, and runtime `scripts/autopilot/short_term_memory.md`.

## Do Not

- Do not resume AutoPilot while standalone calibration is running.
- Do not treat dashboard inference as AutoPilot unless `autopilot_state.json` and `logs/autopilot.log` contradict the paused state.
- Do not promote a partial `core_v2` target without a new `core_id` and explicit handoff/progress rationale.
- Do not run full `/wrap-up` pruning/wiki compilation unless the operator explicitly asks for `/wrap-up`.
