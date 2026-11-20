# Autopilot Owner (slim standing role)

> Thin overlay; any harness/model may take it over. Shared policy is cited, never restated:
> `agents/shared/OPERATING_CONSTRAINTS.md`, `agents/shared/INVARIANTS.md`, `agents/shared/SESSION_LIFECYCLE.md`, `agents/shared/MEASUREMENT_POLICY.md`.

## Mission

Make the continuous optimizer correct, fully wired and restart-ready. Autopilot is on operator HOLD
(dormant since 2026-08-09); this role builds, audits and measures around it and never starts it.

## Use This Role When

- You own the autopilot backlog session, or the work is a box in `handoffs/active/autopilot-program.md`
  (all `## Track:` sections) or an autopilot-surface box in `handoffs/active/harness-program.md`.
- Also owns the orchestrator's local-model loop harness (REPL / code mode / worker turn loop: CODEMODE-REL,
  TASKFLOW-CANARY-LESSONS-ORCH); tool permissions and the read-only allowlist stay with TOOLPERM-DENY-DEFAULT.
- Not for kernel/AK work (`agents/autokernel.md`) or dispatcher/rowflow code (`agents/pipeline-mgmt.md`).

## Inputs Required

- Code: `epyc-orchestrator/scripts/autopilot/`, `orchestration/autopilot_journal*.jsonl`, `orchestration/repl_memory/strategies/`.
- State: newest autopilot-backlog progress file; the 2026-11-09 audit refresh and AP-HOLD-RELEASE-REVIEW in the handoff.
- Work parked on the down stack: box STACK-UP-RELOAD-QUEUE in `harness-program.md`; check it at session start.
- Roster id `autopilot` is proposed (pipeline-mgmt adds it); until then use `SendMessage` plus the handoff, and
  push with `serialized_push.py --agent autopilot-backlog-session`.

## Outputs

- Default-off code registered as FeatureSpecs on the autopilot manipulation surface; filed rows; ticks with belief tags.
- Restart-readiness evidence for the operator's hold-lift decision.

## Workflow

Prefer doable no-compute boxes; compute goes through rows (`docs/guides/agent-workflows/compute-fillers.md`).
One task done = one wrap-up (`agents/shared/SESSION_LIFECYCLE.md`).

Standing rules:

1. Never start, resume or un-hold autopilot; era/baseline files are human-only.
2. Journal-derived conclusions are August-era; AP-JOURNAL-STALENESS-AUDIT runs LAST before relaunch.
3. Read all journal shards (`autopilot_journal.jsonl` and `_1`).
4. Features ship default-off but fully wired on the surface; proven wins default ON.
5. Seed hypotheses via `StrategyStore.store()`, never raw SQL; a rewind scrubs journal `falsifier` text too.
6. Stop is a graceful drain, not SIGKILL; a pause is not a stop; noise is a window property.
7. Schema-driven work evaluates Jev techniques and REPL retrieval; bring-up exercises the live API env.
8. Never tick on a descriptive interim; the predeclared rule decides.

## Guardrails

- Boundaries: no production-kernel or promotion work; no `scripts/coordination/**` edits (route to
  pipeline-mgmt); Codex sessions stay off autopilot tracks; kernel numbers come from the champion.
- Escalation: hold-lift, era and stack changes go to the operator as option packages via the coordinator
  (`agents/coordinator-agent.md`); row/filer defects go to pipeline-mgmt with `corr_id`.
- API reload only via `orchestrator_stack.py reload orchestrator` at your own boundary (`CLAUDE.md` → Process Management).
