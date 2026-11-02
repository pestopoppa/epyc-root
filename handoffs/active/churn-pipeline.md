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

- [x] **Land the MIN_RESUME_GAP_S fix** ✅ 2026-11-02 superseded by dispatcher rewrite ROOT `9612fb48d` [no-belief: tooling]
- [x] **Inventory-target dispatcher change** ✅ 2026-11-02 replaced by operator-loop dispatcher (next = non-inference/inference/blocked/done; yield/cooldown/stuck/park/inventory gates deleted) ROOT `9612fb48d` [no-belief: tooling]
- [ ] **CAF burn measurement**: tokens per completed task before/after CAF-1..7 via `churn/tokens_per_task.py`.
- [ ] **Net line count must go down**: `handoff_sessions.py`, `backlog_gen.py`, `rowflow/`, `churn/` grew this day; find deletions (guardrail unmet).
- [x] **Hotfixes landed** ✅ 2026-11-01 ROOT `139d9cf7a` `ddf791068` `0fec383f5` `a57b57239` [no-belief: tooling-repair; no measurement]
- [x] **Keeper v11 single allocator** ✅ 2026-11-01 ROOT `1a9186e11` [no-belief: build/landing]
- [x] **churn_up.sh persistence runbook** ✅ 2026-11-01 ROOT `d095b4a4d` [no-belief: build/landing]

## Typed decisions and Super-agent patterns from intake-2604/2615 (ws58 intake 2026-11-02; operator approved "Approve, go to Stage 4", D9 acknowledged for scripts/coordination)

Plan: [README.md](../../research/deep-dives/ws58-jev-20261102/README.md). **Order (operator, 2026-11-02):** (1) SA-1 + JEV-1; (2) SA-2, SA-3, JEV-3; (3) JEV-5 phase A, KT-1, KT-3; (4) the rest (JEV-2, JEV-4, JEV-6, SA-4, KT-2, KT-4, KT-5). JEV-5 phases B/C only after the operator has used phase A.

- [ ] **SA-1** [S] Merged into the in-progress sticky-slot change (`54c23474e`, `sticky()`/auto-start gate in `handoff_sessions.py`): auto-start admits only a handoff with a ready row or an operator pin, adds a per-slug start cooldown and a global starts/hour cap, logs `AUTO-START-THROTTLED`; fixtures for rows=[] and just-done. Evidence: 61/63 AUTO-STARTs with `rows=-` on 2026-11-01/02 (intake-2615#record). removes: fresh-session bootstrap per freed slot, the done-then-restart loop, `restarted_from_done` re-admission without a ready row.
- [ ] **SA-2** [S] Zero-token watchdog inside the existing keeper pass (no new daemon): count AUTO-START/DONE per hour against ready rows unclaimed and alarm on starts over cap with no effect. removes: operator log-grepping to spot thrash.
- [ ] **SA-3** [S] Run-end and awaited events carry related ids (row, run, handoff) into the resume `delta()`, so a resumed worker gets a chain-of-recall delta (intake-2615#record). removes: the worker's cold re-read of handoff and row files on each resume.
- [ ] **JEV-3** [M] REPLACE the regex failure classifier (`rowflow/publish_row.py:82-104`, `UNKNOWN-FAILURE-CLASS`) and `handoff_sessions.work_state` regexes with the local native `src/typed_decisions/` path (TD-29: 18/18) returning a named label plus named park/stop reasons; replay of saved `dryrun/*/FAIL-*.json` is a regression check only, no new accuracy study (intake-2604#record). removes: `_UNIT_RE`/`ADV_RX`/`OWN_TASK_RX` regex classification, the UNKNOWN-FAILURE-CLASS fall-through, unnamed MAX_FAILS parking.
- [x] **SA-4** ✅ 2026-11-02 ROOT `1579bd509` [no-belief: doc rule; no measurement] [S] `docs/guides/agent-workflows/agent-loop-design.md`: a long-lived worker per task with code pass-through of its thread's events; fresh start only on a ready row; a watch for unproductive loops (intake-2615#record). removes: per-event fresh-session dispatch as an accepted loop shape.
- [x] **JEV-6** ✅ 2026-11-02 ROOT `1579bd509` [no-belief: doc rule; no measurement] [S] `docs/guides/agent-workflows/agent-loop-design.md`: typed judgments carry label probabilities and a confidence with two thresholds set from held-out real outcomes; unavailable is never an answer; a worker claim is never a result (intake-2604#record, intake-2605#record, intake-2608#record). removes: free-text agent decisions as an accepted loop shape.

## 2026-11-02 wrap-up (ws58)

- [x] **Owner carries row through dry run** ✅ 2026-11-02 ROOT `549eb58` (supersedes `1f054f2c4`) [no-belief: tooling]
- [x] **Sparse lanes keep artifacts/operator/*.sh** ✅ ROOT `ac7e2e1fc` [no-belief: tooling]
- [x] **wrapup.py resolves generated-index conflicts; report.json on every exit** ✅ ROOT `c9eb9e2b8` `005a7fbf5` [no-belief: tooling]
- [x] **Hub pipeline section / backlog graph** ✅ ROOT `28b23bf37` `1c869a310` `60ec225af` `100cb18ba` `8fe3693e9` `4693451cb` [no-belief: dashboard]
- [ ] **JEV-3 deferred**: replace commit `7b2b40b42` kept, uncalled; 1.5B native replay unusable (constant answers, confidence 1.0), `/mnt/raid0/llm/tmp/ws58-csh/jev3-replay-1p5b-20261102.json`.
- [ ] **Measure row publication** after the 10:41Z fixes.
- [ ] **Sessions over-prepare instead of publishing**: find and cut.
- [ ] **Dashboard readied-waiting count is 0**: row/handoff linking bug.
- [ ] **RTG-18 graph checkbox-parse bug**: graph shows open=0, file has 12 open boxes.
- [x] **Turn-end rules, light worker persist, central index_regen.py; box id per turn, steps-since-tick, push lock 15 min** ✅ 2026-11-02 ROOT `30b2ed75c` `262de5c98` [no-belief: tooling]
- [x] **Dry runs take no lock; publish smoke never refuses for busy; smoke disk floor 20 GiB; GPU smokes queue between GPU jobs; tiny rows unscheduled, port exclusivity, drain T + backfill; dry-run harness reaps process group** ✅ 2026-11-02 ROOT `d4f22dccd` `fc4e4352f` `6e0f27d5c` `59c2beb79` `70e5666b1` `d9838cf37` [no-belief: tooling]
- [x] **Dispatcher scratch quota (SCRATCH-OVER)** ✅ 2026-11-02 ROOT `5b34a2409` [no-belief: tooling]
- [x] **Dashboard row badges, legend/info panel, open-count parser fixes, engram boxes** ✅ 2026-11-02 ROOT `23791d952` `6f1f97b43` `da51eb293` `2c360a3ee` [no-belief: dashboard]
- [ ] **Sub-quarter packing**: packing agent was stopped; unfixed.
- [ ] **Rows published with a non-inference payload as compute rows** (e.g. gitnexus analyze held all 96 cores).
- [ ] **Row estimate_s vastly overstated**: fix estimator.
- [ ] **Per-row UNDERUSED is only logged**: act on it.
- [ ] **OBS-CHURN-UP** `churn_up.sh` liveness probes (pidfile+argv, exact-path argv over /proc) are registered `unadopted` in `observer_registry.json`: adopt `observer_guard.sh` three-valued state (measured / absent / blind).

## Stop-everything, disk reclaim and runbook (2026-11-02 afternoon, ws58)

- [x] **Backlog-churn runbook; keeper v12 in git; `churn_up.sh` `--stop` `--status` `--dry-run`** ✅ 2026-11-02 ROOT `27b94990f` [no-belief: tooling]
- [x] **Disk fixes: reaper idle 1 day; standalone `disk_janitor.sh` (reap 30 min, trash sweep hourly); SCRATCH-COPY detection in dispatcher; scratch cleanup on retire** ✅ 2026-11-02 ROOT `c1068744f` [no-belief: tooling]
- [ ] **Verify the disk janitor** (started 14:05Z pid 190444): FREE trend >= 1 day, `.trash` nothing older than about 25 h, no SCRATCH-COPY outstanding.
- [ ] **3 half-cleaned worktrees**: `vgpr-compiler-ab-20260915`, `fix-pii-hook-numeric-json-20261021`, `noninf-20260924/inf41/epyc-orchestrator`.
- [ ] **Dirty/unlanded trees under `tmp/` and `autokernel/` never processed** by the reclaim.
- [ ] **Dangling references to deleted data**: `artifacts/compute/codex3-*` cite `data/stt-cs8-public-20261030`; `memento-block-reasoning-compression.md` cites openmementos; about 10 files cite `backups/episodic-leak-20260917` (`ratify_v10_episodic_repin_20260917*`, `promptforge-mutation-safety-contract.md`, `wiki/safety.md`, orchestrator `purge_eval_leak_memories_20260917.*`).
- [ ] **rowflow test `test_complete_in_smoke_is_filed_not_queued` fails on main.**
- [ ] **Pipeline restart is operator-gated** (all grants revoked to `tmp/ws58-csh/revoked-grants-20261102/`; dispatcher, keepers, watchdogs, filler_run13 launchers stopped).
- [ ] **Registry graveyard row for Qwen2.5-Coder-32B-Instruct-Q4_K_M** (operator deleted the file): commit was blocked by the orchestrator pre-commit contention-matrix freshness hook (matrix stale, cannot refresh with the stack stopped). Patch at `tmp/ws58-csh/registry-graveyard-q4km-20261102.patch`. Also `server_mode.qwen25_coder_32b_q4km` still resolves to the deleted file; needs a stack-change deprecation.
- [ ] **Fable backlog-refactor audit** in progress; output `tmp/ws58-csh/backlog-refactor-proposal-20261102.md`.
