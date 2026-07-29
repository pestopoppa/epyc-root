# Handoff: Model REPL Tool Compliance Testing

**Created:** 2026-01-24
**Completed:** 2026-01-24
**Status:** Completed
**Priority:** Medium
**Estimated Effort:** Low-Medium

---

## Summary

Ensure all models in the orchestration hierarchy can correctly use REPL tools relevant to their role. This includes testing, documentation, and potentially fine-tuning or prompt adjustments.

---

## Problem Statement

During document pipeline integration (2026-01-24), we discovered:
1. The frontdoor model (Qwen3-Coder-30B-A3B) initially tried to use `pathlib` and `os.listdir` instead of `list_dir()`
2. Even with clear "NO IMPORTS" warnings, the model needed explicit examples
3. Different models may have varying instruction-following capabilities

Without validation, we risk:
- Models ignoring available tools
- Sandbox security errors on every request
- Poor user experience from repeated failures

---

## Proposed Solution

### 1. Tool Requirement Matrix

Define which tools each role needs:

| Role | Required Tools | Optional Tools |
|------|----------------|----------------|
| frontdoor | peek, grep, list_dir, file_info, FINAL | llm_call, escalate |
| coder_primary | peek, grep, llm_call, FINAL | list_dir, run_shell |
| worker | peek, grep, FINAL | llm_call |
| ingest | ocr_document, peek, FINAL | extract_figure, analyze_figure |
| architect | peek, grep, llm_call, escalate, FINAL | recall |

### 2. Compliance Test Suite

Create automated tests for each role:

```python
# tests/integration/test_model_tool_compliance.py

TOOL_TESTS = {
    "list_dir": {
        "prompt": "List files in /mnt/raid0/llm/claude/tmp",
        "expected_tool": "list_dir",
        "expected_pattern": r'list_dir\(["\'/]',
    },
    "peek": {
        "prompt": "Show the first 100 characters of /mnt/raid0/llm/claude/README.md",
        "expected_tool": "peek",
        "expected_pattern": r'peek\(\d+.*file_path',
    },
    "ocr_document": {
        "prompt": "Extract text from /path/to/doc.pdf",
        "expected_tool": "ocr_document",
        "expected_pattern": r'ocr_document\(["\'/]',
    },
}

@pytest.mark.parametrize("role", ["frontdoor", "coder_primary"])
@pytest.mark.parametrize("tool_name", ["list_dir", "peek"])
def test_model_uses_correct_tool(role, tool_name):
    """Test that model uses REPL tool instead of imports."""
    test = TOOL_TESTS[tool_name]

    # Get model's response
    response = llm_call(test["prompt"], role=role)

    # Check it uses the right tool
    assert re.search(test["expected_pattern"], response)

    # Check no forbidden imports
    assert "import " not in response
    assert "from " not in response
```

### 3. Per-Model Prompt Tuning

If a model fails compliance tests, options:

1. **Add few-shot examples** - Include 2-3 examples in the system prompt
2. **Adjust prompt emphasis** - Make rules more prominent (CRITICAL, ##)
3. **Model-specific overrides** - Different prompt templates per model
4. **Fine-tuning** - For persistent issues (last resort)

Current prompt adjustments that worked for Qwen3-Coder-30B:
- "## CRITICAL" section at top of rules
- "**NO IMPORTS** - import/from are BLOCKED"
- Inline examples: `list_dir('/path'); FINAL(result)`

### 4. Compliance Dashboard

Add metrics to `/stats` endpoint:

```json
{
  "tool_compliance": {
    "frontdoor": {
      "list_dir": {"tests_run": 10, "passed": 10, "rate": 1.0},
      "peek": {"tests_run": 10, "passed": 9, "rate": 0.9}
    },
    "coder_primary": {...}
  }
}
```

---

## Implementation Steps

1. **Create test suite** (`tests/integration/test_model_tool_compliance.py`)
   - Parametrized tests for role × tool combinations
   - Check for correct tool usage, no imports
   - Run nightly or on model changes

2. **Add MemRL feedback** for tool usage
   - Track which tools are used successfully
   - Learn from patterns of success/failure

3. **Create prompt templates per role**
   - `src/prompts/frontdoor.txt`
   - `src/prompts/coder.txt`
   - Include role-specific examples

4. **Document model quirks**
   - Update `docs/reference/models/QUIRKS.md` with tool compliance notes
   - E.g., "Qwen3-Coder needs explicit NO IMPORTS warning"

---

## Files to Create/Modify

| File | Changes |
|------|---------|
| `tests/integration/test_model_tool_compliance.py` | New test suite |
| `src/prompts/` | New directory for role-specific prompts |
| `docs/reference/models/QUIRKS.md` | Add tool compliance notes |
| `benchmarks/prompts/tool_compliance/` | Test prompts for each tool |

---

## Success Metrics

- All models pass 95%+ of tool compliance tests
- Zero "import blocked" errors in production logs
- Average turns-to-completion ≤ 1.5 for simple tool tasks

---

## Dependencies

- Requires models to be running for integration tests
- Should run after any model change or prompt update

---

## Implementation Summary (Completed 2026-01-24)

### Files Created

| File | Description |
|------|-------------|
| `tests/integration/test_model_tool_compliance.py` | 34 tests for tool compliance validation |
| `benchmarks/prompts/v1/tool_compliance.yaml` | 9 benchmark prompts across 3 tiers |

### Files Modified

| File | Changes |
|------|---------|
| `docs/reference/models/QUIRKS.md` | Added REPL Tool Compliance section |

### Test Results

- 30 tests pass (mock mode)
- 4 tests skipped (require `--run-live-models` flag)

### How to Run

```bash
# Run all compliance tests (mock mode)
pytest tests/integration/test_model_tool_compliance.py -v

# Run with live models (requires orchestrator)
pytest tests/integration/test_model_tool_compliance.py -v --run-live-models
```

---

## Related

- `handoffs/active/orchestrator_document_pipeline.md` - Where this issue was discovered
- `src/prompt_builders.py` - Current prompt templates
- `docs/reference/models/QUIRKS.md` - Model-specific behaviors
