# CF-3c paired continuation pilot results

**2026-11-18 · CANDIDATE · bench.** The [paired continuation protocol](../design/cf3c-pilot-protocol-20261118.md) completed all 18 scheduled cells on a private CPU server running Qwen3.6-35B-A3B-MTP Q8_0. All 14 prompts that exposed the target receipt yielded an exact match. The four prompts that lost it yielded the literal `UNKNOWN` and finished normally. The pilot met its diagnostic coverage criterion. Its scope is policy activation, native rendering and evidence custody on these fixtures.

## Arm results

Exact recovery is higher-is-better; tokens and wall are lower-is-better subject to preserving recovery. Totals include native prompt and completion tokens. Every arm had three cells with usage. Mean cell wall covers transform, native template and tokenizer requests, completion, grading and evidence collection. Server startup was recorded separately at 3.35 s. Deltas compare each arm mean with A0 over the same three cases.

| Arm | Attempted / scheduled | Exact / attempted | Exact / graded | Abstained | NA | UNKNOWN status | Mean total tokens (Δ) | Mean cell wall, s (Δ) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A0 | 3/3 | 3/3 | 3/3 | 0 | 0 | 0 | 5,793 | 130.38 |
| A1-k4 | 3/3 | 1/3 | 1/1 | 2 | 0 | 0 | 4,176 (−27.9%) | 83.87 (−35.7%) |
| A1-k8 | 3/3 | 2/3 | 2/2 | 1 | 0 | 0 | 4,449 (−23.2%) | 90.74 (−30.4%) |
| A1-k12 | 3/3 | 3/3 | 3/3 | 0 | 0 | 0 | 4,986 (−13.9%) | 105.93 (−18.8%) |
| A2 | 3/3 | 2/3 | 2/2 | 1 | 0 | 0 | 3,918 (−32.4%) | 78.04 (−40.1%) |
| A3 | 3/3 | 3/3 | 3/3 | 0 | 0 | 0 | 4,868 (−16.0%) | 104.02 (−20.2%) |

An abstention is a completed response whose content was `UNKNOWN`. It counts in attempted-cell accuracy and is excluded from graded-outcome accuracy. The instrument uses the separate `UNKNOWN` status for an evidence or transport failure. Every cell finished with `stop`, with zero instrument UNKNOWNs, budget-exhaustion NAs, unattempted cells or non-terminations.

## Paired cells in execution order

The policy receipts count modified tool observations and historical assistant entries. Receipt exposure was checked in the saved native render. Prompt and decode times are from the server response. Wall is the harness cell time.

| Cell | Case | Arm | Observations / assistant entries changed | Receipt visible | Outcome | Prompt + decode tokens | Native prompt / decode, s | Wall, s |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| 00 | old-deep | A0 | 0 / 0 | Yes | Exact | 4,482 + 16 | 90.47 / 1.08 | 91.61 |
| 01 | old-deep | A1-k4 | 2 / 0 | No | Abstained | 3,677 + 2 | 70.40 / 0.34 | 70.81 |
| 02 | old-deep | A1-k8 | 0 / 0 | Yes | Exact | 4,482 + 16 | 90.50 / 1.01 | 91.58 |
| 03 | old-deep | A1-k12 | 0 / 0 | Yes | Exact | 4,482 + 16 | 90.47 / 1.01 | 91.54 |
| 04 | old-deep | A2 | 3 / 0 | No | Abstained | 3,346 + 2 | 62.77 / 0.40 | 63.23 |
| 05 | old-deep | A3 | 0 / 3 | Yes | Exact | 3,927 + 16 | 77.48 / 0.97 | 78.52 |
| 06 | old-head | A1-k4 | 4 / 0 | No | Abstained | 4,166 + 2 | 83.39 / 0.35 | 83.81 |
| 07 | old-head | A1-k8 | 4 / 0 | No | Abstained | 4,166 + 2 | 83.17 / 0.34 | 83.58 |
| 08 | old-head | A1-k12 | 0 / 0 | Yes | Exact | 5,765 + 14 | 128.59 / 1.06 | 129.73 |
| 09 | old-head | A2 | 5 / 0 | Yes | Exact | 3,945 + 14 | 77.88 / 0.98 | 78.93 |
| 10 | old-head | A3 | 0 / 5 | Yes | Exact | 4,840 + 14 | 102.42 / 1.03 | 103.52 |
| 11 | old-head | A0 | 0 / 0 | Yes | Exact | 5,765 + 14 | 126.40 / 1.06 | 127.54 |
| 12 | recent | A1-k8 | 6 / 0 | Yes | Exact | 4,666 + 15 | 95.90 / 1.07 | 97.05 |
| 13 | recent | A1-k12 | 6 / 0 | Yes | Exact | 4,666 + 15 | 95.42 / 1.02 | 96.51 |
| 14 | recent | A2 | 7 / 0 | Yes | Exact | 4,432 + 15 | 90.90 / 0.99 | 91.97 |
| 15 | recent | A3 | 0 / 7 | Yes | Exact | 5,792 + 15 | 128.86 / 1.06 | 130.01 |
| 16 | recent | A0 | 0 / 0 | Yes | Exact | 7,087 + 15 | 170.80 / 1.11 | 172.00 |
| 17 | recent | A1-k4 | 6 / 0 | Yes | Exact | 4,666 + 15 | 95.89 / 1.01 | 96.98 |

- **A1** activated on all three histories at k4, the last two at k8 and only the longest at k12. Inactive cells matched A0 prompt tokens and exact recovery. Within each case, active thresholds produced the same prompt token counts and outcomes. The k12 arm's 3/3 includes two inactive cells and one active cell whose recent receipt was protected. Its performance on an older receipt when active remains unmeasured.
- **A2** changed older observations on all three cases and was the lowest-cost arm in this matrix. Its 180-character prefix retained the old-head receipt and dropped the old-deep receipt. The recent observation stayed intact.
- **A3** changed historical assistant entries in every case and reduced native prompt tokens by 555, 925 and 1,295, respectively. It preserved all observations and recovered every receipt. The fixture put receipts exclusively in tool observations, so the test exercised historical reasoning removal without testing retrieval of facts present only in assistant reasoning.

## Scope and custody

Each case supplied one synthetic history and shared one seed across the six arms. Pairing supports case-level comparisons, and rotation varied arm order across cases. The 18 cells represent three paired cases with a single completion per arm and case. History length, receipt position and A1 threshold eligibility vary together across the fixtures. The run cannot resolve the one-percentage-point adoption margin or estimate variability across seeds, workloads or serving sessions. The wall measurements describe this private, uncached CPU replay, which sent structured history directly to the server. Production route serialization, end-to-end agent trajectories and production serving latency remain unmeasured by this pilot.

Orchestrator source pin `12afe2858f9dbd4691447926d6cf1864de64348c`. The native `epyc.cf3c.native.v1` summary is `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c/native/RESULT.json` (SHA-256 `f254f1d20b28ce27c92b98d62e4bb4147aa07acc9998f92872f9283b5e203473`). It records complete coverage and server exit and binds the sealed packet (`69a3375b7b37ff0a6c5253a58160e5516912395b235baac292e27540962a574a`) and the native files in sibling `window-0_5rprkm/`. Each numbered cell preserves the original messages, policy receipt, native template and tokenizer exchanges, completion and trajectory. The window receipt includes build and template digests and the mapped-library evidence.
