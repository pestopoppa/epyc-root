---
schema: epyc.brief.v1
id: AUTOFILE-PATH-RECONCILE
box_text_sha: 9f00157b4afeea6b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/churn/auto_file.py
- epyc-root:scripts/coordination/rowflow2/rowflow2.py
- epyc-root:scripts/coordination/churn/filing.py
approach: 'Two filing writers remain: the keeper auto-file (churn/auto_file.py) and rowflow2 file_step. Make filing.py the
  single queue/writer both call (one idempotent write keyed on row id and terminal), delete the duplicate path at cutover.
  First step: a test where both entry points file the same terminal and exactly one record results.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_filing_single_writer.py
new_tests:
- scripts/coordination/tests/test_filing_single_writer.py
non_goals:
- no filing schema change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/churn/auto_file.py: 3e2f23e707a8ac7e50d9df7365bf7423c75ef3b5
    epyc-root:scripts/coordination/rowflow2/rowflow2.py: 0215c54d7f68f0b039b8d2a697e5801be937d895
    epyc-root:scripts/coordination/churn/filing.py: 7f447cb13f38175f59eab8eb3fbcf4f08ecec945
---
