# Deep Dive: CMV Structural Trimming for REPL Sessions

**Source**: intake-141 (arxiv:2602.22402), intake-140 (lossless-claw repo)
**Date**: 2026-03-15
**Scope**: Evaluate CMV's "trim mechanical bloat" approach for EPYC's REPL session context

## Paper Summary

**Contextual Memory Virtualisation (CMV)** by Cosmo Santoni treats session history as version-controlled state in a DAG. The key innovation is a **three-pass structurally lossless trimming** algorithm that removes mechanical overhead while preserving every user message, assistant response, and tool invocation verbatim.

### Three-Pass Algorithm

| Pass | Purpose | Action |
|------|---------|--------|
| 1 | Compaction boundary detection | Locate last native compression marker via string matching |
| 2 | Pre-boundary tool ID collection | Build set of tool invocation IDs before boundary |
| 3 | Stream-process with trim rules | Single-pass filter applying rules below |

### Trim Rules (Pass 3)

| Content Type | Action | Rationale |
|---|---|---|
| Pre-compaction lines | Skip | Already summarized |
| `file-history`, `queue-op` | Skip | Metadata overhead |
| Base64 images | Remove | Visual content stripped entirely |
| Tool results > τ chars (default 500) | Stub: `[Trimmed: ~N chars]` | Raw output is bloat; model's synthesis preserved in assistant messages |
| Write-tool inputs > τ | Stub (preserve metadata fields) | File paths/commands kept, content trimmed |
| Thinking blocks | Remove | Non-portable |
| Orphaned tool results | Strip | Results for pre-boundary invocations |
| API usage metadata | Remove | Token counts, pricing info |

### Core Insight

> "The model's synthesis of these inputs (its architectural summaries, design decisions, and explanations) is contained in assistant response blocks, which are typically a small fraction of total tokens."

Raw tool outputs are consumed once by the model, which produces a synthesis in its response. Keeping both the raw output AND the synthesis is redundant. CMV keeps the synthesis (assistant message) and stubs the raw output.

### Results

| Session Type | Mean Reduction | Median | Max |
|---|---|---|---|
| All (76 sessions) | 20% | 12% | 86% |
| Mixed (≥15% tool result bytes) | 39% | 33% | 86% |
| Conversational (<15% tool bytes) | 17% | 10% | — |

Break-even under Opus 4.6 prompt caching: 10 turns for mixed sessions, 40 for conversational.

---

## Current EPYC REPL Context Management

Our orchestrator already has **five layers** of context management, several of which partially overlap with CMV's approach:

### Layer 1: Hard Preview Limits
**File**: `src/prompt_builders/types.py:32-36`
- Output preview: **1500 chars**, hard truncation with `"..."`
- Error preview: **500 chars**, hard truncation with `"..."`
- **Problem**: One-way truncation — model sees `"..."` but cannot retrieve the rest

### Layer 2: Stale Tool Output Clearing
**File**: `src/graph/helpers.py:667-728`, function `_clear_stale_tool_outputs()`
- Regex matches `<<<TOOL_OUTPUT>>>...<<<END_TOOL_OUTPUT>>>` blocks
- Keeps 2 most-recent blocks verbatim, replaces older ones with `[Tool result cleared]`
- Triggers when context > 12,000 chars (or 40% of max context)
- Feature-gated: `tool_result_clearing`
- **Problem**: Cleared blocks are irrecoverable — no pointer to original content

### Layer 3: Session Log Summarization
**File**: `src/graph/session_log.py:289-431`
- Worker-synthesized summary (300-400 tokens) regenerated every 2 turns
- Deterministic fallback: first 2 + last 2 turns as one-liners
- Scratchpad extraction: max 8 categorized insights (`bug_location`, `approach_eliminated`, etc.)
- Full log always available on disk at `/mnt/raid0/llm/tmp/session_{task_id}.md`
- **This is good** — already implements "keep synthesis, externalize raw"

### Layer 4: Context Externalization ("Virtual Memory")
**File**: `src/graph/helpers.py:802-929`, function `_maybe_compact_context()`
- Triggers at 60% of model max context
- Dumps full context to disk, generates worker-built structured index
- Keeps recent 20% verbatim + index + pointer to full file
- Feature-gated: `session_compaction`
- **This is aggressive** — goes further than CMV by replacing everything with an index

### Layer 5: Solution File Persistence
**File**: `src/graph/helpers.py:290-318`
- Code persisted to `/mnt/raid0/llm/tmp/{task_id}_solution.py` each turn
- Passed back to model only on error/escalation with `peek()` instruction
- Externalizes code from context

### Summary: What We Have vs CMV

| CMV Approach | EPYC Equivalent | Gap |
|---|---|---|
| Stub tool results > 500 chars | Hard truncate output at 1500 chars | CMV stubs with size hint; we truncate with no recovery |
| Remove base64 images | Not applicable (no images in REPL) | — |
| Remove thinking blocks | Not implemented | We don't strip `<think>` from context |
| Remove file-history/queue-op | Not applicable | — |
| Orphaned tool result stripping | Stale tool output clearing (Layer 2) | Similar outcome, different trigger |
| DAG branching for context reuse | Not implemented | Our escalation creates fresh context |
| Preserve all assistant messages | Session log summarization replaces them | We go further (summarize), CMV is more conservative |

---

## Gap Analysis: What CMV Does That We Don't

### Gap 1: Retrieval Pointers on Truncation

**Current**: `last_output[:1500] + "..."` — model has no way to see the rest.

**CMV approach**: `[Trimmed: ~4,200 chars]` with the understanding that the original is accessible.

**Proposed**: When truncating output or error, spill full content to a temp file and append a retrieval pointer:

```python
# In builder.py, replace hard truncation with spill + pointer
if len(last_output) > config.max_output_preview:
    spill_path = f"/mnt/raid0/llm/tmp/{task_id}_output_t{turn}.txt"
    with open(spill_path, "w") as f:
        f.write(last_output)
    output_preview = last_output[:config.max_output_preview]
    output_preview += f"\n[... {len(last_output) - config.max_output_preview} chars truncated; full output: peek(99999, file_path=\"{spill_path}\")]"
```

**Effort**: ~20 lines in `builder.py`. Low risk.
**Expected impact**: Model can retrieve full output on demand when the truncated portion contains the key information (e.g., error at line 200 of a 300-line traceback).

### Gap 2: Think Block Stripping

**Current**: `<think>` blocks from worker/architect responses remain in context across turns.

**CMV approach**: Remove thinking blocks entirely — they're non-portable and bloated.

**Proposed**: Strip `<think>...</think>` blocks from `state.last_output` and `state.context` before the next turn. The model's answer (outside `<think>`) is the synthesis; the reasoning is mechanical bloat.

```python
# In _execute_turn(), after raw_llm_output processing:
import re
_THINK_STRIP_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
# Strip think blocks from what gets carried into context
context_output = _THINK_STRIP_RE.sub("", raw_llm_output)
```

**Effort**: ~10 lines. Already have `_THINK_BLOCK_RE` in `quality_detector.py`.
**Expected impact**: On reasoning-heavy turns (architect/worker_math), think blocks can be 50-80% of output. Stripping them from carried context could save 1,000-5,000 tokens per turn.
**Risk**: Low — the think block content is never referenced by subsequent turns. The model's actual answer (post-`</think>`) contains the synthesis.

### Gap 3: Structured Tool Result Stubbing

**Current**: Layer 2 replaces entire old tool output blocks with `[Tool result cleared]`.

**CMV approach**: Preserve metadata (which tool, which file, what command) while stubbing the content.

**Proposed**: When clearing stale tool outputs, preserve a structured stub:

```python
# Instead of just "[Tool result cleared]"
stub = f"[Tool result cleared: {tool_name}({key_args}), ~{len(content)//4} tokens]"
```

**Effort**: ~15 lines in `_clear_stale_tool_outputs()`. Requires extracting tool name from block.
**Expected impact**: Small — the session log summary already captures what happened in each turn. But useful for the model to know *which* tool produced which cleared result.

### Gap 4: Error Trace Intelligence

**Current**: First 500 chars of error, hard truncation.

**CMV approach**: Not specifically addressed (CMV is for Claude Code sessions, errors flow differently).

**Proposed**: Extract structured error info before truncation:

```python
# Parse Python tracebacks: keep last frame + exception line
# "TypeError at line 42 in process_data(): 'NoneType' has no attribute 'items'"
# Full trace spilled to file
```

**Effort**: ~40 lines. Moderate — need to handle various error formats.
**Expected impact**: Medium — models often need the specific line number and error type, which may be at the END of a traceback (beyond the 500-char preview).

---

## Implementation Priority

| # | Gap | Effort | Impact | Priority | Status |
|---|---|---|---|---|---|
| 1 | Think block stripping from carried context | ~10 lines | N/A — doesn't apply to REPL architecture | ~~P0~~ | **N/A** (investigated, raw LLM output not carried forward) |
| 2 | Retrieval pointers on output truncation | ~30 lines | Medium (model can recover key info) | **P1** | **DONE** — `_spill_if_truncated()`, 9 tests |
| 3 | Error trace intelligence | ~40 lines | Medium (better error context) | P2 | |
| 4 | Structured tool result stubs | ~15 lines | Low (marginal improvement) | P3 | |

### Why P0 (Think Block Stripping) Doesn't Apply

Investigation revealed that in our REPL architecture, `state.last_output` is the REPL execution stdout (Python code output), NOT the raw LLM response. The flow is:
1. LLM generates response with `<think>` blocks → stored in `raw_llm_output` (local var)
2. Code extracted from response → REPL executes Python code
3. `result.output` (stdout) → `state.last_output` (carried to next turn)
4. `raw_llm_output` is consumed for FINAL() rescue, workspace update, then discarded

Think blocks never appear in `state.last_output` or `state.last_error`. This differs fundamentally from Claude Code's conversation model where the full assistant message (including think blocks) persists in history.

### What NOT to adopt from CMV

- **DAG branching**: Our escalation model (fresh context + solution file) is adequate. DAG branching adds complexity for marginal benefit in our turn-count regime (~5-15 turns, not 50+).
- **Prompt cache break-even math**: We use local llama-server, not API. No prompt caching cost model. The trimming benefit is purely about fitting more useful information in the context window.
- **Three-pass algorithm**: Overkill for our use case. We don't have compaction boundaries in the CMV sense. A single-pass strip of think blocks + output spill is sufficient.

---

## Concrete Next Steps

### Action 10: Think Block Context Stripping — N/A

**Investigated and ruled out**. In our REPL architecture, raw LLM output (with `<think>` blocks) is NOT carried into `state.last_output`. The REPL execution stdout is what flows forward. See "Why P0 Doesn't Apply" section above.

### Action 11: Output Spill with Retrieval Pointer — DONE

**Where**: `src/graph/helpers.py` — `_spill_if_truncated()` helper + wiring in `_execute_turn()`

**What**: When `last_output` or `last_error` exceeds the prompt builder's preview limit, write full content to `/mnt/raid0/llm/tmp/{task_id}_{label}_t{turn}.txt` and append a `peek()` instruction to the truncated preview. Reserves 150 chars for the pointer so the builder's own truncation doesn't clip it.

**Gate**: Feature flag `output_spill_to_file` (production=True, test=False, env=`OUTPUT_SPILL_TO_FILE`).

**Tests** (9 in `tests/unit/test_output_spill.py`):
- Short text returned unchanged
- Exact limit returned unchanged
- Feature flag off → returns unchanged (no pointer)
- Long text spills to file + pointer appended
- Spill file contains full content
- Pointer includes correct file path
- Preview + pointer fits within builder's truncation limit
- Error label produces correct spill path
- Task ID sanitized for filesystem safety
