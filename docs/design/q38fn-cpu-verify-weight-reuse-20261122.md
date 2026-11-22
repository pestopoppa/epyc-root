# Q38FN CPU speculative verify: does a weight load serve all verify rows? (2026-11-22)

**Question.** On the EPYC 9655 CPU (Zen 5, AVX-512 VNNI, NPS4, one 24-core quarter), does the
Qwen3.8-Flash-Next (Q38FN, arch `qwen4exp`) verify forward at M = 2..8 reuse each weight load
across rows, and what would a V5I-style "read each weight once for all rows" kernel buy?

**Answer.** It already reuses. Dense matmuls run the iqk multi-row kernels (nrc_y = 1..8). MoE
experts are grouped per expert, so an expert that several rows share is read once. The measured
marginal cost of about 12 ms per extra row matches the byte cost of the **distinct routed experts**
a new row brings in, at 85-100% of the quarter's bandwidth roofline. A weight-once kernel has
nothing left to remove. **No box.**

Method: code reading at the C16 store's source commit `13d6fc150` (the build the r3 probe used,
`cpu-20261118-13d6fc150-c16`), a GGUF header parse, and the existing smallm-verify r3 data. No new
compute was used. The microbenchmark was skipped because the code and the byte arithmetic already
answer the question.

## 1. Served weights (UD-IQ4_XS, 87.2 GiB in 3 shards)

48 layers, d = 2560, 512 experts with 10 used per token, expert FFN width 640, one shared expert.

| Tensor class | Quant | Bytes read per token |
|---|---|---|
| routed experts: gate/up | IQ3_S (47 layers), IQ4_XS (1 layer) | 10 experts x 48 layers x ~2.33 MB, **~1.12 GB** |
| routed experts: down | IQ4_NL (43 layers), Q8_0 (5 layers) | (included in the row above) |
| attn_qkv/q/gate/output, ssm_out, hc_*, shexp | Q8_0 | ~3.9 GB |
| ffn_gate_inp (router) | F32 | 0.25 GB |
| output | Q6_K | 0.52 GB |
| token_embd / per_layer_token_embd | Q8_0 / IQ4_NL | row lookups only |

M = 1 reads about **5.7 GB per token**. Every extra verify row adds its distinct experts, at most
**about 1.12 GB**.

## 2. Reuse status (file:line at `13d6fc150`)

- **Dense paths, reused.** `ggml/src/ggml-cpu/iqk/iqk_common.h:152` sets `IQK_MAX_NY 8`.
  `iqk_gemm_iquants.cpp:2726-2735` (`set_functions`, used for IQ3_S at `:2815`) instantiates
  `mul_mat_qX_K_q8_K_IQ<Deq, 1..8>`. `iqk_gemm_legacy_quants.cpp:2170-2182` does the same for Q8_0
  and IQ4_NL. `iqk_mul_mat.cpp:82-156` (`mul_mat_NxM`) tiles nrc_y rows per weight pass, so
  M = 2..8 makes one pass over each weight row (`func16` is used only when M >= 16).
- **MoE, reused per shared expert.** `ggml-cpu.c:1877` sends MUL_MAT_ID to
  `ggml_iqk_try_mul_mat_id`. `iqk_dispatch.cpp:525-576,700-710` builds `matrix_row_counts[n_as]`,
  and `:656` calls `iqk_mul_mat_moe` once per expert with all of that expert's rows. A routed expert
  shared by k rows is therefore read once with nrc_y = k. Distinct experts cannot be shared.
- This matches the A3B CPU census: the MUL_MAT_ID per-row cost is flat at 15-18 us, so each new
  row pays for new experts.

## 3. Roofline vs measurement (r3, D1K, 24 threads, one quarter)

Measured mean ms per forward: M=1 94.0, M=2 108.7, M=3 118.2, M=4 128.7, M=8 178.4. The marginal
cost is 10-14.7 ms per row, with a 1-to-8 slope of 12.1 ms per row.

Assumed quarter bandwidth: about 110 GB/s sustained, out of 3 DDR5-6000 channels at 144 GB/s peak.

| | Bytes | Byte floor | Measured | Efficiency |
|---|---|---|---|---|
| M=1 forward | ~5.7 GB | ~52 ms | 94 ms | ~55% |
| marginal row (all experts distinct) | ~1.12 GB | ~10.2 ms | ~12 ms | ~85% |
| marginal row, compute only | ~7e9 int8 MAC | ~0.6 ms at ~11 TMAC/s VNNI | n/a | n/a |

The extra row is bound by routed-expert bytes, not by compute or by re-reading weights. Expert
overlap between draft rows is small: 10 of 512 under random routing, and probably somewhat higher
for correlated draft tokens. That overlap is already captured.

Gap to roofline:
- **Marginal row:** at most about 1.5-2 ms per row, or 3-5 ms per round at M=3.
- **Fixed M=1 cost:** about 40 ms. This is the real headroom. It is attention/SSM, the fixed
  per-node cost, and the Q8_0 dense GEMV running at about 55% of bandwidth.

The ceiling quoted from r3 (a 14% round saving if r(3) fell to 1.05) assumes the extra-row cost
can be removed. It cannot: r(3) is bounded below by about 1 + 2 x 1.12/5.7 ≈ 1.2 at full
bandwidth.

## 4. Ranked fixes (estimated Q38FN CPU round gain at D1K, round ≈ 107 ms at 48 threads)

1. **M=1 dense GEMV bandwidth efficiency (55% → 75-80%).** About 3.9 GB of Q8_0 dense weights
   per token. Candidates: an NTA/prefetch sweep (the default-off NTA build `f35c4a1af` already
   exists), fewer per-node barriers, and the CPU fusion work. Ceiling about 15-20 ms per forward,
   **~10-18% of a round**. This is the existing C-series decode work, so it needs no new box.
2. **Expert-byte diet.** Requantizing the 5 Q8_0 `ffn_down_exps` layers to IQ4_NL saves about
   0.04 GB per row; moving all down projections to IQ3_S saves about 0.25 GB per row. That is
   about 1-3 ms per row, **~1-5% of a round**, and needs the Q38FN 27B-anchored KLD gate. The
   gain is small.
3. **Marginal-row kernel tuning (85% → 95%).** About 1 ms per row, **≤2%**.
4. **V5I-style weight-once verify kernel. ~0%.** The reuse is already in place (section 2).
   **Do not build it.**

## 5. Recommendation

No box. Close the Q38FN-CPU-SMALLM-VERIFY lever as "reuse present; marginal row is
routed-expert bytes". Any CPU round gain belongs to fix 1, the M=1 fixed-cost bandwidth work that
is already in the C-series.
