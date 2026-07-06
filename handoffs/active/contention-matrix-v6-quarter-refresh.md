# Contention matrix v6 quarter refresh — false-stale resolved

**Status**: RESOLVED 2026-07-05 — no matrix re-bench required for the current production role set.
**Created**: 2026-07-05 by the dashboard-hardening session.
**Priority**: HIGH at creation; now MONITOR.

## Resolution (2026-07-05)

The live `matrix_status: "stale"` diagnosis was a topology-fingerprint false
positive, not evidence that the v6 contention matrix was measured under the
wrong production topology.

Root cause:
- Full `NUMA_CONFIG` hash: `5d19b3e4edf6fc27`.
- Stored contention matrix hash: `df373c79cc4af06f`.
- Current hash over roles actually measured in `contention_matrix.yaml`,
  excluding auxiliary explicit-only `eval_batch_frontdoor`:
  `df373c79cc4af06f`.

The auxiliary `eval_batch_frontdoor` role exists in launch topology but is not a
production admission target in the measured contention matrix. Full-topology
freshness checks therefore marked the matrix stale even though all measured
production roles still match the matrix topology.

## What Landed

- Orchestrator `3d1706c6` first changed the dashboard/admission freshness path
  to ignore auxiliary roles in contention topology checks.
- Orchestrator `120498c9` centralized the measured-role topology helper in
  `src/scheduling/contention.py` and aligned the gate, validator,
  SafetyGate/EvalTower consumers, and `scripts/server/contention_matrix.py`
  validation paths.
- Validation passed:
  - `uv run pytest -q tests/unit/test_scheduling_contention.py tests/unit/test_scheduling_contention_gate.py tests/unit/test_dynamic_stack_evidence_packet.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_safety_gate_baseline_eligibility.py` -> `108 passed`
  - `uv run python scripts/validate/check_contention_matrix_fresh.py` -> `OK`
  - `uv run python scripts/server/contention_matrix.py validate` -> status `ok`
- GitNexus is current at orchestrator commit `120498c`.
- The orchestrator API was reloaded; live `/dashboard/api/contention` reports
  `matrix_status: "ok"`.

## What Did Not Happen

The matrix benchmark was **not** rerun. That is intentional: the measured-role
topology hash matched the committed matrix, so rerunning the matrix would have
spent a quiet window to restate existing evidence while mixing in the ambient
MI210 direct-access workload context.

## Follow-Up

- [x] Monitor the one live placement observation from
  `scripts/server/affinity_preflight.py`: production CPU affinities verified,
  but `worker_general` q2 (`:8282`) had correct cpuset placement with only
  about `0.756` local anonymous-memory placement in `numa_maps`. Reloaded that
  instance and re-ran placement preflight on 2026-07-06; `live_affinity_verified=true`
  and `live_memory_placement_verified=true`. ✅ 2026-07-06
- [ ] If a future production role is added to the contention matrix, regenerate
  the matrix under the codified recipe and update the measured-role topology
  hash as part of that change.

## Key Files

- `epyc-orchestrator/src/scheduling/contention.py`
- `epyc-orchestrator/src/scheduling/contention_gate.py`
- `epyc-orchestrator/scripts/server/contention_matrix.py`
- `epyc-orchestrator/scripts/validate/check_contention_matrix_fresh.py`
- `epyc-orchestrator/orchestration/contention_matrix.yaml`
