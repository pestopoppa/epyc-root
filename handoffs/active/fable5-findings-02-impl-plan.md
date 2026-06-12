# Fable 5 findings 02 — IMPLEMENTATION PLAN: routing decision architecture

**Date**: 2026-06-12 (refinement pass, operator-requested). **Companion to**: `fable5-findings-02-routing-decision-architecture.md`. Phases ordered by (damage stopped) ÷ (effort); everything before Phase 3 is justified regardless of which routing end-state you pick.

---

## Phase 0 — Truth restoration (days). *The live system must match SOME declared intent before any redesign is meaningful.*

**0.1 Declare the production flag set.**
- Add an explicit `PRODUCTION_FEATURE_ENV` block to `orchestrator_stack.py` (next to the existing env assembly at `:1114-1193`) that sets `ORCHESTRATOR_<FLAG>=1/0` for **every** registry flag from its `default_prod` — making `/proc/<pid>/environ` a complete, attestable record. (Preferred over calling `get_features(production=True)` at app startup: env wins on precedence, survives reloads identically, and is externally inspectable.)
- **Operator decision required first**: do you *want* prod defaults? Several `default_prod=True` flags (specialist_routing, plan_review, architect_delegation, parallel_execution, model_fallback, unified_streaming) have been silently OFF for months — the system you've been operating IS the test-default system. Recommend: enable in two waves — wave 1 `specialist_routing` + `model_fallback` (low-risk, restores keyword priors + circuit-breaker fallback), wave 2 the heavier paths (plan_review, parallel_execution, unified_streaming) each behind a one-week observation window, because **none of these code paths has run in production recently** — treat them as new code.
- Delete the `production=` ambiguity afterwards: `get_features()` keeps env-only behavior; the parameter stays for tests.

**0.2 Shared, attestable runtime flags.**
- New `orchestration/runtime_flags.json` (atomic-write). `features()` gains a TTL re-read: cache the parsed Features + file mtime; on access, if `now - last_check > 1s`, `stat()` and reload on mtime change (`src/features.py:577-600`; one stat/sec/worker — negligible). Precedence: env (boot intent) < runtime file (operator/autopilot overrides) — and the file records `{flag: value, set_by, ts}` for audit.
- `POST /config` (`src/api/routes/config.py`) writes the file (and updates its own process immediately). All 6 workers converge within 1s.
- `GET /config/attest` (new): returns `{pid, flags, source}` for the answering worker; a small client (`scripts/validate/attest_flags.py`) hits it N×20 times to collect all worker PIDs and diffs them — red if heterogeneous. This becomes part of the ATTESTATION artifact (findings-04 impl).
- **Autopilot interaction**: `structural_lab.apply_flag_experiment` (`:404-412`) gets a post-apply attestation poll (all workers report the new value) before the eval starts — flag experiments become valid for the first time. Also journal the attestation result with the trial.

**0.3 Q-scorer cost-model refresh.** `q_scorer.py:89-99` baselines marked KNOWN STALE (frontdoor 12.7 vs measured ~21–27). Until descriptors (Phase 2) exist, read `baseline_tps_by_role` from the lean registry's measured values at startup. One afternoon; directly de-biases every cost-aware routing decision and reward.

**0.4 Deletions** (zero production impact, proof in findings-02 §4): `get_confidence_routing` + helpers (`chat_routing.py:283-448`), `HybridRouter.route_3way` (`hybrid_router.py:587-699`), `dispatch_swarm_fanout` + module if no handoff claims it within the month. Un-set `ORCHESTRATOR_ROUTING_CLASSIFIER` until weights exist (stop the boot-warning lie). Expected: −1.5–2K LoC, several test files.

**0.5 Shadow telemetry persistence.** Trinity/difficulty/URE shadows currently log to INFO that doesn't persist (the audit could not find their outputs on disk). Either route shadow events into `logs/progress/*.jsonl` (the file QScorer already mines) or stop running them per-request. Without this, TR-3.3/3.4 gates are unsatisfiable and the shadows are pure cost.

## Phase 1 — Measure before redesigning (1–2 days of analysis, gates everything after)

**1.1 DAR-1 regret replay on current traffic** (the handoff's own Phase 1, never run on post-reset data): replay last-7-days routing decisions; for the subset with outcome labels, compute regret vs oracle-best-role. **Gate**: regret ≥5% of requests → proceed to Phase 3; <5% → freeze Phase 3 indefinitely and record routing as not-a-bottleneck (re-run quarterly or on workload change). Prediction from the evidence (77% frontdoor, 96%-uniform Q, cheap-first absorbing easy traffic): **<5%**.
**1.2 Cheap-first hit-rate**: instrument `_try_cheap_first` accept/reject counters into progress JSONL (they're currently unobservable on disk); a week of data answers whether Phase-A unconditional try is paying or burning worker slots.

## Phase 2 — Model-capability descriptors (the model-agnosticism interface; ~1 week; valuable even if Phase 3 never happens)

**2.1 Schema** — `orchestration/model_descriptors.yaml`, one entry per model (NOT per role; `feedback_model_not_role_indexing`):
```yaml
- model_id: qwen3.6-35b-a3b-q8        # canonical: family-params-quant
  family: qwen3.6 ; arch: moe-a3b ; params_b: 35 ; active_b: 3
  quant: Q8_0 ; mem_gb: 37 ; ctx_max: 131072 ; modalities: [text]
  quality: {suite_vector: {math: .92, coder: .81, ...}, source: research-registry@<commit>, eval_protocol: MEASUREMENT.md#canonical-quality}
  speed: {solo_96t_tps: 27.1, quarter_48t_tps: 7.2x4, prefill_tps: ..., source: bench@<date>}
  acceleration: {spec_type: none|mtp|draft, draft_compat: [qwen3-1.7b, qwen3-0.6b], enable_thinking: false, kv: {k: q8_0, v: q8_0}}
  serving: {binary: fork|ik-pr1744, numa_policy: ..., mlock: true}
  descriptor_version: 3 ; compiled_at: ...
```
**2.2 Compiler** — `scripts/registry/compile_descriptors.py`: sources = research registry (comprehensive benchmark record) + lean registry (deployed config) + bench artifacts; refuses to emit a descriptor with missing load-bearing fields (lists gaps instead). Run at stack launch (compose with the existing `--compile-registry` path) and on registry change. **First consumers (immediate, no router redesign)**: q_scorer cost model (replaces 0.3's stopgap), seeder per-role eval config, `orchestrator_stack` acceleration args (spec/MTP/enable_thinking travel with the model — kills the `_NO_SPEC_DECODE` / ik-binary special-case class), eval-tower model signatures (replaces the hand-maintained `model_quality_signatures.yaml`, stale since 2026-04-16, fed to the planner every trial).
**2.3 Swap test (the model-agnosticism gate)**: simulated swap — replace one role's descriptor with a candidate model's, replay a day of routing decisions + launch-arg generation; PASS = no code edits required, only data. This becomes the standing CI for "model-agnostic" and the precondition for ever letting the autopilot propose model swaps (Stack-Config axis).

## Phase 3 — The unified cascade (ONLY if Phase 1 gate passes; ~2–3 weeks)

**3.1 One predictor**: `P(success | task_features, model_descriptor)` — bilinear form (DAR-4's shape, the right one because it factorizes over descriptors and generalizes to unseen models), trained offline from the episodic store + per-question eval ledger (findings-01 Phase 1 supplies labels the store lacks), calibrated (isotonic; report ECE), shipped with an abstain band (the risk-gate concept, now as the same model's uncertainty rather than a parallel mechanism).
**3.2 One policy**: `argmax_m ω·[P(success|m), −cost(m, placement_state)]` where cost comes from descriptors + live placement state (queue depth is already in routing_meta — currently consumed by nothing; this is where it plugs in). Cheap-first = evaluating the cheapest m first with an accept threshold (Phase B/C code exists); escalation = posterior update after observed failure, re-argmax (the chain `worker→coder→architect` becomes the cost-ordered candidate list, not a hardcoded map); think-harder = an action in the same argmax (cost = 2× tokens).
**3.3 Migration**: shadow the unified policy for 2 weeks (log decisions side-by-side, diff rate + simulated-outcome delta); flip role-selection first; fold the special-case mutators (failure-veto, ingest-guard, risk-band effects) into features over 2 more weeks; delete `should_use_learned`/prior-blend/threshold arbitration last. KNN store remains the online memory feeding retraining; MLP/GAT retire.
**3.4 Non-goals**: placement/contention untouched (separate, working, safety-critical); no learned coordinator (OC-*) — data budget unchanged at ~10² labeled outcomes/day; no multi-step planner.

## Acceptance & rollback summary
- 0.2 acceptance: attestation diff across workers is empty after any POST /config; a structural_experiment trial journals uniform attestation.
- 0.1 wave-1 rollback: env block re-emit with flag=0 + reload (one command, runbook line).
- Phase 2 acceptance: swap test passes for 2 candidate models; planner prompt's model signatures show compiled_at within 7 days.
- Phase 3 gate is Phase 1's replay; its rollback is the shadow flag.

## Effort table
| Phase | Effort | Blocked by |
|---|---|---|
| 0.1–0.5 | ~1 week total, parallelizable | operator wave-1/wave-2 decision |
| 1 | 1–2 days | 0.5 (telemetry) for cheap-first; replay runs on existing logs |
| 2 | ~1 week | none (compiler can start today) |
| 3 | 2–3 weeks | Phase 1 gate + findings-01 Phase 1 (labels) |
