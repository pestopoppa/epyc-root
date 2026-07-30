# Coordinator Escalation — unreachable sessions, guard refusals, rate limits

Operational procedure extracted 2026-07-30 from `agents/coordinator-agent.md` (AFC-P6
restructure). The role file keeps the directives; this doc holds the full ladder and timer
constants. Incident narratives: `docs/reference/agent-config/INCIDENT_LOG.md`.

## Guard-refusal ladder (nudge refused on heartbeat/quiet-check)

A guard refusing a nudge on stale or contradictory data is NOT license to bypass it. If
`tmux_adapter.py nudge` refuses because the target's heartbeat reads `working`:

1. **Confirm from the pane** whether the session is genuinely idle or genuinely mid-generation —
   do not assume either way. A genuinely mid-generation session is not blocked at all;
   escalating it is misreading a guard that is working correctly.
2. **Know the deadlock shape**: a completed session that never refreshed its heartbeat, now
   blocked waiting for input, cannot refresh the heartbeat either — and `--heartbeat-max-age`
   does not rescue it because the refusal keys on state, not age. Even then, do not send keys
   around the guard.
3. **Keep re-probing instead of reporting.** `tmux_adapter.py probe --agent <id>` is read-only
   and cheap. A refusal is a snapshot, not a verdict: the quiet-check window (~20s) expires as
   the pane settles; the nudge rate limit (600s, `--min-interval-s`) expires on a timer; a
   stale `working` heartbeat clears at the session's next boundary.
4. **Escalate to the operator only once BOTH hold**:
   - the block has outlived the longest plausible self-clearing timer — anchor to the actual
     timers above; on the order of 10–15 minutes of continuous refusal with no pane activity;
   - something is actually waiting on that session (a deadline-bearing lane, an operator gate,
     another main's dependency). An unreachable session with nothing blocked behind it is a
     note for the next report, not an interrupt.
5. **When escalating**: name the session, what it is waiting on, why the adapter refuses, and
   the exact message to relay. The relayed message must ask the session to refresh its
   heartbeat so the deadlock clears itself. Keep re-probing while the relay is pending; if the
   guard clears on its own, nudge normally and tell the operator the relay is no longer needed.
6. Never busy-wait tightly and never bypass while waiting — continue other coordination work
   between probes (BUS_PROTOCOL rule 2: no agent blocks on the bus, including on a human).

Mirror image of defect C8 (unreachable for want of a delivery path): here the delivery path
exists but the liveness signal lies. Both end with a main sitting idle and invisible.
Origin: INC-20260728-heartbeat-bypass.

## Rate-limit exception after a re-spawn

`--min-interval-s` (default 600) is enforced against the last `nudge` row in the adapter ledger
for that **roster id**, not the window instance — so killing a main and re-spawning it leaves
the FRESH window refusing nudges on account of a message delivered to the destroyed one. That
is the ONE case where passing an explicitly lower `--min-interval-s` is correct: the pane that
received the message no longer exists. This narrow exception does not generalise — a heartbeat-
or quiet-check refusal still means what it says, and you still never route around the adapter
with raw `send-keys`. Origin: INC-20260729-rate-limit-respawn.
