---
schema: epyc.brief.v1
id: UFH14-B4j
box_text_sha: 0a3d74ab0f17f07a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md
- epyc-root:handoffs/completed/kv-unified-stack-rollout.md
approach: 'Make cache_idle_slots:false a prefix_cache_selection field for :8083 (design 3.8) and ship it in ONE stack-change
  package together with KVU-16f''s -b 512 -ub 512 once that A/B is done (the rollout handoff is now under handoffs/completed;
  locate KVU-16f''s current owner via grep). The package must state the pool-full behaviour with idle contexts resident. First
  step: draft the PFX-SEL-1 field spec; package waits on KVU-16f. Operator signs.

  '
acceptance: grep -q 'cache_idle_slots' docs/design/ufh14-b4-prefix-cache-policy-20261003.md
non_goals:
- no launch flag change without signature
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md: ff90378ca69a29bef7be4957afa2290a89141d2e
    epyc-root:handoffs/completed/kv-unified-stack-rollout.md: 0bb6032a3b4667d67a1ea9f3894528fc86088833
---
