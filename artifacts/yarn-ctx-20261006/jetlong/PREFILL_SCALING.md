# CPU long-context prefill scaling (Qwen3.6-35B-A3B-MTP Q8_0, 96 threads, -ub 256, np 1, 2026-10-06)

Derived from slot print_timing lines in /mnt/raid0/llm/tmp/jetlong-longctx-20261006/results/{JON,YS}_524000/server.log (scratch). Instantaneous tok/s = tokens/seconds over a 20-line window (about 10k tokens). JON = Jet-Long window 2048 native 262144; YS = static YaRN. Both logs end near 109k of a ~288k prompt (progress 0.38); the logs do not show completion.

| arm | depth (tokens) | instantaneous tok/s |
|---|---|---|
| JON | 1690 | 374.3 |
| JON | 11930 | 198.3 |
| JON | 22170 | 131.6 |
| JON | 32410 | 96.8 |
| JON | 42650 | 79.3 |
| JON | 52890 | 69.8 |
| JON | 63130 | 59.5 |
| JON | 73370 | 53.0 |
| JON | 83610 | 47.7 |
| JON | 93850 | 42.8 |
| JON | 104090 | 38.9 |
| YS | 2202 | 320.7 |
| YS | 22682 | 128.4 |
| YS | 43162 | 82.1 |
| YS | 63642 | 62.0 |
| YS | 84122 | 49.7 |
| YS | 104602 | 41.5 |

Cumulative average: JON 561 tok/s at 2.2k, 494 at 4.8k, 70.3 at 109k; YS 75.9 at 109k. Prefill cost per token grows with depth (attention over a growing KV on CPU) in both arms; Jet-Long shows no visible slope penalty below native.
