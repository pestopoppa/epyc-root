---
schema: epyc.brief.v1
id: EV-15a
box_text_sha: 9c4e11188f372984
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:artifacts/audit/ni-ev15-readouts-20261031/README.md
approach: 'Clean-room port of the eight read-out formulas (mode, mean, rounded mean, ...), absorbing EV-15c silent-failure
  guards. First step: module with golden unit tests per formula.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-15a\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:artifacts/audit/ni-ev15-readouts-20261031/README.md: 0a3274b7c78d52fd8bf617055820560094caecf8
---
