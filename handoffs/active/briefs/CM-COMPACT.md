---
schema: epyc.brief.v1
id: CM-COMPACT
box_text_sha: t:8d3620547c5b6676
author: intake
written: '2026-11-22'
accepted: pending
where:
- epyc-orchestrator:scripts/benchmark/codemode_ab/run_probe.py
- epyc-orchestrator:scripts/benchmark/codemode_ab/arms.py
approach: 'Step 1 (no inference): write a compact variant of the code-mode prompt tool-catalog description (names plus one-line
  descriptions, schemas on demand) and a script that counts prompt tokens, compact vs current, over the CODEMODE-AB-V2 task
  set. Step 2 is a separately booked inference row: paired C3 vs C3+compact on 35B and 27B reusing 30 pairs per arm; stop-on-answer
  = token cut of 25% or more with success delta inside pair noise, futility = cut under 10%. Pattern from nanocode''s compact
  exec description (intake-2789).

  '
acceptance: python3 -m pytest -q tests/unit/test_codemode_compact_prompt.py
new_tests:
- tests/unit/test_codemode_compact_prompt.py
non_goals:
- intake does not run step 2; the owner books it
tier: terra
grounded:
  at: '2026-11-22'
  blobs:
    epyc-orchestrator:scripts/benchmark/codemode_ab/run_probe.py: ef3dc45146cf2191a70dce3fa3bcb1576a3f31ca
    epyc-orchestrator:scripts/benchmark/codemode_ab/arms.py: b1a5461c4dad14f3302bf56fc4edbc5cc5abf27d
---
