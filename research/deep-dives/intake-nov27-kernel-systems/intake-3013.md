# One Token, Many Lessons: Sliding-Window Attention within Gated Delta Networks

[Primary source](https://arxiv.org/abs/2611.33257v1) · intake-3013 · 2026-11-27

SWGDN substitutes width-4 causal attention for depthwise short convolution in Q/K/V projections; every branch and group has a learned fixed pseudo-query (RMS norm, relative RoPE) that scores the same projected pre-mix keys, softmax-weighting that group’s payload. Recurrence and chunking algorithms are preserved. Seven ~340M GDN2/KDA models share ~15B FineWeb-Edu tokens and 2048 sequence length. Table 4 SWKDA-G1 changes LAMBADA perplexity 28.8534→27.2252 and mean downstream accuracy 45.62→46.11. Table 5 across 14 RULER settings the baseline and strongest SW groups change 35.0→43.9 (GDN2→G64) and 38.8→43.6 (KDA→G1), with regressions in individual tests; Table 6 Q/A recall differs by grouping. Table 3 and Appendix E distinguish similar K/V pairs from stronger writes: layer 9 first-write anchor residual reduction rates are 51.2→62.5% for KDA→SWKDA-G1 and 38.7→30.9% for GDN2→SWGDN2-G1; in a separate SWKDA-G1 intervention at layer 9, removing later source contributions changes a 65.64% rate to 37.81%, while decay-inclusive residual still grows across the window. First evidence-token NLL shift spans zero for layer-9 SWKDA-G1. Table 7 at 4K reports GDN2→SWGDN2-G1 prefill plus equal-length cached decode 92.005→80.888s (−12.1%) and KDA→SWKDA-G1 78.871→66.919s; single RTX 6000D, batch 1, FP32 weights with BF16 autocast. Scope corrections: architecture and retraining, backbone-specific residual behavior, no CPU/gfx90a/throughput-at-concurrency evidence. A bounded exact-source search found no independent reproduction; DynamicConv is a control with published gains at other scales, and its weaker SWGDN paper result does not settle the broader comparison.

Read methods and controls (§3–5), Tables 1–7, Appendix C pseudo-query/DynamicConv comparison and Appendix E intervention. Skimmed conclusion/related work; background derivations, detailed Appendix B training and full Appendix D tables and references not read.

## Evidence

- The learned Q/K/V mixer preserves the original recurrence and chunkwise parallel algorithm in the two tested backbones. [§3.1, last paragraph (#S3.SS1)](https://arxiv.org/html/2611.33257v1)
- On a single RTX 6000D at batch 1, SWGDN2-G1 reduced total prefill plus equal-length cached decode latency at 4K by 12.1% against GDN2. [§5, inference efficiency (#S5.SS0.SSS0.Px6)](https://arxiv.org/html/2611.33257v1)

## Scope and local transfer



Current GDNPROJ_FUSE/GATED_DELTA_NET paths in kernel-champion-and-promotion.md are a relevant cost/diagnostic baseline. A tiny trained paired checkpoint and width-4 mixer could support a reference parity and recurrent mixer cost screen. CPU per-token extra local math plus state traffic matters at batch 1; gfx90a compare fusion and batching with projected-key/payload ring state. Use experimental paths and matching-weight baselines. Existing checkpoints lack these learned pseudo-query weights.

Existing GDN fusion and KDA exponential work measure recurrence or state movement; substituting a trained mixer changes the model. When a qualified checkpoint contains sliding-window q/k/v mixing, trace window KV/cache traffic separately from recurrence on both backends and compare matched quality/latency.

## Sources surfaced

- https://arxiv.org/abs/2606.03825 — Dynamic Short Convolutions Improve Transformers is the direct comparator and has broader-scale and public kernel evidence. Exact ID absent in lane index.
