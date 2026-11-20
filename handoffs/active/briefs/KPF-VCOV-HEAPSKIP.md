---
schema: epyc.brief.v1
id: KPF-VCOV-HEAPSKIP
box_text_sha: 6b554ebbe8dbf3ed
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'verified_coverage() must whitelist gitnexus heap skipped=N lines, then rerun the falsely failed rows (kpf17-oracle,
  kpf182, kpf26, kpf27d, kpf625, kpf191, kpf131-r5). First step: locate verified_coverage (not in root or research scripts
  by name; searched with grep -rn ''def verified_coverage''), add the whitelist with a test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-VCOV\-HEAPSKIP\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
