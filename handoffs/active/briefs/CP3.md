---
schema: epyc.brief.v1
id: CP3
box_text_sha: 07783c7fbc27f7a1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/proactive_delegation/review_service.py::_render_outputs
- epyc-orchestrator:tests/test_candidate_security.py::TestInContentInjectionGap
approach: 'Wrap candidate output refs in _render_outputs in an explicit control/data delimiter with delimiter-escape of embedded
  delimiter text so the payload no longer appears as bare prompt text; flip xfail on test_desired_property_injection_is_quarantined
  and update the verbatim-LIVE test to the new contract.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest tests/test_candidate_security.py::TestInContentInjectionGap
  -q
non_goals:
- No change to the assembly sanitizer; no live reviewer run
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/proactive_delegation/review_service.py: b80f42a995029f228c99826e68a86aefad26322b
    epyc-orchestrator:tests/test_candidate_security.py: 32bcde6941b33e0ac7ade182f4b4da85dc0d3418
---
