# KPF-17 mutation-oracle qualification

These are the reviewed prospective runner and model-free test sources for the
experimental candidate at `8952a0f693fb923918157eb25117641b74766230`.
The runner independently checks recorded in-test library and model mappings,
and contains a bounded subreaper drain for captured debugger descendants.
Twenty-four model-free tests passed, including actual GDB interruption before
the inferior receipt, nested descendants, PID reuse, an injected pidfd-open
failure, and rejection of tampered custody. This is software qualification;
it does not establish a native model result or the KPF-17 mutation verdict.

The native row is `kvfork17-oracle-test-r2-20261104`. Its publisher smoke was
submitted after sealing the runner. Publication and the eventual native result
are separate events and require their own receipts.
