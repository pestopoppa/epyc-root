---
schema: epyc.brief.v1
id: CS-8.LEX2
box_text_sha: 6fe977cdc792c7a8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/stt_bakeoff/lexicon.py
- epyc-inference-research:scripts/speech/stt_bakeoff/boost_guard.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Report-only lexicon-boosting trial on Nemotron 3.5 streaming through NeMo-Speech.cpp speech_contexts, pre-declared
  before scoring; uses lexicon.py and boost_guard.py.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.LEX2\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/stt_bakeoff/lexicon.py: e596bee43ab84859dde37a5643b4bad807827df4
    epyc-inference-research:scripts/speech/stt_bakeoff/boost_guard.py: 7d46eb60990ba83f55af8735c5427a2c12d330d7
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
