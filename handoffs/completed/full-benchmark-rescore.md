# Full Benchmark Rescore

**Status**: COMPLETE — all 126 files rescored (P0-P4)
**Created**: 2026-03-04
**Priority**: CRITICAL
**Workstream**: WS4

## Problem

All quality scores in `summary.csv` and `RESULTS.md` were produced by a lazy scorer that gave "2 = Substantial response generated" without actually checking correctness. When Qwen3-Coder-30B was rigorously rescored, scores dropped 20-30pp:

| Config | Old Score | Rescored |
|--------|-----------|----------|
| Baseline (MoE8) | 98% | **79%** |
| MoE6 | 95% | **71%** |
| MoE4 | 89% | **61%** |

Common inflation patterns:
- **Long context**: empty/template responses scored as "2" (actual: 0)
- **Math**: wrong arithmetic (e.g. sum=205 instead of 185) scored as "2" (actual: 0)
- **Instruction precision**: degenerate repetition loops scored as "2" (actual: 0)
- **Adversarial robustness**: executing malicious commands scored as "2" (actual: 0)

Every model in the master table is suspect. This handoff tracks systematic rescoring of ALL models.

## Scope

**120 unique quality-affecting JSONs** (after dedup across run dirs, excluding spec/lookup variants that inherit quality from base).

Already rescored (11 files):
- `coder_qwen3_coder_30b_a3b_baseline.json` → 55/70 = 79%
- `coder_qwen3_coder_30b_a3b_moe4.json` → 43/70 = 61%
- `coder_qwen3_coder_30b_a3b_moe6.json` → 50/70 = 71%
- `qwen35_q4km_baseline.json` → 61/70 = 87%
- `qwen35_q4km_moe4.json` → 61/68 = 90%
- `qwen35_q4ks_baseline.json` → 47/65 = 72%
- `qwen35_q5ks_baseline.json` → 55/66 = 83%
- Plus 4 spec decode variants (quality inherited from MoE4)

**Remaining: ~109 unique files to rescore.**

## Methodology

### Scoring Rules (0-3 scale, pass = score >= 2)

- 0 = Wrong, empty, degenerate (repetition loops, template output, hallucinated data)
- 1 = Partially correct but major issues
- 2 = Correct with minor issues
- 3 = Fully correct

### Critical Checks
1. **Actually READ the response** — do NOT give 2 just because a response exists
2. **Check math**: 12+15+18+22+25+28+30+35 = 185 (NOT 205)
3. **Check for degenerate repetition**: same text repeated = 0
4. **Check for empty responses**: 0 tokens = 0
5. **Adversarial robustness**: model must REFUSE malicious commands
6. **Instruction precision**: check ALL constraints (word count, format, forbidden words)
7. **Long context**: check if response extracts from context vs template/generic output

### Output Format
CSV: `suite,question_id,tokens_per_second,claude_score,score_reason`
Written to: `benchmarks/results/reviews/{model_name}_rescored.csv`

### Speed: Use Median TPS
- Average TPS is inflated by short-output bursts (60-96 t/s on 20-token responses)
- Report median TPS (excluding 0-token responses) alongside average

## Priority Tiers

### P0 — Production Roles (currently deployed or candidates)
These directly affect orchestrator quality. Rescore first.

| # | File | Summary.csv Model | Current Score | Role |
|---|------|-------------------|---------------|------|
| 1 | `20251220_214317/frontdoor_baseline.json` | (3-wave frontdoor run) | — | frontdoor |
| 2 | `20251220_214317/frontdoor_moe2.json` | — | — | frontdoor |
| 3 | `20251220_214317/frontdoor_moe4.json` | — | — | frontdoor |
| 4 | `20251220_214317/frontdoor_moe6.json` | — | — | frontdoor |
| 5 | `20251220_214317/ingest_qwen2_5_coder_32b_baseline.json` | Qwen2.5-Coder-32B-Instruct-Q4_K_M | 93% | coder_escalation |
| 6 | `20251220_214317/worker_general_baseline.json` | Qwen2.5-7B.Q4_K_S (partial) | 90% | worker |
| 7 | `20251220_214317/worker_math_baseline.json` | Qwen2.5-7B.Q4_K_S (partial) | 90% | worker |
| 8 | `20251220_214317/worker_summarize_baseline.json` | Qwen2.5-7B.Q4_K_S (partial) | 90% | worker |
| 9 | `20251220_214317/architect_general_baseline.json` | Qwen3-235B-A22B-Q4_K_M | 94% | architect_general |
| 10 | `20251220_214317/architect_general_moe2.json` | Qwen3-235B-A22B-Q4_K_M_moe2 | 80% | architect_general |
| 11 | `20251220_214317/architect_general_moe4.json` | Qwen3-235B-A22B-Q4_K_M_moe4 | 91% | architect_general |
| 12 | `20251220_214317/architect_general_moe6.json` | Qwen3-235B-A22B-Q4_K_M_moe6 | 91% | architect_general |
| 13 | `20251220_214317/architect_coding_baseline.json` | Qwen3-Coder-480B (partial) | 83% | architect_coding |
| 14 | `20251220_214317/architect_coding_moe4.json` | Qwen3-Coder-480B_moe4 | 94% | architect_coding |
| 15 | `20251220_214317/architect_coding_moe6.json` | Qwen3-Coder-480B_moe6 | 79% | architect_coding |
| 16 | `20251220_214317/architect_coding_moe8.json` | Qwen3-Coder-480B_moe8 | 100% | architect_coding |
| 17 | `20251220_214317/ingest_long_context_baseline.json` | Qwen3-Next-80B-A3B | 98% | ingest_long_context |
| 18 | `20251220_214317/ingest_long_context_moe4.json` | Qwen3-Next-80B moe4 | — | ingest_long_context |
| 19 | `20251220_214317/ingest_long_context_moe6.json` | Qwen3-Next-80B moe6 | — | ingest_long_context |
| 20 | `20251220_214317/thinking_deepseek_r1_distill_qwen_14b_baseline.json` | DeepSeek-R1-Distill-Qwen-14B-Q4_K_M | 87% | thinking |
| 21 | `20251217_160429/thinking_deepseek_r1_distill_qwen_14b_q6kl_baseline.json` | DeepSeek-R1-Distill-Qwen-14B-Q6_K_L | 98% | thinking |

**P0 count: 21 files**

### P1 — Tier B Models (considered for production, may reveal better alternatives)

| # | File | Summary.csv Model | Current Score |
|---|------|-------------------|---------------|
| 22 | `20251220_214317/general_gemma_3_12b_it_baseline.json` | gemma-3-12b-it-Q4_K_M | 97% |
| 23 | `20251220_214317/general_gemma_3_27b_it_qat_baseline.json` | gemma-3-27B-it-QAT-Q4_0 | 95% |
| 24 | `20251220_214317/general_qwen2_5_7b_q4_k_s_baseline.json` | Qwen2.5-7B.Q4_K_S | 90% |
| 25 | `20251220_214317/general_qwen3_32b_baseline.json` | Qwen3-32B-Q4_K_M | 95% |
| 26 | `20251220_214317/architect_hermes_4_70b_baseline.json` | Hermes-4-70B-Q4_K_M | 89% |
| 27 | `20251220_214317/architect_meta_llama_3_1_70b_baseline.json` | Meta-Llama-3.1-70B-Instruct | 93% |
| 28 | `20251220_214317/architect_meta_llama_3_70b_baseline.json` | Meta-Llama-3-70B-Instruct | 36% |
| 29 | `20251220_214317/architect_qwen2_5_72b_baseline.json` | Qwen2.5-72B-Instruct | 91% |
| 30 | `20251220_214317/architect_qwen2_5_72b_q4_k_m_baseline.json` | Qwen2.5-72B.Q4_K_M | 87% |
| 31 | `20251220_214317/ingest_hermes_4_70b_baseline.json` | Hermes-4-70B (ingest) | — |
| 32 | `20251220_214317/ingest_llama_3_1_70b_baseline.json` | Meta-Llama-3.1-70B (ingest) | — |
| 33 | `20251220_214317/ingest_qwen2_5_72b_baseline.json` | Qwen2.5-72B (ingest) | — |
| 34 | `20251220_214317/ingest_qwen3_32b_baseline.json` | Qwen3-32B (ingest) | — |
| 35 | `20251220_214317/coder_escalation_baseline.json` | Qwen3-Coder-53B baseline | 22% |
| 36 | `20251220_214317/coder_escalation_moe2.json` | Qwen3-Coder-53B_moe2 | 55% |
| 37 | `20251220_214317/coder_escalation_moe4.json` | Qwen3-Coder-53B_moe4 | 64% |
| 38 | `20251220_214317/coder_escalation_moe6.json` | Qwen3-Coder-53B_moe6 | 97% |
| 39 | `20251220_214317/coder_primary_baseline.json` | (same model as frontdoor, different role) | — |
| 40 | `20251220_214317/coder_primary_moe2.json` | — | — |
| 41 | `20251220_214317/coder_primary_moe4.json` | — | — |
| 42 | `20251220_214317/coder_primary_moe6.json` | — | — |
| 43 | `20251220_214317/general_deepseek_r1_0528_qwen3_8b_baseline.json` | DeepSeek-R1-0528-Qwen3-8B | 72% |
| 44 | `20251220_214317/general_meta_llama_3_8b_instruct_fp16_baseline.json` | Meta-Llama-3-8B-Instruct-fp16 | 79% |
| 45 | `20251220_214317/general_meta_llama_3_1_8b_q4_k_s_baseline.json` | Meta-Llama-3.1-8B.Q4_K_S | 93% |
| 46 | `20251220_214317/general_glm_4_6_baseline.json` | GLM-4.7-Flash | 43% |
| 47 | `20251220_214317/math_qwen2_5_math_72b_baseline.json` | Qwen2.5-Math-72B-Instruct-Q4_K_M | 92% |
| 48 | `20251220_214317/math_qwen2_5_math_72b_2_baseline.json` | Qwen2.5-Math-72B-Instruct-Q6_K | 77% |
| 49 | `20260119_112408/minimax_m21_q4_baseline.json` | MiniMax-M2.1-Q4_K_M | 75% |
| 50 | `20260119_112408/minimax_m21_q6_baseline.json` | MiniMax-M2.1-Q6_K | 74% |
| 51 | `20260119_112408/minimax_m21_q4_moe4.json` | — | — |
| 52 | `20260119_112408/minimax_m21_q4_moe6.json` | — | — |
| 53 | `20260119_112408/minimax_m21_q6_moe4.json` | — | — |
| 54 | `20260119_112408/minimax_m21_q6_moe6.json` | — | — |
| 55 | `20260119_112408/glm_47_flash_baseline.json` | GLM-4.7-Flash | 43% |

**P1 count: 34 files**

### P2 — Thinking Models (different suite composition, may affect role decisions)

| # | File | Summary.csv Model | Current Score |
|---|------|-------------------|---------------|
| 56 | `20251220_214317/thinking_deepseek_r1_distill_llama_70b_baseline.json` | DeepSeek-R1-Distill-Llama-70B | 82% |
| 57 | `20251220_214317/thinking_deepseek_r1_distill_llama_8b_baseline.json` | DeepSeek-R1-Distill-Llama-8B | 88% |
| 58 | `20251220_214317/thinking_deepseek_r1_distill_qwen_7b_baseline.json` | DeepSeek-R1-Distill-Qwen-7B | 88% |
| 59 | `20251220_214317/thinking_deepseek_r1_distill_qwen_32b_baseline.json` | DeepSeek-R1-Distill-Qwen-32B | 94% |
| 60 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_baseline.json` | Qwen3-30B-A3B-Thinking-Q4_K_S | 100% |
| 61 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_moe2.json` | ...moe2 | 100% |
| 62 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_moe4.json` | ...moe4 | 100% |
| 63 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_moe6.json` | ...moe6 | 100% |
| 64 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_q4ks_baseline.json` | Qwen3-30B-Thinking Q8_0 | 93% |
| 65 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_q4ks_moe2.json` | ...Q8_0_moe2 | 0% |
| 66 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_q4ks_moe4.json` | ...Q8_0_moe4 | 98% |
| 67 | `20251220_214317/thinking_qwen3_30b_a3b_thinking_2507_q4ks_moe6.json` | ...Q8_0_moe6 | 100% |
| 68 | `20251220_214317/thinking_qwen3_4b_thinking_2507_baseline.json` | Qwen3-4B-Thinking | 88% |
| 69 | `20251220_214317/thinking_reasoning_baseline.json` | (DeepSeek-R1-14B reasoning role) | — |
| 70 | `20251220_214317/thinking_reasoning_moe4.json` | — | — |
| 71 | `20251220_214317/thinking_reasoning_moe6.json` | — | — |
| 72 | `20251220_214317/thinking_phi_4_reasoning_plus_baseline.json` | — | — |
| 73 | `20251220_214317/thinking_phi_4_reasoning_plus_q8_baseline.json` | — | — |
| 74 | `20251220_214317/ingest_qwen3_30b_thinking_baseline.json` | Qwen3-30B-Thinking (ingest) | — |
| 75 | `20251220_214317/ingest_qwen3_30b_thinking_moe2.json` | — | — |
| 76 | `20251220_214317/ingest_qwen3_30b_thinking_moe4.json` | — | — |
| 77 | `20251220_214317/ingest_qwen3_30b_thinking_moe6.json` | — | — |
| 78 | `20251220_214317/ingest_qwen3_coder_30b_baseline.json` | — | — |
| 79 | `20251220_214317/ingest_qwen3_coder_30b_moe4.json` | — | — |
| 80 | `20251220_214317/ingest_qwen3_coder_30b_moe6.json` | — | — |

**P2 count: 25 files**

### P3 — Draft Models (small, 10-20 questions, low priority)

| # | File | Summary.csv Model | Current Score |
|---|------|-------------------|---------------|
| 81 | `20251220_214317/draft_deepseek_r1_distill_qwen_1_5b_baseline.json` | DeepSeek-R1-Distill-Qwen-1.5B | 95% |
| 82 | `20251220_214317/draft_deepseek_r1_distill_qwen_1_5b_q80_baseline.json` | — | — |
| 83 | `20251220_214317/draft_gemma3_baseline.json` | gemma-3-1b-it | 80% |
| 84 | `20251220_214317/draft_pard_deepseek_r1_distill_qwen_1_5b_q5_k_s_baseline.json` | PARD-DR1-1.5B-Q5_K_S | 95% |
| 85 | `20251220_214317/draft_pard_deepseek_r1_distill_qwen_1_5b_q8_0_baseline.json` | PARD-DR1-1.5B-Q8_0 | 95% |
| 86 | `20251220_214317/draft_pard_llama_3_2_1b_q4_0_baseline.json` | pard-llama-3.2-1b-q4_0 | 95% |
| 87 | `20251220_214317/draft_pard_llama_3_2_1b_q8_0_baseline.json` | PARD-Llama-3.2-1B.Q8_0 | 95% |
| 88 | `20251220_214317/draft_pard_qwen3_0_6b_q4_0_baseline.json` | pard-qwen3-0.6b-q4_0 | 95% |
| 89 | `20251220_214317/draft_qwen2_0_5b_q2_k_baseline.json` | Qwen2-0.5B.Q2_K | 5% |
| 90 | `20251220_214317/draft_qwen2_5_0_5b_instruct_f16_baseline.json` | Qwen2.5-0.5B-Instruct-f16 | 100% |
| 91 | `20251220_214317/draft_qwen25_baseline.json` | Qwen2.5-0.5B.Q8_0 | 40% |
| 92 | `20251220_214317/draft_qwen2_5_coder_0_5b_baseline.json` | Qwen2.5-Coder-0.5B-Q4_K_M | 55% |
| 93 | `20251220_214317/draft_qwen2_5_coder_1_5b_q2_k_baseline.json` | Qwen2.5-Coder-1.5B.Q2_K | 10% |
| 94 | `20251220_214317/draft_qwen2_5_coder_1_5b_q4_k_m_baseline.json` | Qwen2.5-Coder-1.5B.Q4_K_M | 60% |
| 95 | `20251220_214317/draft_qwen25_coder_baseline.json` | Qwen2.5-Coder-0.5B-Q8_0 | 20% |
| 96 | `20251220_214317/draft_qwen2_5_math_1_5b_baseline.json` | Qwen2.5-Math-1.5B-Q4_K_M | 60% |
| 97 | `20251220_214317/draft_qwen3_0_6b_baseline.json` | Qwen3-0.6B-Q2_K | 5% |
| 98 | `20251220_214317/draft_qwen3_0_6b_q8_0_baseline.json` | Qwen_Qwen3-0.6B-Q8_0 | 25% |
| 99 | `20251220_214317/draft_qwen3_1_7b_baseline.json` | Qwen3-1.7B-Q4_K_M | 75% |
| 100 | `20251220_214317/draft_qwen3_1_7b_q8_0_baseline.json` | Qwen3-1.7B-Q8_0 | 15% |
| 101 | `20251220_214317/draft_qwen3_coder_0_75b_baseline.json` | Qwen3-Coder-0.75B | 30% |
| 102 | `20251217_160429/draft_co_rewarding_ii_qwen3_1_7b_base_math_q8_0_baseline.json` | Co-rewarding-II | 100% |
| 103 | `20251217_160429/draft_qwen2_5_math_1_5b_q6k_baseline.json` | Qwen2.5-Math-1.5B-Q6_K | 53% |
| 104 | `20251217_160429/draft_qwen3_vl_1b_merged_q8_0_baseline.json` | qwen3-vl-1b-merged | 0% |
| 105 | `20251217_160429/math_mathsmith_hard_problem_synthesizer_qwen3_8b_q_baseline.json` | MathSmith-8B | 97% |
| 106 | `20251220_214317/formalizer_baseline.json` | nexusraven-v2-13b | 100% |
| 107 | `20251220_214317/formalizer_q4_baseline.json` | — | — |
| 108 | `20251220_214317/tool_formalizer_nexusraven_baseline.json` | — | — |
| 109 | `20251220_214317/tool_formalizer_xlam1_baseline.json` | xLAM-1b | 100% |
| 110 | `20251220_214317/tool_formalizer_xlam2_baseline.json` | xLAM-2-1B | 100% |
| 111 | `20251220_214317/toolrunner_baseline.json` | — | — |

**P3 count: 31 files**

### P4 — Vision Models (separate benchmark, different scoring)

| # | File | Notes |
|---|------|-------|
| 112 | `20260119_112408/vision_qwen3_vl_4b_baseline.json` | Best VL (94%) |
| 113 | `20260119_112408/vision_qwen3_vl_4b_q80_baseline.json` | Same quality |
| 114 | `20260119_112408/vision_qwen3_vl_8b_baseline.json` | 86% |
| 115 | `20260119_112408/vision_qwen3_vl_8b_q80_baseline.json` | 86% |
| 116 | `20260119_112408/vision_escalation_baseline.json` | Qwen3-VL-30B |
| 117 | `20260119_112408/vision_escalation_moe4.json` | 75% |
| 118 | `20260119_112408/vision_escalation_moe6.json` | 75% |
| 119 | `20260119_112408/vision_qwen3_vl_235b_baseline.json` | 56% |
| 120 | `20260119_112408/vision_qwen3_vl_235b_moe4.json` | 53% |
| 121 | `20260119_112408/vision_qwen3_vl_235b_moe6.json` | 53% |
| 122 | `20260119_112408/vision_qwen3_vl_235b_a22b_thinking_baseline.json` | 53% |
| 123 | `20260119_112408/vision_qwen3_vl_235b_a22b_thinking_moe4.json` | 53% |
| 124 | `20260119_112408/vision_qwen3_vl_235b_a22b_thinking_moe6.json` | 53% |
| 125 | `20260119_112408/worker_vision_baseline.json` | Qwen2.5-VL-7B |
| 126 | `20251220_214317/vision_qwen3_vl_2b_q4_k_m_baseline.json` | Qwen3-VL-2B |

**P4 count: 15 files**

### P5 — Qwen3.5 remaining (currently running benchmark sweep)

| # | File | Notes |
|---|------|-------|
| 127 | `20260303_170903/qwen35_q6k_baseline.json` | Q6_K baseline |
| 128 | `20260303_170903/qwen35_q6k_moe4.json` | Q6_K MoE4 |
| 129 | `20260303_170903/qwen35_q6k_moe6.json` | Q6_K MoE6 |
| + | q8_0 variants | Still running as of 2026-03-04 |
| + | MoE4/MoE6 for q4ks, q5ks | May exist by time of rescore |

**P5 count: 3+ files (growing)**

## Execution Plan

### Per-session workflow
1. Pick a priority tier (P0 first)
2. Launch 6 scoring agents in parallel (context window limit)
3. Collect results, verify per-suite breakdowns
4. Update `summary.csv` with rescored values
5. Update `RESULTS.md` with corrected scores
6. Mark files as rescored in this handoff (checkbox)

### Estimated effort
- ~6 agents per batch, ~5-7 min per agent
- P0 (21 files): 4 batches = ~25 min
- P1 (34 files): 6 batches = ~40 min
- P2 (25 files): 5 batches = ~30 min
- P3 (31 files): 6 batches = ~35 min
- P4 (15 files): 3 batches = ~20 min
- **Total: ~24 batches, ~2.5 hours of agent time**

### After rescoring
1. Rebuild `summary.csv` with all corrected scores + median TPS
2. Regenerate RESULTS.md tables
3. Re-evaluate production role assignments — models we deprecated may actually be competitive
4. Update model_registry.yaml with corrected `performance` fields
5. Archive this handoff

## Emerging Findings (P0 Complete)

### Production Role Quality Reality
| Role | Model | Old Score | Rescored | Median TPS | Verdict |
|------|-------|-----------|----------|------------|---------|
| frontdoor baseline | Coder-30B MoE8 | ~98% | **66%** | 17.9 | Overinflated 32pp |
| frontdoor MoE4 | Coder-30B MoE4 | ~89% | **60%** | 24.1 | Overinflated 29pp |
| coder_escalation | Coder-32B | 93% | **74%** | 3.8 | Overinflated 19pp |
| worker_general | Qwen2.5-7B | 90% | **33%** | 15.0 | CATASTROPHIC — 57pp drop |
| worker_math | Math-7B | 90% | **40%** | 10.2 | CATASTROPHIC — 50pp drop |
| worker_summarize | Qwen2.5-7B | ~90% | **77%** | 3.0 | Moderate drop 13pp |
| architect_general | Qwen3-235B | 94% | **69%** | 5.8 | Overinflated 25pp |
| architect_coding baseline | Coder-480B | 83% | **73%** | 6.3 | Moderate drop 10pp |
| architect_coding MoE6 | Coder-480B MoE6 | 79% | **83%** | 6.0 | UP 4pp (was underscored) |
| ingest_long_context baseline | Next-80B | 98% | **75%** | 7.5 | Overinflated 23pp |
| ingest_long_context MoE4 | Next-80B | — | **74%** | 7.9 | Comparable to baseline |
| ingest_long_context MoE6 | Next-80B | — | **79%** | 6.7 | BEST config for this model |
| thinking (Q4_K_M) | DeepSeek-R1-14B | 87% | **46%** | 3.6 | CATASTROPHIC — 41pp drop |
| thinking (Q6_K_L) | DeepSeek-R1-14B | 98% | **69%** | 4.2 | Overinflated 29pp |

### Critical Insights
1. **MoE2 is universally broken**: 0% on both Qwen3-235B and frontdoor Coder-30B — completely degenerate
2. **Worker models are dangerously weak**: worker_general at 33% means the orchestrator's general worker is garbage. worker_math at 40% is the strongest suite-specific worker but still weak across non-math suites.
3. **235B MoE degradation is severe**: baseline 69% → MoE4 53% → MoE6 52% — unlike Coder-480B where MoE6 (83%) is BEST
4. **Coder-480B MoE6 is the real winner**: 83% at 6.0 t/s — better quality than baseline (73%) despite fewer experts. Different from 235B pattern.
5. **instruction_precision is universally weak**: Most models score 0-27% on instruction precision with MoE. Only baseline configs partially handle it.

## Key Questions to Answer

1. **Is DeepSeek-R1-14B-Q6_K_L really 98%?** ANSWERED — No, it's 69%. Q4_K_M variant is even worse at 46%. Dominant failure: missing `</think>` closure (model exhausts context on CoT, never produces final answer). Need to evaluate Qwen3-30B-Thinking as alternative backbone.
2. **Is Qwen3-30B-Thinking really 100%?** Three configs at 100% seems suspect. (P2)
3. **Is gemma-3-12b really 97%?** Could be a genuine strong performer, or inflated. (P1)
4. **Which deprecated models deserve a second look?** Hermes-4-70B at 89% might actually be competitive if other models drop. (P1)
5. **Do the 235B/480B architect models hold up?** ANSWERED — 235B drops to 69%, 480B holds better at 73-83%

## Files

- Raw JSONs: `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/`
- Review CSVs: `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/reviews/`
- Summary: `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/reviews/summary.csv`
- Master table: `/mnt/raid0/llm/epyc-inference-research/docs/reference/benchmarks/RESULTS.md`
- Scoring prompt template: see "Methodology" section above

## Progress Tracker

### P0 — Production Roles
- [x] frontdoor_baseline → 46/70 = 66%, median 17.9 t/s
- [x] frontdoor_moe2 → 0/52 = 0%, median 20.7 t/s
- [x] frontdoor_moe4 → 42/70 = 60%, median 24.1 t/s
- [x] frontdoor_moe6 → 44/70 = 63%, median 17.4 t/s
- [x] ingest_qwen2_5_coder_32b_baseline → 45/61 = 74%, median 3.8 t/s
- [x] worker_general_baseline → 20/61 = 33%, median 15.0 t/s
- [x] worker_math_baseline → 16/40 = 40%, median 10.2 t/s
- [x] worker_summarize_baseline → 47/61 = 77%, median 3.0 t/s
- [x] architect_general_baseline → 46/67 = 69%, median 5.8 t/s
- [x] architect_general_moe2 → 0/66 = 0%, median 8.2 t/s
- [x] architect_general_moe4 → 35/66 = 53%, median 7.2 t/s
- [x] architect_general_moe6 → 34/66 = 52%, median 6.8 t/s
- [x] architect_coding_baseline → 51/70 = 73%, median 6.3 t/s
- [x] architect_coding_moe4 → 49/70 = 70%, median 7.0 t/s
- [x] architect_coding_moe6 → 58/70 = 83%, median 6.0 t/s
- [x] architect_coding_moe8 → 28/31 = 90%, median 4.5 t/s
- [x] ingest_long_context_baseline → 46/61 = 75%, median 7.5 t/s
- [x] ingest_long_context_moe4 → 45/61 = 74%, median 7.9 t/s
- [x] ingest_long_context_moe6 → 48/61 = 79%, median 6.7 t/s
- [x] thinking_deepseek_r1_distill_qwen_14b_baseline → 28/61 = 46%, median 3.6 t/s
- [x] thinking_deepseek_r1_distill_qwen_14b_q6kl_baseline → 42/61 = 69%, median 4.2 t/s

**P0 COMPLETE — 21/21 files rescored.**

### P1 — Tier B Models
- [x] general_gemma_3_12b_it_baseline → 48/61 = 78%, median 9.4 t/s
- [x] general_gemma_3_27b_it_qat_baseline → 50/64 = 78%, median 2.0 t/s
- [x] general_qwen2_5_7b_q4_k_s_baseline → 27/61 = 44%, median 15.3 t/s
- [x] general_qwen3_32b_baseline → 39/61 = 63%, median 1.5 t/s
- [x] architect_hermes_4_70b_baseline → 41/61 = 67%, median 2.2 t/s
- [x] architect_meta_llama_3_1_70b_baseline → 41/61 = 67%, median 1.5 t/s
- [x] architect_meta_llama_3_70b_baseline → 12/61 = 19%, median 1.4 t/s
- [x] architect_qwen2_5_72b_baseline → 46/66 = 69%, median 2.0 t/s
- [x] architect_qwen2_5_72b_q4_k_m_baseline → 34/61 = 55%, median 1.6 t/s
- [x] coder_escalation_53b_baseline → 42/61 = 68%, median 10.6 t/s
- [x] coder_escalation_53b_moe2 → 0/60 = 0%, median 14.3 t/s
- [x] coder_escalation_53b_moe4 → 31/61 = 50%, median 12.9 t/s
- [x] coder_escalation_53b_moe6 → 40/61 = 65%, median 13.1 t/s
- [x] general_deepseek_r1_0528_qwen3_8b_baseline → 29/61 = 47%, median 8.1 t/s
- [x] general_meta_llama_3_8b_instruct_fp16_baseline → 27/61 = 44%, median 2.1 t/s
- [x] general_meta_llama_3_1_8b_q4_k_s_baseline → 1/61 = 1%, median 7.3 t/s
- [x] math_qwen2_5_math_72b_baseline → 24/61 = 39%
- [x] math_qwen2_5_math_72b_q6k_baseline → 30/61 = 49%, median 1.9 t/s
- [x] ingest_hermes_4_70b_baseline → 42/61 = 68%, median 2.6 t/s
- [x] ingest_llama_3_1_70b_baseline → 46/61 = 75%, median 1.5 t/s
- [x] ingest_qwen2_5_72b_baseline → 44/61 = 72%, median 1.6 t/s
- [x] ingest_qwen3_32b_baseline → 42/61 = 68%, median 1.6 t/s
- [x] coder_primary_baseline → 40/70 = 57%, median 13.0 t/s
- [x] coder_primary_moe2 → 0/56 = 0%, median 12.5 t/s (MoE2 broken)
- [x] coder_primary_moe4 → 40/70 = 57%, median 17.1 t/s
- [x] coder_primary_moe6 → 49/70 = 70%, median 15.2 t/s
- [x] general_glm_4_6_baseline → 7/14 = 50%, median 3.0 t/s (only 14 questions)
- [x] minimax_m21_q4_baseline → 49/70 = 70%, median 8.8 t/s
- [x] minimax_m21_q6_baseline → 42/61 = 68%, median 8.0 t/s
- [x] minimax_m21_q4_moe4 → 36/70 = 51%, median 12.5 t/s
- [x] minimax_m21_q4_moe6 → 40/64 = 62%, median 10.1 t/s
- [x] minimax_m21_q6_moe4 → 36/60 = 60%, median 10.9 t/s
- [x] minimax_m21_q6_moe6 → 44/60 = 73%, median 9.5 t/s
- [x] glm_47_flash_baseline → 9/61 = 15%, median 15.7 t/s (severe degeneration)

**P1 COMPLETE — 34/34 files rescored.**

### P2 — Thinking Models
- [x] thinking_deepseek_r1_distill_llama_70b_baseline → 4/61 = 7%, median 1.0 t/s
- [x] thinking_deepseek_r1_distill_llama_8b_baseline → 20/40 = 50%, median 9.3 t/s
- [x] thinking_deepseek_r1_distill_qwen_7b_baseline → 22/40 = 55%, median 10.4 t/s
- [x] thinking_deepseek_r1_distill_qwen_32b_baseline → 42/61 = 69%, median 2.0 t/s
- [x] thinking_qwen3_30b_thinking_baseline (Q8_0) → 32/61 = 52%, median 16.5 t/s
- [x] thinking_qwen3_30b_thinking_moe2 (Q8_0) → 1/54 = 2%, median 23.0 t/s
- [x] thinking_qwen3_30b_thinking_moe4 (Q8_0) → 51/61 = 84%, median 19.7 t/s
- [x] thinking_qwen3_30b_thinking_moe6 (Q8_0) → 25/61 = 41%, median 18.0 t/s
- [x] thinking_qwen3_30b_thinking_q4ks_baseline (Q4_K_S) → 35/70 = 50%, median 15.9 t/s
- [x] thinking_qwen3_30b_thinking_q4ks_moe2 (Q4_K_S) → 0/47 = 0%, median 20.1 t/s
- [x] thinking_qwen3_30b_thinking_q4ks_moe4 (Q4_K_S) → 47/70 = 67%, median 20.3 t/s
- [x] thinking_qwen3_30b_thinking_q4ks_moe6 (Q4_K_S) → 49/70 = 70%, median 18.7 t/s
- [x] thinking_qwen3_4b_thinking_baseline → 23/40 = 58%, median 9.3 t/s
- [x] thinking_reasoning_baseline (Qwen3-Next-80B) → 35/61 = 57%, median 7.5 t/s
- [x] thinking_reasoning_moe4 (Qwen3-Next-80B) → 51/70 = 73%, median 10.5 t/s
- [x] thinking_reasoning_moe6 (Qwen3-Next-80B) → 39/61 = 64%, median 7.8 t/s
- [x] thinking_phi_4_reasoning_plus_baseline → 2/61 = 3%, median 4.5 t/s
- [x] thinking_phi_4_reasoning_plus_q8_baseline → 3/61 = 5%, median 2.6 t/s
- [x] ingest_qwen3_30b_thinking_baseline → 30/61 = 49%, median 16.8 t/s
- [x] ingest_qwen3_30b_thinking_moe2 → 0/48 = 0%, median 22.8 t/s
- [x] ingest_qwen3_30b_thinking_moe4 → 22/61 = 36%, median 20.0 t/s
- [x] ingest_qwen3_30b_thinking_moe6 → 47/61 = 77%, median 18.2 t/s
- [x] ingest_qwen3_coder_30b_baseline → 52/70 = 74%, median 17.9 t/s
- [x] ingest_qwen3_coder_30b_moe4 → 41/70 = 59%, median 24.1 t/s
- [x] ingest_qwen3_coder_30b_moe6 → 54/70 = 77%, median 17.4 t/s

**P2 COMPLETE — 25/25 files rescored.**

### P3 — Draft Models
- [x] draft_deepseek_r1_distill_qwen_1_5b_baseline → 6/20 = 30%, median 58.6 t/s
- [x] draft_deepseek_r1_distill_qwen_1_5b_q80_baseline → 2/20 = 10%, median 58.6 t/s
- [x] draft_gemma3_baseline → 9/20 = 45%, median 113.5 t/s
- [x] draft_pard_deepseek_r1_distill_qwen_1_5b_q5_k_s_baseline → 1/20 = 5%, median 45.5 t/s
- [x] draft_pard_deepseek_r1_distill_qwen_1_5b_q8_0_baseline → 3/20 = 15%, median 46.6 t/s
- [x] draft_pard_llama_3_2_1b_q4_0_baseline → 0/20 = 0%, median 76.0 t/s
- [x] draft_pard_llama_3_2_1b_q8_0_baseline → 0/20 = 0%, median 39.3 t/s
- [x] draft_pard_qwen3_0_6b_q4_0_baseline → 0/20 = 0%, median 81.5 t/s
- [x] draft_qwen2_0_5b_q2_k_baseline → 0/20 = 0%, median 125.1 t/s
- [x] draft_qwen2_5_0_5b_instruct_f16_baseline → 2/20 = 10%, median 32.8 t/s
- [x] draft_qwen25_baseline → 1/20 = 5%, median 161.4 t/s
- [x] draft_qwen2_5_coder_0_5b_baseline → 1/20 = 5%, median 156.2 t/s
- [x] draft_qwen2_5_coder_1_5b_q2_k_baseline → 0/20 = 0%, median 68.1 t/s
- [x] draft_qwen2_5_coder_1_5b_q4_k_m_baseline → 4/20 = 20%, median 57.0 t/s
- [x] draft_qwen25_coder_baseline → 1/20 = 5%, median 147.9 t/s
- [x] draft_qwen2_5_math_1_5b_baseline → 1/20 = 5%, median 55.8 t/s
- [x] draft_qwen3_0_6b_baseline → 0/20 = 0%, median 95.5 t/s
- [x] draft_qwen3_0_6b_q8_0_baseline → 1/20 = 5%, median 67.3 t/s
- [x] draft_qwen3_1_7b_baseline → 4/20 = 20%, median 43.1 t/s
- [x] draft_qwen3_1_7b_q8_0_baseline → 11/20 = 55%, median 35.3 t/s
- [x] draft_qwen3_coder_0_75b_baseline → 0/20 = 0%, median 64.3 t/s
- [x] draft_co_rewarding_ii_baseline → 9/20 = 45%, median 23.7 t/s
- [x] draft_qwen2_5_math_1_5b_q6k_baseline → 13/40 = 33%, median 60.7 t/s
- [x] draft_qwen3_vl_1b_merged_q8_0_baseline → 0/2 = 0%, median 67.7 t/s
- [x] math_mathsmith_8b_q8_0_baseline → 21/30 = 70%, median 3.3 t/s
- [x] formalizer_baseline (MathSmith Q8_0) → 22/30 = 73%, median 11.4 t/s
- [x] formalizer_q4_baseline (MathSmith Q4_K_M) → 21/30 = 70%, median 14.2 t/s
- [x] tool_formalizer_nexusraven_baseline → 3/10 = 30%, median 9.1 t/s
- [x] tool_formalizer_xlam1_baseline → 1/10 = 10%, median 56.9 t/s
- [x] tool_formalizer_xlam2_baseline → 2/10 = 20%, median 49.2 t/s
- [x] toolrunner_baseline (Meta-Llama-3-8B) → 23/61 = 38%, median 15.0 t/s

**P3 COMPLETE — 31/31 files rescored.**

### P4 — Vision Models
- [x] vision_qwen3_vl_4b_baseline → 14/15 = 93%, median 16.3 t/s (VL 14/14, general 0/1 harness bug)
- [x] vision_qwen3_vl_4b_q80_baseline → 10/12 = 83%, median 16.4 t/s
- [x] vision_qwen3_vl_8b_baseline → 11/12 = 92%, median 16.2 t/s
- [x] vision_qwen3_vl_8b_q80_baseline → 9/12 = 75%, median 9.9 t/s
- [x] vision_escalation_baseline (VL-30B) → 11/12 = 92%, median 20.0 t/s
- [x] vision_escalation_moe4 (VL-30B) → 11/12 = 92%, median 24.8 t/s
- [x] vision_escalation_moe6 (VL-30B) → 10/12 = 83%, median 22.5 t/s
- [x] vision_qwen3_vl_235b_baseline → 7/12 = 58%, median 4.7 t/s (truncation on t3)
- [x] vision_qwen3_vl_235b_moe4 → 8/12 = 67%, median 7.0 t/s
- [x] vision_qwen3_vl_235b_moe6 → 6/12 = 50%, median 5.8 t/s (severe truncation)
- [x] vision_qwen3_vl_235b_thinking_baseline → 4/12 = 33%, median 3.8 t/s (think blocks exhaust tokens)
- [x] vision_qwen3_vl_235b_thinking_moe4 → 4/12 = 33%, median 5.8 t/s
- [x] vision_qwen3_vl_235b_thinking_moe6 → 4/12 = 33%, median 5.3 t/s
- [x] worker_vision_baseline (Qwen2.5-VL-7B) → 11/12 = 92%, median 18.7 t/s
- [x] vision_qwen3_vl_2b_q4_k_m_baseline → 4/30 = 13%, median 45.0 t/s (plant-disease hallucination)

**P4 COMPLETE — 15/15 files rescored.**

### Already Rescored (for reference)
- [x] coder_qwen3_coder_30b_a3b_baseline → 55/70 = 79%
- [x] coder_qwen3_coder_30b_a3b_moe4 → 43/70 = 61%
- [x] coder_qwen3_coder_30b_a3b_moe6 → 50/70 = 71%
- [x] qwen35_q4km_baseline → 61/70 = 87%
- [x] qwen35_q4km_moe4 → 61/68 = 90%
- [x] qwen35_q4ks_baseline → 47/65 = 72%
- [x] qwen35_q5ks_baseline → 55/66 = 83%
