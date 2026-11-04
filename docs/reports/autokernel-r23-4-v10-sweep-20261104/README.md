# R23-4 v10 one-factor sweep

Outcome: **INCONCLUSIVE**. The completed v10 diagnostic has 63/63 unique requests (seven launches, three prompts and three repetitions). Every treatment’s per-prompt repetition range overlaps its adjacent baseline observations for both streaming-event rate and acceptance. Median differences do not establish factor attribution.

Native run: `72065c56a0e247b89c884001e3f88ae5`; keeper completion `2026-11-02T23:58:26Z`, rc=0. The two baseline rows from the earlier partial run are retained in the native file and excluded from the summary.

| Launch | Prompt 0: events/s / acceptance | Prompt 1 | Prompt 2 |
|---|---:|---:|---:|
| 0 baseline | 89.687 / 0.83810 | 40.365 / 0.29714 | 61.444 / 0.53151 |
| 1 context | 92.209 / 0.86589 | 38.234 / 0.26531 | 59.272 / 0.50411 |
| 2 baseline | 92.325 / 0.86243 | 37.545 / 0.27013 | 62.162 / 0.53229 |
| 3 kv | 92.540 / 0.87143 | 40.443 / 0.29286 | 61.203 / 0.51741 |
| 4 baseline | 88.481 / 0.82799 | 36.730 / 0.24947 | 60.738 / 0.51575 |
| 5 affinity | 86.792 / 0.83598 | 37.140 / 0.25862 | 61.216 / 0.52613 |
| 6 baseline | 85.102 / 0.79419 | 36.959 / 0.25549 | 68.066 / 0.59851 |

The native rows record the expected mapped HIP path, input packet and own-PID in-window residency. Exact persisted log windows reproduce the acceptance counts. `summary.json` retains the 18 range comparisons; original request rows and seven server logs are adjacent.

Scope: frozen v10 `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`; this does not resolve historical `9e18beb0` causal attribution. The client metric counts streaming events, and acceptance uses a unique synchronous single-slot log window rather than a response task ID. No cross-instrument conversion, performance improvement, calibrated causal claim or historical measurement warrant follows.

Belief capture remains prospective under `VB-AK-R23-4-SWEEP-WIRE`; this report records a committed conclusion, not retroactive native claim attestation.
