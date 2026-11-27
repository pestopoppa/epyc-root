# Canonical Taskflow checker validation

The canonical TU and MM checker changes passed all 47 focused and verification
integration tests in 17.61 seconds. The existing test process exited 0.
`git diff --check` also exited 0.

Run from the owning worktree at
`/mnt/raid0/llm/tmp/ws58-a3b-finish-20261126`:

```bash
taskset -c 180-183 /usr/bin/python3 -B -m pytest -q -p no:cacheprovider \
  tests/coordination/test_taskflow_tu_grader_isolation.py \
  tests/coordination/test_taskflow_vision_contract.py \
  tests/coordination/test_taskflow_calibration_scope.py \
  tests/coordination/test_taskflow_r8g_harness_fixes.py
```

The receipt records exec session `92982`, its original output chunks
`cc4845`, `cabd8a`, and `2b9ef1`, the exact test argument vector and the
four tested file hashes. The stdout copy joins the two progress chunks from
that session. The hashes were rechecked when archiving. [Receipt](RECEIPT.json) · [Captured stdout](STDOUT.txt)

The TU projection includes exact source-file matching for class-based JUnit
reports and the qualified launcher and denial checks. Its restricted
missing-launcher path preserves the configured acceptance runner. The MM
projection includes positive-cap unchanged image bytes, feasible aspect and
orientation, and startup environment configuration through a fresh process
and the existing request/recorder checks. Infeasible-cap robustness remains
a separate result from the original-scope MM checks.

The test process used local fixtures, with no native inference or paid model
calls. Archiving reused that completed run.

Next: Main integrates the source and cites this receipt in the canary report.
