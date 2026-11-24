---
schema: epyc.brief.v1
id: AK-LESSON-DEMOTE-1
box_text_sha: t:b39826c03fabcf63
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/controller/do_not_repeat.py
approach: 'Parse program.md, the journal shards and negatives.json. Reconstruct per-iteration rendered lessons from actor_context.py''s
  bundle index, mark which lesson IDs each proposal cited, and simulate three demote policies over epochs (unused-5, alpha=0
  periodic, utility-gated from keep/discard receipts). Exclude do_not_repeat.py-backed entries. Emit a per-policy CSV of chars
  saved and re-proposals.

  '
acceptance: 'per-rule table (chars saved, false-demotion re-proposals, keep-rate delta) filed under this box with the journal
  digest and verdict: adopt a rule only if it has 0 false-demotion re-proposals and the utility-gated arm saves at least as
  many chars as unused-5, else NO-GO'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py: 2a181d1953aabfc4873fd1082680514837e7609c
    epyc-inference-research:scripts/kernel_rnd/autokernel/controller/do_not_repeat.py: 6f78ce210c4f802f487bf415063cd07228454930
---
