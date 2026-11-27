# CPU prefix retention on q0–q2

The C22 CPU build completed two reversed pairs of a synthetic user-turn transition. Consistently enabling `preserve_thinking` retained 9,839 tokens and required 29 fresh tokens on each target. Disabling it retained 282 and required 3,942 fresh tokens. All four targets returned exactly READY. The prefill effect survived reversal despite substantial run-to-run speed variation. [Native receipts and summary](../../artifacts/analysis/ap-w66-cpu-prefix-q012/summary.json)

| Pair | Preserve | Fresh / cached | Native prefill s | Delivered TTFT s | Request wall s |
|---|---|---:|---:|---:|---:|
| 1, first | false | 3,942 / 282 | 6.444 | 6.478 | 6.522 |
| 1, second | true | 29 / 9,839 | 0.744 | 0.779 | 0.870 |
| 2, first | true | 29 / 9,839 | 0.424 | 0.456 | 0.550 |
| 2, second | false | 3,942 / 282 | 9.582 | 9.610 | 9.693 |

Target wall time fell by 5.65 and 9.14 seconds, or 7.49× and 17.64×. These are two diagnostic pairs. Native decode was two tokens per target, so its rate has little interpretive value. The full counters, speculative proposals/acceptances and warm-up requests are retained. The warm requests generated inert tool text. Their only purpose was to populate the cache, and they were excluded from target acceptance. [All eight requests](../../artifacts/analysis/ap-w66-cpu-prefix-q012/results.json)

The warm history was 9,843 tokens and included eight assistant/tool exchanges with explicit reasoning fields. A new user message caused the template to omit previous reasoning when preservation was false. Keeping preservation true retains that history and changes the target input content. The READY check establishes literal completion for this small fixture. Quality on real coding work, long-context GPU scheduling effects and time saved for a decoding neighbor require the remaining live comparison. [Original trace and native prefix control](autopilot-w66-trace.md)

## Placement and recipe

The server and driver inherited CPUs 0–71, covering q0–q2. OpenMP used 72 singleton physical-core places. NUMA interleaving used nodes 0–2. Every sampled server thread had allowed CPUs inside that set. The process never appeared in KFD and loaded no HIP library. Its CPU library digest matched C22's build identity. The model weights used allocated pages through `--no-mmap`. Sampled node-3 mappings were shared file mappings with zero anonymous mappings. The memory placement policy applies to new allocations. [Launch](../../artifacts/analysis/ap-w66-cpu-prefix-q012/launch.json) · [Resource samples](../../artifacts/analysis/ap-w66-cpu-prefix-q012/resources.jsonl) · [Loaded libraries](../../artifacts/analysis/ap-w66-cpu-prefix-q012/loaded-libraries.txt)

The recipe used A3B Q8_0 with MTP D2, reasoning off, one explicit split-KV slot, 16,384 context, f16 K/V, batch/microbatch 2,048, greedy sampling and a 32-token cap. Each arm erased the slot and populated its own warm prefix. The order was false, true, true, false. The question and stopping rule were two paired trials for prefix reuse and target timing. A startup attempt was stopped after the slot-erase route returned 501. Enabling the server's slot-save path exposed the erase route, and the complete eight-request trial then ran once. [Dedicated runner](../../artifacts/analysis/ap-w66-cpu-prefix-q012/run.py)

The owned server exited with return code zero and its PID was absent after cleanup. [Cleanup receipt](../../artifacts/analysis/ap-w66-cpu-prefix-q012/cleanup.json)

Next: RTG-02 uses the stable-prefix treatment in AP-W66-PAIR when the GPU window becomes available.
