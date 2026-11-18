# TB-SEM-1 thinking-budget semantics

Probe the native chat behavior of the pinned v10 CPU build with Qwen3.6-35B-A3B-MTP Q8_0. The orchestrator's `thinking_budget_fields(0)` intentionally emits no field. The pinned native parser accepts `thinking_budget_tokens` and applies the request's Boolean `chat_template_kwargs.enable_thinking` before rendering. The pinned template renders an open think scaffold when enabled and an empty closed block when disabled. The DCP-12 startup flags, including `--reasoning off`, stay exact. Explicit request booleans exercise both template branches. The sealed packet binds those source excerpts to the v10 store's build provenance and digest manifest.

| Order | Request | Question |
|---|---|---|
| 1 | Thinking enabled, budget field omitted | Does the enabled baseline return reasoning? |
| 2 | Thinking enabled, budget 8 | Does an explicit small positive budget affect native reasoning? |
| 3 | Thinking disabled, budget field omitted | Does the template switch suppress returned reasoning? |

Each POST uses the same messages, seed, sampling settings and 128-token generation cap. Capture the exact request/response, HTTP status, parsed `reasoning_content` field presence and value, assistant content, finish reason, usage and native verbose token IDs, rendered prompt and generation settings. Each cell has one attempt. Stop on the first transport, source, custody or deadline failure. Preserve the failed cell and unattempted cells as `UNKNOWN`. Smoke executes cell 1 once and its predicate requires fresh evidence and verified teardown.

The coverage decision is three captured responses with clean teardown. A reasoning-bearing omitted-budget baseline, a shorter reasoning trace with the cap, and no reasoning in the disabled arm support distinct semantics for this prompt. A corresponding rendered-prompt change helps attribute the disabled-arm observation. A non-reasoning baseline, malformed response or capped decode that prevents comparison leaves the relevant semantic comparison unknown. This is a single-prompt diagnostic. The usage counts cover total completion and the reasoning text is not a tokenizer audit of the 8-token cap.

Prepare with `python3 -B scripts/experiments/thinking-budget-semantics/prepare.py` before publishing. Preparation reuses DCP-12's retained weight receipt and binds the existing file identity, template, CPU library digests and source excerpts. The grant performs no download, source copy or GGUF hash. The launcher uses four allocator cores and a private authenticated loopback listener on port 19389 with a per-process production CPU `LD_LIBRARY_PATH`. The run uses a 1,200-second maximum window and a 100-second cap per POST. Official evidence lives in `thinking-probe/native/window-*/` beneath the lane's scratch root. Smoke uses its own Rowflow dry-run directory.
