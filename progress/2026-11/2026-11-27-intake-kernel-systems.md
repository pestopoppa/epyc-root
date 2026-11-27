# November 27 research intake filing

The operator approved the [Stage 3 plan](../../research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md), SHA-256 `2f7f17f2e775fedc0d05fc713e13f6037ebcdf339c3905cb7f4e06817f2cbccb`. The filing bound 19 source dispositions and all 16 recommendations to the approved text and reconciled 17 steering records.

| Task owner | Open tasks filed |
|---|---|
| ROCm kernel authoring | PC-HOSTTRAP-COVERAGE, F32-ROUTER-SPLITK-CENSUS, FATTN-PRIVATE-SEGMENT |
| Quantization and low bit | IQ4-PERM-PLACEMENT |
| AutoKernel loop | VERIFY-F32-GEMV-CENSUS |
| CPU decode roofline | MOE-PHYSICAL-BANK-REPLAY, Q8-Q15-TIE-REPLAY, DRAFTER-CCD-RESIDENCY |
| Harness program | FAIL-GROUP-SPLICE-AUDIT |
| Memory program | MEM-HARNESS-CANDIDATE-REPLAY, MEM-RAW-EPISODE-ARM |
| Routing program | ROUTE-BUDGET-LOOKAHEAD |
| Evaluation tower | SKILL-PAIR-COMPAT-REPLAY |

AutoKernel now carries the generated-kernel golden-output and future sliding-window mixer conditions. Speculative decoding carries the recurrent-depth warm-start condition. These three monitors are prose. The filing added 13 briefs, changed nine existing handoffs, created zero handoffs, flipped zero incumbent checkboxes, and recorded zero explicit declines.

The intake and approved-payload validators passed. The wiki scanner resolved all 19 dives, the [summary](../../research/deep-dives/intake-nov27-kernel-systems/run-summary.md), the plan and the [digest](../../research/deep-dives/intake-digests/2026-11-27-ids-3006-3024.md) at their current content hashes. Each task remains open for its named owner.
