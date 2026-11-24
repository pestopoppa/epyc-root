# Dive — kv4repo — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://github.com/thomaszhang2661/kv4-hopper", retrieved: "2026-11-24", sha256: "b7275c85cf97"}
> Reading material (not anchors): shallow clone at `/mnt/raid0/llm/tmp/dive-ak-1124/kv4repo/repo/`, HEAD `f708dd12f9ec4a1075d66a5eb23c750b26e3db5b`. Stage 2b wave 1, light dive; bearing entry fp4kv = intake-2870 (paper arXiv 2611.30027, already in the index; this repo URL is not).

## 1. Stage-1 fields
- Title: kv4-hopper — "Fast 4-bit KV-cache decoding on Hopper GPUs, and a vLLM plugin". Author: Jian Zhang (per the repo's citation block). State: public, 8 commits, 1 star, 0 forks, Apache-2.0 (`page.txt`).
- Categories: kv_cache, quantization, hardware_optimization, inference_serving.
- Novelty: medium. It is the reference implementation of an entry already ingested (intake-2870); the new content is code-level (exact permutations, instruction sequence, mean-removal calibration) that the paper text only sketches.
- Relevance: high for D2 (fragment map) and D6 (mean-removal recipe), medium-low as code to reuse (sm_90a wgmma/TMA/mbarrier; head dim 128 only).
- credibility_score: 1 = peer-reviewed 0; <=12 months +1; major lab/known contributor 0; commercial bias 0; independent corroboration 0 (single author, 1 star; CI compiles the CUDA but runs no GPU test). Tests exist (`tests/test_formats.py` CPU; `tests/test_kernels.py` GPU).
- Verdict: adopt_patterns. Use it as a model-free oracle and recipe template. The kernels themselves are not portable (TMA producer warp, wgmma m64n8k16, mbarrier).

## 2. Key claims
1. **Settled: write-time cache layout.** CONFIRMED from code. Pages are 64 tokens. For INT4 (`kv4/cuda/decode_int4.py`, `kside.py`): K row = 64 B (128 nibbles) permuted per token into 16 int32 words so thread t (of 4) owns 4 contiguous words, and each word packs 8 nibbles at bit offsets (0,16,4,20,8,24,12,28) = dims 32i+2t, +1, +8, +9, +16, +17, +24, +25 (`kside.py::_perm`). V is permuted per 256-token block, 4096 words ordered [wg 2][kh 2][mt 2][warp 4][lane 32][kk 4], so one word is one lane's PV-fragment pieces (`decode_int4.py::_v_perm`). K scale is ONE fp16 per token row (token-wise, block 0), plus a zero point for asymmetric. NVFP4/MXFP4 pages are 8704 B (MXFP4) or 9216 B (NVFP4) per (page, kv head): K codes 4096 | K scales | V codes 4096 | V scales (`store_fp4.cu` header).
2. **Settled: decode instruction sequence.** CONFIRMED. 8 values cost 1 shift + 4 LOP3 (0.625 instr/value): `(w & 0x000F000F) | 0x64006400` gives f16 1024+c (nibbles 0-3/16-19), `(w & 0x00F000F0) | 0x64006400` gives 1024+16c (nibbles 4-7/20-23), and `w>>8` repeats for the other 16 dims (`kside.cu` header; `common.cuh:L98-L105`, `lop3 ... 0xEA`). The 16x factor is folded into q (q'_d = q_d/16 for d%16>=8) and the 1024 offsets into one constant per head, K0 (`kside.py::prep_q`). V is centred with one HADD2 per register before the MMA ("CENTER"), and P is scaled by 2^10 (`decode_int4.cu:L1-L60`).
3. **License.** CONFIRMED Apache-2.0 (LICENSE + `NOTICE`; vendored `baselines/pr53060/` also Apache-2.0). Copying with attribution is permitted; no license obstacle.
4. **Mean-removal / rotation reference.** CONFIRMED present, with limits. `kv4/formats.py` has `rotate` (block-diagonal Sylvester Hadamard, orthonormal), symmetric INT4 g32 (`int4_g32`, codes -7..7 stored as q+8, fp16 scale) and row-wise INT4 +/- rotation. `bench/calib_kv.py` computes the static per-layer, per-kv-head post-RoPE K mean over positions >= 4 (8 prompts x 2048 tokens, wikitext-2). `bench/accuracy_kl.py` has the `~s`/`~p` mean-removal variants and the KL harness. `store_fp4.cu` applies the mean at write time. Limit: the repo's recipe is NVFP4/MXFP4 on Hopper at head dim 128; no q4_0, no head dim 256, no hybrid layers.
5. **Scope limits.** CONFIRMED by the README: "Not supported: MLA models, head dimension 64 or 256, sliding-window layers, speculative decoding."
6. **README ambiguity (not a claim, recorded).** The README feature list says the recipe includes "layer 0 in BF16", but every command that produces the reported accuracy numbers sets `KV4_BOUNDARY=0` (`README.md:L57`, `slurm/vllm_serve.sbatch:L67`). `KV4_BOUNDARY` selects which layers stay native (`integrations/vllm_plugin/kv4_vllm/__init__.py:L7`). Whether layer 0 was BF16 in those numbers is NOT settled by the repo text. Do not use the repo as evidence for the layer-0 claim (bears D7).

## 3. Reported results
None in the page text as numbers; the README points to `repro/README.md` and `results/` for the paper's tables. Not read; the paper numbers belong to intake-2870. Hardware: H200 SXM/NVL, H100 SXM; vLLM 0.33.0.

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 |
|---|---|---|
| Write-time permutation to the matrix-unit A-fragment (K 16 B/thread, V per 256-token block) | **PARTIAL.** The repo's K permutation exists because wgmma's A layout interleaves cols 2t, 2t+1, 2t+8, 2t+9. The gfx90a MFMA 16x16x16 A operand wants 4 contiguous k per lane (`fattn-gqa-verify.cu:L16-L20 @ 98ff8a4`), which stock q4_0 already has (fp4kv D2). So the K permutation is unnecessary; the V token-pair interleave is the transferable part (V^T gather). Method transfers: derive the lane map in numpy, assert it covers each (token, dim) once (`_v_perm` asserts this). | NO (no matrix unit in decode path). |
| LOP3 magic-number decode, 0.625 instr/value, scale folded into q, offsets into one per-head constant | **YES.** `v_and_or_b32` / packed f16 add are the same integer+f16 ALU work (ISA names uncited). The 1024+16c trick needs the 16x folded into q, which is free at fragment build. | PARTIAL: standard in iqk. |
| Per-token-row scale (one fp16 per 128 dims) | **NO for q4_0.** q4_0 has a scale per 32 dims; the repo shows no mid-row scale application. Group-local scale handling for g=32 is not demonstrated here (see foscar key). | n/a |
| Static K mean + Hadamard at write time, no decode-side correction needed | **YES (offline first).** q.mu is constant over keys for a given query, so it cancels in softmax (same statement fp4kv D6 uses). Apply as a write-time subtraction. | YES (CPU KV write is scalar/AVX code). |
| TMA producer + 2 consumer warpgroups | NO as written (no TMA/mbarrier, uncited); the key-partition idea is in fp4kv Q2. | NO |

## 5. In-house state
Same as fp4kv section 5: gv_fattn has no q4_0 path (`ggml/src/ggml-cuda/fattn-gqa-verify.cu:L680 @ 98ff8a4` rejects K/V other than f16/q8_0). K rotation is whole-head by construction: `build_input_k_rot` picks the largest power-of-two divisor of the head dim (256 gives H256), and V uses H64 (`src/llama-kv-cache.cpp:L1496-L1535 @ 98ff8a4`). No K mean removal, no per-layer type.

## 6. Derived-actionables ledger
| # | Draft task line | Owner | Kind | Stop / decision rule |
|---|---|---|---|---|
| K1 | **Refines fp4kv D2.** Build the model-free fragment oracle for D2 by porting the structure of `kside.py::_perm` and `decode_int4.py::_v_perm` (numpy lane-map plus coverage assert) to the MFMA 16x16x16 lane map and to q4_0 blocks (K: bytes 4kq..4kq+3; V: token-contiguous gather). | `autokernel-loop.md` (D1 step 0) | code/doc-only | Question: does the lane map reproduce `dequantize_row_q4_0` bit-exactly for K and V fragments over random blocks? Done when yes. Not a compute row. |
| K2 | **Refines fp4kv D6.** Use `calib_kv.py` (mean over positions >= 4, post-RoPE, per layer and kv head) and `accuracy_kl.py` `~s` as the template for D6's K dump analysis; add arms "first 4 tokens exact" and "static mean" to the q4_0 g32 simulation. Use symmetric INT4 g32 with q4_0's range (-8..7); the repo's `int4_g32` uses -7..7, so change `INT4_MAX` handling. | `quantization-and-low-bit.md` | doc/code-only (offline Python) | Same rule as D6 (mean energy > 30% of K or simulated KL cut >= 20%). Stop when D6 answers. |
| K3 | Vendor or port the CUDA kernels. | DECLINE | - | Reason specific to the entry: every kernel is sm_90a (TMA, wgmma, mbarrier) at head dim 128; none maps to MFMA at head dim 256. License is not the reason (Apache-2.0 permits it). |

## 7. Dive-surfaced sources
| Source | In index? | Bears on | Recommendation |
|---|---|---|---|
| github.com/thomaszhang2661/kv4-hopper (this entry) | 0 hits before | D2, D6 | this entry |
| vLLM PR #53060 (vendored in `baselines/pr53060/`) | not checked as own entry | baseline kernel for the paper | decline: no ledger row depends on it |
No other source would change a ledger row.

## 8. Contradiction / adversarial pass
- Single author, 1 star, no independent run of the code; the README describes tests, not their results.
- The mean-removal and layer-0 claims are not settled by the repo (item 6 above). The repo covers head dim 128 only, so nothing in it is evidence for Qwen3.5-family D=256 layers.
- Row-wise scale granularity (one scale per 128 dims) is a different quantizer from q4_0 g32; KL numbers from it do not transfer.

## 9. read_depth
PARTIAL. Read: `page.txt`, `kv4/formats.py` (lines 1-200), `kv4/cuda/kside.py`, `kside.cu` header, `decode_int4.py`, `decode_int4.cu` header (lines 1-80), `common.cuh` lop helpers, `store_fp4.cu` (lines 1-200), `bench/calib_kv.py`, grep of `accuracy_kl.py`. Not read: decode_fp4*.cu bodies, merge.cu, plugin, results/, paper/. `lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9`.

## 10. Artifact audit
artifact audit: clean (anchors checked with count >= 1; clone is outside any git repo of ours).
