---
schema: epyc.brief.v1
id: RTE-LOG-1
box_text_sha: 5317f026a766c4d2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/analysis/prompt_layout_live_check.py
- epyc-orchestrator:src/graph/helpers.py
- epyc-orchestrator:tests/unit/test_prompt_layout.py
approach: 'Code, reader and report are done (5d2140f8, e9cf0949, 0226a4c6). Remaining: set ORCHESTRATOR_REQUEST_SOURCE in
  the autopilot and benchmark launchers, then on the next stack start send one request and run prompt_layout_live_check.py
  over dispatch.jsonl and serving_calls.jsonl (exit 0 required; zero records is not a pass). Launcher edit is the prep step.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && grep -rq ORCHESTRATOR_REQUEST_SOURCE scripts/server scripts/autopilot
non_goals:
- no new logging fields
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/analysis/prompt_layout_live_check.py: 1c6fa1d57bcfb4225023978a5f563978167e3a8c
    epyc-orchestrator:src/graph/helpers.py: eb930e373b30b65239d1a6e4d0b95d2e9eab124a
    epyc-orchestrator:tests/unit/test_prompt_layout.py: 648ba42d178e5924409355749e060b26f5eaa03a
---
