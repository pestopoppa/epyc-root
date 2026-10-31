Task: Deterministic FIFO-off control (autokernel-unified-surface-program.md)
Fresh root origin/main 68a4d5e9f: original box unchecked.
Fresh APP origin/main 782c27f65: test source identical to 56fabf52^.
Patch: fifo-controls.patch, historical prepared 56fabf52, not previously on main.
Scope: tests/unit/test_lock_fifo_queue.py only; production code/default unchanged.
GitNexus: test_no_barging_by_rerequesting_releaser upstream impact LOW, 0 callers; registry stale; current source inspected.
Native runtime source on APP lane equals origin/main for cpu_region_lock.py and lock_queue.py.
Mechanism: multiprocessing Event waits intercept only time.sleep after actual failed native occupancy/flock attempt; older waiter keeps its real ticket. Initial holder cannot release before park witness. Younger re-request must reach native queued admission (FIFO ON) or actual acquire (OFF) before parked waiter resumes. No sleeps choose the ordering; deadlines bound harness failures.
Assertions: all children complete, each acquires/releases once, no residual tickets, precise opposite on/off order. No xfail markers remain.
Validation: full-suite.log 24 passed in 7.49s. old-fairness-negative.log restores original fairness property on FIFO OFF: exactly 3 AssertionError failures after harness/deadlock checks; actual ordering demonstrates barging. Probe is scratch-only.
Owner applies original checkbox only after accepted code main SHA, test/artifact evidence and belief marker. No new boxes; no default ON claim.
