---
schema: epyc.brief.v1
id: INK2-INKBLOT-ART
box_text_sha: t:5bdd2fd6be412ecb
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:handoffs/active/model-evaluation-queue.md@23e9ec151
- epyc-llama:convert_hf_to_gguf.py@3d01b5e50
- epyc-llama:tools/quantize/quantize.cpp@3d01b5e50
approach: 'Verify the pinned source LFS hashes and all corresponding per-tensor bytes, including expert and vision tensors.
  Record type exceptions. Use one converter, quantizer, importance matrix policy and template, bind both GGUF hashes, then
  perform the structural CPU reload with MTP off. See the approved study protocol for the release identities.

  '
acceptance: Both input shard hashes, all 1,244 named tensors, comparison classifications, quantizer and converter revisions,
  output hashes, tokenizer and template identities are recorded. Unexpected expert or vision changes and any conversion drift
  have explicit dispositions.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:handoffs/active/model-evaluation-queue.md@23e9ec151: 3230bfdbda2f2007ba1863de231905c8d47039fd
    epyc-llama:convert_hf_to_gguf.py@3d01b5e50: 2c5e62a16fbef67ef1bba243df7e3aa7b4de1543
    epyc-llama:tools/quantize/quantize.cpp@3d01b5e50: 15ef64c4b0edc8ab0934277df3f7f449aa0861d9
---
