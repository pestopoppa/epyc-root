# Routing Intelligence: Factual-Risk Rollout

**Status**: COMPACTED 2026-05-28. Phases 0-5 implementation history moved to completed ledger. Live work is RI-10 canary decision, RI-11/RI-12 staged rollout, optional threshold work before any threshold change, and a gated injection-risk fork for DAR-6/J14.
**Priority**: HIGH for RI-10 decision; MEDIUM for injection-risk fork after J14.
**Blocked by**: current canary sample counts / AR-3 traffic; operator-approved inference/eval windows for rollout decisions.
**Completed ledger**: [`../completed/routing-intelligence-completed-through-2026-05-28.md`](../completed/routing-intelligence-completed-through-2026-05-28.md)
**Updated**: 2026-05-28

## Start Here

Do not implement the old Phase 4/5 sections from the completed ledger. They were superseded by RI-1 through RI-8 landing in March/April 2026. The next implementer should:

1. Pull current RI-10 canary data from logs before deciding anything; elapsed calendar time is not sufficient.
2. If high-risk sample count is still below target, keep the canary running and update AR-3/bulk-inference sources.
3. If sample count is adequate, compare enforce vs shadow on accuracy/factuality, escalation/review rate, latency, and cost.
4. Only then choose RI-11 expand, rollback to shadow, or threshold rework.

## Live Tasks

- [ ] **RI-10 — Shadow-to-enforce canary decision**: current canary is 25% enforce / 75% shadow on frontdoor. Decision requires:
  - >=50 high-risk samples or a documented reason to use a lower-powered decision;
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
| Research intake | AA-Omniscience, STOP, Qwen-Scope SAE caveats, BaRP/Conductor context captured. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |

## Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P6 after RI-10/11/12 status changes.
- Update [`bulk-inference-campaign.md`](bulk-inference-campaign.md) if AR-3/J-package traffic is used to collect RI samples.
- If a new injection-risk classifier is opened, add it here as RI-13 and cross-link DAR-6/J14.
- If a stack/model change changes role throughput or cost, update q-scorer baselines and note the dependency in the routing index.
