---
schema: epyc.brief.v1
id: TU-HR-1
box_text_sha: ed18b8c41f029ed5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/tool-rendering-source-map.md
approach: 'Read-only audit, no inference. Add a test that walks every served role in model_registry.yaml, resolves its backend
  (llama_server vs openai) and chat_template_kwargs via registry_loader, and emits a per-model route table (native tool schema
  forwarded yes/no, template source GGUF metadata vs override). Assert no served role routes through the openai backend path
  that drops tools/tool_choice. Extend the source map doc with the table; unknown GGUF template identity stays listed as unverified.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_tool_rendering_route_table.py
new_tests:
- epyc-orchestrator:tests/unit/test_tool_rendering_route_table.py
non_goals:
- no model calls, no /proc or live endpoint inspection
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/tool-rendering-source-map.md: 46edd94e81d16223bcf00b376a276d50dc9ad473
---
