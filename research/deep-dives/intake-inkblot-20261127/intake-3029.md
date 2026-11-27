# CUDA and HIP flash attention with indexed bias

**intake-3029 · Sweep 3 · partial source read**

[Primary source](https://github.com/ggml-org/llama.cpp/pull/33063)

## Evidence

- Confirmed. The merged backend dispatch supports indexed bias in tile and vector kernels. [ggml/src/ggml-cuda/fattn.cu:L693-L704 @ 2a33525](https://raw.githubusercontent.com/ggml-org/llama.cpp/2a335259caa98ff30013907efdf1beba484db119/ggml/src/ggml-cuda/fattn.cu)
- Confirmed. The upstream indexed bias uses source slot 6 for an auxiliary input. [ggml/src/ggml-cuda/fattn-common.cuh:L1327-L1329 @ 2a33525](https://raw.githubusercontent.com/ggml-org/llama.cpp/2a335259caa98ff30013907efdf1beba484db119/ggml/src/ggml-cuda/fattn-common.cuh)

## Limits and corrections

Read PR, merge revision, dispatcher, tile/vector input access and operator fixtures including one and two streams. No whole-model HIP test was run. EPYC INK2-PORT-2a records champion source-slot conflicts; retain its re-home and test inputs. Operator fixtures do not exercise concurrent requests.

2026-11-27. Use the merged implementation as a reference to the older interface PR. It supplies no MI210 serving result or attribution for the repetition report.

## Recommendations

- RI-HIP. Exercise the qualified HIP path with identical Base items under one and two active requests and isolate any repeated-output failure.

## Sources surfaced

The #32740 interface is already intake-2797#record. The PR’s touched operator files and tests are retained at the merge SHA. No further candidate-quality evidence surfaced.

Artifact audit clean. External code and model weights were not executed.
