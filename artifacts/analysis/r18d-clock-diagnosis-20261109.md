# R18-D r3 clock_stable=false diagnosis (2026-11-09, read-only)

Verdict: the definition is wrong for a pinned MI210. The pin worked. The sampler reads the right field, but stores too little to attribute droop.

## 1. Predicate
- residency.py Sampler.proof: `bool(min_sclk) and min_sclk == max_sclk`. Zero tolerance, whole process window (load included), hwmon freq1_input, 0.25 s poll.
- Origin: a1fcc89e1 (2026-08-29) replaced a vacuous pp_dpm_sclk reader. Claim protected: "a measurement across a clock change is partly a measurement of the governor". Not defined in MEASUREMENT.md or measurement/protocols (only before/after clock recording in gpu-cross-device.md).
- Enforced in r3 project.py:54 and adapters/autokernel_r18d_aa.py:113.

## 2. Captures (136 invocations, none null, 108-119 samples each, about 29 s)
- sclk_max: 1700 on 136/136.
- sclk_min: 1580 / 1595 / 1635 (min/median/max). Spread 65-120 MHz.
- r1 under auto: sclk_min 800 on every scored invocation. The pin raised the floor from 800 to at least 1580.
- Only min and max are stored, with no timestamps, so a dip cannot be placed in load versus kernel. pp512 is about 6 s of the 29 s window.
- Level was read once at set (high) and at restore (auto); not per invocation.

## 3. Can it pass?
Yes on other workloads: docs/design/champion-max-performance-20260908.md records 1700 flat on hwmon-era A3B serving launches (24 launches), and a 1695 dip at np=8. On local 27B Q8 pp512 captures: 0/287 true. pp_features shows APCC_DFLL active; `high` caps the clock and does not stop droop.

## 4. Does throughput follow the clock? (120 scored)
- pp512 t/s: 819.7 / 837.2 / 841.0, CV 0.516%.
- r(t/s, sclk_min) = 0.126, Spearman 0.204. Slope 0.087 t/s per MHz, so 0.31% per 30 MHz.
- Medians by sclk_min bin: 1580-1590 836.9 (n=37); 1595-1600 837.0 (n=72); 1605+ 838.4 (n=11).
- Lowest decile (820-828 t/s) sits at ordinary minima (1580-1600).
- auto vs high median 829.3 vs 837.2 (+0.95%): the regime matters, droop within it is not shown to.
- Limit: range restricted to 1580-1610 and whole-window minima. This is no detectable effect, not proof of none.

## 5. Re-grade without inference?
No. Band policy needs clock_trace, request boundaries and level history, which r3 lacks, so band_verdict fails closed (clock_trace_missing). Whole-window min >= 1580 does imply the droop limit, but the band of 120 was set from r3's own maximum, so r3 passing it is circular. r3 is the calibration set.

## Recommendation
Band is already on research origin/main (gpu_clock_policy.json, request_phase_band, 120 MHz, ratify_ak_c9_2_20261109.json named), but only serving.py consumes it. Not applied to the bench path.

One action: wire the bench path and run r4 prospectively. In autokernel_r18d_aa.py:113 and the job's project.py, replace `proof["clock_stable"] is True` with a band verdict over a per-invocation trace; the bench job must record clock_trace, a per-tick level, and request-phase boundaries (or grade the whole window at >= 1580 as a conservative superset).

Human-only: neither file matches human_only_paths.yaml. gpu_clock_policy.json is already signed; no new ratify unless the band changes.
Re-run: one, about 66 min device time (3,941 s in r3), about 75 min wall, GPU exclusive.
Confidence: high on the diagnosis; medium on droop being harmless, which r4's trace settles.
