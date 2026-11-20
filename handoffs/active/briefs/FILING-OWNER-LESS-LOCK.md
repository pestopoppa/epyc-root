---
schema: epyc.brief.v1
id: FILING-OWNER-LESS-LOCK
box_text_sha: 0824e248287785bd
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- scripts/coordination/churn/auto_file.py
- scripts/coordination/rowflow2/rowflow2.py::file_step
approach: 'Take one shared flock (same lock file path in both writers) around each queue append so a cross-writer duplicate
  is impossible; re-read the snapshot under the lock before dedup. Chosen over single-owner because both writers are live.

  '
acceptance: python3 -m pytest scripts/coordination/rowflow2/tests/test_filing_lock.py -q
new_tests:
- scripts/coordination/rowflow2/tests/test_filing_lock.py
non_goals:
- Do not merge the two writers into one (AUTOFILE-PATH-RECONCILE).
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/churn/auto_file.py: 3e2f23e707a8ac7e50d9df7365bf7423c75ef3b5
    epyc-root:scripts/coordination/rowflow2/rowflow2.py: 0215c54d7f68f0b039b8d2a697e5801be937d895
---
