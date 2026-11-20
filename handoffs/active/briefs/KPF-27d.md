---
schema: epyc.brief.v1
id: KPF-27d
box_text_sha: 0c54428aa6e42083
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/inference/prefix_index.py
approach: 'Land KPF-27 on main (owning session), then a shadow window on :8083 with the flag on. First step: verify landing
  and file the shadow-window manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-27d\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/inference/prefix_index.py: a83686efbfae3e70149953ec230bfe4a7ce774ac
---
