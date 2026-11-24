---
schema: epyc.brief.v1
id: EV-SCORER-FUZZ-1
box_text_sha: t:2d14f7e40387fb61
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-orchestrator:src
approach: 'Write fixture generators for the five mutation categories over GSM8K/MATH-500 gold answers (e.g. gold in prose
  without a box, two conflicting finals, 1e-3 float drift). Call eval_tower''s math_verify and exact-match scorer functions
  directly in pytest, and tabulate accept rates against the strict contract. Keep the fixtures in the repo.

  '
acceptance: per-category FPR/FNR table filed under this box with the fixture digest; any category with FPR > 0 gets a named
  scorer fix box; futility recorded if FPR is 0 everywhere
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-orchestrator:src: tree:8fbfbe16e38959d711e1700615b5208b9d9ce0be
---
