# 2026-10-22 Qwen3.x thinking-off at the source (coordinator 3c4ca599)

Cause: Qwen3.6 defaults to thinking-ON; under a token cap reasoning consumed the budget and content was empty (cme7, hsprof1, kpf64 voided).

Frozen v10 source semantics (read-only, `/mnt/raid0/llm/llama.cpp`):
- `--reasoning off` sets `enable_reasoning=0` and `default_template_kwargs["enable_thinking"]="false"` (`common/arg.cpp:3463-3465`); `--chat-template-kwargs enable_thinking` is deprecated in favour of it (`arg.cpp:3310`).
- A per-request `chat_template_kwargs {enable_thinking:true}` OVERRIDES the server default: request items overwrite the CLI kwargs (`tools/server/server-common.cpp:1074-1078`) and the merged value is parsed at `:1080-1087`. Server-side off is therefore safe for jobs with a thinking-ON arm (YaRN OOL-1).
- `--reasoning-budget` is a separate sampler budget (`arg.cpp:3475`, `server-common.cpp:1118-1127`), not needed.

Fix: `jobs/qwen_thinking_lib.sh` (`qwen_reasoning_args`, `qwen_first_reply_preflight`, rc 9 refusal). Wired into hil15a, hil18a, kpf261-outcome (CPU argv), cme7-poker-smoke and hsprof1-beam (via GPU_RECIPE_EXTRA_ARGS). Not applied: yarn jobs (harness already sends enable_thinking per item; E1 argv left verbatim), rte_pfx2 and kpf64 (server argv built in other agents' worktrees). Fake-server test: reasoning present rc 9, empty content rc 9, OK rc 0. Guide: compute-fillers.md item 15.
