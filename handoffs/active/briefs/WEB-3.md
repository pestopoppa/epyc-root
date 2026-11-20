---
schema: epyc.brief.v1
id: WEB-3
box_text_sha: c948abfdc1a5d5a2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-web:data/catalog.json
- epyc-web:data/recipe.json
- epyc-web:app.js
approach: 'Question: Flash-Next UD-IQ4_XS CPU throughput over np x context on the frozen kernel. This box does not authorize
  running it; it is the refresh step: when a frozen-kernel sweep result exists, replace the card''s unmeasured grid in data/catalog.json
  with source-backed cells (each cell keeps its source path and contention label). Prep: write the cell-import script from
  a sweep results file to the catalog schema. The sweep itself needs an operator-approved row (the Sept 24 sweep was skipped
  by the operator).

  '
acceptance: python3 -c "import json;json.load(open('/workspace/repos/epyc-web/data/catalog.json'))"
non_goals:
- do not run the sweep without operator approval
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-web:data/catalog.json: a8e2be2ff99cdb885832ea892382c9d4d1b278fe
    epyc-web:data/recipe.json: 2724a7ae88877d5503171a7fbe9cdae6dd7a276c
    epyc-web:app.js: 018c3499ad6eec1105a18724f688daf07b7bb850
---
