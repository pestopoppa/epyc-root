# Deep Dive — intake-395 thedotmack/claude-mem

**Date**: 2026-04-17
**Repo**: https://github.com/thedotmack/claude-mem (cloned to `/tmp/claude-mem` for inspection)
**License**: AGPL-3.0 (© 2025 Alex Newman, @thedotmack)
**Intake status**: novelty=medium, relevance=medium, verdict=adopt_patterns (pre-deep-dive)
**Cross-refs**: intake-135 (Cognee), intake-268/269/270 (Karpathy / nvk / qmd wiki cluster), intake-277 (Hermes LLM Wiki), intake-316 (LTM unsolved), intake-321 (ByteRover-adjacent)

This deep dive goes beyond the README to the actual source — hooks config, SDK prompt builders, search orchestrator, token-savings calculator, and the `<private>` tag implementation. The goal is to test whether the three patterns flagged in intake (3-layer MCP workflow, lifecycle-hook taxonomy, `<private>` tag) deliver real value beyond what EPYC already has in flight on `context-folding-progressive.md` and `tool-output-compression.md`.

---

## 1. Architecture Details — What the 3-Layer Search Actually Is

The "3-layer search workflow" advertised in the README (`search → timeline → get_observations`) is **not** a server-side tiered retrieval system. It is a **client-side progressive-disclosure convention** baked into a skill file (`plugin/skills/mem-search/SKILL.md`) that tells Claude Code to call three MCP tools in sequence.

The underlying server-side retrieval is a **2-strategy cascade**, implemented in `src/services/worker/search/SearchOrchestrator.ts:71-120`:

```
Path 1: no query text → SQLiteSearchStrategy (FTS5 + filters only)
Path 2: query text + Chroma available → ChromaSearchStrategy (embeddings)
         └─ on Chroma failure → fall back to SQLiteStrategy with query stripped
Path 3: query text, no Chroma → returns empty {observations:[], sessions:[], prompts:[]}
```

A `HybridSearchStrategy` exists for `findByConcept`/`findByType`/`findByFile` only — NOT for the public `search` tool. The public search tool is strictly "Chroma if available, else SQLite FTS5". There is no RRF fusion, no re-ranking, no BM25+vector combination in the main search path. This is strictly simpler than intake-270 `tobi/qmd`'s documented BM25+vector+LLM-rerank pipeline.

The "3 layers" map to client-side token budgeting:

| Layer | MCP tool | Token cost / result | What is returned |
|-------|----------|---------------------|------------------|
| 1 | `search(query, limit, project, type, obs_type, dateStart/End, offset, orderBy)` | ~50-100 tokens | Markdown table: `ID, Time, Type, Title, ~Read-cost` |
| 2 | `timeline(anchor \| query, depth_before, depth_after)` | ~100-200 / item | Interleaved obs+sessions+prompts within ±depth of an anchor |
| 3 | `get_observations(ids=[...])` | ~500-1000 / obs | Full title, subtitle, narrative, facts, concepts, files_read, files_modified |

This is genuinely useful as a **design pattern** — it is the same progressive-disclosure idea EPYC already has in `tool-output-compression.md` (AXI pattern from intake-301, SkillReducer from intake-302), just applied to memory retrieval instead of tool output. Claude is nudged by the `SKILL.md` to fetch IDs first, filter, then batch-fetch detail with `get_observations(ids=[...])`.

What is new (relative to EPYC's current handoffs): the **batched-ID fetch as a distinct MCP tool** with an explicit protocol: "NEVER fetch full details without filtering first." The skill file wires this into Claude's prompt, not into a harness layer — i.e., it's a prompt-engineered discipline, not an enforced mechanism.

---

## 2. Hook Lifecycle — What Each Hook Actually Captures

From `plugin/hooks/hooks.json` (the installed hook config), claude-mem uses **7 Claude Code lifecycle hooks**, not 5 as the README claims:

| Hook | Timeout | Worker command | What it does |
|------|---------|----------------|--------------|
| `Setup` (`matcher=*`) | 300s | `scripts/smart-install.js` | Plugin install / update self-check |
| `SessionStart` (`matcher=startup\|clear\|compact`) | 60s×3 | `worker-service.cjs start` + `hook claude-code context` | Starts Bun worker on :37777, polls health (20×1s), then injects cross-session context into the new session |
| `UserPromptSubmit` | 60s | `hook claude-code session-init` | Creates a new observer-session row, captures the user's prompt as `contentSessionId`, starts the SDK observer agent |
| `PreToolUse` (`matcher=Read`) | 2000ms | `hook claude-code file-context` | Only on `Read` — pulls prior observations referencing that file, injects as context before the read |
| `PostToolUse` (`matcher=*`) | 120s | `hook claude-code observation` | Fires after every tool call. Sends `{tool_name, tool_input, tool_output, cwd, prompt_number}` to the worker, which queues it for the SDK observer to synthesize into a structured `<observation>` XML block |
| `Stop` | 120s | `hook claude-code summarize` | On assistant-stop (natural turn end), triggers a `<summary>` generation by the observer. This is the compressed progress checkpoint |
| `SessionEnd` | 30s | `hook claude-code session-complete` | Marks session complete in DB |

Noteworthy capture-taxonomy observations:
- **PostToolUse captures raw tool_input+tool_output as JSON** and forwards it to a separate Claude subprocess (via `@anthropic-ai/claude-agent-sdk`) that is sandboxed with ALL tools disallowed (`Bash, Read, Write, Edit, Grep, Glob, WebFetch, WebSearch, Task, NotebookEdit, AskUserQuestion, TodoWrite` — see `src/services/worker/SDKAgent.ts:55-68`). The observer is **observer-only**. This is a clean separation we do not currently have.
- **The observer runs in its own `cwd=OBSERVER_SESSIONS_DIR`** specifically to avoid polluting the user's `claude --resume` project list (Issue #733 referenced in code). Detail that matters if we ever adopt a similar subprocess pattern.
- **Env isolation**: `src/services/worker/SDKAgent.ts:100` uses `sanitizeEnv(buildIsolatedEnv())` so the observer reads `~/.claude-mem/.env`, not the project's `.env`. Prevents random `ANTHROPIC_API_KEY` from project envs leaking into observations.
- **Blocking behavior**: In non-Endless mode, `PostToolUse` is non-blocking (queued). In Endless mode (beta branch, not main), `PostToolUse` **blocks for up to 90s** waiting for observation generation, then injects the compressed observation back into the user's context and clears the raw tool output. See `docs/public/endless-mode.mdx`.

This captures 5 distinct signal classes — `init`, `observation`, `summary`, `file-context-injection`, `session-complete` — which maps directly to the signal taxonomy we need for Phase 1 of `context-folding-progressive.md` (granular-block vs consolidated-segment vs session-boundary distinction). We already have Tier-1/Tier-2 but not the explicit **file-context-injection on Read** signal.

---

## 3. Summarization Strategy — What Actually Gets Stored

Source: `src/sdk/prompts.ts` (242 lines). Three prompt builders.

### 3a. `buildObservationPrompt` (per tool call)

For each `PostToolUse` event, the observer receives:

```xml
<observed_from_primary_session>
  <what_happened>{tool_name}</what_happened>
  <occurred_at>{ISO8601}</occurred_at>
  <working_directory>{cwd}</working_directory>
  <parameters>{JSON.stringify(tool_input, null, 2)}</parameters>
  <outcome>{JSON.stringify(tool_output, null, 2)}</outcome>
</observed_from_primary_session>

Return either one or more <observation>...</observation> blocks, or an empty response if this tool use should be skipped.
Concrete debugging findings from logs, queue state, database rows, session routing, or code-path inspection count as durable discoveries and should be recorded.
Never reply with prose such as "Skipping", "No substantive tool executions", or any explanation outside XML. Non-XML text is discarded.
```

The observer is **allowed to return empty** (skip uninteresting tool calls) and **mandated** to return only XML (parser discards non-XML). This is similar in spirit to EPYC's AP-16 structured output discipline.

### 3b. What an `<observation>` looks like

From `buildInitPrompt` template (`src/sdk/prompts.ts:46-80`):

```xml
<observation>
  <type>[ bugfix | feature | decision | discovery | change | ... mode-defined ]</type>
  <title>...</title>
  <subtitle>...</subtitle>
  <facts>
    <fact>...</fact>
    <fact>...</fact>
  </facts>
  <narrative>...</narrative>
  <concepts>
    <concept>...</concept>
  </concepts>
  <files_read><file>...</file></files_read>
  <files_modified><file>...</file></files_modified>
</observation>
```

The observation type taxonomy is **mode-defined** (`plugin/modes/*.json`) — different modes (code, law-study, meme-tokens, email-investigation, translation-locale modes) redefine the `observation_types` array. This is a genuinely interesting architectural pattern: the taxonomy is data, not code. Compare to our observation categories in `research/taxonomy.yaml` which are code-coupled.

### 3c. `buildSummaryPrompt` (on Stop)

On the `Stop` hook, the observer is sent:

```
--- MODE SWITCH: PROGRESS SUMMARY ---
Do NOT output <observation> tags. This is a summary request.
...
<summary>
  <request>...</request>
  <investigated>...</investigated>
  <learned>...</learned>
  <completed>...</completed>
  <next_steps>...</next_steps>
  <notes>...</notes>
</summary>
```

with `session.last_assistant_message` appended as context. Note: **only the last assistant message is provided** — not the full conversation, not the observation stream. The summary is synthesized from prior context that the observer already accumulated via its own SDK-session state (resumed across prompts via `resume: memorySessionId`). So the observer is a persistent sidecar Claude session that accumulates context from tool observations and emits structured summaries on Stop.

**This is a different architecture than EPYC's Phase 1/2 context folding.** We compact within the main session. Claude-mem keeps a parallel observer session that is never visible to the user and is solely responsible for emitting structured records.

Strengths of their approach:
- Observer never pollutes user context
- Observer can use a cheaper model (`CLAUDE_MEM_MODEL` setting)
- Clear separation of "what happened" (observation stream) from "what to do next" (primary session)

Weaknesses:
- Doubles inference cost per tool call (one for primary, one for observer)
- Observer context can itself overflow — code at `src/services/worker/SDKAgent.ts:201-206, 253-255` handles "Prompt is too long" / "context window" by aborting, but there's no auto-compaction of the observer itself
- Quality of observations is gated entirely by the observer model's reliability, with no eval

### 3d. What is actually persisted

From `src/services/sqlite/observations/store.ts` (confirmed by schema — not fully read, but the worker types in `src/services/worker-types.ts` and the skill's documented return shape confirm):

- **NOT stored**: raw tool output, raw conversation turns
- **Stored**: the observer's structured `<observation>` XML — title, subtitle, facts[], narrative, concepts[], files_read[], files_modified[], type, timestamp, session-id, project, cwd
- **Stored in parallel**: the same observation vectorized into Chroma (see `ChromaSync`) for semantic retrieval

So "compression" is actually **lossy summarization by an observer LLM**, not token-level compression of tool outputs. This is a fundamentally different approach than our Phase 2 native compression (`scripts/utils/compress_tool_output.py`) which preserves deterministic failure-focused slices of raw tool output.

---

## 4. Claims vs Evidence

### "~10x Token Savings" — Not Methodologically Supported

The README says:
> "~10x token savings by filtering before fetching details"

The only source we could find for this claim is `plugin/skills/mem-search/SKILL.md`, which computes it as:

```
search index:     ~50-100 tokens/result
full observation: ~500-1000 tokens each
-> "10x savings by filtering before fetching"
```

This is an **arithmetic ratio of description-vs-detail sizes**, not an end-to-end token-savings measurement. It does not account for:
- Cost of the observer subprocess (which doubles tool-call input tokens)
- Cost of maintaining Chroma embeddings
- Case where the client has to call `get_observations` for most IDs (no savings)
- Compensation effect (LLM asks more follow-up queries because summaries are lossy)

The `scripts/endless-mode-token-calculator.js` simulates savings for Endless Mode, but uses a hardcoded heuristic:

```js
function estimateOriginalToolOutputSize(discoveryTokens) {
  // Conservative multiplier: 2x
  return discoveryTokens * 2;
}
```

So the "savings" are ratio-of-assumed-sizes, not measured. The docs page `docs/public/endless-mode.mdx` explicitly concedes:
> ⚠️ **Theoretical projections** — Efficiency gains not yet validated in production
> ❌ Production validation of token savings
> ❌ Performance benchmarks

**Verdict on the 10x claim**: marketing shorthand for a description/detail size ratio. Directionally plausible as a progressive-disclosure pattern, but unsupported by any controlled measurement.

### "Endless Mode Biomimetic Memory Architecture" — Mostly Marketing

The "biomimetic" label boils down to:
- Working memory = compressed observations
- Archive memory = full transcripts on disk (which is just Claude Code's default `.jsonl` transcripts — no novelty, that's existing Claude Code behavior)
- Synchronous injection = blocking `PostToolUse` hook that replaces raw output with observation

There is no biological-memory-inspired algorithm (no decay, no rehearsal, no hippocampal/cortical consolidation, no spaced repetition). Compare to our `context-folding-progressive.md` Phase 2d which adopts intake-267 (ByteRover) compound-retention scoring with decay `0.995^Δt` and maturity tiers — that is a more substantive biomimetic design than what claude-mem ships.

**Verdict on "biomimetic"**: pure marketing. The mechanism is a blocking-hook observation substitution.

### Implicit Evidence From Issue Tracker

From https://github.com/thedotmack/claude-mem/issues (141 total, both open and closed):

| Issue | Status | Relevance |
|-------|--------|-----------|
| #2048 | open | "Text queries should fall back to FTS5 when Chroma is disabled" — confirms Path 3 gap |
| #2046 | open | "chroma-mcp: No module named 'httpcore' on all query/add operations" — Chroma integration fragility |
| #2053 | open | "Generator restart guard strands pending messages with no recovery" — observation loss |
| #1868 | open **critical** | "SDK pool deadlock: idle finished and hot-restarting sessions monopolize slot cap" — observer starves |
| #1871 | open | "generateContext opens a fresh SessionStore per call" — context injection is not batched |
| #1856 | closed | "Data drift across SQLite and Chroma due to ON UPDATE CASCADE on FKs" — SQLite/Chroma desync was a known quality bug |
| #1819 | closed | "Regression: worktree observations incorrectly tagged with directory names" — taxonomy/project mis-tagging |
| Stop hook performance | open | "Stop hook blocks every assistant turn for 3-7s" — turn-time regression |

Takeaway: the system has real SQLite↔Chroma consistency issues, observer starvation under concurrency, and measurable per-turn latency overhead (3-7s per Stop). These are **operational qualifiers** that any adopter should weigh against the claimed benefits.

---

## 5. Comparison to Existing EPYC-Tracked Work

### vs intake-135 (Cognee, Apache-2.0)

Cognee is a **document-to-KG pipeline** (add → cognify → memify → search) that constructs an OWL-grounded knowledge graph from documents, with multi-backend graph+vector storage. Claude-mem is a **session-observer** that emits structured records from tool events.

| Dimension | Cognee | claude-mem |
|-----------|--------|-----------|
| Input | Documents | Tool-use events |
| Storage | Graph DB + Vector DB | SQLite + FTS5 + Chroma |
| Schema | OWL ontology | Mode-defined XML taxonomy |
| Retrieval | Graph traversal + vector | FTS5 OR Chroma (2-path cascade) |
| License | Apache-2.0 (adoptable) | AGPL-3.0 (blocking) |

Cognee is strictly more powerful and has adoption-compatible licensing. Claude-mem's only architectural edge is **lifecycle-hook-driven capture from a live coding session** — a niche Cognee doesn't cover because Cognee is stack-neutral.

### vs intake-268/269/270 (Karpathy / nvk / qmd wiki cluster)

The Karpathy LLM Wiki concept is about **persistent compiled knowledge** (LLM maintains cross-references, handles bookkeeping). The three-layer architecture (raw sources / wiki pages / schema) is about long-form knowledge curation, not session observations.

Claude-mem's `search → timeline → get_observations` 3-layer is **not the same three layers** as Karpathy's raw/wiki/schema. Claude-mem has no "wiki pages" equivalent — it has flat observation records. No cross-referencing, no contradiction detection, no orphan page handling. The Karpathy cluster is substantively richer on curation; claude-mem is richer on live capture.

intake-270 (qmd) is the closest technical comparison: it runs **local GGUF models** via `node-llama-cpp` with BM25+vector+LLM rerank for hybrid search over markdown KBs. Claude-mem requires cloud Claude (or Gemini, OpenRouter) for the observer and uses a weaker 2-path search (no rerank). qmd is strictly better-engineered for retrieval.

### vs intake-277 (Hermes LLM Wiki Skill, PR#5635)

Hermes PR#5635 is the **ingest/query/lint** pattern for a general-purpose persistent wiki. Three core operations vs claude-mem's `search/timeline/get_observations`. Hermes PR#5635 has **lint operations** (contradiction detection, orphan detection, outdated content) that claude-mem does not have at all.

We already flagged Hermes' implementation as directly adoptable (intake-277 verdict: `new_opportunity`, `adopt_patterns`). Claude-mem does not add anything the Hermes PR does not already cover — except the lifecycle-hook capture taxonomy.

### vs intake-316 (LTM Unsolved — Chrys Bader)

Bader's nine-axis design space (write triggers, storage, retrieval, curation, forgetting policy, etc.) is a framework to classify memory systems. Mapping claude-mem onto it:

| Axis | Claude-mem choice |
|------|-------------------|
| Write trigger | Every tool use (PostToolUse) + every Stop |
| Storage backend | Dual: SQLite+FTS5 (structured) + Chroma (vector) |
| Retrieval mode | Explicit (client calls search MCP tool) |
| Curation | LLM-driven (observer synthesizes records) |
| Forgetting policy | **None** — records never deleted, only `<private>`-tagged content excluded pre-write |
| Derivation | Heavy (full observer summarization, not raw) |
| Ground truth | **None** — no eval suite |
| Entity handling | Implicit via `concepts` field, no disambiguation |
| Contradiction handling | **None** — no cross-reference lint |

Against Bader's failure modes (derivation drift, entity confusion, selective retrieval bias, stale context dominance), claude-mem is vulnerable on all four:
- **Derivation drift**: observer synthesizes lossy records, no ground truth; user cannot verify what was captured correctly without the raw transcript.
- **Entity confusion**: Issue #1819 explicitly confirmed worktree tagging errors.
- **Selective retrieval bias**: Chroma query ranks by embedding similarity; no diversity-aware retrieval.
- **Stale context dominance**: no decay, no recency weighting, no importance scoring. Old observations have equal retrieval weight to new ones.

This means the intake-316 critique applies directly. Claude-mem does not solve any of LTM's unsolved problems — it chose a reasonable set of engineering tradeoffs for a shippable product.

---

## 6. Adoptable Patterns (Specific, Not Vague)

Having dug into the source, here is the refined list — sharper than the original intake's three patterns.

### A. Observer-sidecar pattern (not new to us, but this is a clean reference)

**Pattern**: Run a separate, tool-disabled LLM subprocess alongside the primary session, capture tool events, emit structured records. Subprocess gets isolated env and isolated cwd.

**Code locations** (for reference if we implement):
- `SDKAgent.ts:55-68` — disallowed-tools list for observer-only sandbox
- `SDKAgent.ts:100-101` — `sanitizeEnv(buildIsolatedEnv())` for credential isolation
- `SDKAgent.ts:130-148` — `query()` with `cwd=OBSERVER_SESSIONS_DIR` to isolate from user's project resume list

**Where this fits in EPYC**: This is an alternative to our Tier-1/Tier-2 in-session compaction. We are NOT currently running an observer sidecar — our session compaction mutates the primary session's summary. Worth flagging as a **design option** for Phase 3 of `context-folding-progressive.md` if we ever find in-session compaction is too disruptive to model attention.

**Caveat**: doubles per-tool inference cost. Only adopt if we can use a cheap local model as observer.

### B. Structured XML observation schema with mode-defined taxonomy

**Pattern**: Observation schema is six fixed fields (title/subtitle/facts/narrative/concepts/files) + a mode-defined `<type>` enum. The `plugin/modes/*.json` files parameterize prompt placeholders, type lists, and guidance text per mode.

**Adoptable piece**: The **data-driven taxonomy** — make our research-intake categories YAML-configurable per project instead of code-coupled. We have something like this in `research/taxonomy.yaml` but tighter coupling to prompts would help.

**Concrete action**: On the Phase 2 summarizer (context-folding-progressive.md), consider promoting the prompt template's observation-type list to a per-session config file rather than hardcoding in the summarizer prompt builder.

### C. Batched-ID fetch MCP tool as a progressive-disclosure enforcement point

**Pattern**: Expose a `get_observations(ids=[...])` tool that takes an explicit ID list. The SKILL.md tells Claude "NEVER fetch full details without filtering first". Because the tool requires IDs, Claude must first call `search` or `timeline` to obtain them.

**Adoptable piece**: This is genuinely a cleaner UX than our current `orchestrator-conversation-management.md` pull-model. Our current conversation-management helpers don't require a filter-first step at the tool schema level.

**Concrete action**: For `tool-output-compression.md` Phase 2b monitoring, consider adding a `peek_full_output(ids=[...])` MCP tool that enforces batched-ID retrieval of spilled outputs. The peek mechanism already exists in `helpers.py` — wrap as an MCP tool with ID-list signature to force the filter-first discipline.

### D. `<private>` tag with edge-layer stripping

**Pattern**: Users wrap sensitive content in `<private>...</private>` in prompts or tool inputs. Stripping happens at the hook-layer (`src/utils/tag-stripping.ts`) before data reaches the worker / DB / search indices. Live conversation is unaffected.

**Code details**:
- Strips 6 tag types: `<claude-mem-context>`, `<private>`, `<system_instruction>`, `<system-instruction>`, `<persisted-output>`, `<system-reminder>`
- ReDoS protection with `MAX_TAG_COUNT = 100` before regex
- Applied to tool_input, tool_output, and user prompt content

**Adoptable piece**: We do not currently have user-controlled exclusion for session-compaction. The `<private>` tag convention is trivially adoptable — add to the compaction summarizer's prompt (skip anything in `<private>...</private>`) AND strip before persisting to the session log.

**Concrete action**: Add to `context-folding-progressive.md` Phase 2d (provenance & forgetting) — pair with the existing forgetting-policy work.

### E. Stop-hook checkpoint summary with structured schema

**Pattern**: On `Stop` (turn end), emit a structured `<summary>` with six fields: `request, investigated, learned, completed, next_steps, notes`. Pass only the last assistant message as context; the observer's resumed SDK state provides the rest.

**Adoptable piece**: The **six-field summary schema** is a concrete template for our Tier-2 consolidation. Compare to our current Tier-2 prompt which is freeform dense paragraph. The structured schema might be more RL-friendly (Phase 3 FoldGRPO process rewards could key off per-field completeness).

**Concrete action**: On Phase 2a (summarizer quality) A/B test, compare current freeform Tier-2 against the claude-mem six-field schema for retention@compression.

---

## 7. AGPL-3.0 Implications

Confirmed AGPL-3.0 from `LICENSE` line 1:
> GNU AFFERO GENERAL PUBLIC LICENSE, Version 3, 19 November 2007
> Copyright (C) 2025 Alex Newman (@thedotmack). All rights reserved.

**Strict read**: vendoring any AGPL-3.0 code into EPYC (which has mixed licensing — orchestrator is internal, llama.cpp is MIT, research repo is internal) would require the entire combined work to be AGPL-3.0-licensed and source-available to any user of the orchestrator over a network (the "A" clause). This is a **non-starter** for the orchestrator repo, which we want to keep internal.

**Practical read**:
- Cannot vendor the TypeScript code, hooks, or SKILL.md files.
- Cannot link against the npm `claude-mem` package from orchestrator code.
- CAN re-implement the patterns (A-E above) in Python from scratch. Patterns are not copyrightable.
- CAN cite the structured XML schemas as prior art, since they are short prompt templates used as-is in Python — prompt text copying from an AGPL project is a grey area but very short templates are likely uncopyrightable under merger doctrine.

**Recommendation**: re-implement the A-E patterns in Python, do not vendor any code. Do not cite direct prompt strings verbatim in our own LICENSE-restrictive repos; paraphrase the observation schema. This is consistent with the intake's original "adopt_patterns, no component adoption" stance.

---

## 8. Verdict Delta

### Pre-deep-dive intake (2026-04-17)
- novelty: medium
- relevance: medium
- verdict: adopt_patterns
- three patterns flagged: 3-layer MCP search, lifecycle-hook taxonomy, `<private>` tag

### Post-deep-dive proposed delta

| Dimension | Before | After | Reason |
|-----------|--------|-------|--------|
| novelty | medium | **medium-low** | The "3-layer workflow" is a skill-file client convention over a 2-strategy cascade, not a novel retrieval architecture. Observer-sidecar is clean but not novel (Cognee, Memento, ByteRover all have observer variants). "Biomimetic" is marketing. |
| relevance | medium | **medium** (unchanged) | Five patterns (A-E) are concretely adoptable for our in-flight context-folding-progressive and tool-output-compression handoffs. Not high because we already have 80% of this work in progress; claude-mem confirms direction rather than unlocking new capability. |
| verdict | adopt_patterns | **adopt_patterns** (unchanged) | Reinforced. AGPL-3.0 confirms no component adoption. Patterns A-E are adoptable re-implementations. |
| credibility_score | null | **low-medium** | No benchmarks, no evals, known consistency bugs (#1856, #1819), known observer starvation (#1868). Token-savings claims are arithmetic ratios not measurements. Endless Mode explicitly labeled unvalidated. |

### Key insights not in the original intake

1. **The "3-layer" naming conflates two concepts**: claude-mem's 3 layers are client-side tool calls (progressive disclosure). Karpathy/Hermes 3 layers are raw/wiki/schema (curation hierarchy). These are architecturally different; the original intake linkage to intake-268 is somewhat misleading.

2. **The observer-sidecar doubles inference cost per tool call** — worth flagging explicitly as a tradeoff. Our in-session compaction is cheaper.

3. **The "biomimetic" claim is marketing** — ByteRover/intake-267 that we already track has more substantive biomimetic design (decay, maturity tiers) than claude-mem. No loss from de-prioritizing the "Endless Mode" concept.

4. **The `<private>` tag is the highest-signal pattern per line-of-code** — ~30 lines in `tag-stripping.ts`, user-facing, composable with our existing forgetting policy. Low-effort high-value adoption.

5. **Five concrete patterns (A-E) now specified** replace the original three generic ones. Patterns C (batched-ID fetch MCP tool) and E (six-field Tier-2 schema) are the most directly actionable for existing handoffs.

### Proposed handoff updates

- **`context-folding-progressive.md`**: add Phase 2a A/B candidate for six-field `<summary>` schema (pattern E); add Phase 2d entry for `<private>` tag stripping (pattern D).
- **`tool-output-compression.md`**: add Phase 4 design note for batched-ID MCP peek tool (pattern C).
- **`hermes-agent-index.md`**: no change — Hermes LLM Wiki PR#5635 already covers more ground.

---

## 9. One-line Summary

Claude-mem is a well-engineered but unvalidated Claude-Code-specific observer-sidecar memory plugin whose advertised novelty is largely marketing; five concrete sub-patterns are worth adopting into EPYC's in-flight context-folding and tool-output-compression work, but AGPL-3.0 rules out component adoption.
