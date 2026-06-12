# Capability Registry, Safe Role-Restart Applicator & Promotion Workflow

**Status**: SPEC'D, not started (from the Fable 5 architecture review)
**Created**: 2026-06-12
**Priority**: GATED — on `evidence-plane-ledger.md` (sibling handoff = findings-01 Phase 1: the instrument must certify effects before the optimizer gets bigger levers; spec §C.4). W0 (workload model) is NOT gated and can run now.
**Spec**: [fable5-findings-04-impl-plan.md](fable5-findings-04-impl-plan.md) §C + §D — read before claiming any waypoint
**Related**: [fable5-findings-04-northstar-portfolio-indices.md](fable5-findings-04-northstar-portfolio-indices.md) (why backlog→actionable must be a state transition); [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md) (edit-transaction = first-cohort member); [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) (`moe_spec_budget` evidence source)

## Why

Every measured speed lever that needs a restart is currently operator-only,
and the planner's action surface is a hand-maintained denylist in program.md
that nobody promotes against. The spec turns "what can the autopilot touch"
into data: one YAML row per lever (kind/surface/applicator/range/evidence/
risk/actionable_by), one missing applicator (safe role restart), and one
standing monthly promotion pass. §D's workload model is the smallest
interface with the biggest definitional payoff and rides along as W0.

## Waypoints

- [ ] **W0 — workload model** (1 day, ungated): `orchestration/workload_model.yaml` per spec §D — traffic classes `{interactive, eval_batch, campaign}` with per-class volume share (seed from the 2026-06-11 tally), latency/throughput SLO, serving class, contention priority; extend `request_context` tagging to workload class. Acceptance: routing/placement/autopilot consumers named in §D can read it; eval traffic self-labels `eval_batch`.
- [ ] **W1 — registry schema + seed rows** (~1 day): `orchestration/capability_registry.yaml` per §C.1 schema; seed with the first-cohort levers (W4 list) plus existing operator-only rows. Acceptance: schema-validates; every row names applicator, range, evidence with protocol id, risk, `actionable_by`.
- [ ] **W2 — compilation targets** (~1 day): compile registry → planner Action-Availability section (generated allow/deny + reasons, replacing program.md's hand-maintained denylist) and → master-index `A-by` column (script per §E.4, not hand-edit). Acceptance: both outputs regenerate from the YAML; a row edit propagates to both.
- [ ] **W3 — safe role-restart applicator** (~2–3 days): `config_applicator.restart_role(role, env_overrides, registry_overrides)` per §C.2 — pause autopilot dispatch via existing contention/queue path → `orchestrator_stack.py reload <role>` → health gate (`wait_for_health` + one canned smoke completion) → rollback to prior config on fail → journal `exogenous_role_restart` boundary (spanning trials auto-excluded). Batched restart-class trial protocol (one restart, several trials, restore) enforced by the dispatch gate, declared in the capability row. Acceptance: shadowed restart of one role passes attestation; a deliberately failed health gate rolls back.
- [ ] **W4 — promotion workflow + first cohort** (recurring, ~half day/month): monthly pass per §C.3 — promote operator→autopilot when descriptor/applicator wired + range validated + kill condition written + one shadowed trial passes attestation. First cohort: `moe_spec_budget`, per-role `enable_thinking`, EA compaction profiles (S8/S9), draft_max/p_split where spec-dec is on, and `edit_transaction_auto_routing` (A2 rollout contract prepared in [`multi-file-coding-completion-capability.md`](multi-file-coding-completion-capability.md)). Acceptance: first pass executed and logged; promoted rows flip `actionable_by`.

### First-cohort note: edit transaction auto-routing

`edit_transaction_auto_routing` is the proven protocol fix for routine coding edits, but it is not yet an
autopilot lever. Seed its future registry row as `actionable_by=operator` until the A2 contract's clean-window
A/B, scoped-root attestation, and kill conditions exist. The current production-safe surface is explicit
`force_mode="edit"` only; missing `ORCHESTRATOR_EDIT_TRANSACTION=1` or scoped `ORCHESTRATOR_EDIT_ROOT`
must continue to fail closed rather than falling back to REPL.

## Gates & pitfalls

- Hard gate: W1–W4 wait for `evidence-plane-ledger.md` (findings-01 Phase 1) — same gate as the index rewrite's A15 row. Do not hand the optimizer restart-class levers on an uncertified instrument.
- Lifecycle ONLY via `orchestrator_stack.py` (`feedback_use_orchestrator_stack_for_lifecycle`) — the applicator must never kill PIDs directly.
- The registry is the rollback record — restart with overrides not recorded in it and rollback is undefined.
- Same-GGUF roles share one server process (`feedback_same_model_roles_share_server`): a "role restart" can bounce sibling roles — the applicator must resolve role→process and journal the boundary for ALL roles on that process.
- A-by column and Action-Availability must only ever be generated (W2); one hand edit and the two sources of truth diverge permanently.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; any number cited follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar.
