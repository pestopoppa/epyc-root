# Churn pipeline — dispatcher, backlogs, rows (ws58, opened 2026-11-01)

**Row**: RTG-62 · **Index**: routing-and-optimization-index.md · **Owner**: ws58 (calendar owner) · **Scratch**:
`/mnt/raid0/llm/tmp/compute-flags/` (runtime), `/mnt/raid0/llm/tmp/ws58-*` (scratch; reclaim at wrap-up)

The backlog-churn pipeline: `scripts/coordination/handoff_sessions.py` (dispatcher), `backlog_gen.py`, `rowflow/`,
`churn/`, `GOAL-codex-gen.md`. Canonical flow: `docs/guides/agent-workflows/backlog-churn-flow.md`. This is NOT the
session bus (`session-bus-thin-dispatcher.md`, RTG-34): operator guardrail 2026-11-01 — keep this handoff small.

**Deletion-first (operator guardrail, 2026-11-01).** Every item must REMOVE more than it adds (code paths, files, prompt
text, states, agent steps). Before building an item, its line here says what it deletes or replaces; an item that only
adds is merged into `handoff_sessions.py` / `rowflow.py` or dropped. No new daemons, buses, registries or lock types.
Net line count of `handoff_sessions.py`, `backlog_gen.py`, `rowflow/`, `churn/` and the number of running pipeline
processes are reported at each wrap-up and must go down or stay flat.

## Dispatcher reliability from intake-2603 (dsh-superagent prototype; operator approved "All four" + DSH-5, 2026-11-01)

_Filed from `research/deep-dives/intake-2603-dsh-superagent-prototype.md` (`intake-2603#record`). Adopt the patterns,
not the component. Operator acknowledged the `scripts/coordination/**` code merge under ratified D9 (2026-11-01).
Owner: the `handoff_sessions.py` dispatcher (ws58). Zero compute._

- [x] **DSH-2** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Run-end events are acked by receipt, not by turn end: keep pending_event until filing-done/<id>.FILED exists; re-queue it when a turn ends without the receipt (cap 3, then operator-escalations/); backlog_gen shows ended-unfiled rows as "needs filing", not done. Acceptance: fixture test with a crashed end_prompt turn re-delivers the event once and files once. [unblocks: owner-filed results] [no-belief: dispatcher reliability; no measurement]
- [x] **DSH-1** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [M] Structured turn report: each session writes compute-flags/handoff-sessions/<slug>/report.json {state: progress|ready|blocked|failed|idle|dropped, wrapped_sha, question, rows_published} at its wrap-up; the dispatcher reads it first and falls back to the WRAPPED/IDLE regex for one transition week. Acceptance: pause-rule fixtures pass on report.json alone; transfer prompt includes the last report. [no-belief: dispatcher contract; no measurement]
- [x] **DSH-3** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Transient-failure retry: a turn that ends rc!=0 with a 408/5xx/connection-reset error line (not a usage limit) and no WRAPPED is resumed with "go on" up to 3x with backoff 2/4/8 min, then marked failed in the backlog; PUSH_PROMPT only when a WRAPPED sha exists but has not landed. Acceptance: fixture tests for each branch. [no-belief: dispatcher reliability; no measurement]
- [x] **DSH-4** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Reserve one dispatch slot above max_live for run-end filing resumes, so a finished row's owner is never queued behind auto-start. Acceptance: fixture with max_live live sessions still dispatches a run-end event. [no-belief: dispatcher scheduling; no measurement]
- [x] **DSH-5** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Add a fifth "loop block must show" item to docs/guides/agent-workflows/agent-loop-design.md: how the loop learns each actor's terminal state (a structured record, never free-text parsing) and when an input counts as consumed (ack by durable receipt, redelivered at most N times). Cite actors.py _has_answer/resume.py, controller_io.py extract_action_with_repair/autopilot.py _recover_from_in_flight_trial as conforming examples, and handoff_sessions.py as the DSH-1/2 counterexample. [no-belief: doc rule; no measurement]

