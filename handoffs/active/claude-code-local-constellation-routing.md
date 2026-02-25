# Handoff: Claude Code Integration with Local LLM Constellation Routing/Delegation

**Created**: 2026-02-13  
**Status**: READY TO IMPLEMENT  
**Priority**: HIGH  
**Scope**: Integrate Claude Code UX/runtime entrypoints with this repo's local orchestration stack for optimized routing + delegation across multiple locally-hosted models.

## Executive Summary

Yes, this is feasible. The critical constraint is that the public `anthropics/claude-code` repository is not the full Claude Code runtime source; the runtime itself is distributed as platform binaries. That means deep in-process runtime patching is not the primary path. The practical path is:

1. Use Claude Code plugins/hooks/MCP as the control plane surface.
2. Route execution requests to this repo's orchestrator API (`/chat`, `/v1/chat/completions`) as the data plane.
3. Keep routing/delegation policy local in this repo (MemRL + rule fallback + graph veto + admission/circuit-breakers).

This repo already contains most of the required machinery (hybrid routing, architect delegation loops, role-based local backends, OpenAI-compatible endpoint, and MCP server scaffolding). Implementation work is primarily adapter and contract hardening, not greenfield architecture.

---

## Baseline Facts and Constraints

### Upstream Claude Code constraints

- Upstream repo (`anthropics/claude-code`) currently exposes installer/docs/plugins/examples.
- Install script (`https://claude.ai/install.sh`) downloads a platform binary from GCS and runs `claude install`.
- Conclusion: treat Claude Code runtime as a black-box host; integrate via supported extension surfaces (plugins/hooks/MCP and compatible endpoints), not by modifying proprietary internals.

### Current repo strengths (already in place)

- Pipeline routing/delegation stages:
  - `src/api/routes/chat_pipeline/routing.py`
  - `src/api/routes/chat_pipeline/delegation_stage.py`
- Request/response model already carries routing/delegation controls + telemetry:
  - `src/api/models/requests.py`
  - `src/api/models/responses.py`
- MemRL lazy-init + hybrid routing + graph-aware retrieval:
  - `src/api/services/memrl.py`
- Role/model registry and routing hints:
  - `src/registry_loader.py`
  - `orchestration/model_registry.yaml`
- LLM backend abstraction and role-mapped real calls:
  - `src/llm_primitives/primitives.py`
- OpenAI-compatible route for tool/client compatibility:
  - `src/api/routes/openai_compat.py`
- MCP server already present (currently introspection-heavy):
  - `src/mcp_server.py`
- Local Claude project MCP wiring already configured:
  - `.mcp.json`

---

## Target Architecture

## Control Plane (Claude Code)

- User interacts with Claude Code (terminal + plugin commands).
- Claude Code invokes project MCP tools and/or OpenAI-compatible endpoint.
- Optional plugin hooks enforce policy/safety before tool execution.

## Data Plane (Orchestrator)

- Orchestrator API receives normalized task requests.
- Routing stage decides role (`frontdoor`, `coder_escalation`, `architect_*`, `worker_*`, etc.) with hybrid strategy.
- Mode stage decides `direct`/`repl`/`delegated`.
- Delegation stage performs architect-led multi-loop delegation for complex tasks.
- Backends execute via role->server_url mapping with health/admission/circuit controls.

## Observability Plane

- Emit structured route/delegation telemetry to caller and logs.
- Persist progress + rewards into MemRL.
- Provide route explanation endpoints/tools for debugging + policy tuning.

---

## Integration Patterns (Recommended)

Implement both patterns, with a clear primary.

### Pattern A (Primary): MCP Tool Delegation

Claude Code calls a new MCP tool (e.g. `orchestrator_chat`) which forwards requests to local orchestrator `/chat`.

Pros:
- Explicit control over orchestration options per request.
- Easy to expose diagnostics (`routing_strategy`, `role_history`, `delegation_events`).
- Clean fit for command-driven workflows and team policy.

### Pattern B (Secondary): OpenAI-Compatible Model Endpoint

Configure Claude-compatible clients/tooling that can speak OpenAI schema to call `/v1/chat/completions` and set `model`/`x_orchestrator_role`.

Pros:
- Easy compatibility with existing OpenAI-shaped clients.
- Minimal custom glue for some editors/tools.

Cons:
- Weaker semantic control than a purpose-built MCP tool contract.

### Recommended final posture

- Keep Pattern A as first-class integration for routing/delegation features.
- Keep Pattern B for compatibility and fallback.

---

## Detailed Wiring Plan

## 1) Extend MCP server with write-capable orchestration tools

Current `src/mcp_server.py` is read-only/introspection focused. Add explicit execution tools:

- `orchestrator_chat(prompt, context, options)`
- `orchestrator_route_explain(prompt, context)`
- `orchestrator_health()`
- `orchestrator_roles()`
- `orchestrator_benchmark_lookup(...)` (optional, already close via existing tool)

### Tool contract for `orchestrator_chat`

Input schema (MCP args):
- `prompt: str` (required)
- `context: str = ""`
- `real_mode: bool = true`
- `force_role: str | null`
- `force_mode: str | null` (`direct|repl|delegated`)
- `allow_delegation: bool | null`
- `thinking_budget: int = 0`
- `permission_mode: str = "normal"`
- `cache_prompt: bool | null`
- `image_path: str | null`
- `image_base64: str | null`

Output schema:
- Full `ChatResponse` passthrough from `src/api/models/responses.py`.
- Always include: `answer`, `routed_to`, `role_history`, `routing_strategy`, `mode`, `delegation_events`, `tool_timings`, `error_code`, `error_detail`.

Implementation note:
- Use local HTTP call to orchestrator API (e.g. `http://127.0.0.1:8000/chat`).
- Add robust timeout and structured failure mapping to MCP errors.

## 2) Introduce route explainability endpoint/tool

Current routing happens in `_route_request()` (`src/api/routes/chat_pipeline/routing.py`) and may use:
- forced role
- explicit role
- `_classify_and_route`
- `state.hybrid_router.route(task_ir)`
- failure graph veto override

Add a non-mutating “explain route” API/tool that returns:
- chosen role + strategy
- alternatives considered (if available)
- veto reason (if failure graph changed role)
- timeout selected
- tool requirement detection result

This is essential for tuning learned routing and debugging false escalations.

## 3) Map Claude Code intents to orchestrator options

Define deterministic mapping from user command/context into `ChatRequest` fields.

Recommended mapping:
- default interactive coding flow:
  - `real_mode=true`, `permission_mode="normal"`, `allow_delegation=null`
- explicit direct answer command:
  - `force_mode="direct"`
- explicit worker fast pass:
  - `force_role="worker_explore"`, `allow_delegation=false`
- explicit architect deep pass:
  - `force_role="architect_coding"` for code tasks, else `architect_general`
  - `force_mode="delegated"`, `allow_delegation=true`
- benchmarking/eval probes:
  - set `force_role`, and keep reward injection external (`/chat/reward`) as currently designed

Keep this mapping in one adapter module so policy can evolve without touching MCP handlers.

## 4) Align role vocabulary between Claude-facing labels and internal roles

Internal roles include names like:
- `frontdoor`, `coder_primary`, `coder_escalation`
- `architect_general`, `architect_coding`
- `worker_explore`, `worker_math`, `worker_vision`, `worker_code`, `worker_fast`

Define a translation table:
- public alias -> internal role
- internal role -> human label

Expose aliases in MCP help output so end users do not need to memorize internal names.

## 5) Harden backend routing and admission for constellation behavior

`LLMPrimitives` already supports role->server URLs and per-role semaphores (`src/llm_primitives/primitives.py`).

Planned hardening:
- ensure every delegatable role has a healthy backend URL mapping before request acceptance.
- preflight backend health for heavy architect roles when `force_mode=delegated`.
- enforce admission limits by role class:
  - heavy architects low concurrency
  - workers higher concurrency
- return deterministic error codes in `ChatResponse.error_code` for MCP/UI behavior.

## 6) Unify telemetry and expose to Claude-side UX

Use existing response fields and guarantee they are populated consistently:
- routing: `routed_to`, `role_history`, `routing_strategy`, `mode`
- delegation: `delegation_events`, `delegation_success`
- tools: `tools_used`, `tools_called`, `tool_timings`, `tools_success`
- performance: `elapsed_seconds`, `tokens_generated`, `predicted_tps`, `generation_ms`, `http_overhead_ms`
- reliability: `error_code`, `error_detail`

Add lightweight MCP pretty-printer mode for humans, raw JSON mode for automation.

## 7) Wire safety and permission semantics

Claude Code has permission modes; your `ChatRequest` already includes `permission_mode`.

Policy recommendation:
- `normal`: allow read tools + constrained writes with existing repo hooks.
- `auto-accept`: only for trusted local sessions; log this in response metadata.
- `plan`: force no-write execution paths in REPL/tool layer unless explicitly approved.

Ensure permission mode propagates into REPL/tool invocation policy.

## 8) Add a dedicated integration module

Create a dedicated integration package to avoid scattering adapter logic:

- `src/integrations/claude_code/adapter.py`
- `src/integrations/claude_code/schemas.py`
- `src/integrations/claude_code/policy.py`
- `src/integrations/claude_code/telemetry.py`

Responsibilities:
- normalize Claude-side requests
- map aliases to internal roles/modes
- call orchestrator API
- normalize/relabel response for Claude-facing display

---

## Suggested API and MCP Contracts

## A) MCP tool `orchestrator_chat`

Request example:

```json
{
  "prompt": "Find why test_x is flaky and propose minimal fix",
  "context": "repo: claude",
  "real_mode": true,
  "force_role": null,
  "force_mode": null,
  "allow_delegation": null,
  "permission_mode": "normal",
  "thinking_budget": 12000,
  "cache_prompt": true
}
```

Response example shape:

```json
{
  "answer": "...",
  "routed_to": "architect_coding",
  "role_history": ["architect_coding", "coder_escalation", "worker_explore"],
  "routing_strategy": "learned",
  "mode": "delegated",
  "delegation_events": [
    {"from_role":"architect_coding","to_role":"coder_escalation","success":true,"elapsed_ms":1820}
  ],
  "tools_called": ["peek", "grep", "run_tests"],
  "tool_timings": [
    {"tool_name":"grep","elapsed_ms":42,"success":true}
  ],
  "elapsed_seconds": 8.42,
  "tokens_generated": 1710,
  "predicted_tps": 10.2,
  "error_code": null,
  "error_detail": null
}
```

## B) Route explain tool

Request:

```json
{
  "prompt": "Design migration plan for classifier refactor",
  "context": "",
  "real_mode": true
}
```

Response:

```json
{
  "candidate_role": "architect_general",
  "strategy": "learned",
  "tool_required": false,
  "timeout_s": 600,
  "veto": {
    "applied": false,
    "risk": 0.12,
    "threshold": 0.5
  },
  "notes": ["hybrid_router used", "MemRL initialized"]
}
```

---

## Routing/Delegation Policy Blueprint

Start with conservative defaults and expand.

## Decision hierarchy (authoritative)

1. `force_role` (if present)
2. explicit `role` (non-frontdoor)
3. learned routing (`state.hybrid_router.route`) in `real_mode`
4. classifier/rules fallback (`_classify_and_route`)
5. failure graph veto (safety override)

Keep this ordering explicit and unchanged unless benchmark data justifies a shift.

## Delegation policy

- Delegation only for architect roles by default (current behavior in `delegation_stage.py`).
- For future general delegation expansion, gate behind feature flag and role whitelist.
- Hard cap loops (`max_loops=3` currently).
- On delegation failure, cleanly fall back to direct mode.

## Cheap-first policy

Current `_try_cheap_first` in `src/api/routes/chat.py` is already a speculative optimization layer. Keep disabled for unstable workloads until quality gate confidence improves.

---

## End-to-End Sequence (Target)

1. User asks in Claude Code.
2. Claude Code invokes MCP `orchestrator_chat` tool.
3. MCP tool adapter validates input and calls local `/chat`.
4. API `_handle_chat` executes staged pipeline:
   - routing
   - preprocessing/formalization
   - backend init
   - plan review gate
   - vision/proactive/delegated/direct/repl execution
5. Backends execute against role-specific local servers.
6. Orchestrator returns structured response with telemetry.
7. MCP relays answer + diagnostics back to Claude Code.
8. Optional reward feedback posted to `/chat/reward` for eval workflows.

---

## Implementation Phases

## Phase 0: Contract and scaffolding (low risk)

- Add `src/integrations/claude_code/` adapter package.
- Add MCP execution tools (without changing routing logic).
- Add route explanation endpoint/tool.
- Add schema tests for request/response normalization.

Exit criteria:
- Claude Code can call `orchestrator_chat` and get valid response for mock and real mode.

## Phase 1: Reliability hardening

- Add backend preflight checks for requested/forced roles.
- Standardize timeout behavior and error code mapping.
- Add retry policy for transient backend disconnections.
- Ensure `error_code` always set on non-success path.

Exit criteria:
- deterministic behavior under backend unavailable/timeout scenarios.

## Phase 2: Policy tuning and observability

- Implement route explain traces with reason codes.
- Add per-strategy metrics: learned vs rules vs forced vs vetoed.
- Add delegation success and loop-cap distributions.

Exit criteria:
- route/delegation diagnostics sufficient to tune thresholds without log scraping.

## Phase 3: Advanced delegation expansion (optional)

- Expand delegation eligibility beyond architect under feature flag.
- Add class-based delegation constraints and budgeted chain depth.
- Re-benchmark quality/cost tradeoff for each delegation strategy.

Exit criteria:
- statistically supported improvement over architect-only delegation.

---

## File-Level Change Map (Proposed)

Core integration:
- `src/mcp_server.py`
  - add write-capable orchestration tools and argument validation.
- `src/integrations/claude_code/adapter.py` (new)
  - map Claude tool args -> `ChatRequest` payload.
- `src/integrations/claude_code/schemas.py` (new)
  - Pydantic models for MCP-facing contracts.
- `src/integrations/claude_code/policy.py` (new)
  - role/mode alias mapping, default policy, permission propagation.
- `src/integrations/claude_code/telemetry.py` (new)
  - response normalization + pretty summaries.

Routing explainability:
- `src/api/routes/chat_routing.py`
  - expose explainable classification detail helper.
- `src/api/routes/chat_pipeline/routing.py`
  - optional structured decision trace object.
- `src/api/routes/chat.py` or new `src/api/routes/chat_routing.py` endpoint
  - add `/chat/route-explain`.

Reliability:
- `src/llm_primitives/primitives.py`
  - preflight role availability + improved error surfaces.
- `src/api/routes/chat_pipeline/routing.py`
  - reason-coded fallback path and veto metadata.
- `src/api/models/responses.py`
  - confirm/extend diagnostics fields if needed.

Tests:
- `tests/unit/test_mcp_server_*.py` (new)
- `tests/unit/test_claude_code_adapter.py` (new)
- `tests/unit/test_chat_route_explain.py` (new)
- `tests/integration/test_claude_code_orchestrator_integration.py` (new)

---

## Configuration and Environment Wiring

## Claude Code side

- Ensure project MCP config points to local server:
  - `.mcp.json` already configured for `src/mcp_server.py` with `PYTHONPATH`.
- Optional: add a Claude plugin command that calls `orchestrator_chat` with presets:
  - `/orch-fast` (worker)
  - `/orch-deep` (architect delegated)
  - `/orch-route-explain`

## Orchestrator side

- Ensure `server_urls` mapping is complete for all roles used by routing/delegation.
- Ensure feature flags for MemRL/delegation are set intentionally (not accidental defaults).
- Keep registry routing hints current in `orchestration/model_registry.yaml`.

---

## Failure Modes and Mitigations

1. Claude tool timeout while orchestrator still running.
- Mitigation: MCP tool timeout > orchestrator role timeout budget, with partial progress events if supported.

2. Routed role has no healthy backend.
- Mitigation: preflight role health; fallback to `frontdoor` or explicit degraded error.

3. Delegation loops produce no final answer.
- Mitigation: force-response-on-cap + fallback direct synthesis.

4. MemRL uninitialized or unavailable.
- Mitigation: route via rules/classifier fallback; include `routing_strategy` marker.

5. Failure graph false veto.
- Mitigation: expose veto in route explain; tune threshold from observed regressions.

6. Permission mismatch between Claude and REPL tools.
- Mitigation: explicit mapping table and test matrix for `permission_mode` propagation.

---

## Observability Requirements

Minimum dashboards/metrics to add:

- request volume by `routing_strategy`
- p50/p95 latency by `routed_to` and `mode`
- delegation loop count distribution
- delegation success rate by role pair
- backend timeout/error rate by role
- fallback incidence (learned->rules, specialist->frontdoor veto)
- quality proxy trends from reward injection (`/chat/reward`)

Minimum logs per request:
- `task_id`
- requested role/mode vs actual role/mode
- strategy + veto details
- delegation events summary
- top tool timings
- final error code/detail

---

## Security and Governance Notes

- Keep MCP execution tools local-only by default (bind `127.0.0.1`).
- Do not expose unrestricted shell execution through new MCP tools.
- Preserve existing filesystem hooks in `.claude/settings.json`.
- If adding remote API backends via `BackendConfig` in registry, require explicit allowlist and credential scoping.

---

## Test Plan

## Unit

- request mapping correctness (Claude args -> `ChatRequest`)
- response mapping correctness (`ChatResponse` -> MCP response)
- route explain output completeness
- permission mode propagation

## Integration

- Claude MCP tool -> `/chat` happy path (mock + real)
- forced role, forced mode, delegated mode paths
- backend down and timeout paths return expected `error_code`
- route explain tool consistency with actual routing decisions

## Regression

- existing chat pipeline tests continue passing
- no regressions in openai-compatible endpoint behavior

---

## Rollout Plan

1. Land Phase 0 behind feature flag `claude_code_integration`.
2. Internal usage only; gather telemetry for 3-7 days.
3. Enable reliability hardening (Phase 1) by default.
4. Enable route explain tooling to all users.
5. Expand delegation policy only after benchmark-backed quality/cost validation.

Rollback strategy:
- disable new MCP tools via feature flag and fall back to existing read-only tools.
- retain core `/chat` behavior unchanged.

---

## Open Questions (Resolve Before Implementation)

1. Should Claude-facing defaults prefer `repl` for all tasks, or keep direct-mode heuristics for simple QA?
2. Should permission mode from Claude strictly gate tool classes, or remain advisory initially?
3. What is the desired UX for showing route/delegation telemetry in Claude responses (always vs debug mode)?
4. Which subset of roles should be exposed as user-selectable aliases vs internal-only?
5. Should reward injection be automatic for interactive sessions, or reserved for benchmark harnesses?

---

## Immediate Next Steps (Implementation Checklist)

- [ ] Add integration adapter package (`src/integrations/claude_code/`).
- [ ] Add MCP tool: `orchestrator_chat`.
- [ ] Add MCP tool/API: `orchestrator_route_explain`.
- [ ] Add unit tests for contract mapping and failure handling.
- [ ] Add integration tests for forced/delegated routing paths.
- [ ] Add feature flag + docs for enablement/rollback.
- [ ] Run `make gates` and fix regressions.

---

## Reference Files

- `src/api/routes/chat.py`
- `src/api/routes/chat_pipeline/routing.py`
- `src/api/routes/chat_pipeline/delegation_stage.py`
- `src/api/routes/chat_routing.py`
- `src/api/models/requests.py`
- `src/api/models/responses.py`
- `src/api/services/memrl.py`
- `src/llm_primitives/primitives.py`
- `src/registry_loader.py`
- `orchestration/model_registry.yaml`
- `src/mcp_server.py`
- `.mcp.json`
- `.claude/settings.json`
- `docs/ARCHITECTURE.md`

