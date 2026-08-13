# mainD — Fix compute-request / compute-grant / compute-deny schema kinds

**You are mainD** (roster id `mainD`, C-OWN: the session-bus delivery plane). Bootstrap: run
`session_bus.py provision --agent mainD`, then `drain --agent mainD --triage`, then execute this brief.

## Premise (verified today by three mains independently)

`BUS_PROTOCOL.md` rule 11 (operator directive 2026-08-13) instructs requesting mains to write
`kind=compute-request` (and inference to reply `compute-grant` / `compute-deny`). But
`coordination/session-bus/session_bus.schema.json` `msg.kind` enum lists only 14 kinds — none of the
three exist. Consequences:

- `append` **REFUSES** `kind=compute-request` at authoring (schema violation).
- The relay validates every outbox row against the full schema before fan-out, so the kind could
  never deliver even if authored. The directive is **structurally undeliverable** as written.

Evidence (bus): mainB `msg-20260813T110107Z-25-mainB`, mainC `msg-20260813T110430Z-29-mainC`,
mainA `msg-20260813T111333Z-69-mainA`. Workaround in use fleet-wide (`kind=status` +
`payload.request_kind=compute-request`) satisfies intent but violates the letter of rule 11.

## Task

1. Add `compute-request`, `compute-grant`, `compute-deny` to the `msg.kind` enum in
   `session_bus.schema.json`.
2. Define the payload shape for each, matching rule 11's mechanism:
   - `compute-request`: task, window (named boundaries), device/region, `est_h`, release-condition.
   - `compute-grant`: accepted window boundaries.
   - `compute-deny`: reason + what to do next.
3. Add/adjust tests in `tests/test_session_bus.py` proving each kind authors AND relays.
4. Update `BUS_PROTOCOL.md` rule 11 **only if** the enum addition requires a wording change — as
   written, adding the kinds makes the existing rule true, so prefer leaving rule 11 unchanged.

## Constraints

- lanes `[none]` — no compute, no region claims, no process management (config.yaml roster).
- **Do NOT push.** Commit locally only — push-serialization freeze is still the operative fleet
  instruction until the operator rules otherwise. Surface any work that would be blocked by it.

## Verification

- C34: use `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python` for every bus WRITE and every
  `validate` (the bare interpreter has no jsonschema and lies clean).
- Run `python3 -m pytest tests/test_session_bus.py` (or the repo's test command) plus
  `session_bus.py validate`.
