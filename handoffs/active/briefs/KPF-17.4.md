---
schema: epyc.brief.v1
id: KPF-17.4
box_text_sha: 90100618f7ef20b5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'SWA checkpoint range correctness (TAG_CHECKPOINTS_FIX_POS_MIN) on Qwen3.8-27B target with the DFlash2 SWA drafter.
  First step: test run manifest on the fork build.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-17\.4\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
