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
No native DFlash worker is bundled or claimed integrated by these fixture tests.

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
