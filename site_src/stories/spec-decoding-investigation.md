# The speculative decoding investigation

Speculative decoding looked, on paper, like the single biggest performance lever available to a CPU inference project. The recipe is irresistible: use a small fast draft model to propose K tokens, verify them all in one forward pass through the big model, accept the prefix that matches. If the draft is right N times out of K, you've decoded N tokens for the cost of one big-model forward pass.

The literature was full of 5-11× speedups. We invested heavily in it. The result, after ~14 months of work across maybe 30 separate experiments, is messier than the literature suggested and very informative about *what the CPU regime actually looks like*.

This is what we found, what we deployed, and what we ruled out.

## The framing the literature uses

Most speculative decoding papers are written from a GPU perspective. On a GPU, the dominant cost is the *single forward pass* through the target model — the matmul on the H100 — and verification can amortize K tokens of that pass at near-constant cost. If you can draft cheaply on the side, the speedup approaches K.

On CPU the math is different. The single forward pass is bandwidth-bound, not compute-bound. Each verified token requires re-reading the same KV cache to compute attention; that re-read is *not* constant across K. The verification cost on CPU grows close to linearly in K. So the speedup ceiling — even with a perfect drafter — is much lower than the literature suggests.

For Q4_K_M models on EPYC, [Advanced Speculative Decoding](../subsystems/research/10-advanced-speculative-decoding.md) shows the empirical ceiling: K saturates around 16, after which adding more draft tokens doesn't help (and starts to hurt, because of rejection cascades).

## What we deployed

Three speculative-decode configurations are live in production:

1. **gemma-4-26B-A4B with MTP** (worker_general role). Multi-token prediction is technically a self-speculation variant — the auxiliary heads serve as the drafter, the main head serves as the verifier, no separate draft model needed. Accept rate ~0.5–0.7 depending on content type. Net throughput gain over no-MTP: ~1.5×. The full story is in [Worker_general: 17 → 76 t/s](worker-general-story.md).

2. **Qwen3-Next-80B with prompt lookup** (ingest_long_context role). The "drafter" here isn't a model — it's a string-match lookup against the current prompt's KV cache. For repetitive long-context tasks (summarization, structured extraction over long documents), the prompt-lookup hits a lot. We see ~12.7× speedup on Qwen3-Next-80B's long-context benchmark with a ~13 pp acceptance drop from a freeze-recurrent variant that the SSM constraint forces. See [Prompt Lookup](../subsystems/research/03-prompt-lookup.md) and the [SSM & Hybrid Architectures](../topics/ssm-hybrid.md) topic.

3. **Qwen3-Coder-32B with Qwen2.5-Coder-0.5B drafter** (legacy coder_escalation, now decommissioned). When `coder_escalation` was a separate model from `frontdoor`, the 32B/0.5B pair was the project's biggest spec-decode win: K=24, 70.8 % acceptance, ~11× speedup on code-completion benchmarks. After the 2026-05-06 stack consolidation merged coder_escalation onto frontdoor's Qwen3.6-35B-A3B Q8 model, the standalone pair retired. The win remains documented as a reference benchmark.

Aggregate contribution of speculative decoding to production throughput: +17–21 % over a no-spec baseline. Real but not transformative. The NUMA quartering work (see [Why CPU-only inference is viable](why-cpu-inference.md)) contributes more.

## What we ruled out

Cases where measurement said the idea didn't fit the regime:

**SpecExec (large tree speculation).** The paper proposes verification trees of hundreds-to-thousands of speculative tokens, which on GPU amortize cleanly. On Q4_K_M CPU decode we measure 4–5× verification scaling, not the projected near-flat curve. Practical tree budgets max out at 16–64 nodes. The full reconciliation between the paper's projection and our empirical results is in [Advanced Speculative Decoding](../subsystems/research/10-advanced-speculative-decoding.md), section 10.3.

**Hybrid SSM speculation.** This is the deepest negative result. Hybrid state-space models (like `Qwen3-Next-80B`) have a verification path that's almost entirely sequential — ~220 ms per token, which is ~90 % of the decode cost. Even with a perfect drafter, you can't amortize that sequential cost. We tried it with multiple drafter sizes (1.7 B, 4 B) and multiple K values; the verifier wall dominates every configuration. The result: no draft-verify approach works on hybrid SSM on CPU. The freeze-recurrent variant (used in Qwen3-Next-80B production) sidesteps this by dropping the SSM updates during draft proposal, which costs ~13 pp acceptance but recovers the throughput on prompt-lookup workloads. [SSM & Hybrid Architectures](../topics/ssm-hybrid.md).

**DFlash O(1) drafting.** The paper proposes a constant-time drafter via a learned hash function over the input. We implemented it for Qwen3.6-35B-A3B Q4_K_M; the hash collisions degraded acceptance below the threshold where it pays for the drafter cost. Closed NO-GO. [Advanced Speculative Decoding](../subsystems/research/10-advanced-speculative-decoding.md) section 10.5.

**Slot promotion (v1).** A scheme where the orchestrator dynamically reassigns NUMA quarters between drafter and verifier based on observed acceptance. Net-negative on Qwen3.6 + Qwen3-1.7B drafter (the candidate workload). Tree disabled-by-default in production. Reopen criteria documented: larger drafter, non-greedy verifier, long-context, high drafter/target disagreement workload. None of those describe our current production mix.

**MAB (multi-armed bandit) tree selector.** Adaptive K selection per request. Lost to a fixed K=24 on our workload mix because the bandit's exploration cost was bigger than the per-request optimal-K gain. Closed NO-GO.

## What this story actually demonstrates

Three takeaways:

1. **The CPU verification wall is the most important constraint.** The whole speculative-decode literature is implicitly assuming GPU verification costs. Treat the CPU case as a different problem with a much lower ceiling.

2. **MTP and prompt-lookup are the CPU-friendly variants.** Both avoid the separate-drafter cost. Both have acceptance distributions that suit our typical workload. Both are deployable today.

3. **Closed-negatives are load-bearing knowledge.** Half of the value of this investigation is the set of approaches we now know *not* to try. The [Deprecated Approaches](../subsystems/research/05-deprecated-approaches.md) chapter is the canonical record. Each closure cites the measurement that killed the approach and the reopen criteria that would resurrect it.

## What's next on this thread

[Speculative Decoding](../topics/speculative-decoding.md) is the topic synthesis; [Advanced Speculative Decoding](../subsystems/research/10-advanced-speculative-decoding.md) is the research chapter with the empirical detail. For the SSM-specific side, [SSM & Hybrid Architectures](../topics/ssm-hybrid.md). The broader pattern of pursuing-and-falsifying lives in [What we tried and ruled out](ruled-out.md).
