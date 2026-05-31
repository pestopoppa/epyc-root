# Part B/C Checkpoint — Shape-Keyed Contention Gating (2026-05-30)

**Read this first, then `handoffs/active/shape-keyed-contention-gating.md` (the full design + A/A-1 record).**

## Current resume point (UPDATED wrap-up 2026-05-31 — Step 1 staged, Step 2 dispatch-wiring DONE)

> **2026-05-31 supersedes the 2026-05-30 resume point below.** This session: (a) re-confirmed the dashboard "discrepancy" (frontdoor.half0 decoding on cores worker_general.full holds) is the EXPECTED role-keyed/placement-blind behavior, not rendering drift; (b) **staged Step 1** — `orchestrator_stack.py:1121` now defaults `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` (NOT reloaded; live autopilot mid-run); (c) **built Step 2** — the dispatch-side caller now passes a real `candidate_topology_idx`. B is code-complete end-to-end; remaining work is **rollout-only, no more code**.

- **A/A-1:** code-complete behind `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`. **Step 1 launcher default now staged** at `orchestrator_stack.py:1121` (`env.setdefault(...,"1")`), but the API was NOT reloaded — arms on next `orchestrator_stack.py reload`. Still live-observation-gated.
- **B:** core + gate seam + **dispatch-side caller wiring all DONE.** `inference.py` defers the coarse role-keyed pre-gate for `ConcurrencyAwareBackend` when both flags armed; `concurrency_aware.py` `_dispatch` evaluates the gate per real `candidate_topology_idx` before lock acquisition (denied → skip/re-poll); `contention_gate.py` `admit()` threads `candidate_topology_idx` to `evaluate()`. Regression tests added (pre-gate deferral, real-candidate dispatch + denied-skip, admit() arg propagation); 146-test affected suite green; `git diff --check` clean.
- **Runtime safety:** still inert. Both shape-aware flags default off; API not reloaded; no autopilot relaunch. Live env on pid 3229744 is still only `PER_REGION_LOCKS=1` + `PLACEMENT_STATE_MACHINE=1`.
- **C:** pure `select_backfill_candidate` exists and is tested. The heavy-port veto, all-heavy idle barrier, and pressure skip remain untouched.
- **GitNexus:** `gitnexus@1.6.5` usable for root/orchestrator/research; wrappers use `--skip-agents-md --skip-skills`. llama.cpp re-index remains stale/hung (separate infra follow-up).

**Next authorized work (rollout-only, no code):** (1) after the autopilot wraps, reload to arm Step 1 (GLOBAL region mutex); (2) observe blocked-pair/wait/throughput + verify dashboard attribution survives GLOBAL lock; (3) enable `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` (needs BOTH flags) only after a live smoke confirms disjoint quarters admit while q-overlaps queue; (4) A placement consumes the exact-region snapshot instead of the attribution map; (5) C behavior changes only after B is live/observed and under an epoch boundary.

> Historical notes below preserve the audit chain. Where they mention "pure only," "no call-site rewiring," "worse-of/tightening-only," or stale GitNexus 1.6.1 behavior, the current resume point above supersedes them.

## Task / goal (and how it evolved)
Original thread: operator asked whether the autopilot seeder wastes free CPU quarters. Root-caused (operator-corrected, code-verified) to: **contention is decided per-role and placement-blind, but the physics is per-instance-shape.** Same pair `frontdoor+ingest` has two true matrix entries — `0.37 block` (overlapping node0-half primaries, `contention_matrix.yaml:33`) and `1.716 allow` (disjoint quarters, n_way `:301`) — and nothing in the live path disambiguates. Fix is sequenced **A → B → C** (see main handoff).

- **A (cross-role disjoint placement) + A-1 (global region mutex): DONE**, behind `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` (default OFF). Live-observation gate is operator-owned, deferred until **after J6 ends**.
- **B (shape-keyed `admit_set` + default-off gate seam + dispatch-side caller): CODE-COMPLETE / VERIFIED.** Runtime remains inert because both shape-aware flags are not live together and the API was not reloaded.

## CURRENT STATE OF B (updated 2026-05-30 — core + default-off seam landed)
B's pure core + wiring-seam prerequisites exist in `src/scheduling/contention.py`, `src/runtime/cpu_region_lock.py`, and `src/scheduling/contention_gate.py`. The gate seam is reachable only through `evaluate(candidate_topology_idx=...)` and both dual flags. **Dispatch now supplies real candidate indices when both flags are armed, but live runtime remains inert** because `ORCHESTRATOR_SHAPE_AWARE_CONTENTION` is still off and the API was not reloaded.

### Landed this session (post second-audit; all pure, default-neutral, tests green)
- **admit_set audit fixes (#1/#2/#4):** unknown placement → background **fails closed immediately** before any `pair_policy` fallback (fg keeps legacy fallback); disjoint branch documented as precondition contract (callers pass A's certified smallest-disjoint placements; matrix `n_way` is role-set keyed, not region-set keyed). Tests: `test_unknown_placement_background_fails_closed_even_for_known_allow_pair`, `test_disjoint_verdict_is_nway_for_role_set_precondition_quarter_placement`.
- **P1 — exact-region helper:** new `held_regions_by_role(instance_regions=None) -> {role: frozenset(held regions)}` in `cpu_region_lock.py` (additive; `active_region_holders` UNCHANGED — 0 real deletions to it, pinned by `test_active_region_holders_overreports_same_scenario`). Fixes the over-reporting: attribution view flags an *instance* active if ANY region held (a held q0 flags the `full` instance too); exact view reports only physically-held regions. Tests: `tests/unit/test_held_regions_snapshot.py` (7).
- **P2a/P2b — B wiring seam (default-off, DUAL-flag):** new `seam_admit(...)` + `shape_aware_contention_enabled()` + `_worse_decision` helper in `contention.py`. **Audit #1 (dual-flag contract):** `shape_aware_contention_enabled()` requires BOTH `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` AND `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` (either alone → disabled → `seam_admit` returns None → legacy path). The contention verdict is only trustworthy when the placement layer is also realizing disjoint placements. **Audit #2 (snapshot fail-closed):** if `held_regions_by_role` raises (unknown occupancy), `seam_admit` background → QUEUE (fail closed), foreground → None (caller's legacy path) — never silently ALLOW. (A *successful empty* snapshot still legitimately means "no holders → ALLOW".) **Audit #3 (no bypass):** the `enabled=` override parameter was REMOVED from `seam_admit` — on/off is decided ONLY by `shape_aware_contention_enabled()` (the dual-flag gate), so a runtime caller cannot bypass the safety contract. Tests enable the seam exclusively via the `shape_aware_on` fixture (sets both env flags = the exact runtime gate). **Same-role preservation:** seam routes same-role contention through `pair_policy(role, role)` so `same_role` matrix verdicts are honored (admit_set alone delegates disjoint to `nway_policy`, which dedupes roles and would collapse a same-role pair to ALLOW — the seam prevents that). Cross-role delegates to `admit_set`; returns worse-of. Consumes the EXACT `held_regions_by_role` view, not `active_region_holders`. Tests: `tests/unit/test_shape_aware_seam.py` (12, incl. the same-role-block-where-admit_set-allows crux + default-off proofs).
- **A audit fix (P1 ordering):** `evaluate_placement` size-reorder now gates on the OTHER-role region union being non-empty (`if cross_role_union:`), not merely on a holder map being passed — same-role-only maps no longer perturb ordering. Test: `test_cross_role_holders_self_role_only_preserves_legacy_order`.
- **GitNexus P0 hygiene:** all 4 repo wrappers (`scripts/gitnexus-analyze.sh` ×4) now call `gitnexus analyze --skip-agents-md --skip-skills`. `gitnexus@1.6.5` fixed the earlier 1.6.1 native analyze crash for root/orchestrator/research; llama.cpp still needs separate stale-index follow-up.

### Verification (this session)
- Requested 8-file suite: **129 passed** (seam now 15: +3 dual-flag/fail-closed/no-bypass tests; the `enabled=` override parameter and its redundant test were removed per audit #3).
- (Earlier superset incl. dispatch/concurrency files: **145 passed** (authoritative pytest total)) — `test_shape_aware_seam` 12 + `test_admit_set` 15 + `test_held_regions_snapshot` 7 + `test_placement` 17 + `test_cpu_region_lock` 23 + `test_cross_role_region_mutex` 3 + `test_dispatch_cross_role_placement` 2 + `test_dispatch_placement_state_machine` 4 + `test_concurrency_aware_quarter_preference` 8 + `test_concurrency_aware_migration_sm` 2 + `test_scheduling_contention` 30 + `test_scheduling_contention_gate` 19 + `test_contention_denied_503` 3. `pair_policy`/`nway_policy`/`active_region_holders` behavior unchanged (existing contention/gate/lock tests green).
- Pre-existing unrelated failure unchanged: `test_placement_policy.py::test_live_call_with_no_arg_does_not_crash` (parallel agent's `get_placement_policy` default).

### B CALL-SITE WIRING + C PREP — DONE 2026-05-30 (default-off, triple-inert)
- **Gate wiring** (`contention_gate.py`): `evaluate()` gains optional `candidate_topology_idx: int | None = None`. After the legacy pairwise+nway `worst` is computed, IF `candidate_topology_idx is not None` AND `shape_aware_contention_enabled()` → consult `seam_admit(role, idx, traffic_class=, matrix=)`. A non-None seam verdict is **authoritative** (`worst = seam_decision`), replacing the stale role-keyed legacy verdict in either direction. `seam_admit` exceptions are caught → legacy verdict. Imported `seam_admit` + `shape_aware_contention_enabled` into the gate. **Runtime inert until rollout:** dispatch now passes candidate indices only under the dual-flag path, but both flags are not enabled live together and the API was not reloaded.
- **Seeder** (`seeding_eval.py` `_can_add_role_to_seed_wave`): documented **no-op guard** — wave packing has no candidate placement, so shape-aware admission can't apply there; it belongs at dispatch (the gate's idx path). Legacy path unchanged. NO behavior change.
- **C PREP** (`contention.py`): pure `select_backfill_candidate(candidates, active_holders, traffic_class, *, instance_regions, matrix, floor)` — first candidate that is physically disjoint AND `admit_set`-ALLOW; returns None otherwise. **Unwired** (C prep only; the three C guards — heavy-port veto, `_wait_for_heavy_models_idle` idle barrier, pressure skip — are ALL still present and untouched, count-verified).
- **Tests:** `tests/unit/test_gate_seam_wiring.py` (7: ignores-seam-without-idx, ignores-when-flags-off, applies-tightening, never-loosens, None-keeps-legacy, exception-falls-back, no-holders-short-circuits) + `tests/unit/test_backfill_selection.py` (8). **Full affected suite: 161 passed**; dispatch/placement/concurrency: 16 passed. No regression.
- **GitNexus**: operator upgraded to **1.6.5** (restored `--skip-skills`); all 4 wrappers now `--skip-agents-md --skip-skills`. Infra follow-up resolved.

### ⚠️ B SEMANTIC FIX (audit #1/#2: authoritative seam) — CODE APPLIED, TESTS UNVERIFIED (harness output blank) 2026-05-30
**Operator finding (correct):** the gate seam was wired "tightening-only" (worse-of), which CANNOT unlock B's target — legacy role-keyed `pair_policy(frontdoor,ingest)=0.37→QUEUE` would always win over the placement-aware `seam_admit(frontdoor.q2 ∥ ingest{q0,q1})=ALLOW`. Tightening-only defeats the whole purpose of B.

**Fix applied (`contention_gate.py` seam block, ~line 248-285):** when both flags on AND `candidate_topology_idx` supplied AND `seam_admit` returns non-None → the seam is **AUTHORITATIVE: `worst = seam_decision`** (replaces legacy, both directions), NOT worse-of. SAFE because: (a) matrix-health fail-closed already returned earlier (stale matrix never reaches seam); (b) `seam_admit` is itself fail-closed — physical overlap→QUEUE, unknown placement→bg QUEUE, and its disjoint branch re-checks the SAME `nway_policy` legacy used, so it can only loosen the STALE role-keyed PAIR layer, never an actual measured n_way block; (c) seam returns None when disabled / unknown-fg / snapshot-fail-fg → keeps legacy `worst`. Runtime remains inactive until the dual flags are enabled live and the API is reloaded.

**Tests changed (`test_gate_seam_wiring.py`):** REMOVED the wrong `test_gate_seam_never_loosens` (it enshrined the bug). ADDED: `test_gate_seam_authoritative_overrides_legacy_queue` (mocked seam ALLOW overrides legacy QUEUE → admit), `test_gate_seam_authoritative_can_also_tighten` (seam QUEUE over legacy ALLOW → queue), `test_gate_real_seam_unlocks_disjoint_placement` (END-TO-END real seam_admit + monkeypatched region helpers: frontdoor q2 ∥ ingest node0-half → nway 1.716 → ADMIT), `test_gate_real_seam_overlap_still_queues` (real seam, overlapping candidate → QUEUE, fail-closed safe).

**✅ VERIFIED 2026-05-30:** authoritative fix confirmed live by direct Read (`contention_gate.py:290` = `worst = seam_decision`, NOT the old `_prec[]>` tightening) AND tests. `test_gate_seam_wiring.py` 10/10 pass incl. `test_gate_seam_authoritative_overrides_legacy_queue` (mocked seam ALLOW overrides legacy QUEUE → admit) + `test_gate_real_seam_unlocks_disjoint_placement` (real seam_admit, monkeypatched region helpers, frontdoor.q2 ∥ ingest node0-half → nway 1.716 → ADMIT) + `test_gate_real_seam_overlap_still_queues` (overlap → QUEUE). **Full affected suite: 179 passed** (gate_seam_wiring 10 + shape_aware_seam 15 + admit_set 15 + backfill_selection 8 + held_regions_snapshot 7 + scheduling_contention_gate 19 + scheduling_contention 30 + placement 17 + cpu_region_lock 23 + cross_role_region_mutex 3 + others). The intermittent blank-Bash-output during the edit caused a false "unverified" scare — Read + the from-file pytest result are authoritative and green. seam REMOVED `test_gate_seam_never_loosens` (enshrined the bug); net gate-wiring tests 7→10.

### Doc-drift fix 2026-05-30 (audit follow-up)
`test_gate_seam_wiring.py` module docstring still said the seam "only TIGHTEN … never loosen" (described the removed tightening-only behavior). Corrected to describe the authoritative-replace semantics. No stale "only TIGHTEN / never loosen / tightening-only" strings remain in either the test or `contention_gate.py` (grep=0). 10/10 gate-wiring tests still green.

### STOP POINT (operator-mandated) — UPDATED 2026-05-31
**Dispatch-side caller wiring is now DONE** (Step 2 above): the gate receives a real `candidate_topology_idx` from `_dispatch`. B is code-complete end-to-end. Held per the updated sequence: both shape-aware flags still default off, the API was NOT reloaded, no flag flip, autopilot untouched. Remaining is **rollout-only (no code)** — reload to arm Step 1, observe, then flip `SHAPE_AWARE_CONTENTION=1` after a live smoke. P3/C behavior changes (heavy veto / idle barrier / pressure skip removal) are NOT started — prep only until explicitly authorized.

### Original audit-fix notes (superseded by the section above, kept for trace)

Verification on this checkpoint: `tests/unit/test_admit_set.py` = 15 passed; admit_set + existing contention/gate/503 suite = 67 passed.

## HARD CONSTRAINTS (operator, binding)
1. Pure code + tests ONLY. **STOP before any call-site rewiring.** Do NOT touch `contention_gate.py` or `seeding_eval.py`.
2. Do NOT change `pair_policy()` / `nway_policy()` behavior.
3. `admit_set()` must be **unused by runtime** until explicitly wired (later, separate green-light).
4. Shape-key helpers key from **canonical region sets**, never labels ("full" is not an overlap predicate).
5. Unknown placement: **background → QUEUE; foreground → legacy `pair_policy()` fallback**.
6. Any matrix YAML annotation must be **proven loader-safe**. If the loader is strict (rejects unknown keys), add parser support preserving old behavior. **Do YAML last, only if genuinely non-behavioral.**

## IMPLEMENTATION STATUS (operator-specified order)
1. DONE — pure **placement value shape** + **shape-key helpers** (canonical region sets via `src/runtime/instance_topology.get_instance_regions()` → `frozenset[str]` of q0..q3). A "placement" = `(role, region_set)` or `(role, topology_idx)` resolved through `get_instance_regions`.
2. DONE — **`admit_set(active_placements, candidate_placement, traffic_class) -> PairDecision`** with truth-table tests using **synthetic** `ContentionMatrix` objects: disjoint heavy+light → ALLOW; overlapping → QUEUE/fail-closed; unknown-placement bg → QUEUE; unknown-placement fg → legacy pair fallback.
3. DONE — real-matrix regression: `{frontdoor, ingest_long_context, worker_general}` on disjoint quarters → ALLOW, while overlapping-primary `frontdoor+ingest` → QUEUE. This is the proof B resolves the ambiguity A couldn't.
4. DEFERRED — YAML annotations (mark overlapping-primary `block` entries placement-conditional) only if loader-safe and still useful after review.

## KEY CODE FACTS (verified this session, `src/scheduling/contention.py`)
- Enums: `TrafficClass` (FOREGROUND_INTERACTIVE/FOREGROUND_SPECIALIST/BACKGROUND/MAINTENANCE), `PairDecision` (ALLOW/QUEUE/DEGRADED_ALLOW/BLOCK), `MatrixStatus`.
- Dataclasses: `Pair(roles, ratio, verdict, samples, note)`, `InstancePair(a,b,ratio,verdict,cv)`, `SameRole(role,verdict,note,instance_pairs)`, `Nway(roles[sorted], ratio, verdict, cv, samples, contains_heavy)`, `ContentionMatrix` (starts line 117).
- `pair_policy(role_a, role_b, traffic_class, matrix=None, floor=None)` lines 299–373: role-keyed; `matrix.get_pair(a,b)` at :347; ratio≥1.0→ALLOW, ≥floor→ALLOW fg/QUEUE bg, <floor→QUEUE; unknown pair :348-358 (bg QUEUE / fg ALLOW); same role :334-345.
- `nway_policy(roles, traffic_class, matrix=None, floor=None)` lines 379–434: `matrix.get_nway(sorted_roles)` at :417; measured allow→ALLOW, borderline→ALLOW fg/QUEUE bg, block→QUEUE; unmeasured all-light→ALLOW, else bg QUEUE / fg ALLOW. `nway_light_roles`/`nway_heavy_roles` come from YAML (`_DEFAULT_HEAVY_ROLES = {ingest_long_context, architect_general}` line 376).
- `CONTENTION_RATIO_FLOOR = 0.85`; `load_contention_matrix()` constructs `ContentionMatrix`. `get_pair`/`get_nway`/`get_same_role`/`is_unknown_pair` are role-keyed `ContentionMatrix` methods; `get_pair`/`get_nway` ignore placement shape.
- YAML `pairs[].instance_a/instance_b` carry `{port, cpu_list, threads}` — the shape data B needs already exists; loader currently discards cpu_list into nothing shape-keyed (verify).

## admit_set DESIGN (from main handoff, decisions locked)
- Principled shape-keyed route (interim "n_way supersedes pair" rejected — leaves the 0.37∧1.716 ambiguity unexplained).
- For a candidate placement vs active set: if disjoint → consult role-set `n_way` (authoritative under A's certified smallest-disjoint-placement precondition); measured allow→ALLOW. If overlapping → infeasible (A should never produce; fail closed). Unknown placement → **bg+unknown → QUEUE** before legacy fallback; foreground keeps legacy `pair_policy` role-only fallback.
- `architect_general` strictly solo (placement layer gives it only whole-machine; NOT because pairs block — `architect+worker_general=1.11 allow` exists).

## TEST CONVENTIONS (this repo)
- Run with `.venv/bin/python -m pytest …` (system python lost PyYAML after devcontainer rebuild).
- New test file e.g. `tests/unit/test_admit_set.py`. Synthetic `ContentionMatrix` for truth table; real `load_contention_matrix()` for the one regression.
- Existing related green tests (must stay green): `test_placement.py`(16), `test_cpu_region_lock.py`(23), `test_cross_role_region_mutex.py`(3), `test_dispatch_cross_role_placement.py`(2), `test_dispatch_placement_state_machine.py`(4), `test_concurrency_aware_quarter_preference.py`(8), `test_concurrency_aware_migration_sm.py`(2).
- Pre-existing UNRELATED failure (NOT yours, stash-proven): `test_placement_policy.py::test_live_call_with_no_arg_does_not_crash` — parallel agent changed `get_placement_policy` default to BURST_PREFER_QUARTERS. Leave it.

## ENVIRONMENT / OPERATIONAL STATE
- Stack UP, healthy (35 components). Orchestrator API = uvicorn `src.api:app --workers 6` (pid changes on restart; discover via ss/pgrep, do NOT hardcode). It runs `ORCHESTRATOR_PER_REGION_LOCKS=1`, `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`, **no CROSS_ROLE_DISJOINT** → J6 is clean flag-OFF.
- J6 autopilot soak RUNNING: `autopilot.py start --no-controller --max-trials 2000`, state at `orchestration/autopilot_state.json` (trial_counter ~153+), journal `orchestration/autopilot_journal.{tsv,jsonl}`. Discover daemon pid via `pgrep -af "autopilot.py start"`.
- **STANDING CRITICAL CONSTRAINTS: do NOT restart stack or autopilot, do NOT flip the flag, do NOT relaunch J6, without explicit operator permission.**

## PARETO / FRONTIER FACTS (for the post-J6 flip decision, already answered to operator)
- `ParetoEntry.objectives` is a BAKED 4-tuple `(quality, speed, -cost, reliability)` persisted in `autopilot_state.json`; NOTHING recomputes speed from raw tokens/elapsed. `eval_tower.py:421`: `speed = aggregate_speed if eval_concurrency>1 else median_request_speed`.
- Planner re-reads past trials every iteration (archive.summary_text, journal.summary_text, pareto_geometry, strategy_store, parent_trial lineage) — but as baked summaries.
- **Retroactive rescale of pre-flip speeds: mechanically possible (rewrite stored objectives) but ADVISED AGAINST** — no clean scalar (aggregate vs median mix, role-dependent), violates the "don't mutate baselines" rule, high blast radius. Correct mechanism = `mark_epoch`/archive reset at flip, NOT rescale. Flag-on-and-resume contaminates frontier (mixed dispatch regime); flip is post-J6 only, in a quiesced flag-on→observe→revert-to-OFF bracket, unless deliberately adopting flag-on (which needs the epoch reset).

## TRACKING (done this session)
- Cross-role work now referenced in `bulk-inference-campaign.md` (TRACKING block + ⏳ ACTION ON J6 END), `routing-and-optimization-index.md` (subsystem row), main handoff. Stale J6 pid removed from bulk-inference handoff (replaced with runtime-discovery instruction).
- Memory written: `project_cross_role_contention_placement_blind.md` (+ MEMORY.md index line).

## Commit status
This checkpoint supersedes the earlier "nothing committed" note below: the wrap-up commit records the Step 1 launcher default, Step 2 dispatch-side candidate wiring, focused regression tests, and matching handoff/progress updates. Shared clone caution still applies for later work — stage explicit paths/hunks because unrelated runtime/autopilot files are often dirty.

## CONCRETE NEXT STEPS
1. After autopilot clears, reload the API to arm Step 1 (`ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`) and verify `/proc/<api_pid>/environ`.
2. Run the live smoke for Step 2 with `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1`: disjoint quarters should admit, true q-overlaps should queue, and dashboard attribution should remain usable.
3. Decide whether YAML annotations are still useful after the call-site design is fixed; loader uses `.get()` and is annotation-tolerant, but no annotation is currently required for the pure core.

---

## ⏯️ B CALL-SITE WIRING + C PREP — RESUME PLAN (2026-05-30, paused: flaky harness output during HIGH-blast-radius edit)

**Operator authorized:** default-off B call-site wiring (gate + seeder) AND C prep (tests/helpers only — NO removal of heavy veto / idle barrier / pressure skip). Paused BEFORE editing because harness output went intermittently blank and `contention_gate.py` is HIGH blast radius feeding live J6. Resume only with stable output. Nothing for this step written yet.

### Investigation complete (verified pre-pause)
- **Gate `evaluate(self, role, traffic_class)` has NO candidate placement** (`contention_gate.py:168`). Its holder view is `_active_holders()` (`:151-164`) using the **attribution** `active_region_holders()` (over-reporting). The `admit()` wrapper (`:269`) polls `evaluate` (`:296`). Only same-file caller is `:296`; external caller `env_synth/species.py:155` is a DIFFERENT `evaluate` (solvability gate), not this one.
- **Seeder `_can_add_role_to_seed_wave(role_name, wave_roles)` is role-only** (`seeding_eval.py:87-117`), called at wave-PACK time — no instance/placement chosen yet. `seam_admit` needs a candidate placement the seeder does not have here. **Wiring conclusion: seeder gets a documented no-op/guard, NOT a forced fake placement.** Real seeder shape-awareness belongs at dispatch, not wave-packing.
- **Dispatch** (`concurrency_aware.py:_dispatch`) already does placement via `evaluate_placement`; it does NOT call the gate. seam_admit is a gate/seeder concept.

### Wiring shape (default-off, additive — implement test-first when output stable)
1. **Gate `evaluate`:** add optional `candidate_topology_idx: int | None = None`. After the existing legacy `worst` computation, IF `shape_aware_contention_enabled()` AND `candidate_topology_idx is not None`: compute `seam = seam_admit(role, candidate_topology_idx, held_regions_by_role(), traffic_class=...)`; if `seam is not None`, `worst = _worse_decision(worst, seam)` (NEVER better — seam can only tighten). Off/idx-absent → byte-identical legacy. The `:296` caller passes no idx → unchanged. Thread idx through `admit()` too (optional, default None).
   - Use the EXACT view (`held_regions_by_role`) for the seam, but keep `_active_holders()`/attribution for the legacy pairwise loop (don't change legacy semantics).
2. **Seeder:** add a comment/guard documenting that shape-aware admission is dispatch-time (placement-bearing), not wave-pack-time; leave `_can_add_role_to_seed_wave` legacy. No behavior change.
3. **Tests:** gate test — flags-on + idx supplied + a held region that makes seam QUEUE where legacy ALLOWs → gate returns the tightened verdict; flags-off OR idx=None → identical to legacy (regression). Keep existing `test_scheduling_contention_gate.py` green.

### C PREP (tests/helpers only — DO NOT remove veto/barrier/skip)
C targets (all in `seeding_eval.py`): heavy-port veto `:98`; idle barrier `_wait_for_heavy_models_idle` `:393-395`; pressure skip `:1069-1078`. Prep = add a PURE `select_backfill_candidate(...)`-style helper + tests that, given a free-region set + remaining roles + matrix, picks the next admissible role for the idle quarters (the work-conserving logic C will eventually call) — WITHOUT touching the three guards. Heavy-slot-erase narrowing is design-only until B is wired+observed under an epoch boundary.

### Standing invariants (unchanged)
- J6 flag-OFF, untouched. No flag flips. Nothing committed (working tree). Both flags required for any shape-aware path. gitnexus stale (1.6.1 analyze segfault) → grep for wiring checks. Run tests with `.venv/bin/python -m pytest ... -p no:cacheprovider`.
