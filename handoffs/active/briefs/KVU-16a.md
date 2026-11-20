---
schema: epyc.brief.v1
id: KVU-16a
box_text_sha: 35295d891a6e0122
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/PACKAGE.md
approach: 'Replace derived vram_non_kv_gib with the measured value. First step: measurement script reading launcher per-buffer
  VRAM decomposition and updating the registry field with a test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-16a\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/stack-change-hygiene-20261003/PACKAGE.md: 467d7367dba92847b9cbef33138b786b319a863f
---
