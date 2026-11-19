# rowflow

Inference-row flow: `publish_row.py` (owner publishes + smokes), `rowflow.py allocate` (the keeper tick, sole grant
writer), `filler_run15.sh` (launcher wrapper), `notify.py` (terminal-event alerts). Protocol:
`docs/guides/agent-workflows/backlog-churn-flow.md`.

## The inference mailbox (operator 2026-11-05)

Every row alert (`row-ended`, `smoke-fail`, `disk-floor`) is appended once to
`/mnt/raid0/llm/tmp/compute-flags/notify/inbox/inference.jsonl` (`rowflow.inbox.v1`: key, ts, kind, severity, row_id,
owner, handoff_task, publisher, reason, summary), in addition to `rowflow-alerts.jsonl` and the session-bus message to
`inference`. `publisher` (roster id / session token / user / time, from `publish_row.py`'s env) is information only.

    rowflow.py alerts [--since <ts>] [--row <glob>] [--unacked] [--json]   # read (read-only)
    rowflow.py alerts --ack <key> [--by <id>] [--note <text>]              # mark handled (append-only acks file)

Three delivery paths, none of which depends on someone remembering to look:

1. **Dispatcher (headless owners).** `handoff_sessions.py` prepends an `UNHANDLED ROW ALERTS` block (that session's
   unacked alerts, matched on row owner / handoff_task / its rows / publisher session) to every launch and resume
   prompt, and wakes a non-running owner with an unacked critical alert (once per 30 min, within `max_live`). It never
   acks; the owner does.
2. **Keeper escalation.** A critical alert unacked for `ROWFLOW_ALERT_ESCALATE_S` (default 1800 s) is routed once to
   the operator alarm channel (`route_alert`) and logged as `kind=alert-unacked` in `rowflow-alerts.jsonl`.
3. **Interactive sessions.** Any session that publishes inference rows MUST arm this zero-token watcher (Bash
   `run_in_background`, never `&`); it exits, and so wakes you, when an unacked alert newer than the arm time appears (drop `--since $S` to
   also wake on older unhandled ones):

```bash
S=$(date -u +%FT%TZ); R=/workspace/scripts/coordination/rowflow/rowflow.py; until [ -n "$(python3 $R alerts --unacked --since $S)" ]; do sleep 60; done; python3 $R alerts --unacked
```

   Handle each alert, then `rowflow.py alerts --ack <key>`; re-arm the watcher.

## Friction pass-4 rules (operator 2026-11-06, emergency deploy into the frozen keeper)

`docs/reports/coordination/keeper-friction-review-20261105.md` Pass 4 (P4.3 / P4.4). Replay scenarios `p4-*`
(`tests/replay/scenarios.py`). Only `COMPLETE_BEFORE_RC14` still has a module flag and a negative control; the
always-on switches were deleted 2026-11-10 (pipeline audit #9, INCIDENT_LOG `INC-20261110-rowflow-switches`).

1. **Refusal terminal once.** A launcher `--precond-cmd` refusal (rc=12) PARKS the row at the first refusal: one FAIL
   record, one alert, a `PARK <id>` line. It is retried only after its launcher or manifest sha changes, or after
   `rowflow.py unpark <id> [--by <who>] [--note <text>]` (writes `dryrun/<id>/UNPARK.json`; earlier arming FAILs no
   longer count). Other admission refusals keep the `MAX_FAILS` rule.
2. **A completed row is not rc=14.** A poller that is dead after `grants/<id>.complete` (or an `.ended` receipt
   `rc=0 ... reason=complete`) logs `COMPLETE <id>` and writes no FAIL.
3. **GPU idleness by GPU signals.** A grant holding `gpu-quiet` is judged by its own KFD clients and the device busy %
   only (never by the CPU % of the regions it holds); it reads `IDLE-HELD gpu-quiet` only after `GPU_IDLE_SAMPLES` (2)
   consecutive quiet samples (state `ws58-keeper-state/allocator/gpu_idle.json`). The dry run never raises
   `OVER-DECLARED busy_fraction` for a GPU-token row.

## No-hold deploys and backfill-if-fits (operator 2026-11-07, emergency deploy into the frozen keeper)

Origin: a global `HOLD-ADMISSIONS`, set so a keeper deploy could go out safely, idled q2, q3 and the GPU for hours; a
renamed `HOLD_ADMISSIONS.lifted-symlink` still matched the keeper's `HOLD_*` glob; and the whole-host row
`c7-local-code28k-20261106-r3` (q0-q3) was reported as keeping q2/q3 drained while the LSA rows held q0/q1 for 10+ h.

1. **Engine snapshot at row launch**. `arm_one` copies `filler_run15.sh` and every file a running
   poller or launcher re-reads (`filler_lib.sh`, `notify.py`, `diskpause.py`, `loop_metrics_hook.sh`) into
   `<flags>/dryrun/<id>/engine/` (read-only, `ENGINE.json` with sha256s) and passes `FILLER_ENGINE_SNAPSHOT`; the live
   engine re-execs that copy at once, so a running row executes only its snapshot. `ARMED.json` records
   `engine_snapshot`. The live directory stays the home of shared state (`FILLER_ENGINE_HOME`).
2. **Deploys need no hold.** `deploy_rowflow.sh` refuses (exit 75) only while LEGACY grants are open - pollers armed
   before this change that still read `bin/rowflow/` (`rowflow.py --flags F legacy-grants` lists them;
   `deploy-guard` decides) - unless `--allow-open-grants`. `deploy_when_drained.sh` sets no hold any more: it waits
   for the legacy grants only, admissions continue.
3. **Hold names.** `HOLD_<NAME>` stays the explicit operator emergency stop, matched by EXACT name only (no dot, no
   suffix, an existing file): `*.lifted*`, `*.disabled*` and dangling links never hold (`operator_holds`).
4. **Backfill-if-fits** (port of rowflow2 59f09b81e). A wide row that waited `DRAIN_AFTER_S`
   reserves its regions only until its earliest feasible start S = the latest end of the grants (live smokes:
   `SMOKE_HOLD_S`) holding the regions of its best option; a lower row may take them (free quarters or the GPU) iff
   now + its estimate <= S. S unknown (a needed region held with no known end), not in the future, or beyond the
   longest busy window -> no reservation at all (`NO-RESERVE` line). A persisted drain T is used only while it is
   still in the future: an expired drain never blocks.

Tests: `tests/test_rowflow_nohold_deploy.py` (a real poller on its snapshot survives a broken live engine set; hold
names), `tests/test_rowflow_backfill_if_fits.py`; replay scenarios `backfill-*` (a strict reservation fails the LSA /
whole-host incident scenario).
