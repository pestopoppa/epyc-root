---
schema: epyc.brief.v1
id: REPL-EMB-R4
box_text_sha: 2b6104ad8c832087
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:orchestration/repl_memory/routing_graph.py
- epyc-orchestrator:scripts/graph_router/train_graph_router.py
- epyc-orchestrator:src/embedding_dims.py
approach: 'Three node tables use DOUBLE[1024]; CREATE IF NOT EXISTS will not alter them. Establish by a small test against
  the real engine (Kuzu/DuckDB) whether ALTER on an array type works; if not, drop/recreate and repopulate via train_graph_router.py,
  taking the dimension from src.embedding_dims. First step: the engine ALTER test and a dimension-from-config change in routing_graph.py.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_routing_graph_dim.py
new_tests:
- tests/unit/test_routing_graph_dim.py
non_goals:
- no live graph migration
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:orchestration/repl_memory/routing_graph.py: 1df5363119e45fc24542d6b09bcbca15ece072f6
    epyc-orchestrator:scripts/graph_router/train_graph_router.py: 2ae5463329111ad5ee3059800492efe0d7ab926b
    epyc-orchestrator:src/embedding_dims.py: f46c27a24ee2b7954b3be576fb78a48e744190c6
---
