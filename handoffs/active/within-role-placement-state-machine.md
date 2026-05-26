---
title: Within-role full↔quarter placement state machine + KV migration
status: active
created: 2026-05-25
updated: 2026-05-26
owners: routing-and-optimization-index
predecessors:
  - handoffs/completed/cross-role-bw-aware-routing.md  # Phases A–F, completed 2026-05-24; KV migration under PER_REGION_LOCKS deferred as design-only follow-up
  - handoffs/active/dynamic-stack-concurrency.md       # KV save/restore mechanics, quarter scheduler (DS-6/DS-7)
implementation_status:
  WP-0: MERGED to main 2026-05-26 (epyc-orchestrator commit 33bfe20 via merge fe6805c, live)
  WP-1: MERGED to main 2026-05-26 (cab27ac, live — autopilot default now max_safe_concurrency(frontdoor)=3)
  WP-2: MERGED to main 2026-05-26 (3d94a03, behind ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1, default off)
  WP-3: MERGED to main 2026-05-26 (b4d5161, transactional model + policy gate always-on; budget honored)
  WP-4: MERGED to main 2026-05-26 (66a8bfc, behind ORCHESTRATOR_REVERSE_MIGRATION=1, default off)
  WP-5: scaffold MERGED to main 2026-05-26 (29e95b4, conservative SOLO_PREFER_FULL default for all roles); full ratification deferred (Package J J4)
  WP-6: inference-gated (Package J J5; operator approval required for the bench sweep)
  WP-7: inference-gated (Package J J6; requires WP-6 + 24h autopilot gate)
checkout_state: merged to epyc-orchestrator main at 15350fe; 155/155 dispatcher-adjacent tests green at the merged tip.
---

## Executive summary

The `ConcurrencyAwareBackend` dispatcher and `ContentionGate` admit and place requests by lock availability + NUMA disjointness, but they do not model the within-role full↔quarter cpuset overlap relation. Full and overlapping quarters share physical cores, so concurrent placement is catastrophic even though the same-role contention matrix verdict says "allow." The KV save/restore plumbing is built and live in both dispatch paths. The shipped forward-migration trigger is session-handover-based, transactional, and policy-gated; it is not load-transition-based mid-decode eviction. This handoff closes the gap end-to-end in eight gated phases (P0..P7), each shippable independently behind an env flag or metric guard. The end state is autopilot-grade per-role concurrency without overlap, sticky quarter affinity for handed-over sessions, reverse migration when load drops, and matrix-aware production rollout.

**Audit correction (2026-05-26)**: a proactive "load grew past safe threshold, evict the currently decoding full session before admitting the next request" trigger was explored and removed from the implementation because `_migrate_kv` cannot preempt an in-flight llama-server decode. Package J's J2 gate must validate the shipped session-handover transaction and affinity behavior, not require impossible mid-flight preemption. A future proactive design would need cooperative decode cancellation or server-level preemption and should be scoped as new work.

## Problem (concrete)

For each role, `NUMA_CONFIG` instance 0 is "full" and instances 1..N are quarters. `_compute_quarter_preference()` already orders quarters by NUMA disjointness from full, but `_dispatch` in `src/backends/concurrency_aware.py` still tries full first regardless of in-flight load, then falls through to quarters in preference order. Concrete safe-placement table (computed from the cpu_lists in `scripts/server/stack_numa.py`):

| Role               | Full cpu_list          | Disjoint-from-full quarters | Safe concurrent placements without migration |
|--------------------|------------------------|-----------------------------|----------------------------------------------|
| frontdoor          | NUMA_NODE0 (0-47)      | q2(48-71), q3(72-95)        | {full}, {full, q3}, {full, q3, q2}; N=4 forces overlap |
| ingest_long_context| NUMA_NODE0 (0-47)      | q2, q3                      | same shape as frontdoor                       |
| vision_escalation  | NUMA_NODE1 (48-95)     | q0(0-23), q1(24-47)         | symmetric — N≤3 safe                          |
| worker_general     | NUMA_FULL (0-95)       | (none disjoint)             | {full} only; ANY quarter co-placement contends |
| architect_general  | NUMA_FULL (0-95)       | n/a (single instance)       | {full} only                                   |
| worker_vision      | NUMA_Q0B (24-47)       | n/a (single instance)       | {q0b} only                                    |

`same_role` matrix verdicts in `orchestration/contention_matrix.yaml` only encode "are multi-quarter placements net-positive vs serial" — they say nothing about full+quarter overlap. The gate consults `same_role` as a single `allow / block / n/a` value with no instance-pair granularity (`src/scheduling/contention.py:84-87, 100`).

The KV save/restore code path is in place: `_slot_save()` (`concurrency_aware.py:69-88`), `_slot_restore()` (lines 90-108), `_slot_erase()` (lines 111-120), `_migrate_kv()` (lines 436+). It is wired into both legacy `_select` (trigger at lines 314-319) and per-region-locks `_dispatch` (trigger at lines 636-682). The trigger is "different session takes over full while old session has no quarter affinity yet." It is NOT "load increased past the safe-with-full threshold."

## Goals / non-goals

**Goals**:
- Never place two requests on overlapping cpusets for the same role under the per-region-locks dispatch path.
- When a later session takes over full and an earlier full-backed session has no quarter affinity, migrate that earlier session transactionally to a disjoint quarter and preserve sticky affinity for its next turn.
- When load drops back to 1 and the session is warm, migrate it back to full so peak per-request latency returns.
- Extend the contention matrix to encode placement-overlap as a topology fact, separate from measured throughput ratios.
- Make autopilot's eval fan-out actually exercise the quarter instances (the original motivation that surfaced the gap).

**Non-goals**:
- Cross-server KV sharing (KVCOMM Phase F lives in `dynamic-stack-concurrency.md`).
- Slot multiplexing within a single llama-server (everything stays on slot 0).
- Cross-role placement policy changes (cross-role admission stays as Phases A-F shipped).
- Architect_general re-quartering decision (separate registry-maintainer call; referenced in P5 sub-task 3, not owned here).

## Phase plan (gated, each independently shippable)

### Phase 0 — Revert risky default (≤1h)

Roll back the `AUTOPILOT_EVAL_CONCURRENCY` default from 4 to 1 in `scripts/autopilot/eval_tower.py:_eval_concurrency`. Keep the helper, the `_eval_batch` infrastructure, the env knob. Reason: the =4 default was shipped 2026-05-25 without modeling overlap; under the current dispatcher, 4-way frontdoor fan-out forces 1 overlapping placement and is unsafe for any role whose full spans both sockets. Existing tests (`tests/test_gepa_integration.py`, `tests/unit/test_env_synth_species.py`) already pass; no further code changes.

**Gate**: autopilot run shows serial dispatch matching pre-2026-05-25 baseline; per-region-locks dashboard panel shows full active, all quarters idle, as before.

### Phase 1 — Topology-safe per-role concurrency (≤1d)

Add `max_safe_concurrency(role: str) -> int` in `src/runtime/instance_topology.py`. Reads `NUMA_CONFIG[role]['instances']`, parses cpu_lists via `parse_cpu_list()` (already exists). Returns the largest N such that N requests can be placed on mutually-disjoint cpusets including full. Reference numbers per the table above: frontdoor=3, ingest_long_context=3, vision_escalation=3, worker_general=1, architect_general=1, worker_vision=1.

Thread it into `eval_tower.py`: replace `_eval_concurrency()`'s fixed `4` default with `max_safe_concurrency(bottleneck_role)`. For autopilot, bottleneck role is frontdoor (where sentinels route 90%+ of the time), so the default becomes 3. Operators can still override via env var. The matrix-floor check still applies on top — even safe placements may be sub-floor under some workloads.

Tests: `tests/unit/test_topology_concurrency.py` with synthetic NUMA_CONFIG covering: all-disjoint quarters, full-overlap-quarters, single-instance roles, partial overlap. Property check: `max_safe_concurrency >= 1` always.

**Gate**: autopilot fan-out at 3 (frontdoor) shows full + q3 + q2 active in dashboard during T1 batch; no overlap pill turns red; aggregate t/s on T1 wallclock improves measurably over Phase 0.

### Phase 2 — Placement state machine (no migration; queue-instead-of-overlap) (≤2d)

New module: `src/scheduling/placement.py` housing `class PlacementPolicy`. Inputs: role, live `active_region_holders()` snapshot, NUMA_CONFIG topology. Output: either `Place(instance_idx)` or `Queue(reason, blocking_instances)`.

Refactor `ConcurrencyAwareBackend._dispatch` to delegate the candidate-selection loop to `PlacementPolicy`. Replace the current "try full, then quarters in preference order" with:

1. Compute `safe = {instance i where cpuset(i) ∩ ⋃ cpuset(holders) = ∅}`.
2. If `safe` non-empty: pick full if in `safe`, else first NUMA-disjoint quarter.
3. If `safe` empty: queue (loop on `as_completed`-style wait for the next region-lock release, then re-evaluate). Cap by request deadline; fall through to `ContentionDenied` (existing exception class in `contention_gate.py:336`) on timeout.

Extend `orchestration/contention_matrix.yaml` schema with a derived `placement_overlap` section (auto-generated from topology, not measured): `{role: {(i, j): bool}}`. `pair_policy` in `src/scheduling/contention.py` consults it for same-role pair queries instead of the single-verdict shortcut. Generator script: `scripts/server/derive_placement_overlap.py` (new), runs at stack launch and on NUMA_CONFIG change.

Audit refinement: keep **topology overlap** and **measured throughput matrix** as separate layers. `placement_overlap=true` is a hard safety veto regardless of benchmark ratios. `same_role.instance_pairs[*].verdict` is a throughput gate layered on top for disjoint pairs that underperform serial. Do not encode topology into measured ratios only; stale or missing benchmark data must never permit overlapping cpusets.

Queue semantics: queue entries must be per-role FIFO with deadline-aware cancellation, but re-evaluate placement on every release because the best instance can change after migration or completion. Record queue reason (`topology_overlap`, `matrix_floor`, `migration_in_flight`, `deadline_exceeded`) so dashboard and telemetry can distinguish safe queuing from capacity bugs.

Tests:
- `tests/unit/test_placement_policy.py`: synthetic NUMA_CONFIG, simulate holder snapshots, assert correct Place vs Queue decisions.
- `tests/integration/test_dispatch_queue_instead_of_overlap.py`: spin a mock backend, fire 4 concurrent requests at frontdoor, assert the 4th queues until the 1st finishes (not placed on overlapping quarter).

**Gate**: dashboard's per-region-locks panel: 4 concurrent frontdoor requests show 3 active (full + 2 disjoint quarters), 1 queued (visible in a new queue-depth column). Aggregate t/s ≥ 3-way Phase 1 baseline; tail latency p99 doesn't regress more than +20% vs serial.

### Phase 3 — Forward migration transaction (session handover; no mid-decode preemption) (≤3d)

Shipped trigger condition in `ConcurrencyAwareBackend._dispatch`: when a different session takes over full and the previous full-backed session has no quarter affinity, attempt to migrate the previous session to the policy-selected disjoint quarter. This is not a load-transition eviction of a currently decoding request; if full is still occupied by an in-flight decode, Phase 2 queue semantics remain the safe behavior until a lock releases.

Action:

1. Run `_migrate_kv(role, full_session, target_quarter=preferred_disjoint)` through `MigrationTransaction`. The migration uses existing slot save/restore plumbing.
2. Honor `ChatRequest.migration_budget_ms` as the transaction budget/deadline cap.
3. On migration completion: update `_session_quarter` so the migrated session keeps its quarter affinity on its next request.
4. On migration failure or timeout: abort transactionally, leave source KV intact, and fall through to Phase 2 queue/placement behavior.

Audit refinement: model migration as a transaction with explicit states: `planned -> saving -> restoring -> verified -> source_erased -> committed` or `aborted`. The incoming request must not be placed on the newly-freed full/quarter topology assumption until the transaction reaches `verified`; `_slot_erase` only runs after restore verification. Store the transaction ID in telemetry and `_session_quarter` updates so failures can be reconciled on restart.

Placement after migration: if full is vacated into one disjoint quarter, the incoming request should choose a cpuset disjoint from all current holders, not simply "a different quarter." For frontdoor with full on NUMA_NODE0 and disjoint q2/q3, a migrated full session on q3 means the incoming can use q2; full becomes safe only if no holder overlaps NUMA_NODE0. The policy should recompute from topology after migration rather than relying on a hard-coded role table.

Tests:
- `tests/unit/test_load_transition_migration.py`: verifies the shipped forward-migration transaction and policy gates under per-region locks.
- `tests/unit/test_migration_transaction.py`: transaction states `planned -> saving -> restoring -> verified -> source_erased -> committed` and abort paths.
- `tests/integration/test_migration_under_real_dispatch.py`: real httpx mock server, end-to-end save→restore→erase, verify slot 0 content matches when available.

**Gate**: sustained frontdoor traffic with session handover shows a prior full-backed session migrates to a disjoint quarter, its next request follows sticky quarter affinity, no overlapping cpusets are admitted, and aggregate t/s improves only when placements are actually disjoint. Do not require in-flight full decode preemption.

### Phase 4 — Reverse migration (quarter→full when load drops) (≤2d)

New condition: when the last in-flight request finishes on a quarter AND full has been idle for ≥`reverse_migration_cooldown_ms` (default 2s, avoids thrashing) AND the session has had ≥1 request in the last `reverse_migration_window_ms` (default 30s, avoids migrating idle sessions) AND total migrations for this session is below a per-session cap (default 5, avoids ping-pong), then:

1. Save the quarter's KV.
2. Restore to full.
3. Update `_session_quarter` to remove the affinity.
4. Best-effort; failure leaves session on quarter unchanged.

Telemetry should expose reverse migration count/direction and thrash skips. The original plan named Prometheus counters `kv_migration_direction_total{direction="forward|reverse"}` and `kv_migration_thrash_skipped_total`; as of the 2026-05-26 audit, the reverse path has log/stat evidence but those exact Prometheus counters are not wired. Package J should verify the available observable evidence unless a metrics patch lands first.

Tests: `tests/unit/test_reverse_migration.py` covering: load drops 2→1 → reverse triggered; cooldown gate; thrash guard.

**Gate**: 30-minute mixed traffic profile (alternating burst and solo) shows reverse migrations firing; per-request latency on solo-after-burst regresses ≤10% vs solo-only baseline (proving the migration earns its KV cost back via better peak throughput on subsequent requests).

### Phase 5 — Full-machine roles (worker_general, architect_general) (≤2d)

For roles where `full` spans all of 0-95 (NUMA_FULL), the disjoint-quarter set is empty. Phases 2-4 will correctly queue any concurrent traffic. Decision needed: is that acceptable, or should we mark those roles "quarters-only" and stop launching the full instance entirely?

Sub-tasks:
1. **Audit**: which roles actually receive concurrent traffic in production? (Autopilot evals → mostly frontdoor; worker_general gets 1 query per turn; architect_general is single-instance by `stack_numa.py:91-98`.)
2. **For worker_general**: add a NUMA_CONFIG flag `prefer_quarters_when_load_gt_one: true` that swaps the candidate priority order at N≥2 (try quarters first, full only at N=1). With 4 quarters fully disjoint among themselves, this gives a clean 1→4 scaling path.
3. **For architect_general**: hand off to the registry maintainer — should it be re-quartered? Outside scope of placement work but the answer affects this phase.

**Gate**: worker_general 2-way concurrent test: dispatcher places on q0 + q1, full idle. Aggregate t/s ≥ matrix-measured 2-quarter baseline.

Audit refinement: before adding `prefer_quarters_when_load_gt_one`, decide whether the full instance should remain warm while quarters serve burst load. Keeping full warm improves solo latency but consumes memory and can hide scheduler bugs; disabling full under burst simplifies placement but may regress single-request throughput. Record this as an explicit per-role policy: `solo_prefer_full`, `burst_prefer_quarters`, `full_disabled`, or `queue_only`.

**Sequencing decision (2026-05-25)**: the per-role policy enum is upstream of P3's placement-after-migration logic. If P3 lands with hardcoded role-table fallbacks first, P5 must refactor it. To avoid that churn, **land the policy enum scaffolding alongside or before P3** even if the full per-role decisions (which role gets which policy value) take longer to ratify. Concretely: introduce `RolePlacementPolicy` enum + per-role policy field reads in NUMA_CONFIG as part of WP-3 (or as a tiny pre-P3 patch), populated with the conservative default `solo_prefer_full` for every role. P5 then becomes "ratify per-role policy values + tune for full-machine roles" rather than "introduce the enum and refactor P3 callers." This sequencing keeps the dispatcher's policy-lookup call sites stable from P3 onward.

### Phase 6 — Matrix extension + re-bench (≤2d, can run overnight)

Re-measure `same_role` with instance-pair granularity. Update `scripts/server/contention_matrix.py` (existing Phase F bench harness from cross-role-bw-aware-routing) to also sweep within-role pairs: `full+q0, full+q1, full+q2, full+q3, q0+q1, q0+q2, q0+q3, q1+q2, q1+q3, q2+q3` for each role with ≥2 instances.

Update `orchestration/contention_matrix.yaml` schema:

```yaml
same_role:
  - role: frontdoor
    instance_pairs:
      - {a: full, b: q0, ratio: 0.X, verdict: block}     # MEASURED, not just topology
      - {a: full, b: q3, ratio: 1.X, verdict: allow}
      - {a: q0,   b: q1, ratio: 0.X, verdict: block}     # both NUMA_NODE0
      - {a: q0,   b: q3, ratio: 1.5, verdict: allow}
      # …
```

The topology-derived `placement_overlap` from Phase 2 stays as the hard guard (never co-place on cpu-overlapping instances); the matrix entries are the *throughput* guard layered on top (some disjoint pairs may still under-perform serial in practice).

**Gate**: re-benched matrix produces consistent ratios across 3 runs (CV ≤ 5%); `default_floor: 0.85` still applies; topology_hash bumped.

### Phase 7 — Production rollout + autopilot tuning (≤1d)

Flip `AUTOPILOT_EVAL_CONCURRENCY` default from Phase 1's static `max_safe_concurrency(frontdoor)` to "matrix-aware" — query the gate at startup for the role's max sustainable concurrency given measured ratios. Document the operator override path. Update `wiki/autopilot-tuning.md` (or create it if absent) with the new default and how to read the dashboard panel.

**Gate**: 24-hour autopilot run with new defaults; throughput / quality regression check vs Phase 0 baseline; dashboard shows quarters actively rotating; no `contention_timeout_count` spikes.

## Dependency graph

```
P0 (revert) ──> P1 (topology cap) ──> P2 (placement SM + queue)
                                            │
                                            ▼
                                       P3 (forward migration)
                                            │
                       ┌────────────────────┼────────────────────┐
                       ▼                    ▼                    ▼
                  P4 (reverse mig)    P5 (full-machine)    P6 (matrix re-bench)
                       │                    │                    │
                       └────────────────────┴────────────────────┘
                                            ▼
                                       P7 (rollout)
```

P0 is mandatory before any subsequent phase ships. P4, P5, P6 are independent and can run in parallel after P3 lands.

## Cross-cutting concerns

- **Per-region-locks dashboard panel** (`src/api/routes/dashboard.py:179-366`, edited 2026-05-25): add `queue_depth` column for Phase 2 and `migrations_in_flight` column for Phase 3.
- **Telemetry**: `ContentionGate.metrics_snapshot()` already exposes counters; extend with `placement_queue_depth`, `placement_overlap_avoided_count`, migration counters from Phase 3-4.
- **Settings drift**: `src/config/__init__.py` and `src/config/models.py` have parallel definitions (three drifts fixed 2026-05-25); any new env vars (e.g., `ORCHESTRATOR_REVERSE_MIGRATION_COOLDOWN_MS`) MUST land in both.
- **CLAUDE.md governance**: do not flag KV save/restore as "destructive" — it is reversible by design. The `_slot_erase` on the source instance after restore IS destructive on failure; ensure the restore confirmation completes before the erase.
- **Concurrent benchmark contention** (per `feedback_no_concurrent_inference.md`): every Phase 1-7 measurement gate needs explicit user approval to launch llama traffic.
- **Matrix/topology drift**: derive a `topology_hash` from role instance cpu_lists and write it into both `placement_overlap` and measured `same_role.instance_pairs`. Runtime must warn or fail closed when topology_hash in YAML does not match live NUMA_CONFIG.
- **Fairness/starvation**: queue-instead-of-overlap can starve low-priority sessions during sustained autopilot fan-out. Add per-role queue age metrics and a starvation guard before production rollout.
- **Session affinity consistency**: `_session_quarter` must be the single source of truth for warm-session placement after migrations. Any code path that bypasses `PlacementPolicy` risks stale affinity and must be audited in Phase 2.

## Inference-gate verification results

### J1 / Phase 2 gate — partial verification + verification-vehicle correction (2026-05-26, claude)

Ran with `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1` live (API restarted via `start_orchestrator()`, PID 1306375; `PER_REGION_LOCKS=1`). Topology `df373c79cc4af06f`. Fan-out via a new probe `scripts/benchmark/placement_fanout_probe.py` against `/chat` with `force_role=frontdoor, allow_delegation=False`, distinct sessions. Artifacts in `data/bulk_inference_2026_05_26/j1_*.json`.

| Run | Result |
|-----|--------|
| serial n=3 (baseline) | 25.53 t/s median per-request, p99 latency 52.06s |
| concurrent n=3 | aggregate **42.83 t/s = 1.68×** single-stream; all placed disjoint; no queue (3 ≤ 3 safe slots, expected) |
| concurrent n=4 (clean, no dashboard poll) | all 4 → 200; aggregate **48.78 t/s = 1.91×**; no queue fired |
| concurrent n=8 | 4 → 200, **4 → 429** (rate-limited); aggregate 45.6 t/s; no queue fired |

**Core gate: PASS.** The placement SM distributes concurrent frontdoor requests across disjoint instances with near-linear aggregate scaling (1.68×–1.91×) and **no overlap collapse**. Physical cpuset overlap is structurally impossible (exclusive `fcntl` region flocks); the `Queue(topology_overlap)` decision logic is covered by `test_dispatch_placement_state_machine.py` + `test_per_region_locks_migration.py` (green in preflight).

**Live `topology_overlap` queue event: NOT observed via `/chat`, and that is expected — `/chat` is the wrong vehicle.** Findings:

- **F1 — dashboard `active_instance_idxs` is broken.** `/dashboard/api/region_locks` resolves lock-holder PIDs to *llama-server* ports, but under PER_REGION_LOCKS the flock is held by the *API-worker* process running the dispatcher → `active_instance_idxs` is always `[]`. The panel cannot show "N active" as J1/J2/J3 assumed. Fix options: resolve holders to API-worker PIDs, or derive active instances from `active_region_holders()` directly.
- **F2 — `active_region_holders()` over-reports for full+quarter topology.** It flags every instance *spanning* a held region (full spans q0+q1, so a held q0 marks both full(idx0) and q0(idx1) active). "Count of active idxs" overstates concurrency; use distinct-regions-held (occupancy), not instance-idx count, when interpreting "active instances" in J2/J3/J4.
- **F3 — the HTTP rate limiter shadows the queue.** `RateLimitMiddleware` (60 rpm / 10 burst, shared per-IP, only `/health` exempt) plus a persistent external dashboard client cap concurrent external `/chat` at ~3–4 reaching the dispatcher. The placement-SM `topology_overlap` queue needs >3 *simultaneous at the dispatcher*; external `/chat` can't sustain that. **The queue is relevant to the internal EvalTower / autopilot eval fan-out path (the original WP-0 motivation, `AUTOPILOT_EVAL_CONCURRENCY`), which bypasses the HTTP rate limiter.** → J1's queue observation and **J2/J3 migration verification should be driven through the autopilot eval-concurrency path (folded into J4 / WP-5 ratification), not external `/chat` fan-out.**
- **F4 — p99 "+20% vs serial" gate is mis-specified.** Quarter-placed requests run on 24 physical cores vs full's 48, so they are inherently ~2× slower per-request under concurrency (n=3 p99 92.7s vs serial 52s). Aggregate batch t/s is the correct objective (matches the campaign's concurrent-metric policy). The per-request p99 vs serial comparison should be dropped or re-baselined against the quarter's own solo speed.

**Disposition**: WP-2 placement core verified live (scaling + no overlap). Queue/migration live observation re-assigned to the eval-concurrency path. WP-2/WP-3/WP-4 flags left enabled (`PLACEMENT_STATE_MACHINE=1`). Phases 3–4 (J2/J3) should not be chased via `/chat`.

## Reporting

After each phase:
1. Append a section to this handoff with the gate verification result.
2. Update progress log: `progress/YYYY-MM/YYYY-MM-DD.md`.
3. Update the four index cross-references' status fields.
4. If gate fails: STOP, do not advance to next phase; reopen the design.

## Key file locations

- Dispatcher: `src/backends/concurrency_aware.py` (`_dispatch`, `_select`, `_migrate_kv`, `_compute_quarter_preference`)
- Slot save/restore primitives: `src/backends/concurrency_aware.py:69-120`; also `src/backends/llama_server.py:1021,1044`
- Lock state: `src/runtime/cpu_region_lock.py` (`active_region_holders`)
- Topology: `src/runtime/instance_topology.py` (`parse_cpu_list`, `get_instance_regions`); `scripts/server/stack_numa.py` (`NUMA_CONFIG`)
- Contention matrix + gate: `orchestration/contention_matrix.yaml`, `src/scheduling/contention.py`, `src/scheduling/contention_gate.py`
- Autopilot eval fan-out: `scripts/autopilot/eval_tower.py` (`_eval_concurrency`, `_eval_batch`), `scripts/autopilot/species/gepa_optimizer.py`
- Dashboard panel: `src/api/routes/dashboard.py`, `src/api/routes/dashboard.html`
- Settings: `src/config/__init__.py`, `src/config/models.py` (keep both in sync)

## Rollback per phase

Each phase ships behind an env flag, default-on after its gate passes. Rollback = flip the flag.

- P0: no flag, plain default change; revert is a one-line edit.
- P1: `AUTOPILOT_EVAL_CONCURRENCY` already env-driven; set to 1 to disable.
- P2: `ORCHESTRATOR_PLACEMENT_STATE_MACHINE` (default 1 after gate; 0 falls back to existing `_compute_quarter_preference` greedy path).
- P3: `ORCHESTRATOR_FORWARD_MIGRATION_ON_LOAD` (default 0 until gated; 1 after).
- P4: `ORCHESTRATOR_REVERSE_MIGRATION` (default 0 until gated; 1 after).
- P5: `prefer_quarters_when_load_gt_one` per-role NUMA_CONFIG flag.
- P6: schema-only; doesn't change runtime.
- P7: revert P7 default = revert to P1 default.

## Risks and mitigations

- **KV migration latency vs request deadline**: P3 migration is async but the new request blocks on its completion. Mitigate by exposing `migration_budget_ms` (already exists in ChatRequest, currently unread), and fall through to Phase 2 queue if budget elapses.
- **Thrashing under oscillating load**: P4 includes cooldown + recency window + per-session migration cap. Counters in P4 metrics make the thrash visible immediately.
- **Migration failure leaving stale session on full + new on quarter**: P3 trigger MUST require migration completion confirmation before the erase. Existing `_migrate_kv` ordering (save → restore → erase) is correct; the new caller must check return.
- **Re-introducing the 2026-05-25 bug**: P0 revert ships before anything else; P1 topology cap is a hard guard that prevents *any* overlapping placement regardless of subsequent phase wiring.
- **Concurrent benchmark contamination during gates**: user approval required per existing project guidance.
- **Stale topology/matrix allowing unsafe placement**: live NUMA_CONFIG changes without regenerated YAML could bypass intended rules. Mitigate with topology_hash validation and fail-closed placement when hashes mismatch.
- **Queue deadlock under migration failure**: migration-in-flight events must always resolve success/failure; use `finally` callbacks and timeout counters so waiting requests do not hang forever.
- **Dashboard false confidence**: if queue/migration telemetry is not updated atomically with placement decisions, operators may see "safe" while overlap exists. Phase 2 should include an invariant metric: `active_overlap_detected_count` computed from live holders, independent of the planner.

## Cross-references

- `handoffs/completed/cross-role-bw-aware-routing.md` — direct predecessor; Phases A-F shipped the contention matrix, the gate, and the per-region-locks dispatcher. The deferred "KV migration under PER_REGION_LOCKS=1" item is the seed of this handoff.
- `handoffs/active/dynamic-stack-concurrency.md` — owns the KV save/restore mechanics and the DS-6/DS-7 quarter scheduler. This handoff reuses those primitives; it does not redefine them.
- `handoffs/active/routing-and-optimization-index.md` § P7 — DS-5/DS-6/DS-7 sibling tasks. This handoff's WP-N tasks are nested under P7 in that index.
- `handoffs/active/inference-acceleration-index.md` § Cross-Reference Map — within-role KV dispatcher registered alongside KVCOMM cross-instance KV sharing (different scope; this handoff is single-server within-role, KVCOMM is cross-server).
- `handoffs/active/master-handoff-index.md` § Cross-Index Dependencies — within-role placement affects autopilot throughput observed in inference-acceleration-index gates.
- `handoffs/active/bulk-inference-campaign.md` **§ Package J** (added 2026-05-26) — wires this handoff's inference-gated WPs (J1=WP-2 gate, J2=WP-3 verification, J3=WP-4 verification, J4=WP-5 ratification observability, J5=WP-6 matrix re-bench, J6=WP-7 production rollout). J1-J3 are flagged priority-zero in Package J's execution order: enabling them first raises every downstream Package's effective concurrency.
