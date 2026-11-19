# KPF-18 R9 SSE and rowflow STOP composition

The isolated model-free fixture passed 2/2 tests; the packaged portable copy also passed 2/2 tests on 2026-11-04. It composes the actual R9 `cancel_seed_stream.capture` with a scratch rowflow boundary wrapper: STOP between two native SSE events prevents retaining the second event, propagates terminal refusal, and closes the caller-owned transport. A permitted capture reaches the exact pre-cancel progress trigger and still reports `native_cancel_accepted=false`. The copied modules and test are sealed evidence, with imports made relative to this directory for portability.

This fixture does not instantiate SeedControl, use actual HTTP, prove provider rechecks, prove native cancellation or release, qualify admission, run a model, or clear the DRAFT/HOLD barriers. The full SeedControl / provider / rowflow integration remains open.

Run model-free: `python3 -B -I docs/reports/kv-cache/kpf18-r9-sse-boundary-20261104/test_transport_boundary.py`.

The copied R9 `cancel_seed_stream.py` SHA-256 is `d9ae491aea9ef6f80fe60af855b5c48cb9a25c333ab726aeafc31029b2e301bf`, matching the reviewed candidate. The test changes only its import paths from the original isolated fixture.
