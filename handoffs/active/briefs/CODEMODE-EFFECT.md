---
schema: epyc.brief.v1
id: CODEMODE-EFFECT
box_text_sha: t:d5dd532e06d6b440
author: intake
written: '2026-11-22'
accepted: pending
where:
- epyc-orchestrator:src/registry/tool_registry.py
- epyc-orchestrator:src/graph/session_log.py
approach: 'Add a retry-safety effect class {none, idempotent, external} to Tool in tool_registry.py, derived from the existing
  SideEffect enum (READ_ONLY -> none; undeclared or side-effecting -> external unless declared idempotent). Before dispatching
  an external tool, append and flush a call record to the session journal (session_log.py); after it returns append a result
  record. On REPL/session resume, fold the journal: an external call with a call record and no result returns an explicit
  unknown result to the model and is never re-dispatched; none/idempotent calls rerun (idempotent with the call id as key).
  Seeded crash-injection test with planted mutations (redispatch-after-recovery, flush-after-dispatch) that the test must
  catch. Pattern from harnesslang (intake-2790).

  '
acceptance: python3 -m pytest -q tests/unit/test_tool_effect_recovery.py
new_tests:
- tests/unit/test_tool_effect_recovery.py
non_goals:
- no cell-level replay divergence check (monitor until cells are resumable)
- no inference; scripted model only
tier: terra
grounded:
  at: '2026-11-22'
  blobs:
    epyc-orchestrator:src/registry/tool_registry.py: c8320d5f66e79f1a1248941019d9ff609d0a415d
    epyc-orchestrator:src/graph/session_log.py: 41b42f0581971def4e8388e3ac29abf759ab2574
---
