# DTREE-P2 27B oracle futility verdict (2026-11-19)

Row `ak-dtree-27b-gpu-20261119` completed rc0 and is filed **FAIL** under
pre-data Amendment 1: native `FUTILITY_ORACLE`, not a qualified candidate.
At pair 0, fixed T9 disagreed with its fresh-prefill oracle at 9/48 positions
(18.75%), with maximum reported margin 2.752221904695034 nat > 0.5.
L, auto A and T13 each disagreed at 0/48 sampled positions. This triggers the
registered immediate margin futility rule; the rate rule requiring three pairs
is not used. Lower oracle disagreement is better; higher tokens/s is better.
The oracle is sampled at 16 positions per prompt, not exhaustive token proof.

| Arm | Tokens/s | Ratio to same-pair L | Oracle disagreements |
|---|---:|---:|---:|
| L | 85.1106 | 1 | 0/48 |
| A (auto) | 68.6054 | 0.806074 | 0/48 |
| T9 | 48.3413 | 0.567982 | 9/48 |
| T13 | 49.7936 | 0.585046 | 0/48 |

Only one pair completed: no speed CI or beyond-noise conclusion is available.
Greedy content identity vs L is recorded, not gated under Amendment 1:
A matches 2/3 prompts, T9 0/3, T13 2/3. Both captured residency samples for
each arm report local HIP/library mappings and nonzero owned VRAM
(~36.6 GB L; ~37.7 GB tree arms). This does not assert continuous per-request
residency or diagnose the cause of the oracle disagreement.

The candidate record names commit `70f7d1c09` and C14 store baseline
`gpu-20261118-eee3da838-c14`; the original source manifest and producer are
hash-bound below. No production default is changed. DTREE-P2 stays open for
its separately scheduled A3B twin. P3-P5 are not stopped by this path-row result.
No replacement 27B run is justified by this completed futility answer alone.

The separate CAFE-3 HIP P9 smoke failed despite CLI rc0 because it deliberately
hid devices and loaded no models; the publisher found no VRAM residency.
This is a smoke qualification failure, not a P9 performance result. Next task:
replace the CLI-only smoke with bounded native HIP work and overlapping owned
residency capture, honoring allocated smoke CPUs, then reseal and republish.

The result conclusion is recorded as committed-conclusion observation only;
no historical measurement warrant is invented. Prospective source projection
is tracked under VB-DTREE-P2-WIRE with the shared grading contract.

## Original evidence SHA-256

- `/mnt/raid0/llm/tmp/ak-dtree-27b-gpu-20261119/out/RESULT.json`: `7acadc2abfeefde8ca5e438f06fb75f9ad7e70f7afb0e5687c8508a1415bf4c3`
- `/mnt/raid0/llm/tmp/ak-dtree-27b-gpu-20261119/out/results.jsonl`: `4fe32b3863c9158b19bd53c9bd14c616fe70e25b41344a3e6adc04bd551760ec`
- `/mnt/raid0/llm/tmp/ak-dtree-27b-gpu-20261119/job.py`: `9f10246c7e7b16ab53beb194dc45c4befbb4c81f074e9fc1896df4b7b09b1fba`
- `/mnt/raid0/llm/tmp/ak-dtree-27b-gpu-20261119/SOURCE.sha256`: `324861f3c05b69fa068cd4c0d1320fa1b3e2d62b50aa84d99188f594d51f4a2e`
- `/mnt/raid0/llm/tmp/ak-dtree-27b-gpu-20261119/spec.json`: `65555dec8ee09a57a3c7d2c7a1aa7f186824a417b56da730d2c8e234942dfba8`
- `/mnt/raid0/llm/tmp/ak-dtree-27b-gpu-20261119/launch.sh`: `3f2d6f0429e8e8e51e66f5f61bbbf23df1840f1d983a59ee5b34c36e6dc45858`
- `/mnt/raid0/llm/tmp/compute-flags/ready/ak-dtree-27b-gpu-20261119.json`: `bd6cf63188a23486808c3d836a55d20ded67297f5ab8fba7e9040ad7d673e6d7`
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-hip-20261119/FAIL-1.json`: `93d76a7a2f654bcf4ff2b9421512bd57b5644a820b639d9610d7a0a5e906c0bc`
