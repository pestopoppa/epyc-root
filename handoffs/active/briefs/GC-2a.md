---
schema: epyc.brief.v1
id: GC-2a
box_text_sha: t:eb8505e6ff986949
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/glm52_reviewer_capability_direct_runner.py
- epyc-inference-research:data/glm52_reviewer_capability_direct
approach: 'Question: does a rubric-authoring pass on DeepSeek-V4.1-Flash produce axis-diverse rubrics against frontier-authored
  references? Broaden the task set and/or revise the rubric prompt/schema to force axis diversity (canonical-axis prompt and
  alias-normalising scorer carry over; GC-2r mean_composite=1.0 is GLM-5.2 evidence, not a V4.1 prior). Blocked on the V4.1
  port gates. Prep: extend the capability runner''s task set. Stop on task set scored or futility.

  '
acceptance: grep -q 'GC-2a verdict' handoffs/active/reviewer-control-plane.md
non_goals:
- no claim before RC-6a
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/glm52_reviewer_capability_direct_runner.py: 1d964619f44eaf738879b090f83c9fb9fdce767f
    epyc-inference-research:data/glm52_reviewer_capability_direct: tree:b4095c55f546d517c933fae5b2154077216e4ad7
---
