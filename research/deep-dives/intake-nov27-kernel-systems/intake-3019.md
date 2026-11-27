# FlyingStart: Learned Cross-Token Warm Starts for Fixed-Point Decoding in Recurrent-Depth Language Models

[Primary source](https://arxiv.org/abs/2611.34492v1) · intake-3019 · 2026-11-27

Frozen recurrent model’s current prelude and previous token’s exit state predict a starting state using an affine ridge map calibrated at full-depth. Same core and state-change stopping condition, terminal KV per token, 2h² map weights and no additional KV; the <5% of a loop cost is author-reported. Huginn-0125 on 5,078 pooled math items: at ε=.085, 40.1 vs 46.8 layers/token, 14% reduction; up to 18.9% along interpolated matched-accuracy frontier. A strict 1 pp confidence-bound selection was inconclusive at its preset fallback rule (baseline 29% fallback). Constant-rate contraction and certificate are conditional on fixed context and convergence; finite cutoffs, quantization and changing prefix caches do not guarantee bit-identical outputs. TinyLlama predicted ~0.71 loops; rapid-convergence retrofits save ~0.6–0.9 loops and mostly help at tight budgets, and zero-shot math/code at the same threshold does not establish matched best frontier. H100 batch 128 synchronous fixed 12→10 loops yields 997→1,155 tok/s. RTX 6000 Ada CDB 533→628 (~18%) uses replay of 1,500 ShareGPT exit trajectories; adaptive CDB same threshold +4–5%, not 18%. RTX 3090 GSM8K/WaveFront batch one +10% with full-depth verification and +14% with adaptive exit at reported paired task accuracies. Spec-Bench full-depth verification +4% failed preset +5% threshold; adaptive +24%. Copy-only previous state no better than random, low-rank map/rank-32 under-delivers, and parallel prefill cannot use previous-token map term. Ouro-like non-convergent models are outside the demonstrated regime.

Read §§2–7, Limitations, Appendix A/B selected details, Tables 2/3/9/12/15/16 and relevant figure captions. Other appendix tables and bibliography not read.

## Evidence

- Huginn operating point uses 40.1 vs 46.8 layers/token on pooled math. [§4.2 operating point](https://arxiv.org/html/2611.34492v1)
- CDB served with replayed exit trajectories for the stated throughput comparison. [§4.4 CDB paragraph](https://arxiv.org/html/2611.34492v1)
- Method requires a start-independent attracting fixed point. [Limitations](https://arxiv.org/html/2611.34492v1)

## Scope and local transfer

18% CDB gain is trajectory replay with fixed loop count; adaptive serving +4–5%. Fixed-point guarantee is conditional and finite decode has empirical accuracy, not bit-exact output. Savings apply only to recurrent models with measured contraction and sufficient loops; changing the loop initialization is different from changing the stopping rule.

EPYC 9655: measure whether avoided recurrent-core weight streams exceed added dense predictor traffic plus terminal KV; first contraction and same-output/quality curves on a supported Huginn-like model and held-out prompts, fp/unquantized vs realistic quantized backend. MI210: BF16/HIP predictor matvec or batching is plausible at 3.5B and 64GB HBM, but test batch 1 and throughput-concurrency/long-context at matched accuracy, with real serving throughputs and KV/state bytes. Keep fixed depth, adaptive baseline, and warm-start arms; do not wire production until recurrent serving and qualifying model exist. Lane context-and-token-economy.md:2598–2605 contains Huginn lineage; it is prerequisite context, no EPYC warm-start speed warrant.

The existing DFlash2 target/drafter interface has no interchangeable fixed-point latent; layer savings depend on stability of a shared recurrent block. Reopen when a qualified recurrent-depth model exposes latent-state initialization and adaptive exit. Compare loops, wall time, quality and acceptance at fixed effort on CPU and MI210 separately.

## Sources surfaced

- https://arxiv.org/abs/2610.06833 — Rethinking at Fixed Points is a primary comparator for terminal KV and learned endpoint prediction under different training/caching conditions.
- https://arxiv.org/abs/2608.09444 — Continuous Depth Batching methodology and independent scheduling measurements, not warm-start replication.
- https://arxiv.org/abs/2609.23033 — WaveFront implementation baseline for the speculative combination.
