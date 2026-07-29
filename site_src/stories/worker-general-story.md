# Worker_general: 17 → 76 t/s

Most performance work is incremental — a few percent here, a fraction there. Occasionally a single change cascades through the stack and you get a 4×. This is one of those.

The worker — the role that handles routine, simple-to-moderate complexity tasks — went from running `Qwen2.5-7B-Instruct` at about 17 t/s in February 2026 to running `gemma-4-26B-A4B` at 76 t/s solo (60 t/s in production aggregate) in May 2026. Same hardware. Larger model. Higher throughput. Better quality on every metric we measure. The story is about how that happened, because the answer is more interesting than "we upgraded the model."

## The starting point

In early 2026 the worker role was `Qwen2.5-7B-Instruct` at fp16. We chose a 7 B because the worker handles the majority of traffic by volume and we wanted it to be cheap. Throughput was 17 t/s on a single NUMA quarter. Quality was acceptable on simple tasks, but the tool-compliance score — the rate at which the worker correctly emits valid structured tool calls — sat around 62 %, uncomfortably low for an orchestrator that hands tasks to tools after every escalation.

The obvious plan was to train or fine-tune a better 7 B. That plan didn't survive contact with reality.

## Why a bigger model could be faster

The intuition that bigger means slower assumes you're FLOPs-bound. We're not. We're bandwidth-bound. Decode throughput on this hardware is roughly `(memory bandwidth) / (model size in memory)`, so a 4× larger model with the same architecture would be 4× slower. The path to a bigger-and-faster model goes through changing that architecture.

Two levers did the work. The first was MoE: `gemma-4-26B-A4B` has 26 B total parameters but only 4 B active per token. The decoder only reads the 4 B of weights the routing function selected, plus a small router, so the effective memory footprint per token is closer to a 4 B dense model than a 26 B one. The second was multi-token prediction (MTP): gemma-4 ships with auxiliary heads that predict the next K tokens in parallel during training, and at inference time the heads propose token N+1 directly from token N's hidden state. If the propose verifies (against the main head), you've decoded two tokens for the cost of one. The MTP accept rate on gemma-4 is high enough to deliver about 1.5× on top of the MoE win.

The arithmetic lands cleanly. The Qwen2.5-7B at fp16 reads about 14 GB per token against ~115 GB/s of NUMA-quarter bandwidth, yielding ~8 t/s theoretical and ~17 t/s measured (some prefetching helps). The gemma-4-26B-A4B at Q4_K_M with MTP reads about 2 GB per output token — 4 B active weights at 4-bit, multiplied by the MTP factor — for ~57 t/s theoretical and 60.7 t/s measured. Roughly 4× the throughput from a model that's 4× larger. MoE and MTP, stacked, flipped the bandwidth math. See [MoE Optimization](../topics/moe-optimization.md) for the underlying architecture.

## The runtime had to keep up

The arithmetic only works if the runtime actually implements MTP decode, and mainline llama.cpp didn't at the time. We were on a custom branch of [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) that did, via [PR #1744](https://github.com/ikawrakow/ik_llama.cpp/pull/1744). When we first launched the swap on 2026-05-08 we measured 76.5 t/s solo. Good.

Then we wired it into the orchestrator's `worker_pool` launch path and the production number dropped to about 9 t/s.

## The OMP idle-spin incident

For 24 hours we thought the swap was a regression. The model was hitting full load on its assigned cores and producing tokens, but the throughput was an order of magnitude below the bench number. Other models on the box also slowed down — frontdoor decode dropped 78 %.

The cause was OpenMP idle-spin. The MTP-capable build of ik_llama.cpp parallelizes inside the model via OMP. When a thread runs out of work — say, the MTP head finishes early — the libomp default behavior is to spin on a futex waiting for new work, consuming a full core while spinning. With 96 cores split across four model instances, one model's idle spin was contending with another model's productive work for the same NUMA quarter.

The fix turned out to be one environment variable: `KMP_BLOCKTIME=10` (milliseconds). It tells libomp to give up the core after 10 ms of idleness instead of spinning indefinitely. With it set, idle cores correctly went to sleep on a futex, gemma-4's idle CPU dropped from 95 % to 0 %, frontdoor decode recovered its 78 %, and the whole stack got back to bench-equivalent throughput.

The standard OMP idle-control API (`omp_pause_resource`) doesn't help on this build because AOCC's libomp ignores it. `KMP_BLOCKTIME` is the working knob. We wired the env var into `orchestrator_stack.py`'s worker_pool launch and the incident closed 2026-05-09. [Inference Serving](../topics/inference-serving.md) has the debugging trail and the full env-var stack we now require for any new model launch.

## Quality came along for the ride

The throughput story is the headline, but the quality numbers are where the model swap pays off long-term. Tool compliance — the metric most operationally important to the orchestrator's escalation chain — jumped from 62 % to 80 % (an 18-point gain, Claude-as-Judge). Full-suite Simula scores moved from 71 % to 77 %. The 18-point tool-compliance lift is the one that compounds: escalations are triggered by parsing failures, so fewer parsing failures means fewer escalations, which means lower aggregate latency and cost across the whole stack.

## What this story actually demonstrates

The runtime had to be in the loop before we could even consider the swap. A bigger model on a runtime that doesn't implement MTP would have lost the bandwidth bet. Two of the project's largest single performance wins (this one and the AVX-512BW Q8 kernel) came from runtime work, not model work.

The result also required both levers, not either one alone. MoE alone would have given a moderately faster 26 B (maybe 30 t/s against the 7 B's 17). MTP alone wouldn't have helped a dense 7 B because there's nothing to amortize. The headline number is from the two compounding, and that's the recurring pattern: individually small levers compound multiplicatively when they target orthogonal bottlenecks.

The final lesson is that production is the hostile environment. Bench told us 76.5 t/s; production told us 9. The gap was a global resource the bench didn't share with anything. Always validate model swaps under realistic concurrency, not just solo — that constraint is baked into the project's [benchmark methodology](../topics/benchmark-methodology.md) now.
