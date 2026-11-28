# C22 decode-aware prefill budget on ON 28 and OFF 56

The 256-token / 900-ms budget recovered 49.0–60.5 seconds of ON 28 decode time in three paired comparisons. OFF 56 delivered its first token 6.4–12.9 seconds later, within the 1.30× ceiling each time. Both streams finished later in every observed pair, but those differences were within the observed repeat range. This setting protects the decoder while shifting some wait to the prefilling request. The fixed-length test establishes timing scope. Accepted-work improvement remains unmeasured.

## Paired results

Every request generated exactly 256 tokens. ON 28 retained 38 fresh / 75,077 cached tokens and OFF 56 retained 107,912 fresh / 4,334 cached tokens in all six visits. Both rendered token-ID hashes and actual request-body hashes matched across arms. Preservation was unchanged. [Full numeric summary](../../artifacts/analysis/w66-prefill-budget-20261128/summary.json) · [Independent raw-log audit](../../artifacts/analysis/ap-w66-budget-controls/audit.json)

| Pair and order | ON 28 decode s, control → budget | OFF 56 delivered TTFT s, control → budget | TTFT ratio | Both-finish elapsed s, control → budget |
|---|---:|---:|---:|---:|
| 1, control then budget | 81.595 → 21.097 | 81.290 → 87.668 | 1.078 | 86.370 → 90.729 |
| 2, budget then control | 78.257 → 20.591 | 77.712 → 90.567 | 1.165 | 80.915 → 93.413 |
| 3, control then budget | 68.680 → 19.691 | 68.542 → 78.772 | 1.149 | 72.889 → 82.349 |

ON 28's paired decode reductions were 60.498, 57.666 and 48.989 seconds, each larger than the 12.915-second maximum same-arm repeat range. Peer TTFT increased by 6.379, 12.856 and 10.231 seconds. Each ratio remained below 1.30. Joint elapsed time increased by 4.359, 12.497 and 9.459 seconds. All three joint differences were within the 13.481-second maximum repeat range. The observations support decoder-latency protection and provide no resolved joint-completion gain.

The first two pairs reversed arm order. The joint-time question remained unresolved after those pairs, triggering the predeclared third pair. The run stopped after three pairs with that uncertainty recorded. These are diagnostic paired observations, with same-arm ranges reported as empirical repeat variation. No formal speedup interval is inferred.

## Iteration tail and visible delivery

| Visit | Mixed iterations | Native nearest-rank p99 / maximum ms | Prior-method native p99 ms | ON 28 delivered-event gap p99 ms |
|---|---:|---:|---:|---:|
| Pair 1 control | 83 | 1099.9 | 1098.2 | 1964.9 |
| Pair 1 budget | 97 | 981.4 | 291.3 | 270.3 |
| Pair 2 control | 83 | 1097.6 | 1075.3 | 1827.0 |
| Pair 2 budget | 94 | 988.1 | 270.4 | 272.9 |
| Pair 3 control | 83 | 1097.9 | 1077.5 | 1070.9 |
| Pair 3 budget | 91 | 259.9 | 257.5 | 254.9 |

The declared comparison uses nearest-rank p99, index `ceil(0.99*n)-1`. With fewer than 100 samples it selects the maximum. Treatment missed the 900-ms target in two visits. The earlier 27B trial used index `round(0.99*(n-1))`, which selects the second-largest sample at these counts. All three treatment visits were below 900 ms under that earlier convention. Both statistics retain the complete sample set.

The two large treatment samples were the final mixed iterations, recorded after ON 28's native timing print and final response. C22's native iteration timer spans batch decode, post-decode processing, worker joins and slot rebuild. Source places `checkpoint_after_generation` after the final response and before slot release. The logs are consistent with terminal bookkeeping contributing to those samples. Its exact contribution was not separately timed, so both samples remain in the native tail and maximum.

The native timer excludes batch preparation, pre-decode and time between server updates. Delivered-event gaps measure another boundary. They improved in the treatment, but event coalescing prevents treating them as exact token or iteration timings. Pair 3 control emitted 155 chunks for 256 tokens and had a 30.05-second maximum visible gap. The report therefore retains native iterations, delivered-event gaps, TTFT and joint elapsed independently. [Controller and precedent audit](../../artifacts/analysis/ap-w66-budget-controls/README.md)

## Controller and replay controls

The server binary and eight llama/ggml libraries matched unchanged C22 `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`. The model was Qwen3.6-35B-A3B-MTP Q8_0 with MTP D2, four split f16-KV slots at 131,072 tokens each, 2,048 batch/microbatch, CPUs 88–95 and NUMA node 3. The prior affinity control for ROCr helper threads applied to both arms. The control explicitly supplied zero for both budget flags, matching their default semantics; treatment supplied 256 and 900. Budget-related environment overrides were scrubbed.

Each visit used a fresh server and restored the same sealed ON 28 then OFF 56 snapshot. There was no warm completion before the scored requests. C22's startup warmup runs outside the server controller. Slot restoration does not restore the controller's estimator. ON 28's 38 fresh tokens are below its 64-token estimator-update threshold. Every visit's pre-mixed log therefore showed estimator zero. The first applied treatment cap was 256, and every mixed treatment cap remained 256. No controller code, alignment correction or tail correction was added.

OFF 56 was submitted immediately after ON 28's first visible delta. Timing uses the actual request sends and final streamed completion. Joint elapsed starts at the ON 28 send and ends when both streams finish. All native prompt rows reconcile to the two request counts. In each control visit all 107,912 OFF 56 prompt tokens were processed alongside decode. With the budget, mixed prompt counts were 24,496, 23,728 and 22,960. The remaining 83,416, 84,184 and 84,952 tokens continued after ON 28 finished. Those remaining tokens and their waiting time are included in OFF 56 TTFT and joint elapsed.

Both output caps were fixed at 256 to keep the timing work bounded. The previous replay capped ON 28 while its peer completed naturally. Current controls were remeasured, so the earlier 69.22-second overlap difference is context for this test, rather than its numeric baseline. Rendering, reconstructed prefix, sampler, preservation and peer trigger were fixed across the current arms. Natural completions and task acceptance were not measured in this panel.

The 27B precedent used Qwen3.8-27B with DFlash2 and a C6 fork whose controller added 32-row alignment and RMS tail correction. Its selected 256/900 setting produced native p99 896.2/899.6 ms and neighbour TTFT ratios 1.269/1.295. C22 lacks those corrections. The transferred targets were tested on A3B with the stock controller, with the percentile-definition difference made explicit. [Prior decision](../../handoffs/active/kv-cache-program.md) · [Source and prior packet hashes](../../artifacts/analysis/ap-w66-budget-controls/README.md)

## Custody and decision scope

The run completed with rc=0 at 10:20:21 UTC on 2026-11-28. All twelve observed owned PIDs were absent after cleanup, KFD was empty, the private port was closed and GPU utilization was 0%. The source, qualification, arm receipts, model/runtime proofs, mixed-iteration records and cleanup are preserved. [Runner and reproduction](../../artifacts/analysis/w66-prefill-budget-20261128/README.md) · [Row completion](../../artifacts/analysis/w66-prefill-budget-20261128/rowflow-ended.txt)

The owner-only archive is `/mnt/raid0/llm/archive/compute-evidence/w66-prefill-budget-20261128/`. It contains 116 files, approximately 202 MB, plus verified restore-only links to prior sealed snapshots. Its reducer reproduces the public summary byte for byte. The independent audit joins raw server task IDs, first-delta trigger, wire hashes, cache counts, output caps, estimator seed, applied budgets and native row conservation. [Archive manifest](../../artifacts/analysis/w66-prefill-budget-20261128/archive-manifest.json)

The standalone A3B two-pass gate stays parked. Preservation stays a separate question. The measured scheduler setting offers a substantial decoder-latency tradeoff, passes the peer TTFT ceiling in these visits, and misses the declared nearest-rank 900-ms criterion twice. A quality-qualified accepted-work claim requires natural completions with task grading.

Next: RTG-02 owns any latency-policy or natural-work decision based on these timing receipts.
