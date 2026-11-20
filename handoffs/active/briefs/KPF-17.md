---
schema: epyc.brief.v1
id: KPF-17
box_text_sha: 860721e37bf73999
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'KPF-17 tests: Qwen3.5-0.8B Q8 partial-restore conformance with source-bound model-free prerequisites; stop-on-futility
  on source/control failure. First step: the conformance runner manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-17\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
