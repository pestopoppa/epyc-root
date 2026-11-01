# REPL-EMB-5.1 SEARCH primitive — 2026-11-01

The orchestrator implementation was published to `main` as `eb77f45cfb52791c031bf38dce13c66cc03f18af`; the implementation commit is `303a3b2d136c20eeabf6349302f0f64705dda582`. Its exact source files are `src/scout_search.py` and `tests/unit/test_scout_search.py`.

`ScoutSearch` delegates to an already constructed `ContextSearchIndex` or `ContextBundle`; it does not build an index or resolve an embedding backend. It preserves the existing pointer result shape, bounds query/result sizes, validates pointer ranges and the existing `bm25`/`dense` plus `hybrid`/`lexical`/`lexical_fallback:<reason>` vocabulary, and reports missing/unknown search mode evidence explicitly. The parser/facade is ready for the INF-78 owner to wire into the scout command loop.

## Verification

- `tests/unit/test_scout_search.py` plus existing `tests/unit/test_ufh12_context_search.py`: **48 passed** in 2.10 s.
- R6 wrapper ran on CPUs 130–131 (physical 34–35), with OMP=1, the 34–35 prep mutex, sampled peak process-tree RSS 162,820,096 bytes, and a 900 s time cap. Receipt and captured test log are in `receipts/` and `logs/`.
- Isolated Ruff check on the two source files passed; `git diff --check` passed.
- This was offline correctness verification. No model, inference, network retrieval, runtime flag, deployment, scout wiring, or retrieval-quality claim is included.

[no-belief: source contract and deterministic correctness controls only; no measurement or adoption claim]
