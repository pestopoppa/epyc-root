# KPF-18 group-3 model-free qualification results

Four rows completed rc 0 on 2026-11-05 and satisfy their scoped rules:

- [Later slot queries](later-slots.json): 12 synthetic HTTP controls with joined peers; the copied task-binding and postcancel-idle query paths were exercised. The retained query-2 timeout is swallowed before the fixture's terminal deadline propagates.
- [Residency correlator](residency-correlation.json): all 18 original/private-corrected synthetic outcomes matched. This is a standalone helper, not live residency.
- [RAM admission helper](ram-admission.json): all 28 synthetic comparisons matched and owned-child cleanup was verified. The corrected helper refuses a future-only own grant; the independent rowflow boundary remains separate.
- [Output supervisor](output-supervision.json): six isolated controls passed with captured processes absent. Sampled overshoot is reported; unsampled peak and hard quota are unknown.

These results do not establish integrated candidate behavior, native cancellation, task release, live host/GPU admission, or a historical layout-control verdict. All inputs are software fixtures and original historical results remain unchanged.
