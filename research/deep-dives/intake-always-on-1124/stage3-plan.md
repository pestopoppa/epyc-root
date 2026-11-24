<!-- Line citations are pinned at a290df6 unless marked; origin/main 20a74f6 (rowflow reservation own_start) shifted the RESERVATION block by +84 lines and leaves RESERVATION_MODE = "shadow" and no owner box. -->
# Stage-3 plan: always-on agent primitives against our loops and pipelines (intake-always-on-1124), REVISION 1, APPROVED 2026-11-24 with amendments

## Revision 1 (operator approval relayed by the coordinator, 2026-11-24)

Approved with these amendments, applied in this revision:

1. **P1 replaced.** PM-RESERVE-SOAK and PM-RESERVE-ENFORCE become ONE box, PM-REPLAN-C-SOAK. It soaks re-planning scheduler C (`REPLAN_MODE=shadow`) and enforces C when the six criteria of `docs/design/rowflow-replanning-scheduler.md` hold. Reservation B stays `RESERVATION_MODE=shadow` by operator ruling.
2. **OP-RESERVE-ENFORCE index row dropped.** No index rows are filed.
3. **PM-RESERVE-RETIRE-PATCHES** is gated on PM-REPLAN-C-SOAK. Its rule list now names the rules C subsumes (design doc section 11), keeping whatever B's fallback admission path still calls. The drafted list named B's enforce-bypassed rules, which no longer get enforced; this is the integrator's adaptation of the text.
4. **P2, P3 and P4 are filed as drafted.** P4 is filed in `autokernel-loop.md` for AutoKernel to accept.
6. **Citation narrowed at filing (integrator).** intake-2947 carries one overturned claim (index 4), so the cite gate refuses entry-level citations of it. PM-CODEX-LANE-VERDICT now cites intake-2947#02 (deny-and-continue) and the PM-RULES-WARN-FIRST note cites intake-2947#00 (false-positive rate).
5. **Brief fix at filing (integrator).** The briefs for PM-CODEX-LANE-VERDICT and PM-RESERVE-RETIRE-PATCHES got explicit runnable acceptance commands, because the default (the done-when sentence) does not compile as a pytest command. PM-CODEX-LANE-VERDICT declares its new test file, and both drop non-repo paths from `--where`. Box text and done-when are unchanged.

Integrator note: `REPLAN_MODE` is not yet in `rowflow.py` on origin/main (8d29489). Steps 1-3 of the design doc's build plan (port `replan()`, shadow lines, nightly replay gate) have no owner box other than PM-REPLAN-C-SOAK itself. This is flagged in the Stage-4 report, not added here.

## Run summary

- **Source:** "Building always-on agents" (William Hu, Anthropic, 2026-11-13), https://claude.com/resources/articles/building-always-on-agents, intake-2942.
- **Stage 1:** intake-2942 plus 10 literature expansions (cap 10). Seven came from links in the article: intake-2943 verification, intake-2944 eval hill-climbing, intake-2945 chaos loop, intake-2946 agent memory, intake-2947 auto mode, intake-2948 hooks reference, intake-2949 agent automations. Three came from the Tier-2b contradiction search: intake-2950 RAZ critique, intake-2951 webhook inboxes, intake-2952 Dudycz outbox/inbox. All 11 are relevance medium or high, so all were recommended. Refused at the cap (fetched and retained, not ingested): the agent-identity article, the enterprise coding-agent security guide and the compaction docs.
- **Stage 2 wave 1:** all 11 entries dived (4 sonnet dives, groups A-D).
- **Stage 2 wave 2 (Stage-2b):** 3 dive-surfaced sources ingested and dived: intake-2953 AgentTime (arXiv 2610.09944v2), intake-2954 TicToc (arXiv 2510.23853v3), intake-2955 Code Review post (2 sonnet dives, groups E-F).
- **Second reader (haiku):** 78 of 78 quotes re-found. Supports its claim: 66 yes, 11 partial, 1 no. The "no" was an absence claim (intake-2947 claim 4, no staged rollout described). Its anchor was dropped, because a quote cannot support an absence.
- **Subagents:** 6 sonnet (medium), 1 haiku (low). Fetching, anchoring, integration and main review were done by the integrator (Opus).
- **Main-review corrections to dive output:**
  1. Dive A read light-claim expiry as advisory. It is not: `reap_build_grants` ends every build or light grant past its `end=` on the keeper tick (rowflow.py L6771-L6787 @ a290df6). So AON-A3 is declined.
  2. intake-2943 claims a tuning/test split and per-stage recall for the Code Review eval. The post it links (intake-2955, href checked) contains neither. That claim is recorded as reattributed.

## Per-source verdicts

| Intake | Source | Verdict | Read | Claims C/P/O/NF | One-line finding |
|---|---|---|---|---|---|
| intake-2942 | Building always-on agents | adopt_patterns | FULL | 9/4/0/0 | Sound design guide. One worker per inbox has no lease, dedup stops at the inbox, and the 78% Opus cost figure is a vendor self-report |
| intake-2943 | Claude Code team on verification | adopt_patterns | FULL | 7/1/0/0 (1 reattributed) | Observe mode before enforce; checks the change cannot edit; verification stamp per commit |
| intake-2944 | Eval design and hill-climbing | adopt_patterns | FULL | 4/1/0/0 | The 98.9% headline is on the search set; held out it is 78.6% to 90.5% (n=14) |
| intake-2945 | Chaos loop, Claude Docs | worth_investigating | FULL | 3/2/0/0 | 60 errors across 2 billion launch-week requests, no control |
| intake-2946 | Components of agent memory | adopt_patterns | FULL | 6/1/0/0 | Small injected index; writing progress in the moment distracts the worker; one writer per page |
| intake-2947 | Claude Code auto mode | worth_investigating | FULL | 3/1/0/1 | 0.4% false positives but 17% false negatives (n=52); deny-and-continue capped at 3 consecutive or 20 total |
| intake-2948 | Hooks reference (defer, asyncRewake) | adopt_patterns | PARTIAL | 2/1/0/0 | Defer plus `claude -p --resume`, no timeout, 30-day retention |
| intake-2949 | Building agent automations | adopt_patterns | FULL | 4/0/0/0 | Record a step as done only after external confirmation |
| intake-2950 | RAZ critique | worth_investigating | FULL | 1/4/0/0 | No linked source for any number; the timer-per-parked-question idea stands |
| intake-2951 | Webhook inboxes | adopt_patterns | FULL | 4/0/0/0 | Lease-style claims; we already have the expiry half |
| intake-2952 | Outbox/inbox delivery (Dudycz) | already_integrated | FULL | 3/0/0/0 | Independent corroboration; the session bus already works this way |
| intake-2953 | AgentTime (arXiv 2610.09944v2) | worth_investigating | PARTIAL | 5/2/0/0 | Fable 5.1 returns early on 55% of runs; the controller never resumes; Astra is on time 63% |
| intake-2954 | TicToc (arXiv 2510.23853v3) | worth_investigating | PARTIAL | 2/1/0/0 | Refresh-decision blindness; no EPYC consumer |
| intake-2955 | Code Review post | adopt_patterns | FULL | 3/3/0/0 | Answer key built from incidents plus a clean control; no held-out split |

C/P/O/NF = CONFIRMED / PARTIAL / OVERTURNED / NOT-FOUND-IN-SOURCE.

## Live lessons tested against the sources

| Lesson | Source stance | Evidence (verified passages) | Our current state (pinned) | Plan |
|---|---|---|---|---|
| L1 one-shot workers ending early with no resume | **Agrees and adds.** Every run end is a typed state that a later event resumes (deferred call, progress file); a refusal is a retry signal with a counter; a timer per parked item | intake-2942 Permissions and Memory; intake-2947 deny-and-continue (3 consecutive, 20 total); intake-2950; intake-2953 (Fable returns early on 55% of runs when nothing resumes it) | rowflow already resumes rows (`resume <id>`); the AutoKernel loop resumes from its store (`--resume on`); the autopilot resumes each cycle from durable state. Gaps: taskflow `dispatch.py` has no resume path; the Codex drivers resume on a fixed message with an 8-round cap and no no-progress rule | P2 (no-progress STALLED rule), P3 (count first, then build or decline) |
| L2 claims bypassing the scheduler queue | **Agrees.** Sources never call the agent; everything goes through one inbox with one worker | intake-2942 Event inbox; intake-2952 (independent, 2020) | rowflow.py (L8419 @ a290df6, L8502 @ 20a74f6) records root cause E: light and build claims never ask the planner. Reservation B (`claim_reservation_check`) runs in shadow and stays there; scheduler C is designed but not yet soaked | P1 (PM-REPLAN-C-SOAK) |
| L3 patch-rule accretion versus a single reservation | **Agrees as a pattern; adds pruning.** One source of truth instead of per-source patches; prune rules on a routine and set a promotion bar for new ones | intake-2942; intake-2943 rule pruning | rowflow.py L8424-L8427: enforce mode bypasses five patch rules but does not delete them | P1 (PM-RESERVE-RETIRE-PATCHES) |
| L4 warn-first rollout of new rules | **Agrees directly** (intake-2943 off/observe/enforce); intake-2947 only measures offline, with no staged rollout; intake-2942 is silent | intake-2943 "Observe mode will log what would have been blocked..." | PM-REPLAN-C-SOAK is shadow-then-enforce for the planner; PM-RULES-WARN-FIRST already owns the registry; `RESERVATION_MODE`, `SMOKE_MEASURE_ENFORCE` and commit-hygiene Rule G are existing ad-hoc instances | No new box. intake-2943's block-twice-then-allow valve is declined for keeper rules (AON-B2) |
| L5 deterministic acceptance from artifacts | **Agrees** (intake-2943 checks the change cannot edit and a per-commit stamp; intake-2949 confirmation before the ledger; intake-2955 an agent's approval never counts as a person's) and **adds verifier grading** (intake-2955 answer key from past incidents) | intake-2943, intake-2949, intake-2955 | taskflow `verify.py` already decides from artifacts. Gaps: the Codex drivers stop on the lane's own LANE-STATUS line; no verifier is graded against past failures | P2, P4 |

## Binding map (every operator-named target)

- **AutoKernel loop** (`autokernel-loop.md`, `autokernel-akx-program.md`, research `loop/`): P4 AK-KEEP-ANSWER-KEY. Knowledge-only:
  - The bench/serving split is already a train/test split.
  - The loop resumes from its store.
  - Actors are one-shot `claude -p` / `codex exec` proposal calls, so the defer pattern does not apply (AON-C1).
  - Stagnation escapes already exist in `actor_context.py` (AON-B3).
  - Nothing goes to `autokernel-akx-program.md`: no AKX box owns keep-gate grading.
- **Dispatcher and session bus** (`scripts/coordination/`, `coordination-and-churn-pipeline.md`): the bus is already an at-least-once inbox with id dedup and ack nudges (AON-A4, knowledge-only). The coordination handoff receives P1 and P2.
- **Taskflow worker harness** (`scripts/coordination/taskflow/`): P3 TF-EARLY-END-CENSUS in `churn-pipeline.md`, where the TF-R8G boxes live.
- **Rowflow keeper and scheduler** (`scripts/coordination/rowflow/`): P1.
- **Codex-lane driving** (PM-CODEX-DISPATCH-DETERMINISTIC, README-INTERIM.md): P2 PM-CODEX-LANE-VERDICT. PM-CODEX-DISPATCH-DETERMINISTIC is drafted only in the uncommitted worktree `/mnt/raid0/llm/worktrees/pm-codex-box` and is not on origin/main, so no box can bind to its line. P2 is the verdict function that box would port; it does not refine the box.
- **Orchestrator/autopilot** (`epyc-orchestrator`): knowledge-only (AON-D5). `scripts/autopilot/autopilot.py` @ a5b996bb already has three of the five primitives:
  - **memory:** state, journal and strategy store, plus a generated short-term view;
  - **outbox:** `autopilot_operator_outbox.jsonl`, deduped by action signature;
  - **resume-from-archive:** the planner prompt says the archive digest "replaces chat-session resume".

  Inbox and timers are done differently: polled control fields and a continuous loop. No change is proposed.

## Work packets

| Packet | Project decision | Boxes | Owner | Depends on |
|---|---|---|---|---|
| P1 | Should one planner (scheduler C over B's admission path) place every row, retiring the hand-coded reservation rules? | PM-REPLAN-C-SOAK, PM-RESERVE-RETIRE-PATCHES | `coordination-and-churn-pipeline.md` (pipeline-mgmt) | Chained: soak and enforce, then retire |
| P2 | Is a Codex lane DONE judged from artifacts, with a no-progress stop, before the driver is ported to the dispatcher? | PM-CODEX-LANE-VERDICT | `coordination-and-churn-pipeline.md` (pipeline-mgmt) | none |
| P3 | Does taskflow need a resumable end state for early-ending workers? | TF-EARLY-END-CENSUS | `churn-pipeline.md` (pipeline-mgmt) | none |
| P4 | Can keep-gate changes be scored against past failed keeps? | AK-KEEP-ANSWER-KEY | `autokernel-loop.md` (AutoKernel owns; pipeline-mgmt may prepare it as loop infrastructure) | none |

**Why four packets:** the ledger has four independent units: the reservation, the Codex verdict, the taskflow census and keep-gate grading. Everything else is knowledge-only or declined (see the mapping below).

**Concurrency:** PM-REPLAN-C-SOAK, P2, P3 and P4 can run in parallel. None of them needs compute or a rowflow claim, and they touch disjoint files. Within P1 the two boxes are strictly ordered.

### Minimum rigor

P3 and P4 are deterministic readings of retained records, and PM-REPLAN-C-SOAK reads shadow artifacts against criteria the operator predeclared:

- **Frozen input:** the named log or ledger window, recorded in the report.
- **Baseline:** the current rule (shadow planner, current dispatch, current keep gate).
- **Per-item raw output:** every log line or unit is classified individually.
- **Holdout:** P4 splits the set chronologically. For P1 and P3 a holdout does not apply (a census, not a fitted method). Their replacement check is that every item is classified, so the denominator is complete.
- **Complete denominator:** stated in each done-when.
- **Predeclared decision rule:**
  - P1: the six criteria of the design doc, held for 7 shadow days.
  - P3: build only if at least 2 units ended early and at least 1 was re-run by hand.
  - P4: futility below 10 failed keeps.

P1-retire and P2 are deterministic code. Their conformance checks are named unit tests: one replay test per starvation case A-E, and the three verdict cases (missing branch refused, BLOCKED with new commits resumed, three no-commit rounds STALLED).

**Measurement sufficiency:**

- PM-REPLAN-C-SOAK: question = does C beat greedy without violations? Checkpoint daily (nightly replay). Stop on answer: 7 consecutive passing days, then enforce. A failing day restarts the 7-day count.
- P4: question = what is the keep gate's false-keep rate? Stop on futility: fewer than 10 failed keeps.
- Neither reruns anything; both reuse records that already exist.

### Consumer discovery

Search terms: RESERVATION_MODE, reservation.json, RESERVED-FOR, light claim, LANE-STATUS, drive2, resume, needs-brief, answer key, false keep, LOO, revert. Surfaces searched: `handoffs/active/*.md`, `docs/guides/agent-workflows/compute-fillers.md`, `scripts/coordination/{rowflow,taskflow}`, research `loop/`.

| Primitive | Direct consumers | Evidence consumers | Policy consumers |
|---|---|---|---|
| Planner C over reservation B (P1) | `rowflow.py` claim paths, quiet gates, the keeper | `ws58-calendar-keeper.log`, `queue_status.py` | compute-fillers.md L245 already documents it; no separate consumer box |
| Lane verdict (P2) | the interim drivers; later PM-CODEX-DISPATCH-DETERMINISTIC (prospective) | the README-INTERIM exit log and its 5-DONE count | none |
| Keep answer key (P4) | none yet; any future keep-gate change is a prospective consumer | `accumulate.py` keep receipts | the AutoKernel promotion LOO gate (autokernel-loop.md L7145) stays separate |

## Proposed handoff edits (Stage 4 only, after approval)

Five new boxes, each written with `handoff_box.py add ... --brief --brief-author intake` and landing at the bottom of its track's `### Backlog`. No existing box is edited or refined. No new handoff, so no index row; `index_state.py` regenerates the thin rows.

#### PM-REPLAN-C-SOAK (P1) -> `handoffs/active/coordination-and-churn-pipeline.md`, track `coordination-and-churn-pipeline`

```text
- [ ] **PM-REPLAN-C-SOAK** [non-inference] Soak re-planning scheduler C (REPLAN_MODE=shadow) and enforce when docs/design/rowflow-replanning-scheduler.md criteria hold: 0 violations, solver p99 <1 s, weighted work ≥ greedy, urgent wait ≤0.7× greedy, ≤1 build-lane collision/day, no row past the 12 h pin (operator 2026-11-24; reservation B stays RESERVATION_MODE=shadow; intake-2942, intake-2952)
      · done when: a soak report shows 7 shadow days meeting all six criteria of docs/design/rowflow-replanning-scheduler.md section 11, and rowflow.py on origin/main has REPLAN_MODE = "enforce" with the live keeper start time after that deploy
      · gate: none
      · inputs: `docs/design/rowflow-replanning-scheduler.md`, `scripts/coordination/rowflow/rowflow.py`
```

Brief: where `epyc-root:docs/design/rowflow-replanning-scheduler.md`; `epyc-root:scripts/coordination/rowflow/rowflow.py`. Approach: Run C in shadow as section 11 of the design doc lays out: REPLAN-SHADOW lines and replan-plan.json each tick, no grant writes, plus the nightly replay gate on that day's trace. Read the six criteria per day from those artifacts, no compute beyond the nightly replay. Enforce only after 7 consecutive passing days, behind REPLAN_MODE=enforce with fallback to B (shadowed) or greedy on any solver exception or timeout. Reservation B stays RESERVATION_MODE=shadow. Acceptance: the done-when (accepted: auto).

#### PM-RESERVE-RETIRE-PATCHES (P1) -> `handoffs/active/coordination-and-churn-pipeline.md`, track `coordination-and-churn-pipeline`

```text
- [ ] **PM-RESERVE-RETIRE-PATCHES** [non-inference] Once PM-REPLAN-C-SOAK has enforced scheduler C, delete the hand-coded reservation rules C subsumes (docs/design/rowflow-replanning-scheduler.md section 11: RANK-HOLD, RANK-SKIP, QUIET-RESERVE, QUIET-URGENT-PENDING, BACKFILL-IF-FITS, and rank_reservation/DRAIN except what B's fallback path still calls) and keep one replay test per original starvation case A-E (listed in the RESERVATION comment block of rowflow.py), so one plan is the only path (intake-2942, intake-2943)
      · done when: none of the subsumed rules remains in rowflow.py on origin/main outside B's fallback path and pytest scripts/coordination/tests -k reservation passes with one named test per case A-E
      · gate: PM-REPLAN-C-SOAK
      · inputs: `scripts/coordination/rowflow/rowflow.py`, `docs/design/rowflow-replanning-scheduler.md`
```

Brief: where `epyc-root:scripts/coordination/rowflow/rowflow.py::RESERVATION_MODE`; `epyc-root:scripts/coordination/tests/test_rowflow_reservation.py`. Approach: Write the five A-E replay tests first against C in enforce mode and confirm they pass with the subsumed rules bypassed. Then delete each rule in its own commit (forward-port rule: one feature per commit) and rerun the tests after each deletion. Keep whatever B's fallback admission path calls; C falls back to it on solver failure. Acceptance: pytest scripts/coordination/tests/test_rowflow_reservation.py (accepted: owner).

#### PM-CODEX-LANE-VERDICT (P2) -> `handoffs/active/coordination-and-churn-pipeline.md`, track `coordination-and-churn-pipeline`

```text
- [ ] **PM-CODEX-LANE-VERDICT** [non-inference] Take the interim Codex lane driver's stop decision off the lane's self-written LANE-STATUS line (drive.sh and drive2.sh stop on its first line): commit the loop as scripts/coordination/codex_lane.py whose DONE is computed from artifacts (each reported box's branch and sha exist and pass the static checks; for pushed lanes, reachable from origin/main and box ticked), treat LANE-STATUS as a hint, stop as STALLED after 3 consecutive rounds with no new commit, and log rounds and wall seconds per lane (intake-2943, intake-2947#02, intake-2953)
      · done when: pytest scripts/coordination/tests -k codex_lane_verdict passes on origin/main and covers a DONE line with a missing branch (refused), a BLOCKED line with new commits (resumed) and three no-commit rounds (STALLED)
      · gate: none
      · inputs: `scripts/coordination/taskflow/verify.py`
```

Brief: where `epyc-root:scripts/coordination/taskflow/verify.py`; `epyc-root:scripts/handoffs/done_when.py`. Approach: Port drive2.sh's resume loop unchanged and replace status() with verdict(lane): parse the LANE-STATUS box lines as claims, then check each branch and sha with git and run the same static checks; pushed lanes reuse done_when.py. DONE only when every claim checks out; a BLOCKED line with new commits since the last round is resumed once; three rounds with no new commit end STALLED. Append round, wall_s and verdict per lane to a JSONL ledger. The 5-consecutive-DONE exit criterion in README-INTERIM.md is then counted from this verdict. PM-CODEX-DISPATCH-DETERMINISTIC later ports this function into the dispatcher. Acceptance: pytest scripts/coordination/tests/test_codex_lane_verdict.py (new test file; accepted: owner).

#### TF-EARLY-END-CENSUS (P3) -> `handoffs/active/churn-pipeline.md`, `### Backlog` at L212 (the file has no `## Track:` header)

```text
- [ ] **TF-EARLY-END-CENSUS** [non-inference] Count the taskflow units in canaries r8a-r8g whose worker ended before its wall cap with an empty or partial diff and no verified verdict, and how many were re-run by hand, then apply the brief's build-or-decline rule to a typed resumable end state in dispatch.py that select.py re-admits (intake-2942 deferred-call resume, intake-2950 timer per parked unit, intake-2946 progress written by the harness rather than the worker)
      · done when: a census table (unit, end reason, diff lines, re-dispatched yes or no) for every r8a-r8g unit and a one-line build-or-decline decision are appended to docs/design/taskflow-stage1-canary-findings.md on origin/main
      · gate: none
      · inputs: `scripts/coordination/taskflow/dispatch.py`, `docs/design/taskflow-stage1-canary-findings.md`
```

Brief: where `epyc-root:scripts/coordination/taskflow/dispatch.py`; `epyc-root:docs/design/taskflow-stage1-canary-findings.md`. Approach: Read the r8a-r8g run directories' ledger lines (verdict, reason, failure_class, wall_s) and lane diffs; no reruns. Early end = the worker exited with wall_s below its cap and no verified verdict. Decision rule: build the resumable end state only if early ends are at least 2 of the units and at least one was later re-run by hand; otherwise decline in one line. Acceptance: the done-when (accepted: auto).

#### AK-KEEP-ANSWER-KEY (P4) -> `handoffs/active/autokernel-loop.md`, track `autokernel-research-loop`

```text
- [ ] **AK-KEEP-ANSWER-KEY** [non-inference] Build a labelled answer key of past AutoKernel keeps from the journal and keep receipts (each keep labelled held, or failed by a later serving gate, a neutral or negative leave-one-out arm, or a failed replication), split it by date into a tuning half and a later test half, and report the current keep gate's false-keep rate on the test half, so every later keep-gate change is scored against it (intake-2955, intake-2944)
      · done when: the answer key and a report giving the false-keep rate on the test half are committed under epyc-inference-research scripts/kernel_rnd/autokernel/loop/, or the report shows fewer than 10 failed keeps and closes the box as futile
      · gate: none
      · inputs: `handoffs/active/autokernel-loop.md`
```

Brief: where `epyc-inference-research:scripts/kernel_rnd/autokernel/loop/accumulate.py`; `epyc-inference-research:scripts/kernel_rnd/autokernel/loop/surface_fold.py::ExperimentalKeepReceipt`. Approach: Offline only: read retained receipts and journal shards, no benchmark. Label from later evidence already on record (serving-gate result, LOO arm, replication row). Re-apply the current keep rule to each stored receipt to get its decision. Split chronologically, older half for tuning and the later half as the test. Futility stop: fewer than 10 failed keeps means the set cannot score a gate change; close with the count. Acceptance: the done-when (accepted: auto).

## Monitors and knowledge-only (durable prose, no checkbox)

| Packet | Disposition | Covers | Basis |
|---|---|---|---|
| K1 | knowledge-only | AON-A4, AON-B3, AON-B5, AON-C1, AON-C3, AON-C5, AON-D4, AON-D5 | Already implemented. Session bus dedup and redelivery; AutoKernel resume and stagnation escapes; the Act, Don't Defer admission test; PM-RULES-WARN-FIRST; the WS-4 asyncRewake GO; kb-search; the autopilot's durable-state resume and outbox |
| K2 | knowledge-only | AON-B4, AON-C4, AON-D3, AON-F2 | Methodology and design notes with no live failure behind them; kept on the intake entries plus one autokernel-loop.md note |

No monitor trigger is filed: each closure names what would reopen it in the payload's opportunity review.

At Stage 4 these sentences are added as dated notes, with no checkbox:

- **`coordination-and-churn-pipeline.md`**, under PM-RULES-WARN-FIRST: "2026-11-24 note (intake-2943, intake-2947#00): the warn-then-enforce design matches the Claude Code commit gate (off/observe/enforce). The registry should absorb the existing ad-hoc instances RESERVATION_MODE, SMOKE_MEASURE_ENFORCE and commit-hygiene Rule G. Their block-twice-then-allow valve was declined for keeper rules: a keeper rule refuses a row, not a working agent."
- **`autokernel-loop.md`**, next to AK-KEEP-ANSWER-KEY: "2026-11-24 note (intake-2944): the bench-then-serving gate is this loop's train/test split; the documented bench +5.958% against serving -2.18% divergence is the overfitting signature the hill-climbing post describes."

## Operator decisions

- None open. The operator fixed the enforce criteria for scheduler C in advance (Revision 1), so no operator-decision box and no index row is filed.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| AON-A1 | intake-2942 dive A (Permissions: deferred tool calls) | Count early-ended taskflow units; add a typed resumable end state only if the count warrants | P3 / TF-EARLY-END-CENSUS |
| AON-A2 | intake-2942 dive A (Event inbox: one worker; rowflow.py L8405-L8432) | Give the single planner an owner: soak in shadow, then enforce on predeclared criteria | P1 / PM-REPLAN-C-SOAK |
| AON-A2b | intake-2942 dive A plus main review (rowflow.py L8424-L8427) | Decide enforcement of one planner from soak evidence | P1 / PM-REPLAN-C-SOAK |
| AON-A2c | intake-2943 dive B (rule pruning) and intake-2942 (single inbox) | Delete the subsumed patch rules once the one planner is enforced, keeping A-E replay tests | P1 / PM-RESERVE-RETIRE-PATCHES |
| AON-A3 | intake-2951 dive A (lease-style claims) | Make expired light claims self-release on the keeper tick | decline: reap_build_grants in rowflow.py already ends every build or light grant past its end= on the keeper tick |
| AON-A4 | intake-2952 dive A (at-least-once with idempotent consumers) | Adopt inbox/outbox delivery semantics on the session bus | K1 knowledge-only: the bus already dedups ids over retained history and redelivers unacknowledged messages |
| AON-A5 | intake-2942 dive A (Opus 5.5 cost figure) | Use the 78 percent cost reduction in planning | decline: vendor self-report on an unnamed benchmark |
| AON-A6 | intake-2950 dive A (timer per parked question) | Give every parked worker a follow-up timer | P3 / TF-EARLY-END-CENSUS |
| AON-B1 | intake-2943 dive B (per-commit verification stamp; checks the change cannot edit) | Judge Codex lane DONE from artifacts, not the lane's own LANE-STATUS line | P2 / PM-CODEX-LANE-VERDICT |
| AON-B2 | intake-2943 dive B (block twice then allow) | Add a bounded-block escape valve to PM-RULES-WARN-FIRST | decline: a keeper rule refuses a row, not a working agent; the would-fail count already screens false positives before enforce |
| AON-B3 | intake-2944 dive B (stall-triggered failure bucketing) | Add failure bucketing on stall to the AutoKernel planner | K1 knowledge-only: actor_context.py already forces diminishing-returns and stagnation escapes |
| AON-B4 | intake-2944 dive B (held-out figure) | Cite the held-out 78.6 to 90.5 percent result, not 98.9 percent | K2 knowledge-only: citation hygiene recorded on intake-2944 |
| AON-B5 | intake-2945 dive B (up-front approval list) | Name irreversible decisions before an autonomous loop | K1 knowledge-only: already the Act, Don't Defer admission test |
| AON-C1 | intake-2948 dive C (defer plus claude -p --resume) | Suspend claude -p workers at a question and resume from an inbox event | K1 knowledge-only: no claude -p worker asks questions; AutoKernel actors are one-shot proposal calls and the loop resumes from its store |
| AON-C2 | intake-2947 dive C (3 consecutive or 20 total denials, then escalate) | Bound the Codex driver's resume loop by a no-progress counter | P2 / PM-CODEX-LANE-VERDICT |
| AON-C3 | intake-2947 dive C (FPR on real traffic before trusting a gate) | Measure would-fail counts before enforcing new rules | K1 knowledge-only: the existing warn-first keeper-rule box already specifies would-fail counts before enforce |
| AON-C4 | intake-2949 dive C (write-ahead posting state) | Record a maybe-published state in publish_row | K2 knowledge-only: no observed publish ambiguity; recorded as a design note |
| AON-C5 | intake-2948 dive C (asyncRewake) | Use asyncRewake for zero-token waits | K1 knowledge-only: the asyncRewake spike already returned GO on Claude Code 2.1.321 |
| AON-D1 | intake-2942 and intake-2946 dive D (progress written along the way; capture distracts) | Have the harness, not the worker, write a resume record from artifacts at worker exit | P3 / TF-EARLY-END-CENSUS |
| AON-D2 | intake-2946 dive D (MEMORY.md 200 lines or 25 KB) | Check the auto-memory index against the load window | decline: settled at intake, 97 lines and 20,039 bytes are inside the window |
| AON-D3 | intake-2946 dive D (dreaming) | Scheduled re-validation of stored conclusions | K2 knowledge-only: no measured stale-conclusion failure yet |
| AON-D4 | intake-2946 dive D (wiki plus search) | Keep search beside the compiled wiki | K1 knowledge-only: kb-search already pairs search with the compiled wiki |
| AON-D5 | dive D autopilot mapping (epyc-orchestrator autopilot.py) | Map the autopilot to the five primitives | K1 knowledge-only: the autopilot already resumes each cycle from durable state and dedups its operator outbox |
| AON-E1 | intake-2953 dive E (external timer, forecasts too high) | Log wall seconds per Codex lane round | P2 / PM-CODEX-LANE-VERDICT |
| AON-E2 | intake-2953 dive E (clock tool) | Give agents a time budget in the continue message | decline: the paper shows Fable-class models ignore duration requests (slope 0.24); no tested effect |
| AON-E3 | intake-2954 dive E (DPO for refresh decisions) | Train time-aware refresh decisions | decline: no EPYC consumer makes refresh decisions from elapsed time |
| AON-F1 | intake-2955 dive F (incident-derived answer key) | Score the AutoKernel keep gate against a labelled set of past keeps | P4 / AK-KEEP-ANSWER-KEY |
| AON-F2 | intake-2955 dive F (round cap, diff-only re-review) | Cap reviewer rounds | K2 knowledge-only: the taskflow reviewer is single-pass, so there is no round loop to cap |

**Stage-1 preliminary actionables:** Stage 1 ran under pre-authorisation and listed each entry as a dive candidate with no separate hypotheses. Every dive-ledger row above has a terminal mapping.

## Dive-surfaced sources

| Source | Bears on | Disposition |
|---|---|---|
| claude.dev/blog/solving-code-review-at-anthropic | intake-2943 | Ingested and dived in wave 2 (intake-2955) |
| arXiv 2610.09944 AgentTime | intake-2950 | Ingested and dived in wave 2 (intake-2953) |
| arXiv 2510.23853 TicToc | intake-2950 | Ingested and dived in wave 2 (intake-2954) |
| arXiv 2504.13171 Sleep-time compute | intake-2946 | Already indexed (intake-819); cross-reference only |
| anthropic.com/research/managed-agents | intake-2949 | Already indexed (intake-2616); cross-reference only |
| Anthropic hosted-agent webhook docs (no URL given) | intake-2950 | Declined: no locator, and the conclusion is supported independently by intake-2951 and intake-2952 |
| arXiv 2604.00010, github.com/michaelofengenden/agenttimebench, arXiv 2601.16486, arXiv 2606.00198 | intake-2953 | Declined at the two-wave cap; recorded in intake-2953 dive_corrections |
| Code Review announcement post (no URL in text) | intake-2955 | Declined at the two-wave cap |

## Second-reader partials (for operator awareness; none auto-overturned)

The reader rated 11 anchors partial and itemised 6 of them; in each itemised one, the claim text carries one more detail than the quoted span:

- intake-2942[5]: scheduler steps.
- intake-2946[3]: the search pairing.
- intake-2946[5]: the one-writer remedy.
- intake-2949[3]: the budget pause.
- intake-2950[2]: the "poor clocks" framing.

The extra details are in the source next to the quote, but outside the reader's 400-character window. The 5 unitemised partials were not named by the reader. None of the 11 bears on a plan item: every packet rests on the main review's own reading of the passages and the code.

## Steering ledger

All six operator steering rows are retained verbatim in the payload's `steering_reconciliation`:

- Five are context-only (dive scope, the no-stop instruction, the approval gate, the lessons answered above, index rows prepared only).
- One is planned (binding targets, packet P1 plus the binding map).

## Stage-3 filing payload

```json
{
 "format_version": 2,
 "entry_updates": [
  {
   "id": "intake-2942",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "coordination-and-churn-pipeline.md",
    "churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P1 PM-REPLAN-C-SOAK, PM-RESERVE-RETIRE-PATCHES; P3 TF-EARLY-END-CENSUS"
   ]
  },
  {
   "id": "intake-2943",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "coordination-and-churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P2 PM-CODEX-LANE-VERDICT; P1 PM-RESERVE-RETIRE-PATCHES"
   ]
  },
  {
   "id": "intake-2944",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P4 AK-KEEP-ANSWER-KEY (held-out split)"
   ]
  },
  {
   "id": "intake-2945",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: Approval-list pattern already the Act, Don't Defer admission test; headline uncontrolled (AON-B5)"
   ]
  },
  {
   "id": "intake-2946",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P3 TF-EARLY-END-CENSUS (harness-side progress); MEMORY.md window check settled at intake (AON-D2)"
   ]
  },
  {
   "id": "intake-2947",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "coordination-and-churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P2 PM-CODEX-LANE-VERDICT (no-progress counter)"
   ]
  },
  {
   "id": "intake-2948",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: No claude -p worker asks questions; AutoKernel actors are one-shot and the loop resumes from its store (AON-C1, AON-C5)"
   ]
  },
  {
   "id": "intake-2949",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: Confirmation-before-ledger already how taskflow verify.py works (AON-C4)"
   ]
  },
  {
   "id": "intake-2950",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P3 TF-EARLY-END-CENSUS (timer per parked unit)"
   ]
  },
  {
   "id": "intake-2951",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: Lease expiry already implemented by reap_build_grants (AON-A3 declined)"
   ]
  },
  {
   "id": "intake-2952",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: The session bus already implements at-least-once delivery with id dedup (AON-A4)"
   ]
  },
  {
   "id": "intake-2953",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "coordination-and-churn-pipeline.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P2 PM-CODEX-LANE-VERDICT (wall seconds per round)"
   ]
  },
  {
   "id": "intake-2954",
   "integration_disposition": "knowledge_only",
   "handoffs_updated": [],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: No EPYC consumer makes refresh decisions from elapsed time (AON-E3)"
   ]
  },
  {
   "id": "intake-2955",
   "integration_disposition": "integrated",
   "handoffs_updated": [
    "autokernel-loop.md"
   ],
   "handoffs_created": [],
   "disposition_evidence": [
    "intake-always-on-1124 Stage 3 plan: P4 AK-KEEP-ANSWER-KEY"
   ]
  }
 ],
 "opportunity_reviews": {
  "P1": {
   "project_objective": "Every placement goes through one planner (scheduler C over B's admission path), so urgent heads are not starved and the patch rules stop accreting",
   "implementation_ref": "epyc-root:scripts/coordination/rowflow/rowflow.py RESERVATION block (RESERVATION_MODE = shadow; L8405-L8432 @ a290df6, L8489-L8516 @ 20a74f6) and claim_reservation_check",
   "gap": "Reservation B shipped in shadow (eb643ac37) and stays there by operator ruling; scheduler C is designed and replayed (docs/design/rowflow-replanning-scheduler.md) but no box owns its soak and enforcement or the deletion of the rules it subsumes; REPLAN_MODE is not yet in rowflow.py on origin/main 8d29489",
   "operational_change": "Soak C in shadow, enforce on the six predeclared criteria, then delete the subsumed rules with A-E replay tests",
   "benefit_direction": "Fewer starved urgent rows and fewer special-case rules; correctness constraint: no legitimate claim is refused (false-refusal count must be reported)",
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "execution_conditions": "Shadow soak: no grant writes. Enforce: automatic once the operator's six criteria hold for 7 shadow days. Retirement: only after C is enforced.",
   "closure_basis": "Immediate outcome retained in the named boxes; later steps gated as stated"
  },
  "P2": {
   "project_objective": "Codex lanes are driven deterministically and accepted from artifacts, as README-INTERIM.md already requires",
   "implementation_ref": "/mnt/raid0/llm/tmp/codex-lanes-20261123/drive.sh and drive2.sh (status() greps the first line of the lane's own report) and README-INTERIM.md rules, read 2026-11-24",
   "gap": "The drivers stop on the lane's self-written LANE-STATUS line, so DONE and BLOCKED are agent prose; cx11 self-declared BLOCKED on a non-blocker; the 5-consecutive-DONE exit criterion is counted from that line; rounds are capped at 8 with no no-progress rule and no wall log",
   "operational_change": "An artifact verdict function with a no-progress STALLED rule and a per-round wall log, committed with tests",
   "benefit_direction": "Fewer false DONE and false BLOCKED exits and a trustworthy exit-criterion count; correctness constraint: a genuine DONE is never refused",
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "execution_conditions": "Implementation and unit tests permitted now (no compute, no claim). Porting into the dispatcher stays with PM-CODEX-DISPATCH-DETERMINISTIC after its exit criterion.",
   "closure_basis": "Immediate outcome retained in the named boxes; later steps gated as stated"
  },
  "P3": {
   "project_objective": "Decide with evidence whether taskflow needs a resumable end state for workers that end early",
   "implementation_ref": "epyc-root:scripts/coordination/taskflow/dispatch.py L1-L30 @ a290df6 (run ends verified, rejected, unchecked or needs-brief; no resume path)",
   "gap": "No count exists of units that ended early without a verdict and were redone by hand, so the L1 failure is unmeasured on taskflow",
   "operational_change": "A census of r8a-r8g units with a predeclared build-or-decline rule",
   "benefit_direction": "Build the resume path only if early ends are real; constraint: no rerun, read-only",
   "owner": "handoffs/active/churn-pipeline.md",
   "execution_conditions": "Read-only census permitted now; any build is a separate box filed only if the rule says build.",
   "closure_basis": "Immediate outcome retained in the named boxes; later steps gated as stated"
  },
  "P4": {
   "project_objective": "Score AutoKernel keep-gate changes against a labelled set of past keeps, as the Code Review team scores its reviewer against past incidents",
   "implementation_ref": "epyc-inference-research:scripts/kernel_rnd/autokernel/loop/accumulate.py and surface_fold.py ExperimentalKeepReceipt @ 82d5822",
   "gap": "Nothing grades the keep gate's false-keep rate against keeps that later failed; LOO tests keep contribution at promotion, not the gate",
   "operational_change": "An offline answer key with a chronological held-out half and the current gate's false-keep rate on it",
   "benefit_direction": "Keep-gate changes become measurable; constraint: offline only, futility stop below 10 failed keeps",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "Offline analysis permitted now; no benchmark or claim. AutoKernel owns the handoff; pipeline-mgmt may prepare it as loop infrastructure.",
   "closure_basis": "Immediate outcome retained in the named boxes; later steps gated as stated"
  },
  "K1": {
   "project_objective": "Record source mechanisms that our stack already implements, so they are not rebuilt",
   "implementation_ref": "coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "gap": "None found: bus dedup and redelivery, AutoKernel resume and stagnation escapes, autopilot durable-state resume and outbox, the warn-first keeper box, the asyncRewake GO and kb-search are all in place",
   "operational_change": "None; a dated note under PM-RULES-WARN-FIRST records the source agreement and the ad-hoc mode flags its registry should absorb",
   "benefit_direction": "Avoids duplicate machinery",
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "execution_conditions": "No immediate step remains: each reviewed mechanism is already implemented at the named file",
   "closure_basis": "Closed: mechanisms already implemented in the named files"
  },
  "K2": {
   "project_objective": "Keep methodology and design notes from the sources where future work will read them",
   "implementation_ref": "intake-2944 dive_corrections (held-out figure); intake-2949 write-ahead record; intake-2946 dreaming; intake-2955 round cap; autokernel-loop.md (bench-versus-serving note)",
   "gap": "No live failure motivates code: publish ambiguity unobserved, no stale-conclusion failure measured, the taskflow reviewer is single-pass",
   "operational_change": "Dated notes only (autokernel-loop.md bench-versus-serving note); the rest live on the intake entries",
   "benefit_direction": "Correct citation and design context for later work",
   "owner": "handoffs/active/autokernel-loop.md",
   "execution_conditions": "No immediate step remains; reopen only if a publish ambiguity, a stale conclusion or a multi-round reviewer is observed",
   "closure_basis": "Closed: mechanisms already implemented in the named files"
  }
 },
 "actionable_additions": [
  {
   "ledger_id": "AON-A1",
   "source": "intake-2942 dive A (Permissions: deferred tool calls)",
   "action": "Count early-ended taskflow units; add a typed resumable end state only if the count warrants",
   "terminal_mapping": "P3 / TF-EARLY-END-CENSUS"
  },
  {
   "ledger_id": "AON-A2",
   "source": "intake-2942 dive A (Event inbox: one worker; rowflow.py L8405-L8432)",
   "action": "Give the single planner an owner: soak in shadow, then enforce on predeclared criteria",
   "terminal_mapping": "P1 / PM-REPLAN-C-SOAK"
  },
  {
   "ledger_id": "AON-A2b",
   "source": "intake-2942 dive A plus main review (rowflow.py L8424-L8427)",
   "action": "Decide enforcement of one planner from soak evidence",
   "terminal_mapping": "P1 / PM-REPLAN-C-SOAK"
  },
  {
   "ledger_id": "AON-A2c",
   "source": "intake-2943 dive B (rule pruning) and intake-2942 (single inbox)",
   "action": "Delete the subsumed patch rules once the one planner is enforced, keeping A-E replay tests",
   "terminal_mapping": "P1 / PM-RESERVE-RETIRE-PATCHES"
  },
  {
   "ledger_id": "AON-A3",
   "source": "intake-2951 dive A (lease-style claims)",
   "action": "Make expired light claims self-release on the keeper tick",
   "terminal_mapping": "decline: reap_build_grants in rowflow.py already ends every build or light grant past its end= on the keeper tick"
  },
  {
   "ledger_id": "AON-A4",
   "source": "intake-2952 dive A (at-least-once with idempotent consumers)",
   "action": "Adopt inbox/outbox delivery semantics on the session bus",
   "terminal_mapping": "K1 knowledge-only: the bus already dedups ids over retained history and redelivers unacknowledged messages"
  },
  {
   "ledger_id": "AON-A5",
   "source": "intake-2942 dive A (Opus 5.5 cost figure)",
   "action": "Use the 78 percent cost reduction in planning",
   "terminal_mapping": "decline: vendor self-report on an unnamed benchmark"
  },
  {
   "ledger_id": "AON-A6",
   "source": "intake-2950 dive A (timer per parked question)",
   "action": "Give every parked worker a follow-up timer",
   "terminal_mapping": "P3 / TF-EARLY-END-CENSUS"
  },
  {
   "ledger_id": "AON-B1",
   "source": "intake-2943 dive B (per-commit verification stamp; checks the change cannot edit)",
   "action": "Judge Codex lane DONE from artifacts, not the lane's own LANE-STATUS line",
   "terminal_mapping": "P2 / PM-CODEX-LANE-VERDICT"
  },
  {
   "ledger_id": "AON-B2",
   "source": "intake-2943 dive B (block twice then allow)",
   "action": "Add a bounded-block escape valve to PM-RULES-WARN-FIRST",
   "terminal_mapping": "decline: a keeper rule refuses a row, not a working agent; the would-fail count already screens false positives before enforce"
  },
  {
   "ledger_id": "AON-B3",
   "source": "intake-2944 dive B (stall-triggered failure bucketing)",
   "action": "Add failure bucketing on stall to the AutoKernel planner",
   "terminal_mapping": "K1 knowledge-only: actor_context.py already forces diminishing-returns and stagnation escapes"
  },
  {
   "ledger_id": "AON-B4",
   "source": "intake-2944 dive B (held-out figure)",
   "action": "Cite the held-out 78.6 to 90.5 percent result, not 98.9 percent",
   "terminal_mapping": "K2 knowledge-only: citation hygiene recorded on intake-2944"
  },
  {
   "ledger_id": "AON-B5",
   "source": "intake-2945 dive B (up-front approval list)",
   "action": "Name irreversible decisions before an autonomous loop",
   "terminal_mapping": "K1 knowledge-only: already the Act, Don't Defer admission test"
  },
  {
   "ledger_id": "AON-C1",
   "source": "intake-2948 dive C (defer plus claude -p --resume)",
   "action": "Suspend claude -p workers at a question and resume from an inbox event",
   "terminal_mapping": "K1 knowledge-only: no claude -p worker asks questions; AutoKernel actors are one-shot proposal calls and the loop resumes from its store"
  },
  {
   "ledger_id": "AON-C2",
   "source": "intake-2947 dive C (3 consecutive or 20 total denials, then escalate)",
   "action": "Bound the Codex driver's resume loop by a no-progress counter",
   "terminal_mapping": "P2 / PM-CODEX-LANE-VERDICT"
  },
  {
   "ledger_id": "AON-C3",
   "source": "intake-2947 dive C (FPR on real traffic before trusting a gate)",
   "action": "Measure would-fail counts before enforcing new rules",
   "terminal_mapping": "K1 knowledge-only: the existing warn-first keeper-rule box already specifies would-fail counts before enforce"
  },
  {
   "ledger_id": "AON-C4",
   "source": "intake-2949 dive C (write-ahead posting state)",
   "action": "Record a maybe-published state in publish_row",
   "terminal_mapping": "K2 knowledge-only: no observed publish ambiguity; recorded as a design note"
  },
  {
   "ledger_id": "AON-C5",
   "source": "intake-2948 dive C (asyncRewake)",
   "action": "Use asyncRewake for zero-token waits",
   "terminal_mapping": "K1 knowledge-only: the asyncRewake spike already returned GO on Claude Code 2.1.321"
  },
  {
   "ledger_id": "AON-D1",
   "source": "intake-2942 and intake-2946 dive D (progress written along the way; capture distracts)",
   "action": "Have the harness, not the worker, write a resume record from artifacts at worker exit",
   "terminal_mapping": "P3 / TF-EARLY-END-CENSUS"
  },
  {
   "ledger_id": "AON-D2",
   "source": "intake-2946 dive D (MEMORY.md 200 lines or 25 KB)",
   "action": "Check the auto-memory index against the load window",
   "terminal_mapping": "decline: settled at intake, 97 lines and 20,039 bytes are inside the window"
  },
  {
   "ledger_id": "AON-D3",
   "source": "intake-2946 dive D (dreaming)",
   "action": "Scheduled re-validation of stored conclusions",
   "terminal_mapping": "K2 knowledge-only: no measured stale-conclusion failure yet"
  },
  {
   "ledger_id": "AON-D4",
   "source": "intake-2946 dive D (wiki plus search)",
   "action": "Keep search beside the compiled wiki",
   "terminal_mapping": "K1 knowledge-only: kb-search already pairs search with the compiled wiki"
  },
  {
   "ledger_id": "AON-D5",
   "source": "dive D autopilot mapping (epyc-orchestrator autopilot.py)",
   "action": "Map the autopilot to the five primitives",
   "terminal_mapping": "K1 knowledge-only: the autopilot already resumes each cycle from durable state and dedups its operator outbox"
  },
  {
   "ledger_id": "AON-E1",
   "source": "intake-2953 dive E (external timer, forecasts too high)",
   "action": "Log wall seconds per Codex lane round",
   "terminal_mapping": "P2 / PM-CODEX-LANE-VERDICT"
  },
  {
   "ledger_id": "AON-E2",
   "source": "intake-2953 dive E (clock tool)",
   "action": "Give agents a time budget in the continue message",
   "terminal_mapping": "decline: the paper shows Fable-class models ignore duration requests (slope 0.24); no tested effect"
  },
  {
   "ledger_id": "AON-E3",
   "source": "intake-2954 dive E (DPO for refresh decisions)",
   "action": "Train time-aware refresh decisions",
   "terminal_mapping": "decline: no EPYC consumer makes refresh decisions from elapsed time"
  },
  {
   "ledger_id": "AON-F1",
   "source": "intake-2955 dive F (incident-derived answer key)",
   "action": "Score the AutoKernel keep gate against a labelled set of past keeps",
   "terminal_mapping": "P4 / AK-KEEP-ANSWER-KEY"
  },
  {
   "ledger_id": "AON-F2",
   "source": "intake-2955 dive F (round cap, diff-only re-review)",
   "action": "Cap reviewer rounds",
   "terminal_mapping": "K2 knowledge-only: the taskflow reviewer is single-pass, so there is no round loop to cap"
  }
 ],
 "steering_reconciliation": [
  {
   "seq": 1,
   "stage": 1,
   "ts": "2026-11-24T15:55:00Z",
   "verbatim": "Accept all recommended deep dives and literature expansions for up to two Stage 2 waves. The source seems relevant for building agent loops and general agent pipelines which are central to our project. It could inform refinements to our current infra.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied as the dive set: wave 1 dived all 11 Stage-1 entries, wave 2 dived 3 dive-surfaced sources; remaining surfaced sources declined at the two-wave cap. Not a filing authority."
  },
  {
   "seq": 2,
   "stage": 1,
   "ts": "2026-11-24T15:55:00Z",
   "verbatim": "Pre-authorised dives. The operator has pre-approved every deep dive and literature expansion you recommend, for up to TWO Stage-2 waves. Do not stop to ask which entries to dive. Run waves 1 and 2 on your own recommendations.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied: no stop to select dives; both waves ran on the intake's own recommendations."
  },
  {
   "seq": 3,
   "stage": 1,
   "ts": "2026-11-24T15:55:00Z",
   "verbatim": "Stage 3 still needs approval. Handoff changes are applied only after plan approval. Bring the Stage-3 plan back to me. Don't apply it, unless the skill itself allows applying without approval.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Applied: this plan is returned unapplied; Stage 4 waits for operator approval."
  },
  {
   "seq": 4,
   "stage": 1,
   "ts": "2026-11-24T15:55:00Z",
   "verbatim": "Binding targets. Map learnings to our agent-loop and pipeline infrastructure: the AutoKernel loop: handoffs/active/autokernel-loop.md and autokernel-akx-program.md, plus code in epyc-inference-research scripts/kernel_rnd/autokernel/loop/; the dispatcher and session bus: scripts/coordination/ and handoffs/active/coordination-and-churn-pipeline.md; the taskflow worker harness: scripts/coordination/taskflow/; the rowflow keeper and scheduler: scripts/coordination/rowflow/; Codex-lane driving: the box PM-CODEX-DISPATCH-DETERMINISTIC and /mnt/raid0/llm/tmp/codex-lanes-20261123/README-INTERIM.md; the orchestrator/autopilot (epyc-orchestrator). Search handoffs/active before proposing anything new, and bind each learning to the existing box or handoff that owns it.",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "Every target mapped: rowflow keeper to P1; Codex lanes and PM-CODEX-DISPATCH-DETERMINISTIC to P2; taskflow to P3; AutoKernel loop to P4 plus knowledge-only rows AON-B3 and AON-C1; session bus and orchestrator autopilot to knowledge-only rows AON-A4 and AON-D5. handoffs/active was searched for an owner before each box."
  },
  {
   "seq": 5,
   "stage": 1,
   "ts": "2026-11-24T15:55:00Z",
   "verbatim": "Lessons worth testing against the source. These are this week's live failures: one-shot workers ending early with no resume; claims bypassing the scheduler queue; patch-rule accretion versus a single reservation; warn-first rollout of new rules; deterministic acceptance from artifacts, not agent prose. Note where the source agrees, disagrees, or adds something.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "Answered in the plan's Live lessons table, with the source stance per lesson."
  },
  {
   "seq": 6,
   "stage": 1,
   "ts": "2026-11-24T15:55:00Z",
   "verbatim": "Index rows: prepare them only; I apply them.",
   "disposition": "context-only",
   "plan_ref": null,
   "reason": "No new handoff or stub is proposed, so no index row is needed; generated thin rows refresh through index_state.py at Stage 4."
  },
  {
   "seq": 7,
   "stage": 3,
   "ts": "2026-11-24T18:10:00Z",
   "verbatim": "pipeline-mgmt, the OPERATOR APPROVED the Stage-3 plan with amendments. File all five and finish Stage 4. - P1 (PM-RESERVE-SOAK / PM-RESERVE-ENFORCE): REPLACE it with ONE box, PM-REPLAN-C-SOAK, in coordination-and-churn-pipeline.md: \"Soak re-planning scheduler C (REPLAN_MODE=shadow) and enforce when docs/design/rowflow-replanning-scheduler.md criteria hold: 0 violations, solver p99 <1 s, weighted work ≥ greedy, urgent wait ≤0.7× greedy, ≤1 build-lane collision/day, no row past the 12 h pin\". B stays RESERVATION_MODE=shadow per the operator, so drop the OP-RESERVE-ENFORCE index row. - P1b: PM-RESERVE-RETIRE-PATCHES, gated on PM-REPLAN-C-SOAK. - P2 (PM-CODEX-LANE-VERDICT), P3 (TF-EARLY-END-CENSUS) and P4 (AK-KEEP-ANSWER-KEY, in autokernel-loop.md for AutoKernel to accept): as drafted. Use handoff_box.py with briefs, and run index_state.py --check (must exit 0). Push with serialized_push and confirm PUSH VERIFIED. No index rows. Report the SHAs.",
   "disposition": "planned",
   "plan_ref": "P1",
   "reason": "Operator approval with amendments, relayed by the coordinator: P1 replaced by PM-REPLAN-C-SOAK, the retirement box re-gated on it, the operator-queue row dropped, P2-P4 filed as drafted."
  }
 ],
 "opportunity_scan": [
  {
   "scan_id": "S01",
   "source_ref": "intake-2942 dive A (Permissions: deferred tool calls)",
   "implementation_ref": "epyc-root:scripts/coordination/taskflow/dispatch.py L1-L30 @ a290df6 (run ends verified, rejected, unchecked or needs-brief; no resume path)",
   "mechanism": "Count early-ended taskflow units; add a typed resumable end state only if the count warrants",
   "consumer": "handoffs/active/churn-pipeline.md",
   "application": "Count early-ended taskflow units; add a typed resumable end state only if the count warrants",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-A1"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S02",
   "source_ref": "intake-2942 dive A (Event inbox: one worker; rowflow.py L8405-L8432)",
   "implementation_ref": "epyc-root:scripts/coordination/rowflow/rowflow.py RESERVATION block (RESERVATION_MODE = shadow; L8405-L8432 @ a290df6, L8489-L8516 @ 20a74f6) and claim_reservation_check",
   "mechanism": "Give the single planner an owner: soak in shadow, then enforce on predeclared criteria",
   "consumer": "handoffs/active/coordination-and-churn-pipeline.md",
   "application": "Give the single planner an owner: soak in shadow, then enforce on predeclared criteria",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-A2"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S03",
   "source_ref": "intake-2942 dive A plus main review (rowflow.py L8424-L8427)",
   "implementation_ref": "epyc-root:scripts/coordination/rowflow/rowflow.py RESERVATION block (RESERVATION_MODE = shadow; L8405-L8432 @ a290df6, L8489-L8516 @ 20a74f6) and claim_reservation_check",
   "mechanism": "Decide enforcement of one planner from soak evidence",
   "consumer": "handoffs/active/coordination-and-churn-pipeline.md",
   "application": "Decide enforcement of one planner from soak evidence",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-A2b"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S04",
   "source_ref": "intake-2943 dive B (rule pruning) and intake-2942 (single inbox)",
   "implementation_ref": "epyc-root:scripts/coordination/rowflow/rowflow.py RESERVATION block (RESERVATION_MODE = shadow; L8405-L8432 @ a290df6, L8489-L8516 @ 20a74f6) and claim_reservation_check",
   "mechanism": "Delete the subsumed patch rules once the one planner is enforced, keeping A-E replay tests",
   "consumer": "handoffs/active/coordination-and-churn-pipeline.md",
   "application": "Delete the subsumed patch rules once the one planner is enforced, keeping A-E replay tests",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-A2c"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S05",
   "source_ref": "intake-2951 dive A (lease-style claims)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Make expired light claims self-release on the keeper tick",
   "consumer": "existing implementation named in basis",
   "application": "Make expired light claims self-release on the keeper tick",
   "disposition": "declined",
   "ledger_ids": [
    "AON-A3"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; decline: reap_build_grants in rowflow.py already ends every build or light grant past its end= on the keeper tick"
  },
  {
   "scan_id": "S06",
   "source_ref": "intake-2952 dive A (at-least-once with idempotent consumers)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Adopt inbox/outbox delivery semantics on the session bus",
   "consumer": "existing implementation named in basis",
   "application": "Adopt inbox/outbox delivery semantics on the session bus",
   "disposition": "covered",
   "ledger_ids": [
    "AON-A4"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: the bus already dedups ids over retained history and redelivers unacknowledged messages"
  },
  {
   "scan_id": "S07",
   "source_ref": "intake-2942 dive A (Opus 5.5 cost figure)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Use the 78 percent cost reduction in planning",
   "consumer": "existing implementation named in basis",
   "application": "Use the 78 percent cost reduction in planning",
   "disposition": "declined",
   "ledger_ids": [
    "AON-A5"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; decline: vendor self-report on an unnamed benchmark"
  },
  {
   "scan_id": "S08",
   "source_ref": "intake-2950 dive A (timer per parked question)",
   "implementation_ref": "epyc-root:scripts/coordination/taskflow/dispatch.py L1-L30 @ a290df6 (run ends verified, rejected, unchecked or needs-brief; no resume path)",
   "mechanism": "Give every parked worker a follow-up timer",
   "consumer": "handoffs/active/churn-pipeline.md",
   "application": "Give every parked worker a follow-up timer",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-A6"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S09",
   "source_ref": "intake-2943 dive B (per-commit verification stamp; checks the change cannot edit)",
   "implementation_ref": "/mnt/raid0/llm/tmp/codex-lanes-20261123/drive.sh and drive2.sh (status() greps the first line of the lane's own report) and README-INTERIM.md rules, read 2026-11-24",
   "mechanism": "Judge Codex lane DONE from artifacts, not the lane's own LANE-STATUS line",
   "consumer": "handoffs/active/coordination-and-churn-pipeline.md",
   "application": "Judge Codex lane DONE from artifacts, not the lane's own LANE-STATUS line",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-B1"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S10",
   "source_ref": "intake-2943 dive B (block twice then allow)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Add a bounded-block escape valve to PM-RULES-WARN-FIRST",
   "consumer": "existing implementation named in basis",
   "application": "Add a bounded-block escape valve to PM-RULES-WARN-FIRST",
   "disposition": "declined",
   "ledger_ids": [
    "AON-B2"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; decline: a keeper rule refuses a row, not a working agent; the would-fail count already screens false positives before enforce"
  },
  {
   "scan_id": "S11",
   "source_ref": "intake-2944 dive B (stall-triggered failure bucketing)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Add failure bucketing on stall to the AutoKernel planner",
   "consumer": "existing implementation named in basis",
   "application": "Add failure bucketing on stall to the AutoKernel planner",
   "disposition": "covered",
   "ledger_ids": [
    "AON-B3"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: actor_context.py already forces diminishing-returns and stagnation escapes"
  },
  {
   "scan_id": "S12",
   "source_ref": "intake-2944 dive B (held-out figure)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Cite the held-out 78.6 to 90.5 percent result, not 98.9 percent",
   "consumer": "existing implementation named in basis",
   "application": "Cite the held-out 78.6 to 90.5 percent result, not 98.9 percent",
   "disposition": "covered",
   "ledger_ids": [
    "AON-B4"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K2 knowledge-only: citation hygiene recorded on intake-2944"
  },
  {
   "scan_id": "S13",
   "source_ref": "intake-2945 dive B (up-front approval list)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Name irreversible decisions before an autonomous loop",
   "consumer": "existing implementation named in basis",
   "application": "Name irreversible decisions before an autonomous loop",
   "disposition": "covered",
   "ledger_ids": [
    "AON-B5"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: already the Act, Don't Defer admission test"
  },
  {
   "scan_id": "S14",
   "source_ref": "intake-2948 dive C (defer plus claude -p --resume)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Suspend claude -p workers at a question and resume from an inbox event",
   "consumer": "existing implementation named in basis",
   "application": "Suspend claude -p workers at a question and resume from an inbox event",
   "disposition": "covered",
   "ledger_ids": [
    "AON-C1"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: no claude -p worker asks questions; AutoKernel actors are one-shot proposal calls and the loop resumes from its store"
  },
  {
   "scan_id": "S15",
   "source_ref": "intake-2947 dive C (3 consecutive or 20 total denials, then escalate)",
   "implementation_ref": "/mnt/raid0/llm/tmp/codex-lanes-20261123/drive.sh and drive2.sh (status() greps the first line of the lane's own report) and README-INTERIM.md rules, read 2026-11-24",
   "mechanism": "Bound the Codex driver's resume loop by a no-progress counter",
   "consumer": "handoffs/active/coordination-and-churn-pipeline.md",
   "application": "Bound the Codex driver's resume loop by a no-progress counter",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-C2"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S16",
   "source_ref": "intake-2947 dive C (FPR on real traffic before trusting a gate)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Measure would-fail counts before enforcing new rules",
   "consumer": "existing implementation named in basis",
   "application": "Measure would-fail counts before enforcing new rules",
   "disposition": "covered",
   "ledger_ids": [
    "AON-C3"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: the existing warn-first keeper-rule box already specifies would-fail counts before enforce"
  },
  {
   "scan_id": "S17",
   "source_ref": "intake-2949 dive C (write-ahead posting state)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Record a maybe-published state in publish_row",
   "consumer": "existing implementation named in basis",
   "application": "Record a maybe-published state in publish_row",
   "disposition": "covered",
   "ledger_ids": [
    "AON-C4"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K2 knowledge-only: no observed publish ambiguity; recorded as a design note"
  },
  {
   "scan_id": "S18",
   "source_ref": "intake-2948 dive C (asyncRewake)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Use asyncRewake for zero-token waits",
   "consumer": "existing implementation named in basis",
   "application": "Use asyncRewake for zero-token waits",
   "disposition": "covered",
   "ledger_ids": [
    "AON-C5"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: the asyncRewake spike already returned GO on Claude Code 2.1.321"
  },
  {
   "scan_id": "S19",
   "source_ref": "intake-2942 and intake-2946 dive D (progress written along the way; capture distracts)",
   "implementation_ref": "epyc-root:scripts/coordination/taskflow/dispatch.py L1-L30 @ a290df6 (run ends verified, rejected, unchecked or needs-brief; no resume path)",
   "mechanism": "Have the harness, not the worker, write a resume record from artifacts at worker exit",
   "consumer": "handoffs/active/churn-pipeline.md",
   "application": "Have the harness, not the worker, write a resume record from artifacts at worker exit",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-D1"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S20",
   "source_ref": "intake-2946 dive D (MEMORY.md 200 lines or 25 KB)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Check the auto-memory index against the load window",
   "consumer": "existing implementation named in basis",
   "application": "Check the auto-memory index against the load window",
   "disposition": "declined",
   "ledger_ids": [
    "AON-D2"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; decline: settled at intake, 97 lines and 20,039 bytes are inside the window"
  },
  {
   "scan_id": "S21",
   "source_ref": "intake-2946 dive D (dreaming)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Scheduled re-validation of stored conclusions",
   "consumer": "existing implementation named in basis",
   "application": "Scheduled re-validation of stored conclusions",
   "disposition": "covered",
   "ledger_ids": [
    "AON-D3"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K2 knowledge-only: no measured stale-conclusion failure yet"
  },
  {
   "scan_id": "S22",
   "source_ref": "intake-2946 dive D (wiki plus search)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Keep search beside the compiled wiki",
   "consumer": "existing implementation named in basis",
   "application": "Keep search beside the compiled wiki",
   "disposition": "covered",
   "ledger_ids": [
    "AON-D4"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: kb-search already pairs search with the compiled wiki"
  },
  {
   "scan_id": "S23",
   "source_ref": "dive D autopilot mapping (epyc-orchestrator autopilot.py)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Map the autopilot to the five primitives",
   "consumer": "existing implementation named in basis",
   "application": "Map the autopilot to the five primitives",
   "disposition": "covered",
   "ledger_ids": [
    "AON-D5"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K1 knowledge-only: the autopilot already resumes each cycle from durable state and dedups its operator outbox"
  },
  {
   "scan_id": "S24",
   "source_ref": "intake-2953 dive E (external timer, forecasts too high)",
   "implementation_ref": "/mnt/raid0/llm/tmp/codex-lanes-20261123/drive.sh and drive2.sh (status() greps the first line of the lane's own report) and README-INTERIM.md rules, read 2026-11-24",
   "mechanism": "Log wall seconds per Codex lane round",
   "consumer": "handoffs/active/coordination-and-churn-pipeline.md",
   "application": "Log wall seconds per Codex lane round",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-E1"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S25",
   "source_ref": "intake-2953 dive E (clock tool)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Give agents a time budget in the continue message",
   "consumer": "existing implementation named in basis",
   "application": "Give agents a time budget in the continue message",
   "disposition": "declined",
   "ledger_ids": [
    "AON-E2"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; decline: the paper shows Fable-class models ignore duration requests (slope 0.24); no tested effect"
  },
  {
   "scan_id": "S26",
   "source_ref": "intake-2954 dive E (DPO for refresh decisions)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Train time-aware refresh decisions",
   "consumer": "existing implementation named in basis",
   "application": "Train time-aware refresh decisions",
   "disposition": "declined",
   "ledger_ids": [
    "AON-E3"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; decline: no EPYC consumer makes refresh decisions from elapsed time"
  },
  {
   "scan_id": "S27",
   "source_ref": "intake-2955 dive F (incident-derived answer key)",
   "implementation_ref": "epyc-inference-research:scripts/kernel_rnd/autokernel/loop/accumulate.py and surface_fold.py ExperimentalKeepReceipt @ 82d5822",
   "mechanism": "Score the AutoKernel keep gate against a labelled set of past keeps",
   "consumer": "handoffs/active/autokernel-loop.md",
   "application": "Score the AutoKernel keep gate against a labelled set of past keeps",
   "disposition": "actionable",
   "ledger_ids": [
    "AON-F1"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review"
  },
  {
   "scan_id": "S28",
   "source_ref": "intake-2955 dive F (round cap, diff-only re-review)",
   "implementation_ref": "see terminal mapping basis",
   "mechanism": "Cap reviewer rounds",
   "consumer": "existing implementation named in basis",
   "application": "Cap reviewer rounds",
   "disposition": "covered",
   "ledger_ids": [
    "AON-F2"
   ],
   "basis": "Source passage read in the dive; current consumer read by main review; K2 knowledge-only: the taskflow reviewer is single-pass, so there is no round loop to cap"
  }
 ],
 "outcome_reviews": {
  "AON-A1": {
   "required_outcome": "Count early-ended taskflow units; add a typed resumable end state only if the count warrants",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; TF-EARLY-END-CENSUS's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/churn-pipeline.md",
     "task_id": "TF-EARLY-END-CENSUS",
     "task_text": "- [ ] **TF-EARLY-END-CENSUS** [non-inference] Count the taskflow units in canaries r8a-r8g whose worker ended before its wall cap with an empty or partial diff and no verified verdict, and how many were re-run by hand, then apply the brief's build-or-decline rule to a typed resumable end state in dispatch.py that select.py re-admits (intake-2942 deferred-call resume, intake-2950 timer per parked unit, intake-2946 progress written by the harness rather than the worker)",
     "acceptance": "a census table (unit, end reason, diff lines, re-dispatched yes or no) for every r8a-r8g unit and a one-line build-or-decline decision are appended to docs/design/taskflow-stage1-canary-findings.md on origin/main"
    }
   ]
  },
  "AON-A2": {
   "required_outcome": "Give the single planner an owner: soak in shadow, then enforce on predeclared criteria",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; PM-REPLAN-C-SOAK's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "PM-REPLAN-C-SOAK",
     "task_text": "- [ ] **PM-REPLAN-C-SOAK** [non-inference] Soak re-planning scheduler C (REPLAN_MODE=shadow) and enforce when docs/design/rowflow-replanning-scheduler.md criteria hold: 0 violations, solver p99 <1 s, weighted work ≥ greedy, urgent wait ≤0.7× greedy, ≤1 build-lane collision/day, no row past the 12 h pin (operator 2026-11-24; reservation B stays RESERVATION_MODE=shadow; intake-2942, intake-2952)",
     "acceptance": "a soak report shows 7 shadow days meeting all six criteria of docs/design/rowflow-replanning-scheduler.md section 11, and rowflow.py on origin/main has REPLAN_MODE = \"enforce\" with the live keeper start time after that deploy"
    }
   ]
  },
  "AON-A2b": {
   "required_outcome": "Decide enforcement of one planner from soak evidence",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; PM-REPLAN-C-SOAK's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "PM-REPLAN-C-SOAK",
     "task_text": "- [ ] **PM-REPLAN-C-SOAK** [non-inference] Soak re-planning scheduler C (REPLAN_MODE=shadow) and enforce when docs/design/rowflow-replanning-scheduler.md criteria hold: 0 violations, solver p99 <1 s, weighted work ≥ greedy, urgent wait ≤0.7× greedy, ≤1 build-lane collision/day, no row past the 12 h pin (operator 2026-11-24; reservation B stays RESERVATION_MODE=shadow; intake-2942, intake-2952)",
     "acceptance": "a soak report shows 7 shadow days meeting all six criteria of docs/design/rowflow-replanning-scheduler.md section 11, and rowflow.py on origin/main has REPLAN_MODE = \"enforce\" with the live keeper start time after that deploy"
    }
   ]
  },
  "AON-A2c": {
   "required_outcome": "Delete the subsumed patch rules once the one planner is enforced, keeping A-E replay tests",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; PM-RESERVE-RETIRE-PATCHES's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "PM-RESERVE-RETIRE-PATCHES",
     "task_text": "- [ ] **PM-RESERVE-RETIRE-PATCHES** [non-inference] Once PM-REPLAN-C-SOAK has enforced scheduler C, delete the hand-coded reservation rules C subsumes (docs/design/rowflow-replanning-scheduler.md section 11: RANK-HOLD, RANK-SKIP, QUIET-RESERVE, QUIET-URGENT-PENDING, BACKFILL-IF-FITS, and rank_reservation/DRAIN except what B's fallback path still calls) and keep one replay test per original starvation case A-E (listed in the RESERVATION comment block of rowflow.py), so one plan is the only path (intake-2942, intake-2943)",
     "acceptance": "none of the subsumed rules remains in rowflow.py on origin/main outside B's fallback path and pytest scripts/coordination/tests -k reservation passes with one named test per case A-E"
    }
   ]
  },
  "AON-A3": {
   "required_outcome": "Make expired light claims self-release on the keeper tick",
   "review_status": "closed-with-basis",
   "review_basis": "decline: reap_build_grants in rowflow.py already ends every build or light grant past its end= on the keeper tick",
   "task_refs": []
  },
  "AON-A4": {
   "required_outcome": "Adopt inbox/outbox delivery semantics on the session bus",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: the bus already dedups ids over retained history and redelivers unacknowledged messages; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-A5": {
   "required_outcome": "Use the 78 percent cost reduction in planning",
   "review_status": "closed-with-basis",
   "review_basis": "decline: vendor self-report on an unnamed benchmark",
   "task_refs": []
  },
  "AON-A6": {
   "required_outcome": "Give every parked worker a follow-up timer",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; TF-EARLY-END-CENSUS's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/churn-pipeline.md",
     "task_id": "TF-EARLY-END-CENSUS",
     "task_text": "- [ ] **TF-EARLY-END-CENSUS** [non-inference] Count the taskflow units in canaries r8a-r8g whose worker ended before its wall cap with an empty or partial diff and no verified verdict, and how many were re-run by hand, then apply the brief's build-or-decline rule to a typed resumable end state in dispatch.py that select.py re-admits (intake-2942 deferred-call resume, intake-2950 timer per parked unit, intake-2946 progress written by the harness rather than the worker)",
     "acceptance": "a census table (unit, end reason, diff lines, re-dispatched yes or no) for every r8a-r8g unit and a one-line build-or-decline decision are appended to docs/design/taskflow-stage1-canary-findings.md on origin/main"
    }
   ]
  },
  "AON-B1": {
   "required_outcome": "Judge Codex lane DONE from artifacts, not the lane's own LANE-STATUS line",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; PM-CODEX-LANE-VERDICT's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "PM-CODEX-LANE-VERDICT",
     "task_text": "- [ ] **PM-CODEX-LANE-VERDICT** [non-inference] Take the interim Codex lane driver's stop decision off the lane's self-written LANE-STATUS line (drive.sh and drive2.sh stop on its first line): commit the loop as scripts/coordination/codex_lane.py whose DONE is computed from artifacts (each reported box's branch and sha exist and pass the static checks; for pushed lanes, reachable from origin/main and box ticked), treat LANE-STATUS as a hint, stop as STALLED after 3 consecutive rounds with no new commit, and log rounds and wall seconds per lane (intake-2943, intake-2947#02, intake-2953)",
     "acceptance": "pytest scripts/coordination/tests -k codex_lane_verdict passes on origin/main and covers a DONE line with a missing branch (refused), a BLOCKED line with new commits (resumed) and three no-commit rounds (STALLED)"
    }
   ]
  },
  "AON-B2": {
   "required_outcome": "Add a bounded-block escape valve to PM-RULES-WARN-FIRST",
   "review_status": "closed-with-basis",
   "review_basis": "decline: a keeper rule refuses a row, not a working agent; the would-fail count already screens false positives before enforce",
   "task_refs": []
  },
  "AON-B3": {
   "required_outcome": "Add failure bucketing on stall to the AutoKernel planner",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: actor_context.py already forces diminishing-returns and stagnation escapes; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-B4": {
   "required_outcome": "Cite the held-out 78.6 to 90.5 percent result, not 98.9 percent",
   "review_status": "closed-with-basis",
   "review_basis": "K2 knowledge-only: citation hygiene recorded on intake-2944; reviewed against intake-2944 dive_corrections (held-out figure); intake-2949 write-ahead record; intake-2946 dreaming; intake-2955 round cap; autokernel-loop.md (bench-versus-serving note)",
   "task_refs": []
  },
  "AON-B5": {
   "required_outcome": "Name irreversible decisions before an autonomous loop",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: already the Act, Don't Defer admission test; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-C1": {
   "required_outcome": "Suspend claude -p workers at a question and resume from an inbox event",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: no claude -p worker asks questions; AutoKernel actors are one-shot proposal calls and the loop resumes from its store; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-C2": {
   "required_outcome": "Bound the Codex driver's resume loop by a no-progress counter",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; PM-CODEX-LANE-VERDICT's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "PM-CODEX-LANE-VERDICT",
     "task_text": "- [ ] **PM-CODEX-LANE-VERDICT** [non-inference] Take the interim Codex lane driver's stop decision off the lane's self-written LANE-STATUS line (drive.sh and drive2.sh stop on its first line): commit the loop as scripts/coordination/codex_lane.py whose DONE is computed from artifacts (each reported box's branch and sha exist and pass the static checks; for pushed lanes, reachable from origin/main and box ticked), treat LANE-STATUS as a hint, stop as STALLED after 3 consecutive rounds with no new commit, and log rounds and wall seconds per lane (intake-2943, intake-2947#02, intake-2953)",
     "acceptance": "pytest scripts/coordination/tests -k codex_lane_verdict passes on origin/main and covers a DONE line with a missing branch (refused), a BLOCKED line with new commits (resumed) and three no-commit rounds (STALLED)"
    }
   ]
  },
  "AON-C3": {
   "required_outcome": "Measure would-fail counts before enforcing new rules",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: the existing warn-first keeper-rule box already specifies would-fail counts before enforce; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-C4": {
   "required_outcome": "Record a maybe-published state in publish_row",
   "review_status": "closed-with-basis",
   "review_basis": "K2 knowledge-only: no observed publish ambiguity; recorded as a design note; reviewed against intake-2944 dive_corrections (held-out figure); intake-2949 write-ahead record; intake-2946 dreaming; intake-2955 round cap; autokernel-loop.md (bench-versus-serving note)",
   "task_refs": []
  },
  "AON-C5": {
   "required_outcome": "Use asyncRewake for zero-token waits",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: the asyncRewake spike already returned GO on Claude Code 2.1.321; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-D1": {
   "required_outcome": "Have the harness, not the worker, write a resume record from artifacts at worker exit",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; TF-EARLY-END-CENSUS's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/churn-pipeline.md",
     "task_id": "TF-EARLY-END-CENSUS",
     "task_text": "- [ ] **TF-EARLY-END-CENSUS** [non-inference] Count the taskflow units in canaries r8a-r8g whose worker ended before its wall cap with an empty or partial diff and no verified verdict, and how many were re-run by hand, then apply the brief's build-or-decline rule to a typed resumable end state in dispatch.py that select.py re-admits (intake-2942 deferred-call resume, intake-2950 timer per parked unit, intake-2946 progress written by the harness rather than the worker)",
     "acceptance": "a census table (unit, end reason, diff lines, re-dispatched yes or no) for every r8a-r8g unit and a one-line build-or-decline decision are appended to docs/design/taskflow-stage1-canary-findings.md on origin/main"
    }
   ]
  },
  "AON-D2": {
   "required_outcome": "Check the auto-memory index against the load window",
   "review_status": "closed-with-basis",
   "review_basis": "decline: settled at intake, 97 lines and 20,039 bytes are inside the window",
   "task_refs": []
  },
  "AON-D3": {
   "required_outcome": "Scheduled re-validation of stored conclusions",
   "review_status": "closed-with-basis",
   "review_basis": "K2 knowledge-only: no measured stale-conclusion failure yet; reviewed against intake-2944 dive_corrections (held-out figure); intake-2949 write-ahead record; intake-2946 dreaming; intake-2955 round cap; autokernel-loop.md (bench-versus-serving note)",
   "task_refs": []
  },
  "AON-D4": {
   "required_outcome": "Keep search beside the compiled wiki",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: kb-search already pairs search with the compiled wiki; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-D5": {
   "required_outcome": "Map the autopilot to the five primitives",
   "review_status": "closed-with-basis",
   "review_basis": "K1 knowledge-only: the autopilot already resumes each cycle from durable state and dedups its operator outbox; reviewed against coordination/session-bus/BUS_PROTOCOL.md L28-L37 and session_bus.py L1666-L1672 @ a290df6; research loop/actor_context.py and run_args.py --resume @ 82d5822; epyc-orchestrator scripts/autopilot/autopilot.py @ a5b996bb; coordination-and-churn-pipeline.md PM-RULES-WARN-FIRST and the WS-4 asyncRewake spike",
   "task_refs": []
  },
  "AON-E1": {
   "required_outcome": "Log wall seconds per Codex lane round",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; PM-CODEX-LANE-VERDICT's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/coordination-and-churn-pipeline.md",
     "task_id": "PM-CODEX-LANE-VERDICT",
     "task_text": "- [ ] **PM-CODEX-LANE-VERDICT** [non-inference] Take the interim Codex lane driver's stop decision off the lane's self-written LANE-STATUS line (drive.sh and drive2.sh stop on its first line): commit the loop as scripts/coordination/codex_lane.py whose DONE is computed from artifacts (each reported box's branch and sha exist and pass the static checks; for pushed lanes, reachable from origin/main and box ticked), treat LANE-STATUS as a hint, stop as STALLED after 3 consecutive rounds with no new commit, and log rounds and wall seconds per lane (intake-2943, intake-2947#02, intake-2953)",
     "acceptance": "pytest scripts/coordination/tests -k codex_lane_verdict passes on origin/main and covers a DONE line with a missing branch (refused), a BLOCKED line with new commits (resumed) and three no-commit rounds (STALLED)"
    }
   ]
  },
  "AON-E2": {
   "required_outcome": "Give agents a time budget in the continue message",
   "review_status": "closed-with-basis",
   "review_basis": "decline: the paper shows Fable-class models ignore duration requests (slope 0.24); no tested effect",
   "task_refs": []
  },
  "AON-E3": {
   "required_outcome": "Train time-aware refresh decisions",
   "review_status": "closed-with-basis",
   "review_basis": "decline: no EPYC consumer makes refresh decisions from elapsed time",
   "task_refs": []
  },
  "AON-F1": {
   "required_outcome": "Score the AutoKernel keep gate against a labelled set of past keeps",
   "review_status": "preserved",
   "review_basis": "Main review read the source passage and the pinned implementation; AK-KEEP-ANSWER-KEY's text and done-when deliver this action at its owner",
   "task_refs": [
    {
     "owner": "handoffs/active/autokernel-loop.md",
     "task_id": "AK-KEEP-ANSWER-KEY",
     "task_text": "- [ ] **AK-KEEP-ANSWER-KEY** [non-inference] Build a labelled answer key of past AutoKernel keeps from the journal and keep receipts (each keep labelled held, or failed by a later serving gate, a neutral or negative leave-one-out arm, or a failed replication), split it by date into a tuning half and a later test half, and report the current keep gate's false-keep rate on the test half, so every later keep-gate change is scored against it (intake-2955, intake-2944)",
     "acceptance": "the answer key and a report giving the false-keep rate on the test half are committed under epyc-inference-research scripts/kernel_rnd/autokernel/loop/, or the report shows fewer than 10 failed keeps and closes the box as futile"
    }
   ]
  },
  "AON-F2": {
   "required_outcome": "Cap reviewer rounds",
   "review_status": "closed-with-basis",
   "review_basis": "K2 knowledge-only: the taskflow reviewer is single-pass, so there is no round loop to cap; reviewed against intake-2944 dive_corrections (held-out figure); intake-2949 write-ahead record; intake-2946 dreaming; intake-2955 round cap; autokernel-loop.md (bench-versus-serving note)",
   "task_refs": []
  }
 },
 "proposed_tasks": [
  {
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "task_text": "- [ ] **PM-REPLAN-C-SOAK** [non-inference] Soak re-planning scheduler C (REPLAN_MODE=shadow) and enforce when docs/design/rowflow-replanning-scheduler.md criteria hold: 0 violations, solver p99 <1 s, weighted work ≥ greedy, urgent wait ≤0.7× greedy, ≤1 build-lane collision/day, no row past the 12 h pin (operator 2026-11-24; reservation B stays RESERVATION_MODE=shadow; intake-2942, intake-2952)"
  },
  {
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "task_text": "- [ ] **PM-RESERVE-RETIRE-PATCHES** [non-inference] Once PM-REPLAN-C-SOAK has enforced scheduler C, delete the hand-coded reservation rules C subsumes (docs/design/rowflow-replanning-scheduler.md section 11: RANK-HOLD, RANK-SKIP, QUIET-RESERVE, QUIET-URGENT-PENDING, BACKFILL-IF-FITS, and rank_reservation/DRAIN except what B's fallback path still calls) and keep one replay test per original starvation case A-E (listed in the RESERVATION comment block of rowflow.py), so one plan is the only path (intake-2942, intake-2943)"
  },
  {
   "owner": "handoffs/active/coordination-and-churn-pipeline.md",
   "task_text": "- [ ] **PM-CODEX-LANE-VERDICT** [non-inference] Take the interim Codex lane driver's stop decision off the lane's self-written LANE-STATUS line (drive.sh and drive2.sh stop on its first line): commit the loop as scripts/coordination/codex_lane.py whose DONE is computed from artifacts (each reported box's branch and sha exist and pass the static checks; for pushed lanes, reachable from origin/main and box ticked), treat LANE-STATUS as a hint, stop as STALLED after 3 consecutive rounds with no new commit, and log rounds and wall seconds per lane (intake-2943, intake-2947#02, intake-2953)"
  },
  {
   "owner": "handoffs/active/churn-pipeline.md",
   "task_text": "- [ ] **TF-EARLY-END-CENSUS** [non-inference] Count the taskflow units in canaries r8a-r8g whose worker ended before its wall cap with an empty or partial diff and no verified verdict, and how many were re-run by hand, then apply the brief's build-or-decline rule to a typed resumable end state in dispatch.py that select.py re-admits (intake-2942 deferred-call resume, intake-2950 timer per parked unit, intake-2946 progress written by the harness rather than the worker)"
  },
  {
   "owner": "handoffs/active/autokernel-loop.md",
   "task_text": "- [ ] **AK-KEEP-ANSWER-KEY** [non-inference] Build a labelled answer key of past AutoKernel keeps from the journal and keep receipts (each keep labelled held, or failed by a later serving gate, a neutral or negative leave-one-out arm, or a failed replication), split it by date into a tuning half and a later test half, and report the current keep gate's false-keep rate on the test half, so every later keep-gate change is scored against it (intake-2955, intake-2944)"
  }
 ]
}
```
