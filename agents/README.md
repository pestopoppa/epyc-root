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

- Claude sessions, set the model and effort EXPLICITLY on every subagent dispatch (operator,
  2026-10-05):
  - `Haiku` — clerical, search, mechanical transforms, wrap-up docs/logs/handoff-edit writing.
  - `Sonnet` — code reading, routine fixes, tests, log audits.
  - `Opus` — hard design or hard debugging only.
  - `Fable` — only on explicit operator request; it is metered.
- Codex sessions: smallest capable `gpt-5.6-terra` or `gpt-5.6-luna` at the lowest adequate effort (CLAUDE.md § Codex Delegation Policy).
- Local stack roles route via the orchestrator's frozen registry, never hand-picked per task.

Rule: start with the cheapest model likely to succeed; a failed cheap attempt escalates **exactly
one tier** (Haiku -> Sonnet -> Opus), never straight to the top.

**Never use `subagent_type: "fork"` for cheap work.** A fork inherits the full parent context and
always runs on the parent's model, regardless of any `model` override passed to it — so forking
for a Haiku-shaped task still spends parent-model tokens. Fork only when the point is to share the
parent's context (open-ended research questions), never as a shortcut to spawn cheaply.

**Cheap tiers do not relax lock discipline.** Every brief that runs a CPU build, test, or server
still carries the region-lock / gpu-quiet clause (`agents/shared/OPERATING_CONSTRAINTS.md` → Inference and
Benchmarks), regardless of which model runs the subagent. There is no subagent GPU work during a
measurement window, cheap model or not.

### Delegation brief and report contract

- Briefs are tight and self-contained (the subagent gets no parent context except a fork); reports
  are word-capped.
- A subagent's result is a capped summary (~15 lines) plus a file path for any long output; the
  main reviews the summary and never reads a subagent's raw JSONL transcript.
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
