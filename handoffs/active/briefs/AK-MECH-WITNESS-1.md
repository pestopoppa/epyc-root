---
schema: epyc.brief.v1
id: AK-MECH-WITNESS-1
box_text_sha: t:96832fb2f583f616
author: intake
written: '2026-11-25'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/ak_row_lint.py
- epyc-root:handoffs/active/autokernel-loop.md
approach: 'Mirror the NO-WITNESS rule: detect a speed claim from decision_rule keywords (KEEP_CANDIDATE, GATE_PASS, speedup,
  x >=) and require spec.mechanism_witness with counter, direction (up/down) and aa_band. Check the row code or RESULT schema
  for the counter key. WARN only; enforcement (downgrading a keep to INCONCLUSIVE) is a later decision once the would-fail
  count over new rows is known.

  '
acceptance: pytest scripts/coordination/tests/test_ak_row_lint_mech_witness.py
new_tests:
- scripts/coordination/tests/test_ak_row_lint_mech_witness.py
non_goals:
- No change to keep decisions or verdict strings in this box.
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-root:scripts/coordination/rowflow/ak_row_lint.py: 4745c8c56eac49f64185450835c30a9b3bf82432
    epyc-root:handoffs/active/autokernel-loop.md: 6405bce2c4ca4f32df8a139ace641181f8b166d8
---
