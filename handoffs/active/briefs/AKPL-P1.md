---
schema: epyc.brief.v1
id: AKPL-P1
box_text_sha: t:e97b1597c2c6b5e7
author: owner
written: '2026-11-21'
accepted: owner
where:
- .claude/skills/row-owner-loop/scripts/runend.py
- .claude/skills/row-owner-loop/scripts/watch_rows.sh
- docs/design/autokernel-parallel-loop-p1-replay.md
approach: 'Evaluator lives in epyc-inference-research scripts/kernel_rnd/autokernel/loop/gate_eval.py; runend.py --gate-eval
  drafts verdict.json from it; replay over filing-done records owned by autokernel since 2026-11-06, report in docs/design/autokernel-parallel-loop-p1-replay.md.

  '
acceptance: python3 -m pytest -q .claude/skills/row-owner-loop/tests/
non_goals: []
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:.claude/skills/row-owner-loop/scripts/runend.py: 01bc328e62887a05c13c15931d9ed312af60d78a
    epyc-root:.claude/skills/row-owner-loop/scripts/watch_rows.sh: 298fe6772c013fcc27c1e16dbe0046a385e5917e
    epyc-root:docs/design/autokernel-parallel-loop-p1-replay.md: e993d01f16eaafe6cdd4bdc12ac681c73f4d3c06
---
