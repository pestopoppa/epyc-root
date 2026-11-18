# CF-3c active-evidence and task-level continuation results

**2026-11-18 · CANDIDATE · bench.** The active-evidence and task-level diagnostics each completed and recorded all 18 of 18 scheduled attempts. Each A1 threshold removed the archived observation-tail and observation-head receipts and retained the reasoning-only receipt in both matrices. In the task window, all three A1 thresholds lost both observation-case successes relative to A0 and gained the reasoning-case success. Mean A1 live token use was 22.1% below A0 across the three tasks. The protocols register coverage as a diagnostic completion criterion. [Active-evidence protocol](../design/cf3c-active-evidence-protocol-20261118.md) · [Task-level protocol](../design/cf3c-task-level-protocol-20261118.md)

## Active evidence

Each arm had three scheduled, attempted and usage-bearing cells. All 18 finished normally with `stop`. The exact recovery denominator includes abstentions. Graded cells contain exact or incorrect answers, and `UNKNOWN` returned by the model is an abstention. There were zero NAs, instrument UNKNOWNs, unattempted cells and non-terminations in every arm. Mean token use includes the native prompt and completion. Cell wall includes policy application, native rendering, tokenization and generation. Server startup took 3.31 s separately.

| Arm | Correct / attempted | Graded | Abstained | Incorrect | Mean prompt tokens | Mean total tokens | Mean cell wall, s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A0 | 2/3 | 2 | 1 | 0 | 7,099.7 | 7,110.3 | 168.25 |
| A1-k4 | 1/3 | 1 | 2 | 0 | 4,687.0 | 4,692.7 | 96.16 |
| A1-k8 | 1/3 | 1 | 2 | 0 | 4,687.0 | 4,692.7 | 95.93 |
| A1-k12 | 1/3 | 1 | 2 | 0 | 4,687.0 | 4,692.7 | 95.74 |
| A2 | 1/3 | 1 | 2 | 0 | 4,456.3 | 4,463.3 | 89.99 |
| A3 | 2/3 | 3 | 0 | 1 | 5,797.0 | 5,812.7 | 128.23 |

Each paired entry gives archived target visibility in the native render and the completion outcome. A seed is shared by all six arms of its case.

| Case | Seed | A0 | A1-k4 | A1-k8 | A1-k12 | A2 | A3 |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `old-deep`, tool tail | 1054083393 | Present, exact | Absent, abstained | Absent, abstained | Absent, abstained | Absent, abstained | Present, exact |
| `old-head`, tool head | 493308705 | Present, exact | Absent, abstained | Absent, abstained | Absent, abstained | Present, exact | Present, exact |
| `old-reasoning`, assistant reasoning | 1241115465 | Present, abstained | Present, exact | Present, exact | Present, exact | Present, abstained | Absent, incorrect |

The 18 native exposures matched the registered pattern. The active A1 thresholds produced six tool stubs in each cell and identical prompts and outcomes by case. Each cut mean total tokens by 34.0% relative to A0. Because all three thresholds yielded the same transformed prompts on these fixtures, this matrix provides no independent dose-response comparison among k=4, 8 and 12. The A2 prefix kept the old-head target and its exact recovery, while its removal of the old-tail target coincided with an abstention. With the reasoning-only target visible, A0 and A2 still answered `UNKNOWN`. A3 removed the target and output `30b145328a692f6c`, the receipt decoy in the Desk 3 observation tail (`cell-15`). Its 2/3 exact rate equals A0's, with an incorrect answer where A0 abstained. The prompt checks establish presence and removal directly, while the model outcomes show that presence alone did not guarantee retrieval here.

## Task-level continuation

Each arm had three scheduled, attempted and observed tasks, all with complete cost custody. Every task stopped with a terminal response. There were zero NAs, instrument UNKNOWNs, unattempted tasks, non-terminations and incomplete-cost tasks in every arm. The incomplete-cost lower-bound total is therefore zero. Each of the 48 started generation requests has a verified usage record, eight per arm. Mean live tokens sum prompt and completion usage over each continuation, including repeat input tokens when the prefix is resent. Task wall includes rendering, tokenization, generation and local tools. Server startup took 3.34 s separately.

| Arm | Correct / observed | Graded | Abstained | Incorrect | Mean live tokens | Mean task wall, s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A0 | 2/3 | 2 | 1 | 0 | 6,141.0 | 110.32 |
| A1-k4 | 1/3 | 2 | 1 | 1 | 4,786.3 | 84.65 |
| A1-k8 | 1/3 | 2 | 1 | 1 | 4,786.3 | 84.44 |
| A1-k12 | 1/3 | 2 | 1 | 1 | 4,786.3 | 84.47 |
| A2 | 2/3 | 2 | 1 | 0 | 5,253.7 | 92.62 |
| A3 | 2/3 | 2 | 1 | 0 | 5,906.3 | 105.52 |

Each paired entry gives archived receipt visibility in the live renders, the oracle outcome and the summed live tokens. A correct task required both an actual local release and the exact service confirmation in the terminal answer. `BLOCKED` is an abstention.

| Case | Base seed | A0 | A1-k4 | A1-k8 | A1-k12 | A2 | A3 |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `archive-tail`, desk 2 | 923741 | Present, correct, 6,962 | Absent, blocked, 5,371 | Absent, blocked, 5,371 | Absent, blocked, 5,371 | Absent, blocked, 3,873 | Present, correct, 6,710 |
| `archive-head`, desk 3 | 392847 | Present, correct, 6,950 | Absent, incorrect, 3,572 | Absent, incorrect, 3,572 | Absent, incorrect, 3,572 | Present, correct, 5,942 | Present, correct, 6,698 |
| `archive-reasoning`, desk 4 | 620539 | Present, blocked, 4,511 | Present, correct, 5,416 | Present, correct, 5,416 | Present, correct, 5,416 | Present, correct, 5,946 | Absent, blocked, 4,311 |

- **Archive tail.** All three A1 arms inspected, then attempted release with the correct fresh challenge and the same wrong receipt, `287b46770336`. The service rejected each attempt and each model returned `BLOCKED` (`task-01` through `task-03`). A2 stopped after inspection with `BLOCKED`. A0 and A3 inspected, released and returned the exact confirmation.
- **Archive head.** Each A1 arm inspected and returned `RELEASED 9f0123456789` without a release call. The service state was unreleased and the oracle marked each answer incorrect (`task-06` through `task-08`). A0, A2 and A3 executed the release and returned `RELEASED 547f1632ab5c`.
- **Archive reasoning.** Both A0 and A3 inspected and blocked, with the archived receipt visible under A0 and absent under A3 (`task-16` and `task-15`). All three A1 arms and A2 retained the receipt, used it in the release call and returned the exact confirmation. The case shows A3 removal in the native renders. Its paired terminal outcome ties A0.

A2's 2/3 matches A0 through one loss and one gain. A3 matches A0 on all three tasks and costs 3.8% fewer live tokens overall. The lower overall tokens and wall in every compacted arm include differences in trajectory and outcome. For example, A1 used fewer tokens than A0 on the incorrectly terminated head case and more tokens on the reasoning case it completed successfully.

## Scope and custody

The active diagnostic uses offline-constructed histories and one native continuation per arm and case. The task diagnostic measures live post-archive generation and model-selected tools against a closed local service. Its ten archived tool interactions and historical reasoning witness were scripted. Their generation cost is outside the measured continuation, and the supplied prefix still contributes prompt tokens whenever the model sees it. The windows used the pinned Qwen3.6-35B-A3B-MTP Q8_0 CMP-4 CPU recipe on private uncached listeners. These timings describe that setup. Production graph behavior and end-to-end production costs are outside scope.

Each matrix contains three synthetic cases and one seed per case. A single case changes an arm's exact success rate by 33.3 percentage points. These observations support mechanism and custody findings on the registered fixtures. A one-percentage-point adoption claim requires a representative source-frozen task suite and a prospective paired accuracy and cost analysis.

Both windows pin orchestrator source `12afe2858f9dbd4691447926d6cf1864de64348c` and CMP-4 harness `ed0496bf38d9228bd8420f5b8c3fde238097de9f`. Both bind the frozen v10 CPU server SHA-256 `4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c`, template SHA-256 `1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551` and prior-verified weight SHA-256 `c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131`. The native records report both private servers exited. The audit matched both packet `inputs.json` digests and every listed window file digest, 223 for active evidence and 583 for task continuation.

| Artifact | Active evidence | Task continuation |
| --- | --- | --- |
| Native schema | `epyc.cf3c.native.v1` | `epyc.cf3c.task.native.v1` |
| Run directory under `/mnt/raid0/llm/tmp/delegation-context-preassembly/` | `cf3c-active/` | `cf3c-task/` |
| Packet `inputs.json` SHA-256 | `dfbaf6d142d1b609c9ddf47ddea473cb4f16c4b796092f6709a2cacd494fbe4a` | `8b76aff2fce9e0a431e7bf34562bd2c125a1130ceddcb64003622f0a9c9262f3` |
| `native/RESULT.json` SHA-256 | `9efbab4e2e677c402fc0f59ce38b900f2820ed8d9a046803a4190de36f667d61` | `e118c3b9cf778f1a2df3960a33b4d50bd6203fbaeeb3097223e41faced79719f` |
| Native window directory | `native/window-mem58t0m/` | `native/window-bfh1eout/` |
| Native `WINDOW.json` SHA-256 | `c4c0db3842ed0185667c5140e88a250d6dcb99bfed012a2f5c256ad58113902d` | `be66e05f6270f17874800986069c4ccd280d5b94f11ad593aef31447a42a77fd` |
