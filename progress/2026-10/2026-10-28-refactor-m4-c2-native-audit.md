# 2026-10-28 — M4 recut C2 native audit checkpoint

Completed the bounded M4 recut C2 control audit and filed its result in `handoffs/active/gpu-serving-tie-in-program.md` under `M4.2b-C2-RECUT`.

The native packet at `/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-c2-off-ratio-v2/output/` records four fresh loads in C5/M4/C5/M4 order and 48 valid planned A/B/C rows. `VERDICT.json` is PASS: paired geometric mean `1.000852875330362`, with adjacent overlapping-pair ratios `1.0005335341140928`, `1.001920818321776`, and `1.0001051733023467`. The predeclared M4.2b band is `[0.9, 1.1]`; the overlapping pairs are not independent repeats and no historical absolute 22.05 comparison gates this result.

Per-load native summaries and proof logs record source linkage, graphs ON, `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0`, own-PID VRAM 46.606 GiB (47.357 GiB observed peak), and verified server teardown. Source and model digests were pinned before load; the large GGUF files were not independently rehashed. Verdict SHA-256 is `f96f1e3788ce6d57e53eea5606f72fe0981f9cf721454245534c6e0066200885`; predeclaration SHA-256 is `98887738830d3ec534bd850b016ae58a268700be10c2900c641dbb33100cf5bf`.

This closes only the recut candidate's C2 relative control. It does not establish off-path byte identity, the full M4 measurement, quality, or production/fold readiness; the parent M4 and production gates remain open. The existing native source adapter extension and planning canary remain open under `VB-M4-C5-OFF-C2-WIRE`; no measurement ingest was run. [belief: cc]
