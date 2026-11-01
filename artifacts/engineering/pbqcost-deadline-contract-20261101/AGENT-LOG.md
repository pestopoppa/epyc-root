Task: repair PB-QCOST launcher deadline serialization before any new compute.
Audit: wrapper parsed numeric `FILLER_DEADLINE` epoch, then generated CLI `--deadline` with `+00:00`; existing PB-HOL parser accepts Z/HH:MM only.
Fix: `ba4a037de79e282940dbdc1901646e774e9939ba` adds stdlib-only UTC-Z formatter and driver-local import path; full-entry scratch fixture uses real parser and real `Probe.run_all()` with native leaf operations controlled.
Verification: 5 passed (0.64s), CPU 34-35, OMP=1, sampled peak RSS 63,804 KiB, rc0, process drained. Six RVP WIP paths restored byte-identically after scoped stash/rebase.
Outcome: Research origin/main verified at `ba4a037de79e282940dbdc1901646e774e9939ba`. Old r2 is immutable; zero native phases/requests, no science verdict, no READY/rearm, no science checkbox tick.
