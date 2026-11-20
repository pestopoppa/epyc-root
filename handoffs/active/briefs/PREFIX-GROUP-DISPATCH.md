---
schema: epyc.brief.v1
id: PREFIX-GROUP-DISPATCH
box_text_sha: 6853cb7dfbcbc9d6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat_pipeline/scout_stage.py
- epyc-orchestrator:src/typed_decisions/fanout_policy.py
- epyc-root:handoffs/active/harness-program.md
approach: 'Parent of PREFIX-GROUP-MEASURE (done: concurrent same-port shared prefix ~0 in tap-era traffic, gate NOT met),
  REMEASURE and POLICY. First concrete step is the REMEASURE child once request bodies are logged: rerun the offline LCP analysis
  over the new tap. Parent closes when POLICY is built (if gate met) or declined with the number. Box is a coordination parent;
  acceptance is the closest check.

  '
acceptance: grep -q 'PREFIX-GROUP-REMEASURE.*RESULT' handoffs/active/harness-program.md
non_goals:
- no dispatcher change before the gate is met
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat_pipeline/scout_stage.py: 5ed48af7db1ae4a7fcad3120d604835b55a0a428
    epyc-orchestrator:src/typed_decisions/fanout_policy.py: b00e3eb3ca0317bd5059bd124769858809e5e3bc
    epyc-root:handoffs/active/harness-program.md: 3cb5ef0d88bd7c907a51544f584b042ea93e3a23
---
