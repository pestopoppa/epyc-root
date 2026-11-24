# Dive — flagrot — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.03992v1", retrieved: "2026-11-24", sha256: "e67a81a48421"}

## 1. Stage-1 fields
- Title: FlagRot: Selective Rotation for Low-Bit KV Caches. Authors: Kunming Shao, Xijie Huang, Jierun Chen, Jiaqi Shao, Yanli Wang, Jiangnan Yu, Qiwei Li, Wei Zhang, Kwang-Ting Cheng, Chi Ying Tsui (HKUST and others). v1, 2026-11-02, cs.CL. Code: github.com/KunmingSHAO/FlagRot_releaser (not fetched).
- Categories: kv_cache, quantization.
- Novelty: medium-high. Per-32-channel choice between identity and Hadamard, selected by a calibrated attention-error criterion, flag stored in scale sign bits.
- Relevance: high for D5 (rotation on/off arm and stop rule). The paper's model set includes **Qwen3.8-27B** (hybrid, 16 of 64 layers hold KV, 4 KV heads, head dim 256), the production 27B family (anchor 6).
- credibility_score: 2 = preprint 0; <=12 months +1; major lab 0; commercial bias 0; independent corroboration +1 (the rotation-harms-NVFP4 direction on Qwen3-8B is also reported by fp4kv/intake-2870, different authors, different number: restatement of direction only, not of figure; and intake-499 records that llama.cpp's PR #21038 rotation improves q4_0 KV perplexity, as stated in that entry, not re-verified here).
- Verdict: worth_investigating (D5 decides whether selective rotation is ever needed).

## 2. Key claims
1. **Whole-head rotation harms Qwen3 under NVFP4 (E2M1), not under INT4.** CONFIRMED and sharpened. Whole-head Hadamard raised NVFP4 KL on Qwen3-8B by +215% (MXFP4 +41%) while helping Llama-3.1-8B (anchor 1). On INT4 g32 (asymmetric, zero point stored, 4.5 bits/element) whole-head rotation lowers KL on every Qwen3 model in Table 25: Qwen3-8B -28.4%, Qwen3-14B -46.3%, Qwen3-32B -43.1%, Qwen3-30B-A3B -30.4%, **Qwen3.8-27B -8.0%** (KL 6.7e-3 to 6.2e-3, no BF16 protected tokens) (anchors 2, 3). The mechanism: with exact FP32 scales the NVFP4 increase persists (+264%) and a uniform 4-bit grid of the same range turns it into a reduction (-27%), so the harm is E2M1's grid, not rotation or scales (anchor 4).
2. **Prediction for llama.cpp's automatic rotation on q4_0.** PARTIAL (inference). q4_0 is a uniform symmetric INT4 g32 grid, the same grid family as the paper's INT4, so the paper predicts rotation helps (or is neutral on 27B) rather than hurts. Caveats: (a) the paper's INT4 is asymmetric with a zero point, q4_0 is symmetric (no zero point); (b) llama.cpp rotates K with the largest power-of-two block dividing the head dim (H256 whole-head on D 256) and V with H64 (`src/llama-kv-cache.cpp:L1496-L1535 @ 98ff8a4`); (c) the paper's "Head" baseline does not state whether V is rotated (FlagRot itself leaves V unrotated: anchor 5); (d) fp4kv's "10x KL" for rotation without mean removal was NVFP4 on Qwen3-8B-Base and does not carry to q4_0.
3. **Where the benefit sits.** CONFIRMED: selecting on keys alone recovers 93-94% of the KL reduction of selecting on keys and values; values alone give 4-5% (anchor 7). Rotation matters on K; V rotation is nearly inert.
4. **Selective rotation gains over whole-head on INT4.** CONFIRMED: Qwen3.8-27B INT4 KL: RTN 6.7, whole-head 6.2, calibrated base 5.2, FlagRot 5.8, FlagRot-L 4.4 (x1e-3) (anchor 3). Geo-mean over 12 models: whole-head 11.05 vs FlagRot 7.88 vs RTN 16.72 (Table 30). The 27B has the lowest baseline error of the Qwen3 family in the table, so its absolute headroom is small.
5. **Limits.** The studied models are mostly D = 128; one D = 256 model (the hybrid 27B). KL is measured with prefill-style windows on H200 (wikitext-2 validation), without protected BF16 tokens in these tables; no llama.cpp, no GGUF, no q4_0.

## 3. Reported results
INT4 g32 KL x1e-3, no BF16 tokens (Table 25): Qwen3-8B RTN 43.5, whole-head 31.2; Qwen3-14B RTN 25.1, whole-head 13.5; Qwen3.8-27B RTN 6.7, whole-head 6.2, FlagRot-L 4.4. NVFP4: Qwen3-8B RTN 38.4, whole-head +214.9% (relative); Qwen3.8-27B RTN 8.3, whole-head -3.4% (relative). Headline: at 2.5 bits FlagRot lowers twelve-model KIVI KL from 18.7 to 12.4 x1e-3; +2.9 RULER at 128k; at 4 bits it lowers INT4/MXFP4/NVFP4 KL by 13-89% relative to RTN. Hardware: H200 for serving rows (Qwen3.8-27B decode 8192 context, INT4 per-token cache takes 5.3% more time per output token than BF16 at batch 64).

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 |
|---|---|---|
| Whole-head Hadamard on K (and V), query rotated instead of keys rotated back | **YES, already done in-house:** llama.cpp rotates activations before the cache write and the query before the dot product; cost is one 256x256 (K) / 64x64 (V) matmul per token per layer, not on the KV read path. | YES (same graph ops). |
| Per-32-channel selective rotation with a 1-bit flag in the scale sign bit | **PARTIAL.** Query must be rotated into 2 bases per step and per-group flags select partial dot products: extra MFMA/VALU in the gv inner loop, plus calibration data. q4_0's scale is f16 with sign bit unused (uncited layout detail: `block_q4_0` d is `ggml_half`), so the flag would fit in-place. Only worth it if D5 shows q4_0 rot-on KLD is too high. | PARTIAL: per-block branch in the vec_dot; bandwidth-bound anyway. |
| Calibrated attention-error criterion (C_q = E[qq^T]) | **YES (offline).** A Python simulation on dumped K, Q fits D6's dump. | YES |
| Static key centering (for Qwen2.5 biased keys) | Not needed: our served configs have `attention_bias: False` (fp4kv section 5). | n/a |

## 5. In-house state
`LLAMA_ATTN_ROT_DISABLE` (single env var, disables K and V rotation together) and the `n_embd_head % 64 == 0` + quantized-type gate: `src/llama-kv-cache.cpp:L317-L340 @ 98ff8a4`. K rotation size: `build_input_k_rot` loop (`:L1496-L1516`); V rotation fixed at 64 (`:L1521-L1535`, with comments citing upstream PR #21038 discussion). There is no separate K-only or V-only switch. Production serves q8_0 KV (rotation active, since q8_0 is quantized); q4_0 KV is unmeasured (fp4kv section 5).

## 6. Derived-actionables ledger
| # | Draft task line | Owner | Kind | Stop / decision rule |
|---|---|---|---|---|
| R1 | **Refines fp4kv D5.** Keep D5's rot-on vs `LLAMA_ATTN_ROT_DISABLE=1` arm but state the prior: the paper predicts rot-on <= rot-off for uniform INT4 on Qwen3 (27B: -8%, others -28 to -46%). Run it as a falsification check on 27B first (one context, one arm pair), CPU or GPU. | `quantization-and-low-bit.md` | GPU or CPU row (no code) | Question: does auto-rotation hurt q4_0 on 27B? If rot-off KLD >= rot-on KLD (as predicted), stop: the D6 "rotation off" branch is dead and no grid is run. If rot-off < 0.9x rot-on, the paper is contradicted for symmetric q4_0 or D=256: run the other models and file D6. Replace D5's blanket 0.9x rule only for the order of runs; keep the 0.9x threshold. |
| R2 | Split `LLAMA_ATTN_ROT_DISABLE` into K-only and V-only switches (env, default off) in the experimental tree so D5 can separate the two. | `autokernel-loop.md` or `quantization-and-low-bit.md` (the owner of the D5 row) | code (small, experimental branch only) | Gate: do it only if R1's 27B arm shows an effect of either sign > 10% KLD; paper says V rotation is worth 4-5% of the K+V gain, so a K-only arm is the informative one. Otherwise skip. |
| R3 | If D5 shows q4_0 rot-on KLD > 2x q8_0 on 27B, simulate FlagRot's keys-only selection offline (Python, on D6's K/Q dumps) before any kernel work. | `quantization-and-low-bit.md` | code/doc-only (offline) | Question: does keys-only selection cut q4_0 KL >= 30% on the 27B dumps (paper: -56% on four dev models, 0.02 bits/element; 27B headroom is smaller)? KEEP the idea only if yes; otherwise drop. Conditional on D5. |

## 7. Dive-surfaced sources
| Source | In index? | Bears on | Recommendation |
|---|---|---|---|
| github.com/KunmingSHAO/FlagRot_releaser | 0 hits | a KL harness and selection code for R3 | decline: R3 is conditional and is offline Python; revisit only if R3 triggers |
| llama.cpp PR #21038 (the in-house rotation) | recorded in intake-499 notes and handoff mentions, no own entry | D5 prior for q4_0 | decline: already referenced; the code is read directly at `src/llama-kv-cache.cpp` |
No other source would change a ledger row.

## 8. Contradiction / adversarial pass
- Authors' own limits: results are KL on wikitext windows and task accuracy on a handful of models; "five runs do not establish formal equivalence" language appears for serving. NVFP4 sign flip is attributed to the E2M1 grid on QK-norm models; Table 36 shows crest/kurtosis statistics do not separate harmed from helped models (so no cheap predictor).
- The reported "Head" (QuaRot-style) rotation is a baseline the authors beat in 40 of 45 model-format pairs; it is a baseline, so its INT4 gains are a lower bound on rotation's value, not an upper one.
- Not tested: symmetric q4_0, head dim 256 beyond the one hybrid model, any llama.cpp numerics, rotation of V at H64 specifically.
- Restatement note: fp4kv's rotation-harm figure (10x, Qwen3-8B-Base, NVFP4) and this paper's +215% (Qwen3-8B, NVFP4) agree on direction, not on size; both are E2M1.

## 9. read_depth
PARTIAL. Read: abstract, introduction, section 2 (partial), Table 6, Tables 25/26/30/35/36/38, Appendix C.1-C.2, E.1-E.2, model table (Table 10), hybrid-serving notes. Not read: sections 3-5 derivations in full, Appendices A, B, D, most task tables. `lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9`.

## 10. Artifact audit
artifact audit: clean (symmetric-vs-asymmetric and V-rotation caveats stated; "Head" column K/V scope flagged as unstated).
