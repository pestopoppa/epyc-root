# HSF-4 CPU prompt-cache update aggregate

Retained CPU KPF-64 C/D log lines include prompt state MiB and enclosing prompt-cache update time. This prospective read-only census binds all four logs to pinned SHA-256 and emits per-arm counts and rates only. It selects blocks with exactly one explicit save and positive elapsed time, reporting all other blocks as excluded. Its effective state-bytes/update-time ratio includes any other operations inside that enclosing update; it is not a pure copy rate or restore rate and cannot close HSF-4. The denominator's measurement is a logged whole-update time, not a timer around a memcpy. No prompts, request IDs or raw log lines are emitted. Four-CPU smoke uses a synthetic fixture only.

## Full historical aggregate, filed 2026-11-19

The full row completed on 2026-11-05 with rc=0 and native status `COMPLETE`: four digest-bound logs, 86 update blocks, 70 eligible single-save blocks and 16 excluded blocks. PASS applies to the bounded census decision rule; HSF-4 remains open. [belief: cc]

| Arm | Total | Excluded | Eligible | Median GB/s | Min GB/s | Max GB/s |
|---|---:|---:|---:|---:|---:|---:|
| pass1-C | 22 | 4 | 18 | 7.159434 | 6.236471 | 889.541589 |
| pass1-D | 22 | 4 | 18 | 7.137308 | 5.148491 | 389.607665 |
| pass2-C | 21 | 4 | 17 | 7.644068 | 4.536056 | 1104.756764 |
| pass2-D | 21 | 4 | 17 | 6.544608 | 5.139905 | 839.019503 |

Rates are saved-state bytes divided by the enclosing update elapsed time, in decimal GB/s. They may include allocation, search, checkpoint and load overhead. The extreme maxima are retained descriptive ratios, not demonstrated memory-copy bandwidth. No arm superiority, restore speed, controlled timing or crossover is established. This census does not close HSF-4.

Native result: `/mnt/raid0/llm/tmp/kvu/hsf4-cpu-save-aggregate-20261105/out/RESULT.json`; SHA-256 `4452f7d2038007fb3e81dec470d051f3484b12b85b054adc542e2654aa687341`. The native result records the SHA-256 of each source log. Existing source logs and results are referenced in place; no raw logs are copied. This committed conclusion is an OBSERVATION, without retrospective measurement warrant. [belief: cc]
