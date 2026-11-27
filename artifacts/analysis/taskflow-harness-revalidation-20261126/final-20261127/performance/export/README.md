# Closed canary performance export

REQUESTS.csv contains one row per unique request receipt, including stream/slot, latency, queue, upstream and delivered streaming TTFT, native prefill/decode, cache and MTP fields, failure details, role observations and source hashes. TASKS.csv retains task windows, metrics and shared resource summaries. SUMMARY.json records the aggregate and its scope.

- This exports existing closed receipts, not a new experiment or hardware benchmark.
- Blank CSV values are unknown, not zero. Native reasoning-only counts are unavailable.
- TTFT applies to streaming deltas; response completion is not first-token timing.
- Native phase union rates are estimates from right-aligned intervals.
- Resources are shared-host observations, not per-task attribution; repeated windows are references.
- Standalone source review of superseded intermediate artifacts is not pending dispatch work.
- Accepted artifact variants are not unique tasks or an estimated model success rate.

Next: owning main publishes these exports with the task/paid-cost report.
