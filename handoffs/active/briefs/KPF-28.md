---
schema: epyc.brief.v1
id: KPF-28
box_text_sha: 1104100dbb71882c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'DS41 (dsv4 memory) checkpoint and fork characterisation: record GGUF bytes per context checkpoint per component
  on the prefix-fork build. First step: byte-accounting script and manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-28\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
