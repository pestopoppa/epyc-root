# Handoff: Orchestrator Document Pipeline Integration

**Created:** 2026-01-24
**Updated:** 2026-01-24
**Status:** COMPLETED
**Priority:** Done

---

## Summary

Implemented all REPL tools for document processing. Full /chat integration now works - model correctly uses REPL tools after prompt improvements.

---

## Completed ✓

### 1. Document Processing Tools

| Tool | Status | Notes |
|------|--------|-------|
| `ocr_document(path)` | ✓ Works | 32-page PDF in 4 min, 11 figures detected |
| `analyze_figure(image_path, prompt)` | ✓ Code works | Server needs VL model |
| `extract_figure(pdf_path, page, bbox)` | ✓ Works | Crops figures from PDF |

### 2. Utility Tools

| Tool | Status | Notes |
|------|--------|-------|
| `list_dir(path)` | ✓ Works | Returns JSON with file list |
| `file_info(path)` | ✓ Works | Returns file metadata |
| `web_fetch(url, max_chars)` | ✓ Works | Fetches URL, strips HTML |
| `run_shell(cmd)` | ✓ Works | Sandboxed read-only shell |

### 3. Orchestration Tools

| Tool | Status | Notes |
|------|--------|-------|
| `recall(query, limit)` | ✓ Works | Episodic memory seeded with 48 examples |
| `escalate(reason)` | ✓ Works | Sets artifact flags |

### 4. Episodic Memory Seeding

Seeded MemRL episodic memory with 48 canonical REPL tool usage examples:

| Category | Count | Examples |
|----------|-------|----------|
| filesystem | 8 | list_dir, file_info, peek |
| document | 6 | ocr_document, extract_figure |
| complex | 7 | Multi-step with llm_call |
| shell | 5 | git, ls, find |
| simple | 4 | Direct calculations |
| search | 3 | grep patterns |
| vision | 3 | analyze_figure |
| web | 3 | web_fetch |
| artifacts | 3 | Store/retrieve values |
| memory | 2 | recall past tasks |
| escalation | 2 | escalate to architect |
| parallel | 2 | llm_batch operations |

### 5. Configuration & Prompt Fixes

- Increased REPL timeout: 120s → 600s (10 min for document processing)
- Added `json` module to REPL globals
- **Fixed code extraction** to strip leading whitespace (was causing SyntaxError)
- **Updated prompts** with:
  - "## CRITICAL" section with NO IMPORTS warning
  - Explicit examples: `list_dir('/path'); FINAL(result)`
  - Tool-specific section headers

---

## Final Test Results

### /chat Integration (All Working)

| Test | Result |
|------|--------|
| `"What is 2+2?"` | ✓ PASS - Returns "4" in 1 turn |
| `"List files in /mnt/raid0/llm/claude/tmp"` | ✓ PASS - Uses list_dir(), 1 turn, 0.98s |

### Root Cause of Initial Failures

1. **Leading whitespace** in LLM response caused `SyntaxError: unexpected indent`
2. **Model ignored tools** because prompt didn't emphasize they were the ONLY option
3. **No examples** meant model defaulted to familiar Python stdlib

---

## Remaining Blockers (Non-Critical)

### 1. Vision API - VL Model Missing

```
FileNotFoundError: VL model not found at /mnt/raid0/llm/models/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf
```

**Fix:** Download and convert Qwen2.5-VL-7B-Instruct to GGUF format.

---

## Files Modified

| File | Changes |
|------|---------|
| `src/repl_environment.py` | Added 9 new tools, increased timeout, added json to globals |
| `src/prompt_builders.py` | Updated DEFAULT_ROOT_LM_TOOLS and DEFAULT_ROOT_LM_RULES, fixed code extraction |
| `docs/ARCHITECTURE.md` | Added REPL permission architecture section |
| `orchestration/repl_memory/seed_examples.json` | Created 48 canonical REPL tool usage examples |
| `orchestration/repl_memory/seed_loader.py` | Created script to load seeds into episodic memory |

---

## Follow-Up Handoffs Created

1. **`repl_permission_tiers.md`** - Configurable read/write/delete permissions
2. **`model_repl_tool_compliance.md`** - Testing all models can use REPL tools correctly

---

## Key Learnings

1. **Prompt engineering matters** - "NO IMPORTS" needs to be LOUD and explicit
2. **Examples are essential** - Models follow examples more reliably than rules
3. **Code extraction must be robust** - Strip whitespace, handle malformed markdown
4. **Sandbox errors need clarity** - Model needs to understand WHY imports fail

---

## Related Documentation

- LightOnOCR server: `src/services/lightonocr_llama_server.py`
- Vision API: `src/api/routes/vision.py`
- REPL environment: `src/repl_environment.py`
- Prompt builders: `src/prompt_builders.py`
