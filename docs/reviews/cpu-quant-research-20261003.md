# CPU quant research for DS41 and Q38FN — quality evidence, EXL3 re-derivation, CPU formats (2026-10-03)

**Source**: `/mnt/raid0/llm/tmp/cpu-quant-research-20261003/report.md` (scratch; copied verbatim below the line apart from path clarifications)
**Date**: 2026-10-03
**Author session**: ak-ds41-main
**Status**: research review — not a measurement claim. Labels: **M** measured (by us or a cited source), **C** computed here, **I** inference.
**Operator decisions (2026-10-03/04)**: (a) IQ\*_K/KS self-quant for Q38FN (Qwen3.8-Flash-Next) is allowed "exceptionally if justifiable" — this lifts the no-requant constraint stated below for that one option only; (b) DS41 (DeepSeek-V4.1-Flash) lossless MXFP4 experts: "plan it".
**Companion**: [quant-variant-survey-20261003.md](quant-variant-survey-20261003.md) (the survey this follow-up corrects; see §5).
**Paths**: `iqk_dispatch.cpp`, `ggml-cpu/…`, `arch/x86/…` and `iqk_*.cpp` refer to the experimental tree `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925` @ `74ee5c502`. "PR #NN" means ik_llama.cpp pull requests.

---
**Labels:** **M** = measured (by us or a cited source). **C** = computed here. **I** = inference.

## 1. Public quality evidence

### 1.1 Q38FN: structural facts that set up the comparison

**What the type maps are.** Local headers are verified; bartowski's map is inferred from published file sizes.
- **`ffn_down_exps` is 640 wide**, so no 256-block type fits.
  - UD: IQ4_NL ×43 + Q8_0 ×5.
  - Our local uniform file: IQ4_NL ×42 + Q5_1 ×6.
  - bartowski: IQ4_NL by the same rule. AtomicChat's card states the fallback: ask for IQ2_XXS and you get IQ4_NL; ask for Q6_K and you get Q8_0.
- **The PLE/n-gram table (51 B params)** is IQ4_NL with no imatrix in both local files. bartowski's is inferred to be IQ4_NL too: its IQ4_NL − IQ4_XS size gap (2.61 GB) equals gate/up alone.

**So the trade is:**
- bartowski: gate/up **+0.81 bpw** (IQ4_XS 4.25 vs IQ3_S 3.44), about +8 GB on file.
- In exchange: dense **Q8_0 → IQ4_XS/Q5_K**, about −1.8 GB/token.
- Dense is **~65% of per-token active parameters** on Q38FN (C: 4.31 G dense vs 2.36 G expert params per token). That is a far larger share than on the 35B-A3B siblings below, and it is the main risk in transferring their results.

**Not verified:** bartowski's real per-tensor map. A header range-read of `IQ4_XS-00001` (a few MB) settles it. That counts as a download, so it needs the operator's OK.

### 1.2 Q38FN: published numbers

KLD is comparable only within one table.

| Source | Reference / corpus | Rows (mean KLD; top-1) | Caveats |
|---|---|---|---|
| **unsloth official** (unsloth.ai/docs/models/qwen3.8-next) | not stated | UD-IQ4_XS 93.7 GB **0.0836; 89.55%** · UD-Q4_K_XL 0.0469; 92.26% · UD-Q3_K_XL 0.1065; 88.32% · UD-IQ3_XXS 0.1651; 85.41% · UD-Q5_K_XL 0.0304; 93.68% · **Q8_0 0.0266; 94.12%** | No bartowski row. Q8_0 shows a large floor (agentionai warns wikitext overlaps the memorised n-gram set) |
| **turboderp** (exllamav3) | FP, self-generated in-domain, 14.5k in + 45.6k out tokens, floor 0.0025 | UD-IQ4_XS 0.0165 · UD-Q4_K_XL 0.0084 · UD-IQ3_XXS 0.0349 · EXL3 3.05 0.0177 · 4.05 0.0067 · NVFP4 W4A16 0.0100 · NVFP4 W4A4 0.0241 | No uniform row. Absolute KLD is 5× lower than unsloth's (corpus effect) |
| **ukisai Swift-1.5** (HF card) | the **finetune's** BF16; wikitext-2, 100×512 and 9×32k | built with **bartowski's exact type map**: IQ4_XS **0.1305 @512 / 0.0929 @32k; top-p 88.91%** · Q8_0 0.0297 / 0.0220; 94.91% · IQ4_NL 0.0926 @32k · Q4_K_M 0.1100 · Q4_K_S 0.1311 · Q4_0 0.2593 · Q4_K_L 0.0740 | A finetune, not Q38FN. Q5_K_M (0.1386) is worse than Q4_K_M, an anomaly |
| **AesSedai** (HF card) | BF16; corpus not stated | PLE at Q8_0: IQ4_XS mix (Q8_0 dense / IQ3_S gate+up / IQ4_XS down) **0.0762** · Q4_K_M (Q8_0 / Q4_K / Q5_K) **0.0342** · Q5_K_M 0.0202 · IQ3_S 0.1604. PLE at Q4_0: 0.0844 / 0.0435 / 0.0309 | **Gate/up IQ3_S → Q4_K with dense held at Q8_0 cuts KLD 55%** |
| agentionai AP | `--kl-divergence`, c=2048, held-out | AP-Q4_K_XL 0.0992; 85.71% · AP-IQ4_XS 0.1584; 82.89% | custom mixes |
| AtomicChat | BF16 PPL 4.0445; 4000×512 chunks | AD-4.27bpw 0.084; 89.5% | custom mix |
| ji-farthing (ik_llama) | BF16 | IQ4_KT v2: 0.1328 English / 0.1246 code; top-1 86.3% / 93.2% | ik-only types |
| julianmb | wikitext PPL, c=2048 | imatrix IQ4_XS, PLE Q8_0: 4.2809 · PLE IQ4_NL: 4.2932 · static: 4.5221 | PPL only |

**Not found anywhere:** a bartowski Q38FN row, a same-harness UD vs uniform pair on Q38FN, or any Reddit, X, GitHub or ik thread with Q38FN KLD.

### 1.3 Same-architecture siblings (hybrid GDN MoE), same harness

| Model / source | UD-style (Q8 dense, IQ3_S gate/up) | bartowski uniform IQ4_XS | ratio |
|---|---|---|---|
| Qwen3.5-35B-A3B, unsloth table | AesSedai IQ4_XS 0.0235 (99.9% KLD 0.8067) | **0.0234** (0.7265) | **1.00×**; uniform tail better |
| Qwen3.6-35B-A3B, unsloth chart (±5%) | UD-IQ4_XS ≈0.033 | ≈0.027 | ≈0.83× |
| Qwen3.5-35B-A3B, localbench (250k tokens, top-40 KL) | UD-IQ4_XS 0.179; 92.8% (Q8_0 0.121; 95.4%) | ≈0.200 | 1.12× raw, ≈1.36× above the Q8 floor |
| Qwen3-30B-A3B, ubergarm (mid-2025) | UD-Q4_K_XL 0.0165 | Q4_K_M 0.0101 | 0.61× (older recipe generation) |

Caveat: on the siblings `ffn_down` is not 640 wide, so bartowski's down is real IQ4_XS there, and the dense share is smaller. No isolated "dense Q8_0 vs IQ4_XS, experts fixed" study exists for any model.

### 1.4 DS41: Q4_K-from-FP4 vs a lossless MXFP4 repack

| Source | Reference / corpus | Rows | Caveats |
|---|---|---|---|
| **unsloth, DeepSeek-V4-Flash** (unsloth.ai/docs/models/deepseek-v4) | official weights (PPL 4.5319), wikitext-2, c=512 | **UD-Q4_K_XL (native MXFP4 experts, Q8_0 rest) 155.1 GB: 0.0102; 96.28%** · bartowski MXFP4 0.0105; 96.18% · **antirez Q4KExperts-F16 164.6 GB: 0.0290; 93.94%** (imatrix variant 0.0291; 93.95%) · antirez IQ2XXS 0.4207; 77.92% | Predecessor model. unsloth notes Q4_K must round each weight (≈5.2% RMSE) |
| Tied Trit-Planes, arXiv 2608.08910, DS4-Flash | corpus not stated | released MXFP4 (4.25 bpw): PPL 4.39 @512 / 3.15 @2048 · Q4_K imatrix (4.5 bpw): 4.50 / 3.20 | +2.5% / +1.6% PPL for more bits |
| sokann DS4-Flash | own MXFP4 repack | Q4: 0.115; 88.79% | Reference suspect: PPL matches unsloth but KLD is 4× higher |
| AtomicChat DS4-0731 | "AD-BF16" | AD-MXFP4 0.1564 · UD-Q4_K_XL 0.1557 | Unexplained floor |
| Lucebox, DS41 | FP4 teacher | Q2-class only | **No Q4 or MXFP4 rows** |
| antirez card; PR #28696; JigSawPT / smalinin / mxxm-t | — | no KLD; JigSawPT gives logit correlation 0.9967 at 1,401 tokens | — |

**Read (I).**
- DS41 antirez Q4 is most likely at ~2.5–3× the KLD of a lossless repack, with ~2 pp lower top-1.
- DSpark acceptance may rise with lossless experts (unmeasured). The Q38FN sensitivity is 1.5–2%/0.01 α (B10), so +0.01 α would be worth about the byte gain.

### 1.5 Verdict

- **KLD ≤1.25×: more likely than not (~60%).**
  - For: sibling pairs at 0.83–1.00×, and the extra bits land on the dominant lever.
  - Against: localbench's floor-adjusted 1.36×, the finetune proxy's 1.25–1.77× above floor (cross-harness), and Q38FN's dense-heavy active compute.
- **Top-1 within 1 pp: undecided (~45–50%).** The Swift proxy loses 6.0 pp from its own Q8_0, vs UD's 4.6 pp in unsloth's harness: about 1.4 pp worse.
- **What public evidence rules out:** both a large failure (≥2× KLD) and a clear win.

**What to do instead of the Q8_0 download:**
1. **Phase S first.** §2 predicts a serving-shape gain below +8%.
2. If it passes, ask the operator for the header range-read.
3. Download bartowski and run a **paired per-item task eval** vs UD, which is the project gate (wiki: KLD/PPL is fidelity, not quality).
4. Only if the eval is ambiguous, run relative KLD with UD-Q5_K_XL (158 GB, lower floor) as the reference.

## 2. Re-deriving "EXL3 on CPU = +0–6% for Q38FN"

### 2.1 Inputs

**Per-token bytes, N=1 (C, from the header census of the local uniform file):**

| class | params/token | uniform bytes | EXL3 3.05 |
|---|---:|---:|---|
| routed experts | 2.359 G | 1.296 GB | K3 → 0.885 GB (INF-71, exact) |
| attn_qkv / gate / q / output, ssm_out, k, v | 2.674 G | 1.571 GB | K5 |
| lm_head | 0.636 G | 0.521 GB (Q6_K) | K5 |
| shared expert | 0.236 G | 0.130 GB | K5 |
| hc_* | 0.640 G | 0.353 GB | unknown (BF16 would be 1.28 GB) |
| router `ffn_gate_inp` | 0.063 G | **0.252 GB, F32** | — |
| **total** | 6.67 G | **4.16 GB** | **≈3.75 GB** |

**Correction 1 (C): EXL3's dense half is byte-neutral.**
- The K5 linear tensors come to 3.546 G × 5/8 = 2.216 GB, against 2.222 GB for the same tensors in the uniform file.
- So EXL3 3.05 is −9.9% vs uniform (not −13%) and −35% vs UD. If hc stays BF16, it is +12% vs uniform.

**Side finding:** the F32 router is 6% of uniform per-token bytes. BF16 would save 3%, but it needs a requant and a routing check.

**Correction 2 (C): elasticity.**
- UD → uniform: +10.5% to +15.2% decode for −28.3% bytes. As log-elasticity that is **0.30–0.43**, not 0.4–0.5.
- It is confounded by the IQ3_S dequant path, so the pure-bytes elasticity is lower.
- Regime anchors:
  - tg128 at 48T post-BIOS: 59.5 ms for 4.16 GB = 70 GB/s = 17% of the 410 GB/s 48T read ceiling.
  - INF-71: MTP serving at 16.6% of the pre-BIOS 153 GB/s.
- No post-BIOS per-node census exists at the serving shape, and it is the key missing input.

**Correction 3 (C): MTP verify reads the expert union.**
- With verify N=5 and 10-of-512 routing, distinct experts per layer are U = 3.3× (route correlation 0.6) to 4.8× (independent) of one token's.
- Experts are therefore 50–69% of verify bytes, while dense is read once.
- INF-71 divided plain-token bytes by 3.79, which understates experts.

**Decode cost (M, X1).**
- Per core: K3 25 G w/s, K4 34.6 G w/s, compute-bound.
- At 48T: K3 ≈1.2 T w/s ≈ 459 GB/s-equivalent, against the 410 GB/s 48T ceiling.
- At 96T, if it scales (I): ≈2× the bandwidth rate.
- Assumption (I): iqk IQ4_XS decode ≈70 G w/s per core. The debit is the K3 − IQ4_XS difference.

### 2.2 Results (C)

Speed vs the uniform/bartowski anchor:

| shape | variant | bytes vs uniform | e=0.35 | e=0.6 | e=1.0 |
|---|---|---:|---:|---:|---:|
| N=1 | GGUF dense + EXL3 K3 experts (same bytes as full 3.05) | −9.9% | +3.6% | +6.3% | +11.0% |
| N=1 | GGUF dense + EXL3 K4 experts | −2.8% | +1.0% | +1.7% | +2.9% |
| N=1 | hypothetical IQ4_KS dense + IQ3_KS experts | −13.8% | +5.1% | +9.1% | +16.1% |
| N=5 verify | EXL3 K3 experts | −19 to −22% | +7–8% | +13–15% | +23–28% |
| N=5 verify | EXL3 K4 experts | −5 to −6% | +2% | +3–4% | +6–7% |
| N=5 verify | hypothetical IQ4_KS / IQ3_KS | −19.5 to −21% | +7–8% | +13–15% | +24–27% |
| N=1 | UD vs uniform (reference) | +39.6% | −12% | −19% | −28% |
| N=5 verify | UD vs uniform (reference) | +12 to +19% | −4 to −6% | −7 to −10% | −11 to −16% |

**Net of the K3 debit at e=1.** The two bounds are fully overlapped decode (= gross) and fully serialized decode:

| shape | 48T | 96T |
|---|---|---|
| N=1 | −2.5% … +11% | +3.2% … +11% |
| N=5 verify | −5% … +28% | +6% … +28% |

**Stated range:**
- **Today (e ≈ 0.3–0.4):** +0–4% plain, +2–8% MTP, with the debit of the same order. This confirms +0–6% and the NO-GO.
- **e → 1:** plain about +4–7% at the midpoint; MTP serving about +9–17% midpoint, +28% ceiling. The ceiling needs 96T and a well-overlapped fused kernel; at 48T the realistic net is about 0.

**Assumptions:**
1. Dense keeps the GGUF uniform map. EXL3 K5 dense adds no byte gain plus unmeasured decode cost (K5 never pairs in `byte_pair_ok`).
2. The union model needs validating with the routing tap.
3. m per expert under MTP is ≈1.0–1.6, so trellis extraction is barely amortized.
4. α is unchanged. Δα −0.03 erases the MTP gain.
5. The X1 per-core rates transfer in situ. That transfer has "failed four times" before.

**Quality caveat.** The 0.0177 KLD is EXL3 3.05 with **K5 dense**. The byte-efficient hybrid (K3 experts + IQ4_XS dense) has lower-precision dense, so its KLD is likely higher, plausibly 0.02–0.025 on turboderp's scale (I). Pairing K3 experts with Q8_0 dense holds quality but saves only 5% of bytes vs UD.

**Bottom line.**
- EXL3's CPU value is an expert-only, MTP-shape lever. Reopen it only when a serving-shape census shows the expert stream binding (≥~60% of ceiling).
- Even then it must beat the same-bytes IQ3_K/IQ3_KS GGUF option on quality by enough to pay for 6–10 sessions plus the debit.

## 3. CPU-suited formats

### 3.1 What our tree supports (`fastload-ds41-20260925` @ `74ee5c502`)

- **`iqk_typeA_supported`** (`iqk_dispatch.cpp:128`): Q4_K/Q5_K/Q6_K/Q8_0/Q4_0/Q5_0/Q4_1/Q5_1, IQ2_XXS/XS/S, IQ3_XXS/S, IQ4_XS. **IQ4_NL, MXFP4 and NVFP4 are absent.**
- **Compiled iqk sources** (`ggml-cpu/CMakeLists.txt:57-61`): kquants, iquants, legacy_quants, quantize_min, stubs.
- **Vendored but not compiled:**
  - `iqk_gemm_iqk_quants.cpp` (5,473 lines): IQ2_K/KS/KL, IQ3_K/KS, IQ4_K/KS/KSS, IQ5_K/KS, IQ6_K and their `_R4` variants, plus converters to `q8_k_r8`.
  - `iqk_gemm_ktquants.cpp`, `iqk_gemm_1bit.cpp`, `iqk_gemm_floats.cpp`, and the full `iqk_quantize.cpp` (10,415 lines; includes `quantize_iq4_ks`).
  - `iqk_stubs.cpp` returns false for these.
- **IQK/KT types are `#define` casts only** (`iqk_ext_types.h`: IQ4_KS=144, IQ3_KS=156, IQ2_KL=157, IQ4_KT=155, …) against `GGML_TYPE_COUNT = 43`. There are no `type_traits` rows or block structs, so **our binary cannot load or produce these GGUFs**.
- **The iqk MXFP4 / IQ4_NL kernels exist** (`iqk_gemm_legacy_quants.cpp:641-785, 2076-2117`) but are unreachable through the allowlist. These types run on mainline `iq4_nl_8x8` / `mxfp4_8x8` AVX2 repack today.
- **NVFP4** (type 40) has an AVX2-only x86 `vec_dot` (`arch/x86/quants.c:1113`). There is no NVFP4/ModelOpt handling in `convert_hf_to_gguf.py`.
- `/mnt/raid0/llm/ik_llama.cpp` (`c04881fc0`) has all IQK/KT types and could be used as a measurement instrument (the INF-26 T2 precedent).

### 3.2 Candidates

| Format | bpw | Quality per bit | AVX-512 decode cost | Published weights | Our tree |
|---|---|---|---|---|---|
| **IQ4_KS / IQ5_KS / IQ4_KSS** | 4.25 / 5.25 / 4.0 | Error vs IQ4_XS: 1.85% vs 2.54% (L3.1-8B), 0.72% vs 1.23% (Gemma2-27B), PR #83. Qwen3-30B-A3B IQ4_KS KLD 0.0146 @15.5 GiB vs UD-Q4_K_XL 0.0165 @16.5 GiB. Gemma-3-27B QAT: iq4_ks PPL 8.1755 @4.48 bpw vs q4_0 8.2500 @5.10 | Lookup decode, ≈ IQ4_XS (PR #83). 7950X 2T TG: IQ4_XS 13.58 vs Q4_0 12.92. `_R4` TG +3–54% (PR #150) | none for Q38FN or DS41 | vendored; unregistered |
| **IQ2_K…IQ6_K, IQ3_KS, IQ2_KL** | 2.375–6.5 | IQ4_K error 40% below Q4_K_S (L3.1-70B). IQ2_KL beats Q2_K | K-quant-class TG (Zen4 IQ2_KL 19.21 vs Q2_K 19.62) | none (one abliterated V4-Flash) | vendored; unregistered |
| **IQ1–IQ4_KT** (QTIP trellis) | 1.75–4.0 | ~0.2 bpw better than IQK at equal error (PR #113) | Compute-bound: 7950X IQ4_KT TG 3.27 t/s @2T, 11.30 @8T, vs ~13.6–14.5 for IQ4_XS/IQ4_KSS (PR #541). Emits fp32 per weight | Q38FN: ji-farthing IQ4_KT/IQ3_KT (down IQ4_NL) | plumbing absent; INF-26 T2/T3 |
| **EXL3 mul1** | any | Best measured on Q38FN (4.05: 0.0067). Gemma-4-12B same harness: GGUF Q5_K_M beats EXL3 4.0 at equal file size (0.0172 vs 0.0248, intake-1509) | ≈4 uops per 16 weights. Per core K3 25 / K4 34.6 G w/s (M) | turboderp Q38FN (reclaimed locally). DS41 EXL3s ≤3.5 bpw | none; 6–10 sessions |
| **MXFP4** | 4.25 | Lossless for DS41 experts. As a PTQ of BF16 it is worse than IQ4_NL | 16-LUT + E8M0 shift, IQ4_NL class. ik has Zen4 MXFP4/MXFP4_R8 | DS41: JigSawPT, smalinin, mxxm-t (incompatible containers) | registered; iqk kernel unreachable |
| **NVFP4** | 4.5 | Q38FN experts-only NVFP4 + BF16 dense: KLD 0.0100 (turboderp "W4A16"; exact pack unresolved), vs UD-IQ4_XS 0.0165. Qwen3-4B PTQ: KLD 0.110 | 16-LUT + E4M3 scale per 16. Upstream x86 SIMD shelved; ours is AVX2 only | Q38FN: nvidia NVFP4 (133 GB, experts only; GDN/attn/router/hc/shexp/lm_head BF16), RedHatAI, RadixArk. DS41: nvidia NVFP4 492 GiB (losslessness unverified). No NVFP4 GGUFs | registered; slow path; no converter |
| **Q4_0 / Q8_0 + VNNI** | 4.5 / 8.5 | Q4_0 poor without QAT: Swift Q38FN Q4_0 KLD 0.2593, the worst row | cheapest | everywhere | in allowlist |
| **LUT GEMV** (T-MAC, Vec-LUT, BitNet) | ≤2 mostly | n/a at 4-bit | T-MAC 4-bit 38 vs 32 t/s on M2-Ultra; no server-x86 4-bit win | none | none |
| **AQLM / VPTQ / HIGGS / any4** | 2–4 | strong in papers | GPU-first; AQLM numba CPU only 3.7–4.1× FP32 | none | none |

### 3.3 Ranking: gain × quality × effort, assuming kernels improve

**Q38FN**

| # | Option | Decode gain | Quality | Effort / precondition |
|---|---|---|---|---|
| 1 | iqk IQ4_NL (+MXFP4) allowlist | `ffn_down` ≈1/3 of expert bytes in every file; experts are 50–69% of verify bytes. Unmeasured, likely 1–4% (I) | none | ~1 session, NEW-1-style; NMSE + non-IQ regression gate. **Do first** |
| 2 | bartowski IQ4_XS swap | N=1 +10–15% (M, local proxy); serving shape +4–6% at e≈0.35 (C), +11–16% at e=1 | KLD probably ≤1.25×; top-1 undecided | Phase S free; then 97.7 GB + task eval |
| 3 | IQ*_K/KS port + self-quant (IQ4_KS or IQ3_K gate/up, IQ5_KS/IQ4_KS dense, IQ4_NL down) | Same bytes as the EXL3-K3 options, **no decode debit**: +5% today → +16% (N=1) / +24–27% (MTP) bandwidth-bound | ~25–40% lower error than IQ4_XS | Operator lifts the no-requant constraint; type registration (the `715383cde` OOB class) + compile vendored code + imatrix; ~2–4 sessions |
| 4 | EXL3 K3 experts + GGUF dense | today +0–6%; e=1: −2…+11% (N=1), −5…+28% (MTP) | 3.05 ≈ UD with K5 dense; hybrid unproven | 6–10 sessions; no prefill fallback (KS-3) |
| 5 | NVFP4 experts (nvidia repack) + Q8_0 dense | ≈0 vs UD | KLD ≈0.010 vs 0.0165: a quality upgrade | converter + AVX-512 kernel + 133 GB |
| 6 | KT trellis | negative or neutral (4× compute) | ~0.2 bpw better than IQK | 3–6 days; INF-26 T2 gate |
| 7 | ISTA GSQ-RCO IQ3_S | worse than uniform at N=1; ≈ at MTP | task claims only | 83.6 GB; BF16 hc outside iqk |
| 8 | Q4_0+VNNI / LUT / AQLM-class | no 4-bit x86 win shown | Q4_0 poor | flag only |

**DS41**

| # | Option | Decode gain | Quality | Effort / precondition |
|---|---|---|---|---|
| 1 | **Lossless MXFP4 experts spliced into antirez's container** | −2.0% bytes (N=1), −3.5% (N=3) → ≈ +1–2%, plus possible α gain | KLD ≈2.8× lower, top-1 ≈ +2.3 pp (DS4-Flash) | (a) iqk MXFP4 allowlist first, else it may be slower than iqk Q4_K. (b) Splice tool keeping antirez's `e4m3_e8m0_32_row264` engram. (c) ~290–300 GB download vs 232 GB free: operator decides the disk plan. ~2 sessions. **Promote from park to planned** |
| 2 | Native FP8 dense (~8.03 bpw lossless vs Q8_0 8.5) | ≈ −3.5% N=1 bytes, ≤ +1.5% | ≥ Q8_0 | New ggml type + converter + kernel. The loader already decodes e4m3_e8m0 for engram |
| 3 | Dense Q6_K/Q5_K | +3–4% | lossy | needs a requant (excluded) |
| 4 | nvidia DS41 NVFP4 | none (larger) | unverified | no |
| 5 | EXL3 | — | lossy (<4.25-bpw source) | no |
| 6 | IQ*_K | — | no better than lossless MXFP4 | no |

## 4. What each flagged option would take

- **IQ*_K/KS (Q38FN).** Operator lifts the self-requant constraint. Then:
  - register ~15 types (`ggml.h`, `type_traits`, `ggml-common.h`, GGUF);
  - choose the ID policy: honour ik's 137–157 and ripple through the CUDA/HIP tables, or remap and lose ik GGUF compatibility;
  - compile the kernels and quantizer and remove the stubs;
  - build an imatrix;
  - gate on NMSE, coherence and a paired task eval.
- **EXL3.** Fix INF-71's MTP accounting to use the expert union. Run a post-BIOS serving-shape census. Answer the 3.05 quality question (~2–5 GB). Then port.
- **NVFP4 (quality).** ModelOpt `MIXED_PRECISION` converter (per-tensor `weight_scale_2`; issue #20504 shows the pitfalls), an AVX-512/iqk GEMV, and 133 GB, of which 53.7 GB is FP8 MTP/PLE we don't need.
- **KT.** INF-26 T2 as written.
- **LUT / AQLM / VPTQ / HIGGS.** Wait for a published x86 server decode win at ≥3 bpw, then an intake.
- **Router F32 → BF16.** −3% bytes; one-tensor-class requant plus a routing-agreement check.

## 5. Corrections to the prior survey and INF-71

1. EXL3 3.05 is −9.9% vs uniform, not −13%. K5 dense is byte-neutral, and hc handling is unknown.
2. Observed elasticity is 0.30–0.43 (log), confounded by the IQ3_S path.
3. MTP accounting must use the expert union: experts are 50–69% of verify bytes. That raises the value of expert levers and lowers uniform-vs-UD, so Phase S's +8% stop rule is likely to fire.
4. The DS41 MXFP4 repack is a quality upgrade with public evidence (0.0290 → 0.0102 KLD, +2.3 pp top-1 on DS4-Flash).
5. A Q8_0 KLD reference on Q38FN has a ~0.022–0.027 KLD / ~94–95% top-1 floor (unsloth, Swift), so it was never a clean instrument.