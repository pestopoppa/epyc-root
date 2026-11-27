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

The intake and approved-payload validators passed. The wiki scanner resolved all 19 dives, the [summary](../../research/deep-dives/intake-nov27-kernel-systems/run-summary.md), the plan and the [digest](../../research/deep-dives/intake-digests/2026-11-27-ids-3006-3024.md) at their current content hashes. All 13 tasks were open at filing.

## Kernel priorities after local measurements

The [November 26 filing](2026-11-26-intake-nov26-kernels.md) covered 24 sources. Its short-row census and sampler-tie questions intersected the November 27 verify, router and Q15 proposals. The following decisions use the kernel owner's published experiment records. Stage 4 on main records the original assignments.

| Question | Local evidence | Decision |
|---|---|---|
| Does cheaper Q8 GEMV conversion improve served decode? | Vector instructions per KiB fell 12.9%. At width eight, bandwidth rose 0.46%. Across eight paired MI210 blocks the served speedup was 0.998× (95% CI 0.990–1.006), below the 1.01× threshold. All arms passed 46/46 operator tests. [Gate result](https://github.com/pestopoppa/epyc-root/blob/949920327794595fc90897dc2a486fe5df5aa19b/research/deep-dives/q8-gemv-convcore-20261127/README.md) | NO_KEEP. Retain V5I. |
| Can short rows or a skinny F32 router move request time? | Dense 27B dispatched zero F32 weight matmuls across 156 verify forwards. Eliminating both A3B Q8 short-row groups would recover at most 0.49% of single-request decode. The 256-row router already benefits from chunking. The C21 one-row shared gate cost 0.339–0.342 ms per verify forward. [Dispatch census](https://github.com/pestopoppa/epyc-root/blob/64c43a72b7197cbabdf5a74b6a7aa9ecf423ca1a/research/deep-dives/mi210-matmul-census-20261127/README.md) | A 1.01× served result would require removing about 72% of the one-row cost, including any new reduction launch. Revisit if C22 traces show a larger share or fusion can remove adjacent launches. |
| Does Q15 fix held-out greedy decisions cheaply? | Native Q8 and Q15 both preserved 48/48 decisions at 1, 8 and 24 threads. Q15 repaired five engineered flips and one calibration flip. The full head was 6.2% slower at one thread. The 24-thread gain over matched Q8 was within repeat noise. Equal logits also produced different tokens after sampler filtering. [Head replay](https://github.com/pestopoppa/epyc-root/blob/64c43a72b7197cbabdf5a74b6a7aa9ecf423ca1a/artifacts/compute/q8-q15-tie-replay-20261127/README.md) · [Sampler control](https://github.com/pestopoppa/epyc-root/blob/64c43a72b7197cbabdf5a74b6a7aa9ecf423ca1a/data/spec-filter-ties-20261127/README.md) | NO_KEEP. Preserve the separate pre-sampler and post-sampler controls. |
| Does a constant V-load bound eliminate attention scratch? | The targeted V load already has a fixed bound. The audited A3B prefill and 27B RF6 verify kernels used zero scratch. A separate two-column A3B kernel had a 144-byte private frame. Its 5.76 ms covered all work in 33 dispatches. [Dispatch and code-object audit](https://github.com/pestopoppa/epyc-root/blob/64c43a72b7197cbabdf5a74b6a7aa9ecf423ca1a/research/deep-dives/fattn-private-segment-20261127/README.md) | Close the constant-bound treatment for the audited paths. Scratch cost in the two-column kernel is unmeasured. |

**Give the next authorized MI210 window to AP-W66-PAIR.** Among 140 actual C22 serving receipts, OFF 56 spent 138.24 s in fresh prefill and overlapped ON 28, which spent 164.59 s decoding. The synthetic CPU reversal saved 5.65–9.14 s on the target by retaining a longer prefix. It changed the input and established neither real-task quality nor a GPU speedup. Replaying each archived request against itself can distinguish prefix cost, contention and a persistent isolated decode penalty. Only the last outcome calls for kernel profiling. [Trace](../../docs/reports/autopilot-w66-trace.md) · [CPU control](../../docs/reports/autopilot-w66-cpu-prefix-q012.md) · [Replay plan](../../docs/reports/autopilot-w66-replay-plan.md).

Next: RTG-02 replays OFF 52/56 and ON 28/29 alone and with overlapping peers under matched slot history in the next authorized MI210 window. Stop on a stable difference beyond repeat noise or at three matched pairs per target.
