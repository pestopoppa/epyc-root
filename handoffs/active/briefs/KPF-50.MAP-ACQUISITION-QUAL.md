---
schema: epyc.brief.v1
id: KPF-50.MAP-ACQUISITION-QUAL
box_text_sha: 3ecc8d389b67e858
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf50
approach: 'Qualify native own-child mapping acquisition: sealed model-free acquisition and private DSO fixture, one CPU quarter
  300 s. First step: run fixture; require actual owned-child map ranges and PID evidence.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-50\.MAP\-ACQUISITION\-QUAL\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf50: tree:9e10e547f9ef5ea95c23c20953895bf0680f0d1b
---
