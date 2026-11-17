# Prospective elementwise GPU-pool capture

Row `ni-gpu-pool-elementwise-20261117-v1` plans seven sequential native
invocations at original seed `2026102603`. Each uses the exact original
operator selector and the pinned, model-free c463f601b candidate on MI210
with CPUs 184–191. The 300-second scheduling envelope covers setup, seven
invocations and strict readback. The other 31 historical seeds are outside
this row's scope.

| Operator | Selected | Expected supported passes | Expected unsupported |
| --- | ---: | ---: | ---: |
| ADD | 16 | 16 | 0 |
| MUL | 16 | 16 | 0 |
| SCALE | 4 | 4 | 0 |
| NORM | 30 | 20 | 10 |
| RMS_NORM | 21 | 21 | 0 |
| SUM | 8 | 7 | 1 |
| SUM_ROWS | 10 | 4 | 6 |
| Total | 105 | 88 | 17 |

The private packet is at
`/mnt/raid0/llm/tmp/vidya-belief-substrate/elementwise-ready/`. Its executable,
four DSOs, source snapshot and shim share the digest-pinned attention-rest
artifact bytes. The removed source worktree's dirty state remains UNKNOWN.
The recreated shim source still differs from the original source digest
receipt.

`case-plan.tsv` specifies the parameter identities and expected support
dispositions for prospective verification. The producer compares each new
terminal log with that plan and requires the artifact's native CPU-reference
summary and two distinct, complete in-window samples per invocation. Each
sample binds process PID and birth ticks, KFD and positive VRAM, pinned
executable and library maps, and task affinity. A fresh request precedes all
invocations. The official result is written after strict readback of seven
existing-schema tuples, with a value equal to each operator's supported pass
count. The existing grade and candidate-local scope apply. The record supports
artifact-specific correctness for this seed and these cases.

The preparation record tracks validation. The private controls are model-free
and synthetic. Publication smoke, official capture and the planning-context
canary have their own acceptance conditions.

During publisher smoke, the acquired smoke grant hosts the focused controls
before the fresh native invocations. The smoke predicate verifies the control
receipt and its log digest alongside the strict native smoke result. The
preparation stage completed shell syntax, input digest and case partition checks.
The focused controls await the smoke grant.
