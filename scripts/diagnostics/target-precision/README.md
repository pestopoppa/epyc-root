# Prospective target-precision native capture

`capture.py` binds producer-authored native fields for the existing missing-control
box in `handoffs/active/speculative-decoding.md`. The existing research
`dflash2_beliefs.py` concurrency-grid carrier has a fixed different protocol and
is left unchanged. Stable bounded reads reuse
`scripts/vidya/qwen4exp_quality_capture.py:stable_bytes_identity`.

The admitted matrix entry point `runner.py PLAN OUTPUT_DIR` calls `open_capture(plan_path, opened_path)`
**before** any cells execute, then `finalize_precision(opened_path, cell_paths,
output_path)` at its native finalize boundary. Both writes are exclusive and
fsynced. The output directory must be new; there is no implicit resume or redraw.
The plan must declare synthetic or native-claimed origin, run/cell/prompt/seed/
repetition identities, target quant and prepared artifact hashes, fixed drafter,
backend, binary/library/source hashes, verification and sampling settings,
prompt/holdout/protocol digests, numerical floor and prospective decision rule.
No model hashing occurs in this module.

Each cell binds the exact plan digest, settings and case, terminal status and
original JSON output digest. Successful cells require original-output-matching
per-position accepted/drafted counts, exact total denominators and finite
nonnegative numerical divergence values. Failed/invalid/abstained cells retain
native fields and reasons; absent counts remain absent. Missing, foreign and
duplicate cells refuse closure. Successful-cell acceptance uses summed counts;
per-quant numerators and denominators remain separate. The overall weighted
acceptance describes successful cells only; it is not a precision comparison.

This binder establishes declaration/byte consistency only. It does not prove
actual residency, truthful settings, matched weights, pre-execution opening,
same-backend numerical adequacy, prompt holdout independence or a precision cause.
It always emits `causal_gate=UNRESOLVED` and `projection_ready=false`; the latter
means decision-bearing readiness, even when descriptive observations can project.
A planning-context canary, actual native-worker adoption and the missing scientific
controls remain required before decision-bearing execution.
No historical tuple reconstruction or grading rule is added.

Validation: `python3 -m pytest -q scripts/diagnostics/target-precision/test_capture.py`
(model-free tests only; no inference or precision evidence).

`runner` in the plan declares `argv` (a nonempty string list) and positive
`timeout_s`. The command receives `--plan PATH --cell-id ID --output PATH`.
The native worker must write a JSON object with explicit `status` and either the
successful telemetry above or a terminal failure reason. Nonzero exits/timeouts,
missing outputs and malformed JSON retain a failed/invalid cell. Stdout, stderr
and every existing output, including malformed bytes, are retained and hashed.
This entry point performs no model acquisition/preparation and must run inside
an admitted compute row; a passing model-free test does not qualify a model run.
`worker.py` supplies the per-cell process adapter for a **trace-enabled** DFlash
executable. This does not make the stock `llama-server` compatible: its summary
counters do not contain matched-prefix numerical controls. `native.cpp` now
implements the C++ producer using the actual common DFlash API. Model execution
and scientific qualification remain unperformed; fixture tests establish neither.

Select it with `runner.argv = ["/absolute/python", "/absolute/worker.py"]`.
`native_worker` must contain exactly `executable`, `env`, `prompt_manifest`,
`targets` (quant to absolute prepared GGUF path), `drafter` (absolute prepared
path), and positive `timeout_s`. `env` is the entire child environment and must
include its own `LD_LIBRARY_PATH`. The small JSON prompt manifest has the form
`{"prompts": {"prompt-id": "exact text"}}` and must match the shared manifest
digest. The worker checks the executable digest; it never hashes model weights.
Admission must separately bind prepared model/library identities and verify
runtime residency. A request echo alone cannot establish those facts.

For native-claimed cells, `runtime.py` observes only the worker's captured
`Popen` child during execution. Successful cells require two distinct observations
with the same PID/start-time identity, all declared libraries mapped at the
hashed file's device/inode, and no undeclared `libggml`/`libllama` mappings.
Library hashing streams bounded library files, caches stable inode identities,
and never opens model weights. HIP additionally requires `libggml-hip`, KFD
membership and nonzero per-child VRAM in both observations. CPU panels refuse
accelerator library mappings. A short or missed window is invalid, rather than
evidence that GPU execution did not occur. Timeout kills/reaps only this child.

`runtime.json` retains the request, process identities, monotonic timestamps,
original maps text, observed library identities, KFD counters and bounded error
diagnostics. Two qualifying samples are retained while observation continues;
subsequent identity/library contradictions invalidate the cell. Runner and closure
replay bind the original proof digest, cell request and runtime implementation.
Failed/invalid cells retain available proof records without gaining acceptance
counts. Synthetic fixtures bypass the live observer and never provide run evidence.
These checks establish observed residency within the cell process window; they
do not identify the verify kernel, prove overlap with an individual verify pass,
or independently attest the producer. No numerical-floor or causal claim follows.

The executable is invoked as `EXECUTABLE --request REQUEST.json --output TRACE.json`
with no shell or extra flags. The request seals the plan digest, case (including
seed and target quant), prompt text, every shared setting, entire runtime
configuration and the trace semantics. The native producer must consume these
settings and echo the exact request in `trace.request`. Successful trace fields:

```json
{"request": {}, "status": "ok", "spec_type": "draft-dflash", "blocks": [
  {"block": 0, "draft_tokens": [1], "accepted": 1, "logits": [
    {"verify_prefix": [2], "serial_prefix": [2],
     "verify": [0.0, 2.0, 1.0], "serial": [0.0, 1.5, 1.0]},
    {"verify_prefix": [2, 1], "serial_prefix": [2, 1],
     "verify": [2.0, 0.0, 1.0], "serial": [2.0, 0.0, 1.0]}
  ]}
]}
```

The empty request above is illustrative; actual execution requires the entire
exact request. This first version supports greedy `temperature=0, top_k=1` only.
There are `len(draft_tokens)+1` full-vocabulary logit rows per block, including
the bonus. Serial and verify logits must be evaluated on the identical explicit
prefix, including rejected draft continuations; they are not separate generated
answers. Prefixes advance through each draft and across accepted block/bonus
continuations. The worker checks the accepted greedy prefix against verify
argmax, accumulates actual per-position drafted denominators across variable
widths, and derives max absolute and RMS logit differences (lower is better).
It refuses missing, nonfinite, contradictory or mismatched traces. Argmax ties
use the lowest token ID; a producer with different tie semantics must abstain.

Native `failed`, `invalid` and `abstained` statuses require a reason and never
receive imputed acceptance counts. Nonzero exits and timeouts fail; malformed
or missing traces are invalid. Requests, stdout/stderr and any trace bytes,
including malformed output, are retained beneath `CELL.raw.native/`, and their
identities enter the replayed closure. All bounded declaration reads currently
have a 16 MiB limit: the full-logit protocol is suitable only for bounded probe
cells, not an unbounded completion dump. A compact/streamed C++ producer is a
necessary follow-up before sizing or publishing a real matrix. No numerical
floor adequacy or precision-causal conclusion follows from this software.

Optional prospective `measurement_labels` supplies `id_prefix`, `date`,
`category` and `claim`. At finalize the producer records one descriptive
successful-cell weighted acceptance metric per quant, with higher-is-better
semantics and separate accepted/drafted counts. An artifact/protocol digest is
not a ratified protocol ID. There is no inferred repetition count.

`scripts/vidya/adapters/target_precision.py:native_rows(final_path)` discovers
only these recorded metrics. `project(row)` reopens the plan, opening, cells,
raw output and logs, replays the entire closure and requires the discovery-time
closure digest. Missing/tampered originals, substituted metric IDs and caller
supplied values refuse projection. Synthetic origin or absent native labels
emits zero rows. Native-claimed labels yield observations via the existing
`ClaimTuple` measurement ladder with no protocol ID, not causal/gating evidence.
No claim is made that a native-claimed origin proves execution or residency.

## Native producer profile

`native.cpp` consumes the worker request directly. It loads the declared target
and DFlash drafter, calls `common_speculative_process` on each physical prefill
ubatch, calls the real `common_speculative_draft`, and verifies `[last, draft...]`
in one target ubatch. Each block starts from fresh target/drafter contexts and
the full accepted token prefix. This avoids relying on unqualified hybrid
partial rollback. It is deliberately expensive and provides no throughput data.
The serial reference starts fresh and decodes the identical prefix and every
draft continuation one token at a time, including rejected draft positions.
This replay/shape difference must be included in numerical-floor controls.
No EOS stop is applied: the declared fixed block count is the diagnostic extent.

Its exact verification object is:

```json
{"mode":"block", "replay":"fresh-block-serial-v1", "kv_type":"f16",
 "context":4096, "batch":512, "ubatch":512, "draft_max":7, "blocks":8,
 "threads":4, "flash_attention":"on"}
```

Unknown/missing keys, non-greedy sampling, invalid seeds, non-f16 KV, widths
above 16, more than 16 blocks, context above 8192, or a verify block larger than
its ubatch refuse execution. The backend selects 0 (CPU) or 99 (HIP) GPU layers
for both models; actual device residency still requires the row's runtime
proof. Target/drafter identities and library/source digests remain admission
obligations; no weight hashing or acquisition happens in the executable.

The trace declares `numerical_encoding=full-vocabulary-moments-v1`. Every row
retains both explicit prefixes and `witness={count,verify_argmax,max_abs,sum_squared}`,
computed from every coordinate of the actual paired float logit vectors in
`native_witness.h`. Argmax uses lowest token ID on ties. The worker validates
moment bounds, vocabulary stability, prefix continuation and acceptance, then
combines sums and coordinate counts for weighted RMS. Full vectors are not
retained in this encoding, so coordinate-level reanalysis is unavailable;
original compact traces, producer source/binary identities and logs are retained.
The old full-logit protocol is still supported; mixed/unknown encodings refuse.
The producer refuses output over 16 MiB and never overwrites an existing trace.

Build against a **fresh detached experimental checkout** of production
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, never inside the frozen tree. For the
model-free build test, use its headers and link the approved v10 CPU kernel-store
libraries (the `cpu` symlink already points to `bin`, so do not append `/bin`):

```bash
g++ -std=c++17 -O1 -Wall -Wextra -Werror \
  -I "$PRECISION_SOURCE/common" -I "$PRECISION_SOURCE/include" \
  -I "$PRECISION_SOURCE/ggml/include" -I "$PRECISION_SOURCE/vendor/nlohmann" \
  scripts/diagnostics/target-precision/native.cpp \
  -L /mnt/raid0/llm/kernels/production/cpu \
  -Wl,-rpath,/mnt/raid0/llm/kernels/production/cpu \
  -lllama-common -lllama -lggml -lggml-base -pthread -o "$PRECISION_OUTPUT"
```

Set the executable's own `LD_LIBRARY_PATH`; a HIP run needs its separately
admitted matching HIP build. A successful CPU link does not qualify HIP.
`EPYC_PRECISION_SOURCE`, `EPYC_PRECISION_EXECUTABLE` and
`EPYC_PRECISION_LIBRARIES` enable the optional real-header and real-executable
tests in `test_native.py`. Those tests compile/run the actual C++ numerical
reducer and refuse unsupported requests **before loading any model**. No model
execution, native acceptance measurement, matrix qualification or causal result
is implied. Run the actual admitted matrix only through a published compute row.


## Native matrix admission

`admission.py` is called before the runner creates an output directory, again
on the sealed plan, and by the per-cell worker before any native subprocess.
Synthetic process fixtures remain model-free. `native_claimed` execution now
requires `plan.admission`: four `{path, sha256}` references to prepared, small
JSON receipts (`weights`, `build`, `floor`, `holdout`) plus `runtime_proof`.
Receipt schemas are `epyc.target-precision.<name>.v1`; paths are absolute.
These reads never hash or open model weights. Prepare evidence before publishing.
The native opening also binds the admission implementation digest, and closure
replay rechecks all receipt and original-floor-output digests.

The weights receipt declares a pinned `base={repo, revision}` (40 hex commit),
`targets` keyed by quant with artifact `path`, `sha256`, identical `base`,
`tensor_correspondence="verified"`, `conversion_sha256` and `catalog_sha256`.
`drafter` binds its path/digest, identical `target_base` and BF16 `training_dtype`.
Paths must match `native_worker`. Exactly one BF16/F16 arm, Q8_0 and Q4_K_M are
required, with identical prompt/seed/repetition coverage and one complete matched
group per consecutive three cells. Each quant uses one artifact throughout.

The build receipt binds backend, executable, source and library-map digests,
`source_commit`, absolute library paths/digests and the child's `ld_library_path`.
`libraries_sha256` is the SHA-256 of the sorted compact JSON `libraries` map.
The holdout receipt binds the prompt/protocol digests and disjoint `evaluation`
and `calibration` lists of `[prompt_id, seed]`; evaluation exactly covers cells,
and its receipt digest equals `holdout_sha256`. Independence remains a scientific
obligation; a declaration cannot establish that prompts were never inspected.

The floor receipt binds backend, binary/source/libraries/drafter, verification
and sampling. For each quant it retains the exact target digest, comparison
`fresh-block-vs-serial-same-prefix`, at least two repetitions, positive logit
coordinate count, finite `max_abs`/`rms` (lower is better) bounded by the declared
`numerical_floor`, and `native_output={path,sha256}`. That original JSON must
match the control fields exactly. Verification must declare
`replay="fresh-block-serial-v1"`. Missing/failed controls refuse matrix execution;
this gate does not run controls or fabricate their evidence.

`runtime_proof` declares `sampling_window="during-each-cell"`, `own_pid=true`
and `mapped_library_sha256` equal to the build map. HIP also requires
`kfd_process=true` and `nonzero_vram=true`. This is a **proof plan**, not a
collector or a passing runtime proof. Actual admitted row execution still must
collect those observations during each cell, qualify resource/disk admission
and establish source/build provenance. A consistent receipt can contain false
declarations; admission is a refusal gate, never independent verification of
weight equivalence, control execution, residency or a precision cause.

`test_admission.py:make_panel` supplies a complete model-free receipt example.
Run `python3 -m pytest -q scripts/diagnostics/target-precision/` for refusal,
closure/projection and native-producer tests; optional real-header/executable
tests require the environment described above. No model smoke is implied.
