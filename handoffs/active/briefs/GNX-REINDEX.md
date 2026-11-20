---
schema: epyc.brief.v1
id: GNX-REINDEX
box_text_sha: a496dd7e3004b11b
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/gitnexus-reindex.py
- epyc-root:tests/gitnexus/test_gitnexus_reindex.py
approach: 'Standing housekeeping target for reindex rows; rows cite this box as handoff_task. Done when a real keeper-run
  reindex leaves gitnexus status fresh; history.jsonl gives measured walls for estimates.

  '
acceptance: python3 scripts/gitnexus-reindex.py check
non_goals:
- do not self-claim regions; keeper packs the row
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/gitnexus-reindex.py: 2ccb6803410eb7bb718c0a62991eb7c4484a2c01
    epyc-root:tests/gitnexus/test_gitnexus_reindex.py: cdf5a1e88149a74b571968176bdf8d2dd26e4369
---
