# EXP-09 R7 completed descriptive screen

R7 finished on 2026-11-05 (rc=0). The original operator verdict is descriptive PASS under the declared rule: verified-quote mean accuracy exceeds control. This archive preserves that existing verdict rather than issuing a replacement. The stale completion alert was acknowledged on 2026-11-17.

The exact grid contains 96 native cells: 24 byte-pinned R3 controls and 72 R7 treatments. All answers parsed, maximum answer length was 500 tokens against the 1024-token cap, and all 24 planted mismatches were rejected. The R7 native preflight and pass_complete share execution ID `3cd36b60a388`, valid kernel linkage, and the unchanged control function. The original seed SHA-256 is `59b4358cfdb709bf3b14a0781803d6595080b3045c8c0133b830b3e836ba7266`.

| Arm (24 cells each) | Mean accuracy | Exact-ID macro recall | Refetch requests |
|---|---:|---:|---:|
| Current summary | 0.766333 | 0.125000 | 12 |
| Verified quotes | 0.820417 | 0.679625 | 11 |
| Deterministic shape header | 0.979167 | 0.908333 | 7 |
| Pointer only | 0.260375 | 0.000000 | 24 |

Verified quotes improved the primary score by 0.054083, with 9 better, 10 tied and 5 worse pairs. Original 12 logs: control 0.782667, quotes 0.868083; added 12: control 0.750000, quotes 0.772750. Quotes were accepted in 21 cells and fell back in 3, retained in the primary denominator. The deterministic header had the highest descriptive score; this screen does not establish its production suitability.

The primary scorer uses substring matching against a reference capped at ten failed IDs. Exact-ID recall is a separate report-only companion. Cases are nonrepresentative and correlated: 21 provenance groups overall, nine among the added logs, with overlapping capped reference IDs, an intentional negative control and one log above the pilot length bound. Reused pilot cases are not independent confirmation. Full per-group and per-arm figures are in [analysis.json](analysis.json).

R3 control execution `f31565b84cc2` used CPUs 0–23; R7 treatments used CPUs 24–47 on the following day. Spill pointers also have different scratch roots. This is a split-execution descriptive comparison, with no served-latency, significance, promotion or production activation claim. Parent TOC-SP-3 remains open for implementation and its broader contrastive evaluation. The existing belief-source enrollment is VB-EXP09-SPILL-WRITE; this archive does not invent a measurement warrant for the historical run.

Native records are under [out/](out/); [verdict.json](verdict.json) is the original operator filing, and [published-manifest.json](published-manifest.json) contains the declared decision rule. [SHA256SUMS](SHA256SUMS) binds the archived bytes.
