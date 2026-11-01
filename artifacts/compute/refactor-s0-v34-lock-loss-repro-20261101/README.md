# S0 v34 lock-loss reproducer

This reproduces the v33 `/proc/locks` false refusal while keeping the canonical region-lock process alive. Under a real q3 `build` region claim, a sibling process churns 192 private `flock` files while the unchanged v33 `capture()` + `verify()` predicate repeatedly scans `/proc/locks`. At a transient scan gap, v33 raises `RuntimeError: lock lost`; the same observation records both exclusive locks still present in the owner process's `/proc/<pid>/fdinfo` rows. The v34 owner-FD witness continues to see the locks.

The run is a lock-custody reproducer only: it launches no model, server, benchmark, or GPU work. `run-20261101T0915Z/launcher.log` records the real q3 region claim and successful exit; `run-20261101T0915Z/RESULT.json` records the `lock lost` refusal and owner-FD evidence. `test_result.py` checks the committed result capsule.

Reproduce from `/mnt/raid0/llm/epyc-orchestrator`:

```bash
ART=/mnt/raid0/llm/worktrees/mains/codex-refactor-01a16fc3/artifacts/compute/refactor-s0-v34-lock-loss-repro-20261101
FILLER_CPUS=72-95 ORCHESTRATOR_TMP_DIR="$ART/private-locks" \
  /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python3 -m src.runtime.region_lock_cli run \
  --cpu-list 72-95 --role build --timeout-s 120 \
  --tag refactor-s0-v34-lock-loss-repro-20261101 -- \
  /usr/bin/python3 -B "$ART/old_global_probe.py" "$ART/private-locks" "$ART/run-new"
```

The v33 and v34 witness modules are retained verbatim from the S0 continuation packet. Their source identities are pinned in `SHA256SUMS`; the canonical transport identity is pinned in `source-proposal/R13-IDENTITY.json`. A reproduction may need multiple attempts because the legacy `/proc/locks` race is timing-dependent. The captured 2026-11-01 run hit it after 30 iterations.
