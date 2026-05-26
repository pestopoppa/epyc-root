# Worker_general: 17 → 76 t/s

Most performance work is incremental — a few percent here, a fraction there. Occasionally a single change cascades through the stack and you get a *4×*. This is one of those.

The worker — the role that handles routine, simple-to-moderate complexity tasks — went from running `Qwen2.5-7B-Instruct` at ~17 t/s in February 2026 to running `gemma-4-26B-A4B` at 76 t/s solo (60 t/s in production aggregate) in May 2026. Same hardware. Larger model. Higher throughput. Better quality.

This story is about how that happened, because the answer is more interesting than "we upgraded the model."

## The starting point

In early 2026 the worker role was `Qwen2.5-7B-Instruct` at fp16. We chose a 7 B because the worker handles the majority of traffic by volume and we wanted it to be cheap. Throughput was 17 t/s on a single NUMA quarter. Quality was acceptable on simple tasks but the tool_compliance score (the rate at which the worker correctly emits valid structured tool calls) sat around 62 % — uncomfortably low for an orchestrator that hands tasks to tools after every escalation.

The plan at the time was the obvious one: train or fine-tune a better 7 B. That plan didn't survive contact with reality.

## Why a bigger model could be faster

The intuition that bigger = slower assumes you're FLOPs-bound. We're not. We're bandwidth-bound. Decode throughput is roughly `(memory bandwidth) / (model size in memory)`. So a 4× larger model with the same architecture would be 4× slower.

But two things changed that arithmetic:

1. **MoE.** A `gemma-4-26B-A4B` has 26 B total parameters but only 4 B *active* per token. The decoder only reads the 4 B of weights that the routing function selected, plus a small router. Effective memory footprint per token is closer to a 4 B dense model than a 26 B one. [MoE Optimization](../topics/moe-optimization.md).

2. **Multi-token prediction (MTP).** Gemma-4 ships with auxiliary heads that predict the next K tokens in parallel during training. At inference time, with the right runtime, you can use those heads to skip a model evaluation: the heads propose token N+1 directly from token N's hidden state. If the propose succeeds (verified by the main head), you've decoded two tokens for the cost of one. On gemma-4, the MTP accept rate is high enough that we see ~1.5× throughput gain from this alone.

The math:
- Dense Qwen2.5-7B at fp16: 14 GB to read per token, bandwidth 115 GB/s → ~8 t/s theoretical, ~17 t/s measured (with some prefetching).
- MoE gemma-4-26B-A4B at Q4_K_M with MTP: 2 GB active weights to read per output token (4 B active × 4-bit + MTP factor) → ~57 t/s theoretical, 60.7 t/s measured.

Roughly 4× the throughput from a model that's 4× larger. The MoE + MTP combination flipped the bandwidth math.

## The runtime had to keep up

The arithmetic above only works if the runtime *implements MTP decode*. Mainline llama.cpp didn't, at the time. We were on a custom branch of [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) that did, via [PR #1744](https://github.com/ikawrakow/ik_llama.cpp/pull/1744). When we first launched the swap on 2026-05-08, we measured 76.5 t/s solo. Good.

Then we wired it into the orchestrator's `worker_pool` launch path and the production number dropped to ~9 t/s.

## The OMP idle-spin incident

For 24 hours we thought the swap was a regression. The model was hitting full load on its assigned cores and producing tokens, but the throughput was an order of magnitude below the bench number. Other models on the box also slowed down — frontdoor decode dropped 78 %.

The cause was idle-spin. The MTP-capable build of ik_llama.cpp parallelizes inside the model via OpenMP. When a thread runs out of work (e.g. the MTP head finishes early), the libomp default behavior is to spin on a futex waiting for new work, *consuming a full core* while spinning. With 96 cores split across four model instances, the idle spin from one model was contending with the productive work of every other model on the chip.

The fix turned out to be one environment variable: `KMP_BLOCKTIME=10` (milliseconds). This tells libomp to give up the core after 10 ms of idleness instead of spinning indefinitely. With it set, idle cores correctly went to sleep on a futex; idle CPU dropped from 95 % to 0 % on gemma-4; frontdoor decode recovered its 78 %; the whole stack got back to bench-equivalent throughput.

The standard OMP idle-control API (`omp_pause_resource`) doesn't help on this build because AOCC's libomp ignores it. `KMP_BLOCKTIME` is the working knob. We wired the env var into `orchestrator_stack.py`'s worker_pool launch and the incident closed 2026-05-09. [Inference Serving](../topics/inference-serving.md) has the full debugging trail and the env-var stack we now require for any new model launch.

## Quality came along for the ride

The throughput story is the headline, but the quality numbers are where the model swap pays off long-term.

| Metric | Qwen2.5-7B | gemma-4-26B-A4B | Δ |
|---|---:|---:|---:|
| Full suite (Simula) | 71 % | 77 % | +6 pp |
| Tool compliance (Claude-as-Judge) | 62 % | 80 % | +18 pp |
| Single-stream throughput (t/s) | 17.3 | 60.7 | +250 % |

The tool_compliance jump is the operationally important one. The orchestrator's escalation chain depends on workers emitting structured outputs the next stage can parse. An 18 pp lift in compliance means substantially fewer cascading failures, which means substantially fewer escalations to the bigger models, which means lower aggregate latency and cost.

## What this story actually demonstrates

Three things, in increasing order of how much they generalize:

1. **Pick the right runtime.** A bigger model on a runtime that doesn't implement MTP would have lost the bandwidth bet. The runtime had to be in the loop before we could even consider the swap. Two of the project's largest single performance wins (this one, and the AVX-512BW Q8 kernel) came from runtime work, not model work.

2. **Stack the levers.** Neither MoE nor MTP alone explains the result. MoE alone would have given a moderately faster 26 B (probably ~30 t/s vs the 7 B's 17). MTP alone wouldn't have helped a dense 7 B because there's nothing to amortize. Both levers compounding gives the headline number. The project's recurring lesson is that *individually small levers compound multiplicatively* when they target orthogonal bottlenecks. [Hardware Optimization](../topics/hardware-optimization.md), [MoE Optimization](../topics/moe-optimization.md).

3. **Production is the hostile environment.** Bench measurements told us 76.5 t/s. Production told us 9. The gap was a global resource the bench didn't share with anything. The lesson — always validate model swaps under realistic concurrency, not just solo — is baked into the project's benchmarking protocol now. [Benchmark Methodology](../topics/benchmark-methodology.md).

## What's next on this thread

If you want the underlying mechanics, [MoE Optimization](../topics/moe-optimization.md) is the deeper version of the architecture story and [Inference Serving](../topics/inference-serving.md) covers the runtime side. If you want the broader lever-stacking pattern, [The speculative decoding investigation](spec-decoding-investigation.md) is another example of multiple-orthogonal-levers compounding.
