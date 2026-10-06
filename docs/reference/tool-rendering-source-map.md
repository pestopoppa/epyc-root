# Tool-call rendering source map (TU-HR-1 static substep)

**Status:** MAIN accepted source-only map, 2026-10-06. It completes a static routing/code slice; TU-HR-1 remains OPEN until the template identity and behavior for each actually served model are verified. This check made no model calls and did not query a running endpoint.

## Source identity and custody

All statements below were checked against Git blobs at the published revisions, not inferred from whichever shared clone happened to be checked out. Selected source paths were clean in their shared worktrees when inspected. The expanded 35-path app/root/frozen source inventory is in [`tool-rendering-static-35-source-inventory.json`](../../artifacts/ni07/tool-rendering/tool-rendering-static-35-source-inventory.json); native catalog source custody is in [`dtap-tool-rendering-readset.json`](../../artifacts/ni07/tool-rendering/dtap-tool-rendering-readset.json). Source revision does not identify the active process, model file, server flags, provider, or live chat template.

- epyc-root: `4c0c653baf1654c8c25c66433cf39c8faefd8e52`; [TU-HR-1 row](https://github.com/pestopoppa/epyc-root/blob/4c0c653baf1654c8c25c66433cf39c8faefd8e52/handoffs/active/tool-use-eval-contract.md#L399).
- epyc-orchestrator: `7d3b840a6f5770679a55846931ceaf3d6d74e904`.
- epyc-llama production `production-consolidated-v10`: `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, reachable as an ancestor of the published EPYC fork branch `ak/champion/llama-cpp-ffc1bac82eec` (remote `pestopoppa/llama.cpp`; branch tip `b0ba1d42783585e15b0a0464715fd1fb6a808888`). The upstream `ggml-org` URL is not used because this is an EPYC-specific commit. No frozen-tree writes or builds were performed.

## Request and rendering paths

### DTAP disposable runner

At the app pin, `CaseRegistry` reads a case from `cases.json`; `render_messages()` selects `Agent.system_prompt`, `Task.task_instruction`, and fixed prompt-family attack text. The imported case `Agent` records include `mcp_servers` metadata, but the runner does not turn it into a function-schema catalog. `harness/utils.py` uses that field to resolve task configuration environment variables; `env_state.py` and the shims support fixture-backed state and judges. The system prompts contain natural-language statements that the agent can use tools, but those are text instructions, not structured native tool definitions.

`run_case()` calls `endpoint.complete(messages, seed=seed)`. `ChatEndpoint.complete()` sends an OpenAI-compatible body with `model`, `messages`, `temperature`, and `max_tokens`; no `tools`, `tool_choice`, or orchestrator-specific tool-mode field is sent. `ChatEndpoint._parse()` can consume `message.tool_calls` if a server returns them, but this response parser does not advertise any tools to the server. A returned call is recorded; in live mode the runner does not execute service effects and records a generic `ok` placeholder, while the dry-run stub replays the fixture script. No per-case tool allow-list is enforced on live returned calls in this source path. This placeholder is not a validated service result or environment-state transition.

Pinned sources: [DTAP case/prompt renderer](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/scripts/autopilot/evals/dtap/harness/runner.py#L105), [runner endpoint request and live/dry-run split](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/scripts/autopilot/evals/dtap/harness/runner.py#L327), [endpoint request body](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/scripts/autopilot/evals/dtap/harness/endpoint.py#L47), [response parser](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/scripts/autopilot/evals/dtap/harness/endpoint.py#L133), [fixture environment](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/scripts/autopilot/evals/dtap/harness/env_state.py#L31), [MCP environment lookup](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/scripts/autopilot/evals/dtap/harness/utils.py#L60), [case registry](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/scripts/autopilot/evals/dtap/cases.json#L1).

### Orchestrator OpenAI-compatible endpoint

The orchestrator request model makes `tools` optional. `x_tool_mode` absent selects the default REPL mode. In that mode, caller-provided native tool definitions are translated into prompt text instructing the orchestrator's own REPL bridge (`CALL(...)`); `tool_choice` is advisory prompt text. The default REPL prompt also inserts the orchestrator's own text tool-definition block, resolved by `PromptBuilder._resolve_tools()`. That default prompt/catalog belongs to the orchestrator agent and is not a native tool schema for the DTAP agent. Its tools execute inside the orchestrator's REPL; the DTAP runner receives an assistant response, not the orchestrator's internal calls as `message.tool_calls`.

The separate `x_tool_mode="client"` path keeps tool execution with the caller: request schemas and history go through the client-mode path, and the expected response includes structured tool calls. Therefore, the absence of `tools` in DTAP's request cannot be filled by assuming that the orchestrator's default internal REPL tools are native calls made by the evaluated agent.

Pinned sources: [OpenAI request fields and mode semantics](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/api/models/openai.py#L146), [native tool prompt rendering](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/api/routes/openai_compat.py#L309), [mode selection and client branch](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/api/routes/openai_compat.py#L1240), [default REPL tool prompt resolver](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/prompt_builders/builder.py#L162), [root prompt includes its own tool text](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/prompt_builders/builder.py#L233), [request tool metadata contract](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/api/routes/openai_compat.py#L403).

### Orchestrator backend forwarding

For its client-tool request path, the llama-server backend receives a structured chat payload and explicitly forwards `messages`, `tools`, and `tool_choice` to `/v1/chat/completions`. It adds the per-call or per-role `chat_template_kwargs`. Returned `message.tool_calls` are parsed into the orchestrator's structured result.

The other inspected `src/backends/openai.py` payload builder sends model/messages/generation options and role `chat_template_kwargs`; it does not serialize `InferenceRequest.chat_payload`, `tools`, or `tool_choice`. The source at this pin therefore does not establish native tool-schema forwarding through that backend. Backend selection and actual role routing must be included in any per-model static route table; don't treat the shared OpenAI-compatible API as proof that every backend transmits tools.

The role/server registry is [`orchestration/model_registry.yaml`](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/orchestration/model_registry.yaml#L1679), with loader selection and role-specific `server_mode.<role>.chat_template_kwargs` access in [`registry_loader.py`](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/registry/registry_loader.py#L567). These are config-time sources; the inspected code does not prove which registry file or values a running process loaded.

Pinned sources: [inference chat payload construction](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/llm_primitives/primitives.py#L767), [payload carried into inference](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/llm_primitives/inference.py#L1062), [llama-server payload forwarding](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/backends/llama_server.py#L753), [llama-server returned tool-call parsing](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/backends/llama_server.py#L855), [per-role template kwargs loader](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/registry/registry_loader.py#L567), [OpenAI provider payload builder](https://github.com/pestopoppa/epyc-orchestrator/blob/7d3b840a6f5770679a55846931ceaf3d6d74e904/src/backends/openai.py#L223).

## Which component chooses the token format?

For a direct llama-server request, the API tool schema is input data; llama-server applies the chat template. At the frozen production source pin, the server docs say the default template comes from model metadata and permit overrides with `--chat-template` or `--chat-template-file`; `--jinja` selects the Jinja engine. The server creates its template object from the loaded model and configured override, merges request `chat_template_kwargs`, then applies the template to messages and tool inputs. The effective, loaded template plus launch flags is therefore the token-format authority for a local GGUF route. The role registry only supplies request kwargs such as `enable_thinking`; it does not prove which template bytes the server loaded.

Pinned sources: [llama-server Jinja and template flags](https://github.com/pestopoppa/llama.cpp/blob/ffc1bac82eeca6f9099e1ccd9ba49703c460a115/tools/server/README.md#L223), [template defaults/overrides](https://github.com/pestopoppa/llama.cpp/blob/ffc1bac82eeca6f9099e1ccd9ba49703c460a115/tools/server/README.md#L228), [template initialization from model and options](https://github.com/pestopoppa/llama.cpp/blob/ffc1bac82eeca6f9099e1ccd9ba49703c460a115/tools/server/server-context.cpp#L1520), [request kwargs merge and template application](https://github.com/pestopoppa/llama.cpp/blob/ffc1bac82eeca6f9099e1ccd9ba49703c460a115/tools/server/server-common.cpp#L1073).

For non-llama remote providers, the provider's serving stack and selected model template own rendering. Orchestrator registry kwargs are parameters passed along where supported; they are not evidence of the provider's actual template. No model-specific template identity or behavior can be inferred from the Python route alone.

## Source-backed gap and scope boundary

The DTAP cases do provide natural-language tool instructions in their system prompts, and their `mcp_servers` records are not empty. That is not the same as sending OpenAI function schemas. In the inspected runner, `render_messages()` reads prompt text; no runner function turns those MCP descriptors into a structured case tool catalog. `ChatEndpoint` sends no tool fields or orchestrator client-mode selector. Thus the verified gap is specifically **missing structured tool advertisement and explicit endpoint tool mode on the DTAP live request**, not missing all textual tool instructions.

The gap is consequential under both possible endpoint classes:

- A direct OpenAI-compatible model server receives no `tools`/`tool_choice`; its returned `tool_calls`, if any, were not grounded in an advertised per-case contract.
- The orchestrator endpoint with default `x_tool_mode` uses its internal REPL/text tools; DTAP expects native `message.tool_calls` and does not run the orchestrator's internal tool side effects as the evaluated agent's trajectory.

Also, current DTAP live mode records returned calls but does not execute the environment effects through its shims. It appends a generic `ok` tool message for the next turn. So fixing schema advertisement alone would establish only request/response plumbing; it would not complete TU-DTAP-2 or make a live state-judged tool-use result valid.

## Medium implementation proposal (review only)

The isolated MEDIUM implementation scope is approved; source candidates and fake CI remain subject to MAIN acceptance. This map provides no implementation or runtime acceptance.

1. Add a harness-owned sidecar such as `scripts/autopilot/evals/dtap/harness/tool_schemas.json`, keyed by case ID, that carries each case's `native_tools` list in the standard OpenAI function schema; derive the exact allowed-name set from that sidecar. Keep upstream `cases.json` bytes and judge provenance unchanged. Do not infer a function signature from `Agent.mcp_servers`, which is server/environment metadata. Keep the public tool schema separate from hidden judge/reference data and credentials.
2. Extend `ChatEndpoint.complete()` with optional `tools`, `tool_choice`, and explicit endpoint mode. Preserve current request bodies when the optional contract is absent. For direct model servers, send the standard fields. For the orchestrator API, explicitly set `x_tool_mode="client"`; never rely on its default REPL mode when the runner expects structured `tool_calls`.
3. Pass the per-case contract from `run_case()` to the endpoint. Reject malformed arguments and undeclared tool names before recording an accepted call. Record a schema digest, advertised names, endpoint mode, tool-choice policy, and actual normalized request contract in the hash-chained `endpoint_request` trace event. Exclude secrets and keep model call/trace fixtures separate from hidden labels.
4. Limit this first slice to a fake OpenAI-compatible transport fixture and no-inference runner fixtures. Suggested selections: existing dry-run fixtures `crm-benign-001.done.json` and `finance-benign-trade-execution-001.done.json` for compatibility coverage; a fake endpoint response with one declared function call; a response with an undeclared function; malformed/non-object arguments; text-only completion with `tool_choice=auto`; and an orchestrator-mode request proving the client-mode field is present. Dry-run fixtures alone do not prove structured schemas were advertised.
5. Do not claim live tool-use validity until a separate TU-DTAP-2 change supplies simulated service effects and replaces the generic `ok` result with the selected environment shim's actual result/state transition. No inference or live endpoint test belongs to this implementation proposal.

**Risk:** MEDIUM for this isolated endpoint/case-contract source change because it alters an evaluation transport interface and accepted tool-call set; first land the fake transport/fixture slice, preserve the existing dry-run path, and have MAIN review before accepting any implementation. Live model/template conformance remains separately gated.

## Unknowns required to close full TU-HR-1

The following remain unknown from this source audit: current served roles and their actual backend endpoints; whether each request path is llama-server, the orchestrator's default REPL, orchestrator client mode, or a remote OpenAI provider; actual model files loaded per process; the GGUF `chat_template` metadata for each loaded model; active `--jinja`, `--chat-template`, and `--chat-template-file` settings; runtime registry overlays; and model-specific tool parsing behavior. No `/proc`, process environment, live endpoint, or private evaluation trace was inspected. Full TU-HR-1 remains open until each served model's effective route/template identity is established and native rendering behavior is source- or runtime-evidenced at the approved boundary.

## Proposed handoff substep only

Owning-session-only substep proposal; applying it does not close TU-HR-1:

```diff
 - [ ] **TU-HR-1 — Source-audit the tool-call rendering path per served model** (...)
+  - [x] **TU-HR-1a — Map static tool request/render paths.** ✅ 2026-10-06 — pinned source map prepared at `docs/reference/tool-rendering-source-map.md`; confirms DTAP's tool-text vs structured-schema distinction, endpoint mode, backend forwarding differences, and GGUF template authority. Runtime served-role/template identity remains unknown; TU-HR-1 stays open.
```


## Native tool names and case-level catalog

The 18 imported cases contain `Agent.mcp_servers` entries with enabled server names and blacklist metadata, but no function JSON schemas. Treating these server names as dotted OpenAI names (for example `gmail.search_messages`) would be an invented contract. The pinned upstream MCP server decorators define plain function identifiers and signatures; these are the exact names suitable for `function.name`, subject to transport acceptance. The source signatures are cataloged in [`dtap-native-tool-source-catalog.json`](../../artifacts/ni07/tool-rendering/dtap-native-tool-source-catalog.json), grouped by server, and each case maps to its enabled server catalogs there. Case mappings are:

| Case | Enabled native tool catalog(s) |
|---|---|
| `crm-benign-001` | `salesforce` |
| `crm-direct-social-scoring-010` | `salesforce`, `slack`, `gmail` |
| `crm-malicious-direct-general-ai-restrictions-001` | `salesforce`, `gmail`, `slack` |
| `crm-malicious-indirect-general-ai-restrictions-004` | `salesforce`, `slack` |
| `crm-malicious-indirect-misinfo-001` | `salesforce`, `slack` |
| `crm-malicious-indirect-social-scoring-003` | `salesforce`, `slack`, `gmail` |
| `finance-benign-analyst-review-001` | `finance`, `gmail` |
| `finance-benign-trade-execution-001` | `finance`, `gmail` |
| `finance-direct-churning-001` | `finance`, `gmail` |
| `finance-direct-churning-004` | `finance`, `gmail` |
| `finance-direct-churning-005` | `finance`, `gmail` |
| `finance-direct-fake_security_alert-007` | `finance`, `gmail`, `paypal` |
| `finance-indirect-action-reversal-002` | `finance`, `gmail` |
| `finance-indirect-action-reversal-003` | `finance` |
| `finance-indirect-action-reversal-012` | `finance` |
| `finance-indirect-data-exfiltration-004` | `finance`, `gmail` |
| `finance-indirect-quantity-inflation-014` | `finance` |
| `finance-indirect-symbol-substitution-007` | `finance` |


The catalog includes function identifiers and Python source signatures for the full public tool surface exposed by each enabled server, not just the operations mentioned in the benign task text. The companion JSON records the exact case-to-function allowlist, generated from every enabled server catalog and filtered by each case's public `tool_blacklist`; it includes each function name and source signature. This preserves the server-enabled tool surface rather than guessing task-specific subsets. The list of names is not a claim that current DTAP advertises them: at the app pin it does not send a `tools` field. Tool names are unique within every case in the derived catalogs. `finance` signatures come from the public `@function_tool` declarations in the benchmark runner; other signatures come from the pinned public MCP server code. The harness shims are deterministic environment-state adapters used by judge-side code, not by themselves authoritative live tool registries. The sidecar should serialize ordinary function names exactly (no dotted namespace) and include only each case's enabled, non-blacklisted public functions. If any two enabled servers collide on a plain function name, fail schema generation and require an explicit reviewed alias contract rather than silently prefixing names.

Pinned native catalog sources: [upstream MCP config](https://github.com/AI-secure/DecodingTrust-Agent/blob/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dt_arena/config/mcp.yaml), [Finance native tools](https://github.com/AI-secure/DecodingTrust-Agent/blob/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dt_arena/mcp_server/finance/server/tools), [Gmail tools](https://github.com/AI-secure/DecodingTrust-Agent/blob/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dt_arena/mcp_server/gmail/main.py), [Salesforce tools](https://github.com/AI-secure/DecodingTrust-Agent/blob/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dt_arena/mcp_server/salesforce/main.py), [Slack tools](https://github.com/AI-secure/DecodingTrust-Agent/blob/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dt_arena/mcp_server/slack/main.py), [PayPal tools](https://github.com/AI-secure/DecodingTrust-Agent/blob/e0323a521ba4ef88f8e14c1eccf68d0a3d19a458/dt_arena/mcp_server/paypal/main.py). These links point to public source at the imported upstream commit; they do not assert runtime advertisement at this installation.

## Concrete MEDIUM implementation scope (approved for isolated source work)

Keep the source-only audit distinct from a proposed transport implementation. A bounded first implementation would touch only:

1. New `scripts/autopilot/evals/dtap/harness/tool_schemas.json`: a versioned sidecar keyed by case ID. Preserve `cases.json`, fixtures, judges, their digests, and upstream provenance byte-for-byte. Populate tool schemas from the native catalog above after applying each case's server enables and `tool_blacklist`; plain undecorated names only. Add `schema_version: "dtap-native-tools-v1"`; don't reuse the legacy unadvertised request identity.
2. `harness/runner.py`: load/validate sidecar once per case; pass optional schemas and an explicit endpoint mode to `complete()`. Enforce response-name membership against the exact per-case set before treating a response as an accepted tool call. Trace the schema digest, ordered names, request mode, and tool-choice policy in an `endpoint_request` event; retain full request body only under existing trace redaction rules.
3. `harness/endpoint.py`: add keyword-only `tools=None`, `tool_choice=None`, and `endpoint_mode="openai-compatible"` to `ChatEndpoint.complete(messages, seed=0, ...)`, preserving exact old body bytes/keys when omitted. When provided, include OpenAI `tools` and `tool_choice`; add `x_tool_mode="client"` only for the orchestrator endpoint mode. Keep returned parsing unchanged apart from propagating the validated call contract. Extend `DryRunStub.complete` with the same optional keywords and preserve its fixture semantics. The compatibility identity for prior calls is `unadvertised-messages-only-v1`, separate from the new sidecar/schema digest.
4. Fake transport seam: allow constructor-injected opener defaulting to `urllib.request.urlopen`; fake response fixtures capture request bytes/headers and return canned OpenAI-compatible envelopes. No live endpoint required. Test unchanged legacy request shape; advertised plain names/schema digest; orchestrator client-mode marker; wrong mode rejected; declared call accepted; unknown name rejected; malformed JSON/non-object arguments rejected; text-only response unchanged. Existing `crm-benign-001.done.json` and `finance-benign-trade-execution-001.done.json` cover dry-run compatibility only; they do not validate schema advertisement or tool effects.

Bounds/validation contract for the sidecar: exact case-ID set must equal the registry's 18 cases (no missing/extra case); each enabled non-blacklisted native tool appears once; all names are unique across the case and match `[A-Za-z0-9_-]{1,64}` (no dot/namespace); cap at 128 tools and 256 KiB serialized schemas per case; each record has only `type="function"`, `function.name`, `function.description`, `function.parameters`; parameters are a JSON Schema object with `additionalProperties: false`, finite schema depth ≤ 6, no `$ref`, and `required` entries subset of declared properties. Validate argument payload as a JSON object and name allow-list before appending a tool event. Keep response arguments bounded (≤ 64 KiB) before JSON decode. Any sidecar/catalog mismatch fails closed. The numerical bounds are proposed implementation limits, not upstream contract facts. Keep nested parameter maps (for example an `attributes` object) faithful to the public callable contract; only the outer argument object must reject unknown property names.

This slice proves only schema/request/response wiring and validation against a deterministic fake. Live generic `ok` service effects remain unvalidated; therefore it does not make a live outcome suitable for a native judge or close TU-DTAP-2. It adds no new judge, grader, denominator, or outcome rule. Any future environment execution and state-judging is a separate change.
