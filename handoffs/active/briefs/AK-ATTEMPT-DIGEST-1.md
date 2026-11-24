---
schema: epyc.brief.v1
id: AK-ATTEMPT-DIGEST-1
box_text_sha: t:daff94b43d3ef7f2
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py
approach: 'In actor_context.py, add a digest builder that reads each attempt''s per-call file, takes the mechanism, the arm
  and the verdict line, and emits one 2-4 sentence entry into the bundle index. Keep the full file path beside each digest.
  Regenerate one bundle from the live journal, diff index sizes, and guard the result with a unit test on a fixture journal.

  '
acceptance: change committed with its SHA and a replayed-bundle comparison (index chars before/after, attempts visible before/after)
  recorded under this box; reverted if the 10% budget is exceeded
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_context.py: 2a181d1953aabfc4873fd1082680514837e7609c
---
