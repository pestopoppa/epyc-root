---
schema: epyc.brief.v1
id: REPL-EMB-R3
box_text_sha: daeeeb52c12497a0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:orchestration/repl_memory/lightweight_gat.py
- epyc-orchestrator:src/embedding_dims.py
approach: 'Make LightweightGAT input_dim derive from src.embedding_dims (not 1024), add a stored-dim check in load() so mismatched
  weights are refused, then a first training on EG2 vectors. First step (code, zero inference): the derive + load check with
  a unit test; training after R2 dataset exists.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_lightweight_gat_dim_check.py
new_tests:
- tests/unit/test_lightweight_gat_dim_check.py
non_goals:
- no training in the first step
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:orchestration/repl_memory/lightweight_gat.py: 674d649e27167c3ee8d52ce9bdf0e2ea7a0d5e17
    epyc-orchestrator:src/embedding_dims.py: f46c27a24ee2b7954b3be576fb78a48e744190c6
---
