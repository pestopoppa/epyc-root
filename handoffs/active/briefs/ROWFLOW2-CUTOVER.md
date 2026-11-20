---
schema: epyc.brief.v1
id: ROWFLOW2-CUTOVER
box_text_sha: 0de2aabc1ab59b42
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow/deploy_rowflow.sh
- epyc-root:scripts/coordination/rowflow2/rowflow2.py
- epyc-root:docs/design/rowflow2-20261105.md
approach: 'After the shadow week passes: one deploy at a grant-quiet boundary via deploy_rowflow.sh, then delete the P3.3
  mechanisms in one commit and lift the deploy_rowflow.sh freeze. Hold-price gating already decided (plain backfill-if-fits).
  First step: prepare the deletion commit and the pre-deploy checklist (carrying LOOP-11 and LOOP-58 rules) so cutover is
  one command.

  '
acceptance: '! grep -q ''FROZEN'' scripts/coordination/rowflow/deploy_rowflow.sh'
non_goals:
- no deploy before ROWFLOW2-SHADOW-WEEK passes
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/deploy_rowflow.sh: 08e64587a06cbac40cbd4c4d7b683407ead7514c
    epyc-root:scripts/coordination/rowflow2/rowflow2.py: 0215c54d7f68f0b039b8d2a697e5801be937d895
    epyc-root:docs/design/rowflow2-20261105.md: b6189f226ff8fc5200cdad96ae695f62cbed2187
---
