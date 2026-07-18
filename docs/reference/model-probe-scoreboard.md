# Model Probe Scoreboard (experimental-v7)

**Living scoreboard** — one glance-able read of how every candidate model is performing on the
`experimental-v7-refresh-20260716 @ d1e5a20eb` kernel (iqk + GPU-opts + `Q2_0`). All rows are
**OBSERVATION-grade** (single-config, small-n per MEASUREMENT.md) — hypotheses, not
decision-grade. MI210 = gfx90a/ROCm 6.2; CPU = EPYC 9655. Compiled 2026-07-18 from the probe
runs scattered across the inference handoffs.

**Update rule (for the running agent):** every new model/quant probe appends a row here (model,
quant, device, pp t/s, tg t/s, quality, role-ready, artifact) — do not bury results in a
checkbox line + artifact path alone. Keep this the single source of "how are the models doing."

## Scoreboard

| Model | Quant | Device | Prompt t/s (pp) | Decode t/s (tg) | Quality | Role-ready? | Evidence |
|---|---|---|---|---|---|---|---|
| **Qwable-v1** (35B-A3B reasoner) | IQ4_XS | MI210 | 2050/1951/1764 (2K/8K/32K) | 91.5 / 100.3 (tg1024/512) | 18/18 deterministic (plain+ngram) | **Yes** — primary reasoning-heavy route | `qwable_reasoning_economics/…20260717T184136Z` |
| Qwable-v1 | IQ4_XS | CPU | — | 15.96 | 18/18 | Yes (CPU fallback) | `…iq4_cpu_expanded_final` |
| Qwable-v1 | Q8_0 | MI210 | 2086/1982/1648 | 102.9 / 104.1 | 6/6; no Q8-only gain | IQ4_XS preferred (½ footprint) | idx L101,180 |
| **Frontdoor Qwen3.6-35B-A3B** | Q8_0 native-MTP | MI210 | — | no-spec 95.4; **MTP 119.7** (8K, 100% accept); 2K/32K 123.6/105.2 | production | **Yes** — production; Gate-R residency (obs) | `k35_stack_context_matrix/frontdoor_pgpu1_candidate` |
| Frontdoor Qwen3.6-35B-A3B | Q8_0 | CPU | — | no-spec 17.1; 2K/32K 21.6/10.2 | production | Yes | same |
| **gemma-4-26B-A4B worker** (ngram+draft-mtp) | Q8_0 | CPU | ~120–136 | 2K 175.8 / 8K 110.0 / 14K 97.6 | K5 gate **+0.0%** MMLU-Pro/GPQA | **Yes** — live worker_general | K35 worker curve, idx L206 |
| gemma-4-26B-A4B | Q8_0 (+v6 MTP) | MI210 | 274–282 | single-slot MTP ~158; schema 122 | schema 10/10; **free-form multi-slot 8–9/10, 2–3 hashes** | **No** for GPU free-form worker (K11.1 open) | `k11_gemma4_long_mtp_np4_n10…20260718T142203Z` |
| **Architect Qwen3.5-122B** (NEXTN) | UD-Q4_K_M | CPU | — | 2K 23.9 / 8K 20.7 (accept 818/820) | production | Yes | idx L207 |
| **Ingest Qwen3-Next-80B-A3B** | Q4_K_M | CPU | — | 2K 20.5 / 8K 15.9 / 32K 9.7 | production | Yes | idx L208 |
| **GLM-5.2** (754B glm-moe-dsa) | UD-IQ2_M | CPU | ~26 (12K); 24→17 as KV grows; 64K 6.8 | **~2.56** (12K); 64K 1.20 | exact-answer FA 0.0%/FR 16.7%; **patch-review over-approves (FA up to 91.7%)**; DSA-DENSE-MASK | **No** — quality-blocked | `glm52_reviewer_corpus_direct/…ccrab-patchdiff…` |
| GLM-5.2 native-MTP | UD-IQ2_M | CPU | — | — (scaffold only) | builds + bounded draft-mtp smoke | No — no throughput yet, quality-gated | tree-draft B6/K23.1 |
| **MiniCPM-o-4_5** vision (+F16 proj) | Q4_K_M | MI210 | 732–884 | 111–127 | 4/4 OCR/chart (`--reasoning off`) | **Yes** — activated `vision_escalation` (live smoke 4/4) | `k35-vision-escalation-live-smoke-20260718T1225Z` |
| MiniCPM-o-4_5 | Q4_K_M | CPU | — | 12.0–14.1 | 4/4 (reasoning off) | (CPU fallback) | `k35-minicpm-o45-reasoning-off` |
| Qwen2.5-VL-7B worker_vision (+mmproj) | — | MI210 | — | 16.9–21.3 | 4/4 | **Yes** — live worker_vision + escalation safety alias | `k35-vision-matrix-20260717T1500Z` |
| Bonsai-8B | Q1_0 | MI210 | 2349 / 1751 (2K/8K) | 38.4 | speed-only (no quality run) | No (research) | `v7-bonsai8b-gpu-bench-current-20260718T141319Z` |
| Bonsai-27B | Q1_0 | MI210 | 799 / 759 | 11.2 (decode-slow) | 6/8 strict (fails 6-word IF) | No | `bonsai27_q1_mi210_llama_bench_20260718T150243Z` |
| Ternary Bonsai | Q2_g64 | MI210/CPU | ~26 (p512) | raw 10.5 (MI210) / 8.4 (CPU); ngram 9.8→22.9 | 6/8 strict; retry wrong output | No (speed-only) | `ternary_q2_g64_quality_gate/…` |
| Ternary Bonsai | Q2_0 | — | — (fails load) | — | **loader rejects** — 498/498 tensors short (noncanonical layout) | No — broken load | `ternary_bonsai_q2_layout_contract_20260718Tcodex.json` |
| Nemotron-Nano | Q8 | MI210 | — | 84.0 / 84.5 | 0/5 → 4/5 @512tok; **fails strict JSON** (budget→reasoning) | No — protocol-blocked | idx L222 |
| Qwen3-VL-8B (+F16 proj) | Q4_K_M | MI210 | — | 110–126 | 3/4 — chart→"Moldova" | No (candidate; MI210 chart-fail; CPU 4/4) | `k35-qwen3vl8-candidate` |
| Qwen3-VL-30B (MoE) | — | MI210 | — | 36–50 (short) | 3/4 — chart→"Moldova" | No — replaced by CPU alias→MiniCPM-o | `k35-vision-matrix` |
| SuperGemma4-26B multimodal (+F16 proj) | Q8_0 | MI210 | — | 80–84 | 4/4 | No — MiniCPM-o preferred (faster/smaller) | `k35-supergemma4-candidate` |
| PaddleOCR-VL-1.6 (+mmproj) | GGUF | MI210 | — | 484–490 (OCR) | OCR clean; **table TEDS 0.0** (vs ODL 0.78) | No — OCR specialist, not general QA | `paddleocr-vl-first-smoke` |
| Hy3 (hybrid) | — | MI210-hybrid / CPU | — | 11.5 / 5.2 (no-spec) | 5/6 — fails 6-word IF | No (research) | idx L221 |

## Verdict buckets

**1. Clear wins (fast + quality-clean):**
- **Qwable-v1 IQ4_XS (MI210)** — 91–100 t/s, 18/18 deterministic → primary reasoning route (Q8 works too, no quality gain, 2× footprint).
- **MiniCPM-o-4_5 Q4_K_M (MI210)** — 111–127 t/s, 4/4 OCR/chart → **activated** as `vision_escalation` (must run `--reasoning off`).
- **Frontdoor Qwen3.6-35B-A3B native-MTP (MI210)** — 119.7 t/s / 7.0× CPU at 8K, 100% accept (production; Gate-R obs-grade).
- **gemma-4-26B-A4B CPU worker** — 98–176 t/s, K5 gate +0.0% (live worker_general). Plus clean production rows: architect 122B (21–24), ingest 80B (10–21), worker_vision Qwen2.5-VL 4/4.

**2. Speed-only / quality-blocked (fast but not usable):**
- **Nemotron-Nano Q8** — 84 t/s but fails strict JSON (burns budget on reasoning).
- **gemma-4-26B-A4B MI210 free-form multi-slot** — ~158 t/s single-slot but multi-slot determinism fails (2–3 hashes); K11.1 open.
- **Bonsai-8B/27B Q1_0** — very fast pp, but no quality clearance / 6-word-IF fail.
- **Ternary Q2_g64** — ngram accelerates to 22.9 t/s but 6/8, empty `<think>` tags.
- **Qwen3-VL-8B/30B** — fast but chart-fixture fail (3/4).
- **Hy3** — 5–11 t/s, 5/6; research-only.
- **GLM-5.2** — additionally slow (2.56 t/s) AND patch-review quality-blocked (exact-answer judging OK).

**3. Broken / failed load:**
- **Ternary Bonsai Q2_0** — loader rejects (498/498 tensors short; noncanonical PrismML packing, not corruption). Needs producer/transcode fix or a gated compat loader; Q2_g64 is the usable ternary path.
