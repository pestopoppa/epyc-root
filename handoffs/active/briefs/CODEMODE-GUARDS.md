---
schema: epyc.brief.v1
id: CODEMODE-GUARDS
box_text_sha: t:33e78dcc600dec24
author: intake
written: '2026-11-22'
accepted: pending
where:
- epyc-orchestrator:src/repl_environment/codemode_tools.py
approach: 'Behind a new FeatureSpec flag registered on the autopilot manipulation surface: (a) count nested calls per tool
  within one code-mode cell and refuse calls over a configurable cap with a structured non-retryable error {code: call_limit,
  retryable: false, message: batch the work into fewer calls or split it across cells}; (b) when a cell''s output exceeds
  the result budget, keep head and tail and replace the middle with a marker stating the original token count and line total.
  Pattern from nanocode Code Mode (intake-2789).

  '
acceptance: python3 -m pytest -q tests/unit/test_codemode_guards.py
new_tests:
- tests/unit/test_codemode_guards.py
non_goals:
- no default-on flip without a measured improvement
tier: terra
grounded:
  at: '2026-11-22'
  blobs:
    epyc-orchestrator:src/repl_environment/codemode_tools.py: cfaae2f92b9ccbc95cefa49fdcb66c24017955aa
---
