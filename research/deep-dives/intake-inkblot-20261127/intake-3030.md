# Inkling 2 Mini repetition with concurrent requests on HIP

**intake-3030 · Sweep 2 · partial source read**

[Primary source](https://github.com/ggml-org/llama.cpp/issues/33150)

## Evidence

- Confirmed within the stated scope. One reporter on two RX 9070 XTs saw 33/120 responses hit the repeat limit with two active requests versus 1/28 with one busy slot on the same two-slot server. [Issue body, Results table, HIP simultaneous and sequential rows](https://github.com/ggml-org/llama.cpp/issues/33150)
- Confirmed. The reporter did not isolate the cause of the symptom. [Issue body, paragraph following example tails](https://github.com/ggml-org/llama.cpp/issues/33150)

## Limits and corrections

Read issue body, config, hardware, results table, tail examples and comment inventory. Pre-merge f7d1bbb on two gfx1201 devices, IQ3_S, FA on, q8_0 KV, BFCL tool prompts. Different request subsets and counts. CUDA observation used another setup. No bisection or single-MI210 run.

2026-11-27. Concurrent Base repetition can confound model quality. This is one field report on a different GPU architecture. Two configured slots with one busy is distinct from a one-slot server. Do not infer that the merge, Inkblot or loop depth causes the symptom.

## Recommendations

- RI-HIP. Exercise the qualified HIP path with identical Base items under one and two active requests and isolate any repeated-output failure.

## Sources surfaced

The merged indexed-bias implementation was selected for sweep 3. The older comparison CUDA run differs in device, context and KV; it supplies no additional controlled replication.

Artifact audit clean. External code and model weights were not executed.
