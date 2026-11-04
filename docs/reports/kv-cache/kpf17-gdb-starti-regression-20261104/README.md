KPF-17 GDB fork-before-starti-receipt regression — 2026-11-04

Result: PASS, 1/1 model-free own-child regression.
Command: `PYTHONDONTWRITEBYTECODE=1 python3 -B test_regression.py`

Files in this isolated directory:
- `test_regression.py` — sets and verifies `PR_SET_CHILD_SUBREAPER`; starts GDB with harmless `/usr/bin/sleep 30`; waits until `starti` has stopped and the test hook holds GDB immediately before the PID/birth receipt command; confirms the inferior is a GDB child and captures its birth ticks plus pidfd; injects STOP; stops then SIGKILLs only the captured GDB PID via pidfd; verifies the inferior is adopted by the subreaper with the same birth identity; terminates it via its captured pidfd, reaps it, and checks no starti receipt, PID file or COMPLETE marker was fabricated. It verifies no direct children remain.
- `gdb_hook.py` — test-only GDB hook for the deterministic post-starti/pre-receipt pause and receipt command.
- `gdb.log`, `STOP`, `release`, and `held-before-receipt.json` — local test artifacts; no COMPLETE, receipt, or PID file exists after the expected interrupted path.

The regression uses a deliberately forced SIGKILL escalation after SIGSTOP so the child must either be reparented to the verified subreaper or fail the test. It passed: `GDB` exited/reaped, the inferior was adopted, birth matched, pidfd cleanup and wait succeeded, and no completion evidence appeared. This demonstrates the proposed custody path on this host/GDB version for this synthetic case; it does not prove all GDB versions, startup states, or arbitrary descendant behavior. Production requires the same subreaper setup before GDB spawn, initial-stop receipt validation, STOP/deadline wiring, bounded drain, and failure-to-INVALID behavior.

No model was loaded; no inference, project packet, gate, rowflow, grant, or publication was touched.

Review limitation: this fixture captures the inferior PID/birth and pidfd before stopping GDB, then verifies adoption of that identity. It does not yet exercise discovering an inferior whose identity was entirely unknown until after reparenting; that case and actual packet integration remain open.

Preserved test SHA-256: `3ae0a1f5809bb9706420d969065a0be589f6afe3f227ffec38a384b89c9ffe88`; preserved GDB hook SHA-256: `c667d18a13a5c045a740a582186cbccb47203f0c150158bb60143cff6ee8eb38`.
