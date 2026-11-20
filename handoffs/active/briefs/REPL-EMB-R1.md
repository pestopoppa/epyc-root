---
schema: epyc.brief.v1
id: REPL-EMB-R1
box_text_sha: a0c15e92d7f62e4f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/graph_router/irt_scorer.py
- epyc-orchestrator:scripts/calibration/build_irt_prompt_embeddings.py
- epyc-orchestrator:src/embedding_dims.py
approach: 'Retrain the IRT ridge on EG2@256 prompt embeddings (side=document) and accept on held-out IRT Spearman not below
  the BGE fit on BOTH difficulty and discrimination (n=102, higher better). Last native result failed (difficulty 0.145 vs
  0.175); successor CPU row codex-ufh12-r1-irt-v3-20261101 awaits keeper dry-run. First step: file the successor''s native
  result and decision; if it fails again, decide RETIRE for this consumer. Dimension guard must refuse 256-d input until MIGRATED.

  '
acceptance: python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py --owner codex | grep -q
  'codex-ufh12-r1-irt-v3-20261101.*COMPLETE'
non_goals:
- no production swap
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/graph_router/irt_scorer.py: ae3437430b673b0181b384f58aca06a6e2e05601
    epyc-orchestrator:scripts/calibration/build_irt_prompt_embeddings.py: f1c156e21a84d13d24536f173f74faee451d9001
    epyc-orchestrator:src/embedding_dims.py: f46c27a24ee2b7954b3be576fb78a48e744190c6
---
