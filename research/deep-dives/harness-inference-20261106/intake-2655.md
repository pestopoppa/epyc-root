# Durable Execution for Agent Runtimes: Workflow Engines, Replay, and Recoverable AI Work

**Intake**: intake-2655 · **Verification**: dive-verified · **Read depth**: PARTIAL · **Source**: https://zylos.ai/research/2026-04-27-durable-execution-agent-runtimes/

## What the dive found

2026-11-06 Stage-2 dive (read_depth PARTIAL; page read from disk, every workflow-engine statement checked against Temporal and Inngest primaries fetched the same day). All three claims confirmed at the vector the source states, with two precision edits: Continue-As-New is a roll-forward to a new Run Id, not compaction, and 'durable record over prompt summary' is a design principle with no engine counterpart. The EPYC session-bus audit is the payload: rule 9's rebuildability is enforced by a runnable `rebuild` (BUS_PROTOCOL:85-91; session_bus.py:2538-2583), boundary receipts are keyed by boundary_id and deduped (BUS_PROTOCOL:533-553), and there is NO time-bounded idempotency anywhere - retention is cursor-gated and --stale-after-h only prints a label. So EPYC is not exposed to constraint 3, and importing a vendor-style TTL would be a regression. One real defect found: `append` honours a caller-supplied message id without a uniqueness check (session_bus.py:1607-1611) while every consumer dedupes by id, so a collision silently loses a message. The R6c rationale at coordination-and-churn-pipeline.md:437-441 is stale against current rebuild_state and should be re-screened.

## Claims and corrections

- claim 0: **unaffected** — Confirmed against Temporal primaries: replay re-runs orchestration from the beginning and reuses journaled Activity results rather than recomputing them. Precision edit: the source says 'should' (a prescription), and 'resume from recorded cognition' is the author's framing - the primitive is 'record the model/tool decision as an activity result'.

- claim 1: **narrowed** — Clause 1 verified numerically (Event History warning at 10,240 events, termination at 51,200 events / 2,000 Updates / 10,000 Signals; Continue-As-New recommended to avoid the limit). But Continue-As-New is NOT compaction: it starts a new execution segment with the same Workflow Id and a different Run Id, retaining the old history. Clause 2 (durable record over prompt summary) has no primary counterpart and is the author's design principle.

- claim 2: **unaffected** — Confirmed twice from Inngest primaries: event-level idempotency is 24h on producer id, function-level 24h on a CEL expression. Primary is stronger than the source - idempotency is also ignored for debouncing, event batching, and while a function is paused.


## Anchors

intake-2655 carries 6 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
