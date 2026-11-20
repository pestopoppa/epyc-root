---
schema: epyc.brief.v1
id: LOOP-72
box_text_sha: 88e9be3cfdb37bd7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-root:research/refactor-audit-2026-10/findings-orchestrator-core.md
- epyc-orchestrator:src/backends/llama_server.py
- epyc-orchestrator:src/llm_primitives/inference.py
approach: 'O1 stage B (backend failure semantics and streaming stop): A2-02 (four near-duplicate lanes in llama_server.py
  each build payload/timeout/parsing/stats/InferenceResult), A2-M1, A2-M2, A2-03, A2-05, A2-11, A2-16. Requires stage A (LOOP-65)
  merged. Step: cross-lane contract tests first (A2-22 owns them in D3), then fix failure semantics per finding, one finding
  per commit with a failing-then-passing test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_llama_server.py
non_goals:
- no lane de-duplication (D3)
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-root:research/refactor-audit-2026-10/findings-orchestrator-core.md: fd6ea64e7ff4e54dd56dd195c78a9977771eb91d
    epyc-orchestrator:src/backends/llama_server.py: 944dc58f251001af0044976dcc07484efdd45b6f
    epyc-orchestrator:src/llm_primitives/inference.py: 95df5e5fe8b106f53d2d32ab0a13f7d2085f96f2
---
