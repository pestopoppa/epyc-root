# Routing, Autopilot & Stack — Active Backlog

**Purpose**: dispatch. Orchestrator, registry, stack lifecycle, autopilot, fleet coordination.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/routing-and-optimization-index-history-through-2026-08-10.md`](../archived/routing-and-optimization-index-history-through-2026-08-10.md).

**IDs are stable.** `RTG-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| RTG-02 | autopilot continuous optimization | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) | Prospectively capture menus, model/decoding identity, holdout and paired continuations; rerun sealed replay | — |
| RTG-03 | autopilot dashboard fidelity audit 2026 07 2 | [autopilot-dashboard-fidelity-audit-2026-07-22.md](autopilot-dashboard-fidelity-audit-2026-07-22.md) | On next live lineup, verify C1 #2 against its producer; route C1 #3 to stack owner | — |
| RTG-04 | batched edit parallel apply | [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md) | BEP-2 / J8 — Optional CPU latency A/B for the legacy patchset path: batch-edit mode vs interleaved Root LM loop on an edit workload | — |
| RTG-05 | bep dcp falsification harness | [bep-dcp-falsification-harness.md](bep-dcp-falsification-harness.md) | DCP-6 — At a host-quiet window, clear the feature-flag intent diffs, then run inference; record top-up rate, token overhead, success deltas | — |
| RTG-07 | contention model device and load axes rider | [contention-model-device-and-load-axes-rider.md](contention-model-device-and-load-axes-rider.md) | Parameterize Artifact 2 capacity/VRAM fit, then Artifact 3 interference cost; retain E5 as final calibration dependency | INF-07 |
| RTG-08 | context folding progressive | [context-and-token-economy.md](context-and-token-economy.md) | CF-L5 — Run the L5 single-sentence compression check only if it answers a live question; verdict vs L3: rejected, role-limited, or tune | — |
| RTG-09 | decision aware routing | [decision-aware-routing.md](decision-aware-routing.md) | Hold until autopilot trains on the swapped stack AND UFH-13 re-opens (2026-09-29); then unfreeze DAR-LAT, DAR-SPLIT-1 first | — |
| RTG-11 | dynamic stack concurrency | [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md) | G4 — measure the post-restore prompt-reuse rate on the hybrid frontdoor (slot save/restore, upstream #25913); K4a master-registry drift | — |
| RTG-13 | evidence plane event sourcing and narrative | [evidence-plane-event-sourcing-and-narrative.md](evidence-plane-event-sourcing-and-narrative.md) | W3 — after the first automatic segment snapshot (trial 1999→2000), demonstrate bounded startup cost on the next AutoPilot restart | — |
| RTG-14 | internal interaction lifecycle | [internal-interaction-lifecycle.md](internal-interaction-lifecycle.md) | P3-3 — run consult_gate_probe on T2/T3 hard slices: always-consult vs targeted gate on quality, tasks/hour, false skips | — |
| RTG-15 | learned routing controller | [learned-routing-controller.md](learned-routing-controller.md) | EP-5 — re-run the outcome-label probe on rows updated after 24b43990 (or after the EPD-1b backfill); then EPD-3 | — |
| RTG-16 | loops and dashboards audit 2026 07 05 | [loops-and-dashboards-audit-2026-07-05.md](loops-and-dashboards-audit-2026-07-05.md) | De-saturate real_suite_v1 to MDE < 0.15 before OP-1 (instability root-caused 2026-09-24; needs a larger eval run — inference) | — |
| RTG-17 | model capability descriptors | [model-capability-descriptors.md](model-capability-descriptors.md) | W5 — GATED tail: unified cascade (Phase 3) (2–3 weeks IF ever opened): one calibrated bilinear P(success \| task_features, model_descriptor… | — |
| RTG-22 | non inference backlog | [engineering-hygiene-backlog.md](engineering-hygiene-backlog.md) | Land LOOP-10..12, disk LOOP-21..25 and LOOP-26/27 (no blocking Qs unattended, filing alarm); review NIB2-98; prove NIB2-102.b | — |
| RTG-23 | objective task rate goodput | [objective-task-rate-goodput.md](objective-task-rate-goodput.md) | W3e — merge sub/autopilot-safety, then add an objective policy whose TierSpec drops neg_cost (3-D ref point, era stamp, fence) | — |
| RTG-24 | orchestration robustness audit 2026 07 11 | [orchestration-robustness-audit-2026-07-11.md](orchestration-robustness-audit-2026-07-11.md) | P0.1 operator run/pause decision on autopilot candidate species | — |
| RTG-29 | retrain routing models | [retrain-routing-models.md](retrain-routing-models.md) | Operator decision: run a --keep-enabled bracket to actually enable live routing | — |
| RTG-30 | routing intelligence | [routing-intelligence.md](routing-intelligence.md) | RI-18c: verify review_gate/review_verdict null on a COMPLETED live /chat in a DS41 open window; RI-19 use_memrl off; RI-24 | UFH-14 |
| RTG-32 | scaffold autopilot cost lever deployment | [scaffold-autopilot-cost-lever-deployment.md](scaffold-autopilot-cost-lever-deployment.md) | T0.1 — Verify AutoPilot is down (no autopilot.py, no journal activity) and get operator go-ahead for the capability-registry row | — |
| RTG-34 | session bus thin dispatcher | [session-bus-thin-dispatcher.md](session-bus-thin-dispatcher.md) | AIR-6 — deploy exact guarded source and require ordinary-work refusal; then resume live canaries | — |
| RTG-35 | shape keyed contention gating | [shape-keyed-contention-gating.md](shape-keyed-contention-gating.md) | REGION-SIBLING-1: merge fix/region-lock-smt-siblings-ec 4ae008a8 after operator approval (OP-77); then the q* nomenclature review | — |
| RTG-36 | stack change governance pipeline | [stack-lifecycle-program.md](stack-lifecycle-program.md) | OP-72 sign STACKCHG-HYGIENE, then SCG-PRIORS-WARM-b + DRAFT-SEL-2b; SCG-FASTPATH; SCG-TEST-ORDER | — |
| RTG-40 | tri role coordinator architecture | [tri-role-coordinator-architecture.md](tri-role-coordinator-architecture.md) | TR-4.1 — Compose role with model selection in routing.py; frozen until the DAR-regret and per-question-vector gates reopen routing | — |
| RTG-41 | unified trace memory service | [unified-trace-memory-service.md](unified-trace-memory-service.md) | UTM-LB2.2 ingest projector events; UTM-B1 catalog-growth; UTM-B2 pairing | — |
| RTG-42 | within role placement state machine | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) | WP-8 — teach compute_max_safe_concurrency the largest-dimension rule for quarters-only eval fan-out (WP-6/WP-7 await the operator) | — |
| RTG-45 | x mas text routing | [x-mas-text-routing.md](x-mas-text-routing.md) | Monitor post-enable X-MAS telemetry for domain/latency regressions or guard bypasses; rollback is `xmas_routing.mode: off` + API reload | — |
| RTG-46 | handoff index and backlog graph | [handoff-index-and-backlog-graph.md](handoff-index-and-backlog-graph.md) | Human visual verdict on the :8100 graph lattice layout (4cd106c2 deployed); OP-9 hub_supervisor relaunch pending | — |
| RTG-47 | dashboard architecture restructure | [dashboard-architecture-restructure.md](dashboard-architecture-restructure.md) | Re-eyeball the tap's live ACTIVE/streaming token counters under real traffic; Phase 1b awaits operator parity | — |
| RTG-48 | coordinator role failure modes | [coordinator-role-failure-modes-and-refactor.md](coordinator-role-failure-modes-and-refactor.md) | R-7 — Assign a successor to retired namespace owner mainD; then reconcile the C49 references | RTG-34 |
| RTG-49 | fleet fanout measurement | [fleet-fanout-measurement.md](fleet-fanout-measurement.md) | FM-7 journal delegation accounting + FM-8 subagent types/dispatch hook (parallel), then FM-9 doctrine diff; FM-2 Stage 1 after | RTG-34, RTG-48 |
| RTG-51 | wrap up division of labor policy | [wrap-up-division-of-labor-policy.md](wrap-up-division-of-labor-policy.md) | Reconcile the Phase-5 instruction migration matrix and prepare protected policy signoff; retain the real Auditor canary | RTG-34, RTG-48 |
| RTG-52 | loop owned fleet implementation | [loop-owned-fleet-implementation.md](loop-owned-fleet-implementation.md) | P4-1 — adjudicate the 7-day role-shrink gate; then P5-1 hook-surface trust-boundary analysis and P5-2 NL-only fixture | RTG-34, RTG-48 |
| RTG-55 | promptforge mutation safety | [promptforge-mutation-safety-contract.md](promptforge-mutation-safety-contract.md) | MHS-3d — operator runs the v10 episodic re-pin RATIFY (run_v10_episodic_repin_ratify_20260917.sh); then MHS-12 | RTG-02 |
| RTG-56 | typed decision plane | [typed-decision-plane.md](typed-decision-plane.md) | Run fresh three-arm shadow at the inference owner’s boundary; retain inference gates | — |
| RTG-57 | kv unified stack rollout | [kv-unified-stack-rollout.md](kv-unified-stack-rollout.md) | Follow the 2026-11-02 execution contract: reconcile capacity evidence and prepare remaining candidate gates; preserve HPR exposure | RTG-36, INF-79 |
| RTG-58 | kv prefix fork and paged attention | [kv-prefix-fork-and-paged-attention.md](kv-prefix-fork-and-paged-attention.md) | Qualify P1 candidate correctness; complete chunk-KV integration and repair the KPF-64 family cohort | RTG-57, EVL-14, INF-65 |
| RTG-62 | churn pipeline | [churn-pipeline.md](churn-pipeline.md) | SA-1 (merge into sticky-slot change: ready-row admission, start cooldown) then SA-2/SA-3/JEV-3 | — |
| RTG-63 | backlog refactor 2026-11 | [backlog-refactor-2026-11.md](backlog-refactor-2026-11.md) | BRF-T1-0: reconcile the fold plan against origin/main and commit the ordered route-1a fold list | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
