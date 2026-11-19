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
loaded into that carrier. Selection itself is not implemented here.

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
AM-PORT-3 remains open for the model capture driver, per-layer/head graph bias,
C2 cache loading and a published calibration/decode row. This code does not alter
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
`[1, 1, padded_query_token, cache_row]`. This preserves quantized K/V as actually
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
source trees are vendored here. Real-model capture, NPZ conversion with original
position/query IDs, shared selection, fitted carrier loading and decode remain
unimplemented.
