# R22-5 preserved source proposals — 2026-11-02

These patches preserve the exact unvalidated proposal commits on root main for review and recovery. They are not production code or evidence of a passing test.

- `kernel.patch`: experimental v10-based commit `8f26e4f3a46cb79a09ed796b82f16daed3ecda63`, also on kernel fork branch `codex/r22-5-boundary-proposal-20261102`.
- `research.patch`: research commit `fa620eaa32677745fafdb062ed133d3838941241`, also on research branch `codex/r22-5-boundary-proposal-20261102`.

Both claimed builds were stopped after their region owners reported live processes behind missing lock wrappers. No build or test completed; no interrupted binary establishes freshness. The explicit boundary gate covers six proposed families and refuses unmapped operations; universal coverage, CPU/GPU numerical validation, and integration remain open. Production kernels remain frozen. See `progress/2026-11/2026-11-02-r22-5-boundary-proposal.md` and INF-66 R22-5.
