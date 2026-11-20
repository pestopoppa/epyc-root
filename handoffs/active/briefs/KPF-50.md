---
schema: epyc.brief.v1
id: KPF-50
box_text_sha: b7831adea7857188
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf50
approach: 'rocprof profile first (GPU window) on the P1 build at 4 x 80k with a 60k forked trunk; if trunk attention >=20%
  of step time design the trunk-block change. First step: rocprof manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-50\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf50: tree:9e10e547f9ef5ea95c23c20953895bf0680f0d1b
---
