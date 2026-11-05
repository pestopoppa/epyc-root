# 2026-11-05 — handoff fable5-window2-findings-05c-mi210-lever

## 00:25Z — Filed ROCm 10.1 stage-1 NO-GO with valid paired evidence.

Q38P-3: r2 rc0 stage-1 NO-GO: B/Bp decode ratios 1.0867/1.1032 and pp512 0.9891/0.9873, while pp2048 0.9763/0.9760 falls below 0.98. Three B/C and four Bp/C valid pairs; excluded foreign-KFD failures. pp512 at depth 16k 0.7729/0.7724 descriptive. Raw evidence preserved; no production or stage-2 verdict.

## 01:29Z — Filed NPD r2 with scoped measured ratios and missing residency evidence.

NPD1-STEP2: r2 ABBA ratios cross the idle reject threshold (A1/A0 1.645, 1.600), while TTFT and contention criteria pass; filed inconclusive because no in-window nonzero own-PID VRAM or mapped HIP evidence is recorded. Filtered grant records and raw packet preserved; prospective capture and reviewable instrumentation delegated. No serving change or gate decision.

## 03:55Z — Prepare NPD1-STEP3 idle decode comparison

Prepared NPD1-STEP3 CPU-only store comparison for Q38FN: matched t48 and batch settings, four ABBA launches, native decode timing and bounded smoke. Both stores identify source 181483cfc; checked server and CPU-library digests against build manifests. The two formerly routed PF1 and M4 rows were dropped or cancelled by the operator.

## 04:01Z — Prepare ROCm spec-off decode comparison

Prepared Q38P-3a speculation-off same-frame ABBA diagnostic on the Qwen3.8-27B Q8_0, comparing C5 ROCm 6.2 with its ROCm 10.1 build. The comparison is exploratory and profiling follows only if its futility rule permits; no promotion verdict is claimed.

## 04:16Z — File Q38P-3a result and restore Q38P-4 inputs

Filed q38p3a-specoff-abba-20261105 rc0: four valid launches, B/C ratios 0.98508584 and 0.98815882, geometric mean 0.98662113 below the 1.02 futility threshold; stop the conditional profile. Native records and sources retained at data/mi210/q38p3a-specoff-result-20261105. The producer reported digest checks but did not retain observed digest values per sample. NPD1-STEP2 unchanged-config rerun is not scheduled before armed STEP3 diagnosis; a draft under /mnt/raid0/llm/tmp/fable5-window2-findings-05c-mi210-lever/npd1-step2-r3 was not smoked or reviewed. Q38P-4 full-token parity remains unready: prior probe compared only prefixes with unmatched sampling settings, its GGUF and pinned vLLM image were reaped. Exact image restoration is running with image-ready/image-failed event registrations. On image arrival, recreate a detached worktree of c72ec82f5417bb2937310326120f149b665e8400 and regenerate BF16 GGUF from /mnt/raid0/llm/models/Qwen3-4B-Instruct-2507, then remove worktree, construct a controlled token-parity packet and pass publish_row.py smoke. No Q38P-4 parity spec has been completed or published.

## 04:24Z — NPD1-STEP3: await the already-qualified idle decode diagnostic before choosing the corrective path.

NPD1-STEP3: the idle decode ABBA diagnostic `npd1-step3-idle-abba-20261105` passed publisher smoke and is grantable; its result determines the corrective path. The stale PF1 refinement and Q38 recipe rows are explicitly dropped and cancelled respectively in the handoff and are not being requalified. [no-belief: scheduling state, no measurement]
