---
schema: epyc.brief.v1
id: KPF-64-RERUN-TRACEBACK
box_text_sha: e0caaf01065a7bc1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf64_replay
approach: 'Rerun kpf64 keeping the full traceback (prior run inconclusive without it, 020bdd856). First step: rerun with traceback
  capture and file the traceback.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-64\-RERUN\-TRACEBACK\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf64_replay: tree:a0b14606d9e85ad361878f1ffb827280488d884e
---
