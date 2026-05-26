# What we tried and ruled out

The cleanest signal a research project can produce is a falsified hypothesis with the measurement that killed it. This page collects the ones we've earned. They're as load-bearing as any feature in production — knowing what *not* to try saves more time than any single optimization saves.

Each entry: hypothesis, what we measured, why we closed it, and (if known) the reopen criteria.

## L3-as-NUMA BIOS configuration

**Hypothesis.** AMD EPYC supports a BIOS mode that exposes each CCD's L3 cache as its own NUMA domain. This sounded like a free win — finer-grained memory-locality control, predictable cache behavior, smaller affinity domains. The CPU1 phase-1 work had projected single-digit-percent gains.

**What we measured.** Flipped the BIOS setting in late April 2026, ran the production benchmark suite on five models. Every single one regressed:

| Model | NPS4 baseline | L3aaN | Δ |
|---|---:|---:|---:|
| Qwen3-Coder-30B | 49.1 t/s | 23.6 t/s | −52 % |
| Qwen3.6-35B-A3B (frontdoor) | 12.7 t/s | 6.2 t/s | −51 % |
| gemma-4-26B-A4B (worker) | 60.7 t/s | 38.4 t/s | −37 % |
| Qwen3.5-122B-A10B | 12.19 t/s | 7.4 t/s | −39 % |
| Qwen3-Next-80B | 14.4 t/s | 10.1 t/s | −30 % |

**Why it closed.** The implicit assumption ("more, smaller NUMA domains = better locality control") didn't survive contact with the fact that *the production stack doesn't have memory-locality problems large enough to be worth the extra fragmentation cost*. Each CCD has only 32 MB of L3; model weights at 4-bit quant are ~6–250 GB. The L3 is a thin layer over DRAM; making it a separate domain just adds allocator pressure.

**Reopen criteria.** None. The mechanism would need to change (e.g. a tier of tensor parallelism where weights actually live in L3) before this is worth revisiting. We measured, we reverted, we moved on. The full reversal is documented in [project_l3aan_reverted](https://github.com/pestopoppa/epyc-root/blob/main/handoffs/completed/cpu-optimization-cpu1-l3aan-reversal.md). [Hardware Optimization](../topics/hardware-optimization.md).

## NUMA mirror (weight duplication)

**Hypothesis.** Duplicate model weights across all four NUMA nodes. Each token's threads then read from their local node only, eliminating cross-node fabric traffic. On 2-socket configs this is known to win; we wanted to know if the single-socket NPS4 case shared the benefit.

**What we measured.** Mirrored gemma-4-26B-A4B (`worker_general`) and Qwen3-Next-80B across all four nodes, ran the same production benchmark. Differences:

| Model | Single-bind | NUMA mirror | Δ |
|---|---:|---:|---:|
| Qwen3-Coder-30B (proxy) | 49.1 t/s | 48.6 t/s | −1.0 % |
| Qwen3.6-35B-A3B | 12.7 t/s | 12.78 t/s | +0.6 % |

Both within measurement noise.

**Why it closed.** The single-socket EPYC's *bottleneck is DRAM channels, not the inter-CCD fabric*. Mirroring buys you locality on a fabric that isn't the bottleneck. The measurement was clean enough to close the question on this hardware.

**Reopen criteria.** Two-socket configurations only. On a 2P EPYC the cross-socket fabric *is* the bottleneck, so mirroring there should win. We don't have 2P hardware so we can't test, but the closure is explicit about scope: closed for single-socket, deferred for 2P. [Hardware Optimization](../topics/hardware-optimization.md).

## DeepConf (confidence-routed multi-sample)

**Hypothesis.** Run a generation multiple times, take the answer where the model expresses highest confidence, return that. The paper claimed this beat majority-vote across multiple benchmarks. For routing — where we already do escalation on failed outputs — this could be a free quality lift.

**What we measured.** Implemented DeepConf scoring on Qwen3.6 frontdoor, ran 1,000-sample evaluations. The model's confidence score had near-zero correlation with answer correctness. The "high-confidence" picks were no better than the majority vote, and on some benchmarks they were *worse*.

**Why it closed.** The mechanism the paper depends on (confidence as a proxy for correctness) doesn't hold for our model + prompting regime. We don't fully understand why — there's a literature suggesting confidence calibration is highly model-specific — but the empirical signal was unambiguous: no gain. Closed NO-GO 2026-04. [Inference Serving](../topics/inference-serving.md).

**Reopen criteria.** A model with demonstrably-calibrated confidence (we'd need that result independently before we'd trust the routing).

## AReaL (RLHF training framework)

**Hypothesis.** A research-grade RLHF framework with a published recipe. The wiki had flagged it as a possible substrate for training a frontdoor-specific routing model.

**What we measured.** Read the source, estimated the compute requirements. AReaL is sized for ~10^5 GPU-hours per training run. Our budget is ~10^−1 GPU-hours equivalent (running on CPU). Six orders of magnitude mismatch.

**Why it closed.** Not a measurement, an obvious gating constraint we should have checked earlier. Cataloged as closed-on-compute-cost rather than closed-on-quality so future readers don't waste time re-investigating. [Reinforcement Learning](../topics/reinforcement-learning.md).

**Reopen criteria.** Access to 10^4+ GPU-hours of training compute.

## Slot promotion v1

**Hypothesis.** Dynamically promote NUMA quarters from drafter-serving to verifier-serving (and back) based on observed acceptance rate. Sounds elegant; the orchestrator already knows each slot's role and could reassign.

**What we measured.** Built v1 with `--spec-numa-quarters` flag. Net-negative on the Qwen3.6 + Qwen3-1.7B drafter combo (our then-candidate workload). The promotion overhead — KV cache invalidation, server-state reload, brief role-confusion window — was larger than the acceptance-rate gain.

**Why it closed.** v1 was net-negative on the workload mix we care about. The promotion mechanism is correct in principle; it's the workload that's wrong for it. Closed but flag is preserved (disabled by default) so the path stays open for a future workload.

**Reopen criteria.** Larger drafter (3B+), non-greedy verifier, long-context, high drafter/target disagreement. None of those are our current production mix. [Spec decoding investigation](spec-decoding-investigation.md).

## SLIDERS (structured-DB + SQL alternative to RAG)

**Hypothesis.** Replace vector-RAG with structured queries against a SQL database the model writes against. For domain-specific applications this can be more precise than embedding similarity.

**What we measured.** Didn't get to running it. The paper's adoption pipeline depends on a hard-coded GPT-4.1 step that we don't have an open-source equivalent for. We tried substituting with Qwen3.5-122B; the prompt-translation step degraded enough that the SLIDERS quality advantage evaporated.

**Why it closed.** Gated behind the closed-source dependency. Not a falsification of SLIDERS — a falsification of the open-source path to SLIDERS. [RAG Alternatives](../topics/rag-alternatives.md).

**Reopen criteria.** An open-source model that can reliably emit the structured query format SLIDERS expects. Qwen3-Coder-480B might be close; haven't measured.

## DFlash O(1) drafting (speculative decode variant)

**Hypothesis.** A learned hash function on the input that maps to a draft token in constant time. If the hash is good, you skip the drafter forward pass entirely.

**What we measured.** Implemented on Qwen3.6-35B-A3B Q4_K_M. Hash collision rate was high enough that the acceptance rate dropped below the break-even point. Specifically: a real drafter at 0.70 acceptance is worth more than a hash drafter at 0.31 acceptance even though the hash is "free", because the verification cost is non-trivial and you pay it on every rejection.

**Why it closed.** The CPU verification cost makes hash-based drafting impractical. On GPU (where verification is cheap) this might still work. Closed for CPU. [Spec decoding investigation](spec-decoding-investigation.md).

**Reopen criteria.** Substantial improvement to the hash function (e.g. learned + content-conditional) that drives collision rate down below 5 %.

## MAB (multi-armed bandit) tree selector

**Hypothesis.** Adapt the speculative-decode K parameter per-request via a bandit. Different requests have different optimal K; an online bandit should converge.

**What we measured.** Built it, ran on production traffic for a week. The bandit's exploration cost (occasional bad K choices for the sake of learning) exceeded the per-request gain from optimal K selection. Fixed K=24 was within 1–2 % of bandit-best on every workload we tested.

**Why it closed.** The optimal-K distribution is narrower than the literature suggests for our workloads. The bandit is solving a problem we don't have. Closed NO-GO.

**Reopen criteria.** A workload mix where measured optimal-K varies meaningfully (say, factor of 2× between request types). None of our current workloads hit this.

## What this story actually demonstrates

These aren't failures. Each one is a piece of knowledge: a region of the design space where, on this hardware, with these models, the obvious-sounding move doesn't work. They're cheap to look up later — when we evaluate a new paper that touches one of these areas, we can compare directly against the closed entry and decide quickly whether anything has changed enough to revisit.

A pattern across the list: most of these closures **invalidate an assumption** rather than disproving a mechanism. L3aaN didn't fail because L3-as-NUMA is a bad idea — it failed because our workload's actual bottleneck wasn't where we thought. NUMA mirror didn't fail because mirroring is wrong — it failed because the fabric isn't our limit on single-socket. DeepConf didn't fail because confidence-routing is bad — it failed because *our* confidence isn't calibrated.

The most repeated meta-lesson: **measure the actual bottleneck before adopting a paper that targets a different bottleneck**.

## What's next on this thread

The active counterpart to this page is [What we're investigating now](investigating-now.md). The deeper synthesis articles that compile these closures are [Hardware Optimization](../topics/hardware-optimization.md), [Speculative Decoding](../topics/speculative-decoding.md), and [Inference Serving](../topics/inference-serving.md). For the meta-discipline of avoiding "closure inflation" (over-generalizing from one falsification to a broader claim), the project memory `feedback_closure_inflation` is the corrective.
