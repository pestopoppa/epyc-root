---
schema: epyc.brief.v1
id: CJ-3d
box_text_sha: e472a6cca2ef8c4c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:docs/design/cj1-gpqa-sample-and-cj1e-gpu-pair.md
approach: 'Wire a representative BFCL sample; decide first whether to measure the production REPL path or native function
  calling (different instruments, different keys); tool-call parser pinned at 22c476dd. First step: record that decision in
  the box and harness config.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-3d\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:docs/design/cj1-gpqa-sample-and-cj1e-gpu-pair.md: 48387fabd2c169be52d730483e04319b2bba6054
---
