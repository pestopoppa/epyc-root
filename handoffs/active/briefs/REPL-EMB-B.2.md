---
schema: epyc.brief.v1
id: REPL-EMB-B.2
box_text_sha: 236d55e3686fbbff
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
approach: 'Speed baseline of a large MoE hybrid (Qwen3.8-Flash-Next or DeepSeek v4.1) across CPU+RAM and both MI210s measured
  on concurrency x tasks/hr x aggregate tok/s, after B.1. First step: write the row spec (recipe from the canonical recipes,
  launcher, concurrency grid, contention label) and publish when B.1 ticks. Stop: grid complete or futility. Feeds the architect
  placement decision.

  '
acceptance: grep -q 'REPL-EMB-B.2.*RESULT' handoffs/active/harness-program.md
non_goals:
- no accuracy claims
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: cadd2da6b668a35f911a3b0ad52a85e94ee62ea0
---
