# What we're investigating now

A snapshot of in-flight work, written for outside readers and updated periodically. The live handoff queue is operationally noisy and not published here; the canonical version lives at [handoffs/active/](https://github.com/pestopoppa/epyc-root/tree/main/handoffs/active).

Last updated: 2026-05-26.

## The three threads worth following

Most of what's in the active queue is incremental — kernel tuning, retraining, characterization runs. Three threads stand out as having materially changed the system if they land.

**Learned routing controller production rollout.** The classifier has been wired end-to-end since 2026-05-21 at 98.7 % validation accuracy and is currently in shadow mode — every routing decision is computed both by the classifier and by the rule-based router, with the classifier's choice logged but unused. After enough shadow data accumulates we promote the classifier to canonical and demote the rule-based path to fallback. The expected lift is in the 4-8 pp range on out-of-distribution tasks, which is the regime where the classifier's confidence-abstain mechanism matters most. This is the routing-decisions story's natural sequel — see [Routing Intelligence](../topics/routing-intelligence.md) and [How a request flows](how-a-request-flows.md) for the substrate.

**Per-request reasoning budget.** A budget knob that caps internal-reasoning tokens (the `<think>...</think>` content) on a per-task basis. The model produces the budgeted reasoning, gets cut off, and is forced to commit to its final answer. The mechanism is straightforward; the harder part is wiring the budget into the routing layer's escalation triggers so the orchestrator can spend reasoning tokens generously on hard tasks and stingily on easy ones rather than applying a fixed cap. Drafting the API surface now.

**Within-role placement state machine.** A model's NUMA placement is currently decided once at server startup, and that's been fine because workloads have been roughly stationary. They're not stationary any more. We're scoping a dynamic placement layer that migrates work between quarters when one quarter overloads and another idles. The hard part is migrating KV cache (which is per-quarter); model weights are mmap'd so weight migration is free. Active design; nothing deployed.

## The rest of the active queue

Smaller and more focused items, grouped by where they live in the stack.

| Item | What it is | Status |
|---|---|---|
| **Retrain routing models** | The current classifier was trained against the pre-2026-05-06 stack (when `architect_coding` existed); needs retraining on post-consolidation episodes | Bottlenecked on data collection: ~2,000 needed, ~700 collected |
| **Cross-role BW-aware routing** | Routing penalty that accounts for current backend congestion (e.g. `worker_general` and `frontdoor` sharing NUMA quarter 0) | Scoping; small refinement, not structural |
| **N-way contention matrix** | Throughput cross-influence between every pair of models running concurrently; feeds a concurrency-aware admission control policy | Measurement campaign queued |
| **Q5_K / Q6_K / Q8_0 repack dispatcher** | Mainline llama.cpp has a NEON-only fast-path for these formats; x86 fallback is generic-scalar (60-70 % slower). Hand-tuned AVX-512BW versions in progress | Q5_K and Q6_K queued; Q8 8×8 shipped earlier (see [Quantization](../topics/quantization.md)) |
| **OpenMP sync primitive** | Replace condition-variable synchronization with user-space wait/wake on a per-team counter; estimated 1-3 % on bandwidth-saturated workloads, 5-8 % on dense small models | Identified in CPU optimization survey |
| **ColBERT reranker S5** | LateOn-Code drop-in for code retrieval channel; S1-S4 phases complete (ONNX, 180 ms encoding) | Code staged, not merged |
| **Reason-mxbai edge fallback** | Small reranker fallback for when the main ColBERT reranker is overloaded | Queued behind S5 |
| **Bulk inference campaign** | ~12,000 queries through the full stack to characterize end-to-end production-realistic latency and quality distributions | Running; feeds the next routing-classifier retrain |
| **AutoPilot KV-compression characterization** | AM (Attention Matching) is the production winner at 50× compression; checking whether EA (Expected Attention) wins on specific request types | Continuous; nightly Pareto-archive work |
| **Engram-Sentinel** | Whether n-gram embedding layers (LongCat-Flash-Lite style) lift frontdoor accuracy; LongCat ships a simpler arch than the original Engram paper described | Investigating |
| **Constrained-creativity planner Phase 2** | Phase 1 landed 2026-05-23 (stagnation-gated rich prompt + 3-axis rubric + persisted falsifier sidecar); Phase 2 wires it into AutoPilot's seed-generation step | Designing |
| **Link-rewriter follow-on** | Site has ~8 residual link warnings (stale anchor refs in the underlying chapter content); cosmetic but tractable | Low priority |
| **More narrative pages** | Future stories on SkillBank rollout, autopilot exogenous-restart resilience incident, the constrained-creativity planner. Hand-curated; no auto-generation planned | Queued |

The full long tail — items in `handoffs/blocked/` waiting on upstream dependencies, items in `handoffs/completed/` already landed, intake-triage entries marked `worth_investigating` but not active — lives on GitHub at [handoffs/active/](https://github.com/pestopoppa/epyc-root/tree/main/handoffs/active). It changes too fast for a static page.
