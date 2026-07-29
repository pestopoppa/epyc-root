# Handoff: Replace 9 Brittle Heuristics with Semantic Classifiers

**Status**: READY TO IMPLEMENT
**Created**: 2026-01-29
**Updated**: 2026-02-06 (file locations updated after chat.py decomposition)
**Priority**: High (blocking benchmark quality improvement)

## Problem

The codebase has 9 hardcoded keyword/pattern heuristics scattered across route modules that are fragile:
- Adding a keyword fixes one case, breaks another (whack-a-mole)
- Fix 13 (date injection) proved this: adding `"Current date: ..."` to all prompts caused instruction_precision to regress from 70% to 45.5%
- Date injection was fully removed; factual context should come via tools + ReAct loop

## The 9 Heuristics (Current Locations)

| # | Function | File | Line | Category |
|---|----------|------|------|----------|
| 1 | `_is_summarization_task()` | `chat_summarization.py` | :29 | A: Input |
| 2 | `_needs_structured_analysis()` | `chat_vision.py` | :49 | A: Input |
| 3 | `_should_use_direct_mode()` | `chat_routing.py` | :22 | A: Input |
| 4 | `_is_stub_final()` | `chat_utils.py` | :117 | B: Output |
| 5 | `_strip_tool_outputs()` | `chat_utils.py` | :128 | B: Output |
| 6 | `_detect_output_quality_issue()` | `chat_review.py` | :27 | C: Quality |
| 7 | `_is_ocr_heavy_prompt()` | `chat_vision.py` | :30 | A: Input |
| 8 | Verdict parsing ("OK" / "WRONG") | `chat_review.py` | grep `"OK"` | B: Output |
| 9 | Success detection patterns | various | grep `success` | B: Output |

All files in `src/api/routes/`.

## Solution Architecture

Replace all 9 with a `src/classifiers/` module backed by:

- **Category A (Input)**: EpisodicStore + TwoPhaseRetriever (existing MemRL infra) for embedding-based classification with Q-learning. Falls back to keyword matching.
- **Category B (Output)**: Config-driven OutputParser with compiled regex from YAML, structured return types (VerdictResult, StubResult, ErrorResult).
- **Category C (Quality)**: QualityDetector with all thresholds externalized to YAML (no magic numbers).

**Key principle**: New categories = YAML edits, not code changes. Everything lives in `orchestration/classifier_config.yaml`.

**Design constraint**: Reuse the existing EpisodicStore + TwoPhaseRetriever instead of building a parallel embedding system. Classification exemplars are stored as `MemoryEntry(action_type="classification")`. Q-values learn from outcomes over time.

## Files to Create

| File | Purpose |
|------|---------|
| `src/classifiers/__init__.py` | Public API + lazy singletons |
| `src/classifiers/types.py` | Dataclasses (ClassificationResult, VerdictResult, etc.) |
| `src/classifiers/input_classifier.py` | MemRL-backed prompt classification |
| `src/classifiers/output_parser.py` | Structured output parsing (stub detection, verdict parsing) |
| `src/classifiers/quality_detector.py` | Configurable quality detection |
| `orchestration/classifier_config.yaml` | All exemplars, patterns, thresholds |
| `tests/unit/test_classifiers.py` | Unit tests (aim for 30+ tests) |

## Files to Modify

| File | Changes |
|------|---------|
| `src/api/routes/chat_summarization.py` | Replace `_is_summarization_task()` body |
| `src/api/routes/chat_vision.py` | Replace `_needs_structured_analysis()`, `_is_ocr_heavy_prompt()` bodies |
| `src/api/routes/chat_routing.py` | Replace `_should_use_direct_mode()` body |
| `src/api/routes/chat_utils.py` | Replace `_is_stub_final()`, `_strip_tool_outputs()` bodies |
| `src/api/routes/chat_review.py` | Replace `_detect_output_quality_issue()` body |
| `src/features.py` | Add `semantic_classifiers: bool` flag |
| `orchestration/repl_memory/retriever.py` | Add `retrieve_for_classification()` method |
| `src/api/__init__.py` or lifespan | Seed classification exemplars on API init |

## Implementation Order

1. **`types.py`** — Dataclasses (no deps)
2. **`quality_detector.py`** — Simplest, no MemRL, just configurable thresholds
3. **`output_parser.py`** — Regex-based, no MemRL
4. **`classifier_config.yaml`** — Migrate all current keywords/patterns from the 9 functions
5. **`retriever.py`** — Add `retrieve_for_classification()` method
6. **`input_classifier.py`** — Uses TwoPhaseRetriever + keyword fallback
7. **`__init__.py`** — Wiring + lazy singletons
8. **API startup** — Seed exemplars from YAML into EpisodicStore
9. **Route modules** — Replace 9 heuristic bodies with classifier calls
10. **`features.py`** — Add feature flag
11. **`test_classifiers.py`** — Tests
12. **Benchmark** — Run to validate

## Key Files to Read First

```bash
# The 9 heuristic functions to replace
src/api/routes/chat_summarization.py   # _is_summarization_task
src/api/routes/chat_vision.py          # _needs_structured_analysis, _is_ocr_heavy_prompt
src/api/routes/chat_routing.py         # _should_use_direct_mode
src/api/routes/chat_utils.py           # _is_stub_final, _strip_tool_outputs
src/api/routes/chat_review.py          # _detect_output_quality_issue

# MemRL infrastructure to reuse
orchestration/repl_memory/retriever.py    # TwoPhaseRetriever to extend
orchestration/repl_memory/embedder.py     # TaskEmbedder.embed_text() interface
orchestration/repl_memory/episodic_store.py # MemoryEntry + store() method

# Patterns to follow
src/features.py                        # Feature flag pattern
```

## Verification Commands

```bash
# Run tests after each step
cd /mnt/raid0/llm/claude && python3 -m pytest tests/unit/test_classifiers.py -v

# Full test suite (should stay at 2015+ passing)
python3 -m pytest tests/unit/ -x -q

# Benchmark validation
python scripts/benchmark/compare_orchestrator_direct.py --debug --suite all
```

## Success Criteria

1. All 9 heuristics delegate to classifiers
2. `semantic_classifiers` feature flag controls behavior
3. 30+ unit tests for classifier module
4. No test regressions (2015+ tests passing)
5. Benchmark quality ≥ 76% (current baseline), target 85%+

## Design Details

### InputClassifier

```python
class InputClassifier:
    def classify(self, prompt: str, context: str = "") -> ClassificationResult:
        # 1. Try MemRL retrieval (embedding similarity)
        episodes = self.retriever.retrieve_for_classification(prompt, k=5)
        if episodes and episodes[0].score > 0.6:
            return ClassificationResult(
                label=episodes[0].action_type,
                confidence=episodes[0].score,
                source="memrl"
            )
        # 2. Fall back to keyword matching
        return self._keyword_fallback(prompt)
```

### classifier_config.yaml

```yaml
input_classifiers:
  summarization:
    keywords: ["summarize", "summary", "tldr", "key points", "main ideas"]
    exemplars:  # Seeded into EpisodicStore
      - prompt: "Summarize this document"
        label: "summarization"
      - prompt: "Give me the key takeaways"
        label: "summarization"

  direct_mode:
    keywords: ["what is", "who is", "when did", "how many"]
    negative_keywords: ["implement", "write code", "create"]

output_parsers:
  verdict:
    patterns:
      ok: "^OK$"
      wrong: "^WRONG:\\s*(.+)$"

  stub:
    patterns:
      - "I don't have"
      - "I cannot"
      - "As an AI"

quality_thresholds:
  repetition_ratio: 0.3
  min_answer_length: 10
  max_answer_length: 50000
```

## Notes

- The original plan file was lost during cleanup — this handoff contains all necessary details
- chat.py was decomposed in Feb 2026 — functions now live in separate route modules
- Feature flag allows gradual rollout and A/B testing
