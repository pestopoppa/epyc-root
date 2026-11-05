# 2026-11-05 — handoff fable5-window2-findings-05c-mi210-lever

## 00:25Z — Filed ROCm 10.1 stage-1 NO-GO with valid paired evidence.

Q38P-3: r2 rc0 stage-1 NO-GO: B/Bp decode ratios 1.0867/1.1032 and pp512 0.9891/0.9873, while pp2048 0.9763/0.9760 falls below 0.98. Three B/C and four Bp/C valid pairs; excluded foreign-KFD failures. pp512 at depth 16k 0.7729/0.7724 descriptive. Raw evidence preserved; no production or stage-2 verdict.

## 01:29Z — Filed NPD r2 with scoped measured ratios and missing residency evidence.

NPD1-STEP2: r2 ABBA ratios cross the idle reject threshold (A1/A0 1.645, 1.600), while TTFT and contention criteria pass; filed inconclusive because no in-window nonzero own-PID VRAM or mapped HIP evidence is recorded. Filtered grant records and raw packet preserved; prospective capture and reviewable instrumentation delegated. No serving change or gate decision.

## 03:55Z — Prepare NPD1-STEP3 idle decode comparison

Prepared NPD1-STEP3 CPU-only store comparison for Q38FN: matched t48 and batch settings, four ABBA launches, native decode timing and bounded smoke. Both stores identify source 181483cfc; checked server and CPU-library digests against build manifests. The two formerly routed PF1 and M4 rows were dropped or cancelled by the operator.

## 04:01Z — Prepare ROCm spec-off decode comparison

Prepared Q38P-3a speculation-off same-frame ABBA diagnostic on the Qwen3.8-27B Q8_0, comparing C5 ROCm 6.2 with its ROCm 10.1 build. The comparison is exploratory and profiling follows only if its futility rule permits; no promotion verdict is claimed.
