# OpenCode Re-Audit at Tip: HS-4 P0.3 (2026-09-16)

**Owner handoff:** [`handoffs/active/harness-selection-and-integration.md`](../../../handoffs/active/harness-selection-and-integration.md), HS-4, Phase 0 step P0.3
**Spec:** [`docs/design/hs4-shell-and-orchestrator-features-20260916.md`](../../design/hs4-shell-and-orchestrator-features-20260916.md) §4, P0.3
**Instrument:** the HS-1g call-verb check, [`client-surface-audit.md`](client-surface-audit.md) Step 3 (originally written in the Hermes handoff, now [`handoffs/completed/hermes-outer-shell.md`](../../../handoffs/completed/hermes-outer-shell.md))
**Prepared by:** `sub-hs4-p03`. Zero inference. Nothing was sent to any model endpoint and OpenCode was never run. The only network use was the clone and pinned npm tarballs for offline tests.

## 1. Pin

| Item | Value |
|---|---|
| Upstream | `https://github.com/anomalyco/opencode` (`sst/opencode`, the HS-1g remote, now redirects here) |
| Tip SHA | **`350c726aa8b6b11eb9242040bc5eb7ae837fbf8a`** (2026-09-16T13:44:33Z, "chore: generate") |
| Versions | `packages/opencode` 1.18.31, `@opencode-ai/plugin` 1.18.31, `ai` 6.0.168, `@ai-sdk/openai-compatible` **2.0.41** (+ provider 3.0.8, provider-utils 4.0.23 per `bun.lock`) |
| Distance from HS-1g pin | 700 commits after `4bffbb655` (the old pin is an ancestor) |
| Licence | **MIT** (`LICENSE`, "Copyright (c) 2025 opencode"); `packages/plugin` also MIT |
| Clone | `/mnt/raid0/llm/harness/opencode` (blobless clone, not vendored into any repo) |
| SDK local patch | `patches/@ai-sdk%2Fopenai-compatible@2.0.41.patch` changes only stream error propagation (`error.message` → `error`). It does not touch body construction. |

All `path:line` below are relative to `packages/opencode/src/` at `350c726aa` unless another package is named.

## 2. Lever and wire shape (why the plugin works)

1. `session/llm/request.ts:114-131`: every request prepared by `LLM.Service` triggers `chat.params` with `{sessionID, agent, model, provider, message}`. The hook's `output.options` object is used as the request options.
2. `session/llm.ts:316`: `providerOptions: ProviderTransform.providerOptions(model, options)`.
3. `provider/transform.ts:1450-1465`: for `@ai-sdk/openai-compatible` the namespace is `providerID.split(".")[0]`. The SDK is built with `name: model.providerID` (`provider/provider.ts:1835,1858`), and the SDK derives its key the same way (`openai-compatible-chat-language-model.ts:103-105`), so the two always match.
4. `@ai-sdk/openai-compatible@2.0.41`, `src/chat/openai-compatible-chat-language-model.ts:231-240`: the namespace object is **spread into the top level of the JSON body**. Only its schema keys `user`, `reasoningEffort`, `textVerbosity` and `strictJsonSchema` are removed and mapped. There is no camelCase conversion. The spread comes after `model`/`max_tokens` and before `messages`/`tools`.
5. **Proven offline:** `harness/opencode-plugin/test/wire-contract.test.ts` drives the real 2.0.41 SDK with a capturing fake `fetch`, through `doGenerate` and `doStream`. `x_session_id`, `x_user_id`, `x_tool_mode` and static keys arrive top-level and unrenamed, with no nested namespace object.

The HS-1g traps still hold at this tip:
- **models.dev-mode camelCasing** of `provider.body` (`provider/provider.ts:1334,1349-1353`). It does not apply to config-defined models.
- **Provider-level `options`** configure the SDK only (baseURL, timeouts) and never reach the body.

The template keeps every `x_*` key in the plugin, and the config lint refuses `x_*` under provider or model `options`.

## 3. Call-verb matrix (HS-1g form)

Lever = the `epyc-orchestrator` plugin's `chat.params` (`x_session_id`, `x_user_id`, `x_tool_mode="client"`, static `x_*`). Anchors are `opencode@350c726aa`.

| # | Egress (request path) | Class | Default? | Call verb → body | Lever | Disabled by our config? | Residual risk |
|---|---|---|---|---|---|---|---|
| E1 | Main agent loop: `SessionPrompt` → `SessionProcessor.process` → `LLM.stream` (`session/processor.ts:654`) | main loop | yes | `streamText` (`session/llm.ts:280`) | **HONOURED** (`llm/request.ts:114`) | n/a (required) | none at source; P0.4 confirms live |
| E2 | Retries: `Effect.retry(SessionRetry.policy)` (`session/processor.ts:674`); up to 5 (`session/retry.ts:31`) on 429/5xx/network patterns | retry | yes | re-runs `llm.stream(streamInput)` → `prepare` → hook fires again | **HONOURED** | no (wanted) | same model, same body. The orchestrator must treat a retried turn as a resend: 503 from admission control will be retried with backoff and honours `retry-after` (`retry.ts:47-78`). AI SDK `maxRetries` is `input.retries ?? 0` (`llm.ts:323`), so it is 0 on the main loop. |
| E3 | Title: `SessionPrompt.ensureTitle` → `LLM.stream({small:true})` (`session/prompt.ts:226-235`, `retries: 2`) | auxiliary | yes | `streamText` | **HONOURED**, a **change since HS-1g**: the title call now goes through `prepare`, so `chat.params` fires with the real session id; `smallOptions` is only the base (`llm/request.ts:84-91`) | **yes**: `agent.title.disable:true` → `agents.get("title")` returns nothing → early return (`prompt.ts:216-217`); `small_model` = the orchestrator model | none while disabled. If re-enabled it is keyed, and AI SDK retries (2) resend with the same body. |
| E4 | Auto-compaction: overflow → `compaction.create({auto:true})` (`prompt.ts:1164-1166`, `:1321-1327`) → `processor.process` (`session/compaction.ts:358,425`) | compaction | yes (upstream default `auto:true`) | `streamText` via E1 machinery | **HONOURED** | **yes**: `compaction.auto:false` makes `isOverflow` return false (`session/overflow.ts:28`). A provider `ContextOverflowError` then ends the turn instead of compacting (`processor.ts:621-627`). Belt-and-braces: `OPENCODE_DISABLE_AUTOCOMPACT=1` (`config/config.ts:593`). | long sessions surface `ContextOverflowError`, so server-side folding (HS-4 P1) is required. Exception: the check skips when the failing message is itself a summary (`processor.ts:622`), which only arises inside a user-triggered compaction. |
| E5 | Manual compaction (`/compact`, `session.summarize`) | compaction | user action | same as E4 | **HONOURED** | not disabled (user-invoked) | keyed, so the orchestrator sees it. Advise operators not to use it once P1 lands. |
| E6 | Prune (`compaction.prune`) | none (no LLM call) | off upstream (`prune` default false) | n/a | **N/A** | `prune:false` + `OPENCODE_DISABLE_PRUNE=1` | none |
| E7 | Sub-agents: `task` tool → child session → E1 (`tool/task.ts:92-230`) | sub-agent | model-initiated | `streamText` | **HONOURED**, but `x_session_id` = the **child** session id (the hook input has no parent id; the `x-parent-session-id` header is set, `llm/request.ts:201`) | **yes, three layers**: `permission.task:"deny"` removes the tool (`llm/request.ts:208-214`); `subagent_depth:0` makes `task` fail at depth 0 (`task.ts:111`); `agent.general/explore.disable` removes the targets | none while disabled |
| E8 | User-typed `@agent` / `subtask` command → `handleSubtask` (`prompt.ts:255-331`) | sub-agent | user action | E7 with `bypassAgentCheck:true` (`prompt.ts:331`) | **HONOURED** (child id, as E7) | **yes** via `subagent_depth:0` and disabled sub-agents. **`permission.task:"deny"` alone does NOT stop this path** (new finding). | none with the full template. The lint refuses a config without all three. |
| E9 | Background sub-agents (`task` with `background:true`) | sub-agent | no (`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`, `task.ts:98-102`) | E7 | HONOURED | yes (flag unset/0, task denied) | none |
| E10 | Project-copy name generation `POST /experimental/project/:id/copy/generate-name` (`server/routes/instance/httpapi/handlers/project-copy.ts:34-52`); caller: TUI "move to copy" (`packages/tui/src/component/prompt/move.tsx:36`) | auxiliary | user action (TUI move) | `LLM.stream({small:true})` → `streamText` | **HONOURED**, but with a **synthetic** `SessionID.descending()` (`project-copy.ts:33`), so `x_session_id` names no real session. **New since HS-1g.** | not disableable by config; only reachable from the TUI move/copy flow | low: a keyed request with an orphan session id. The orchestrator should tolerate an unknown `x_session_id` (create-on-first-use) and not treat it as a memory owner. |
| E11 | `opencode agent create` → `Agent.generate` → `generateObject` (`agent/agent.ts:435`; OpenAI-OAuth branch `streamObject`, `:420`) | auxiliary | explicit CLI command only | `generateObject` **without `providerOptions`** | **SILENT-NO-OP** (unchanged from HS-1g) | not config-disableable; do not run `opencode agent create` against `:8000` | it still reaches our router (default model), but with no `x_*` keys. Operator guidance only. |
| E12 | **v2 session runner**: `packages/core/src/session/runner/llm.ts:205-219` (`LLM.request` → `LLMClient.stream`), plus its own compaction (`packages/core/src/session/compaction.ts:203,232-233`); exposed at `POST /api/session/:sessionID/prompt` (`packages/protocol/src/groups/session.ts:205`, handler `packages/server/src/handlers/session.ts:140`, mounted by `server/routes/instance/httpapi/server.ts:299-303`) | main loop (v2) | **not by any in-tree client**: TUI (`packages/tui/src/component/prompt/index.tsx:1094`), `opencode run` (`cli/cmd/run.ts:864`) and ACP (`acp/service.ts:525`) all use the v1 `session.prompt` | `LLMClient` directly; request built with fixed `providerOptions: {openai: {promptCacheKey}}` | **SILENT-NO-OP**: no plugin hook on this path. **It already existed at `4bffbb655`, and HS-1g missed it.** | no config switch; our config uses no client that calls it | **Watch item.** Any future client or release that moves prompting to `/api/session/*/prompt` silently drops every `x_*` key. The v2 path does send `X-Session-Id`/`x-session-affinity` headers. See §5 for the orchestrator tripwire. |
| E13 | Native LLM runtime (`session/llm.ts:226-269`, `llm/native-runtime.ts:50-72`) | runtime swap | no (`OPENCODE_EXPERIMENTAL_NATIVE_LLM`, default false; not implied by `OPENCODE_EXPERIMENTAL`, `effect/runtime-flags.ts:54`) | `LLMClient`; receives `prepared.params.options` | UNVERIFIED (would need `@opencode-ai/llm` body audit) | yes: flag unset, **and** the gate refuses any provider other than `openai`/`anthropic`/`opencode*` (`native-runtime.ts:55-56`); our ID is `epyc-orchestrator` | the HS-4 flip condition ("native gate widened to custom providers") has **not** happened at this tip. Re-check on every bump. |
| E14 | MCP sampling (server-initiated LLM calls) | auxiliary | no | client capability commented out (`mcp/index.ts:42`) | **N/A** | n/a | none |
| E15 | GitLab Workflow model (`llm.ts:105-206`) | vendor | only for that provider | vendor websocket | N/A | `enabled_providers` = ours only | none |

**Verdict: all default egress paths honour the lever, as at HS-1g.** With the P0.3 template:
- E3, E4, E7, E8 and E9 are disabled.
- E1, E2 and E5 are keyed.
- E10 is keyed, with a synthetic id.
- E11 and E12 are the two silent-no-op paths. Neither runs from our configured clients.

**No flip to pi is triggered.** The native gate is still closed to custom providers, and `chat.params` keys still land at the top level (proven offline in §2.5).

### 3.1 Tool-argument stamping (`tool.execute.before`)

| Path | Hook fires? | Name the hook sees | Arg mutation reaches the call? |
|---|---|---|---|
| MCP tools (`session/tools.ts:390-409`) | yes, before permission ask and execute | `sanitize(server) + "_" + sanitize(tool)` (`mcp/catalog.ts:117-119`) | **only in place**: the hook gets `{ args }` and `execute(args, opts)` uses the local binding, so reassigning `output.args` is a silent no-op. The plugin mutates in place, and a test pins this. |
| Code-mode MCP calls (`tool/code-mode.ts:134-150`, experimental and off; `tools.ts:388`) | yes, same key | same | in place (`input.args`) |
| Built-in tools (`tools.ts:92-133`) | yes | tool id | not stamped (prefix mismatch) |

So a stamp prefix is an **MCP server name plus `_`**. `orchestrator_` matches every tool of an MCP server named `orchestrator` (for example `orchestrator_orchestrator_chat`), and `memory_` matches a future `memory` server.

**Server-side residual:** the orchestrator's FastMCP (`mcp` 1.27.0 in the orchestrator venv) validates with a pydantic `ArgModelBase` that has no `extra="forbid"` (`mcp/server/fastmcp/utilities/func_metadata.py:47`). An **undeclared `session_id` is silently dropped**, so each `orchestrator_*`/`memory_*` tool that needs the session must declare a `session_id` parameter (P2/P3 work; done: orch `54b6439d` / `ed554da2`). *Correction 2026-09-17: the "silently dropped" claim is wrong at our pin. The orchestrator pins `fastmcp>=3,<4` (`pyproject.toml`), and FastMCP 3.x REFUSES a call carrying an undeclared argument rather than dropping it; `tests/unit/test_mcp_undeclared_args_refused.py` pins that behaviour. The conclusion stands for the opposite reason: a stamped `session_id` on a tool that does not declare it fails the call, so every stamped tool must declare it. All `@mcp.tool()` functions in `src/mcp_server.py` now do (`54b6439d`).*

## 4. "No model-fallback" grep

- **Commands:**
  - `grep -rniE 'fallback' session/ provider/ agent/ tool/task.ts packages/llm/src/route`
  - `grep -rniE 'fallback_?model|model_?fallback|fallbackModels?|fallbackChain|alternateModel|nextModel|failover'` across `packages/` (excluding tests and node_modules).
- **Session layer:** the only hits are a log label (`compaction.ts:259`), the native-runtime comment (`llm.ts:225`) and a GCP env note (`provider.ts:512`). None of them chooses a model.
- **Retry:** `session/retry.ts` is same-model backoff. `policy()` returns only a delay (`:183-207`), and the processor retries the same `streamInput`.
- **Selection-time defaults (not runtime fallback):**
  - `Provider.defaultModel` (`provider.ts:2008-2040`): config `model`, then recent, then the first configured provider.
  - `getSmallModel` (`:1939-2006`): `small_model`, then the plugin hook, then a family list **within the same provider**.
  - TUI `fallbackModel` (`packages/tui/src/context/local.tsx:197-231`): picks a model at startup when none is valid.
  - v2 `ModelSwitched` (`packages/core/src/session.ts:402-415`): an explicit user switch.
  - With `enabled_providers:["epyc-orchestrator"]`, `model` and `small_model` pinned, none of these can reach another provider.
- **Built-in plugin hooks:** the codex, copilot and cerebras `chat.params`/`chat.headers` hooks are each provider-scoped (`plugin/openai/codex.ts:559-573`, `plugin/github-copilot/copilot.ts:340-360`, `plugin/cerebras.ts:5-9`). The template also sets `OPENCODE_DISABLE_DEFAULT_PLUGINS=1`.

**Result: no automatic fallback router exists at `350c726aa`.** A request is never re-sent to a different provider or model.

## 5. Findings that change P0 work

1. **Plugin load failure fails open upstream.** A plugin that throws during init is only logged (`plugin/index.ts:222-240`), and `OPENCODE_PURE` skips all external plugins (`:181`).
   - **Mitigation in the plugin:** `server()` never throws. A bad configuration makes our provider's `chat.params` and stamped tool calls reject, so the turn errors visibly (unit-tested).
   - **Residual:** a plugin that is **absent** (wrong path, `OPENCODE_PURE`) still sends unkeyed requests.
   - **Recommended P0.2 tripwire (orchestrator side):** when a request carries `User-Agent: opencode/…` or `X-Session-Id` but no `x_session_id` body key, refuse it with 422. This also covers E11 and E12.
   - **Landed (2026-09-17 note):** orch `ed554da2`, feature flag `v1_client_session_guard` (registry default on), guard in `src/api/routes/openai_compat.py`.
2. **`:8000` currently drops unknown `x_*` keys silently.** `OpenAIChatRequest` uses pydantic's default `extra="ignore"`, and only `response_format` has an explicit refusal (`src/api/models/openai.py:41`). Until P0.2 types `x_session_id`/`x_user_id`/`x_tool_mode`, the plugin's keys are accepted and ignored (done: orch `54b6439d` / `ed554da2`). P0.4 must run after P0.2.
   - **Landed (2026-09-17 note):** typed keys `x_session_id`/`x_user_id`/`x_memory`/`x_tool_mode` in `src/api/models/openai.py` (orch `ed554da2` + `b44ab3a8`), 422 on bad values. Unknown `x_*` keys outside that set are still ignored (`extra="ignore"` unchanged).
3. **`permission.task:"deny"` does not close user-typed `@agent` subtasks (E8).** The template adds `subagent_depth:0` and disables `general`/`explore`, and the lint enforces all three.
4. **HS-1g missed the v2 session runner (E12).** Add "v2 `/api/session/*/prompt` still unused by TUI/run/ACP" to the per-bump checklist.
5. **Title is now keyed (E3).** The HS-1g "title call swaps in `smallOptions`" caveat no longer applies. It is disabled anyway.

## 6. Coverage summary

| Path | Covered (keys reach body) | Disabled by P0.3 config | Residual |
|---|---|---|---|
| E1 main loop | yes | — | none at source; P0.4 live check |
| E2 retries | yes | — | resend semantics on 5xx |
| E3 title | yes | yes | none |
| E4 auto-compaction | yes | yes | needs P1 server-side folding |
| E5 manual compaction | yes | no (user action) | operator guidance |
| E6 prune | n/a | yes | none |
| E7 task sub-agents | yes (child id) | yes | none |
| E8 `@agent` subtasks | yes (child id) | yes (depth 0 + disabled agents) | none with full template |
| E9 background sub-agents | yes | yes | none |
| E10 project-copy naming | yes (synthetic id) | no | orphan session id |
| E11 `agent create` | **no** | no (CLI command) | do not run it against `:8000`; P0.2 tripwire |
| E12 v2 session runner | **no** | not used by our clients | per-bump watch; P0.2 tripwire |
| E13 native runtime | unverified | yes (flag + provider gate) | per-bump watch |
| E14 MCP sampling | n/a | not implemented | none |
| E15 GitLab workflow | n/a | provider not enabled | none |
| MCP tool stamping | yes (in place) | — | server tools must declare `session_id` |

**Per-bump checklist** (extends HS-1g for OpenCode):
- re-run E1–E15;
- `native-runtime.ts` provider gate;
- `openai-compatible` version and its `getArgs` spread;
- no in-tree caller of `/api/session/*/prompt`;
- `tools.ts` hook-then-execute binding;
- `mcp/catalog.ts` `toolName`;
- plugin load failure handling;
- the no-fallback grep.

## 7. Deliverables (root repo)

| Path | What |
|---|---|
| `harness/opencode-plugin/src/index.ts` | Plugin module: default export `{ id: "epyc-orchestrator", server }`; fail-closed hooks |
| `harness/opencode-plugin/src/lib.ts` | Pure logic: option parsing and validation, `chat.params` keys, in-place arg stamping |
| `harness/opencode-plugin/src/config-lint.ts`, `scripts/lint-config.ts` | P0.3 acceptance "config lint (all required keys present)", for config and env file |
| `harness/opencode-plugin/config/opencode.jsonc.template` | Custom-provider config. Required keys: `baseURL`, `compaction.auto/prune:false`, `share:"disabled"`, `autoupdate:false`, `small_model`, `permission.task:"deny"`, `skills.paths`. Plus: title and sub-agents disabled, `subagent_depth:0`, `enabled_providers`. |
| `harness/opencode-plugin/config/opencode.env` | `OPENCODE_DISABLE_{MODELS_FETCH,AUTOUPDATE,SHARE,CLAUDE_CODE,EXTERNAL_SKILLS,AUTOCOMPACT,PRUNE,DEFAULT_PLUGINS,LSP_DOWNLOAD}`; warns against `OPENCODE_PURE` and native LLM |
| `harness/opencode-skills/` | The versioned in-repo skills folder (empty) |
| `harness/opencode-plugin/test/*.test.ts` | Offline tests (below) |

The container or worktree jail from the P0.3 spec is a launch concern and is not built here. The template relies on it for `external_directory`.

## Tests

OpenCode ships no public plugin test harness: `packages/plugin` has no tests, and `packages/opencode/test` builds the full Effect service graph. The tests therefore mock the exact call sites quoted in §2–§3.1 and use `node:test` with Node ≥ 22.18 type stripping. There are no dependencies.

```bash
cd harness/opencode-plugin
node --test 'test/*.test.ts'                       # 38 pass, 2 skipped (wire contract needs the SDK)
node scripts/lint-config.ts config/opencode.jsonc.template config/opencode.env   # PASS
# Wire contract against the OpenCode-pinned SDK (offline; fake fetch):
D=/mnt/raid0/llm/harness/audit-deps/typecheck      # any scratch dir outside the repo
npm --prefix "$D" install --ignore-scripts --save-exact \
  @ai-sdk/openai-compatible@2.0.41 @opencode-ai/plugin@1.18.31 typescript@5.9.3 @types/node@22.18.0
EPYC_OPENCODE_CONTRACT=1 EPYC_OPENCODE_SDK_DIR="$D" node --test 'test/*.test.ts'   # 40 pass, 0 skipped
# EPYC_OPENCODE_CONTRACT=1 without the SDK FAILS (no vacuous pass).
```

- **Recorded 2026-09-16:** 40/40 with the contract enabled; 38 pass + 2 skip without it.
- **Typecheck:** `tsc` 5.9.3 against `@opencode-ai/plugin@1.18.31` exits 0.
- **Negative control:** a deliberate `input.tool: number` error is reported (TS2322), so the hook types really resolve.
- **Contents:**
  - option validation (unknown options, provider-ID shape, static-key namespace and collisions);
  - provider scoping;
  - in-place mutation for both hooks;
  - overwriting a model-supplied `session_id`;
  - fail-closed behaviour on bad configuration;
  - loader module shape;
  - 20 config-lint mutations;
  - env-file lint;
  - the wire contract (`doGenerate` and `doStream`).

## Addendum P0.3b: User-Agent marker for the `/v1` session guard

The P0.1/P0.2 session guard returns 422 for an OpenCode request with no `x_session_id`. It recognises OpenCode by a User-Agent containing `opencode` or by `x_tool_mode=client`. Measured against the pinned SDK with a fake fetch (node 22):

| Call | User-Agent on the wire |
|---|---|
| Session call (E1–E5, E7–E10). `session/llm/request.ts:196-200` sets `User-Agent: opencode/<build>` per call, with or without the plugin | `opencode/1.18.31 ai-sdk/provider-utils/4.0.23 runtime/node.js/22` (the call-level value replaces the provider header and the SDK's provider suffix) |
| SDK call with no call-level headers (E11 `agent create`; any plugin-less path outside `prepare`), **without** the template header | `ai-sdk/openai-compatible/2.0.41 ai-sdk/provider-utils/4.0.23 runtime/node.js/22`: **no marker**, so the guard cannot fire |
| Same call **with** `provider.options.headers["User-Agent"] = "opencode/1.18.31 epyc-orchestrator"` | `opencode/1.18.31 epyc-orchestrator ai-sdk/openai-compatible/2.0.41 ai-sdk/provider-utils/4.0.23 runtime/node.js/22` |

- **Template:** now sets that header.
- **Config lint:** requires exactly one `User-Agent` matching `^opencode/X.Y.Z epyc-orchestrator$`.
- **Tests:**
  - `test/wire-contract.test.ts` checks both wire rows above, using the header from the shipped template.
  - A mutation run with the header removed fails, as expected.
  - Results: 45/45 with `EPYC_OPENCODE_CONTRACT=1`; 41 pass + 4 skip without the SDK.
- **Still uncovered:** E12, the core v2 runner, uses `LLMClient`, not this SDK instance, so the template header is not shown to reach it. It remains a per-bump watch item.

## Addendum 2026-09-24: `opencode run` as a headless actor — measured pitfalls

The AutoKernel loop drives `opencode run` (1.18.31, same pin as above) headless as its planner/author seat
(research `scripts/kernel_rnd/autokernel/loop/actors.py`, main `21ca61b0`). The DS41 campaign found six ways
that invocation fails silently, and one behaviour to design around (rows 8-10, added later on 2026-09-24,
record the plain seat's tool surface and the export's observability limits). Each one looks like a model failure
(empty, truncated, quoted or abstaining reply) and is not one. Any launcher that runs `opencode run` headless —
HS-4 shells, scripts, other loops — inherits all of them.

| # | Pitfall | Evidence | Do this |
|---|---|---|---|
| 1 | **A positional prompt is re-quoted.** `run` joins its positionals as `arg.includes(" ") ? "\"" + arg.replace(/"/g, '\\"') + "\"" : arg` (`packages/opencode/src/cli/cmd/run.ts:288-290` at `350c726aa`). Any prompt containing a space reaches the model wrapped in quotes, with every inner quote backslash-escaped. | The DS41 run-7 planner prompt arrived with 2,982 escaped quotes, all in its JSON. | Pass the prompt on **stdin**. Piped stdin is read with `Bun.stdin.text()` and merged unchanged (`run.ts:416`). This also keeps a ~100 KB prompt clear of the kernel's 128 KiB per-argument limit. Reference: `actors.py` `Backend.argv` / `Backend.stdin_payload`. |
| 2 | **Bun exits without draining a stdout pipe.** | The same `opencode export` read 65,536 or 98,304 bytes through a pipe, and 328,871 bytes when written to a file. | Capture stdout and stderr to **files**, never pipes. The reply is the tail of stdout, so a truncated pipe loses exactly the JSON the caller needs. Reference: `actors._run_agent` (`tempfile.TemporaryFile`). |
| 3 | **An agent `prompt` REPLACES the system prompt.** `session/llm/request.ts:60` uses `agent.prompt` *instead of* `SystemPrompt.provider(model)`. | With guidance supplied as an agent `prompt`, the 27B decoded a median 1,626 tokens per step against 266 on the default prompt (~6x), and filled its 98k slot in 12 steps. | Put guidance in top-level **`instructions`** files, which are appended to the default system prompt. Reference: `actor_opencode_config.write_actor_config` (v2). |
| 4 | **Compaction summaries go to stdout and quote the prompt.** When a session compacts, opencode prints its self-summary, and that summary quotes the reply template, e.g. `{"abstain":"<reason>"}`. | The bounded-v1 A/B driver recorded exactly that template echo as its "hypothesis". | Never take the first or last JSON object on stdout at face value. Refuse objects whose values are the template's own placeholders. Reference: `actors._is_template_echo` / `_extract_json`. |
| 5 | **rc=1 with a complete reply.** After an internal error in its own bash tool (`(res.stderr \|\| "").trim is not a function`, triggered by `mkdir -p $HOME/...` probes) that the agent recovered from, `run` exits 1 while stdout holds a complete, schema-valid answer. | Run 7's first 27B proposal (39 min) was discarded unread and retried from zero. | Salvage a non-zero exit only when rc > 0 AND the reply is complete for your schema. A signal death (rc < 0) never finished its work. Reference: `actors._run_agent`. |
| 6 | **`hidden: true` hides nothing from the model.** In the TUI it only filters the agent lists (`packages/tui/src/context/local.tsx:78-79`). | — | Restrict agents through `permission` (`task`, `edit`, tool globs), not `hidden`. |
| 7 | **An offered subagent is not a used one.** | The 27B planner, given an allowed `task` tool plus fan-out guidance, made 0 scout calls in 69 bounded steps (DS41-C20c). | Do not count on model-initiated fan-out. Fan-out is the orchestrator's decision (see [`agent-loop-design.md`](../../guides/agent-workflows/agent-loop-design.md) → *Who owns fan-out and context*). |
| 8 | **Bare `opencode run` has no MCP server; out-of-tree reads ride on `--auto`.** With no `OPENCODE_CONFIG`, the global config has no `mcp` block. `external_directory` defaults to `ask`, and `--auto` approves every non-denied ask. | The plain DS41 seat used only `bash`/`read`/`grep`/`glob` (C20c export: 25 calls, 0 MCP). Run 8 read the anchor tree and `/tmp` from a lane `--dir`. A read-only critic (no `--auto`) cannot. | Hand a plain seat context as FILES, not MCP tools. Grant out-of-tree reads explicitly rather than by blanket approval (research `ce5800cb`). |
| 9 | **`opencode export` has per-step tokens, but no per-tool latency, no per-step wall and no compaction step.** A `compaction` part carries only `tail_start_id`. | Research `0bf2d7c2` `actor_metrics.py` against the real C20c export. | Report tool time as "unknown", or derive it from step timestamps; never report zero. |
| 10 | **`opencode session list` has no parent/child link.** | Same. | Snapshot sessions before the call; scouts = sessions new since then; primary = most steps. |

**Verify a per-run config with no model call.** Run each of these with `OPENCODE_CONFIG=<file>` set:
- `opencode debug config` prints the merged configuration. The per-run file is merged OVER
  `~/.config/opencode/opencode.jsonc`, so check the result, not the file.
- `opencode debug agent <name>` prints one agent's resolved permissions and prompt.
- `opencode mcp list` shows whether each configured MCP server starts.

The commands live at `cli/cmd/debug/config.ts`, `cli/cmd/debug/agent.ts` and `cli/cmd/mcp.ts`.

**Where these came from:** `handoffs/active/deepseek-v41-flash-evaluation.md` DS41-C20 (and its C20c A/B), and
HS-4 P7 in `handoffs/active/harness-selection-and-integration.md`, which carries the repo-wide stdin audit.
