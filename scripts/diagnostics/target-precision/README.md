# Prospective target-precision native capture

`capture.py` binds producer-authored native fields for the existing missing-control
box in `handoffs/active/speculative-decoding.md`. The existing research
`dflash2_beliefs.py` concurrency-grid carrier has a fixed different protocol and
is left unchanged. Stable bounded reads reuse
`scripts/vidya/qwen4exp_quality_capture.py:stable_bytes_identity`.

A future admitted matrix runner must call `open_capture(plan_path, opened_path)`
**before** any cells execute, then `finalize_precision(opened_path, cell_paths,
output_path)` at its native finalize boundary. Both writes are exclusive and
fsynced. This is a callable producer contract; the matrix runner is not integrated.
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
It always emits `causal_gate=UNRESOLVED` and `projection_ready=false`.
Native runner integration and strict projection/canary through the existing
ClaimTuple measurement ladder remain required before decision-bearing execution.
No historical tuple reconstruction, adapter registration or grading rule is added.

Validation: `python3 -m pytest -q scripts/diagnostics/target-precision/test_capture.py`
(26 model-free tests; no inference or precision evidence).
