---
schema: epyc.brief.v1
id: KPF-RS-1.OBS-IMPACT
box_text_sha: b8f4ae9a8186e68e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Capture twelve native upstream observer and synchronization impacts on candidate build 8952a0f693fb (whole-host
  CPU, 7200 s). First step: run manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-RS\-1\.OBS\-IMPACT\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
