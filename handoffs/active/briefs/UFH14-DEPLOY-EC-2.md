---
schema: epyc.brief.v1
id: UFH14-DEPLOY-EC-2
box_text_sha: 2850ee23c1b42b83
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat.py
- epyc-orchestrator:src/backends/serving_calls.py
approach: 'Live proofs after the :8083 restore: (1) one completed live /chat with review_gate / review_verdict null (RI-18c;
  needs CPU regions free); (2) one dispatched primitives-lane record carrying request.prefix_fp (B4); plus the pending B6
  streamed completion with timings and the KVU-15a 2-worker replay. First step: a checker that greps dispatch.jsonl for prefix_fp
  and the /chat response for null review fields. Operational; needs live stack.

  '
acceptance: grep -q 'prefix_fp' /workspace/repos/epyc-orchestrator/logs/dispatch/dispatch.jsonl
non_goals:
- no source change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat.py: f5b585c6c630d4001b279ea37be22e908fe3b54f
    epyc-orchestrator:src/backends/serving_calls.py: eeb700373c1e14620d6defeba6a6122c884e64b9
---
