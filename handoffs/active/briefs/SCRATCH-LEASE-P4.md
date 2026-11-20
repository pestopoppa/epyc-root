---
schema: epyc.brief.v1
id: SCRATCH-LEASE-P4
box_text_sha: f217e159cd544185
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/system/scratch_cleanup.py
- epyc-root:tests/test_scratch_lease_coverage.py
approach: 'Delete dead cleanup_scratch paths after SCRATCH-LEASE-P3 retires the old reapers. Step now: enumerate callers of
  cleanup_scratch (grep) and list which are dead given current reapers, so deletion is mechanical after P3. Box has no done-when;
  acceptance is the closest check.

  '
acceptance: '! grep -rq ''cleanup_scratch'' scripts'
non_goals:
- no deletion before P3
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/system/scratch_cleanup.py: ae75ac2e6dc92fda028a76e18b6bd92f034ef8f8
    epyc-root:tests/test_scratch_lease_coverage.py: fa269ac2eadcec25f0141e9330e6e88aac10bce5
---
