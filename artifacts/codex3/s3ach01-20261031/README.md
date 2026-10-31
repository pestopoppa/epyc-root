# S3-ACH-01 spike verification

Fresh ROOT base `8a24905c3c93bc59c7de305851f686f8a15ea4e0`; this is a source-only, default-off prototype. No live actor, setting, hook, model, build, benchmark, GPU or inference was enabled or launched. Simulated host fixture tests are not a Claude session.

Before the input fix, the isolated hook was given 20,000 opening brackets, `0`, and 20,000 closing brackets. `raw-deep-input-before.rc`, `.stdout` and `.stderr` preserve the actual result (exit 1 and RecursionError). The focused suite includes this nested payload and a payload over 65,536 bytes; both now emit `ask` with exit 0.

`test-run.txt` is the focused suite and supervisor's raw output. It ran 2026-10-31 under the 30-31 mutex on admitted relocated sibling CPUs 126,127, OMP_NUM_THREADS=1; process tree RSS is sampled, not a hard peak. It covers native JSON requests, the fixed-operand actor-seat subprocess, unknown actions, configuration shape, and simulated host blocking of failure/unavailability/timeout/invalid JSON. The host contract requires the documented Claude version, registration and human approval flow; it has not been validated in a live Claude session.
