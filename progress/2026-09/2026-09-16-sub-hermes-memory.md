# Hermes memory vs orchestrator episodic memory — HS-4 input (sub-hermes-memory, 2026-09-16)

**Operator question:** will Hermes' memory and delegation features compete with, or interfere with, the orchestrator's episodic memory? Or are the two complementary?

**Method:** zero inference, source only. Nothing was run, built or installed.

**Pins:**

| Tree | Pin |
|---|---|
| Hermes | `/mnt/raid0/llm/hermes-agent` @ `532a49f1` (`v2026.3.23-44`), the pin audited by HS-1b/HS-1g |
| Orchestrator | `0329ab10` |
| Research | `origin/main` |
| Root docs | read from `origin/main` |

**Inputs:**
- `docs/design/hs4-harness-decision-package-20260916.md`
- `handoffs/active/hermes-outer-shell.md`
- `handoffs/active/unified-trace-memory-service.md`
- `handoffs/active/episodic-memory-integrity.md`
- `handoffs/active/context-folding-progressive.md`
- `handoffs/active/conversational-memory-eval-instrument.md`

## 1. What Hermes remembers (at `532a49f1`)

| Store | Where | Written when | Read back when / how | Can it be disabled or redirected? |
|---|---|---|---|---|
| **MEMORY.md** (agent notes) and **USER.md** (user profile) | `$HERMES_HOME/memories/` flat files, entries separated by `§` (`tools/memory_tool.py:39-41`). Size caps are 2200 and 1375 chars (`:100`). | By the `memory` tool (add/replace/remove, `:185-320`). Writes reach disk immediately. | Injected into the **system prompt** as a snapshot frozen at session start (`memory_tool.py:11-14`, `:108-123`, `:322-334`; `run_agent.py:2341-2350`). Mid-session writes show up only in tool results. | `memory.memory_enabled` / `memory.user_profile_enabled` (`run_agent.py:911-926`). Hermes defaults both to **true** (`hermes_cli/config.py:304-309`), and so does our config (`scripts/hermes/hermes-config.yaml:82-88`). Dropping `memory` from `platform_toolsets` removes the tool. |
| **Memory nudge / background review** | Same files; skill writes go to `$HERMES_HOME/skills/` (`tools/skill_manager_tool.py:79-80`). | Every `nudge_interval` user turns (default 10, `run_agent.py:5494-5500`), and after skill-heavy turns (`:7171-7189`). A **forked `AIAgent`** re-reads the whole conversation and writes memory and skills (`:1383-1428`). | Next session start. | `nudge_interval: 0`, `skills.creation_nudge_interval: 0`. |
| **`flush_memories`** | Same files. | Before every compression, session reset or CLI exit, once the session has at least `flush_min_turns` (6) user turns (`run_agent.py:4424-4448`). Before compression it always runs (`:4594`, `min_turns=0`). It makes one extra LLM call through the auxiliary client (`:4500-4501`). | Next session start. | Off automatically when memory is disabled (`:4440-4441`). |
| **Session DB** (full transcripts) | SQLite `$HERMES_HOME/state.db` with FTS5 (`hermes_state.py:1-27`, `:66-100`). | Every turn (`run_agent.py:1509-1540`). Compression **splits** the session into a new id with `parent_session_id` (`:4606-4628`). | Only through the `session_search` tool. That tool runs an FTS match, then an **LLM summarisation call** through the auxiliary client (`tools/session_search_tool.py:1-16`, `:156-157`). | Drop `session_search` from the toolsets. Our config enables it (`hermes-config.yaml:77`). |
| **Honcho** (cloud or self-hosted user modelling) | Remote service (`honcho_integration/client.py:91-99`; `base_url` is overridable, `:92-93`, `:144`). | Per turn. | Recall is appended to the current user message at API-call time and never persisted (`run_agent.py:328-340`, `:5682`). The `honcho_*` tools are also exposed. | Inactive unless it is enabled **and** has an API key (`run_agent.py:2015-2019`). It is inactive for us, and the tools are stripped (`:978-981`). A `honcho` peer mode turns off the local MEMORY/USER writes (`:982-996`). |
| **Compaction** | In-context only. | Above a threshold (0.50 of the window). A structured, iterative summary replaces the middle turns (`agent/context_compressor.py:1-36`, `:546`), after `flush_memories`. | Summary message is marked `[CONTEXT COMPACTION]`. | `compression.enabled`. Our config sets it **true** (`hermes-config.yaml:44-45`), against the HS-1b recommendation. |
| **Delegation** | None of its own. | Not applicable. | Children run with `skip_memory=True` and `skip_context_files=True`, and are **blocked from the `memory` tool** (`tools/delegate_tool.py:29-36`, `:224-225`). They share the parent's `session_db` (`:227`) and inherit the parent's `base_url` (`:201-209`). | Gate `delegate_task` out of the toolsets. |

**Plugin/provider API at the pin.** The only hooks are `pre/post_tool_call`, `pre/post_llm_call` and `on_session_start/end` (`hermes_cli/plugins.py:59-66`), plus `register_tool` and `register_command` (`:124`, `:174`). There is **no memory-provider interface**: the MemoryStore and Honcho are hard-wired into `_build_system_prompt` and `__init__`, and a grep for `MemoryProvider` / `memory_provider` returns nothing. The only built-in external backend is Honcho (`base_url` overridable). The newer upstream (v2026.4.23+) has a larger plugin surface (`research/deep-dives/hermes-agent-v2026-4-23-release.md:69-77`). Whether it has a memory-provider abstraction is **not verified**: no newer upstream tree is present locally.

**An inert config block (defect).** `hermes-config.yaml:115-120` declares `mempalace: enabled: true`. Hermes at this pin never reads a `mempalace` key (a grep finds nothing; MCP servers come only from `mcp_servers:`, `tools/mcp_tool.py:9-15`). The "H-8 MemPalace memory" is therefore not wired, even though the config comment claims it is. This is harmless today, but the claim is false.

## 2. What the orchestrator remembers

| Store | Where | Who writes | How it is read | On the `/v1/chat/completions` path? |
|---|---|---|---|---|
| **Episodic store** (SQLite + FAISS; "Episodic FAISS 61,286 vectors" is reported by `scripts/server/stack_commands.py:1135-1140`) | `orchestration/repl_memory/sessions/` (`episodic_store.py:46`) | MemRL / `q_scorer` (`q_scorer.py:1695`, `:1890`, `:2056`), strategy store, distiller, seed loader, replay | **Routing decisions**, not prompt content. Rows are `(task embedding, action = routing/escalation/exploration, outcome, q_value)` (`episodic_store.py:154-178`). Read by `HybridRouter` / `TwoPhaseRetriever` (`retriever.py:252`, `:723`; `chat.py:447`), by the REPL `recall()` tool (`src/repl_environment/routing.py:62-83`), and by the stuck-guidance note (`context.py:266-272`). | **No.** `openai_compat.py` has zero references to `hybrid_router`, `progress_logger`, `retriever`, `episodic`, `memrl` or `skill_context`. The REPL it builds is created **without** a retriever (`openai_compat.py:675-681`). |
| **SkillBank** (prompt-injected skills) | FAISS | Distillation pipeline | Prepended to the prompt (`direct_stage.py:95-96`; `routing_decision.py:212-216`) | No. It is `/chat`-only, and `skillbank` is off in production (`features.py:124`). |
| **Unified trace store** | `data/trace/events.sqlite`, FTS5 (`src/trace/store.py:25`) | Ingesters for agent_audit, progress and autopilot, plus live pushes (`store.py:30-45`) | CLI and navigation are **read-only** (`navigation.py:1-7`). `select_budgeted_records` is pure, default-off and has **no callers** (`navigation.py:215-244`; UTM-M7/M8). | No. `EventSource.HERMES_SESSION` (`store.py:36`) has no ingester (UTM T7 is deferred; UTM-P1 is open). |
| **Context folding** | In-request | Not applicable | `/v1` flattens the client's history into `context` (`openai_compat.py:467-497`). B2 `context_compression` is off in production (`features.py:185`). Progressive folding (`src/graph/session_log.py`) is on the graph/`/chat` path. | Only B2 (off). |

**Key structural fact.** The orchestrator's `/v1` endpoint is **stateless per request**. It neither reads nor writes episodic or trace memory for that traffic. Its memory is about *which model/role/strategy works*. It is written by the autopilot, eval and `/chat` pipelines, and it is consumed by routing.

**A latent defect found on the `/v1` path.** Because `/v1` passes no retriever, `recall()` falls through to `_recall_legacy`. That function calls `EpisodicStore().search_similar(...)` (`src/repl_environment/routing.py:161-169`), but **no `search_similar` method exists** on any `repl_memory` class. The call raises, and the exception is swallowed into `{"results": [], "error": ...}` (`:200-204`). As a result, `recall()` is silently dead for every `/v1` client, including Hermes. It also constructs a fresh `TaskEmbedder` on each call. The fix belongs to the orchestrator owner: pass `state.hybrid_router.retriever` into the `/v1` REPL, or delete the legacy branch. I did not change it, because my scope was commit-nothing.

## 3. Interaction analysis: Hermes → `:8000/v1`

### Orthogonal (the bulk)
- **Different subjects.** Hermes stores facts about the user, the environment and conversations. The orchestrator stores routing and strategy Q-values. The "two-layer" design in `hermes-outer-shell.md:46-60` holds at source.
- **No shared storage.** Hermes writes under `$HERMES_HOME` (`~/.hermes`). The orchestrator writes under its repo `orchestration/repl_memory/` and `data/trace/`. Neither ingests the other: T7 is unbuilt, and Hermes has no orchestrator reader.
- **No double injection today.** Hermes injects MEMORY/USER into the system message. `/v1` injects nothing from memory (no SkillBank, no episodic recall that works, no trace retrieval).

### Duplicated (the overlap is in *mechanism*, not in data)
1. **Two compactors.** Hermes compaction is on in our config. The orchestrator folds on `/chat` (and on `/v1` only if B2 is enabled). If both fire, the orchestrator folds text that Hermes has already summarised. The known failure mode is double folding and anti-thrashing interaction (`research/deep-dives/hermes-agent-v2026-4-23-release.md:142`).
2. **Two transcript-recall surfaces.** Hermes has `session_search` (FTS plus LLM summary). The orchestrator has the trace navigation tools (`trace search-records` and related). They are redundant only if T7 ingests Hermes sessions.
3. **Two "skill" stores.** Hermes background review writes `~/.hermes/skills`; the orchestrator has SkillBank. Both are procedural memory, but they have disjoint consumers, and SkillBank is off in production.

### Conflicting (real interference, all on the *routing/eval* plane, none on data)
1. **Memory calls bypass the override lever.**
   - HS-1g already lists `flush_memories` (`run_agent.py:4500`) and compaction.
   - This audit adds **two more memory-driven egress paths that HS-1g missed**:
     - (a) `session_search` summarisation goes through `async_call_llm` (`tools/session_search_tool.py:156`) and has no `extra_body`;
     - (b) the **background memory/skill review** builds a fresh `AIAgent` with no `session_id` (`run_agent.py:1412-1428`, fresh id at `:845-852`). The EPYC plugin keys its overrides by session and falls back only to `"default"` (`plugins/epyc-orchestrator-overrides/__init__.py:127-129`). Every 10 turns, a full re-read of the conversation therefore reaches `:8000` **without** `/use`, `/escalation` or `/nocode`.
   - These calls are routed by the frontdoor as ordinary user traffic. They consume slots and pollute any per-request telemetry that later learns from `/v1`.
2. **Background review adds load.** Every `nudge_interval` turns, the whole conversation is re-sent (prefill) as an extra request. That is a hidden cost at 32K context on a shared host.
3. **Stale-memory contradiction.** USER.md is frozen at session start, and its "preferences" arrive as system-prompt text. If a user preference such as "always use the big model" lives there, it reaches routing only as prose. It can then contradict an explicit `x_*` override, or a routing decision learned by episodic memory, with no contract to settle which wins (`hermes-outer-shell.md:57-60`). This is a precedence gap, not data corruption.
4. **Compaction breaks trace pairing.** Hermes compaction rewrites history and **re-keys the session id** (`run_agent.py:4606-4628`). Once UTM-P1 or T7 pairs traces by session or turn ordinal, one logical conversation shows up as a chain of ids, and the orchestrator sees summarised rather than raw turns. Any Hermes ingest must follow `parent_session_id`.
5. **Delegation.** Children are memory-blocked (good), but they bypass overrides (HS-1g) and run their own fan-out beside the orchestrator's escalation. That is a routing conflict, not a memory conflict.

### Effect on evaluation (M-12 Tulving/BEAM)
- **Structurally fenced today.** The M-12 arms run through the research benchmark runner, not through Hermes. The `trace` arm builds a **private per-run `events.sqlite` in a mkdtemp** (`epyc-inference-research scripts/benchmark/beam_memory_retrievers.py:151-156`; `tulving_trace_retriever.py:44`, `:111`). Hermes memory cannot reach those prompts, and Hermes traffic cannot reach that store.
- **What would contaminate it:**
  - (i) running any memory eval *through* Hermes: MEMORY/USER in the system prompt, `session_search` over earlier benchmark sessions, and the background review writing benchmark facts into `~/.hermes`;
  - (ii) a future T7 ingest into the production trace DB, if an M-12 arm were ever pointed at it;
  - (iii) a future `/v1` MemRL wiring that learns Q-values from Hermes traffic, including the un-overridden review and flush calls.
- **Fence:**
  - M-12 and any cross-harness bake-off must run with a throwaway `HERMES_HOME`, `memory_enabled=false`, `user_profile_enabled=false`, `nudge_interval=0`, no `session_search`, and `compression.enabled=false`;
  - record these settings on the Harness Card (the HS-6c locked-harness rule);
  - T7 must write to a source-tagged partition (`source=hermes_session`) that eval arms exclude by construction.

## 4. Integration options

| Option | What | Cost | Assessment |
|---|---|---|---|
| **(a) Disable Hermes memory entirely** | `memory_enabled/user_profile_enabled=false`, `nudge_interval=0`, drop `memory` and `session_search` from `platform_toolsets`, `compression.enabled=false`, and keep Honcho off | Config only, ≈0 code. **Also closes 3 of the 5 memory-driven bypasses** (flush, review, `session_search`). | Hermes loses its main UX differentiator: cross-session user profile. Mandatory for eval runs regardless. |
| **(b) Route Hermes memory to the orchestrator store** | No memory-provider API exists at the pin. The two routes are (1) a **Honcho-compatible shim** (`HONCHO_BASE_URL`) in front of the orchestrator, or (2) a plugin `register_tool` replacement for `memory`, plus a core patch to `_build_system_prompt`. | MEDIUM–HIGH: a new server API or a maintained core patch. | **Wrong target.** The episodic store holds routing Q-tuples, not user facts, so user preferences have no home in it. The trace store is read-only by design (UTM non-goal, `unified-trace-memory-service.md:124-125`). Revisit only if a newer upstream ships a provider ABC. |
| **(c) Keep both, partition responsibilities** | Hermes keeps only USER.md (and optionally MEMORY.md). The orchestrator owns routing, folding and escalation. Set compression off and `delegate_task` gated, `nudge_interval=0` (or patch the review agent to inherit `session_id`), and `session_search` off (or patch it to carry overrides). Add a precedence rule: an explicit `x_*` beats profile prose. T7 ingests later with lineage. | LOW: config, plus the small patch HS-4 option D already requires, extended to the review and `session_search` paths. | **The natural fit, and what the two-layer design intended.** |
| **(d) Adopt Hermes memory instead** | Replace episodic memory with MEMORY.md, Honcho or `session_search` | Very high | Not viable. Hermes memory is a 2.2 KB prose file plus FTS. It cannot hold Q-values, embeddings or routing outcomes, and it runs client-side, invisible to autopilot. |

**Comparison with the other candidates.** OpenCode and pi have **no persistent memory tier**. Their only layer-(B) memory-like behaviour is compaction, switched off with `compaction.auto:false` or `compaction.enabled=false` (HS-4 package §2 row "Own layer-(B) loop", `hs4-harness-decision-package-20260916.md:42`; pi-agent-core has "no memory tier", `hermes-outer-shell.md:448`). The whole question in this report is therefore Hermes-specific. For OpenCode or pi the answer is a single config flag. For Hermes it is config, plus a small, ongoing patch surface that grows from 4 paths to 6 once the review agent and `session_search` are counted. omp's `autolearn/` surface was not audited here.

## Verdict

**MIXED: complementary in data, competing in mechanism.**

- **Complementary in data.**
  - Hermes remembers the *user*; the orchestrator remembers *which routes work*.
  - They share no store.
  - The `/v1` path reads and writes no orchestrator memory, so there is no double injection or duplicate record today.
- **Competing in mechanism.** Hermes' memory machinery generates its own LLM traffic that the orchestrator routes without overrides:
  - `flush_memories`;
  - the background review agent (new finding);
  - `session_search` summarisation (new finding);
  - compaction.
  It also runs a second compactor and a second delegation loop.

Eval contamination is fenced today by construction (private trace DBs; M-12 does not go through Hermes). It must stay fenced by disabling Hermes memory on every measured run.

## Recommendation for HS-4

1. **Memory does not overturn the package's recommendation (Option A, OpenCode; pi as the alternative). It strengthens it.**
   - For OpenCode or pi the memory question closes with one config flag.
   - For Hermes it adds two more bypass paths to Option D's patch list: the background review and `session_search`.
2. **If Hermes (D) is chosen, adopt partition (c):**
   - USER.md only;
   - `nudge_interval=0`;
   - `session_search` off;
   - `compression.enabled=false`;
   - `delegate_task` gated;
   - an "explicit `x_*` beats profile prose" rule;
   - re-run HS-1g at the new pin with the two added paths.
   Reject (b) and (d).
3. **For any choice:**
   - measured runs use option (a);
   - T7 / UTM-P1 ingest must be source-partitioned and lineage-aware (`parent_session_id`).
4. **Follow-ups for the owning sessions, independent of HS-4:**
   - fix the dead `/v1` `recall()` (`routing.py:165`, `search_similar` does not exist);
   - remove or correct the inert `mempalace:` block (`hermes-config.yaml:115-120`);
   - flip `compression.enabled` to false in `hermes-config.yaml:45`, per HS-1b.
