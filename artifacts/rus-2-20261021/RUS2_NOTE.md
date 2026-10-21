# RUS-2 result note (2026-10-21, lane dpf-sample-yarn-zc; zero inference)

Source: `epyc-inference-research/benchmarks/results/eval/*.jsonl`, 62 files, probe `scripts/analysis/rus2_trace_length_probe.py` (research lane commit 4cc8e1730), output `rus2_result.json` / `rus2_table.txt` (all 92 cells). Run under region-lock build role on q3 (72-95), nice 19 (deviation from `--cpu-list 0-95`: all quarters were held on the calendar).

## Field verification (the first step of the task)
- Per-sample records carry `tokens_generated` and a boolean `passed`: 6006 usable samples in 92 (role, mode, suite) cells; 462 samples dropped for missing/zero tokens_generated.
- NOT recorded: `finish_reason` (truncation cannot be read; a cap-value proxy was used and excluded: 559 samples), `temperature` (6565 of 6565 samples: not recorded), and the reasoning trace (only the final `answer` text; tap offsets point at logs that no longer exist for these runs).

## Within-question arm: VERIFIED NEGATIVE
Across all cells, only 1 question has repeated samples with mixed outcomes (frontdoor/direct/debugbench; 1 correct-vs-incorrect pair). The corpus is one sample per (question, role, mode), so the within-question rank agreement (the only direction that matters for best-of-K) CANNOT be measured on existing logs: N = 1 mixed question, 1 pair. A repeated-sample run would be needed (an inference task, not filed here).

## Between-question AUROC (tokens generated vs correctness), cells with >=100 questions
| role | mode | suite | Q | samples | correct | cap-proxy excl | AUROC(tokens, correct) | 95% CI (question bootstrap) | review-ratio n / AUROC |
|---|---|---|---|---|---|---|---|---|---|
| architect_coding | delegated | coder | 128 | 128 | 121 | 0 | 0.6576 | [0.4315, 0.9194] | 95 / None |
| architect_coding | delegated | general | 126 | 126 | 76 | 0 | 0.4329 | [0.353, 0.5378] | 1 / None |
| architect_coding | delegated | gpqa | 130 | 130 | 39 | 0 | 0.3904 | [0.3105, 0.4706] | 17 / 0.5 |
| architect_coding | delegated | hotpotqa | 127 | 127 | 4 | 0 | 0.1057 | [0.0476, 0.1787] | 23 / None |
| architect_coding | delegated | math | 131 | 131 | 50 | 0 | 0.3012 | [0.2057, 0.3846] | 10 / None |
| architect_coding | delegated | simpleqa | 104 | 104 | 2 | 0 | 0.5123 | [0.267, 0.7108] | 7 / None |
| architect_coding | delegated | thinking | 105 | 105 | 68 | 0 | 0.5028 | [0.4574, 0.551] | 0 / None |
| architect_general | delegated | coder | 167 | 167 | 129 | 0 | 0.6088 | [0.5078, 0.7023] | 96 / 0.5 |
| architect_general | delegated | general | 166 | 166 | 128 | 0 | 0.3892 | [0.3138, 0.4864] | 0 / None |
| architect_general | delegated | gpqa | 171 | 171 | 66 | 0 | 0.3375 | [0.2697, 0.4048] | 19 / None |
| architect_general | delegated | hotpotqa | 168 | 168 | 10 | 0 | 0.288 | [0.1867, 0.3988] | 0 / None |
| architect_general | delegated | math | 171 | 171 | 74 | 0 | 0.4136 | [0.318, 0.4991] | 2 / None |
| architect_general | delegated | simpleqa | 129 | 129 | 4 | 4 | 0.458 | [0.2659, 0.8425] | 0 / None |
| architect_general | delegated | thinking | 128 | 128 | 102 | 0 | 0.2519 | [0.1616, 0.3443] | 0 / None |
| architect_general | direct | instruction_precision | 128 | 128 | 107 | 12 | 0.585 | [0.4483, 0.7314] | 46 / 0.575 |
| frontdoor | direct | coder | 166 | 166 | 157 | 9 | 0.5743 | [0.3712, 0.791] | 160 / 0.5329 |
| frontdoor | direct | debugbench | 154 | 160 | 132 | 0 | 0.5116 | [0.3805, 0.6234] | 159 / 0.493 |
| frontdoor | direct | general | 174 | 174 | 140 | 0 | 0.4962 | [0.4516, 0.5443] | 4 / 0.6667 |
| frontdoor | direct | gpqa | 124 | 124 | 60 | 105 | 0.5023 | [0.4356, 0.5678] | 22 / 0.4583 |
| frontdoor | direct | hotpotqa | 253 | 253 | 179 | 0 | 0.2116 | [0.1434, 0.2888] | 169 / 0.2785 |
| frontdoor | direct | instruction_precision | 134 | 134 | 114 | 36 | 0.6662 | [0.4904, 0.7871] | 80 / 0.5485 |
| frontdoor | direct | livecodebench | 130 | 130 | 129 | 0 | 1.0 | [1.0, 1.0] | 128 / None |
| frontdoor | direct | math | 127 | 127 | 110 | 51 | 0.4834 | [0.3134, 0.6452] | 126 / 0.5461 |
| frontdoor | direct | simpleqa | 107 | 107 | 10 | 110 | 0.6268 | [0.3735, 0.8278] | 56 / 0.656 |
| frontdoor | direct | thinking | 107 | 107 | 96 | 28 | 0.5724 | [0.4663, 0.6722] | 4 / None |
| frontdoor | repl | coder | 164 | 164 | 90 | 0 | 0.5627 | [0.4775, 0.6581] | 67 / None |
| frontdoor | repl | general | 164 | 164 | 94 | 0 | 0.5695 | [0.4685, 0.6811] | 16 / None |
| frontdoor | repl | gpqa | 158 | 158 | 72 | 0 | 0.387 | [0.3042, 0.4893] | 8 / None |
| frontdoor | repl | hotpotqa | 162 | 162 | 116 | 0 | 0.3007 | [0.2099, 0.3921] | 0 / None |
| frontdoor | repl | math | 169 | 169 | 86 | 0 | 0.7534 | [0.6794, 0.8234] | 0 / None |
| frontdoor | repl | thinking | 127 | 127 | 98 | 0 | 0.3837 | [0.2537, 0.5242] | 6 / None |

AUROC below 0.5 means correct samples are shorter. Direction is not consistent across cells (0.11 to 0.75, and 1.0 where 129 of 130 are correct, which is degenerate). Between-question length mostly tracks question difficulty and answer format, not within-question correctness, so these numbers do not license a length selector.

## Review ratio
Computed on the answer text only (cells with >= 4 chunks per answer). Coverage is low and AUROC values sit near 0.5 where n >= 30 (e.g. frontdoor direct coder 0.5329 on 160, math 0.5461 on 126), with one outlier (frontdoor direct hotpotqa 0.2785 on 169). It is not a measurement of reasoning-trace review behaviour.

## RUS-1 selector table: proposed edit (for main to apply; RUS-1 is already ticked)
Clause 1 of the RUS-1 note: DROP the shorter-length row from the planned selector table as a default candidate; keep it only as a diagnostic row labelled `unvalidated on our roles: no within-question data (RUS-2, 2026-10-21)`. Keep the lower review-ratio row only if a trace-bearing arm records traces; answer-text ratios are not usable. Reason: the length signal could not be validated in the best-of-K direction (N=1 mixed question) and the between-question direction flips across cells.

## Belief Kernel wiring (prep; owning session applies)
Row for `scripts/vidya/adapters/README.md` source table: `| RUS-2 trace-length / review-ratio probe over eval JSONL (2026-10-21, research `benchmarks/results/eval/`, script `scripts/analysis/rus2_trace_length_probe.py`, output `artifacts/rus-2-20261021/rus2_result.json`) | measurement (candidate) | not yet wired; per-sample records carry tokens_generated + passed but NO temperature or finish_reason, so tuples cannot carry a complete protocol; within-question arm N=1 | producer: probe JSON per cell; adapter pending |`.
Task for `handoffs/active/vidya-belief-substrate-program.md`: `- [ ] Wire RUS-2 probe output as a measurement adapter (projection only; record that temperature/finish_reason are absent so grade() downgrades).`
