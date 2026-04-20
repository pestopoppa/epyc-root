# pi-autoresearch MAD Scoring — Deep Dive

- **Source**: https://github.com/davebcn87/pi-autoresearch
- **Date**: 2026-04-20
- **Intake ID**: intake-421
- **Verdict (initial)**: already_integrated

---

## 1. What MAD Confidence Scoring Does

Median Absolute Deviation (MAD) is a robust measure of statistical dispersion. Unlike standard deviation, it's resistant to outliers. pi-autoresearch uses it to answer: "Is this benchmark improvement real, or is it noise?"

**The formula**:
```
MAD = median(|x_i - median(X)|)
```

**Decision rule** (pi-autoresearch's implementation):
1. Run benchmark N times (minimum 3)
2. Compute MAD of the measurements
3. If the improvement exceeds `k * MAD` (typically k=2-3), it's a real improvement
4. Otherwise, it's within noise — don't accept the change

## 2. Current Safety Gate — What's Missing

Our `safety_gate.py` (350 lines) checks:
- Quality floor (hard minimum)
- Regression vs baseline (relative: -5% threshold)
- Per-suite regression (-0.1 absolute threshold)
- Routing diversity cap
- Throughput floor (80% of baseline)
- Proxy-only improvement detection

**What it does NOT do**: Statistical noise filtering. The thresholds are fixed constants. If a trial produces quality=2.01 and baseline is 2.00, it's "better" — even if that 0.01 difference is entirely noise.

**Where this bites us**: The autopilot runs benchmark evaluations that have inherent variance from:
- LLM inference non-determinism (temperature > 0)
- Quality scoring variance (judge model's own stochasticity)
- Routing randomness (tie-breaking in difficulty estimation)

A 0.01 quality delta could be noise or signal — currently we can't distinguish.

## 3. Where MAD Fits in the Autopilot

```
Trial produces config → EvalTower runs benchmark → EvalResult returned
                                                         ↓
                                                   SafetyGate.check()
                                                         ↓
                                              Accept / Reject / Rollback
```

MAD scoring slots into the `check()` method, specifically at step 2 (regression vs baseline). Instead of comparing a single measurement against a fixed threshold, we'd compare against the **statistical spread** of recent measurements.

## 4. Implementation — It's ~15 Lines

The change touches `safety_gate.py` in two places:

### 4a. Track measurement history

Add a rolling window of recent quality measurements to `SafetyGate`:

```python
from collections import deque
import statistics

class SafetyGate:
    def __init__(self, ...):
        ...
        self._quality_history: deque[float] = deque(maxlen=10)
```

### 4b. Add MAD-based noise filter

In the `check()` method, after computing `relative_delta`:

```python
def _is_significant(self, new_quality: float) -> bool:
    """MAD-based significance test: is the delta larger than noise?"""
    if len(self._quality_history) < 3:
        return True  # Not enough data — accept at face value
    
    median_q = statistics.median(self._quality_history)
    mad = statistics.median(
        abs(x - median_q) for x in self._quality_history
    )
    
    if mad == 0:
        return new_quality != median_q  # Zero variance — any change is significant
    
    # Normalized deviation: how many MADs away is the new measurement?
    z_mad = abs(new_quality - median_q) / (mad * 1.4826)  # 1.4826 = consistency constant
    return z_mad > 2.0  # Significant if >2 MADs from median
```

### 4c. Integration point

In `check()`, wrap the improvement acceptance:

```python
# After computing relative_delta...
if relative_delta > 0:
    # Improvement detected — but is it real?
    if not self._is_significant(result.quality):
        warnings.append(
            f"Improvement within noise: {result.quality:.3f} vs "
            f"median {statistics.median(self._quality_history):.3f} "
            f"(MAD: {mad:.4f}, z={z_mad:.1f})"
        )
    
# Always record
self._quality_history.append(result.quality)
```

### 4d. Persistence

The quality history needs to survive autopilot restarts. Add to `autopilot_state.json`:

```python
def save_state(self) -> dict:
    return {"quality_history": list(self._quality_history)}

def load_state(self, data: dict) -> None:
    self._quality_history = deque(data.get("quality_history", []), maxlen=10)
```

## 5. What This Prevents

| Scenario | Without MAD | With MAD |
|----------|-------------|----------|
| Trial produces quality 2.01 vs baseline 2.00 | Accepted as improvement | Warning: within noise (z=0.4) |
| Trial produces quality 2.10 vs baseline 2.00 | Accepted | Accepted (z=4.2, significant) |
| Noisy benchmark oscilates 1.95-2.05 | Constant flip-flopping of "better/worse" | Only accepts when signal exceeds noise band |
| Autopilot burns compute on noise-level "improvements" | Yes — false positives waste T1/T2 evals | No — noise filtered at gate level |

## 6. Why Not Standard Deviation?

MAD is preferred over std dev because:
1. **Outlier resistance**: One bad run (model crash, OOM, etc.) doesn't blow up the variance estimate
2. **Works with small N**: Meaningful with as few as 3 samples (std dev needs ~30 for normality)
3. **Matches our data**: Benchmark scores have occasional outliers (judge model failures, partial responses)

## 7. Edge Cases

- **First 3 runs**: Not enough history → skip MAD check, use current threshold-based logic
- **Baseline update**: When baseline updates, quality history should NOT be cleared (it represents noise characteristics, not absolute level)
- **Different tiers**: T0 (10 questions) has more noise than T2 (500 questions). Could have tier-specific MAD thresholds — but starting with a single global window is fine

## 8. Cost of Not Adding This

Every autopilot session currently risks:
- Accepting noise-level "improvements" → wasting T1/T2 eval budget on false positives
- Pareto archive accumulating configs that aren't actually better than existing ones
- Strategy memory learning from false signals

The fix is ~15 lines of code + ~5 lines of persistence. No external dependencies (Python `statistics` module is stdlib).

## 9. Verdict Delta

| Aspect | Initial Assessment | Post Deep-Dive |
|--------|-------------------|----------------|
| Verdict | already_integrated | **adopt_component** — the MAD scoring specifically is NOT in safety_gate |
| Integration effort | "1-line addition" | **~20 lines** + persistence hook (still trivial) |
| Impact | "file for future reference" | **Add now** — prevents false positive waste every autopilot session |
| Risk | None identified | None — purely additive, gate only emits warnings (not blocking violations) |

**Updated verdict: `adopt_component`** — Implement MAD-based noise filtering in `safety_gate.py` immediately. No reason to defer.
