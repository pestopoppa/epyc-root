---
schema: epyc.brief.v1
id: CS22-ALIGNMENT-INTEGRATE
box_text_sha: e5480657cb80fae0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/voice/turn_taking/tt_spec.py
- epyc-inference-research:scripts/voice/turn_taking/tt_align_fw.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Carry the reviewed isolated frontend/precision fix into a fresh experimental speech candidate, validate vs the
  original reference policy, then satisfy V1; no frozen-speech edit; first step is the cherry of the fix onto a fresh candidate.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS22-ALIGNMENT-INTEGRATE\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/voice/turn_taking/tt_spec.py: 1e1f982d765f6c43725fb177e10afa93650a50d0
    epyc-inference-research:scripts/voice/turn_taking/tt_align_fw.py: 0e985f63b44e0884fa07354b59f3e9b6c959754c
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
