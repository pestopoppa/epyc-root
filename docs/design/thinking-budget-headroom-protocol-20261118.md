# TB-SEM-1b thinking-budget headroom protocol

The original native v10 probe captured all three responses. With thinking enabled and the budget field omitted, the server returned reasoning and reached the shared 128-token ceiling before emitting an answer. The budget-8 and thinking-disabled arms both stopped normally. The successor asks whether the enabled baseline finishes with a larger completion allowance and whether the resulting native responses distinguish omitting a budget from disabling thinking for the historical Step 3 decision. [Original observations and custody](../research/thinking-budget-semantics-results-20261118.json)

## Registered comparison

Use Qwen3.6-35B-A3B-MTP Q8_0 and the pinned production-consolidated-v10 CPU build 10303 at `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. Use the original DCP-12 server recipe, including startup `--reasoning off` and the pinned chat template. Send these native non-streaming `/v1/chat/completions` requests in order, once each.

| Arm | `chat_template_kwargs.enable_thinking` | `thinking_budget_tokens` |
| --- | --- | --- |
| `budget-omitted` | `true` | Omitted |
| `budget-8` | `true` | `8` |
| `thinking-disabled` | `false` | Omitted |

All three requests reuse the original user message, seed `20261118`, temperature `0.0`, top-k `1`, disabled prompt caching, `reasoning_format: deepseek` and verbose token capture. The sole request-body change is `max_tokens: 1024` in all three arms. The serving invocation differs only in the private loopback port, `19390`. The per-request wall timeout is 180 seconds within a maximum 1,200-second official window on four allocator-assigned CPU cores. [Registered requests and preparation](../../scripts/experiments/thinking-budget-semantics/prepare.py)

## Custody and stopping

The sealed Rowflow spec is `/mnt/raid0/llm/tmp/delegation-context-preassembly/thinking-probe-headroom/packet/spec.json` for row `thinking-budget-semantics-headroom-20261118`. Its manifest SHA-256 is `b49d69a7b5978ad039b00118f094669daa94e30295ea5d9ff0f74fd82c3908c7`. It carries byte-identical source, build, template and serving custody receipts from the original packet. Preparation verifies the current GGUF file identity against the retained digest receipt and checks the CPU build and template digests. Rowflow smoke captures one omitted-budget response and verifies teardown in its own dry-run directory. The official attempt writes to `thinking-probe-headroom/native/window-*/` and leaves the original `thinking-probe` evidence in place.

Retain the exact request and native response, HTTP status, reasoning field presence and value, assistant content, finish reason, usage, native token IDs, rendered prompt and generation settings. Bind those records to the window receipt, source and build pins, file identity, server arguments, library linkage and listener and teardown checks. Stop after three responses with clean teardown or the first custody, transport or cleanup failure, allocator STOP, or deadline. Record failed or unattempted cells as unknown. The official window is single-use and has no retries. [Capture and qualification rules](../../scripts/experiments/thinking-budget-semantics/runner.py)

## Interpretation

- `completed >= 3` with verified teardown establishes response coverage. The semantic comparison is descriptive, with one observation per arm and no population estimate or statistical pass criterion.
- Compare finish reason, assistant content and the reasoning field first. A naturally finished enabled baseline with reasoning, paired with a disabled arm that omits reasoning and renders a closed think scaffold, supports treating budget omission and thinking suppression as distinct controls for this prompt. This can explain the historical request under the current orchestrator contract, where `thinking_budget_fields(0)` omits the field and `enable_thinking: false` controls the template. The comparison addresses the current setup. The original Qwen3.5 reproduction, an explicit numeric-zero native request and a pure-MoE comparison are outside its scope.
- If the enabled prompts match and the budget-8 arm returns a shorter reasoning trace, record the observed difference alongside the native output. Usage and verbose token IDs cover total completion. This single prompt cannot establish exact reasoning-token accounting or comparative answer quality.
- If the omitted-budget baseline still reaches the completion ceiling, times out, or lacks evidence required for a complete comparison, record the affected conclusion as unknown. The run ends at the registered limit without an automatic expansion.
