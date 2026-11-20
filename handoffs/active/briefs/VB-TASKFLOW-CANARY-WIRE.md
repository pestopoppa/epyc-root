---
schema: epyc.brief.v1
id: VB-TASKFLOW-CANARY-WIRE
box_text_sha: t:83dbb25f615e9ce4
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/dispatch.py
- epyc-root:scripts/vidya/adapters/README.md
- epyc-root:scripts/coordination/taskflow/harness/local_llm.py
approach: 'Add a small adapter that reads a round''s proofs.json, results.jsonl and RESULT.json and projects each task outcome
  (tier, arm, task features) and each phase''s perf as ClaimTuples through the existing measurement carrier. Bind identities
  from proofs.json at write time; call the hook from the row job at phase end. Pre-hook rounds stay committed-conclusion observations.

  '
acceptance: a canary round written after the hook lands yields ClaimTuples for every task and phase that claim_tuple.grade()
  accepts, and the planning-context canary passes
non_goals:
- no new grading ladder
- no retrospective warrant for r1-r8 rounds
- no change to dispatch verdict logic
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/taskflow/dispatch.py: b2de30aae006e9f40c1c043f58e52aa98bc293b6
    epyc-root:scripts/vidya/adapters/README.md: 88bcb97603a2c03c604fbef950ad5a33df10ec0e
    epyc-root:scripts/coordination/taskflow/harness/local_llm.py: 0952a3eab321e07064b0ba2a0b7d09fd8c2545b2
---
