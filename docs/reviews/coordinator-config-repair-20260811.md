# Coordinator configuration repair — root cause and change proposal

Commissioned by the operator, 2026-08-11. Investigation only: **nothing in this report has been
applied**. No agent file, skill, config, handoff, checkbox, bus row, or commit was touched.

---

## 0. The finding that reframes everything

Before the per-failure analysis: F2 is not "the coordinator-agent only exists during a turn."
The fleet's autonomous wake path is **structurally dead**, and has been since the mains moved
from Codex to Claude.

Live probe, run during this investigation:

```
$ python3 scripts/coordination/tmux_adapter.py probe --agent mainA
runtime    UNAVAILABLE — backend 'claude': no runtime signal implemented yet
heartbeat  working (age 44762s)
nudge_ok   False
  BLOCKED  heartbeat is 44762s stale (> 900s)
```

Three facts compose into a deadlock:

1. `session_bus_coordinator.py:1634` — the daemon's stuck predicate counts a heartbeat **older
   than 3600 s** as stuck.
2. `tmux_adapter.py:1600` (`--heartbeat-max-age`, default **900 s**) and `:1140-1141` — the
   adapter **refuses to nudge** any agent whose heartbeat is older than 900 s.
3. The two overrides that could break the tie are both unavailable. C35 (`:1113-1139`) only
   lifts the `state == "working"` blocker, never the *staleness* blocker. C36 (`:1112`) lifts
   both — but only when the runtime probe returns a definite `idle`, and the runtime reader is
   **Codex-rollout-only** (`tmux_adapter.py:645`, `_BACKENDS`). Every main today is a Claude
   backend, so C36 is **0 % available**.

The guard therefore gets *stronger the worse the condition it guards against gets*: an agent
that stops writing heartbeats becomes permanently unreachable, and staleness only ever grows.
Every roster main crossed 900 s at ~10:14–10:22Z and the whole fleet — coordinator included —
became un-nudgeable for the rest of the day.

The daemon noticed and recorded it, in a file with no reader:

| agent | `stuck-nudge-refused` rows, 2026-08-11 | first |
|---|---|---|
| mainC | 129 | 08:55Z |
| mainA | 127 | 08:55Z |
| **coordinator-agent** | **126** | 10:22Z |
| auditor | 100 | 12:47Z |

`coordinator-agent` sat at **39 unread** while the daemon logged 126 consecutive refusals into
`coordination/session-bus/advisory.jsonl`. The refusal branch
(`session_bus_coordinator.py:1897-1901`) writes an advisory and retries every
`_STUCK_REFUSAL_RETRY_S` = 300 s **forever**. The one escalation that would have surfaced it,
`stuck-refusing-drain` (`:1863-1875`), is gated on `rec["last_nudge_sig"]`, which is only ever
written on `rc == 0` (`:1889-1891`). **A nudge that is always refused can never escalate.** That
is a fail-open of exactly the C3/C6/C8 class, inside the module whose entire defect history is
fail-opens.

This single defect is the highest-leverage repair on the list.

---

## 1. Per-failure root cause

### F1 — no progress logged for a full working day (PRIMARY)

**A rule existed; nothing enforced it — and the one mechanism that would have done it is
contractually forbidden from firing on its own.**

- `CLAUDE.md:70`: "Daily progress in `progress/YYYY-MM/YYYY-MM-DD.md`. Always update after
  significant work." Prose, no actor, no trigger, no check.
- `agents/coordinator-agent.md` — grep for `progress/`: **zero hits**. The role that owns fleet
  reporting has no progress-log duty written into it at all.
- `agents/shared/SESSION_LIFECYCLE.md:34-41` ("Wrap-up at major checkpoints") never names
  `progress/` either. Its whole enforcement story is the *checkbox* axiom.
- The only thing that actually writes the file is `/wrap-up` step 1
  (`.claude/commands/wrap-up.md:9-13`), and `:5` says: **"⚠ MANUAL TRIGGER ONLY … there is no
  `Stop`/`SessionEnd`/`PreCompact` hook, cron, or nightshift task that calls it, and there must
  not be one."**

So the obligation is stated in a file with no enforcement, is absent from the owner's role file,
and is bundled inside a routine that policy forbids automating. Nothing could have fired. The
day's shape confirms it: 37 commits in epyc-root between 08:48Z and 21:46Z;
`progress/2026-08/2026-08-11.md` mtime **02:47:33Z**, untouched by any of them.

**The remedy hinges on a distinction the current files never draw**: `/wrap-up` bundles a cheap,
safe, high-frequency artifact (the progress entry) with expensive, review-cadence operations
(index pruning, handoff compaction, wiki compile, branch promotion). Only the second group needs
to be manual. `wrap-up.md:5` already concedes this — "autonomous … sessions **may commit
progress directly** … is fine and encouraged for checkpointing". **Split the progress write out
of `/wrap-up` and it becomes automatable without touching the manual-only contract.**

### F2 — 10-hour fleet stall

Detection worked at every layer and **transport** failed. `detect_task_boundaries`
(`session_bus_coordinator.py:1559`) correctly filed task-boundary notices to
`inbox/coordinator-agent.jsonl`; `resolve_stuck_agents` (`:1740`) correctly detected
`coordinator-agent` stuck from 10:22Z. Then the adapter's staleness guard refused every one of
126 delivery attempts (§0), the refusal branch had no escalation, and the daemon's operator
bypass — `pending_operator_actions` / `_OPERATOR_ITEM_KINDS = {"token-request", "defect"}`
(`:1929`), which writes into `tokens/token-queue.md` after 5400 s — scans **inbox rows**, not
advisory rows, so a 126-row transport failure was invisible to the one path designed to reach
the operator when the coordinator can't be reached.

Secondary contributor: the daemon's stuck predicate requires `unread > 0` (`:1803`). An idle
main that has drained its inbox is, to the daemon, **not stuck** — even though
`SESSION_LIFECYCLE.md:10` calls exactly that state "a coordination failure". The daemon has no
concept of *idle with an empty queue*.

On the CronCreate mitigation (job `00fbd3bb`, hourly at `:07`): it is a real improvement over
nothing, because it manufactures a turn, which is the missing ingredient. But it is **not** the
durable answer, on four counts: (a) it is session-scoped and dies with the session — the exact
property that made C8's session-local poller a defect; (b) it auto-expires after 7 days, so it
fails **silently and open** on day 8; (c) it lives outside the repo, so it is not reviewable,
not versioned, and invisible to a fresh coordinator doing a cold start; (d) it does nothing for
the un-nudgeable-fleet defect underneath — an hourly coordinator tick that still cannot reach
any main is an hourly report of a stall, not its repair. Fix the adapter first; keep the cron as
a belt.

### F3 — net-negative board movement, unnoticed

**No rule and no mechanism existed.** `scripts/handoffs/index_state.py` computes exactly the
right quantity per handoff — `scan_handoff` (`:138-155`) returns `open`/`closed`/`guarded`/
`blocked` — and then **throws `closed` away**: the domain aggregate at `:204-219` sums only
`open` and `blocked`, and `render_block` (`:221-232`) prints only those. So `closed` is computed
174 times per run and never reaches any output. Worse, the tool is a **pure snapshot**: it
overwrites `.index-state.json` each run with no history, so a *delta* is not derivable after the
fact even in principle. The operator's "doesn't show much more progress" was a manual eyeball of
a number the tooling had, discarded, and could not have compared.

### F4 — coordinator reasoning from a stale internal clock

**No rule existed.** Between-turn wall time is invisible to a model: nothing in `CLAUDE.md`,
`agents/coordinator-agent.md`, `SESSION_LIFECYCLE.md`, or the cold-start skill tells the
coordinator that its context is a snapshot with an age. The nearest existing rules are
adjacent but do not cover it: "DRAIN BEFORE YOU SPEAK" (`coordinator-agent.md:60-69`) mandates
re-reading the *inbox*, and "Verify agent state before reporting it" (`:103`) mandates re-reading
*heartbeats* — neither says "your recollection of when something happened is stale, re-read
before asserting a time-dependent fact." The token-authoring assertion was a state read the
coordinator believed it had already done, hours earlier. Note this is not a coordinator-only
hazard: the same class produced C40 ("drain and triage say how OLD a message is", commit
`5ff9c56b`, today) — the repo already recognised that ages must be *rendered*, not inferred.

---

## 2. Ranked change proposal

Strength ladder: **(a)** harness-enforced hook · **(b)** daemon check escalating on the bus ·
**(c)** script gate exiting non-zero · **(d)** prose.

### R1 — Break the nudge deadlock. Strength (b)+(c). Closes F2. **Do this first.**

Nothing else in this report matters while the fleet is unreachable.

- `scripts/coordination/tmux_adapter.py:1140-1141` — the staleness blocker must gain the same
  quiescence override C35 gives the `working` blocker. Proposed condition, mirroring the C35
  reasoning verbatim so the polarity argument is unchanged: if `dead is False` **and**
  `quiet_for is not None` **and** `quiet_for >= hb_override_quiet_s` (120 s), the pane is settled
  at its prompt and staleness is a stale self-report, not evidence of generation — record
  `hb_override_applied` and drop the blocker. If the pane is unreadable or recently active, the
  blocker stands (fail-closed preserved).
- `scripts/coordination/tmux_adapter.py:645` `_BACKENDS` — the C36 runtime reader is Codex-only,
  so C36 is 0 % available on an all-Claude fleet. Either implement a Claude-backend runtime
  signal or state in the module docstring that C36 is inert for this fleet. **Right now the file
  reads as if a protection exists that does not.**
- `scripts/coordination/session_bus_coordinator.py:1897-1901` — a repeated refusal must escalate.
  Add a refusal counter to the durable `_STUCK_STATE` record and, past a bounded deadline (2 h /
  ~24 consecutive refusals), file a `defect` **into `inbox/coordinator-agent.jsonl`** naming the
  agent and the verbatim refusal text. Because `defect ∈ _OPERATOR_ITEM_KINDS` (`:1929`), the
  existing C20 bypass then carries it to `tokens/token-queue.md` after 90 min unread — which is
  precisely the "coordinator unreachable" case. **No new escalation path is needed; the item just
  has to enter the one that already works.**
- Consistency: the daemon considers >3600 s stale as *stuck* while the adapter treats >900 s as
  *unreachable*. These two constants must be reconciled or the deadlock returns by drift.

### R2 — Daemon-side progress-log check. Strength (b). Closes F1.

New function in `scripts/coordination/session_bus_coordinator.py`, called from `tick()`
(`:2684-2731`) alongside `audit()` — this is exactly the shape `audit()` already has:

```python
def progress_log_currency(bus_root, epoch, *, hours=4):
    """Commits landed with no progress-log write. Fails CLOSED: if git or the
    progress file cannot be read, emit a defect saying so — never 'clean'."""
    # 1. newest commit ts across the three owned repos (git log -1 --format=%cI)
    # 2. mtime of progress/<YYYY-MM>/<today>.md  (absent => epoch 0, i.e. overdue)
    # 3. if commits_since(progress_mtime) >= 1 and now - progress_mtime > hours:
    #        file kind="defect", to=coordinator-agent, check="progress-log-stale",
    #        detail="N commits since HH:MMZ; progress/<file> last written HH:MMZ"
```

Why this is the right shape: it reuses the daemon's existing `git log` capability (`audit()`
`:1425-1437` already shells out to git), it files a `defect`, and `defect` is already in
`_OPERATOR_ITEM_KINDS` — so an unpresented one reaches `token-queue.md` on the C20 timer without
one line of new escalation code. **Fail-closed requirement:** an unreadable git or missing
progress directory must emit the defect, never suppress it. `scan_operator_receipts` (`:2046`)
is the in-repo precedent — it returns a `*-skipped` advisory rather than an all-clear.

### R3 — Split the progress write out of `/wrap-up`. Strength (c)+(d). Closes F1.

The obligation cannot be automated while it lives inside a manual-only routine.

- New `scripts/session/progress_checkpoint.py` — appends a timestamped section to
  `progress/YYYY-MM/YYYY-MM-DD.md` from a supplied summary + the commit range since the last
  entry; `--check` exits non-zero when commits exist with no entry covering them. This is a
  **checkpoint** artifact, explicitly the thing `wrap-up.md:5` already blesses, and it performs
  **none** of the manual-only operations (no index pruning, no compaction, no wiki compile, no
  promotion).
- `.claude/commands/wrap-up.md:9-13` — Step 1 delegates to that script; the manual-only banner at
  `:5` gains one sentence stating that *the progress entry alone* is checkpointable, and that the
  manual-only scope is Steps 3, 5 and 7. Without this the banner and R2 contradict each other,
  and a future agent will read the banner and disable the check.
- `agents/coordinator-agent.md` — add a Guardrail (this is (d), and it is proposed **only** as
  the human-readable pointer to R2's mechanism, not as the enforcement):
  > **A working day with commits and no progress entry is a coordinator defect.** At every
  > checkpoint, and at minimum every 4 hours of fleet activity, either a main has written
  > `progress/YYYY-MM/YYYY-MM-DD.md` or you write the fleet-level entry yourself. The daemon's
  > `progress-log-stale` defect is the backstop, not the plan.

### R4 — Throughput measurement. Strength (c). Closes F3.

`scripts/handoffs/index_state.py`:

- `:204-219` — carry `closed` into the domain aggregate (already computed at `:138-155`, then
  discarded).
- `:221-232` `render_block` — add `Closed` and `Δopen / Δclosed since previous run` columns.
- New append-only `handoffs/active/.index-history.jsonl`, one row per run:
  `{ts, open, closed, blocked, handoffs}`. A snapshot file cannot yield a delta after the fact;
  **this is the load-bearing part** and it is three lines.
- `--summary` prints the delta since the last row. Surface it in the coordinator skill's per-tick
  loop (R6) and in the daemon's periodic report.
- Do **not** gate `--check` on a negative delta. Negative throughput is legitimate (filing
  discovered work is progress); it needs *visibility*, not a veto. A gate here would be routed
  around within a day.

### R5 — Hooks. Strength (a). Partially closes F1/F4.

Available Claude Code hook events: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`,
`Notification`, `Stop`, `SubagentStop`, `PreCompact`, `SessionStart`, `SessionEnd`. This repo
already runs 12 hooks from `.claude/settings.json:1-83` (all `PreToolUse`/`PostToolUse`), so the
mechanism is proven here.

- **`SessionStart` → context injection (F4).** Emit the current UTC time, the age of the newest
  `progress/` entry, and the mtime of `coordination/session-bus/advisory.jsonl`. Cheap, cannot
  fail open in a harmful direction (worst case: no context). Recommended.
- **`UserPromptSubmit` → staleness banner (F4).** When >30 min of wall time has passed since the
  previous turn in this session, inject "⏱ N hours have passed since your last turn — re-read
  state before asserting anything time-dependent." **This is the strongest available closure of
  F4**: it fires on the exact event (a new turn after a gap) and it is harness-enforced, not
  remembered.
- **`PostToolUse` matcher `Bash` → commit counter (F1).** The existing
  `check_commit_hygiene.py` (`PreToolUse`) already parses git-commit command lines, so the
  parsing is done. A `PostToolUse` sibling can stamp a counter file that R2 reads, giving the
  daemon a commit signal that does not depend on git-log parsing. Optional; R2 works without it.
- **`Stop` → wrap-up.** **Do not build this.** `wrap-up.md:5` forbids it by name, and the
  prohibition is correct — a `Stop` hook that runs index pruning and branch promotion on every
  turn end is a disaster. A `Stop` hook that merely *warns* "commits landed, no progress entry"
  is acceptable and much weaker than R2 (it fires only when the session happens to end); take it
  only as a supplement.

### R6 — Ordered per-tick loop in the coordinator skill. Strength (d). Supports F1/F2/F3.

`.claude/skills/coordinator-agent/SKILL.md` currently has Phases 0-4 for the **cold start** and
one standing rule at `:315-328` (DRAIN BEFORE YOU SPEAK). There is **no defined recurring tick**
— Phase 3 step 4 says only "Begin boundary watching", which is an intention, not a procedure.
Add a numbered, ordered **Phase 5 — every tick**:

1. `drain --agent coordinator-agent`, severity triage.
2. Refresh heartbeat (this is also what keeps the fleet nudgeable under R1's override).
3. Read the clock; state elapsed time since last tick before asserting any time-dependent fact.
4. `index_state.py --summary` — report the open/closed delta (R4).
5. **Progress obligation**: if commits landed since the last progress entry, dispatch a
   progress-write subagent *before* dispatching new work.
6. Per-main boundary check: idle → wrap-up-then-dispatch, or close.
7. `grep stuck-nudge-refused` in `advisory.jsonl` since the last tick — the file has no reader
   today.

Ordering matters because step 5 must precede step 6: today's failure was precisely dispatching
new work over an unwrapped boundary. This is (d) — **and I propose it knowing (d) is what failed
today.** It is included only because a mechanism needs a documented procedure to point at; R2
and R1 are what actually enforce it. If only one of R6 and R2 can be built, build R2.

---

## 3. Evaluation of the named candidate mechanisms

| Candidate | Feasible? | Verdict |
|---|---|---|
| Daemon compares commit activity vs `progress/*.md` mtime, files a `defect` | **Yes** | R2. Strongest realistic F1 closure. The daemon already runs git (`:1425`) and already files defects, and `defect` already routes to the operator via C20 without new code. |
| Wrap-up obligation attached to the task-boundary event; block dispatch until wrapped | **Partly — do not build the blocking half** | See below. |
| Throughput delta computed by `index_state.py`, surfaced each tick | **Yes, trivially** | R4. `closed` is already computed and discarded; the only real addition is the history file. |
| A hook in `.claude/settings.json` | **Yes** | R5. `SessionStart` + `UserPromptSubmit` are the useful events; `Stop`-triggered wrap-up is forbidden by `wrap-up.md:5` and should stay forbidden. |
| Ordered non-skippable wrap-up step in the coordinator skill | **Yes** | R6, as documentation of R2's mechanism only. Strength (d). |

**On the boundary-gated wrap-up, in detail.** The *detection* half is free: the daemon already
emits the boundary (`:1559-1615`). Recording an obligation against it is a small addition to
`boundary_state.json` — for each `working → idle` transition, store `{agent, task_id, ts,
wrapped: false}`, cleared when a commit touches `progress/` or the handoff owning `task_id`. That
half I recommend, and it strictly improves the daemon's blindness noted in F2 (it does not depend
on `unread > 0`).

The *enforcement* half — refusing to dispatch new work until the previous task is wrapped — I
recommend **against**, at least initially. The daemon runs at `authority: manual`
(`config.yaml:83`), so it does not dispatch at all; the block would have to live in the
coordinator-agent, i.e. it is (d) again wearing a mechanism's clothes. And it fails in the
dangerous direction: a hard block on an unverifiable condition (did the wrap-up "count"?) stalls
the fleet, which is F2's failure mode, to prevent F1's. Make the obligation **visible and
overdue-flagged**, not blocking.

---

## 4. Draft INCIDENT_LOG.md entries — DRAFT ONLY, not added to the file

House style checked against `docs/reference/agent-config/INCIDENT_LOG.md:1-5`: `## INC-<date>-<slug>`,
prose narrative, measured specifics, closing "Rule fed:" line naming the file the rule lives in.

```markdown
## INC-20260811-unnudgeable-fleet-stale-heartbeat-deadlock
Every roster main, coordinator-agent included, became permanently unreachable at ~10:14-10:22Z
and stayed so for over ten hours. The daemon's stuck predicate counts a heartbeat older than
3600 s as stuck (`session_bus_coordinator.py` `_STUCK_HEARTBEAT_STALE_S`); the adapter's guard
chain refuses to nudge any agent whose heartbeat is older than 900 s
(`tmux_adapter.py --heartbeat-max-age`). The two overrides that could break the tie were both
absent: C35's quiescence override lifts only the `state == "working"` blocker, never staleness,
and C36's runtime reader is implemented for the Codex backend only — on an all-Claude fleet it
reports UNAVAILABLE 100 % of the time. The guard therefore hardens monotonically as the
condition it guards against worsens. The daemon detected the stall correctly and logged 129
(mainC), 127 (mainA), 126 (coordinator-agent) and 100 (auditor) consecutive `stuck-nudge-refused`
advisories into `advisory.jsonl`, a file with no reader; the one escalation that would have
surfaced it, `stuck-refusing-drain`, is gated on a nudge having succeeded, so a nudge that is
always refused can never escalate. Fail-open, in the module whose defect history (C3, C6, C8) is
entirely fail-opens. Rules fed: the staleness blocker gains C35's quiescence override; a bounded
run of refusals files a `defect` to coordinator-agent's inbox so the existing C20 operator bypass
carries it; the daemon's and the adapter's staleness constants are reconciled rather than drifting.

## INC-20260811-unlogged-working-day
Five mains landed 33 commits between 08:50Z and 21:45Z while
`progress/2026-08/2026-08-11.md` kept an mtime of 02:47Z — written before the fleet spawned. Two
rules covered this and neither could fire. `CLAUDE.md` § Progress Tracking states the obligation
in prose with no actor and no check; `agents/coordinator-agent.md` does not mention `progress/`
at all; and the only routine that writes the file, `/wrap-up` Step 1, is stamped MANUAL TRIGGER
ONLY and explicitly forbids any Stop/SessionEnd/cron trigger. The obligation was thus stated
where nothing enforces it and implemented only inside a routine policy forbids automating. The
underlying conflation is that `/wrap-up` bundles a cheap daily artifact (the progress entry) with
review-cadence operations (index pruning, handoff compaction, wiki compile, branch promotion) —
only the latter needs to be manual, as the routine's own banner concedes when it blesses direct
progress commits for checkpointing. Rules fed: the progress entry is split into a checkpointable
script; the daemon files a `progress-log-stale` defect when commits land with no progress write
in N hours; the coordinator's role file gains the obligation it never had.

## INC-20260811-throughput-unmeasured
Open checkboxes across `handoffs/active/` moved 1283 -> 1293 while done moved 2274 -> 2294: about
30 rows filed against 20 closed, a net-negative day that nobody detected until the operator said
the board "doesn't show much more progress than this morning". `index_state.py` computes exactly
the needed quantity — `scan_handoff` returns open/closed/guarded/blocked for all 174 handoffs —
and then discards `closed`: the domain aggregate and the rendered rollup carry only `open` and
`blocked`. It is also a pure snapshot, overwriting `.index-state.json` each run with no history,
so a delta was not derivable after the fact even in principle. Rules fed: `closed` reaches the
aggregate and the rollup; every run appends `{ts, open, closed, blocked}` to
`.index-history.jsonl`; the coordinator reports the delta each tick. Deliberately NOT fed: a
`--check` gate on negative throughput — filing discovered work is progress, and a gate there
would be routed around.

## INC-20260811-stale-clock-assertion
Across a 12-hour gap between turns, the coordinator told the operator that ratification tokens
"aren't authored yet (the auditor is drafting)" when they had been filed hours earlier. It was
not a memory failure but a category error: it reasoned from a state read it had genuinely
performed, without registering that the read had aged. Between-turn wall time is invisible to a
model, and no rule anywhere told it so — "DRAIN BEFORE YOU SPEAK" mandates re-reading the inbox
and "Verify agent state before reporting it" mandates re-reading heartbeats, but neither covers
"your recollection of WHEN is stale." Same class as C40 (`5ff9c56b`, same day), which made
message age a rendered field rather than an inferred one. Rule fed: a `UserPromptSubmit` hook
injects elapsed wall time when a turn follows a gap, and the coordinator tick loop reads the
clock before any time-dependent assertion.
```

---

## 5. What NOT to do

- **Do not make the CronCreate hourly tick the answer to F2.** Session-scoped, dies with the
  session, expires silently after 7 days, invisible to a cold start — every property that made
  C8's session-local poller a defect. Keep it as a belt; the braces are R1.
- **Do not add a `Stop`/`SessionEnd` hook that runs `/wrap-up`.** `wrap-up.md:5` forbids it by
  name and the prohibition is sound: index pruning and branch promotion on every turn end is a
  far worse failure than an unwritten progress entry.
- **Do not block dispatch on an unverified wrap-up.** A hard block on a condition no machine can
  evaluate ("was this wrap-up adequate?") stalls the fleet — F2's failure mode — to prevent F1's.
- **Do not gate `index_state.py --check` on a negative open/closed delta.** Negative throughput is
  often correct. A gate that fires on legitimate behaviour gets bypassed, and then the *real*
  checks in that script get bypassed with it.
- **Do not raise `--heartbeat-max-age` as the fix for R1.** It converts a refusal into an
  unconditional permission to nudge mid-generation — a fail-open, and the exact harm C21/C35/C36
  were built to prevent. The fix is the *quiescence-conditioned* override, which preserves
  fail-closed on an unreadable pane.
- **Do not delete the `stuck-nudge-refused` advisory rows or quieten the retry loop.** The rows
  are the evidence trail; the defect is that nothing reads them, not that there are too many.

**My own most fail-open-prone proposal: R2.** A progress-log freshness check has three ways to
silently pass — git unreadable, `progress/` directory absent or month-rolled, and "no commits
found" from a scoping bug (wrong repo, wrong branch, wrong time window). Any of the three would
report clean on the exact day it is needed. R2 is only worth building if every one of them
**emits the defect instead of suppressing it**, and if it ships with a test that stubs each
failure and asserts a defect is filed. `scan_operator_receipts`
(`session_bus_coordinator.py:2046-2060`) is the in-repo pattern to copy: it returns an explicit
`*-skipped` row rather than an all-clear when it cannot evaluate.

**Runner-up: R4's history file.** If `.index-history.jsonl` is written by the same run that
computes the state and the write fails, the delta silently becomes "since the last successful
run" — an arbitrarily long window reported as if it were one tick. Every row must carry its own
`ts` and the delta must be reported **with its window** ("Δ since 2026-08-09"), never as a bare
number.
