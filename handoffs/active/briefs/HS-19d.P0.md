---
schema: epyc.brief.v1
id: HS-19d.P0
box_text_sha: cc524de129c18bde
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/hs19d-p0-seed-corpus-20261102.md
- epyc-root:artifacts/hs19d-preflight/source-preflight-20261102.md
- epyc-root:artifacts/hs19d-preflight/hs19a-tap-inventory-20261102.md
- epyc-root:artifacts/hs19d-preflight/probe-tap-inventory-20261102.md
approach: 'Epic; first concrete step: the offline multi-call test. Add a canned two-tool_calls response test proving /v1 passes
  more than one tool_calls through, and read the served templates'' supports_parallel_tool_calls. Later steps in the box (frozen
  corpus, tap join, VB-DISPATCH-S2 wiring) follow. Box has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_v1_multi_tool_calls_passthrough.py
new_tests:
- tests/unit/test_v1_multi_tool_calls_passthrough.py
non_goals:
- no inference
- P1+ frozen until UFH-13 verdict
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/hs19d-p0-seed-corpus-20261102.md: b7da86f66c64b6ea8f3c62607ecba10de553faf5
    epyc-root:artifacts/hs19d-preflight/source-preflight-20261102.md: 023a054a8157c085b65f504a2af6bdc0b65c21fe
    epyc-root:artifacts/hs19d-preflight/hs19a-tap-inventory-20261102.md: a9161063156f2114ae2efad3faefc2abcd17ceaf
    epyc-root:artifacts/hs19d-preflight/probe-tap-inventory-20261102.md: a55563be395c04efdb975c1de31820059e9950ea
---
