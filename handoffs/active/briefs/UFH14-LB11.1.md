---
schema: epyc.brief.v1
id: UFH14-LB11.1
box_text_sha: 6dcfca5e1f643b7d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py::repl_think_fence_continue
- epyc-orchestrator:src/features.py::thinking_roles_chat_lane
- epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py
approach: 'Code landed flag-off (f3ab78b2): counter turn_ended_in_unclosed_think and parse_event think_fence_cut are live;
  option (b) bounded continuation behind repl_think_fence_continue default OFF; (c) thinking_roles_chat_lane for architect_critic/coder_escalation/ingest_long_context
  after RI-23b. Question: Max-nudges rate on coder_escalation with (b) vs (c) vs baseline. Step 1: read the counter on live
  traffic; step 2 A/B the flags. Stop when >=100 coder_escalation turns per arm. Decision: which flag to default on.

  '
acceptance: grep -q 'UFH14-LB11.1.*verdict' handoffs/active/harness-program.md
non_goals:
- no dropping of the fence stop (option a rejected)
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py: 57c230f9f7cc16cf5076c10729601290804d6292
---
