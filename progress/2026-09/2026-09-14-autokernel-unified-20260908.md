# AutoKernel unified — 2026-09-14

## GLM-5.3-Flash continuous 50-loop acceptance

Completed the operator-requested health proof for the existing GLM-5.3-Flash CPU AutoKernel.
The acceptance required an observed CPU profile, a real measured candidate path, continuous
automatic operation, and 50 monitored terminal loops with halt/fix/relaunch on genuine faults.

### Result

- Terminal continuations: **50/50**, composed from retained continuous states v2/v3/v4/v7 as
  `2 + 20 + 3 + 25`. Aggregate outcomes are `42 measured_null` and `8 kept`.
- Ordered continuation-digest-list SHA-256:
  `b89c41aa4b2d68be096671d6962f37a200f7990bf193c6dd292005398b7e7ff6`.
- Final loop: v7 `batch-000024`, terminal `complete`, one `kept` outcome. Continuation SHA-256:
  `41da2b2c8c493ebed97844e3840793067d0d233fac835e95683d6f06531d0c7e`.
- Final mechanism: `akm-q4k-pairrow-zmm-accumulate`, marginal matched A/B `+0.182%` over five
  pairs. Clean-built anchor `dc3798db10a6654721f2a1fa6a162be2e5fdf95f` passed its five-pair
  A/A guard at `+0.0773869451%` drift.
- Accumulator: 23 keeps, tip `dc3798db10a6`, direct current-snapshot effect
  **+0.8303809823155373%** versus champion-of-record `c463f601bd39`. Accumulator bundle SHA-256:
  `e3df3b43bad0afdc75aad5cd3ad9d09d64e12985671c11e90c649c99c23445b5`.
- Final post-keep original-request CPU profile completed with the actual serving process and
  simultaneous `perf` capture. Receipt SHA-256:
  `b67e9b4a254eb8ac00decd8ea3d2bf0867f286f61c1423dbbf9c5f96ade9b950`.
- Loop 49's cadence gate directly measured the prior 22-keep stack at `+0.5400504842%` on the
  bench comparison and `+0.3349231781%` on the serving surface. The serving effect was not
  decisive, so it was retained as a surface divergence rather than promoted.

### Runtime disposition

The continuous supervisor automatically launched v7 batch 25 after the 50th completion,
demonstrating boundary-to-boundary continuation. The exact supervisor and post-boundary child
PIDs were stopped at the requested monitoring boundary; the supervisor wrote its `STOP` sentinel
and `stop_requested: true`. Batch 25 has no terminal continuation and is excluded from the
50-loop result. No broad PID matching was used. No production kernel was modified or promoted.

### Authoritative paths

- Store: `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-store`
- Supervisor: `/mnt/raid0/llm/tmp/aku-glm53-continuous-20260912-v7`
- Final continuation:
  `/mnt/raid0/llm/tmp/aku-glm53-continuous-20260912-v7/batches/batch-000024/loop-continuation.json`
- Experimental source: `/mnt/raid0/llm/tmp/glm53-recovered-accumulator-20260912`
