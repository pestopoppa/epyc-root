# Persistent C22 queue admission

The watcher supports the exact qualified TU thinking and W66 light-v2 plans. It validates their current owner, source seals and approved plan hashes. TU waits for PAW's GPU slot 0 terminal receipt. W66 waits for TU paid on slot 1 and MM OFF on slot 2, without waiting for the unrelated GPU slot 3 or the whole callback batch. It then verifies each private slot lock is free and checks the native GPU reports each slot idle.

Use the exact main-supplied approval JSON and its SHA-256. The watcher approval schema has four fields: `approved_by`, `runner_seal_sha256`, `plan` and `plan_sha256`. The accepted value for `approved_by` is `main`. The sealed plans and allowed commands are fixed by the queue name.

```text
/usr/bin/python3 -B -u watch.py tu-on --seal WATCHER_SHA --approval ABS_TU_APPROVAL --approval-sha256 TU_APPROVAL_SHA --audit ABS_WATCHER_RUN
/usr/bin/python3 -B -u watch.py w66 --seal WATCHER_SHA --approval ABS_W66_APPROVAL --approval-sha256 W66_APPROVAL_SHA --audit ABS_WATCHER_RUN
```

Use a new private audit directory beneath `runs/`. The launcher writes the waiting decision, exact predecessor digests and idle checks, followed immediately by the captured callback PID and exact argv. It records terminal status. Its lock prevents a duplicate watcher. On owner loss it refuses new work and interrupts only its own already-started callback, which supervises its workers and containers.

`--probe` checks the live route with no launch, approval file or watcher audit required. The model-free control verified exact prior receipts, the native readiness path, and rejection of a changed approval digest, stale owner birth and busy slot lock.
