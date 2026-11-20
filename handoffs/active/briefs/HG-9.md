---
schema: epyc.brief.v1
id: HG-9
box_text_sha: t:a87948aaae5f04c2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/hg9-detect-repair-topology.md
- epyc-orchestrator:src/proactive_delegation/delegator.py
approach: 'Step 1 (topology contract) is done. Step 2 (inference, after an EV-13b resume per eval-tower-verification.md):
  measure detection F1 of the small-model detector pool and fix quality of the larger recommender on the same findings, A/B
  vs the single-model baseline. Prep: the paired runner config from the design doc. Stop on F1 and fix-quality measured per
  arm; decision: whether AutoPilot learns the detect/repair edge.

  '
acceptance: grep -q 'HG-9 step 2 verdict' handoffs/active/reviewer-control-plane.md
non_goals:
- no fixed pipeline
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/hg9-detect-repair-topology.md: 7e7095ebc5ce45e96b4719c89488fd534ca5e3c1
    epyc-orchestrator:src/proactive_delegation/delegator.py: 4ae56089935b24a5e1697c67618ef349b9eb8e32
---
