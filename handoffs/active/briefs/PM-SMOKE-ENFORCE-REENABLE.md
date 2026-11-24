---
schema: epyc.brief.v1
id: PM-SMOKE-ENFORCE-REENABLE
box_text_sha: t:4195d40f305da23e
author: wrap-up
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py::SMOKE_MEASURE_ENFORCE
approach: 'Wait for AK confirmation on the bus; count queued rows lacking smoke_measure.json (incl. out/smoke path); flip
  only at zero; deploy via deploy_rowflow.

  '
acceptance: grep 'SMOKE_MEASURE_ENFORCE = True' scripts/coordination/rowflow/rowflow.py
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: eea19c9a9ab23fd772d46c51f8cfc3cd07695066
---
