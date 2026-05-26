# What we tried and ruled out

The cleanest signal a research project can produce is a falsified hypothesis paired with the measurement that killed it. This page collects the ones we've earned. They're as load-bearing as any feature in production — knowing what *not* to try saves more time than any single optimization saves.

A pattern across the list: most of these closures **invalidated an assumption** rather than disproving a mechanism. L3-as-NUMA didn't fail because L3-as-NUMA is a bad idea; it failed because our workload's actual bottleneck wasn't where we thought. NUMA mirroring didn't fail because mirroring is wrong; it failed because the fabric isn't our limit on single-socket. DeepConf didn't fail because confidence-routing is bad; it failed because *our* confidence isn't calibrated. The most-repeated meta-lesson is to measure the actual bottleneck before adopting a paper that targets a different one.

The three cases below are the most informative. The shorter table afterwards catalogues the rest.

## L3-as-NUMA BIOS configuration

The hypothesis was that exposing each EPYC CCD's L3 cache as its own NUMA domain — a BIOS-level option — would give us finer-grained memory-locality control, predictable cache behavior, and smaller affinity domains. The CPU1 phase-1 work projected single-digit-percent gains and the mechanism sounded clean.

We flipped the BIOS setting in late April 2026 and ran the production benchmark suite on five models. Every single one regressed, badly:

| Model | NPS4 baseline | L3-as-NUMA | Δ |
|---|---:|---:|---:|
| Qwen3-Coder-30B | 49.1 t/s | 23.6 t/s | −52 % |
| Qwen3.6-35B-A3B (frontdoor) | 12.7 t/s | 6.2 t/s | −51 % |
| gemma-4-26B-A4B (worker) | 60.7 t/s | 38.4 t/s | −37 % |
| Qwen3.5-122B-A10B | 12.19 t/s | 7.4 t/s | −39 % |
| Qwen3-Next-80B | 14.4 t/s | 10.1 t/s | −30 % |

The implicit assumption was that more, smaller NUMA domains buys better locality control. The reality is that each CCD has only 32 MB of L3 while model weights at 4-bit quant are 6-250 GB — the L3 is a thin layer over DRAM, and making it a separate NUMA domain just adds allocator pressure without giving the locality system anything new to optimize. We measured, we reverted, we moved on. The full reversal is documented in [project_l3aan_reverted](https://github.com/pestopoppa/epyc-root/blob/main/handoffs/completed/cpu-optimization-cpu1-l3aan-reversal.md) and the broader hardware context is in [Hardware Optimization](../topics/hardware-optimization.md). The mechanism would need to change — e.g. a tier of tensor parallelism where weights actually live in L3 — before this is worth revisiting.

## NUMA mirror (weight duplication)

The hypothesis was that duplicating model weights across all four NUMA nodes would eliminate cross-node fabric traffic during decode. Each token's threads would read from their local node only. On 2-socket EPYC this is a known win; the question was whether the single-socket NPS4 case shared the benefit.

We mirrored two production models across all four nodes and compared against the single-bind baseline:

| Model | Single-bind | NUMA mirror | Δ |
|---|---:|---:|---:|
| Qwen3-Coder-30B (proxy) | 49.1 t/s | 48.6 t/s | −1.0 % |
| Qwen3.6-35B-A3B | 12.7 t/s | 12.78 t/s | +0.6 % |

Both differences are inside measurement noise. The single-socket EPYC's bottleneck is DRAM channels, not the inter-CCD fabric; mirroring buys you locality on a fabric that isn't the constraint. Clean falsification for single-socket, with a precise scope: the closure is deferred (not closed) for 2P configurations, where the cross-socket fabric *would* be the bottleneck. We don't have 2P hardware so we can't test there. [Hardware Optimization](../topics/hardware-optimization.md).

## DeepConf (confidence-routed multi-sample)

The hypothesis was that running a generation multiple times and returning the answer with the highest expressed confidence would beat majority-vote, per a published claim across several benchmarks. For our routing — where we already escalate on failed outputs — this would be a free quality lift.

We implemented DeepConf scoring on the Qwen3.6 frontdoor and ran 1,000-sample evaluations. The model's confidence score had near-zero correlation with answer correctness. The high-confidence picks were no better than the majority vote, and on some benchmarks they were measurably worse.

This is the subtlest of the three closures because the mechanism the paper relies on — confidence as a proxy for correctness — could in principle hold for some models even if it doesn't hold for ours. There's a literature suggesting confidence calibration is highly model-specific. We closed it NO-GO 2026-04 with reopen criteria attached: a model with independently-demonstrated calibrated confidence would let us revisit. Until then, our routing layer doesn't get to use this. [Inference Serving](../topics/inference-serving.md).

## Briefer closures

The remaining ruled-out items follow the same template but the measurement stories are shorter.

| Approach | Hypothesis | Why it closed | Reopen criteria |
|---|---|---|---|
| **AReaL** (RLHF training framework) | Use a published research-grade RLHF recipe to train a frontdoor-specific routing model | Compute budget mismatch: AReaL is sized for ~10⁵ GPU-hours per run; our equivalent budget is ~10⁻¹ GPU-hours. Six orders of magnitude. Catalogued as closed-on-compute-cost so the falsification is scoped. | Access to 10⁴+ GPU-hours of training compute. [Reinforcement Learning](../topics/reinforcement-learning.md). |
| **Slot promotion v1** | Dynamically promote NUMA quarters from drafter-serving to verifier-serving (and back) based on observed acceptance rate | Promotion overhead — KV cache invalidation, server-state reload, brief role-confusion window — exceeded acceptance-rate gain on the candidate workload (Qwen3.6 + Qwen3-1.7B drafter). Flag preserved (disabled by default). | Larger drafter (3B+), non-greedy verifier, long-context, high drafter/target disagreement. Not our current production mix. [Spec decoding investigation](spec-decoding-investigation.md). |
| **SLIDERS** (structured-DB + SQL alternative to RAG) | Replace vector-RAG with structured queries against a SQL database the model writes against | Adoption pipeline depends on a hard-coded GPT-4.1 step; Qwen3.5-122B substitute degraded prompt-translation enough that SLIDERS' quality advantage evaporated. Falsifies the open-source path to SLIDERS, not the technique. | Open-source model that reliably emits SLIDERS' query format. Qwen3-Coder-480B might be close. [RAG Alternatives](../topics/rag-alternatives.md). |
| **DFlash** (O(1) drafting) | Constant-time drafter via learned hash function; skip drafter forward pass entirely | Hash collision rate drove acceptance below break-even, given non-trivial CPU verification cost. A real drafter at 0.70 acceptance beats a "free" hash drafter at 0.31. | Substantially better hash function (learned + content-conditional) driving collisions below 5 %. [Spec decoding investigation](spec-decoding-investigation.md). |
| **MAB tree selector** | Adapt speculative-decode K parameter per-request via bandit; different requests have different optimal K | Bandit exploration cost (occasional bad K choices for learning) exceeded the per-request optimal-K gain. Fixed K=24 within 1-2 % of bandit-best on every workload measured. | Workload mix where measured optimal-K varies meaningfully (≥2× across request types). |

## What these aren't

These aren't failures. Each entry is a region of the design space where the obvious-sounding move doesn't work on this hardware with these models, and each is cheap to look up later when a new paper touches the same area. The discipline is to keep the closures *scoped* — to say what specifically didn't work and what would have to change to reopen — rather than letting one negative result generalize into "the whole technique is dead." The project's `feedback_closure_inflation` note is the corrective for that drift, and the audit trail in [the autonomous research loop](autonomous-research-loop.md) is how we catch it when it starts to happen.
