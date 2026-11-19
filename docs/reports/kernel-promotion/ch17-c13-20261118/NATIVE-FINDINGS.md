# CH-17 frontdoor CPU diagnostic

Row `ch17-c13-frontdoor-cpu-20261118-r4` completed its predeclared descriptive comparison (rc0, 2026-11-18). C13 `bda43aa17` served Qwen3.6-35B-A3B-MTP Q8_0 on CPUs 48–71, 24 threads, np1, context 32768 and q8_0 KV. Three adjacent AB/BA/AB pairs compared native MTP depth 4 with no speculative decoding across four fixed 128-token greedy prompts. Higher decode throughput is better.

| Pair | Order | Median paired MTP/control throughput ratio |
| --- | --- | ---: |
| 1 | none / MTP | 1.524414 |
| 2 | MTP / none | 1.528828 |
| 3 | none / MTP | 1.534941 |

All twelve paired token streams were identical. MTP accepted 1152 of 1446 draft tokens (79.67%); individual observed throughput ratios ranged 1.208390–1.694159. All 24 requests retained 7–36 complete in-request samples of process start identity, mapped libraries and per-thread affinity; all six captured processes were proved stopped.

The four-prompt, three-pair design supplies descriptive observations without a confidence interval or a final speed winner. It does not establish the production 96t/np4 or 48t/np1 recipes, other models/backends, task quality, all-role selection or promotion acceptance. The native writer did not emit a ClaimTuple; committed conclusions are observations, with prospective projection tracked as `VB-CH17-FRONTDOOR-CPU-WIRE`.

[NATIVE-RESULT.json](NATIVE-RESULT.json) preserves the original result. [EVIDENCE.json](EVIDENCE.json) binds original and stored bytes. The `native/` records are losslessly compressed where large, retaining complete raw responses and live custody. Three prior qualification failures prohibit another retry of this lineage.
