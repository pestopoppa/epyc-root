# Tool Token Optimization — Output Compression + Definition Reduction

**Status**: Phase 2 implemented (output compression); Phase 2b monitoring wired (2026-04-11); Phase 3a-c done (definition audit, compression, AP-16 runtime measurement); A/B done (+4pp REPL, suite-dependent); Phase 4a-d MCP wrapper/telemetry/registration landed; P3d fallback chain now landed in orchestrator runtime scope; P3d.5 done
**Created**: 2026-04-04 (via research intake deep dive)
**Updated**: 2026-10-06
**Categories**: context_management, agent_architecture
**Priority**: MEDIUM
**Depends on**: None (independent workstream)
**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/` (MAIN review and decision custody; KEEP-marked).

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

1. **`_spill_if_truncated()`** at `helpers.py:320-355` — truncates output to `max_output_preview` (1500 chars), spills full content to `/mnt/raid0/llm/tmp/` with `peek()` retrieval pointer. Feature flag `output_spill_to_file` (True in production). [2026-09-14: location is `src/graph/file_artifacts.py:47-73` (see the 2026-08-12 reference correction below); the effective default of `output_spill_to_file` must be re-verified — "True in production" is stale. `intake-1350#record`]
2. **`truncate_output()`** at `tools/base.py:105-120` (was `:80-95`, re-anchored 2026-09-14) — 8192 char hard cap per tool execution.

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

**Orchestrator integration**: Feature flag `tool_output_compression` (env `TOOL_OUTPUT_COMPRESSION`, default off). Wired at `helpers.py:1497` before `_spill_if_truncated()`. [2026-09-14: now `helpers.py:~700`, calls at `:727`/`:730`.]

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
| `../completed/meta-harness-optimization.md` | RTK/native hooks could be deployed as harness optimizations in autopilot; AP-16 tracks instruction_token_ratio for Phase 3 |
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

- D — pin bump v2026.3.23 → v2026.4.23 (now routed by [`user-facing-harness-index.md`](user-facing-harness-index.md)) — recommended-but-not-strict prerequisite. We can read the upstream patches directly without bumping our pin first; bumping makes side-by-side comparison easier and lets us run upstream's anti-thrashing test fixtures.

### Work Items

- [x] **3d.1 — Inspect upstream patches** — locate the v0.10.0 → v0.11.0 commits touching the compressor module in `/mnt/raid0/llm/hermes-agent`. Identify the three patterns (anti-thrashing, language-aware, fallback chain) at the function/class level. Capture upstream's test fixtures if any. (~1 h) **DONE 2026-06-14**: upstream local history maps to context-compressor commits, not a direct deterministic bash-output port; no upstream fixture should be blindly transplanted.
- [x] **3d.2 — Port anti-thrashing into `scripts/utils/compress_tool_output.py`** — minimal version: track recent compress/decompress operations on the same content hash; suppress the third operation in any A→B→A oscillation pattern within a turn. (~2 h) **DONE 2026-06-18** in `epyc-root` `ca8c338`: the deterministic compressor now keeps a bounded recent outcome history by content hash, suppresses the third flip in a recent compress → passthrough → compress pattern, and emits `*_anti_thrash_suppressed` metadata when the guard fires. GitNexus impact for `compress_tool_output_with_metadata` was LOW (`impactedCount=2`). Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py` passed; the base interpreter lacked `pytest`/`pip`/`venv`, so the worker used a direct Python smoke for the new gate.
- [x] **3d.3 — Port language-aware collapse** — extend the existing per-content-type routing with a language detector for code blocks (re-use existing fence-marker heuristics in the file); preserve fence boundaries when collapsing. (~2 h) **DONE 2026-06-27**: `scripts/utils/compress_tool_output.py` now applies a deterministic `code_fence_collapse` fallback for unknown-command outputs with oversized fenced blocks, preserving fence delimiters and language tags while replacing middle lines with language-appropriate omission markers. GitNexus impact for `compress_tool_output` was LOW (`impactedCount=1`); `compress_tool_output_with_metadata` was LOW (`impactedCount=2`). Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py`; `uv run --with pytest pytest scripts/utils/test_compress_tool_output.py -q` -> `33 passed`; `uv run --with ruff ruff check scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py` passed.
- [x] **3d.4 — Port fallback chain (503/404 → main model)** — when compressor model returns 503/404 or times out, route the input through the main model with a prompt template targeting summarization instead of compression-style condensation; cap fallback retries at 1. (~1–2 h) **DONE 2026-06-28** in `epyc-orchestrator` `a5080ecb`: the deterministic root compressor remains model-free, and the actual runtime fallback landed at `src/api/routes/chat_summarization.py::_run_two_stage_summarization`. If `llm_batch()` falls back to sequential chunk digesting and a worker digest fails with 404/503/timeout, the chunk is retried once through the synthesis/main role (`frontdoor`) before becoming a failed-section placeholder. Stats now expose `worker_fallback_role`, `worker_fallback_count`, and `worker_failure_count`. GitNexus impact was LOW for the orchestrator file (`impactedCount=6`) and LOW for `_run_two_stage_summarization` (`impactedCount=2`). Validation: `py_compile`, `ruff`, focused summarization tests (`39 passed`), adjacent chat vision/REPL/pipeline tests (`96 passed`), and API import smoke + summarization (`76 passed`).
- [x] **3d.5 — Validate against recorded oscillation transcript** — replay a saved Phase 2b monitoring transcript that exhibits the documented oscillation; confirm anti-thrashing prevents the third compression and the resulting context is correct. (~1 h, offline fixture only) **DONE 2026-06-28**: no recorded fixture existed locally, so `scripts/utils/test_compress_tool_output.py` now reconstructs the Phase 2b compress -> passthrough -> compress sequence on the same content hash and asserts the third call returns `pytest_anti_thrash_suppressed` with unchanged text/char counts. Validation: `python3 -m py_compile scripts/utils/compress_tool_output.py scripts/utils/test_compress_tool_output.py`; `uv run --with pytest pytest scripts/utils/test_compress_tool_output.py -q` (`34 passed`); `ruff` unavailable on this host.

### Cross-references

- Synergizes with [`context-folding-progressive.md`](context-folding-progressive.md) Phase 3c — anti-thrashing reduces oscillation-induced false positives in their monitoring telemetry. See that handoff's Phase 3c subsection for cross-ref.
- Companion to [`user-facing-harness-index.md`](user-facing-harness-index.md) (the pin bump that gives us side-by-side access to upstream patches).

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

**Status**: P4a/P4b landed 2026-06-14 (`epyc-orchestrator` `fe64140`); P4c landed 2026-06-14 (`epyc-orchestrator` `5cf9d1e`); P4d landed 2026-06-14 (`epyc-orchestrator` `e346613`); **P4e closed 2026-09-24: the MCP surface was DROPPED (OP-49 C), see P4e.** Resolves the Bash-output gap that PostToolUse hooks cannot close (only MCP tools support `updatedMCPToolOutput`).

### Objective

Expose the existing `scripts/utils/compress_tool_output.py` logic as an MCP tool surface so Claude Code sees compressed Bash output for the high-frequency commands enumerated in §"Strategy Prioritization" (`cargo test`, `git status/diff/log`, `ls`, `cargo build`/`make`/`tsc`/`gcc`). The orchestrator-side path that runs through `helpers.py:1497` [2026-09-14: now `~:700`] (`TOOL_OUTPUT_COMPRESSION` flag) keeps working unchanged — Phase 4 only adds the Claude Code MCP-tool surface that Phase 2's PostToolUse hook approach could not.

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
- [x] **P4e — Decision gate: roll-out scope** ✅ 2026-09-24 — **DROPPED (operator, OP-49 option C).** The
  `bash-compressor` registration was removed from both `.mcp.json` files (root and orchestrator) and from the local
  `enabledMcpjsonServers`. Reasons: zero calls in 3 months. The tool's allowlist is not read-only (`python`,
  `sed -i`, `find -exec`). It has no shell, so no pipes, and builds/bench commands aren't allowed. And every
  PreToolUse guard matches `Bash` only, so promoting it would have been a route around all 8 of them. The module
  `src/tool_output_compressor_mcp.py`, its tests and `tool_compression_topups.py` stay in the tree, unregistered.
  The compressor library and the orchestrator-side `TOOL_COMPRESSION` path are unaffected. Any future Claude Code
  output compression must go through the `Bash` tool and its hooks, not a parallel MCP shell. Original: (no time estimate; data-driven). After 1 week of P4c data, decide per-command: (i) promote to default (Claude Code agent file overlay points the model at `run_bash_compressed` for that command), (ii) keep optional, or (iii) drop. Record decisions in this handoff under a "P4e results" subsection. **2026-06-28 evidence status**: telemetry is now present but underpowered. A controlled `git status` smoke created `/mnt/raid0/llm/epyc-root/logs/tool_compression_monitor.jsonl`; the analyzer reports `compressed_calls=1`, `min_compressed_calls=100`, `rollout_decision=awaiting_minimum_observations`, and `ready_for_rollout_decision=false`. `epyc-orchestrator` now prevents one-off smoke rows from falsely producing `promote_candidate`. **2026-09-14:** `/mnt/raid0/llm/epyc-root/logs/tool_compression_monitor.jsonl` does not exist on disk (checked 2026-09-14) — the observation window is not accruing. `intake-1359#record`. **2026-09-24 root cause (UFH-07): the tool is never CALLED.** Across all 1,092 retained Claude Code transcripts (2026-08-24→09-24) there are 0 `mcp__*` tool_use blocks of any kind and 0 ToolSearch queries for the compressor; MCP tools surface as deferred tools, and no agent file or skill points a session at `run_bash_compressed`. Registration (both `.mcp.json`, `enabledMcpjsonServers`) and the write path are correct: a real FastMCP in-memory `call_tool("run_bash_compressed", {"command": "git status"})` wrote a full P4c row (all follow-up fields populated); 19/19 unit tests pass. The window cannot accrue until an agent file directs use, and doing that for every session IS option (i) — so the P4e gate is now an operator choice about how to collect the data — **OP-49** (options: direct agents to the tool, which is option (i) in effect; a tagged canary that stays out of the top-up-rate calculation; or drop the tool).

### Dependencies

- Standalone `fastmcp>=3` in `epyc-orchestrator/pyproject.toml` — **LANDED 2026-05-26** alongside the `src/mcp_server.py` migration. No further dep work.
- Existing `scripts/utils/compress_tool_output.py` (Phase 2) — re-used as a library, not modified.
- Existing Phase 2b monitoring sink (`logs/tool_compression_monitor.jsonl`) — extended with new fields, schema-backward-compatible.

### Cross-references

- Phase 2 (orchestrator-side compression at `helpers.py:1497`) — Phase 4 is the **Claude-Code-facing** counterpart; the two paths are independent and can both ship.
- **Harness↔orchestrator context-management collision (2026-07-16):** a candidate *user-facing* harness (Hermes/OpenCode/ACP-speaker — NOT the dev harness) runs its OWN conversation compaction / prompt-cache mgmt / sub-agent spawning that can double-up or fight this orchestrator-side compression + `context-folding-progressive.md`. Orchestrator-side compression only pays off if the harness **cooperates** (defers to the Orch) — the concrete instance of the "layer-B needs harness cooperation ⇒ open-source harness" requirement in [`harness-selection-and-integration.md`](harness-selection-and-integration.md). Seam = the `/v1` boundary.
- Phase 3d (anti-thrashing / language-aware / fallback chain) — those patches go into `compress_tool_output.py` itself, so they automatically benefit Phase 4 once the middleware is wired.
- [`internal-kb-rag.md`](internal-kb-rag.md) — K6 was satisfied via the kb-search skill route, not an MCP tool; the v3 middleware pattern in P4b is the precedent if a future kb-search MCP variant is wanted.
- [`meta-harness-optimization.md`](../completed/meta-harness-optimization.md) HLE-1 — the per-call telemetry shape in P4b is a candidate evidence source for the "per-component harness metrics" axis if the compressor is ever scored as a harness component.
- intake-609 `notes` field — feature-boundary table behind the v1-vs-v3 decision.

## Research Intake Update — 2026-07-21 (Phase 3d: observation-dropping beats summarization on the evidence)

- **[intake-869] "Diagnosing and Mitigating Context Rot in Long-horizon Search"** (arxiv:2606.29718; GAIR/SJTU) + `github.com/GAIR-NLP/ContextRot`
  - Relevance to Phase 3d: a seven-policy head-to-head that our evidence base (intake-273/274) could not provide. **But read the ablation, not the headline** — keep-latest alone 43.8% and plain Discard 44.6% versus keep-latest+summary 48.2% off a 35.0% ReAct baseline, i.e. dropping stale observations carries ~9pp of the 13.2pp lift and summarization contributes 3.6-4.4pp.
  - This corroborates intake-274 (The Complexity Trap) rather than contradicting it: masking matched or beat LLM summarization on SWE-bench in 4 of 5 configs on cost, with summaries causing 13-15% trajectory elongation. Two domains, same direction.
  - Second finding worth carrying: method effectiveness is **model-dependent** (isolation +19% on Qwen3.5, negative on GLM-4.7), which cautions against one global compression policy across our heterogeneous role stack — though it rests on n=2.
  - Numbers are OBSERVATION-grade (100-sample splits, no chance-corrected judge agreement, live-web contamination exposure per intake-877).

- [x] Phase 3d design input: bias the fallback chain toward cheap observation-dropping before LLM summarization, and require summarization to earn its cost in an A/B rather than assuming it. ✅ 2026-07-29 — audit resolves the ownership boundary: `compress_tool_output.py` already does deterministic observation dropping for recognized commands and fenced blocks, and deliberately has no model dependency. The only model fallback is the separate orchestrator two-stage document-summarization path, so it must not be ported into this tool-output script by analogy. Any runtime reorder needs its own telemetry-backed orchestrator task; unknown-command passthrough remains fail-safe rather than a generic lossy dropper. [intake-869, intake-274] [2026-10-20 regime caveat, `intake-2157#00`, `intake-2157#01`: dropping stale observations gains accuracy only while the model's own no-management accuracy on the task is below about 70 percent, and extra turns are paid in every regime; stratify before promoting an elision default per role. Default stays spill-only; see TOC-SP-7.]

## Research Intake Update — 2026-07-29 (the compaction-default question: verbatim log + grep vs summarize-and-compact)

_Via `/research-intake` Stage-2 2026-07-29 (intake-913…932 batch). ACM (intake-914) and PRO-LONG (intake-919) both argue for a verbatim append-only trajectory log read back by `grep`/Python in place of threshold-triggered summarize-and-compact. Every arm in both papers is a closed frontier model, so the transfer question is ours to answer. Sibling filings in [`context-folding-progressive.md`](context-folding-progressive.md) (CF-3c masking anchor, ACM Base arm, non-termination counter)._

- [ ] **First-party A/B: verbatim-append trajectory log + grep/Python read, vs current summarize-and-compact.** Run on OUR models (frontdoor Qwen3.6-35B-A3B, architect Qwen3.8-Flash-Next UD-IQ4_XS — retargeted 2026-10-28 (operator): Qwen3.5-122B deprecated). This is the transfer test neither PRO-LONG nor its antecedent offers — every arm in both is a closed frontier model. MUST report **WALL-CLOCK** (neither paper reports latency) and MUST include a **log-growth / grep-latency curve** — the axis both papers assert ("tractable for logs over 100k+ lines") and neither measures. Deterministic-replay-eligible on the scoring axis. [2026-10-20 harness-cluster pointer: see TOC-SP-7 in the "Research Intake Update — 2026-10-20 (harness cluster)" section at the end of this file.]
  - [ ] **A/B-CTRL — the nominal control arm may not exist. Resolve before scheduling any compute**
        (intake-1316#record). `context-folding-progressive.md:84` states the live path does
        deterministic type-aware stubbing only and *"no caller invokes an LLM summarizer"*. Decide
        what "current summarize-and-compact" means as a **runnable** arm, or the comparison has no
        control. Zero compute; blocks the A/B independently of any source.
  - [ ] **A/B-C — hold the context budget C explicitly EQUAL across backbones and record it in the
        artifact** (intake-1316#record). Scroll's sweep is unauditable in exactly this way, and that
        is the specific defect our A/B should be built not to have. LOCA Table 4 may be cited as a
        prior for **GLM-5.2 only** (66.7 / 62.7 at LOCA 128K/256K) with the harness caveat stated
        inline; **do NOT cite the Qwen3.6-35B-A3B row as same-harness evidence about our frontdoor
        class.** COMPUTE-GATED as a citation-bearing arm; the requirement itself is zero-compute
        design text.
  - [ ] **A/B-INSTR — LOCA-bench evaluated as a candidate suite and DECLINED** (intake-1342#record),
        five reasons: n=75 with no repetitions, so SE 4.6–5.8 pp exceeds the effect sought; answer
        cardinality confounded with the length knob; no latency axis, which this A/B requires as
        its binding output; 7 mock MCP servers / 280 tools / Docker as cost of entry;
        ground-truth-adjacency in the verifier harness. Three requirements LOCA nonetheless earns
        for OUR arms: hold C equal across arms and record it; hold ground-truth answer cardinality
        fixed while scaling the log; log trajectory length, tool-call count and tool-output tokens
        alongside accuracy so premature termination is visible as itself rather than as a wash.
  - [x] **A/B-COST** (TOC-SP-7, 2026-10-20): every elision, masking or LLM-compression arm reports compressor wall time per episode, extra model turns per task, the SUM of input tokens over all turns (rolling input tokens, not final context size), prefix-cache reuse and the number of prefix-cache invalidations (history compression versus pre-cache observation compression), and declares summary placement (top versus tail append) (`intake-2150#04`, `intake-2157#02`); when arms share tasks it also reports per-task best arm and the oracle gain over the best single arm before any router is built (`intake-2172#record`).
  - [x] **A/B-TRIG** (TOC-SP-7, 2026-10-20): record the trigger fraction against the named window denominator and run at least two fractions (0.25 and 0.5) so context rot is separable from overflow avoidance.
  - [x] **A/B-STRAT** (TOC-SP-7, 2026-10-20): report accuracy per policy arm per evidence-span stratum and per terminal_state, with eta, rho and aligned rho beside accuracy (`intake-2172#record`, `intake-2189#record`).
  - **A/B-ARMS / A/B-REL** (TOC-MP-2, TOC-MP-3, 2026-10-31): arm table with each arm's flag/config recipe and C, plus the reliability, retrieval-miss, literal-recoverability and wall-share requirements and their schema additions: [`docs/design/toc-mp-ab-design-20261031.md`](../../docs/design/toc-mp-ab-design-20261031.md).
- [x] **Prerequisite: produce a single chronological, grep-able trajectory artifact per task** — and audit which `peek`/`grep` implementation is live. [2026-09-14: the event schema must include a per-task `spill_pointer_follows` count (peek/grep events whose path matches a spill path) and a retrieval-vs-execution tool-call split — completion can stay flat while re-queries double (5/6 cells in one synthetic environment; no surge in ALFWorld). `intake-1359#01`.] [2026-10-20 harness-cluster pointer: see TOC-SP-6 in the "Research Intake Update — 2026-10-20 (harness cluster)" section at the end of this file.] ✅ 2026-10-22
  **AUDIT HALF DONE 2026-08-12 (`auditor`) — box stays open for the build half.** The live
  implementation is the FILE-CAPABLE one: standard `REPLEnvironment` → `_FileToolsMixin`
  (`file_tools.py:15,22`) → `_FileExplorationMixin`, bound into the model namespace at
  `environment.py:416` (`"peek": self._peek`). Spill pointers ARE followable today. The
  context-only `RestrictedExecutor` variant is DOUBLY dormant: `restricted_python` defaults
  False (`features.py:112`) AND `is_available()` returns False on this host (RestrictedPython
  not installed), so the import-guarded path falls back regardless. **Latent hazard worth one
  line in the build**: installing RestrictedPython and flipping the flag silently swaps in
  context-only `peek` (`restricted_executor.py:206`, no `file_path` param) and every
  `_spill_if_truncated()` pointer becomes unfollowable — the build should either port
  `file_path` into `RestrictedExecutor._peek` or make `_RestrictedREPLEnvironment` refuse
  loudly at construction while spill pointers exist.
  *Build half — the one design input it needs before code (named, routed 2026-08-12): the
  artifact's EVENT SCHEMA is owned by the A/B above (what must the grep-latency curve grep
  for — code/output/error only, or prompt + token counts per event?). Hook point is known:
  `graph/helpers.py` has `state.last_output`/`last_error`/`last_code` untruncated in hand
  before the compression/spill block (~:700); `_spill_if_truncated` fires only on truncation
  so it is NOT the seam. Wrong schema = re-run the A/B, so the requirements come first.* **The gap is NOT verbatim storage.** Our episodic memory store is *already* untruncated and recently hardened: `orchestration/repl_memory/episodic_store.py`, `memories` table, with `action` / `context` / `outcome` as plain `TEXT` columns and no truncation at the write chokepoint. What does truncate is the REPL processing journal — `src/graph/session_log.py` (`output_preview[:200]`, `error_message[:300]`, `tool_calls[:5]`) — and what is missing is any *one* chronological artifact spanning a whole trajectory that a `grep` can walk. Second half of the audit: `src/repl_environment/file_exploration.py` has file-capable `_peek`/`_grep` while `src/restricted_executor.py`'s variants are CONTEXT-ONLY (no `file_path`) — if the latter sits on a live path, the `peek(99999, file_path=…)` pointer that `_spill_if_truncated()` emits is unfollowable there.
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): `terminal_state` in {finished, context-exhausted, turn-exhausted, killed} (turn exhaustion is today only the string `[Max turns (N) reached]`, `src/graph/langgraph/nodes.py:154-158 @5d4ad2c0`; `intake-2172#record`).
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): prompt tokens and served `n_ctx` per turn.
  - 2026-10-22 (rte-toc-writers) BUILD HALF DONE (orchestrator `e9cf0949`, origin/main). `src/graph/trajectory_artifact.py` writes one append-only JSONL per task (`<ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR>/<task_id>.trajectory.jsonl`): a `turn` event per REPL turn (request_id, prompt chars, server prompt/cached/completion tokens - null when unobserved, `n_ctx` from the compiled registry, retrieval-vs-execution tool-call split, spill-ledger fields with `turn_created`/`turn_age`, `ledger_visible` size/age, `shell_compaction_seen`) and one `final` event (`terminal_state`, `terminal_reason`, `solved` = the graph's finish flag NOT a grade, rolling input tokens with observed-turn count, `prefix_cache_invalidations`, `compressor_wall_s`, `spill_pointer_follows`, `evidence_span_tokens` null, computed offline by `evidence_span_tokens_est`). Hashes, lengths, counts and spill paths only. Default OFF: runtime flag `trajectory_artifact` (declared in `orchestration/runtime_flags.spec.yaml`) AND `ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR`; hooks in `_record_session_turn`, `_make_end_result`, `_spill_if_truncated`, `_execute_turn`, all fail-silent. Flag-off proof: `tests/unit/test_trajectory_artifact.py::test_flag_off_writes_nothing_and_spill_is_byte_identical` (flag off with dir set; flag on without dir; flag on with dir: spill text identical, no file or state when off). 44 passed (prompt_layout + trajectory_artifact + output_spill), 111 with features/runtime_flags. `terminal_state` mapping: success=finished, `[Max turns`=turn-exhausted, context-overflow error=context-exhausted, anything else=killed with the bracketed reason kept.
  - [x] **TOC-WRITER-HOOKS-1 - hook `trajectory_artifact.note_history_rewrite` and `note_shell_compaction` into their producers.** Today no compression arm calls `note_history_rewrite` (so `prefix_cache_invalidations` is always 0) and no OpenCode plugin `event` handler (`session.compacted`, see TOC-SP-10) calls `note_shell_compaction` (so `shell_compaction_seen` is always false). Call the first from every path that rewrites already-sent history (session compaction / history-level compression arms) and the second from the shell-compaction signal. Acceptance: a unit test per hook showing the final-event counter moves, flag-off byte identity retained. Owner: the TOC A/B session. ✅ 2026-10-22
    - 2026-10-22 (a1-orch-code, 3c4ca599) DONE, orchestrator `9eeb7ba8` (origin/main). Producers: `note_rendered_history` (the rendered session-log block, i.e. summary refresh / two-level consolidation; a non-append-only change counts one `prefix_cache_invalidations`) called where `_execute_turn` renders it, and escalation compression that changes the prompt. Session compaction is deliberately NOT a producer: it rewrites `TaskState.context`, never rendered into a prompt (UFH14-B1), so counting it would inflate the field. Shell compaction: control-only `/v1` packet `x_session_compacted` (answered before prompt parsing, no inference) -> `note_shell_compaction_session`, applied to every task bound to the session via `bind_session` (repl_executor) and to later ones; the OpenCode plugin `event` hook forwards `session.compacted` (root `harness/opencode-plugin`, node tests 100 pass / 6 skip). Caveat: `/v1` turns that do not run the graph produce no trajectory, so the mark lands only on graph tasks sharing the session id. Tests `tests/unit/test_trajectory_artifact.py` 22 (21 pass, 1 pre-existing skip: root toc_ab carrier path); flag off = no-op, byte identity kept.
  - [x] **TOC-WRITER-TOOLCALLS-1 - pass `tool_calls` on error turns so the retrieval/execution split is not undercounted.** `trajectory_artifact.note_turn` takes the tool-call names that `_record_session_turn` is given; the error-path callers in `src/graph/helpers.py` pass none, so retrieval/execution totals undercount on error turns. Pass `_get_exploration_tool_calls(...)` (baseline-diffed) at the error-path call sites. Acceptance: a test with an error turn that peeked, showing `retrieval` counted. Owner: the TOC A/B session. ✅ 2026-10-22
    - 2026-10-22 (a1-orch-code, 3c4ca599) DONE, orchestrator `9eeb7ba8`. The two post-execution nudge paths in `src/graph/helpers.py` (input() error turn, rejected status FINAL) pass the baseline-diffed `_get_exploration_tool_calls(...)` to the trajectory artifact only (new `trajectory_tool_calls` kwarg of `_record_session_turn`, None unless the artifact is on). The session-log record is NOT given them because its `tools:[...]` renders into the session-summary prompt block, so prompt bytes stay identical. Test: an error turn that peeked counts `retrieval`=1 while the session-log record keeps `tool_calls=[]`.
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): spill-ledger fields (chars, lines, turn created, turn age at each follow, whether any size or age ledger was visible to the model at that turn; `intake-2151#00`, `intake-2151#01`).
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): the trajectory-only evidence-span covariate (tokens between the first and last tool results the answer needs; `intake-2189#record`).
  - [x] Trajectory-artifact schema field (harness-cluster, 2026-10-20): a request id that joins each event to the inference tap so cost fields can be joined.
  - Trajectory-artifact schema field (TOC-SP-10, 2026-10-21; design text, the writer stays the line-477 box): `shell_compaction_seen` (boolean, per task, default `false`; set `true` for the rest of the trajectory once the harness reports that it compacted the session itself, so double compaction by the shell and by our policy is separable from our policy alone; `intake-1011#record`). Source event, verified against OpenCode pin `350c726a`: `session.compacted` is a bus event (`packages/schema/src/session-compaction-event.ts`, payload `{sessionID}`), published once per completed compaction (`packages/opencode/src/session/compaction.ts:554`, only when the compaction result is `continue`), and delivered to a plugin through the generic `event` hook (`packages/plugin/src/index.ts:224`, dispatched at `packages/opencode/src/plugin/index.ts:259`); there is no hook literally named `session.compacted`, so the template's premise is corrected: subscribe in the plugin's `event` handler and match `event.type === "session.compacted"`. The distinct pre-compaction hook is `experimental.session.compacting` (`plugin/src/index.ts:305`); it fires before the summary is written and is not the signal. Only the harness-side flag is verified at the pin; nothing was run.
  - [x] **VB-TOC-AB-WRITE producer call (owed, filed 2026-10-21):** the trajectory-artifact writer calls `scripts/vidya/adapters/toc_ab.write_belief_measurements(out_dir, run_id=..., producer=..., trajectory_path=..., arms=...)` at its finalize boundary, before the first compression A/B run; carrier and reader landed in root `7335da327`. ✅ 2026-10-29 (audit: orchestrator e9cf0949 (2026-10-21, on origin/main) TOC-SP-6 writer + toc_ab sidecar; scripts/benchmark/toc_ab_sidecar.py:100-103 calls write_belief_measurements at finalize; handoffs commit 9f8082a9e) [no-belief: audit-reconciliation]
- [ ] Instrument **TOTAL** tokens per episode (not peak) in any compression A/B. **REOPENED 2026-09-16** (the closure below is false). ~~✅ 2026-07-29~~ — `src/graph/session_log.py` now accepts optional observed `input_tokens` / `output_tokens` per turn and aggregates episode `total_input_tokens`, `total_output_tokens`, `total_tokens`, and `token_observed_turns`. Missing usage stays explicit (`None` / observed-turn denominator), never silently zero; generated session logs expose per-turn totals when present. Focused suite `tests/unit/test_session_log.py` 52 passed. This is a telemetry primitive only; the first-party A/B remains open and any result is observation-grade until protocolled. ACM reports peak only while raising tool calls 1.6-2.4×, plus a summarizer call per compression and a full-archive-ingesting querier call per retrieval. On a prefill-bound CPU host, flatter peaks at 2× the calls may be a net throughput LOSS. [2026-10-20 harness-cluster pointer: see TOC-SP-7 in the "Research Intake Update — 2026-10-20 (harness cluster)" section at the end of this file.]
  - **Reopen note 2026-09-16 (sub-closure-fix, `closure_audit.py --strict-idents` sweep):** the claimed session-log token totals **exist on no ref**. Orchestrator `origin/main` @ `88a2902d` `src/graph/session_log.py` has no per-turn `input_tokens`/`output_tokens` and no `total_input_tokens`/`total_output_tokens`/`total_tokens`/`token_observed_turns` aggregation; `tests/unit/test_session_log.py` has no such test. `git log --all -G` over `src/graph/` and that test file finds no commit on any branch that ever added them. The tick arrived in root `08e9d60d` (2026-07-29), the same "2026-07-29" codex-lane closure wave as RC-9/E1a. Evidence: `progress/2026-09/2026-09-16-sub-closure-fix.md`. The total-token telemetry primitive is still needed before any compression A/B.
- [ ] Map `query_memory` onto the existing `_spill_if_truncated()` pointer machinery. VERIFIED: ACM's memory needs NO embedding model, NO vector index, NO chunking — verbatim JSON archived by integer key, read back via one LLM recall call. This is a read API over spill pointers we already write (`helpers.py:320-355`).
  **SCOPED 2026-07-29 (`auditor`) — machinery verified, one MISMATCH to resolve before implementing, and
  the row's code reference is wrong.**
  *Reference correction:* `_spill_if_truncated` lives at **`src/graph/file_artifacts.py:47-73`**, not
  `helpers.py:320-355` — helpers.py only re-exports it (`:39-42`) and calls it (`:727`, `:730`);
  `helpers.py:320-355` is unrelated `<<<TOOL_OUTPUT>>>` block-matching code.
  *What the pointer machinery actually is:* the full text is written to
  `/mnt/raid0/llm/tmp/{safe_task_id}_{label}_t{turn}.txt` and the model is handed a pointer string
  `[... N chars truncated; full {label}: peek(99999, file_path="…")]`. So the archive is keyed by the
  **triple (task_id, label, turn), encoded as a filesystem path**.
  *THE MISMATCH:* ACM's model — and this row's own wording — is *"verbatim JSON archived by **integer
  key**"*. The existing spill has no integer key and no index; the path IS the key. So `query_memory`
  cannot be a thin read over what is already written. It needs one of:
  (a) a per-task manifest mapping `int -> spill path` written at spill time (smallest change, keeps
  the path as truth); (b) renaming spills to a monotonic integer per task (breaks the existing
  `peek(...)` pointers already in transcripts); or (c) `query_memory(task_id, label, turn)` — no
  integer key at all, matching what exists and dropping ACM's key convention.
  **(a) is recommended:** it adds an index without invalidating any pointer already emitted, and the
  spill write is the only place that needs to change.
  *Left unimplemented deliberately:* this is a new agent-facing read API, not a fix — it wants the key
  decision above made first, and a design that adds an index is a different-sized change from the
  "thin read API" the row assumes.

## Research Intake Update — 2026-09-14 (intake-1346…1366)
_Via /research-intake Stage-4 (operator-approved plan 2026-09-14). Sources: intake-1350 SoL-Pi, intake-1357 act-context, intake-1359 compression interaction costs, intake-1365 SWEzze — all dive-verified._

**STANDING (2026-09-14):** never LLM-summarise code-bearing tool output that feeds an edit; prefer verbatim slicing/masking. Summaries answered 4/45 behavioural questions vs 27/45 for source `intake-1357#03`; token-level compression (LLMLingua-2 ~3x) was −7…+6 instances vs full context `intake-1365#02`.

- [x] **TOC-SP-1 — Spill footer calls `peek`/`grep` with arguments in the wrong order.** ✅ 2026-09-14 — merged to epyc-orchestrator main `35b05fde` (pushed to origin 2026-09-14) (commit `1e2a6315`). `environment.py:650` emitted `peek("{path}")` / `grep("{path}", pattern)` but the signatures are `_peek(n, file_path)` / `_grep(pattern, file_path)` — the pointer never read the file. Footer now `peek(2000, file_path=...)` / `grep("<pattern>", file_path=...)`; the same bug in `suggestions.py` hint templates (flag `REPL_SUGGESTIONS`) fixed too; test executes the footer calls against a real spill. `intake-1350#record`.
- [x] **TOC-SP-2 — Exact recall for spilled output.** Add offset/length paging to `peek` (reads only `f.read(n)` from byte 0, `file_exploration.py:58-94`), a tail excerpt to `_spill_if_truncated` (head-only, `file_artifacts.py:63-70`), and content-hash spill names (currently `{task}_{label}_t{turn}` opened "w"). Pattern: SoL-Pi ObservationPack handle + exact paged recall. `intake-1350#02`. ✅ 2026-09-16
  - Evidence: epyc-orchestrator branch `sub/tooling-orch-20260916`, commit `af89c864`, integrated by orchestrator merge `370dc715` (pushed in `753343f5`, 2026-09-16).
    - `peek(n, file_path=None, offset=0)` pages by character offset; a negative offset counts from the end. It reads with `newline=""`, so CR/CRLF offsets are exact. At offset 0 the behaviour is unchanged.
    - `_spill_if_truncated` now returns head + tail, with an executable `peek(<omitted>, file_path=..., offset=<head_len>)` marker between them. The result stays within `max_chars`.
    - Spill names are `{task}_{label}_{sha256[:16]}.txt`, written atomically and never overwritten. Legacy `_t{turn}` files are untouched.
  - Tests: `tests/unit/test_output_spill.py`, 13 tests. They cover exact span recall via `REPLEnvironment.execute`, a verbatim legacy `peek(99999, file_path="…_t3.txt")` pointer still resolving, and paging round-trips. Combined with the peek and spill suites, 50/50 pass. GitNexus impact on `_spill_if_truncated` is LOW.
  - Not changed: the `root_lm_system.txt` peek doc (a prompt change, so left for the owner).
- [ ] **TOC-SP-3 — Verified-quote receipt for the spill worker summary.** `_spill_output` (`environment.py:746-838 @5d4ad2c0`; synchronous `role="worker"`, `n_tokens=512` `llm_call` at :818-824) summarises only the last 4,000 chars and accepts it unverified. Replace with quotes byte-verified against the full spill, exit-status agreement, failure evidence required inside quote content (stricter than SoL-Pi's label-only check), fail-open to head/tail; the summary is also accepted only if it is non-empty and shorter than the span it summarises (a cheap safety net, nearly vacuous at the 8,192-char spill threshold). Measure evidence retention vs the current summary on real failing test logs (inference), one shared failing-log set with REPL-EMB-3.1/3.2, as contrastive pairs (same task, raw spill readable vs summary only; keep tasks where the raw run succeeds and the summary run fails) and classify each loss as missing critical fact, lost variable or state, incorrect summary, unnecessary re-discovery or token truncation (`intake-2150#00`). Arms: current summary, verified-quote summary, a deterministic no-LLM shape header (JSON/CSV keys and row counts, code symbol list, test-log failure lines; replay-eligible and consistent with the standing rule against LLM-summarising edit-bearing output; `intake-2152#02`), and a placeholder-plus-pointer arm with no summary (`intake-2157#04`). Zero-compute preparation already done: the current prompts lack identifier/path/value retention, the task instruction as input, errors-only-if-they-inform-avoidance and a fixed state structure relative to ACON's optimized guideline (`intake-2150#record`); do not adopt ACON's credential-truncation rule (redaction is TOC-RD-1). `intake-1350#03`.
- [x] **TOC-RD-1 — Redact before compressing.** ✅ 2026-09-14 — merged to epyc-orchestrator main `35b05fde` (pushed to origin 2026-09-14) (commit `118b65e5`). `tool_output_compressor_mcp.py` returned output without redaction; now `redact_if_enabled` runs on raw text before compression, on the returned text, and inside direct `run_bash_compressed` calls (after the 200k cap). The `redaction.py` PEM rule now also redacts from an unterminated BEGIN header to end-of-text (terminated keys unchanged). Note: an unterminated key redacts everything after it, by design. New PEM tests live in `tests/unit/test_credential_redaction_truncated_pem.py` because the root `pii_precommit.sh` hook blocks edits to the existing credential test file.
  - [x] **TOC-RD-1a — PII pre-commit hook gaps (root `scripts/hooks/pii_precommit.sh`).** ✅ 2026-10-06 — ED25519 recognition is complete under NI07-31. Operator chose 1B: retain scanning of both credential-redaction fixture files; the proposed two global whole-file exclusions are rejected and unapplied. This closes the remaining operator-choice deliverable, not fixture editability. Exact source/content/custody guidance for any future concrete fixture edit is in the [resolved decision](../../docs/reference/credential-fixture-hook-decision.md); no exception is authorized. `intake-1350#record`.
  - [ ] **TOC-RD-1b — PII hook over-blocks perf sample periods in markdown table cells** (filed 2026-09-24,
    main-ak-seat). Committing research `ce5800cb`'s fixture (`loop/fixtures/ds41-run8-planner-prompt.txt`, a real
    DS41 planner prompt) tripped the `account_number` rule (`\b[0-9]{12,19}\b`) on 12-13-digit `perf` sample periods
    in 7 markdown table cells. The author redacted them. The committed bytes therefore differ from the real prompt. Inline
    mode's byte-for-byte fidelity was shown against the copy recovered from the opencode store (sha equal to the call
    record's), not against the committed fixture. Candidate exemption: a digit run in a `|`-delimited cell whose column header or row
    names a perf field (`Period`, `Samples`, `period`), with no account/card/customer/iban/routing/ssn token on the
    line — the same guard the config exemption uses.
    - Add a must-block negative-control fixture row (an account number in a markdown table) in the SAME change.
      `reviewer-calibration-accounting.md` flags this exemption surface for being tuned on its own over-blocks.
    - Do not change the hook outside that reviewed change. Acceptance: the unredacted fixture commits, and the
      negative control still blocks.
    - **Recurred 2026-09-25 (research `135b8492`).** The hook redacted 7 period cells in each of the two committed
      OAB-9 bundle `INDEX.md` copies (`artifacts/autokernel_ctx_ab_20260925/bundle-manifests/`). This time it
      rewrote the files in place, with `[period redacted]`, rather than blocking. So evidence copies silently
      stop being byte-exact, and the artifact README has to say so. Same exemption shape, second instance.

- [x] **TOC-RD-1B-SRC — implement and verify the exact observed-periods cell selector.** ✅ 2026-10-06 — [MAIN source/native acceptance](../../artifacts/ni08/pii-period-source-20261006/README.md), staged synthetic73/73 with same-table account/secret refusal and full compatibility controls. Parent historical unredacted-fixture acceptance remains open; no whole-file exemption or historical reconstruction.

- [x] **TOC-RD-1a-NI-ED25519 — staged header recognition child.** ✅ 2026-10-06 — ROOT staged-blob scanner recognizes ED25519 while retaining RSA/OPENSSH; source/recipe promoted eb870f0fe697f02f887bedecaeaccaf24df2d531; native run 37474797195 TRUE9/9. This closes only the implementation child. Parent TOC-RD-1a is resolved by operator choice 1B: both fixture files remain scanned, with no whole-file exemption applied.

[Resolved scanner decision and narrower preparation guidance](../../docs/reference/credential-fixture-hook-decision.md); the rejected exact patch remains unchanged historical evidence.


### Prospective bounded spill-summary request correction — 2026-10-07

- [x] **TOC-SP-4 — bound the rolling spill-summary request context.** ✅ 2026-10-07 — [MAIN original and product acceptance](../../artifacts/ni08/ufh12-spill-summary-source-acceptance-20261007/README.md). APP source `63399d6` is published as product `8108452` (exact two-file bytes); the 4,000-character request budget includes labels, bounded previous summary and at least one new-tail character. Whole15 mocked-worker/owned-spill controls passed in original hosted run `37664607006` at ROOT recipe `533d649`, with the complete eager source/config/readset and 52 locked packages/714 wheel hashes. Original NULL `37649822725` (pytest missing) and NULL `37659831973` (langgraph missing) remain separate. This closes request-size source conformance only; TOC-SP-3 quote verification, summary correctness/evidence retention, inference, runtime and deployment remain open. Native companion: VB-NI08-UFH12-SPILL-SUMMARY-CONTEXT-BUDGET.

Source/native recipe custody remains retained under /mnt/raid0/llm/tmp/ni08_remaining_backlog_screen-20261007/; MAIN applies checklists only after review of original source/read/result/error evidence.

## Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- [ ] **TOC-SP-5 — Decide the 1991-L1/L2 gates on the one standing per-turn corpus, or record each blocked on the trajectory-artifact build (read-only, zero inference).** Over `data/bep_sandbox` (62 trajectories, coder_escalation, 5 tasks x 2 arms; the only per-turn corpus, MF-VBS-1) compute: (a) per served role and its named window denominator (65,536 per slot on :8070; on :8083 the per-request cap 262,144 inside the shared 393,216 pool, the 98,304 figure is historical) the share of trajectories whose peak prompt exceeds 0.50, 0.60 and 0.85 of the window (`intake-1991#01`, `intake-2153#00`); (b) the spill-pointer follow rate per task (peek or grep by spill path), stratified by spill-size decile with follows-per-spill, plus re-reads and re-runs of the same path or command after an elision (`intake-1991#02`, `intake-2151#04`, `intake-2157#04`). Predeclared rule (Stage-3 proposal): a metric the corpus cannot compute is recorded 'blocked on the TOC-SP-6 artifact build'; if under 10 percent of trajectories exceed 0.60 of the window at a role, the CF-AB-1 compaction arms are skipped for that role; if under 10 percent of tasks ever dereference a spill pointer, the `query_memory` row (line 498) stops at the stub-with-rerun-hint form. Denominator: all 62 trajectories, unparsable ones counted. 62 trajectories cannot support a population claim; the result gates arms and a schema decision only. Record a dated result note under this task.
  - 2026-10-21 (noninf-toc; read-only, zero inference) PARTIAL, not ticked. Corpus `data/bep_sandbox/**/traces/*.jsonl`: 62 trajectories, 0 unparsable, 384 turns; roles `coder_escalation` (59 trajectories) and `architect_coding`+`coder_escalation` (3). (a) The corpus records no prompt tokens and no served n_ctx, only `prompt_chars` and on 162 of 384 turns; 26 of 62 trajectories carry it on every turn, 36 on none. Because tokens cannot exceed characters, a trajectory whose largest `prompt_chars` is below 0.50 x window cannot exceed 0.50 of that window: the largest value over the 26 covered trajectories is 12,649 chars, below 0.50 x 65,536 = 32,768, so none of those 26 exceeds 0.50, 0.60 or 0.85 of the :8070 per-slot window (nor of the 262,144 per-request cap on :8083). The other 36 trajectories (denominator is all 62) are recorded 'blocked on the TOC-SP-6 artifact build' (no per-turn prompt tokens). The share-above-0.60 rule (under 10 percent skips CF-AB-1 compaction arms) therefore cannot be decided at any role from this corpus; role-to-window mapping for `architect_coding` was not resolved. (b) Spill-pointer follow rate: blocked/undefined. 0 turns carry a spill header in `prompt_tail` and 0 turns reference a spill path in `raw_output`/`extracted_code`; the tasks never spilled, so there are no spills to follow and 'under 10 percent dereference' would be vacuous. The `query_memory` stop rule is NOT triggered by this. Re-run once the TOC-SP-6/line-477 artifact exists.
  - 2026-10-22 (rte-toc-writers): stays OPEN. The trajectory-artifact writer landed (orchestrator `e9cf0949`, default off) but no run has emitted artifacts yet, so the read-only (a)/(b) computation has nothing to read. Re-run it over the first A/B run's artifacts (`final.rolling_input_tokens`, per-turn `prompt_tokens`/`n_ctx`, `spill_follows`); the previously 'blocked on the TOC-SP-6 artifact build' metrics become computable then.
- [x] **TOC-SP-6 — Extend the UFH-07 trajectory-artifact event schema (the open prerequisite box at line 477) with the fields the harness-cluster dives need (design text; the writer stays the line-477 box).** Add as sub-bullets: `terminal_state` in {finished, context-exhausted, turn-exhausted, killed} (turn exhaustion is today only the string `[Max turns (N) reached]`, `src/graph/langgraph/nodes.py:154-158 @5d4ad2c0`; `intake-2172#record`); prompt tokens and served `n_ctx` per turn; spill-ledger fields (chars, lines, turn created, turn age at each follow, whether any size or age ledger was visible to the model at that turn; `intake-2151#00`, `intake-2151#01`); the trajectory-only evidence-span covariate (tokens between the first and last tool results the answer needs; `intake-2189#record`); and a request id that joins each event to the inference tap so cost fields can be joined. ✅ 2026-10-20
- [x] **TOC-SP-7 — Amend the compression A/B requirements: children A/B-COST, A/B-TRIG, A/B-STRAT under the first-party A/B box (line 456), and the Phase 3d regime caveat on line 450.** A/B-COST: every elision, masking or LLM-compression arm reports compressor wall time per episode, extra model turns per task, the SUM of input tokens over all turns (rolling input tokens, not final context size), prefix-cache reuse and the number of prefix-cache invalidations (history compression versus pre-cache observation compression), and declares summary placement (top versus tail append) (`intake-2150#04`, `intake-2157#02`); when arms share tasks it also reports per-task best arm and the oracle gain over the best single arm before any router is built (`intake-2172#record`); add a one-line pointer on line 496. A/B-TRIG: record the trigger fraction against the named window denominator and run at least two fractions (0.25 and 0.5) so context rot is separable from overflow avoidance. A/B-STRAT: report accuracy per policy arm per evidence-span stratum and per terminal_state, with eta, rho and aligned rho beside accuracy (`intake-2172#record`, `intake-2189#record`). Phase 3d annotation, in place and without unticking: regime caveat (`intake-2157#00`, `intake-2157#01`), the masking gain collapses above about 70 percent no-management accuracy and extra turns are paid in every regime, so stratify before promoting any elision default per role; the default stays spill-only and any non-default policy per role carries a stratified A/B result before it is declared as per-role registry data (precedent: `COMPACTION_PROFILES`, `src/graph/session_log.py:501-559 @5d4ad2c0`). ✅ 2026-10-20
- [x] **TOC-SP-8 — Error-bearing output is never LLM-summarised or aged out in the REPL spill path (implement behind a default-off flag).** Today `_spill_output` is purely length-triggered and summarises an error-bearing stdout/[STDERR] over 8,192 chars exactly like a success, while the prompt-build path truncates errors harder than outputs (500 versus 1,500 chars, `graph/helpers.py:1200-1205 @5d4ad2c0`) and `scripts/utils/compress_tool_output.py:52-125` keys on the command string only; the only exemption is the default-off `/v1` folding path (`src/context_compression.py:203-235`, substring match). Implement: output with a non-zero exit, a traceback marker or a [STDERR] segment keeps head+tail with the executable peek marker and is never worker-summarised; unit tests in `tests/unit/test_output_spill.py` for success/error parity, flag-off byte identity and the 500-char error budget; the error definition is taken from the structured `ExecutionResult.error` plus a [STDERR] marker check. Evidence: masking error outputs raised the open-error rate (`intake-2157#04`). No activation; activation belongs to the CF-AB-1 A/B.
  - 2026-10-21 (noninf-toc) code done, not ticked. epyc-orchestrator `af8ac62f` (lane noninf-toc-20261021): `_spill_output(output, error=None)` in `src/repl_environment/environment.py`; flag `ORCHESTRATOR_REPL_SPILL_ERROR_PRESERVE=1` (default off, read per call). Error-bearing = structured `error` argument, `[STDERR]` marker, `Traceback (most recent call last)` line, or a `[exit code: N]` line with N>0. Such output is spilled in full, returns header + first 300 + last 200 chars (500-char budget) + executable `peek(2000, file_path=...)` footer, and never calls the worker. Tests in `tests/unit/test_output_spill.py::TestSpillErrorPreserve` (success/error parity, kwarg, flag-off still summarises, 300-char head) plus the existing `tests/unit/test_repl_spill_output.py`: 32 passed. Follow-up (main-approved): with the flag on, `execute()`'s exception text over `output_cap` is routed through `_spill_output(..., error=...)` (`_error_text_for_result`); flag off and under-cap text are byte-identical (exact-string tests); 40 passed across the three test files. No activation. ✅ 2026-10-21
- [x] **TOC-SP-9 — Draft a result-equality repeat-notice guard as a default-off, separable REPL-loop arm.** Baseline: the call-agnostic no-progress guard `ORCHESTRATOR_REPL_LOOP_GUARD` (`graph/helpers.py:296-322, 1255-1262 @5d4ad2c0`, default off; it counts turns without `file_write_safe` or `FINAL(` and is explicitly not identical-match); there is no repeated-error or read-without-edit detector. Design: key = (action sha256, observation hash or exit+output hash, file revision+range); deliver one factual notice per evidence key after a quiet period (through turn 10); the text calls it a repeat notice and states it does not establish stalled progress; a terminate rule only after an identical failing streak (5 for reminder and 8 for terminate are the published hypothesis with no efficacy evidence, `intake-1991#record`); the notice is measured apart from view shortening (`intake-2153#02`). Fixtures: identical call with a different result, identical result with a different file revision, quiet period, flag-off identity. Draft and fixtures only; no activation.
  - 2026-10-21 (noninf-toc) draft and fixtures done, not ticked. epyc-orchestrator `af8ac62f`: new unwired `src/graph/repeat_notice.py` (`RepeatNoticeGuard`, flag `ORCHESTRATOR_REPL_REPEAT_NOTICE`, default off, separate from `ORCHESTRATOR_REPL_LOOP_GUARD`); key = (action sha256, exit+output sha256, file revision, range); one factual notice per key after the quiet period (no notice through turn 10); text says it does not establish stalled progress; reminder at 5 and terminate at 8 identical failing turns (hypothesis constants). `tests/unit/test_repeat_notice.py`: 6 passed (different result, different file revision/range, exit status, quiet period + one-per-key, terminate streak, flag default). Flag-off identity holds trivially: nothing imports the module. Interpretation of "quiet period (through turn 10)": no notice is delivered through turn 10 (accepted by main). Draft only, default off, unwired. ✅ 2026-10-21
- [x] **TOC-SP-10 — Add `shell_compaction_seen` to the trajectory event schema.** Add a boolean `shell_compaction_seen` to the trajectory-artifact event schema, populated from the OpenCode plugin hook `session.compacted` once the event name is verified against the audited OpenCode pin `350c726a` (the premise is read only from a template), so double compaction is observable (intake-1011#record). Acceptance: the field is in the schema and the event name is verified or the task records the pin check failed. Estimate: 0.3 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): field filed as design text under the trajectory-artifact schema list (below the request-id field). Event name verified at OpenCode pin `350c726a`: `session.compacted` is a bus event (`packages/schema/src/session-compaction-event.ts`, published `compaction.ts:554`), delivered via the plugin `event` hook (`plugin/src/index.ts:224`, dispatched `opencode/src/plugin/index.ts:259`); no hook is literally named `session.compacted`. Nothing run.
- [x] **TOC-SP-11 — External-corpus cross-check for the TOC-SP-5 window-binding gate (column-only read).** Read only the top-level columns (harness, benchmark, models, status, success, steps, max_tokens) of the 12 v2 parquet files of the public Exgentic traces dataset by column projection (no message bodies), first confirming the definition of max_tokens in the dataset build script, then report per benchmark and harness the share of runs whose max_tokens exceeds 0.60 and 0.85 of 65,536 and of 262,144, beside the 62-trajectory corpus result (intake-2303#record). Zero inference. Acceptance: a per-benchmark table with N and the max_tokens definition recorded. Estimate: 0.5 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): DONE. Column-only read (no `spans`) of Exgentic/agent-llm-traces-v2 at revision `4b8ad4ab`; table and script: `artifacts/dpf-logpfx/toc-sp-11-exgentic-v2-window-crosscheck.json`, `scripts/analysis/toc_sp11_exgentic_window_crosscheck.py`. Definition of `max_tokens` (dataset build script `_recompute_aggregates`): per-session maximum over surviving chat spans of input plus output tokens, NOT the request parameter. Discrepancy: the task says 12 parquet files; the dataset has 9 (`data/train/0000..0008`), and 10,056 rows were read against 10,057 documented. Share of runs above 0.60 / 0.85 of 65,536 and of 262,144: ALL (10,056) 33.6/25.9% and 5.7/4.0%; appworld (1,500) 78.5/64.3% and 0.1/0.0%; browsecompplus (1,948) 51.9/40.1% and 13.3/9.2%; swebench (1,959) 36.3/22.1% and 12.0/10.4%; tau2_airline (957) 8.8/6.8% and 1.0/0.6%; tau2_retail (1,848) 10.5/9.5% and 1.0/0.3%; tau2_telecom (1,844) 10.8/10.0% and 2.6/0.6%. By harness (>0.60 of 65,536): smolagents_code 57.6%, claude_code 32.5%, tool_calling 28.1%, openai_solo 21.1%, tool_calling_with_shortlisting 2.7%. Window-binding signal for the TOC-SP-5 gate: appworld and browsecompplus exceed 0.60 of a 64K window in 52-79% of runs. Beside the 62-trajectory corpus (none of the 26 covered trajectories exceed any threshold; 36 blocked) the two do not overlap enough to compare. Caveat: max values reach 3.4M tokens, above any window, so tails are not interpreted.
- **M7 (monitor, 2026-10-20) — Context-policy follow-ons (cache of repeated read-only results, reject-with-notice overflow, LLM-compression tuning, learned router, staleness measure, Yuj replication, AgentLongBench probe, IterResearch, ParallelMuse, LongBioBench).** Trigger: The TOC-SP-5 result shows a role with a binding window (peak prompt above 0.60 for more than 10 percent of trajectories), or the A/B-CTRL arm survives the standing rule against LLM-summarising edit-bearing output. First step when it fires: Add the listed arm to the CF-AB-1 comparison at that role. No immediate step remains: Without a binding window none of them has a problem to solve; each is untested by its author.
- **K2 (knowledge, 2026-10-20) — Per-model and regime priors (component and context-policy value depends on served model and budget; main effects suffice; a wall-clock cap conflates speed with window management; preview length sits at ACON's threshold).** Retained use: Cited by TOC-SP-7 and HIL-9 items 8 and 19; borrows no number.

### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **TOC-SP-LB1 — Measure the rate of consecutive identical (name, args) tool calls and what follows them in the conversation stores, then choose between wiring the result-equality repeat notice and model-voiced steering with a one-reply tool ban (intake-2386).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / locals-a.)* Measured (branch `f8/locals-a-orch-20261022` (unmerged, not pushed), commit `640e7a37`, `scripts/analysis/toc_sp_lb1_repeat_calls.py`; read-only over the cloud-llm-vault `claude` and `codex` stores and `opencode.db` (`mode=ro`, LIMITed); polling tools `write_stdin`/`wait`/`sleep`/`BashOutput`/`TaskOutput` excluded; a repeat = the same (tool, canonical args) as the immediately preceding call; only counts leave the script). Consecutive-identical rate: **qwen-gpu 1/3,383 = 0.03%** (162 sessions), **qwen-local 0/918**, deepseek (cloud, opencode) 1/2,745 = 0.04%, Claude vault 77/32,179 = 0.24% (1,703 files; 83% result-equal, 19% followed by a third identical call; top repeats Edit 41, Bash 19, Read 10), Codex vault 28/7,107 = 0.39% (142 files; 11% result-equal, 11% followed by a third). The 1,393 Codex `write_stdin` repeats are polling and excluded. **Decision: wire NEITHER the result-equality repeat notice NOR the one-reply tool ban now.** The local repeat rate is two to three orders of magnitude below any rate where either costs back its tokens and prompt surface (1 repeat in 4,301 local calls); the only sizeable pattern (cloud-agent `Edit` retried with an identical failing argument, 83% result-equal) is the case a result-equality notice would address, so if a trigger fires later, build the notice, not the ban. Trigger to reopen: local repeat rate above 1% over at least 5,000 local calls.

## Research Intake Update — 2026-10-30 (Mainplane retrieval over compaction; intake-2522..2534)

Operator-approved 2026-10-31 via research intake (plan sha256 525849605518c57ce866f299b686116b6686df9efb457f4af9fc5f0866ffe097). Monitor records are prose: no checkbox, no index next action.

- [x] **TOC-MP-1 — Prove every REPL context pointer is readable by the REPL that receives it, and fix any denial (zero inference).** The orchestrator emits three pointer kinds, all under `tmp_dir`: the session-log block `Full log: peek(99999, file_path=...)` (`src/graph/session_summary.py:351-362`), compaction's `read_file("<tmp_dir>/session_<task>_ctx_<n>.md")` (`src/graph/compaction.py:278-291`) and spill `peek(n, file_path=..., offset=k)` (`src/graph/file_artifacts.py:100-139`). `_validate_file_path` (`src/repl_environment/environment.py:570-625 @ b0f8613d`) admits only the scratch task root when `task_root_active()` and only root + read_roots under `request_scope()`, so a pointer can be dead in those modes. Add a unit test that emits each pointer kind under default, task-root and request-scope modes and calls the pointed tool; where a read is denied, admit the request's own session artifacts or write them under the task root. Acceptance: the test passes in all three modes, with the fix commit named here (intake-2523, intake-2524). ✅ 2026-10-31 — ORCH `9ca8511726afddea9c4e0fc2af4a43fb27d2adf4`, `tests/unit/test_toc_mp1_artifact_pointers.py`; [test and fix evidence](../../progress/2026-10/2026-10-31-toc-mp1-pointer-custody.md). [belief: cc]
  - 2026-10-31: ORCH main `9ca8511726afddea9c4e0fc2af4a43fb27d2adf4` fixes the emitted compaction `read_file` pointer in all three modes and session-log/spill `peek` under task-root and request-scope, using exact per-REPL session artifact capabilities. Sibling, symlink, knowledge-fence and disabled-tool negatives remain refused; legacy unowned resumed-log pointers are withheld. Focused pointer tests: 47 passed, 1 skipped; related tests: 168 passed; Ruff clean. Zero inference. [Completion receipt](../../progress/2026-10/2026-10-31-toc-mp1-pointer-custody.md). [belief: cc]
- [x] **TOC-MP-2 — A/B-ARMS: fix the arm set of the first-party verbatim-log A/B (design text, zero inference).** Arms at one recorded context budget C: (1) summary-only, the MemGPT DMR baseline shape (intake-2530); (2) summary + full-log pointer, today's production shape (`_session_log_prompt_block`) and the Cursor / Claude Code / OpenClaw shape (intake-2524, intake-2534); (3) pointer-only: recent verbatim tail + full-log pointer + one continuation sentence, no summary (Mainplane, intake-2522, intake-2523); (4) no-summary tool-result pruning (OpenClaw client path: soft-trim, then placeholder) with a pointer written into each placeholder (intake-2534); (5) full history in context while it fits, as reference. Arms 1-2 use OpenClaw's published sectioned summary prompt (`compaction.ts` @ 0e7b5c3) so the summary arm is not a straw man; A/B-CTRL still decides how the summary is produced on the live path. Acceptance: an arm table under the A/B box giving each arm's flag/config recipe and C. ✅ 2026-10-31
  - 2026-10-31 (workspace-58): arm table, C = 16,384 tokens (harness-side prompt cap inside the 65,536 :8070 slot), shared boundary at f x C (f = 0.5, also 0.25), shared 0.20 x C verbatim tail, OpenClaw prompts pinned by sha256 at `0e7b5c34`, arm-to-code map and flags in [`docs/design/toc-mp-ab-design-20261031.md`](../../docs/design/toc-mp-ab-design-20261031.md) section 1. Finding: no arm runs today; the REPL prompt renders no history, `_maybe_compact_context` rewrites unrendered `TaskState.context`, and the production `Full log` pointer names a 200-char-preview journal. Implementation is TOC-MP-2i. [no-belief: design text]
- [x] **TOC-MP-3 — A/B-REL: add reliability, retrieval-miss, literal-recoverability and wall-time requirements to the A/B (design text, zero inference).** (a) n >= 2 trials per task (prefer 4, the tau2 protocol, intake-2532) and pass^k / pass@k per arm with the per-task estimator mean_task C(c,k)/C(n,k) (intake-2533), never p^k of the mean success; (b) post-boundary blocked/error actions over the first 5 actions, counted separately from deliberate re-reads (intake-2527); (c) retrieval misses: tasks whose needed fact sits only in the externalized log and is never read, plus re-fetch tokens and wall time per arm (intake-2522, intake-2526); (d) probes stratified by literal recoverability: direct (literal in the query), paraphrase, two-hop (intake-2531); (e) compaction wall time as a share of end-to-end time (intake-2528#record). Acceptance: the requirements sit under the A/B box and every field they need is in the trajectory-artifact schema or filed as a schema addition. ✅ 2026-10-31
  - 2026-10-31 (workspace-58): requirements (a)-(e), metric directions and the field mapping (existing trajectory fields plus filed schema additions) in [`docs/design/toc-mp-ab-design-20261031.md`](../../docs/design/toc-mp-ab-design-20261031.md) section 2; the additions ship with TOC-MP-2i. [no-belief: design text]
- [x] **TOC-MP-2i — Implement the A/B arm knobs and TOC-MP-3 schema additions behind default-off flags (zero inference; before TOC-MP-4).** Per `docs/design/toc-mp-ab-design-20261031.md`: `session_log_verbatim` (`ORCHESTRATOR_SESSION_LOG_VERBATIM`) verbatim per-turn log with byte offsets, written where TOC-MP-1 makes it readable; `context_arm_ab` (`ORCHESTRATOR_CONTEXT_ARM_AB`) with env knobs `ORCHESTRATOR_CONTEXT_ARM`, `ORCHESTRATOR_CONTEXT_BUDGET_TOKENS`, `ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION`, `ORCHESTRATOR_CONTEXT_FORCE_TURNS`, `ORCHESTRATOR_SESSION_SUMMARY_PROMPT`; boundary branch in `_maybe_compact_context` measuring the rendered history, `_session_history_prompt_block` renderer, OpenClaw prompts vendored with sha256 test; trajectory additions (`boundary` event, `turn.blocked`, `turn.log_follows` incl. `read_file`, `turn.probe_literals_present`, `turn.code_sha256`, `turn.turn_wall_s`, `final.arm`/`context_budget_tokens`/`trigger_fraction`/`trial_index`/`boundary_wall_s`/`task_wall_s`). Acceptance: flag-off prompt bytes identical to origin/main (exact-string test); one unit test per arm showing the rendered block after a forced boundary; runtime_flags spec re-synced. ✅ 2026-10-31 orchestrator `f61cca823bb714bbcd69c218f32aba913fd6f869` · [tests](../../artifacts/compute/codex3-toc-mp2i-20261031/record-final.log) [no-belief: default-off code and tests only]
  - Implemented in orchestrator `f61cca823bb714bbcd69c218f32aba913fd6f869`, promoted on main `f87b7c545f847ed2fa48b018664d1de3533a23f6`. Offline validation: 108 passed / 1 skipped plus 12 final targeted passes, Ruff and diff check; [review and validation](/mnt/raid0/llm/tmp/codex3-toc-mp2i-20261031/REVIEW.md), [completion receipt](/mnt/raid0/llm/tmp/toc-mp1-20261031/MP2i-DONE.json). History captures post-redaction REPL output; capped context bundles and foreign legacy logs refuse. Task wall is graph-run wall excluding HTTP/queue; the scientific runner must prove target tokenizer identity and reject heuristic fallback. No inference, grade, A/B result or TOC-MP-4 completion is claimed.
- [ ] **TOC-MP-4 — Exact-value needle screen across arms 1-3 before the full A/B (correctness-class inference; after TOC-MP-1 and TOC-MP-2).** Fixture: 20 REPL tasks whose answer is an unforgeable 24-character value printed once by an early tool call inside a >4,000-character output, with externalization forced at fixed turn indices (ARC Appendix B design, intake-2525). Arms 1-3 of TOC-MP-2 at one recorded C; frontdoor model; n = 2 runs per task; score only the exact submitted value. Record orchestrator commit, flags, model/quant, C and the trajectory artifacts. Decision rule, fixed in advance: pointer-only exact recall >= summary+pointer keeps arm 3 in the full A/B as the candidate default; otherwise record the miss pattern here and fire M-MP2. Acceptance: result table, artifact path and the decision line.
- **M-MP2 (monitor, 2026-10-30 intake) — pointer-arm refinements.** Content-addressed spill stubs (head/tail preview + short hash id + length) with recall guards (per-step recall cap, per-recall char cap, LRU re-stub) from ARC (intake-2525), and a MemGPT-style memory-pressure notice before externalization so the model can save facts first (intake-2530). Trigger: TOC-MP-4 or the full A/B records pointer-only retrieval misses. No checkbox until then.
- **M-MP3 (monitor, 2026-10-30 intake) — summary-arm refinements, added to M7's LLM-compression tuning list.** Parallel or asynchronous compaction (intake-2528#record) and verifier-optimised summary prompts (TRACE, intake-2527). Trigger: a summary arm wins the full A/B. No checkbox until then.
