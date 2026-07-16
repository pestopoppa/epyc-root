# Tool Token Optimization — Output Compression + Definition Reduction

**Status**: Phase 2 implemented (output compression); Phase 2b monitoring wired (2026-04-11); Phase 3a-c done (definition audit, compression, AP-16 runtime measurement); A/B done (+4pp REPL, suite-dependent); Phase 4a-d MCP wrapper/telemetry/registration landed; P3d fallback chain now landed in orchestrator runtime scope; P3d.5 done
**Created**: 2026-04-04 (via research intake deep dive)
**Updated**: 2026-06-28
**Categories**: context_management, agent_architecture
**Priority**: MEDIUM
**Depends on**: None (independent workstream)

---

## Objective

Reduce token consumption from tool outputs (shell commands, test runners, git operations) by 60-90% before they enter the LLM context window. This is an **upstream compression layer** — complementary to session-level context folding (which compresses conversation history) and reasoning compression (which compresses model output). Together they multiplicatively reduce context pressure.

Target environments:
1. **Autopilot sessions** (Claude API) — direct cost reduction on input tokens
2. **Local llama.cpp sessions** — extend effective context within constrained windows (8K-32K)
3. **Root-archetype** — if successful, push patterns to the shared agent archetype for all Claude Code users

---

## Existing Infrastructure (audit 2026-04-05)

The orchestrator already has two output handling mechanisms that the original handoff did not account for:

1. **`_spill_if_truncated()`** at `helpers.py:320-355` — truncates output to `max_output_preview` (1500 chars), spills full content to `/mnt/raid0/llm/tmp/` with `peek()` retrieval pointer. Feature flag `output_spill_to_file` (True in production).
2. **`truncate_output()`** at `tools/base.py:80-95` — 8192 char hard cap per tool execution.

The Phase 2 native compression module **layers before** these mechanisms: compress first, then spill if still too long. This is strictly better — a 50K pytest output compresses to ~2K (failure-focused), and spill handles the case where even 2K exceeds the 1500-char preview limit.

## Phase 2 Implementation (2026-04-05)

**Compression module**: `epyc-root/scripts/utils/compress_tool_output.py` (27 tests, all pass)

7 command handlers:
| Command | Strategy | Expected Savings |
|---------|----------|-----------------|
| pytest / python -m pytest | Failure focus — keep FAILED/ERRORS + summary | 90%+ |
| cargo test | Failure focus for Rust output | 90%+ |
| git status | Stats extraction — count by category + file list | 80-90% |
| git diff | Drop index/---/+++ boilerplate, keep changed lines | 70-80% |
| git log | Compact to hash + subject (detect already-compact) | 60-70% |
| ls | Aggregate by extension — `42 files (15 .py, 8 .ts)` | 70-80% |
| cargo build / make / tsc / gcc | Error focus — strip compilation, keep errors + context | 80-90% |

**Orchestrator integration**: Feature flag `tool_output_compression` (env `TOOL_OUTPUT_COMPRESSION`, default off). Wired at `helpers.py:1497` before `_spill_if_truncated()`.

**Claude Code hook finding**: PostToolUse hooks **cannot replace built-in tool output** (only MCP tools support `updatedMCPToolOutput`). The Claude Code hook approach from Phase 0/1 is not viable for Bash output compression. ~~Future work: wrap compression as an MCP tool~~ → **DONE (Phase 4 landed the MCP-tool wrapper `tool_output_compressor_mcp.py`)**; PreToolUse command rewriting remains an alternative.

---

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-259 | RTK — Rust Token Killer | high | worth_investigating |

### RTK Assessment (from deep dive, 2026-04-04)

**Strengths**:
- 60-90% token reduction across 100+ commands, <10ms overhead
- 12 well-documented filtering strategies (stats extraction, failure focus, tree compression, deduplication, etc.)
- 17.3k GitHub stars, active development (v0.34.3 stable, v0.35.0-rc active)
- Claude Code PreToolUse hook integration exists

**Risks (deploy-cautious)**:
- **Security**: Shell injection via `sh -c` (runner.rs), telemetry enabled by default, plaintext secrets in tracking DB, CI trust bypass — Issue #640 unresolved
- **Compensation problem**: Issue #582 reports 18% cost *increase* — compressed output forces more output tokens from LLM to compensate for missing context
- **Resource exhaustion**: EAGAIN/posix_spawn errors under heavy tool use (Issue #968) — directly relevant to autopilot workloads
- **376 open issues** including P1-critical bugs (multi-file cat, git push timeouts, broken JSON)
- **Hook scope**: Only intercepts Bash tool calls — Claude Code built-in tools (Read, Grep, Glob) bypass entirely

---

## Phase 0 — RTK Sandboxed Trial

**Objective**: Measure actual net token savings (input reduction minus output compensation) under autopilot workload.

**Steps**:
1. Install RTK binary: `curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh`
2. Configure: `RTK_TELEMETRY_DISABLED=1`, exclude sensitive commands (`curl`, `env`)
3. Run `rtk init -g --auto-patch` to install Claude Code hook
4. Execute one standard autopilot session with RTK enabled
5. Collect metrics: `rtk gain --all --format json`
6. Compare against a baseline autopilot session without RTK:
   - Input tokens (should decrease)
   - Output tokens (may increase — compensation effect)
   - Total cost
   - Task completion rate (must not regress)
   - Retry/re-run frequency (indicator of information loss)

**Go/no-go criteria**:
- Net token savings ≥ 40% (accounting for output compensation)
- No EAGAIN errors during the session
- Task completion rate within 5% of baseline
- No security incidents (secrets in logs, unexpected network calls)

**Outcome → Phase 1 or Phase 2** depending on results.

---

## Phase 1 — Deploy RTK (if Phase 0 passes go/no-go)

**Objective**: Production deployment with feature flag and monitoring.

**Steps**:
1. Add RTK binary to autopilot bootstrap (`scripts/nightshift/`)
2. Feature flag: `TOOL_OUTPUT_COMPRESSION=rtk` (values: `off`, `rtk`, `native`)
3. Configure exclusions per our security requirements
4. Add `rtk gain` metrics to autopilot session reports
5. Monitor for EAGAIN errors, cost regression, task quality

**Rollback**: `TOOL_OUTPUT_COMPRESSION=off` + `rtk init -g --uninstall`

---

## Phase 2 — Native Hook Implementation (if Phase 0 fails go/no-go, or after Phase 1 identifies RTK limitations)

**Objective**: Implement the highest-value compression strategies as native Claude Code hooks, without RTK's security surface or bug load.

### Strategy Prioritization (by our command frequency × compression ratio)

| Priority | Command | Strategy | Expected Savings | Effort |
|----------|---------|----------|-----------------|--------|
| P0 | test runners (pytest, cargo test) | Failure focus — hide passing tests, show only failures with context | 90%+ | ~100 lines |
| P0 | git status | Stats extraction — counts by status category | 80-90% | ~30 lines |
| P0 | git diff | Smart truncation — keep meaningful hunks, drop boilerplate headers | 70-80% | ~60 lines |
| P1 | git log | Stats extraction — compact format with hash + subject | 60-70% | ~20 lines |
| P1 | ls/tree | Tree compression — aggregate by directory, group by type | 70-80% | ~50 lines |
| P2 | build output (cargo build, tsc) | Error focus — strip passing compilation, show errors only | 80-90% | ~40 lines |
| P2 | linter output | Grouping by pattern — aggregate by rule/severity | 70-80% | ~40 lines |

### Implementation Architecture

Two options:

**Option A: Shell-based hooks** (lowest effort)
- One bash script per command in `scripts/hooks/tool_output_compress/`
- Register as PostToolUse hooks in Claude Code settings
- Pipe command output through the compression script
- Pro: Simple, easy to customize, no compilation
- Con: Slower than Rust, shell parsing fragility

**Option B: Python compression module** (moderate effort)
- `scripts/utils/compress_tool_output.py` with per-command handlers
- Callable from hooks or directly from autopilot infrastructure
- Can also compress outputs in orchestrator's REPL pipeline (not just Claude Code)
- Pro: Testable, reusable across autopilot and orchestrator
- Con: More infrastructure

**Recommendation**: Option B — the Python module can serve both Claude Code hooks AND the orchestrator's REPL output path (where `_spill_if_truncated()` already operates). Single implementation, two integration points.

### Root-Archetype Integration

If native compression proves valuable:
1. Extract the compression module as a standalone utility
2. Add to `agents/shared/` as a tool output processing standard
3. Document in root-archetype's operating constraints
4. Ship as a recommended hook configuration in agent bootstrap

---

## Cross-References

| Handoff | Relationship |
|---------|-------------|
| `context-folding-progressive.md` | Complementary layers: this handoff compresses tool inputs, context-folding compresses conversation accumulation |
| `reasoning-compression.md` | Complementary layers: this compresses tool outputs, reasoning-compression compresses model reasoning |
| `meta-harness-optimization.md` | RTK/native hooks could be deployed as harness optimizations in autopilot; AP-16 tracks instruction_token_ratio for Phase 3 |
| `orchestrator-conversation-management.md` | Output compression reduces what enters the conversation, easing conversation management |
| `repl-turn-efficiency.md` | Complementary: this compresses tokens per tool call, REPL turn efficiency reduces number of tool calls |

---

## Open Questions

- Does the compensation effect (Issue #582) scale with task complexity? Simple tasks may benefit from compression while complex debugging tasks may suffer.
- What's the right compression level per agent role? Architect may need full context, worker may benefit from compressed.
- Should compression be adaptive — start compressed, fall back to full on retry?
- For the orchestrator's REPL pipeline: compress before `build_root_lm_prompt()` or before `_spill_if_truncated()`?

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-273] "Context Rot"** (Chroma) — Performance degrades with input length, especially low-similarity content. Validates aggressive compression of tool outputs before context entry. Distractors (topically related but wrong content) amplify degradation — our compression should strip irrelevant tool output sections, not just truncate.
- **[intake-274] "The Complexity Trap" (arXiv:2508.21433)** — Simple observation masking (stripping old tool outputs) matches LLM summarization. 50% cost reduction, solve rates maintained. **Direct validation**: our pattern-based compression (Phase 2) is the right approach — possibly better than LLM-based compression for tool outputs. The hybrid finding (masking + summarization = 7-11% further savings) confirms our two-layer architecture (compress tool outputs first, then LLM-summarize conversation). Answers Open Question 4: compress before `_spill_if_truncated()` is correct — upstream compression is strictly better.
- **[intake-271] "Skill Issue: Harness Engineering"** (HumanLayer) — 14-22% token overhead from verbose agent instructions. Tool outputs that include explanatory framing (e.g., git status headers, pytest collection lines) are effectively "instructions" that consume attention budget without aiding task completion.

## Research Intake Update — 2026-04-09

### New Related Research
- **[intake-301] "AXI: Agent eXperience Interface"** (axi.md)
  - Relevance: TOON format achieves ~40% token savings over JSON — directly applicable as wire format for compressed tool outputs
  - Key technique: Combined operations (navigate+snapshot in single call), pre-computed aggregates (inline totals), progressive disclosure (minimal default + `--full`)
  - Reported results: 100% success, $0.074/task (lowest), 4.5 turns (most efficient) across 490 browser automation runs
  - Delta from current approach: Our Phase 2 compresses output *content*; AXI optimizes output *format*. These are complementary — apply TOON encoding after pattern-based compression for multiplicative savings. The progressive disclosure principle (minimal default, explicit `--full`) mirrors our truncation + peek() architecture.

- **[intake-302] "SkillReducer: Optimizing LLM Agent Skills for Token Efficiency"** (arXiv:2603.29919)
  - Relevance: 48% compression of tool/skill descriptions via adversarial delta debugging — applicable to our orchestrator's tool definitions
  - Key technique: Taxonomy-driven progressive disclosure separates core rules from supplementary content loaded conditionally
  - Reported results: 48% description compression, 39% body compression, +2.8% quality improvement (less-is-more)
  - Delta from current approach: We compress tool *outputs*; SkillReducer compresses tool *definitions*. Combined with AXI's output format optimization, this is a three-layer compression stack: definition → output format → output content.

---

## Phase 3 — Tool Definition Compression (SkillReducer)

**Status**: design ready
**Source**: intake-302 (SkillReducer, arXiv:2603.29919)

### Objective

Apply SkillReducer's compression principles to orchestrator tool definitions. We compress tool OUTPUTS (Phase 2) but not tool DEFINITIONS. SkillReducer reports 48% description compression, 39% body compression, +2.8% quality improvement (less-is-more effect).

### Target Surface Area

1. **`DEFAULT_ROOT_LM_TOOLS`** in `src/prompt_builders/constants.py` (~2382 words)
   - Primary tool description block injected into every REPL prompt
   - Contains 30+ tool descriptions with when-to-use / when-not-to-use patterns
   - Apply adversarial delta debugging: remove description content, measure task success, keep minimal surviving description

2. **Agent role overlays** (`orchestration/prompts/*.md`)
   - frontdoor.md, architect_investigate.md, etc.
   - Each adds role-specific instructions that could be compressed
   - AP-16 already tracks `instruction_token_ratio` — use as measurement

3. **`tool_registry.py`** tool descriptions
   - Registered tool descriptions used by `list_tools()`
   - Visible to the model at runtime

### Implementation Approach

**P3a — Audit current token cost**:
- Count tokens in each tool definition across all prompt paths
- Rank by frequency of use (from autopilot logs) * token cost
- Identify low-value descriptions (tools rarely used but consuming tokens)

**P3b — Manual compression pass**:
- Remove redundant when-NOT-to-use patterns where obvious from context
- Collapse duplicate tool entries (e.g., `web_research` appears multiple times in constants.py)
- Apply progressive disclosure: minimal description + `--help` escape hatch
- Measure `instruction_token_ratio` before/after via AP-16

**P3c — A/B test**:
- Run compressed vs original definitions on seeding harness
- Gate: quality must not regress (SkillReducer's +2.8% finding suggests it won't)

**P3d — Automated compression (future)**:
- Build adversarial delta debugging script
- Input: tool definition text + eval suite
- Output: minimal description that maintains task success

### Work Items

- [x] P3a: Token audit of tool definitions across all prompt paths — ✅ 2026-04-09. `scripts/analysis/token_audit.py` + `docs/token_audit_report.md`. DEFAULT: 841 est. tokens (647 words), 41 entries, 4 duplicates. No usage freq data (seeding diagnostics unavailable). Instruction token ratio: 29.8%.
- [x] P3b: Manual compression of `DEFAULT_ROOT_LM_TOOLS` — ✅ 2026-04-09. 55% reduction (647→290 words). Removed 4 duplicates, all "Do NOT" clauses, merged related tools, flattened sections. Old version preserved as `VERBOSE_ROOT_LM_TOOLS` for A/B. Instruction token ratio: 16.0%. 162 tests pass.
- [x] P3c: Measure `instruction_token_ratio` delta (AP-16) — ✅ 2026-06-28. Static audit now reports default tool definitions at 15.0% of tools+rules+roles, with a prompt-library proxy of 10,686 char-proxy tokens. Runtime AP-16 was repaired in `epyc-orchestrator` commit `bd627b3e`; patched v6-era trials `#1010/#1011` recorded 3,188/3,295 instruction tokens and 91.8%/92.1% instruction ratios, replacing the stale 10,748-token prompt-library charge. `docs/token_audit_report.md` now separates active PromptBuilder scaffold from full prompt-library size.
- [x] P3d: A/B test compressed vs original definitions on seeding harness ✅ 2026-07-14 — A/B done (+4pp REPL, suite-dependent), per status header.

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-395] "Claude-Mem: Persistent Memory Compression System for Claude Code"** (repo: thedotmack/claude-mem)
  - Relevance: 3-layer progressive-disclosure retrieval (search → timeline → get_observations) is a direct template for how compressed tool outputs could be queried token-efficiently.
  - Key technique: hybrid FTS5+Chroma search over AI-summarized observations; ~10x token savings claimed via batched-ID full-detail fetch only after index filtering.
  - Delta: adopt the progressive-disclosure layering pattern for tool-output retrieval surfaces; do not adopt the component (AGPL-3.0, Bun/Node).

- **[intake-397] "Open Agents — Vercel-Labs Reference App for Background Coding Agents"** (repo: vercel-labs/open-agents)
  - Relevance: durable-workflow + tool-result reconnection patterns for long-running tool invocations whose outputs should survive disconnects/compaction.
  - Key technique: Vercel Workflow SDK step persistence with stream-reconnect; explicit agent/sandbox separation so tool outputs belong to the sandbox state rather than agent context.
  - Delta: pattern-only (TS/Vercel stack); cross-ref with hermes-outer-shell's two-layer memory architecture.

- **[intake-399] "GenericAgent: minimal self-evolving autonomous agent framework"** (repo: lsdefine/GenericAgent)
  - Relevance: minimal-tool-set discipline (9 atomic tools, <30K context) as a constraint when designing compression-aware tool interfaces.
  - Key technique: dynamic tool creation via `code_run` rather than adding tool surface area; layered memory pulls reduce per-turn context inflation.
  - Delta: reinforces the design pressure toward minimal tool surfaces and lazy-loaded tool outputs.

## Research Intake Update — 2026-04-20

### New Related Research
- **[intake-414] "Token Savior Recall — 97% Token Reduction MCP Server"** (repo: mibayy/token-savior)
  - Relevance: AST-level symbol navigation replaces full-file reads (41M → 67 chars per symbol lookup); hybrid BM25+vector search with RRF fusion for memory retrieval.
  - Key technique: structural AST indexing with symbol-level granularity; three-layer progressive disclosure contract (15/60/200 tokens); backward slice (130→12 lines, -92%); content-hash staleness detection.
  - Reported results: 98% task success rate, 40% active token reduction, 85% injected char reduction, 46% wall-time reduction.
  - Delta from current approach: RRF fusion in search path is an upgrade over simpler cascade; content-hash symbol staleness for automatic invalidation when code changes is novel for the compression pipeline.

- **[intake-415] "Context Mode — Context Window Optimization for AI Coding Agents"** (repo: mksglu/context-mode)
  - Relevance: subprocess sandbox execution prevents raw tool output from entering context — the exact Phase 3 MCP tool wrapping pattern identified in this handoff.
  - Key technique: subprocess sandbox in 11 language runtimes (only stdout enters context); FTS5+BM25 with RRF and Porter stemming; intent-driven filtering (>5KB threshold → index, return relevant sections only).
  - Reported results: Playwright snapshot 56.2KB→299B (99%); GitHub issues x20: 58.9KB→1.1KB (98%); large JSON API: 7.5MB→0.9KB (99%).
  - Delta from current approach: the subprocess sandbox pattern is the workaround for the PostToolUse hook limitation identified in Phase 2. The >5KB intent-threshold gating heuristic is a practical implementation detail worth borrowing.

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-454] "hermes-agent v2026.4.23 (v0.11.0)"** (`github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23`)
  - Relevance: upstream compressor gains anti-thrashing, dedup, language-respecting collapse, and a fallback-to-main-model chain on 503/404. Directly overlaps this handoff's Phase 3+ compressor work.
  - Key technique: anti-thrashing (prevents the "compress → uncompress → compress again" oscillation we flagged in Phase 2b monitoring); language-aware collapse (preserves code-block structure in multi-language tool outputs); fallback chain so compressor failures degrade to main-model summarization instead of retry loops.
  - Delta: evaluate whether to port upstream compressor patches directly (our fork lags); the anti-thrashing logic in particular is a concrete fix for a known Phase 2b failure mode. Language-aware collapse is a natural extension to the current content-type routing.

- **[intake-450] "Venice Skills — Agent Skills for the Venice.ai API"** (`github.com/veniceai/skills`)
  - Relevance: ≤500-line SKILL.md rubric + explicit "gotchas" section — models the pattern this handoff's definition-reduction work (Phase 3a-b) is already following.
  - Delta: corroborating reference point, not a new technique. Apply to any future skill authored from compression insights.

## Phase 3d — Fallback Chain (added 2026-04-24 from intake-454 deep-dive)

Source: [`research/deep-dives/hermes-agent-v2026-4-23-release.md`](../../research/deep-dives/hermes-agent-v2026-4-23-release.md). Upstream hermes-agent v2026.4.23 ships compressor improvements that **directly close a Phase 2b oscillation failure mode** flagged in our monitoring. All work non-inference (offline fixtures sufficient for unit-level validation).

**2026-06-14 audit correction**: the local `/mnt/raid0/llm/hermes-agent` clone has no `v2026.4.23` / `v0.11.0` tag; available compression commits map mainly to `agent/context_compressor.py` history (`119bad65` prune-first, `548cedb8` role-aware summary insertion, `3e2ed18a` one-shot main-endpoint fallback). Those are context-compaction patterns, not a direct drop-in for the deterministic bash-output compressor. Current local targets are split:

- `epyc-root/scripts/utils/compress_tool_output.py` — deterministic command-output compressor used by REPL output compression and the MCP wrapper.
- `epyc-orchestrator/src/context_compression.py` — B2 history compaction cheap pre-pass; already has type-aware tool output summarization and tool-pair sanitization.
- `epyc-orchestrator/src/tool_output_compressor_mcp.py` — Claude-Code-facing MCP wrapper; Phase 4a-b now owns compressed tool result telemetry.

Do not port a model fallback chain into `compress_tool_output.py` without new evidence: that script has no model dependency by design. Use Phase 4c top-up telemetry to decide whether anti-thrashing/language-aware additions are still needed.

### Objective

Port three upstream compressor patterns into our `scripts/utils/compress_tool_output.py`:
1. **Anti-thrashing** — prevents the "compress → uncompress → re-compress" oscillation we already see in Phase 2b monitoring telemetry.
2. **Language-aware collapse** — preserves code-block structure across multi-language tool outputs (current per-content-type routing is a coarser version of this).
3. **Fallback-to-main-model chain on 503/404** — when the compressor model is unavailable, degrade to main-model summarization rather than dropping into retry loops that poison context.

### Dependency

- D — pin bump v2026.3.23 → v2026.4.23 (lives in [`hermes-agent-index.md`](hermes-agent-index.md) P2.6.1) — recommended-but-not-strict prerequisite. We can read the upstream patches directly without bumping our pin first; bumping makes side-by-side comparison easier and lets us run upstream's anti-thrashing test fixtures.

### Work Items

- [x] **3d.1 — Inspect upstream patches** — locate the v0.10.0 → v0.11.0 commits touching the compressor module in `/mnt/raid0/llm/hermes-agent`. Identify the three patterns (anti-thrashing, language-aware, fallback chain) at the function/class level. Capture upstream's test fixtures if any. (~1 h) **DONE 2026-06-14**: upstream local history maps to context-compressor commits, not a direct deterministic bash-output port; no upstream fixture should be blindly transplanted.
- [x] **3d.2 — Port anti-thrashing into `scripts/utils/compress_tool_output.py`** — minimal version: track recent compress/decompress operations on the same content hash; suppress the third operation in any A→B→A oscillation pattern within a turn. (~2 h) **DONE 2026-06-18** in `epyc-root` `ca8c338`: the deterministic compressor now keeps a bounded recent outcome history by content hash, suppresses the third flip in a recent compress → passthrough → compress pattern, and emits `*_anti_thrash_suppressed` metadata when the guard fires. GitNexus impact for `compress_tool_output_with_metadata` was LOW (`impactedCount=2`). Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py` passed; the base interpreter lacked `pytest`/`pip`/`venv`, so the worker used a direct Python smoke for the new gate.
- [x] **3d.3 — Port language-aware collapse** — extend the existing per-content-type routing with a language detector for code blocks (re-use existing fence-marker heuristics in the file); preserve fence boundaries when collapsing. (~2 h) **DONE 2026-06-27**: `scripts/utils/compress_tool_output.py` now applies a deterministic `code_fence_collapse` fallback for unknown-command outputs with oversized fenced blocks, preserving fence delimiters and language tags while replacing middle lines with language-appropriate omission markers. GitNexus impact for `compress_tool_output` was LOW (`impactedCount=1`); `compress_tool_output_with_metadata` was LOW (`impactedCount=2`). Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py`; `uv run --with pytest pytest scripts/utils/test_compress_tool_output.py -q` -> `33 passed`; `uv run --with ruff ruff check scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py` passed.
- [x] **3d.4 — Port fallback chain (503/404 → main model)** — when compressor model returns 503/404 or times out, route the input through the main model with a prompt template targeting summarization instead of compression-style condensation; cap fallback retries at 1. (~1–2 h) **DONE 2026-06-28** in `epyc-orchestrator` `a5080ecb`: the deterministic root compressor remains model-free, and the actual runtime fallback landed at `src/api/routes/chat_summarization.py::_run_two_stage_summarization`. If `llm_batch()` falls back to sequential chunk digesting and a worker digest fails with 404/503/timeout, the chunk is retried once through the synthesis/main role (`frontdoor`) before becoming a failed-section placeholder. Stats now expose `worker_fallback_role`, `worker_fallback_count`, and `worker_failure_count`. GitNexus impact was LOW for the orchestrator file (`impactedCount=6`) and LOW for `_run_two_stage_summarization` (`impactedCount=2`). Validation: `py_compile`, `ruff`, focused summarization tests (`39 passed`), adjacent chat vision/REPL/pipeline tests (`96 passed`), and API import smoke + summarization (`76 passed`).
- [x] **3d.5 — Validate against recorded oscillation transcript** — replay a saved Phase 2b monitoring transcript that exhibits the documented oscillation; confirm anti-thrashing prevents the third compression and the resulting context is correct. (~1 h, offline fixture only) **DONE 2026-06-28**: no recorded fixture existed locally, so `scripts/utils/test_compress_tool_output.py` now reconstructs the Phase 2b compress -> passthrough -> compress sequence on the same content hash and asserts the third call returns `pytest_anti_thrash_suppressed` with unchanged text/char counts. Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py`; `uv run --with pytest pytest scripts/utils/test_compress_tool_output.py -q` (`34 passed`); `ruff` unavailable on this host.

### Cross-references

- Synergizes with [`context-folding-progressive.md`](context-folding-progressive.md) Phase 3c — anti-thrashing reduces oscillation-induced false positives in their monitoring telemetry. See that handoff's Phase 3c subsection for cross-ref.
- Companion to [`hermes-agent-index.md`](hermes-agent-index.md) P2.6 (the pin bump that gives us side-by-side access to upstream patches).

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-473] "@mariozechner/pi-agent-core — Stateful TypeScript Agent Runtime"** (`github.com/badlogic/pi-mono/tree/main/packages/agent`)
  - Relevance: defines `afterToolCall` as the canonical post-execute / pre-LLM-payload hook for tool-result rewriting. This is precisely the surface our compress_tool_output work needs to live on once it generalizes beyond a single point in the pipeline. Field-replace semantics let an `afterToolCall` return only the rewritten `content` (what the LLM sees) without touching `details` (what the UI sees), or vice versa — no deep merge, no coupling to tool internals.
  - Key technique: **throw-isolation** — a throw inside an `afterToolCall` middleware becomes an error tool result for that one call only, batch continues. CHANGELOG #3084 (2026-04-17) shows this was a deliberate fix to an earlier "abort whole batch" bug. Means the compaction / fallback / language-aware-collapse logic can fail on a single output without taking down adjacent compressions in the same parallel batch — directly addresses the Phase 3d.4 "compressor 503/404 → main model" fallback story.
  - Delta from current approach: our `scripts/utils/compress_tool_output.py` is currently invoked as a single point in the pipeline. The pi-agent-core hook architecture suggests factoring it as a composable middleware that other concerns (PII redaction, secret stripping, audit metadata injection) can stack onto without knowing about each other. Pairs cleanly with the upstream hermes v0.11.0 plugin-result-transform-hook surface tracked in 3d.x — same idea, different runtime.
  - Implementation refs:
    - `agent-loop.ts:617-642` — `afterToolCall` integration with field-replace semantics and throw-isolation.
    - `types.ts:64-73` — `AfterToolCallResult` shape (`{ content?, details?, isError?, terminate? }`).
  - Deep-dive: `research/deep-dives/pi-agent-core-stateful-ts-runtime.md`

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-509] "Skills For Real Engineers — Matt Pocock's Claude Code skills collection"** (`github.com/mattpocock/skills`)
  - **Reframe (post deep-dive 2026-04-30): `/caveman` is a prose-envelope-only style rider, NOT a generic compression alternative.** It is **orthogonal to TOON, not substitutable** — TOON owns structured payloads (already shipped, ~40% measured at the encoding layer); `/caveman` operates on the model's free-form prose generation. Stack order is `caveman on prose wrapper → TOON on the embedded structured payload`. Anything this handoff compresses that is structured (tool args, JSON-shaped tool results, registry slices) belongs to TOON; `/caveman` is only a candidate for the prose envelope around it.
  - Relevance: ships **`/caveman`** — a SKILL.md prompt instructing the agent to drop filler/articles/pleasantries/hedging from its own output while preserving technical accuracy. Pocock claims ~75% token reduction (self-reported, no methodology disclosed, no public measurement protocol — anecdotal headline only). The skill is one level up from our tool-output compressors and operates at the *agent's outgoing prose* layer.
  - Key technique: pure prompt-side compression — no second-pass LLM, no compressor model dependency, no parsing, no failure modes from a 503/404 fallback. A system-prompt rider is the leanest possible compression mechanism. Genuinely different mechanism class from the compressor-model approach this handoff currently pursues (Phase 3d.x); the two are complementary on prose-only payloads.
  - Delta from current approach: nothing in this handoff currently addresses *assistant-output* prose verbosity — the entire Phase 3d focus is tool-output compression. `/caveman` raises the question of whether a sibling "prose-envelope rider" lever should land in Phase 4+, gated identically to the suggestion-injection feature flag in `repl-turn-efficiency`. **Not in scope for Phase 3d.**
  - **Critical risks (block deployment without explicit eval gates)**:
    1. **Hedge-preservation risk**: `/caveman`'s drop-list explicitly includes "hedging" alongside articles/pleasantries. For inter-model escalation/delegation/consultation flows, hedge-stripping silently turns "this might work but..." into "this work" — a downstream verifier or aggregator that compares confidence levels across models cannot tell low-confidence answers from high-confidence ones. **Lever must NOT be deployed on flows that aggregate multi-model opinions until a hedge-preservation eval (uncertainty-marker recall on a held-out set) is in place.**
    2. **Persistence-clause risk**: `/caveman`'s prompt body says **"ACTIVE EVERY RESPONSE once triggered. No revert."** Applied across an inter-model session, the consumer model permanently degrades the upstream's prose unless the protocol carries an explicit "stop caveman" reset token. Need a session-scoped (not turn-scoped) on/off contract before this can be wired into any auto-flow.
    3. **Reasoning-fidelity risk**: prompt-side style riders are known to occasionally degrade reasoning on multi-step tasks (the model "compresses" intermediate thinking it actually needed). Pocock's repo does not measure this; the auto-clarity exception in `/caveman` covers "multi-step sequences where fragment order risks misread" but the gate is non-deterministic.
  - **Minimum eval gate before deployment** (Phase 4+ work): 50 consultation traces, blind quality scoring by Q-scorer, target **≥95% baseline quality at ≥40% prose-only token reduction**, plus an explicit hedge-preservation recall eval on a held-out set with explicit uncertainty markers. Do NOT trust Pocock's 75% headline as either a target or a baseline — treat it as an upper bound only.
  - Caveat: no empirical claims with methodology (credibility_score null). Pattern adoption only — no runtime component, MIT-licensed but calibrated to TypeScript app development. Pre-deep-dive framing of `/caveman` as a generic compression alternative was overstated; the corrected framing above governs.

## Research Intake Update — 2026-05-25

### New Related Research
- **[intake-605] "Repo Prompt — context-engineering tool (CodeMaps, Context Builder)"** (repoprompt.com)
  - Relevance: CodeMaps extracts classes/functions/references into a compact structural overview — a token-reduction lever at the *input/context-assembly* layer, sibling to this handoff's tool-output compressors. Reinforces the structured-vs-prose split: structural maps (like TOON for payloads) beat shipping full file bodies.
  - Key technique: structural symbol extraction + token-budget-bounded context selection; "curate over auto-search."
  - Reported results: vendor claim ~80% token reduction (unbenchmarked, credibility null) — treat as upper bound only, same caution as the `/caveman` 75% headline.
  - Delta from current approach: input-side analogue, not a tool-output compressor; proprietary GUI so pattern-only. Overlaps intake-330 (code-review-graph, ~8.2× structural token reduction) already tracked.
  - Audit refinement: if DCP emits CodeMaps or manifests as tool/context payloads, encode them with structured fields and stable IDs rather than prose blobs. Token savings should be measured with model-calibrated token counts and downstream top-up/error rates, not vendor headline percentages.

## Research Intake Update — 2026-05-26

### New Related Research
- **[intake-609] "FastMCP — Pythonic framework for building MCP servers and clients"** (`github.com/prefecthq/fastmcp`, Apache-2.0, v3.3.1)
  - Relevance: Phase 3 of this handoff identifies "wrap compression as MCP tool" as the workaround for the PostToolUse hook limitation (PostToolUse cannot replace built-in tool output; only MCP tools support `updatedMCPToolOutput`). FastMCP is the canonical Python scaffold for that wrapper; the project already runs a live FastMCP server (`epyc-orchestrator/src/mcp_server.py`, 11 tools, stdio, vendored-v1 path via `mcp>=1.0.0`).
  - Key technique (Phase 3 requires standalone v3, NOT the vendored v1 — feature boundary verified in intake-609 `notes`):
    - **Around-style middleware** (`on_call_tool` hook with pre+post + mutate-response + short-circuit): the natural insertion point for the compressor — pre-call passes through, post-call rewrites the tool result with the compressed payload AND emits the compression-ratio + downstream-top-up-rate metrics from intake-605's audit refinement, without instrumenting each tool by hand. Vendored-v1 has NO middleware.
    - **In-memory transport / test client**: unit-test the compressor end-to-end against the real tool without subprocess overhead. Vendored-v1 path requires a stdio subprocess.
    - **Server composition**: stack the compressor next to other internal tools in one process if Phase 3 grows beyond a single endpoint.
  - Delta from current approach: replaces the Phase 3 "wrap as MCP tool" stub with a concrete framework choice. Cost: adds `fastmcp>=3` as a new top-level dep alongside the existing `mcp>=1.0.0` — OR migrate the live `src/mcp_server.py` from vendored v1 to standalone v3 at the same time (recommended in intake-609 `notes` to avoid dual-codepath drift). v2→v3 upgrade guide exists; standalone v3 is a strict superset of the vendored v1 API at the decorator surface.

## Phase 4 — MCP Tool Wrapping (unblocked 2026-05-26)

**Status**: P4a/P4b landed 2026-06-14 (`epyc-orchestrator` `fe64140`); P4c landed 2026-06-14 (`epyc-orchestrator` `5cf9d1e`); P4d landed 2026-06-14 (`epyc-orchestrator` `e346613`); P4e remains observation-gated. Resolves the Bash-output gap that PostToolUse hooks cannot close (only MCP tools support `updatedMCPToolOutput`).

### Objective

Expose the existing `scripts/utils/compress_tool_output.py` logic as an MCP tool surface so Claude Code sees compressed Bash output for the high-frequency commands enumerated in §"Strategy Prioritization" (`cargo test`, `git status/diff/log`, `ls`, `cargo build`/`make`/`tsc`/`gcc`). The orchestrator-side path that runs through `helpers.py:1497` (`TOOL_OUTPUT_COMPRESSION` flag) keeps working unchanged — Phase 4 only adds the Claude Code MCP-tool surface that Phase 2's PostToolUse hook approach could not.

### Approach

Add a new MCP server module that wraps the bash invocation as a `run_bash_compressed` tool, with an around-style middleware that runs the existing compressor on the tool result before it returns. This is intentionally a **separate FastMCP instance** from `src/mcp_server.py` (whose 11 tools are read-only introspection) — composed into the same Claude Code session via two `.mcp.json` entries, not via FastMCP server composition (the two surfaces have nothing to share at the composition layer).

### Work Items

- [x] **P4a — Bash-compressor MCP server skeleton** (~1 h). New file `epyc-orchestrator/src/tool_output_compressor_mcp.py`. Single tool `run_bash_compressed(command: str, timeout_s: int = 60, working_dir: str = "") -> str` that shells out via `subprocess.run` with the same security envelope as the existing orchestrator bash path. Uses `from fastmcp import FastMCP` (v3, already pinned in pyproject after the 2026-05-26 migration). Add module-level test (`tests/unit/test_tool_output_compressor_mcp.py`) mirroring `test_mcp_server.py`'s direct-import pattern — v3 keeps `@mcp.tool()` callable, so existing test style transfers. **DONE 2026-06-14**.
- [x] **P4b — Compressor middleware** (~2 h). Implement `CompressorMiddleware(Middleware)` with `on_call_tool(self, context, call_next)`:
  1. `result = await call_next(context)` — let the tool run.
  2. Detect content type from the command (re-use the existing routing logic in `scripts/utils/compress_tool_output.py` — import, don't duplicate).
  3. Run the compressor on `result.content` strings; rewrite the result with the compressed payload.
  4. Emit per-call telemetry (`command`, `pre_bytes`, `post_bytes`, `compression_ratio`, `compressor_strategy`) into the existing Phase 2b monitoring sink (`logs/tool_compression_monitor.jsonl`).
  Wire via `mcp.add_middleware(CompressorMiddleware())` in the module's bottom. Use the FastMCP in-memory client (`from fastmcp import Client; Client(mcp)`) for the unit-test fixture so the middleware path is exercised without spawning a stdio subprocess. **DONE 2026-06-14**: root compressor now exposes metadata (`compress_tool_output_with_metadata`); MCP middleware rewrites text content, preserves structured result content, attaches `tool_compression` metadata, and writes JSONL telemetry with env override `TOOL_COMPRESSION_MONITOR_PATH`.
- [x] **P4c — Downstream-top-up rate measurement** (~1 h). Per intake-605's audit refinement (line 373), vendor token-reduction claims must be measured by *downstream* effects, not headline %. Add a paired telemetry field `next_turn_followup_command` to the Phase 2b sink — populated by reading the next bash command in the same session journal; flag patterns that look like "re-run uncompressed for missing context" (e.g., the same command re-issued within 3 turns, or `cat`/`head`/`tail` against a file just listed). Compute weekly `top_up_rate = followups / compressed_calls` from the journal; gate any compression-strategy promotion on top_up_rate ≤ 10%. **DONE 2026-06-14** in `epyc-orchestrator` `5cf9d1e`: MCP telemetry now records `top_up_candidate`, `followup_distance`, `followup_reason`, `next_turn_followup_command`, `followup_source_command`, and `session_id`; detection covers repeated commands within three compressed calls plus `cat`/`head`/`tail` views after `ls`, including common `head`/`tail` flags. Session filtering is exact when `TOOL_COMPRESSION_SESSION_ID` is set, avoiding cross-session contamination. Added `scripts/analysis/tool_compression_topups.py` to compute the weekly JSONL `top_up_rate` and gate against `<=10%`. Validation: `py_compile`; `ruff`; `pytest` for `test_tool_output_compressor_mcp.py` + `test_tool_compression_topups.py` passed 14; empty-live-log smoke reports 0 compressed calls, gate n/a.
- [x] **P4d — `.mcp.json` registration + Claude Code smoke test** (~30 min). Add a second entry to `epyc-orchestrator/.mcp.json` alongside `orchestrator`: `bash-compressor` → `python src/tool_output_compressor_mcp.py`, stdio. Restart Claude Code, run the smoke commands from §"Strategy Prioritization" via `run_bash_compressed`, verify each returns a visibly compressed result with the expected ratio band (60-90% per the table). Gate live use on a 1-week observation window of P4c top-up-rate before defaulting any high-frequency command to the compressed surface. **DONE 2026-06-14** in `epyc-orchestrator` `e346613`: project `.mcp.json` now registers both `orchestrator` and `bash-compressor` using the repo `.venv/bin/python` and absolute script paths with `PYTHONPATH=/mnt/raid0/llm/epyc-orchestrator`. Validation: `python3 -m json.tool .mcp.json`; both FastMCP servers booted and exited cleanly on stdio EOF; in-memory `run_bash_compressed` smoke returned `git status` strategy `git_status` at ratio `0.3399`, `ls -la tests/unit` strategy `ls` at ratio `0.0012`, and a top-up smoke flagged `ls src` → `head -20 src/tool_output_compressor_mcp.py` as `file_view_after_listing`. **Root registration fix 2026-06-28**: umbrella-session `.mcp.json` now also registers `bash-compressor`; root-started Claude Code sessions were previously unable to create the P4c telemetry sink.
- [ ] **P4e — Decision gate: roll-out scope** (no time estimate; data-driven). After 1 week of P4c data, decide per-command: (i) promote to default (Claude Code agent file overlay points the model at `run_bash_compressed` for that command), (ii) keep optional, or (iii) drop. Record decisions in this handoff under a "P4e results" subsection. **2026-06-28 evidence status**: telemetry is now present but underpowered. A controlled `git status` smoke created `/mnt/raid0/llm/epyc-root/logs/tool_compression_monitor.jsonl`; the analyzer reports `compressed_calls=1`, `min_compressed_calls=100`, `rollout_decision=awaiting_minimum_observations`, and `ready_for_rollout_decision=false`. `epyc-orchestrator` now prevents one-off smoke rows from falsely producing `promote_candidate`.

### Dependencies

- Standalone `fastmcp>=3` in `epyc-orchestrator/pyproject.toml` — **LANDED 2026-05-26** alongside the `src/mcp_server.py` migration. No further dep work.
- Existing `scripts/utils/compress_tool_output.py` (Phase 2) — re-used as a library, not modified.
- Existing Phase 2b monitoring sink (`logs/tool_compression_monitor.jsonl`) — extended with new fields, schema-backward-compatible.

### Cross-references

- Phase 2 (orchestrator-side compression at `helpers.py:1497`) — Phase 4 is the **Claude-Code-facing** counterpart; the two paths are independent and can both ship.
- **Harness↔orchestrator context-management collision (2026-07-16):** a candidate *user-facing* harness (Hermes/OpenCode/ACP-speaker — NOT the dev harness) runs its OWN conversation compaction / prompt-cache mgmt / sub-agent spawning that can double-up or fight this orchestrator-side compression + `context-folding-progressive.md`. Orchestrator-side compression only pays off if the harness **cooperates** (defers to the Orch) — the concrete instance of the "layer-B needs harness cooperation ⇒ open-source harness" requirement in [`harness-selection-and-integration.md`](harness-selection-and-integration.md). Seam = the `/v1` boundary.
- Phase 3d (anti-thrashing / language-aware / fallback chain) — those patches go into `compress_tool_output.py` itself, so they automatically benefit Phase 4 once the middleware is wired.
- [`internal-kb-rag.md`](internal-kb-rag.md) — K6 was satisfied via the kb-search skill route, not an MCP tool; the v3 middleware pattern in P4b is the precedent if a future kb-search MCP variant is wanted.
- [`meta-harness-optimization.md`](meta-harness-optimization.md) HLE-1 — the per-call telemetry shape in P4b is a candidate evidence source for the "per-component harness metrics" axis if the compressor is ever scored as a harness component.
- intake-609 `notes` field — feature-boundary table behind the v1-vs-v3 decision.
