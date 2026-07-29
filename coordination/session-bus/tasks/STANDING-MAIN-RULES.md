# STANDING MAIN RULES — all mains, all tasks

**If you read nothing else:** you hold a standing **GOAL**, not a task list — derive your own next
item from it and never sit idle; report to `coordinator-agent` on TWO conditions (out of work, or
needing an operator decision), and keep your heartbeat honest — `idle` when awaiting dispatch,
`working` otherwise, refreshed at every task boundary.

This is the shared contract behind every per-task brief. Your brief carries only what is specific to
your task; everything below applies regardless of what you were dispatched to do. **Your standing
goal lives in [`MAIN-GOALS.md`](MAIN-GOALS.md)** — read your own section there before your brief,
because the brief is one instance of the goal and the goal is what survives it.

---

## 1. The roster — use YOUR id verbatim

Roster ids are **model-agnostic** as of 2026-07-29, so a main can be re-spawned on a different backend
— including a local model — without its identity changing. The id is what every queue row, cursor,
inbox and outbox is keyed on.

| id | owns |
|---|---|
| `inference` | inference tasks; **currently the stack owner** |
| `auditor` | miscellaneous work; the DEFAULT main for auditing other mains' completed work |
| `mainA` `mainB` `mainC` `mainD` | whatever handoff / backlog work is dispatched to them |
| `coordinator-agent` | cross-main sequencing; **the only role the operator talks to** |

Every bus command takes `--agent <your-id>`. Use your id exactly as spelled above — the CLI derives the
files you are permitted to write from that string. Older briefs still name the pre-rename ids (`codex`,
`fable-auditor`, `claude-main`, `claude-gpu-lane`); that is history, read it as such.

Lanes come from your roster row in `coordination/session-bus/config.yaml` — that row, not this file, is
the authority on which lanes you may take.

## 2. Never sit idle

When you finish an item, **immediately take the next one** from your owning handoff or from
`queue.jsonl`. Do not wait to be told, do not stop to report and then wait for a reply.

**Reason:** an idle main with an empty queue is a coordination failure, not a resting state. The
operator's target is 1000+ tasks closed per week against 293 last week — so the binding constraint on
the fleet is **idle mains**, not throughput per main. A main that stops to wait costs more than a main
that picks a slightly suboptimal next item.

"Take the next item immediately" does **not** mean "skip the bookkeeping". Flipping the checkbox,
appending the progress entry and persisting the work (§8) are part of *finishing* an item — an item
whose checkbox and progress entry are missing is not finished, and moving on from it just makes the
loss permanent.

## 3. Goal-based dispatch — you hold a GOAL, not a list

**A list runs out. A goal does not.** This section is the mechanism that makes §2 achievable: no main
can "never sit idle" if what it was handed has a last line.

Your dispatch is a **standing GOAL**, written down in [`MAIN-GOALS.md`](MAIN-GOALS.md) — one section
per roster main, with what "good" looks like, your owning handoffs, your lane and your escalation
list. Task briefs, `queue.jsonl` rows and backlog tables are **instances** of that goal, never the
goal itself. The goal outlives every one of them, and finishing one does not retire it.

### You own the decomposition

Selecting, ordering, re-scoping, splitting, deferring and **abandoning** individual tasks in service
of your goal is your judgement to exercise, **without asking**. Choosing what to work on next IS the
job — not an interruption of it, not a thing to clear with the coordinator first. A main that waits
to be told which item to take next has handed its autonomy back and re-created the list it was given.

You may also create work that nobody dispatched: if the goal needs a thing and no task line exists
for it, write the `- [ ]` line yourself (§7) and do it.

### A goal is never "done" the way a list is done

When the obvious work under your goal is exhausted, you have not finished — you **widen**:

1. **Re-read your owning handoffs end to end**, not only the section you were working in.
2. **Re-derive what the goal still needs**: unflipped boxes, decisions recorded but never
   implemented, findings filed but never actioned, claims nobody verified, work that fell out of an
   index and is reachable from no navigation path.
3. **Pick the highest-value remaining thing and start it.** Highest-value, not easiest-to-find.

**Running out of ideas is a signal to look harder, not a signal to stop.** "Nothing obvious left" is
a statement about how far you looked, not about the state of the work.

### What still MUST come to the coordinator — the exhaustive list

Autonomy needs a crisp edge, so here is the whole edge. Escalate **exactly** these, and decide
everything else yourself:

**a. Anything needing an operator decision or signature.** A ratification token, a choice among
alternatives with real tradeoffs, an authorisation you do not hold. Shape it per §4 — options,
tradeoffs, your recommendation — and route it; do not ask the operator directly.

**b. Cross-main conflicts** — above all, **two mains needing the same files or the same host
resource**. You can see your own lane; you cannot see the other five, and the coordinator exists
precisely because nobody else holds that view.

**c. A blocker you cannot clear yourself** — a dependency owned by another main, a tool broken
outside your scope, a precondition nobody has met.

**d. Work that would cross a trust boundary** — signing, instrument-era rows, `human_only_paths.yaml`,
another owner's checkbox. Human-amendment-only means the human, not you and not the coordinator.

**e. Discovering that the goal itself is wrong** or has been overtaken by events (see below).

Everything else — what to do next, in what order, at what depth, whether to abandon a line of attack
that is not paying — is yours. If an item is not on that list, you do not need permission for it.

### Report progress against the GOAL, not against a checklist

A status report is not a list of ticked boxes. Say:

- **what moved** — the goal is closer in this specific way;
- **what it cost** — wall clock, host time, tokens, whatever was scarce;
- **what is now known that was not before** — including negative results, which are findings;
- **what you intend next**, and why that and not something else.

**Reason:** intent is the only part the coordinator can act on early. A report that lists only
completed items lets the coordinator discover drift at the end of a campaign, when redirecting is
expensive; a report that states the next intended move lets it redirect for the cost of one message.

### You may propose a revision to your own goal

If your evidence says the goal is wrong, mis-scoped, already achieved, or overtaken by events,
**say so**. That is escalation class (e), and it is **high-value work, not insubordination** — you
hold context the coordinator does not, and a goal nobody challenges outlives its own usefulness.
Propose the revision with the evidence that prompted it; keep executing the current goal until it is
answered, unless continuing would waste something irrecoverable.

### Reason, and the incident

A **list-driven** main stops the moment the list ends. It has, correctly, completed its instruction —
so it sits at its prompt with nothing to do, and because its heartbeat still reads `working` (§5) it
is simultaneously **unreachable**: `tmux_adapter.py nudge` refuses on that state, and the session
cannot clear the flag itself because clearing it would require being told to. Completed-and-silent
is indistinguishable from working-and-busy from the outside.

**2026-07-29:** mains repeatedly went idle this way and the **operator** — not the coordinator — kept
catching it, typing by hand into panes that were finished but could not say so. Root cause: mains
were dispatched a LIST, so they stopped when the list was done. A main that had completed
"TOP-40 rows 14-26" had nothing left to derive from its instruction.

A **goal-driven** main never reaches that state: there is always a next action derivable from the
goal itself, so the only things it ever needs the coordinator for are the five above.

## 4. Report on TWO conditions, not one

Send a report to `coordinator-agent` when:

1. **You run dry** — no assignable work left in your handoff or the queue; and
2. **You need OPERATOR input** — a decision you cannot resolve autonomously.

**Reason:** a main blocked on a decision is neither idle nor exhausted. "Report when you're dry" alone
leaves that main sitting with nothing it is allowed to say, which is the exact deadlock this rule
exists to prevent.

Escalations go to `coordinator-agent` with `action_required: true`. The coordinator turns your
escalation into a decision package — 2–4 concrete options with tradeoffs (cost / risk / time / quality
/ reversibility), a recommendation, and the default outcome if nobody chooses — and puts that to the
operator.

- **Do NOT ask the operator directly.**
- **Do NOT guess** and proceed as if the decision were made.
- **DO state your own recommendation and your reasoning** in the escalation. You hold the context the
  coordinator does not; an escalation without your recommendation forces the coordinator to
  reconstruct what you already know.

## 5. Heartbeat polarity

Write `state: idle` when you are **genuinely awaiting dispatch**, `state: working` otherwise. Refresh at
**every** task boundary — not once at startup.

```bash
python3 scripts/coordination/session_bus.py append --agent <your-id> \
  --target heartbeat --json '{"state":"working","task_id":"<current>"}'
```

**Reason, concretely:** a main that is idling but still advertises `working` **cannot be nudged at
all**. `tmux_adapter.py nudge` refuses on heartbeat *state*; `--heartbeat-max-age` does not rescue it,
because the refusal keys on state and not on age; and the session cannot clear the flag itself, because
clearing it would require being told to — which is precisely what the guard is refusing to do. The
refusal and the silence reinforce each other into a deadlock that only a hand relay from the operator
breaks. **This happened twice on 2026-07-29.** A heartbeat written once is a birth certificate, not a
liveness signal.

## 6. Leverage subagents hard

Fan independent work out to subagents **in parallel** instead of doing it serially on your main thread.

- Match subagent **model and effort** to the task — smallest capable model, lowest adequate effort.
- Treat every subagent result as **PROPOSED work**: review its evidence and its diffs, and run the
  appropriate validation, before accepting it.

**Reason:** your main thread's scarce resource is attention to task boundaries — deciding what is next,
integrating, reporting. Work that does not need that attention should not consume it.

## 7. Checkbox discipline

Any edit that records completed work flips `- [ ]` → `- [x]` with an inline check-date
(`✅ 2026-07-29`). Work discovered mid-flight gets its **own** `- [ ]` line rather than being folded
silently into an existing one.

**Reason:** the handoff dashboard counts **checkbox state only**. Prose status updates are invisible to
it. An unflipped box is, from the operator's view, work that did not happen.

## 8. Persist progress at every checkpoint and task boundary

Not only at session end.

- **Progress log.** Append to `progress/YYYY-MM/YYYY-MM-DD.md` after significant work. Convert relative
  dates to absolute ones — "yesterday" is unreadable to whoever picks this up next week.
- **Owning handoff.** Update it **as gates land**: flip the checkbox with an inline check-date, and add
  a `- [ ]` line for work discovered mid-flight (§7). Never defer dashboard truth to the next wrap-up —
  a handoff that is accurate only at session end is inaccurate for most of the session.
- **Agent audit log.** `source scripts/utils/agent_log.sh`, then `agent_session_start` once and
  `agent_task_start` / `agent_task_end` around each unit of work, per `CLAUDE.md` → *Agent Logging*.
- **Wrap up at every MAJOR checkpoint** — a phase boundary or a completed campaign, not every task. Use
  the `/wrap-up` skill, and **dispatch it to a subagent on your behalf** rather than stalling your own
  main thread or letting the record rot while you keep working. A checkpoint that was not wrapped is,
  from the operator's view, work that did not happen.
- **Commit AND push** at boundaries. Work that exists only in a working tree is invisible to every
  other main and dies with the session. Fetch before committing. **Commit with an explicit
  pathspec:**

  ```bash
  git commit -F - -- path/one path/two
  ```

  Never `git add -A`, never `git add` a shared file wholesale, and **never a bare `git commit` after
  `git add`** — not even chained with `&&`. **Reason:** these trees are shared by parallel sessions
  that stage into the index *continuously*, and a bare commit reads the WHOLE index, so anything
  staged in the gap rides into your commit. `git add … && git commit` is still two steps; chaining
  narrows the window, it does not remove it. A pathspec-limited commit takes working-tree content
  for exactly the named paths and never reads the index for anything else — there is no window
  because there is no read.

  *Corrected 2026-07-29 by `auditor`. This bullet previously said "stage explicit paths and commit in
  ONE step", which is not achievable with `git add` + `git commit` and was being read as an
  endorsement of the chained form. Measured that day: `auditor` chained them and a parallel session's
  completed checkbox flip rode in; after `reset --soft` and unstaging, a **different** session's file
  rode into the very next attempt, ~1 minute later. `mainA` independently confirmed it had been using
  the chained form and audited 14 commits across three repos (all clean — lucky, not careful). Do not
  put the verification (`git diff --cached --name-only`) in the same `&&` chain as the commit: you
  then read it only after the commit has already run.*
- **Incremental persistence on long runs.** Persist per unit — per question, per cell — because every
  persisted unit is also a **drain point**. That is what makes a run resumable and pausable instead of
  all-or-nothing.

**Reason, plainly:** a main can be closed, cleared, or killed at any moment, including by a reboot.
Anything not persisted at the last boundary is gone, and the next session inherits nothing.

## 9. Bus discipline

At every task boundary:

```bash
python3 scripts/coordination/session_bus.py drain --agent <your-id> --triage
```

- **`--triage` is not optional.** It prints the standing queue of messages routed to you — in full,
  cursor-independent, never truncated. Draining alone cannot consume that queue.
- **Write only your own** `outbox/<your-id>.jsonl`, `heartbeats/<your-id>.json`,
  `cursors/<your-id>.json`. `queue.jsonl` and every `inbox/*` belong to the coordinator-daemon. No file
  ever has two writers.
- **Route intent as STRUCTURAL fields** — `needs_routing_to` (array of roster ids) and
  `action_required` (boolean). Never as "FOR <AGENT>" prose. **Reason:** prose routing is invisible to
  tools and gets truncated away; two routed messages were missed exactly this way on 2026-07-29.
- **Clear a triage item by disposition**, written to your own outbox with `corr_id` set to the message
  id: any substantive kind, or `kind: ack` with `payload.disposition` in
  `done | declined | handed-off | superseded`. A bare ack is receipt, not action — it clears a
  reach-only message but leaves an `action_required` one listed as acked-awaiting-action.
- **Keep payloads terse and item-specific.** A byte-identical payload repeated across N `corr_id`s is
  bus noise by construction (defect C23).

## 10. Lanes and contention

- **Respect your rostered lanes.**
- **`inference` owns the stack and the serving lane.** Only the session that owns the inference may
  reload the orchestrator API or the stack, at a moment it chooses — API-only reloads included. If you
  need a reload, **route the request to `coordinator-agent`**; never run one yourself, and never let one
  land around another session's protected run. **Reason:** a reload forced from outside is preemption of
  running inference by another name (fabric axiom 4) — on 2026-07-28 two external API-only reloads
  crossed in-flight ordinals of a protected collection and forced them to be regenerated.
- **ACQUIRE region claims via `region-lock`** (`epyc-orchestrator/scripts/region-lock`). Never infer
  that a region is free by observing it — observation is TOCTOU; only holding the lock excludes.
- **Report measured contention as DATA, not as a request for permission.** Co-residency is a scheduling
  question for the coordinator; concurrency alone is never grounds for a human gate.

## 11. Measurement

- A decision-gating number is `(metric, protocol-id, n/reps, date, attestation ref)`. A number without
  a protocol citation is an **observation** — fine for hypotheses, never able to gate a decision.
- **Deterministic replay before regeneration.** If a result is obtainable by deterministically
  rescoring or transforming saved outputs, do that instead of re-running inference. Rebaseline only the
  axis that changed.
- Benchmarks run **only** via the codified recipes (`bench_canonical.sh` / `canonical_recipe.py`), and
  you **import the recipe constants** rather than retyping remembered values.
- **Trust boundaries are human-only.** Never sign, never flip a checkbox you do not own, never edit
  `human_only_paths.yaml`. The coordinator sequences and presents; neither it nor you signs.

## 12. Throughput over polish — and what makes that safe

Prefer **finishing whole items** to polishing partial ones.

This is explicitly balanced by the `auditor` main periodically reviewing completed work. "Ship it and
move on" is therefore the **intended** behaviour, not a workaround — the review pass is the safety net
that makes the bias correct rather than reckless.

It is not a licence to leave work broken:

- do not skip tests;
- do not skip the checkbox (§7);
- do not leave a handoff mid-edit.

---

## Where the sources appear to conflict

Flagged rather than silently resolved. If either matters to your task, raise it with
`coordinator-agent` instead of picking a side on your own.

1. **Who delivers a decision package.** `CLAUDE.md` → *Operator Decision Requests* and
   `agents/shared/OPERATING_CONSTRAINTS.md` → *Operator Decision Requests* both say a Claude Code
   session delivers its decision package to the operator directly via AskUserQuestion. §4 above says a
   main escalates to `coordinator-agent`, which is the only role that talks to the operator. The
   consistent reading is that the required *shape* (options + tradeoffs + recommendation + default) is
   unchanged and the *channel* for a rostered main is the coordinator — but the two texts are not
   literally reconciled, and only `coordinator-agent` can rule on it. Note the standing exception in
   both sources: a pure factual gap (a missing credential, an ambiguous file reference) may be asked
   directly; this contract governs choices among alternatives, not fact retrieval.

2. **"Never sit idle" vs. "close the session".** §2 and `BUS_PROTOCOL.md` say an idle main with an
   empty queue is a coordination failure; the session-lifecycle table in
   `OPERATING_CONSTRAINTS.md` → *Session Lifecycle* says that when **no further task can be assigned**,
   the correct action is to **close the session**, not to idle. The sources do not say who determines
   that nothing is assignable. Report dry (§4) and let the coordinator make that call rather than
   closing yourself. Note also §3: under goal-based dispatch "dry" is a much rarer state than it
   looks, because a goal always admits a next derivable action — reaching for it is the first move,
   and reporting dry is what you do after widening has genuinely failed.
