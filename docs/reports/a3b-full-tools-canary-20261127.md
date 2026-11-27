# A3B full-tools canary and exploratory task comparison

A3B produced accepted runtime-test and image-sizing work, and a decode note after guidance, under the qualified full-tools C22 setup. NARIQ, PAW and TU retained substantive errors in the bounded attempts. Main-only was the faster workflow for this set; a material end-to-end benefit from A3B was not established, even with free local tokens.

## Question and scope

The question is whether A3B can do useful real-world work with the best reliable OpenCode-derived setup tested here, what assistance it needs, and whether it benefits the main model when local tokens have zero monetary cost. This is an exploratory task study, not a CPU/GPU benchmark or a promotion gate. The operator requested no formal numerical benefit threshold.

These are calibration replays from pinned repositories, with fresh sessions and matched acceptance; they do not close the same live backlog rows again. The set contains six original pinned tasks: runtime/source-continuity test repair (DS41-W-66), a kernel source map (NARIQ), compile-once candidate analysis (PAW), a decode-dominance note (PFXC), an isolation-check test (TU), and image-size handling (MM). These detailed briefs already provide substantial guidance. A separate fresh W66 light-brief condition removes the supplied repair recipe and matches fresh main-only execution. Repeating a case under a different brief is not another unique task.

Keep three observations separate: an unchanged task check passing, an independent reviewer accepting an artifact, and a stronger controlled regression property holding. They sometimes disagree in this study. Preserve failed attempts and guidance branches rather than replacing them with their successful continuations.

## Tested setup and harness repairs

Both servers use the operator-requested C22 composite source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba` and Qwen3.6-35B-A3B-MTP-Q8_0, with four slots and 131072 context per slot. Thinking runs use the GPU. CPU whole-host serving intentionally overlaps GPU control cores. Production v10 was not modified or used as the canary's serving kernel. Source/build hashes, loaded mappings and during-run residency receipts establish the running binaries; directory names alone do not.

OpenCode 2.2.5 supplies the twelve observed direct tools and its matching Code Mode catalog. Qualification exercises execution error feedback and repair, questions, child sessions, skills, public web access, and protected references. The absence of a stock todo schema is recorded rather than represented as an intentional tool restriction. The earlier restricted-harness results are not full-tools capability evidence.

The effective primary/explore output cap is 32768; nonthinking title generation uses 64. Summary uses the effective SDK-requested 19660, with the primary cap and tools restored after compaction. Native reasoning-history and same-session compaction checks preserve prior reasoning and tool results. Cumulative generated-token accounting is separate from individual completion caps.

Observed failures led to qualified repairs in the following areas:

| Area | Resulting behavior |
| --- | --- |
| Tool and session configuration | Useful tools remain available; syntax errors are actionable tool results, and saved sessions retain their history and references. |
| Caps, streaming and cancellation | Actual request caps, absolute deadlines, reservations, queued calls, terminal exports and late wire receipts are tracked separately. |
| C22 parallel serving | Disabling cross-slot RAM snapshot caching avoids the observed busy-slot restore failure while preserving ordinary in-slot KV reuse. An eight-slot native control qualifies the setting. |
| CPU placement | `--no-mmap`, bounded balanced allocation preparation and live model-scale anonymous-memory checks reject the previously skewed placement. |
| Grader isolation and parsing | Private lock fixtures avoid host-control interference. Class-aware JUnit parsing binds the exact intended test file and rejects foreign or duplicate cases. |
| Acceptance and feedback | Markdown layout, immutable pin resolution, PFX source geometry, MM startup-time environment handling, and TU denial/error distinctions have separate positive and negative controls. |
| Review input and scheduling | Preservation reviewers receive the actual original file and exact patch inside their allowed lane. Review processes use control cores 180–183 rather than the saturated CPU-serving cores. |
| Callback admission | Transient slot-probe timeouts remain bounded pending readiness; dependent work recognizes verified pre-dispatch terminals without fabricating worker receipts. |

These are claims about observed defects and qualified configurations, not proof that no future harness bug exists. A failed negative-control fixture is retained: the first TU V4 null-errno mutant still had a helper that correctly rejected null. The revised fixture changes both relevant layers; the checker itself stays unchanged, and all 14 qualification controls pass.

## Task observations

| Case | Observed A3B result | Main-only comparison |
| --- | --- | --- |
| W66, detailed | ON completed and was accepted. Common-sampler OFF produced an accepted artifact at its deadline. CPU completed after the separately recorded resource-boundary continuation. | Fresh accepted implementation in 74.823704 CLI seconds. |
| W66, light | ON preserves exact fixture-receipt identity. Initial OFF passes both original tests and receives two expert ACCEPT advisories, but a real substitution control shows loss of the original identity assertion. One deterministic diagnostic restores it. | Fresh accepted implementation in 54.217887 CLI seconds, plus 13.8852 seconds of independent checking. |
| NARIQ | Bounded guided outputs retain substantive source/layout errors. Correcting a filename-placement grade does not make the CPU note semantically correct. | Fresh accepted note in 89.898506 CLI seconds. |
| PAW | A clean replay excludes consumed false pin feedback. Neutral self-check followed by one paid semantic correction still leaves unsound reference labels and pinned routing claims. Final source review rejects it despite corrected structure passing. | Fresh accepted analysis in 66.922348 CLI seconds. |
| PFXC | The ON artifact is accepted after deterministic feedback, one paid guidance round and a separate link-only correction. The original two-correction rejection remains recorded. | Fresh accepted note in 111.710705 CLI seconds. |
| TU | CPU paid2 and GPU OFF's two additional CI turns pass the earlier V3 checks but fail source review and the qualified V4 cases. They still misclassify launcher/mount errors or denial evidence. Thinking-ON paid2 repairs both errno checks but still fails V4 and final source review for the mount-error skip. Its native chain uses 25576 generated tokens. | Accepted after 119.841858 seconds for the first attempt and 71.562237 seconds for a measured repair. |
| MM | Later candidates pass original/feasible geometry and startup-environment checks. The separately labelled impossible-cap robustness check still fails. All three final variants receive independent original-scope acceptance after deterministic feedback. Their impossible-cap behavior remains a separate failed robustness condition. | Fresh accepted implementation in 140.117489 CLI seconds. |

No rejected proposal is treated as landed work. Reusing an already accepted main reference is a fallback, not A3B completion or a newly measured takeover.

## Thinking and guidance

The common-sampler W66 light pair is directly interpretable on the same GPU: ON used 23599 generated tokens and 1511.037 seconds; OFF used 14111 and 1133.295 seconds. Both passed the original tests. ON retained the stronger identity check initially; OFF restored it with 1778 more tokens and 30.476 seconds of local model time (39.7 seconds of supervision), for 15889 total local tokens. The repair changes only receipt capture and its exact equality assertion. The normal tests pass and the controlled substitution is caught afterward.

This is a useful bounded example of deterministic guidance, not evidence of intrinsic inability. It also does not establish a general thinking advantage: ON spent more tokens and time, OFF caught up with a small correction, and both independent reviewers accepted the initial weaker OFF artifact even after receiving the original and patch. Their interpretation and the controlled assertion-sensitivity result remain visible separately.

The six initial thinking-ON attempts generated **75745 tokens in total** across all captured model roles: W66 26791, NARIQ 8634, PAW 6745, PFXC 7244, TU 13671 and MM 12660. Their captured receipt counts have no unknown generation counters. The corresponding common-sampler OFF conditions generated at least 50292 tokens, with one unknown receipt in W66; NARIQ and PFXC are fresh supplemental conditions. These totals describe the initial attempts, not the additional guided continuations or reasoning-only tokens. Across all 17 retained thinking-ON task-condition attempts, including guided continuations and the light condition, the deduplicated wire ledger records 222450 generated tokens with no unknown generation receipts. This includes metadata roles; it is not a reasoning-only count.

Other ON/OFF comparisons must keep sampling differences explicit. The recommended OFF profile differs from ON; supplemental OFF common-sampler cases separate that confound. CPU nonthinking runs provide additional work throughput, not a device-based estimate of thinking's effect. Native reasoning-only token splits remain unknown where the wire does not expose them.

## Effort and timing limits

The six-case main-only detailed set contains seven paid CLI turns, including TU's repair: 1226305 input tokens, 1067136 cached, 159169 uncached, and 19368 output including 379 explicit reasoning tokens. Summed CLI execution time is 674.876847 seconds. It is not parallel batch elapsed time or isolated model compute time. The light W66 run is a separate eighth implementation turn.

Paid assistance includes diagnosis, corrective guidance, final acceptance and failed or superseded review calls. In particular, both W66 review generations remain charged; correcting their missing comparison evidence does not erase the earlier bill. Local generated tokens are monetarily free by the experiment's convention, but their latency and resource use remain measured.

Manager review, harness preparation, coordination and historical brief-authoring effort were not isolated into comparable task-execution vectors. A dated goal-counter checkpoint additionally retains 8474625 tokens and 21089 seconds for the long-running manager goal; its accounting definition and mixed work scope differ from API billing, so it is not added to the CLI vectors or used as a matched task-cost denominator. They are not zero and are not included in the fresh CLI totals. Per-arm comparisons must retain cached/uncached input and output separately and must not compare the sum of all alternative A3B arms with one main-only implementation.

A concrete clean comparison is MM ON: its acceptance review used 1910 output and 26502 uncached input tokens, versus 2973 output and 13029 uncached input for fresh main implementation. That saves main generation in the review component but increases uncached input, while the local chain adds 26886 generated tokens and its elapsed time. It is not a net saving established by treating the local tokens as free.

The evidence does not establish a material end-to-end advantage over main-only execution. It does demonstrate useful execution on some constrained tasks and a small deterministic repair that avoids another paid source-guidance round. The final task matrix and performance export will state the narrower supported conclusions, including unresolved cost attribution.

## Evidence and remaining closure

The protocol is [the revalidation plan](../design/taskflow-a3b-revalidation-plan-20261126.md). Byte-preserving checkpoints are under [the artifact directory](../../artifacts/analysis/taskflow-harness-revalidation-20261126/). Raw prior verdicts, qualified migrations, source decisions and measured paid calls are retained rather than overwritten. Final performance includes per-stream latency and streaming TTFT, native prefill/decode, cache, MTP, resource samples and explicit unknowns; aggregate phase timing estimates must be labelled as estimates.



The final export covers **18 serving epochs, 62 attempts and 1061 unique request receipts**, with zero unreceipted archives and zero read warnings. It retains 514121 known generated tokens and four unknown generation receipts. Paired MTP counters record 319920 accepted of 387019 proposed tokens; five receipts lack a complete pair. The estimated aggregate phase-union rates are 47.666 decode and 548.103 prefill tokens/s across the mixed campaign, not a hardware ranking or exact phase-timestamp measurement. Per-stream rates and both upstream and delivered streaming TTFT are exported; tiny native timing intervals can produce large rate outliers.

Forty unique paid executions comprise eight implementation turns and 32 assistance/review turns. The whole experimental inventory totals 3259.404165 summed CLI seconds, 7438036 input tokens (6365696 cached, 1072340 uncached), and 56853 output tokens including 2246 reasoning tokens. That sum spans alternative arms and is **not** an effectiveness comparison against one implementation. Use the [per-alternative paid-cost table](../../artifacts/analysis/taskflow-harness-revalidation-20261126/final-20261127/paid-final-40/SUMMARY.md) instead.

The [per-request CSV](../../artifacts/analysis/taskflow-harness-revalidation-20261126/final-20261127/performance/export/REQUESTS.csv), [per-attempt CSV](../../artifacts/analysis/taskflow-harness-revalidation-20261126/final-20261127/performance/export/TASKS.csv), compressed full report and exact-patch owner receipts accompany the [final evidence audit](../../artifacts/analysis/taskflow-harness-revalidation-20261126/final-20261127/audits/completion-audit-final/REPORT.md). The immutable measurement snapshot has nine accepted artifact variants across repeated conditions, not nine unique tasks. A dated owner addendum closes the separate MM robustness attempt as rejected without changing its earlier snapshot display state or transferring acceptance from another patch.

Canonical TU/MM checks now include the qualified parser, error-denial, under-cap byte-identity, feasible geometry and fresh-startup environment cases. Their source and test hashes match the saved **47-pass** focused/integration receipt. Earlier unchanged full-tools/transport/CPU-placement tests and native controls remain separately bound in the completion audit; they were not needlessly rerun.

Both owned C22 servers exited cleanly after all eight slots were idle and all eight callback locks were acquired. Captured CPU/GPU processes and their controller/holder were confirmed gone; the cleanup receipt records no KFD PIDs. The existing remote-control app server remained live. No production kernel or unrelated process was stopped or changed.

The report is a committed-conclusion observation of this campaign. Existing prospective Taskflow source-wiring tasks remain explicit; no retrospective native measurement warrant or new grading ladder is asserted. Raw KEEP-retained scratch roots and their hashes remain recorded for deeper audit, while byte-preserving compressed evidence and readable exports are committed here.

Next: Taskflow owners retain the tested full-tool configuration, actionable CI feedback, exact comparison evidence and independent source acceptance when dispatching similar work; wider routing requires its own task evidence.
