# The speculative decoding investigation

Speculative decoding looked, on paper, like the single biggest performance lever available to a CPU inference project. The recipe is irresistible: use a small fast draft model to propose K tokens, verify them all in one forward pass through the big model, accept the prefix that matches. The literature was full of 5-11× speedups. We invested heavily.

The result, after about fourteen months of work across maybe thirty experiments, is that speculation contributes a real but unspectacular 17-21 % to production throughput. The headline gain on this hardware comes from elsewhere — see [Why CPU-only inference is viable](why-cpu-inference.md). The interesting part of the investigation is *why* the literature numbers don't transfer, because the answer reshapes how to read every other CPU-vs-GPU comparison.

## The regime difference that breaks everything

Most speculative decoding papers are written from a GPU perspective. On a GPU, the dominant cost is the single forward pass through the target model — the matmul on the H100 — and verification can amortize K tokens of that pass at near-constant cost. If you can draft cheaply on the side, the speedup approaches K. That's the implicit story behind the 11× numbers.

On CPU the math is different in one specific way: each verified token requires re-reading the same KV cache to compute attention, and that re-read is *not* constant across K. The verification cost grows close to linearly in K, so the speedup ceiling — even with a perfect drafter — is much lower than the literature suggests. Empirically, for Q4_K_M models on EPYC, K saturates around 16. Past that, adding draft tokens stops helping and starts hurting because rejection cascades cost more than the wins. [Advanced Speculative Decoding](../subsystems/research/10-advanced-speculative-decoding.md) has the measurement.

That single constraint reshapes which variants are worth pursuing and which aren't. The variants that work on CPU all share one property: they avoid paying the separate-drafter cost. The variants that don't work all share another: they assume verification is cheap.

## What works: self-speculation in the model itself

The clearest CPU-friendly variant is **multi-token prediction (MTP)**, where the model's own auxiliary heads serve as the drafter and its main head serves as the verifier — no separate draft model, no extra weights to load. On `gemma-4-26B-A4B` (the worker role) the MTP accept rate sits at 0.5-0.7 depending on content type, and the net throughput gain over no-MTP is about 1.5×. This is one of the two levers in the [worker_general story](worker-general-story.md), the other being MoE expert sparsity.

A close cousin is **prompt lookup**, where the "drafter" isn't a model at all but a string-match against the prompt's own KV cache. For repetitive long-context workloads (summarization, structured extraction over long documents) this hits often. On Qwen3-Next-80B's long-context benchmark we measure roughly 12.7× speedup, though with a ~13 pp acceptance drop from a freeze-recurrent variant we're forced into by the SSM architecture. [Prompt Lookup](../subsystems/research/03-prompt-lookup.md) and [SSM & Hybrid Architectures](../topics/ssm-hybrid.md) cover the constraint.

The earlier production winner was a separate-drafter pair — Qwen3-Coder-32B verified by a Qwen2.5-Coder-0.5B drafter, K=24, 70.8 % acceptance, ~11× on code-completion benchmarks. That configuration retired after the 2026-05-06 stack consolidation merged the coder role into frontdoor; the win is preserved as a reference benchmark. The 11× number is real and reproducible, but it lived in a workload niche (high-acceptance code completion with a cheap aligned drafter) that doesn't generalize across the production mix.

## What doesn't work: anything that depends on cheap verification

The deepest negative result is **hybrid SSM speculation**. Hybrid state-space models like Qwen3-Next-80B have a verification path that's almost entirely sequential — about 220 ms per token, which is roughly 90 % of the decode cost. Even with a perfect drafter you can't amortize that sequential cost; we tried it with drafter sizes from 1.7 B to 4 B and K values from 4 to 24, and the verifier wall dominates every configuration. The freeze-recurrent variant in production sidesteps the wall by dropping SSM updates during draft proposal, which costs ~13 pp acceptance but recovers throughput on prompt-lookup workloads. No draft-verify approach works on hybrid SSM on CPU, full stop. [SSM & Hybrid Architectures](../topics/ssm-hybrid.md).

The other closures cluster around the same theme — approaches that depended on near-flat verification scaling or on cheap drafting:

| Approach | What it assumed | Why it closed |
|---|---|---|
| **SpecExec** (large tree speculation) | Verification trees of hundreds-to-thousands of speculative tokens amortize at near-flat cost | Q4_K_M CPU decode measures 4-5× verification scaling, not flat. Practical tree budgets max out at 16-64 nodes. |
| **DFlash** (O(1) drafting) | A learned hash function maps input to a draft token in constant time, eliminating drafter forward pass | Hash collisions drove acceptance below the break-even where verification cost dominates |
| **Slot promotion v1** | Dynamically reassigning NUMA quarters between drafter and verifier should improve aggregate throughput | Promotion overhead (KV-cache invalidation, server-state reload) larger than per-request gain on our workload mix |
| **MAB tree selector** | Per-request optimal-K varies enough that a bandit should converge to better-than-fixed-K | Optimal-K distribution is narrower than the literature suggests; fixed K=24 within 1-2 % of bandit-best on every measured workload |

All four have reopen criteria documented in their respective handoffs and chapters; none of those criteria describe the current production mix.

## The lesson the literature obscures

The CPU verification wall is the most important constraint for this whole investigation, and it's almost never named directly in the GPU-centric literature because it isn't a constraint on a GPU. Read any speculative decoding paper from 2024-2026 with the question "what does this assume about verification cost?" pinned to the top of the page and most of the technique-selection problems on CPU become tractable.

Practically: MTP and prompt-lookup are the two CPU-friendly variants worth deploying. The separate-drafter pairs work when the drafter is small, aligned to the target, and the workload has high acceptance — code completion, structured extraction — and not much else. The big architectural ideas in the literature (SpecExec, DFlash) need a different verification regime than ours to land their headline numbers.

The other half of this investigation's value is the explicit set of approaches we now know not to retry. [What we tried and ruled out](ruled-out.md) catalogues them with reopen criteria; [Deprecated Approaches](../subsystems/research/05-deprecated-approaches.md) is the per-chapter version with measurement detail.
