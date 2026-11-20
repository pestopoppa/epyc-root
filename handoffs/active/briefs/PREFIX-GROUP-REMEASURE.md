---
schema: epyc.brief.v1
id: PREFIX-GROUP-REMEASURE
box_text_sha: e3f8253efd6285e3
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/analysis/prefix_cache_report.py
- epyc-orchestrator:src/typed_decisions/fanout_policy.py
approach: 'Zero-compute offline rerun: sibling-subtask and concurrent same-port longest-common-prefix fractions (byte and
  token estimate, excluding truncated prompts, per role/port) over the NEW request-body log, same method as PREFIX-GROUP-MEASURE
  (tap events carry prompt, parent_request_id, role, port). Question: is the shared fraction now material with the prefix-stable
  layout served. Stop when n>=500 requests with bodies; decision feeds PREFIX-GROUP-POLICY gate. Prep step: copy the MEASURE
  script, point it at the new log.

  '
acceptance: grep -q 'PREFIX-GROUP-REMEASURE.*RESULT' handoffs/active/harness-program.md
non_goals:
- no flag or dispatcher change
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/analysis/prefix_cache_report.py: dbf69f359009287e90c0db9e6645185adee48d99
    epyc-orchestrator:src/typed_decisions/fanout_policy.py: b00e3eb3ca0317bd5059bd124769858809e5e3bc
---
