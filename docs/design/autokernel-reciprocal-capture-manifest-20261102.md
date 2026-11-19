# Reciprocal quantizer dispatch capture contract

This is a design for a future diagnostic capture, not an implemented collector or
runtime finding. It refines `artifacts/engineering/autokernel-quantize-reciprocal-20261102/path-witness-protocol.md`.
A successful receipt demonstrates target dispatch for one sealed recipe and build;
it does not demonstrate numerical correctness, performance, or general coverage.

## Capture receipt

The collector writes one immutable JSON receipt for one fresh trace directory:

- `schema`, `capture_id`, collector identity and version; capture start/end.
- `source`: candidate tree and diff digests, and the full build-manifest digest.
- `artifacts`: paths and SHA-256 digests for executable and actual loaded ggml/HIP
  libraries and code objects; retain the process maps and linkage check, with hashes.
- `invocation`: full executable argv, isolated environment and working directory,
  recipe digest, graph mode, model path and preverified content digest, profiler
  path, digest and version. Retain a pre-run model identity check against the
  preparation receipt; do not hash model weights in the grant.
- `process`: actual workload PID and start identity, exit status, child-process
  census, drain result and timestamped evidence tying that identity to the trace
  directory. GPU agent identifiers are not process identifiers.
- `window`: active-inference start/end, source of both boundaries, trace timestamp
  clock domain and validated mapping. Retain evidence distinguishing initialization,
  warmup and graph capture from the active region.
- `residency`: timestamped own-PID GPU residency observations with identity and
  clock mapping, including coverage of the active window and sampling gaps.
- `trace`: trace path, digest, collector exit status and custody; checker version,
  arguments, exit status, output path and digest. Preserve the raw trace and checker
  output alongside the receipt.

Bind all referenced evidence to its digest, use fresh output paths, and finalize
atomically after collection and process drain. Record failure or interruption rather
than synthesizing a successful receipt. The collector must establish provenance;
validating self-consistent JSON alone cannot authenticate process or trace custody.

## Admission and outcomes

Refuse a capture if required fields, evidence, digests, clock mapping or identities
are absent, contradictory, stale or unverifiable; if the build cannot be bound to
the approved candidate source; if actual loaded libraries cannot be bound to that
build; if process attribution is mixed or ambiguous; if the target process remains
live; or if residency evidence is absent, outside the active interval, contradictory
or has unaccounted capture gaps. Refuse a recipe mismatch, including HIP graph mode.
The old ROCm CSV has no PID column; a fresh trace folder, single workload process,
PID/start identity and process census are mandatory unless independent evidence
resolves attribution. Do not use GPU `Agent_Id` as a PID.

After these admission checks, run the existing `path_witness.py` with the sealed
active-window bounds. Its exit 0 means the exact target `quantize_q8_1(...)` was
observed fully inside the window with grid y*z > 1; exit 3 means the target was not
observed; exit 2 means invalid input. Checker exit 0 without capture admission is
not evidence. A nonzero profiler or workload status, missing raw trace, failed
checker invocation or unverifiable attribution produces an invalid/inconclusive
capture, not a no-dispatch conclusion.

Trace timestamps are diagnostic only. Performance A/B runs must be separate,
unprofiled, and use the same content-sealed release binary, loaded libraries,
model, recipe and graph mode. No diagnostic timing is eligible as a pair.
