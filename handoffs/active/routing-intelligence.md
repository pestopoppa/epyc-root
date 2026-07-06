# Routing Intelligence: Factual-Risk Rollout

**Status**: COMPACTED 2026-05-28. Phases 0-5 implementation history moved to completed ledger. Live work is RI-10 canary decision, RI-11/RI-12 staged rollout, optional threshold work before any threshold change, and a gated injection-risk fork for DAR-6/J14. 2026-07-06 current decision packet `ri10_canary_decision_report_20260706T065654Z` attaches the scored factuality evidence from `ri10_canary_scored_summary_20260705T185001Z`: the scorer is ready (`60` rows, `30` enforce / `30` shadow, `0` missing), but enforce accuracy is tied with shadow (`0.10` vs `0.10`, delta `0.0`; token-F1 delta `+0.000531`). Operational proxies remain favorable to enforce in the live canary logs (`61` enforce / `80` shadow current rows; p95 latency ratio `0.211511`; mean estimated-cost ratio `0.532151`; operational error-rate delta `-0.0125`), but RI-10 now holds on `hold_quality_scored_no_lift`, not missing scoring. Keep RI-11 frozen unless a future scored packet shows an enforce factuality lift or the operator explicitly accepts a lower-evidence rollout decision. Treat the July 4 `20`-row / `1` enforce / `19` shadow state and the 2026-07-05 `hold_quality_unscored` packet as historical pre-scoring context. `epyc-orchestrator` removes process-RNG canary skew on the live chat path by deriving RI-10 enforce/shadow assignment from a stable task-id sample key while preserving the configured `canary_ratio`.
**Priority**: HIGH for RI-10 decision; MEDIUM for injection-risk fork after J14.
**Blocked by**: future scored factuality evidence showing enforce-arm lift, or an explicit operator-approved lower-evidence rollout decision.
**Completed ledger**: [`../completed/routing-intelligence-completed-through-2026-05-28.md`](../completed/routing-intelligence-completed-through-2026-05-28.md)
**Updated**: 2026-07-06

## Start Here

Do not implement the old Phase 4/5 sections from the completed ledger. They were superseded by RI-1 through RI-8 landing in March/April 2026. The next implementer should:

1. Pull current RI-10 canary data from logs before deciding anything; elapsed calendar time is not sufficient.
2. Confirm the current decision-ready sample still has enough arm-attributed rows in both enforce and shadow.
3. Use `scripts/analysis/ri10_canary_decision_report.py --scored-summary ...` to compare operational proxies with the attached scored factuality evidence. Current packet: `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`.
4. Keep RI-11 frozen unless a future scored packet shows enforce-arm factuality lift, or the operator explicitly accepts a lower-evidence rollout decision.

Current 2026-07-06 refresh: live Fable/DS-E1 reads report `ri10_telemetry_collection_blocker=decision_ready`, and the scored canary response report is attached to the rollout decision packet. `epyc-orchestrator` `adf010b4` extends `ri10_canary_decision_report.py` with `--scored-summary`, generates `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`, and records status `hold_quality_scored_no_lift`. The scored packet `ri10_canary_scored_summary_20260705T185001Z` is complete (`60/60` scored, no missing responses), but exact accuracy is tied (`3/30` enforce vs `3/30` shadow). The earlier 2026-07-04 reports (`ri10_canary_sample_report_20260704T095500Z.json`, `ri10_canary_sample_report_all_roles_20260704T005332Z.json`) and the 2026-07-05 `hold_quality_unscored` packet remain historical diagnostics only.

## Live Tasks

- [ ] **RI-10 — Shadow-to-enforce canary decision**: current canary is configured as 25% enforce / 75% shadow on `frontdoor`, `worker_general`, and `worker_vision`, and `7647b32e` exposes the chosen arm in routing progress metadata. The 2026-07-04 deterministic sampler fix makes future arm assignment stable per task id instead of process-RNG sampled, and the 2026-07-06 refresh shows telemetry depth and scored-response completeness are ready. Decision packet `20260706T065654Z` holds on `factuality_no_enforce_lift`; do not expand to RI-11 from favorable operational proxies alone. Decision requires:
  - controlled restart/window with `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true`; `ORCHESTRATOR_FACTUAL_RISK_MODE` is not the canary switch because it only accepts `off|shadow|enforce`;
  - >=50 arm-attributed high-risk samples or a documented reason to use a lower-powered decision; current refresh satisfies the depth gate with `31` enforce and `50` shadow high-risk rows;
  - no p95 latency regression >10%;
  - no cost regression >5% at equal factuality;
  - no unexplained escalation/review inflation >20%;
  - no 5xx/error cluster attributable to factual-risk scoring.
  - scored factuality/accuracy showing enforce-arm lift, or an explicit operator-approved lower-evidence decision. Current scored packet: `ri10_canary_scored_summary_20260705T185001Z` (`accuracy_delta=0.0`, token-F1 delta `+0.000531`).
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
| epyc-orchestrator | `scripts/analysis/ri10_canary_score_responses.py` | RI-10 scored factuality response report after quiet-window dispatch |
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
| RI-10 decision packet | Standalone decision report now joins current canary rows to task outcomes, escalation events, plan-review events, and optional scored-response evidence. Current packet is `hold_quality_scored_no_lift`: operational proxies favor enforce, but scored factuality has no exact-accuracy lift (`0.10` vs `0.10`). | `epyc-orchestrator` `adf010b4`; `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`; `uv run pytest -q tests/unit/test_ri10_canary_decision_report.py tests/unit/test_ri10_canary_score_responses.py tests/unit/test_ri10_canary_request_plan.py` -> `19 passed` |
| RI-10 scored collection packet | Request planner now supports dataset-backed expected-answer rows, answer-key JSONL output, and self-leak filtering. Generated a balanced scored canary packet: `60` requests, `30` enforce / `30` shadow, `20` per canary role, answer key separated from payloads, and no nontrivial expected-answer leakage. | `epyc-orchestrator` `8455af52`; `orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.{json,payloads.jsonl,answer_key.jsonl}`; `uv run pytest tests/unit/test_ri10_canary_request_plan.py -q` -> `7 passed`; `ruff` passed |
| RI-10 scored response scorer | Response scorer joins quiet-window response JSONL to the answer key, extracts common response shapes, scores deterministic answer equivalence, and summarizes accuracy/token-F1 by role and enforce/shadow arm. | `epyc-orchestrator` `92ab4de7`; `scripts/analysis/ri10_canary_score_responses.py`; `uv run pytest tests/unit/test_ri10_canary_score_responses.py tests/unit/test_ri10_canary_request_plan.py -q` -> `11 passed`; focused `ruff` and `py_compile` passed |
| RI-10 scored response result | Quiet-window scored response artifacts are complete: `60` rows, `60` scored, `0` missing; enforce and shadow exact accuracy tie at `3/30` each, with only a tiny token-F1 enforce delta. This closes the "unscored" blocker and replaces it with "no enforce factuality lift." | `orchestration/reports/ri10_canary_scored_summary_20260705T185001Z.{json,md}`; `orchestration/reports/ri10_canary_scored_rows_20260705T185001Z.jsonl` |
| G12 role-tier recalibration | AA-Omniscience frontdoor/worker/architect evidence completed; deterministic 4-class scoring accepted for role-tier recalibration; measured tier multipliers landed in orchestrator. Mode/canary/enforce decisions remain RI-10+ gates. | [bulk-inference-campaign](bulk-inference-campaign.md) |
| Research intake | AA-Omniscience, STOP, Qwen-Scope SAE caveats, BaRP/Conductor context captured. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P6 after RI-10/11/12 status changes.
- Update [`bulk-inference-campaign.md`](bulk-inference-campaign.md) if AR-3/J-package traffic is used to collect RI samples.
- If a new injection-risk classifier is opened, add it here as RI-13 and cross-link DAR-6/J14.
- If a stack/model change changes role throughput or cost, update q-scorer baselines and note the dependency in the routing index.
