---
schema: epyc.brief.v1
id: TOOLPERM-DENY-DEFAULT
box_text_sha: 070d379c03e87943
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/registry/tool_registry.py
- epyc-orchestrator:orchestration/model_registry.yaml
approach: 'A role without tool_permissions currently gets all 65 tools (13 of 15 roles). Implement deny-default in load_permissions_from_registry
  (no tool_permissions means no tools plus a startup warning) and give every tool-using role an explicit allowlist (architect_general/critic:
  web, data, llm; coder_escalation and toolrunner: all explicit; worker_math: math and data; rest from per-role use audit).
  Operator-signed package backup /mnt/raid0/llm/tmp/toolperm-deny-default-signed-20261111.patch; external gate is production
  relaunch plus contention_matrix refresh. Step: code the deny-default with a before/after resolution diff test for all roles;
  the registry edit ships through stack-change.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_tool_permissions_deny_default.py
new_tests:
- tests/unit/test_tool_permissions_deny_default.py
non_goals:
- no registry edit outside stack-change
- no relaunch
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/registry/tool_registry.py: c8320d5f66e79f1a1248941019d9ff609d0a415d
    epyc-orchestrator:orchestration/model_registry.yaml: 8dd5725e9a06ee932ec62cc366ec0c9898884dfe
---
