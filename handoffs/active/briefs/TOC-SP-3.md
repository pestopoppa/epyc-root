---
schema: epyc.brief.v1
id: TOC-SP-3
box_text_sha: 50204ebbec0ceb80
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/environment.py
approach: 'Verified-quote receipt for the spill worker summary: _spill_output (environment.py:907) must attach verified quotes.
  First step: receipt function with unit tests in the REPL environment.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-SP\-3\b' handoffs/active/context-and-token-economy.md
new_tests:
- tests/unit/test_spill_output_receipt.py
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/environment.py: cd93f9e4825452efdf31e0f2e81efa7b8142aecc
---
