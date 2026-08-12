# Objective: task_rate Axis + Goodput Frontier Rebuild

**Status**: W3 FLIPPED AND LIVE ✅ 2026-08-04 — live dominance is `task_rate_4d_v1`
`(quality, seq_task_rate_qph, -cost, reliability)` (`afdd5d74`); legacy `median_request_tps` is now
the shadow series. Frontier restarted at the flip commit. Open: W3d (the superseded hold conditions,
incl. the still-live zero-quality/high-rate objection), W3e (retire the tier-cost axis — blocked by
positional consumers), W5 (regime-profiled offered load).
**Created**: 2026-06-12
**Updated**: 2026-08-04
**Priority**: ACTIVE — the flip landed on an operator decision; remaining work is axis hygiene (W3d/W3e) and the load-profile era (W5)
**Spec**: [fable5-findings-05-objective-design.md](../completed/fable5-findings-05-objective-design.md) — read before claiming any waypoint. Slots into [fable5-findings-01-impl-plan.md](../completed/fable5-findings-01-impl-plan.md) as Phase 1.6.
**Related**: [evidence-plane-instrument-repair.md](evidence-plane-instrument-repair.md) (noise/admission rules the new axis inherits), [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) (live consumer), [MEASUREMENT.md](../../MEASUREMENT.md) §P-SPEED-OBJ (already names task_rate as the speed axis) + §5 era table (E3→E4 retire-view)

## 2026-07-27 Operator re-prioritization — PIVOT-FIRST after bench closure

Operator (reviewing the E8 frontier): "optimizing [median_request_tps] is gameable — verbose
output pumps the metric; the only real-world metric is how quickly orchestration performs a
task, and how well." This is this handoff's thesis; elevated out of the dead lane as the
FIRST item of the post-closure robustness/workload-tuning pivot (master-index ★ block).
Key unlock: the 16 fresh E8 reseed trials (2026-07-26/27) are era-fenced, honest-instrument
rows — plausibly satisfying W3's quality-eligible-replay gate — and the replay is
deterministic journal recomputation (zero inference; per MEASUREMENT_POLICY.md →
*Deterministic replay before regeneration*). Sequence: replay E8 rows → task_rate/goodput
frontier → operator policy decision on the live vector flip (P-SPEED-OBJ already names
task_rate as the axis) → panels relabel (extends E8-PANELS-a axis-labeling task).

## 2026-07-26 Staleness Review

The era prerequisite has advanced, but the
[design-backlog triage](design-backlog-triage-2026-07-23.md) still requires a
fresh quality-eligible replay: the previous task-rate frontier admitted
quality-floor violations. W3 therefore remains a narrowly gated replay and
policy decision, not a live-vector flip.

## Why

The current Pareto vector is fully blind to token bloat: quality, t/s, and
reliability are all bloat-invariant, and the "cost" axis is a routing-tier
average, not a token count — so a verbose and a terse config at equal
correctness are Pareto-indistinguishable while differing 30% in wall-per-task
(spec §verdict). An entire manual research domain (TrimR, brevity limits,
enable_thinking=False, tool-output compression) exists as corrective work the
optimizer could not discover natively. `task_rate` = n / eval-wall-hours; both
inputs are journaled, so the axis replays over FULL journal history at zero inference.

## Waypoints

- [x] **W1 — axis + shadow journal** (~half day): added task-rate helpers and policy constants in `src/autopilot_core/tier_specs.py`; `eval_tower._aggregate()` records `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task`; new journal rows include live legacy vector + shadow task-rate vector under policy labels.
- [x] **W2 — historical replay + bloat-artifact diff report** (~half day, ZERO inference): replay implemented via `scripts/analysis/task_rate_goodput_replay.py` and `journal_reconstruction` objective-policy replay. Full-journal report: `epyc-orchestrator/orchestration/reports/task_rate_goodput_replay_2026-06-12.md`. Follow-up `d21bbee` folds append-only supersession events before rendering report rows, so replay tables match supersession-aware archive/dashboard state. Follow-up `47c75de` adds a `Baseline Promotion Evidence` section scoped to `baseline_promotion` events whose source trial is present in the effective folded replay rows; malformed/incomplete events render as `n/a` rather than crashing the report.
- [x] **W3 — flip the vector** ✅ 2026-08-04 — LIVE. Operator threw the armed W3b-C tripwire
      ("Autopilot should use tasks/hr"). Landed as `task_rate_4d_v1`
      `(quality, seq_task_rate_qph, -cost, reliability)` in `afdd5d74`, **not** the planned 3-D
      vector, and **not** on the shadow rate metric. Three findings forced both departures:
      - The 3-D `task_rate_3d_v1` CANNOT be the live vector. Consumers index the tuple
        positionally past axis 1 — `safety_gate.py:2303` refuses `len(objectives) < 4`
        ("frontier representative missing objective tuple") and `pareto_archive.py` reads
        `[2]`/`[3]`. Going 3-D would not raise; it would **silently block every baseline
        promotion**. `tier_specs.objectives_from` is the documented chokepoint on
        CONSTRUCTION, but not on CONSUMPTION. So the 4-D shape is kept and axis 1's UNIT
        changes. **Retiring the tier-cost axis is therefore still open — see W3e.**
      - Axis 1 uses `seq_task_rate_qph`, not `task_rate_qph`. The latter divides the
        decision-partition question count by the FULL-batch wall clock: trial 775 scored
        202.9 qph @ 51.5 t/s vs trial 778 at 170.5 qph @ 49.8 t/s — a **19% objective gap
        from a 3% speed difference**, the rest being `n` moving 43→38. It also returns
        `0.0` for "unavailable" on **128 of 1,466** journal rows.
      - `dominates()` truncated via `zip()`, so a 3-D point vs a 4-D one compared qph
        against t/s and reliability against `-cost`. It now raises on shape mismatch.

      Verified live on trial 1472: `objectives_live_v1 = [2.025, 59.49, -0.5, 0.8]`,
      `objectives_legacy_v1 = [2.025, 14.78, -0.5, 0.8]`. Frontier restarted via
      `pareto_exclude_before_ts` at the flip commit (both vectors are 4-D, so nothing
      catches a mixed frontier by shape — the epoch fence is what separates them).
- [x] **W3d — the 2026-06-13 hold conditions were never satisfied; they were superseded.**
      Record why, so the hold is not silently re-derived: the flip shipped on an operator
      decision, not on the ">=2/5 legacy frontier points drop" proof threshold. The
      "raw `task_rate` admits a zero-quality high-rate frontier point" objection is still
      LIVE and unaddressed — quality remains a separate axis, so a zero-quality/high-rate
      point can still enter the frontier. Decide whether goodput (quality-scaled rate)
      should replace raw rate on axis 1, or whether the reliability floor is sufficient.
      **✅ 2026-08-12 (`mainA`, pulled from the generated bench and claimed) — RECORDED, and the
      objection is not merely still live: it is MEASURABLY REALISED, and the mechanism is worse
      than the row states.**
      **The live vector** (`tier_specs.py:328` `_rate_objectives_from_row`) is
      `(quality, rate, -cost, reliability)`, all maximised. Quality is read as
      `float(row.get("quality") or 0.0)`.
      **1. A zero-quality high-rate point genuinely cannot be excluded by dominance.** It is
      dominated only by a point that is at least equal on ALL FOUR axes. A point holding the max
      rate is unbeatable on rate, so nothing dominates it regardless of how bad its quality is.
      Pareto cannot fix this; only a floor or a scaled axis can. Searched for one — no
      `quality_floor` / `min_quality` / reliability floor exists in `src/autopilot_core/`.
      **2. The worse half: ABSENT quality is silently scored as ZERO.** `or 0.0` cannot
      distinguish *measured zero* from *never measured*. Measured over both journal shards:
      **231 of 1372 trial rows (16.8%) carry falsy or absent quality** and are therefore admitted
      to the frontier as zero-quality points. So the objection is not a hypothetical about a
      future bad point — one row in six is already in that state.
      **3. `objectives_measurable` promises more than it checks.** Its docstring reads *"True when
      this result carries every axis the live dominance vector needs"* and its body is
      `return seq_task_rate_qph_from(result) is not None` — it validates the RATE and nothing else.
      A row with no quality, cost or reliability passes a gate whose name and docstring both say
      it checked them. That is the same claim-without-witness shape as the era stamps and the
      `--validate-only` help text, sitting in the objective plane.
      **Why the hold was superseded, recorded so it is not silently re-derived:** the flip shipped
      on an operator decision, not on the `>=2/5 legacy frontier points drop` proof threshold the
      2026-06-13 hold named. The threshold was never met and never waived — it was overtaken. Any
      future reader finding the hold unsatisfied should NOT reinstate it; it is void, not pending.
  - [ ] **OPERATOR DECISION — goodput vs raw rate on axis 1.** Not mine to take, and it is bigger
    than a scoring tweak: per the 2026-08-11 rider, a metric change is structurally an **ERA
    BOUNDARY** and should be recorded as an era row rather than an edit. Three options: (a)
    quality-scaled goodput replaces raw rate on axis 1; (b) raw rate stays and a quality floor
    gates admission; (c) status quo, accepting that ~1 row in 6 enters at zero quality.
    **Recommend (b) plus a separate fix**: a floor addresses the dominance hole without redefining
    a banked axis, and the 231 absent-quality rows are a DATA defect that a metric change would
    silently paper over — `or 0.0` should distinguish absent from zero regardless of which option
    is chosen, or the same 231 rows will re-enter under goodput scored as zero goodput.
- [ ] **W3e — retire the tier-cost axis from dominance** (deferred out of W3). The original
      W3 scope included dropping `-cost`; that is what made the vector 3-D and is blocked by
      the positional consumers above. Doing it means fixing `safety_gate.py:2303` and
      `pareto_archive.py`'s `[2]`/`[3]` reads to be axis-NAME-driven rather than positional.
      Until then `-cost` stays a dominance axis and the frontier is wider than intended.

### W6 — the eval instrument the rate axis is measured on (opened 2026-08-04)

Questions/hour is only meaningful relative to a fixed question set, so the flip made the
instrument's composition load-bearing in a way it never was under tokens/second.

- [x] **W6a — declare the tier mix** ✅ 2026-08-04 (`81be1e56`). The sampler stratified by
      SUITE only (`per_suite = n // len(suites)`); difficulty tier was never a sampling
      dimension, so the realized mix was a byproduct — the real seed-42 n=50 draw was
      **T1:24 / T2:15 / T3:11** and moved with `n` and with any pool edit. Operator chose
      **equal thirds**. Verified on the real 79,479-row pool: n=50 → 17/17/16, n=100 →
      34/33/33, 34 distinct suites still represented, deterministic. A starved tier is
      REPORTED, never backfilled from another tier. **Dashboard visibility ✅ 2026-08-09
      (`epyc-orchestrator` `9e7e5226`)**: GEPA and Pareto now distinguish the outer EvalTower
      lane from this inner difficulty mix. Current points render as `lane T1` plus
      `D1/D2/D3 17/17/16`, with the scored/target count, policy, core id, and rotation in
      point/row context; a bare `T1` no longer falsely implies T1-only decision questions.
- [x] **W6b — rotate the core draw so the optimizer cannot overfit one set** ✅ 2026-08-04
      (`ce6e4bea`). Operator: *"the draw should be somewhat randomized."* Rotating PER TRIAL
      was rejected with numbers: quality is a fraction-correct over n=50, so an independent
      draw each trial adds binomial error `sqrt(0.25/50)` = 7.1% ≈ **0.21 on the 0–3 scale**
      against a baseline near 1.5 — several times the effect sizes the ratchet detects.
      Rotation is per EPOCH (default 20 trials, env-overridable): fixed within a block,
      fresh between. Measured cross-block overlap **3/50, 0/50, 1/50**, mix 17/17/16 every
      rotation. n, mix and pool constant ⇒ expected difficulty unchanged ⇒ a rotation does
      NOT force a re-baseline.
- [x] **W6c — make instrument drift detectable across a restart** ✅ 2026-08-04 (`8e90948e`).
      `_DATASET_SHA_BY_CORE_ID` was a module-level dict, so drift was only visible WITHIN one
      process — and a pool edit lands while the daemon is DOWN. That is exactly how the
      2026-08-04 debugbench retarget passed unnoticed. Ledger persisted; tier mix compared
      too, because `dataset_content_sha256` deliberately does not hash `tier`.
- [ ] **W6d — decide whether the mix should be production-traffic-weighted rather than
      equal thirds.** Equal thirds was chosen as a clean default; a production-representative
      mix would make qph track real throughput more closely. Needs the production task-tier
      distribution, which was not established — the investigation was cut short. Cheapest to
      change while a frontier is already restarting.
- [ ] **W6e — surface the generalization gap.** The W6 audit block already draws FRESH
      questions per trial (`_audit_seed(trial_id, core_id)`) but is `shadow_only=1`. Report
      core-vs-fresh score as an explicit overfitting signal, so epoch rotation is
      instrumented rather than assumed to be sufficient.
- [ ] **W6f — re-establish the T1 quality baseline on the new instrument.** Cleared
      2026-08-04 because equal thirds is a harder mix than the old T1-heavy draw and holding
      1.5357 would score every new trial as a regression and block all promotion. Old values
      preserved in state under `_pre_equal_thirds_baseline_record`. Blocked on trials landing
      on the new instrument; will self-seed via the SG-3/B3a explicit-seed path.
  - [x] **W3a — E8 quality-eligible replay EXECUTED** ✅ 2026-07-27 (Claude session, zero
    inference; report `epyc-orchestrator/orchestration/reports/task_rate_goodput_replay_e8_20260727.md`).
    Machinery green on the fresh era: 1356 journal rows parsed (0 malformed), state epoch
    scoping admitted exactly the **16 E8 reseed trials**; the 2026-06-13 blocker class is
    ABSENT on E8 rows (no zero-quality/low-quality frontier admissions — all task-rate
    frontier points q≥1.77, floor 1.0). Legacy frontier 3 points / HV 8.16; task-rate
    frontier 5 points / HV 150.33; task-rate ADDS trials 1444 (89.1 q/h, 1487 tok/solved)
    and 1456 (83.2 q/h). **Pre-registered drop criterion NOT met** (0/3 legacy points fall
    off; spec needs ≥2/3): the 16 homogeneous surface-sweep trials don't vary verbosity, so
    axis divergence hasn't had a chance to appear. Flip decision → operator (options below).
  - [x] **W3b — operator flip decision: OPTION C chosen** ✅ 2026-07-27 — dual-report
    interim: legacy stays the live dominance vector; task_rate/goodput surfaces on panels +
    telemetry immediately; flip armed on first observed divergence (amber tripwire badge when
    ≥2 legacy frontier points drop under task-rate). Options A (flip now) and B (silent hold)
    declined in favor of visibility-without-risk.
  - [x] **W3c — dual-report panel implementation** ✅ 2026-07-27 (orchestrator `3f21d760`,
    +508/−22, 296+2 tests green; canonical helpers reused from tier_specs + the replay module,
    zero math reimplemented; live-journal smoke reproduces the E8 report: legacy frontier
    {1445,1446,1450}, task-rate adds 1444/1456, tripwire quiet at dropped=0; activates at the
    queued API reload): pareto payload gains task_rate_qph/goodput_qph/tokens_per_solved + offered_load
    per entry (canonical helpers, no reimplementation); speed-axis toggle (median request t/s
    ↔ task_rate q/h); dual-report banner; server-side divergence tripwire. Display-only;
    dominance unchanged; ships at the queued API reload.
  - [x] **W3d — panel activation verified live** ✅ 2026-07-27: API-only reload via
    `orchestrator_stack.py reload orchestrator` (performed while fixing the probe-env health
    flapping); `/dashboard/api/pareto` confirmed serving `task_rate_qph`, `goodput_qph`,
    `tokens_per_solved`, `offered_load` + divergence tripwire; 6/6 backend probes green
    post-reload.
- [ ] **W5 — regime-profiled offered load (NEXT INSTRUMENT ERA, pairs with batching
  integration; operator design decision 2026-07-27).** The trial eval's single fixed arrival
  pattern (closed-loop concurrency-3) means task_rate measures one operating point; configs
  can win that point while being wrong for sparse single-request traffic. Resolution chosen:
  regime-ADAPTIVITY stays in the router/placement layer (WP-12 burst machinery + placement
  surfaces are already AutoPilot-trialable); regime-REPRESENTATIVENESS moves into the eval —
  a small offered-load profile set (sparse-1 / steady-3 / burst-N), task_rate per profile,
  dominance on the steady profile or an F1-real-task-corpus-weighted mix. Explicitly REJECTED:
  baking regime-switching into the scalar (unauditable, newly gameable; violates
  one-number-one-protocol). The `offered_load` field landed in W3c future-proofs rows/panels
  for this.
- [x] **W4 — telemetry + doc truth** (~half day): `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task` are journaled; `scripts/autopilot/program.md` now states that EvalTower `speed` remains the current Pareto speed axis/host-throttle diagnostic, task-rate fields are shadow policy telemetry, and `tokens_per_solved_task` is the bloat diagnostic. The stale wall-occupancy `sum(tokens_generated[role] / throughput_tps[role])` proxy is explicitly marked as not computed/not live. `rg` found no other live system-card copy of that stale text.
- [x] **W5 — policy decision** (2026-06-13, zero inference): keep `task_rate_qph`, `goodput_qph`, and `tokens_per_solved_task` as shadow telemetry; leave live Pareto dominance on the current objective until preconditions below are met.

## 2026-06-13 Policy Decision

**Verdict: HOLD the live vector flip; continue shadow telemetry.**

Rationale:

- The replay did not meet the Fable proof gate: only 1/5 legacy canonical T1 frontier points fell off under `task_rate_3d_v1`; the proposed gate was >=2/5.
- Raw `task_rate` creates an obviously unsafe frontier point: trial 75 enters the task-rate frontier with quality 0.000 and goodput 0.00 because it completed quickly. Quality remains an axis, but the replay proves raw rate alone can preserve junk candidates as non-dominated noise.
- Findings-01 dependencies are not fully in place: per-question ledger, sequential verdicts, core_v2 repair, and E4 retire-view bootstrap are still pending, so flipping now would create another objective-era boundary before the evidence plane can certify effects.

Reopen W3 only after all of these are true:

- N2 per-question ledger + sequential e-process verdict path is live for the restart bundle.
- Instrument repair/core_v2 or equivalent E4 boundary is in force, with frontier/baseline retire-view mechanics ready.
- A replay of the chosen policy (`task_rate` with explicit quality eligibility, or a goodput-shaped variant) no longer admits zero-quality high-rate frontier entries.
- The replay either meets the original >=2/5 historical-frontier proof threshold or a documented shadow-period result shows task-rate/goodput changes live decisions without degrading quality/reliability.

## Gates & pitfalls

- Wall time carries the same ~9% host-noise CV as t/s (spec caveat 1) — findings-01 Phase 1.4 sequential/median-cluster admission rules apply to the new axis unchanged; never single-trial rate claims.
- `task_rate` depends on question mix AND eval concurrency — both are instrument: fix per core-version, bump policy version on any change; per-suite wall telemetry attributes which suites pay the bloat.
- **2026-08-05 boundary prepared**: orchestrator `65aac3d6` bumps the live identifier to
  `task_rate_4d_v2_resource_lanes`, retains `task_rate_4d_v1` only for faithful historical
  replay, rejects mismatched snapshots from live archive authority, and refuses startup until
  state names the matching execution instrument. The E9 registry/state apply remains human-owned;
  no v2 measurements exist until that transaction is applied.
- Degenerate-terseness is bounded (quality is a co-equal axis); if a long-form role emerges, add a suite-level format-adequacy check — never re-reward tokens globally.
- Tool tokens stay excluded from the rate (already correct); tool use is priced by downstream correctness + wall cost.
- Replay is retire-view, not rewrite: journal rows are immutable; quality is NOT rescaled across eras (MEASUREMENT.md §5).

## Reporting

Tick waypoints here + one-line progress entry; all rate numbers via the MEASUREMENT.md §2 claim grammar. The master-index N6 row was removed on 2026-06-13 after the hold decision; future W3 work belongs in the gated cluster until reopen criteria are met.

## Checkpoints

- 2026-06-12 W2 replay result: 656 journal rows parsed, 0 malformed skipped; legacy canonical T1 frontier = 5 points, task-rate replay frontier = 8 points, admitted entries = 247 in both views. Dropped legacy point: trial 776 (quality 1.884, wall 804.5s, task_rate 192.42 q/h, goodput 120.82 q/h) dominated by trial 775 under task-rate. Fable proof criterion (`>=2 of 5`) was **not met**.
- Verification: `uv run pytest tests/unit/test_autopilot_core_contracts.py tests/unit/test_eval_tower_concurrency_metrics.py tests/unit/test_eval_tower_hybrid_eval.py tests/unit/test_autopilot_controller_io.py tests/unit/test_evolution_manager_scrub.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_per_suite_regression_resolution.py tests/unit/test_self_criticism_resolution.py` → 81 passed; `git diff --check` clean.
- 2026-06-12 W4 doc-truth verification: `gitnexus impact File:scripts/autopilot/program.md --direction upstream` LOW; `rg` confirms the only remaining stale wall-occupancy phrase is the negated warning in the updated text; `git diff --check -- scripts/autopilot/program.md` clean. Landed in `epyc-orchestrator` `9bc4c3a`.
- 2026-06-13 W5 policy checkpoint: live dominance flip held. Shadow telemetry remains useful, but the NOW-class decision is closed as "do not flip yet"; W3 remains gated on N2/E4 and a quality-eligible replay.
- 2026-06-14 replay read-path follow-up: `epyc-orchestrator` `d21bbee` makes `scripts/analysis/task_rate_goodput_replay.py` fold append-only supersession events before rendered report rows. Regression coverage in `tests/unit/test_task_rate_goodput_replay.py` verifies folded values replace raw superseded metrics; combined analytics validation passed (`15 passed`) with focused ruff and diff-check clean.
- 2026-06-14 baseline-promotion evidence follow-up: `epyc-orchestrator` `47c75de` makes `task_rate_goodput_replay.py` report baseline promotion evidence scoped to effective folded replay rows. It does not affect legacy or task-rate archive reconstruction, and incomplete promotion events render safely. Validation: `python3 -m py_compile scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `uv run ruff check scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `git diff --check -- scripts/analysis/task_rate_goodput_replay.py tests/unit/test_task_rate_goodput_replay.py`; `uv run pytest -q tests/unit/test_task_rate_goodput_replay.py` -> 3 passed.
