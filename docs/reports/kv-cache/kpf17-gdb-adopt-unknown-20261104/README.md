KPF-17 GDB fork-before-starti-receipt regression — 2026-11-04

Result: PASS, 4/4 model-free own-child tests.
Command: `PYTHONDONTWRITEBYTECODE=1 python3 -B test_regression.py`

Files:
- `test_regression.py` — four paths: (1) GDB starti pause, STOP, captured-GDB PIDFD escalation, inferior adoption, PID/birth/PIDFD cleanup and reaping; (2) repeat the same pre-receipt pause but deliberately retain no inferior PID, birth or pidfd before GDB termination, then enumerate the subreaper's newly adopted direct children and capture each PID/birth/pidfd before signaling; (3) a pre-existing STOP takes the modeled pre-spawn refusal branch without starting GDB; (4) normal GDB exit writes the receipt before the fixture writes COMPLETE and leaves no child.
- `gdb_hook.py` — pauses the harmless `/usr/bin/sleep` or `/usr/bin/true` inferior after GDB `starti` and before the receipt command.
- `gdb.log`, `held-before-receipt.json`, `STOP`, `release`, `pidfile`, and `receipt.json` are local test artifacts. Interrupted cases create no `COMPLETE`; normal case creates it only after GDB rc=0 and receipt existence.

The no-prior-identity test does not inspect or retain the inferior PID/birth/pidfd before killing captured GDB. After GDB is reaped, it discovers the adopted child from the subreaper's direct-child list, captures identity and pidfd, then signals and reaps that exact identity. All cleanup is bounded and the tests assert no children remain.

Limits: the STOP-before-fork case validates only the preflight branch modeled in this fixture, not the production launcher. GDB tests use this host's GDB 16.3 and harmless system binaries. They do not prove behavior for every GDB/kernel version, multilevel escaping descendants, real oracle build, or the production packet. No model/inference, benchmark, gate or rowflow edit, grant, or publication occurred.

Preserved test SHA-256: `cba7eeabe6047b9081c2dda3b6de7364f43a1cceb6c9bcec454cf29feaddccac`; GDB hook SHA-256: `c667d18a13a5c045a740a582186cbccb47203f0c150158bb60143cff6ee8eb38`.
