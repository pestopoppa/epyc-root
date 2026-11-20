---
schema: epyc.brief.v1
id: GGUF-RECIPE-SCORER
box_text_sha: 4a0365a23a4c7d64
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/answer_scoring.py
- epyc-llama:tools/perplexity/perplexity.cpp
approach: 'New scorer scripts/benchmark/gguf_recipe_scorer.py: per candidate tensor-type map + imatrix, run llama-quantize
  --dry-run and reject over-budget bytes, quantize, run llama-perplexity --kl-divergence on held-out text, parse same-top-p/KLD/EAR
  from its log, attach the QUANT-LOOPCHK-1 counter, emit one JSON row. Unit tests cover budget rejection and the log parser;
  the small-model end-to-end run is a separate operational step.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/benchmark/test_gguf_recipe_scorer.py
new_tests:
- epyc-inference-research:scripts/benchmark/test_gguf_recipe_scorer.py
non_goals:
- no compute inside the unit tests
- no search loop (that is GGUF-RECIPE-SEARCH)
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/answer_scoring.py: bb1e0fe958e16a945df56dc373cdfa7dfb1a1f90
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
---
