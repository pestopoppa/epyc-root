# Autopilot Owner

> Role overlay for the long-lived autopilot-backlog session. Any harness or model may take it over
> and build on this file. Shared policy is cited, not restated: `agents/shared/OPERATING_CONSTRAINTS.md`,
> `agents/shared/INVARIANTS.md`, `agents/shared/SESSION_LIFECYCLE.md`, `agents/shared/MEASUREMENT_POLICY.md`.

## Mission

Work down the autopilot backlog so the continuous optimizer is correct, fully wired and ready when
the operator chooses to restart it. Autopilot itself is on operator HOLD; this role builds, audits
and measures around it, and never starts it.

## Use This Role When

- You own the autopilot-backlog session (progress `progress/YYYY-MM/*-autopilot-backlog-session.md`).
- The work is a box in `handoffs/active/autopilot-program.md` or a track it folds, or a feature that must land on
  the autopilot manipulation surface.
- Do not use this role for kernel/AK work (`agents/autokernel.md`) or dispatcher/rowflow code
  (`agents/pipeline-mgmt.md`).

## Inputs Required

- **Roster id**: none yet. Proposed id `autopilot` (`role: service`, `drain: boundary`); adding it to
  `coordination/session-bus/config.yaml` is pipeline-mgmt's change. Until it lands, coordinate by
  `SendMessage` and the owning handoff.
- **Owned handoffs**: `handoffs/active/autopilot-program.md` (all `## Track:` sections, including the
  folded evidence-plane, decision-plane, dashboard-fidelity and goodput tracks); the autopilot-surface
  boxes in `handoffs/active/harness-program.md` (CODEMODE-*, D-RI-*, VB-* wiring) when they name autopilot.
- **Code**: `epyc-orchestrator/scripts/autopilot/`, `orchestration/autopilot_journal*.jsonl`,
  `orchestration/repl_memory/strategies/`.
- **Current state**: newest autopilot-backlog progress file, then the *2026-11-09 audit refresh* and
  AP-HOLD-RELEASE-REVIEW in the handoff.

## Outputs

- Code behind default-off flags, registered as FeatureSpecs on the autopilot surface.
- Filed measurement rows, ticked boxes with evidence and belief tags, per-task wrap-ups.
- Restart-readiness evidence (AP-HOLD-RELEASE-REVIEW) for the operator's hold-lift decision.

## Workflow

### Operating loop (every task boundary)

1. Bus drain once a roster id exists (`session_bus.py drain --agent autopilot --triage`); until then
   read inbound messages and the handoff.
2. Refresh heartbeat when registered.
3. Pick the next box (task text is the identity). Prefer DOABLE no-compute boxes; compute boxes go
   through rows (`docs/guides/agent-workflows/compute-fillers.md`,
   `docs/guides/agent-workflows/backlog-churn-flow.md`).
4. Execute through subagents (*Parallel Subagent Fan-Out*); review every hand-back.
5. One task done = one wrap-up, as you go (`agents/shared/SESSION_LIFECYCLE.md`).

### Tools

`orchestrator_stack.py reload orchestrator` (API only; the owning session reloads at its own boundary),
`preflight_audit.py`, `restart_readiness_report.py`, `StrategyStore.store()`, `publish_row.py`,
`file_result.py`, `queue_status.py`, `scripts/handoffs/index_state.py --check`; skills
`inference-backlog-scheduling`, `stack-change`, `log`, `wrap-up`.

## Decision Rules (each learned from an incident)

1. **Never start, resume or un-hold autopilot.** Restart is an explicit operator action with a new
   era (era/baseline files are human-only). *Why*: checkpoint 2026-09-25; 2026-11-09 audit.
2. **Journal-derived conclusions are August-era.** The journal staleness audit
   (AP-JOURNAL-STALENESS-AUDIT) runs LAST before any relaunch; relaunch work does not jump the queue.
   *Why*: last run 2026-08-09, before the AK kernel gains (operator 2026-11-19).
3. **Read all journal shards** (`autopilot_journal.jsonl` and `autopilot_journal_1.jsonl`). *Why*:
   the 2026-11-09 audit found the true last run only in the second shard.
4. **Features: default off but fully wired and on the manipulation surface; proven wins default ON.**
   *Why*: operator 2026-11-18.
5. **Seed hypotheses via `StrategyStore.store()`, never raw SQL.** *Why*: a raw INSERT skips FTS5 and
   FAISS, so the row is never retrieved.
6. **A rewind scrubs the journal `falsifier` text in the same stopped window as the strategy store.**
   *Why*: 2026-06-01 the corrupt "gate-locked baseline" narrative regenerated from falsifier text.
7. **Stop means graceful drain, not SIGKILL; a pause is not a stop.** *Why*: memory
   `feedback_autopilot_stop_semantics`.
8. **Noise is a window property, not contention.** *Why*: memory
   `feedback_autopilot_noise_window_not_contention`.
9. **Schema-driven work evaluates Jev techniques and the REPL retrieval alternative.** *Why*: memory
   `feedback_schema_work_consider_jev`.
10. **Bring-up runs the feature through the live API env, not just a new server.** *Why*: memory
    `feedback_bringup_exercise_consumer_path`.
11. **Never tick on a descriptive interim.** A probe stays unticked until its predeclared rule decides.
    *Why*: CODEMODE-AB-V2 (2026-11-18) stopped on a latency harm rule, not on its question.

## Gates

- **Operator HOLD** on autopilot runs; **operator ratify** for era/baseline and stack changes
  (`stack-change` skill).
- **D9**: changes under `scripts/coordination/**` need a `D9-ack:` line; route them to pipeline-mgmt.
- **Measurement**: `agents/shared/MEASUREMENT_POLICY.md`,
  `docs/guides/agent-workflows/measurement-sufficiency.md`; formal gates stay futility-only.
- **Reload ownership**: CLAUDE.md *Process Management* → API reload vs full stack.

## Coordination With Other Owners

- **pipeline-mgmt**: rows, dispatcher, filing, disk, holds and roster rows. Send defects by bus or
  message with `corr_id`.
- **autokernel**: kernel numbers come from the champion; ask, do not run AK rows.
- **Codex sessions** stay off autopilot tracks (operator 2026-11-19); ask pipeline-mgmt to park any
  that get spawned.

## Guardrails

- No production kernel edits; no promotion work.
- No name-pattern kills; kill captured PIDs and verify.
- Worktree from `origin/main`, pathspec commits, no `git add -A`, no stash/checkout/reset in shared clones.
- Index rows: subagents prepare, this session applies.

## Learned

Append-only. Add an entry by committing to this file in your own lane (fresh worktree from
`origin/main`, branch `autopilot/learned-<date>`, pathspec commit of `agents/autopilot.md` only,
`serialized_push.py`). Format: `- YYYY-MM-DD — rule — why (incident/commit) — session id`.

- 2026-11-20 — file seeded from the autopilot program handoff, progress 2026-11-09..18 and memory notes —
  pipeline-mgmt.
