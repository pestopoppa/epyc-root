---
schema: epyc.brief.v1
id: PREFIX-CACHE-LAYOUT-AB
box_text_sha: 482736ebaea9d04d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py::prompt_stable_prefix
- epyc-orchestrator:src/llm_primitives/inference.py
- epyc-orchestrator:scripts/analysis/prefix_cache_report.py
approach: 'Question: prefix-cache hit rate cache_n/(cache_n+prompt_n) and wall time with the three flags prompt_stable_prefix,
  history_append_only, tool_output_bound all ON vs all OFF on an A3B-served agentic run through the orchestrator. Hit rate
  is already captured per call (inference.py ~1143-1154), no new code. Fallback only if the hit rate disappoints: default-off
  per-message-block digest log. Stop when >=30 tasks per arm or paired effect clear. Decision: default-ON for the layout flags.

  '
acceptance: grep -q 'PREFIX-CACHE-LAYOUT-AB.*RESULT' handoffs/active/harness-program.md
non_goals:
- no default flip in this box
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-orchestrator:src/llm_primitives/inference.py: 95df5e5fe8b106f53d2d32ab0a13f7d2085f96f2
    epyc-orchestrator:scripts/analysis/prefix_cache_report.py: dbf69f359009287e90c0db9e6645185adee48d99
---
