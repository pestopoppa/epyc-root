---
schema: epyc.brief.v1
id: PM-CODEX-LANE-VERDICT
box_text_sha: t:0cf1615ef0904afe
author: intake
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/verify.py
- epyc-root:scripts/handoffs/done_when.py
approach: 'Port drive2.sh''s resume loop unchanged and replace status() with verdict(lane): parse the LANE-STATUS box lines
  as claims, then check each branch and sha with git and run the same static checks; pushed lanes reuse done_when.py. DONE
  only when every claim checks out; a BLOCKED line with new commits since the last round is resumed once; three rounds with
  no new commit end STALLED. Append round, wall_s and verdict per lane to a JSONL ledger. The 5-consecutive-DONE exit criterion
  in README-INTERIM.md is then counted from this verdict. PM-CODEX-DISPATCH-DETERMINISTIC later ports this function into the
  dispatcher.

  '
acceptance: pytest scripts/coordination/tests/test_codex_lane_verdict.py
new_tests:
- scripts/coordination/tests/test_codex_lane_verdict.py
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/taskflow/verify.py: 3afa87fe881edd54cc5b38180715c25ed2c1892f
    epyc-root:scripts/handoffs/done_when.py: abc74c1ab54a17ed44515168c05ca58ee720940c
---
