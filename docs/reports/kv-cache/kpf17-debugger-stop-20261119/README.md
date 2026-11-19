# KPF-17 captured debugger shutdown

The prospective `scripts/coordination/kvfork/kpf17-oracle-test/gdb_job.py` used process-group TERM/KILL and an unbounded wait after KILL. Its STOP/deadline and finalizer paths now call `stop_debugger`, which signals only the captured Popen child, bounds both waits, and requires absent-by-ps-and-proc verification. A failed KILL/reap or absence proof raises rather than publishing completion. Inferior cleanup remains separately governed by its captured PID/birth witness; this change does not prove descendant adoption or native oracle safety.

All 17 scoped tests PASS, including five new shutdown tests. Real own-child fixtures cover TERM/reap and TERM-ignore KILL/reap, plus refusal of failed absence proof and no signal after reaping. A synthetic unkillable child proves both waits are bounded and final timeout propagates. No model, GDB or GPU was run. Existing retained packets and historical results are unchanged.

Reproduce: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/coordination/kvfork/kpf17-oracle-test -p 'test_*.py' -v`. `git diff --check` passes.

Source SHA-256:

- `scripts/coordination/kvfork/kpf17-oracle-test/gdb_job.py`: `dcb3c3048fa3800a3a1c55aa4178c102206fec0ebe3345d47dd6988cdb1263f6`
- `scripts/coordination/kvfork/kpf17-oracle-test/test_debugger_stop.py`: `f6964c388c69620e42e0241bbd80e97772d2009d6c703090e3362a01ed87c321`

GitNexus status and upstream impact were requested but refused because this lane has no index. No graph risk rating is claimed. Static callers are the prospective runner main and new tests; prepare.py copies this source only into a newly prepared packet. A separately sealed successor must qualify actual GDB/inferior lifecycle before native publication. KPF-17 remains open.
