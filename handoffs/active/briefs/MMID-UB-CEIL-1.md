---
schema: epyc.brief.v1
id: MMID-UB-CEIL-1
box_text_sha: t:348a156e221885c0
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-orchestrator:scripts/server/orchestrator_stack.py
- epyc-llama:ggml/src/ggml-cuda/mmid.cu
approach: 'In orchestrator_stack.py, beside _has_any_flag''s K4 check, parse -ub/--ubatch-size for GPU MoE roles and refuse
  values above 16384 with a clear message, plus a pytest case. On ROCm0, run test-backend-ops -o MUL_MAT_ID with a 16384-token
  and a 16385-token case (Q4_0, n_used 2) and record pass vs GGML_ASSERT abort.

  '
acceptance: guard committed with a unit test and its SHA, and the smoke result (pass at 16384, abort at 16385, or the measured
  ceiling if different) recorded under this box
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-orchestrator:scripts/server/orchestrator_stack.py: 4ae8d93cc08e26ac81584ca95ab566af86914394
    epyc-llama:ggml/src/ggml-cuda/mmid.cu: f80442fbe4e81f3e91fefd26ddf6109d4f9ffaaa
---
