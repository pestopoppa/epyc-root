# CF-3c native REPL task-suite results

**2026-11-18 · CANDIDATE · bench.** The repaired instrument completed **24 of 24 fixed cells**. There were zero `UNKNOWN` or unattempted cells. The allocator recorded `rc=0` at 16:19:56 UTC, and the native result confirmed server exit. None of the A1 or A2 policies changed the history in a sent request. This meets the registered scaling-futility rule for the tested profile. The 1,128 later cells of the frozen 1,152-cell schedule remain idle. The shard is descriptive and leaves arm ranking and the 1-percentage-point adoption margin unresolved. [Registered protocol](../design/cf3c-task-suite-protocol-20261118.md)

## Per-arm outcomes

All four cases per arm were accuracy-eligible. Each arm had one correct answer, one incorrect answer and two no-answer outcomes counted as misses. The table reports runner wall time across all four observed cells, including the known-zero pre-generation cell.

| Arm | Observed | Correct / eligible | NA | Activated cells | Retrieval calls | Give-up proxy | Mean wall seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A0 | 4/4 | 1/4 | 2 | 0 | 0 | 0 | 156.84 |
| A1-k4 | 4/4 | 1/4 | 2 | 0 | 0 | 0 | 153.47 |
| A1-k8 | 4/4 | 1/4 | 2 | 0 | 0 | 0 | 153.38 |
| A1-k12 | 4/4 | 1/4 | 2 | 0 | 0 | 0 | 154.02 |
| A2 | 4/4 | 1/4 | 2 | 0 | 0 | 0 | 163.99 |
| A3 | 4/4 | 1/4 | 2 | 0 | 0 | 0 | 154.05 |

| Fixed case | Outcome in every arm | Generation requests per arm | Prompt tokens | Completion tokens |
| --- | --- | ---: | ---: | ---: |
| `ifeval_2801` | Finished on turn one, graded correct | 1 | 2,692 | 50 |
| `longcot_mini_18` | Native graph killed after repeated no-progress nudges, NA | 3 | 10,362 | 1,152 |
| `ruler_niah_4096_25` | Finished on turn one, graded incorrect | 1 | 6,717 | 10 |
| `longbench_671b3fa1bb02136c067d5353` | Native context exhaustion before generation, NA | 0 | 0 | 0 |

## Activation and cost reconciliation

All 30 native generation exchanges reached a verified SSE terminal with server usage. The 20 A1/A2 receipts reported no eligible observation change. The five A3 receipts reported an absent historical reasoning carrier in this graph projection. A3 therefore operated as an inactive control at this seam. LongCoT was the only multigeneration case. Its second and third requests carried nonempty history. For each of the five matched request positions across the suite, the selected-history digest and the sent request body digest were identical in all six arms.

The 24 outcome records reproduce all native per-arm summary values, including accuracy, no-answer counts, wall time and token cost. The accounting distinction is the cost denominator. The launcher treats the oversized LongBench cell as a complete, known-zero generation cost. Its raw count is **4/4 complete-cost tasks per arm**, with **5,245.75 tokens per complete-cost task**. The cell has zero generation exchanges and zero server-counter observations. Restricting the denominator to the **3/4 tasks with terminal-verified generation** gives **6,994.33 tokens per generating task** in every arm. Both means use the same **20,983 tokens per arm**, made up of 19,771 prompt and 1,212 completion tokens. Cached prompt tokens were zero on all five observed requests per arm. There were no interrupted exchanges or partial counter observations.

The four paired source cases use one seed each. The successor repeats the task/seed schedule exposed by the failed original run and qualification. These development observations do not establish held-out validity, independent task-population accuracy or production representativeness. A new binding-context cohort requires prospective task selection and a declared interval design before scale-up.

## Evidence custody

The [machine-readable reconciliation](cf3c-task-suite-results-20261118.json) retains the raw per-arm counters, the 24 per-cell outcomes with digests and the matched sent-request hashes. The reconciliation used the stored source-grader outcomes. All 349 entries in the native window manifest were verified, including the 24 outcome and graph files and the wire records. The repaired run is separate from the [first attempt's partial result](cf3c-task-suite-failure-20261118.md).

| Artifact | Path | SHA-256 |
| --- | --- | --- |
| Native summary | `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-suite-r2/native/RESULT.json` | `7c80b7294a6b149f922775157f75e713a31839c3841c26a631920a0e27687c00` |
| Allocator completion | `/mnt/raid0/llm/tmp/compute-flags/grants/cf3c-task-suite-r2-20261118.ended` | `c77a511b11cb05f5c5a4409e2be81663285d16563c9770c2cca12f556b021a3c` |
