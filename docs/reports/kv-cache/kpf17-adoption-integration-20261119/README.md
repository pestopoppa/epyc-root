# KPF-17 captured debugger and adopted-inferior cleanup integration

The prospective oracle supervisor now verifies exclusive single-threaded subreaper ownership before spawning GDB. After stopping and reaping only the captured debugger, it discovers newly adopted direct children from its own kernel child table, captures PID/birth and pidfd before signals, drains them with bounded TERM/KILL and waitpid reaping, and requires ps/proc absence. Cleanup runs on normal exit, STOP/deadline and supervisor callback exceptions, including a failure writing the debugger PID receipt. Pre-existing children refuse the adoption scope. Cleanup failure raises before result publication; any adopted child invalidates the oracle verdict. Completion validation requires the adoption proof. The source is prospective: retained packets are unchanged.

All **20 scoped unittest methods PASS**, including four isolated actual-GDB scenarios: normal `/usr/bin/true` exit, nonzero `/usr/bin/false` exit, STOP after starti before any inferior identity receipt, and a supervisor callback exception at that same point. The interrupted controls stop only captured GDB to force its bounded TERM/KILL escalation, then verify inferior adoption, PID/birth-bound cleanup, reaping and no remaining children. Normal and exit-1 cases record post-continue inferior PID zero and leave no adopted children. Additional refusal controls cover pre-existing children and a failed adoption drain. Existing PID-reuse, shutdown and witness tests remain green. One initial nonzero fixture using Python `-c` failed because GDB argument quoting changed the command; the final fixture uses `/usr/bin/false` and expects exactly 1.

Reproduce from the lane: `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s scripts/coordination/kvfork/kpf17-oracle-test -p 'test_*.py' -v`. Runtime about two seconds; these are software regression fixtures, no model or benchmark. Scratch is isolated under `/mnt/raid0/llm/tmp/kvu` and removed by the tests. `git diff --check` passes.

GitNexus status and upstream impact for `stop_debugger` were requested and refused because the lane has no index; no graph risk rating is claimed. Manual callers are prospective `gdb_job.main`, the new supervisor helpers and tests; `prepare.py` copies these modules only when preparing another packet. The native main and completion predicate were inspected together. No production kernel, scheduler, grants or retained packet changed.

Limits: actual GDB regression coverage is not qualification of a separately sealed successor, model/library custody, multilevel escaping descendants or the native Test 6 oracle. KPF-17 remains open. Next prepare a separately sealed successor carrying this integration and qualify its lifecycle before native oracle publication.

Source SHA-256 (existing files, no copied evidence):

- `scripts/coordination/kvfork/kpf17-oracle-test/cleanup.py`: `2823c85d41b3de874c637d4fe51a60ea4848ef74a84b2437788299915506b78a`
- `scripts/coordination/kvfork/kpf17-oracle-test/gdb_job.py`: `d2e19bbbab48c3bc06cdaa7fc7738cfbe104626cb6adaf27003db08946e11dfb`
- `scripts/coordination/kvfork/kpf17-oracle-test/complete.py`: `7ba818cdb8fa1aa3bc58d3beb16c1953000799f39ee4e8b99e28dd90a890eaca`
- `scripts/coordination/kvfork/kpf17-oracle-test/test_adoption.py`: `38370cb1fdc3c22feec72446c9a93f62b8ee7c11d90860e6bd08afa1bf13fb49`
- Host `/usr/bin/gdb` used by short fixtures: `3832cc070ae1716e322105d3b39fb398695e5f031c9d39224cf227a8c2b889f6`
