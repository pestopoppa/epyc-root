# Z10: fp16-denormal Q-scale reciprocal audit

The named fp16 reciprocal-overflow mechanism is absent from the audited CUDA/HIP Flash Attention Q-quantization path at production v10. This is a static source conclusion, not a numerical test or a general FA correctness claim. The frozen tree's separate Vulkan shader still retains the old mechanism under its fp16 MMQ configuration; no Vulkan build or execution is established here.

## Source authority and scope

Production is `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. The historical locator was v9 `0db32c06e3e550065b78311a6031ef3dd2c4f27c`. G10's actual candidate is `933666a9db27b9a668ef74378331329524fc39aa`; its only change from v10 is `tests/test-backend-ops.cpp`, so the audited kernel files are byte-identical. The read used immutable Git objects, retained 25 source-file snapshots with SHA-256 and Git blob identities, and left the frozen production tracked tree unchanged. The [source audit manifest](../../artifacts/compute/refactor-z10-static-20261031/source-audit.json) records every file hash and both source and resource receipts.

[Upstream PR #27413](https://github.com/ggml-org/llama.cpp/pull/27413) describes a Vulkan Q quantization scale whose fp16 reciprocal overflows despite a nonzero guard. Its [merge commit `78ec4c378031811671d1c76a067acbee4f4c56ce`](https://github.com/ggml-org/llama.cpp/commit/78ec4c378031811671d1c76a067acbee4f4c56ce) promotes the working quantization values and reciprocal to fp32. The author separately cautions about flushing a denormal stored in shared memory. That report supplies the hypothesis, not evidence of a HIP failure.

## Q-scale producer and all downstream consumers

All line locators below are at v10; the G10 candidate has the same kernel bytes.

| Stage | Exact source path and lines | Source finding |
| --- | --- | --- |
| HIP source mapping | `ggml/src/ggml-hip/CMakeLists.txt:60–83` | HIP includes the CUDA headers/translation units and the default q4_0/q8_0 FA vector instances. The directory name does not limit this audit to NVIDIA. |
| Input type | `ggml/src/ggml-cuda/fattn-common.cuh:990–991` | FA checks Q and output as F32. |
| Quantization activation | `ggml/src/ggml-cuda/fattn-vec.cuh:104,154–206` | Q8 query quantization is selected for quantized K, not F16/BF16 K. Q scale storage and registers are `float2`. The one CUDA call instantiates `quantize_q8_1_to_shared<float2,...>` at line188 (v9 line181). |
| Quantizer | `ggml/src/ggml-cuda/fattn-common.cuh:331–373` | `vals`, `amax`, `sum`, and `d=amax/127` are float. Nonzero d divides float values before integer rounding. Exact zero leaves initialized integer zeros. The instantiated branch stores `make_float2(d,sum)`; the half2 branch is unreachable for this source instantiation. No fp16 reciprocal is formed. |
| Q4_0 K | same file `:149–177` | Reads float2 Q scale; multiplies it and subtracts the row-sum correction. K's stored half scale is converted to float. No reciprocal of either stored scale. |
| Q4_1 K | same file `:180–210` | Converts K's half2 scale/offset to float2 and multiplies with Q's float2 values. Division is by fixed `QI8_1`, not a scale. |
| Q5_0 K | same file `:213–255` | Same multiplicative scale plus row-sum pattern as Q4_0. No scale reciprocal. |
| Q5_1 K | same file `:258–301` | Same float2 scale/offset pattern as Q4_1. Division is by fixed `QI8_1`. |
| Q8_0 K | same file `:304–329`; `vecdotq.cuh:243–256` | Loads Q_d as float and calls `vec_dot_q8_0_q8_1_impl<float,1>`, whose scale operation is multiplication. The K half scale converts into the float parameter; no half reciprocal. |
| Selector and use | `fattn-common.cuh:620–642`; `fattn-vec.cuh:280` | Selector enumerates the five quantized K consumers above; the call passes the same Q_ds registers. No other CUDA consumer of this producer is present. |
| V dequantization | `fattn-common.cuh:410–619` | Quantized V dequantizers multiply stored scales, and add stored offsets where present. Half-output branches can use half multiplication; none takes a reciprocal of a stored quantization scale. |

The whole-tree symbol search also finds a separate SYCL definition/call. Therefore the old handoff's “single call in the whole tree” should be read as one CUDA call; this audit makes no SYCL backend-correctness claim.

## Reciprocal sweep and denormal-but-nonzero case

The audit read the FA common/vector/tile/MMA files, dot-product helpers, and adjacent Q8 quantizers, then traced the produced Q scale through every selected quantized-K consumer. The FA vector helper computes division in float and never narrows the resulting d before its consumers; a scale in the fp16-denormal range therefore does not encounter an fp16 reciprocal here. Downstream Q/K/V scale uses are multiplicative. The tile's `1.0f/KQ_sum` and vector/fixup output divisions normalize softmax sums, not stored quantization scales.

Adjacent generic `quantize_q8_1` and its 1-D version (`quantize.cu:59–68,126–135`) divide in float before storing a half2 scale. The MMQ quantizer (`:456–462`) computes both `127.0f/amax` and its inverse in float before the later store. The MXFP4 reciprocal (`:339`) is also explicitly float. These are not downstream inversions of this FA helper's stored scale and do not introduce the named fp16 reciprocal operation.

This does not prove correct behavior for arbitrary fp32-subnormal inputs, compiler reciprocal lowering, denormal flushing, quantization underflow, or non-finite inputs. It also does not establish any compiled image's instructions. Those broader properties are outside the particular fp16 reciprocal-overflow hypothesis; no binary, DSO, model, timing, or GPU-residency claim is made.

## Separate Vulkan source finding

At v10, `ggml/src/ggml-vulkan/vulkan-shaders/flash_attn.comp:123–145` still performs Q quantization and `1/qd` in `FLOAT_TYPE`. The shader generator (`vulkan-shaders-gen.cpp:661–701`) sets that type to `float16_t` for its fp16 pass and conditionally generates the MMQ variant when integer-dot shader support is enabled. Upstream's fix is not an ancestor of the frozen production commit. Thus the source still contains the reported mechanism on that conditional Vulkan path. This is not evidence that Vulkan is compiled, selected, or exposed by this host's CUDA/HIP serving route. Production remains frozen; this audit applies no patch.

## Acceptance and remaining scope

Z10's static read is complete with a scoped negative for the named CUDA/HIP fp16 mechanism and an explicit conditional Vulkan source finding. No new G10 execution follows from a supposed HIP fp16 reciprocal: that operation is absent in the audited path. G10's independently recorded numerical and residency outcomes stay unchanged, and its measurement parent is not closed by this source read.

The bounded source-only check exited0, verified all25 retained source identities and G10/v10 equality, and drained its owned children. It compiled and executed no kernel, model, or native benchmark. Parent publication must record the actual audit commit and this artifact before ticking only the exact Z10 source-read task.
