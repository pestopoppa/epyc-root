---
schema: epyc.brief.v1
id: CF-AB-A7-PROBE
box_text_sha: 7e2a9394357b9344
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/context_arm_ab.py
approach: 'Prompt-only exact-recall probe built from our verbatim session logs (key-value lookups, counting) comparing summary_only,
  pointer_only, summary_pointer and the box''s other arms. First step: probe generator with a deterministic fixture test,
  then the run.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CF\-AB\-A7\-PROBE\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/context_arm_ab.py: 5f04f543e3d659b4f40e3683181386af6c9cae88
---
