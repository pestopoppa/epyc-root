# pi-agent-core (badlogic/pi-mono/packages/agent) — Deep Dive

- **Source**: https://github.com/badlogic/pi-mono/tree/main/packages/agent (npm: `@mariozechner/pi-agent-core`)
- **Commit surveyed**: HEAD of `main` at clone time, agent-loop.ts last touched 2026-04-22, package version 0.70.2 (2026-04-24)
- **Lines of code**: src 1,966 LOC (agent-loop 683, agent 543, types 365, proxy 367, index 8); tests 2,048 LOC. ~1:1 test-to-source ratio.
- **Repo activity**: 3,805 commits since 2025-08-09, 80+ contributors, ~70 versions. Top contributors: Mario Zechner (2,957) · Helmut Januschka (66) · **Armin Ronacher (55)** · Aliou Diallo (51) · Markus Ylisiurunen (44).
- **Brand**: Hosted at github.com/badlogic/pi-mono; product domain `pi.dev` (donated by exe.dev). Active Discord, CI workflows, formal CHANGELOG, conventional-commit messages tied to GitHub issues (e.g., `closes #3525`).
- **Intake verdict delta**: initial intake (`novelty=low, relevance=low, credibility=null, verdict=worth_investigating`) was based on README scan only and **materially mis-estimated credibility and contributor depth**. Post-source-review the entry should move to `relevance=medium`, `verdict=adopt_patterns` for *named primitives we don't have explicit names for in our orchestrator*, and credibility upgraded to a non-null score (the framework does have empirical claims via the published HuggingFace session datasets, just not benchmark numbers).

---

## 1. The Agent Loop — what's actually in 683 lines?

`packages/agent/src/agent-loop.ts:155-234` is the real loop. It is genuinely small (~80 lines for the `runLoop` body) and is the only loop body in the file — everything else is event marshalling, parallel/sequential dispatch, and prepare/execute/finalize stages.

```typescript
// agent-loop.ts:168-231 (annotated, not source-perfect)
let firstTurn = true;
let pendingMessages: AgentMessage[] = (await config.getSteeringMessages?.()) || [];

while (true) {                                      // OUTER: revives on follow-up
  let hasMoreToolCalls = true;
  while (hasMoreToolCalls || pendingMessages.length > 0) {   // INNER: turns
    if (!firstTurn) await emit({ type: "turn_start" });
    firstTurn = false;

    if (pendingMessages.length > 0) {               // STEERING injected pre-call
      for (const m of pendingMessages) {
        await emit({ type: "message_start", message: m });
        await emit({ type: "message_end", message: m });
        currentContext.messages.push(m);
        newMessages.push(m);
      }
      pendingMessages = [];
    }

    const message = await streamAssistantResponse(...);
    newMessages.push(message);

    if (message.stopReason === "error" || message.stopReason === "aborted") {
      await emit({ type: "turn_end", message, toolResults: [] });
      await emit({ type: "agent_end", messages: newMessages });
      return;
    }

    const toolCalls = message.content.filter(c => c.type === "toolCall");
    const toolResults: ToolResultMessage[] = [];
    hasMoreToolCalls = false;
    if (toolCalls.length > 0) {
      const batch = await executeToolCalls(...);    // parallel or sequential
      toolResults.push(...batch.messages);
      hasMoreToolCalls = !batch.terminate;          // TERMINATE hint
      for (const r of toolResults) {
        currentContext.messages.push(r);
        newMessages.push(r);
      }
    }

    await emit({ type: "turn_end", message, toolResults });
    pendingMessages = (await config.getSteeringMessages?.()) || [];   // STEER again
  }

  const followUpMessages = (await config.getFollowUpMessages?.()) || [];
  if (followUpMessages.length > 0) {                // FOLLOW-UP wakes the agent
    pendingMessages = followUpMessages;
    continue;
  }
  break;
}
await emit({ type: "agent_end", messages: newMessages });
```

Design properties that are **actually load-bearing** (and that the README undersells):

- **Steering polled twice per turn** (`agent-loop.ts:165`, `:218`). Once at start, once at the end of each turn body. Steering messages are injected *before* the next assistant call, so the LLM sees them as user input on the next turn. Tool calls in flight from the *current* assistant message are not skipped.
- **Follow-up wakes a stopped agent**. The outer `while (true)` exists only so that `getFollowUpMessages()` can revive the agent after it would otherwise stop — without re-entering `agent.prompt()`. This is a state-machine distinction: steering = "inject before the next turn", follow-up = "agent thinks it's done; here's more work."
- **Termination requires unanimous batch consent** (`agent-loop.ts:499-501`): `finalizedCalls.every(f => f.result.terminate === true)`. A mixed batch where one tool says "we're done" and another doesn't will continue. This is intentional — covers the case where the LLM calls `notify_done` *and* `read_file` in the same batch; the read still needs to feed back into the next turn.
- **Inner-loop guard is two-condition**: `hasMoreToolCalls || pendingMessages.length > 0`. So even on a turn where the LLM produced no tool calls, if steering arrived during that turn, the loop runs another turn to inject it. Without this, steered messages would be deferred until the next `prompt()`.

Loop is ~80 lines. The rest of `agent-loop.ts` (~600 lines) is:
- `streamAssistantResponse` (95 lines): event-driven streaming with partial-message reconciliation
- `executeToolCallsParallel` (60 lines): preflight sequentially, execute concurrently, emit ends in completion order, emit messages in source order
- `executeToolCallsSequential` (50 lines): both stages serialized
- `prepareToolCall` / `executePreparedToolCall` / `finalizeExecutedToolCall` (~150 lines): the three stages that surround `execute()` so `beforeToolCall` and `afterToolCall` hooks have well-defined surfaces

This is where the design pays off: the parallel executor doesn't just `Promise.all` the tools — it **runs preflight (arg validation + `beforeToolCall`) sequentially**, then runs `execute()` in parallel, then runs `finalize` (apply `afterToolCall`) per-tool, emits `tool_execution_end` *as each tool completes*, and only at the very end emits the persisted `toolResult` messages **in assistant source order**. Two ordering systems running at once: events for UI (completion-ordered for responsiveness), persisted transcript (source-ordered for replayability).

---

## 2. AgentMessage Abstraction — why two-stage pipeline?

```
AgentMessage[]  →  transformContext(messages, signal)?  →  AgentMessage[]  →  convertToLlm(messages)  →  Message[]  →  LLM
                   (optional, AgentMessage-level)                            (required)
```

Both stages exist for distinct reasons (`types.ts:103-154`):

- **`transformContext`** (optional): pre-LLM context engineering at the *agent message* level. Pruning, summarization, RAG-style injection. Sees the full transcript including custom message types.
- **`convertToLlm`** (required): filters and shapes the message list into the strict `user|assistant|toolResult` shape the LLM provider expects. Custom message types must be either filtered out (UI-only notifications) or coerced into a standard role.

Why split? Three concrete reasons visible in the code:

1. **Custom message types via TypeScript declaration merging** (`types.ts:247-256`):
   ```typescript
   declare module "@mariozechner/pi-agent-core" {
     interface CustomAgentMessages {
       artifact: ArtifactMessage;
       notification: NotificationMessage;
     }
   }
   ```
   `AgentMessage = Message | CustomAgentMessages[keyof CustomAgentMessages]`. The agent transcript can contain anything; only `convertToLlm` knows what the LLM accepts. This is genuinely clean — Hermes-agent and our orchestrator both fudge this with sentinel string formatting.

2. **`transformContext` runs *every turn***, not just on prompt entry (`agent-loop.ts:248-251`). So it acts as a per-turn context-window manager. Pruning logic doesn't need to know about LLM-specific roles, it just operates on agent-level message metadata.

3. **The split makes `agent_end` settlement deterministic.** Listeners see the same `AgentMessage[]` the agent stored, not the LLM-coerced version. UI can render notifications and artifacts without re-deserializing.

This is the pattern most worth taking back to our stack. Our `epyc-orchestrator/src/orchestrator/` does *not* have an analogue — we have ad-hoc `_to_llm_messages` helpers scattered across ~5 files (verify with `grep -rn "to_llm_messages\|_format_for_llm" epyc-orchestrator/src/` — these are the hot spots of role coupling).

---

## 3. Tool Execution Hooks — what `beforeToolCall` and `afterToolCall` actually buy you

`agent-loop.ts:517-567` (prepareToolCall) and `:606-649` (finalize):

| Stage | When | Capability |
|---|---|---|
| `prepareToolCallArguments` (`:503-515`) | After tool dispatch, before validation | Compatibility shim — rewrite raw LLM args to fit the schema (e.g., legacy snake_case keys, missing defaults) |
| `validateToolArguments` (from pi-ai) | After prepare | Throws on schema mismatch; loop converts throw into an `immediate` error result, batch continues |
| **`beforeToolCall`** (`:536-553`) | Args validated, tool not yet executed | Block (`{ block: true, reason }`) — execution is short-circuited and an error tool result with the given reason is emitted in place |
| `tool.execute` (`:577-594`) | After preflight | The actual tool body. `onUpdate` callback streams partial results as `tool_execution_update` events |
| **`afterToolCall`** (`:617-642`) | After execute, before final events | Field-replace any of `content`, `details`, `isError`, `terminate`. No deep merge. Throws are converted into error tool results. |
| `emit tool_execution_end` (`:658-666`) | After finalize | UI gets the post-`afterToolCall` result. Persisted toolResult message (`:680-683`) is emitted later (in source order, parallel mode) |

What this enables that a vanilla "execute and stuff into context" loop doesn't:

- **Preflight without tool body knowledge**: `beforeToolCall` sees the validated args but is independent of the tool implementation. Drop-in for permission gates, audit logging, "are you sure?" UX, kill switches. The README's example (`bash` disabled if `toolCall.name === "bash"`) is the canonical use.
- **Postprocess result rewriting**: `afterToolCall` is where you *redact* secrets from outputs, *trim* large stdout, *add* audit metadata to `details` for UI rendering, or **flip `terminate: true` after the fact** based on result content. Field-replace semantics mean you can replace `content` (what the LLM sees) without touching `details` (what the UI sees), or vice versa.
- **Failure isolation**: throws inside `afterToolCall` become error results for *this* tool call only. Parallel batch continues. CHANGELOG `#3084` (2026-04-17) shows this was a deliberate fix — earlier versions aborted the whole batch on `afterToolCall` throw.

We have nothing equivalent in the orchestrator. The closest analogue is `tool-output-compression` handoff's idea of post-truncating tool outputs, but that work is positioned as a single point in the pipeline. `afterToolCall`-as-a-hook lets *every* stack layer (security, compaction, audit, telemetry) compose without any one layer knowing about the others.

---

## 4. Steering vs Follow-up — the queueing model

`agent.ts:113-144` defines `PendingMessageQueue` with a `mode: "all" | "one-at-a-time"`. The Agent owns two such queues:

```typescript
constructor(options: AgentOptions = {}) {
  this.steeringQueue = new PendingMessageQueue(options.steeringMode ?? "one-at-a-time");
  this.followUpQueue = new PendingMessageQueue(options.followUpMode ?? "one-at-a-time");
}
```

API (`agent.ts:252-280`):

- `steer(message)` — enqueue. Drained at *every* turn boundary while the agent is running.
- `followUp(message)` — enqueue. Drained only when the agent would otherwise stop (the outer-loop awakening described in §1).
- `clearSteeringQueue()`, `clearFollowUpQueue()`, `clearAllQueues()`, `hasQueuedMessages()`.
- `steeringMode` / `followUpMode` setters at runtime — switch between draining all queued messages at once vs. one per opportunity.

The drain semantics matter (`agent.ts:126-139`):

```typescript
drain(): AgentMessage[] {
  if (this.mode === "all") {
    const drained = this.messages.slice();
    this.messages = [];
    return drained;
  }
  const first = this.messages[0];
  if (!first) return [];
  this.messages = this.messages.slice(1);
  return [first];
}
```

`one-at-a-time` is the default — a backpressure model. The agent absorbs one steering message per turn, and the rest of the queue waits. This is the right default for chat: if the user types 4 messages while the LLM is mid-response, the agent doesn't see all 4 jammed together at the next turn boundary, it sees them one per turn. Order is preserved.

Why this is interesting for us: the `repl-turn-efficiency` handoff (§1) talks about "S3 contextual suggestions may worsen the Omega problem by encouraging more tool use" and feature-flags suggestions. The pi-agent-core `mode: "all"` vs `"one-at-a-time"` switch is the same problem, but as a first-class API knob. Our turn-bookkeeping is implicit in the orchestrator request loop; theirs is named.

`continue()` also has drain logic (`agent.ts:336-353`): if the last message is `assistant`, `continue()` first drains steering, then follow-up, then errors. Drain order is meaningful — steering is treated as more recent, more user-driven.

---

## 5. Proxy Architecture — what `streamProxy` actually does

`proxy.ts:101-233` is a **bandwidth-optimization layer**, not a security layer.

The shape:
- Server (provider proxy) sends events with the `partial` field stripped — only the *delta* is on the wire.
- Client reconstructs `partial` locally inside `processProxyEvent` (`:238-367`) by mutating a `partial: AssistantMessage` object as deltas arrive.
- Tool-call deltas use `parseStreamingJson` (from pi-ai) so partial JSON is always valid as far as it parses.

Why it exists: in browser SaaS apps, the delta-only payload is significantly smaller than the full partial message on each chunk (especially after a long thinking block with thousands of accumulated tokens). The server is also where API keys live — `authToken` is the user's session token, *not* the LLM provider key. Provider key never reaches the browser.

Reusable pattern, not directly applicable to us (we don't run a SaaS frontend that needs to hide provider keys from users on a different trust boundary). But the `streamFn` injection pattern (`agent.ts:194` `this.streamFn = options.streamFn ?? streamSimple;`) is the borrowable bit — `streamFn` is a single substitution point that lets the Agent class be transport-agnostic. We could mirror this for our orchestrator if we ever wanted to switch between local llama-server and a remote provider without changing the agent class.

---

## 6. What's NOT in pi-agent-core (and why)

The package is deliberately small. None of the following are present:

- **No built-in tools.** Zero. No `read`, `write`, `bash`, `grep`, `web_fetch`. Tools are an entirely external concern, defined by the consumer using TypeBox schemas. The sibling package `pi-coding-agent` has 14 tool files (`bash.ts`, `edit.ts`, `edit-diff.ts`, `find.ts`, `grep.ts`, `ls.ts`, `read.ts`, `write.ts`, `file-mutation-queue.ts`, etc.) totaling ~45K LOC — those are the actual coding-agent tools, riding on top of pi-agent-core.
- **No memory tier.** No L0-L4 hierarchy, no episodic store, no skill library. The Agent's `state.messages` is the entire memory model. Compaction/summarization is the consumer's job via `transformContext`.
- **No skill / subagent / planner primitives.** README is explicit: *"Pi ships with powerful defaults but skips features like sub agents and plan mode. Instead, you can ask pi to build what you want or install a third party pi package that matches your workflow."*
- **No security/sandbox.** `beforeToolCall` is a *hook for the consumer to implement gates*, not an enforcement layer. There is no `seccomp`/`chroot`/`docker` integration anywhere in the package.
- **No MCP.** Tools are the `AgentTool` interface; MCP would be a separate adapter, not a first-class concept.
- **No conversation persistence.** No SQLite, no JSONL, no checkpoint/resume API. Consumer holds `state.messages` and decides what to do.

This is consistent with the framework's positioning. It's the runtime layer below a coding-agent (or any agent), not a batteries-included harness. The natural comparison is **deepagents** (intake-144, LangGraph harness with planning + sub-agents + MCP) vs **pi-agent-core** (no harness, just a runtime). They sit at different abstraction levels.

---

## 7. Comparison Matrix

| Property | pi-agent-core | GenericAgent | deepagents (intake-144) | Hermes-agent (intake-117) | Anthropic Agent SDK |
|---|---|---|---|---|---|
| Language | TypeScript | Python | Python | Python | Python/TS |
| Core LoC | ~2K (with proxy) | ~3K core, ~9K w/ frontends | ~3K (LangGraph wrapper) | bigger; full app shell | proprietary |
| Built-in tools | **None** | 9 atomic + `code_run` escape hatch | Pre-tuned: planning, file ops, shell, sub-agent delegation | Skill plugins | MCP-first |
| Sub-agent / plan mode | **Explicitly excluded** | SOP-prompted, not engine-level | First-class | Multi-agent | First-class |
| Memory model | `state.messages` only | Flat-file L0-L4 + remote skill_search | LangGraph state + file-based output store | Bounded files + FTS5 | Memory tool |
| Tool execution | Configurable parallel/sequential, **per-tool override** | Single tool-at-a-time loop | LangGraph-native | Skill execution | Parallel by default |
| Hook surface | `beforeToolCall` + `afterToolCall` hooks; `transformContext` per-turn | `do_no_tool` recovery only | LangGraph callbacks | Skill lifecycle | Tool middleware |
| Steering / mid-run injection | **First-class API** (`steer`, `followUp`, queue modes) | Not present | LangGraph interrupt API | Out-of-band msg push | Streaming pause |
| Streaming | Event sink + custom message types | Generator-based dispatch | LangGraph events | App-level | SSE |
| Proxy backend | First-class `streamProxy` (delta-only wire format) | Not applicable | N/A | App-level | First-party |
| Dependencies | `pi-ai`, `typebox` | Anthropic / OpenAI / Kimi clients | `langgraph`, `langchain-anthropic` | LiteLLM / OpenAI-compat | Anthropic SDK |
| Custom message types | **Declaration merging** — type-safe | Not modeled | Custom state schema | Tagged messages | Tool blocks only |
| Tests | 2,048 LOC test, ~1:1 with src | Limited | LangGraph-tested | Limited | Internal |
| Active contributors | 80+, 2 of whom are notable (Zechner, Ronacher) | 1 dominant + 18 | LangChain core team | Nous Research | Anthropic |

**Where pi-agent-core genuinely contributes** — distinct from the alternatives:

1. **Two-stage message pipeline (transformContext + convertToLlm) with declaration-merging custom message types**: this is the cleanest abstraction in the lineup for "agent transcript ≠ LLM payload". GenericAgent has no model. deepagents has LangGraph state. Hermes-agent uses tags. Anthropic SDK has tool blocks but no transcript-level custom types. **This is the strongest pattern to lift.**
2. **`afterToolCall` field-replace semantics with throw-isolation**: redaction/audit/compaction-on-result without coupling to tool implementation. Strong composition story.
3. **Steering vs follow-up as named primitives**: nobody else in this list separates "interrupt before next turn" from "wake up after finishing", and both are common in chat UX. Naming matters — once you have the words, the orchestrator design discussions get sharper.
4. **`one-at-a-time` vs `all` queue mode**: backpressure as a first-class API knob.
5. **Per-tool `executionMode` override** with batch-falls-back-to-sequential semantics: a coherent rule for mixing tools that need exclusive access (DB writes, single-FD ops) with tools that don't.

**Where pi-agent-core is inferior or just different**:

- No batteries — every consumer rebuilds tools, memory, planning, MCP. For us this is *good* if we're after patterns; *bad* if we wanted to drop in a working agent.
- TypeScript-only. EPYC orchestrator is Python. Direct port of a primitive (e.g., `PendingMessageQueue` with mode switching) is straightforward; framework-wholesale adoption is not.
- No persistence layer. We'd still need our own `messages` checkpointer.

---

## 8. Verdict Delta (vs. initial intake-473 assessment)

**Initial intake**: novelty=low, relevance=low, credibility=null, verdict=worth_investigating. Justification was mostly *"agent-framework category is saturated; no benchmarks; single-author indie; TS not Python"*.

**Post-deep-dive corrections**:

| Axis | Initial | Revised | Why |
|---|---|---|---|
| Novelty | low | **low-medium** | Patterns themselves aren't novel research, but the *named primitive set* (transformContext / convertToLlm split, steering vs follow-up queues with `one-at-a-time` mode, `beforeToolCall` / `afterToolCall` field-replace, terminate-unanimous-batch) is more crisply factored than any other open-source TS agent framework I've reviewed. That's a documentation-and-architecture novelty, not a research one. |
| Relevance | low | **medium** | Initial scoring assumed TS = irrelevant. Revising because (a) the *primitives* port to Python in ~50 LOC each, (b) we have explicit handoffs that need exactly these primitives but with different names (`hermes-outer-shell`, `tool-output-compression`, `repl-turn-efficiency`, `meta-harness-optimization`, `orchestrator-conversation-management`), (c) we *do* maintain a TS frontend (Hermes outer shell, Package E streaming) where pi-agent-core could be a literal drop-in. Not high — there's no immediate forcing function. |
| Credibility | null | **3** (medium) | Initial scoring said "repo, no empirical claims". Reality: 80+ contributors, 3,805 commits, 70 versions, formal CHANGELOG with issue links, ~1:1 test/source ratio, **Armin Ronacher is a top-5 contributor**. No benchmark suite, but the project publishes session datasets to HuggingFace (`huggingface.co/datasets/badlogicgames/pi-mono`) — those *are* empirical evidence at the agent-product layer. Score: peer-reviewed=N (–0), recent=+1 (active), authority=+1 (Ronacher cosignatory), bias=–0, corroboration=+1 (project is referenced by `openclaw/openclaw` SDK integration). |
| Verdict | worth_investigating | **adopt_patterns** (with caveats) | Specific patterns are portable and named-better-than-ours. Whole-framework adoption stays no — TS, no batteries, our orchestrator is Python. |

**Specific patterns to adopt** (in priority order):

1. **Two-stage message pipeline** (`transformContext` + `convertToLlm`) — naming + factoring. Map to `epyc-orchestrator/src/orchestrator/` request building. **Sequence**: rename our scattered `_to_llm_messages` helpers, add a per-turn `transform_context` hook that runs before LLM-payload conversion. Pairs naturally with `tool-output-compression` and `context-folding-progressive` handoffs.
2. **`beforeToolCall` / `afterToolCall` hooks with field-replace + throw-isolation semantics** — direct map to a new orchestrator middleware layer. Required for clean composition of (security gates · audit · output redaction · compaction) without each layer knowing the others. Naturally lands in `meta-harness-optimization` work.
3. **Steering / follow-up split as named API** — adopt the *naming* even if we don't adopt the queues. `repl-turn-efficiency` handoff currently lacks language for "user typed mid-response" vs "user typed after response".
4. **Per-tool `executionMode` override + batch-fallback** — useful when we add tool concurrency (currently sequential by default in our orchestrator). Defer until we have parallel tools in the first place.
5. **Terminate-unanimous-batch semantics** — drop-in when we add an early-stop signal from tools. Cheap to copy.

**Specific patterns to NOT adopt**:

- The `streamFn` injection pattern for proxy backends (we have a single transport: local llama-server + occasional Anthropic API; no SaaS-frontend trust boundary to preserve).
- TypeScript declaration-merging mechanism for custom message types (Python equivalent is just a discriminated union dataclass; no language-feature port).
- The Agent class wholesale (Python orchestrator already has a different state model).

**Sibling packages worth a separately-scoped intake**:

- **`pi-pods`** — CLI for managing vLLM deployments on GPU pods. Potentially relevant to `gpu-acceleration-path` handoff if/when GPU work resumes. Should be a distinct intake, not a sub-section of this one.
- **`pi-coding-agent`** — 45K-LOC consumer of pi-agent-core with real tool implementations (read/write/edit/grep/find/ls/bash/edit-diff/file-mutation-queue/truncate). Worth a *coding-agent benchmarking* intake, separate from the framework deep-dive.

---

## 9. Key Implementation References (for anyone borrowing patterns)

Absolute paths in the cloned repo at `/tmp/pi-mono/`:

- Loop body: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:155-234` (`runLoop`)
- Steering and follow-up polling: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:165`, `:218`, `:222`
- Termination semantics: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:499-501` (`shouldTerminateToolBatch`)
- Parallel tool execution: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:412-471` (`executeToolCallsParallel`)
- Sequential tool execution: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:360-410` (`executeToolCallsSequential`)
- `beforeToolCall` integration: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:536-553`
- `afterToolCall` integration with throw-isolation: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:617-642`
- `transformContext` + `convertToLlm` pipeline: `/tmp/pi-mono/packages/agent/src/agent-loop.ts:248-254`
- AgentMessage / CustomAgentMessages declaration merging: `/tmp/pi-mono/packages/agent/src/types.ts:233-256`
- `PendingMessageQueue` with `one-at-a-time` vs `all` modes: `/tmp/pi-mono/packages/agent/src/agent.ts:113-144`
- Steering/follow-up public API: `/tmp/pi-mono/packages/agent/src/agent.ts:252-280`
- `continue()` drain order (steering → follow-up → error): `/tmp/pi-mono/packages/agent/src/agent.ts:326-353`
- `streamFn` injection point: `/tmp/pi-mono/packages/agent/src/agent.ts:194`, `:269`
- Proxy delta-only wire format: `/tmp/pi-mono/packages/agent/src/proxy.ts:36-57`, `:238-367`
- CHANGELOG with issue traceback: `/tmp/pi-mono/packages/agent/CHANGELOG.md`
- Sibling consumer (real tools): `/tmp/pi-mono/packages/coding-agent/src/core/tools/`

---

## 10. Open questions / follow-up signals

- **Empirical performance** — pi-coding-agent posts session datasets to HuggingFace. Worth a pass to see if there is meaningful task-success or token-usage data we can compare against our own. (Pinned for separate intake on `pi-coding-agent`, not this one.)
- **`pi-pods` and vLLM deployment** — orthogonal to this entry; if the GPU acceleration path resumes, pull `pi-pods` as a separate intake.
- **Trip-wire**: if EPYC ever moves to a TS-based orchestrator shell (would be a significant pivot), revisit `relevance` upgrade to `high`. The patterns + the existing TS stack would make pi-agent-core a candidate for direct adoption.
- **Confirmation-bias check (Tier 2b)**: searched for *"pi-agent-core" criticism* and *"pi-agent-core" limitations* — no results. Searched for *"badlogic pi-mono" issues* — repo has 1,000+ closed issues following the auto-close-new-contributors policy, which is a defensible-but-unusual governance choice. No evidence of design-flaw critiques surfaces in public discussion. Absence of contradicting evidence is partly because the project is recent (8 months old) and the audience is narrow (TS coding-agent builders).
