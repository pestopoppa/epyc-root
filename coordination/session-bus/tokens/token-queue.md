# Operator token queue

Clone of the op-bundle grant pattern. **Agents author blocks in their outbox as `token-request`
messages; the coordinator-daemon relays them here verbatim; the coordinator-agent presents them;
the operator flips `[ ]` → `[x] GRANTED <date>`.** Nobody but the operator touches a checkbox.

**Pre-validation is mandatory.** Every block carries the exact command plus dry-run evidence. An
operator-presented command that fails is a **defect row attributed to the requesting agent**, not
an operator problem.

**Presentation is saturation-gated.** The coordinator-agent surfaces pending tokens only while the
saturation snapshot shows lanes busy — *except* when a gate is the sole cause of imminent lane
idleness, which forces immediate presentation. A pending token never gates unrelated work
(`BUS_PROTOCOL.md` rule 2).

**Consolidated unblock (R8).** These blocks are batched into ONE artifact so the operator runs a
single command on return: pinned HEAD + file `sha256`s, refuse on drift, idempotent, per-line
independently validated so striking one line cannot invalidate the rest. A failed validation
repairs and re-presents the **same** token — never a new chain. A struck line's task returns to
`HELD_OP_GATE`: held, not dropped, not silently requeued.

---

## Standing gates (default OFF — grant individually)

- [x] **OP-SENDKEYS-CODEX** GRANTED 2026-07-27 — allow the coordinator-daemon to nudge a main via
  `tmux send-keys`, and to spawn a main as a **window in the one live session**
  (`tmux.live_session`) — never its own session. Rate-limited per agent
  (`--min-interval-s`, default 600s) and capped per day by `caps.max_spawns_per_day`; both values
  live in `config.yaml` rather than here, so this block cannot go stale against them.
  *Granted to authorise the BUILD*: `scripts/coordination/tmux_adapter.py` did not exist at grant
  time, and `capability_status()` reported `NOT IMPLEMENTED` regardless of the flag until it did —
  a flag can never make an absent adapter look present. The original "evidence required: the nudge
  ladder demonstrably exhausted" condition was therefore **not** the basis for this grant, and is
  recorded as superseded rather than quietly dropped.
- [ ] **triage: on** — enable the M5 one-shot triage hook (dead-agent block drafting + routing
  annotations). Operator flag after the M4 soak; budget-capped by `caps.triage_calls_per_day`.
- [ ] **headless-worker caps > 0** — only after M4 acceptance.

## Pending token requests

_(none — the coordinator-daemon appends relayed blocks below this line)_
