---
schema: epyc.brief.v1
id: HIL-LB1a
box_text_sha: 0d7aeae8c99846c6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/trace/hil_lb1a_label_tap.py
- epyc-orchestrator:tests/unit/test_hil_lb1a_tap_label.py
- epyc-orchestrator:src/backends/llama_server.py
approach: 'Historical request flags were not recorded so the 16 apparent cuts stay unproven; a controlled unconstrained request
  was cut mid-JSON and the Locals TOOLS profile also fired. Next: implement the default-off per-request opt-out of the free-form
  streaming repetition guard as a feature flag and run the planned A/B (plan in progress/2026-10/2026-10-29.md) on unconstrained
  JSON-shaped prompts, guard on vs off, counting cut-vs-valid-JSON. Stop when 30 prompts per arm; decision: whether to scope
  the guard off for JSON-shaped replies.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_hil_lb1a_tap_label.py
non_goals:
- no default-on change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/trace/hil_lb1a_label_tap.py: 767fa41a77cc7cdb0310030e2fd0f7d3957247cf
    epyc-orchestrator:tests/unit/test_hil_lb1a_tap_label.py: b13830339fd2c9789b72da936065e0e9821b4c72
    epyc-orchestrator:src/backends/llama_server.py: 944dc58f251001af0044976dcc07484efdd45b6f
---
