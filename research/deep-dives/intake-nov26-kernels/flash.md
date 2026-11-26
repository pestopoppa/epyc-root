# FlashInfer v0.7.6

Version v0.7.6 tag object 8fe80f70f073dd080139f044fb62f6ef3ec0a853 resolves to ebf047a43bf84a2d0a635d25c697b51f4addded9. Release reports batch-invariant KDA/GDN and sampling by seed+offset and MoE on SM100/103/107; caller-owned Mamba2 state pool; selective cuDNN prefill on Hopper/Blackwell; SM107 die-local MoE and SM100/103 sparse NVFP4 KV. Highlights supply feature scope without EPYC metrics.

[Primary source](https://github.com/flashinfer-ai/flashinfer/releases/tag/v0.7.6)

## Evidence checked

- FlashInfer v0.7.6 reports position-independent token draws for the named samplers in batch-invariant mode, keyed by per-row seed and offset, on SM100, SM103 and SM107. (Release highlights, batch-invariant mode).
- FlashInfer v0.7.6 Mamba2 prefill with the Cake backend reads and writes a caller-owned state pool indexed by slot on SM100, SM103 and SM107. (Release highlights, linear attention and Mamba2).
- FlashInfer v0.7.6 documents cuDNN auto-dispatch for qualifying long paged prefills on Blackwell and H100. (Release highlights, paged prefill).

## EPYC applicability

Portable interface and test ideas apply to MI210/Zen5. SM107 locality, cuDNN, NVFP4 and CUDA graph implementations are architecture-specific; gfx90a equivalents need separate layout and performance design.

handoffs/active/kv-cache-program.md:797 demonstrates the local state isolation concern; no package upgrade is needed for these patterns. (EPYC root a660ead17).

## Counterevidence and limits

Searched FlashInfer v0.7.6 AMD/ROCm and supported architecture README. The README and highlights specify NVIDIA SM targets for cited features; no direct AMD implementation or performance evidence was found.

## Derived action for review

Review the target sampler RNG cursor lifecycle for stable per-request coordinates under permutations, batch resize and slot recycle; borrow a small backend-neutral metamorphic fixture if current tests lack it. Treat state slots as a related pattern for existing restore ownership.

handoffs/active/speculative-decoding.md and handoffs/active/kv-cache-program.md

## Sources surfaced

https://github.com/flashinfer-ai/flashinfer/pull/9365 and https://github.com/flashinfer-ai/flashinfer/pull/9619 for RNG implementation, and https://github.com/flashinfer-ai/flashinfer/pull/9644 only for the pool design.
