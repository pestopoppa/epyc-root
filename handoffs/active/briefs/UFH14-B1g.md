---
schema: epyc.brief.v1
id: UFH14-B1g
box_text_sha: eb845833aa7e87d8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py::repl_answer_force
- epyc-orchestrator:scripts/benchmark/feature_validation.py
approach: 'Question: does repl_answer_force (forced-answer turn at 0.65 of the request budget) raise rescue rate and accuracy
  per suite vs off on EvalTower? Arms: flag on vs off, same tasks and role pin, A/B ordered per cell. Stop when >=30 tasks
  per suite per arm or paired effect clear; futility on infra failures. Decision: default-ON enable for repl_answer_force
  (derived_prefill_timeout enable rides B1d).

  '
acceptance: grep -q 'UFH14-B1g verdict' handoffs/active/harness-program.md
non_goals:
- no enable of session_compaction_llm_index
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-orchestrator:scripts/benchmark/feature_validation.py: 84074848d9d26450a0066870b57961f475f5e522
---
