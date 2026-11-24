---
schema: epyc.brief.v1
id: SPEC-ID-NOISE-2
box_text_sha: t:b54b900d580e94d3
author: planning
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:common/common.h
- epyc-llama:examples/eval-callback
- epyc-llama:ggml/src/ggml-cuda/mmq.cu
approach: 'Reuse the SPEC-ID-NOISE-1 job.py and prompt digest. Arm A: 4 relaunches, leave-one-out gate calls. Arm B: export
  GGML_HIP_Q8_SKINNY=0 and rerun the same 64 prompts. Arm C: build eval-callback with a cb_eval hook that sha256-hashes each
  tensor by name, diff the two launch logs and record the first mismatching node. Arm D: CPU quarter, -ctk f32 -ctv f32 with
  LLAMA_SPEC_EXACT=serial vs default, resume vs fresh.

  '
acceptance: 'per-arm verdicts filed under this box with the run path: arm A pass/false-FAIL count, arm B divergence count
  out of 64, arm C first-divergent node name per prompt, arm D divergence count out of 64'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:common/common.h: ee56c9fb24fdec6bf5f902c14d0c176418dadc9b
    epyc-llama:examples/eval-callback: tree:91ea2ad7cf9c80863025b89c07407d186939be03
    epyc-llama:ggml/src/ggml-cuda/mmq.cu: 0dd68ebfb61dcc209f00db12479085707461dba6
---
