---
schema: epyc.brief.v1
id: M26-POSTCAP-APPLY
box_text_sha: e753e2e0e1587f47
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/intake_index.yaml
- epyc-root:research/deep-dives/intake-digests
approach: 'Apply the accepted DP-J table (OP-POSTCAP 2026-11-11) to bearing entries: monitor or decline per row, locate-first
  triggers stay as written. Edit dive_corrections/monitor records in research/intake_index.yaml, then run cite-check. Zero
  inference.

  '
acceptance: python3 scripts/vidya/cli.py cite-check --as-of 2026-11-20
non_goals:
- no change to triggers
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/intake_index.yaml: 8a5da1c715192005eeb85b67289eb0b5a40093d1
    epyc-root:research/deep-dives/intake-digests: tree:3632bf10c75fc4e934b7bb846eab9f7b7840c028
---
