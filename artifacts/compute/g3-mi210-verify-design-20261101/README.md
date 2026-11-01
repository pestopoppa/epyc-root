# G3 MI210 verify-kernel diagnostic — design draft

**Status:** source/design preparation only; no build, run, dispatcher observation, performance result or deployment claim. This draft supports the open G3 task in `handoffs/active/speculative-decoding-mtp-refresh.md`; it does not close it or B5.

## Question and boundaries

For a named model, runtime, quantized K/V types and actual speculative verify batches, which flash-attention kernel does the MI210 dispatch? The source-only v9 reading is a hypothesis about this named kernel, not a measurement and not a CPU result. At v9 `0db32c06e3e550065b78311a6031ef3dd2c4f27c`, AMD MFMA selection occurs before the generic quantized-KV VEC fallback in `ggml/src/ggml-cuda/fattn.cu`; `Q->ne[1] <= 2` is a condition in that fallback, not sufficient to guarantee VEC. Report only observed shapes and actual emitted verify batches; draft budget alone does not prove a verify width.

## Candidate and evidence binding

1. Start a fresh, isolated experimental worktree from the current production tip; never modify or build the frozen production tree. Record full base and candidate commits, tracked diff, build flags, compiler/ROCm identity and hashes of all input models and the binary and actual HIP library. If the diagnostic targets the historical v9 source instead, label it v9 and do not generalize to v10.
2. Add diagnostic-only instrumentation at actual `ggml_cuda_flash_attn_ext` dispatch, not just its selector, and at the server boundary where the target verify batch is formed. The v10 source at `ffc1bac82eeca6f9099e1ccd9ba49703c460a115` places dispatch at `ggml/src/ggml-cuda/fattn.cu:643–645`; re-resolve after choosing the actual candidate. Tag verify batches with a monotonically unique request/slot/batch identifier and correlate actual GPU dispatches to that batch. Record prefill and ordinary decode distinctly; do not infer verify solely from shape or timestamps. Ensure instrumentation does not change routing; capture the selected enum from the same selector result used for execution. If reliable cross-layer correlation is absent, classify the dispatch as unknown rather than verify.
3. Each dispatch record should include candidate/build identity, batch/request/slot identifiers, phase, device, selected kernel, Q dimensions including `Q->ne[1]` and head dimension, GQA ratio, K/V types and sizes, and any selector-relevant parameters. Record actual draft count/verify width. Use bounded structured output, disclose truncation or drops, and retain raw logs and a row-level manifest.
4. At run time verify the loaded `libggml-hip.so` path and digest from `/proc/<pid>/maps`, a fix-specific instrumentation marker in that library, the linkage verifier, nonzero VRAM sampled during the request and KFD process count. A source tree, directory name, mtime or server version alone does not identify the loaded GPU implementation. Preserve the full source/build manifest and runtime evidence with the results.

## Scheduled diagnostic

Prepare the build and probe as keeper-owned CPU/GPU rows with explicit stop handling; this design does not authorize direct execution. Predeclare model/drafter hashes, exact launch and prompt set, K/V quantization, context lengths, repetitions and controls. Exercise at least draft budgets 1 and 2 or more, with distinct prompts and actual verified nonempty drafts at each width; include plain/no-spec and prompt-processing controls. Require at least one unambiguously correlated verify dispatch per intended condition. If a budget yields no draft or no identifiable verify event, that condition is UNKNOWN, not a negative finding. Keep the run diagnostic rather than a speed or promotion test.

Record the per-condition counts and selected enum by actual verify width, with any unsupported quant type, instrumentation loss, missing residency, early stop and unknown classification visible. The result can establish that VEC was or was not observed in the sampled verify events under the pinned setup. It cannot establish that VEC never occurs on all prompts, models, or widths.

## Separate bandwidth decision

Kernel selection and full-cache conversion are mechanistic observations; neither by itself establishes that a configuration is bandwidth-positive, faster, or deployment-worthy. If the G3 observation motivates a performance question, predeclare a separate matched, interleaved comparison with quantized and appropriate nonquantized K/V controls, real acceptance and correctness instruments, GPU residency, comparable contexts and a noise floor. Measure the relevant bytes/bandwidth or timings under the measurement constitution, and do not make a general bandwidth-positive claim from a dispatch-only run. B5 remains open until its own acceptance and correctness evidence exists.
