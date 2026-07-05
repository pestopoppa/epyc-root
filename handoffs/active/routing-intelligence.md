# Routing Intelligence: Factual-Risk Rollout

**Status**: COMPACTED 2026-05-28. Phases 0-5 implementation history moved to completed ledger. Live work is RI-10 canary decision, RI-11/RI-12 staged rollout, optional threshold work before any threshold change, and a gated injection-risk fork for DAR-6/J14. 2026-07-05 current-window refresh shows RI-10 telemetry is decision-ready: current-window arm counts are sufficient (`enforce_high_risk=31`, `shadow_high_risk=50`), role coverage is populated (`frontdoor=11/11`, `worker_general=10/23`, `worker_vision=10/16`), and current deficit counters are zero. The first decision packet (`ri10_canary_decision_report_20260705T150054Z`) is `hold_quality_unscored`: enforce has favorable operational proxies (p95 latency ratio `0.080068`, mean estimated-cost ratio `0.382801`, operational error-rate delta `-0.02`, no escalation/review inflation), but both arms have `quality_count=0`, so RI-11 must stay frozen until factuality/accuracy is scored. A scored request/answer-key packet now exists at `orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.{json,payloads.jsonl,answer_key.jsonl}`: `60` planned requests, `30` enforce / `30` shadow, `20` per canary role, no nontrivial expected-answer leakage into payloads. Frontdoor has only `4` unique eligible expected-answer prompts under current classifier thresholds, so interpret that arm with the recorded uniqueness caveat. Treat the July 4 `20`-row / `1` enforce / `19` shadow state as historical pre-accrual context. `epyc-orchestrator` removes process-RNG canary skew on the live chat path by deriving RI-10 enforce/shadow assignment from a stable task-id sample key while preserving the configured `canary_ratio`; the next step is executing/scoring the prepared factuality packet, not more telemetry-depth collection.
**Priority**: HIGH for RI-10 decision; MEDIUM for injection-risk fork after J14.
**Blocked by**: quality-scored factuality/accuracy evidence for the now decision-ready enforce/shadow canary sample; operator-approved inference/eval windows for rollout decisions.
**Completed ledger**: [`../completed/routing-intelligence-completed-through-2026-05-28.md`](../completed/routing-intelligence-completed-through-2026-05-28.md)
**Updated**: 2026-07-05

## Start Here

Do not implement the old Phase 4/5 sections from the completed ledger. They were superseded by RI-1 through RI-8 landing in March/April 2026. The next implementer should:

1. Pull current RI-10 canary data from logs before deciding anything; elapsed calendar time is not sufficient.
2. Confirm the current decision-ready sample still has enough arm-attributed rows in both enforce and shadow.
3. Use `scripts/analysis/ri10_canary_decision_report.py` to compare operational proxies, then run or attach scored factuality/accuracy evidence for both arms. Prepared packet: `orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.payloads.jsonl` with answer key `...answer_key.jsonl`.
4. Choose RI-11 expand, rollback to shadow, or threshold rework only after factuality is scored.

Current 2026-07-05 refresh: live Fable/DS-E1 reads report `ri10_telemetry_collection_blocker=decision_ready`, `enforce_high_risk=31`, `shadow_high_risk=50`, and zero current sample/volume/balance deficits. `epyc-orchestrator` `a24a95a4` adds the RI-10 decision packet generator and commits `orchestration/reports/ri10_canary_decision_report_20260705T150054Z.{json,md}`. That packet reports `hold_quality_unscored`: operational rows are favorable to enforce (`31/31` success, p95 `2.583s`; shadow `49/50` success, p95 `32.26s`), but factuality/accuracy is absent for both arms. `scripts/analysis/ri10_canary_request_plan.py` now has dataset-backed scored mode and generated `ri10_canary_scored_request_plan_20260705T151725Z.{json,payloads.jsonl,answer_key.jsonl}` from `factual_risk_calibration_v2.jsonl`; run the payloads in a quiet window and score against the answer key before RI-11. The earlier 2026-07-04 reports (`ri10_canary_sample_report_20260704T095500Z.json`, `ri10_canary_sample_report_all_roles_20260704T005332Z.json`) remain useful as historical diagnostics for the pre-accrual `20`-row imbalance, but should not be used as the current blocker state.

## Live Tasks

- [ ] **RI-10 — Shadow-to-enforce canary decision**: current canary is configured as 25% enforce / 75% shadow on `frontdoor`, `worker_general`, and `worker_vision`, and `7647b32e` exposes the chosen arm in routing progress metadata. The 2026-07-04 deterministic sampler fix makes future arm assignment stable per task id instead of process-RNG sampled, and the 2026-07-05 refresh shows telemetry depth is decision-ready. Decision packet `20260705T150054Z` holds on `factuality_not_scored`; do not expand to RI-11 from operational proxies alone. Decision requires:
  - controlled restart/window with `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true`; `ORCHESTRATOR_FACTUAL_RISK_MODE` is not the canary switch because it only accepts `off|shadow|enforce`;
  - >=50 arm-attributed high-risk samples or a documented reason to use a lower-powered decision; current refresh satisfies the depth gate with `31` enforce and `50` shadow high-risk rows;
  - no p95 latency regression >10%;
  - no cost regression >5% at equal factuality;
  - no unexplained escalation/review inflation >20%;
  - no 5xx/error cluster attributable to factual-risk scoring.
  - scored factuality/accuracy for both arms, or an explicit operator-approved lower-evidence decision. Prepared scored packet: `ri10_canary_scored_request_plan_20260705T151725Z.payloads.jsonl` plus `ri10_canary_scored_request_plan_20260705T151725Z.answer_key.jsonl`.
- [ ] **RI-11 — Enforce expand**: if RI-10 passes, expand to frontdoor 100% plus worker_general for 7 days. Keep a rollback flag path to shadow.
- [ ] **RI-12 — Global enforce**: only after RI-11 passes; update dashboards/alerts and q-scorer baseline dependencies.
- [ ] **RI-9b — Threshold/Pareto sweep if thresholds change**: Package B already produced risk-distribution profiling. Run a fresh threshold sweep only if RI-10 suggests changing bands or enforcement thresholds.
- [ ] **RI-13 — Injection-risk classifier fork (DAR-6/J14)**: do not build until the cheap-first unconditional J14 swarm-fanout A/B clears its gate. If it clears, add an injection-risk axis to this handoff rather than burying it in DAR.
- [ ] **RI-X — New-model onboarding contract**: if learned-routing-controller P5.2 passes, document cold-start workflow here and link the `tools/onboard_specialist.py` wrapper from that handoff.

## Dependency Graph

```text
AR-3 / production traffic
    -> RI-10 canary sample counts
        -> RI-11 expand
            -> RI-12 global enforce

RI-10 threshold pathology
    -> RI-9b threshold/Pareto sweep
        -> repeat RI-10 decision

DAR-6.5 unconditional J14 A/B pass
    -> RI-13 injection-risk classifier
        -> conditional swarm-fanout routing
```

## Forks And Mitigations

| Condition | Action |
|-----------|--------|
| RI-10 lacks high-risk samples | Keep canary; route traffic generation through AR-3/bulk-inference rather than changing thresholds blindly. |
| Enforce improves factuality but inflates cost | Sweep thresholds with RI-9b; prefer role-specific thresholds over global rollback. |
| Enforce regresses factuality or latency | Roll back to shadow; preserve logs and add a short failure analysis before retesting. |
| Verifier role lands via tri-role coordinator | Keep factual-risk review trigger as a substrate; Verifier may subsume review execution but not the risk signal. |
| SAE-feature classifier looks attractive | Treat as audit/interpretability layer only until difference-in-means and linear-probe baselines are run on the same v2 calibration slice. |
| Deep-research classifier work is needed | Use [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md); do not expand this handoff for MindDR. |
| P3 consult gating becomes downstream consumer | Provide `factual_risk_score` / `difficulty_band` / shadow-routing signals as inputs to [`internal-interaction-lifecycle.md`](internal-interaction-lifecycle.md) P3 `should_consult()` policy; routing-intelligence owns signal QUALITY, not lifecycle. |

## Key Files

| Repo | Path | Purpose |
|------|------|---------|
| epyc-orchestrator | `src/classifiers/factual_risk.py` | prompt-side factual-risk scorer |
| epyc-orchestrator | `orchestration/classifier_config.yaml` | classifier/factual-risk config and thresholds |
| epyc-orchestrator | `src/api/routes/chat.py` | cheap-first bypass and request routing surface |
| epyc-orchestrator | `src/api/routes/chat_pipeline/routing.py` | plan review gate, failure graph veto, routing metadata |
| epyc-orchestrator | `src/escalation.py` | risk-aware escalation policy |
| epyc-orchestrator | `scripts/analysis/ri10_canary_sample_report.py` | RI-10 telemetry-depth gate |
| epyc-orchestrator | `scripts/analysis/ri10_canary_decision_report.py` | RI-10 operational-proxy + factuality-readiness decision packet |
| epyc-research | `scripts/benchmark/seed_specialist_routing.py` | seeding/eval harness for A/B and threshold sweeps |
| epyc-research | `orchestration/factual_risk_calibration_v2.jsonl` | 2,600-example v2 calibration dataset |

## Completed Scope

| Scope | Outcome | Evidence |
|-------|---------|----------|
| Phase 0 telemetry | Delegation/routing telemetry fields repaired. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 1 classifier module | Types/config/output parsers and keyword delegating wrappers completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 2 MemRL classifier | `ClassificationRetriever` and exemplar seeding completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 3 factual-risk scorer | Regex scorer and shadow logging completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 4 enforcement code | RI-1 through RI-7 implemented and A/B tested; initial A/B underpowered. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 5 seeding fields | RI-8 verified on `RoleResult`; v2 calibration dataset built via NIB2-34. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| RI-10 arm telemetry repair | Routing now logs the sampled factual-risk canary arm as `routing_meta.factual_risk_mode`, and the plan-review gate reuses that persisted arm instead of resampling. Existing 2026-06-20 rows remain insufficient; collect fresh post-fix rows before a rollout decision. | `epyc-orchestrator` `7647b32e`; `uv run pytest -q tests/unit/test_factual_risk.py tests/unit/test_pipeline_routing.py` -> `110 passed` |
| RI-10 report/gate semantics hardening | `ri10_canary_sample_report.py` now distinguishes raw high-risk volume from decision-grade arm-attributed telemetry, separates historical missing-mode rows from the current telemetry-health window, and derives default canary-role scope from `classifier_config.yaml`. DS-E1/Fable5 aggregate gates stay blocked when only raw count is ready. The 2026-07-04 current report has `464` raw high-risk rows since canary start, `20` current-window high-risk rows with `0` missing mode, and all `20` current rows fall inside the widened canary role scope; the scope-free diagnostic returns the same current-window count, so the blocker is insufficient arm count/balance. | `orchestration/reports/ri10_canary_sample_report_20260704T005256Z.json`; `orchestration/reports/ri10_canary_sample_report_all_roles_20260704T005332Z.json`; `orchestration/reports/fable5_gate_report_20260704T005355Z.md` |
| RI-10 deficit surfacing | Current report consumers now expose the exact collection deficits instead of only repeating "not ready": `canary_role_sample_deficit=30`, `canary_arm_volume_deficit=30`, and balance deficits `enforce=9`, `shadow=0`, plus by-role and by-role-arm counts in DS-E1/Fable next-action evidence. DS-E1 also refreshes from live progress logs when the latest saved RI-10 artifact predates the new schema. | `epyc-orchestrator` `807939fa`; `uv run python -m pytest -q tests/unit/test_ri10_canary_sample_report.py tests/unit/test_dynamic_stack_evidence_packet.py tests/unit/test_fable5_gate_report.py` -> `47 passed` |
| RI-10 decision-ready refresh | Live Fable/DS-E1 reads now show RI-10 no longer blocks the aggregate gate: current-window arm counts are sufficient (`enforce_high_risk=31`, `shadow_high_risk=50`), role coverage is populated (`frontdoor=11/11`, `worker_general=10/23`, `worker_vision=10/16`), and the current deficit counters are zero. Treat the July 4 insufficient-sample notes above as historical pre-accrual state. | 2026-07-05 live read-only refresh; `ri10_telemetry_collection_blocker=decision_ready`; Fable gate after W8 repair blocks only on W6 audit clearance |
| RI-10 decision packet | Standalone decision report now joins current canary rows to task outcomes, escalation events, and plan-review events. Current packet is `hold_quality_unscored`: operational proxies favor enforce, but no factuality/accuracy scores are present for either arm. | `epyc-orchestrator` `a24a95a4`; `orchestration/reports/ri10_canary_decision_report_20260705T150054Z.{json,md}`; `uv run pytest tests/unit/test_ri10_canary_decision_report.py tests/unit/test_ri10_canary_sample_report.py -q` -> `14 passed` |
| RI-10 scored collection packet | Request planner now supports dataset-backed expected-answer rows, answer-key JSONL output, and self-leak filtering. Generated a balanced scored canary packet: `60` requests, `30` enforce / `30` shadow, `20` per canary role, answer key separated from payloads, and no nontrivial expected-answer leakage. | `epyc-orchestrator` `8455af52`; `orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.{json,payloads.jsonl,answer_key.jsonl}`; `uv run pytest tests/unit/test_ri10_canary_request_plan.py -q` -> `7 passed`; `ruff` passed |
| G12 role-tier recalibration | AA-Omniscience frontdoor/worker/architect evidence completed; deterministic 4-class scoring accepted for role-tier recalibration; measured tier multipliers landed in orchestrator. Mode/canary/enforce decisions remain RI-10+ gates. | [bulk-inference-campaign](bulk-inference-campaign.md) |
| Research intake | AA-Omniscience, STOP, Qwen-Scope SAE caveats, BaRP/Conductor context captured. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P6 after RI-10/11/12 status changes.
- Update [`bulk-inference-campaign.md`](bulk-inference-campaign.md) if AR-3/J-package traffic is used to collect RI samples.
- If a new injection-risk classifier is opened, add it here as RI-13 and cross-link DAR-6/J14.
- If a stack/model change changes role throughput or cost, update q-scorer baselines and note the dependency in the routing index.
