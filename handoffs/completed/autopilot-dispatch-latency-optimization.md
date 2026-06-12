# Autopilot Dispatch Latency Optimization

## Closure note (2026-06-12, Fable 5 portfolio pass)

**Final outcome**: Core implementation landed 2026-05-26 and has been live through the continuous autopilot run since: phase heartbeat (`phase_status.py` + `/mnt/raid0/llm/tmp/autopilot_phase.{json,jsonl}`), dashboard idle-explanation panel (incl. the 2026-05-28 top-strip classification fix and `orphan inference` state), async auxiliary tasks (plots/digest off the critical path, durable writes kept synchronous), shorter configurable idle sleeps, and conservative contention-aware seeder role fan-out. Focused tests passed (19 unit tests across phase status, seed waves, dashboard helpers).

**Why archived**: core done; the remaining follow-ups are optional and none is a queue item. Operator policy + env knobs below remain the reference for interpreting dashboard idle states.

**Where residuals now live** (all optional, recorded here):
- **Request-level `trial_id`/`batch_id` stamping** through `call_orchestrator_forced` — **flagged HIGH blast-radius by GitNexus**; do this only with explicit operator acceptance and full regression tests across seeding legacy/per-role/EvalTower/model-grader callers. If accepted, coordinate with the fable5 per-question-ledger schema work (`autopilot-continuous-optimization.md` owns the autopilot evidence-plane changes).
- Phase-timing analyzer over `autopilot_phase.jsonl` (B), broader heavy-heavy seeder fan-out (C — requires the CRITICAL `_eval_single_config` edit; do not attempt mid-run), event-driven pause/health waits (D) — opportunistic only.

**Reopen triggers**: operator accepts the HIGH-risk request-level metadata edit, or a new dispatch-latency regression is measured at the autopilot layer (start from the phase heartbeat data, not from this file's queue).

---

**Status**: active implementation handoff; initial code landed 2026-05-26.
**Created**: 2026-05-26
**Updated**: 2026-05-26
**Priority**: HIGH
**Owner**: orchestrator/autopilot
**Related**: [`autopilot-continuous-optimization.md`](../active/autopilot-continuous-optimization.md), [`bulk-inference-campaign.md`](../active/bulk-inference-campaign.md), [`cross-role-nway-contention-matrix.md`](../completed/cross-role-nway-contention-matrix.md), [`within-role-placement-state-machine.md`](../active/within-role-placement-state-machine.md)

---

## Problem

The dashboard can show all CPU-region locks as ready while no model inference and no planner subprocess are visible. That state is ambiguous: it may mean the autopilot process is down, paused, in health backoff, building the planner prompt, doing post-trial bookkeeping, or sitting in a serial seeding path that under-feeds the now-parallel model stack.

Parallel dispatch raises the cost of that ambiguity. If the long bulk-inference session is meant to keep the stack saturated, every non-model gap must either be explained, shortened, or safely overlapped with other work.

---

## Current Findings

### Dashboard state interpretation

The CPU-region table is a readiness/placement view, not an activity view. `✅ ready to dispatch` means an instance shape is legal and not locked; it does not prove that the planner or autopilot dispatcher is alive.

The audited live state on 2026-05-26 showed:

- `uvicorn` was running.
- No `autopilot.py start` process was present.
- `logs/autopilot.log` ended with `Shutdown requested (signal 15)` at `2026-05-26T23:08:45Z`.

That specific idle dashboard state was therefore an autopilot-stopped/reload condition, not CPU lock contention.

Follow-up 2026-05-28: a separate top-strip classification regression was fixed after the dashboard showed `run state
quiet` while structured live tap and CPU-region lock panels still showed active frontdoor decode. The dashboard now
treats active structured tap requests or held CPU-region locks as inference-active for the top run-state label, and
shows `orphan inference` if those signals survive while autopilot itself is down. The same follow-up also scoped the
GEPA/Pareto and hypervolume panels to the latest journal segment after the current trial-id reset, pruned deprecated
pre-reset journal/state Pareto rows, and verified `/dashboard/api/pareto` as `source=journal_current_run` with frontier
`[38,71,76,77]`, 61 entries, 61 hypervolume points, and monotonic HV through trial 77.

### Root latency sources

1. **Invisible pre-planner work**
   - `scripts/autopilot/autopilot.py::_run_loop_inner` builds a large controller prompt before `invoke_controller()` opens the planner tap.
   - During this phase there is no inference tap and no planner tap activity.

2. **Serial seed batches**
   - `scripts/autopilot/species/seeder.py::Seeder.run_batch` loops questions serially.
   - `scripts/benchmark/seeding_eval.py::evaluate_question_per_role` previously looped roles serially.
   - EvalTower T0/T1/T2 already has concurrent fan-out, but the seed phase that often precedes it did not.

3. **Synchronous post-trial auxiliary work**
   - Journal/archive/state writes must remain ordered and durable.
   - Plot and digest generation are auxiliary and can be moved off the critical path after durable state writes.

4. **Contention/placement waits are not the main gap**
   - Contention gate and placement state-machine polling are both `150 ms`.
   - Human-visible gaps usually originate above the lock layer.

---

## Implementation Landed

Repository: `/mnt/raid0/llm/epyc-orchestrator`

### 1. Autopilot phase heartbeat

New file:

- `scripts/autopilot/phase_status.py`

Runtime artifacts:

- `/mnt/raid0/llm/tmp/autopilot_phase.json`
- `/mnt/raid0/llm/tmp/autopilot_phase.jsonl`

The heartbeat records:

- `phase`
- `trial_id`
- `action_type`
- `species`
- `phase_started_at`
- `phase_age_s`
- `updated_at`
- `pid`
- `idle_reason`
- optional prompt/session details

Instrumented phases include:

- `starting`
- `loop_start`
- `paused`
- `health_check`
- `health_backoff`
- `preflight`
- `observe`
- `planner_prompt_build`
- `planner_invoke`
- `planner_parse`
- `autonomous_select`
- `action_selected`
- `dispatch_action`
- `dispatch_complete`
- `safety_gate`
- `self_criticism`
- `record_trial`
- `post_trial_artifacts`
- `checkpoint`
- `async_plots_scheduled`
- `save_state`
- `async_digest_scheduled`
- `shutting_down`
- `stopped`

### 2. Dashboard idle explanation

Updated files:

- `src/api/routes/dashboard.py`
- `src/api/routes/dashboard.html`

`/dashboard/api/process_status` now includes:

- `autopilot_phase`
- `autopilot_phase_age_s`

The dashboard autopilot panel now shows the current phase and idle reason. If the phase file exists but the process is down, the dashboard annotates the phase as process-down instead of leaving the operator to infer from stale taps.

### 3. Safe async auxiliary tasks

New helper:

- `AsyncTaskRunner` in `scripts/autopilot/phase_status.py`

Default behavior:

- Enabled unless `AUTOPILOT_ASYNC_AUX=0`.
- Worker count from `AUTOPILOT_ASYNC_WORKERS`, default `2`.

Moved off the main loop:

- Periodic plot generation runs as `python autopilot.py plot`.
- Daily digest generation runs as `python autopilot.py digest --no-state-update`.

Durability rule:

- Journal/archive/state mutation remains synchronous.
- `last_digest_date` is updated synchronously before scheduling the digest subprocess, so a long digest cannot hold up the next trial and also cannot schedule duplicates every loop.
- Auto-checkpoint remains synchronous because it snapshots mutable working state and can race with the next trial if backgrounded.

### 4. Shorter explicit idle sleeps

Updated file:

- `scripts/autopilot/autopilot.py`

Runtime controls:

- `AUTOPILOT_PAUSE_POLL_S`, default `1`
- `AUTOPILOT_HEALTH_BACKOFF_S`, default `10`

Previous hardcoded waits were `10s` for pause polling and `30s` for unhealthy orchestrator backoff. The new defaults reduce operator-visible dead time while keeping both values configurable for noisy recovery scenarios.

### 5. Contention-aware seeder role fan-out

Updated file:

- `scripts/benchmark/seeding_eval.py`

New helpers:

- `_seed_role_concurrency_limit()`
- `_can_add_role_to_seed_wave()`
- `_seed_role_waves()`

Runtime control:

- `AUTOPILOT_SEED_ROLE_CONCURRENCY=auto` or unset: greedily use all matrix-safe role waves.
- `AUTOPILOT_SEED_ROLE_CONCURRENCY=1`: force legacy serial role evaluation.
- `AUTOPILOT_SEED_ROLE_CONCURRENCY=N`: cap each safe wave at `N` roles.

Safety policy:

- Uses `pair_policy(..., TrafficClass.BACKGROUND)` and `nway_policy(..., TrafficClass.BACKGROUND)`.
- Unknown, borderline-for-background, or measured-block combinations are not grouped.
- Roles sharing the same port are not grouped.
- At most one `HEAVY_PORTS` role is allowed per wave because `_eval_single_config` still has a legacy global heavy-port idle preflight and slot-erase path.
- The high-blast-radius leaf `_eval_single_config` was not modified.

Example with current common seed roles:

- `frontdoor + worker_general` can run in one wave.
- `coder_escalation` stays separate from `frontdoor` because both use port `8070`.
- `ingest_long_context` and `architect_general` stay separate from other heavy roles.

This is deliberately conservative: it reduces dead time without violating the old heavy-port cleanup assumptions.

---

## Explicit Non-Changes

GitNexus marked these as high or critical blast-radius:

- `scripts/benchmark/seeding_eval.py::_eval_single_config` — CRITICAL
- `scripts/benchmark/seeding_orchestrator.py::_call_orchestrator_with_slot_poll` — HIGH
- `scripts/benchmark/seeding_orchestrator.py::call_orchestrator_forced` — HIGH
- `scripts/autopilot/eval_tower.py::EvalTower._eval_batch` — HIGH

Therefore the implementation did not change their public contracts or core semantics.

Consequence:

- The structured live inference tap already supports `trial_id` and `batch_id`, but seed/eval HTTP callers still do not stamp those fields end-to-end through `call_orchestrator_forced`.
- The phase heartbeat now provides trial/action visibility at the autopilot layer; request-level `trial_id` propagation remains a follow-up only if the operator accepts the HIGH-risk benchmark-call contract edit.

---

## Operator Policy

### During bulk inference

Use the dashboard phase panel to classify apparent idle time:

- `autopilot DOWN`: restart or intentionally leave stopped.
- `paused`: resume only when host state is valid.
- `health_backoff`: inspect `/health` and stack logs.
- `planner_prompt_build`: no planner tap yet; this is local prompt assembly.
- `planner_invoke`: planner should be visible in the planner tap.
- `dispatch_action`: model activity should be visible unless the action is non-inference.
- `async_*_scheduled`: the trial loop should continue; auxiliary work should not block.

### Environment knobs

Recommended default for the bulk run:

```bash
AUTOPILOT_ASYNC_AUX=1
AUTOPILOT_ASYNC_WORKERS=2
AUTOPILOT_SEED_ROLE_CONCURRENCY=auto
AUTOPILOT_PAUSE_POLL_S=1
AUTOPILOT_HEALTH_BACKOFF_S=10
```

Debug fallback:

```bash
AUTOPILOT_SEED_ROLE_CONCURRENCY=1
AUTOPILOT_ASYNC_AUX=0
AUTOPILOT_PAUSE_POLL_S=10
AUTOPILOT_HEALTH_BACKOFF_S=30
```

### Baseline integrity

Do not mutate production baselines from any run unless the trial record contains valid speed semantics and topology/matrix status. Concurrent trials must continue using aggregate batch throughput for safety gates while preserving raw median request speed in details.

### Concurrency integrity

Seeder fan-out is only for roles that pass the background contention policy and the heavy-port guard. If the contention matrix is stale, missing, or invalid, the policy should naturally collapse toward serial waves for background traffic.

---

## Validation

Focused checks added:

- `tests/unit/test_autopilot_phase_status.py`
- `tests/unit/test_seeding_eval.py::test_seed_role_waves_group_matrix_safe_light_with_one_heavy`
- `tests/unit/test_seeding_eval.py::test_seed_role_waves_can_be_forced_serial`
- `tests/unit/test_dashboard_helpers.py::test_read_autopilot_phase_returns_dict`
- `tests/unit/test_dashboard_helpers.py::test_read_autopilot_phase_invalid_returns_empty`

Commands:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m py_compile scripts/autopilot/phase_status.py scripts/autopilot/autopilot.py scripts/benchmark/seeding_eval.py src/api/routes/dashboard.py
pytest -q tests/unit/test_autopilot_phase_status.py \
  tests/unit/test_seeding_eval.py::test_seed_role_waves_group_matrix_safe_light_with_one_heavy \
  tests/unit/test_seeding_eval.py::test_seed_role_waves_can_be_forced_serial \
  tests/unit/test_dashboard_helpers.py::test_read_autopilot_phase_returns_dict \
  tests/unit/test_dashboard_helpers.py::test_read_autopilot_phase_invalid_returns_empty
```

Executed verification in the implementation session:

- `py_compile` passed for touched autopilot, seeding, and dashboard modules.
- Focused pytest passed: `19 passed` across `tests/unit/test_seeding_eval.py`, `tests/unit/test_autopilot_phase_status.py`, and dashboard helper tests.
- Dashboard JavaScript syntax check with Node passed.
- Touched-file `git diff --check` passed. Full orchestrator diff-check remains blocked by pre-existing trailing whitespace in `scripts/autopilot/short_term_memory.md:99`.

---

## Follow-Up Work

### A. Request-level trial metadata

Only do this if explicitly accepted despite HIGH blast radius:

- Add backward-compatible optional metadata to `call_orchestrator_forced`.
- Thread `trial_id`, `batch_id`, and a parent `request_id` from autopilot seed/eval callers.
- Add regression tests across seeding legacy, per-role, EvalTower, and model-grader callers.

This is useful for request-grouped dashboards, but not required for the current phase heartbeat or safe seed fan-out.

### B. Phase timing report

Add a small analyzer over `/mnt/raid0/llm/tmp/autopilot_phase.jsonl`:

- phase p50/p95 duration
- time from trial complete to next planner start
- time spent prompt-building
- time spent dispatching vs model tap active
- async task failure count

Use this before further scheduler work.

### C. Broader seeder fan-out

The conservative first pass allows one heavy role plus light roles per wave. Full heavy-heavy fan-out requires changing the legacy heavy-port idle/erase path in `_eval_single_config`, which GitNexus marks CRITICAL. Do not attempt that during a bulk inference run.

### D. Event-driven pause/health waits

The current pause and health paths are now shorter/configurable, but still polling-based. After the dashboard phase panel is observed in production, consider making them event-driven. This is not a correctness blocker.
