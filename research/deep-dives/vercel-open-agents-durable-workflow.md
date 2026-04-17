# Deep Dive — vercel-labs/open-agents + Vercel Workflow SDK + Sandbox

**Intake**: intake-397 (novelty=low, relevance=low, verdict=adopt_patterns)
**Deep-dive date**: 2026-04-17
**Scope**: Validate the three patterns flagged at intake (control-plane/execution separation, durable workflow reconnect-to-stream, snapshot-based sandbox hibernate/resume) against the actual implementations, and decide whether they are actionable for hermes-outer-shell and the REPL, or whether they reduce to "use a TypeScript workflow engine on a managed cloud."

---

## 1. Workflow SDK Durability Mechanics

### What the SDK actually is

Vercel Workflows is a managed runtime built on the open-source **Workflow SDK** (`workflow-sdk.dev`) for TypeScript/JavaScript, with a Python port via the Vercel Python SDK. The programming model uses two JS directives:

- `'use workflow'` — marks an orchestration function. Must be deterministic. Is re-executed (replayed) on every resumption.
- `'use step'` — marks a unit of real work. Has "full runtime access" (Node APIs, npm, I/O). Results are persisted to an **event log** and not re-executed on replay.

The execution model is the Temporal/Restate/Inngest family: the orchestration body is replayed from the event log to rebuild local variables, and `await step()` calls short-circuit with cached results when the event log already has a recorded outcome for that invocation. When the replay reaches an uncommitted step, execution continues forward.

Determinism is enforced by the runtime monkey-patching `Math.random` and `Date` to return stable values during replay. Anything non-deterministic that isn't wrapped in a step (network, filesystem, clocks that aren't `Date`) will diverge on replay and break resumability.

### What is durable vs in-memory

| Layer | Durable | Volatile |
|---|---|---|
| Step inputs and outputs | ✅ event log | — |
| Workflow-local variables | ✅ reconstructed by replay | Not stored; re-derived each resumption |
| Streams | ✅ Redis-backed on Vercel; filesystem locally | Chunks deleted after retention expires |
| Timers / sleeps | ✅ logical time, not wall-clock | — |
| In-step computation mid-execution | ❌ | ✅ if the step crashes partway, it re-runs from scratch |
| Sandbox VM state | ❌ not a workflow concern | Orthogonal system (see §2) |

The critical insight: **the workflow's durability guarantee is exclusively at step boundaries**. A long-running step (e.g., an agent turn that takes 90 seconds) has no internal checkpoints. If the function crashes mid-step, the entire step re-runs on retry. The model is fundamentally "write idempotent steps at the right granularity, and the runtime handles everything between them."

### Stream reconnection — the actual mechanism

This is the load-bearing piece for "durable reconnect-to-stream." From the Workflow SDK streaming docs:

- A stream is a managed queue of chunks, backed by Redis on Vercel (filesystem for local dev).
- Chunks bypass the event log (the event log would be too expensive for every token) but are kept in separate persistent storage during the stream's retention window.
- Clients reconnect via `run.getReadable({ startIndex })`, where `startIndex` is the last chunk index the client received (negative values mean "N from the end", with the caveat that they resolve to different absolute positions on each call — not true pagination).

The reconnection pattern in open-agents (`apps/web/app/api/chat/route.ts`):
1. Chat record stores `activeStreamId` for the current workflow run.
2. On a new POST, the route checks if `activeStreamId` references a still-running or pending workflow.
3. If yes, it re-attaches to that run's readable stream instead of spawning a new workflow.
4. Compare-and-set semantics (`compareAndSetChatActiveStreamId`) handle the race where two tabs reconnect simultaneously — the loser calls `getRun(id).cancel()` and returns 409.
5. A stale `activeStreamId` is cleared and a new workflow is started.

This is the "reconnect to a live agent turn without losing progress" pattern. The durability boundary is: the **workflow's completed steps** persist (you don't re-run the bash commands the agent has already executed), and the **stream chunks** persist for some retention window so a reconnecting client can catch up on output. An in-progress step's internal state is still volatile.

### What breaks

- Non-deterministic code in the workflow body (not a step) corrupts replay.
- Mid-step crashes lose all work inside the step and re-run on retry → the sandbox is expected to be idempotent under repeated execution, which is a strong assumption for a shell.
- The `startIndex` reconnection primitive is offset-based with caveats; there is no true cursor API yet.
- Issue #781 (persist large `web_fetch` response bodies) is exactly this failure mode: the workflow only carries a truncated preview in its event log; the full payload was volatile and is gone on reconnect. The proposed fix is to write the full payload to the sandbox filesystem and store only the path in the workflow.

---

## 2. Sandbox Snapshot Model

### Vercel Sandbox — what is actually snapshotted

From `vercel.com/docs/vercel-sandbox/concepts/snapshots`:

> "Snapshots capture the state of a running sandbox, including the **filesystem and installed packages**."

And from the persistent-sandboxes doc (beta):

> "When you stop a persistent sandbox, the SDK automatically **snapshots the filesystem**. When you resume it, a new session boots from that snapshot."

**Vercel Sandbox snapshots are filesystem-only.** No memory, no running processes, no open file descriptors, no network state. The VM is Firecracker-based for isolation, but the snapshot is effectively a filesystem image, not a microVM memory snapshot. Resuming starts a new session (new VM instance) with the filesystem restored.

Use cases explicitly listed: "skip dependency installation by snapshotting after setup", "save progress on long-running tasks", "give teammates an identical starting point." All filesystem-level.

**Implication for the "snapshot-based resume" pattern**: the claim at intake overstated what Vercel actually does. What open-agents relies on is:
1. Agent state lives **in the workflow event log**, not in the sandbox.
2. Sandbox state lives **in the filesystem**, which the snapshot captures.
3. Processes die on stop; the agent must restart any background servers after resume (this is why the `bash` tool has an explicit `detached` flag and a readiness-probe pattern is recommended).

### E2B — what a real memory-snapshot system looks like

For contrast, E2B (also Firecracker-based) does something substantively different:

> "both the sandbox's filesystem and memory state will be saved. This includes all the files in the sandbox's filesystem and all the running processes, loaded variables, data, etc."
> — ~4 seconds to pause per GiB of RAM, ~1 second to resume, up to 30 days retention.

E2B uses actual Firecracker microVM memory snapshots. A paused Python REPL with variables bound in memory can resume with all variables intact. Processes resume from the exact syscall they were blocked on.

This is a real CPU/memory hibernate. Vercel Sandbox is not.

### Modal — filesystem-snapshot family, same as Vercel

> "For longer durations, Modal recommends using Filesystem Snapshots to preserve its state, and then restore from that snapshot with a subsequent Sandbox."

Same category as Vercel: filesystem-only snapshots plus idle/readiness primitives. Sandboxes are ephemeral; durability is at the FS layer.

### Anthropic Computer Use

Computer Use is a tool surface (the model drives a VM via screenshots and keystrokes), not a managed workflow/sandbox primitive. There is no durable workflow under it. If the containing app crashes mid-trajectory, the trajectory is lost unless the app layer persists it. It is closer to open-agents' *tools layer* than to its *workflow layer*.

### Translatability to Linux CPU-only (our stack)

| Mechanism | Ship today? | Translates to our stack? |
|---|---|---|
| Vercel-style FS-only snapshot | trivially: `tar`, `zfs snapshot`, `btrfs send/receive`, or plain rsync of a workspace dir | Yes, but we already have this implicitly (the workspace is a plain git clone). The useful variant is "snapshot the workspace + pinned tool cache" for fast seeding of fresh agent runs. |
| E2B-style memory+process snapshot via Firecracker | Requires running agents inside Firecracker microVMs. Non-trivial infra. | Possible but heavy. Would require an F1 microVM host + jailer + agent runtime inside. |
| CRIU (process-level checkpoint/restore in userspace) | On vanilla Linux, yes; Python processes with open GPU handles, network sockets, and JIT code (llama.cpp's mmap'd models) are problematic. | **Limited.** CRIU fails on GPU handles (confirmed by NVIDIA docs), requires identical library versions at restore (our venvs drift), requires PID availability. For a Python REPL with nothing exotic loaded, it can work. For a REPL that has already invoked an inference HTTP call and holds socket state, it's fragile. |
| Workflow event log (own impl) | Yes — SQLite write-ahead log of `(step_id, input_hash, output)` tuples | **Yes, this is the actually-portable piece.** See §5. |

**Net**: the "snapshot-based resume" claim in the intake conflates two things — (a) Vercel's FS-only snapshot, which is trivial to replicate and already implicit in our setup; and (b) E2B-style memory hibernate, which open-agents does not actually use. The interesting technique is not the snapshot but the workflow-log substrate that sits above the sandbox and makes FS-only snapshots sufficient.

---

## 3. Control-Plane / Execution-Plane Contract

### The open-agents tool surface

From `packages/agent/tools/` and `packages/agent/open-harness-agent.ts`, the tool list is:

| Tool | Params (zod) | Purpose |
|---|---|---|
| `bash` | `command: string`, `cwd?: string`, `detached?: boolean` | Shell in sandbox. `detached` for background servers. 120s timeout, 50 KB stdout truncation. |
| `read` | (path) | Read file from sandbox |
| `write` | (path, content) | Write file to sandbox |
| `edit` | (path, oldString, newString) | Targeted edit (Claude Code style) |
| `glob` | (pattern) | File pattern matching |
| `grep` | (pattern, path?) | Content search |
| `fetch` | (url) | Web fetch (the one issue #781 wants to improve) |
| `ask_user_question` | (question) | Escalate to human |
| `task` | `subagentType`, `task`, `instructions` | Spawn a named subagent, return its summary only |
| `skill` | `skill: string`, `args?: string` | Load a skill file from the sandbox (slash-command-like; `/commit`, `/pdf`) |
| `todo_write` | (todos) | Plain todo list tool (Claude Code parity) |

The **sandbox interface** that tools call into (inferred from `bash.ts`):
- `sandbox.exec(command, cwd, timeout, { signal })` → `{ success, exitCode, stdout, stderr, truncated }`
- `sandbox.execDetached(command, cwd)` → `{ commandId }`
- Plus file read/write primitives (in the other tools)

### Is this a clean contract?

**Yes**, and it is the cleanest piece of open-agents. The agent package does not know which sandbox backend it is running against — the sandbox is passed into `experimental_context` as an opaque handle, and the tools call a small set of methods on it. The contract is:

```
interface Sandbox {
  exec(cmd, cwd, timeout, opts): ExecResult
  execDetached(cmd, cwd): { commandId }
  readFile(path): string
  writeFile(path, content): void
  // (glob/grep may be FS-level via ripgrep inside exec)
}
```

Issue #776 (request to add Daytona backend) indicates the abstraction is intentional but not yet pluggable — the sandbox interface is implicitly coupled to Vercel. It *could* be made backend-agnostic; the open issue shows someone is aware of this.

### Is this directly analogous to hermes-outer-shell?

Partially. Hermes runs a conversation-level loop (memory, skills, multi-platform gateway) and delegates real work to the orchestrator via `/v1/chat/completions`. The analogy maps:

| open-agents | hermes-outer-shell |
|---|---|
| Next.js UI + workflow orchestrator | Hermes (conversation/memory) |
| Agent package (LLM loop + tool registry) | EPYC orchestrator (frontdoor → specialist REPL) |
| Sandbox VM | REPL environment inside orchestrator process |

But the analogy **breaks** at two places:
1. open-agents agent loop runs **outside** the sandbox and calls into it through a thin RPC; our REPL runs **inside** the orchestrator process (the REPL is just Python globals). There is no RPC boundary to snapshot.
2. open-agents' "durable workflow" is the workflow SDK; ours is the specialist turn inside a FastAPI request. There is no event log; a crashed turn is lost.

The *directly* useful piece is the **typed sandbox contract**: a small, pluggable interface between "the thing that runs the LLM loop" and "the thing that executes tools." We already have this split within hermes-outer-shell Phase 2 (the `x_*` override parameters on `/v1/chat/completions` are exactly the typed contract across the outer/inner boundary). The tool set itself (bash/read/write/edit/grep/glob/fetch/task/skill/todo) is essentially a Claude-Code-compatible surface and is not a new idea.

---

## 4. Comparison Matrix

| Property | open-agents | Claude Computer Use | E2B | Modal | Daytona |
|---|---|---|---|---|---|
| Sandbox isolation | Firecracker (Vercel) | app-provided (usually Docker) | Firecracker | gVisor/firecracker | Docker + dev-container |
| Snapshot semantics | **FS-only** | none native | **FS + memory + processes** (true hibernate) | FS snapshots | dev container rebuild |
| Workflow durability | **Vercel Workflow SDK** (managed event log) | app-provided | none in sandbox layer; app must implement | some via `.function` durable retries | none; stateless workspace tool |
| Agent-outside-sandbox | yes, explicit | yes (driver outside VM) | either; SDK runs outside | either | yes |
| Tool surface | Claude-Code-shaped (bash/read/write/edit/grep/glob/fetch/task/skill) | screen+mouse+kb | language SDK (run_code, filesystem) | Python-first SDK | workspace-oriented (dev env) |
| Stream reconnect | **yes, via workflow stream index** | no native primitive | no native primitive | no native primitive | no |
| Open source? | **yes**, MIT (agent + UI code) | no (Anthropic-proprietary) | yes (SDK), managed service | SDK OSS, runtime proprietary | yes |

**Cleanest control-plane/execution-plane separation**: open-agents is the cleanest among these for the specific pattern we care about (typed sandbox interface + durable workflow around agent turns). E2B has a more powerful sandbox primitive but no workflow layer; Modal has durability primitives but weaker tool conventions; Computer Use has neither and is a tool-surface only.

But — and this is the honest take — open-agents' workflow layer is **not the agent-architecture contribution**. It is a Vercel product placement. The genuinely novel piece is Vercel's Workflow SDK, which is an independent product that happens to back this reference app. The agent itself is an unremarkable Claude-Code-alike.

---

## 5. Translatable Patterns for hermes-outer-shell and REPL

Mining for what is actually adoptable. Four patterns survive scrutiny; two do not.

### 5.1 Survives — Typed sandbox contract as an explicit boundary

The `Sandbox` interface (exec/execDetached/read/write) is small and clearly defined. Port analogue:

- Current state: the REPL lives inside the orchestrator process; there is no explicit `ExecutionEnvironment` interface separating the tool-execution surface from the LLM loop.
- Proposal: extract an `ExecutionEnvironment` protocol from `repl_environment/` with methods (`exec`, `read_file`, `write_file`, `grep`, `code_search`, `list_dir`, `peek`, `web_search`, `web_fetch`) and a concrete `InProcessREPL` implementation. The typed interface makes swapping for a subprocess-isolated REPL, a Docker-based REPL, or a remote REPL a one-adapter change.
- Why this helps: repl-turn-efficiency.md Gap 3 (`_batch_llm_query` combined-op) and the workspace_scan proposal both become clearly-scoped interface changes rather than cross-cutting edits. Also supports the planned safety isolation discussion in `handoffs/archived/*` about eventually running untrusted code in containers.

### 5.2 Survives — `task` / subagent contract as scoped delegation

open-agents' `task` tool takes `(subagentType, task, instructions)` and returns only a summary. This is a tight formalization of what we already do with `_escalate()` and child specialists but with two refinements worth stealing:

- **Named subagent types**. Our current `_escalate(reason)` picks from a registry by role; open-agents has an enum of subagent kinds with distinct system prompts per type. Closer to a typed contract, less reliant on reason-string matching.
- **Only a summary returns to the parent.** Sub-turns' internal tool calls are NOT surfaced to the parent agent's context. This is equivalent to our `compact=True` specialist reports but with an enforced boundary — the parent cannot even inspect the subagent's internal turns. Useful for context budget.

### 5.3 Survives (partially) — Workflow event log as reconnect substrate

The actual useful piece of the Workflow SDK is the **event log**, not the cloud runtime. We cannot adopt Vercel Workflows, but we can build a minimal SQLite-backed event log:

```
events(run_id PK, step_id, input_hash, output_blob, committed_at)
```

Where each REPL tool call is a step with a deterministic input hash. A disconnected client reconnecting to an active turn could replay the log to reconstruct state without re-executing tools. This is the *exact* mechanism repl-turn-efficiency.md needs for wasted-turn-on-reconnect avoidance — and the pattern is 200 lines of Python, not a cloud dependency.

Scope for the first iteration:
- Wrap `REPLEnvironment.exec`, `peek`, `grep`, `list_dir`, `code_search`, `web_search`, `web_fetch` to persist `(turn_id, tool_name, args_hash) → output` in SQLite.
- On reconnect to a partially-completed turn, replay the log to rebuild the tool-call history in context before continuing.
- Tie into the existing `inference_tap.log` / `autopilot.log` infrastructure — same data shape.

This is **a small, valuable adoption** — not "use a TypeScript workflow engine."

### 5.4 Survives — Persisting large tool outputs to the sandbox FS (issue #781)

The fix pattern issue #781 proposes is generalizable and directly applicable to repl-turn-efficiency and tool-output-compression:

- Tool returns a compact summary `{ status, content_type, byte_count, file_path }` to the model.
- Full payload is written to a workspace-local file.
- The model accesses details via `read(file_path, offset, limit)` when needed.

This is exactly the TOON-encoded-summary + file-backing pattern we already partially use. open-agents' concrete convention (`status/content_type/byte_count/file_path` shape) is worth standardizing across `web_fetch`, `web_search`, `peek`, and any other tool whose outputs can blow past context budget.

### 5.5 Does not survive — Snapshot-based hibernate for the agent

Vercel's snapshots are FS-only. They are not a hibernate primitive. The "snapshot-resume" framing at intake was generous; in practice open-agents does not hibernate a running agent turn, it just re-starts the VM with the filesystem restored and re-executes whatever the workflow event log says to re-execute.

For our stack, we would need CRIU to hibernate a running Python REPL with socket state, and CRIU is fragile for Python processes with open HTTP connections to llama-server. Not worth pursuing. The **workflow event log (§5.3)** is the correct substitute — you don't hibernate the process; you log enough to redo the turn.

### 5.6 Does not survive — GitHub branch→commit→PR integration

Useful reference but superfluous for us. Our work is across four local repos with git workflows already well-established. The open-agents automation (auto-branch, auto-commit, auto-push, auto-PR) is a UI-level concern for their web app; we gain nothing porting it. This can be struck from future mining.

---

## 6. Verdict Delta

Initial intake: `novelty=low, relevance=low, verdict=adopt_patterns` — correct overall, but the justification needs updating.

### Recommended delta

| Field | Before | After | Rationale |
|---|---|---|---|
| novelty | low | **low (unchanged)** | No novel technique; all patterns are recognizable from Temporal/Inngest/Claude-Code/E2B. |
| relevance | low | **medium-low** | One pattern (workflow event log for reconnect) is genuinely adoptable; another (typed sandbox contract) formalizes something we already have. |
| verdict | adopt_patterns | **adopt_patterns (unchanged)** | Still pattern-level adoption only. No code, no dependency. |

### Clarifications to the intake `notes` field

Proposed replacement for the existing notes:

> Three patterns at intake, on closer inspection only two survive scrutiny:
> (1) **Typed sandbox contract** (a small `Sandbox` interface between the LLM loop and the execution environment) — analogous to our `REPLEnvironment` but worth formalizing as an explicit protocol, e.g. `ExecutionEnvironment`, to decouple the agent from the execution backend. Minor refactor in `repl_environment/`.
> (2) **Durable reconnect via workflow event log** — the technique, not the Vercel SDK. A SQLite WAL of `(run_id, step_id, args_hash) → output` tuples is ~200 lines of Python and directly addresses repl-turn-efficiency.md's reconnection-waste concern. Actionable.
> (3) **Snapshot-based sandbox hibernate** — overstated at intake. Vercel Sandbox snapshots are filesystem-only (confirmed in `docs/vercel-sandbox/concepts/snapshots`); E2B does real memory+process hibernate via Firecracker, but open-agents does not use that. For our CPU-only Linux stack the correct substitute is the event log (pattern 2), not CRIU, which is too fragile for Python processes holding sockets to llama-server. Discard this mining target.
>
> Bonus survivors from deeper reading:
> (4) **Scoped subagent contract**: `task(subagentType, task, instructions)` returns only a summary; internal tool calls stay isolated from parent context. Tighter than our `_escalate()` signal. Worth mirroring.
> (5) **Large-output-to-FS pattern** (from issue #781): tool returns `{ status, content_type, byte_count, file_path }`, full payload on disk, model fetches details via read. Generalize across `web_fetch`, `web_search`, `peek`. Already partially present; make it a convention.
>
> Does not survive: snapshot hibernate (FS-only on Vercel), GitHub PR automation (UI-level, unhelpful for our local multi-repo workflow).

### Cross-reference updates

The existing cross-references (hermes-outer-shell, hermes-agent-index, meta-harness-optimization, repl-turn-efficiency, tool-output-compression) are all correct. The most actionable handoff for mining these patterns is **repl-turn-efficiency.md** (for the event-log reconnect pattern + FS-backed large outputs), with **hermes-outer-shell.md** secondary (typed boundary contract).

---

## Appendix — Raw findings log

- `vercel-labs/open-agents` tool files: `ask-user-question`, `bash`, `fetch`, `glob`, `grep`, `read`, `write`, `edit`, `skill`, `task`, `todo` (11 tools + utils/tests). Zod schemas throughout.
- `bash.ts`: `command: string, cwd?: string, detached?: boolean`. 120 s timeout, 50 KB truncation, abortable.
- `skill.ts`: file-backed, slash-invoked (`/commit`, `/pdf`), frontmatter-stripped, arg-substituted, supports `disable-model-invocation` to prevent LLM invocation.
- `task.ts`: `subagentType` enum, `task` summary string, `instructions` long-form; returns only concise summary, subagent tool calls isolated.
- `open-harness-agent.ts`: `ToolLoopAgent` with 10 registered tools, sandbox passed via `experimental_context`, no streaming/reconnection logic at this layer — that lives in the chat route.
- `apps/web/app/api/chat/route.ts`: workflow started with `start(runAgentWorkflow, [...])`, stream obtained via `run.getReadable<WebAgentUIMessageChunk>()`, active-stream reconciliation through `activeStreamId` with compare-and-set; duplicate workflows cancelled with `getRun(id).cancel()` + 409 on conflict.
- Open issues relevant to durability/long-running: #781 (persist large fetch bodies), #798 (per-tool timeouts), #800 (sandbox creation failures), #776 (Daytona backend support — indicates abstraction gap). No open issue explicitly about workflow-reconnect failure modes, suggesting that layer is relatively stable or underused.
- E2B by contrast: full FS+memory+process snapshot via Firecracker, ~4 s/GiB pause, ~1 s resume, 30-day retention. Real hibernate.
- Modal: FS snapshots only, same category as Vercel Sandbox.
- CRIU feasibility: workable for pure-Python, vanilla processes; fragile for GPU handles, open sockets, library-version drift. Not a reliable substrate for our REPL holding HTTP state to llama-server.
