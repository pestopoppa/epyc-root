---
schema: epyc.brief.v1
id: PM-RULES-WARN-FIRST
box_text_sha: t:8b40c1ebff41b6c8
author: wrap-up
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
approach: 'Add a RULES table {name: mode}; keeper logs would-fail counts per warn rule each SNAPSHOT; promotion to enforce
  requires count 0; freeze flag file blocks mode changes while an AK push is in flight.

  '
acceptance: pytest scripts/coordination/tests -k rule_mode
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: eea19c9a9ab23fd772d46c51f8cfc3cd07695066
---
