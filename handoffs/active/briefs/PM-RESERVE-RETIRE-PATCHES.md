---
schema: epyc.brief.v1
id: PM-RESERVE-RETIRE-PATCHES
box_text_sha: t:fa63d3835d9f2118
author: intake
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py::RESERVATION_MODE
- epyc-root:scripts/coordination/tests/test_rowflow_reservation.py
approach: 'Write the five A-E replay tests first against C in enforce mode and confirm they pass with the subsumed rules bypassed.
  Then delete each rule in its own commit (forward-port rule: one feature per commit) and rerun the tests after each deletion.
  Keep whatever B''s fallback admission path calls; C falls back to it on solver failure.

  '
acceptance: pytest scripts/coordination/tests/test_rowflow_reservation.py
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: b854ad584380c3d0347cd2a740b0b11199cf6ad8
    epyc-root:scripts/coordination/tests/test_rowflow_reservation.py: f9dec65dd8be7c12058f5f4a79ec3c0fb8740a1c
---
