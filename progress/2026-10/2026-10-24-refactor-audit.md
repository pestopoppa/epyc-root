# 2026-10-24 — refactor audit (cloud session `refactor-audit`)

Session: claude.ai/code session_01C4SLLAQhop8AA9rJJusAYj. Ran in an ephemeral 4-CPU / 15 GiB cloud container
on fresh clones; nothing ran on the host. Started 2026-10-07; paused by the operator 2026-10-24.
Plan and queue: [`handoffs/active/refactoring-multirepo-2026-10.md`](../../handoffs/active/refactoring-multirepo-2026-10.md).
Evidence: [`research/refactor-audit-2026-10/`](../../research/refactor-audit-2026-10/README.md).

## Problem

The operator asked for an audit and refactor of epyc-orchestrator (including autopilot) and AutoKernel for best
practice, documentation, modularity, compute performance, debuggability, test quality, and code-size bloat.

## Root causes found

- **No feedback loop.** The orchestrator suite could not run anywhere but the production host (its conftest
  resolved the production kernel store and checked host RAM at import), there was no orchestrator CI, and the
  AutoKernel guards workflow was disabled after 168 red runs. Real failures accumulated unseen (AutoKernel: 476
  failed + 87 errors on 2026-10-07; about 42% of them real regressions).
- **Growth without deletion.** Insertions outran deletions about 10:1; AutoKernel regrew from a 3,450-LOC loop
  budget to 95,260 code lines; dormant planes (unified/standalone, discovery_*, release/) stayed importable.
- **Copy-paste drift.** Duplicated lanes and helpers had already diverged into real bugs (llama_server request
  lanes, escalation chains, journal shard readers, `_canonical` JSON forms, git wrappers).
- **Shared mutable state on the request path.** One LLMPrimitives per worker held per-request state, which
  reroutes requests under concurrency; model and REPL calls blocked the uvicorn event loop.

## Changes (all on `refactor/*` branches, rebased on origin/main 2026-10-24; none merged; none reviewed by a second agent)

| Repo | Branch | What |
|---|---|---|
| epyc-root | `refactor/containment-scanner` | scanner bypass fixes; degraded-mode regression fix (main since 84b0de13 allows `sudo mount` with no scanner); behaviour-change note for operator review |
| epyc-root | `refactor/refactoring-plan` | the handoff (58-item checklist), bug report, findings for 17 units, metrics, package definitions, implementer reports, baselines, this progress file |
| epyc-orchestrator | `refactor/hermetic-tests` | conftest stub kernel store + host-RAM fallback (no-ops on the host); `ORCHESTRATOR_PATHS_KERNEL_ROOT` |
| epyc-orchestrator | `refactor/request-path`, `refactor/config-registry`, `refactor/test-hazards`, `refactor/autopilot-gate`, `refactor/autopilot-loop`, `refactor/scripts-cleanup` | 52 commits across packages O1, O3, O6, O7, P1, P2 (finding ids in each commit subject) |
| epyc-inference-research | `refactor/autokernel-loop-bugs` | one WIP commit (C1-05); do not merge while the AutoKernel launch hold stands |

## Results

- 382 findings (orchestrator core 148, autopilot 113, AutoKernel 121; AutoKernel C4-C6 unverified after a usage limit).
- Orchestrator suite off the host: 20,815 collected; 20,496 passed, 127 failed, 21 errors at origin/main + hermetic-tests.
- 55 findings committed, 35 of them bugs; packages O3 and P2 complete; O1, O6, O7, P1 partial; the rest not started.
- Operator decisions: one batched evaluator era event; delete all three unreachable AutoKernel planes, staying
  current with main; add orchestrator CI and repair the AutoKernel workflow; full program, paced.
- Coordination with workspace-58 (the host session): its live-path and file boundaries adopted; it checked all
  refactor branches against live jobs and found no collision.

## Deferred (with blockers)

- Every pushed branch needs an adversarial review before merge (none ran: the operator paused the session).
- Index row for the handoff: prepared in the handoff, not applied (index files belong to workspace-58).
- Wiki compilation sweep and index pruning: not run (workspace-58 owns `wiki/source_manifest.json` and the index files).
- `orchestrator_stack.py` restructuring (A5-10/16/17/19): live path on the host. C5-05: needs an operator decision.
