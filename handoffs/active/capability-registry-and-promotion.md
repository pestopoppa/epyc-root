# Capability Registry, Safe Role-Restart Applicator & Promotion Workflow

**Status**: IN PROGRESS — W0 traffic-class interface branch-ready 2026-06-13 and TaskIR/task-record capture landed 2026-06-19; W1 seed rows landed; W2 generated Action-Availability + index A-by surfaces landed/adopted 2026-06-27; W3-W4 remain gated on evidence-plane ledger
**Created**: 2026-06-12
**Priority**: GATED — on `evidence-plane-ledger.md` (sibling handoff = findings-01 Phase 1: the instrument must certify effects before the optimizer gets bigger levers; spec §C.4). W0 (workload model) is NOT gated and can run now.
**Spec**: [fable5-findings-04-impl-plan.md](../completed/fable5-findings-04-impl-plan.md) §C + §D — read before claiming any waypoint
**Related**: [fable5-findings-04-northstar-portfolio-indices.md](../completed/fable5-findings-04-northstar-portfolio-indices.md) (why backlog→actionable must be a state transition); [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md) (edit-transaction = first-cohort member); [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) (`moe_spec_budget` evidence source)

## Why

Every measured speed lever that needs a restart is currently operator-only,
and the planner's action surface is a hand-maintained denylist in program.md
that nobody promotes against. The spec turns "what can the autopilot touch"
into data: one YAML row per lever (kind/surface/applicator/range/evidence/
risk/actionable_by), one missing applicator (safe role restart), and one
standing monthly promotion pass. §D's workload model is the smallest
interface with the biggest definitional payoff and rides along as W0.

## Waypoints

- [ ] **W0 — workload model** (1 day, ungated): `orchestration/workload_model.yaml` per spec §D — traffic classes `{interactive, eval_batch, campaign}` with per-class volume share (seed from the 2026-06-11 tally), latency/throughput SLO, serving class, contention priority; extend `request_context` tagging to workload class. Acceptance: routing/placement/autopilot consumers named in §D can read it; eval traffic self-labels `eval_batch`. **Interface branch-ready 2026-06-13**: `feat/workload-traffic-classes` commit `b62946d` extends the F1 workload model with `traffic_classes:` and `traffic_class_tagging:`, adds read-only `src/workload_model.py` loader/inference helpers, and validates the three required traffic classes. **Capture lane landed 2026-06-19**: orchestrator `02370da` adds `capture_workload_class()`, persists `workload_class` through TaskIR canonicalization and progress task records, and keeps legacy inference for older records. Live `request_context` wiring remains deliberately deferred after GitNexus impact on `LLMPrimitives.request_context` returned HIGH.
- [x] **W1 — registry schema + seed rows** (~1 day): `orchestration/capability_registry.yaml` per §C.1 schema; seed with the first-cohort levers (W4 list) plus existing operator-only rows. Acceptance: schema-validates; every row names applicator, range, evidence with protocol id, risk, `actionable_by`.
- [x] **W2 — compilation targets** (~1 day): compile registry → planner Action-Availability section (generated allow/deny + reasons, replacing program.md's hand-maintained denylist) and → master-index `A-by` column (script per §E.4, not hand-edit). Acceptance: both outputs regenerate from the YAML; a row edit propagates to both.
- [ ] **W3 — safe role-restart applicator** (~2–3 days): `config_applicator.restart_role(role, env_overrides, registry_overrides)` per §C.2 — pause autopilot dispatch via existing contention/queue path → `orchestrator_stack.py reload <role>` → health gate (`wait_for_health` + one canned smoke completion) → rollback to prior config on fail → journal `exogenous_role_restart` boundary (spanning trials auto-excluded). Batched restart-class trial protocol (one restart, several trials, restore) enforced by the dispatch gate, declared in the capability row. Acceptance: shadowed restart of one role passes attestation; a deliberately failed health gate rolls back.
- [ ] **W4 — promotion workflow + first cohort** (recurring, ~half day/month): monthly pass per §C.3 — promote operator→autopilot when descriptor/applicator wired + range validated + kill condition written + one shadowed trial passes attestation. First cohort: `moe_spec_budget`, per-role `enable_thinking`, EA compaction profiles (S8/S9), draft_max/p_split where spec-dec is on, and `edit_transaction_auto_routing` (A2 rollout contract prepared in [`multi-file-coding-completion-capability.md`](multi-file-coding-completion-capability.md)). Acceptance: first pass executed and logged; promoted rows flip `actionable_by`.

### First-cohort note: edit transaction auto-routing

`edit_transaction_auto_routing` is the proven protocol fix for routine coding edits, but it is not yet an
autopilot lever. Seed its future registry row as `actionable_by=operator` until the A2 contract's clean-window
A/B, scoped-root attestation, and kill conditions exist. The current production-safe surface is explicit
`force_mode="edit"` only; missing `ORCHESTRATOR_EDIT_TRANSACTION=1` or scoped `ORCHESTRATOR_EDIT_ROOT`
must continue to fail closed rather than falling back to REPL.

2026-06-19 checkpoint: Orchestrator `3f6692b` made the first-cohort A2 row executable as a guarded
placeholder: the id now matches this handoff (`edit_transaction_auto_routing`), `actionable_by=operator`
is explicit, the A2 kill condition is recorded in the row, and the registry loader rejects any promoted row
without a `kill_condition`. Orchestrator `63bbc8b` tightened the loader further: `actionable_by` must be
`operator`, `autopilot`, or `gated:<condition>`, and `promotion_state=promoted` rows must be
autopilot-actionable with a non-empty string kill condition. W2/W3/W4 remain gated; no autopilot action
surface was enabled.

2026-06-27 checkpoint: Orchestrator `d9fe32eb` adds the W2 compiler foundation. `src/registry/capability_registry.py`
now compiles capability rows into generated planner Action-Availability text and a generated index A-by table;
`scripts/registry/compile_capability_registry.py` exposes both outputs as CLI targets. AutoPilot appends the
generated capability section to the existing `### Action Availability` prompt/critic surface, so the planner now
sees all first-cohort levers as registry-derived blocked/operator-only rows. No capability was promoted and no
dispatch/applicator path was enabled; the generated index table exists, but live master-index column replacement
still needs a deliberate adoption pass.

2026-06-27 follow-up: the generated `index-a-by` table was adopted into
`master-handoff-index.md` under "Generated Capability A-by Table" with the exact compiler command. This closes W2
without changing any row's `actionable_by` or `promotion_state`: all restart-class levers remain gated on
`evidence-plane-ledger.md Phase 1`, and `edit_transaction_auto_routing` remains operator-only.

## Gates & pitfalls

- Hard gate: W1–W4 wait for `evidence-plane-ledger.md` (findings-01 Phase 1) — same gate as the index rewrite's A15 row. Do not hand the optimizer restart-class levers on an uncertified instrument.
- Lifecycle ONLY via `orchestrator_stack.py` (`feedback_use_orchestrator_stack_for_lifecycle`) — the applicator must never kill PIDs directly.
- The registry is the rollback record — restart with overrides not recorded in it and rollback is undefined.
- Same-GGUF roles share one server process (`feedback_same_model_roles_share_server`): a "role restart" can bounce sibling roles — the applicator must resolve role→process and journal the boundary for ALL roles on that process.
- A-by column and Action-Availability must only ever be generated (W2); one hand edit and the two sources of truth diverge permanently.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; any number cited follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar.

## Checkpoints

- 2026-06-13 W0 interface branch-ready: `feat/workload-traffic-classes` commit `b62946d`, based on F1 `feat/task-record-harvester` `40bde0d`. GitNexus re-indexed the worktree first (48,880 nodes, 83,890 edges, 300 flows). Formal graph impact could not resolve `orchestration/workload_model.yaml` (`UNKNOWN`); manual `rg` found only the F1 harvester reading it. Separate GitNexus impact on live `LLMPrimitives.request_context` was HIGH, so this pass avoided live request tagging. Validation: `python3 -m py_compile src/workload_model.py tests/unit/test_workload_model.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_workload_model.py tests/unit/test_task_harvester.py` -> 6 passed, 1 pytest config warning; `uv run --with ruff ruff check src/workload_model.py tests/unit/test_workload_model.py` passed; `git diff --cached --check` passed.
- 2026-06-19 A2 first-cohort row tightened on active: Orchestrator `3f6692b` (`Canonicalize edit transaction capability row`) updated `orchestration/capability_registry.yaml`, `src/registry/capability_registry.py`, and `tests/unit/test_capability_registry.py`. Validation: `python3 -m py_compile src/registry/capability_registry.py tests/unit/test_capability_registry.py`; `uv run pytest -q tests/unit/test_capability_registry.py` -> 47 passed; `uv run ruff check ...`; `git diff --check`.
- 2026-06-19 W0/A2 hardening on active: Orchestrator `02370da` persists explicit `workload_class` on TaskIR/task records while keeping legacy inference (`uv run pytest -q tests/unit/test_workload_model.py tests/unit/test_task_ir.py tests/unit/test_progress_logger_task_record.py tests/unit/test_task_harvester.py` -> 17 passed). Orchestrator `63bbc8b` fail-closes promoted capability rows unless they are autopilot-actionable and carry a non-empty string kill condition (`tests/unit/test_capability_registry.py` included in the 122-test focused gate). Live `request_context` and live edit auto-routing remain deferred/gated.
- 2026-06-27 W2 compiler foundation: Orchestrator `d9fe32eb` wires generated capability-registry availability into AutoPilot planning and adds `compile_capability_registry.py --target action-availability|index-a-by`. Validation: `python3 -m py_compile src/registry/capability_registry.py scripts/registry/compile_capability_registry.py scripts/autopilot/autopilot.py tests/unit/test_capability_registry.py tests/unit/test_autopilot_creativity.py`; `uv run pytest -q tests/unit/test_capability_registry.py tests/unit/test_autopilot_creativity.py` -> 70 passed; `uv run ruff check ...`; both compiler targets emitted expected generated output. No live capability promotion.
- 2026-06-27 W2 index adoption: Root docs adopted the generated `index-a-by` table in `master-handoff-index.md`. Validation: reran `uv run python scripts/registry/compile_capability_registry.py --target index-a-by`; GitNexus impact was HIGH for both root docs because they are coordination surfaces, so the edit stayed in the main thread. No runtime files or capability promotion states changed.
