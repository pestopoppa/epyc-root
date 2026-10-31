# Agent System Map

This directory is organized for agent legibility and low drift.

## Start Here

1. Read `agents/AGENT_INSTRUCTIONS.md` for the global execution contract.
2. Read `agents/shared/OPERATING_CONSTRAINTS.md` for safety and environment constraints.
3. Read `agents/shared/MEASUREMENT_POLICY.md` if the task produces or consumes performance/quality numbers.
4. Read `agents/shared/ENGINEERING_STANDARDS.md` for coding invariants.
5. Read `agents/shared/WORKFLOWS.md` for common operating procedures.
6. Read workflow depth docs in `docs/guides/agent-workflows/`.
7. Open the role file only if your session holds that role.

## Roles

| Role | File | Primary Use |
|---|---|---|
| Coordinator Agent | `agents/coordinator-agent.md` | Cross-main sequencing on the session bus; the only role with cross-main authority |
| Inference Main | `agents/inference-main.md` | Inference compute ownership, leases, and persistent-idle recovery (roster id `inference`; `role: inference-main` after the 2026-08-16 merge — see the note below) |
| Auditor | `agents/auditor-main.md` | The review CONTRACT carried out under the `auditor` identity. **P3-7 retired the interactive auditor SESSION** (roster `auditor` is `role: service`); the reviewer function now runs as per-packet headless invocations, so read this file as a contract, not as a session to route to |

The roster is the authority on who holds which role: `coordination/session-bus/config.yaml`
assigns every agent a roster id and one role from a closed set — `main`, `coordinator-agent`,
`reviewer`, `retired`, `service`. Work reaches an agent as a queue row addressed to a roster id,
with a lane and a typed brief. There is no persona-based routing.

> **MERGE NOTE (2026-08-16):** the other merge side widened that set with `inference-main` (live in
> `config.yaml`, read by `session_bus_coordinator.py`) and `auditor-main` (on the contested
> `auditor` row). The "no persona-based routing" rule stands; the enumeration above needs
> reconciling once the `auditor` roster row is adjudicated.

**Archived 2026-08-16**: the eight task-based persona files (Lead Developer, Research Engineer,
Benchmark Analyst, Research Writer, Build Engineer, Model Engineer, Sysadmin, Safety Reviewer)
moved to `agents/archived/` under the Loop-Owned Fleet doctrine collapse (P1-5). They were a
dormant layer that no roster, dispatch path, hook, or validator consumed. Read
`agents/archived/README.md` before citing or restoring any of them.

## Pool Workers

Added 2026-08-16. Alongside the interactive sessions the roster addresses, work also reaches a
**pool-worker tier**: one roster identity, `workerpool` (`role: main`, `endpoint:
"exec:worker_runner"`), which the daemon *exec's fresh for each assignment* instead of a session it
holds a conversation with. The program behind that endpoint is
`scripts/coordination/worker_runner.py`; the pool's bounds (harness, concurrency, token ceiling,
lease grace) are data in `coordination/session-bus/config.yaml` under `worker_pool:`, and the pool
is executable only while `worker_pool.enabled` is true.

A pool worker is a process, not a session:

- **One per assignment.** The runner starts on a daemon tick, does the batch, and exits. Nothing
  persists between assignments.
- **Works in a pool worktree.** `/mnt/raid0/llm/worktrees/pool/lane0..lane3`, one worker per lane
  (enforced by a `.worker.lock` lockfile). Never an interactive main's lane worktree — a
  commit-per-unit or salvage commit in an occupied tree is the documented commit-sweep hazard.
- **Delivers commits, signals by file.** The deliverable is pathspec-limited commits in the lane
  worktree, one per completed unit. The typed report (`worker_report.v1`) is the *only* completion
  signal and carries pointers, not the diff — a headless auditor re-derives the change from git
  independently. Denied tool calls are recorded in the report rather than passing silently.
- **Fans out its own subagents**, 3–5 concurrent, like any main (D0).

Its tmux pane is **visible and human-authoritative** (D8): the operator may watch it, steer it, and
answer permission prompts by hand. The machine never types into a pane and never makes a decision
from pane text — it may only capture scrollback as evidence for a human to triage.

Design of record: `docs/design/loop-owned-fleet.html` — *The pivot: pool workers in visible panes*
(`#pivot`), *worker_runner: per-assignment lifecycle* (`#d-runner`), and *Ratified decisions*
(`#decisions`, D0/D1/D2/D6/D8). Task-level state and gates:
`handoffs/active/loop-owned-fleet-implementation.md` (Phase 2). Consult those rather
than this section for the design rationale.

## Model Routing (Task-Based)

Measured numbers in this section come from FM-7, the delegation accounting over every Claude Code
journal and Codex rollout on this host from 2026-09-24 to 2026-10-31 (5,829 transcripts):
`data/fanout_timing/delegation_accounting_report.v1.json`, produced by
`python3 scripts/coordination/fanout_timing.py delegation-accounting` (commit `8a1ca9227`). Cited
below as *(FM-7)*; "our arithmetic" means a product or ratio of FM-7 fields.

- Claude sessions, set the model and effort EXPLICITLY on every subagent dispatch (operator,
  2026-10-05), or dispatch a project subagent type from `.claude/agents/` (`explorer`, `runner`,
  `clerk`) whose frontmatter pins both (intake-2540#01, intake-2540#03). The main-thread hook
  `scripts/hooks/check_agent_dispatch.py` logs, in warn mode, every dispatch that does neither
  (FM-8; hooks see `agent_id` inside subagents, so it acts on the main thread only, intake-2540#00):
  - `Haiku` — clerical, search, mechanical transforms, wrap-up docs/logs/handoff-edit writing. A
    Haiku reader **points, it does not conclude**: it returns `path:start-end` citations with at
    most a short reason each, never a summary the main acts on (`explorer`; intake-2537#04,
    intake-2535#03).
  - `Sonnet` — code reading, routine fixes, tests, log audits, and execution/test-running
    subagents (`runner`). Under an Opus main, a Sonnet execution subagent matched an Opus one
    within noise (intake-2538#record, reported results).
  - `Opus` — hard design or hard debugging only, started at `medium` effort (see *Effort before
    tier*).
  - `Fable` — only on explicit operator request; it is metered.
- Codex sessions: see *Codex sub-agent routing* below.
- Local stack roles route via the orchestrator's frozen registry, never hand-picked per task.

**Effort is part of the cheapest-capable choice (operator, 2026-10-05; reiterated 2026-10-20 and
2026-10-21).** Haiku at lower effort for mechanical or self-checking work; Sonnet for engineering,
judgment and research dives. The main thread dispatches, reviews submitted work and decides; it
does no hands-on execution (`agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent
Fan-Out*). Operator, 2026-10-21: *"when you dispatch tasks to subagents, you should use the
cheapest model/effort capable of executing the task. Reserve the main thread for reviewing task
work submissions so that everythign checks out."*

**Effort before tier.** Start with the cheapest model likely to succeed, at the lowest effort
likely to succeed. When a failure is checkable (tests, a validator, a reproducible error), first
re-run the same tier at higher effort, then escalate **exactly one tier** (Haiku -> Sonnet -> Opus),
never straight to the top. The source rule is to sweep effort on the current model before adding a
second one (intake-2541#05); running low and re-running only the failures at high cost about 40%
less than all-high at the same pass rate, and it needs a real failure signal (intake-2541#record,
reported results). On a single dependent chain that fits one context, lower the effort before you
lower the tier: Haiku subagents under an Opus main cost about 4 pp of pass rate for 32% less, the
same trade a lower effort gives (intake-2541#03), and delegating to cheaper workers saved money
only for routine work with a long cost tail or work larger than one context (intake-2541#02).
Today the order is reversed in practice: over the last 30 days Claude mains re-dispatched 5 of
1,343 cheap dispatches at a higher tier and none at higher effort, and 82% of Opus subagents
(676 of 823) ran at `high` (FM-7: `claude.redispatch`, `claude.subagents_by_tier.opus.effort_mix`).

**Where the tokens actually go (FM-7: `spend_share`, `subagents_by_tier`).** Shares are of all
tokens in that harness, main threads included.

| Harness | Main threads | Subagents, by tier (agents; mean requests per agent) |
|---|---|---|
| Claude (29.2 G tokens) | 39.3% | Opus 35.9% (823; 69) · Sonnet 23.6% (1,191; 37) · Haiku 0.65% (160; 15) · Fable 0.60% (52; 23) |
| Codex (69.4 G tokens) | 32.0% | terra 31.2% (343; 310) · luna 21.7% (435; 259) · sol 15.0% (559; 129) · astra 0.06% (9; 44) |

- **Claude: the lever is Opus subagents, not more Haiku.** Haiku already holds 0.65% of spend, so
  moving more clerical work to it can save at most that order of tokens. Opus subagents hold 35.9%
  at 12.7 M tokens each (our arithmetic): send execution and routine work to Sonnet, and run Opus
  at `medium` unless a checkable failure says otherwise. The other lever is main-thread turns: a
  main request re-reads the whole main context, 495 k tokens on average (our arithmetic,
  `claude.main_by_tier.opus` total input ÷ requests).
- **Codex: the lever is sub-agent length, not tier.** The cheapest tier, luna, holds 21.7% of all
  Codex tokens because its sub-agents average 259 requests each; terra sub-agents average 310
  requests and 63 M tokens each (our arithmetic). Bound each sub-agent to one unit of work with a
  stated stop condition before reconsidering its tier; 47% of luna sub-agents (206 of 435) ran at
  `high` effort (`codex.subagents_by_tier.luna.effort_mix`).

**When a subagent is not worth its fixed load (arithmetic).** Every subagent starts with a fixed
load F before it does any work: Claude median 49.9 k tokens (p90 53.3 k), flat across tiers (Haiku
49.4 k, Sonnet 50.6 k, Opus 47.5 k), so a cheaper tier lowers the price per token, not the load;
Codex median 21.8 k (FM-7: `fixed_overhead_all_subagents`, `first_request_input`). Every earlier
turn is resent on each request (intake-2541#00), so a subagent of k requests carries at least
F × k tokens. F × mean requests is about 61% of a mean Haiku subagent's tokens, 33% of a Sonnet
one's and 26% of an Opus one's (our arithmetic): small subagents are mostly fixed load.

- Cost of delegating: at least one main request for the dispatch (a second for a background
  result), plus F × k in the subagent. The smallest useful subagent (one tool call, read the result, answer) is
  k ≈ 3: **at least 150 k tokens on Claude and 65 k on Codex** before its first useful byte.
- Cost of doing it on the main: the output N stays in main context and is resent on each of the R
  main requests left before the next compaction, about N × R.
- So delegate only when it removes main requests or keeps N × R above F × k. Work that fits in
  **one main request** with known targets and output under about **5 k tokens** (about 20 k
  characters) is cheaper inline whenever 30 or fewer main requests remain (5 k × 30 = 150 k).
  Which such work the main may do itself is set by the main-thread carve-out in
  `agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*; the rest of that size
  class goes to one subagent, never several.
- Do not split one batch of lookups across several subagents to reach a width: each extra
  subagent adds at least F × 3. Give the batch to one subagent, which can issue the lookups in one
  parallel request.
- Above that size delegation wins on tokens: one avoided main request (about 495 k) pays for about
  ten Claude subagent requests at F (our arithmetic; token counts, not price).

**Never use `subagent_type: "fork"` for cheap work.** A fork inherits the full parent context and
always runs on the parent's model, regardless of any `model` override passed to it — so forking
for a Haiku-shaped task still spends parent-model tokens. Fork only when the point is to share the
parent's context (open-ended research questions), never as a shortcut to spawn cheaply.

**Cheap tiers do not relax lock discipline.** Every brief that runs a CPU build, test, or server
still carries the region-lock / gpu-quiet clause (`agents/shared/OPERATING_CONSTRAINTS.md` → Inference and
Benchmarks), regardless of which model runs the subagent. There is no subagent GPU work during a
measurement window, cheap model or not.

### Codex sub-agent routing

Codex sessions, the Codex worker sessions included, delegate under the same rules as Claude
sessions above; the model ids and the Codex-specific pins (wrap-up tier, Auditor floor, compute
calendar) are in `agents/shared/OPERATING_CONSTRAINTS.md` → *Codex Delegation & Long-Horizon
Throughput*. The tier ladder below is the order FM-7 ranks Codex tiers in (`CODEX_TIERS` in
`scripts/coordination/delegation_accounting.py`: luna 1, terra 2, sol 3, astra 4).

- Set the model and the reasoning effort explicitly on every sub-agent spawn:
  - `luna` — clerical, search, mechanical transforms, wrap-up writing. A luna reader points, it
    does not conclude: it returns `path:start-end` citations, never a summary the main acts on
    (intake-2537#04, intake-2535#03).
  - `terra` — code reading, implementation, routine fixes, tests, execution.
  - `sol` — hard design or hard debugging only, or after a checkable terra failure that a
    higher-effort terra re-run did not fix.
  - `astra` — only on explicit operator request.
- **Effort before tier**, exactly as above: on a checkable failure re-run the same tier at higher
  effort (`low` → `medium` → `high` → `xhigh`), then escalate one tier (luna → terra → sol)
  (intake-2541#05). Codex mains already do this more than Claude mains do: 3 effort-only re-runs
  and 1 higher-tier re-dispatch out of 788 cheap dispatches in the last 30 days
  (FM-7: `codex.redispatch.last_30_days`).
- **Bound the length.** One unit of work per sub-agent, with a stop condition in the brief; Codex
  spend follows the request count (luna 259 and terra 310 mean requests per sub-agent, see the
  table above), and the 21.8 k fixed load is resent on every one of those requests.
- **Not worth a sub-agent:** the same arithmetic with F = 21.8 k — at least 65 k tokens for a
  three-request sub-agent, so a known-target lookup that fits in one main request stays inline.
  A Codex main request re-reads 250 k tokens on average on terra (our arithmetic,
  `codex.main_and_exec_by_tier.terra`).
- The brief, return and accounting contracts below bind Codex sub-agents unchanged. Codex rollouts
  record no structured file-read event, so a Codex claim about read volume uses the tool-output
  proxy and says so (FM-7: `codex.A_not_computable`).

### Delegation brief and report contract

Binds Claude subagents and Codex sub-agents alike.

- Briefs are tight and self-contained (the subagent gets no parent context except a fork); reports
  are word-capped.
- Every brief names four things: the objective, the output format, the tools and sources to use,
  and the boundaries of the task (intake-1113#record), on top of the lane, scratch and region-lock
  clauses in `agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*.
- A subagent's result is a capped summary (~15 lines) plus a file path for any long output; the
  main reviews the summary and never reads a subagent's raw JSONL transcript.
- Execution and test-running subagents return one block per command: command, exit status,
  pass/fail counts, key error excerpt (intake-2538#00). Debugging subagents return Question /
  Answer / Evidence / Location and make no edits; the hypothesis and the fix stay with the main
  (intake-2543#02).
- Anything the main will edit from comes back as `path:start-end` and is re-read by the main with
  offset/limit. Line numbers inside a subagent's prose are not edit input: summaries carry no
  reliable line numbers (intake-2535#03), and broad citations make the main redo the search
  (intake-2537#04).
- **A claim that a delegation pattern saves tokens reports main, subagent and total tokens plus an
  outcome check.** Main-context tokens alone are not a saving: published explorer and execution
  results count the main agent only (intake-2537#02, intake-2538#02), and adding a debug subagent
  raised total tokens in every configuration tested (intake-2543#03). On our fleet
  subagents hold 60.7% of Claude tokens and 68.0% of Codex tokens (FM-7: `spend_share`), so a
  main-only number misses most of the spend. Measure with
  `python3 scripts/coordination/fanout_timing.py delegation-accounting` over a frozen
  `delegation-manifest`.
- **Harness caveat**: some subagent types/harness configurations refuse a Write of a report file
  ("subagents should return findings as text, not write report files"). Word the brief so it works
  either way — ask for the deliverable as returned text (the main persists it to a file itself if
  a durable copy is needed) or as a non-report artifact (a patch, a diff, a code file) rather than
  assuming a report-file Write will succeed.

Role launch profiles are recommendations, not identity. In particular, the Auditor and Inference
Main profiles in their role files may be changed by the operator at any time without a warning,
validation failure, lease action, or reprovisioning.

## Design Principles

- Keep role files focused on role-specific behavior.
- Keep cross-cutting policy in `agents/shared/`.
- Keep durable project knowledge in `docs/`, not in role prompts.
- Prefer mechanical checks over prose-only reminders.

## Multi-Repo Context

This project spans four repositories. Agent files here in `epyc-root` provide cross-repo governance.
Orchestrator code lives in `epyc-orchestrator`, research in `epyc-inference-research`, llama.cpp in `epyc-llama`.
See `.claude/dependency-map.json` for coupling edges.

## Migration Note

- Legacy long-form role playbooks were intentionally split.
- Operational detail moved to `docs/guides/agent-workflows/`.
- Schema and reference consistency is enforced via `scripts/validate/` and hooks in `scripts/hooks/` (in this repo).
- Full design rationale: `docs/reference/agent-config/AGENT_FILE_LOGIC.md`.
