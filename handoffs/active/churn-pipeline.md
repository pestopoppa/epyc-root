# Churn Pipeline — dispatcher, backlogs, rows

**Status**: ACTIVE — split out of `coordination-and-churn-pipeline.md` on 2026-11-09 (RTG-34, operator decision "Split out churn, trim rest"); the dispatcher, backlog-generator and rowflow defect list.
**Owner**: Pipeline (Pipeline Management)
**Scratch**: `/mnt/raid0/llm/tmp/compute-flags/` (runtime), `/mnt/raid0/llm/tmp/ws58-*` (scratch; reclaim at wrap-up)
**Back-pointer**: split from [coordination-and-churn-pipeline.md](coordination-and-churn-pipeline.md#track-churn-pipeline) (`## Track: churn-pipeline`, folded there 2026-11-02 from the former `churn-pipeline.md`, row RTG-62). Split justification (handoff-index-authoring.md rule 5): a different owner (Pipeline, not the coordination plane) and a first screen that no longer answered "what next?". Body moved verbatim; every box kept its text and ID.
**Created**: 2026-11-01 (ws58) · **Split**: 2026-11-09
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)


> Folded from `handoffs/active/churn-pipeline.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F18, route 1a, operator D1/D5; retired row RTG-62 → RTG-34). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Churn pipeline — dispatcher, backlogs, rows (ws58, opened 2026-11-01)

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

#### Dispatcher reliability from intake-2603 (dsh-superagent prototype; operator approved "All four" + DSH-5, 2026-11-01)

_Filed from `research/deep-dives/intake-2603-dsh-superagent-prototype.md` (`intake-2603#record`). Adopt the patterns,
not the component. Operator acknowledged the `scripts/coordination/**` code merge under ratified D9 (2026-11-01).
Owner: the `handoff_sessions.py` dispatcher (ws58). Zero compute._

- [x] **DSH-2** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Run-end events are acked by receipt, not by turn end: keep pending_event until filing-done/<id>.FILED exists; re-queue it when a turn ends without the receipt (cap 3, then operator-escalations/); backlog_gen shows ended-unfiled rows as "needs filing", not done. Acceptance: fixture test with a crashed end_prompt turn re-delivers the event once and files once. [unblocks: owner-filed results] [no-belief: dispatcher reliability; no measurement]
- [x] **DSH-1** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [M] Structured turn report: each session writes compute-flags/handoff-sessions/<slug>/report.json {state: progress|ready|blocked|failed|idle|dropped, wrapped_sha, question, rows_published} at its wrap-up; the dispatcher reads it first and falls back to the WRAPPED/IDLE regex for one transition week. Acceptance: pause-rule fixtures pass on report.json alone; transfer prompt includes the last report. [no-belief: dispatcher contract; no measurement]
- [x] **DSH-3** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Transient-failure retry: a turn that ends rc!=0 with a 408/5xx/connection-reset error line (not a usage limit) and no WRAPPED is resumed with "go on" up to 3x with backoff 2/4/8 min, then marked failed in the backlog; PUSH_PROMPT only when a WRAPPED sha exists but has not landed. Acceptance: fixture tests for each branch. [no-belief: dispatcher reliability; no measurement]
- [x] **DSH-4** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Reserve one dispatch slot above max_live for run-end filing resumes, so a finished row's owner is never queued behind auto-start. Acceptance: fixture with max_live live sessions still dispatches a run-end event. [no-belief: dispatcher scheduling; no measurement]
- [x] **DSH-5** ✅ 2026-11-01 ROOT `7259bbdc8` [no-belief: dispatcher conformance; no measurement] [S] Add a fifth "loop block must show" item to docs/guides/agent-workflows/agent-loop-design.md: how the loop learns each actor's terminal state (a structured record, never free-text parsing) and when an input counts as consumed (ack by durable receipt, redelivered at most N times). Cite actors.py _has_answer/resume.py, controller_io.py extract_action_with_repair/autopilot.py _recover_from_in_flight_trial as conforming examples, and handoff_sessions.py as the DSH-1/2 counterexample. [no-belief: doc rule; no measurement]

#### Churn AI-free mechanization (2026-11-01; operator approved CAF-1..7 with the D9 acknowledgement)

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

#### Open at 2026-11-01 wrap-up (ws58)

- [x] **Land the MIN_RESUME_GAP_S fix** ✅ 2026-11-02 superseded by dispatcher rewrite ROOT `9612fb48d` [no-belief: tooling]
- [x] **Inventory-target dispatcher change** ✅ 2026-11-02 replaced by operator-loop dispatcher (next = non-inference/inference/blocked/done; yield/cooldown/stuck/park/inventory gates deleted) ROOT `9612fb48d` [no-belief: tooling]
- [ ] **CAF burn measurement**: tokens per completed task before/after CAF-1..7 via `churn/tokens_per_task.py`.
- **[declined: ws58 2026-11-03 content-review: self-referential guardrail with no behaviour change]** **Net line count must go down**: `handoff_sessions.py`, `backlog_gen.py`, `rowflow/`, `churn/` grew this day; find deletions (guardrail unmet).
- [x] **Hotfixes landed** ✅ 2026-11-01 ROOT `139d9cf7a` `ddf791068` `0fec383f5` `a57b57239` [no-belief: tooling-repair; no measurement]
- [x] **Keeper v11 single allocator** ✅ 2026-11-01 ROOT `1a9186e11` [no-belief: build/landing]
- [x] **churn_up.sh persistence runbook** ✅ 2026-11-01 ROOT `d095b4a4d` [no-belief: build/landing]

#### Typed decisions and Super-agent patterns from intake-2604/2615 (ws58 intake 2026-11-02; operator approved "Approve, go to Stage 4", D9 acknowledged for scripts/coordination)

Plan: [README.md](../../research/deep-dives/ws58-jev-20261102/README.md). **Order (operator, 2026-11-02):** (1) SA-1 + JEV-1; (2) SA-2, SA-3, JEV-3; (3) JEV-5 phase A, KT-1, KT-3; (4) the rest (JEV-2, JEV-4, JEV-6, SA-4, KT-2, KT-4, KT-5). JEV-5 phases B/C only after the operator has used phase A.

- **[superseded: 2026-11-09 screen: the cooldown/starts-per-hour code of e13875235 is gone from `handoff_sessions.py`; the dispatcher was rewritten to the operator loop in 9612fb48d, which owns start throttling (only the disk-floor AUTO-START-THROTTLED remains)]** **SA-1** [S] Merged into the in-progress sticky-slot change (`54c23474e`, `sticky()`/auto-start gate in `handoff_sessions.py`): auto-start admits only a handoff with a ready row or an operator pin, adds a per-slug start cooldown and a global starts/hour cap, logs `AUTO-START-THROTTLED`; fixtures for rows=[] and just-done. Evidence: 61/63 AUTO-STARTs with `rows=-` on 2026-11-01/02 (intake-2615#record). removes: fresh-session bootstrap per freed slot, the done-then-restart loop, `restarted_from_done` re-admission without a ready row. [no-belief: superseded]
- [x] **SA-2** [S] Zero-token watchdog inside the existing keeper pass (no new daemon): count AUTO-START/DONE per hour against ready rows unclaimed and alarm on starts over cap with no effect. removes: operator log-grepping to spot thrash. ✅ 2026-11-09 (verified: `428439572`, `AUTO-START-NO-EFFECT` watchdog at `handoff_sessions.py:1160`, test in `test_handoff_sessions_autostart.py`) [no-belief: tooling-repair]
- [x] **SA-3** [S] Run-end and awaited events carry related ids (row, run, handoff) into the resume `delta()`, so a resumed worker gets a chain-of-recall delta (intake-2615#record). removes: the worker's cold re-read of handoff and row files on each resume. ✅ 2026-11-09 (verified: `428439572`, `related_ids()` at `handoff_sessions.py:458`, test `test_related_ids_in_run_end_and_no_effect_watchdog`) [no-belief: tooling-repair]
- [ ] **JEV-3** [M] REPLACE the regex failure classifier (`rowflow/publish_row.py:82-104`, `UNKNOWN-FAILURE-CLASS`) and `handoff_sessions.work_state` regexes with the local native `src/typed_decisions/` path (TD-29: 18/18) returning a named label plus named park/stop reasons; replay of saved `dryrun/*/FAIL-*.json` is a regression check only, no new accuracy study (intake-2604#record). removes: `_UNIT_RE`/`ADV_RX`/`OWN_TASK_RX` regex classification, the UNKNOWN-FAILURE-CLASS fall-through, unnamed MAX_FAILS parking. Status 2026-11-02 (absorbs the deferral note): replacement commit 7b2b40b42 is kept but uncalled; the 1.5B native replay was unusable (constant answers, confidence 1.0) — re-run the replay with the served worker model before wiring the call.
- [x] **SA-4** ✅ 2026-11-02 ROOT `1579bd509` [no-belief: doc rule; no measurement] [S] `docs/guides/agent-workflows/agent-loop-design.md`: a long-lived worker per task with code pass-through of its thread's events; fresh start only on a ready row; a watch for unproductive loops (intake-2615#record). removes: per-event fresh-session dispatch as an accepted loop shape.
- [x] **JEV-6** ✅ 2026-11-02 ROOT `1579bd509` [no-belief: doc rule; no measurement] [S] `docs/guides/agent-workflows/agent-loop-design.md`: typed judgments carry label probabilities and a confidence with two thresholds set from held-out real outcomes; unavailable is never an answer; a worker claim is never a result (intake-2604#record, intake-2605#record, intake-2608#record). removes: free-text agent decisions as an accepted loop shape.

#### 2026-11-02 wrap-up (ws58)

- [x] **Owner carries row through dry run** ✅ 2026-11-02 ROOT `549eb58` (supersedes `1f054f2c4`) [no-belief: tooling]
- [x] **Sparse lanes keep artifacts/operator/*.sh** ✅ ROOT `ac7e2e1fc` [no-belief: tooling]
- [x] **wrapup.py resolves generated-index conflicts; report.json on every exit** ✅ ROOT `c9eb9e2b8` `005a7fbf5` [no-belief: tooling]
- [x] **Hub pipeline section / backlog graph** ✅ ROOT `28b23bf37` `1c869a310` `60ec225af` `100cb18ba` `8fe3693e9` `4693451cb` [no-belief: dashboard]
- **[declined: ws58 2026-11-03 content-review: merged into JEV-3 as its status]** **JEV-3 deferred**: replace commit `7b2b40b42` kept, uncalled; 1.5B native replay unusable (constant answers, confidence 1.0), `/mnt/raid0/llm/tmp/ws58-csh/jev3-replay-1p5b-20261102.json`.
- [ ] **Measure row publication** after the 10:41Z fixes.
- [ ] **Sessions over-prepare instead of publishing**: measure per session over 48 h the rows PUBLISHED vs preparation artifacts written (packets, PREDECLARATION.md, dry-runs); any preparation step that produced no published row in 7 days is cut from the dispatcher's path. Done when the ratio is reported and at least one step is removed or justified.
- [x] **Dashboard readied-waiting count is 0**: row/handoff linking bug. ✅ 2026-11-10 ROOT `6c0e65792` (normalise row handoff keys); live /api/pipeline shows non-zero ready/running counts and the readied-waiting class. [no-belief: dashboard]
- [ ] **RTG-18 graph checkbox-parse bug**: graph shows open=0, file has 12 open boxes.
- [x] **Turn-end rules, light worker persist, central index_regen.py; box id per turn, steps-since-tick, push lock 15 min** ✅ 2026-11-02 ROOT `30b2ed75c` `262de5c98` [no-belief: tooling]
- [x] **Dry runs take no lock; publish smoke never refuses for busy; smoke disk floor 20 GiB; GPU smokes queue between GPU jobs; tiny rows unscheduled, port exclusivity, drain T + backfill; dry-run harness reaps process group** ✅ 2026-11-02 ROOT `d4f22dccd` `fc4e4352f` `6e0f27d5c` `59c2beb79` `70e5666b1` `d9838cf37` [no-belief: tooling]
- [x] **Dispatcher scratch quota (SCRATCH-OVER)** ✅ 2026-11-02 ROOT `5b34a2409` [no-belief: tooling]
- [x] **Dashboard row badges, legend/info panel, open-count parser fixes, engram boxes** ✅ 2026-11-02 ROOT `23791d952` `6f1f97b43` `da51eb293` `2c360a3ee` [no-belief: dashboard]
- [ ] **Sub-quarter packing**: packing agent was stopped; unfixed.
- [ ] **Rows published with a non-inference payload as compute rows** (e.g. gitnexus analyze held all 96 cores).
- [ ] **Row estimate_s vastly overstated**: fix estimator. Progress 2026-11-10: `eeb1a40b3` books by one booking duration (`book_s`), which bounds the overbooking, but the estimator itself is not fixed; box stays open.
- [x] **Per-row UNDERUSED is only logged**: act on it. ✅ 2026-11-10 ROOT `411dcae47` (IDLE-HELD escalates, and reclaims when opted in). [no-belief: tooling]
- [moved: handoffs/active/coordination-and-churn-pipeline.md] **OBS-CHURN-UP** — kept in the old file because `scripts/coordination/observer_registry.json` (loop plane, D9 operator ack) names that file as owning_handoff for marker OBS-CHURN-UP and the observer-contract commit hook requires an open box there. Move it here when the operator acks repointing the registry row. Full text is the box in the old file.
- [ ] **CHURN-UP-NO-DISPATCHER** `churn_up.sh` must not start the handoff dispatcher implicitly. 2026-11-04 it started pid 3977332, which resumed 11 Codex handoff sessions the operator had not asked for (stopped at operator order; sessions left running). Done when `churn_up.sh` starts the dispatcher only on an explicit flag and a `--dry-run` test proves the default path leaves it down. [no-belief: tooling]
- [x] **PIPE-EVE-JANITOR-QUIET** Janitor skips scheduled reaps during a live quiet-host grant unless free disk < 150 GiB. ✅ 2026-11-09 ROOT `9d597d559`, running copy sha equals git; the skip has not yet fired on a real grant. [no-belief: build/landing]
- [x] **PIPE-EVE-FILING-SUPERSEDE** Filing auto-supersedes only attempts that did not complete. ✅ 2026-11-09 ROOT `54a53fabc`, installed sha equals git. [no-belief: build/landing]
- [x] **PIPE-EVE-RESIDENCY-FALSE-FAIL** Since keeper c303970ee went live (20:27Z), six GPU smokes failed with `max None B` while c10-fold-gate's job logged 1369 MiB. Prove or refute the own-tree sampler as cause, then fix or roll back; the affected rows then need republishing by their owners. Needs operator D9-ack. ✅ 2026-11-10 ROOT `ca625eed8` `701852108` `4123a0852` `5b02d1861` + engine cgroup leaf `9e25eda4d` (live via deploy_rowflow, bin/rowflow/DEPLOYED.json); c10-fold-gate FOLD_PASS and W2 passed+completed after republish. [no-belief: tooling-repair]
- [x] **PIPE-EVE-KEEPER-LAND** Decide whether `keeper-frozen-20261109` (c303970ee) lands on main, after PIPE-EVE-RESIDENCY-FALSE-FAIL. Live keeper differs from main until then, so a main-based deploy reverts it. Conflicts: `.index-graph.json` (generated), one LOOP-11 line. Operator decides. ✅ 2026-11-10 keeper branch landed as `39fccee65`..`ca625eed8` (8 commits) then `b1fb6d43c` (index regen). [no-belief: tooling-repair]
- [x] **PIPE-EVE-SIGN-FLOOR** Operator signs `run_ak_q38fn_floor_accept_20261109.sh --apply` in a real terminal. ✅ 2026-11-10 SUPERSEDED: registered C9 floors; AutoKernel supplies a C10 accept instead (operator). [no-belief: operator-action]
- [x] **PIPE-EVE-SIGN-RATIFY2** Operator signs `run_ak_c9_ratify2_20261109.sh --apply` in a real terminal. ✅ 2026-11-10 `scripts/operator/run_ak_c9_ratify2_20261109.sh` review run: "ALREADY RATIFIED: all items are on origin/main". [no-belief: operator-action]
- [x] **PIPE-EVE-BIN-CHURN-MODULES** Operator installs `row_worktree`, `worktree_gate`, `worktree_salvage` into `bin/churn` (absent at 21:14Z); until then `reclaim_row.py` cannot import from the installed copy. Then a D9-acked `churn_up.sh` install-list fix so the modules stay installed. ✅ 2026-11-10 compute-flags `bin/churn/{row_worktree,worktree_gate,worktree_salvage}.py` byte-equal to source; `scripts/coordination/INSTALL.manifest` L37-39 + `deploy_rowflow.sh --parity` (`a452b5ec4`). [no-belief: tooling-repair]
- [ ] **PIPE-EVE-CHURN-UP-RUN** Run `churn_up.sh` with clearance so the watchdog guard and core.bare watcher start. [no-belief: tooling-repair]
- [ ] **PIPE-EVE-CHURN-UP-PIDFILE** `start_bg` recorded the wrapper pid in the janitor pidfile on 2026-11-09 (corrected by hand); fix `churn_up.sh`, D9-ack needed. [no-belief: tooling-repair]
- [x] **PIPE-EVE-UNFILED** File the ended-unfiled rows (117 at 21:14Z). ✅ 2026-11-10 362 `*.FILED` markers dated 11-10 in `compute-flags/filing-done/`. [no-belief: tooling-repair]
- [x] **PIPE-EVE-INF22-DIGESTS** Regenerate the 8 dirty digests of `worktrees/inf22-intake` against main in a fresh worktree and compare; ids 2662-2663 may be new. ✅ 2026-11-10 REASSIGNED to AutoKernel by the operator; closed here. [no-belief: tooling-repair]
- [ ] **PIPE-EVE-LONGCTX-WT** Operator runs the cleanup commands given for `worktrees/longctx-c9-20261109` (patches in `tmp/worktree-cleanup-20261109/`). [no-belief: operator-action]
  - 2026-11-10: HEAD c8c409d68 is landed; only 2 generated index files are dirty (timestamp-only, patch saved at tmp/worktree-cleanup-20261109/longctx-dirty.patch). Operator OK needed for git restore + plain worktree remove.
- [ ] **PIPE-EVE-RAM-MARGIN** Raise RAM margin from 64 to 100 GiB with `ram_gib` injection. [no-belief: tooling-repair]
- [ ] **PIPE-EVE-VALIDATOR-REFS** Resolve the dangling validator cross-references (85 at the last count). [no-belief: tooling-repair]
- [x] **PIPE-EVE-VIDYA-GROUP-A** Land the Group A vidya adapters from worktree `vb-belief-park-20261108`. ✅ 2026-11-10 landed 9047ad47f on origin/main (cj7a-inverse-mutation, dar-join-coverage, odl-unlimited-ocr-intrinsic adapters + registry + README rows; chat-template intrinsic fix); touched tests 161 passed, the 2 failures are the pre-existing numpy/ufh12 ones identical on clean main; adapters use shared claim_tuple.grade() only [no-belief: tooling-repair]
- [ ] **PIPE-EVE-C6-WIRE-WT** Remove `worktrees/c6-wire-20261109` once its untracked `.tmp-c6-tests/` is cleared; bf94b0965 is landed, the gate says DIRTY. [no-belief: tooling-repair]

#### Stop-everything, disk reclaim and runbook (2026-11-02 afternoon, ws58)

- [x] **Backlog-churn runbook; keeper v12 in git; `churn_up.sh` `--stop` `--status` `--dry-run`** ✅ 2026-11-02 ROOT `27b94990f` [no-belief: tooling]
- [x] **Disk fixes: reaper idle 1 day; standalone `disk_janitor.sh` (reap 30 min, trash sweep hourly); SCRATCH-COPY detection in dispatcher; scratch cleanup on retire** ✅ 2026-11-02 ROOT `c1068744f` [no-belief: tooling]
- [ ] **Verify the disk janitor** (started 14:05Z pid 190444): FREE trend >= 1 day, `.trash` nothing older than about 25 h, no SCRATCH-COPY outstanding.
- [ ] **3 half-cleaned worktrees**: `vgpr-compiler-ab-20260915`, `fix-pii-hook-numeric-json-20261021`, `noninf-20260924/inf41/epyc-orchestrator`.
  - 2026-11-10 pipeline-mgmt: fix-pii-hook-* and noninf-20260924/inf41 worktrees already gone (salvage in archive/worktree-salvage/). Remaining: vgpr-compiler-ab-20260915 (untracked dive/ = public upstream clones) and noninf-20260924/ scratch files; operator OK needed.
- [ ] **Dirty/unlanded trees under `tmp/` and `autokernel/` never processed** by the reclaim.
  - 2026-11-10 pipeline-mgmt: classified 871 trees under tmp/ and autokernel/; removed 19 landed worktrees (plain git worktree remove) and trashed 194 clean landed clones via guarded_rm (about 59 GiB; trash sweep pending). Still listed, untouched: about 480 trees with unlanded commits, about 90 with unique dirty files, 25 worktrees pointing at missing repos.
- [x] **Dangling references to deleted data**: `artifacts/compute/codex3-*` cite `data/stt-cs8-public-20261030`; `memento-block-reasoning-compression.md` cites openmementos; about 10 files cite `backups/episodic-leak-20260917` (`ratify_v10_episodic_repin_20260917*`, `promptforge-mutation-safety-contract.md`, `wiki/safety.md`, orchestrator `purge_eval_leak_memories_20260917.*`). ✅ 2026-11-10 ROOT afba1bd24 — docs fixed (wiki/safety.md, autopilot-program.md, context-and-token-economy.md); signed artifacts and the task_lint RETIRED list left on purpose; data/stt-cs8-public-20261030 re-materialized 2026-11-05 as a 1.3 GB subset, not dangling. [no-belief: tooling-repair]
- [x] **rowflow test `test_complete_in_smoke_is_filed_not_queued` fails on main.** ✅ 2026-11-09 (verified by running `pytest scripts/coordination/tests/test_rowflow_tiny_and_ports.py -k test_complete_in_smoke_is_filed_not_queued`: 1 passed on origin/main 4c8fa6212; the reported failure no longer reproduces) [no-belief: tooling-repair]
- **[declined: ws58 2026-11-03 content-review: a state note, not a task; the restart is the operator's call and is recorded in the runbook]** **Pipeline restart is operator-gated** (all grants revoked to `tmp/ws58-csh/revoked-grants-20261102/`; dispatcher, keepers, watchdogs, filler_run13 launchers stopped).
- [x] **Registry graveyard row for Qwen2.5-Coder-32B-Instruct-Q4_K_M** (operator deleted the file): commit was blocked by the orchestrator pre-commit contention-matrix freshness hook (matrix stale, cannot refresh with the stack stopped). Patch at `tmp/ws58-csh/registry-graveyard-q4km-20261102.patch`. Also `server_mode.qwen25_coder_32b_q4km` still resolves to the deleted file; needs a stack-change deprecation. ✅ 2026-11-10 (stale: graveyard row, deprecated server_mode and roles already on research origin/main at 568aa7d9c, 2026-11-02; weights confirmed deleted by operator 2026-11-10) [no-belief: tooling-repair]
- **[declined: ws58 2026-11-03 content-review: done — the backlog refactor 2026-11 completed (1127924c8) and its proposal was consumed]** **Fable backlog-refactor audit** in progress; output `tmp/ws58-csh/backlog-refactor-proposal-20261102.md`.

- [x] **CHURN-WARM-1 — One grant, N measurement units: a warm worker that deletes the second full launch per row.** Today a measurement row pays publish, then a smoke (the queued dry run since the 2026-11-05 smokes rule) that is itself a full launch and model load, then grant, startup and one measurement. Hold one grant, load the model/server once, and execute N queued measurement units inside it; keep `restart_role()` as the rollback path, bind cache/state exactly as the recipe already does with `cache_state: warm|cold`, and record `published_at -> first_result_unit` plus per-unit wall on every row. Deletion: the per-row dry-run launch and the per-row model load. Phase A is a zero-GPU replay over 20 closed rows estimating saved seconds; phase B is one live warm window. Stop if median saved per unit <10% or any unit's measurement context differs from its cold twin. Implementation target is rowflow2 (ROWFLOW2-SHADOW, engineering-hygiene-backlog.md); `rowflow.py` is frozen, so phase B waits for the rowflow2 cut-over and phase A does not. (intake-2643#record) [belief: cc]
  - 2026-11-06 PHASE A RESULT (operator-adhoc-ops-20261105; `scripts/coordination/churn_warm/phase_a_replay.py`, `artifacts/churn-warm-1-phase-a-20261106.json`): 20 most recent closed rc=0 rows, saved = the smoke launch wall (lower bound; real-run model load not counted): median 48 s/row, 1,266 s total, median **6.7%** of row wall, below the 10% stop threshold. The stop rule fires on the lower bound: phase B is not justified unless a model-load-inclusive estimate clears 10%. Phase B waits for rowflow2 either way.
  - 2026-11-06 VERDICT (operator-adhoc-ops-20261105): **warm reuse saves <10%** (phase A stop rule fired: median 6.7% < 10%; stop-on-answer per measurement-sufficiency). Phase A ticked [belief: cc]. The line's own rule is `Stop if median saved per unit <10%`, so it does not say phase B proceeds regardless; followed as written.

- **CHURN-WARM-1 phase B** (one live warm window; not a checkbox, the parent box above is phase A's closure) [declined: operator-adhoc-ops-20261105 2026-11-06 stop-rule fired in phase A (6.7% < 10%); revisit only if rowflow2 grant overhead changes]

#### Containment learnings from the Fractal design (2026-11-07, operator: "learnings for the general churn pipeline — you should own those")

Source: `docs/design/fractal-disposable-host-trial.md` (EVL-29 ID-14 declined; the AK-loop half is in [autokernel-loop.md](autokernel-loop.md) AK-CONT-*). Gap audit 2026-11-07 against current code; each box names what already exists so it is not rebuilt.

- [x] **CHURN-CONT-RESERVE** — token/time cleanup reserve. Exists: disk-only reserve (`rowflow/diskpause.py` 150/180/50 GiB); `token_guards.py` caps rate, not remaining budget. Build: a `reserve` tranche in `token_guards` DEFAULTS that stops new admissions once remaining weekly budget hits it; janitor/filing/teardown spend charged outside row accounting. Done when a test shows admission refused at reserve and filing still admitted. ✅ 2026-11-07 [no-belief: build/landing]
  - 2026-11-07 LANDED (24c923aaf, same D9-ack): `token_guards` reserve tranche (5 % of the weekly budget) plus `admit()` wired into `handoff_sessions` dispatch; run-end filing resumes stay admitted, a missing meter fails closed for work. Meter dry-run on landing: codex weekly_fraction 1.0 and claude 1.33 against 5.5B, so a dispatcher restart will log `ADMIT-REFUSED` until usage falls below 95 %. Not a defect: the restart is operator-gated and the refusal is the reserve working.
- [x] **CHURN-CONT-SURVIVORS** — **declined 2026-11-07 (operator: "if it isn't essential, do without it")**: already enforced. `filler_run15.sh` `kill_job` re-scans the setsid group, every descendant and env-tagged orphans (FILLER_ID + FILLER_STOPFILE, which catches re-setsid escapes) after the KILL; if anything survives the reason becomes `cleanup-failed`, the grant is retained and no .ended is written, so a `survivors=` line adds nothing. Original text: prove the kill. Exists: setsid group TERM→KILL after `--stop-grace` (`rowflow/filler_run15.sh:43-44,118`), killpg in `dryrun_check.py:398`, `churn_up.sh:291-293`. Gap: nothing verifies the group is gone, and a job that re-setsids escapes. Build: after the grace KILL, scan /proc for the pgid/session (or run the job in a cgroup scope and use `cgroup.kill`) and write `survivors=<n>` into the row's ended record; n>0 alarms. Keeper-side, so it ships via an approved `deploy_rowflow.sh --emergency`. [no-belief: decline]
- [x] **CHURN-CONT-SCOPE** — scoped filing/commit paths. Exists: runtime write allowlist only (`job_templates/job_fence.py` Landlock + MAX_FILE_MIB). Gap: `churn/file_result.py` does not check a filing's changed paths. Build: reject a filing whose `git diff --name-only` (symlinks resolved, no traversal/gitlinks) leaves the row's declared scope; rows without a scope get a default of their output dir + their handoff. ✅ 2026-11-07 [no-belief: build/landing]
  - 2026-11-07 LANDED (b7e5edb12, D9-ack operator 2026-11-07 "Land both; SCOPE warns by default"): `churn/filing.py` checks a filing's changed paths against the row scope; enforced when the row declares a scope, otherwise a warning line goes to `filing-scope-warn.jsonl`. Tests in `tests/test_churn_filing.py`.
- [x] **CHURN-CONT-COSTBASIS** — **declined 2026-11-07 (operator: "if it isn't essential, do without it")**: telemetry with no consumer; tokens, disk and the wall-clock 1.5x rule already gate the pipeline, and a prototype read of the launcher rusage returned 0 CPU-s (would need cgroup plumbing). Reopen only if a scheduling decision needs CPU or GPU-seconds. Original text: CPU/GPU-seconds as a metered cost. Exists: tokens (`codex_budget_meter.py`), disk (`row_disk_budget.py`), wall-clock estimate (1.5x rule in the inference-backlog-scheduling skill), CPU confinement (job_fence `repin_threads`, taskset grant). Gap: CPU- and GPU-seconds are confined, never measured or capped. Build: record per-row CPU-s (cgroup `cpu.stat` or /proc rusage of the group) and GPU-s (sampled KFD residency) next to tokens and disk in the ended record; surface in `queue_status.py`. Cap later, once a week of data sets the ceiling. [no-belief: decline]
- [x] **CHURN-CONT-TREE** — budget aggregation up a node tree: **declined 2026-11-07** — churn rows and sessions are siblings under one dispatcher, so the only root is the fleet, which `token_guards.width_cap()` + `codex_budget_meter.py` already meter; an unmetered seat failing closed is covered by CHURN-CONT-COSTBASIS. [no-belief: decline]

- **Standing note: AutoKernel loop custody (agreed 2026-11-07).** Diffs to `loop/{run,loop,pipeline,actors}.py` in the research repo go to the AutoKernel session for review and re-pin BEFORE any push; Pipeline Management does not push them directly. (AutoKernel re-pinned `run.py` at research `e37852556` on 2026-11-07.)
