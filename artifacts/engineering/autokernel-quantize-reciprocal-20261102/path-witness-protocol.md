# Quantize reciprocal dispatch witness (prepared, not run)

Source inspected: lane `scratch/quantize-reciprocal-v10-source-20261102`,
`ggml/src/ggml-cuda/quantize.cu:502-522` and `mmvq.cu:2437-2442`.
The wrapper dispatches the changed `quantize_q8_1` only when at least one of
`ne1`, `ne2`, `ne3` differs from one. Grid y is `ne1`; grid z is `ne2*ne3`.
The unchanged `quantize_q8_1_1d` is selected when all three equal one.
The MMVQ caller can reuse a cached graph quantization, so source reachability
does not guarantee a dispatch on every operation. No quantizer-specific runtime
profiling hook was found in the lane CUDA sources.

Use the existing ROCm 6.2 external dispatch tracer, without kernel edits. It is
installed at `/mnt/raid0/llm/tools/rocm-profilers-6.2/opt/rocm-6.2.0/bin/rocprofv3`;
the installed launcher source supports `--kernel-trace`, `--output-format csv`,
`--output-directory`, and `--output-file`. Leave `--mangled-kernels` and
`--truncate-kernels` unset. Example command shape, for a future authorized run:

```text
rocprofv3 --kernel-trace --output-format csv --output-directory <new-capture-dir> --output-file prof -- <exact-sealed-release-binary> <exact-recipe-argv>
python3 path_witness.py <new-capture-dir>/prof_kernel_trace.csv --start-ns <active-window-start> --end-ns <active-window-end>
```

This is a recipe, not permission to acquire compute or run it. The capture owner
must set and retain the lane's isolated library environment and seal the actual
loaded HIP library/code objects against the approved full-candidate build manifest,
not just the executable. Capture executable/library digests, `/proc/<pid>/maps`,
full argv and environment, model digest, source tree/diff and build manifest hashes,
profiler path/hash/version, exact child PID and start identity, return code, trace
hash, own-PID residency samples and verified process drain. The old SDK native CSV
has **no PID column**: collect exactly one workload process per fresh trace folder,
capture its PID at launch and bind the folder to that process. Never infer PID
ownership from Agent_Id (it identifies a GPU agent). Unexpected workload children
or mixed-process captures invalidate attribution unless independently resolved.

Define the active inference interval before capture and record boundaries in the
same timestamp domain as the dispatch trace, with the clock mapping retained.
Choose a reproducible recipe with one active region per process if direct phase
markers are unavailable. Exclude startup, warmup and graph-capture activity from
the window; do not substitute the whole process lifetime. Require target dispatches
fully inside that window, with exact `quantize_q8_1(...)` symbol and grid y*z > 1.
Keep HIP graph settings identical to the benchmark recipe. A graph-disabled
diagnostic cannot prove dispatch under the graph-enabled recipe.

The checker returns 0 for target dispatch coverage, 3 for no observed target,
and 2 for invalid input. Its JSON is diagnostic only and explicitly refuses
performance eligibility. It distinguishes `_1d`, MMQ and similarly named helpers.
It cannot validate build/PID provenance; the capture manifest gates that separately.
A zero result is not a correctness, speed, or representative-workload claim.
No target in the selected window means that recipe has not demonstrated exposure
to the candidate; inspect the dispatch mix and select a multidimensional MMVQ
recipe before making a candidate performance claim.

Profile the **same content-sealed uninstrumented release artifacts** that will be
used in comparison. External tracing needs no diagnostic kernel binary, but all
profiled invocations remain diagnostic and their timings never enter benchmark
pairs. Run performance pairs separately with profiler injection absent and with
the same sealed artifact digests, model/recipe and library paths. If source
instrumentation is ever used as fallback, its binary is ineligible for performance
evidence; a fresh uninstrumented build plus structural/digest verification is
required. A path witness for a different instrumented artifact does not by itself
prove the measured artifact dispatched the target.

Validation performed here: seven synthetic CSV tests covering target/1d
separation, 1d-only refusal, warmup/edge exclusion, similar-name refusal,
contradictory-grid refusal, z-dimensional dispatch and stats-CSV refusal.
No build, model run, profiling capture, compute reservation or runtime evidence
was produced. Existing retained NEMO CSVs were consulted only to verify the native
column names and demangled symbol spelling; none is candidate evidence.
