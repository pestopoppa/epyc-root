---
schema: epyc.brief.v1
id: TOOLCALL-PARSE-CLIENT-AB
box_text_sha: 05b6c1a68fcc5bf6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py::tool_call_parse_error_retry
- epyc-orchestrator:src/backends/llama_server.py
- epyc-orchestrator:scripts/analysis/prefix_cache_report.py
approach: 'Question: with tool_call_parse_error_retry and tool_call_arg_leak_guard ON, what are retry rate and retried_ok
  share on a tool-heavy A3B (Qwen3.6-35B-A3B) run, per role and trigger counters from llama_server. Run a tool-heavy seeding/codemode_ab
  suite through the orchestrator with each flag on vs off. Stop when >=100 tool calls observed per arm or on futility (stack
  down). Decision: default-ON for either flag; re-check after PFXC-TOOLPARSE is in a promoted kernel and remove the arg-leak
  guard if it never fires.

  '
acceptance: grep -q 'TOOLCALL-PARSE-CLIENT-AB.*RESULT' handoffs/active/harness-program.md
non_goals:
- no default flip in this box
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-orchestrator:src/backends/llama_server.py: 944dc58f251001af0044976dcc07484efdd45b6f
    epyc-orchestrator:scripts/analysis/prefix_cache_report.py: dbf69f359009287e90c0db9e6645185adee48d99
---
