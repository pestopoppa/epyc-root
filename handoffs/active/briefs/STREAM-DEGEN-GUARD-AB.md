---
schema: epyc.brief.v1
id: STREAM-DEGEN-GUARD-AB
box_text_sha: 6a5559fd44f7d0a8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py::stream_degeneration_guard
- epyc-orchestrator:src/backends/llama_server.py
approach: 'Question: with stream_degeneration_guard ON (MTP draft acceptance <0.2 over >=512 tokens or 6-gram repeat >=0.6),
  what are abort rate and tokens saved, and are there false aborts? Run an A3B-served agentic suite through the orchestrator,
  guard on vs off, inspect every aborted output by hand. Stop when >=300 streamed requests per arm or >=10 aborts reviewed.
  Decision: default-ON for the guard.

  '
acceptance: grep -q 'STREAM-DEGEN-GUARD-AB.*RESULT' handoffs/active/harness-program.md
non_goals:
- no default flip in this box
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-orchestrator:src/backends/llama_server.py: 944dc58f251001af0044976dcc07484efdd45b6f
---
