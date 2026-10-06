# Prospective opencode event duty

The source adds an inactive duty. Current registry bytes and daemon defaults do
not change. `HYGIENE_OPENCODE_EVENTS` must equal `1` before the tick considers the
duty. The daily Codex report remains report-only and CPU-gated.

An owning session must review and execute a later runtime handover. It must stop
its identified daemon, verify that PID is dead, deploy the canonical reaper with
`LR8_ONCE_STATUS_V1` support, and set the reaper registry runtime to:

```json
{
  "mode": "scheduled",
  "scheduler": "host_hygiene_tick",
  "restart_on_stale": false,
  "relaunch_if_down": false,
  "log": "/mnt/raid0/llm/epyc-root/logs/hygiene/opencode_event_reaper.log",
  "max_age_s": 3600
}
```

Remove `start_argv`. The exact log must equal the selected hygiene state directory
plus `opencode_event_reaper.log`. Registry scheduled validation requires a
positive `max_age_s`. Then explicitly enable the environment opt-in in the
reviewed owner deployment. This source preparation authorizes none of these steps.

The keeper observes the same registry and skips the scheduled row because
`relaunch_if_down` is false. The tick refuses a malformed or mixed handover, a
missing source capability, any observed reaper copy, or an unreadable process
scan. The process check and subsequent start have a race. The unchanged daemon
does not hold the new lock. This lock excludes concurrent `once-status` jobs;
it cannot prove atomic exclusion against that daemon. The owner must prevent a
daemon restart during handover and keep one scheduler thereafter.
The process scan checks the script name in the first three argv elements.
Wrappers with a later script argument, changed names, or an empty readable
cmdline can escape that identity check. This preflight does not replace the
owner's verified daemon stop. The owner must also reconcile any retired guardian
alarm during the later handover; new scheduled runs neither raise nor clear it.

The duty runs independently of the daily heavy phase. It checks the CPU-region
gate immediately before execution. Successful and failed attempts consume the
1800-second cadence. A busy CPU gate, dry run or refused handover does not.
The nonblocking lock covers the complete new reaper invocation. It exits 75
when another new invocation owns the lock.
Future cadence timestamps raise an alarm and refuse execution, including after
a backwards clock change. The owner must reconcile that state. No unbounded
delay is silently accepted.

`once-status` retains the existing event-table pruning and absent-only VACUUM
decision. Present and unobservable observations withhold VACUUM. This mode emits
one terminal marker with the observation state and actual prune pipeline status.
It delegates alarms to the tick's stable `opencode-event-duty` key. The tick
rejects missing, malformed, duplicate, oversized or contradictory status output,
nonzero status and timeout. Blind and failed results raise the same alarm;
confirmed present or absent results clear it. Failed jobs do not refresh the
scheduled log. State and the latest native result remain under the hygiene
state directory. These operational records are ungraded; do not derive scientific
claims from them or retrofit ClaimTuples after a run.
Result or scheduled-log write failure marks the duty failed and raises its alarm.
A later hygiene heartbeat records tick liveness and cannot establish duty success.
The existing subprocess timeout is not proof that descendants were cancelled.
Inherited lock descriptors can remain with descendants; no cancellation or
descendant exclusion guarantee is claimed by these fixtures.

The existing `run`, `once`, registry policy, live daemon and harness transcripts
retain their current behavior. Synthetic fixture evidence proves only the
tested source behavior, not live handover or cleanup acceptance.
