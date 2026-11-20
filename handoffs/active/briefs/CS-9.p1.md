---
schema: epyc.brief.v1
id: CS-9.p1
box_text_sha: 103af1ce4da93001
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/speech/cs6-second-gpu-bench-plan.md
- epyc-inference-research:scripts/voice/probe_latency.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Run the declared arms per the box (card 2, 35B-A3B at np 1/4/..., speech on/off, CU-mask arm); record per-arm p95
  LLM tok/s per slot, speech TTFA/RTF, VRAM per co-tenant and a CU-mask PASS/FAIL on speech-reservation protection; stop on
  futility per measurement-sufficiency.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-9.p1\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/speech/cs6-second-gpu-bench-plan.md: a9d9508cc7dd29183e3a9a9253dff1da3fe37729
    epyc-inference-research:scripts/voice/probe_latency.py: b3f79199e08f2999eb3a190ac1f81482b83eebee
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
