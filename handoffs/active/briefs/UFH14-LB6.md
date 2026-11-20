---
schema: epyc.brief.v1
id: UFH14-LB6
box_text_sha: 98095f86d8630159
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_calls.py
approach: 'Source landed (365b20c6, c7f3c8ff). Remaining proof over one hour of real traffic: serving_calls.health() per worker
  pid and the ratio of method=infer records to llama POST start log lines ~1; non-zero write_failed/build_failed must name
  the cause and be fixed. Needs a live stack hour. First step: write a one-command ratio checker (log lines vs records) so
  the proof is a single run.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_serving_calls_ratio_check.py
new_tests:
- tests/unit/test_serving_calls_ratio_check.py
non_goals:
- no source change to the recorder beyond what a named failure cause requires
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_calls.py: eeb700373c1e14620d6defeba6a6122c884e64b9
---
