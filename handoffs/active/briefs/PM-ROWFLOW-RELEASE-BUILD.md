---
schema: epyc.brief.v1
id: PM-ROWFLOW-RELEASE-BUILD
box_text_sha: t:71e1844b954f01cf
author: wrap-up
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
approach: 'Find the release path that looks up the open grant; when no grants/<id>.json exists, fall back to grants/<id>.build.json
  and release that claim (same ended/flag writes). Add a unit test with a build-only claim.

  '
acceptance: pytest scripts/coordination/tests -k release_build
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: eea19c9a9ab23fd772d46c51f8cfc3cd07695066
---
