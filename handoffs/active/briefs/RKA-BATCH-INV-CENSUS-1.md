---
schema: epyc.brief.v1
id: RKA-BATCH-INV-CENSUS-1
box_text_sha: t:3f4c9872db292da6
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:ggml/src/ggml-cuda/mmvq.cu
- epyc-llama:ggml/src/ggml-cuda/fattn-common.cuh
approach: 'Read each listed kernel''s launch-parameter code and record which parameters depend on ncols/n_tokens/n_kv (nwarps,
  parallel_blocks, split count) and where atomics or reduction-order changes occur. Fill a table of op, dependency, required
  change and estimated LOC/perf cost. No build or run.

  '
acceptance: 'per-op census table committed in this handoff with the commit SHA recorded under this box, and the verdict: open
  an implementation box for a default-off invariant audit arm if 3 or fewer ops need change, else record the cost and close'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/mmvq.cu: 77f711be4fd5b88e514d3f4ecfb3c91e9346164f
    epyc-llama:ggml/src/ggml-cuda/fattn-common.cuh: e67cc7fdf784c18bc4ce93918005cbf048148c26
---
