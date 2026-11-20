---
schema: epyc.brief.v1
id: M16-FLAGSRC-APPLY
box_text_sha: 9717fb7193bf853c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/intake_index.yaml
- epyc-root:research/deep-dives/intake-digests/2026-10-20-ids-2116-2190.md
approach: 'Apply the accepted DP-D table (17 flagged sources, recommendation column adopted by OP-FLAGSRC 2026-11-11) to each
  bearing entry''s dive_corrections in research/intake_index.yaml: one row per source with its recommended disposition. Use
  the intake validator after the edit. Zero inference.

  '
acceptance: python3 scripts/vidya/cli.py cite-check --as-of 2026-11-20
non_goals:
- no new dispositions beyond the table
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/intake_index.yaml: 8a5da1c715192005eeb85b67289eb0b5a40093d1
    epyc-root:research/deep-dives/intake-digests/2026-10-20-ids-2116-2190.md: e265da1c50cb317c3ab9e0e8a7d1220637abf768
---
