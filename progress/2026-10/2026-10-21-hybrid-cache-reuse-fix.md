# 2026-10-21 hybrid-cache-reuse-fix

- Bug: recurrent `get_can_shift()` returned true and hybrid(-iswa) returned the attention answer only, so the server kept `--cache-reuse` / ctx_shift on hybrid and recurrent models (stale recurrent state after KV shift).
- Fix: `experimental/hybrid-cache-reuse-guard-20261021` @ `8b08c9f25` on fork (recurrent false; hybrid and hybrid-iswa AND both parts). Test `tests/test-memory-can-shift.cpp`, server test `unit/test_cache_reuse_recurrent.py`.
- Evidence: can_shift=0 on Qwen3.5-0.8B, LFM2.5-1.2B and 6 generated recurrent/hybrid archs, 1 on dense; server warns "cache_reuse is not supported by this context" on both hybrids. Server pytest not run (build has no HTTPS); nemotron_h ctest not run (generator aborts at deepseek41).
- Behaviour change: `--context-shift` now disabled on hybrid/recurrent models.
- Manifest: V11-098 PEND, root main `4bbe082ee`. Folds at the next consolidation.
