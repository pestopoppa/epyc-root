---
schema: epyc.brief.v1
id: KPF-26
box_text_sha: c6ffced346b7304b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/inference/prefix_index.py
approach: 'P2 gate: replay a real fan-out (HS-19 scouting round or delegate wave) through :8000. First step: replay driver
  manifest; stop on prefix-hit and latency rows filed.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-26\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/inference/prefix_index.py: a83686efbfae3e70149953ec230bfe4a7ce774ac
---
