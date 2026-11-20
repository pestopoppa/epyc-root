---
schema: epyc.brief.v1
id: REPL-EMB-CONSUMER-GATE
box_text_sha: 45a92d794be1f764
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
- epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md
approach: 'Roll-up box: drive R1-R5 (each its own box) to MIGRATED-to-EG2-256 or RETIRED before the v11 freeze. First step:
  build a status table listing each consumer''s terminal criterion and current state from the five boxes. Box has no done-when
  of its own; acceptance is the closest check: all five boxes ticked.

  '
acceptance: test $(awk '/REPL-EMB-R[1-5] -/ && /\[ \]/' handoffs/active/harness-program.md | wc -l) -eq 0
non_goals:
- no per-consumer work in this box
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: 3cb5ef0d88bd7c907a51544f584b042ea93e3a23
    epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md: 291a8f44609f92978b78ff5504893ecf8d129bf4
---
