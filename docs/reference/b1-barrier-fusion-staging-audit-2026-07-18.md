# B1 Barrier-Fusion Staging Audit - 2026-07-18

## Verdict

B1 is **not ready as a flag A/B** for the OP-2 quiet window.

Current `experimental-v7-refresh-20260716` (`cf051d3e18c7d8d898581f42a468602c7f6bade0`) has no current `B1_FUSION_ENV_FLAG` and no qwen35/qwen35moe barrier-fusion path. OP-2 should not advertise B1 as a simple environment-toggle measurement unless a fresh v7 fusion branch and immutable binary pair are staged first.

## Current Source Findings

- `/mnt/raid0/llm/llama.cpp-experimental/src/models/qwen35.cpp`: qwen35 still builds `wqkv`, `wqkv_gate`, `ssm_beta`, and `ssm_alpha` as separate matmuls.
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/qwen35moe.cpp`: MoE frontdoor follows the same separate-matmul pattern.
- `/mnt/raid0/llm/llama.cpp-experimental/src/llama-model.h`: tensor slots remain separate for `wqkv_gate`, `ssm_beta`, and `ssm_alpha`; there is no fused tensor slot.
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ggml-cpu.c`: `GGML_CPU_DISABLE_FUSION` exists, but it disables generic CPU fusions and is not a B1 enable/disable control.
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/ops.cpp`: current generic CPU fusion is RMS_NORM+MUL, not qwen35 barrier-count fusion.
- `/mnt/raid0/llm/llama.cpp-experimental/ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp`: `GGML_IQK=1` and `GGML_IQK_Q8_0=1` gate iqk dispatch only; they are not B1.

Historical branches contain barrier experiments such as `GGML_BARRIER_COALESCE`, but those are v5-era / feature-branch artifacts and are not valid OP-2 B1 arms without forward-porting, rebuilding, and validating on current v7.

## OP-2 Handling

Use this rule at OP-2 launch:

- If no prebuilt fusion binary/commit pair exists, skip B1 and record it as not staged.
- If B1 remains desired, pre-stage two immutable binaries before the quiet window:
  - control: current v7 or canonical v6 binary, exact commit and path recorded
  - fusion: fresh v7 branch implementing qwen35/qwen35moe graph/loader fusion, exact commit and path recorded

The likely implementation surface is:

- `/mnt/raid0/llm/llama.cpp-experimental/src/models/qwen35.cpp`
- `/mnt/raid0/llm/llama.cpp-experimental/src/models/qwen35moe.cpp`
- `/mnt/raid0/llm/llama.cpp-experimental/src/llama-model.h`
- `/mnt/raid0/llm/llama.cpp-experimental/src/llama-model.cpp`

## Measurement Skeleton

The canonical control remains the OP-2 `frontdoor_q8 tg128` recipe through `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_canonical.sh`.

If two B1 binaries are later staged, capture per arm:

- arm name, binary path, branch, commit, dirty status
- copied `CMakeCache.txt`
- binary `stat`, `sha256sum`, pinned `ldd`, and `readelf -d`
- full environment and argv
- raw JSON stdout/stderr
- median decode tokens/s and MAD
- cleanup proof

Until the fusion arm exists on current v7, any B1 result should be marked "not run / not staged", not "failed" and not "flag unavailable at runtime".
