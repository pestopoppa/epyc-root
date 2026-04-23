# Deep Dive: Hazy Research Megakernel — Single-Dispatch LLM Inference

**Date**: 2026-04-23
**Intake**: intake-448 (hazyresearch.stanford.edu/blog/2025-05-27-no-bubbles)
**Related intake**: intake-447 (Lucebox, applied port of this methodology)
**Question**: Is the megakernel pattern a useful design primitive for our future GPU inference path, and does any of it map back to CPU?

## Executive Summary

**Foundational methodology for any future GPU inference engine we build; no CPU carryover.** The megakernel pattern is a GPU-specific answer to a GPU-specific problem (kernel launch overhead + memory pipeline bubbles between ops). CPU inference does not have this problem in the same form — our overheads are elsewhere (NUMA crossings, dequant cost, sequential SSM recurrence).

**The reason to care now is downstream, not direct.** Lucebox (intake-447) is the first open port of this pattern to a hybrid SSM model (Qwen3.5-0.8B). Log-Linear GDN (`log-linear-gated-deltanet-readiness.md`) and any future DGX Spark / Blackwell work would touch the same primitives. Reading this paper once is prerequisite for any serious GPU engine design conversation.

**Results that matter for our roofline thinking:**
- 78% memory-bandwidth utilization on H100 (vs ~50% for vLLM/SGLang)
- Sub-1 ms forward pass for Llama-1B on H100
- 1.5–2.5× vs vLLM, 1.5× vs SGLang

The key insight is not the numbers — it's the diagnosis that production inference engines leave ~50% of GPU bandwidth on the floor due to kernel fragmentation. That's a large untapped slice; Lucebox shows it generalizes beyond dense-attention Llama-1B.

## Technique Analysis

### The Core Problem

Standard LLM inference on GPU runs ~100 separate kernels per forward pass: RMSNorm, QKV projection, RoPE, attention, output projection, MLP up/gate, SwiGLU, MLP down, etc. Each kernel:
- Has a setup cost (grid launch, register/shared-memory allocation).
- Cannot overlap its memory loads with the previous kernel's memory stores.
- Synchronizes the entire grid at its boundary.

On H100 this wastes roughly half of achievable memory bandwidth. Most of the wasted time is the memory pipeline stalling during kernel transitions — weights for the next op are not being prefetched while the current op is finishing.

### The Megakernel Solution

Collapse all ops into a single CUDA kernel with an on-GPU interpreter. Each streaming multiprocessor (SM) receives a pre-scheduled instruction sequence and executes it without ever returning to the host. Key components:

| Mechanism | Purpose |
|-----------|--------|
| On-GPU interpreter per SM | Executes instruction sequence without kernel boundaries |
| Pre-scheduled instructions | Compiled once on Python side, reused across many forward passes |
| Shared-memory pagination (213 kB / 13 pages) | Explicit request/release semantics to keep SRAM-resident state coherent |
| Counter-based global synchronization | Track instruction dependencies without grid-level barriers |
| Fine-grained chunked processing | Start dependent instructions before predecessors fully complete |

The result is pipeline-level overlap between what would otherwise be separate kernels: weight loads for op N+1 overlap with compute for op N; no grid-wide sync barrier between them.

### Reported Results

| Hardware | Model | Forward pass | Memory BW | vs vLLM | vs SGLang |
|---|---|---|---|---|---|
| H100 | Llama-1B | <1 ms | 78% | 2.5× | 1.5× |
| B200 | Llama-1B | ~680 µs | (not stated) | 3.5× | — |

These are single-user, batch-1 numbers. The methodology is specifically tuned for low-latency local inference, not throughput-oriented serving.

### Extended / Follow-On Work

- **ThunderMLA** (Hazy Research, 2025-03-04): FlashMLA fused kernel, precursor to the full megakernel pattern. (Candidate for future intake expansion.)
- **Mirage Persistent Kernel (MPK)** (arXiv:2512.22219): A compiler that automates mega-kernelization for arbitrary PyTorch models. Reports 1.0–1.7× over SGLang/vLLM on A100/H100/B200. (Candidate for future intake expansion — much more directly portable than hand-written megakernels.)
- **Lucebox Megakernel** (intake-447): First open port of the pattern to a hybrid SSM model (Qwen3.5-0.8B), on consumer RTX 3090. 1.55× over llama.cpp BF16, 30% less power.

## Cross-Reference to EPYC Stack

### What this DOESN'T change for CPU inference

- **No CPU kernel-fragmentation bottleneck in the same form.** ggml's CPU backend dispatches through a graph, not via kernel launches with grid-sync overhead. Our overheads are: NUMA memory accesses (cross-socket penalty), Q4_K_M dequant cost per token, and — the big one for hybrid — DeltaNet's sequential state recurrence. None of these are addressed by the megakernel pattern.
- **No new CPU optimization to implement.** The closest CPU-analog work is `llama-cpp-kernel-push-rebase.md` (operator fusion, kernel-level throughput). Note: TIDE calibration-router early exit — previously the best 27B-dense-hybrid candidate at 1.76× — was deprecated 2026-04-23 after projection quality could not be solved with either linear or bottleneck-adapter approaches. That line of CPU recovery is closed.

### What this DOES change for future planning

1. **Establishes the GPU roofline target realistically.** 78% memory bandwidth utilization is the achievable ceiling on a modern NVIDIA GPU with this pattern. Anything we design for DGX Spark should be benchmarked against this ceiling — not against vLLM's ~50% baseline.
2. **Log-Linear GDN context.** `log-linear-gated-deltanet-readiness.md` tracks Qwen4/Qwen3.5 hybrids with parallel-scan-friendly state. If that architecture ships, the megakernel pattern is the natural inference primitive to combine with it: one kernel, all layers, with parallel-scan for the linear-attention state. This is the combination that would re-open speculative decoding for hybrids on GPU (and, speculatively, on a sufficiently fast CPU).
3. **Blackwell / DGX Spark engine choices.** If we ever build our own GPU engine (unlikely but possible), this is the pattern. Otherwise the decision becomes: use vLLM (50% of bandwidth, but fully maintained), use Mirage (70–90% of bandwidth, auto-compiled, less mature), or use hand-written megakernels (Lucebox-style, highest perf, most maintenance).
4. **Benchmark discipline.** Any time we look at a GPU inference benchmark and the achieved tok/s divided by bandwidth/model-size is ≤ 0.5, we know there's another 2× on the table by switching engines. That's a diagnostic heuristic we didn't have before.

### What's genuinely unportable to CPU

- **SM-level interpreters.** CPUs don't have the SIMT scheduling abstraction that makes pre-scheduled instruction sequences per SM a win. Modern CPUs already execute instruction streams efficiently.
- **Shared-memory pagination.** Our NUMA-per-socket cache hierarchy is a different animal; the analogous optimization (L3 cache blocking) is already what ggml does via tile sizing.
- **Counter-based global sync.** Thread barriers on CPU are essentially free compared to global-memory atomics on GPU; there's no analogous overhead to remove.

## Adoption Posture

| Trigger | Action |
|--------|--------|
| **Now** | Read as design primer. Cite in `gpu-acceleration-path.md` as the roofline reference. No code work. |
| **Log-Linear GDN model available** | Re-read alongside `log-linear-gated-deltanet-readiness.md` — this pattern + parallel-scan SSM is the natural combination. |
| **DGX Spark acquired** | Evaluate three GPU-engine options: vLLM (safe baseline), Mirage Persistent Kernel (auto-compile path, lower maintenance), hand-written megakernel (Lucebox-style, highest perf, highest maintenance). Default should be vLLM unless latency requirements force otherwise. |
| **Mirage Persistent Kernel gains traction** | Intake MPK as a separate entry; it's the practically-usable form of this pattern for arbitrary models. |

## Risks and Caveats

1. **Batch=1, latency-oriented.** Megakernel benefits are largest for single-user low-latency decode. Throughput-oriented multi-user serving is already well-optimized by vLLM/SGLang continuous batching; the megakernel gap there is smaller.
2. **Compilation overhead.** Pre-scheduling instruction sequences is a static compile step. For models that change shape (variable context lengths, MoE expert routing) the compile/recompile cost may offset runtime savings. Lucebox reports batch=1 only — this is likely why.
3. **Maintenance cost.** A hand-tuned megakernel per model is O(model × hardware-generation) effort. Hazy Research's Llama-1B kernel does not port to Qwen3.5-27B without substantial rework; Lucebox's Qwen3.5-0.8B kernel does not port to Qwen3.5-27B (different layer count, ratio, state sizes).
4. **MPK as the pragmatic path.** If we care about megakernel-class perf without megakernel-class maintenance, Mirage Persistent Kernel (compiler-generated) is the right target. The raw Hazy Research work is the reference implementation to study, not to ship.

## Open Questions

- Does Mirage Persistent Kernel (arXiv:2512.22219) reach the same 78% bandwidth utilization as hand-written megakernels, or is there a meaningful gap? (Intake it to find out.)
- How does megakernel perf scale with model size? Llama-1B fits in a working set that favors the pattern; does a 27B model with 15 GB weights still benefit at the same ratio, or does the pattern degrade when the working set doesn't fit in shared memory?
- Is there a CPU analog of the diagnosis — i.e., a measurable "bandwidth utilization gap" on our EPYC stack that would indicate a structural optimization we've missed? (Action: measure effective DDR5 BW on Qwen3.6-27B decode and compare to 460 GB/s theoretical peak.)

## References

- Primary: https://hazyresearch.stanford.edu/blog/2025-05-27-no-bubbles
- Code: https://github.com/HazyResearch/Megakernels
- Applied port: Lucebox (intake-447), `research/deep-dives/lucebox-hub-consumer-gpu-dflash.md`
- Related: ThunderMLA (Hazy, 2025-03-04); Mirage Persistent Kernel (arXiv:2512.22219) — both candidates for future intake expansion
- Related handoffs: `gpu-acceleration-path.md`, `log-linear-gated-deltanet-readiness.md`
