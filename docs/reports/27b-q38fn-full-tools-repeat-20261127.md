# 27B GPU and Q38FN CPU full-tools repeat, November 27

All **49 native task attempts** closed, including **28 of 28 initial conditions**. Main accepted seven variants spanning three fixtures. Q38FN CPU thinking OFF produced two accepted implementations on the original brief and within the original window, MM-5 and detailed W66. Neither used corrective guidance. The 27B GPU initial arms had no acceptances. Two subsequent 27B GPU MM attempts earned acceptance within 30 minutes, once with case-neutral execution guidance and once on the original brief in a lane that delivered no tool warning. Together, the results describe the observed model, harness, sampling, prompt and wall budgets. They do not establish an intrinsic model or hardware ranking.

## Protocol

The six pinned real-task fixtures and the separate accurate-light W66 brief ran with thinking OFF and ON on each model. The GPU route served Qwen3.8-27B Q8_0 with DFlash2. The CPU route served Qwen3.8-Flash-Next UD-IQ4_XS with shared MTP, with all three model shards bound to the serving identity. Both used verified kernel-store binaries built from **C22 `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`**, four physical slots each and 131,072 context tokens per slot.

OpenCode 2.2.5 exposed edit, execute, glob, grep, question, read, shell, skill, subagent, webfetch, websearch and write, with the CodeMode catalogue. There was no six-read or thirty-turn limit and no extra task-specific skill bundle. The common setting was temperature 0.6, top-p 0.95, top-k 20, min-p 0, repeat penalty 1, presence penalty 0 and seed 223355. Primary requests had a 32,768 output-token cap and each condition had a 120,000 generated-token allowance. Original phase windows were 1,800 s GPU and 3,600 s CPU. Thinking ON used the native default xhigh unless the supplement explicitly set another effort. The earlier A3B work used a different effort and retry workflow, so its acceptance counts are descriptive context.

Acceptance required deterministic checks, independent exact-source review and explicit main adoption. Budget expiry remained censored against the declared window even when it left a reviewable artifact. A late-artifact continuation, a fresh retry with paid planning, and a fresh session carrying a prior artifact each have their own trace and cost. This was a replay on pinned source, without landing duplicate task implementations.

## Original condition matrix

| Fixture / brief | 27B GPU OFF | 27B GPU ON | Q38FN CPU OFF | Q38FN CPU ON |
|---|---|---|---|---|
| DS41-W-66, detailed | Expired, no edit | Expired, no edit | **Accepted**, normal completion | Expired, no edit |
| DS41-W-66, accurate light | Expired, no edit | Expired, no edit | Expired, no edit | Expired, no edit |
| TU-GR-1 | Normal candidate, checker failed | Expired, no edit | Expired, partial | Expired, no edit |
| MM-5 | Expired, no edit | Expired, no edit | **Accepted**, normal completion | Expired, partial |
| PAW-5 | Expired, no edit | Expired, no edit | Expired, no edit | Expired, no edit |
| NARIQ-LIBTRELLIS-MAP-1 | Expired, no edit | Expired, no edit | Expired, no edit | Expired, no edit |
| PFXC-A3 | Expired, partial | Expired, no edit | Expired, partial | Expired, partial |

Initial outcomes total three normal candidate returns (two accepted, one failed), five budget-closed partial artifacts and twenty budget-closed no-edit attempts. See `QUALITY.json` for per-attempt timestamps, grades, withdrawn results and owner dispositions.

## Continuations and driving checks

| Condition | Observed result and help |
|---|---|
| GPU PFXC-A3 OFF | **Accepted** after same-session CI correction, source diagnosis and main arithmetic reminder. Two paid source reviews total, including diagnosis. Worker phases 1,802.315 + 1,346.068 + 340.891 s. |
| CPU MM-5 ON | **Accepted** after one same-session CI correction for missing tests and one final paid review. The initial 3,605.160 s artifact remains partial. Its correction took 2,493.799 s, with 4,810 observed generated tokens and one unknown receipt. |
| GPU MM-5 OFF, generic execution guidance | **Accepted**, normal completion in 1,472.812 s with 7,698 generated tokens, six reads, zero repeated tool inputs and one paid review. No task-specific corrective help. |
| GPU MM-5 OFF, original brief with broader repeated-tool warning enabled | **Accepted** after behavioral PASS and one independent source review. Normal completion in 1,602.882 s with 12,684 generated tokens. The audit in `tool-warning-v2-owner-acceptance-prep` found one plugin load, at most two occurrences of any exact tool input and zero warning markers or delivered advisories. |
| GPU MM-5 OFF, original brief extended to 60 min | Expired without edits at 3,602.390 s. The initial 30-minute attempt also made no edits and used an exact tool input up to 17 times. |
| GPU MM-5 OFF, original brief with direct-read warning | Expired without edits. The run repeated shell inspections, which the direct-read guard did not cover. |
| GPU detailed W66 ON | Generic execution guidance at native xhigh, medium and low each expired without an edit. The unchanged-brief medium control also expired without edits. Neither the separate paid planning retry nor the registered sampler supplement produced an edit. |
| CPU PAW-5 ON | Separate paid planning retry and registered sampler supplement expired without edits. |
| GPU TU-GR-1 OFF | Final guided candidate had old-checker PASS and paid source ACCEPT. Main rejected it after the amended checker found a classification gap for an injected executable-launch permission error mentioning `/proc/self/`. Eight contained controls retained the pinned main-only positive and rejected the exact GPU candidate and an overly broad synthetic classifier. |
| CPU TU-GR-1 OFF | **Rejected** after one bounded same-session CI correction. The 3,603.563 s phase left a budget-closed patch with 25,592 observed generated tokens and one unknown receipt. V5 failed because the launcher overmounted the staged child script, and source audit found an overbroad refusal classifier. The chain exhausted its 120,000-token allowance. No paid review was needed. |
| CPU PFXC-A3 ON | Expired without a reviewable patch after 3,601.807 s. A fresh session carried the frozen initial document and paid diagnosis, with prior charged allowance debited. This phase recorded 13,843 observed generated tokens, one unknown receipt and 46,611 charged tokens. No session history transfer or measured slot-cache equivalence. |
| CPU PFXC-A3 OFF | **Accepted** on same-session repair after a fresh artifact-carryover phase. That phase took 1,021.588 s and 6,317 generated tokens, passed V7 and failed paid review on unsupported selection-bias claims. The repair completed in 531.848 s with 3,891 generated tokens and no unknowns, passed V7 and earned source ACCEPT. The chain used one CI correction, two paid diagnoses, a main factual reminder and three paid reviews total. The original budget-closed artifact and fresh-phase rejection remain recorded. |

The two successful fresh GPU MM trajectories disprove an inability to deliver this fixture under the tested setup. An original-brief repeat succeeded with no actual warning delivery, so the evidence does not establish a warning benefit or isolate the generic prompt's effect from sampling, slot/cache history and concurrency. W66 supplied no positive evidence for the tested effort and generic-guidance variants.

A separate native qualification sent matched cap-128 GPU requests differing only in the reasoning budget. Budget 0 returned 254 visible reasoning characters; the default returned 230. Both exhausted the cap with no final content. Two additional cap-128 controls set `speculative.n_max=0` and verified zero draft proposals. Budget 0 and the default each returned 255 reasoning characters. The zero-budget control failed with and without DFlash on C22. No 4,096-budget quality arm was launched. Visible reasoning characters and separately reported native token counters are distinct quantities.

## Performance

The initial arms charge title and compaction requests to their parent task. Latencies are medians in seconds. Rates are tokens per second, first per-request medians and then approximate aggregate rates over the union of native phase intervals.

| Initial arm | Forwarded / failed | Client wall | TTFT upstream / delivered | Prefill / decode median | Prefill / decode aggregate | Draft accepted / proposed |
|---|---:|---:|---:|---:|---:|---:|
| GPU OFF | 325 / 6 | 16.164 | 15.802 / 16.031 | 181.049 / 7.227 | 282.941 / 8.773 | 39,720 / 73,731 |
| GPU ON | 68 / 7 | 74.711 | 16.793 / 23.607 | 231.869 / 5.392 | 293.648 / 9.381 | 48,282 / 109,116 |
| CPU OFF | 307 / 7 | 32.300 | 27.899 / 29.492 | 63.526 / 6.081 | 119.175 / 5.167 | 43,640 / 54,281 |
| CPU ON | 123 / 7 | 88.731 | 11.719 / 14.245 | 110.211 / 3.926 | 132.527 / 5.350 | 47,603 / 66,298 |

| Initial arm | Actual thinking ON / OFF | Known generated tokens | Unknown generation receipts | Unknown reasoning-token receipts |
|---|---:|---:|---:|---:|
| GPU OFF | 0 / 325 | 50,551 | 2 | 325 |
| GPU ON | 61 / 7 | 63,934 | 0 | 68 |
| CPU OFF | 0 / 307 | 59,091 | 0 | 307 |
| CPU ON | 116 / 7 | 70,465 | 0 | 123 |

Thinking ON produced no additional unaided acceptances in this sample. CPU MM ON became acceptable after a missing-test reminder, while its OFF counterpart had already completed unaided. The original ON arms generated 63,934 known tokens on GPU and 70,465 on CPU, including their title requests; separate reasoning-token counts were not reported. These observations do not establish a thinking benefit or a general absence of one.

`COMMON-PERFORMANCE.json` includes metric sample counts and the actual thinking setting split. The full proxy inventory contains 2,027 receipts, with 2,003 forwarded, 43 forwarded failures and 24 blocked or otherwise unforwarded. Four direct native budget controls are archived separately from the proxy inventory.

The machine-readable performance summary and native request JSONL/CSV contain per-attempt, per-mode and physical-stream counts, client and upstream latency, upstream and delivered TTFT, native prefill and decode rates, cache counts, jointly observed draft/accepted counts, failures, cancellations and concurrent resource samples. Prefill/decode aggregates use approximate unions of right-aligned native phase durations and include observed post-terminal drain. Worker wall time includes tools. Native counters missing at interruption remain unknown. Charged allowance includes reservations and is separate from observed generation.

## Paid work and elapsed time

The valid main-only comparator was reused with **zero new implementations and zero new model calls**. It covers seven case/brief conditions and eight implementation calls, including the failed first TU implementation and its paid repair.

| Paid implementation scope | CLI wall, s | Input | Cached input | Uncached input | Output | Reasoning subset |
|---|---:|---:|---:|---:|---:|---:|
| Historical main-only, six detailed cases | 674.876847 | 1,226,305 | 1,067,136 | 159,169 | 19,368 | 379 |
| Historical main-only, all seven including accurate-light W66 | 729.094734 | 1,430,897 | 1,256,832 | 174,065 | 20,498 | 401 |

| Matched fixture | Local worker wall, s | Local paid source-review wall, s | Local review uncached input / output | Historical direct wall, s | Historical direct uncached input / output |
|---|---:|---:|---:|---:|---:|
| MM-5, CPU OFF initial | 2,615.949 | 20.04 | 29,513 / 456 | 140.117489 | 13,029 / 2,973 |
| MM-5, GPU OFF generic | 1,472.812 | 21.21 | 23,446 / 471 | 140.117489 | 13,029 / 2,973 |
| MM-5, GPU OFF warning-enabled repeat | 1,602.882 | 20.91 | 38,085 / 460 | 140.117489 | 13,029 / 2,973 |
| W66 detailed, CPU OFF initial | 3,393.222 | 28.48 | 17,774 / 813 | 74.823704 | 40,204 / 2,056 |
| PFXC-A3, GPU OFF guided chain | 3,489.274 | 37.31 | 43,069 / 1,058 | 111.710705 | 23,850 / 5,051 |
| PFXC-A3, CPU OFF guided chain | 5,155.387 | 82.88 | 79,456 / 2,291 | 111.710705 | 23,850 / 5,051 |

Each MM row compares a different workflow against the same historical implementation. Each PFX row adds its initial censored phase and both guided continuations, with main reminders charged to management. The table excludes other failed/supplemental arms and the shared overhead below. Historical direct wall/usage covers implementation. Historical review, setup and management were not separately metered in that baseline.

`PAID-CALLS.json` accounts for 15 distinct paid review and planning threads, including rejected candidates and false-positive advice. Advice reused for a correction is counted once. All usage fields were known, with no unreported executions.

| Current paid calls | Calls | CLI wall, s | Input | Cached input | Uncached input | Output | Reasoning subset |
|---|---:|---:|---:|---:|---:|---:|---:|
| Independent source review | 13 | 304.100699 | 1,363,490 | 1,043,584 | 319,906 | 7,641 | 401 |
| Fresh-task planning | 2 | 49.418567 | 162,743 | 131,712 | 31,031 | 1,660 | 0 |
| Total | 15 | 353.519266 | 1,526,233 | 1,175,296 | 350,937 | 9,301 | 401 |

The separate sanitized management ledger covers root and helper responses, including context compaction, through **14:38:18.142105 UTC on November 27**. Closing work after that cutoff is unmetered.

| Management phase | Responses | Input | Cached input | Uncached input | Output | Reasoning subset |
|---|---:|---:|---:|---:|---:|---:|
| Setup before first dispatch | 349 | 63,788,445 | 62,704,768 | 1,083,677 | 186,282 | 50,344 |
| Dispatch and iterative management | 889 | 179,635,115 | 178,159,360 | 1,475,755 | 691,884 | 419,501 |
| Total | 1,238 | 243,423,560 | 240,864,128 | 2,559,432 | 878,166 | 469,845 |

Free local tokens do not make the observed workflow faster or demonstrate net premium savings. The direct baseline is faster than these matched local worker paths. Several reviewed local paths used fewer paid output tokens but more uncached input than direct implementation before shared management costs. The total exploration includes failures and engineering work, and there is no measured up-front routing rule that chooses the best observed variant each time.

## Corrections and evidence

The first GPU qualification exposed stochastic device-selection incompatibility before task dispatch. The final GPU epoch used the supported host selector with native speculation controls. CPU used explicit singleton physical places 0–95 with all-thread affinity and live residency checks. PFX V7 fixed the blank spacer-column parser while preserving pinned row/order/value checks. A completion watcher startup race was fixed without rerunning tasks. An exact nine-record amendment corrects CPU file-custody labels and preserves raw records. The TU V5 control records the original-criteria false positive while preserving prior verdicts and paid usage.

Evidence binds exact candidate, source, behavioral, independent review and owner receipts. `FINAL-CLEANUP-PROOF.json` confirms 49 terminal native attempts, absence of the four captured owner/holder/server PIDs and no remaining owned process locks. Archive verification decoded all 21,187 selected files across 50 shards totaling 254,759,507 stored bytes. Layout SHA-256 `11bcc1151a583761818416c62f01bb4850d5daf91f66a50e8ef04ccb68397afd`. See [archive and verification](../../artifacts/analysis/27b-q38fn-full-tools-repeat-20261127/README.md).

The prepared TU V5 and generic-driving patches were applied after archive capture. The actual worktree passed all 43 targeted tests in 21.64 s: `tests/coordination/test_taskflow_tu_grader_isolation.py` and `tests/coordination/test_taskflow_opencode_derived.py`, with third-party pytest plugins disabled. The TU change adds the executable-launch refusal regression. Optional native reasoning-effort selection is restricted to the qualified thinking-on GPU27B template and preserves legacy defaults and exact-session resume identity. The verbatim generic instruction is retained as an explicit experimental recipe; passive warning presence is not promoted as a proven improvement.

Next: codex-a3b-pilot reuses this evidence for the next authorized dispatch; this repeat is closed with no queued runs.
