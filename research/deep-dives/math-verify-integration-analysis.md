# Deep Dive: Math-Verify Integration Analysis

**Covers**: intake-377, intake-379
**Date**: 2026-04-15
**Target handoff**: eval-tower-verification.md

## Math-Verify Architecture

Three-step cascading comparison with fallback chain:

```
String match → Numeric comparison → Symbolic simplification → Specialized handlers
                                                                ├─ Relations
                                                                ├─ Sets/Intervals
                                                                ├─ Matrices
                                                                └─ Symbols
```

### Core API

```python
verify(gold, target, float_rounding=6, numeric_precision=15, strict=True,
       allow_set_relation_comp=False, timeout_seconds=5, raise_on_error=False) -> bool
```

### Critical Implementation Details

1. **NOT symmetric**: `verify(gold, pred)` ≠ `verify(pred, gold)` in some cases (assignment simplification, equation-interval conversion). Gold answer MUST be the first argument.

2. **NOT thread-safe**: Uses `signal.alarm()` for timeout. Will raise `ValueError` in threaded environments. If `eval_tower.py` uses `ThreadPoolExecutor` for parallel question evaluation, this WILL break.

3. **List matching**: Uses `any()` over product of gold × target lists — "any match wins" semantics. This means `verify([a, b], [c])` returns True if c matches either a or b.

4. **Percentage handling**: "9%" is parsed as `9 * UnevaluatedExpr(Rational(1,100))`. Correctly equates "9%", "0.09", and "9/100".

5. **Open interval ambiguity**: "(1,2)" gets converted to `Tuple(1,2)` for open interval representation. Could false-positive if the expected answer is actually a coordinate pair, not an interval. The `allow_set_relation_comp` flag controls some of this behavior.

### Configuration Knobs

| Parameter | Default | Effect | Our Use Case |
|-----------|---------|--------|--------------|
| `float_rounding` | 6 | Decimal precision for float comparison | Default OK for most math |
| `numeric_precision` | 15 | SymPy evalf() digit count | Default OK |
| `strict` | True | Enforce variable name matching | True for eval, prevents `x=1` matching `y=1` |
| `timeout_seconds` | 5 | Max comparison duration | May need increase for complex symbolic expressions |
| `raise_on_error` | False | Silent failure vs exception | False for batch eval, True for debugging |

## Integration Path: eval_tower.py

### Current Scoring

`score_answer_deterministic()` in `safety_gate.py` does binary exact-match. This misses:
- LaTeX-formatted answers vs plain text
- Equivalent expressions ("2x+1" vs "1+2x")
- Numeric precision ("0.333" vs "1/3")
- Set notation ("{1,2,3}" vs "{3,2,1}")

### Proposed Change

```python
# In _eval_question() or score_answer_deterministic()
from math_verify import verify

def score_answer_math_verify(gold: str, prediction: str) -> bool:
    try:
        return verify(gold, prediction, timeout_seconds=5, raise_on_error=False)
    except Exception:
        # Fallback to exact match if math_verify fails entirely
        return gold.strip() == prediction.strip()
```

### Thread Safety Workaround

If eval_tower.py uses threading:

**Option A**: Use `multiprocessing.Pool` instead of `ThreadPoolExecutor` for question evaluation. Each process gets its own signal handler.

**Option B**: Set `timeout_seconds=None` and manage timeouts externally via `concurrent.futures.as_completed(timeout=5)`.

**Option C**: Wrap each `verify()` call in a subprocess. Heaviest but safest.

### Dependencies

```
pip install math-verify  # Pulls ANTLR4 runtime
```

ANTLR4 version compatibility: 4.13.2, 4.11.0, or 4.9.3. Check against any existing ANTLR4 in the environment.

## MathQ-Verify (intake-379): Question Quality Layer

Complementary tool — verifies questions, not answers. Five-stage pipeline:

1. **InstValid**: Contaminated instruction detection (meta-language, answer leaks)
2. **Clean**: Linguistic error detection (typos, grammar, LaTeX breaks)
3. **AtomValidAll**: Atomic condition validation per domain rules
4. **Consistent**: Cross-condition conflict detection (joint satisfiability)
5. **Complete**: Condition completeness validation (can goals be derived?)

### Ablation Results (GPT-o4-mini)

| Stage Removed | Precision Change | F1 Change |
|---------------|-----------------|-----------|
| Stage 1 (Instructions) | -2.47pp | -1.55pp |
| Stage 2 (Linguistic) | **-6.38pp** | -3.36pp |
| Stage 3 (Atomic) | -0.69pp | -0.52pp |
| Stage 4 (Consistency) | -1.97pp | -0.23pp |
| Stage 5 (Completeness) | -1.35pp | **+0.57pp** |

Stage 2 is the most impactful. Stage 5 (completeness) actually hurts F1 — it introduces false positives. **Recommendation: deploy stages 1-4 only, skip completeness check.**

### Hidden Gem: Missing Premises and Overthinking

Referenced paper arxiv:2504.06514 "Missing premise exacerbates overthinking in reasoning models" — flawed questions with missing premises cause models to generate MORE reasoning tokens, not fewer. This is directly relevant to reasoning compression: filtering bad questions reduces token waste at inference time, not just at training time.

### Integration Priority

| Tool | Priority | Effort | Impact |
|------|----------|--------|--------|
| Math-Verify answer verification | HIGH | Low (pip install + 10-line change) | Eliminates up to 40pp underestimation |
| MathQ-Verify question filtering | LOW | Medium (needs LLM calls per question) | Improves dataset quality |

## Accuracy Impact Estimate

Math-Verify reports 0.1328 vs lm-eval-harness 0.0802 on MATH dataset — that's a 66% improvement in detected correct answers. Our current exact-match scoring likely underestimates model capability by a similar factor on math questions.

The 40-point underestimation claim means our T0/T1 sentinel math questions could be reporting models as worse than they actually are. This could affect routing decisions and model selection.
