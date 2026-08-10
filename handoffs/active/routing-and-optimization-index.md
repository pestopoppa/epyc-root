# Routing, Autopilot & Stack — Active Backlog

**Purpose**: dispatch. Orchestrator, registry, stack lifecycle, autopilot, fleet coordination.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/routing-and-optimization-index-history-through-2026-08-10.md`](../archived/routing-and-optimization-index-history-through-2026-08-10.md).

**IDs are stable.** `RTG-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| RTG-01 | agent world env synthesis | [agent-world-env-synthesis.md](agent-world-env-synthesis.md) | Run the AW-6 48h bootstrap discovery (≥50 envs / ≥500 tools / ≥500 tasks) with incremental persistence | — |
| RTG-02 | autopilot continuous optimization | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) | AP-26: evaluate dspy.RLM for long-horizon autopilot analysis where metadata-first exploration avoids context overflow | — |
| RTG-03 | autopilot dashboard fidelity audit 2026 07 2 | [autopilot-dashboard-fidelity-audit-2026-07-22.md](autopilot-dashboard-fidelity-audit-2026-07-22.md) | C1 fix #2 Manifest writer intent-not-realized gap — writer lives in | — |
| RTG-04 | batched edit parallel apply | [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md) | BEP-2 / J8 — CPU latency A/B for the legacy structured patchset path. Head-to-head bench: batch-edit mode vs interleaved Root LM loop on a… | — |
| RTG-05 | bep dcp falsification harness | [bep-dcp-falsification-harness.md](bep-dcp-falsification-harness.md) | DCP-6 deploy attestation + inference gate: launch-code provenance is satisfied (server_launch_git_sha=eeb8cce, ancestor of 2e2e0d3 and 756c… | — |
| RTG-06 | capability registry and promotion | [capability-registry-and-promotion.md](capability-registry-and-promotion.md) | W3 — build config_applicator.restart_role() for safe role restarts (~2-3d, pauses autopilot) | — |
| RTG-07 | contention model device and load axes rider | [contention-model-device-and-load-axes-rider.md](contention-model-device-and-load-axes-rider.md) | Q4 — decide whether the interference model needs INF-07's E5 NUMA×batch data first | INF-07 |
| RTG-08 | context folding progressive | [context-folding-progressive.md](context-folding-progressive.md) | CF-L5 maximum-compression validation: run the L5 single-sentence-per-segment compression check only if it answers a current production ques… | — |
| RTG-09 | decision aware routing | [decision-aware-routing.md](decision-aware-routing.md) | Implement the SPO+ (Smart Predict-then-Optimize) loss | — |
| RTG-10 | delegation context preassembly | [delegation-context-preassembly.md](delegation-context-preassembly.md) | DCP-6 — Eval. Measure on a delegation-heavy workload: prefill tokens, end-to-end latency, top-up count, bundle-build latency, downstream an… | — |
| RTG-11 | dynamic stack concurrency | [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md) | DS-6-live — QuarterScheduler revalidation gate: parked. Only implement dynamic quarter reassignment if future DS-E1-equivalent evidence sho… | — |
| RTG-12 | esc8 stack restart landmine audit 2026 07 22 | [esc8-stack-restart-landmine-audit-2026-07-22.md](esc8-stack-restart-landmine-audit-2026-07-22.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-13 | evidence plane event sourcing and narrative | [evidence-plane-event-sourcing-and-narrative.md](evidence-plane-event-sourcing-and-narrative.md) | W3 — rotation snapshots (impl 3.2, ~1 day): journal segments per 1000 trials chained with a snapshot row (full reconstructed view + policy… | — |
| RTG-14 | internal interaction lifecycle | [internal-interaction-lifecycle.md](internal-interaction-lifecycle.md) | P3-3. Shadow/optimization calibration: use consult_gate_probe on T2/T3 hard workflow slices to compare always-consult vs targeted-gate beha… | — |
| RTG-15 | learned routing controller | [learned-routing-controller.md](learned-routing-controller.md) | EP-5 — re-run the probe only after the outcome-label defects are fixed | — |
| RTG-16 | loops and dashboards audit 2026 07 05 | [loops-and-dashboards-audit-2026-07-05.md](loops-and-dashboards-audit-2026-07-05.md) | Fix real_suite_v1 discriminability BEFORE certifying OP-1 (forward work from the audit above) — root-cause the run-instability first (two r… | — |
| RTG-17 | model capability descriptors | [model-capability-descriptors.md](model-capability-descriptors.md) | W5 — GATED tail: unified cascade (Phase 3) (2–3 weeks IF ever opened): one calibrated bilinear P(success \| task_features, model_descriptor… | — |
| RTG-18 | model stack change standardization audit | [model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-19 | model stack single source update pipeline | [model-stack-single-source-update-pipeline.md](model-stack-single-source-update-pipeline.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-20 | model stack update pipeline audit | [model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md) | Direct benchmark runtime enforcement only if promotion-gate coverage proves insufficient | — |
| RTG-21 | multi file coding completion capability | [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md) | If a coder-role A/B is authorized, use bartowski's Q8_0 (34.38 GB) for a quant-matched run against the incumbent 35.21 GB frontdoor. This a… | — |
| RTG-22 | non inference backlog | [non-inference-backlog.md](non-inference-backlog.md) | NIB2-18: DS-6 QuarterScheduler revalidation gate — dynamic-stack-concurrency.md(dynamic-stack-concurrency.md) DS-6-live. Do not treat as co… | — |
| RTG-23 | objective task rate goodput | [objective-task-rate-goodput.md](objective-task-rate-goodput.md) | W3d — the 2026-06-13 hold conditions were superseded, not satisfied; close them out | — |
| RTG-24 | orchestration robustness audit 2026 07 11 | [orchestration-robustness-audit-2026-07-11.md](orchestration-robustness-audit-2026-07-11.md) | P0.1 operator run/pause decision on autopilot candidate species | — |
| RTG-25 | orchestrator nps4 48x4 notes | [orchestrator-nps4-48x4-notes.md](orchestrator-nps4-48x4-notes.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-26 | outer coordinator learned head | [outer-coordinator-learned-head.md](outer-coordinator-learned-head.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-27 | prompt construction determinism | [prompt-construction-determinism.md](prompt-construction-determinism.md) | D3 — manual canonical bench (sampling quality cert) (clean window; certifies #1–3). Greedy→sampled(0.1–0.3)+seed shifts output behavior. Ce… | — |
| RTG-28 | reasoning effort levels | [reasoning-effort-levels.md](reasoning-effort-levels.md) | TB-1 — per-model budget curve on a truncation-inducing suite | — |
| RTG-29 | retrain routing models | [retrain-routing-models.md](retrain-routing-models.md) | Operator decision: run a --keep-enabled bracket to actually enable live routing | — |
| RTG-30 | routing intelligence | [routing-intelligence.md](routing-intelligence.md) | RI-10 — Shadow-to-enforce canary decision: current canary is configured as 25% enforce / 75% shadow on frontdoor, worker_general, and worke… | — |
| RTG-31 | routing truth restoration | [routing-truth-restoration.md](routing-truth-restoration.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-32 | scaffold autopilot cost lever deployment | [scaffold-autopilot-cost-lever-deployment.md](scaffold-autopilot-cost-lever-deployment.md) | T0.1 — Coordinate with the live autopilot agent. Confirm the daemon is idle/handed-back before any scripts/autopilot/ or registry edit. Get… | — |
| RTG-33 | searxng search backend | [searxng-search-backend.md](searxng-search-backend.md) | SX-5: Load test — Folded into AR-3 Package D. Web_research sentinel suite (50q) provides realistic load validation. Post-AR-3: analyze engi… | — |
| RTG-34 | session bus thin dispatcher | [session-bus-thin-dispatcher.md](session-bus-thin-dispatcher.md) | R1a — the end-to-end bench claim never fired; wiring exists but is inference-gated | — |
| RTG-35 | shape keyed contention gating | [shape-keyed-contention-gating.md](shape-keyed-contention-gating.md) | Echo GateDecision into /chat response metadata (admitted/waited_s/decision/topology_idx) | — |
| RTG-36 | stack change governance pipeline | [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md) | W4 - Consumer migration: continue migrating remaining stack-sensitive consumers to generated stack priors or explicit degraded fallbacks. U… | — |
| RTG-37 | stack lineup dossier 2026 07 23 | [stack-lineup-dossier-2026-07-23.md](stack-lineup-dossier-2026-07-23.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-38 | standardized stack update pipeline finalizat | [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md) | SS-BENCH-GATE — a stack reload must check for a running CPU bench, not just autopilot. | — |
| RTG-39 | swarm dataset distillation | [../blocked/swarm-dataset-distillation.md](../blocked/swarm-dataset-distillation.md) | BLOCKED on strand Phase B — correct the premise first: distillation objective is ~2pp, the teacher-prompting change is ~38pp | — |
| RTG-40 | tri role coordinator architecture | [tri-role-coordinator-architecture.md](tri-role-coordinator-architecture.md) | TR-4.1 In routing.py, compose role with model selection: per-role model-affinity table OR independent role+model softmax (per TR-1.3 decisi… | — |
| RTG-41 | unified trace memory service | [unified-trace-memory-service.md](unified-trace-memory-service.md) | T7 (optional): Hermes session ingest — Walk ~/.hermes/sessions/.json if present, normalize into events. Gated on whether Hermes goes into p… | — |
| RTG-42 | within role placement state machine | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) | WP-6 / WP-7 full ratification - inference-gated, awaiting operator approval + measurement | — |
| RTG-43 | wp12 fleet layer design | [wp12-fleet-layer-design.md](wp12-fleet-layer-design.md) | Post-soak §5 cleanup (code + tests as ONE change): retire the legacy per-role build path — ServerURLsConfig URL ownership, Fix-A delegation… | — |
| RTG-44 | wp9 wp10 lineup event prep | [wp9-wp10-lineup-event-prep.md](wp9-wp10-lineup-event-prep.md) | _no open dispatchable task — verify complete or file the next step_ | — |
| RTG-45 | x mas text routing | [x-mas-text-routing.md](x-mas-text-routing.md) | Monitor post-enable live telemetry for unexpected domain regressions, latency regressions, or guard bypasses; rollback is xmas_routing.mode… | — |
| RTG-46 | handoff index and backlog graph | [handoff-index-and-backlog-graph.md](handoff-index-and-backlog-graph.md) | Decide whether .index-state.json / .index-graph.json are git-ignored — timeline artifact already is | — |
| RTG-47 | dashboard architecture restructure | [dashboard-architecture-restructure.md](dashboard-architecture-restructure.md) | Land fix-10 retention overlay; re-eyeball live ↑/↓ under real load; run old+new in parallel toward the Phase 1b call | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
