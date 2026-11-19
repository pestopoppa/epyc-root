# AM-PORT-3 offline fitter

`fit.py` implements the per-layer, per-KV-head beta and value solve for the
faithful AM port. It is independent of the native server and changes no default
decode path. Seven model-free tests cover analytic 5x compaction, an independent
normal-equations oracle, rank deficiency, masks, invalid inputs, undefined cosine,
and content identity/query split enforcement.

```bash
OPENBLAS_NUM_THREADS=1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python \
  -m unittest discover -s scripts/benchmark/am_port3 -v
```

The mathematics follows research repo `scripts/benchmark/attention_matching.py`,
blob `1ff2f885f005a784acc83d288940b20983a23d93` at commit
`a794f5b54bea1a1f0752e0e3514ce07fa14c5ff2`. Like its fast path,
beta is `log(max(lstsq(exp_scores[:, indices], sum(exp_scores)), 1e-12))`;
C2 solves compact attention weights against the original attention output.
Clamping least squares is the specified fast approximation to NNLS, not the
constrained optimum. This implementation uses float64 SVD internally rather than
the reference's float32 Torch `gels`, and exports float32 beta/C2. It does not
claim bitwise Torch agreement. No source files are copied from the research repo.

Each input NPZ contains ONE layer and KV head:

| Array | Shape | Meaning |
|---|---|---|
| K | T × Dk | Original keys after native QK normalization and RoPE |
| V | T × Dv | Original dequantized values, before any rewrite |
| Q_fit | Nfit × Dk | Calibration queries after native QK normalization and RoPE |
| Q_eval | Neval × Dk | Separate held-out queries in the same coordinates |
| indices | t | Sorted unique original cache row indices |
| fit_ids, eval_ids | Nfit, Neval | Unique strings encoding sequence, position, and query head |
| bias_fit, bias_eval | T or N × T | Optional original additive attention bias/mask |

GQA query heads belonging to this KV head are pooled on the query row axis.
Do not mix distinct KV heads or layers. The native cell carrier shares retained
positions across heads **and layers**, so the capture/selection stage must supply
the same indices to every shard. Independent per-head top-k selection cannot be
loaded into that carrier. `convert.py` now supplies a common deterministic uniform
selection with both prefix endpoints; it does not optimize the selection.

The sidecar JSON requires `source_commit`, `model_identity`, `capture_id`, integer
`layer`, integer `kv_head`, positive `attention_scale`, `coordinates: "post_rope"`,
and `capture_sha256`. Record the actual graph scale; do not infer it from model
embedding width. Identity strings must refer to the actual capture/build/model;
the digest check proves file binding, not the truth of caller-supplied identities.
Query ID disjointness refuses declared leakage; capture must also guarantee the
split's provenance. Use a frozen original cache for both query sets.

```bash
OPENBLAS_NUM_THREADS=1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python \
  scripts/benchmark/am_port3/fit.py --capture /scratch/head.npz \
  --metadata /scratch/head.json --out /scratch/new-fit-directory
```

Output `carrier.npz` contains indices, beta[t], and C2[t,Dv]. `FIT.json` binds
capture metadata, capture bytes, fitter source, and carrier bytes by SHA-256;
records rank/clamp diagnostics; and reports held-out mean/min cosine (higher is
better), relative L2 (lower is better), and undefined cosine count. Zero-norm
outputs have undefined cosine and cannot silently pass a threshold. Existing
output directories are refused. These records are offline diagnostics, with no
automatic native quality verdict or belief grade.

Original attention may include a mask; compact weights use beta alone, following
the reference. This is suitable for the frozen-cache decode view. It does not
establish correctness for arbitrary causal prefill masks, sliding windows, key
repositioning, future RoPE positions, or quantized carrier loading. Future native
integration must keep original retained positions, verify the export/reload
attention output, and measure cache quantization effects explicitly.

The solver holds N×T full attention and N×t least-squares matrices for one shard;
capture must bound N before scheduling. No 32K model run, 36 GiB memory proof,
16-layer cosine verdict, or default-off throughput/KLD comparison has been run.
AM-PORT-3 remains open for the model capture driver, linked patched-kernel
validation and a published calibration/decode row; experimental graph/C2 hooks
are supplied below. This code does not alter
the existing per-cell beta implementation.

## Bounded native attention capture

`native_capture.h` provides a `ggml_backend_sched_eval_callback` for the pinned
`c9f2e34cea7a0e9ddac5ad7b2088bf06b56ee1db` public API. A calibration driver can
install it through `llama_context_params.cb_eval` and `cb_eval_user_data`:

```cpp
am_capture::state capture;
params.cb_eval = am_capture::callback;
params.cb_eval_user_data = &capture;
// Create context, fill the original cache, then arm exactly one bounded ubatch.
capture.begin(new_capture_directory, actual_global_attention_layer_ids);
int rc = llama_decode(ctx, calibration_batch);
llama_synchronize(ctx);
if (rc != 0) { /* refuse the capture; do not call it complete */ }
else capture.finish(); // REQUIRED: callback errors do not cancel native decode
```

The driver must preserve build/model/input identities and query positions before
decoding; use a fresh, single-sequence, contiguous-position cache. It must provide
the actual global-attention layer set, use FA, bound the final batch to one
ubatch, and keep callback state alive until context evaluation finishes. The
callback starts disabled, does not mutate tensors or add graph nodes, and records
the flash node's actual scale. It identifies Qwen35 global layers through the
post-RoPE `Qcur-<layer>` name and its unary view ancestors. Unknown layers,
multiple streams, sinks, ALiBi/softcap, duplicate layer visits, missing layers,
unsupported tensor layout and budget overruns refuse completion. DCA and other
architectures are not silently treated as captured: missing layers refuse at
`finish()`.

Native tensor reads use backend transfers and per-type dequantizers, one row at
a time. Files contain canonical little-endian float32 with dimensions reversed
from ggml `ne`: Q/K/V `[stream, head, token, width]`, output
`[stream, query_token, query_head, value_width]`, mask
`[1, 1 or query_heads, padded_query_token, cache_row]`. This preserves quantized K/V as actually
consumed by attention, noncontiguous Q, unused cache rows and padding masks.
The default bounds are 512 query tokens, 36,864 KV rows, width 512 and 4 GiB total
float32 output. Streaming limits host row scratch; it does not prove the
real-model GPU memory budget. `COMPLETE.json` appears atomically only after all
requested layers succeed. Incomplete directories are diagnostics, never inputs
to fitting.

`capture.py --check <directory>` reconstructs native attention using pooled GQA
head mapping, captured masks and scale. It emits content hashes and relative L2 /
maximum absolute difference. This checks capture integrity; it does not measure
compact-cache quality. A model-free CPU scheduler test (4 query heads, 2 KV
heads, quantized K/V, a noncontiguous Q view and padded causal mask) observed
relative L2 `0.0001949131192` and max absolute difference `0.0005026979804`
against the float64 numpy oracle. Capture enabled/disabled outputs were exactly
equal in that test. These are not model throughput/KLD or GPU findings.

Compile/run the native test against headers and libraries bound to the approved
source by its BUILD.json (set `LD_LIBRARY_PATH` to that build's own `bin`):

```bash
c++ -std=c++17 -O2 -Wall -Wextra -Werror -I<source>/ggml/include \
  scripts/benchmark/am_port3/test_native_capture.cpp -L<build>/bin \
  -lggml-cpu -lggml-base -lggml -Wl,-rpath,<build>/bin -o <scratch>/test_capture
LD_LIBRARY_PATH=<build>/bin <scratch>/test_capture <new-empty-scratch-directory>
OPENBLAS_NUM_THREADS=1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python \
  scripts/benchmark/am_port3/capture.py --check <new-empty-scratch-directory>/valid
```

The test's output parent must exist and its child names must be unused. It checks
the actual scheduler callback, quantized row reads, output parity, missing and
unexpected layers, duplicate ubatches, and byte-budget refusal. Python tests now
total 11, including reader failure and GQA/output-layout checks. The native test
used the AM-PORT-2 BUILD.json source pin above and verified its CPU-library digest
`1cdfde8202836f92cf0ed115c37a1540cf0dc880154b8ee6a1f50d37d75b48ec`
before linking. Original evidence remains in
`/mnt/raid0/llm/tmp/triattention-kv-selection/am-port3-native/`; no binaries or
source trees are vendored here. The driver/converter below implement the capture,
original-position/query-ID conversion, shared selection and fitted loading paths.
Executing the fully linked patched build on a model remains a row task.

## Native beta mask and C2 loading primitives

`native_carrier.h` is an explicit, standalone ggml interface, tested against the
same approved header blobs and CPU-library digest above. The experimental patch below installs it
in `llama-graph.cpp`; no serving kernel or server has been deployed. A driver/integration must:

1. Assemble one complete `layer_fit` per global layer, pooling the fitted shards
   into head-major beta/C2 arrays; call `validate_layers` to require a single
   common retained-position selection and unique layer identities.
2. Synchronize the context and resolve the original selected positions to the
   current native physical cache rows. Supply that exact `row_binding` to every
   operation. The binding expires after cache movement, defragmentation, state
   restore or mutation; these primitives cannot verify caller-supplied native
   cell identity. Do not shift retained positions or infer them from row numbers.
3. Call `load_values` on the correct layer's raw V tensor while the context is
   synchronized. Only untransposed single-stream `[head*width, cache_row]`
   storage is accepted. F32, F16 and block-aligned Q8_0 are supported. All heads
   are validated and encoded before any write; finite input that overflows F16
   or the Q8_0 scale is refused without changing earlier rows. Backend transfer
   failure is fatal in ggml, so this is validation atomicity, not transactional
   recovery. Quantization changes C2 and must enter the native quality verdict.
4. In the attention graph, pass the original causal mask to `build_mask`, with
   the layer carrier and binding. Its explicit graph input scatters each beta
   onto its physical row, with zero for new/unfitted rows. Original mask holes
   and query padding remain masked. GQA uses contiguous query-head groups,
   expanded to ALL query heads to avoid modulo-broadcast assigning the wrong
   KV head. Pass the returned F16 mask to FA; allocate the graph, then call
   `graph_mask.upload()` before evaluation/reuse. Its data is a snapshot, so
   rebuild/rebind after cell movement. Do not also apply PORT-1's scalar beta.

Null carrier is the default-off branch: it returns the original mask pointer
without allocating inputs or graph nodes. Active masks are bounded to 36,864
cache rows, 512 padded query rows, 256 heads and a default 256 MiB per-layer F32
expanded-mask budget. This bounds each temporary, not the entire model graph.
Head-specific masks bypass some optimized HIP FA paths; CPU correctness here
does not establish HIP support, residency, throughput or the 36 GiB budget.

`test_native_carrier.cpp` evaluates two independently biased layers through the
real CPU scheduler, with 4 query heads/2 KV heads, sparse retained rows, original
mask holes and a newly appended row. Its independent double-precision oracle
uses actual dequantized Q8_0 C2 bytes and the actual rounded F16 beta mask. It
also checks untouched cache rows, inconsistent layer selections, default-off
tensor identity, GQA refusal, byte limits, wrong layer/position/physical-row
bindings, nonfinite values and late F16 overflow before writes. Observed maximum
attention absolute error `4.62855e-06`, layer-beta output difference `1.71148`,
and maximum Q8_0 value round-trip absolute error `0.00484622` are model-free
diagnostics, not real-model quality evidence.

Compile with the native-capture command above, substituting
`test_native_carrier.cpp` and a scratch executable name; it takes no arguments.
The experimental context/graph-input hook and raw-cache binding are supplied
below. Capture driver/NPZ conversion and a bounded GPU row remain. AM-PORT-3 stays open.


## Experimental context and graph integration

`integration.patch` applies only to detached scratch worktrees at
`c9f2e34cea7a0e9ddac5ad7b2088bf06b56ee1db`. `apply_integration.py` refuses any
other source commit, attached branch, main checkout or dirty tree, and installs
the two lane-owned headers alongside the patch. It never edits a serving tree.

```bash
python3 scripts/benchmark/am_port3/apply_integration.py --source <detached-scratch-worktree>
python3 scripts/benchmark/am_port3/check_integration.py \
  --source <detached-scratch-worktree> --manifest <approved-CPU-build>/BUILD.json \
  --out <new-empty-scratch-output>
```

The internal C++ API is `ctx->am_install(std::move(layer_fits), 0)`. Install once,
after synchronizing and pruning the original cache to the COMMON original
retained positions; do not reposition keys. The integration independently
synchronizes, validates native model head geometry and exact coverage of every
attention layer, resolves original positions through `llama_kv_cells`, and
prepares every layer's C2 encoding before writing any layer. A late invalid
layer therefore leaves all cache bytes unchanged. Backend transfer failures
remain fatal, not recoverable transactions. `attention_cache()` resolves the
hybrid's attention member, never its recurrent state. The driver must preserve
the recurrent state corresponding to the original prompt.

Context-owned state reaches graph parameters explicitly. Enabling it clears
cached graph results, and graph reuse compares its identity. Each global layer
registers its own `llm_graph_input_i`; its `set_input()` re-resolves current native
cells and uploads head-specific beta on every evaluation, including reuse of an
already allocated graph. Contiguous GQA groups, original causal/padding masks,
and zero beta on newly appended rows are preserved. The fused CPU decode path
is bypassed while active so it cannot silently ignore the graph carrier.

This first integration permits ordinary causal FA on Qwen35, sequence zero,
`n_seq_max=1`, single-stream untransposed storage and append-only queries beyond
the installed frozen cache. It refuses DCA, SWA, sinks, ALiBi/softcap, shared
cells, missing/duplicate positions, inconsistent head geometry and PORT-1 beta.
Quantized K/V normally enables Hadamard rotations in this kernel; use F16 K/V
for the first model run, or disable rotations **before original capture** and
prove those coordinates. Loading unrotated C2 into a rotated cache is refused.
F16 C2 conversion error must still enter the native quality verdict.

A cache mutation epoch invalidates active fits after sequence removal/copy/keep,
position changes, scalar-beta changes, clear, shift, stream copy, chunk injection
or state restore. Even restoring the same positions invalidates the fit, because
the restored V may be the original values. Conservative invalidation also applies
to attempted mutations. Make a fresh context and repeat capture/prune/install
after invalidation; installation is one-shot. Direct writes through raw tensor
access are outside this API and forbidden while active. Saving an active cache
does not serialize the fit and cannot yield a resumable fitted context.

`check_integration.py` checks the exact tracked patch, installed header bytes,
source pin and approved CPU-library digest, syntax-checks the three modified
translation units, and runs native carrier/runtime tests. The runtime test uses
actual native cell metadata and an already allocated CPU scheduler graph for two
layers (4 query / 2 KV heads); it changes physical bindings between evaluations
and verifies refreshed beta, mask holes and new-row zeros. This tests the input
primitive's refresh; the active context deliberately refuses actual cache
movement via its epoch. The carrier test also refuses a late-layer overflow
without writing an earlier valid layer. Test evidence remains at
`/mnt/raid0/llm/tmp/triattention-kv-selection/am-port3-integration/check/TEST.json`.

These checks do not link or execute a complete patched model kernel. The original
CPU library supplies unchanged ggml operations only. Full patched CPU/HIP build,
context-install/default-off decode checks, calibration driver/NPZ conversion,
native compact-output quality, 36 GiB residency and 32K decode still require a
published row. Multi-head HIP FA support and default-off throughput/KLD remain
unmeasured; syntax and model-free tests cannot close those gates.

## Calibration/append driver and frozen-prefix conversion

`driver.cpp` supplies two separate native invocations against `integration.patch`:

* `capture`: decode prepared prefix token IDs in bounded batches, save its native
  sequence state (including recurrent state), then capture exactly one suffix
  ubatch. Persist the actual native physical-row/original-position map and split
  suffix positions into alternating fit/eval sets. Every GQA head at a position
  stays in the same split. Model tokenization/preparation happens before the row.
* `reload`: restore that saved prefix and verify the saved token IDs; prune only
  the attention cache to the common original selection, install head-specific
  beta/C2, then run a bounded greedy append probe. The first token is supplied
  from full-prefix logits; EOS does not shorten the fixed stability probe. This
  probe records completed steps and refuses nonfinite logits. It does not score
  quality or compare default-off performance/KLD.

Capture `RESULT.json` records `prefix_greedy_token` before evaluating the suffix;
use that value as reload's `first_decode_token`.

Use `run_driver.py` from an admitted row launcher. It seals successful capture
outputs with state/completion SHA-256 and verifies state/carrier/identity bindings
before reload. Invoking the C++ executable directly bypasses these content checks.
The row must additionally prove the linked binary contains the exact patch and
headers, and bind model/prepared inputs to their approved identities. A config's
`source_commit` string alone is not a binary freshness proof.

Compile the driver with C++17, **installed patched `src` first in the include
search order**, then the lane AM-PORT-3 directory, `include`, `ggml/include`, and
`vendor`. It uses the kernel's vendored nlohmann header and internal context API.
Link the complete patched llama/ggml libraries and set that build's own
`LD_LIBRARY_PATH`. Merely linking the original AM-PORT-2 library cannot supply
`am_install`. No full patched link/model execution has been verified yet.

Config common fields: `mode`, new `out` directory, `model`, `model_identity`,
`source_commit` (the exact pin above), `capture_id`, `prefix_tokens` (prepared ID
array, 2..32768), `n_ctx` (<=36864), `n_gpu_layers`, and `threads`. Capture adds
`calibration_tokens` (2..512 IDs fitting the context). Reload adds `prefix_state`,
`carrier`, `decode_steps` (1..32768, within remaining context capacity), and
`first_decode_token`. F16 K/V, ordinary FA, sequence zero and disabled PORT-1 beta
are required. Callback and its bounded capture remain disabled during reload.
There is no serving deployment or quantized-KV fallback.

After a completed capture wrapper invocation:

```bash
python scripts/benchmark/am_port3/convert.py --capture <capture-out>/native \
  --provenance <capture-out>/PROVENANCE.json --keep <ceil(prefix_tokens/5)> \
  --out <new-fit-directory>
python scripts/benchmark/am_port3/run_driver.py --driver <patched-build>/am-driver \
  --config <reload-config.json> --converted <new-fit-directory>
```

Conversion crops **all calibration tokens and padding** from K/V, resolves original
prefix order through the native row map and requires every captured query to see
every prefix key with zero mask bias. It recomputes reference outputs on the
frozen prefix. Thus held-out fitter cosines compare a mathematical prefix view;
they are not the native causal suffix outputs (which also attend suffix keys).
The saved recurrent prefix state must be restored before install; leaving the
post-calibration recurrent state would pair incompatible histories. The optional compact capture/checker below supplies native reload-output
agreement; it still requires execution in a fully linked model row. The append
probe alone cannot close AM-PORT-3.

Conversion writes per-head NPZ/metadata/FIT records and `carrier.bin`, followed
last by `CONVERT.json` with capture/provenance/carrier hashes. A partial directory
without this manifest is refused by the wrapper. The native reader accepts only
the bounded little-endian `EPYCAM03` format: uint32 layer count/kept count, shared
int64 positions, then each layer's uint32 layer/head/value-width fields followed
by head-major float32 beta and C2. It validates shared positions, dimensions,
finiteness, duplicate layers, truncation and trailing bytes before installation.
Fits that overflow F16 C2 or the native beta bounds refuse conversion.

The model-free tests exercise a two-layer, 4Q/2KV-head 5x duplicate-cache fixture
with deliberately permuted physical rows, unused padding and extreme suffix
values; conversion excludes the suffix and recovers beta=log(5), C2 and held-out
cosine >0.999999. The compiled C++ reader independently checks all carrier axes
and malformed-file refusals. Run with `AM_BUNDLE_TEST=<compiled
test_native_bundle.cpp executable>` alongside the unittest command above. There
are 19 Python tests, including the native-reader invocation when this variable
is set. The driver passes patched-source syntax checks; full CPU/HIP builds,
GPU capture/reload agreement, default-off controls and residency remain row work.


## First-append compact capture and native oracle

Set `capture_reload: true` in the reload config and pass `--original
<capture-out>/native` to `run_driver.py` alongside `--converted`. The driver arms
capture only around the FIRST appended token after restore/prune/install. It
records the actual physical-row/original-position map and query position in
`COMPACT.raw.json`, then disables capture for the rest of the stability probe.
The default is false. Shared base masks and masks expanded to every query head
are supported; intermediate head counts refuse capture rather than broadcasting
with the wrong GQA mapping.

The wrapper requires the original capture and completed conversion before native
execution. After a successful reload it seals `COMPACT.json` with conversion and
completion hashes, then writes `CHECK.json` only after `compact_check.py` validates
all original/converted/native bindings. This checks original capture hashes,
FIT/carrier hashes, exact retained K, F16-rounded C2 and beta at resolved physical
rows, zero beta for the appended row, masked unused rows, and complete native
layer coverage. A standalone recheck is:

```bash
python scripts/benchmark/am_port3/compact_check.py \
  --original <capture-out>/native --converted <fit-directory> \
  --reloaded <reload-out>
```

Two metrics answer different questions, with cosine higher and error lower better:

* `native_vs_compact_oracle`: native flash output versus float64 attention using
  the ACTUAL captured compact K/V, head masks and queries, including the appended
  row. This isolates native reload/graph/capture integrity.
* `frozen_prefix_quality_on_reload_queries`: reconstructed compact-prefix output
  versus the ORIGINAL full-prefix reference using the reload's actual queries.
  Both sides exclude the appended row. This measures local prefix approximation,
  conditional on Q from the compact trajectory. It is not an independent
  full-model hidden-state/logit/KLD comparison or a new held-out calibration set.

Zero-norm outputs produce undefined cosine counts and null minimum/mean when no
cosines exist. The checker emits metrics; the admitted row's decision rule must
apply quality thresholds and combine native correctness, budget, default-off and
32K stability results. No automatic pass is inferred from a completion marker.

Twenty-five model-free tests cover 5x two-layer 4Q/2KV reloads with permuted rows,
C2/beta/K/padding corruption, original/fit/identity tampering, invalid head masks,
zero norms, wrapper preflight and successful sealing. A real CPU scheduler test
runs shared and distinct per-query-head masks against the numpy oracle, checks
capture enabled/disabled byte parity and preserves failure guards. Driver syntax
passes against the exact patch. These establish code behavior, not a full patched
link, model/GPU quality, default-off throughput/KLD or residency verdict. The full
CPU/HIP build and bounded capture/fit/reload/stability row remain to publish.

## Default-off controls (row execution only)

`control.cpp` is a separate public-API executable. Compile the SAME file against
the baseline and patched libraries; it includes no AM internal headers, installs
no fit or callback, and makes no cache mutations. This permits a baseline link
without the experimental `am_install` symbol. Use C++17 and the pinned source's
`include`, `ggml/include`, and `vendor` include directories, linking `llama`,
`ggml`, and `ggml-base` from each build's own `bin` directory. Keep the executable
beside its own backend libraries. The model and token arrays must already be
prepared before publishing. The comparison uses identical teacher-forced tokens
so a greedy divergence cannot silently change the workload.

Control config fields are `mode: "control"`, new `out`, `model`,
`model_identity`, `source_commit`, `prefix_tokens` (2..32768), `warmup_tokens`
(1..256), `probe_tokens` (1..256), `n_ctx` (<=36864, accommodating all tokens),
`threads`, and nonnegative `n_gpu_layers`. The context uses ordinary FA, F16 K/V,
one sequence, batch/ubatch 512. Prefix prefill and teacher-forced warm-up precede
the measured append steps. Each measured step times synchronized native decode;
logit reads, finite checks and trace I/O follow outside the timer. Fixed-length
teacher forcing does not stop at EOS. The bounded little-endian float32 trace
contains the logits AFTER each probe token (steps x actual vocabulary), capped
at 512 MiB. This is decode performance, not prefill or end-to-end latency.

Invoke only from an admitted row:

```bash
python scripts/benchmark/am_port3/controls.py run --driver <build>/bin/am-control \
  --library-dir <build>/bin --config <prepared-control-config.json>
python scripts/benchmark/am_port3/controls.py compare \
  --baseline <baseline-run-1> <baseline-run-2> <baseline-run-3> \
  --patched <patched-run-1> <patched-run-2> <patched-run-3> \
  --min-throughput-ratio <predeclared-threshold>
```

The wrapper clears `LLAMA_KV_AM_BETA`, sets that build's `LD_LIBRARY_PATH`, binds
executable/all llama+ggml shared-library bytes before AND after execution, and
requires actual `/proc/self/maps` llama/ggml paths to belong to that inventory.
This covers dlopened ggml backends, which executable `ldd` misses. A wrong or
changed library/config, partial trace, nonfinite logits, invalid timing or wrong
geometry refuses the completion `SEAL.json`. The seal also binds config identity,
trace/result bytes, current control-source digest, affinity and relevant
LLAMA/GGML/HIP/HSA/ROCR/CUDA/OMP/BLAS environment. These digests establish runtime
file identity; they do **not** establish that the executable was compiled from
the recorded source. Full CPU/HIP build manifests must independently bind the
exact patch/headers/control source and compiled artifacts before row admission.
Mapped HIP library paths also do not prove GPU residency; sample VRAM/KFD during
the model run separately.

Before publishing, predeclare the question (does the default-off patch change
decode logits/performance?), minimum meaningful slowdown, sample count and
throughput threshold; choose replicates relative to observed host noise. Run at
least three fresh contexts per variant in interleaved order with the same CPU
affinity and model offload, saving every completed run. Use a fixed sample count
without interim pass decisions; stop on a confirmed logit difference or invalid
runtime binding, otherwise finish that count. The comparator refuses repeated
directories, mismatched inputs/environment/source/affinity and artifact changes
within a variant. It reports baseline-to-patched KL (lower is better), exact
logit bytes, maximum logit error, greedy equality, per-run tokens/s, relative
median absolute deviation and patched/baseline median throughput ratio (higher
is better). Baseline repeat nondeterminism fails the exact-logit screen too.
An additive logit shift can have KL=0 while failing exact bytes. The explicit
throughput threshold is a screen within the measured noise, never proof of
literally zero throughput change. It cannot silently satisfy AM-PORT-3's
default-off futility rule; the model-row verdict must interpret these controls
under its predeclared decision rule. No real-model control verdict is supplied
by the synthetic tests or the baseline executable link.
