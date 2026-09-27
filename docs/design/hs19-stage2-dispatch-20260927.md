# HS-19 stage 2 "Scheduled" + HS-19c generalized scouting: how the stack dispatches subagent work (design, 2026-09-27)

Owner handoff: [`harness-selection-and-integration.md`](../../handoffs/active/harness-selection-and-integration.md) → HS-19 / HS-19d (this stage) and HS-19c.
Operator approval: 2026-09-27, in the session that approved stage 1 ([`hs19a-linked-subagents-20260927.md`](hs19a-linked-subagents-20260927.md)).
Status: **design only.** No inference and no process management went into it. Every build phase in §14 sits behind a default-off flag.

## 0. Rulings this design implements (not reopened here)

1. **The orchestrator owns model selection.** The harness never pins a model. The only pin is `x_force_*`, used for evaluation (HS-19 operator decisions, 2026-09-27).
2. **Build order:** 1 Linked (live, HS-19a.6 PASS 18/18) → **2 Scheduled (this doc)** → 2.5 shared context by pointer → 3 shared REPLs.
3. **Splitting is orchestration** (operator ruling 2026-09-24, recorded in `scout_stage.py`'s module docstring). The planner is told its budget. The budget is **enforced by code, never trusted to the plan.**
4. **The strongest model is a consultant.** Smaller models do the grunt work. Planning is itself a routing choice.

## 1. The pipeline in one table

| Step | Question | Who or what decides | Enforced by | Default when unsure |
|---|---|---|---|---|
| **Gate** | Is this request worth splitting or scouting? | A typed decision on the frontdoor: one question, a four-option menu (§5) | confidence ≥ τ, else `direct` | `direct` (today's path) |
| **Plan** | Which subtasks, what types, what depends on what? | Planner role, chosen by the gate: frontdoor, or the consultant for hard splits (§6) | Schema `epyc.dispatch_plan.v1` + validator (§7) | reject → one corrective retry → `direct` |
| **Size** | How many run now, and how many wait? | Code: live `/slots` free minus reserve, plus a process-wide reservation (§8) | Dispatcher admission | unknown capacity → `direct` |
| **Select** | Which model serves each subtask? | Code: type → candidate roles, then the DAR-LAT prior and saturation guard (§9) | the router; `x_force_*` for eval only | first candidate from the type table |
| **Aggregate** | How do results get back to the parent? | Code: a sized result block now; pointers at stage 2.5 (§10) | per-subtask character budgets and schema checks | text, truncated with a marker |

**Two front doors** (§4). **A**, orchestrator-driven (`/chat`, or the harness via an MCP tool), runs all five steps. **B** is harness-driven: an OpenCode `task` call on `/v1`. There the main thread has already done Gate and Plan, so the orchestrator runs Size, Select and Aggregate. In B, OpenCode itself does the aggregation.

## 2. What already exists: generalize it, do not fork it

| Machinery | Where (orch `b020a1a8`) | What stage 2 takes from it | What it lacks |
|---|---|---|---|
| **Proactive stage 7.5** (architect decomposes COMPLEX tasks into TaskIR steps, then `ProactiveDelegator` runs them in waves) | `src/api/routes/chat_pipeline/proactive_stage.py:192-241`; `/api/delegate` `src/api/routes/delegate.py:51-138`; feature `parallel_execution` | The TaskIR `plan.steps` shape (`orchestration/task_ir.schema.json`: `id ^S[0-9]+$`, `depends_on`, typed `call_edges`, `parallel_group`, `timeout_seconds`) and `compute_waves` DAG validation (`src/parallel_step_executor.py:75-115`: duplicates, dangling references, cycles) | Its gate is a heuristic (`classify_task_complexity`, `:224-228`). Its planner is always the architect: `role="architect_general"`, `n_tokens=256` (`:241-262`), which inverts ruling 4. It dispatches in waves: a wave barrier, not readiness. It runs through `LLMPrimitives`, which serializes same-role calls. Each step names a role (`actor` ∈ worker/coder/architect, `:86`), so the plan picks models. **Declared off in production** (`scripts/server/orchestrator_stack.py:2247-2255`, `parallel_execution: False`). |
| **Scout stage 6.8** (OAB-8: READ/GREP/SUMMARY scouts before the planner turn) | `src/api/routes/chat_pipeline/scout_stage.py` | Admission `resolve_cap` (`:712-742`): `free = slots − processing`, `cap = min(max, targets, free − reserve)`, `reserve ≥ 1`, unknown occupancy runs none. The shared cancel flag (stage budget, request deadline, disconnect). R2: the stage is awaited inside `/chat`, so nothing outlives the reply (`:50-60`). `render_block` for the sized result block. Direct streamed transport, which bypasses the per-role semaphore. | Targets beyond the cap are **skipped, not queued** (`:845-847`). It is triggered only by `ChatRequest.scouts`, which in practice only AutoKernel sends (HS-19c). |
| **Typed decisions** | `src/typed_decisions/` (`types.py` Question/Decision/ParseFailure; `confidence.py`; `runner.run_typed_decisions`; `fanout_policy.py`) | The gate contract: one pass, typed `choice`, `ParseFailure` never defaults silently, and a local confidence statistic (explicitly **not calibrated**, `confidence.py:9-16`) | Native scoring works on the champion, but production v10 lacks it until v11 (typed-decision-plane.md TD-1d, 2026-09-24). The gate runs in JSON mode until then. |
| **DAR-LAT-1/2** | root [`decision-aware-routing.md`](../../handoffs/active/decision-aware-routing.md) DAR-LAT-1/2 (open) | `expected_wait_s(role)` on the ONE admission ledger. The static per-role latency prior plus saturation guard, keyed by (role, device, topology_hash) (intake-1815#0, intake-1815#6). Lands at λ_lat = 0. | Not built. Stage 2 consumes the interface and must never build a second occupancy model. |
| **HS-19a link** | orch `src/api/routes/v1_subagent_link.py`, flag `v1_subagent_link` | Parent/child ids, depth, `x_agent_name`, and one `harness_subagent_link` session-log row per child: the stage-2 telemetry spine | It records only. It changes no scheduling. |
| **HS-OD-8/9** | root handoff `:120-121` (open) | Pre-stream 503 + `Retry-After` + `retry-after-ms`, then delay derived from DAR-LAT-1 | Not built. It is a prerequisite for front door B's Size step. |
| **Embedding-pool scheduler** | `src/embedding_pool/scheduler.py:1-26,187-270` | The process-wide `try_reserve`/`release` accounting pattern: grants are counted in-process, so two concurrent callers cannot both spend the same free slot, and a saturated caller waits up to its budget and then degrades | Different resource. It is a pattern to reuse, not a dependency. |

**Decision.** Stage 2 is a new dispatch stage that **replaces** stage 7.5's gate, planner and executor, and **generalizes** stage 6.8's admission (queue instead of skip). The plan compiles into TaskIR `plan.steps`, so the existing validation and tooling apply. Stage 7.5 stays declared off and is deleted once the §13 eval has run. It must not become a third fan-out path.

## 3. Evidence

- **Delegation has to be instructed or orchestrator-driven.** The 2026-09-27 controlled probe (`scripts/harness/task_delegation_probe.py`; evidence `/mnt/raid0/llm/tmp/task-probe-20260927/summary.json`, 15 valid runs) used one OpenCode pin and one logical model:
  - Under HS-19a's imperative prompt ("use the task tool…"), frontdoor, 27B-nothink and 27B-think each delegated **3/3**.
  - Under DS41-C20c's seat shape, with discretionary fan-out guidance and a prompt that never names the tool, frontdoor and 27B-think each delegated **0/3** (self-served 3/3). The conditional 27B-nothink ds41 cell was not run (`run_conditional_block: false`).
  - Verdict `SETUP`: the model is able to delegate, and the prompt shape decides whether it does.
- **Stage 1 is live.** HS-19a.6 PASS 18/18. Frontdoor delegated one `general` child at depth 1. The child was served by normal selection with no pin. Evidence is in `artifacts/harness/hs19a-20260927/`.
- **Multi-agent is not free, and not a default.**
  - Multi-agent uses 3–10× the tokens of a single agent, and three conditions justify it: context pollution, genuine parallelism, specialization (intake-1121#00, intake-1121#01). Its benefit is thoroughness, not speed (intake-1121#02).
  - At equal thinking budgets, a single agent matches or beats a multi-agent system on multi-hop reasoning (intake-1109#00, reasoning only, not tool use). Multi-agent gains vanish as sub-agents get stronger (intake-1126#04).
  - Most coding tasks have few truly parallel parts (intake-1113#02).
  - Hence the gate defaults to `direct`, and the eval baseline is the strongest model alone.
- **Plan the whole graph; dispatch on readiness.** LLMCompiler's planner emits a DAG, and a task-fetching unit dispatches greedily with **no duration or cost inputs** (intake-1117#00). Whole-graph planning beats immediate-batch native parallel calling (intake-1117#02; the structural argument survives, the 2023 magnitude does not). Under parallelism, latency is the critical path (intake-1112#record, stage-1 only).
- **Static priors are enough for Select.** RouteBalance's four-arm isolation found a static per-tier latency prior as good as a learned live estimate, with the gain cross-tier (intake-1796#02). RouterWise is per-(model, setup) (intake-1815#0).
- **No standard backpressure channel exists**, but OpenCode honours HTTP 429/5xx plus `Retry-After` (intake-1790#record, intake-1792#record; source-verified in §4).
- **Shared context is expensive.** It should be admitted by code or by cheap models, never by the strongest (intake-1803#record, intake-1820#record, intake-1821#record). That is why pointers wait for stage 2.5, and why stage 2 aggregates text.
- **Schema-constrained subagent returns** stop a prose flood from overwhelming the aggregator (intake-693#01).
- **Gateways expose capacity as gauges and hints** (intake-1783#record, intake-1785#record). We keep `/slots` plus the ledger and add no `/metrics` dependency (DAR-LAT-1 Axiom 1).

## 4. OpenCode, source-verified: what each step gets out of the box

Pin: tag `v1.18.31` = `014614d35b39`. The read clone is `/mnt/raid0/llm/harness/opencode` at `350c726aa8b6`. `git diff v1.18.31 350c726a -- packages/opencode packages/plugin packages/core` is empty, so every anchor holds at the served tag. Paths are relative to `packages/opencode/src/` unless another package is named. AI SDK: `ai@6.0.168` (`npm pack`, read-only, `dist/index.mjs`).

**4.1 The `task` tool's parameters** (`tool/task.ts:43-62`):
- `description` (3–5 words), `prompt`, `subagent_type`, optional `task_id` (resume a prior child session) and optional `command`.
- `background` exists but is only exposed when `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS` is on (`:361-366`).
- The model-visible description appends "Available agent types…" built from every non-`primary` agent the caller's permission allows (`tool/registry.ts:265-278, 318-331`).

**4.2 Several `task` calls per turn, run concurrently: PROVIDED, with no cap.**
- The tool text tells the model to "launch multiple agents concurrently … a single message with multiple tool uses" (`tool/task.txt:13`).
- Every tool is an AI SDK `tool({execute})` (`session/tools.ts:99-133`). The SDK's `runToolsTransformation` starts `executeToolCall` for each tool-call part **without awaiting the previous one**. The step closes when `outstandingToolResults` is empty (`ai/dist/index.mjs:6141-6147, 6264-6293`).
- A foreground task registers a job and waits on it (`tool/task.ts:284-297, 328-345`). `background/job.ts` has no limit or semaphore, and the session code uses `concurrency: "unbounded"` (`session/prompt.ts:188`, `session/processor.ts:588`, `session/llm.ts:102`).
- The only structural bound is depth (`task.ts:104-117`, `subagent_depth`, default 1).
- **Caveat:** whether the model *emits* more than one call depends on the server. OpenCode never sends `parallel_tool_calls` (no occurrence in `packages/opencode`). Neither does the orchestrator (no occurrence in orch `src/`). llama-server therefore defaults to the chat template's capability (`llama.cpp tools/server/server-common.cpp:1044`; `common/chat.cpp:1072` `max_calls = parallel ? -1 : 1`). Phase 0 checks this.

**4.3 Capacity and rate awareness: PARTIAL, per call only.**
- Each LLM call retries under `SessionRetry.policy` (`session/processor.ts:674-687`), up to 5 times (`session/retry.ts:31, 193`).
- The delay honours `retry-after-ms` first, then `retry-after` in seconds or as an HTTP date. Otherwise it is exponential from 2 s with 25% jitter, capped at 30 s (`retry.ts:26-31, 47-83`).
- It retries every 5xx, and any 429 whose message matches the rate/overload patterns (`retry.ts:33-41, 85-98`).
- There is **no fan-out-level awareness**: no concurrency cap, no token bucket, and no shared view across sibling children. Each child backs off on its own. After 5 failed retries the child fails, and the parent sees a tool error.
- This is exactly the lever HS-OD-8/9 plans to use. Today it is inert: a denial is a 502 with no header, or an SSE error after a 200 (root handoff `:120`).

**4.4 Results back to the parent: PROVIDED (text).**
- The child's **last text part** (`task.ts:224`) comes back wrapped as `<task id=… state="completed"><task_result>…</task_result></task>` (`:64-79, 341-345`).
- An error part or error message becomes `Subagent failed (task_id: …): …` (`:213-223`), which the SDK surfaces as a tool error.
- Each call gets a fresh child session unless `task_id` is passed (`:136-138`; `task.txt:16`). The child sees only `prompt`, not the parent's history.
- Children are denied `todowrite` and `task` unless their agent allows them (`:143-155`).

**4.5 `todowrite` as a proto-plan: PARTIAL.**
- `todowrite` rewrites the session's whole list. Each item has `content`, `status` and `priority` (`tool/todo.ts:6-45`; `session/todo.ts:40-42`).
- **There is no `todoread` tool at this pin.** The registry has only `todo` (`tool/registry.ts:219, 242`), and it echoes the list back as output.
- There are no dependencies, no types, and no link between a todo and a `task` call. It is a user-facing checklist, not a dispatchable plan.

**4.6 Custom agents as planner or worker roles: PROVIDED.**
- Markdown files under `{agent,agents}/**/*.md` load as agents (`config/agent.ts:11-31`).
- Frontmatter supports `description`, `mode` (subagent|primary|all), `steps`, `permission`, `prompt`, `options` and `model` (`packages/core/src/v1/config/agent.ts:12-38`).
- A child's model is `next.model ?? the parent message's model` (`task.ts:181-184`). Our lint forbids per-agent `model` (HS-19a.4), so every child runs on the one logical model and the orchestrator selects.
- **Agent names are therefore the natural subtask-type vocabulary for front door B.** They reach us as `x_agent_name`.

**4.7 `OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS`: off in our env, as it should be.**
- The flag is `enabledByExperimental` (`effect/runtime-flags.ts:11-14, 43`), so an explicit `0` (`harness/opencode-plugin/config/opencode.env:25`) beats `OPENCODE_EXPERIMENTAL`.
- When on, `background:true` returns at once and later injects the result as a synthetic user message, which starts a **new parent turn** (`task.ts:227-254, 316-319`).
- That breaks the parent-waits contract that front door B's Aggregate relies on. Keep it off.

**4.8 What a plugin can observe or change per `task` call: PARTIAL, but enough.**
- `chat.params` / `chat.headers` fire on every LLM call, including every child's. Their input is `{sessionID, agent, model, provider, message}` (`packages/plugin/src/index.ts:247-260`, fired at `session/llm/request.ts:114-145`). There is no parent id and no call id. OpenCode itself sends `x-parent-session-id` (`request.ts:201`); HS-19a uses it.
- `tool.execute.before` sees `{tool, sessionID (parent), callID}` and **mutable** `args` (`plugin index.ts:266-269`, fired at `session/tools.ts:104-110`). It fires *before* argument decoding (`tool/tool.ts:111-121`). Our plugin already stamps MCP tool args there (`harness/opencode-plugin/src/index.ts:57-64`).
- `tool.definition` can rewrite a tool's description and JSON schema (`tool/registry.ts:312-323`; `plugin index.ts:334`). A plugin could therefore add optional `plan_id`/`subtask_type` fields to `task`, read them in `tool.execute.before`, and let the Struct decode drop them.
- `tool.execute.after` sees the output metadata, which includes the child `sessionId` (`task.ts:185-195`).
- **Cheapest wiring needs no plugin change.** The orchestrator itself generated the parent's `task` tool calls. The child's first request carries `x-parent-session-id`, and its first user message equals `args.prompt`. So `(parent_session_id, sha256(prompt))` joins child to tool call on the server side. A plugin stamp is a fallback only if Phase 0 finds the join ambiguous.

**4.9 Per-step verdict and cheapest wiring**

| Step | OpenCode provides | Cheapest wiring |
|---|---|---|
| Gate | **Not provided.** The model decides at its own discretion, and the probe shows it will not under discretionary guidance. | Front door A: an orchestrator-side typed decision. Front door B: the decision is the user's or the prompt's. Optionally, an orchestrator capacity note on turns that offer `task` (§8.3). |
| Plan | **Partial.** N parallel `task` calls form a flat plan with a type (`subagent_type`). There are no dependencies and no expected-output contract. `todowrite` is an untyped, undispatchable checklist. | Front door A: the planner endpoint (§6–7), exposed to the harness as an MCP tool `orchestrator_dispatch` (HS-17's timeout is a prerequisite). Front door B: markdown agents named after the subtask types. |
| Size | **Not provided.** Fan-out is unbounded, the retry is per call, and `Retry-After` is honoured (§4.3). | The orchestrator holds child requests under a per-parent in-flight cap. Beyond the hold budget it returns a pre-stream 503 with `Retry-After` and `retry-after-ms` derived from `/slots` and the ledger (HS-OD-8/9). |
| Select | **Not OpenCode's job, by design.** It uses one logical model, and the child inherits it (`task.ts:181-184`). | The orchestrator maps `x_agent_name` → type → candidate roles → DAR-LAT prior and guard (§9). |
| Aggregate | **Provided (text).** The last text part is wrapped in `<task>` XML, and an error becomes a tool error. | Nothing is needed now. At stage 2.5 the child returns a pointer plus a gist, and the parent pulls on demand. |

## 5. Gate: a typed decision

- **Where it runs:** front door A only. It runs on the frontdoor role in JSON mode today and in native mode once v11 ships. It makes one call and asks one question, so `fanout_policy.choose_fanout_mode` returns `SEQUENTIAL_SINGLETON` for this single-question catalogue.
- **Skipped without a model call** (the result is `direct`) when: `force_mode` is set; any `x_force_*` is present; the request already carries `scouts` (the existing path); dispatch depth ≥ 1 (no grandchildren); the dispatch flag is off; or a request-shape pre-filter fires. The pre-filter uses a prompt length floor and a no-work-product check. Its thresholds are named constants with provenance `predeclared, uncalibrated` and are re-derived from the Phase 0 corpus.
- **Question** `dispatch.mode` (kind `choice`):
  > "Would this request be served better by (a) answering directly, (b) first reading specific files or code it names, (c) splitting it into two or more parts that separate workers can do independently, or (d) splitting it when deciding the split itself is hard or ambiguous?"
- **Menu:** `direct` | `scout` | `decompose` | `decompose_consult`.
  - `scout` is **HS-19c's trigger**. It sends the request to stage 6.8 with targets that the planner derives (§6), so scouts stop being AutoKernel-only.
- **Threshold:** act on a non-`direct` value only when `choice_confidence ≥ τ_gate` (initial 0.5, predeclared). The confidence is a local statistic, not a probability, so τ is re-set from the Phase 0 corpus and the shadow run. A `ParseFailure` (`no_json`, `schema_violation`, and so on) means `direct`, recorded by reason.
- **Shadow first.** Phase 3a records the decision and changes nothing.

## 6. Plan: who plans, and the capacity budget

- **Planner selection:** `decompose` → the **frontdoor** plans. `decompose_consult` → the **consultant** plans (today the architect role; the registry name comes from the stack registry, never hardcoded).
  - Saturation guard: if the consultant's `expected_wait_s` exceeds the planning budget, the frontdoor plans instead and the fallback is recorded.
  - Escalation: a frontdoor plan that fails validation twice may escalate once to the consultant. This is behind a flag and off by default.
  - Stage 7.5's always-architect planner is the anti-pattern this replaces.
- **Budget handoff:** before the planner call, Size computes and records:
  - `N_now` = Σ over the plan's eligible roles of `max(0, free_r − reserve_r)`, capped at `max_inflight_per_plan` (default 4);
  - `N_total` = `max_subtasks` (default 8).
  - The planner prompt states both numbers ("at most N_total subtasks; at most N_now start immediately; the rest wait"). It also tells the planner to prefer the fewest truly independent subtasks, and to return a single subtask if splitting is not worth it (a single subtask means `direct`).
  - The planner never sees role or model names.
- **Scout derivation** (the `scout` gate result): the same planner call, with `type: read|search` subtasks only. It emits `ScoutTarget`s for stage 6.8, which the planner then consumes as today.

## 7. Plan schema `epyc.dispatch_plan.v1`

The model fills the fields below. The server adds `plan_id`, `created_at`, the capacity snapshot and the selected roles. Decoding is **grammar-constrained**: the JSON schema is passed as `response_format` and llama.cpp compiles it to GBNF, with `maxItems = N_total`. `parse_with_repair` (`src/structured_output/repair.py`) gets one corrective retry.

```json
{
  "schema": "epyc.dispatch_plan.v1",
  "objective": "one sentence: what the parent will do with the results",
  "subtasks": [
    {
      "id": "S1",
      "type": "read | search | summarize | code | reason | verify",
      "instruction": "self-contained task text (the child sees nothing else)",
      "inputs": [
        {"kind": "request"},
        {"kind": "path", "value": "src/foo.py"},
        {"kind": "subtask", "ref": "S2"}
      ],
      "depends_on": ["S2"],
      "expects": {"format": "text | json", "json_schema": {}, "max_chars": 4000},
      "hints": {"difficulty": "routine | hard"}
    }
  ],
  "aggregate": {"instruction": "how the parent should combine the results"}
}
```

**Validation rules** (all enforced in code; any failure rejects the whole plan with a typed reason, and a plan is never silently truncated):

1. `schema` equals the literal string. `additionalProperties: false` at every level, so **no `model`, `role`, `actor` or `x_*` key can appear**.
2. `2 ≤ len(subtasks) ≤ N_total`. A single subtask means `direct` (`reason=single_subtask`).
3. Ids match `^S[1-9][0-9]{0,2}$` and are unique.
4. `type` is in the closed enum, and the enum version travels with the schema version.
5. `depends_on` refers only to existing ids, and the graph is acyclic. Both checks go through `compute_waves`, whose `ValueError` maps to `reason=graph_invalid`.
6. Every `inputs[kind=subtask].ref` is in that subtask's `depends_on`. A data edge implies an ordering edge.
7. The critical path length (longest `depends_on` chain) is ≤ `max_depth` (default 3).
8. Every `path` input passes the request's `TaskScope.read_denial`, the same confinement the scouts use. A plan that names an out-of-scope path is rejected, not pruned.
9. `instruction` is 1..4000 characters. `expects.max_chars` ≤ the per-subtask aggregate budget (§10). A `json_schema`, if present, must itself be valid, at most 2 KB, and have no `$ref` outside itself.
10. Duplicate work: two subtasks with the same `(type, instruction)` hash → `reason=duplicate_subtask`.

**TaskIR projection** (lossless one way): each subtask becomes a `plan.steps` entry.
- `{id, action: instruction, inputs, outputs: ["<id>.result"], depends_on}`, with `call_edges[type=data]` for `kind=subtask` inputs.
- `actor` is filled **after Select** with the chosen role.
- The plan therefore validates against `orchestration/task_ir.schema.json` and flows through `canonicalize_task_ir` for logs and replay.

## 8. Size: admission and queueing semantics

### 8.1 Front door A (`/chat`)

- **Readiness dispatch, not waves.** A subtask is *ready* when all its `depends_on` have completed. Ready subtasks start as soon as admission grants a slot. There is no wave barrier (intake-1117#00, intake-1112#record). The queue order is plan order, which is deterministic and replayable. Critical-path-first ordering is a later, measured change.
- **Admission** generalizes `scout_stage.resolve_cap`: `free_r = slots − processing` from live `/slots`, then `grant` if `free_r − reserve_r − reserved_in_process_r > 0`.
  - `reserved_in_process_r` is a process-wide reservation, in the pattern of `EmbeddingScheduler.try_reserve/release`. It closes the gap between reading `/slots` and the server reflecting our dispatch, so two concurrent plans cannot spend the same slot.
  - When DAR-LAT-1 lands, the source switches to its `SlotCapacity`, with the source recorded. There is never a second occupancy model.
- **Queue:** a subtask that is not granted **waits**; it is not skipped as in stage 6.8 today. The dispatcher re-evaluates on every subtask completion and at most once per second otherwise. `max_inflight_per_plan` caps one plan's share.
- **Deadline:** dispatch budget = the request's remaining budget minus the aggregate reserve. The reserve is the parent synthesis estimate from the DAR-LAT-2 T̂ for the parent role, or a named constant until then. When the budget is spent:
  - queued subtasks become `skipped: deadline`;
  - running subtasks are stopped through the shared cancel flag (streamed transport closes, and llama-server stops decoding);
  - Aggregate runs with what has finished, marked `partial: true`.
- **R2:** the stage is awaited inside `_handle_chat`. Every subtask finishes, times out or is cancelled before the synthesis turn, so **nothing outlives `/chat`**. The OAB-3 trailing-work witness applies unchanged.
- **Unknown capacity:** no `/slots` or no ledger → `direct`, recorded as `size_source=unavailable`. The cap is never a guess.
- **No hold-and-wait deadlock:** the planner call has finished before dispatch, and the parent's synthesis call starts after it, so the parent holds no slot while it waits.

### 8.2 Front door B (`/v1`, OpenCode `task`)

- OpenCode fires every child at once (§4.2). The orchestrator applies a **per-parent in-flight cap**. Children are keyed by the HS-19a `parent_session_id`, and the cap is the same `max_inflight_per_plan` intersected with admission.
- A child request that cannot be granted is **held** before the stream starts, while `expected_wait_s` fits the hold budget. Holding is safe: the template's `headerTimeout: false` keeps a pre-stream hold from timing out the shell (root handoff `:121`).
- Beyond the hold budget, the child gets a **pre-stream 503** with `Retry-After` = ceil(s) and `retry-after-ms`. This is HS-OD-8's status fix plus HS-OD-9's derivation, which OpenCode honours (`retry.ts:47-78`).
- The hold budget plus up to 5 retries must cover the expected queue, or the child fails and the parent sees a tool error (§4.3). The receipts are VB-V1-BACKPRESSURE.

### 8.3 The optional capacity note (front door B)

On a parent turn whose tool list contains `task`, the orchestrator may append a one-line system note at the **tail** of the messages, not in the system prompt, which keeps the prefix cache intact: "at most N_now subagents can run now". This is the instructed-delegation lever the probe points to. It sits behind its own flag, and the note text is fixed and versioned.

## 9. Select: per-subtask model

1. **Type → candidate roles** (a static, versioned table in config):
   - `read | search | summarize` → worker-class roles, then frontdoor;
   - `code` → coder role, then frontdoor;
   - `reason` → frontdoor;
   - `verify` → frontdoor, or the consultant only when `hints.difficulty=hard`.
   - Front door B takes the type from `x_agent_name` through an agent→type map, using the markdown agents in the subagents profile (§4.6). An unknown agent gets the `reason` row.
2. Among the candidates: the DAR-LAT-2 score (the static prior keyed by role, device and topology_hash, plus the saturation guard). It lands at λ_lat = 0 until DAR-LAT-3 decides.
   - Before DAR-LAT-2 exists, the rule is the table order plus a saturation skip: skip a candidate with no grantable slot when a later candidate has one.
3. **Grunt types never go to the consultant** (ruling 4). The consultant is reachable only through `verify` with `difficulty=hard`, and through planning (§6).
4. **Evaluation pins only:** `x_force_role` on the `/chat` request pins the parent, as in the probe. A separate eval-only `x_force_subtask_role` pins every subtask. It is refused unless the request is in eval mode, and it is recorded in the tap. No harness config may carry it (HS-19a.4 lint).
5. Each subtask writes the DAR-LAT-2 selection receipt: components, the admission snapshot, and the selection-time role versus the final role.

## 10. Aggregate

- **Stage 2, text:** the parent's synthesis turn receives one sized block, built with `render_block` from stage 6.8. It lists every subtask with id, type, status and the result, truncated to `expects.max_chars` with an explicit truncation marker. The block total is capped at the aggregate budget (default 16k characters).
  - Failed or skipped subtasks are **listed with their reason**, never omitted.
  - `expects.format=json` results are validated against the subtask's `json_schema`. A violation gets one corrective retry, the fast-rlm pattern (intake-693#01). After that the subtask is `failed: schema`.
- **Front door B:** OpenCode's own `<task>` rendering (§4.4). The orchestrator does not rewrite tool results.
- **Stage 2.5, pointers:** each subtask's output is stored in the UFH-12 retrieval store / context bundle (REPL-EMB-5.1's SEARCH primitive, not a fork). The parent receives `{ref, gist ≤ 100 tokens, size, schema_ok}` and pulls on demand. Admission to any shared context is by code or a cheap model, never the consultant (intake-1803#record).

## 11. Failure modes

| Failure | Detection | Handling | Recorded as |
|---|---|---|---|
| Gate unparsable or below threshold | `ParseFailure`, or confidence < τ | `direct` | `gate.outcome=parse_failure / low_confidence` |
| Planner emits too many subtasks | `maxItems` makes it structurally impossible under constrained decoding; the validator rule 2 otherwise | one corrective retry that states the count; then `direct` | `plan.reject=too_many` |
| Planner emits invalid JSON, a cycle, a dangling reference or an out-of-scope path | `parse_with_repair`, `compute_waves`, `read_denial` | one corrective retry; then `direct` (or escalate once to the consultant, if flagged) | `plan.reject=<reason>` |
| Plan has one subtask | rule 2 | `direct` (no cost beyond the planner call) | `plan.reject=single_subtask` |
| A subtask errors or times out | transport, timeout, or `ParseFailure` on `expects` | dependents become `skipped: upstream_failed`; independent siblings continue. A **transport** error retries once on the next candidate role; a **content** failure does not retry. | per-subtask `status`, `error` |
| Deadline | dispatch budget spent | cancel queued, stop running, aggregate partial | `partial=true`, counts |
| Client disconnect | the existing cancel flag | stop everything; await all threads (R2) | `cancelled` |
| Capacity unknown | `resolve_cap` source ≠ `live_slots` | `direct` | `size_source=unavailable` |
| Front door B child exhausts OpenCode's 5 retries | the child request stops arriving | nothing on our side; the parent sees a tool error | bounce receipts (VB-V1-BACKPRESSURE) |
| A child tries to fan out again | depth ≥ 1 | Front door A: the dispatch stage is skipped at depth ≥ 1. Front door B: `subagent_depth` 1 and `general` denies `task` (HS-19a.3) | `depth_refused` |

## 12. Telemetry

- **Spine = HS-19a link rows.**
  - Front door A subtasks are issued as child sessions, `x_session_id = <parent>/<plan_id>/<Sx>`, with `parent_session_id` set, so the same tap `request_keys` and `harness_subagent_link` rows describe both front doors.
  - New keys: `plan_id`, `subtask_id`, `subtask_type`, `selected_role`, `selection_receipt_id`, `admission` (`queued_s`, capacity snapshot, source), `status`, `wall_s`, and tokens in and out.
- **One `dispatch_plan` progress-log row per plan:** the gate decision and confidence; the planner role and fallback; the plan's sha256; validation outcome and reason; `N_now` and `N_total`; the TaskIR projection hash.
- **Front door B join:** `(parent_session_id, sha256(first user message))` ↔ the parent response's `tool_calls[].function.arguments.prompt`. Phase 0 confirms that the tap keeps the emitted tool calls.
- **Tree metrics** use the OrchBench real-side definitions (declared, started and completed agents; parallel utilization; workflow depth; intake-1111#record, whose headline correlation was dive-overturned). Rows go through the existing `fanout_timing` schema where it fits, not a new one.
- **Belief kernel:** the eval (§13) produces measurements, so its write side is filed now (VB-DISPATCH-S2 in `vidya-belief-substrate-program.md`, plus a source-table row in `scripts/vidya/adapters/README.md`).

## 13. Evaluation plan

- **Standing baseline A0: the strongest model alone.** The consultant role answers in one pass, pinned by `x_force_role`, with the same wall budget. Stage 2 must beat or match it.
- **Arms:**
  - A1 frontdoor alone (today's default route);
  - A2 the full pipeline (gate, routed planner, scheduled subtasks, text aggregate);
  - A3 A2 with the gate forced to `decompose` (measures what the gate saves: false-positive cost);
  - A4 A2 with the consultant always planning (measures the value of routing the planner).
- **Workloads:**
  - decomposable: multi-file read and summarize, multi-question lookup, independent code checks;
  - **non-decomposable controls**: single-hop QA, short code edits.
  - Gate labels are written before any run.
- **Metrics:**
  - per-suite graded quality;
  - end-to-end p50/p90 and TTFT;
  - **consultant device-seconds**, the scarce resource;
  - total tokens across the tree;
  - fan-out width, critical path, queue wait, parallel utilization;
  - gate precision and recall against the labels;
  - plan validity rate, subtask failure rate, partial rate;
  - the R2 witness (zero trailing work).
- **Secondary cut at matched token budget** (intake-1109#record: equal budgets remove most multi-agent gains in reasoning).
- **Decision rule** (predeclared, then frozen at launch): adopt for a workload class only if quality is non-inferior to A0 (≥ −1 per-suite quantum), AND consultant device-seconds or p50 wall improve, AND controls do not regress beyond the noise floor. Otherwise the result is a bounded null for that class, and the gate learns `direct` for it.
- **Protocol:** pre-register it as a protocol annex under `measurement/protocols/` before the first block. Until the operator ratifies it, results are observation-grade. Inference runs only in a coordinated window owned by the session that holds the inference.

## 14. Phased build plan (each phase behind a default-off flag; flags off = byte-identical)

- [ ] **P0 — preflight, zero inference.**
  - (a) Offline test: `/v1` returns more than one `tool_calls` entry from a canned multi-call llama-server response, and passes it through unchanged. Read the served templates' `supports_parallel_tool_calls`.
  - (b) Count `task` parts per assistant message in the HS-19a and probe taps.
  - (c) Confirm that the tap keeps emitted tool calls (the §12 join).
  - (d) Build the gate and plan corpus from the HS-19a/probe trees plus labelled `/chat` prompts.
  - (e) Wire the VB-DISPATCH-S2 write side.
- [ ] **P1 — schema + validator + TaskIR projection** (a library with no flag, since nothing calls it). Module `src/dispatch/plan.py`, schema JSON, and the rules in §7 with one test per rule. GBNF round-trip through `response_format`.
- [ ] **P2 — dispatcher** (flag `dispatch_scheduler`). Readiness dispatch, admission generalized from `resolve_cap` with a process-wide reservation, the queue, the deadline, the cancel flag, and R2. Stage 6.8 may adopt it later for queue-instead-of-skip under the same flag. Tests use a fake `/slots` and a fake transport, as the scout tests do.
- [ ] **P3a — gate in shadow** (flag `dispatch_gate_shadow`). It records `dispatch.mode` and confidence on live `/chat` and changes nothing. τ is re-set from the P0 corpus plus the shadow rows.
- [ ] **P3b — front door A live** (flag `dispatch_plan`, requires P1–P3a). Gate → planner selection → plan → Size → Select (the table plus saturation skip; DAR-LAT-2 when it lands) → text Aggregate. Stage 7.5 stays off and is deleted after P5.
- [ ] **P3c — HS-19c scouting through the gate** (flag `dispatch_scout`). `scout` → planner-derived `ScoutTarget`s → stage 6.8. Coordinate with INF-78 (OAB-8) and UFH-12 REPL-EMB-5.1, and fork neither.
- [ ] **P4a — front door B Size** (flag `v1_subagent_schedule`, requires HS-OD-8/9). Per-parent in-flight cap, hold, then 503 + `Retry-After`. The type comes from `x_agent_name`, via typed markdown agents in the subagents profile, with the lint extended.
- [ ] **P4b — `orchestrator_dispatch` MCP tool** (flag, requires HS-17). The harness reaches front door A with one tool call. This is the orchestrator-driven answer to the probe's finding.
- [ ] **P4c — capacity note** (flag `v1_capacity_note`). §8.3, fixed text, tail placement.
- [ ] **P5 — eval** (§13, inference, coordinated window). Then decide per workload class, and delete stage 7.5.
- [ ] **P6 — stage 2.5 pointers** (flag `dispatch_pointer_results`). §10, on UFH-12. Its own design goes through HS-19b.

## 15. Prior-art check (intake index, 2026-09-27; nothing ingested this round)

**Already ingested**

| Intake | Work | Verdict | Key claim used here |
|---|---|---|---|
| intake-1117#record | LLMCompiler (arXiv:2312.04511) | adopt_patterns, dived | The planner emits a DAG; a task-fetching unit dispatches greedily with no duration inputs (#00). Whole-graph beats immediate-batch planning (#02). The planner caused 8% of failures (#03). Era caveat: 2023 models. |
| intake-846#record | Anthropic engineering set (incl. "Building effective agents": orchestrator-workers) | adopt_patterns | About 15× chat tokens; execution is synchronous and blocked on the slowest subagent |
| intake-1113#record | Anthropic multi-agent research system | worth_investigating | Lead plus 3–5 subagents; not a fit for coding or shared-context work; a 50-subagent pathology |
| intake-1121#record | Anthropic "Building multi-agent systems: when and how" | adopt_patterns | 3–10× the tokens of a single agent; three justifying conditions; thoroughness over speed |
| intake-1109#record | Single-agent vs MAS at equal thinking budgets | worth_investigating | A single agent matches or beats MAS on multi-hop reasoning when budgets are equal |
| intake-1126#record | MAS-Orchestra | worth_investigating | Gains are conditional and vanish as sub-agents strengthen |
| intake-1112#record | LAMaS | worth_investigating (stage 1) | The critical path is the objective |
| intake-1111#record | OrchBench | headline dive-overturned | Real-side metric definitions are reusable |
| intake-493#record | Conductor (RL-trained 7B coordinator) | adopt_patterns | A learned topology plus per-worker prompts; a long-run option for the planner |
| intake-693#record | Schema-validated subagent returns (fast-rlm) | adopt_patterns | Typed returns act as an attention mask for the aggregator |
| intake-788#record, intake-1068#record | AFlow, ADAS (workflow search) | worth_investigating | Not needed for stage 2 |
| intake-1806#record | Recursive agent harnesses | worth_investigating | Script-spawned width knows nothing about capacity (§8.2) |
| intake-1793#record | Codex subagents | adopt_patterns | A static client-side thread cap; the harness pins the model (we do not) |
| intake-705#record | OpenRouter subagent server tool | adopt_patterns | Server-side delegation with an isolated task description |
| intake-1816#record, intake-1196#record | ThunderAgent, KVFlow | adopt_patterns (KVFlow is dive-overturned as an entry; its eviction mechanism, claim #01, was cleared) | The program or step graph as a scheduling and KV-eviction unit (for P2 and beyond) |
| intake-146#record, intake-847#record | LangGraph | worth_investigating / adopt_component | Graph execution; its plan-and-execute template is not adopted |
| intake-014#record | ReAct | already_integrated | The per-subtask executor loop |

**Missing: candidates for a future intake round (not ingested; only one round was authorized)**

- **ReWOO** (arXiv:2305.18323): plans the whole task up front with evidence placeholders, then worker and solver passes; the token-saving counterpart to LLMCompiler.
- **HuggingGPT** (arXiv:2303.17580): a controller LLM plans a task graph and selects a specialist model per task from model descriptions; closest prior art to our Select step.
- **TaskWeaver** (arXiv:2311.17541): a code-first planner/executor split with a planner role separate from the code interpreter.
- **Magentic-One** (arXiv:2411.04468): an orchestrator with a task ledger and a progress ledger that replans on stall; directly relevant to §11.
- **AutoGen** (arXiv:2308.08155): cited only inside intake-607#record, intake-1196#record and intake-1313#record, with no entry of its own; the conversation-programming baseline.
- **Plan-and-Solve** (arXiv:2305.04091): prompt-level plan-then-execute in a single model; low relevance, but a baseline for "planning without dispatch".
- **Plan-and-Act** (arXiv:2503.09572): cited only in intake-1320#record; a separate planner/executor with synthetic plan data for training a planner.
- **ADaPT** (arXiv:2311.05772): decomposes only when the executor fails; an alternative gate design (decompose on failure rather than up front).
- **Agent-Oriented Planning** (arXiv:2410.02189): principles for decomposition (solvability, completeness, non-redundancy) and a plan-checking reward model; relevant to §7's validator.
- **Skeleton-of-Thought** (arXiv:2307.15337): parallel expansion of the points in an outline; the text-answer analogue of `decompose`.
- **Graph of Thoughts** (arXiv:2308.09687) and **Tree of Thoughts** (arXiv:2305.10601): cited only in intake-748#record's references; aggregation operators over thought graphs.
- **LLM-Tool Compiler** (arXiv:2405.17438): fuses similar tool operations to parallelize calls.
- **AsyncLM** (arXiv:2412.07017): asynchronous function calling with interrupts, so the caller does not block on the slowest call.
- **Parrot** (arXiv:2405.19888), **Teola** (arXiv:2407.00326) and **Autellix** (arXiv:2502.13965, cited only inside intake-1196#record and intake-1816#record): serving schedulers that know the program or DAG; the closest prior art to our Size step on shared llama-servers.
