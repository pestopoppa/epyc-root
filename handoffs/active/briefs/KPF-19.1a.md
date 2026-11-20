---
schema: epyc.brief.v1
id: KPF-19.1a
box_text_sha: b0fe8be62d969c85
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'DFlash2 SWA-drafter fork run (correctness, CPU): on the job-28 build run test_kpf191 with KPF_SPEC_TYPE set to
  the DFlash2 type. First step: run manifest; stop on filed verdict.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-19\.1a\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
