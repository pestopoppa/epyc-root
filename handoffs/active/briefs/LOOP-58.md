---
schema: epyc.brief.v1
id: LOOP-58
box_text_sha: 9641a3b21fc29699
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/rowflow2/rowflow2.py
approach: 'rowflow.publish refuses null/empty decision_rule/result_path (rowflow.py:770-771) but the legacy migration path
  (:1101-1105) substitutes placeholders so such rows pass. rowflow2 already refuses a MIGRATED: decision_rule unless legacy-mapped.
  Remaining: decide close-the-path-at-cutover vs accept; since rowflow.py is frozen, the closure rides ROWFLOW2-CUTOVER. First
  step: a rowflow2 test that every published row has a real decision_rule and result_path.

  '
acceptance: python3 -m pytest -q scripts/coordination/rowflow2/tests/test_publish_requires_decision_rule.py
new_tests:
- scripts/coordination/rowflow2/tests/test_publish_requires_decision_rule.py
non_goals:
- no edit to frozen rowflow.py
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/rowflow2/rowflow2.py: 0215c54d7f68f0b039b8d2a697e5801be937d895
---
