# MI210 next kernel speed levers, from existing traces only (2026-11-18)

Owner: autokernel. Scope: served GPU models, which are the 27B Q8_0 + DFlash2 architect_critic and the A3B Q8_0 MTP shadow lane.
No new runs. Everything below comes from rocprofv3 kernel traces already on disk. Excluded because they are already in
flight: gv_fattn bandwidth, the A3B router MMVF knob and its wide-batch extension, EPI-Q8 and FAROWS. Excluded because they
were rejected: H16 M=36 MMQ, FA_VEC_LONGCTX_PB, folding q8_1 into MMVQ, paired gate/up launches, and the C10 q8wv
prefetch/bandwidth work (`kernel-champion-and-promotion.md`, C10-Q8WV-BANDWIDTH, closed twice).

## Traces used

| Trace | Model / phase | Notes |
|---|---|---|
| `/mnt/raid0/llm/tmp/c8-h17-profile-20261107/out/prof/{tg,dflash}_d{8192,32768,131072}/r0-*/.hip-tmp/trace/prof_kernel_trace.csv` | 27B decode, DFlash2 verify | The decode/verify window is the set of dispatches after the last `Cijk` (prefill) kernel |
| `/mnt/raid0/llm/tmp/ak-gpu-signals-ctr-20261116/out/PP/trace/trace_kernel_trace.csv` | 27B prefill | Uses the same tile mix as the run-25 profile |
| `/mnt/raid0/llm/tmp/rka-a3b-n4-trace-gpu-20261118/out/trace/r{1,2}-n{3,4}/kt_kernel_trace.csv` | A3B Q8_0 MTP verify, n=3 and n=4 (llama-bench `-p n -r 5`, d0) | Built from the C14 base |
| `/mnt/raid0/llm/tmp/c10-c6-dispatch-reprofile-20261110-r2`, `c6-admission-live-proof-r*` | Op-level q4_K probes | Not a served model, so not ranked |

Aggregator scripts: `/mnt/raid0/llm/tmp/c16-scout-work/agg.py` and `agg2.py` (agg2 does the post-prefill split).

**Staleness caveat.** The 27B h17 traces predate parts of C16. One example: the conv-state copies (`cpy_scalar` f32,
grid 30720 = 3 x 10240, K = n_rs_seq+1 copies per GDN layer, 3.8-4.2% of the DFlash2 verify step) show up unfused, but
AK-ASM-H15 (`bd950e2dc`) already fuses that concat + K-copy + ssm_conv chain. These traces therefore set an upper bound on
residual small-op work. Before anyone files a 27B small-op lever, re-trace C16 DFlash2 verify.

## Shares and efficiency

**27B DFlash2 verify (n=8), share of GPU busy time**

| Kernel | d8192 | d32768 | d131072 |
|---|---|---|---|
| Weight GEMV (MMVQ / q8wv) | 72% | 63% | 54% |
| Attention (gv_fattn / FA-vec) | 5% | 14% | 27% |

- GPU busy is 92-95%.
- q8wv runs at 837-881 GB/s, which is 52-55% of the 1.6 TB/s peak (filed C9 PMC recut). Its no-overlap limit is diagnosed
  and the closure stands.
- Attention is in flight.
- What is left: about 10-12% of small ops (quantize, rms_norm, bin_bcast, get_rows, concat). Part of that is already fused
  in C16.

**27B decode (n=1), d8192**

- MMVQ is 72% of busy time. 27B weights / per-token MMVQ time = 28.6 GB / 23.6 ms = about 1.21 TB/s (76% of peak).
- At d131072, FA-vec takes 54% and the GPU is busy only 37% of wall time. That is a host-gap finding, but plain decode is
  not the served path.

**27B prefill (pp, 11-16 trace)**

| Kernel | Share |
|---|---|
| MT128x96 | 23.9% |
| MT64x64 | 22.0% |
| gated_delta_net | 13.5% |
| MT64x32 | 12.0% |
| `dequantize_block_q8_0_f16` | 10.8% |
| `convert_unary` | 3.9% |

The `down` tile fix (MT160x256) is already in C10. The dequant + convert work (14.7%) re-materializes f16 weights for
every ubatch.

**A3B MTP verify, n=4 (r1)**

Total is 170.8 ms over 5 verify steps (34 ms/step).

| Kernel | Share | Notes |
|---|---|---|
| `mul_mat_vec_q` dense | 26.9% | |
| `mul_mat_f` router | 13.4% | In flight |
| `mul_mat_vec_q_moe` | 13.2% | |
| `k_bin_bcast` | 7.0% | 2595 launches of about 4.6 us |
| `quantize_q8_1` | 9.0% | Excluded (q8_1 fold / EPI-Q8) |
| `rms_norm` | 3.7% | |
| `get_rows` | 2.7% | |
| argsort | 2.3% | |
| softmax / sum_rows / clamp / div | about 2% | |

## Ranked levers (share x headroom, exclusions applied)

| # | Lever | Kernel(s) | Current efficiency | Fix | Expected e2e | Effort |
|---|---|---|---|---|---|---|
| **L1** | **A3B multi-row topk-moe fusion refused** | Router chain at n>=2: soft_max 7.7 + argsort 20.5 + get_rows 4.6 + sum_rows 4.6 + clamp 4.5 + div 5.4 = **47 us/layer x 40 = 1.9 ms = 5.6% of the n=4 step** | The n=1 draft pass already runs the fused AITER `topksoftmax_4x256x8` in 8.6 us. That makes the verify pass 5.5x slower on the same work | `ggml_cuda_check_fusion_memory_ranges` exempts only `nrows==1`. At n>=2 the allocator places ids/weights over the router logits and the fusion is refused. Stage the logits in a pool scratch buffer (one 4 KB D2D copy) and run the fused kernel on the copy | about -1.35 ms/step, so **+3-4% on A3B MTP verify (D=4, n=5)**. Nothing changes on the 27B (it has no MoE) | **S** (≈70 LOC, done) |
| L2 | A3B MoE expert GEMV | `mul_mat_vec_q_moe<Q8_0,2>`, 13.2% (gate/up 36 us, down 40 us) | Even if all 32 expert slots were distinct, it reaches only about 0.9-1.0 TB/s (55-61%). Overlapping experts across the 4 tokens are re-read per warp, so the true figure is lower | Group slots by expert so each expert's rows are read once for all tokens routed to it (ncols up to n). Also sweep a CDNA rows-per-block value (2 was tuned on NVIDIA) | +2-4% A3B MTP | M |
| L3 | A3B elementwise tail | `k_bin_bcast` 7% (residual adds 1024x1 and 4096x1, MoE weight mul 1024x8) plus `scale_f32` 1.7% | All launch-bound at about 4.5 us | Fold the MoE weight-multiply and expert-sum into the down-projection MoE epilogue, and the residual add into the following rms_norm (the add+rms_norm fusion pattern) | +3-5% A3B MTP | M |

Not top 3:

- 27B prefill dequant/convert (14.7% of prefill). Prefill is not the served bottleneck, and f16 weight caching does not fit
  in VRAM.
- 27B DFlash2 residual small ops. Re-trace C16 first (see the staleness caveat).
- The 27B long-context decode host gap (37% busy at 131k). Plain decode is not served; DFlash2 is busy 93% of wall time.

## Chosen candidate: L1, C16-TOPK-STAGE

- Branch `llama.cpp-experimental-c16-gpu-next-20261118` @ `c6294773f` (pushed to `fork`), based on the C16 composite
  `13d6fc150`.
- Knob `GGML_HIP_TOPK_MOE_STAGE=1`, default off.
- On first use it logs `C16-TOPK-STAGE staged-logits topk-moe fusion active`.
- The only logic change is in `ggml/src/ggml-cuda/ggml-cuda.cu`:
  - a new helper `ggml_cuda_topk_moe_only_logits_overlap`;
  - a staged branch after the existing memory-range check. That branch runs only when the knob is set and the logits are the
    only overlapping non-elided src.
- Not compiled yet. The row builds it.

Why the overlap check is the discriminator. Of the fusion conditions, the only one that depends on n_rows is the
`ggml_nrows(...) == 1` exemption in the memory-range check. Pattern match, `ggml_can_fuse_subgraph` and
`ggml_cuda_should_use_topk_moe` do not depend on it. The trace shows n=1 fused and n=4 unfused on the same model and graph
builder. The row confirms the mechanism directly in two ways: the engaged line must appear on B, and the n=4 op ratio has a
futility bar.

Row: `/mnt/raid0/llm/tmp/c16-topk-stage-gpu-20261118/` (prepared, NOT published, has a `READY-TO-PUBLISH` marker).

- **Grant:** gpu-q3, 16 cpus (88-95, 184-191). Servers and benches are pinned to 184-191. The core check runs on the live run
  only.
- **Correctness:** `test-backend-ops -o TOPK_MOE` on both arms.
- **Op timing:** A3B llama-bench at n=1, 4, 5 and 8 @32k, ABBA, plus a 27B control.
- **E2E:** A3B MTP D=4, 4 ABBA pairs.
- **Gate:** the operator's 27B KLD/PPL gate is needed only if 27B numerics change. The row proves they do not, because the
  engaged line must be absent on the 27B B arm. If it is present, the row FAILs and the gate run is required.
- **KEEP** iff e2e geomean >= 1.02, with no cell < 0.99 and AA-calibrated identity.
- **Futility points:**
  - n=4 op ratio < 1.005, or B not engaged;
  - e2e < 1.003 after 3 pairs.
- `handoff_task`: `rocm-kernel-authoring.md:C16-TOPK-STAGE`. **That box does not exist yet; it is needed.**
