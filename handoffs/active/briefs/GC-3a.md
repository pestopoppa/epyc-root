---
schema: epyc.brief.v1
id: GC-3a
box_text_sha: t:b0bec75604c289b4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/glm52_reviewer_capability_direct_runner.py
- epyc-inference-research:data/glm52_reviewer_capability_direct
approach: 'Question: does V4.1-Flash do why-diagnosis (not just that-detection) on corpus-v1? Retest after P-REV-1 sign-off;
  the old IQ2-quant hypothesis (intake-836) is void, any weakness must be re-attributed from scratch against V4.1''s quant.
  Blocked on the V4.1 port gates. Prep: repair the why-diagnosis smoke for the V4.1 template and pin the corpus-v1 rows.

  '
acceptance: grep -q 'GC-3a verdict' handoffs/active/reviewer-control-plane.md
non_goals:
- no claim before RC-6a
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/glm52_reviewer_capability_direct_runner.py: 1d964619f44eaf738879b090f83c9fb9fdce767f
    epyc-inference-research:data/glm52_reviewer_capability_direct: tree:b4095c55f546d517c933fae5b2154077216e4ad7
---
