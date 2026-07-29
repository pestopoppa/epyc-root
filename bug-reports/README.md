# bug-reports/

Upstream bugs surfaced during EPYC inference research. One file per bug; format is informal but covers repro, expected/actual, root cause, suggested fix, and downstream workaround.

Filing these upstream is operator-discretion. Each report includes the target repo + a downstream-cited workaround if filing is deferred.

## Index

### `llama-cpp-deepseek-v4/` (antirez/llama.cpp-deepseek-v4-flash @ 2f2d44052)

| # | Severity | Title | Component |
|---|---|---|---|
| 01 | HIGH | [llama-bench V4 sched_reserve assert](llama-cpp-deepseek-v4/01-llama-bench-sched-reserve-assert.md) — patch: [`01-deepseek4-sched-reserve.patch`](llama-cpp-deepseek-v4/01-deepseek4-sched-reserve.patch) | `deepseek4.cpp:1153` × `llama_context::sched_reserve` |
| 02 | HIGH | [llama-cli conversation-mode fallthrough + EOF loop; llama-completion auto-cnv warning](llama-cpp-deepseek-v4/02-llama-cli-completion-conversation-mode-issues.md) — patches: [`02ab-cli.patch`](llama-cpp-deepseek-v4/02ab-cli.patch), [`02c-completion.patch`](llama-cpp-deepseek-v4/02c-completion.patch) | `tools/cli/cli.cpp` + `tools/completion/completion.cpp` |
| 03 | LOW | [llama-gguf `r` mode aborts on real models](llama-cpp-deepseek-v4/03-llama-gguf-r-mode-aborts-on-real-models.md) — patch: [`03-llama-gguf-r-mode.patch`](llama-cpp-deepseek-v4/03-llama-gguf-r-mode.patch) | `examples/gguf/gguf.cpp:269` |

**All four patches applied + built + binary-verified locally** at `/mnt/raid0/llm/llama.cpp-deepseek-v4` against tip `2f2d44052`. Functional verification against real V4 GGUF (would require running `llama-bench` / `llama-gguf`) deferred to operator authorization per `feedback_no_concurrent_inference`. Compile + binary-string + linkage checks all pass.

Cross-reference: all three surfaced 2026-05-28 → 2026-05-30 during the DeepSeek-V4-Flash Strategy B execution (see `handoffs/active/deepseek-v4-flash-cpu-port.md`).
