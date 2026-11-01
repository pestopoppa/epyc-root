# KVU-12.5 proposed verdict review — 2026-11-01

The proposed `SPLIT_BETTER` verdict is **rejected as filed**; the one-quarter task remains open. This is a review of existing records, not a new run or a finding of equal performance.

The operator-approved handoff calls for one CPU quarter. The predeclaration names q3, CPUs 72–95 and 168–191 with `-t 24`, while noting a possible full-host recipe. The retained `launch.out` reports a claim on q0–q3, CPUs 0–95 and 96 threads. Both arm `waves_capture.jsonl` records independently report `cpu_list: 0-95`, `threads: 96`. Thus the handoff's statement that this particular run used q3 and 24 threads is incorrect. The row mentioned a full-host fallback, but these records alone do not establish that the quarter-scoped operator decision was amended.

The predeclared np8 rule also requires a within-launch wave-range term when it exceeds the anchor floor. The generated `VERDICT.json` explicitly says this term was omitted pending manual recomputation. Unified decode waves 1–3 have per-stream medians 1.345, 1.615 and 1.230 tok/s; their range is 0.385 tok/s. Dividing by the median (1.345) gives 28.62%; doubling gives 57.25%, exceeding the reported 44.49% stream deficit and the anchor-based 23.86% threshold. Even using the maximum wave as denominator gives a 47.68% doubled range. The predeclaration does not specify the normalization, so this is an explicit sensitivity check, not a new formally ratified noise rule. The sum-wave values are 10.49, 11.49 and 10.36 tok/s. The predeclared `SPLIT_BETTER` rule requires both decode gaps to exceed their thresholds; the unreviewed anchor-only verdict cannot establish that.

Evidence under `/mnt/raid0/llm/tmp/cal-1025/kvu12-5-np8/`:

- `PREDECLARATION.md`, `VERDICT.json`, `launch.out`.
- Unified `out/k5_unified_np8_pool524288_L64k_depth/unified_np8_pool524288/64k_depth/waves_capture.jsonl`, SHA-256 `aa57662b5063d0a69e93bbdd81b561da1f377acde2e204c0fa19ab499f64b126`.
- Split `out/k5_split_np8_slot65536_L64k_depth/split_np8_slot65536/64k_depth/waves_capture.jsonl`, SHA-256 `3710eed93e666f9dc7a5290ffc16227250041c058b5a3fc092f7d68935a2c8e7`.

The original measurements and proposed verdict remain unchanged. A successor quarter-scoped row needs a prospective wave-range normalization and keeper admission; no production decision follows from this review.
