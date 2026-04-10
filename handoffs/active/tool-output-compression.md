# Tool Token Optimization — Output Compression + Definition Reduction

**Status**: Phase 2 implemented (output compression); Phase 3a-b done (definition audit + compression); A/B done (+4pp REPL, suite-dependent)
**Created**: 2026-04-04 (via research intake deep dive)
**Updated**: 2026-04-10
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

**Claude Code hook finding**: PostToolUse hooks **cannot replace built-in tool output** (only MCP tools support `updatedMCPToolOutput`). The Claude Code hook approach from Phase 0/1 is not viable for Bash output compression. Future work: wrap compression as an MCP tool, or use PreToolUse command rewriting.

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
- [ ] P3c: Measure `instruction_token_ratio` delta (AP-16) — ratio dropped 29.8% → 16.0% (static measure done; AP-16 runtime measurement pending inference)
- [ ] P3d: A/B test compressed vs original definitions on seeding harness
