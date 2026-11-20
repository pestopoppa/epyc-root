---
schema: epyc.brief.v1
id: KEEPER-CLASS-FIX
box_text_sha: 8b6024e2fce67108
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow2/rowflow2.py
- epyc-root:docs/reports/coordination/keeper-friction-review-20261105.md
- epyc-root:docs/design/rowflow2-20261105.md
approach: 'Items #1 reclaim idle use-holds / release-on-phase, #3 per-row pinned engine dir, #5 single state model, #6 idle
  SLO with fixed alarm route are open; rowflow.py is FROZEN so they land in rowflow2 behind the shadow week. Epic; first step:
  implement #1 (release-on-phase) in rowflow2.py with a replay test against a recorded idle day, deploying only through deploy_rowflow.sh.

  '
acceptance: python3 -m pytest -q scripts/coordination/rowflow2/tests/test_release_on_phase.py
new_tests:
- scripts/coordination/rowflow2/tests/test_release_on_phase.py
non_goals:
- no edit to frozen rowflow.py
- deploy only via deploy_rowflow.sh
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow2/rowflow2.py: 0215c54d7f68f0b039b8d2a697e5801be937d895
    epyc-root:docs/reports/coordination/keeper-friction-review-20261105.md: 645e336a20eb954e71fe3316ab23304136867d91
    epyc-root:docs/design/rowflow2-20261105.md: b6189f226ff8fc5200cdad96ae695f62cbed2187
---
