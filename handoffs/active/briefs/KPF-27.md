---
schema: epyc.brief.v1
id: KPF-27
box_text_sha: 3865a29b691e6d64
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/inference/prefix_index.py
approach: 'Revived prefix index (radix tree) orchestrator side behind ORCHESTRATOR_PREFIX_INDEX. First step: the remaining
  unticked sub-item in the box with tests in src/inference/prefix_index.py.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-27\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/inference/prefix_index.py: a83686efbfae3e70149953ec230bfe4a7ce774ac
---
