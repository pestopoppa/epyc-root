---
schema: epyc.brief.v1
id: REPL-EMB-2.12
box_text_sha: a099f2a0f88680f9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/embedding_dims.py
- epyc-orchestrator:scripts/benchmark/repl_emb_eval.py
- epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md
approach: 'Question: EG2 throughput (sets INDEX_ASSUMED_TEXTS_PER_S, 25 in code vs 3.5 provisional; MAX_DENSE_CHUNKS), decode
  interference at 3 text sizes (floor 0.86; BGE post-cap 0.921/0.918/0.862), memory (G-T1, G-1, G-2, G-3, G-M), plus EG2 GPU
  timing on the MI210 (HIP and Vulkan), inside the frozen REPL-EMB-0.3 package in the v11 full-stack window. Prep: the measurement
  driver and the row spec with contention labels. Stop on all gates measured or futility on host contention. Decision: set
  the index constants.

  '
acceptance: grep -q 'REPL-EMB-2.12.*RESULT' handoffs/active/harness-program.md
non_goals:
- no promotion
- accuracy work is not performance-sensitive
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/embedding_dims.py: f46c27a24ee2b7954b3be576fb78a48e744190c6
    epyc-orchestrator:scripts/benchmark/repl_emb_eval.py: 1668d4b48c04da06ee4229a3bf65ccc925d48256
    epyc-root:docs/reference/kernel-manifests/llama-v11-manifest.md: 291a8f44609f92978b78ff5504893ecf8d129bf4
---
