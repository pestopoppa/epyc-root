# Contention matrix re-bench — topology-hash STALE after quarter-mode cutover

**Status**: ACTIVE — ready to execute; ownership passed to the session that owns the running seeding sweep (operator-directed 2026-07-05)
**Created**: 2026-07-05 by the dashboard-hardening session
**Priority**: HIGH — a production admission gate is running degraded NOW
**Operator approval**: GIVEN 2026-07-05 ("there's a quiet window right now, lets do it asap") — approval covers the measurement run itself; no further sign-off needed once the machine is actually quiet.

## Why (verified live 2026-07-05 ~19:00Z)

- `GET :8000/dashboard/api/contention` → **`matrix_status: "stale"`**. The matrix file (`epyc-orchestrator/orchestration/contention_matrix.yaml`, measured 2026-06-27 for the v6 cutover) is only 8.4d old vs the 30d age threshold, so the stale verdict is the **topology-hash mismatch** path (`src/scheduling/contention.py:matrix_status`, hash vs `scripts/server/stack_numa.py` NUMA_CONFIG): the role/NUMA layout changed since measurement — plausibly the `--numa-mode quarter` launcher default (orch `01d14301`) and/or the 07-05 stack relaunches.
- Impact: the cross-role admission gate consumes this matrix. Measured-under-old-topology pairs can mispredict; unmeasured pairs are `unknown` → **block for background traffic**. This degrades placement/admission quality until re-measured.

## Blocker at handoff time

- [ ] Wait for **`seed_specialist_routing.py --suites all`** (was PID `2859968`/`2859973`, launched by this owning session) to finish/drain. It sends frontdoor/coder_escalation requests every ~10–20s — running the matrix concurrently poisons both the matrix and the seeding rewards.
- AutoPilot is already DOWN (SIGTERM 18:46:52, log `epyc-orchestrator/logs/autopilot.log`) — do not relaunch it until after the matrix run.
- MI210 GPU server on :8802 (direct-access testbed) may stay up: host-side footprint ≈1 core of 96; both bench arms see the same ambient. Record it as runtime context in the commit message, don't block on it.

## Execution (all from `/mnt/raid0/llm/epyc-orchestrator`)

- [ ] **Preflight — quiet check**: `curl -s :8000/dashboard/api/snapshot | jq '.activity | map_values(.n_active) | with_entries(select(.value>0))'` → must be empty (or only `8802`).
- [ ] **Preflight — throttle check**: verify CPU freq not degraded (multi-day −60% mode per [[feedback_host_throttle_check]]); `grep MHz /proc/cpuinfo | sort -u | tail` sanity. Host uptime is 3d — if frequencies look clamped, `drop_caches` remediation first (≤1wk rule), then re-warm interleave ([[feedback_drop_caches_numa_eviction]]).
- [ ] **Preflight — live affinity**: run `affinity_preflight.py` (verify LIVE affinity, not just topology hash — [[feedback_verify_live_affinity_not_just_topology_hash]]).
- [ ] **Dry-run**: `uv run python scripts/server/contention_matrix.py --dry-run` — review the pair plan/scope against the live quarter-mode stack.
- [ ] **Run**: `uv run python scripts/server/contention_matrix.py` (writes `orchestration/contention_matrix.yaml` with fresh `topology_hash`, `measured_at`, binary commit). Smart-prune skips N-way combos containing catastrophic (<0.65) pairs — expected.
- [ ] **Verify**: `curl -s :8000/dashboard/api/contention | jq .matrix_status` → `"ok"`; spot-check a few pair ratios are sane (0.5–1.2 band) vs the 06-27 matrix.
- [ ] **Commit** (explicit pathspec — shared tree): `git add orchestration/contention_matrix.yaml && git commit` — note the MI210 ambient context + that this is the quarter-mode-era matrix.
- [ ] Only then: relaunch AutoPilot via `start_fable_authority_daemon.py --max-trials 2000` (it will also pick up the new `config_applicator.py` no-op restart guard landing separately today).

## Reporting

- Flip the checkboxes above; add a one-line entry to `progress/2026-07/2026-07-05.md` (or the day's file) with the new `measured_at` + hash.
- The dashboard's contention chip is being rewired to `matrix_status` (fingerprint verdict) by the dashboard-hardening session — no action needed here.

## Key files

- `epyc-orchestrator/scripts/server/contention_matrix.py` (the codified recipe — Phase F of `handoffs/active/cross-role-bw-aware-routing.md`)
- `epyc-orchestrator/orchestration/contention_matrix.yaml` (output, git-tracked)
- `epyc-orchestrator/src/scheduling/contention.py` (gate + `matrix_status` semantics)
