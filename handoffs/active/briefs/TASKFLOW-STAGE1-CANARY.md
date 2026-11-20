---
schema: epyc.brief.v1
id: TASKFLOW-STAGE1-CANARY
box_text_sha: 6c4443cdf5f4a85e
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/dispatch.py
- epyc-root:scripts/coordination/taskflow/select.py
- epyc-root:scripts/coordination/taskflow/verify.py
approach: 'This is an inference row (gpu-q3, est 4200 s): the work is publishing and running the row defined in the box (10
  select.py boxes, opencode workers on a row-owned llama-server), then applying its stated rule to the result to get STAY-35B
  / TRY-27B / FIX-HARNESS. Acceptance is the box''s verdict string, greppable once the owner files it in the handoff; it fails
  until then.

  '
acceptance: 'grep -rE ''verdict: (STAY-35B|TRY-27B|FIX-HARNESS)'' handoffs/active/churn-pipeline.md | grep -v ''done when'''
non_goals:
- no new accuracy study beyond the 10 tasks
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/taskflow/dispatch.py: e3c4d1b3dddb764e7da6ff85829f4fb7a345579b
    epyc-root:scripts/coordination/taskflow/select.py: 039141ad68150f4571ad4a578ad86aebe9125d65
    epyc-root:scripts/coordination/taskflow/verify.py: 8061e4e89eb76fba309a8b779dcc94f6d5c774a2
---
