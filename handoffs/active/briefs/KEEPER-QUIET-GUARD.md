---
schema: epyc.brief.v1
id: KEEPER-QUIET-GUARD
box_text_sha: t:2f188229aa2bb400
author: owner
written: '2026-11-21'
accepted: owner
where:
- scripts/coordination/rowflow
approach: 'Add the field to the row spec schema and lint, teach the keeper utilisation report to treat those regions as guarded.

  '
acceptance: 'Fixture test: guard row shows GUARDING; unguarded idle row still UNDERUSED.'
non_goals:
- Changing grant ranking.
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:scripts/coordination/rowflow: tree:579d6303d385dd308742407277dfd0ed88721509
---
