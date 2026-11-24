---
schema: epyc.brief.v1
id: MMVF-I64-OFFSET
box_text_sha: t:e2ef3b91fac31e57
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:ggml/src/ggml-cuda/mmvf.cu
- epyc-llama:ggml/src/ggml-cuda/ggml-cuda.cu
approach: 'Use the prepared gate directory: run its job on the MI210 against the branch build at 7eb398b16 (test-backend-ops
  -o MUL_MAT,MUL_MAT_ID plus perf at ne11 1-8 with the route-log env), compare against C21''s A/A floor, and file RESULT.json.
  Evaluate c47c574ba and 7eb398b16 separately via the per-commit arms the gate defines.

  '
acceptance: 'gate RESULT filed under this box with the run path: test-backend-ops correctness 100% on ROCm0, MUL_MAT perf
  at ne11 1-8 within the A/A floor and route histograms unchanged for each of c47c574ba and 7eb398b16'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/mmvf.cu: d7dbc8b992820c5da385575526a85a7524a6aaa2
    epyc-llama:ggml/src/ggml-cuda/ggml-cuda.cu: fe4652125893551b139328a54d4b243ccaba3bf2
---
