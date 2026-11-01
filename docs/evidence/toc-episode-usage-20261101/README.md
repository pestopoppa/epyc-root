# TOC episode-usage projection evidence — 2026-11-01

The prospective TOC A/B reader reopens each task's hash-pinned native trajectory segment, validates its task, event sequence, final counters and episode usage, and projects observed token costs with the shared ClaimTuple grader. Attempted and observed call counts and cache replays remain contextual fields; missing totals remain unknown. Legacy rows are not backfilled.

- ROOT adapter SHA-256: `6817b910d9e7887b20c16ff887dc93b64d4c61f2072400d45c49b21cd2f16a38`.
- ROOT `tests/vidya/test_prospective_ab_carriers.py` and `tests/vidya/test_toc_episode_usage.py`: 54 passed under the bounded R4 supervisor.
- Orchestrator producer commit `44fa7f7d61305564c9b88ae14a13d7eb93ae785b`; proof commit `73dff64ccb79518b65ce351f41291564b6c62e0f`, `docs/evidence/toc-episode-usage-20261101/canary.log`. The two source-bound canaries exercise the actual REPL executor, native UsageLedger, sidecar, strict reader and private ledger, including failed two-stage fallback; graph/backend work is simulated and no inference is run.
- The existing planning consumer cannot select these records from the producer's run/arm scope alone. No model or stack scope has been inferred. `VB-TOC-EPISODE-USAGE` remains open until a real consumer canary proves applicability.
