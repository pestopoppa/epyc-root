# Hawkeye's MI350 comparison of Hipify and generated HIP

**Recorded:** 2026-10-07. **Scope:** source finding only; no local performance or production claim.

The existing intake record `intake-1218#05` reports a 0.05× geometric-mean performance ratio for Hipify's MI350 kernels against `torch.compile` across GEMM, Conv2D, and attention. It reports 1.26× for HAWKEYE against the same baseline on MI350. Dividing the displayed geometric means gives 25.2×; this is a ratio of rounded aggregate values, not a per-workload comparison or a causal estimate.

Table 3's indexed MI350 BF16 row gives relative throughput 0.75× for GEMM, 1.88× for Conv2D and 1.43× for attention. GEMM loses against the baseline; the aggregate does not establish per-workload superiority or a cause.

These are MI350/CDNA4 results, not MI210/gfx90a results, and they do not predict transfer to our hardware. They support including both direct HIP authoring and translation in a future controlled comparison; they do not establish local performance, readiness, or a universal ranking. The phrase “a group with no stake in our hand-port decision” is unsupported and is withdrawn. `intake-1226#record` records an implementation choice, not independent measured corroboration.

## Source identity and provenance

- Paper: [Hawkeye: Hardware-Aware GPU Kernel Optimization with Minimal Supervision](https://openreview.net/pdf/b635c08f50c0b6b899b8847fd4078ce6d74699ec.pdf), page 6, Table 3; Appendix A.2 for the Hipify aggregate.
- A cached PDF version is retained in the upstream source archive at `epyc-root/tmp/dive1219/Hawkeye`, commit `a226e955d56c04be044d46f6fd876191cfce5bf4`, path `docs/deep-research/00-hawkeye-neurips-2026/paper.pdf`, Git blob `9045be24fc9e7185abc2cc6414d44246a2796ba1`, SHA-256 `7f005167ea298bc660b0b628d223061721816583493c54daf93b2ac81ca31921` (437,346 bytes).
- The delegated source review verified the Table 3 values from OpenReview indexed text; MAIN independently verified the aggregate paragraph through the primary PDF search index. Live-index text was not byte-matched to the cached PDF. The retained local PDF byte stream did not yield a parseable text extraction in this review; no local-parser or authenticated OpenReview forum-access claim is made.
- Arithmetic only: the three displayed ratios have geometric mean about 1.264; the aggregate quotient uses rounded reported values.
