---
schema: epyc.brief.v1
id: UFH14-TOOLS-1
box_text_sha: 1aaec29898547313
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:orchestration/tool_surface_allowlist.yaml
- epyc-orchestrator:src/features.py::tool_surface_cap
approach: 'Code landed (flags tool_surface_logging and tool_surface_cap, default off). Remaining: populate orchestration/tool_surface_allowlist.yaml
  per role from measured per-turn usage in logs/tool_surface/ (frontdoor calls a tool in only 3.8-4.9% of turns), then the
  A/B with the cap on vs off (prompt tokens, task accuracy, tool-call success). Stop when each role has an allowlist from
  >=200 logged turns. First step: usage aggregation script over logs/tool_surface.

  '
acceptance: grep -c ':' /workspace/repos/epyc-orchestrator/orchestration/tool_surface_allowlist.yaml | grep -qv '^0$'
non_goals:
- no default-on cap
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:orchestration/tool_surface_allowlist.yaml: c38cc5f710e35ffdc77cff5915acee54d351fed6
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
