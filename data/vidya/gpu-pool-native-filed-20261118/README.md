# SC18 GPU pool native captures and planning replay — 2026-11-18

All five rows meet the decision rules in their retained ready manifests. The original allocator terminal records report rc 0 and complete on `mi210_0,184-191`. Each existing producer's read-only `complete` command returned rc 0 against its original packet. The original sealed capture bytes match the SHA-256 in each producer result. All 12 native invocations exited rc 0 under recorded non-smoke grants with candidate and selection custody, zero strict projection refusals and at least two distinct same-PID in-window samples qualifying on KFD, positive VRAM, pinned HIP mappings and affinity.

| Official row and owner-filed verdict | Handoff box | Seed | Exact selected CPU-reference census | Tuples / refusals | Qualified residency samples |
| --- | --- | --- | --- | --- | --- |
| [attention v1](ni-gpu-pool-attention-20261117-v1/RESULT.json) — pass | SC18-GPU-POOL-ATTENTION-LIVE | 2026102603 | ROPE 328/328 passed | 1 / 0 | ROPE 579 |
| [attention v2](ni-gpu-pool-attention-20261117-v2/RESULT.json) — pass | SC18-GPU-POOL-ATTENTION-REST-LIVE | 2026102603 | SOFT_MAX 207/207 and FLASH_ATTN_EXT 528/528 passed | 2 / 0 | SOFT_MAX 94, FLASH_ATTN_EXT 249 |
| [elementwise v1](ni-gpu-pool-elementwise-20261117-v1/RESULT.json) — pass | SC18-GPU-POOL-ELEMENTWISE-LIVE | 2026102603 | 105 observed, 88 passed, 17 explicit UNSUPPORTED | 7 / 0 | 140 across seven invocations |
| [matmul v1](ni-gpu-pool-matmul-20261117-v1/RESULT.json) — pass | SC18-GPU-POOL-MATMUL-LIVE | 20261026 | MUL_MAT 201/201 passed | 1 / 0 | MUL_MAT 40 |
| [matmul v2](ni-gpu-pool-matmul-20261117-v2/RESULT.json) — pass | SC18-GPU-POOL-MATMUL-ID-LIVE | 20261026 | MUL_MAT_ID 370/370 passed in the original case multiset | 1 / 0 | MUL_MAT_ID 295 |

Every official row recorded zero failed cases. All unsupported cases came from elementwise. Its ordered partitions are below.

| Operator | Observed | Passed | Unsupported | Qualified residency samples |
| --- | ---: | ---: | ---: | ---: |
| ADD | 16 | 16 | 0 | 22 |
| MUL | 16 | 16 | 0 | 16 |
| SCALE | 4 | 4 | 0 | 22 |
| NORM | 30 | 20 | 10 | 17 |
| RMS_NORM | 21 | 21 | 0 | 24 |
| SUM | 8 | 7 | 1 | 22 |
| SUM_ROWS | 10 | 4 | 6 | 17 |

An earlier MUL_MAT_ID publisher smoke exited rc 1 before first progress on 2026-11-17 at 23:56:57 UTC. The superseded receipt records zero units and no residency evidence. The accepted native result comes from the separate official grant on 2026-11-18. [Original smoke failure receipt](ni-gpu-pool-matmul-20261117-v2/superseded-smoke-FAIL-1.json)

The existing planning canary replayed each original native result and capture through the registered ingestion path into its own isolated ledger, with exact current-reader matching enabled. The five replays projected 12 tuples with zero refusals, emitted 36 frames and emitted zero frames on retry. Exact candidate/build/operator/run targets presented one Judged/Located claim per operator. Missing operator and mismatched artifact, operator, run, shim and source checks presented zero. Ordinary `autokernel.planner` and `autopilot.planner` model targets each presented zero claims and denied reliance. Each row retains its byte-exact `planning-replay.json` with claim IDs, exact scope checks, native grant data and reader source digests.

The result applies to the model-free, digest-pinned `c463f601b` HIP executable and DSOs and the recorded finite CPU-reference selections. Original source dirty state is UNKNOWN and the recreated shim source differs from the historical source receipt. Elementwise covers one seed. The capture and replay provide no performance, population-error, clean-source, release, promotion, RVP-C2-2 or production-consumer adoption evidence.

Each row directory retains the original ready manifest, producer result, allocator complete and ended records and planning replay receipt. The producer result and planning replay reference the original sealed capture and raw evidence at their original absolute paths. `SHA256SUMS` covers the retained copies.
