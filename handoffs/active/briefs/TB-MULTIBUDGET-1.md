---
schema: epyc.brief.v1
id: TB-MULTIBUDGET-1
box_text_sha: 6c40e5b5b34d29c3
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/context-and-token-economy.md
approach: 'Add a subsection headed ''Multi-budget rule (TB-MULTIBUDGET-1)'' under Track: per-request-reasoning-budget stating
  the rule (3+ budgets, accuracy and output length, top budget uncensored) plus a table of served/candidate models with RL/length-training
  status taken from model cards and the registry.

  '
acceptance: grep -q 'Multi-budget rule (TB-MULTIBUDGET-1)' handoffs/active/context-and-token-economy.md
non_goals:
- No budget sweep is run
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: 55a59d4e87cf3920d424f3fb6d879a3b4d8a3801
---
