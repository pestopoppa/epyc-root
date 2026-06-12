# Evidence Plane — Instrument Repair (Phase-0 hotfixes + pool sampling)

**Status**: SPEC'D, not started (from the Fable 5 architecture review)
**Created**: 2026-06-12
**Priority**: NOW/HIGH — live damage: the t775 baseline ratchet is failing ~half of honest trials today
**Spec**: [fable5-findings-01-impl-plan.md](fable5-findings-01-impl-plan.md) Phase 0 + Phase 2 (exact sites/changes/acceptance per item) and [fable5-findings-01-measurement-and-integrity.md](fable5-findings-01-measurement-and-integrity.md) §3 (defect evidence) — read before claiming any waypoint
**Related**: [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) · [eval-tower-verification.md](eval-tower-verification.md) (EV-4 calibration waits on this) · [../../MEASUREMENT.md](../../MEASUREMENT.md) §P-QUAL-T1/P-QUAL-PROMO (the instrument card this work realizes) · [../../repos/epyc-orchestrator/orchestration/instrument_eras.yaml](../../repos/epyc-orchestrator/orchestration/instrument_eras.yaml) — append era E4 when the repaired instrument lands · downstream: [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md)

## Why

The autopilot's instrument resolution sits below the effect sizes being optimized: of the
fixed 43-question T1 set, ~8 can never pass (`expected=''` gate, missing pandas, vl unresolved)
and ~14 more are saturated — effective discriminating n ≈ 10–14 (spec Phase-2 evidence). On
top of that, eight live gate defects (worst: trial 775 ratcheted the T1 baseline to its
all-time noise max, so the −5% gate now fails the modal honest outcome) are actively writing
spurious reverts/blacklists. This handoff stops the live damage, repairs the dead questions,
then replaces the accidental seed=42 core with a designed, versioned sampling architecture
over the 53K pool. Sites, schemas and acceptance live in the spec — not duplicated here.

## Waypoints

- [ ] **W1 — ratchet + double-check hotfixes** (impl 0.1+0.2, ~1 day): `safety_gate.py` `update_baseline` requires repro-cluster median (or rolling-median interim) + one-time operator reset of `baselines_by_tier['1']` (1.953 → cluster median ~1.84); single `gate.check()` per trial via handler-returned verdict. Acceptance: replay 714–776 modal outcome passes; MAD window gains exactly 1 entry/trial.
- [ ] **W2 — gate plumbing hotfixes** (impl 0.3–0.5, ~1 day): live `speed_floor_anchor` refreshed in `update_tier` (re-arms host-throttle remediation); T0 fork — recommend drop from `hybrid_eval` (operator picks a/b); self-criticism threshold `max(0.02, quantum)` with new `unchanged` label. Acceptance per impl table (35 t/s injection trips floor; ≥60% of last-120 keep/revert labels become `unchanged`).
- [ ] **W3 — narrative-leak + quantum clamps** (impl 0.6–0.8, ~half day): strategy-store write gated on `not learning_excluded_by`; distill filters `bug_corrupted_by`/exclusion-tagged rows; server-side clamp of planner-supplied eval `n`/`seed`. Acceptance: unit tests per impl table.
- [ ] **W4 — instrument repair** (impl 2.0, 2–3 days): fix or scope the `expected==''` scoring gate; pandas into the venv (or excise the 2 bcb items); trace ONE vl eval request end-to-end (cause unresolved); NFKD diacritic fold in `_normalize_text` + pool scan; journal T0 sentinels as `sentinel_<suite>`; persist Seeder per-question results + seen-set into `seeder_state`. Acceptance: zero structurally-dead items left in T1, or each consciously excised.
- [ ] **W5 — designed core_v2** (impl 2.1, 2–3 days + ONE operator-approved calibration batch ~300q×3): `benchmarks/prompts/core_v2.jsonl` (~40 items, per-item p∈[0.2,0.8], stratified), versioned `core_id` journaled per trial. Acceptance: first pool-level quality estimate with a CI; core selected from measured item stats, not accident.
- [ ] **W6 — rotating audit block** (impl 2.2, 1 day): +10 fresh stratified pool questions/trial, trial-id-seeded; overfit alarm (core-delta vs audit-delta correlation) + pool-level estimator. Acceptance: audit outcomes journaled per-qid; +23% wall accepted or every-2nd-trial fallback chosen.
- [ ] **W7 — item analytics** (impl 2.3, 2 days, zero inference): `scripts/autopilot/item_analytics.py` weekly/per-100-trials — per-qid p, discrimination, broken-item report. Acceptance: each of the 5 pinned-zero suites verdicted artifact-vs-genuinely-hard (resolves the effective-n question).
- [ ] **W8 — promotion evals** (impl 2.4, ~1 day wiring): `confirmed` candidates trigger a fresh stratified n=200–500 draw; promotion needs core-confirmed AND promotion-delta CI excluding regression. Acceptance: per MEASUREMENT.md P-QUAL-PROMO.

## Gates & pitfalls

- W1–W3 ship at the next routine autopilot restart; nothing here touches the orchestrator API. W1 is live damage — first.
- Do NOT naively rotate the core: fresh-questions-per-trial multiplies trial variance ~4× (spec Phase-2 preamble). The fixed paired core is the design; the pool feeds audit/analytics/promotion instead.
- W5's calibration batch is inference — per-run operator approval required; W8 consumes `confirmed` verdicts from [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md).
- Core/instrument changes invalidate cross-version comparisons — bump `core_id`, append era E4 to `instrument_eras.yaml`, never mix n=38/n=43/core_v2 frontiers.
- The first sweep's vl explanation ("no vision server") was WRONG (ports live, plumbing present) — trace before fixing (`feedback_observe_before_diagnosing`).

## Reporting

Tick waypoints + one-line progress entry per phase; claim numbers per MEASUREMENT.md grammar (e.g. `[P-QUAL-T1/core_v2, n, date]`); on completion delete this handoff's master-index row and move to `completed/`.
