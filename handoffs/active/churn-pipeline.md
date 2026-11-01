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

## Churn AI-free mechanization (2026-11-01; operator approved CAF-1..7 with the D9 acknowledgement)

_Source: `research/deep-dives/churn-ai-free-audit-20261101.md` §3 (turn count drives cost; bookkeeping = 23% of
handoff-session spend). Deletion-first: each line names what it deletes before anything is built. ONE schema for the
turn record: `compute-flags/handoff-sessions/<slug>/report.json` = the wrapup JSON (DSH-1 and CAF-2 are the same file):
`{"slug", "state": "progress|ready|blocked|failed|idle|dropped", "task_text", "ticks": [text], "progress_md", "paths": [],
"belief": "cc|clm_<id>|no-belief: <reason>", "message", "question", "rows_published": [], "wrapped_sha"}` — the agent
writes everything but `wrapped_sha`; `wrapup.py` fills it after the push._

- [x] **CAF-1 — no-poll resume.** ✅ 2026-11-01 ROOT `72632c80d` [no-belief: dispatcher conformance; no measurement]
  Deletes: the brief's "do not poll"/"non-blocking code while waiting" prose and every in-turn wait (monitor_wait,
  13.9% of spend). `handoff_sessions.py` resumes a session on its grant end, its dry-run result
  (`dryrun/<id>/PASS.json|FAIL-n.json`) or a file registered under `handoff-sessions/<slug>/awaiting/`. Plus the no-op
  guard: a turn with no commit, no row, no filing is not resumed until a new event (`NOOP` log). Evidence: audit §3.
- [x] **CAF-6 — run-end dedupe.** ✅ 2026-11-01 ROOT `72632c80d` [no-belief: dispatcher conformance; no measurement]
  Deletes: the duplicate `.ended`+`.complete` delivery (`DEDUPE` log; 2 RUN-END lines for stt5-v3-tc-rebind-r1 at 21:49Z).
- [x] **CAF-2 — `scripts/coordination/churn/wrapup.py`.** ✅ 2026-11-01 ROOT `9e10d1186` [no-belief: tooling; no measurement] Deletes: the brief's six-step manual wrap-up prose (progress,
  tick, index check, pathspec commit, serialized_push, cherry) and the agent turns that perform it (wrapup_mech 6.4%);
  the WRAPPED-line regex becomes the one-week fallback only. JSON (schema above) in → progress append, tick-by-text,
  `index_state.py --check`, pathspec commit in the lane with trailers, `serialized_push.py --repo <lane>`, cherry empty,
  `report.json` written with `wrapped_sha`, prints `WRAPPED <sha>`. Deps: none.
- [x] **CAF-3 — resume delta.** ✅ 2026-11-01 ROOT `bcd7653b1` [no-belief: tooling; no measurement] Deletes: "re-read the handoff and BACKLOG" from every prompt and the re-read turns
  (read_brief 22%); `backlog_gen` emits a per-slug state delta (rows: state/rc/result_path; next task text; own inference
  tasks) that the resume prompt carries. Deps: none.
- [x] **CAF-4 — `publish_row.py --repair` + spec lint.** ✅ 2026-11-01 ROOT `f080425df` [no-belief: tooling; no measurement] Deletes: the session turn after a dry-run FAIL of the two known
  classes (result_path → completion marker; derivable spec fields) and the keeper→agent→republish loop for them
  (republish 1.5% + spec_fix 5.2%); the lint stops them at publish time. Deps: none.
- [x] **CAF-5 — `scripts/coordination/churn/file_result.py`.** ✅ 2026-11-01 ROOT `9e10d1186` [no-belief: tooling; no measurement] Deletes: the agent filing turn for rows whose
  `decision_rule` is numeric (filing_verdict 1.7%) and the end_prompt's "YOU file the verdict" prose for them; the
  dispatcher files such rows itself and touches `.FILED`; non-numeric rules take the agent's `{verdict, rationale}` JSON.
  Deps: CAF-2.
- [x] **CAF-7 — codex-gen routing.** ✅ 2026-11-01 ROOT `f080425df` [no-belief: tooling; no measurement] Deletes: codex-gen's bookkeeping tasks (regenerate/commit/push, republish) — they
  call CAF-2/4/5 directly; `GOAL-codex-gen.md` (and its git copy in `scripts/coordination/churn/`) loses the manual steps.
  Deps: CAF-2, CAF-4.

## Open at 2026-11-01 wrap-up (ws58)

- [ ] **Land the MIN_RESUME_GAP_S fix** (gap only after no-effect turns): installed in compute-flags/bin, not on origin/main; owner of `handoff_sessions.py` commits it.
- [ ] **Inventory-target dispatcher change**: in progress, owned by another agent.
- [ ] **CAF burn measurement**: tokens per completed task before/after CAF-1..7 via `churn/tokens_per_task.py`.
- [ ] **Net line count must go down**: `handoff_sessions.py`, `backlog_gen.py`, `rowflow/`, `churn/` grew this day; find deletions (guardrail unmet).
- [x] **Hotfixes landed** ✅ 2026-11-01 ROOT `139d9cf7a` `ddf791068` `0fec383f5` `a57b57239` [no-belief: tooling-repair; no measurement]
- [x] **Keeper v11 single allocator** ✅ 2026-11-01 ROOT `1a9186e11` [no-belief: build/landing]
- [x] **churn_up.sh persistence runbook** ✅ 2026-11-01 ROOT `d095b4a4d` [no-belief: build/landing]

