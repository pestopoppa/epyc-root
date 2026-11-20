---
schema: epyc.brief.v1
id: SELECTOR-HARDEN
box_text_sha: 2b07f26072cbb187
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/codemode_tools.py
- epyc-orchestrator:scripts/benchmark/codemode_ab/run_probe.py
- epyc-orchestrator:tests/unit/test_tool_selector_codemode_ab.py
approach: 'Code is on orchestrator main (hardened C1 picker, pooled-embedder providers, flags, per-model validation harness
  128ea5ec). The box stays open for the multi-model validation: run the per-model picker validation (recall, recovery, breaker,
  latency) on each stack model including the Flash row, using the existing harness; inputs-missing SELECTOR_HARDENING.md should
  be regenerated from the v2 evidence. Stop when every stack model has a filed picker verdict or on futility. Feeds CODEMODE-REL-FLIP.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_tool_selector_codemode_ab.py
non_goals:
- no default flips
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/codemode_tools.py: cfaae2f92b9ccbc95cefa49fdcb66c24017955aa
    epyc-orchestrator:scripts/benchmark/codemode_ab/run_probe.py: ef3dc45146cf2191a70dce3fa3bcb1576a3f31ca
    epyc-orchestrator:tests/unit/test_tool_selector_codemode_ab.py: 067f989ca589d8652250550a35521078e73b3524
---
