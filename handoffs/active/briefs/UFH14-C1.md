---
schema: epyc.brief.v1
id: UFH14-C1
box_text_sha: 845d049e453a97e7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
- epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md
approach: 'Epic; first concrete step: a per-role matrix (CPU/GPU roles, frontdoor, architect, workers, embedders) x (routing,
  admission, compaction, caching, telemetry, per-model parameters) listing which A and B fixes apply, including a delete-lens
  column naming fixes that should NOT become generic, and the passthrough multi-endpoint 422 scope question. Final output
  is the operator decision package (options, tradeoffs, recommendation) plus follow-ups filed in owning handoffs.

  '
acceptance: test -f docs/design/ufh14-c1-fold-matrix.md
non_goals:
- no implementation in this box
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: aa7dc419bf8eb745819bc97721912f46fb95d42d
    epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md: ff90378ca69a29bef7be4957afa2290a89141d2e
---
