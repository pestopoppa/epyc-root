# 2026-10-21 dpf-logpfx (DP-F non-inference lane)

- RTE-LOG-1 (open): `blocks[]` on dispatch and serving records (`src/backends/prompt_layout.py`), reader `scripts/analysis/prompt_layout_reader.py`, format doc; producer gaps and live check listed as sub-items.
- RTE-CORPUS-1 (open): corpus flag-off fast path in `build_corpus_context`; operator ratifier pending.
- REPL-EMB-6.1, M-28, B7-LOG-1, RTE-PFX-1, CF-AB-3 (blocked record), TOC-SP-10, TOC-SP-11 ticked with notes. RTE-PFX-3 filed (move `Turn N` out of the state block head).
- Evidence: `artifacts/dpf-logpfx/`. Tests: 282 passed across the seven touched orchestrator test files (region-lock q2); 5 passed in `tests/analysis/test_cf_ab3_prefix_replay.py`.
