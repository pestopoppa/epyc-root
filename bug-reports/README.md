# bug-reports/

Upstream bugs surfaced during EPYC inference research. One file per bug; format is informal but covers repro, expected/actual, root cause, suggested fix, and downstream workaround.

Filing these upstream is operator-discretion. Each report includes the target repo + a downstream-cited workaround if filing is deferred.

## Index

### `llama-cpp-deepseek-v4/` (antirez/llama.cpp-deepseek-v4-flash @ 2f2d44052)

| # | Severity | Title | Component |
|---|---|---|---|
| 01 | HIGH | [llama-bench V4 sched_reserve assert](llama-cpp-deepseek-v4/01-llama-bench-sched-reserve-assert.md) | `deepseek4.cpp:1153` × `llama_context::sched_reserve` |
| 02 | MED | [llama-cli / llama-completion conversation-mode issues](llama-cpp-deepseek-v4/02-llama-cli-completion-conversation-mode-issues.md) | `cli.cpp`, `common/arg.cpp`, `completion.cpp:213` |
| 03 | LOW | [llama-gguf `r` mode aborts on real models](llama-cpp-deepseek-v4/03-llama-gguf-r-mode-aborts-on-real-models.md) | `examples/gguf/gguf.cpp:269` |

Cross-reference: all three surfaced 2026-05-28 → 2026-05-30 during the DeepSeek-V4-Flash Strategy B execution (see `handoffs/active/deepseek-v4-flash-cpu-port.md`).
