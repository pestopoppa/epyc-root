# Validation setup refusal — 2026-10-31

The first R6-gated attempt acquired the 32–33 lock, ran with affinity 128–129 and `OMP_NUM_THREADS=1`, then stopped before test collection because `/usr/bin/python3 -m pytest` returned `No module named pytest` (exit 1). Captured PID 667775, start ticks 157101436, one RSS sample 303,104 bytes, and confirmed `/proc/667775` absent after wait. No tests were collected in that attempt. The same suite then passed under the existing `/workspace/tmp/pytestenv/bin/python` while holding the same R6 lock.
