# Task: test coverage for the session bus

**Assigned to** `codex-bus-tests` (roster id — use it verbatim for every bus command).
**Assigned by** coordinator-agent, operator-directed, 2026-07-28.
**Lane** `none`. You must **never** take a `cpu` or `gpu` lane: another codex main is running
G3/E8 inference on this host. Nothing in this task needs inference.

## Why this exists

The session bus is now load-bearing for cross-session coordination and has **zero automated
tests** — no file under `tests/` references `session_bus`. That gap was found on 2026-07-28
while repairing defects C1–C4, which had left the coordinator-agent message plane dead in both
directions for an entire session without anything noticing.

Every one of those defects was mechanically testable. That is the standard to hit: a regression
suite that would have caught them.

## Files under test

- `scripts/coordination/session_bus.py` — agent CLI (append / drain / cursor / fold / validate /
  provision / rebuild / status)
- `scripts/coordination/session_bus_coordinator.py` — daemon (transcribe, relay, advice,
  revocation, stall ladder, epoch fencing)
- `coordination/session-bus/session_bus.schema.json` — msg + queue_row schemas
- Contract: `coordination/session-bus/BUS_PROTOCOL.md` — **read this first; it is the spec.**

## Required coverage

Anchor each test to the protocol rule or defect it defends. Rule numbers are BUS_PROTOCOL's.

### The four repaired defects — regression tests, non-negotiable
1. **C1** — a roster member with no inbox is detectable; `provision` creates exactly the 4 files,
   is idempotent, and refuses an id absent from the roster.
2. **C2** — an agent-authored outbox message addressed to another agent is relayed to that
   agent's inbox; the original `from` is preserved; a second tick relays nothing (idempotence via
   `relayed_src`); `to: "*"` fans out to all roster members except the sender; kinds in
   `_NO_RELAY_KINDS` are not relayed; a schema-invalid outbox row is **skipped** and reported as
   a defect rather than propagated.
3. **C3** — `drain` on a missing inbox exits non-zero and says so; `drain` on a genuinely empty
   inbox exits 0. These two must not be confusable — that ambiguity is what hid C1.
4. **C4** — a `requires_ack` message unacked past `ack_deadline_s` is redelivered as a `nudge`
   with the same `corr_id`, and a consumer that dedupes by msg `id` sees it once.

### Protocol invariants
5. **Rule 1 (single writer)** — `append` refuses a target path whose owner is not the asserted
   `--agent`, for every combination: queue, another agent's inbox, another agent's outbox,
   another agent's heartbeat. `validate`'s ownership lint flags a row whose `from` != file owner.
6. **Rule 4 (cursors)** — a cursor only advances; `drain --peek` does not advance it.
7. **Rule 8 (quiesce-and-drain)** — a `lease-revoke` from an authorised sender marks the row
   `revoking` with status UNCHANGED; the holder reporting `draining` releases it to `READY` with
   owner cleared; the released task is **excluded from that same tick's assignment**. An
   unauthorised sender is rejected with a `defect` and the lease is untouched.
8. **Rule 9 (reconstructibility)** — `rebuild` derives the same state from bus files alone after
   a process restart; no in-memory-only authority.
9. **Rule 10** — a queue row with no `gating` classification is a hard validation failure.
10. **Epoch fencing** — advisory rows carry the epoch; a stale-epoch record is identifiable.

## Hard constraints

- **Every test runs against a temporary bus root** (`tmp_path`), never
  `coordination/session-bus/`. Tests that mutate the live bus are an automatic fail — a live
  daemon and two working mains are reading those files right now.
- **Never start, stop, signal or `pkill` the coordinator-daemon.** If a test needs a tick, call
  `tick(bus_root, epoch)` / `cmd_once` directly against your temp root.
- No network, no inference, no `region-lock`, no benchmarks.
- Interpreter: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python` (it carries `jsonschema`; the
  system python3 does not).
- Place tests under `tests/`, following the existing naming convention.
- Pre-existing unrelated failures you are **not** responsible for and must not "fix":
  `tests/compliance/` collection error (missing module), `test_e8_quality_*`,
  `tests/validate/test_repo_readiness_scorer.py`.

## Definition of done

- `pytest tests/test_session_bus*.py -q` green.
- The full suite shows no NEW failures beyond the pre-existing ones listed above.
- Each test names the rule or defect id it defends, in the test name or a docstring.
- Report via your outbox; do not tick checkboxes anywhere.

## Bus protocol for you

Register first so the daemon can see you:

    ./scripts/coordination/session_bus.py append --agent codex-bus-tests \
      --target heartbeat --json '{"state":"working","task_id":"bus-test-coverage"}'

At **every** task boundary, both of these:

    ./scripts/coordination/session_bus.py drain --agent codex-bus-tests
    ./scripts/coordination/session_bus.py append --agent codex-bus-tests \
      --target heartbeat --json '{"state":"working","task_id":"bus-test-coverage"}'

A heartbeat written once is a birth certificate, not a liveness signal. Report status and
findings to `outbox/codex-bus-tests.jsonl` — it is the only outbox you may write. Address
messages to `coordinator-agent`.

If you find further defects while writing these tests — likely, since nobody has ever tested
this code — file them as `kind: finding` to `coordinator-agent` rather than fixing the bus
yourself. A test that documents a real defect should be written and marked `xfail` with the
reason, not quietly adjusted until it passes.
