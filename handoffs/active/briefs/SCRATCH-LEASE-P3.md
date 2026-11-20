---
schema: epyc.brief.v1
id: SCRATCH-LEASE-P3
box_text_sha: 5a5163fbc5453383
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/system/scratch_lease.py
- epyc-root:scripts/system/scratch_cleanup.py
- epyc-root:tests/test_scratch_lease_coverage.py
approach: 'Retire old reapers once leases cover all scratch roots. Blockers per 2026-11-09 audit: leases only bound a KEEP
  veto, cover only top-level tmp/, and kernel_store_gc, worktree_salvage and reclaim_row ignore them. Step: extend lease coverage
  to the other scratch roots and make those three consult leases, pinned by tests/test_scratch_lease_coverage.py; then retire
  one reaper at a time.

  '
acceptance: python3 -m pytest -q tests/test_scratch_lease_coverage.py
non_goals:
- no reaper removal before coverage proves complete
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/system/scratch_lease.py: 9a21f6b077bfd2f8b22d6602381c4acd2694ae6b
    epyc-root:scripts/system/scratch_cleanup.py: ae75ac2e6dc92fda028a76e18b6bd92f034ef8f8
    epyc-root:tests/test_scratch_lease_coverage.py: fa269ac2eadcec25f0141e9330e6e88aac10bce5
---
