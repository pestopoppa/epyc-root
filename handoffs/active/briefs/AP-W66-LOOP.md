---
schema: epyc.brief.v1
id: AP-W66-LOOP
box_text_sha: t:1175484c98ad7937
author: planning
written: '2026-11-27'
accepted: auto
where:
- epyc-root:docs/reports/autopilot-w66-replay-plan.md
- epyc-orchestrator:scripts/autopilot/eval_tower.py
approach: 'Extend the existing serving-call recorder/report consumer and eval tower''s task-rate/goodput path in epyc-orchestrator
  (src/backends/serving_calls.py, scripts/autopilot/eval_tower.py). Emit a versioned, optional phase breakdown keyed to trial,
  request and stream. Run the real report entry point on saved slow-prefill, slow-decode, missing-counter and legacy records.
  Verify distinct evidence for each, unknown fields remain unknown, and aggregate concurrency is counted once. Demonstrate
  a shadow planner/journal decision on a held-out trace: heavy fresh-prefill seconds suggests testing prefix retention; a
  reproducible decode loss during peer prefill suggests testing admission/batch scheduling; slow isolated decode with matched
  context suggests a kernel/recipe investigation. Record evidence and uncertainty when none applies. Reuse AP-72 for physical
  ceilings and VB-TASKFLOW-CANARY-PERF-WIRE for prospective provenance. Evaluate any proposed change by accepted tasks per
  hour at equal quality, reporting paid effort separately.

  '
acceptance: the actual report and journal entry point distinguish prefill, decode and insufficient evidence with source receipts,
  pass legacy/missing-counter controls, and preserve quality-qualified goodput.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:docs/reports/autopilot-w66-replay-plan.md: ec15417f839d78efe2cc894c3d9a77e3c8fc43d9
    epyc-orchestrator:scripts/autopilot/eval_tower.py: 37c36d7abf5bad63946ab1fb50d1c2e3548313dd
---
