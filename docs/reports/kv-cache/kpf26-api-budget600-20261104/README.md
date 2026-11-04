**UNSUBMITTED / FUTURE ONLY.** Original API OFF/ON observations answer the scoped diagnostic; no600s successor is needed. See `../kpf26-api-results-20261104/README.md`.

# KPF-26 API explicit-budget successor packet

Fresh generation `rtg58-kpf26-api-{off,on}-diag-r2-20261104` continues the original off/on lineages after both original IDs became terminal. Original published scratch and READY manifests were not changed, and prior API attempt results remain in their original paths. The model, source pin, flags, scope/cohort, required-term scorer and diagnostic-only decision rule are preserved. This packet changes private diagnostic timeout configuration, not orchestrator source.

Confirmed shared full-job cause from the code OFF run: native per-call cap180 and request fraction0.4 clamped its requested600s scout budget; long native prefill had not yet completed before cancellation. This successor configures ONLY the private API-process `scout_stage.PER_CALL_TIMEOUT_S=600.0` after asserting native cap180/fraction0.4. The fraction stays0.4. Rebinding sets route timeout1800s (and manifest arm timeout1800), preserving scout budget600; min(600,0.4*1800)=600 before elapsed request overhead. Actual effective budget is the native scout report's `budget_s`, not inferred from this arithmetic. The API writes its effective policy data to each run's `runtime-policy.json`.

The original full API diagnostic completed descriptively on both earlier IDs; this packet makes no claim about their scored outcomes without their owner's result review. It is a prospectively explicit-budget diagnostic and cannot establish timing, correctness, KPF-26 gate, or deployment. Native one-token smoke stays isolated before API startup and cannot satisfy the full two-scout task.

Offline validation: three policy tests pass, including cap/fraction integrity and packet hash/scorer preservation; three shell scripts pass bash syntax and three Python scripts compile. The original reviewed native-smoke helper and preflight remain byte-preserved except updated run paths. No model inference, smoke, publication or grant occurred during preparation. Main publishes each fresh-ID spec.

Task scratch: `/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-api-budget600-20261104/`. Specs estimate2400s and window3000s with the existing900s minimum; source checks, binary checks and ggml linkage remain fail closed. Binary input directory is a symlink to unchanged retained binaries; no source checkout was copied.
