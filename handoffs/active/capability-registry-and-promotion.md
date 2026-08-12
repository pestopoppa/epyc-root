# Capability Registry, Safe Role-Restart Applicator & Promotion Workflow

**Status**: IN PROGRESS — revalidated 2026-08-05. W0 traffic-class interface, TaskIR/task-record capture, and live `request_context` workload-class tagging are closed; W1 seed rows landed; W2 generated Action-Availability + index A-by surfaces landed/adopted 2026-06-27; W3 implementation primitives remain present, but its live shadow-restart attestation is still absent; W4 has not run and every registry row remains `promotion_state: placeholder`.
**Created**: 2026-06-12
**Priority**: READY FOR W3 ATTESTATION — the implementation prerequisites survived the 2026-08-05 code audit, but promotion remains fail-closed until a shadowed live restart supplies the required attestation. W4 remains downstream of that evidence; this audit does not promote any row.
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

- [x] **W0 — workload model** (1 day, ungated): `orchestration/workload_model.yaml` per spec §D — traffic classes `{interactive, eval_batch, campaign}` with per-class volume share (seed from the 2026-06-11 tally), latency/throughput SLO, serving class, contention priority; extend `request_context` tagging to workload class. Acceptance: routing/placement/autopilot consumers named in §D can read it; eval traffic self-labels `eval_batch`. **Interface branch-ready 2026-06-13**: `feat/workload-traffic-classes` commit `b62946d` extends the F1 workload model with `traffic_classes:` and `traffic_class_tagging:`, adds read-only `src/workload_model.py` loader/inference helpers, and validates the three required traffic classes. **Capture lane landed 2026-06-19**: orchestrator `02370da` adds `capture_workload_class()`, persists `workload_class` through TaskIR canonicalization and progress task records, and keeps legacy inference for older records. **Live request context closed 2026-06-28**: orchestrator `f895282d` adds explicit `ChatRequest.workload_class`, request-local `LLMPrimitives` workload-class state, backend request metadata propagation, delegated specialist preservation, and scheduler-policy wrapping without changing admission priority or promoting any capability row.
- [x] **W1 — registry schema + seed rows** (~1 day): `orchestration/capability_registry.yaml` per §C.1 schema; seed with the first-cohort levers (W4 list) plus existing operator-only rows. Acceptance: schema-validates; every row names applicator, range, evidence with protocol id, risk, `actionable_by`.
- [x] **W2 — compilation targets** (~1 day): compile registry → planner Action-Availability section (generated allow/deny + reasons, replacing program.md's hand-maintained denylist) and → master-index `A-by` column (script per §E.4, not hand-edit). Acceptance: both outputs regenerate from the YAML; a row edit propagates to both.
- [ ] **W3 — safe role-restart applicator** (~2–3 days): `config_applicator.restart_role(role, env_overrides, registry_overrides)` per §C.2 — pause autopilot dispatch via existing contention/queue path → `orchestrator_stack.py reload <role>` → health gate (`wait_for_health` + one canned smoke completion) → rollback to prior config on fail → journal `exogenous_role_restart` boundary (spanning trials auto-excluded). Batched restart-class trial protocol (one restart, several trials, restore) enforced by the dispatch gate, declared in the capability row; strict callers must pass explicit affected roles and a smoke hook, not infer restart scope. Acceptance: shadowed restart of one role passes attestation; a deliberately failed health gate rolls back.
  - [x] **W3-a — the "deliberately failed health gate rolls back" acceptance half is now covered by an
        induced-failure unit test ✅ 2026-08-12.** Measured before writing anything: `coverage run
        --rcfile=/dev/null --include='*config_applicator.py' -m pytest tests/unit/test_config_applicator.py`
        showed the entire `role == "orchestrator"` branch of `restart_role()` — the ONLY place the API
        health gate is consulted — as never executed (lines 2221-2223, 2228-2230, 2232, 2246-2248), because
        all 44 existing tests pass a MODEL role and evaluate that branch False. The rollback tests that did
        exist induce a *reload* failure or a *smoke* failure; both reach the same rollback block from a
        different source, so a health-gate regression was invisible. Also uncovered: the empty-role guard
        (2144) and the registry-restore-exception path (2292-2293). Five tests added; `restart_role()` now
        has zero missing statements. Five mutations, each caught by exactly the intended test with the suite
        still reporting 49 collected: health gate forced green, health failure swallowed, empty-role guard
        removed, registry-restore failure laundered to `ok`, smoke run despite a failed health gate.
  - [ ] **W3-b — BLOCKED on a reload window owned by the inference session.** The remaining acceptance half
        is a LIVE shadowed role restart, and reload ownership belongs to whichever session owns the
        inference — running one around it caused INC-20260728-reload-preemption. Everything reachable
        without executing a reload is now done; this row needs a reload window, not more code. Stated in
        blocker grammar deliberately, so `backlog_row_check.py` refuses to dispatch W3 to a session that
        cannot finish it — the 2026-08-12 dispatch that produced W3-a screened DISPATCHABLE with no blocker.
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

2026-06-27 W2 guard + W3 first primitive: Orchestrator `7b47671e` added `--replace-block` and `--check-block`
to the capability compiler so the generated master-index A-by table can be mechanically checked. Root `82904490`
wrapped that table in capability-registry markers and recorded the check command. Orchestrator W3 follow-up adds a
dormant `restart_role(role, env_overrides, registry_overrides)` primitive with mocked success and rollback coverage
for env-backed role restarts. Registry overrides still fail closed until a rollback record exists, and W3 remains
open for dispatch pause, smoke completion, exogenous restart journaling, and shadow attestation.

2026-06-27 W3 boundary journal slice: Orchestrator adds an append-only `role_restart_boundary` journal event and
optionally attaches it from `restart_role(..., journal=...)`. The event uses `boundary_trial_id` rather than
reserved `trial_id`, round-trips without counting as a trial, and is ignored by archive reconstruction. This closes
the W3 journal-record primitive only; W3 remains open for dispatch pause, smoke completion, co-hosted-role
resolution, registry override rollback semantics, and a shadowed live restart attestation.

2026-06-28 W3 dispatch-pause slice: Orchestrator `config_applicator.restart_role()` now accepts
`pause_dispatch=True` plus an optional AutoPilot state path and grace period. When requested, it sets
`paused=True` in the AutoPilot state file before invoking `orchestrator_stack.py reload <role>`, fails closed before
reload if the state file cannot be paused, and restores `paused=False` only if the applicator changed it from false.
The pause result is attached to the restart payload and is restored on both successful reloads and rollback paths.
This closes the W3 dispatch-pause primitive without promoting any capability row or touching the live AutoPilot run.

2026-06-28 W3 registry-rollback slice: Orchestrator `config_applicator.restart_role()` now applies
`registry_overrides` as dotted YAML paths against an explicit registry file, records the exact prior leaf values, and
atomically restores that rollback record before the rollback reload when reload or smoke gating fails. Missing parents
fail closed before any reload, and restart-boundary events now include the registry override keys. This closes the W3
registry override rollback primitive without promoting any capability row or touching the live stack. W3 remains open
only for a shadowed live restart attestation once the evidence plane allows restart-class experiments.

2026-07-03 W3/W4 protocol hardening: Orchestrator now requires every `role_restart` / `stack_restart` capability row to
declare a structured `trial_protocol` mapping (`class: batched_restart`, `min_trials >= 1`,
`restore_after_batch: true`, and non-empty `boundary_event`). The first restart-class rows (`moe_spec_budget`,
`ea_compaction_profiles`, and `draft_max_p_split`) now carry the shared `role_restart_boundary` / 5-trial restore
contract. This does not promote any row or enable live restarts; it makes the C.2 batched restart protocol a validated
data contract before future W4 promotion work.

2026-07-04 W3 strict-scope hardening: Orchestrator `config_applicator.restart_role()` now has strict opt-in gates for
future promoted callers: `require_explicit_affected_roles=True` fails before dispatch pause, registry edits, or reload
unless the caller supplied the exact restart surface; `require_smoke_check=True` likewise fails before reload unless a
role smoke hook is present. The capability registry restart protocol now requires `smoke_check: canned_completion` and
`require_explicit_affected_roles: true` on every `role_restart` / `stack_restart` row. This keeps the existing manual
helper compatible while ensuring future AutoPilot promotion cannot rely on stack-prior inference or skip the smoke
gate. W3 still waits for a shadowed live restart attestation.

## Gates & pitfalls

- Hard gate: W1–W4 wait for `evidence-plane-ledger.md` (findings-01 Phase 1) — same gate as the index rewrite's A15 row. Do not hand the optimizer restart-class levers on an uncertified instrument.
- Lifecycle ONLY via `orchestrator_stack.py` (`feedback_use_orchestrator_stack_for_lifecycle`) — the applicator must never kill PIDs directly.
- The registry is the rollback record — restart with overrides not recorded in it and rollback is undefined.
- Same-GGUF roles share one server process (`feedback_same_model_roles_share_server`): a "role restart" can bounce sibling roles — the promoted path must pass an explicit affected-role set and journal the boundary for ALL roles on that process.
- A-by column and Action-Availability must only ever be generated (W2); one hand edit and the two sources of truth diverge permanently.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; any number cited follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar.

## Checkpoints

- [x] **2026-08-05 staleness audit:** re-read the live orchestrator implementation and registry rather than refreshing this file cosmetically. `config_applicator.restart_role()` and its boundary/trial-protocol gates remain present; the registry still contains only `promotion_state: placeholder` rows, and focused tests explicitly preserve the no-live/no-promoted invariant. No live shadow-restart attestation was found. Therefore W3 stays open on its acceptance test and W4 stays open with zero promotions; the obsolete blanket “evidence plane Phase 1” priority wording above is replaced by the narrower, current gate. ✅ 2026-08-05

- 2026-06-13 W0 interface branch-ready: `feat/workload-traffic-classes` commit `b62946d`, based on F1 `feat/task-record-harvester` `40bde0d`. GitNexus re-indexed the worktree first (48,880 nodes, 83,890 edges, 300 flows). Formal graph impact could not resolve `orchestration/workload_model.yaml` (`UNKNOWN`); manual `rg` found only the F1 harvester reading it. Separate GitNexus impact on live `LLMPrimitives.request_context` was HIGH, so this pass avoided live request tagging. Validation: `python3 -m py_compile src/workload_model.py tests/unit/test_workload_model.py` passed; `uv run --with pytest --with pyyaml pytest -q tests/unit/test_workload_model.py tests/unit/test_task_harvester.py` -> 6 passed, 1 pytest config warning; `uv run --with ruff ruff check src/workload_model.py tests/unit/test_workload_model.py` passed; `git diff --cached --check` passed.
- 2026-06-19 A2 first-cohort row tightened on active: Orchestrator `3f6692b` (`Canonicalize edit transaction capability row`) updated `orchestration/capability_registry.yaml`, `src/registry/capability_registry.py`, and `tests/unit/test_capability_registry.py`. Validation: `python3 -m py_compile src/registry/capability_registry.py tests/unit/test_capability_registry.py`; `uv run pytest -q tests/unit/test_capability_registry.py` -> 47 passed; `uv run ruff check ...`; `git diff --check`.
- 2026-06-19 W0/A2 hardening on active: Orchestrator `02370da` persists explicit `workload_class` on TaskIR/task records while keeping legacy inference (`uv run pytest -q tests/unit/test_workload_model.py tests/unit/test_task_ir.py tests/unit/test_progress_logger_task_record.py tests/unit/test_task_harvester.py` -> 17 passed). Orchestrator `63bbc8b` fail-closes promoted capability rows unless they are autopilot-actionable and carry a non-empty string kill condition (`tests/unit/test_capability_registry.py` included in the 122-test focused gate). Live edit auto-routing remains deferred/gated.
- 2026-06-28 W0 live request-context closure: Orchestrator `f895282d` wires workload class through the live request context. `ChatRequest.workload_class` is constrained to `interactive|eval_batch|campaign`; unset requests infer from existing metadata, so background/batched calls attribute as `eval_batch` while preserving existing admission priority behavior. `LLMPrimitives.request_context()` now stores request-local workload class in diagnostics, forwards it to backend request metadata, and delegated specialist contexts preserve it. `SchedulerPolicy` mirrors the field for interaction-lifecycle wrappers. GitNexus impact on the exact `LLMPrimitives.request_context` method was LOW (`impactedCount=3`; the earlier HIGH concern is no longer present on the current graph). Validation: `python3 -m py_compile` on touched modules/tests; `uv run ruff check ...`; `uv run pytest -q tests/unit/test_llm_primitives.py tests/unit/test_inference_mixin.py tests/unit/test_interaction_lifecycle.py tests/unit/test_workload_model.py tests/unit/test_task_ir.py` -> `70 passed`; `git diff --check`.
- 2026-06-27 W2 compiler foundation: Orchestrator `d9fe32eb` wires generated capability-registry availability into AutoPilot planning and adds `compile_capability_registry.py --target action-availability|index-a-by`. Validation: `python3 -m py_compile src/registry/capability_registry.py scripts/registry/compile_capability_registry.py scripts/autopilot/autopilot.py tests/unit/test_capability_registry.py tests/unit/test_autopilot_creativity.py`; `uv run pytest -q tests/unit/test_capability_registry.py tests/unit/test_autopilot_creativity.py` -> 70 passed; `uv run ruff check ...`; both compiler targets emitted expected generated output. No live capability promotion.
- 2026-06-27 W2 index adoption: Root docs adopted the generated `index-a-by` table in `master-handoff-index.md`. Validation: reran `uv run python scripts/registry/compile_capability_registry.py --target index-a-by`; GitNexus impact was HIGH for both root docs because they are coordination surfaces, so the edit stayed in the main thread. No runtime files or capability promotion states changed.
- 2026-06-27 W2 drift guard + W3 primitive: Orchestrator `7b47671e` added marked-block replace/check support to `compile_capability_registry.py`; Root `82904490` adopted the marked block. Orchestrator W3 primitive adds `restart_role()` env rollback support but does not wire planner/AutoPilot calls. Validation: `uv run pytest -q tests/unit/test_capability_registry.py` -> 55 passed; `uv run python scripts/registry/compile_capability_registry.py --target index-a-by --check-block /mnt/raid0/llm/epyc-root/handoffs/active/master-handoff-index.md` passed; `python3 -m py_compile scripts/autopilot/config_applicator.py tests/unit/test_config_applicator.py`; `uv run pytest -q tests/unit/test_config_applicator.py` -> 10 passed; `uv run ruff check scripts/autopilot/config_applicator.py tests/unit/test_config_applicator.py`.
- 2026-06-27 W3 boundary journal slice: Orchestrator added `role_restart_boundary` append-only events plus optional `restart_role(..., journal=...)` attachment. Validation: `python3 -m py_compile scripts/autopilot/experiment_journal.py scripts/autopilot/config_applicator.py tests/unit/test_journal_supersession_events.py tests/unit/test_config_applicator.py`; `uv run pytest -q tests/unit/test_journal_supersession_events.py tests/unit/test_config_applicator.py` -> 22 passed; `uv run ruff check ...`; `git diff --check`.
- 2026-07-03 W3/W4 protocol hardening: Orchestrator validates structured restart-class `trial_protocol` rows and populates the first-cohort restart rows with the batched-restart/restore/boundary contract. Validation: `uv run pytest -q tests/unit/test_capability_registry.py` -> 58 passed; `python3 -m py_compile`; `uv run ruff check src/registry/capability_registry.py tests/unit/test_capability_registry.py`; both capability compiler targets; and generated block drift check against the root master index.
- 2026-07-04 W3 strict-scope hardening: Orchestrator added strict-mode `restart_role()` gates for explicit affected roles and required smoke hooks, and the registry validator now rejects restart-class rows without `smoke_check` plus `require_explicit_affected_roles: true`. Validation: GitNexus impact was LOW for `_validate_entry` (`impactedCount=8`) and `restart_role` (`impactedCount=0`); `uv run pytest tests/unit/test_config_applicator.py tests/unit/test_capability_registry.py -q` -> 81 passed; `uv run ruff check scripts/autopilot/config_applicator.py src/registry/capability_registry.py tests/unit/test_config_applicator.py tests/unit/test_capability_registry.py`; both capability compiler targets rendered.
- 2026-08-12 W3 health-gate acceptance (W3-a): the backlog row that dispatched this reads "build `config_applicator.restart_role()` … the ONE missing applicator", and that premise is **false** — the applicator has existed since the 2026-06-27…07-04 slices and the 2026-08-05 audit re-confirmed it. What was actually missing was the row's own second acceptance clause. Coverage-measured first, not assumed: `restart_role()`'s `role == "orchestrator"` branch (the only consult of `health_check`) had **zero** executed statements across all 44 existing tests, so "a deliberately failed health gate rolls back" was untested; the empty-role guard and the registry-restore-exception path were likewise dead. Orchestrator `tests/unit/test_config_applicator.py` adds five induced-failure tests (health gate fails → env+registry rollback, boundary journaled, smoke never invoked; health ok + smoke fails → rollback; both green → one reload, no rollback; empty role fails closed before any reload; registry-restore exception is recorded and does not swallow the env rollback). Validation: `.venv/bin/python -m pytest -q tests/unit/test_config_applicator.py` -> **49 passed** (was 44, so the five are counted by the reporter); `coverage` re-run shows **zero** missing statements in `restart_role()` (2112-2329); five mutations run against an out-of-tree mutated copy of the module (never writing the shared file) each failed exactly one intended test — `health_gate_always_ok`, `health_failure_not_recorded`, `no_empty_role_guard`, `registry_restore_laundered`, `smoke_runs_despite_health`; `ruff check` clean; `git diff --check` clean. **No reload was executed** — `subprocess.run` is stubbed in every test, and reload ownership belongs to the inference-owning session (INC-20260728-reload-preemption). Call-site check: `restart_role()` does have a production caller chain (`apply_role_restart_params` → `restart_role`, `config_applicator.py:1556`, reached from `apply_params`), fail-closed behind `AUTOPILOT_AP3_ROLE_RESTART_ENABLE` and zero promoted registry rows — so it is wired, not orphaned.
