---
schema: epyc.brief.v1
id: KPF-60
box_text_sha: e604ca4fdbf1dc3f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Chunk-KV phase 0: setup, frozen gate thresholds, measurements per /mnt/raid0/llm/tmp/cacheclip-port-20261021/DESIGN.md
  section 6 on experimental/chunk-kv-reuse-p0. First step: remaining unticked phase-0 measurement.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-60\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
