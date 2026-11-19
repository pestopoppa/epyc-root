# G3 independent native control execution (2026-11-19)

`native_protocol.py` adds a prospective diagnostic wrapper around the existing
content-bound native runner. It predeclares six separate process executions:
FA on, MTP off for Q8_0 and Q4_0 KV, followed by the retained four cells
(Q8_0/Q4_0 × draft maxima 1/4). Configurations retain the same requests and
runtime inputs; each execution has a distinct output directory. Ambiguous
controlled CLI options are refused. This is code for a future GPU row; it has
not run native inference or been published as a successor.

The negative-control gate parses the native trace independently. No verify
candidate is permitted, including an UNKNOWN candidate. Every request requires
a completed generated-token response, a native FA dispatch inside its window
with the configured KV type, request-scoped residency PASS, and verified drain.
Startup-only events and MTP-on prefill cannot substitute for these controls.
The executor stops after a failed control or failed native process and saves
an UNKNOWN partial endpoint. Request-window residency does not attribute the
negative-control dispatches individually.

The diagnostic fold requires both controls, all four positive cells, complete
revised dispatch coverage, consistent KV observations, and actual draft-length
strata (1 and >=2). Partial coverage or an early VEC observation cannot bypass
the controls. `dispatch_protocol=PASS` is an internal qualification result;
the final `status` remains UNKNOWN because this code does not independently
verify GPU grant ownership or GPU operating-clock stability. The sampled
realtime/monotonic offset check is not an operating-clock check. A future
successor must bind these sources and integrate those independent gates before
filing any final endpoint. Historical R4/R5 records remain unchanged and UNKNOWN.

Validation: **30 model-free tests PASS**: 11 native-protocol tests, 11 timed
analysis tests, six V5 parser tests, and two native-runner tests. The new suite
executes the real trace parser on negative fixtures, exercises six separate
mock native subprocess calls and retained endpoint output, and tests failed
controls, incomplete output/drain/residency, missing cells, partial coverage,
wrong KV, missing draft-length strata, malformed capture, and startup-only
trace refusal. No model or GPU compute ran. `git diff --check` passed.

Source identities (SHA-256):

- `native_protocol.py`: `a96e7b1fed4280f0e37c3c80ed5340aacab0cc492c1a0230de3ae7fdf4901ee9`

- `test_native_protocol.py`: `30a21bc7563b7a8bf1d3308d5ba6b79483cadc6f04d4756cd0e617ab47896019`

[no-belief: diagnostic code and model-free tests only]
