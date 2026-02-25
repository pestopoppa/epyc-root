# PR Draft: Orchestration Architecture Optimization

## Title
`orchestration: risk-controlled posterior routing + telemetry/workspace/regulation hardening`

## Summary
This PR implements the architecture-optimization handoff across routing, escalation, replay metrics, and tuning surfaces.

### Implemented
1. Decoupled routing confidence from similarity and switched learned gating to robust Q-confidence (`median`/`trimmed_mean`).
2. Replaced cache-affinity score hacks with explicit expected warm/cold cost modeling.
3. Implemented conditional schema escalation (capability-gap aware; parser/transient schema failures remain retry-only).
4. Added teacher/delegation reward shaping hooks and richer trajectory extraction metadata.
5. Added replay calibration/risk metrics: `ece_global`, `brier_global`, `conformal_coverage`, `conformal_risk`.
6. Added think-harder ROI regulation scaffolding and bounded workspace-state propagation.
7. Added heuristic prior + learned posterior routing blend (without bypassing hard constraints).
8. Exposed retrieval/risk tuning parameters across seeding, debugger replay context, and meta-agent candidate path.
9. Completed docs updates for architecture, memrl, escalation, cost-aware routing, and calibration/risk control chapter.
10. Fixed proactive async regression: architect planning call is offloaded via `asyncio.to_thread(...)` in production paths, with test/mocked inline fallback to avoid teardown deadlocks.

## Validation
Command:
```bash
pytest -q -n 0 \
  tests/unit/test_replay_engine.py \
  tests/unit/test_pipeline_routing.py \
  tests/unit/test_chat_pipeline_stages.py \
  tests/unit/test_stream_adapter.py \
  tests/unit/test_escalation.py \
  tests/unit/test_orchestration_graph.py
```

Result: `159 passed`

## Shadow Replay Snapshot (14-day)
Dataset:
- Complete trajectories: `1000`
- Incomplete skipped by extractor: `230`

Comparison:
- Baseline: `RetrievalConfig()`
- Tuned: `cost_lambda=0.22`, `confidence_estimator=trimmed_mean`, `confidence_trim_ratio=0.15`, `confidence_min_neighbors=5`, `warm_probability_hit=0.88`, `warm_probability_miss=0.12`, `calibrated_confidence_threshold=0.67`, `conformal_margin=0.03`, `risk_control_enabled=True`, `risk_budget_id='default'`, `risk_gate_min_samples=3`, `risk_abstain_target_role='architect_general'`, `risk_gate_rollout_ratio=1.0`, `risk_gate_kill_switch=False`, `risk_budget_guardrail_min_events=50`, `risk_budget_guardrail_max_abstain_rate=0.60`, `prior_strength=0.15`

| Metric | Baseline | Tuned | Delta |
|---|---:|---:|---:|
| routing_accuracy | 0.0000 | 0.0000 | 0.0000 |
| avg_reward | 0.9720 | 0.9720 | 0.0000 |
| cumulative_reward | 972.05 | 972.05 | 0.00 |
| cost_efficiency | 0.9720 | 0.9720 | 0.0000 |
| ece_global | 0.0000 | 0.0000 | 0.0000 |
| brier_global | 0.0000 | 0.0000 | 0.0000 |
| conformal_coverage | 1.0000 | 1.0000 | 0.0000 |
| conformal_risk | 0.0150 | 0.0150 | 0.0000 |

Interpretation:
- No measurable delta on this replay slice. Treat as instrumentation sanity check, not a performance claim.

## Required Final Task Matrix

| Parameter | Runtime use site | Seeding capture/consumption path | Debugger visibility | Meta-agent tunability |
|---|---|---|---|---|
| `cost_lambda` | `orchestration/repl_memory/retriever.py` (`_retrieve`, `GraphEnhancedRetriever._retrieve_with_graph`) | `scripts/benchmark/seed_specialist_routing.py` (`_build_retrieval_config_from_args` -> periodic/post replay `ReplayEngine.run_with_metrics`) | `src/pipeline_monitor/claude_debugger.py` (`retrieval_overrides` + replay summary) | `orchestration/repl_memory/replay/meta_agent.py` (`_PARAM_RANGES`, `_format_config`) + `orchestration/repl_memory/replay/candidates.py` |
| `confidence_estimator` | `orchestration/repl_memory/retriever.py` (`_compute_robust_confidence`) | same seeding path | same debugger path | same meta-agent path |
| `confidence_trim_ratio` | `orchestration/repl_memory/retriever.py` (`_compute_robust_confidence`) | same seeding path | same debugger path | same meta-agent path |
| `confidence_min_neighbors` | `orchestration/repl_memory/retriever.py` (`_apply_confidence`, replay confidence extraction) | same seeding path | same debugger path | same meta-agent path |
| `warm_probability_hit` | `orchestration/repl_memory/retriever.py` (`_estimate_cost_components`) | same seeding path | same debugger path | same meta-agent path |
| `warm_probability_miss` | `orchestration/repl_memory/retriever.py` (`_estimate_cost_components`) | same seeding path | same debugger path | same meta-agent path |
| `warm_cost_fallback_s` | `orchestration/repl_memory/retriever.py` (`_estimate_cost_components`) | same seeding path | same debugger path | same meta-agent path |
| `cold_cost_fallback_s` | `orchestration/repl_memory/retriever.py` (`_estimate_cost_components`) | same seeding path | same debugger path | same meta-agent path |
| `calibrated_confidence_threshold` | `orchestration/repl_memory/retriever.py` (`get_effective_confidence_threshold`, `should_use_learned`, `get_best_action`) | same seeding path | same debugger path | `orchestration/repl_memory/replay/meta_agent.py` (`_PARAM_RANGES`, `_format_config`) + candidates serialization |
| `conformal_margin` | `orchestration/repl_memory/retriever.py` (`get_effective_confidence_threshold`) | same seeding path | same debugger path | same meta-agent path |
| `risk_control_enabled` | `orchestration/repl_memory/retriever.py` (`get_effective_confidence_threshold`) | same seeding path | same debugger path | parsed in `orchestration/repl_memory/replay/meta_agent.py` + persisted in `orchestration/repl_memory/replay/candidates.py` |
| `risk_budget_id` | `orchestration/repl_memory/retriever.py` (`evaluate_risk_gate`, decision meta emission) | same seeding path | same debugger path | formatted/parsed in `orchestration/repl_memory/replay/meta_agent.py` + persisted in `orchestration/repl_memory/replay/candidates.py` |
| `risk_gate_min_samples` | `orchestration/repl_memory/retriever.py` (`evaluate_risk_gate`) | same seeding path | same debugger path | `_PARAM_RANGES` + `_format_config` in `orchestration/repl_memory/replay/meta_agent.py` |
| `risk_abstain_target_role` | `orchestration/repl_memory/retriever.py` (`HybridRouter.route`, `route_with_mode`) | same seeding path | same debugger path | `_format_config` + candidate persistence path |
| `risk_gate_rollout_ratio` | `orchestration/repl_memory/retriever.py` (`_is_risk_gate_enforced_for_route`) | same seeding path | same debugger path | `_PARAM_RANGES` + `_format_config` in `orchestration/repl_memory/replay/meta_agent.py` |
| `risk_gate_kill_switch` | `orchestration/repl_memory/retriever.py` (`evaluate_risk_gate`) | same seeding path | same debugger path | `_format_config` + candidate persistence path |
| `risk_budget_guardrail_min_events` | `orchestration/repl_memory/retriever.py` (`_guardrail_blocks_gate`) | same seeding path | same debugger path | `_PARAM_RANGES` + `_format_config` in `orchestration/repl_memory/replay/meta_agent.py` |
| `risk_budget_guardrail_max_abstain_rate` | `orchestration/repl_memory/retriever.py` (`_guardrail_blocks_gate`) | same seeding path | same debugger path | `_PARAM_RANGES` + `_format_config` in `orchestration/repl_memory/replay/meta_agent.py` |
| `prior_strength` | `orchestration/repl_memory/retriever.py` (`HybridRouter._apply_priors`) | same seeding path | same debugger path | `_PARAM_RANGES` + `_format_config` in `orchestration/repl_memory/replay/meta_agent.py` |

## Risks / Follow-ups
1. Replay currently shows no metric separation for tuned vs baseline retrieval config on sampled trajectories.
2. Follow-up: improve replay candidate-action simulation sensitivity to retrieval knobs and confidence thresholds.
3. Follow-up: run staged shadow/live checks before enabling strict calibrated thresholds globally.
