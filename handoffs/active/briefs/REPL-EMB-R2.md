---
schema: epyc.brief.v1
id: REPL-EMB-R2
box_text_sha: 4b4042305088a25e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/graph_router/embed_soft_label_dataset.py
- epyc-orchestrator:scripts/graph_router/train_graph_router.py
- epyc-orchestrator:src/embedding_dims.py
approach: 'Rebuild soft_labels_embedded.npz, training_data.npz (526,661 x 1031) and offline_reward_verifier_data at 256+7
  (derive dim from src.embedding_dims, relax the !=1024 guard accordingly), retrain routing_classifier*, verifier_head, offline_reward
  verifiers via train_graph_router.py, recalibrate (precision 0.9, classifier_confidence 0.8, verifier 0.5). Accept: routing
  accuracy on the frozen eval not below the BGE models. First step: dimension-parametrize the dataset builder with a unit
  test. Flags default OFF so nothing live depends.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_embed_soft_label_dims.py
new_tests:
- tests/unit/test_embed_soft_label_dims.py
non_goals:
- no live routing change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/graph_router/embed_soft_label_dataset.py: 798d9779494f70e235e3147dbea3e9a278d4686c
    epyc-orchestrator:scripts/graph_router/train_graph_router.py: 2ae5463329111ad5ee3059800492efe0d7ab926b
    epyc-orchestrator:src/embedding_dims.py: f46c27a24ee2b7954b3be576fb78a48e744190c6
---
