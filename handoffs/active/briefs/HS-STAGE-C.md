---
schema: epyc.brief.v1
id: HS-STAGE-C
box_text_sha: 6d5833c411704cb4
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/handoffs/box_index.py
- epyc-root:scripts/handoffs/task_lint.py
- epyc-root:scripts/handoffs/propose_rewrites.py
approach: 'Rewrite content of lint-failing boxes (spec STAGE-C-BRIEF.md / HANDOFF-STANDARD.md in the dispatcher-redesign tmp
  dir) via propose_rewrites.py, owner-applied, until box_index counts lint_ok/total >= 0.45 (343/1528 = 22.4% at 2026-11-20);
  then file the Stage C ratify package for the operator. The percentage is the runnable half; the ratify package is checked
  by hand.

  '
acceptance: python3 scripts/handoffs/index_state.py --box-index >/dev/null && python3 -c "import json;c=json.load(open('handoffs/active/.box-index.json'))['counts'];assert
  c['lint_ok']/c['total']>=0.45,c"
non_goals:
- do not weaken task_lint rules to reach the number
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/handoffs/box_index.py: 4d32d5339199792507cae187d7cf5b2e1a20ec64
    epyc-root:scripts/handoffs/task_lint.py: a93b0a6ff4882ec85be567380542ef6f2e1190a0
    epyc-root:scripts/handoffs/propose_rewrites.py: 7c6ebe8a2162502799198bd937a1f6cd92f21920
---
