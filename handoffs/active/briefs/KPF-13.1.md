---
schema: epyc.brief.v1
id: KPF-13.1
box_text_sha: a7e6dd44732649fe
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Drafter restore vs re-prefill A/B at the fork point: plain-KV MTP drafter and DFlash2, fork a slot twice from one
  junction (restore vs recompute). First step: launcher manifest on the P1 build; stop on both drafters measured.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-13\.1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
