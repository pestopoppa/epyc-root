---
schema: epyc.brief.v1
id: LOOP-82
box_text_sha: 2c087437ee29c6c9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:scripts/autopilot/autopilot.py
approach: 'D1: decompose the autopilot loop (_run_loop_inner, autopilot.py:8415-8611) behind the P1 safety net (needs LOOP-68
  merged). Follow B1-02''s staged seams exactly, one stage per commit, run the loop harness and autopilot unit tests after
  each stage; never touch evaluator files. First step: stage 1 per the finding with the harness green before and after.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit -x -q -k autopilot_loop
non_goals:
- no evaluator file edits
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:scripts/autopilot/autopilot.py: da41d9e6aba6c969b6eafb2730b1ae7f76e960c3
---
