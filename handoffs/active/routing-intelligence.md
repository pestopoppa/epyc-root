# Routing Intelligence: Factual-Risk Rollout

**Status**: COMPACTED 2026-05-28. Phases 0-5 implementation history moved to completed ledger. Live work is RI-10 canary decision, RI-11/RI-12 staged rollout, optional threshold work before any threshold change, and a gated injection-risk fork for DAR-6/J14. 2026-07-03 audit finds raw high-risk sample volume is still sufficient (`463` since canary start; `285` frontdoor), but only `19` rows have observable canary arms (`1` enforce / `18` shadow), with `444` non-evaluable rows and `407` `not_enforced:risk_control_disabled` rows. RI-10 remains blocked on decision-grade arm-attributed evidence, not raw sample count.
**Priority**: HIGH for RI-10 decision; MEDIUM for injection-risk fork after J14.
**Blocked by**: decision-grade enforce/shadow canary-arm telemetry under `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true` / AR-3 traffic; operator-approved inference/eval windows for rollout decisions.
**Completed ledger**: [`../completed/routing-intelligence-completed-through-2026-05-28.md`](../completed/routing-intelligence-completed-through-2026-05-28.md)
**Updated**: 2026-07-03

## Start Here

Do not implement the old Phase 4/5 sections from the completed ledger. They were superseded by RI-1 through RI-8 landing in March/April 2026. The next implementer should:

1. Pull current RI-10 canary data from logs before deciding anything; elapsed calendar time is not sufficient.
2. If raw high-risk sample count regresses below target, keep the canary running and update AR-3/bulk-inference sources.
3. If raw sample count is adequate, confirm the logs expose enough arm-attributed rows in both enforce and shadow before comparing accuracy/factuality, escalation/review rate, latency, and cost.
4. Only then choose RI-11 expand, rollback to shadow, or threshold rework.

Current 2026-07-03 report: `orchestration/reports/ri10_canary_sample_report_20260703.json` counts `463` high-risk routing decisions since the 2026-04-06 canary start (`285` frontdoor), but only `19` high-risk rows have observable enforce/shadow arms (`1` enforce / `18` shadow). The hardened report now requires both `>=50` arm-attributed high-risk rows and `>=10` rows in each observable arm before `canary_decision_ready=true`; this report is therefore not a valid RI-10 enforce-vs-shadow decision sample. The earlier missing-arm repair remains `7647b32e`; the 2026-07-03 follow-up hardens report semantics so aggregate DS-E1/Fable5 gates no longer treat raw high-risk volume as decision-grade canary evidence.

## Live Tasks

- [ ] **RI-10 — Shadow-to-enforce canary decision**: current canary is configured as 25% enforce / 75% shadow on frontdoor, and `7647b32e` now exposes the chosen arm in routing progress metadata. Decision requires:
  - controlled restart/window with `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true`; `ORCHESTRATOR_FACTUAL_RISK_MODE` is not the canary switch because it only accepts `off|shadow|enforce`;
  - >=50 arm-attributed high-risk samples or a documented reason to use a lower-powered decision; current raw count is sufficient, but only `19` rows are arm-attributed and the enforce/shadow balance is `1` / `18`;
  - no p95 latency regression >10%;
  - no cost regression >5% at equal factuality;
  - no unexplained escalation/review inflation >20%;
  - no 5xx/error cluster attributable to factual-risk scoring.
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
| RI-10 report/gate semantics hardening | `ri10_canary_sample_report.py` now distinguishes raw high-risk volume from decision-grade arm-attributed telemetry. DS-E1/Fable5 aggregate gates stay blocked when only raw count is ready. The 2026-07-03 report has `463` raw high-risk rows, `19` arm-attributed rows, and no decision-grade enforce/shadow balance. | `orchestration/reports/ri10_canary_sample_report_20260703.json`; `orchestration/reports/fable5_gate_20260703T104437Z.md` |
| G12 role-tier recalibration | AA-Omniscience frontdoor/worker/architect evidence completed; deterministic 4-class scoring accepted for role-tier recalibration; measured tier multipliers landed in orchestrator. Mode/canary/enforce decisions remain RI-10+ gates. | [bulk-inference-campaign](bulk-inference-campaign.md) |
| Research intake | AA-Omniscience, STOP, Qwen-Scope SAE caveats, BaRP/Conductor context captured. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P6 after RI-10/11/12 status changes.
- Update [`bulk-inference-campaign.md`](bulk-inference-campaign.md) if AR-3/J-package traffic is used to collect RI samples.
- If a new injection-risk classifier is opened, add it here as RI-13 and cross-link DAR-6/J14.
- If a stack/model change changes role throughput or cost, update q-scorer baselines and note the dependency in the routing index.
