# Routing, Autopilot & Stack — Active Backlog

**Purpose**: dispatch. Orchestrator, registry, stack lifecycle, autopilot, fleet coordination.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/routing-and-optimization-index-history-through-2026-08-10.md`](../archived/routing-and-optimization-index-history-through-2026-08-10.md).

**IDs are stable.** `RTG-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| RTG-01 | agent world env synthesis | [agent-world-env-synthesis.md](agent-world-env-synthesis.md) | Run the AW-6 48h bootstrap discovery (≥50 envs / ≥500 tools / ≥500 tasks) with incremental persistence | — |
| RTG-02 | autopilot continuous optimization | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) | AP-57 — journal the speed-axis reseed (option B), then AP-63(a) stamp the AP-1510 run manifest onto journal rows | — |
| RTG-03 | autopilot dashboard fidelity audit 2026 07 2 | [autopilot-dashboard-fidelity-audit-2026-07-22.md](autopilot-dashboard-fidelity-audit-2026-07-22.md) | C1 fix #2 Manifest writer intent-not-realized gap — writer lives in | — |
| RTG-04 | batched edit parallel apply | [batched-edit-parallel-apply.md](batched-edit-parallel-apply.md) | BEP-2 / J8 — Optional CPU latency A/B for the legacy patchset path: batch-edit mode vs interleaved Root LM loop on an edit workload | — |
| RTG-05 | bep dcp falsification harness | [bep-dcp-falsification-harness.md](bep-dcp-falsification-harness.md) | DCP-6 — At a host-quiet window, clear the feature-flag intent diffs, then run inference; record top-up rate, token overhead, success deltas | — |
| RTG-06 | capability registry and promotion | [capability-registry-and-promotion.md](capability-registry-and-promotion.md) | W3-b — LIVE shadowed role-restart attestation (BLOCKED: reload window owned by the inference session) | — |
| RTG-07 | contention model device and load axes rider | [contention-model-device-and-load-axes-rider.md](contention-model-device-and-load-axes-rider.md) | Q4 — decide whether the interference model needs INF-07's E5 NUMA×batch data first | INF-07 |
| RTG-08 | context folding progressive | [context-folding-progressive.md](context-folding-progressive.md) | CF-L5 — Run the L5 single-sentence compression check only if it answers a live question; verdict vs L3: rejected, role-limited, or tune | — |
| RTG-09 | decision aware routing | [decision-aware-routing.md](decision-aware-routing.md) | Add a wall-clock task_started→task_completed duration term to compute_reward as the speed axis; demote tokens/sec to secondary | — |
| RTG-10 | delegation context preassembly | [delegation-context-preassembly.md](delegation-context-preassembly.md) | DCP-10 — build the zero-decode ContextBench discovery scorer (wrap the shipped scorer first), then score lexical vs ColGREP arms | — |
| RTG-11 | dynamic stack concurrency | [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md) | K4 — Frontdoor `-ub 8192` is inert without `-b`: pass `-b 8192` or drop the flag from the launch config | — |
| RTG-13 | evidence plane event sourcing and narrative | [evidence-plane-event-sourcing-and-narrative.md](evidence-plane-event-sourcing-and-narrative.md) | W3 — after the first automatic segment snapshot (trial 1999→2000), demonstrate bounded startup cost on the next AutoPilot restart | — |
| RTG-14 | internal interaction lifecycle | [internal-interaction-lifecycle.md](internal-interaction-lifecycle.md) | P3-3 — run consult_gate_probe on T2/T3 hard slices: always-consult vs targeted gate on quality, tasks/hour, false skips | — |
| RTG-15 | learned routing controller | [learned-routing-controller.md](learned-routing-controller.md) | EPD-3-R5/R6/R8 — annotate the deprecated type:chat copy, fail-close the seed write loop, route builders via the shared one | — |
| RTG-16 | loops and dashboards audit 2026 07 05 | [loops-and-dashboards-audit-2026-07-05.md](loops-and-dashboards-audit-2026-07-05.md) | Fix real_suite_v1 discriminability before OP-1: root-cause the same-qid run instability, then de-saturate to MDE < 0.15 | — |
| RTG-17 | model capability descriptors | [model-capability-descriptors.md](model-capability-descriptors.md) | W5 — GATED tail: unified cascade (Phase 3) (2–3 weeks IF ever opened): one calibrated bilinear P(success \| task_features, model_descriptor… | — |
| RTG-18 | model stack change standardization audit | [model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md) | Keep as the per-change update checklist — run it at every model-stack change; never dispatch or flip its boxes | — |
| RTG-19 | model stack single source update pipeline | [model-stack-single-source-update-pipeline.md](model-stack-single-source-update-pipeline.md) | Keep as holder of the seven standing single-source constraints; no dispatchable task by design | — |
| RTG-20 | model stack update pipeline audit | [model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md) | Direct benchmark runtime enforcement only if promotion-gate coverage proves insufficient | — |
| RTG-21 | multi file coding completion capability | [multi-file-coding-completion-capability.md](multi-file-coding-completion-capability.md) | MF-VBS-1 — measure the verify-before-stop failure rate from existing BEP/REPL traces before building any gate | — |
| RTG-22 | non inference backlog | [non-inference-backlog.md](non-inference-backlog.md) | OBS-12 — audit the other .claude/skills for bare-python3 interpreter calls, starting with lint_wiki.py's PyYAML failure | — |
| RTG-23 | objective task rate goodput | [objective-task-rate-goodput.md](objective-task-rate-goodput.md) | W3e — merge sub/autopilot-safety, then add an objective policy whose TierSpec drops neg_cost (3-D ref point, era stamp, fence) | — |
| RTG-24 | orchestration robustness audit 2026 07 11 | [orchestration-robustness-audit-2026-07-11.md](orchestration-robustness-audit-2026-07-11.md) | P0.1 operator run/pause decision on autopilot candidate species | — |
| RTG-27 | prompt construction determinism | [prompt-construction-determinism.md](prompt-construction-determinism.md) | D3 — Run the P-BENCH canonical sampling-quality cert (`bench_canonical.sh`) in a clean window to certify items #1–3 | — |
| RTG-28 | reasoning effort levels | [reasoning-effort-levels.md](reasoning-effort-levels.md) | TB-1 — per-model budget curve on a truncation-inducing suite | — |
| RTG-29 | retrain routing models | [retrain-routing-models.md](retrain-routing-models.md) | Operator decision: run a --keep-enabled bracket to actually enable live routing | — |
| RTG-30 | routing intelligence | [routing-intelligence.md](routing-intelligence.md) | RI-10 — Decide the shadow→enforce canary; waits on scored enforce-arm factuality lift or an operator-approved lower-evidence call | — |
| RTG-32 | scaffold autopilot cost lever deployment | [scaffold-autopilot-cost-lever-deployment.md](scaffold-autopilot-cost-lever-deployment.md) | T0.1 — Verify AutoPilot is down (no autopilot.py, no journal activity) and get operator go-ahead for the capability-registry row | — |
| RTG-33 | searxng search backend | [searxng-search-backend.md](searxng-search-backend.md) | SX-5/SX-6 wait on AR-3; meanwhile relabel intake-365 (Firecrawl) superseded by intake-372, matching intake-364 | — |
| RTG-34 | session bus thin dispatcher | [session-bus-thin-dispatcher.md](session-bus-thin-dispatcher.md) | AIR-6 — deploy exact guarded source and require ordinary-work refusal; then resume live canaries | — |
| RTG-35 | shape keyed contention gating | [shape-keyed-contention-gating.md](shape-keyed-contention-gating.md) | Retire the stale q* nomenclature on half-sized instances, reviewed together with the contention_nway_restricted_count label | — |
| RTG-36 | stack change governance pipeline | [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md) | W4 — Migrate remaining stack-sensitive consumers to generated stack priors or explicit degraded fallbacks (per the surface manifest) | — |
| RTG-38 | standardized stack update pipeline finalizat | [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md) | W4 swap-CI — prove representative stack changes move generated descriptors, priors and gate execution together | — |
| RTG-39 | swarm dataset distillation | [../blocked/swarm-dataset-distillation.md](../blocked/swarm-dataset-distillation.md) | BLOCKED on strand Phase B — correct the premise first: distillation objective is ~2pp, the teacher-prompting change is ~38pp | EVL-45 |
| RTG-40 | tri role coordinator architecture | [tri-role-coordinator-architecture.md](tri-role-coordinator-architecture.md) | TR-4.1 — Compose role with model selection in routing.py; frozen until the DAR-regret and per-question-vector gates reopen routing | — |
| RTG-41 | unified trace memory service | [unified-trace-memory-service.md](unified-trace-memory-service.md) | UTM-P1 — add harness identity, seed and turn-ordinal pairing keys to the trace event schema (src/trace/store.py) | — |
| RTG-42 | within role placement state machine | [within-role-placement-state-machine.md](within-role-placement-state-machine.md) | WP-6/WP-7 ratification: inference-gated, awaiting operator. WP-9 superseded by burst_prefer_split; WP-10 fixed at W1 cutover (OP-45) | — |
| RTG-43 | wp12 fleet layer design | [wp12-fleet-layer-design.md](wp12-fleet-layer-design.md) | Post-soak §5 cleanup — retire the legacy per-role build path; waits on the operator retiring the ORCHESTRATOR_FLEET_LAYER rollback | — |
| RTG-45 | x mas text routing | [x-mas-text-routing.md](x-mas-text-routing.md) | Monitor post-enable X-MAS telemetry for domain/latency regressions or guard bypasses; rollback is `xmas_routing.mode: off` + API reload | — |
| RTG-46 | handoff index and backlog graph | [handoff-index-and-backlog-graph.md](handoff-index-and-backlog-graph.md) | Human visual verdict on the :8100 graph lattice layout (4cd106c2 deployed); OP-9 hub_supervisor relaunch pending | — |
| RTG-47 | dashboard architecture restructure | [dashboard-architecture-restructure.md](dashboard-architecture-restructure.md) | Tap writer: record terminal `n_prompt_tokens` per request so completed cards carry true prompt tokens; Phase 1b awaits operator parity | — |
| RTG-48 | coordinator role failure modes | [coordinator-role-failure-modes-and-refactor.md](coordinator-role-failure-modes-and-refactor.md) | Auditor: audit the Mech column — a MECH claim holds only if the mechanism would have REFUSED that specific failure; mutation-test it | RTG-34 |
| RTG-49 | fleet fanout measurement | [fleet-fanout-measurement.md](fleet-fanout-measurement.md) | FM-2 Stage 1 — add adamast base_url passthrough + Claude/Codex JSONL normalizer, run adamast judge on a stratified trace sample | RTG-34, RTG-48 |
| RTG-50 | decomposition to batch mapping | [decomposition-to-batch-mapping.md](decomposition-to-batch-mapping.md) | DB-1 — establish whether a task decomposition can be expressed as np-batch slots across CPU and GPU instances | RTG-49 |
| RTG-51 | wrap up division of labor policy | [wrap-up-division-of-labor-policy.md](wrap-up-division-of-labor-policy.md) | Wire compute blocker/window events and the receipt-cut heavy-wrap executor; then shadow the complete lifecycle | RTG-34, RTG-48 |
| RTG-52 | loop owned fleet implementation | [loop-owned-fleet-implementation.md](loop-owned-fleet-implementation.md) | P4-1 — adjudicate the 7-day role-shrink gate; then P5-1 hook-surface trust-boundary analysis and P5-2 NL-only fixture | RTG-34, RTG-48 |
| RTG-54 | qwen chat template evaluation | [qwen-chat-template-evaluation.md](qwen-chat-template-evaluation.md) | CT-11 — re-decide the pilot template adoption once the three roles serve real traffic; run the CT-10 cruxeval re-check alongside | — |
| RTG-55 | promptforge mutation safety | [promptforge-mutation-safety-contract.md](promptforge-mutation-safety-contract.md) | MHS-3c — purge the pinned multitier_v10 episodic store and ratify its re-pin (operator choice pending); then MHS-12 | RTG-02 |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
