# Consolidated unblock

generated 2026-07-27T20:29:59+00:00  ·  epyc-root @ 92fa6c99
pending 3 · granted 0 · struck 0 · malformed 0

## The one command

    bash /workspace/artifacts/operator/unblock.sh

It applies every gate you ticked, skips the rest, and reports what it did.
Add `--plan` to see what it would run without running anything.

## How to adjudicate

Edit `coordination/session-bus/tokens/token-queue.md` — the only file whose
checkboxes you own:

    - [x] **GATE-ID** … GRANTED 2026-07-27      apply it
    - [ ] **GATE-ID** … STRUCK 2026-07-27 — why  decline this round; stays held

Leave a line untouched to decide later. Never delete a line: a missing gate
reads as *absent*, not as *declined*. An ISO date is required — an undated
grant leaves no record of when you gave it.

## Awaiting your decision

### OP-SENDKEYS-CODEX

- holds: _no task currently held_
- **no pre-validated command recorded** — this gate cannot be applied
  automatically. The requesting agent owes dry-run evidence; presenting
  an unvalidated command is an agent defect, so nothing is guessed here.

### triage

- holds: _no task currently held_
- **no pre-validated command recorded** — this gate cannot be applied
  automatically. The requesting agent owes dry-run evidence; presenting
  an unvalidated command is an agent defect, so nothing is guessed here.

### headless-worker

- holds: _no task currently held_
- **no pre-validated command recorded** — this gate cannot be applied
  automatically. The requesting agent owes dry-run evidence; presenting
  an unvalidated command is an agent defect, so nothing is guessed here.

