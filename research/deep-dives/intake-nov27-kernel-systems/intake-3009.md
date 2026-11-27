# cuda : use constant V load length when head dim is unpadded

[Primary source](https://github.com/ggml-org/llama.cpp/pull/33161) · intake-3009 · 2026-11-27

Open on 2026-11-27. One-line change inside flash_attn_ext_f16_iter and nstages<=1 selects compile-time 2*nbatch_V2 for DVp==DV; padded head dimensions retain min(i0_stop,DV)-i0_start. Author reports the 512-head f16 2x8 kernel stack frame shrank 272→16 B. A6000/sm_86 CUDA 12.0 Gemma-4-12B-it-qat-UD-Q4_K_XL against master 94a1e4b72: pp16k 1052.81/1013.20→1940.21/1950.93 t/s and pp32k 652.50/652.86→1698.78/1726.56 t/s, two runs each, first baseline shared GPU. FLASH_ATTN_EXT author tests 4430/4430 before and after.

handoffs/active/rocm-kernel-authoring.md:L1147 @ b93bd31 owns served verify attention attribution, documented local shape 256 and q8_0 KV, distinct from the external 512 f16 case. HIP shares parts of the header; test compiler scratch and VGPR changes on actual AMD instantiations before routing or timing work. EPYC 9655 has separate FA backend; only the general compile-time-versus-runtime length specialization motif transfers.

## Evidence

- The unpadded head case uses a constant V length and leaves the clamp for padded V. [ggml/src/ggml-cuda/fattn-mma-f16.cuh:L944-L949 @ 078992f](https://raw.githubusercontent.com/sunnyadn/llama.cpp/078992f0f1b522e8a716f793f5257c609ccaf4bc/ggml/src/ggml-cuda/fattn-mma-f16.cuh)
- At pp32000 the two baseline runs produced 652.50 and 652.86 t/s and the patched runs produced 1698.78 and 1726.56 t/s. [Additional information §Prompt throughput table](https://github.com/ggml-org/llama.cpp/pull/33161)

## Scope and local transfer

Linked issue #32871 independently reports an A4000 prefill regression on build b12285, corroborating symptom only. The PR closes no demonstrated local gap. Results paired on a shared GPU with another process active during first baseline.



A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes wave-level streaming. Join executed attention symbols to private-segment bytes and scratch instructions from content-identified code objects. Compare constant-length and dynamic-tail paths only on affected shapes, retaining correctness for padded V and partial tiles.

## Sources surfaced

No additional decision-changing source identified.
