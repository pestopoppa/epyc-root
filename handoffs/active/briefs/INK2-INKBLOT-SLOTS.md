---
schema: epyc.brief.v1
id: INK2-INKBLOT-SLOTS
box_text_sha: t:6b5a88d1a82c8c26
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu@2a335259
- epyc-inference-research:scripts/utils/verify_ggml_linkage.sh
approach: 'Use the port’s re-homed indexed-bias inputs and verify residency and linkage during decode. Fix the Base GGUF,
  FA, f16 KV, template, cap, context, seed and two configured slots. Replay all 12 frozen tool prompts with one busy slot
  and two, saving output, stop cause and slot mapping. Repeat a diverging ID twice before diagnosing. See the approved HIP
  brief for the conditional q8_0 arm.

  '
acceptance: The same 12 frozen tool IDs have raw outputs, slot and stop records under both occupancy settings, plus recorded
  backend residency and a repeat or parity verdict for every ID.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu@2a335259: 6e8372791c5fc6b198f48ce77134cb0a5c07412e
    epyc-inference-research:scripts/utils/verify_ggml_linkage.sh: 95ef3425c545f582c8749e4fed95fdda53490148
---
