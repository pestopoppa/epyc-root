---
schema: epyc.brief.v1
id: RA-13a
box_text_sha: t:6f858d78f0ae782d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/reviewer/blind_readback.py
approach: 'Harness built (48 tests, 9/9 mutants killed); the N=20 blind read-back pilot itself is unrun: the auditor sees
  only the artifact plus a read-back spec (never the task statement, request or author intent), emits a literal description,
  and the main compares it with the original ask; fresh context per revision. Run N=20 with a local model via the harness
  (operator-gated live calls: request through the grant path). Stop at N=20 or futility. Report with citable_summary().

  '
acceptance: grep -q 'RA-13a pilot' handoffs/active/reviewer-control-plane.md
non_goals:
- no change to the field whitelist
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/reviewer/blind_readback.py: 40485df54abf95b13d6e96f0cabc2428439d678e
---
