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

- [ ] **OP-SENDKEYS-CODEX** — allow the coordinator-daemon to nudge a main via
  `tmux send-keys`. Rate-limited, idle-pane-checked. Evidence required: the nudge ladder
  demonstrably exhausted without it. Note this is also the mechanism behind spawning mains into
  new tmux panes, and `caps.max_spawns_per_day` is currently `0`.
- [ ] **triage: on** — enable the M5 one-shot triage hook (dead-agent block drafting + routing
  annotations). Operator flag after the M4 soak; budget-capped by `caps.triage_calls_per_day`.
- [ ] **headless-worker caps > 0** — only after M4 acceptance.

## Pending token requests

_(none — the coordinator-daemon appends relayed blocks below this line)_
