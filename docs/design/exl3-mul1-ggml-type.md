# EXL3 `mul1` trellis weights as a ggml tensor type — format spec (X0 draft)

**Status**: DRAFT from source, 2026-09-02 (INF-71 X0). Facts below were read from exllamav3 `499890c75`
(v1.4.6, MIT) — `exllamav3_ext/cpu/moe_mul1.cpp`, `quant/codebook.cuh`, `quant/pack.cu`, `quant/exl3_dq.cuh`,
`modules/quant/exl3_lib/quantize.py::regularize`, `model/moe_cpu_host.py::rehome` — and from the safetensors
headers of `turboderp/Qwen3.8-Flash-Next-exl3` (`4.05bpw_h6_ng6`, `3.05bpw_h5_ng5`). `exllamav3/doc/exl3.md` (the repo's format page) is plots only;
it documents nothing about the layout. Every layout statement here was validated bit-exactly on real tensors
(`/mnt/raid0/llm/tmp/inf70/agents/x1/{verify.log,verify_k3.log,ref_decode*.log}`).

## 1. What the artifact contains

Per quantized linear module, four tensors (75,587 modules in the 4.05 branch, all `codebook: mul1`):

| tensor | shape | dtype | meaning |
|---|---|---|---|
| `<mod>.trellis` | `[k/16, n/16, 16·K]` | int16 | packed 16×16 tiles, K bits/weight, tile `(kt, nt)` at `((kt·tiles_n)+nt)·16K` words |
| `<mod>.suh` | `[k]` | fp16 | **input-side sign × scale**: `su = sign · in_channel_rms / (−codebook_scale) / g_scale` (quantize.py 1212-1226). NOT ±1 — values ≈ ±0.008 (k=2560) / ±0.013 (k=640) |
| `<mod>.svh` | `[n]` | fp16 | **output-side sign × out-channel scale**: `sv = sign · out_channel_rms/mean` when out-scales apply (quantize.py 1195-1207). `out_scales: always` means this is where they live — there is no separate out_scales tensor. Values: experts 0.67–1.59, dense 0.55–2.85, lm_head 0.48–2.14 |
| `<mod>.mul1` | `[]` | int32 | the codebook multiplier itself, `2212286765 = 0x83DCD12D`, identical in all 74,041 modules. Presence = "this module uses cb2/mul1" |

K per module comes from `quantization_config.json` → `tensor_storage[<mod>].bits_per_weight` (and redundantly from
`trellis.shape[2]/16`). **This model has no fractional per-tensor mix: every routed expert is exactly K=4 (4.05
branch) or K=3 (3.05 branch)**; "4.05" is the file-level average (suh/svh/mul1 overhead: 4.031 eff. bpw per
expert). Bit classes, 4.05 branch (3.05 in parentheses):

| class | modules | K | bytes | 
|---|---|---|---|
| routed experts `mlp.experts.N.{gate,up,down}_proj` | 3 × 24,576 (48 layers × 512) | **4** (3) | 60.87 GB (45.77) |
| shared expert `mlp.shared_expert.*` | 144 | 6 (5) | 0.18 GB |
| full-attn `self_attn.{q,k,v,o}_proj` (12 layers) | 48 | 6 (5) | 0.45 GB; `indexer.index_qk_proj` K=4 (3) |
| linear-attn `linear_attn.{in_proj_qkv,in_proj_z,out_proj}` (36 layers) | 108 | 6 (5) | 1.56 GB |
| `lm_head` `[2560 → 248320]` | 1 | **6 = `head_bits`** (5) | 0.477 GB |
| router `mlp.gate` `[512,2560]`, hyper-connection mixers, norms, `in_proj_a/b`, `A_log`, `dt_bias` | — | unquantized fp16/bf16 | 1.4 GB |
| `embed_tokens` `[248320,2560]` | 1 | bf16 | 1.27 GB |
| MTP head `mtp.*` (own 512 experts + dense + `fc_embedding`/`fc_hidden`) | 6,203 tensors | experts **4 = `mtp_bits`** (3), dense 6 (5), fc_* 5 | shard 9; not listed in quantization_config |
| n-gram table `ngram_embedding.safetensors` | 1 (4.05) / 128 shards (3.05) | **6 = `_ng6`** (5 = `_ng5`) | 39.0 GB (32.6): format `exl3_ngram_trellis`, `[320,001,536 rows, 10K+1]` int16, row_dim 160, `codebook_scale: heuristic(gamma=3.00, hi=0.92)`, `head_bias [16,160]`, `head_offsets`, `head_vocab_sizes`, `layer_multipliers` |

Suffix decoding: `<bpw>bpw_h<head_bits>_ng<ngram_bits>` — `_h6` = lm_head at K=6, `_ng6` = the n-gram embedding
table trellis-quantized at K=6 (a *different* row format from the linear layers: no tiles, one row = 160 weights).

## 2. Tile bit layout (validated bit-exact against an independent decoder written from `pack.cu`)

A tile is 16 (k) × 16 (n) weights = 256 codebook **states** of K bits, stored as `16·K` uint16.
Packing (`pack_trellis_kernel<K>`): 16 spans of 16 states; span `t` writes its states MSB-first into K consecutive
uint16 words starting at word `K·t`; then every uint32 has its 16-bit halves swapped. Reading: undo the swap and
the tile is one MSB-first bitstring of 256·K bits, state `i` at bits `[i·K, (i+1)·K)`.
**Decode**: the 16-bit codebook *index* of weight `i` is the 16-bit window ending at bit `(i+1)·K`, **wrapping
around the tile** (tail-biting trellis; `exl3_dq.cuh: b0 = t·bits + bits − 16 + 256·bits`, index mod `words32`).
Consecutive states therefore share 16−K bits — this is what makes the 65,536-entry codebook addressable with K
bits/weight and why decode is *sequential-dependent* only through the bit window, not through arithmetic.

State `i` lands at tile position `perm[i] = (row, col)`, `make_tc_perm()` (tensor-core fragment order):
`t = i/8, j = i%8: row = (t%4)·2 + (j&1) + 8·((j>>1)&1), col = t/4 + 8·(j>>2)`. Row = k within tile (input),
col = n within tile (output).

Codebook `mul1` (cb2): `w(s) = (bytesum(s · 0x83DCD12D mod 2³²) − 510) · k_inv`, `k_inv = fp16(0x1eee) =
0.006767272949 (= 1/147.77)`. Alphabet: bytesum ∈ [0, 1005] → values ∈ [−3.451, 3.350], 913 distinct, mean
−0.0001, std 1.0003 over all 65,536 states; the quantized domain of a real expert has rms ≈ 0.90–0.93.

## 3. What a forward computes (this is the whole inference contract)

For `y = x W` with W `[k, n]` (k = input dim):

1. `x' = x ⊙ suh` (per input channel, fp16 scale incl. sign)
2. `x'' = H₁₂₈(x') · 1/√128` blockwise over consecutive 128-element blocks of k (`hadamard_128`, `HAD_SCALE`)
3. **CPU kernel**: Q8-quantize `x''` per row (`q = amax/127`, symmetric, clamp ±127), keep `Σx8`
4. `acc[n] = Σ_k bytesum(s_kn · M) · x8_k` — exactly one `vpdpbusd` per 16 weights (u8 product bytes × s8 activation
   splat); `y'[n] = k_inv · q · (acc[n] − 510 · Σx8)` — the −510 folds into one correction per output
5. `y'' = H₁₂₈(y') · 1/√128` blockwise over n
6. `y[n] = y''[n] ⊙ svh[n]` (+ bias if present)

So the **Hadamard is on both sides, per 128-block, per GEMV**, and `suh`/`svh` are *dense fp16 vectors*, not sign
bitfields (the packed `su`/`sv` form exists in the loader but the shipped files carry `suh`/`svh`). Because `suh`
differs per (expert, projection) — gate and up of the same expert have different `suh` — **the input transform
cannot be hoisted out of the expert loop**: INF-71 X3's "activation Hadamard applied once per op, not per expert"
is wrong as written; it is once per (expert, projection), O(k) against an O(k·n) GEMV (1/640 of the work). What
*can* be shared is the raw `x`.
Accuracy of the Q8 activation path vs fp32: 0.66–0.97 % output RMS on real expert tensors (verify.log), matching
the kernel's own "~0.9 %" statement.

## 4. What a GGUF tensor of the new type must carry

Proposed `GGML_TYPE_EXL3_MUL1_K4` / `_K3` (one type per K; K=6 later for X5), `blck_size = 256` is **not** the
natural unit — the natural unit is a 16×16 tile spanning 16 rows of the ggml `ne[0]` axis, so this cannot be a
row-block type like IQ4_XS. Two options:

- **(A) Opaque per-matrix blob** (recommended for X2/X3): `ne = [k, n, n_expert]`, `type_size` defined so that
  `nbytes = n_expert · (16K·tiles_k·tiles_n·2 + 2k + 2n)`; the row stride is meaningless, `ggml_row_size` is only
  used for allocation. Layout per expert slab: `[trellis: tiles_k × tiles_n × 16K u16, swizzled (§5)] [suh: k fp16]
  [svh: n fp16]`. Requires `mul_mat_id`/`mul_mat` to special-case the type (they already special-case repacked
  types), and `ggml_get_rows`/`ggml_cpy` need not support it (decode-only type).
- **(B) Split tensors**: keep `suh`/`svh` as separate F16 tensors (`ffn_up_exps_suh` `[k, n_expert]`,
  `ffn_up_exps_svh` `[n, n_expert]`) and make only the trellis the new type. Cleaner ggml-wise but needs a new
  graph node that consumes three tensors; more llama.cpp plumbing.

Constraints inherited from the kernel: `k % 128 == 0`, `n % 128 == 0` (Hadamard blocks; 2560 and 640 both OK),
`k ≤ 8192` (i32 accumulator), K ∈ [1, 8]. Per-op requirements: `from_float` = the suh-multiply + H₁₂₈ + Q8 prep
(per expert, so it is *not* ggml's usual "quantize the activation once" — the Q8 buffer is per (expert, proj)),
and an epilogue op (H₁₂₈ + svh) after the GEMV, before the SiLU·up product. Prefill (m > 4): exllamav3 has no CPU
path; the KT-style dequant-then-GEMM fallback is needed or pp regresses.

## 5. Layout the CPU kernel wants: band-contiguous ("swizzled")

`moe_cpu_host.py::rehome(band_swizzle=True)`: tile `(kt, nt)` stored at `((nt/8)·tiles_k·8 + kt·8 + nt%8)·16K`
words — i.e. group of 8 output tiles outermost, then k, then member — so a worker's 8-tile output band reads
the whole k-stream sequentially (exllamav3 measured 3.4× over the native layout on cold DRAM). Requires `tiles_n
% 8 == 0` (40 and 160 OK). The importer should write this order; the kernel then splits work in whole 8-tile
groups (5 per gate/up matrix, 20 per down matrix — this granularity caps threads-per-matrix, see REPORT.md).

## 6. Bytes per token (routed experts, 10 of 512, 48 layers)

| format | per expert (gate+up+down) | per token, all layers |
|---|---|---|
| IQ4_XS uniform artifact (up/gate IQ4_XS 4.25 bpw, down Q5_1 6 bpw) | 2,969,600 B | **1.296 GB** (GGUF header, 10/512 of 66.37 GB) |
| EXL3 K=4 (+ suh/svh 19,200 B) | 2,457,600 (+19,200) B | **1.180 GB** (1.189 with suh/svh) → −9 % |
| EXL3 K=3 (+ suh/svh) | 1,843,200 (+19,200) B | **0.885 GB** (0.894) → −32 % |

## 6b. Measured decode cost of the reference kernel on this box (REPORT.md section 4, non-claims)

Zen 5, VBMI tier, swizzled layout, real layer-3 experts: per core the fused decode+dot runs 34.7 Gw/s at K=4
(17.3 GB/s of trellis) and 25 Gw/s at K=3 (9.4 GB/s) -- compute-bound; decode-only 53.5 / 42.4 Gw/s. At 48 threads on
10 random experts: 110 GB/s (full 5-phase forward) / 124 GB/s (GEMV phases) at K=4, 91 / 105 at K=3 -- memory-bound.
Any ggml port inherits: (i) the K=3 kernel needs ~1.4x the cores of K=4 to saturate DRAM; (ii) the three non-GEMV
phases cost ~8 us each at 48T regardless of work; (iii) the 8-tile group granularity leaves a single gate/up matrix
using at most 5 threads.

## 7. K range to support first

K=4 and K=3 cover every routed expert in both branches (no mixing inside a layer or across layers). K=6 is needed
only for X5 (dense + lm_head + shared expert). K=5 only for the 3.05 branch's dense/head.
