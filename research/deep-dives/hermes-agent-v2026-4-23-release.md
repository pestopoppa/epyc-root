# Deep Dive: hermes-agent v2026.4.23 (v0.11.0)

**Date**: 2026-04-24
**Intake**: intake-454 (github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23)
**Release**: v0.11.0, tagged 2026-04-23 (one day old at time of writing)
**Previous release**: v0.9.0 (intake-117 baseline, 2026-03-15 era)
**Local checkout state**: `/mnt/raid0/llm/hermes-agent` is on `origin/main` at `v2026.3.23-43-g...`, **clean against upstream**. Our only local artifact is an untracked `HERMES.md` (system prompt). We are NOT maintaining a fork diff — all EPYC customization lives externally in `/workspace/scripts/hermes/` (config YAML, launch script, skill bundles) and in the orchestrator (`x_*` override params on `/v1/chat/completions`).
**Question**: Which patterns in this release merit full-repo bump vs selective adoption vs ignore, and in what order?

## Executive Summary

**Bump upstream main to v2026.4.23.** We do not run a fork; we run pinned upstream + external config. The low-cost action is `git pull` (or an explicit tag checkout) and re-smoke-testing, not a rebase. The expensive action — and the real reason to treat this as a major intake — is that **four active handoffs now have concrete upstream patterns to port or mirror**: (1) tool-output-compression's known Phase 2b thrashing failure mode has a named fix upstream (compressor anti-thrashing + fallback chain); (2) context-folding-progressive's Phase 3c language/role-aware condensation has a natural template in the language-aware summarizer; (3) hermes-outer-shell Phase 2 `x_*` overrides are a candidate for re-expression as a **namespaced plugin bundle** with execution-veto hooks rather than API-side patches; (4) meta-harness-optimization's parallel-subagent design has a ready-made upstream substrate in the orchestrator-role + cross-agent file-state coordination layer.

**Refined verdict: `adopt_component` for the base binary (we already run it; bumping is trivial); `adopt_patterns` for the individual subsystems that overlap our active work.** The intake's `adopt_patterns` label was technically accurate ("cherry-pick individual patterns into our own code") but the underlying economics are that the cheapest thing we can do is take the whole component and then decide which of our external add-ons (orchestrator `x_*` overrides, hermes-config.yaml, skill bundle) to re-express in upstream's new plugin surface.

**Novelty: medium (unchanged).** No single feature is unprecedented, but the compression of four independent patterns we were independently designing — anti-thrashing, veto hooks, transport abstraction, namespaced skills — into a single shipped release is surprising for a 40-day window.

**Relevance: high (unchanged).** Hermes is a running component in our stack, and this release touches four of our active handoffs.

## Release Overview

| Metric | Value |
|--------|------:|
| Commits since v0.9.0 | 1,556 |
| Merged PRs | 761 |
| Community contributors | 29 (290 with co-authors) |
| Files touched | 1,314 |
| Top PR author | @kshitijk4poor (49 PRs — transport refactor, Step Plan, Xiaomi) |
| TUI rewrite commits | ~310 (Ink/React) |
| New inference providers | 7+ (Bedrock native, NIM, Arcee, Step Plan, Gemini CLI OAuth, ai-gateway, GPT-5.5 via Codex OAuth) |
| New messaging platforms | 1 full (QQBot) + parity across 5 existing (Discord/Feishu/DingTalk/WhatsApp/Signal) |
| New MCP capabilities | 12, incl. CDP raw passthrough |
| Tenure | 40 days (2026-03-15 ish → 2026-04-23) |

1,556 commits in 40 days = ~39 commits/day. That is not a bugfix release; it is a platform cycle. The release is held together by three load-bearing refactors (transport abstraction, plugin surface, Ink TUI) and then a very long tail of providers, platforms, and skills.

## Pattern-by-Pattern Analysis

### 1. Orchestrator role + cross-agent file-state coordination

**What it does.** A new `orchestrator` agent role with configurable `max_spawn_depth` (default flat, i.e., no recursive spawning). Concurrent sibling subagents share filesystem state through an explicit file-coordination layer — locks, turn-taking, visibility of partial work — rather than racing on the FS.

**Maps to.** `meta-harness-optimization.md` (parallel subagent search), `repl-turn-efficiency.md` (turn-per-task accounting when subagents parallelize), and secondarily `autopilot-iteration-strategy-synthesis.md` (how autopilot sessions might fan out).

**Porting cost.** Medium. We do not currently spawn parallel subagents from the orchestrator; adopting this pattern means reusing hermes-agent's orchestrator role *inside* the outer shell rather than reimplementing it. If we keep the two-layer architecture (Hermes outer, EPYC inner), parallel subagents live at the Hermes layer and make N independent `/v1/chat/completions` calls — our orchestrator already handles concurrent requests correctly per `hermes-outer-shell.md` Question 5.

**Blast radius.** Low on our fork (none — we have no fork). Medium on our orchestrator: multiple concurrent Hermes-side subagents flowing into the same `localhost:8000` endpoint will exercise the inference lock / per-slot context assumptions (`-np 1` config decision per hermes-outer-shell Phase 1). This is the "swarm coordination" open question from hermes-outer-shell P2 and it is now a forced one.

### 2. `/steer <prompt>` mid-run course correction

**What it does.** Injects a steering note after the next tool call without interrupting the current turn or breaking prompt cache. The in-progress generation finishes, the steer text is appended to the subsequent turn's context, and the cache-prefix up to the injection point is preserved.

**Maps to.** `repl-turn-efficiency.md` (cache-preserving turn edits), and indirectly `context-folding-progressive.md` Phase 3c (role-aware compaction — `/steer` is effectively a role/priority nudge delivered mid-session).

**Porting cost.** Trivial on the outer shell (it's a built-in slash command in v0.11.0). Medium if we want an analogous mechanism inside the orchestrator's REPL loop. The interesting sub-question is whether a user `/steer` issued through Hermes should *also* pass through to the orchestrator as a routing-override hint (e.g., map to a new `x_steer` field that updates role metadata without re-running frontdoor).

**Blast radius.** Zero on current production if we just enable the upstream slash command. Medium if we extend it into `x_steer` — touches `openai_compat.py` and the same routing-override path as `x_force_model`/`x_max_escalation`/`x_disable_repl`.

### 3. Compressor: anti-thrashing + language-aware + fallback-to-main chain

**What it does.** Upstream's compression model pass gains (a) **anti-thrashing**: detection and suppression of the "compress → context grows → re-compress the same window" oscillation; (b) **language-respecting collapse**: preserves code-block structure and doesn't cross natural-language boundaries mid-sentence; (c) **fallback chain**: when the dedicated compressor provider returns 503/404 (common with self-hosted vLLM during restart), the call degrades to the main model instead of retrying into a failure loop; (d) smarter dedup and a template upgrade; (e) richer Hindsight session-scoped retain metadata.

**Maps to.** `tool-output-compression.md` Phase 2b/3+ **directly**, and `context-folding-progressive.md` Phase 3c (role-aware compaction) secondarily. The anti-thrashing logic is a concrete fix for the oscillation failure mode flagged in tool-output-compression Phase 2b monitoring (2026-04-11).

**Porting cost.** Medium. We can either (a) lift upstream's anti-thrashing heuristic into our `scripts/utils/compress_tool_output.py` (our native implementation) or (b) rely on the upstream compressor for conversation-level compression and keep our native module for tool-output-specific compression. Option (b) is the cleaner separation and matches our existing two-layer memory design (hermes-outer-shell §"Two-Layer Memory Architecture").

**Blast radius.** Low if we confine adoption to the Hermes layer (upstream ships this wired up — turning it on is a config toggle). Low-medium if we also port the anti-thrashing heuristic into our native module (27 tests exist and need supplementing). **This is the single highest-ROI adoption in the release** because it closes a known open failure mode rather than adding a new capability.

### 4. Plugin surface: `register_command` / `dispatch_tool` / `pre_tool_call` veto / `transform_tool_result` / shell hooks / namespaced skill bundles

**What it does.** A six-way expansion of the plugin API: plugins can register slash commands, dispatch tools directly without going through the model, veto a pending tool call synchronously, rewrite tool results before they re-enter context, transform terminal output, and register a skills bundle under a namespace. There is also an opt-in "disk cleanup" bundled plugin as a reference implementation.

**Maps to.** `hermes-outer-shell.md` Phase 2+ (our `x_*` override surface) **directly**. Also `orchestrator-conversation-management.md` B7 (prompt-injection scanning is a natural fit for a `pre_tool_call` veto plugin). Also `tool-output-compression.md` (compression could be a `transform_tool_result` plugin rather than an in-process hook).

**Porting cost.** Medium. The key question is whether our `x_max_escalation` / `x_force_model` / `x_disable_repl` overrides — currently implemented as extension fields on `OpenAIChatRequest` (hermes-outer-shell Phase 2 Routing API) — should be re-expressed as a namespaced plugin bundle that registers as slash commands on the Hermes side and dispatches to the orchestrator endpoint. This replaces "Hermes command → Hermes config lookup → API call with `x_*`" with "Hermes plugin slash command → plugin dispatcher → API call". The net win is that the slash commands become user-discoverable via Hermes's own `/help` surface instead of being documented only in our skill YAMLs.

**Blast radius.** Low on production (the current `x_*` path keeps working; the plugin is additive). Medium on governance — adding a bundled plugin means adding a new directory under `scripts/hermes/` and a plugin manifest. Cleanup-of-old-model: the current three SKILL.md files under `scripts/hermes/skills/use/escalation/nocode/` could either stay and be supplemented, or be migrated into a single namespaced "epyc-orchestrator" plugin bundle.

### 5. Transport abstraction + 5+ new inference paths

**What it does.** A transport/format abstraction layer with four concrete adapters: `AnthropicTransport`, `ChatCompletionsTransport`, `ResponsesApiTransport`, `BedrockTransport`. On top of it, native providers for Bedrock, NVIDIA NIM, Arcee, Step Plan, Gemini CLI OAuth, Vercel ai-gateway (with pricing + dynamic discovery), and GPT-5.5 via Codex OAuth.

**Maps to.** `hermes-outer-shell.md` §"Source Audit Findings" — we picked Hermes over OpenGauss partly because it "uses OpenAI SDK directly" and had first-class custom endpoint support. The new transport layer *generalizes* that and potentially obsoletes any custom patches we might have contemplated for multi-provider fan-out.

**Porting cost.** Trivial — we don't use any of the new providers. Our only transport is `ChatCompletionsTransport` → `localhost:8000/v1/chat/completions` → llama-server. The new layer is strictly additive from our perspective.

**Blast radius.** Near-zero. The only way this affects us is if the refactor changed request serialization for the ChatCompletions path in a way that breaks our llama-server chat template. This is a specific smoke-test item for the version bump (see Risks §1).

**Does it obsolete fork patches?** N/A — we don't carry transport patches.

### 6. MCP improvements (CDP raw passthrough, timeout handling, tool-call forwarding)

**What it does.** 12 MCP improvements. Headliners: `browser_cdp` raw DevTools Protocol passthrough (bypasses the built-in browser tool and lets an MCP server drive Chrome directly), timeout handling for long-running MCP tools, and cleaner tool-call forwarding so model-emitted tool_calls round-trip through MCP without reformatting artifacts.

**Maps to.** Our MCP infrastructure: MemPalace MCP (intake-326, P2.5 H-8 done), mcp-searxng (intake-361, future), GitNexus MCP (already in `CLAUDE.md`). Also `orchestrator-conversation-management.md` B3 (Skill Hub Interop) where skills increasingly surface as MCP servers.

**Porting cost.** Trivial — the upstream improvements are transparent to us as MCP clients. No config changes required.

**Blast radius.** Low. MCP timeout handling should be tested against the MemPalace server (slow vector queries on cold cache) as part of the version-bump smoke test. CDP raw passthrough is not a current need.

### 7. Execution modes (project/strict) + auto-prune sessions + VACUUM state.db

**What it does.** Tool execution has two modes, `project` (default, permissive within the project root) and `strict` (allowlist-only, audit trail). Separately, at startup, old sessions are auto-pruned and `VACUUM` is run on the SQLite state database.

**Maps to.** Our operational hygiene. State files live in `~/.hermes/` per user; we have no handoff for state management but this is adjacent to `feedback_no_core_dumps` and `feedback_incremental_persistence` memories.

**Porting cost.** Trivial — opt-in. The gotcha is the VACUUM at startup: on our machine `~/.hermes/state.db` could be large if Hermes has been accumulating sessions since 2026-03-25. A VACUUM will rewrite the whole file and on first post-upgrade start might take non-trivial time. Document-only risk.

**Blast radius.** Low. Execution-mode default is `project`, which matches our current behavior. Switching to `strict` would require auditing our skill commands (`/use`, `/escalation`, `/nocode`) to ensure they declare all tool dependencies — currently they don't need to.

### 8. Ink-based TUI rewrite (React + Python JSON-RPC backend)

**What it does.** The TUI is rewritten from a Python curses-style loop to an Ink/React frontend process that talks to a Python backend over JSON-RPC. New features: stable picker keys, `/clear` confirm, light-theme preset, Git branch in status bar, per-turn elapsed stopwatch, subagent-spawn observability overlay, sticky composer, OSC-52 clipboard support, virtualized history rendering.

**Maps to.** Nothing in our active handoffs — we drive Hermes in CLI/scripted mode and don't depend on the TUI for automation. However, the **Python JSON-RPC backend** is potentially interesting as an alternative integration surface: rather than spawning `hermes` as a child process and speaking to it over stdin/stdout, we could call the JSON-RPC backend directly.

**Porting cost.** N/A — pure upstream. Ignore unless we start building a custom frontend (none planned).

**Blast radius.** Low-medium. The rewrite touches 310+ commits and is by far the largest single subsystem change. Any headless-mode usage we have needs smoke-testing against the new backend. Specifically: `launch_hermes_backend.sh` and any script that pipes into `hermes` CLI should be verified post-upgrade.

## Fork-Rebase vs Cherry-Pick Decision

**Recommendation: neither — bump the pin.** We do not maintain a fork. `/mnt/raid0/llm/hermes-agent` tracks `origin/main` cleanly; our local work is external (orchestrator-side API overrides, config YAML, skill bundles, launch script). The correct operation is:

1. `cd /mnt/raid0/llm/hermes-agent && git fetch && git checkout v2026.4.23` (or stay on `main`; at time of writing main == the tag).
2. Re-run `scripts/hermes/setup_hermes.sh` if the upstream config schema moved.
3. Smoke-test the five scenarios enumerated in Risks §1.
4. Then, in priority order, port / re-express the four patterns under Concrete Next Actions.

If at some later point we *do* want to carry a fork patch (e.g., a llama.cpp-specific streaming fix that upstream will not accept), the calculus changes — but nothing in this release creates that need. The plugin surface is explicitly designed to avoid forking for extension.

## Risk / Breaking Changes

1. **Chat-template / streaming drift (HIGH priority to test).** The ChatCompletions transport was refactored (#2903 `Idempotency-Key support, body size limit, OpenAI error envelope` is a visible signal). Our `scripts/hermes/chat-template-no-think.jinja` + `-np 1 + context_length: 32768` Phase-1 config needs to be validated — specifically: (a) does the new transport still send the Jinja-templated prompt unchanged to llama-server, (b) does SSE streaming still work end-to-end with `x_force_model`/`x_max_escalation`/`x_disable_repl` (Package E validation from hermes-outer-shell needs re-running).

2. **Config schema additions.** `max_spawn_depth`, plugin surface config, execution mode, compression template upgrades, and the dashboard plugin config may introduce new required or changed-default keys in `~/.hermes/config.yaml`. Diff `hermes-config.yaml.example` between v2026.3.23 and v2026.4.23 before overwriting.

3. **State.db VACUUM at first startup.** Expect a delay on the first post-upgrade `hermes` invocation. Benign but surprising.

4. **Subagent FS coordination meets our `-np 1` llama-server config.** If anyone enables the orchestrator role and spawns parallel subagents, each will issue concurrent `/v1/chat/completions` calls. Our single-slot llama-server will serialize them. This is a *correctness* win (no racing) but a *throughput* surprise vs any implicit expectation of parallelism.

5. **Compressor fallback chain interacts with our auxiliary=main config.** hermes-outer-shell Phase 1 set auxiliary compression model to `provider: "main"` (same local endpoint). With the upstream fallback chain (compressor 503/404 → main model), if the "main" model IS the compressor, fallback becomes a no-op retry loop. The anti-thrashing guard should prevent oscillation, but verify. Specifically: check that fallback is a same-provider-different-model check, not a blind retry.

6. **Ink TUI rewrite + headless invocation.** Our `launch_hermes_backend.sh` starts llama-server; `hermes` CLI is launched interactively or piped. Virtualized history rendering and the JSON-RPC backend split may change the `hermes --non-interactive` or scripted-mode contract. Low-confidence risk but worth a smoke test.

7. **Message-platform surface expansion ≠ security expansion.** QQBot (17th platform) joins 16 existing. Not all of these platforms' auth models have had parity review. We only use CLI, so this is theoretical — but if anyone ever enables Discord/Feishu/DingTalk tool, the new `require_mention`/`allowed_users` gating should be the *first* config touched.

8. **Skills: hardcoded `/steer`, `/clear`, and plugin slash commands may collide with our three custom skills** (`/use`, `/escalation`, `/nocode`). Confirm no namespace clash. Low probability.

## Refined Assessment

The intake label was `adopt_patterns`. That is *technically* correct — we will adopt individual patterns — but it masks that the cheapest path is a full-component bump (`adopt_component` at the binary level) followed by **selective re-expression** of our external customization (`adopt_patterns` at the integration level). The distinction matters for effort estimation:

- **`adopt_component` framing** suggests 2-4 hours: `git pull`, re-run setup script, smoke-test 5 scenarios, log results.
- **`adopt_patterns` framing** would suggest 20-40 hours of cherry-picking individual patches. That is wrong effort for our situation.

The *real* work after the bump — porting anti-thrashing into our native compressor, re-expressing overrides as a plugin bundle, prototyping subagent + single-slot llama interaction — is a **separate decision tree** per item (and is owned by the individual handoffs).

Updated verdict row (suggested edit to intake-454):
```
Verdict: adopt_component (base binary — bump from v2026.3.23 to v2026.4.23)
         + adopt_patterns (compressor anti-thrashing, plugin-bundle override, subagent+slot interaction)
Novelty: medium (unchanged)
Relevance: high (unchanged)
```

## Concrete Next Actions

Ordered by ROI × certainty:

1. **[DO FIRST — today or tomorrow] Bump pinned Hermes to v2026.4.23 + smoke-test.** `cd /mnt/raid0/llm/hermes-agent && git pull --ff-only`. Re-run `/workspace/scripts/hermes/setup_hermes.sh`. Run the five validation scenarios from hermes-outer-shell "Deferred: Inference Validation" (basic conversation, tool execution, multi-turn context, streaming with `x_*` overrides, compression trigger). Log results in `progress/2026-04/2026-04-24.md` and check off in hermes-outer-shell handoff. Effort: 2-4h.

2. **[HIGH value — closes known failure mode] Port compressor anti-thrashing + fallback chain into `scripts/utils/compress_tool_output.py`** (tool-output-compression Phase 2b open item). Read upstream's implementation, extract the oscillation-detection heuristic, add tests. Keep the native tool-output compressor separate from Hermes's conversation-level compressor — two layers, one shared pattern. Effort: 4-8h.

3. **[MEDIUM value — UX + governance] Re-express `x_*` overrides as a namespaced Hermes plugin bundle** (hermes-outer-shell Phase 2+). Move the three skill YAMLs (`use/`, `escalation/`, `nocode/`) into a single plugin under `scripts/hermes/plugins/epyc-orchestrator/` with `register_command()` + direct-dispatch-to-orchestrator. Keeps `x_*` API as the stable wire format; gains `/help` integration and cleaner versioning. Effort: 4-6h.

4. **[MEDIUM value — closes open question] Validate subagent-spawn + single-slot llama-server interaction** (hermes-outer-shell Question 5, now forced by orchestrator-role availability). Write a test script that spawns 3 concurrent subagents via the new orchestrator role, each issuing `/v1/chat/completions` calls, and verify serialization (not corruption). Document the observed throughput penalty. Effort: 3-5h.

5. **[LOW priority — watch item] Compare `hermes-config.yaml.example` diff against our live config** to identify new required/default keys (auto-prune, execution mode, plugin settings). Update `scripts/hermes/hermes-config.yaml` accordingly. Effort: 1-2h.

6. **[DEFER — revisit after item 4] Decide whether to port the orchestrator-role + FS coordination primitives into `meta-harness-optimization.md` Tier-1/2 loop.** Only makes sense if item 4 shows acceptable behavior; otherwise the parallel-subagent pattern stays at the Hermes layer and meta-harness stays single-threaded. Effort: TBD, gated on 4.

## Sources

- Primary release: https://github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23
- Repo: https://github.com/NousResearch/hermes-agent (upstream, we track `main`)
- Compare (404 at fetch time): https://github.com/NousResearch/hermes-agent/compare/v0.9.0...v2026.4.23
- Local checkout: `/mnt/raid0/llm/hermes-agent` @ `v2026.3.23-43-g...` (clean against upstream)
- Local customization: `/workspace/scripts/hermes/` (config, launch, skills)
- Related handoffs: `/workspace/handoffs/active/hermes-agent-index.md`, `hermes-outer-shell.md`, `tool-output-compression.md`, `context-folding-progressive.md`, `meta-harness-optimization.md`, `repl-turn-efficiency.md`, `orchestrator-conversation-management.md`
- Cross-intakes: intake-117 (original Hermes), intake-172/173 (OpenGauss), intake-277 (LLM Wiki skill), intake-327 (self-evolution), intake-337 (anti-rationalization), intake-388/393 (reasoning traces), intake-450 (Venice Skills cross-runtime pattern), intake-454 (this release)
- Top contributor attributions: @kshitijk4poor (49 PRs, transport refactor), @OutThisLife (31 PRs, TUI), @helix4u (11 PRs, voice/MCP), @austinpickett (8 PRs, dashboard), @alt-glitch (8 PRs, platform hints)
