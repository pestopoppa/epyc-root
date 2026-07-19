# Reviewer Control Plane — Autopilot Integration (H8)

**Status**: active — gated on H2 (schema) + H3 (shadow decisions); screening driver additionally on H4 corpus v1
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; operator: "a lot of upgrade work to do to autopilot to tackle all the new design surfaces")
**Categories**: agent_architecture, routing_intelligence, cost_aware_routing
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) (runtime truth-of-record), [`reviewer-model-ablations.md`](reviewer-model-ablations.md) (H5 screening consumer), [`scaffold-autopilot-cost-lever-deployment.md`](scaffold-autopilot-cost-lever-deployment.md) (cost-lever lineage)
**Repo**: `epyc-orchestrator` (`scripts/autopilot/`, `src/autopilot_core/`)

## Objective

Upgrade the autopilot to exploit the control plane's new design surfaces: register the four tuning-surface classes, add reviewer-calibration Pareto axes, add the tournament screening driver, and dogfood the typed ReviewDecision schema into the autopilot's own planner/critic loop. Context: the Pareto frontier has been **flat at 75.08 for 4+ days** — the optimizer has exhausted its current knob space; these are genuinely orthogonal knobs.

## Prioritized Task List

- [x] **AP-1 — Register tuning-surface class 1 (control-plane governance)** ✅ 2026-07-17 (knob registry + validate/normalize/classify plumbing → ORCHESTRATOR_DELEGATION_* env-restart bucket; reads review_plane_knobs.yaml w/ graceful fallback; seed entries as fixture, NOT written to live store; orchestrator `30d3232b`) in the guarded numeric-surface manifest (OP-1/P0.2 lineage): review-trigger complexity threshold, iteration bounds, confidence/band cutoffs, reminder cadence, per-subtask-review gate, majority-k, request-evidence budget. Wire via `config_applicator.apply_params` → runtime flags (cheap knobs, no restart); seed initial values via the strategy store (flag-gate + SQLite write, per seeding discipline).
- [x] **AP-2 — Register class 3 (GPU placement/teleport policy)** ✅ 2026-07-19 (`epyc-orchestrator` `c5abe0a3`): default-off `placement_policy.*` manifest and apply plumbing now covers long-running-stream trigger tokens, rate window, resident break-even threshold, minimum speedup, and GPU lease weights by workload mix; `gpu_placement_policy` NumericSwarm can tune thresholds/weights but cannot flip `placement_policy.teleport_enabled`, which requires explicit `AUTOPILOT_AXA3_TELEPORT_ENABLE=1`. Cheap runtime-policy knobs only; the teleport mechanism and production enablement remain in the MI210 roadmap.
- [ ] **AP-3 — Classes 2/4 (spec-dec composition; per-role KV config)**: restart-scoped launch-arg knobs (`--spec-type` set, `--spec-draft-n-max`, tree width/depth, ngram n_min; KV dtype f16-vs-q8_0, Expected-Attention aggressiveness once server-wired) — declared with restart-cost annotations → expensive-trial class in the species budget; applied via registry launch params + `orchestrator_stack.py` sequential reload.
  - [x] **AP-3a — Guarded role-restart registry/applicator surface ✅ 2026-07-19** (`epyc-orchestrator` `d8dcaad1`): `role_restart.*` manifest block, enum-aware validation, registry-override grouping, rollback/smoke-check reuse, and explicit `AUTOPILOT_AP3_ROLE_RESTART_ENABLE=1` live gate. NumericSwarm exposes only the numeric subset (`frontdoor_draft_max`, `worker_draft_max`, `worker_draft_p_min`, `worker_threads_draft`, `architect_draft_max`); categorical `spec_type` and KV-profile choices stay explicit quality-gated action params.
  - [ ] **AP-3b — Source-prove remaining launch fields before exposure**: draft-tree policy and any future verification-depth/tree-width controls need exact current llama.cpp/server registry names and pass/fail launch probes before they can become planner-visible restart knobs.
    - [x] **AP-3b.1 — Source-proven ngram/draft-min/split numeric controls wired ✅ 2026-07-19** (`epyc-orchestrator` pending commit): read-only v7 source proof confirmed `--spec-type ngram-mod,draft-mtp` is a real ordered ngram-first/MTP-fallback chain; current server flags include `--spec-draft-n-min`, `--draft-p-split`, and `--spec-ngram-mod-n-{min,max,match}`. These are now registered as guarded `role_restart.*` numeric knobs for frontdoor, worker, and architect lanes; `NumericSwarm` can sweep the numeric subset, but categorical spec-type/KV/reasoning choices remain explicit quality-gated actions. Launcher plumbing now carries the overrides through `stack_priors.py` into real `llama-server` argv, including legal zero values for ngram minima.
    - [ ] **AP-3b.2 — Draft-tree / verification-depth decision**: source proof found no independent MTP depth or verification-depth flag; MTP `n_max` is capped by model NEXTN metadata. Decide whether `draft-tree` belongs in AP-3 at all, then source-prove any tree-specific controls before exposure.
  - [ ] **AP-3c — Expected-Attention launch policy**: expose only after the server-wired EA/evict policy fields are source-proven and paired with quality checks.
- [x] **AP-4 — New Pareto quality axes** ✅ 2026-07-17 (reviewer_fa_rate/fr_rate/ratio/decision_latency_ms as OPTIONAL EvalResult axes, purely additive; era-registration row emitted as fixture — instrument_eras.yaml untouched, operator action): reviewer FA/FR (+ratio) and per-decision latency join task quality/throughput as objectives; SafetyGate + `sequential_verdict` integration; instrument-era registration for the new axes (append, never rewrite).
- [x] **AP-5 — New actions in `actions.py`** ✅ 2026-07-17 (`review_policy_trial` + `screening_tier_driver` registered; dry-run plans (screening queue entries carry dispatch:placement_queue per RM-3); live path env-flag-gated → NotImplementedError, zero-inference honored): `review_policy_trial` (class-1 sweep), `placement_policy_trial` (class-3), and the **H5 screening-tier driver** (fan out cheap pairings via eval-tower T0/T1; placement-queue discipline, NOT /chat; respects no-concurrent-inference windows).
- [x] **AP-6 — Dogfooding** ✅ 2026-07-17 (codex_critic critiques emit schema-valid ReviewDecisions via parse_review_decision; content/control-flow untouched; parse failures counted in CODEX_REVIEW_DECISION_STATS; ledger seam import-guarded no-op until live): the autopilot's Claude-planner/codex_critic loop (`planner_providers.py` — codex is already read-only) adopts the typed ReviewDecision schema (H2) for plan critiques → first live control-plane tenant, generating calibration ledger rows for free.
- [x] **AP-7 — State/journal schema extensions** ✅ 2026-07-17 (as-scoped: event-type constants + dataclasses + REVIEW_STATE_DEFAULTS checkpoint-compat in review_policy_trials.py; experiment_journal.py untouched, no live writes): `autopilot_state.json` + journal events for review decisions/policy trials; checkpoint compatibility (checkpoints save autopilot_state.json — lost frontier = lost compute); journal rotation awareness (read all `_<n>.jsonl` shards).
- [x] **AP-8 — Digest/dashboard surfacing** ✅ 2026-07-17 (digest reviewer-calibration section, import-guarded, renders no-data-yet gracefully): reviewer-calibration trends in `digest.py` output + handoff-dashboard hub.

## Dependency Graph

```text
H2 + H3 shadow → AP-1 → AP-4 → AP-5(review_policy_trial)
AP-2 after MI210 roadmap teleport-axis tasks declare their knobs
AP-3 after kernel handoff quality-clears composed-spec configs (ngram-mod JSON errors NOT quality-cleared yet)
AP-5 screening driver after H4 corpus v1 → feeds H5 RM-3
AP-6 after H2 schemas ; AP-7 with AP-4 ; AP-8 last
```

## Cross-Cutting Concerns

1. **Emergent-behavior hazard** (intake-846): small changes to governing knobs can unpredictably change downstream behavior — bound the search ranges in the manifest; rely on full tracing (H1) to diagnose; SafetyGate + e-process demotion as the backstop.
2. **Instrument discipline** — new Pareto axes are instruments; era-register them; autopilot numbers remain observations until P-REV-1-cited.
3. **Spec-dec quality gate** — class-2 sweeps must pair every speed number with a correctness/garbage check (ngram-mod +50.6% came with errorful JSON).

## Key Files / Surfaces

- `scripts/autopilot/actions.py` (`_ACTION_HANDLERS`), `config_applicator.py`, `planner_providers.py`, `digest.py`, `species/` + `meta_optimizer.py`
- `src/autopilot_core/{sequential_verdict.py, baseline_ledger.py, pareto_math.py}`; `scripts/autopilot/safety_gate.py`
- `orchestration/repl_memory/strategy_store.py` (seeding), `orchestration/autopilot_state.json`

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; knob registrations recorded here + in the numeric-surface manifest changelog; first frontier movement on the new axes reported to H0; autopilot restarts follow SIGTERM+drain discipline.

## Evidence Base (intake)

intake-846 emergent-behavior + effort-scaling · intake-835 adaptive review gating (2509.03581: −85% tokens at equal reward) · intake-849 P7 sticky/predicate patterns · Pareto-flat-at-75.08 digests (progress/2026-07/*-autopilot.md) · audit doc 2026-07-16.
