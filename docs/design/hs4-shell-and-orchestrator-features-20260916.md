# HS-4 Follow-Through: Shell Choice and Where the Hermes Features Live (2026-09-16)

**Owner handoff:** [`handoffs/active/harness-selection-and-integration.md`](../../handoffs/active/harness-selection-and-integration.md) → HS-4
**Prepared by:** `sub-hs4-design`. Zero inference: nothing was run, built, installed or sent.
**Builds on:** [`hs4-harness-decision-package-20260916.md`](hs4-harness-decision-package-20260916.md) (the package) and [`progress/2026-09/2026-09-16-sub-hermes-memory.md`](../../progress/2026-09/2026-09-16-sub-hermes-memory.md) (the memory audit).

## 0. The operator decision (HS-4, 2026-09-16)

- Adopt a **thin off-the-shelf shell**.
- Build the Hermes features we want **inside the orchestrator**, not inside the shell: user-profile memory, delegation, background review and compaction.
- Keep **one memory system and one router**, with **no patches to carry**.
- The operator asked: *"or maybe we just integrate with OpenCode or oh-my-pi and custom-add Hermes features afterwards?"* This doc answers that question. It picks between OpenCode and oh-my-pi (with pi as the minimal fallback) and says where each feature lives.

**Short answer.**
- **Shell: OpenCode.** pi is the fallback. oh-my-pi is not chosen.
- **The features go in the orchestrator.** The shell reaches them through implicit `/v1` behaviour and a few MCP tools.
- **The shell carries only one first-party plugin.** It stamps session identity onto each request. It is written against a documented hook API, so it is not a patch.
- **A Phase 0 blocker exists that no earlier audit caught.** It is described in §1.1.

### Pins used

| Tree | Pin | Where |
|---|---|---|
| epyc-orchestrator | `83c7ed2f` (origin/main, 2026-09-16T15:07Z) | `/workspace/repos/epyc-orchestrator` |
| OpenCode | `4bffbb655` (2026-07-17, `packages/opencode` v1.18.3) | `/mnt/raid0/llm/tmp/hs1g-opencode` |
| oh-my-pi | `37eee7197` (2026-08-16, `coding-agent` v17.3.5) | `/mnt/raid0/llm/tmp/hs1g-ohmypi` |
| earendil-works/pi | `ceea48f5` (2026-09-14) | `/mnt/raid0/llm/tmp/hs1g-pi` |
| Hermes | `532a49f1` | `/mnt/raid0/llm/hermes-agent` |

These are the HS-1g clones. Orchestrator paths below are relative to the repo root. Shell paths are relative to each clone.

---

## 1. Shell choice: OpenCode vs oh-my-pi

### 1.1 First, a seam blocker that applies to every agentic shell

HS-1 and HS-1g audited the **request** direction: do our `x_*` keys reach the body? None of them audited the **response** direction. At `83c7ed2f`, `/v1/chat/completions` **never returns `tool_calls`**:

- Tool definitions supplied by the client are rewritten into prompt text telling the model to call them through the REPL as `CALL("tool_name", …)`. See `src/api/routes/openai_compat.py:228` (`_format_native_tools_for_repl`).
- The response is stamped `native_tool_contract="internal_repl_execution"` and `response_tool_calls="not_emitted"` (`:322-331`). This was a deliberate choice in `6c333cd7`, recorded in `tool-use-eval-contract.md` Phase 2.
- `CALL()` resolves names against the **orchestrator's** tool registry (`src/repl_environment/context.py:599`). A shell's `bash`, `read` or `edit` tool therefore cannot run: the orchestrator does not have it, and the shell never receives a call to execute.

**Consequence.** Every shell we are choosing between (OpenCode, oh-my-pi, pi, Hermes) runs its tools when the model returns `tool_calls`. Against today's `:8000`, any of them degrades to a chat window with no working tools. This does not separate the candidates. It is the **first Phase 0 item** (§4, P0.1).

The fix is additive: an opt-in **client-executed tool mode**.
- `/v1` forwards `tools`, `tool_choice` and the structured tool history to the backend's chat-completions path. That path already exists: `use_chat_completions` and `_infer_chat_completions` at `src/backends/llama_server.py:134,535`, which rely on llama-server `--jinja`.
- It returns `tool_calls` with `finish_reason:"tool_calls"`.
- The internal REPL bridge stays the default, so the eval tower's behaviour does not change.

This makes the orchestrator a **gateway that carries tool calls through**: the model decides, the shell executes, and the orchestrator routes and records. It is not a change to the cooperation contract in the operator's sense. It is the missing half of "OpenAI-compatible".

### 1.2 Evidence matrix

| Axis | OpenCode `4bffbb655` | oh-my-pi `37eee7197` |
|---|---|---|
| **Extension surface** (adding features later) | Typed `Hooks` interface (`packages/plugin/src/index.ts:222-335`): `tool` (register tools, `:226`), `chat.params` (`:247`, its input carries `sessionID`), `chat.headers`, `permission.ask` (`:261`), `tool.execute.before` (`:266`, can rewrite args and knows `sessionID`), `tool.execute.after`, `experimental.chat.system.transform` (`:291`), `experimental.chat.messages.transform`, `experimental.session.compacting`, `tool.definition`, `event`, `config`. Native SKILL.md skills: a `skill` tool (`packages/opencode/src/tool/skill.ts:12-28`) and a `skill` permission key (`packages/core/src/v1/config/permission.ts:33`). | Wider: the `pi.on(...)` event bus (`docs/extensions.md:224-275`) includes `before_provider_request` (can **replace** the payload), `tool_call`/`tool_result` middleware, and `session_stop` continuation. Custom tools, hooks, a plugin marketplace **with auto-update** (`src/extensibility/plugins/marketplace-auto-update.ts`), and skills. |
| **MCP** | Native client with stdio, streamable-HTTP and SSE transports (`packages/opencode/src/mcp/index.ts:7-9`), plus MCP prompts and resources (`mcp/catalog.ts:124,132`). | Native client with stdio, HTTP and SSE transports (`docs/mcp-protocol-transports.md:22-24`). MCP tools are given approval tier `write` (`docs/approval-mode.md`). |
| **How our request parameters flow** (HS-1g) | **All default egress paths honour them.** Main loop, compaction and `task` children use `streamText`, and the keys land at the **top level** of the body. **Per-turn dynamic keys are native:** `chat.params` receives `sessionID`, so `x_session_id` costs one line. **Traps:** models.dev-mode camelCasing; the `agent create`/`generateObject` and title (`smallOptions`) side calls. | **All default egress paths honour them** through `compat.extraBody`. However, `extraBody` is **static per model**, so per-session keys need a `before_provider_request` extension that rewrites the payload. **Traps:** `providerOptions`; v2 remote compaction. |
| **Competing router** | **None exists.** Each agent has a static model. The session layer has no model-fallback code: a grep for model fallback in `session/` and `provider/provider.ts` finds nothing, and `session/retry.ts:26-28` is same-model backoff. | Yes: `retry.fallbackChains` plus 10 model roles (`src/config/model-roles.ts:55-66`: default, smol, slow, vision, plan, designer, commit, tiny, task, advisor). **It can be fully disabled; see §1.3.** |
| **Permission / sandbox** | `ask\|allow\|deny` per tool with patterns (`core/src/v1/config/permission.ts:5-35`). An unmatched rule falls back to **`ask`** (`opencode/src/permission/index.ts:28-37`), and `opencode run` auto-rejects asks. Bash arguments are not path-gated, so the layer is porous but real (`intake-1353#02`). No sandbox. | Tiers `read`/`write`/`exec`, plus per-tool `allow\|prompt\|deny` and critical-pattern overrides for bash (`docs/approval-mode.md`). **The default mode is `yolo`, which auto-approves exec** (`src/config/settings-schema.ts:3678-3681`); it must be set to `always-ask`/`write`. No sandbox. |
| **Own autonomy surface to switch off** | `compaction.auto`/`prune` (`core/src/v1/config/config.ts:149-159`), `share` (`:57`), `autoupdate` (`:64`), `small_model` (`:77`), `OPENCODE_DISABLE_{AUTOCOMPACT,PRUNE,AUTOUPDATE,MODELS_FETCH,SHARE,CLAUDE_CODE*,EXTERNAL_SKILLS}`, `permission.task`. | Most of it is **off by default**: `advisor.enabled` (`:450`), `memories.enabled` (`:2582`), `memory.backend="off"` (`:2620`), `autolearn.enabled` (`:2645`). `compaction.enabled` is **on** (`:2145`). Beyond these switches there is a very large code surface (`advisor/ autolearn/ autoresearch/ goals/ hindsight/ mnemopi/ memory-backend/ …`) that must be re-audited on every bump. |
| **Upstream maintenance risk** | Activity from 2026-04-17 to the pin: 3,561 commits by 153 authors. The top non-bot author has 679. Broad maintainer base. The pin is **two months old**, so a re-audit at the current tip is a P0 step. | Activity from 2026-05-16 to the pin: 12,789 commits by 313 authors, but **one maintainer wrote 6,401 and his bot `roboomp` wrote 2,924 (about 73%)**. Bus factor about 1, with extreme churn. It is a detached fork of pi at about 0.50, renumbered to 17.x (`intake-1360#record`). The advertised install is `curl \| sh` (`intake-1149#record`). |
| **Licence** | MIT (`LICENSE`). | MIT (`LICENSE`). |
| **Headless / eval fan-out** | `run --format json`. | NDJSON RPC and a Node SDK. |
| **Trainability (not a selection criterion; HS-5b)** | First-party `opencode_env` exists. Its training half cannot run on this host. | None. |

pi (`ceea48f5`), the fallback, was scored by HS-1f and the package. It has the strongest orthogonality, no core MCP, no permission layer, and needs an extension for MCP. It also exposes `before_provider_request`, so it could carry the same session-stamping extension.

### 1.3 Can oh-my-pi's `retry.fallbackChains` router be fully disabled? Yes, by configuration.

- **Master switch: `retry.modelFallback: false`** (`settings-schema.ts:1531`, default `true`).
  - The recovery path returns before it picks any fallback: `session/turn-recovery.ts:1397`.
  - Start-up selection checks the same switch: `sdk.ts:2170` and `sdk.ts:2253-2257`.
  - oh-my-pi's own security scan disables routing the same way: `security/coordinator.ts:229-231` overrides `retry.modelFallback=false` and `retry.fallbackChains={}`.
- **Other settings to set:**
  - `retry.fallbackChains: {}`. This is already the default (`:1600-1602`).
  - `retry.usageAwareFallback: false`. Also the default (`:1541`).
  - All 10 `modelRoles` point at the single orchestrator model.
  - Use single-selector model patterns only. A comma-separated `--model a,b` pattern **auto-installs** a chain (`sdk.ts:2340-2374`), and so do multi-candidate sub-agents (`task/executor.ts:236-276`). The master switch still stops those chains from being used.
- **Residual risk.** A single boolean guards a fast-moving recovery path. Any new fallback path added upstream is not covered until someone re-audits. So a "no competing router" check would have to join the HS-1g call-verb check on every oh-my-pi bump. OpenCode has no such router, so it needs no such check.

### 1.4 Recommendation: OpenCode, with pi as the fallback

Given the operator's constraints (thin shell, features in the orchestrator, one router, no patches):

1. **One router.** OpenCode has **no router at all**. oh-my-pi has one that is switched off by a boolean that must be re-audited on every bump. A router that does not exist is better than one that is disabled.
2. **Per-session identity is native in OpenCode.** Features that live in the orchestrator need `x_session_id` and `x_user_id` on every request. OpenCode's `chat.params` hands the plugin `sessionID`, and `tool.execute.before` can stamp the same id onto MCP tool arguments. oh-my-pi needs a payload-rewriting extension for the same result.
3. **Safer defaults.** OpenCode falls back to `ask`. oh-my-pi defaults to `yolo`. Neither replaces the container (package §4), but defence in depth should not start from auto-approve.
4. **Upstream risk.** OpenCode has a broad maintainer base. oh-my-pi's bus factor is about 1, with the highest churn of any candidate.
5. **Features added "afterwards" go in the orchestrator (§2).** So oh-my-pi's richer extension bus, its only real advantage, buys nothing we plan to use.

**What would flip the recommendation:**
- **To pi:**
  - if the operator drops native MCP tool consumption as a requirement (the package's tie-break); or
  - if the OpenCode re-audit at its current tip (P0.3) finds a default egress path that no longer honours the lever. Examples: the native-runtime gate (`session/llm/native-runtime.ts`) is widened to custom providers, or `chat.params` keys stop landing at the top level.
- **To oh-my-pi:**
  - if a feature ever *must* live in the shell and needs payload replacement or a stop-hook continuation that OpenCode lacks. The design below has no such feature;
  - or if OpenCode relicenses, or breaks the `chat.params` / `tool.execute.before` hook API without a replacement.
- **Not a flip:** external benchmark rankings (OBSERVATION grade, package §5).

**The shell choice is therefore settled: OpenCode.** No operator sub-choice remains. The `task` tool is **denied**, because delegation lives in the orchestrator (§3.5).

---

## 2. "Add Hermes features afterwards": added where?

**(i) In the shell**, as OpenCode plugins. **(ii) In the orchestrator**, exposed as implicit `/v1` behaviour or as MCP tools.

| Criterion | (i) Shell plugins | (ii) Orchestrator |
|---|---|---|
| **Routing compliance.** Does every model call go through our router? | Only if each plugin's own LLM calls hit `:8000` with the right `x_*` keys. This is the HS-1g silent-no-op class, repeated for every plugin we write. Hermes shows what happens: memory flush, background review and `session_search` all bypassed overrides (memory audit §3). | **By construction.** Summarisation, review and delegation calls go through `LLMPrimitives`, the same seam the router, admission control and the inference tap already cover. |
| **Measurability** (M-12, belief kernel) | State lives in the client's data directory, which autopilot and the belief kernel cannot see. Every measured run has to fence it off separately for each shell (memory audit §3, "Fence"). | Write-side hooks sit next to the stores M-12 already measures. The Tulving and BEAM adapters are live (`scripts/vidya/adapters/README.md`, rows `tulving_episodic` and BEAM). Arm identity becomes a typed request key (`x_memory`), not a per-shell config audit. |
| **Shell independence** (HS-7) | None. A shell swap throws the work away. | Complete. Any client that sends `x_session_id` gets the features. |
| **Effort** | TypeScript in a foreign runtime, tracking `experimental.*` hook churn. | Python in our own repo. Most of the mechanisms already exist (§3). The cost is `/v1` wiring plus the session-key contract. |

**Verdict: (ii) for every feature.** (i) is used only for things that are configuration rather than code:
- the one session-stamping plugin;
- the shell's native reading of `AGENTS.md` and `SKILL.md` files (§3.2, §3.7).

This meets "no patches to carry": a plugin written against a documented hook is an integration, not a fork.

**Precedence rule, applied to every feature.** A typed `x_*` field always beats memory prose. Profile and notes text is injected as prompt content, and **routing never reads it**.

---

## 3. Feature map

**New typed `/v1` body keys (P0.2).** The seam refuses unknown values rather than dropping them, following the HS-OD-1 pattern.

| Key | Values | Purpose |
|---|---|---|
| `x_session_id` | string | Session identity for every per-session feature |
| `x_user_id` | string, default `"default"` | User identity for profile and notes |
| `x_memory` | `"on"` \| `"off"`, default `"off"` until P2 lands | `off` is the no-memory control arm |
| `x_tool_mode` | `"internal"` (default) \| `"client"` | Selects the client-executed tool mode (§1.1) |

MCP tools are added to `src/mcp_server.py` (FastMCP, stdio). The plugin's `tool.execute.before` hook stamps `session_id` onto their arguments.

### 3.1 User-profile memory (Hermes USER.md / Honcho)

- **Home:** `src/user_modeling/` (B1, cherry-picked 2026-04-05).
- **What exists today:**
  - `ProfileStore`: SQLite, `§`-separated entries, 4 KB cap (`profile_store.py:31`), injection scan on write (`:121-132`).
  - Four REPL tools: `user_profile`, `user_search`, `user_context`, `user_conclude` (`orchestration/tool_registry.yaml:950-1006`).
  - Frozen-snapshot injection in `PromptBuilder.get_system_prompt` (`src/prompt_builders/builder.py:640-647`).
  - Feature flag `user_modeling` is off in both test and prod (`src/features.py:186`).
- **The gap:**
  - **The injection is dead code.** `get_system_prompt()` has **no serving caller**. Its only callers are `scripts/analysis/token_audit.py:255` and a character count at `scripts/autopilot/eval_tower.py:5985`. Turning the flag on would inject nothing.
  - So the work is:
    1. inject the snapshot on `/v1`, once per `x_session_id`, frozen at session start so the prefix cache is preserved;
    2. key the profile on `x_user_id`;
    3. honour `x_memory=off`;
    4. add a `remove` operation (Hermes has add, replace and remove; B1 has only add).
- **Interface:** implicit (system-prompt injection). Plus MCP tools `memory_profile_get()`, `memory_profile_write(op: add|replace|remove, text, category)` and `memory_profile_search(query)`.
- **Effort:** S–M.
- **Dependencies:** P0.2 keys; `injection_scanning` (on in prod, `features.py:184`).
- **How it is measured:**
  - BEAM `preference_following` and `instruction_following` columns, with profile on vs `x_memory=off`;
  - the no-memory control arm (UTM-M9 intent);
  - a write-precision audit per UTM-V3.

### 3.2 MEMORY.md-style agent notes

- **Home:** the same `ProfileStore`, with a second bounded scope (`scope="notes"`).
- **What exists today:** only the user scope.
- **The gap:** add the scope and inject it together with the profile.
- **Do not rebuild project facts.** Facts about a repository belong in `AGENTS.md`. OpenCode already loads it (`packages/opencode/src/session/instruction.ts:61-65`), it is versioned with the code, and it is the HS-7/HS-8 policy-document surface. The server scope is only for facts that span projects or describe the host environment.
- **Interface:** implicit injection, plus MCP `memory_notes_write(op, text)`.
- **Effort:** S.
- **Dependencies:** §3.1.
- **How it is measured:** the same arms as §3.1. Notes and profile each get their own on/off leg only if the §3.1 A/B shows an effect.

### 3.3 `session_search` (Hermes: FTS5 over transcripts plus an LLM summary)

- **Home:** `src/trace/` ([`unified-trace-memory-service.md`](../../handoffs/active/unified-trace-memory-service.md): UTM-B1, UTM-P1; T7 is generalised here).
- **What exists today:**
  - `src/trace/navigation.py`: `search_records`, `search_conversation`, `get_records`, `get_conversation`, and RRF k=60 (`:36-178`). Read-only, with one CLI consumer and no MCP registration (UTM-B1).
  - The session store's text search is a plain `LIKE` (`src/session/sqlite_store.py:847-853`).
  - `EventSource.HERMES_SESSION` is a dead constant (`src/trace/store.py:36`).
- **The gap:**
  - **Write side:** `/v1` records each turn as an event, `source=v1_session`, carrying `x_session_id`, a turn ordinal and the harness identity (UTM-P1). The orchestrator sees every turn, so it **never needs to read the shell's database**. T7 becomes unnecessary, which removes the lineage problem that compaction re-keying causes (memory audit §3, conflict 4).
  - **Read side:** register `ms.search` and `ms.expand` as MCP tools (UTM-B1).
  - Return **ranked snippets** by default. **Do not rebuild Hermes's per-search LLM summary.** It is an extra, unrouted-by-default inference cost, and a snippet list serves the calling model directly.
  - **Partitioning:** eval arms exclude `source=v1_session` by construction.
- **Interface:** MCP `memory_session_search(query, limit)` and `memory_session_get(event_ids)`.
- **Effort:** M.
- **Dependencies:** P0.2 and UTM-P1.
- **How it is measured:** the M-12b BEAM `trace` arm and the UTM-B4 Tulving `retrieved` arm use **the same surface**, which is what keeps this one memory system. Note that the BEAM/Tulving arms build private stores (`beam_memory_retrievers.py:151-156`), so production data never reaches them.

### 3.4 Background review and nudges (Hermes: a forked agent every 10 turns)

- **Home:** `src/user_modeling/deriver.py`, plus the admission controller's background class.
- **What exists today:** `derive_preferences()` (`deriver.py:87`) extracts `PREF [category]` lines and persists them through `ProfileStore`. **It has no caller outside its tests.**
- **The gap:**
  - A trigger runs it at session idle or end (never mid-turn), and every N turns, keyed by `x_session_id`.
  - It reads the §3.3 transcript.
  - It runs as a **background-priority** request through `LLMPrimitives`, so it is routed, admitted and tapped.
  - Its writes are **proposals**: scanned for injection and structurally verified (UTM-V2/V3), never authoritative.
  - It is suppressed when `x_memory=off`, and suppressed during a region claim or measured run (idle-compute rules).
- **Do not rebuild autonomous skill creation** (Hermes's skill nudge). See §3.7.
- **Interface:** implicit. The shell does nothing. An MCP tool `memory_review_pending()` lets the user inspect and approve proposals.
- **Effort:** M.
- **Dependencies:** §3.1, §3.3, and the admission background class.
- **How it is measured:**
  - BEAM `preference_following` with derived-profile vs no-memory arms;
  - proposal precision and recall on a labelled transcript set (UTM-V3);
  - background prefill tokens per session, the hidden cost the memory audit flagged.

### 3.5 Delegation and sub-agents (Hermes `delegate_task`)

- **Home:** `src/proactive_delegation/`, `src/api/routes/delegate.py` (`POST /api/delegate`, TaskIR), `chat_delegation*.py`, and `architect_delegation` / `parallel_execution` (on in prod, `features.py:118-119`).
- **What exists today:**
  - All of it runs on the native `/chat` pipeline.
  - On `/v1`, the role comes from the model name or `x_*` only (`openai_compat.py:517-523`), and `x_max_escalation` is **metadata only** (`:528`). `/v1` has no escalation or delegation. The shared retriever and router now reach the `/v1` REPL (`:53-70`, `83c7ed2f`), but only for `recall()`, not for routing decisions.
- **The gap:**
  1. **Routing parity.** When `model="orchestrator"`, `/v1` requests take the same routing decision as `/chat`. This is what "one router" means in practice. Today `/v1` uses a fixed front door.
  2. An MCP tool `orchestrator_delegate(objective, steps?)` wraps `/api/delegate`. Delegated workers return **text and artifacts only**. Workspace writes stay with the shell's own tools, inside the shell's jail, so the orchestrator REPL sandbox gap (HS-6c fields 1–2) is not extended to the user's workspace.
  3. The shell's `task` tool is **denied** (`permission.task: deny`).
- **Interface:** implicit (routing and escalation on `/v1`), plus MCP `orchestrator_delegate`. The existing `orchestrator_chat` (gated by `claude_code_mcp_chat`) is the precedent.
- **Effort:** M for the MCP tool; M–L for routing parity.
- **Dependencies:** P0.1 (client tool mode must stay off the delegated path), P0.2.
- **How it is measured:** `src/delegation_reports.py` telemetry; routing decisions in the trace; the delegation rows in the eval tower. Routing compliance holds by construction, because child calls never leave the orchestrator.

### 3.6 Compaction (Hermes context compressor)

- **Home:** `src/context_compression.py` (B2), `src/graph/compaction.py` with the session log (`/chat`), [`context-folding-progressive.md`](../../handoffs/active/context-folding-progressive.md) (CF-3c, CF-PB-1), and [`tool-output-compression.md`](../../handoffs/active/tool-output-compression.md).
- **What exists today:**
  - B2 is already wired on `/v1` (`openai_compat.py:488-505`), but the flag is **off** (`features.py:185`).
  - It is **stateless per request**, so it re-folds every turn and changes the prefix every turn, which defeats the prefix cache.
  - Its failure branch silently falls back to the unfolded history (`:505`): a fail-open.
- **The gap:**
  - A **fold cache keyed by session**. Fold only at a plan or threshold boundary, priced by CF-PB-1 break-even. Re-send the byte-identical folded prefix until the next boundary.
  - The fold's summary call goes through `LLMPrimitives`.
  - A fold failure is logged and counted, never silent.
  - `usage` must report the tokens actually sent.
- **Shell side:** `compaction.auto:false` and `compaction.prune:false`, with `limit.context` set to the orchestrator's advertised window. With auto off, OpenCode never folds (`session/overflow.ts:28`) and only surfaces a `ContextOverflowError` (`session/message-v2.ts:682`). Server-side folding is therefore **required** for long sessions, which is why it is phase 1.
- **Interface:** implicit.
- **Effort:** M.
- **Dependencies:** P0.2, and CF-3c's persisted monitor.
- **How it is measured:**
  - CF-3c quality monitor, with the mandatory masking/truncation anchor;
  - Tulving and BEAM long-context arms, folded vs full;
  - prefill tokens per solved task and prefix-cache hit share (the HS-14 bake-off columns);
  - a byte-identity check on the prefix.

### 3.7 Skills (Hermes SKILL.md, the agentskills.io hub, `skill_manager`)

- **Home:** the shell's native loader for *consuming* skills. `src/skill_hub_interop.py` (B3) for *exporting* them.
- **What exists today:**
  - OpenCode loads SKILL.md folders through its `skill` tool, controlled by the `skill` permission.
  - The orchestrator has SkillBank (off in prod, `features.py:124`) and B3, which parses and exports SKILL.md but **has no callers**.
  - Re-distillation M-11a is gated on inference.
- **The gap:** none for P0. Point OpenCode's `skills.paths` at a versioned in-repo folder.
  - Optional, and gated on M-11a/M-12 evidence: export distilled skills to that folder through B3, as a **reviewed commit**.
- **Do not rebuild:**
  - **skill loading in the orchestrator.** Skills are policy documents, and the NLAH/HS-7 principle keeps them as editable documents that the harness reads.
  - **autonomous skill creation.** A model that silently edits its own policy documents breaks HS-7 re-targetability, and it breaks the HS-5b freeze-before-tuning ordering (`intake-1323#record`, `intake-1339#record`).
- **Interface:** configuration only.
- **Effort:** S (configuration); M (gated export).
- **Dependencies:** M-11a and M-12 for the export.
- **How it is measured:** each skill folder version is recorded in the Harness Card (HS-7). The export is admitted only after a SkillBank A/B.

### 3.8 Hermes features explicitly *not* rebuilt

| Feature | Why not |
|---|---|
| Honcho (cloud user modelling) | B1 covers it locally, under the open-source/local policy. |
| Session re-keying on compaction (`parent_session_id`) | Server-side folding keeps one session id, so the lineage problem disappears. |
| LLM summary on every `session_search` | Hidden inference; ranked snippets are enough (§3.3). |
| Autonomous skill creation | HS-7 and HS-5b (§3.7). |
| Iteration-limit summary | A Hermes-specific loop artefact. OpenCode has none. |
| Multi-platform gateway (Telegram, Slack, …) | **Not dismissed.** The operator did not ask for it, and it belongs to the shell layer. Flagged for operator interest; no work filed. |

---

## 4. Phased plan

**Legend.**
- **Inf:** whether the step needs inference.
- **GPU-only?:** whether the inference can be run entirely on the MI210 lane, under a region claim.
- Code steps are acceptance-tested by unit tests with fake backends, with zero inference.

### Phase 0: shell integration with no Hermes features

| Step | What | Acceptance test | Inf | GPU-only? |
|---|---|---|---|---|
| P0.1 | `/v1` client-executed tool mode (`x_tool_mode="client"`). Forward `tools`, `tool_choice` and structured tool history to the backend chat-completions path, and return `tool_calls` with `finish_reason:"tool_calls"`. The REPL bridge stays the default. | Unit (fake backend): (a) a tool call comes back as `message.tool_calls`; (b) default mode is byte-identical to today; (c) a `tool` result message round-trips with its id. **Live:** OpenCode completes a read → edit → bash loop on a scratch repo. | code: no; live: yes | Yes, if the acceptance role is served on the GPU with a tool-capable `--jinja` template |
| P0.2 | Typed keys `x_session_id`, `x_user_id`, `x_memory`, `x_tool_mode`. Unknown values are refused. The keys are echoed into metadata and the trace. | Unit: a bad value returns 422; valid keys appear in `x_orchestrator_metadata`. | no | — |
| P0.3 | Re-clone OpenCode at its current tip. Re-run the HS-1g call-verb check and a "no model-fallback" grep (procedure: [`client-surface-audit.md`](../reference/harness-candidates/client-surface-audit.md) §2 Steps 1–4), then pin. Write the `epyc-orchestrator` plugin: `chat.params` sets `x_session_id`, `x_user_id`, `x_tool_mode="client"` and the static `x_*`; `tool.execute.before` stamps `session_id` onto `orchestrator_*`/`memory_*` MCP arguments. Config (custom-provider mode): `baseURL`; `compaction.auto:false`; `prune:false`; `share:"disabled"`; `autoupdate:false`; `small_model` set to the orchestrator model; `permission.task:"deny"`; the `OPENCODE_DISABLE_{MODELS_FETCH,AUTOUPDATE,SHARE,CLAUDE_CODE,EXTERNAL_SKILLS}` flags; `skills.paths` pointing at the in-repo folder. Container or worktree jail. | Source audit recorded in HS-1g form. Config lint (all required keys present). | no | — |
| P0.4 | Live acceptance and freeze: one request confirming that `x_*` keys arrive at the top level (the HS-1c residual); title and side calls carry the keys or are disabled; no compaction events. Republish the Harness Card for this configuration (HS-7). Freeze the pin (HS-5b). | Request capture shows the keys at the body's top level. The P0.1 live loop passes. The card is published. | yes | Yes |
| P0.5 | Belief-kernel wiring **before any measured shell run**. Draft below. | Row and task added; the writer emits one sidecar per run. | no | — |

**P0.5 wiring draft**, to be applied by the owning session (CLAUDE.md "Belief Kernel"):
- **Source-table row:** `| OpenCode-shell runs through /v1 (HS-4 P0.4 acceptance, HS-14 bake-off) | measurement | **prospective — write-side hook required before the first measured shell run** | (to author) |`
- **Program task:** `SC86 — wire HS-4 shell runs on the WRITE side: each run emits a ClaimTuple carrying the harness pin, plugin and config hash, Harness Card version, x_memory arm, and the HS-14 column set; locator = run.`

### Phases 1–5: features in value order

| Phase | Feature (§) | Acceptance test | Inf | GPU-only? |
|---|---|---|---|---|
| **P1** | Server-side compaction with a session fold cache (§3.6). Value: long sessions **fail** without it once shell compaction is off. | Unit: a synthetic 200-turn session stays under the window; the folded prefix is byte-identical between boundaries; a fold failure is counted and never silent. **Quality:** CF-3c with the masking anchor; Tulving/BEAM folded vs full arms. | mechanism: no; quality: yes | Yes (the M-12 B5 GPU recipe exists) |
| **P2** | User profile plus notes (§3.1, §3.2): injection on `/v1`, MCP write/search tools, `x_memory`. | Unit: the snapshot is injected once per session and frozen; `x_memory=off` injects nothing; `remove` works; the injection scan rejects bad writes; a typed `x_*` overrides profile prose. **Efficacy:** BEAM `preference_following`, on vs off. | unit: no; efficacy: yes | Yes |
| **P3** | `session_search` (§3.3): `/v1` transcript write-side, UTM-P1 keys, MCP `ms.search`/`ms.expand`. | Unit: one event per turn with session, turn and harness keys; eval arms exclude `v1_session`; search returns ranked snippets without an LLM call. **Efficacy:** M-12b `trace` arm, UTM-B4. | unit: no; efficacy: yes | Yes |
| **P4** | Delegation and one router (§3.5): MCP `orchestrator_delegate`; `/v1` routing parity when `model="orchestrator"`. | Unit: the delegate tool goes through `/api/delegate`; delegated workers get no workspace-write tools; `/v1` and `/chat` take the same routing decision for the same input (fixture). **Live:** an escalation case routes correctly from OpenCode. | unit: no; live: yes | Partly. Routing parity touches roles served on CPU, so it needs a CPU+GPU region claim. |
| **P5** | Background review (§3.4): session-idle trigger, background priority, proposal-only writes. | Unit: no trigger during a region claim or with `x_memory=off`; proposals need approval; the call goes through `LLMPrimitives` at background priority. **Efficacy:** proposal precision/recall on labelled transcripts; BEAM derived-profile arm. | unit: no; efficacy: yes | Yes |
| (gated) | Skill export through B3 (§3.7). | Only after M-11a/M-12: a SkillBank A/B clears its gate, and each export is a reviewed commit. | yes | — |

**After P0 (post-freeze, HS-5b):** the local HS-14 bake-off, with the columns from package §5. Needs inference and a region claim.

---

## 5. Recording and index drafts

- **Recorded:** the operator decision and a pointer to this doc are added to the HS-4 box in `harness-selection-and-integration.md`, and its Status line is updated. The HS-4 checkbox itself is left for the owning session to tick when it applies the index change below.
- **Drafted, not applied.** The owning session applies these, per ruling (b).

**`master-handoff-index.md`: delete the `OP-HS4` row.** The shell choice is settled (OpenCode), and no operator sub-choice remains (`task` is denied by design; pi is a fallback, not an open choice).
```
- | OP-HS4 | Harness selection: A OpenCode (recommended) / B pi / C omp / D Hermes / E dsh / F defer; tie-break = native MCP tool consumption; decidable without HS-1f.1 | [harness-selection-and-integration.md](harness-selection-and-integration.md) HS-4; [package](../../docs/design/hs4-harness-decision-package-20260916.md) | 2026-09-16 |
```

**`user-facing-harness-index.md`: new UFH-01 next action.**
```
| UFH-01 | harness selection and integration | [harness-selection-and-integration.md](harness-selection-and-integration.md) | HS-4 P0.1: /v1 client tool_calls mode + x_session_id keys, then pin OpenCode at a re-audited tip (see hs4-shell doc §4) | — |
```

**Optional, same index: UFH-02 narrowed.** Hermes is no longer a shell candidate. *(2026-09-16, `sub-close-ufh02`: the handoff is now closed and moved to [`handoffs/completed/hermes-outer-shell.md`](../../handoffs/completed/hermes-outer-shell.md), with findings in [`hermes-evaluation-20260916.md`](../reference/harness-candidates/hermes-evaluation-20260916.md). The owning session deletes the UFH-02 row instead of narrowing it.)*
```
| UFH-02 | hermes outer shell | [hermes-outer-shell.md](hermes-outer-shell.md) | Close out: Hermes not selected (HS-4 2026-09-16); keep its feature notes as reference, move to completed/ | — |
```
