# Hermes Agent as Outer Shell — Evaluation Record (closed 2026-09-16)

**Decision (operator, HS-4, 2026-09-16): Hermes was not selected.** The shell is **OpenCode**, with
pi as the fallback. The Hermes-style features we want (user-profile memory, notes,
`session_search`, delegation, background review, compaction) will be built **inside the
orchestrator**: one memory system, one router, no shell patches to carry. See
[`docs/design/hs4-shell-and-orchestrator-features-20260916.md`](../../design/hs4-shell-and-orchestrator-features-20260916.md)
(§0 decision, §3 feature map, §4 phased plan) and the decision package
[`docs/design/hs4-harness-decision-package-20260916.md`](../../design/hs4-harness-decision-package-20260916.md).

**Source handoff:** [`handoffs/completed/hermes-outer-shell.md`](../../../handoffs/completed/hermes-outer-shell.md)
(2026-03-20 to 2026-09-16). The live track is
[`harness-selection-and-integration.md`](../../../handoffs/active/harness-selection-and-integration.md).
**Reusable instrument:** [`client-surface-audit.md`](client-surface-audit.md).
**Memory audit:** [`progress/2026-09/2026-09-16-sub-hermes-memory.md`](../../../progress/2026-09/2026-09-16-sub-hermes-memory.md).
**Audited pin:** `/mnt/raid0/llm/hermes-agent` @ `532a49f1` (`v2026.3.23-44`). All `path:line`
references below are at this pin unless stated.

## 1. What was built and validated

- **Choice of Hermes over OpenGauss (2026-03-25).** OpenGauss is specialised for Lean 4. Hermes is
  general-purpose and has first-class support for a custom OpenAI-compatible endpoint. The source
  audit found no litellm (the OpenAI SDK is used directly), model auto-detection from `/v1/models`,
  and memory kept in flat files.
- **Root-side assets (still in tree, now reference only):** `scripts/hermes/` holds
  `hermes-config.yaml`, `launch_hermes_backend.sh` (llama-server on `:8099`), `setup_hermes.sh`,
  `HERMES.md`, `chat-template-no-think.jinja`, `hermes_pin_audit.py`, `run_hermes_smokes.sh`,
  `reference_openai_client.py`, the `skills/` corpus (`TEMPLATE.md`, `AUTHORING.md`,
  `check_drift.py`, `overview/`, `use/`, `escalation/`, `nocode/`) and `plugins/`
  (`epyc-orchestrator-overrides`, `local-image-generate`).
- **Orchestrator API (2026-04-05, shell-agnostic, kept):** `x_max_escalation`, `x_force_model` and
  `x_disable_repl` were added to `OpenAIChatRequest`, and all overrides are echoed in
  `x_orchestrator_metadata` when `x_show_routing=true`.
- **Skill drift check (2026-06-14):** `check_drift.py` diffs the declared `x_*` fields against those
  documented in skills, wired through `scripts/hooks/hermes_drift_precommit.sh`. The pattern is from
  Venice's `sync_from_swagger.py` (intake-450#record). It generalises to any skill corpus that documents
  the `x_*` contract, including OpenCode's in-repo skills folder.
- **Live smokes:** the 2026-03-25 smoke passed basic conversation and tool execution (slow: about
  24 s to the first response, spent on think tokens). The inference-batch run
  `BULK-hermes-smokes-20260721T042834Z` passed `P-SMOKE-1` 13/13. That covered `live:subagent`
  (2 parallel sub-agents serialised on one slot, no shared-state corruption), `live:multiturn`,
  `live:streaming` and `live:reference-client`. Artifacts are in
  `coordination/inference-batch/bundles/BULK-hermes-smokes/`.

## 2. Plugin behaviour

- **Hook surface at the pin:** `pre/post_tool_call`, `pre/post_llm_call`,
  `on_session_start/end`, `register_tool` and `register_command` (`hermes_cli/plugins.py:59-66`,
  `:124`, `:174`). There is **no memory-provider interface**.
- **`pre_llm_call` receives the mutable `api_kwargs`** on every main-loop turn
  (`run_agent.py:4213-4224`), in chat-completions mode only. The anthropic and codex branches return
  before the hook (`:4042-4108`). `extra_body` serialises to top-level body keys, which is exactly
  the orchestrator contract.
- **The EPYC plugin** `epyc-orchestrator-overrides` registers `/use`, `/escalation`, `/nocode` and
  `/epyc-overrides`. It stores overrides per Hermes session and injects `x_orchestrator_role`,
  `x_max_escalation` and `x_disable_repl` through `extra_body`. It looks overrides up **by
  session id, with only `"default"` as a fallback** (`__init__.py:127-129`). Any agent created with a
  fresh session id therefore runs without overrides.
- **Tool override by name.** The `tools.registry` uses plain dict assignment, so a plugin tool with
  the same name replaces the built-in. This is how `local-image-generate` replaced the FAL-backed
  `image_generate` (backend: ERNIE-Image-Turbo through ComfyUI, see `ernie-image-turbo-evaluation.md`).
- **Upstream core patch needed for slash commands.** `register_command()` plumbing,
  `invoke_plugin_command()` and the mutable `pre_llm_call` invocation were added in local commit
  `532a49f1` (2026-07-06), which is on no pushed ref (the clone's only remote is NousResearch
  upstream). With the handoff closed, the commit is preserved as
  [`patches/hermes-agent-532a49f1-plugin-slash-commands.patch`](patches/hermes-agent-532a49f1-plugin-slash-commands.patch)
  (7 files, +357/−33). Newer upstream releases (v2026.4.23+) have a larger plugin surface.
  Whether they have a memory-provider abstraction was not verified.

## 3. Bypass paths: where the override lever does not reach

Found with the call-verb check ([`client-surface-audit.md`](client-surface-audit.md) Step 3).
**Only the main loop honours the plugin's `extra_body`.** Every path below reaches `:8000` as
ordinary user traffic without `/use`, `/escalation` or `/nocode`.

| Path | Runs by default? | Why it bypasses | Evidence |
|---|---|---|---|
| Context compaction | yes (threshold 0.50) | the compressor calls the aux `call_llm` with no `extra_body` | `agent/context_compressor.py:346-355` |
| Iteration-limit summary | when `max_turns` is hit | builds its own kwargs; no hook | `run_agent.py:5297-5350` |
| `flush_memories` | before every compression, reset or exit (≥6 user turns; always before compression) | aux `call_llm` | `run_agent.py:4424-4448`, `:4497-4501`, `:4594` |
| `delegate_task` children | when the tool is enabled | child `AIAgent` gets no `session_id`, so a fresh id misses the session-keyed plugin | `tools/delegate_tool.py:207`; `run_agent.py:845-852` |
| Background memory/skill review | every `nudge_interval` (10) user turns | forked `AIAgent` with a fresh session id; it re-sends the whole conversation | `run_agent.py:1383-1428`, `:5494-5500` |
| `session_search` summary | when the tool is called | `async_call_llm` with no `extra_body` | `tools/session_search_tool.py:156` |

**Consequence.** The HS-1b verdict ("patch cost ≈ 0") held only with `compression.enabled:false`
and `delegate_task` gated off. The memory audit then added the background review and
`session_search`, which grew Option D's patch surface from 4 paths to 6. This was a
material input to the HS-4 decision against Hermes.

## 4. Memory model

| Store | Where | Read back how | Switch |
|---|---|---|---|
| `MEMORY.md` (agent notes, 2200-char cap) and `USER.md` (profile, 1375-char cap) | `$HERMES_HOME/memories/`, entries separated by `§` | Injected into the **system prompt** as a snapshot frozen at session start; mid-session writes show only in tool results | `memory.memory_enabled`, `memory.user_profile_enabled` (both default true) |
| Background review writes | same files, plus `$HERMES_HOME/skills/` | next session | `nudge_interval: 0`, `skills.creation_nudge_interval: 0` |
| Session DB | SQLite `state.db` with FTS5; compaction **re-keys** the session (`parent_session_id`) | only through `session_search` (FTS plus an LLM summary) | drop the tool |
| Honcho | remote service (`base_url` overridable) | appended to the user message at call time, never persisted | inactive without enable **and** API key |
| Delegation | none of its own | children run `skip_memory=True` and are blocked from the `memory` tool | gate `delegate_task` |

**Relation to the orchestrator: complementary in data, competing in mechanism.** Hermes remembers
the *user*. The orchestrator's episodic store remembers *which routes work*, as routing
Q-tuples. The two share no store, and the `/v1` path reads and writes no orchestrator memory. The
competition is in mechanism: Hermes adds a second compactor, a second delegation loop and
un-overridden memory side traffic (§3). Compaction re-keying also breaks trace pairing, so any
ingest has to follow `parent_session_id`. Routing Hermes memory into the episodic store was the
wrong target, because that store holds no user facts. This is why HS-4 rebuilds the features
server-side instead (design doc §3.1–3.6).

**Eval fence (applies to any shell).** Measured runs, including M-12 and any cross-harness
bake-off, must not run through a shell's memory. For Hermes that meant a throwaway `HERMES_HOME`,
memory and profile off, `nudge_interval=0`, no `session_search` and compression off, all recorded
on the Harness Card. For OpenCode the equivalent is `compaction.auto:false` plus `x_memory=off`
(HS-4 P0.3/P2).

## 5. Config lessons

- **`-np N` splits the context.** `-np 2` with `-c 32768` gave 16K per slot, and `/v1/props` reports
  the per-slot value. For a single-user CLI, use `-np 1` and state `context_length` explicitly.
- **Think tokens burn context and wall-clock time on trivial turns.** The backend first used a
  no-think chat template (`chat-template-no-think.jinja`). The 2026-07-21 batch switched to the
  model's built-in Qwen3-Coder template with native `--reasoning off`. Qwen3.6+ needs
  `enable_thinking=false` on the chat-completions path.
- **Tool calling needs `--jinja`.** Check `Chat format:` in the server log.
- **Auxiliary models** (compression, vision, web extract) can all point at the same local endpoint
  with `provider: "main"`. An empty `summary_model` resolves to the auto-detected model.
- **The inert `mempalace:` block.** `hermes-config.yaml` declared `mempalace: enabled: true`, but
  Hermes never reads that key. It loads MCP servers only from `mcp_servers:`
  (`tools/mcp_tool.py:9-15`), so "H-8 MemPalace memory" was never wired, and the comment claiming it
  was was false. **Fixed** in root `91d56181` (block commented out and annotated). General lesson: a
  config key that no code reads fails silently. Before claiming a feature is wired, grep the pinned
  tree for the key.
- **`compression.enabled: true`** in `hermes-config.yaml` contradicts the HS-1b recommendation.
  No change was made: Hermes is no longer a deployment target, and the file is reference only.
- **Config keys that do nothing** against a text-only local endpoint: `vision_model`, and
  `web_search_model` (its cloud tool is disabled).
- **Pin hygiene.** `hermes_pin_audit.py` is the no-fetch pin checklist. The planned pin bump was
  never done: the checkout stayed at `532a49f1`, one commit ahead of `origin/main`, with an
  untracked `HERMES.md`.

## 6. Follow-ups and filings

- **Dead `/v1` `recall()`**, found by the memory audit: `_recall_legacy` called a non-existent
  `EpisodicStore.search_similar`, and the error was swallowed. **Fixed** in orchestrator
  `83c7ed2f` ("wire shared retriever, fail loudly").
- **AP-04 / AP-54b.** No Hermes item was filed under either id. AP-54b in
  `autopilot-continuous-optimization.md` is the wiki-fence A/B on eval rollouts, which is not a
  Hermes item, and AP-04 is not a Hermes item either. Nothing to update.
- **Carried to the live track:** the shell-agnostic `/v1` override validations (live
  `reference_openai_client.py --send` covering role, force-model, escalation cap, REPL disable,
  routing metadata and streaming) were moved to `harness-selection-and-integration.md` as HS-4
  P0.4 input. See the completion header of the source handoff for how each open box was closed.

## 7. Design patterns kept from the handoff's research intake

These are pointers only. The full notes are in the source handoff's Research Intake sections and
the linked deep-dives.

- **HOS-Pattern-S (Mirage, intake-572#record):** a 5-file adapter shim per framework (`__init__`,
  `backend`, `prompt`, `_convert`, `_messages`).
- **HOS-Pattern-R (Mirage):** replay-drift detection. Record each fingerprint from the tool response
  at read time, never from a fresh stat at snapshot time.
- **Side-git snapshot store (DeepSeek-TUI, intake-508#record):** `--git-dir`/`--work-tree` on every call,
  a two-tier FNV-1a path hash, and snapshots of workspace files only. Conversation state must be
  restored separately.
- **Placeholder-credential egress proxy (Centaur, intake-696#record):** the agent process never holds live
  secrets.
- **A2A (intake-655#record):** relevant only if external exposure (Path A) becomes load-bearing. The
  internal lifecycle is tracked in `internal-interaction-lifecycle.md`.
- **Recursion depth:** the RLM reproduction shows depth-2 recursion degrades accuracy. Default
  `max_depth=1` for any delegation feature unless a depth controller is trained (intake-536#record cluster;
  applies to HS-4 P4).
