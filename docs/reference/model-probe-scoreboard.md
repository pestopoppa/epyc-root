# Model Probe Scoreboard (production-consolidated-v8)

**Living scoreboard** — one glance-able read of how every candidate model is performing on the
production v8 stack. Current production is `production-consolidated-v8 @
67a433bf45a8a091d83b4ea0b32ff0735fd51800` (binary `10107`; `GGML_IQK=1` supports IQ2/IQ3 and IQ4_XS, while IQ1 remains non-accelerated; some older rows name
their original artifact commit). Newer `llama.cpp-experimental` commits are
post-candidate research until they rerun the final coherence+garbage smoke. All rows are
**OBSERVATION-grade** (single-config, small-n per MEASUREMENT.md) — hypotheses, not
decision-grade. MI210 = gfx90a/ROCm 6.2; CPU = EPYC 9655. Updated 2026-07-20 from the probe
runs scattered across the inference handoffs and v7 cutover record.

**Update rule (for the running agent):** every future model/quant probe appends a row here (model,
quant, device, pp t/s, tg t/s, quality, role-ready, artifact) — do not bury results in a
checkbox line + artifact path alone. Keep this the single source of "how are the models doing."
Blocked candidates are not speed-rerun unless a named quality, loader, protocol, parser, or
artifact fix states the reopen hypothesis.

## ⚠ Steering (2026-07-19) — stop grinding the quality-blocked breadth

The sub-2-bit / exotic-model breadth is **OBSERVATION speed-only and quality-blocked or broken**
— none are role-ready, and continued probing is **low-EV**. **STOP probing these unless a
*specific* quality or loader path opens** (a concrete prompt/schema/artifact/loader fix with
a hypothesis, not another speed rerun):
- **Bonsai-8B / Bonsai-27B Q1_0** — fast/cheap curiosity only; Bonsai-27B fails the strict
  instruction gate and Bonsai-8B is orphan/provenance-limited. Reopen only on a prompt/template,
  provenance, or role-quality fix.
- **Ternary Bonsai Q2_g64** — 6/8, empty `<think>` tags; ngram is speed-only. Reopen only on
  a quality/protocol fix.
- **Ternary Bonsai Q2_0** — broken load (498/498 tensors short); needs a producer/transcode
  fix or a documented compatibility-loader contract, not reruns.
- **Nemotron-Nano Q8 / Nemotron-Diffusion (intake-576)** — Nano fails broader visible-content
  behavior despite small-slice protocol repairs; Diffusion still lacks a quality-clean
  stock-v7 constrained/server path. Reopen only on protocol/parser/loader fixes.
- **Qwen3-VL-8B/30B, SuperGemma4, other extra vision candidates** — paused unless they fix a
  fixture or role gap not already covered by MiniCPM-o plus the worker_vision safety alias.

**Redirect freed cycles to promotion and reviewer-route work** (higher EV): **AXA-2 teleport**,
post-ratification `P-GPU-1` certification prep, and H5/RM-2 remaining anchors + RM-3 screening.
GLM accept-control (`GC-shadow-repair4b`) is closed and failed; OP-2 passed; `P-GPU-1` is signed
but production-named certification reruns wait for v7 promotion. See
[`v7-promotion.md`](../../handoffs/active/v7-promotion.md) gate +
[`inference-acceleration-index.md`](../../handoffs/active/inference-acceleration-index.md) LANE A/B.

**And: maintain this scoreboard** — append every future probe row here rather than burying it in a
checkbox line, so there's always one glance-able read.

## Scoreboard

| Model | Quant | Device | Prompt t/s (pp) | Decode t/s (tg) | Quality | Role-ready? | Evidence |
|---|---|---|---|---|---|---|---|
| **Qwable-v1** (35B-A3B reasoner) | IQ4_XS | MI210 | 2050/1951/1764 (2K/8K/32K) | 91.5 / 100.3 (tg1024/512); current-v7 repeat 108.4 | historical 18/18 deterministic (plain+ngram); later current-v7 paired repeat 14/18 vs Q8 13/18 | **Yes** — primary reasoning-heavy route, but repeat/protocol-sensitive | `qwable_reasoning_economics/…20260717T184136Z`, registry current-v7 repeat |
| Qwable-v1 reviewer arm | IQ4_XS | MI210 | same as Qwable IQ4_XS | RM-2 median row wall 2.1s | decision-grade C-CRAB P-REV-1 failed: FA 54.2%, FR 45.8%, AUC 0.438, ECE 0.441 | **No** — not a patch-reviewer | `reviewer_model_ablations/rm2-fast-b-qwable-iq4xs-ccrab-p-rev1-20260719T162712Z` |
| Qwen3.6-27B + Qwable scaffold reviewer arm | Q8_0 + IQ4_XS | MI210 co-resident | final reviewer uses Qwen dense Q8 | RM-2 median row wall 6.5s | decision-grade C-CRAB P-REV-1: FA 33.3%, FR 41.7%, AUC 0.659, ECE 0.315 | **No** — repair hypothesis only; FR too high | `reviewer_model_ablations/rm2-fast-b-qwen36-27b-q8-plus-qwable-iq4xs-scaffold-ccrab-p-rev1-20260719T162958Z` |
| Qwable-v1 | IQ4_XS | CPU | — | 15.96 | 18/18 | Yes (CPU fallback) | `…iq4_cpu_expanded_final` |
| Qwable-v1 | Q8_0 | MI210 | 2086/1982/1648 | 102.9 / 104.1 | 6/6; no Q8-only gain | IQ4_XS preferred (½ footprint) | idx L101,180 |
| **Frontdoor Qwen3.6-35B-A3B** | Q8_0 native-MTP | MI210 | — | no-spec 95.4; **MTP 119.7** (8K, 100% accept); 2K/32K 123.6/105.2 | production | **Yes** — production; Gate-R residency (obs) | `k35_stack_context_matrix/frontdoor_pgpu1_candidate` |
| Frontdoor Qwen3.6-35B-A3B | Q8_0 | CPU | — | no-spec 17.1; 2K/32K 21.6/10.2 | production | Yes | same |
| **gemma-4-26B-A4B worker** (ngram+draft-mtp) | Q8_0 | CPU | ~120–136 | 2K 175.8 / 8K 110.0 / 14K 97.6 | K5 gate **+0.0%** MMLU-Pro/GPQA | **Yes** — live worker_general | K35 worker curve, idx L206 |
| gemma-4-26B-A4B | Q8_0 (+v6 MTP) | MI210 / CPU control | 274-282 | single-slot MTP ~158; schema 122; natural free-form ORIG mean 108.7; explicit-greedy repeat 91.2; traced GPU no-spec np1 69.44; pre-sampling graph-on 72.52 / graphs-off 66.48 / FA-off 79.61; CPU no-spec np1 21.12 | schema 10/10; repeated-token stop-string 10/10 one hash; natural prose clean n=10 failed with 9 hashes and 0/10 exact 160-word runs; explicit-greedy repeat also failed with 10 hashes and 0/10 exact 160; traced GPU MTP/no-spec/np1 all branch early, CPU no-spec np1 deterministic; pre-sampling GPU A/B says graphs-off and FA-off do not fix | **No** for broad GPU free-form worker (K11.1 open) | `k11_gemma4_long_mtp_np4_n10…20260718T142203Z`, `k11_stop_end_orig_q4_mtp_n10_concurrent_pc4o_20260720T085122Z`, `k11_natural_freeform_compare_20260720T0937Z.summary.json`, `k11_natural_freeform_explicit_greedy_compare_20260720T1059Z`, `k11_natural_freeform_trace_compare_20260720T1139Z`, `k11_natural_freeform_orig_q4_cpu_nospec_np1_explicit_greedy_trace_20260720T114120Z`, `k11_gpu_backend_path_ab_20260720T1204Z` |
| **Architect Qwen3.5-122B** (NEXTN) | UD-Q4_K_M | CPU | — | 2K 23.9 / 8K 20.7 (accept 818/820) | production | Yes | idx L207 |
| **Ingest Qwen3-Next-80B-A3B** | Q4_K_M | CPU | — | 2K 20.5 / 8K 15.9 / 32K 9.7 | production | Yes | idx L208 |
| **GLM-5.2** (754B glm-moe-dsa) | UD-IQ2_M | CPU | ~26 (12K); 24→17 as KV grows; 64K 6.8 | **~2.56** (12K); 64K 1.20 | exact-answer FA 0.0%/FR 16.7%; C-CRAB P-REV-1 failed: **FA 41.7%, FR 25.0%, AUC 0.509, ECE 0.239, Brier 0.278, parse 0.0%**; JudgeBench-GPT exact-choice positive: **22/24 (91.7%)**; SWE accept controls positive: **22/24, FR 8.3%, parse 0/24**; GC-external-1e route-away verdict | **No** — not production patch reviewer on current policy | `glm52_reviewer_corpus_direct/gc-shadow-repair4b-p-rev1-20260719T132459Z`, `glm52_external_ground_truth_direct/glm52-external-judgebench-gpt-n24-p-rev1-choice-rescore-20260719`, `glm52_external_ground_truth_direct/glm52-external-swebench-verified-n24-p-rev1-20260719Tlive` |
| GLM-5.2 native-MTP | UD-IQ2_M | CPU | repaired long run 22.77 pp | repaired `draft-mtp` 5.33 vs no-spec 2.49 | alpha 0.933 (`376/403` accepted), single-NextN repaired; acceleration evidence only | No — reviewer admission failed; acceleration not role admission | `glm52_native_mtp_ab/glm52-native-mtp-draft-long-repair-20260719T195037Z/plan.json` |
| **MiniCPM-o-4_5** vision (+F16 proj) | Q4_K_M | MI210 | 732–884 | 111–127 | 4/4 OCR/chart (`--reasoning off`) | **Yes** candidate — source-wired + controlled smoke; persistent live traffic unconfirmed | `k35-vision-escalation-live-smoke-20260718T1225Z` |
| MiniCPM-o-4_5 | Q4_K_M | CPU | — | 12.0–14.1 | 4/4 (reasoning off) | (CPU fallback) | `k35-minicpm-o45-reasoning-off` |
| Qwen2.5-VL-7B worker_vision (+mmproj) | — | MI210 | — | 16.9–21.3 | 4/4 | **Yes** — live worker_vision + escalation safety alias | `k35-vision-matrix-20260717T1500Z` |
| Bonsai-8B | Q1_0 | MI210 | 2349 / 1751 (2K/8K) | 38.4 | speed-only; orphan/provenance-limited | No — stop-list; reopen on provenance + quality fix | `v7-bonsai8b-gpu-bench-current-20260718T141319Z` |
| Bonsai-27B | Q1_0 | MI210 | 799 / 759 | 11.2 (decode-slow) | 6/8 strict (fails 6-word IF) | No — stop-list; reopen on quality fix | `bonsai27_q1_mi210_llama_bench_20260718T150243Z` |
| Ternary Bonsai | Q2_g64 | MI210/CPU | ~26 (p512) | raw 10.5 (MI210) / 8.4 (CPU); ngram 9.8→22.9 | 6/8 strict; retry wrong output | No — stop-list; ngram speed-only | `ternary_q2_g64_quality_gate/…` |
| Ternary Bonsai | Q2_0 | — | — (fails load) | — | **loader rejects** — 498/498 tensors short (noncanonical layout) | No — stop-list; reopen on artifact/loader contract fix | `ternary_bonsai_q2_layout_contract_20260718Tcodex.json` |
| Nemotron-Nano | Q8 | MI210 | — | 78–84 | small slice repaired, but broader 7/24 visible-content failure | No — stop-list; protocol-quality blocked | `nemotron_nano_task_quality/…broad24…` |
| Qwen3-VL-8B (+F16 proj) | Q4_K_M | MI210 | — | 110–126 | 3/4 — chart→"Moldova" | No — stop-list; reopen on chart/role-gap fix | `k35-qwen3vl8-candidate` |
| Qwen3-VL-30B (MoE) | — | MI210 | — | 36–50 (short) | 3/4 — chart→"Moldova" | No — replaced by CPU alias→MiniCPM-o | `k35-vision-matrix` |
| SuperGemma4-26B multimodal (+F16 proj) | Q8_0 | MI210 | — | 80–84 | 4/4 | No — MiniCPM-o preferred (faster/smaller) | `k35-supergemma4-candidate` |
| PaddleOCR-VL-1.6 (+mmproj) | GGUF | MI210 | — | 484–490 (OCR) | OCR clean; **table TEDS 0.0** (vs ODL 0.78) | No — OCR specialist, not general QA | `paddleocr-vl-first-smoke` |
| Hy3 (hybrid) | IQ1_M | MI210-hybrid / CPU | MI210-hybrid repaired strict 22.33; context 2K/8K/32K 71.31/82.65/72.34 | repaired strict 11.43 hybrid / 5.17 CPU; context 2K/8K/32K 9.62/9.37/8.61 | repaired strict suites 7/7 on CPU and MI210-hybrid; draft-MTP slower than no-spec | No — research; broader role/admission still open | `hy3_current_v7/hy3_mi210_hybrid_repaired_strict_suite_20260718T200124Z`, registry `hy3_angelslim_iq1m_mtp` block around L6808-L6881 |
| Qwen3.5-122B-A10B | UD-IQ2_M | MI210 | 736.96 pp512; 180.15/269.32 combined 2K/4K+tg512 | 44.34-45.06 no-spec; ngram+MTP 287.09 repeated / 50.77 mixed / 80.77 broad; reviewer median row wall 5.5s; AXA-2 same-quant CPU→MI210 cutover smoke executed with exact seeded continuity | 8/8 no-spec architect; reasoning-auto 0/4 final-content; ngram+MTP broad 5/8; reviewer A3 decision-grade C-CRAB P-REV-1: FA 12.5%, FR 58.3%, AUC 0.513, ECE 0.302; AXA-2 live smoke `lease_released=true` and `first_char_divergence=null` | No — research route-gated; not a patch-reviewer (FR too high); DR-3/P-GPU-1 open | `qwen35_122b_iq2m_mi210_context_20260719T001712Z`, `qwen35_122b_a10b_ud_iq2_m_architect_mi210_20260719T002502Z`, `qwen35_122b_iq2m_ngram_mtp_broad_20260719T014335Z`, `reviewer_model_ablations/rm2-next-a3-qwen35-122b-iq2-ccrab-p-rev1-20260719T204845Z`, `axa2_live_cutover_runs/axa2-live-samequant-iq2-20260720T052826Z/summary.json` |
| Qwen3.5-122B-A10B quant-asym self-spec | UD-Q4_K_M CPU verifier + UD-IQ2_M MI210 drafter | CPU+MI210 | CPU verifier baseline not measured for pp; combined K1/K2/K4 use 122B CPU target + 122B IQ2 MI210 drafter | baseline 7.08; combined K1/K2/K4 9.89 / 11.41 / 11.85 t/s (`1.40x` / `1.61x` / `1.67x`); alpha 0.945 / 0.900 / 0.787; DR-3c K2 8K/16K 10.54 / 10.43 t/s; DR-3d frontdoor before/after lease 93.69 / 94.16 t/s (`1.005x`) | DR-0e.2 final sweep passed quality 28/28, combined-vs-CPU output stability for all K arms/tasks, and cleanup; DR-3c broader K2 package passed quality 24/24; DR-3d opportunity-cost gate passed with cleanup | No — keep-candidate; production-named `P-GPU-1` certification still required before serving/NumericSwarm | `dr0_quant_asym_self_spec/dr0_quant_asym_self_spec_20260720T060423Z_dr0e2_full_k_sweep_final/summary.json`, `dr3_quant_asym_k2_admission/dr3_quant_asym_k2_admission_20260720T071816Z_dr3c_default_ctx8192_16384_r1/summary.json`, `dr3_frontdoor_opportunity_cost/dr3_frontdoor_opportunity_cost_20260720T074853Z_live_ctx8192_r1/summary.json`, `docs/reference/quant-asymmetric-self-spec-serving-design-2026-07-20.md` |
| Qwen3.5-122B-A10B | UD-IQ2_M | CPU | 122.31/114.40 pp2K/8K | 6.24 tg16 | prefill/cost sizing only | No — decode too slow; hybrid-placement input | `cpu_prefill_compute/20260719T014801Z_qwen35_122b_iq2_cpu_prefill` |
| Qwen3.5-122B-A10B status-quo self-review | UD-Q4_K_M | CPU | reviewer prompt throughput about 83-85 t/s on longer rows | RM-2 median row wall 41.4s | decision-grade C-CRAB P-REV-1 failed: FA 45.8%, FR 41.7%, AUC 0.463, ECE 0.385 | **No** — not a patch-reviewer | `reviewer_model_ablations/rm2-next-a1-architect-statusquo-ccrab-p-rev1-20260719T210513Z` |
| Qwen3-Next-80B-A3B-Instruct | IQ2_M | MI210 | 1220.90 pp512; 236.06/537.95/796.13 combined 2K/8K/32K+tg512 | 56.11 tg512; quality-wall 14.47-22.56; broader 16.79 | 12/12 then 23/24; code-review repair 10/10; broader role 35/42 | No — promising research, reviewer/selector not clean | `qwen3next-80b-iq2m-sourcehead-v7-gpu-context-clean-20260718T235036Z`, `qwen3next_80b_iq2m_mi210_broader_role_quality_probe_20260719T034859Z` |
| Qwen3-4B-Instruct-2507 | Q8_0 | MI210 / CPU | MI210 3874/3153/2417 pp512/4K/8K; CPU 479/374/321 | MI210 145.39; CPU 10.12 | grammar verifier 12/12, expanded 22/24, policy 15/18 | No — small-verifier candidate; prompt-robust gate open | `qwen3_4b_instruct_2507_q8_mi210_llama_bench_20260719Tmain`, `qwen3_4b_instruct_2507_mi210_verifier_grammar_slice24_20260719T033317Z` |
| Qwen3-4B-Instruct-2507 | BF16 | MI210 / CPU | MI210 3395/3154/2412 pp512/4K/8K; CPU 446/337/286 | MI210 102.46; CPU 7.14 | grammar verifier 8/12 | No — diagnostic only; Q8 faster and cleaner | `qwen3_4b_instruct_2507_bf16_mi210_llama_bench_20260719Tmain`, `qwen3_4b_instruct_2507_bf16_mi210_verifier_grammar_slice_20260719Tmain` |
| Qwen3-4B-Thinking-2507 | Q8_0 | MI210 / CPU | MI210 4013/3525/2353/991 pp512/2K/8K/32K; CPU 320/274/159/49 | MI210 119.04 current, server smoke 146.95; CPU 11.53 | server/chat content 0/3; useful output in `reasoning_content` | No — protocol-gated until content/reasoning contract is fixed | `qwen3_4b_thinking_2507_q8_mi210_context_6a8dd5ea68_20260719T045143Z`, `20260719_cpu_lane_qwen3_4b_thinking_2507_q8_k24cpu_r1` |
| gemma-4-26B-A4B UD source-head (+assistant MTP) | UD-IQ4_XS | MI210 | 269.94 no-stop free-form; load row pp2048 2449 | 126.33 no-stop n=3; post-candidate no-stop n=10 126.44; stop-string n=10 113.74; natural free-form mean 89.55; explicit-greedy natural free-form 78.0; schema about 95-122 | schema 10/10 one hash; no-stop n=10 one hash; repeated-token stop-string n=10 one hash; natural prose clean n=10 failed with 10 hashes and only 1/10 exact 160-word runs; explicit-greedy repeat failed with 10 hashes and 0/10 exact 160 | No — structured/repeated-token lanes promising, but natural free-form and ORIG speed/quality selection remain open | `k11_schema_word_array_ud_iq4xs_mtp_np4_n10_currentv7_20260719Tmain_1024`, `gemma4_ud_iq4xs_mtp_freeform_termination_20260719T035436Z`, `k11_freeform_ud_iq4xs_mtp_n10_post_candidate_20260720T063000Z`, `k11_stop_end_ud_iq4xs_mtp_n10_concurrent_pc4o_20260720T084818Z`, `k11_natural_freeform_compare_20260720T0937Z.summary.json`, `k11_natural_freeform_explicit_greedy_compare_20260720T1059Z` |
| Qwen3.5-9B MTP | Q4_K_M | MI210 | — | no-spec 74.34; draft-mtp 114.81; ngram+MTP 466.47 | repeated 1024-word output exact; earlier broader slice 13/18 | No — structured/repetitive-output niche only | `qwen35_9b_mtp_longoutput_currentv7_20260719T052017Z`, `qwen35_9b_ngram_mtp_longoutput_currentv7_20260719T052242Z` |
| LightOnOCR-2-1B-bbox (+F16 mmproj) | Q4_K_M | MI210 | 2927-4008 | 224.45-234.66, median 226.62 | useful text extraction; table markers missing; OCRBench digit wrong | No — parser comparison, not table/QA clean | `lightonocr2-1b-bbox-v7-odl-probe-20260719T0154Z` |
| Nemotron-Labs-Diffusion-14B | Q8_0 | MI210 / CPU | MI210 pp512 1700.42; CPU pp512 157.57 | MI210 tg512 69.05 / about 106 ms diffusion step; CPU tg256 2.69 | stock-v7 content-control repair 0/4; grammar/schema flags inert in diffusion sampler | No — stop-list quality/protocol blocked | `nemotron_diffusion_stock_v7/content_control_repair_sourcehead_mi210_20260719T020722Z` |
| Qwen3.6-27B dense | Q8_0 | MI210 | 854.17/807.61/666.62 pp2K/8K/32K | 29.64 tg512; RM-2 median row wall 6.2s | reviewer P-REV-1 failed: FA 54.2%, FR 16.7%, AUC 0.503, ECE 0.316; no spec selector in `llama-bench` | No — not a patch-reviewer | `qwen36-27b-dense-v7-context-20260718T2225Z`, `reviewer_model_ablations/rm2-fast-qwen36-27b-q8-ccrab-p-rev1-20260719T162109Z` |
| Qwen3.6-27B MTP artifact | Q8_0 | MI210 | 839.72 pp512; 134.70/311.90/477.89 combined 2K/8K/32K+tg512 | 30.85 tg128 | speed-only; `llama-bench` did not enable MTP | No — artifact throughput only | `qwen36-27b-mtp-q8-v7-context-20260718T222725Z` |
| Qwen3.6-27B MTP artifact | Q4_K_M | MI210 | 781.20 pp512; 146.40/327.54/471.50 combined 2K/8K/32K+tg512 | 34.80 tg128 | speed-only; `llama-bench` did not enable MTP | No — artifact throughput only | `qwen36-27b-mtp-q4km-v7-context-20260718T223647Z` |
| Qwen3.6-27B MTP artifact | F16-upcast | MI210 | 930.09 pp512; 87.67/226.28/412.26 combined 2K/8K/32K+tg512 | 19.34 tg128 | speed-only; `llama-bench` did not enable MTP | No — artifact throughput only | `qwen36-27b-mtp-f16-upcast-v7-context-20260718T224253Z` |

## Verdict buckets

**1. Clear wins (fast + quality-clean):**
- **Qwable-v1 IQ4_XS (MI210)** — 91–100 t/s, historical 18/18 deterministic; later current-v7 paired repeat was 14/18 vs Q8 13/18, so keep it as the primary reasoning route but do not overstate the old slice as protocol-independent.
- **MiniCPM-o-4_5 Q4_K_M (MI210)** — 111–127 t/s, 4/4 OCR/chart → controlled smoke executed; persistent live traffic plus API/AutoPilot restart remains unconfirmed (must run `--reasoning off`).
- **Frontdoor Qwen3.6-35B-A3B native-MTP (MI210)** — 119.7 t/s / 7.0× CPU at 8K, 100% accept (production; Gate-R obs-grade).
- **gemma-4-26B-A4B CPU worker** — 98–176 t/s, K5 gate +0.0% (live worker_general). Plus clean production rows: architect 122B (21–24), ingest 80B (10–21), worker_vision Qwen2.5-VL 4/4.

**2. Speed-only / quality-blocked (fast but not usable):**
- **Nemotron-Nano Q8** — 78–84 t/s but broad visible-content behavior failed after the small-slice repair.
- **gemma-4-26B-A4B MI210 free-form** — UD-IQ4_XS assistant-head MTP now passes no-stop n=10 exact-count free-form on post-candidate `12a292f0c21d` and a concurrent stop-string n=10 slice, but matched ORIG-Q4 was faster (`141.79` vs `113.74 t/s`) and quality retention remains open. The 2026-07-20 token-trace triad shows ORIG-Q4 natural prose still diverges under GPU MTP+np4, no-spec+np4, and no-spec+np1, while the CPU no-spec np1 trace is deterministic with one hash. The pre-sampling A/B then ruled out graph replay and flash-attention as sufficient fixes. External-head MTP and multi-slot scheduling are not required to reproduce the defect; the remaining K11.1 root cause is GPU/backend-path specific.
- **Bonsai-8B/27B Q1_0** — speed-only/orphan or 6-word-IF fail; no role-quality clearance.
- **Ternary Q2_g64** — ngram accelerates to 22.9 t/s but 6/8, empty `<think>` tags.
- **Qwen3-VL-8B/30B and extra vision candidates** — paused behind concrete fixture/role-gap fixes.
- **Hy3** — repaired strict suites now pass 7/7 on CPU and MI210-hybrid, but throughput remains 5–11 t/s and draft-MTP is slower than no-spec; research-only pending broader role/admission.
- **GLM-5.2** — additionally slow (2.56 t/s) and rejected for production patch-review on the current policy by decision-grade C-CRAB P-REV-1 failure. JudgeBench-GPT pairwise exact-choice is positive (`22/24`), and SWE-bench-Verified accept controls are positive (`22/24`, `FR 8.3%`, parse `0/24`), but neither clears hard-negative patch-review risk. RM-2 fast alternatives do not clear the role: Qwen/Qwable standalone fail, and Qwen+Qwable scaffold is only a repair hypothesis. Do not rerun unchanged GLM C-CRAB/SWE policies.

**3. Broken / failed load:**
- **Ternary Bonsai Q2_0** — loader rejects (498/498 tensors short; noncanonical PrismML packing, not corruption). Needs producer/transcode fix or a gated compat loader; Q2_g64 is the usable ternary path.
