# 2026-11-21 autokernel

## Wrap-up 10 (00:00Z-03:30Z)

### Headline: V5I makes the SERVED 27B+DFlash2 9.95% faster at noise-floor numerics
- `ak-v5i-27b-dflash2-e2e-gpu-20261121` KEEP: tok/s +9.95% [1.078, 1.121], 4 pairs, acceptance unchanged, oracle 0/96.
- `ak-v5i-27b-kld-gpu-20261121` PASS: KLD 0.000387 (X/X 0.000338), dPPL +0.17%, top-1 99.118% = X/X. Box V5I-SERVED-27B ticked (pipeline) + receipt-ack. C17 fold candidate.

### What cracked it
| Lever | Evidence | Effect |
|---|---|---|
| Stage-contiguous in-place weight repack | 0689c70ee | +13-26% op bandwidth |
| Q8MF V5 kernel: 4 WG/CU at 118 VGPR, half-tile units, atomic tail, nontemporal (slc) loads | fork 1778cda76, boxes 1ad781e58/568f36302 | flat cost n1-16 (27B 34.3/37.8/40.0/41.7 ms at p1/8/12/16) |
| V6 3-stage prefetch (128 VGPR) | 4180a4b8a | NO_GAIN: prefetch depth is not the limiter |
| Packed consumers | 60c2d7397 | packed prefill convert fold-ready (p512 0.999x X); packed n1 MMVQ slower -> MMVQ_MAX=0 default |
Bandwidth: stream ceiling 1498 GB/s (MI210 peak 1.6 TB/s); best op V5I-slc 1205 GB/s = 80% of stream.

### Trees
- DTREE-ROUND-OVERHEAD (f3d9bc5a0, f468e6f57): extra per-round cost is state-save copies (GDN tree snapshot scatter 3.85 ms, conv per-column copies 3.3 ms), not verify GEMMs. Fixes 5916360ea + efaecfc5d: G12/L 0.920 -> 0.972 [0.949,0.994]. New box DTREE-ROUND-OVERHEAD-2 for the remaining ~4.5 ms.
- Greedy rows (fixed builder): 27B G12 mean len +16.4%, G16 +19.7%; measured tree acceptance 27B +5.8% at T12, +11% at T16. Round overhead is the blocker, not acceptance.

### Kernel and Q38FN levers
- H11-UNIQ FAIL(dup_ids) (96dec22d5): topk-moe fusion router emits duplicate ids on exact ties; new box AK-ASM-H11-UNIQ-FIX, fix in flight.
- DRAFT-HEAD-APPROX-RECALL r2q0 PASS (630e1275d) with faithful-arithmetic recompute (e06dcc3c9); DRAFT-HEAD-SVD-CPU built (b5d6a32a6), row r2q0 queued.
- LSA-CPU e2e build + tests PASS; row lsa-cpu-sparse-e2e-20261121-r1 queued.
- chainverify r3 (V5I) KEEP: 27B MF/OFF M4 0.788 [0.780,0.796] (r2 had silently run V3I).
- sclk-detm FAIL (5b4bb6ace, fixed clock -8.1% pp2048); sclk-energy NO_WIN (45d903ef8).
- H15 np2 fallback cheap (4ebce70c7, +0.49%); AK-GAP-1 step1 PASS (0a3c03958).

### Pipeline / keeper fixes
any-of region granting, pid-based waiters, rowflow release verb (466e6b97a), q3 build pocket.

### Process lessons
- 4 GPU rows silently failed smoke and never queued -> smoke-FAIL watcher (watch FAIL-*.json, not only .ended).
- Job stderr is tail-truncated: witness lines lost; templates must keep the first 4 KB too.
- A subagent claimed chainverify-r2 ran V5; job.py said MF=3 (V3I). Verify on disk, never on report.

### Boxes
Ticked this wrap-up: AKX-ALL-31.QDEC-CPU-MULMAT. Receipt-acks: V5I-SERVED-27B, DTREE-ROUND-OVERHEAD. Filed: AK-ASM-H11-UNIQ-FIX, DTREE-ROUND-OVERHEAD-2.
