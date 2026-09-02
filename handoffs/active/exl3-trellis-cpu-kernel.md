# EXL3 trellis weights on the CPU kernel — Qwen3.8-Flash-Next

**Status**: NEW — filed 2026-09-02 from the INF-70 audit at the operator's request ("EXL3 weights are all
the rage; if they exist for this model, explore using them and building the supporting feature into the
experimental CPU kernel"). Feasibility established from source; no code written yet.
**Created**: 2026-09-02
**Priority**: MED — a bytes-per-token lever for INF-70 Axis B with a working reference kernel, but a
multi-session port; sequenced after INF-70's C0/C5/B1/D0 measurements rank the levers
**Categories**: hardware_optimization, local_inference, moe_optimization, kernel_architecture, quantization
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-71)
**Related**: [`cpu-decode-roofline-program.md`](cpu-decode-roofline-program.md) (INF-70 — this is its lever
B7), [`iqk-iquant-enablement.md`](iqk-iquant-enablement.md) (the IQK dequant path this would sit beside),
[`tq3-quantization-evaluation.md`](tq3-quantization-evaluation.md) (the quant-ladder evaluation discipline)

## What exists (verified 2026-09-02, URLs in the audit record)

- **Weights**: `turboderp/Qwen3.8-Flash-Next-exl3` (created 2026-08-31, updated 2026-09-01), five branches:
  `2.05bpw_h4_ng4` 62.8 GB · `3.05bpw_h5_ng5` 85.1 GB · `4.05bpw_h6_ng6` 107.5 GB · `5.05bpw_h6_ng6`
  123.3 GB · `6.05bpw_h6_ng6` 139.0 GB. The 4.05 branch's `quantization_config`: `quant_method: exl3`,
  `version 1.4.4`, `bits 4.05`, `head_bits 6`, `out_scales: always`, **`codebook: "mul1"`**, **`mtp_bits: 4`
  — the MTP head is quantized and shipped.** Tensor inventory: `trellis` / `suh` / `svh` / `mul1` ×75,587
  each, plus `A_log` / `dt_bias` (the Gated-DeltaNet params). Quality evidence in the repo is plots only
  (KLD, PPL); no numeric table, so any quality claim has to be measured here.
- **Format** (`exllamav3/doc/exl3.md`): a streamlined QTIP — procedural codebook, tail-biting trellis,
  blockwise Hadamard incoherence processing (`suh`/`svh` are the sign vectors), Viterbi search over
  16-element vectors in **16×16 tiles**, fractional mixed bitrates per layer. **Decode is arithmetic, not a
  lookup**: the `mul1` (cb2) codebook is `w(s) = (bytesum(s · 0x83DCD12D) − 510) · k_inv`.
- **A CPU kernel already ships**: `exllamav3/exllamav3_ext/cpu/moe_mul1.cpp` (~2,150 lines) with
  `avx512_target.cpp` / `avx2_target.cpp` — a threaded AVX-512/VNNI GEMV for `mul1` MoE expert tensors.
  Because the codebook is affine in a byte-sum, dequant and the activation product fuse:
  `Σ_k w_kn x_k = k_inv·q·( Σ_k bytesum(s_kn·M)·x8_k − 510·Σ_k x8_k )`, so "`bytesum(s·M)·x8` is exactly one
  `vpdpbusd` per 16 weights". Roughly four vector uops per 16 weights: bit-field extraction of the trellis
  states (`vpermt2var` + funnel shifts), one 32-bit multiply, one `vpdpbusd`. Limits: `mul1` only, K ∈ [1, 8]
  bits, `MAX_M = 4` (GEMV, not prefill), MoE experts only (gate/up/down); attention and dense projections
  have no CPU path; band-contiguous "swizzled" k-major layout (3.4× over per-column on cold DRAM).
- **Architecture support**: exllamav3 v1.4.5 (2026-08-31) "Support Qwen4ExpForConditionalGeneration
  (Qwen3.8-Flash-Next)"; a `gdn.cu` Gated-DeltaNet kernel exists. **ROCm is unsupported** (to-do in the
  README; cu128 wheels only) — irrelevant here, the MI210 is out of scope.
- **Prior art in ggml-land**: none. `ggml-org/llama.cpp` has zero issues or PRs for "trellis", "QTIP",
  "exl3" (discussion #10125 from 2024-11 never became a PR). `ik_llama.cpp` has trellis quants
  (IQ2_KT / IQ3_KT / IQ4_KT, PR #113) that are **very slow on CPU** (PR #441: ~4.8 t/s vs ~4.6 t/s F16;
  PR #482: "TG performance … still very low") — **but they use QTIP's 3INST decode, which emits an fp32
  per weight and forces an fp32 GEMM.** That verdict does not transfer to `mul1`, whose decode folds into
  the integer dot product. Anyone citing the KT numbers against EXL3-on-CPU is generalising from a
  different decode.

## Why it is a lever, and how big (inference — measure before believing)

INF-70's ledger puts the routed-expert stream at ~1.30 GB/token at IQ4_XS/Q5_1 (4.25–5.5 bpw) out of
~4.16 GB. At 3.05 bpw the same experts are ~0.9 GB (−0.4 GB/token, ~10% of the stream); at 4.05 bpw the
bytes are a wash but the quality-per-bit is claimed higher (unverified). On the compute side: 400 G
weights/s ≈ 25 G 16-weight groups/s ≈ 100 G vector uops/s against ~670 G uops/s of 512-bit VNNI issue
across 96 Zen 5 cores — ~15% of vector issue, so decode stays off the critical path and the run stays
bandwidth-bound. The gap is scope and plumbing, not feasibility: a new ggml tensor type, the Hadamard
rotation of the activation per tile, quantized (Q8) activations for `vpdpbusd`, the swizzled layout, and a
converter/importer from the exl3 safetensors into GGUF for the expert tensors only (dense stays IQ4_XS).

## Plan — phases with gates

- [x] **X-DL — weights on disk.** ✅ 2026-09-02 16:51Z — both branches complete, every LFS file `SHA-OK` against the repo oids (26 files; `download.log`), 101 GB + 80 GB under `models/turboderp/Qwen3.8-Flash-Next-exl3/`. Started 2026-09-02 11:50Z at the operator's direction
      (`/mnt/raid0/llm/tmp/inf70/download_exl3.sh`, one file at a time, resume-safe, sha256 against the LFS
      oids): `4.05bpw_h6_ng6` (100.1 GiB — 9 shards + 36.4 GiB `ngram_embedding.safetensors` + `vision_k6`)
      first, then `3.05bpw_h5_ng5` (79.3 GiB, includes `mtp_hyper_connection_mixer_patch.safetensors`), into
      `models/turboderp/Qwen3.8-Flash-Next-exl3/<branch>/`. ~10 MB/s → ~3 h and ~2.3 h. Tick when
      `download.log` shows `SHA-OK` for every LFS file of both branches. Not a measurement-window concern
      (I/O only), but do not start a second download while it runs.
*(Gate satisfied 2026-09-02: INF-70 C0/C5/B1/D0 have ranked the levers — the weight paths run at ~40% of read
bandwidth and the expert path is bytes-proportional, so a bytes lever pays at ~1.5× its roofline value (B2).
X0 and the reference-kernel half of X1 started 2026-09-02 ~19:00Z as subagent `x1`, Fable-low: format facts
from the downloaded 4.05 branch's headers + exllamav3's own `mul1` CPU GEMV extracted into a torch-free
harness and run on REAL expert tensors at 1/8/24/48 threads, cache-resident and DRAM-streaming. Note for the
record: nothing on this host can execute EXL3 end to end today — no GGUF, exllamav3 is CUDA-first with no
ROCm support, and its CPU code covers only the MoE expert GEMV.)*
- [ ] **X0 — format spec from source (no compute).** Read `moe_mul1.cpp`, `codebook.cuh`, `exl3.md` and the
      4.05 branch's tensor metadata; write `docs/design/exl3-mul1-ggml-type.md`: the bit layout of a 16×16
      tile at K bits, the `suh`/`svh` role at inference (which side gets the Hadamard, per tile or per row),
      the `mul1` scale tensors, how `out_scales: always` applies, and what a GGUF tensor of the new type
      must carry. Decide K range to support first (the 3.05 and 4.05 branches → K ∈ {3, 4} plus the fractional
      mix). Deliverable: a spec another session can implement from.
- [ ] **X1 — clean-room micro-kernel + honest benchmark.** A ggml-external C++ kernel for one expert
      matrix `[2560 × 640]` at K=4 (and K=3): the fused byte-sum decode → `vpdpbusd` GEMV against a Q8
      activation row, band-contiguous layout. Benchmark per INF-70 C3/C4 discipline: same box, same window,
      against the IQ4_XS `vec_dot` and the IQ4_NL 8×8 repack path on the *same shape*, cache-resident and
      DRAM-streaming, at 1 and 48 threads. **Remember the campaign's standing lesson: clean-room gemv wins
      have failed to transfer in situ four times** — this phase only proves the decode is not compute-bound;
      it does not predict end-to-end gain.
- [ ] **X2 — importer.** `gguf-py` tool that reads the exl3 safetensors branch and writes a GGUF whose
      expert tensors (`ffn_{up,gate,down}_exps`) are the new type and whose remaining tensors are copied
      from the uniform IQ4_XS trunk (INF-70 B4/B5 artifact) — a mixed artifact. Handle the per-expert
      slab layout (expert is the outermost dim), the Hadamard sign vectors, and the scales. Verify with a
      round-trip: dequantize one expert on the CPU path and compare against exllamav3's own dequant of the
      same tensor (their `dequant` utility; numerical identity is the gate).
- [ ] **X3 — ggml type + `mul_mat_id` path in the experimental tree.** New `GGML_TYPE_EXL3_MUL1_K{3,4}`,
      `type_traits`, `from_float` = Q8 activation quant, `vec_dot`/gemv for the type, and the
      `mul_mat_id` expert path; **activation Hadamard applied once per op, not per expert.** Gates: greedy
      generation identical in *meaning* (not bit-exact — different weights), logit KLD vs the IQ4_XS-uniform
      trunk on a fixed 64-prompt set, `test-backend-ops` for the new type, arch test.
- [ ] **X4 — the measured comparison per INF-70's artifact rule.** Mixed EXL3-experts artifact vs the
      uniform IQ4_XS artifact, same build, same window, C5 recipe, at 3.05 and 4.05 bpw experts: ms/token,
      achieved GB/s, KLD/PPL. Keep only if it beats the B4-optimised IQ4_XS/IQ4_NL artifact at equal or
      better KLD. Report to INF-70's ledger.
- [ ] **X5 (optional) — dense projections and the head.** exllamav3 has no CPU path for these; if X4 wins
      on experts, extend the type to the dense `[n × 2560]` shapes and the 4-bit MTP head (`mtp_bits: 4`)
      so Axis E can draft from the same format.

## Non-goals and hazards

- Not a port of exllamav3's runtime, PyTorch extension, or CUDA kernels; only the `mul1` decode identity
  and the layout are borrowed. Licence: exllamav3 is MIT (verify at X0 before copying any code).
- Quality claims come from the turboderp README's plots only — X4 measures them here.
- Prefill: the shipped CPU kernel is `MAX_M = 4`; prefill through the new type needs a dequantize-then-GEMM
  path (what ik_llama.cpp did for its KT types) or it will regress pp badly. Scope X3 as decode-first and
  measure pp512 on every arm.
- Do not start X1 until INF-70 C0/C5/B1/D0 have ranked the levers; if the token is dispatch-bound at the
  measured floor, a bytes lever pays less than Axis D.
