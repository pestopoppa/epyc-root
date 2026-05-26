# What we're investigating now

A curated snapshot of the active work queue, written for outside readers. Hand-edited (not auto-synced) because the full handoff queue contains a lot of operational noise that would confuse a cold reader. This page is updated periodically; for the live, complete queue see the project's [handoffs/active/](https://github.com/pestopoppa/epyc-root/tree/main/handoffs/active) directory on GitHub.

Last updated: 2026-05-26.

## Routing & decision-making

**Learned routing controller — production rollout (Phase 2).** The 98.7 % validation-accuracy classifier is wired end-to-end as of 2026-05-21. It's currently running in *shadow mode* — every routing decision is computed by both the classifier and the fallback rule-based router; the classifier's choice is logged but the rule-based router's choice is used. After 24–48 hours of shadow data we promote it to canonical and demote the rule-based router to fallback. The lift we expect from a real promotion is in the 4–8 pp success-rate range on out-of-distribution tasks; we'll know in a few days.

**Retrain routing models on the latest stack.** The classifier was trained against the pre-2026-05-06 stack (when `architect_coding` was a separate role). We need to retrain on post-consolidation data so the classifier doesn't keep proposing a route that no longer exists. Currently bottlenecked on collecting enough post-consolidation episodes to make the retrain meaningful — about 2,000 needed, ~700 collected as of writing.

**Cross-role bandwidth-aware routing.** Currently the router treats all roles as equally bandwidth-priced. In reality, routing to `worker_general` while frontdoor is busy isn't free — the worker and frontdoor share NUMA quarter 0, so they fight for ~115 GB/s. We're scoping a routing penalty that accounts for current backend congestion. This is a small refinement, not a structural change.

## Model serving & runtime

**Per-request reasoning budget.** A budget knob that lets the orchestrator cap the number of internal-reasoning tokens (the `<think>...</think>` content) a model can spend on a single task. The model produces the budgeted reasoning, gets cut off, and is forced to produce its final answer. Useful both for cost control and for forcing concise outputs on tasks where the model would otherwise meander. Drafting the API surface now; full integration with the routing layer's escalation triggers is the harder part.

**N-way contention matrix.** A measurement we don't yet have: what's the throughput cross-influence between every pair of models when they run concurrently on the same chip? We have pairwise data for a few combinations but not a full matrix. The point of the matrix isn't the numbers — it's that the data will inform a *concurrency-aware* admission control policy that throttles requests when the predicted contention cost exceeds the predicted task value.

**Within-role placement state machine.** Currently a model's NUMA placement is decided once at server startup. We want it dynamic — if frontdoor is overloaded on quarter 0 and quarter 3 is idle, the orchestrator should be able to migrate work. The hard part is migrating *KV cache* (which is per-quarter); the model weights are mmap'd so migration there is free. Active design; nothing deployed.

## Optimization at the kernel level

**Q5_K / Q6_K / Q8_0 repack dispatcher.** Mainline llama.cpp has a NEON-only fast-path for repacking these quant formats; on x86 it falls back to a generic-scalar kernel that's 60–70 % slower than the kernel it replaces. We're writing hand-tuned AVX-512BW versions. CPU2's Q8 8×8 work shipped earlier — see [Quantization](../topics/quantization.md). Q5_K and Q6_K are queued.

**Sync primitive in OpenMP team coordination.** A pure-CPU optimization candidate identified in the [Hardware Optimization](../topics/hardware-optimization.md) work. Current synchronization uses condition variables which incur futex overhead per token. A pure user-space wait/wake based on a per-team counter would shave a small per-token cost; on bandwidth-saturated workloads this might be 1–3 %, on dense small models it might be 5–8 %.

## Knowledge & retrieval

**ColBERT reranker S5 (LateOn drop-in).** The S1–S4 phases of the ColBERT-based document retrieval are complete (ONNX Runtime, 180 ms encoding, perfect ranking separation on the internal evals). S5 swaps in LateOn-Code for the code retrieval channel specifically. Code is staged but not merged. See [Search & Retrieval](../topics/search-retrieval.md).

**Reason-mxbai edge fallback.** A small reranker fallback for the case where the main ColBERT reranker is overloaded or down. Queued behind S5.

**Bulk inference campaign.** Running ~12,000 queries through the full stack to characterize end-to-end production-realistic latency and quality distributions. This is the data set that the next round of routing-classifier training is waiting on (see "Retrain routing models" above).

## Continuous optimization

**Autopilot continuous optimization.** AutoPilot is doing its regular nightly Pareto-archive work. The current focus is the KV-cache compression integration; AM (Attention Matching) is the production winner at 50× compression, but EA (Expected Attention) might do better on specific request types. AutoPilot is currently characterizing the trade.

## Experimental: research deep-dives in progress

**Engram-Sentinel.** Investigating whether an n-gram embedding layer (à la LongCat-Flash-Lite) can give a non-trivial accuracy lift to the frontdoor model. LongCat shipped a simpler architecture than the original Engram paper described — we documented the distinction in [project_engram_vs_longcat_distinction](https://github.com/pestopoppa/epyc-root/blob/main/handoffs/active/engram-spike-sentinel-eval.md) — and we want to know which version (if either) is worth deploying. Tracking via the engram-spike handoffs.

**Constrained-creativity planner (Phase 2).** A planner that uses stagnation detection to switch between exploitative and exploratory prompting. Phase 1 landed 2026-05-23 with a 3-axis rubric and a persisted falsifier sidecar; Phase 2 wires it into the autopilot's seed-generation step.

## Documentation & site

**Link-rewriter follow-on.** This site has 8 residual link warnings (stale anchor refs in research/03-prompt-lookup.md and 01-speculative-decoding.md). They're inert but cosmetic. Low priority but tractable.

**More narrative pages.** This page and the others under [Stories](index.md) are the first batch. Future stories: the SkillBank experience-distillation rollout, the autopilot exogenous-restart resilience incident, the constrained-creativity planner work. Hand-curated; no auto-generation planned.

## Things deliberately not on this list

Items currently in `handoffs/blocked/` (waiting on upstream dependencies). Items in `handoffs/completed/` (done, recorded). The full long tail of intake-triage entries marked `worth_investigating` but not currently active.

For the live full queue: [handoffs/active/](https://github.com/pestopoppa/epyc-root/tree/main/handoffs/active) on GitHub.
