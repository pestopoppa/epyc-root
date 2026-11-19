# Direct LB1c diagnostic

`lb1c_direct.py` generates a patch against production source commit
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, without changing any source tree.
The patch adds an opt-in `GGML_LB1C_PATH=MMVQ|MMQ` dispatch override and
replaces the backend test's default population in both `test` and `perf` modes
with the same seven quant types, widths 4–9, and supplied `(m,k)` shapes.
Here `m` is output rows and `k` is the reduction dimension.

Supply a JSON config with `lane` equal to `DS41` or `Q38FN`, a `shape_source`
object containing `repo`, full `commit`, and `path`, and a nonempty `shapes`
array of objects containing positive integer `m` and 256-aligned integer `k`.
The source locator must identify an actual reviewed shape inventory; syntactic
validation of that locator does not verify its contents. All seven types are
tested at those shapes, independently of whether the model uses each type.
This isolates kernel crossover from the model's quant-type mix.

```
python3 scripts/fillers/v11/lb1c_direct.py \
  --repo /mnt/raid0/llm/llama.cpp \
  --config /path/to/committed-shape-config.json \
  --output /mnt/raid0/llm/tmp/iqk-iquant-enablement/lb1c-direct/generated
```

The output contains `direct.patch` and `manifest.json` with the production
commit, source hashes, patch hash and complete config. Generation grants no
build or device authority. Apply only in a fresh experimental worktree and
publish the build and GPU sweeps through rowflow. Bind the resulting binary
and libraries to the patched source/build manifest; require the
`LB1C_DIRECT_V1` marker in the library and the expected path marker in each
launch. Use the same binary for both paths, changing only the environment.
Run correctness for each path before perf, with identical inputs and CPU
reference checks, in the owning session's claimed GPU window. Keep three
interleaved launches per path and separate timings for each shape; lower
microseconds is better. A kernel crossover is not a serving speed result.

The override refuses unsupported architecture, wave size, quant type, width,
layout, batched tensors and unsafe padding instead of falling back. Its path
marker logs once per thread to avoid repeated logging in timed invocations.
Unset leaves ordinary routing and test populations unchanged.

This patch is diagnostic instrumentation, never a champion candidate. Remove
it before any promotion, rebuild, and verify `LB1C_DIRECT_V1` and
`GGML_LB1C_PATH` are absent from the rebuilt library. Host tests compile and
exercise the emitted C++ branch/refusals and matrix, but establish neither HIP
compilation, device correctness nor crossover thresholds.
