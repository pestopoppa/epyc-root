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
