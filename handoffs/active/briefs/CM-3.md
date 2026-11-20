---
schema: epyc.brief.v1
id: CM-3
box_text_sha: 776be460b3988a3c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/codemode_tools.py::check_shape_consistency
- epyc-orchestrator:src/registry/tool_registry.py
- epyc-orchestrator:tests/unit/test_codemode_cm45.py
approach: 'Code landed flag-gated (ORCHESTRATOR_STRUCTURED_READ_ONLY). Remaining: run check_shape_consistency against every
  REAL read-only tool handler with realistic args at probe-5 and max-batch sizes (the intake-2675 failure mode) and add a
  consumer-tolerance check (errors become envelopes). Add the test that no read-only tool in the registry returns a bare string
  on success.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_codemode_shape_all_readonly.py
new_tests:
- tests/unit/test_codemode_shape_all_readonly.py
non_goals:
- no write-tool shape change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/codemode_tools.py: cfaae2f92b9ccbc95cefa49fdcb66c24017955aa
    epyc-orchestrator:src/registry/tool_registry.py: c8320d5f66e79f1a1248941019d9ff609d0a415d
    epyc-orchestrator:tests/unit/test_codemode_cm45.py: 12412b307efe50f6be4a79ef18c1a02cd9975107
---
