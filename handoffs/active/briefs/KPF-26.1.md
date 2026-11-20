---
schema: epyc.brief.v1
id: KPF-26.1
box_text_sha: 2284adad41a46ab0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/inference/prefix_index.py
approach: 'Task-outcome check on persona-bearing waves behind ORCHESTRATOR_PREFIX_INDEX plus _FORK (a572338d). First step:
  paired outcome harness manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-26\.1\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/inference/prefix_index.py: a83686efbfae3e70149953ec230bfe4a7ce774ac
---
