# LSA combined CPU numerics — 2026-11-04

The model-free unit and frozen random projection fixture completed in order with direct-run rc=0. `projection-count.txt` and the original projection log record **KEY_MISMATCH count=0, max_bf16_steps=0**. The fixture separately allows up to one BF16 step; the measured strict count is zero. Query and key maximum absolute error were zero; coupled selected-index order and selected attention output were exact at positions 0, 4096 and 5120.

This is one frozen synthetic fixture, not model quality, MI210 validation or a latency claim. The original records, source and binary digest manifests, disassembly, linkage and admission records are preserved verbatim. Paths embedded in the original records identify their execution locations; binaries themselves are not copied. `SHA256SUMS` binds the archived evidence bytes.

The original disassembly is preserved losslessly as `disassembly.txt.gz`; `disassembly-original.sha256` records the uncompressed digest.
