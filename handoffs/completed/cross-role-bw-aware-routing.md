# Cross-role BW-aware request routing + dynamic full/quarter migration

**Status**: ✅ IMPLEMENTED 2026-05-24 (phases A-F shipped; KV-migration-under-PER_REGION_LOCKS port deferred as design-only follow-up — disabled+reported per Phase E acceptance)
**Owners**: routing-and-optimization-index
**Related**: [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) Part 2-4, [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md)
**Source data**: `/workspace/tmp/contention_matrix_results.txt`, `/workspace/tmp/contention_matrix_v2_results.txt`, `/workspace/tmp/contention_matrix_v3_results.txt`, `/workspace/tmp/teardown_bench.log`
**Shipped code**: `orchestration/contention_matrix.yaml`, `src/scheduling/{contention.py,contention_gate.py}`, `src/runtime/cpu_region_lock.py:active_region_holders()`, `src/api/models/requests.py:ChatRequest.{max_queue_wait_ms,migration_budget_ms}`, `src/llm_primitives/{inference.py,primitives.py}` integration, `src/backends/concurrency_aware.py:{_compute_quarter_preference,kv_migration_status}`, `scripts/server/contention_matrix.py`, `scripts/validate/check_contention_matrix_fresh.py`, `scripts/benchmark/seeding_orchestrator.py` (Phase C autopilot stamping). **135/135 unit tests passing.**

## Executive Summary

The 2026-05-24 frontdoor throughput drop was not a launcher regression. A clean-stack teardown bench shows frontdoor solo at **24.94 t/s**. The observed 4-10 t/s happens when autopilot or another caller decodes a high-contention role at the same time.

The fix belongs in the orchestrator scheduling layer:

1. Persist the measured role-pair contention matrix with enough metadata to know when it is stale.
2. Gate **background/autopilot** requests behind active foreground traffic when the pair is known-bad or unknown.
3. Gate any new request behind an active decode when the pair is known catastrophic and the latency budget allows waiting.
4. Keep same-role quartering, but make quarter selection topology-aware and do not rely on KV migration until the active dispatch path is verified to use it.

This handoff is close to implementable, but the first shipped change should be the cross-role contention gate. Dynamic migration and full/quarter reshaping are second-order until foreground traffic is protected from autopilot.

## Current Implementation Surface

Impact check before editing this handoff:

- `ConcurrencyAwareBackend`: upstream impact LOW, 3 import dependants, no affected execution flows.
- `NUMA_CONFIG` variable in `scripts/server/stack_numa.py`: upstream impact LOW, no upstream dependants reported by GitNexus.

Relevant live code in `epyc-orchestrator`:

| Area | Current state | Notes |
|---|---|---|
| Intra-role full/quarter backend | `src/backends/concurrency_aware.py:121-690` | Routes `full:` prefixed roles to 1 full instance plus quarters. Legacy path can migrate an old session from full to a quarter via slot save/restore. |
| Cross-process region locks | `ConcurrencyAwareBackend._dispatch()` | `scripts/server/orchestrator_stack.py:start_orchestrator()` sets `ORCHESTRATOR_PER_REGION_LOCKS=1` by default. Production dispatch picks the first CPU-region lock it can acquire. This path updates telemetry but does **not** perform the legacy KV migration flow. |
| Region-lock owner truth | `src/runtime/cpu_region_lock.py:_current_lock_owner_pids()` | Best available cross-process source of "which CPU region is held" today. Phase B must use this lock-holder state or an equivalent shared registry, not per-worker in-process counters. |
| Active request tracking | `_full_active`, `_quarter_active`, `session_affinity`, optional CPU-region locks | Tracks activity inside a role. It does not expose a global "role X is decoding" scheduler primitive. |
| Topology source | `scripts/server/stack_numa.py:43+` `NUMA_CONFIG` | Source of truth for role instance ports, CPU sets, thread counts, mlock, and `numactl_policy`. |
| Quarter lifecycle scaffold | `scripts/server/quarter_scheduler.py` | Health/assignment/burst scaffold exists. It is not yet the right place to solve cross-role decode contention. |
| Backend construction | `src/llm_primitives/backend.py:_init_caching_backends()` | `full:` URL prefix creates `ConcurrencyAwareBackend`; comma-separated URLs without `full:` use round-robin. |
| API request priority | `src/api/models/requests.py:ChatRequest.request_priority` | Existing field currently distinguishes `interactive` vs `background`. Phase B can extend this into `traffic_class` semantics and add a max queue-wait budget. |

Important correction to the prior draft: "intra-role migration is stable" is only true for the legacy `ConcurrencyAwareBackend` path. Per-region locks are enabled by default in production, so the dispatch path currently chooses instances with locks and bypasses migration. The Phase E migration caveat is load-bearing.

## Problem

The orchestrator can route within a role, but it has no cross-role bandwidth model. CPU MoE decode is primarily DRAM-bandwidth bound. When two heavy decoders share the wrong NUMA resources, both collapse even if each role is individually configured correctly.

The painful case is autopilot seeding. A seed batch probes multiple roles per trial. Those probes are useful, but today they are scheduled without regard to live foreground traffic or to each other. When a probe lands on `ingest_long_context` or `architect_general` while `frontdoor` is decoding, the host splits finite DRAM bandwidth between them and the foreground request pays the latency cost.

This is a scheduler failure, not a per-role config failure. The per-role NUMA configs were reverted and validated on 2026-05-24; frontdoor solo still hits the expected ceiling.

## Empirical Foundation

Measurement convention:

- Sequential aggregate = total tokens / sum(per-role elapsed).
- Parallel aggregate = total tokens / max(per-role elapsed).
- Ratio = parallel aggregate / sequential aggregate.
- Ratio > 1.0 means concurrent execution improves aggregate throughput.
- Ratio < 1.0 means concurrent execution loses aggregate throughput; below 0.85 should normally be blocked for background traffic.

### Primary-instance cross-role pairs

13 primary-instance cross-role pairs have complete measurements. The six-role matrix would contain 15 pairs; `ingest_long_context + worker_vision` and `architect_general + worker_vision` are not complete in the current artifacts and should be treated as unknown.

| Pair | Topology | Seq agg | Par agg | Ratio | Policy |
|---|---|---:|---:|---:|---|
| frontdoor + ingest_long_context | both NUMA_NODE0 | 19.52 | 7.30 | **0.37** | block |
| frontdoor + architect_general | NUMA_NODE0 + NUMA_FULL | 16.96 | 8.52 | **0.50** | block |
| ingest_long_context + architect_general | NUMA_NODE0 + NUMA_FULL | 14.08 | 8.38 | **0.60** | block |
| architect_general + vision_escalation | NUMA_FULL + NUMA_NODE1 | 18.04 | 10.65 | **0.59** | block |
| frontdoor + worker_vision | NUMA_NODE0 overlaps Q0B | 13.85 | 8.81 | **0.64** | block for background; foreground by SLO |
| frontdoor + vision_escalation | NUMA_NODE0 + NUMA_NODE1 | 26.60 | 22.29 | **0.84** | borderline; block background by default |
| worker_general + worker_vision | 0-95 overlaps Q0B | 16.56 | 17.74 | **1.07** | allow |
| worker_general + architect_general | both use 0-95 / interleave | 21.27 | 23.56 | **1.11** | allow |
| ingest_long_context + worker_general | NUMA_NODE0 + 0-95 | 25.43 | 29.98 | **1.18** | allow |
| frontdoor + worker_general | NUMA_NODE0 + 0-95, gemma4 MTP | 34.64 | 44.44 | **1.28** | allow |
| vision_escalation + worker_vision | NUMA_NODE1 + Q0B | 14.44 | 19.15 | **1.33** | allow |
| ingest_long_context + vision_escalation | NUMA_NODE0 + NUMA_NODE1 | 17.60 | 25.21 | **1.43** | allow |
| worker_general + vision_escalation | 0-95 + NUMA_NODE1 | 37.47 | 55.44 | **1.48** | allow |

### Same-role and multi-instance findings

| Combo | Seq agg | Par agg | Ratio | Policy implication |
|---|---:|---:|---:|---|
| frontdoor q0 + q1 | 23.11 | 28.39 | **1.23** | Same-role quartering is useful even on one NUMA node. |
| frontdoor q0 + q3 | 23.63 | 35.38 | **1.50** | Prefer cross-node quarters when possible. |
| frontdoor q0 + q2 | 23.28 | 36.71 | **1.58** | Prefer cross-node quarters when possible. |
| frontdoor full + own q3 | 21.52 | 36.86 | **1.71** | Full + one disjoint quarter can be excellent. |
| frontdoor 4 quarters, no full | 23.32 | 43.83 | **1.88** | Four quarters beat solo for aggregate throughput. |
| frontdoor full + 4 quarters | 21.66 | 19.05 | **0.88** | Do not run full plus all quarters as one 5-way mode. |
| ingest_long_context 4 quarters | 13.55 | 38.76 | **2.86** | Strongest same-role quartering result. |
| vision_escalation 4 quarters | 26.34 | 7.75 | **0.29** | Anomaly. Leave the already-deployed quarters live, but the scheduler should treat `vision_escalation + vision_escalation` as blocked for concurrent admission until investigated. |

Timing caveat: the matrix artifacts were produced during the same correction window as the frontdoor/ingest/vision NUMA reverts. Persisted YAML must store per-pair CPU lists and launch args, not just role names, so reruns after Phase F can explain small topology-era deltas instead of treating them as drift.

### Triples

| Triple | Seq agg | Par agg | Ratio | Conclusion |
|---|---:|---:|---:|---|
| frontdoor + worker_general + vision_escalation | 32.47 | 46.95 | **1.45** | N-way concurrency is viable when every pair is acceptable. |
| frontdoor + worker_general + ingest_long_context | 21.77 | 10.61 | **0.49** | One catastrophic pair poisons the whole set. |

## Production Policy

### Pair threshold

Use a default `CONTENTION_RATIO_FLOOR = 0.85`.

- `ratio >= 1.0`: allow in parallel.
- `0.85 <= ratio < 1.0`: allow for foreground latency; configurable for background workloads.
- `ratio < 0.85`: block or delay unless the incoming request has an explicit low-latency override.
- Unknown pairs: treat as **blocked for autopilot/background** and **allowed for foreground only if waiting would violate SLO**. Unknown should also emit a metric and a "matrix incomplete" warning.
- Missing or stale matrix file: fail open for foreground runtime admission so a fresh install or first boot after stack change does not break the orchestrator. Emit a loud structured warning, expose a dashboard/status badge (`contention_matrix: missing|stale`), and block autopilot from starting new background campaigns unless explicitly overridden. Do **not** synchronously generate the matrix during startup; matrix benches are disruptive decode workloads and must run only in an explicit maintenance/idle window. Startup should instead enumerate missing/stale combinations and enqueue or advertise a re-bench action.

The original draft used "default unknown ratio = 1.0". That is efficient but unsafe for this incident class; unknown pairs should not let autopilot discover catastrophic contention against live users.

### Priority

The scheduler needs request classes:

| Class | Examples | Default behavior |
|---|---|---|
| Foreground interactive | chat/frontdoor user request | May run through borderline pairs; should not be blocked behind long background probes unless the pair is catastrophic and the wait estimate is short. |
| Foreground specialist | user-visible escalation | Same as foreground, but can tolerate longer queueing than frontdoor. |
| Background/autopilot | seed_batch, numeric trials, matrix bench | Must yield to active foreground decodes and must serialize against known-bad or unknown pairs. |
| Maintenance | validation, re-bench | Runs only under explicit operator control or idle windows. |

The non-preemptive limitation matters: once a background llama-server decode is in flight, the orchestrator cannot cheaply stop it without request cancellation semantics. So the first practical mitigation is **admission control before starting background probes**, not attempted mid-decode preemption.

### N-way rule

When a request for role `R` arrives, compare `R` against every active decoding role. Let `min_ratio` be the minimum known pair ratio. If any active pair is unknown, apply the unknown policy above. If any known pair is below the floor, queue according to priority and latency budget.

Explicit allow case: if every active pair has a known ratio at or above the floor, allow N-way concurrency. Do not require a directly measured N-way tuple before allowing the request.

Pairwise filtering is supported by the triple data: the all-good triple wins, while the triple containing `frontdoor + ingest_long_context` collapses.

## Architecture Target

Introduce a small cross-role contention gate ahead of backend selection.

```
request arrives for role R
  |
  |-- classify traffic: foreground / background / maintenance
  |
  |-- snapshot active decodes across roles
  |     (region-lock holders when ORCHESTRATOR_PER_REGION_LOCKS=1)
  |
  |-- evaluate pair policy for R vs each active role
  |     |
  |     |-- all pairs allowed -> enter role backend
  |     |
  |     |-- blocked pair exists
  |          |
  |          |-- background -> queue/yield
  |          |-- foreground -> wait if predicted wait is within SLO,
  |                         otherwise allow only under explicit degradation policy
  |
  |-- role backend selects full or quarter instance
```

The gate should wrap the call site that invokes `backend.infer*()` rather than be buried in `ConcurrencyAwareBackend`. Cross-role contention is a global scheduling concern; `ConcurrencyAwareBackend` only knows one role.

Concrete integration points to evaluate first:

- `src/llm_primitives/inference.py:_real_call()` around the existing backend call sites (`infer_stream_text` / `infer`) is the likely central wrapper. It sees the resolved role, request timeout budget, backend URL, cancellation checks, and already branches on `ORCHESTRATOR_PER_REGION_LOCKS`.
- `src/api/routes/chat.py:_handle_chat()` direct-mode dispatch is the API-facing place to stamp foreground request metadata before the call reaches primitives.
- Autopilot/seeding callers already use `ChatRequest.force_role`; they should also set background priority/queue metadata before submitting `/chat`.

## Implementation Plan

### Phase A - Persist the contention matrix

Create `orchestration/contention_matrix.yaml` generated from the bench artifacts.

Minimum schema:

```yaml
version: 1
measured_at: "2026-05-24T12:48:38Z"
host: "Beelzebub"
binary:
  llama_server_path: "..."
  git_commit: "..."
topology_hash: "sha256 of NUMA_CONFIG role instance entries"
default_floor: 0.85
pairs:
  - roles: ["frontdoor", "ingest_long_context"]
    instance_a: {port: 8070, cpu_list: "0-47,96-143", threads: 96}
    instance_b: {port: 8085, cpu_list: "0-47,96-143", threads: 96}
    seq_aggregate_tps: 19.52
    parallel_aggregate_tps: 7.30
    ratio: 0.37
    samples: 1
    verdict: "block"
```

Add `src/scheduling/contention.py`:

- `load_contention_matrix(path) -> ContentionMatrix`
- `contention_ratio(role_a, role_b) -> float | None`
- `pair_policy(role_a, role_b, traffic_class, floor=0.85) -> PairDecision`
- `matrix_status(path, topology_hash) -> MatrixStatus` with `ok|missing|stale|invalid`
- `topology_fingerprint(NUMA_CONFIG) -> str`

Tests should cover sorted role keys, unknown pairs, threshold boundaries, stale topology detection, and fail-open runtime behavior for missing/stale matrices.

### Phase B - Admission gate for active decodes

Add a scheduler wrapper near the central model-call boundary:

- Track active decode counts by role from the authoritative cross-process source.
- With `ORCHESTRATOR_PER_REGION_LOCKS=1`, do **not** trust `ConcurrencyAwareBackend._full_active` / `_quarter_active` for admission. Read CPU-region lock holders from `src/runtime/cpu_region_lock.py` or factor that code into a supported `active_region_holders()` helper.
- Track traffic class, request id, and max queue wait.
- Before starting a decode, evaluate the new role against the active set.
- Queue/yield background traffic on known-bad or unknown pairs.
- Emit metrics: `contention_blocked_count{role,other_role}`, `contention_wait_seconds`, `active_decodes_by_role`, `contention_unknown_pair_count`.

Initial API surface:

- Reuse `ChatRequest.request_priority` for `interactive` vs `background` unless a broader `traffic_class` enum is introduced.
- Add `ChatRequest.max_queue_wait_ms` or equivalent request metadata; default interactive waits should be short, background waits can be long/backoff-driven.
- Internally carry `traffic_class`, `max_queue_wait_ms`, `task_id/session_id`, and `force_role` into the gate.

Candidate call sites:

- **Primary**: wrap **`src/llm_primitives/inference.py:_real_call_impl()`** (or `_real_call_single()`) — those are the variants that actually invoke `backend.infer_stream_text(...)` / `backend.infer(...)`. The outer `_real_call()` at line 77 is a budget/diagnostics wrapper that delegates downward; wrapping it would miss the backend dispatch.
- API metadata stamping: `src/api/routes/chat.py:_handle_chat()` (line 363) before Stage 8 direct/delegated/REPL execution.
- Seeder/autopilot stamping: set background priority in the seeding `/chat` request construction path.

Avoid naming the module `queue.py`; use `contention_gate.py` or `admission.py` to avoid confusion with the Python stdlib module.

**Ordering vs `_acquire_role`**: the gate MUST run BEFORE `LLMPrimitives._acquire_role()` (`src/llm_primitives/primitives.py:432-443`). If the gate admits a request and then `_acquire_role` blocks on its per-role threading semaphore, the gate's `active_decodes_by_role` snapshot is briefly stale (request "admitted" but not yet actually decoding). Running the gate first means: (1) we check the cross-role contention against the truly active set, (2) the request waits on its own role's semaphore (intra-role limit) after admission, which doesn't affect other roles' admission decisions.

**Shared helper required**: factor `cpu_region_lock._current_lock_owner_pids()` (currently a private helper) into a public **`active_region_holders() -> dict[str, list[int]]`** returning `{role: [instance_idx, ...]}` rather than `[pid_str, ...]`. The gate consumes this; tests mock it. Without this factoring the gate either reaches into a private API or duplicates the file-glob+flock-probe logic.

This phase is the highest-value short-term fix. It directly prevents autopilot probes from crushing frontdoor.

### Phase C - Autopilot integration

Autopilot should become a polite background client:

- Attach `traffic_class=background` to seed_batch and trial requests.
- Ask the contention gate for a permit before each role probe.
- Back off or skip a probe when a foreground-active pair is blocked.
- Log skipped/delayed probes so evaluation speed regressions are explainable.

This is better than adding a global decode lock. A global lock fixes the incident but throws away known-good concurrency such as `frontdoor + worker_general` and `worker_general + vision_escalation`.

### Phase D - Topology-aware quarter selection

Once the gate is in place, improve `ConcurrencyAwareBackend` selection:

- Pass instance metadata from `NUMA_CONFIG` into the backend or a side table.
- Prefer idle quarters on the opposite NUMA half from the active full instance.
- For frontdoor/ingest full on NUMA_NODE0, prefer Q1A/Q1B before Q0A/Q0B.
- Do not schedule `full + all 4 quarters` as a normal mode; the matrix shows it loses.

Preferred quarter order:

| Active full instance | Preferred quarter order |
|---|---|
| Full on NUMA_NODE0 (`0-47,96-143`) | q3 -> q2 -> q1 -> q0 |
| Full on NUMA_NODE1 (`48-95,144-191`) | q0 -> q1 -> q3 -> q2 |
| Full on NUMA_FULL (`0-95`) | any; no truly disjoint quarter exists |

This phase should include tests for deterministic preference order and fallback when preferred quarters are busy.

### Phase E - KV migration budget

Add a per-request migration decision only after Phase D is correct.

Inputs:

- Estimated remaining generated tokens.
- Context tokens / saved-state size proxy.
- Request traffic class.
- Target pair ratio and expected parallel-decode duration.

Rule of thumb:

- Short foreground turns should usually queue or use an already-idle slot rather than pay a 1-5 s migration.
- Long conversations and background probes can amortize migration if the destination topology is good.

Critical implementation caveat: if `ORCHESTRATOR_PER_REGION_LOCKS=1` is required in production, the migration logic must be ported into that dispatch path or migration must be marked disabled. Do not assume the legacy migration path is active.

### Phase F - Canonical matrix re-bench tooling

Build `scripts/server/contention_matrix.py` as the canonical replacement for the ad hoc `/workspace/tmp/contention_matrix*.sh` scripts.

Requirements:

- Read role/instance topology from `NUMA_CONFIG`.
- Select relevant full/full, quarter/quarter, and same-role combinations.
- Smart-prune after catastrophic pairs, but record skipped pairs explicitly as `unknown` or `skipped_due_to`.
- Write `orchestration/contention_matrix.yaml`.
- Include enough environment metadata to invalidate stale data: binary path, binary git commit, model path/hash, launch args, `NUMA_CONFIG` fingerprint, host uptime, kernel, BIOS/NPS if available.

Add validation:

- `scripts/validate/check_contention_matrix_fresh.py`
- `orchestrator_stack.py validate --contention-matrix`
- CI/pre-commit warning when `NUMA_CONFIG` or role model config changes without matrix refresh.

Startup behavior:

- On orchestrator startup, compute the topology hash and compare it with the stored matrix.
- If the matrix is missing, stale, or lacks pairs for live roles, expose that as degraded scheduler metadata and list the missing combinations.
- Do not auto-run pair benches inline with startup. Generating the matrix launches real decode workloads across role combinations, can crush foreground latency, and may require stack topology/control-plane operations that should not happen while the API is trying to become healthy.
- Provide an explicit `--fill-missing` / maintenance command that runs only when the operator or autopilot maintenance policy grants an idle window.

## Short-term Mitigation

Until the full scheduler lands, implement the smallest safe behavior:

1. Add a contention gate with the current matrix hardcoded or loaded from YAML.
2. Mark autopilot/seeder requests as background.
3. Serialize background probes when any foreground decode is active for a blocked, borderline, or unknown pair.
4. Keep known-good parallelism enabled for measured safe pairs.

This avoids the overcorrection of a global decode lock while protecting frontdoor from the exact measured failures: `frontdoor + ingest_long_context`, `frontdoor + architect_general`, and `frontdoor + worker_vision`.

## Open Issues

- Complete the two missing full-pair measurements: `ingest_long_context + worker_vision`, `architect_general + worker_vision`.
- Investigate the `vision_escalation` 4-quarter anomaly before using vision quartering as a production aggregate-throughput strategy.
- Production runs with `ORCHESTRATOR_PER_REGION_LOCKS=1` by default. Update migration implementation/tests accordingly before relying on KV migration.
- Decide foreground catastrophic-pair behavior by SLO: wait, allow degraded parallelism, or return an explicit busy/backpressure response.
- Decide whether matrix drift can be estimated from production telemetry or only from controlled benches.
- Review whether the current per-role concurrency semaphores in `src/llm_primitives/primitives.py` interact cleanly with the new gate, especially for batch calls and delegated/repl flows.
- Decide dashboard/operator UX for `contention_matrix` status, blocked background probes, and active region-lock holders.

## Acceptance Criteria

- [x] `orchestration/contention_matrix.yaml` exists with measured pairs, unknown/skipped pairs, topology metadata, and threshold policy. (13 pairs + 6 same-role + 2 unknown, topology_hash=df373c79cc4af06f)
- [x] `src/scheduling/contention.py` loads and validates the matrix, with unit tests for unknowns and stale topology. (24 tests pass)
- [x] Cross-role admission gate tracks active decodes across roles from region-lock holders when per-region locks are enabled, and blocks background traffic on known-bad or unknown pairs. (`src/scheduling/contention_gate.py` + `src/runtime/cpu_region_lock.py:active_region_holders()`, 18 tests)
- [x] Missing/stale matrix fails open for interactive runtime, emits metrics/warnings, and blocks background campaigns unless explicitly overridden. (`pair_policy()` fail-open + `matrix_status()` MISSING/STALE/INVALID enum)
- [x] Autopilot seed_batch requests use background priority/traffic class and respect contention permits. (`scripts/benchmark/seeding_orchestrator.py:561+` sets `request_priority="background"` + `max_queue_wait_ms`)
- [x] API requests can carry a max queue-wait budget into the gate. (`ChatRequest.max_queue_wait_ms` + `request_context(max_queue_wait_ms=...)` ContextVar)
- [x] Metrics expose blocked counts, wait time, active decode counts, and unknown-pair encounters. (`ContentionGate.metrics_snapshot()`)
- [x] `ConcurrencyAwareBackend` quarter choice prefers topology-disjoint quarters, with tests. (`_compute_quarter_preference()`, 7 tests confirm frontdoor→[q2,q3 first], vision_escalation→[q0,q1 first])
- [x] Per-region lock mode either supports KV migration or clearly disables/reports it. (`kv_migration_status()` reports `enabled=False` under PER_REGION_LOCKS=1, follow-up logged for proper port)
- [x] `scripts/server/contention_matrix.py` is the canonical re-bench tool and `validate --contention-matrix` detects stale matrices. (subcommands `run` + `validate`; `scripts/validate/check_contention_matrix_fresh.py` for pre-commit/CI)
- [ ] Operator docs in `program.md` describe when to re-run the matrix and how to interpret block/allow decisions. **deferred — small doc-only follow-up; doesn't gate the runtime fix**

## Files Referenced

- `/mnt/raid0/llm/epyc-orchestrator/src/backends/concurrency_aware.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_numa.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/quarter_scheduler.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/llm_primitives/backend.py`
- `/workspace/tmp/contention_matrix_results.txt`
- `/workspace/tmp/contention_matrix_v2_results.txt`
- `/workspace/tmp/contention_matrix_v3_results.txt`
- `/workspace/tmp/teardown_bench.log`
- [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md)
- [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md)

## Out of Scope

- GPU acceleration path; GPU serving has a different contention model.
- Model swap decisions; keep those in `autopilot-continuous-optimization.md`.
- Embedder concurrency; embedders do not materially compete for decode bandwidth in the measured regime.
