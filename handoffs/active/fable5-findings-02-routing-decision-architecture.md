# Fable 5 findings 02 — Routing/serving decision architecture (facet 3)

**Date**: 2026-06-12. **Scope**: brief §4.3. Citations `file:line` under `/mnt/raid0/llm/epyc-orchestrator`. Live-process evidence from PID 1884727 (`/proc/<pid>/environ`) and `logs/progress/2026-06-11.jsonl` (1,765 requests tallied).

---

## 1. Verdict on hypothesis #3 — partially refuted, and the refutation is better news than the hypothesis

You suspect routing "has accreted past a unifying principle and would be simpler under one decision model." Half right:

- **The accretion is real but it is dark mass, not active complexity.** ~26–28K LoC of routing-adjacent code, ≥11 optimization paradigms, ~12 learned-artifact stores, ≈40 independent on/off levers. But the **live** decision stack is small: KNN-memory router (75% of decisions) + cheap-first pre-filter + rule fallbacks + escalation state machine + placement/contention safety layer. Three weight files don't exist (`routing_classifier_weights.npz` — missing since the 2026-05-25 memory reset while its flag says ON; `graph_router_weights.npz`; `bilinear_scorer_weights.npz`), the verifier head is unreachable (only fires inside the dead classifier path), and Trinity/difficulty/risk-abstain/swarm/proactive-delegation are shadow- or flag-off.
- **The unifying principle already exists in your code** — you don't need to invent it, you need to *enforce* it. At least seven components estimate the same value function `Q(prompt, action) ≈ P(success) − λ·cost`: the KNN Q-table and its selection score (`retriever.py:256`), the reward that trains it (`q_reward.py:88-106`), the MLP (distilled argmax of it), the GAT (cold-start prior of it), the bilinear scorer (factored form of it), the verifier head (its frontdoor column), the review/cheap-first gates (threshold reads of it). Your own DAR-4/5 handoffs already converge on "one bilinear Q(prompt, model) + preference vector ω."
- **A hierarchical-MDP redesign is the wrong prescription** for a system whose live decision count is this small and whose learner is this data-starved. The simpler design is: **one calibrated success-probability model + one explicit cost model + one scalarization ω**, with cheap-first as the cost-extreme arm of the same argmax, escalation as sequential re-evaluation of the same Q after a failure observation, and risk/difficulty bands as *features* of that model rather than parallel mode machines. Placement/contention stays a separate feasibility/safety layer (topology vetoes + measured pair matrix) — it is correctly not a learner.

## 2. What is actually broken (and invisible from inside)

### 2.1 Production runs on TEST feature defaults — verified
`features()` lazy-loads `get_features()` with `production=False` (`src/features.py:526-600`; no `production=True` call exists in API init). Flags whose registry says `default_prod=True` — `specialist_routing`, `plan_review`, `architect_delegation`, `parallel_execution`, `model_fallback`, `unified_streaming` — are **silently OFF live** (verified: none of their env vars in `/proc/1884727/environ`). Knock-ons: the keyword classifier constant-returns frontdoor (`keyword_matcher.py:403-408`), so heuristic *priors are frontdoor-degenerate and systematically pull learned routing toward frontdoor* (additive prior blend can flip rankings — your own test proves it); the failure-graph veto is inert (no graph is ever built, `memrl.py:399-415`). 77% of traffic lands on frontdoor. **Decision needed**: declare the intended production flag set explicitly in the launcher (one env block), and delete the `production=` parameter ambiguity. This is a one-day fix that changes the live architecture more than any redesign.

### 2.2 Flag mutations reach 1 of 6 workers — verified
`POST /config` calls `set_features()` on a per-process module global; uvicorn runs `--workers 6` (`orchestrator_stack.py:1210`); the kernel distributes requests across workers. So any runtime flag change — autopilot `structural_experiment`, operator hot-swap — applies to ~1/6 of subsequent requests, silently, until the next restart, with **no endpoint to read per-worker state**. Consequences: (a) every autopilot flag experiment ever run under multi-worker uvicorn measured a 5/6-unmutated system (see findings-01 §3.4); (b) live flag state is unknowable and possibly heterogeneous right now. **Fix shape**: flags move to a shared substrate (file/mmap/redis-style) read per-request or pushed to all workers; plus a `GET /config?worker=all` attestation endpoint. This is the routing-layer instance of the system-wide invariant you're missing (see findings-04): **running-state attestation** — the system must be able to *prove what is actually on*.

### 2.3 The learner is data-starved, and the learned layer is regrowing from zero
DAR-1 measured **96% uniform Q-values** — cost/similarity/degenerate-priors decide, not learning. The 2026-05-25 episodic reset wiped classifier/GAT/SkillBank training data simultaneously (retrain BLOCKED on ~500 fresh memories; refill rate ≈ 81 q-updates/day, and the routing-retrain handoff notes the real blocker is missing BGE embeddings). At ~1,765 req/day of which 400 are forced evals, **the de-facto primary user of this orchestrator is the autopilot/eval harness itself** — single-user human traffic cannot train a 6-way router in any reasonable time. This is the routing instance of the binding constraint from findings-01: decision-grade evidence throughput.

**2026-06-12 follow-up**: the BGE embedding blocker has been cleared by `repair_episodic_embeddings.py --repair` (diagnose-only HEALTHY: 275,960 FAISS vectors, 94.6% coverage). Current-data MLP retrain is staged (81.0% validation accuracy; >=0.8 threshold precision 94.4% over 61.6% coverage) and wiring preflight passes, but `/config/attest` still shows `routing_classifier=false` on all sampled workers. This does **not** unfreeze routing expansion; it only repairs the production-correctness path so a clean-window rollout decision can be made explicitly.

## 3. The recommended decision architecture

**Name**: a single **capability-conditioned cascade** — one calibrated `P(success | task-features, model-descriptor)` + explicit `cost(model, placement-state)` + preference vector ω, executed as optimal stopping (try the cheapest acceptable arm; escalate = re-evaluate posterior after observing a failure). **Theorem**: a cascade with a shared calibrated predictor is regret-optimal among role-selection policies when per-arm costs are known and success is observable — and every one of your live mechanisms (cheap-first, escalation chain, review gate, think-harder ROI) is already an ad-hoc special case of it.

What makes it *model-agnostic* (the North Star clause routing currently violates):
- **Model-capability descriptors** as the router's input, not role names. Today routing intelligence is keyed to the deployed stack and *dies on stack change* (the reset incident; your own memory: "benchmarks MUST index by model, never by role"). The research registry already holds per-model benchmark records — distill them into a versioned capability vector (suite-quality profile, t/s, ctx, modality, cost-class) per model. A model swap becomes a descriptor update; the predictor transfers; routing survives. This is the **single missing interface** between your benchmarking program (CPU indices, bulk-inference campaigns) and your serving system — months of measurement currently feed a YAML the router never reads.
- **One store, one update rule**: the episodic KNN remains the online memory; MLP/GAT/bilinear become *offline distillations of the same store with the same target* — or get deleted. Pick ONE distilled form (the bilinear `Q(task-feat, model-desc)` is the right shape because it factorizes over the descriptor and therefore generalizes to unseen models); drop the other two.
- **Calibration as a contract**: the predictor ships with an ECE bound and an abstain band (your risk-abstain gate, currently config-off, becomes the calibrated fallback rather than a parallel mechanism).

## 4. Deletion / freeze list (evidence-backed; "delete" = remove code, "freeze" = keep behind flag but strike from active docs)

| Item | Status proof | Action |
|---|---|---|
| `get_confidence_routing` / CONF protocol (`chat_routing.py:283-448`) | zero callers | **Delete** |
| `HybridRouter.route_3way` | zero callers | **Delete** |
| `dispatch_swarm_fanout` (474 LoC) | zero callers + flag default-off | **Delete or move to experiments/** |
| GraphRouter GAT stack (~1.2K LoC) | flag off + weights absent + would retrain from the same starved store | **Freeze**; revisit only after descriptor-based predictor exists |
| Bilinear scorer | weights absent, telemetry-only | **Re-purpose** as the ONE distilled predictor (§3) — else delete |
| SPO+/ε-greedy (DAR-3) | env unset → ε=0 | **Freeze** until the instrument can score exploration (findings-01 §2.3) |
| SkillBank routing | flag off, skills.db stale | **Freeze** |
| Verifier head | unreachable (dead classifier path) + trained pre-reset | **Delete weights, keep concept** as the calibrated-abstain band |
| Trinity tri-role shadow | always-on, never acted on, telemetry unreadable (INFO logs don't persist — agent could not find them on disk) | **Decide**: fix telemetry persistence or stop paying per-request cost |
| MLP classifier fast-path | flag ON, weights missing — *stated* architecture ≠ running architecture | **Un-flag until retrained**; the flag-says-on/weights-missing state is an attestation failure |

The honest accounting: **~3–4 of ≥11 paradigms influence production today.** Deleting/freezing the rest removes the gap between the described system and the running system — which is the same narrative-vs-fact disease findings-01 diagnoses in the autopilot, manifesting at the infra layer.

## 5. What routing should NOT become

- Do **not** unify placement into the decision model. Placement/contention is feasibility (topology vetoes, measured pair throughput); it has different failure semantics (safety) and is one of the few layers that works as designed (WP-2/cross-role-disjoint/reverse-migration verified live in env).
- Do **not** build the outer-coordinator/Conductor-class learned head now (your own handoff already says SCOPING/PARKING — correct). A 7B coordinator cannot be trained or even evaluated on 81 updates/day.
- Do **not** add more shadow modes. Three shadow layers (Trinity, difficulty, URE) already run per-request with no persisted telemetry pipeline that anyone reads — shadow without a ratification path is pure cost (and another attestation gap).

## 6. Decision gates

- **Fix-now (no gate)**: §2.1 explicit prod flag block; §2.2 shared flag substrate + attestation endpoint; delete the zero-caller trio.
- **Adopt descriptors** when: the capability-vector schema can be auto-compiled from the research registry for ≥80% of deployed models (it can — verify field coverage); gate **passes** when a simulated model-swap (replay routing decisions with one role's descriptor swapped) preserves learned-routing behavior without retraining.
- **Adopt the unified cascade** when: per-question eval vectors exist (findings-01) so router changes can be A/B-scored at all. Until then, freeze routing *learning* changes entirely — every learned-routing experiment before that date is unmeasurable, per findings-01 §1.
- **Smallest decisive observation**: run DAR-1's regret replay on one week of current traffic. If regret vs oracle-best-role is <5% of requests, routing is NOT your bottleneck and the entire facet should be down-prioritized below findings-01 — spend the attention there. (Prediction: it is <5%, because 77% frontdoor + cheap-first already covers a single-user workload.)
