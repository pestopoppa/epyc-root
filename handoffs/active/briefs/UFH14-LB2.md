---
schema: epyc.brief.v1
id: UFH14-LB2
box_text_sha: 492dcc23cab9c0b4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/structured_output/parse_events.py
- epyc-orchestrator:src/backends/serving_calls.py
approach: 'Persist half landed (cbe542ca); reload clock started 2026-10-23T14:59Z so 14 days elapsed 2026-11-06. Remaining:
  run python -m src.structured_output.parse_events over the accrued events and file per-site length_truncated vs malformed
  (unknown_stop separately); if absent/unknown >20% of failures wire generation_context at repl_final. Last audit had only
  11 events, so first check the event count; if still tiny, report traffic-insufficient and re-check later. Zero inference.

  '
acceptance: grep -q 'UFH14-LB2 classification' handoffs/active/harness-program.md
non_goals:
- no new events schema
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/structured_output/parse_events.py: 26ff570a7acf7d07a92164f6ddf541b24591ad57
    epyc-orchestrator:src/backends/serving_calls.py: eeb700373c1e14620d6defeba6a6122c884e64b9
---
