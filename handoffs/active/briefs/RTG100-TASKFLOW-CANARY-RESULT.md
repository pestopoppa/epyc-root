---
schema: epyc.brief.v1
id: RTG100-TASKFLOW-CANARY-RESULT
box_text_sha: d95ab81bd3851bb8
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/dispatch.py
- epyc-root:scripts/coordination/taskflow/verify.py
approach: 'Filing box for row tf1-canary-35b-c14-gpu-r1-20261120: when the row ends, read its result via the row''s filing
  path, apply the rule in TASKFLOW-STAGE1-CANARY (>=0.3 verified and model-limitation minority = STAY-35B; <0.3 with >=50%
  model-limitation = TRY-27B; >=50% harness = FIX-HARNESS) and record the verdict against TASKFLOW-STAGE1. Gated on the canary
  box; same acceptance string.

  '
acceptance: 'grep -rE ''verdict: (STAY-35B|TRY-27B|FIX-HARNESS)'' handoffs/active/churn-pipeline.md | grep -v ''done when'''
non_goals:
- do not re-run the row
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/taskflow/dispatch.py: e3c4d1b3dddb764e7da6ff85829f4fb7a345579b
    epyc-root:scripts/coordination/taskflow/verify.py: 8061e4e89eb76fba309a8b779dcc94f6d5c774a2
---
