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
counters do not contain matched-prefix numerical controls. The C++ trace producer
is still required. No fixture test establishes native DFlash execution.

Select it with `runner.argv = ["/absolute/python", "/absolute/worker.py"]`.
`native_worker` must contain exactly `executable`, `env`, `prompt_manifest`,
`targets` (quant to absolute prepared GGUF path), `drafter` (absolute prepared
path), and positive `timeout_s`. `env` is the entire child environment and must
include its own `LD_LIBRARY_PATH`. The small JSON prompt manifest has the form
`{"prompts": {"prompt-id": "exact text"}}` and must match the shared manifest
digest. The worker checks the executable digest; it never hashes model weights.
Admission must separately bind prepared model/library identities and verify
runtime residency. A request echo alone cannot establish those facts.

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
