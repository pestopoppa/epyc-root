---
schema: epyc.brief.v1
id: AKPL-P0
box_text_sha: t:009f777c47ae150a
author: owner
written: '2026-11-21'
accepted: owner
where:
- scripts/coordination/rowflow/estimate_history.py
- .claude/skills/row-owner-loop/scripts/row_scaffold.py
approach: 'Research repo (epyc-inference-research scripts/kernel_rnd/autokernel/loop/tail_timing.py, run.py): merge tail_timing.result_block
  into $AK_RESULT_JSON at run end. Root: estimate_history reads grants/*.ended, ready manifests and filing-done verdicts;
  row_scaffold defaults to it when no measured estimate is given. The 30-iteration clause needs one loop run.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_estimate_history.py .claude/skills/row-owner-loop/tests/
non_goals: []
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:scripts/coordination/rowflow/estimate_history.py: 4deb43f0d17832a37f19a831a1067ca34ea77149
    epyc-root:.claude/skills/row-owner-loop/scripts/row_scaffold.py: a524b6353fc864fbabd002960b1a2454c29bd897
---
