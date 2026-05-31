# Shape-Keyed Contention Gating + Cross-Role Disjoint Placement

**Status:** ACTIVE — A/A-1 code-complete behind default-off flags; **B code-complete END-TO-END (dispatch-side caller wiring landed 2026-05-31, Step 2)**; C has pure backfill-selection prep only. **No production behavior is enabled yet**: both shape-aware flags default off and the API has not been reloaded, so live traffic is unaffected. Remaining work is now **rollout-only (no more code)**: live observation, flag-on, exact-region placement input (#3), and C behavior changes under an epoch boundary.
**Created:** 2026-05-30
**Owner:** (operator-directed; implementation by assistant)
**Repos:** `epyc-orchestrator` (src/scheduling, src/backends, src/runtime, scripts/benchmark)
**Depends on:** `contention_matrix.yaml` (topology_hash `df373c79cc4af06f`), `instance_topology.get_instance_regions()`

---

## Current state (start here)

- [x] **A — Cross-role disjoint placement** (prerequisite; correctness-critical) — **CODE-COMPLETE 2026-05-30, behind `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`; A-1 TOCTOU RESOLVED** via the global region mutex (`cpu_region.GLOBAL.{region}.lock`). Still LIVE-OBSERVATION-GATED before flag-on.
- [x] **B — Shape-keyed admission core + default-off gate seam + dispatch-side caller wiring** — `Placement`, `admit_set`, `held_regions_by_role`, `seam_admit`, dual-flag gate, and `ContentionGate.evaluate(candidate_topology_idx=...)` are code-complete and verified. The seam is **authoritative** when consulted (`worst = seam_decision`), not tightening-only. **Dispatch-side caller wiring DONE 2026-05-31 (Step 2):** `inference.py` defers the coarse role-keyed pre-gate for `ConcurrencyAwareBackend` when both flags are armed (so it can't mask a later disjoint candidate); `concurrency_aware.py` `_dispatch` evaluates the gate per **real** `candidate_topology_idx` before acquiring the candidate lock (denied candidates skipped/re-polled); `contention_gate.py` `admit()` threads `candidate_topology_idx` through to `evaluate()`. B is now code-complete end-to-end; production remains **inert** only because both shape-aware flags default off and the API was not reloaded.
- [~] **C — Backfill prep only** — pure `select_backfill_candidate` is implemented and tested; the heavy-port veto, all-heavy idle barrier, and pressure skip remain intact. Behavior-changing C work is not started.

### Next actions (operator-gated)

1. **Step 1 staged, not live:** `orchestrator_stack.py:1121` now defaults `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`, but the API was NOT reloaded (a live 185-trial autopilot was mid-run; reloading would contaminate its Pareto archive). After the autopilot wraps, `orchestrator_stack.py reload` arms the GLOBAL region mutex. Verify live env via `/proc/<api_pid>/environ` before trusting cross-role exclusion.
2. **Observe Step 1 live:** region-lock dashboard must show a heavy+light set landing on disjoint shapes; quantify Step 1's throughput cost on the deliberate `frontdoor+worker_general allow` pair (correctness floor — likely costs some overlap throughput). Sanity-check `active_region_holders()` still attributes correctly with GLOBAL lock in play.
3. ~~Wire the dispatch-side caller to pass the selected `candidate_topology_idx`~~ ✅ **DONE 2026-05-31 (Step 2, default-off).** Remaining: enable `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` (requires BOTH flags) only after a live smoke confirms disjoint quarters admit while q-overlaps queue.
4. Switch A placement from the attribution view (`active_region_holders`) to the exact-region view (`held_regions_by_role`) so flag-on placement does not overblock free quarters.
5. Only after B is live and observed, perform C behavior work: narrow the legacy heavy-slot barrier/erase, add work-conserving backfill, then remove the line-98 heavy-port veto.

> **2026-05-31 — dashboard-metrics holder accounting corrected (display only, gate unchanged).**
> `active_region_holders()` (attribution view) over-counted the dashboard's active-role
> readout: a single full-shape MTP worker holding q0–q3 rendered as ×5. Added
> `active_region_holder_instances()` in `src/runtime/cpu_region_lock.py` (group held locks
> by (role, PID) → resolve each PID's exact held-region set to its instance shape) and wired
> it into `ContentionGate.active_decodes_by_role`/`active_instances_by_role`. The scheduler
> attribution view `active_region_holders()` is **unchanged** (GitNexus HIGH-risk; still used
> by A placement). This is a precedent for **Next-action #3** (exact-region view) but does not
> itself change any gate/placement behavior. Commit `263b1b0`; see `progress/2026-05/2026-05-31.md`.

### A — implementation record (2026-05-30)

- `src/scheduling/placement.py`: added `_cross_role_regions_union(self_role, cross_role_holders, instance_regions)` + a `cross_role_holders: dict[str,Iterable[int]] | None = None` kwarg on `evaluate_placement`. When supplied, holder regions are unioned across **all** roles (self-role entry skipped); `None` → empty union → byte-identical legacy same-role-only behavior. Overlap is computed from canonical region sets (`instance_regions`), never a shape label.
- `src/backends/concurrency_aware.py`: new `@staticmethod _cross_role_disjoint_placement_enabled()` reading `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` (default off); the WP-2 `_dispatch` poll loop now snapshots the full `active_region_holders()` map once per iteration and passes it as `cross_role_holders` **only when both** that flag and the existing `ORCHESTRATOR_PLACEMENT_STATE_MACHINE` are on.
- Tests (`tests/unit/test_placement.py`, +5): cross-role half0 holder filters overlapping quarters; same-role∪cross-role union; whole-machine holder → queue; `cross_role_holders=None` preserves legacy isolation; disjoint node1 holder does **not** filter node0 quarters. Written red-first (confirmed `TypeError` on missing kwarg) then green.
- **Suite:** `test_placement.py` (16) + `test_dispatch_placement_state_machine.py` (10) + `test_concurrency_aware_quarter_preference.py` (8) + `test_concurrency_aware_migration_sm.py` (12) = **46 pass**.
- **Pre-existing failure (NOT mine):** `tests/unit/test_placement_policy.py::test_live_call_with_no_arg_does_not_crash` fails identically with my changes git-stashed — a parallel agent's uncommitted change made `get_placement_policy("frontdoor")` return `BURST_PREFER_QUARTERS` instead of the `SOLO_PREFER_FULL` default the test asserts. Flagged, untouched.

**Gate to exit A (unmet — needs live observation):** flag is OFF; behind-flag code is proven by unit tests only. Before flipping `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`, observe the region-lock dashboard showing a heavy+light set landing on disjoint shapes (operator-gated; needs the stack + a co-residency-inducing workload). **Not committed yet** — working tree only.

Sequencing is **A → B → C**, strict. Each gate below must be met before the next part starts.

---

## Problem

The autopilot seeder serializes "heavy" roles one-per-wave and barriers between waves, leaving physically-free CPU quarters idle while a node-half instance (e.g. `ingest_long_context.half0` on q0+q1) runs — even though the contention matrix has **already measured** that a fitting role could co-reside profitably (`{frontdoor, ingest_long_context, worker_general} = 1.535× allow`, `{frontdoor, ingest, vision} = 1.731× allow`). The waste is real, but the cause is **not** the heavy-port veto.

### Root cause (one line)

**Contention is decided per-role and placement-blind, but the physics is per-instance-shape.** The same role pair has two true, non-contradictory measured entries — `frontdoor+ingest = 0.37 block` for overlapping node0-half primaries, `frontdoor+ingest = 1.716 allow` for disjoint quarters — and nothing in the live path can disambiguate them or steer toward the good placement.

### Why "just delete line 98" does nothing (empirically proven)

Operator monkey-patched `HEAVY_PORTS = set()`; the seed wave plan was **unchanged** (`frontdoor+worker_general | coder_escalation | ingest_long_context | architect_general`). Because:

1. **`pair_policy` is role-keyed and placement-blind** — `contention.py:299-305`, lookup `matrix.get_pair(role_a, role_b)` at `:347`, no shape/instance arg. `frontdoor+ingest` always resolves to the stale primary `0.37` → background → `QUEUE` (`:362-373`).
2. **The gate can only make the verdict worse, never better** — `contention_gate.py:209-246`: it accumulates `worst` across all active-role pairs, then at `:234` applies an N-way result **only if more restrictive** (`_prec[nway] > _prec[worst]`). An N-way `allow` is inert against a pair-derived `QUEUE`. The seeder replicates the same order and is stricter still (requires `pair == ALLOW`, `seeding_eval.py:104-106`).
3. **Placement is a blocker, not a check** — `placement.py:92` `evaluate_placement` filters candidates against the **same** role's holders only (`_holder_regions_union(role, …)` at `:80-89`), called with `holders_for_role = active_region_holders().get(self._topology_role)` (`concurrency_aware.py:949`); and the candidate list pushes `full` first (`:912`). So placement neither avoids cross-role overlap nor *produces* the disjoint-quarter layout the optimistic n_way numbers assume. So line 98 is a symptom downstream of a path that was already going to queue.

So removing line 98 alone changes nothing. The matrix is already the measurement — this work reconciles three code layers to it. **No perf benchmark is required for the claim.**

---

## Invariants (bake these in)

1. **Overlap is computed from canonical region sets, never inferred from a shape's label.** `full` is not an overlap predicate. Per `instance_topology.py`: regions are quarter labels `q0,q1,q2,q3`; node0-half = `{q0,q1}`, node1-half = `{q2,q3}`, full = `{q0,q1,q2,q3}`. Role primary shapes differ:
   - `frontdoor` (8070), `ingest_long_context` (8085) primary = **node0-half** `{q0,q1}` (`0-47,96-143`)
   - `vision_escalation` (8087) primary = **node1-half** `{q2,q3}` (`48-95,144-191`)
   - `architect_general` (8083), `worker_general` (8072) "full" = **all four** `{q0,q1,q2,q3}` (`0-95`)
   - `worker_vision` (8086) = sub-quarter `q0B` (`24-47,120-143`)
   Use `get_instance_regions()` / `regions_overlap()` / `regions_for(role, idx)` as the single source of truth (already derived from `stack_numa.NUMA_CONFIG`).
2. **`architect_general` is strictly solo** — its only feasible instance is whole-machine (no quarter/half), so every candidate placement overlaps any other holder. It is correctly never in a feasible co-residency set. (NB: this is because of the placement layer, *not* because every old pair entry blocks — `architect_general+worker_general = 1.11 allow` exists at `matrix:101`.)
3. **Decision keys on placement (region sets / instance shapes), not bare role names.** Role-only `pair_policy()` survives **only** as a legacy fallback when the proposed placement is unknown. For **background traffic with unknown placement → fail closed (QUEUE).**
4. **Candidate ordering is region-set based:**
   - No cross-role holders → preserve the role's normal solo preference (sticky-quarter, then its primary, etc.).
   - Cross-role holders present → prefer the **smallest disjoint candidate that the placement-aware admission policy allows**.
   - Never use a human label (`full`) as a proxy for overlap.

---

## Design

### Part A — Cross-role disjoint placement (prerequisite; correctness-critical)

Make placement compute occupied regions across **all** roles and prefer disjoint shapes.

- `src/scheduling/placement.py:80-118` — `evaluate_placement` / `_holder_regions_union` must union holder regions across **every** `(role, idx)` currently holding a lock, not just the dispatching role. Take the full cross-role holder map + `instance_regions` and filter candidates whose region set overlaps the cross-role union (`regions_overlap`).
- `src/backends/concurrency_aware.py:909-916, 949` — build `candidates` region-set aware: when cross-role holders exist, do **not** offer `full` first; order by smallest disjoint candidate. Pass the cross-role holder map (`active_region_holders()` whole dict, not `.get(self._topology_role)`).
- Keep the 60 s poll-on-queue fallback (`:945-`) intact.

**Tests before wiring behavior** (per operator): unit-test `evaluate_placement` with a fixture where `ingest_long_context.half0` holds `{q0,q1}` and assert a `frontdoor`/`worker_general`/`vision_escalation` quarter candidate in `{q2,q3}` survives while `{q0,q1}` candidates and any `full` candidate are filtered. Add the cross-role-union case explicitly (today only same-role is covered).

**Gate to exit A:** unit tests green **AND** a live region-lock/dashboard observation showing a heavy+light set actually landing on disjoint shapes (observation, not a bench).

### Part B — Shape-keyed admission decision (semantic core; safe once A lands)

Add a single placement-aware decision function and route both callers through it.

- New in `src/scheduling/contention.py`:
  `admit_set(active_placements, candidate_placement, traffic_class) -> PairDecision`
  where a *placement* is `(role, region_set)` (or `(role, topology_idx)` resolved via `get_instance_regions`). It looks up contention by **region set / instance shape**, not bare role:
  - disjoint candidate vs active set → consult the **quarter-level `n_way`** layer (authoritative for quarter-capable placement); measured `allow` → ALLOW.
  - overlapping candidate → that placement is infeasible (Part A should never produce it); fail closed.
  - placement unknown → legacy `pair_policy()` role-only fallback; **background + unknown → QUEUE (fail closed)**.
- Both `contention_gate.py:208-246` and the seeder `seeding_eval.py:104-106` (`_can_add_role_to_seed_wave`) call `admit_set` — they currently replicate the pair-before-nway ordering; centralizing removes the duplicated bug and the "n_way can only worsen" asymmetry.

**Matrix schema change** (`contention_matrix.yaml`):
- Pair/n_way lookups become shape-aware. The data is already shape-tagged (`instance_a/instance_b/cpu_list`); `get_pair`/`get_nway` must key on canonical region sets.
- Mark the overlapping-primary `block` entries (`matrix:33,43,53,62,71`) as **placement-conditional** (overlapping-primary placement) so they stop poisoning role-keyed lookups for disjoint placements. Keep them — they are the *correct* verdict for the overlapping placement Part A now refuses to make.

**Tests:** `admit_set` truth table — disjoint heavy+light → ALLOW; overlapping → QUEUE/closed; unknown placement bg → QUEUE; unknown placement fg → ALLOW. Plus a regression asserting an n_way `allow` is no longer masked by a stale primary-pair `queue` once placement is disjoint.

**Gate to exit B:** gate + seeder both produce a co-resident wave (e.g. `frontdoor + ingest + worker_general` on disjoint shapes) in a unit/integration test; no regression on overlapping sets.

### Part C — Narrow legacy heavy barrier, add backfill, remove line-98

- `scripts/benchmark/seeding_eval.py:393` (`_eval_single_config`) — narrow the "wait all-heavy-ports idle + erase busy heavy slots" to the role's **own** target port/instance; drop the all-heavy-idle wait. Cross-thread erase hazard is `seeding_orchestrator.py:59` (a concurrent heavy seed thread can erase another heavy request's slot) — scope erase to own instance.
- `scripts/benchmark/seeding_eval.py:1069` — dispatch-time "heavy lock under pressure" path: change from **skip** to **backfill** (pick the next admissible role for the free regions via `admit_set`). This is what actually closes the wall-clock idle.
- `scripts/benchmark/seeding_eval.py:98` — **remove** the `HEAVY_PORTS`-both veto last (inert until A+B+C, proven by the monkey-patch).

**Gate to exit C:** with the stack live, the seed wave plan packs a matrix-allowed disjoint heavy+light set into one wave, and the region-lock dashboard shows the intended co-residency. No silent slot erasure of a foreign instance (assert via slot ownership).

---

## Rollout / rollback

- Each part lands behind its own flag where feasible:
  - A: the placement state machine already gates on `_placement_state_machine_enabled()` (`concurrency_aware.py:921`) — extend that flag or add a `CROSS_ROLE_DISJOINT_PLACEMENT` sub-flag so A can be toggled without reverting code.
  - B: `admit_set` can be feature-flagged to fall back to the legacy pair-before-nway path.
  - C: the line-98 veto removal + backfill are the only irreversible-by-data changes; land last, revert by re-adding the veto (a 1-line revert).
- Rollback order is reverse: C → B → A.
- Topology guard: all of this assumes `topology_hash df373c79cc4af06f`. If `NUMA_CONFIG` changes, the matrix is stale and `admit_set` must fail closed (the gate already does this at `contention_gate.py:198-206`).

## Acceptance (no perf bench)

1. Unit tests for A (cross-role placement filter), B (`admit_set` truth table + un-masking regression), C (own-instance erase scoping + backfill selection).
2. Live observation: region-lock/dashboard shows the intended disjoint heavy+light shape co-resident under the seeder. This — not a throughput number — is the acceptance signal, because the matrix already supplies the measured ratios.

---

## Evidence index (verified 2026-05-30)

| Claim | Site |
|---|---|
| `pair_policy` role-keyed, placement-blind | `src/scheduling/contention.py:299-305,347,362-373` |
| Gate accumulates `worst`, n_way only worsens | `src/scheduling/contention_gate.py:209-246` |
| Seeder replicates pair-before-nway, stricter | `scripts/benchmark/seeding_eval.py:101-107` |
| Heavy-port veto (the symptom) | `scripts/benchmark/seeding_eval.py:98` |
| Placement same-role-only filter | `src/scheduling/placement.py:80-118` |
| Placement called with same-role holders; full-first | `src/backends/concurrency_aware.py:909-916,949` |
| Heavy-slot erase / all-heavy-idle wait | `scripts/benchmark/seeding_eval.py:393`; `scripts/benchmark/seeding_orchestrator.py:59` |
| Dispatch-time pressure skip (not backfill) | `scripts/benchmark/seeding_eval.py:1069` |
| Canonical region model (authoritative) | `src/runtime/instance_topology.py` (`get_instance_regions`, `Q_ALL/NODE0_HALF/NODE1_HALF`, `regions_overlap`) |
| Stale primary vs quarter n_way (0.37 vs 1.716) | `orchestration/contention_matrix.yaml:33,301` |
| Monkey-patch `HEAVY_PORTS=set()` → waves unchanged | operator test, 2026-05-30 |

## Decisions locked

- Part B route: **principled shape-keyed** (`admit_set` keyed on canonical region sets / instance shapes). The interim "let n_way supersede pair if A placed disjointly" is rejected — it leaves the central ambiguity (same pair = 0.37 block ∧ 1.716 allow) unexplained.
- Role-only `pair_policy()` kept **only** as a legacy fallback for unknown placement; **background + unknown placement → fail closed**.
- `architect_general` stays solo (placement layer, not pair entries).
- Candidate ordering region-set based; never use `full` as an overlap proxy.

---

## A-1 — RESOLVED (cross-role mutual exclusion / global region mutex)  [implemented 2026-05-30, test-first]

**Status of A:** CODE-COMPLETE, still LIVE-OBSERVATION-GATED (flag off; needs the region-lock dashboard showing a heavy+light set on disjoint shapes before flag-on). A-1 closes the TOCTOU — the behind-flag code now realizes both the *preference* AND the cross-role *guarantee*.

### A-1 implementation (Option 1 — global region-mutex layer)

- `src/runtime/cpu_region_lock.py` (+67/−13):
  - `global_region_lock_path(region)` → `{tmp_dir}/cpu_region.GLOBAL.{region}.lock` (role-agnostic).
  - `_cross_role_mutex_enabled()` reads `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` (default off).
  - `cpu_region_lock(...)`: when enabled, acquires the **GLOBAL** mutex for all regions first (sorted), THEN the per-role attribution locks (sorted) — consistent global ordering = deadlock-free; both layers on the same LIFO release stack. Flag off → GLOBAL layer skipped → byte-identical legacy behavior.
  - Per-role locks UNCHANGED as the attribution layer. `active_region_holders` is driven by the topology table (real `(role, idx)` only) and never globs lock files, so the `GLOBAL` pseudo-role is automatically invisible to attribution.
- Tests — `tests/unit/test_cross_role_region_mutex.py` (NEW, real **fork** processes for honest cross-process flock; spawn can't import the pytest module in the child):
  - flag-OFF → two roles overlap on q0 (documents the TOCTOU; passes against the bug).
  - flag-ON → windows serialize (disjoint) + GLOBAL lock acquirable after release (clean release).
  - `active_region_holders` ignores a held GLOBAL lock (attribution stays role-only).
  - **Hygiene (operator audit fix):** `_run_two_role_race` wraps start/join in try/finally with terminate→join→kill cleanup (mirrors `test_cpu_region_lock.py:400`) so a failed assertion or hung worker can never leak a child; the inert `@pytest.mark.timeout` marks were removed (pytest-timeout not in this venv) in favor of a hard 30s join bound + the finally-kill.
- **Regression:** `test_cpu_region_lock.py` 23/23 pass (legacy lock path intact); full placement/dispatch/mutex suite **58 pass** (mutex 3 + cpu_region_lock 23 + placement 16 + dispatch_cross_role 2 + dispatch_sm 4 + quarter_pref 8 + migration_sm 2). Pre-existing unrelated failure unchanged: `test_placement_policy::test_live_call_with_no_arg_does_not_crash` (parallel agent's `get_placement_policy` default change; stash-proven not mine). [audit-fix re-verified 2026-05-30]

**Remaining A gate (operator):** flip `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` only after a live region-lock/dashboard observation of a heavy+light set landing on disjoint shapes. **Nothing committed — working tree only.** Per operator instruction: **STOP here; do NOT start B (`admit_set`) until this is reviewed.**

---

## A-1 — original blocker writeup (now resolved; kept for context)

**Status of A:** PARTIAL. The behind-flag code realizes the *preference* (placement filters + smallest-disjoint ordering + dispatch wiring + 48 passing tests) but NOT the cross-role *guarantee*. Do not flip `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` until A-1 is resolved.

**The race.** Region locks are **per-role** files: `cpu_region.{role}.{region}.lock` (`src/runtime/cpu_region_lock.py:98,108`). So `frontdoor.q0.lock` and `ingest_long_context.q0.lock` are *different inodes* — `flock` on them provides **no cross-role mutual exclusion**. `_dispatch` (`src/backends/concurrency_aware.py:962`) snapshots all holders, evaluates disjointness, then acquires only **its own role's** lock (`:974`) with **no post-acquire cross-role revalidation**. Two different roles can each pass a compatible snapshot and then take physically-overlapping regions. (Found by operator audit 2026-05-30; confirmed against the lock-path source.)

**Test owed:** a unit/concurrency test that forces the interleaving (role A and role B both see each other absent in the snapshot, both acquire overlapping regions) and asserts it CANNOT happen after the fix.

### A-1 design fork (decide before implementing)

1. **Global region-mutex layer (RECOMMENDED).** Keep per-role lock files for holder *attribution* (the dashboard and `active_region_holders()` — and the cross-role union itself — depend on them), but before taking the per-role lock, also acquire a role-agnostic `cpu_region.GLOBAL.{region}.lock` (blocking, acquired in sorted-region order to avoid deadlock) for every region the chosen candidate needs. The global flock gives true cross-role exclusion; the per-role files preserve attribution. Additive (new lock files only), contained to the lock layer, lives behind the same flag.
2. **Post-acquire recheck + release/retry.** After acquiring own-role lock, re-snapshot holders; if a cross-role overlap appeared, release and re-poll. Insufficient alone — the symmetric "both acquired, both recheck, both release" case livelocks, and "A acquired and already passed its recheck before B acquires" still double-holds. Would need a deterministic tiebreaker and still leaves a residual window. NOT recommended as the sole mechanism.
3. **Collapse role out of the lock path (global namespace).** Simplest exclusion but BREAKS `active_region_holders()` role attribution that the dashboard + cross-role union need. Rejected unless attribution is rebuilt elsewhere.

**Recommendation: option 1** — the only one that gives a real guarantee without losing attribution.

### Corrected A scope/test record (supersedes the earlier "CODE COMPLETE / 46 pass" note above)

- `placement.py`: `_cross_role_regions_union` + `cross_role_holders` kwarg on `evaluate_placement`; `None` → byte-identical legacy. **Ordering invariant FIXED** — when cross-role holders present, `safe` is stable-sorted by ascending region-set size (smallest disjoint first; quarters before full/half); no-cross-role path unchanged.
- `concurrency_aware.py`: `@staticmethod _cross_role_disjoint_placement_enabled()` (`ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`, default off, effective only with `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`); `_dispatch` snapshots the full holder map once per poll iteration and passes it through.
- Tests: `tests/unit/test_placement.py` (+5 incl. size-ordering) and **new** `tests/unit/test_dispatch_cross_role_placement.py` (+2 dispatch-level: flag-ON frontdoor avoids ingest's held node0-half → lands q2/q3; flag-OFF takes full). **48 pass** across the 5 placement/dispatch files. NB: `_dispatch` re-imports `active_region_holders`/`get_instance_regions` function-locally from their SOURCE modules — patch those, not `ca_mod`.
- **Pre-existing failure (NOT mine):** `tests/unit/test_placement_policy.py::test_live_call_with_no_arg_does_not_crash` — fails identically with my changes git-stashed; a parallel agent's uncommitted change makes `get_placement_policy("frontdoor")` return `BURST_PREFER_QUARTERS` not `SOLO_PREFER_FULL`. Untouched.
- **Nothing committed** — working tree only.

---

## ⏯️ RESUME HERE — A-1 implementation in progress (context refreshed 2026-05-30)

**Future self: you were mid-implementation of A-1 (global region-mutex layer), test-first, when context ran out. Nothing for A-1 was written yet — you were still reading `cpu_region_lock.py` to plan the integration point. Pick up from the plan below.**

### Operator's explicit instructions for A-1 (binding constraints)
- **Option 1 only**: global region-mutex layer. Keep per-role locks EXACTLY as attribution locks.
- Add role-agnostic locks as an ADDITIONAL layer, acquired **first**, sorted by region: `cpu_region.GLOBAL.{region}.lock`.
- Gate behind `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`; **flag OFF must preserve current behavior byte-for-byte**.
- **Race test must use multiprocessing/subprocess** (flock semantics within one process are misleading — flock is per-(fd) and the same process re-acquiring its own lock can succeed misleadingly).
- Test BOTH sides: flag OFF → today's cross-role same-region overlap is ALLOWED (two roles both acquire q0); flag ON → blocked, and releases cleanly.
- **Do NOT start B** until A-1 is green AND the handoff marks A as code-complete-but-live-observation-gated. Then STOP for review.

### Where things stand (verified facts)
- `src/runtime/cpu_region_lock.py`:
  - `region_lock_path(role, region)` (~line 98–108) → `{tmp_dir}/cpu_region.{role}.{region}.lock`. Sanitizes role/region (`/`,`\` → `_`).
  - `_try_flock(fd, lock_type)` (~line 118) → non-blocking flock, returns bool; raises on non-EAGAIN/EWOULDBLOCK.
  - `_acquire_one_with_timeout(fh, *, region, role, timeout_s, deadline_s, cancel_check, request_tag)` (~line 131) → blocking-with-timeout acquire loop; returns elapsed; raises `CpuRegionLockTimeout`.
  - `active_region_holders(instance_regions=None)` (~line 209) → `{role: [instance_idx,…]}` by scanning `cpu_region.*.lock` files. **CRITICAL: this parses lock FILENAMES for attribution. If you add `cpu_region.GLOBAL.{region}.lock` files, make SURE `active_region_holders` SKIPS the `GLOBAL` pseudo-role** (else dashboard shows a bogus "GLOBAL" role holder). Verify its filename-parsing/glob and add a `GLOBAL` skip.
  - The main entry context manager is **`cpu_region_lock_for_instance(role, instance_idx, *, timeout_s, deadline_s, cancel_check=None, request_tag=None)`** — a `@contextmanager`. It: resolves the instance's region set via `get_instance_regions()` / instance_topology, sorts regions lexicographically, opens+acquires each per-role region lock via `_acquire_one_with_timeout`, yields the list of lock paths, and releases LIFO on exit (all-or-nothing: on any timeout, releases already-held and raises). **THIS is the function you were about to read in full (it lives somewhere around lines 256–404; the file is ~404 lines). Read it FIRST on resume.**
  - File length: ~404 lines (the sed 245–415 only returned 11 lines once, which was a flaky/truncated read — do a fresh `wc -l` and `grep -n "def cpu_region_lock_for_instance"` to get the real boundaries).

### The A-1 implementation plan (do this, test-first)
1. **Write the failing race test FIRST**: `tests/unit/test_cross_role_region_mutex.py` (NEW). Use `multiprocessing` (spawn or fork) OR `subprocess` with two child workers:
   - Each child calls a tiny helper that acquires `cpu_region_lock_for_instance("frontdoor", <q0 instance idx>)` and `("ingest_long_context", <q0 instance idx>)` respectively — i.e. two DIFFERENT roles both wanting region **q0** — holds briefly (writes a timestamp to a shared file / pipe), then releases.
   - Point `ORCHESTRATOR_TMP_DIR` at a `tmp_path` so lock files are isolated.
   - **Flag OFF assertion**: both children hold q0 SIMULTANEOUSLY (overlapping hold windows) — proves today's TOCTOU bug exists. (This documents current behavior; it should pass against unmodified code.)
   - **Flag ON assertion** (`ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`): hold windows are DISJOINT (one waits for the other) — proves the global mutex serializes cross-role same-region. Also assert clean release (second acquires after first exits; no leftover GLOBAL lock file held).
   - Helper must be module-level (picklable) for multiprocessing spawn.
2. **Implement**: in `cpu_region_lock_for_instance`, when `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` is on, BEFORE acquiring the per-role region locks, acquire `cpu_region.GLOBAL.{region}.lock` for each region in the instance's set, in sorted order, via the same `_acquire_one_with_timeout` machinery. Add the global paths to the same release stack so LIFO release covers them. Add a `global_region_lock_path(region)` helper → `cpu_region.GLOBAL.{region}.lock`.
   - Flag OFF: skip the GLOBAL acquisition entirely → behavior identical to today.
   - Ordering/deadlock: acquire GLOBAL locks for all regions first (sorted), THEN per-role locks (sorted). Consistent global order across all callers = no deadlock.
3. **Make `active_region_holders` skip `GLOBAL`** (attribution must stay role-only). Add a regression assertion that a held GLOBAL lock does NOT appear as a role.
4. Run: `tests/unit/test_cross_role_region_mutex.py` + the full placement/dispatch suite (`test_placement.py`, `test_dispatch_placement_state_machine.py`, `test_dispatch_cross_role_placement.py`, `test_concurrency_aware_quarter_preference.py`, `test_concurrency_aware_migration_sm.py`) — must stay green (48 currently). Also re-confirm `test_placement_policy::test_live_call_with_no_arg_does_not_crash` is STILL the only pre-existing failure (not introduced by you).
5. Update handoff: flip A-1 from OPEN → resolved; mark A "code-complete, live-observation-gated"; update the routing index row. Then **STOP for operator review. Do NOT start B (`admit_set`).**

### Test/infra gotchas (learned this session)
- Use `.venv/bin/python -m pytest …` (system python lost PyYAML after devcontainer rebuild; venv is correct).
- `_dispatch` re-imports `active_region_holders` / `get_instance_regions` / `cpu_region_lock_for_instance` **function-locally from their SOURCE modules** (`src.runtime.cpu_region_lock`, `src.runtime.instance_topology`) — monkeypatch THOSE, not `ca_mod` attributes.
- Bash tool output rendering has been flaky this session (results sometimes arrive blank then appear on a later call). If a test result looks empty, re-run to a temp file and `cat` it; don't trust a single blank.
- Shared clone `/mnt/raid0/llm` has many uncommitted parallel-agent changes. When committing, use `git add -p` / explicit hunks — NEVER `git add` whole shared files. Nothing from this whole task is committed yet (working-tree only) — operator commits manually.

### What's DONE and must not be re-done (A core, behind flag, uncommitted)
- `src/scheduling/placement.py`: `_cross_role_regions_union()` + `cross_role_holders` kwarg on `evaluate_placement`; smallest-disjoint **stable size-sort** applied only when `cross_role_holders` truthy; `None`/empty → byte-identical legacy.
- `src/backends/concurrency_aware.py`: `@staticmethod _cross_role_disjoint_placement_enabled()` reads `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` (default off); `_dispatch` snapshots full `active_region_holders()` once/iteration and passes it as `cross_role_holders` only when that flag AND `ORCHESTRATOR_PLACEMENT_STATE_MACHINE` are both on.
- Tests: `tests/unit/test_placement.py` (+5, incl. `test_cross_role_disjoint_holder_prefers_smallest_then_full`), `tests/unit/test_dispatch_cross_role_placement.py` (NEW, +2). 48 pass across the 5 files.

### Standing operational context
- Stack is UP (started this session, all 35 components healthy, `[1.5]` prewarm validated — NUMA balance 26/24.6/24.6/24.6%).
- J6 autopilot soak RUNNING: daemon `autopilot.py start --no-controller --max-trials 2000`, state at `orchestration/autopilot_state.json` (NOT scripts/autopilot/), resumed at trial_counter=124. Log `logs/autopilot_relaunch15_*.log`. **Do NOT touch/restart autopilot or stack without explicit operator permission** (two standing CRITICAL constraints).
- [shape-keyed-contention-gating-B-RESUME.md] Part B admit_set scaffolding resume checkpoint
