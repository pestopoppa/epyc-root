# AutoKernel static probes — 2026-08-10

These probes were read-only. They did not launch a model, benchmark, server, GPU workload, or other
inference. The production kernel tree remained untouched.

## RVP-T0-2 — production gfx90a MFMA disassembly

- Frozen source/build identity: `production-consolidated-v8` at
  `67a433bf45a8a091d83b4ea0b32ff0735fd51800`.
- Input library: `/mnt/raid0/llm/llama.cpp/build-hip/bin/libggml-hip.so.0.16.0`, SHA-256
  `5aad7e89b2f2fae5b49c43ad06c52ecbbaac8b4f4f07e94cd9f3418077685cee`.
  <!-- CORRECTED 2026-08-10: originally recorded as ...8b4f07e94... (62 hex chars). That was a
       transcription error, not a truncation — the true digest contains "8b4f4f07e94". Re-verified
       with sha256sum. A provenance pin that does not verify is worse than none, because it looks
       checkable and fails only for whoever tries. -->
- Instruction-count reproduction note: `roc-obj` extraction is temp-directory based, so re-running it
  produces the same counts but different paths; the counts below are the reproducible artifact.
- Method: `/opt/rocm/bin/roc-obj -d -t gfx90a -o <temporary-directory> <library>`, followed by
  searches over the captured `.s` files. The extraction produced 134 gfx90a code objects.
- Result: 57 disassemblies contain `v_mfma_*`; 38 of those also contain a `mul_mat` symbol. Across all
  extracted disassemblies the instruction counts were:

  | instruction | count |
  |---|---:|
  | `v_mfma_f32_16x16x16f16` | 39,280 |
  | `v_mfma_f32_16x16x4f32` | 24,576 |
  | `v_mfma_f32_16x16x16bf16_1k` | 12,288 |
  | `v_mfma_i32_16x16x16i8` | 9,612 |

Conclusion: the hypothesis that MFMA is entirely absent from the production gfx90a `mul_mat`
artifacts is falsified. This is only an artifact-presence result: static disassembly does not establish
which runtime dispatch path a workload selects, nor the selected path's wall-time share.

## RVP-T0-5 — `init_tensor_uniform` call-site classification

- Input source: `/mnt/raid0/llm/llama.cpp/tests/test-backend-ops.cpp` at the same frozen commit,
  SHA-256 `7d57f30290929702539095ae017f8196e52f6829c8eca7f1cf91d496aa97ab6e`.
- Method: enumerate every `init_tensor_uniform(...)` call with `rg`, then read the only variable-bound
  call at lines 2042–2054. The function definition at line 54 is excluded.
- Result: all 56 call sites were classified.

  | input-range class | count | source lines |
  |---|---:|---|
  | symmetric about zero | 44 | 1198, 2054, 2119, 2177, 2237, 2293, 2346, 2432, 2566, 2640, 2684, 2745, 3047, 3172, 3246, 3482, 3525, 3581, 3640, 3746, 3748, 3889, 3989, 4217, 4244, 4573, 4616, 4694, 4725, 4756, 4787, 5053, 6113, 6780, 6784, 6829, 6988, 7023, 7056, 7130, 7215, 7442, 7445, 7584 |
  | one-sided | 9 | 2564, 3170, 3983, 3985, 4498, 4538, 5051, 6914, 6954 |
  | asymmetric and crossing zero | 3 | 3987, 6167, 6240 |

The variable-bound call at line 2054 is symmetric: it uses `[-150, 150]`, narrowed to `[-10, 10]`
for FP16 `EXP`/`EXPM1`. Default calls use `[-1, 1]`.

Conclusion: negate is distribution-preserving and therefore near-useless as a metamorphic input
transform for 44/56 sites. It is informative for the 12 non-symmetric sites; the nine one-sided sites
are also the highest-priority inputs for a constant-output/degenerate-range screen.
