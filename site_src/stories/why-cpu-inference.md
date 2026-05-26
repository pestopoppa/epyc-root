# Why CPU-only inference is viable on EPYC

The conventional wisdom is that real LLM inference needs GPUs. For some workloads it does. For a non-trivial chunk of production work, it doesn't — and the difference is mostly about understanding where your bottleneck actually is.

This is the hardware story behind the project.

## The bottleneck isn't compute

Modern LLM decode is **memory-bandwidth bound**, not FLOP-bound. For each generated token you read the entire model from memory (the weights), do a relatively small amount of arithmetic, and write back a small KV-cache update. The arithmetic-to-bytes ratio is so low that the CPU/GPU is idling on memory most of the time.

On an AMD EPYC 9655 we have 12 channels of DDR5-5600 delivering ~460 GB/s of aggregate memory bandwidth. That's roughly a quarter of an A100 (1.6 TB/s) and about 1/7 of an H100 (3.4 TB/s). So the upper bound on single-stream decode throughput is also about 1/4 to 1/7 of GPU-equivalent.

But — and this is the lever the project is built on — the chip has *96 cores* split across *four NUMA nodes*, each with its own quarter of the bandwidth. If you can run four independent model instances and they each saturate one quarter, you get back roughly 3× the effective decode throughput. That's NUMA quartering, and it's the single biggest performance lever on this machine. [Hardware Optimization](../topics/hardware-optimization.md) has the full picture, including the measurement that pinned 4×24-thread quartering at 4.6× the throughput of 1×96-thread single-instance on the same model.

## The NPS4 decision

EPYC chips ship with a configurable NUMA-per-socket (NPS) setting in BIOS. NPS1 means one NUMA node (one memory pool) per socket; NPS4 splits the socket into four. The default many vendors ship is NPS1 because it's safer for general-purpose workloads.

For LLM inference, NPS4 won. By a lot. Switching from NPS1 to NPS4 picked up ~25 % aggregate throughput on the production stack — not because NPS4 has more bandwidth (it doesn't), but because it forces explicit allocation discipline. Under NPS1 we were silently relying on Linux's auto-balancing to put a model's weights near its threads. Under NPS4 we *have* to specify, and being explicit caught a bunch of mis-pinned cases that NPS1 had been papering over.

The full NPS4 commissioning and the CCD-aware load-balancing work that followed are in [Hardware Optimization](../topics/hardware-optimization.md).

## Quantization is essential, not optional

A 26 B parameter MoE model is ~52 GB in fp16 and ~16 GB in Q4_K_M. We use Q4_K_M (4-bit weights with K-quants) for nearly everything in production. The bandwidth savings are linear with the bit width, so a 4× compression buys roughly 4× the single-stream decode throughput. Quality loss is real but small — usually 1–2 pp on standard benchmarks — and for production workloads it's worth the trade. [Quantization](../topics/quantization.md) covers the variants we evaluated (including TQ3, PolarQuant, and QJL, all of which lost to Q4_K_M on CPU) and why Hadamard + Q4_0 is our KV-cache configuration of choice.

The exception is the embedder. We run BGE-large-en-v1.5 at F16 because embedding throughput isn't on the critical path and the quality difference matters more.

## The ik_llama.cpp fork

We use a custom fork of [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) (which is itself a fork of llama.cpp focused on CPU performance and quantization variants). The reason isn't ideological — it's that mainline llama.cpp lacks several features that matter for CPU production:

- **Multi-token prediction (MTP) decode**, used by `gemma-4` and `Qwen3-Next`. Without this, gemma-4 decodes at 17 t/s. With it, 60+ t/s.
- **Better Q8 8×8 GEMM kernels** with hand-written AVX-512BW intrinsics. CPU2's contribution: +31.8 % single-thread Q8 decode (single-thread regime; bandwidth-saturated regimes see less).
- **NUMA-aware memory binding** (`set_mempolicy(MPOL_INTERLEAVE)` on weight buffers) so a 96-thread instance can interleave across all four NUMA nodes instead of pinning to one.

The fork tracks upstream regularly and we cherry-pick fixes when they're available. The fork is at `pestopoppa/llama.cpp` (branch `production-consolidated-v5`). [Local Inference](../topics/local-inference.md) covers the cherry-pick workflow and the cases where we've had to write our own fix.

## What CPU-only doesn't get you

This is also a story of what *doesn't* work, because being honest about it is part of why the project ships.

- **Hybrid SSM models don't speculate.** The whole speculative decoding playbook relies on cheap drafting + parallel verification. Hybrid SSM models like `Qwen3-Next-80B` have a verification path that takes ~220 ms per token (90 % of the decode cost). That kills speculation as a speedup. We documented this thoroughly because the SSM literature keeps publishing "10× speculation speedups" without mentioning this constraint. [SSM & Hybrid Architectures](../topics/ssm-hybrid.md).
- **Very large dense models don't fit the bandwidth budget.** A 70 B fp16 dense model on this hardware decodes at ~2 t/s. Useless for interactive work. We deal with this by routing dense-only-feasible tasks to the orchestrator's smallest-acceptable tier rather than always escalating to the architect.
- **Latency-sensitive multimodal is hard.** Vision tokens are large and the prefill cost is non-trivial. We handle this by pinning vision models to dedicated cores and using a smaller VL model for first-pass, escalating only if it fails.

## What it does get you

- A 1.13 TB DDR5 chip costs less than one H100. It can host 9 production models simultaneously in HOT memory (always-resident), no swap, no reload latency. The architect (Qwen3.5-122B-A10B) and the long-context ingestor (Qwen3-Next-80B) together would not fit in 80 GB of GPU memory at all.
- The system is **single-machine**. No distributed inference, no cross-host routing, no NIC bottleneck. The whole orchestrator stack — routing, escalation, embedders, OCR, retrieval — lives on one box.
- We can run the whole research-and-production loop on the same hardware. AutoPilot continuously tunes the production stack overnight; the same machine runs benchmarks during the day. There's no separate "training cluster" or "eval cluster."

## What changed our minds

A few specific measurements moved the project from "let's see if this works" to "this is the right substrate":

| Year | Finding | Source |
|---|---|---|
| 2026-03 | 4×24t NUMA quartering = +290 % over 1×96t single-instance on `Qwen3-Coder-30B` | [Hardware Optimization](../topics/hardware-optimization.md) |
| 2026-04 | NPS4 + CCD-aware load balancing = +25 % aggregate over NPS1 on production stack | [Hardware Optimization](../topics/hardware-optimization.md) |
| 2026-04 | CPU2 AVX-512BW 8×8 Q8 kernel = +31.8 % single-thread decode | [Quantization](../topics/quantization.md) |
| 2026-05 | gemma-4-26B-A4B MTP swap = +36 % worker throughput, +18 pp tool_compliance | [MoE Optimization](../topics/moe-optimization.md), [Worker_general: 17 → 76 t/s](worker-general-story.md) |

The headline of the project isn't that CPU inference is faster than GPU. It isn't. The headline is that **CPU inference at this hardware tier is good enough that you can run a serious multi-model orchestrator on a single machine for less than the cost of a single H100** — and being on one machine simplifies the whole system architecture downstream.

## What's next on this thread

The follow-on stories are [Worker_general: 17 → 76 t/s](worker-general-story.md) (a specific instance of the optimization stack compounding), [The speculative decoding investigation](spec-decoding-investigation.md) (what we tried, what worked, what didn't), and [What we tried and ruled out](ruled-out.md) (including the L3-as-NUMA reversal that taught us not to trust elegant-sounding ideas without measuring).
