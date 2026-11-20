---
schema: epyc.brief.v1
id: CS-4
box_text_sha: 9b61eb7578aa7a22
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/voice/turn_taking/tt_spec.py
- epyc-inference-research:scripts/voice/turn_taking/tt_corpus.py
- epyc-inference-research:scripts/voice/turn_taking/tt_verify.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Epic: first step is to extend the corpus builder to emit the five sets under Annex S rules (PCM-SHA-256 bound,
  selection and confirmation splits disjoint) starting with the sets that need no human recording; human-recorded strata stay
  empty until the operator records them.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-4\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/voice/turn_taking/tt_spec.py: 1e1f982d765f6c43725fb177e10afa93650a50d0
    epyc-inference-research:scripts/voice/turn_taking/tt_corpus.py: eb01ef9d93fd5319495810de8582a28b549c421b
    epyc-inference-research:scripts/voice/turn_taking/tt_verify.py: cb53ca1ee5d9e30754e7db87e0414c2d61ec29cc
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
