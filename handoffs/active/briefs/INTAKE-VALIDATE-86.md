---
schema: epyc.brief.v1
id: INTAKE-VALIDATE-86
box_text_sha: 7d492f20c44aa2e4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/validate/validate_intake.sh
- epyc-root:research/intake_index.yaml
approach: 'Resolve or explicitly decline each of the 86 dangling cross-references reported by validate_intake.sh in research/intake_index.yaml
  (pre-existing, unchanged by the class C corrections). Step: dump the 86 into a table (entry, field, dangling id), fix the
  typo/renumber ones, mark the rest with the repo''s decline marker. Done when the validator exits 0.

  '
acceptance: bash scripts/validate/validate_intake.sh
non_goals:
- no deletion of intake entries
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/validate/validate_intake.sh: 6edb2ae18313009fd4c20e87f10a60a37f9f2ddb
    epyc-root:research/intake_index.yaml: 8a5da1c715192005eeb85b67289eb0b5a40093d1
---
