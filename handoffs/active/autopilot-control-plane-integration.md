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

- [ ] **AP-1 — Register tuning-surface class 1 (control-plane governance)** in the guarded numeric-surface manifest (OP-1/P0.2 lineage): review-trigger complexity threshold, iteration bounds, confidence/band cutoffs, reminder cadence, per-subtask-review gate, majority-k, request-evidence budget. Wire via `config_applicator.apply_params` → runtime flags (cheap knobs, no restart); seed initial values via the strategy store (flag-gate + SQLite write, per seeding discipline).
- [ ] **AP-2 — Register class 3 (GPU placement/teleport policy)**: long-running-stream detection trigger (token count / rate window), migration break-even threshold, GPU lease policy weights. Cheap runtime-policy knobs; the mechanisms live in the MI210 roadmap — autopilot only tunes declared policy parameters.
- [ ] **AP-3 — Classes 2/4 (spec-dec composition; per-role KV config)**: restart-scoped launch-arg knobs (`--spec-type` set, `--spec-draft-n-max`, tree width/depth, ngram n_min; KV dtype f16-vs-q8_0, Expected-Attention aggressiveness once server-wired) — declared with restart-cost annotations → expensive-trial class in the species budget; applied via registry launch params + `orchestrator_stack.py` sequential reload.
- [ ] **AP-4 — New Pareto quality axes**: reviewer FA/FR (+ratio) and per-decision latency join task quality/throughput as objectives; SafetyGate + `sequential_verdict` integration; instrument-era registration for the new axes (append, never rewrite).
- [ ] **AP-5 — New actions in `actions.py`**: `review_policy_trial` (class-1 sweep), `placement_policy_trial` (class-3), and the **H5 screening-tier driver** (fan out cheap pairings via eval-tower T0/T1; placement-queue discipline, NOT /chat; respects no-concurrent-inference windows).
- [ ] **AP-6 — Dogfooding**: the autopilot's Claude-planner/codex_critic loop (`planner_providers.py` — codex is already read-only) adopts the typed ReviewDecision schema (H2) for plan critiques → first live control-plane tenant, generating calibration ledger rows for free.
- [ ] **AP-7 — State/journal schema extensions**: `autopilot_state.json` + journal events for review decisions/policy trials; checkpoint compatibility (checkpoints save autopilot_state.json — lost frontier = lost compute); journal rotation awareness (read all `_<n>.jsonl` shards).
- [ ] **AP-8 — Digest/dashboard surfacing**: reviewer-calibration trends in `digest.py` output + handoff-dashboard hub.

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
