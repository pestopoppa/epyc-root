---
schema: epyc.brief.v1
id: TASKFLOW-CANARY-FLAG-AB
box_text_sha: 6c28ba0d7ec4acb0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py::repl_syntax_loop_breaker
- epyc-orchestrator:src/features.py::repl_plan_narration_nudge
- epyc-orchestrator:src/features.py::harness_failure_ratio_guard
approach: 'Question: do repl_syntax_loop_breaker, repl_plan_narration_nudge and harness_failure_ratio_guard help or hurt on
  a local-model agentic suite? Paired on vs off per guard on the taskflow canary r2 suite (or the codemode_ab suite if r2
  has not landed), stack up, local A3B model. Report pass rate, turns, tokens and guard fire counts. Stop when >=30 tasks
  per arm or effect clear; futility on infra failure. Decision: default-ON per guard.

  '
acceptance: grep -q 'TASKFLOW-CANARY-FLAG-AB.*verdict' handoffs/active/engineering-hygiene-backlog.md
non_goals:
- no default flip in this box
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
