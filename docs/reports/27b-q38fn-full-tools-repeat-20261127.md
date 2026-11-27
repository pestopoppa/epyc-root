# 27B GPU / Q38FN CPU full-tools repeat — November 27

Status: running; interim document. Final quality, performance and accounting exports follow all terminal records and independent audits.

## What was repeated

The six original real-task fixtures plus the separate accurate-light W66 brief, each with thinking OFF and ON, on two models: 28 initial conditions, seven case/brief conditions per mode/model. This replays pinned task snapshots; it does not land duplicate work into today's backlog. Valid pinned main-only implementations and their paid usage were reused rather than rerun.

- GPU only: Qwen3.8-27B Q8_0 with DFlash2.
- CPU only: Qwen3.8-Flash-Next UD-IQ4_XS hybrid MoE with shared MTP (Q38FN).
- Both: C22 composite source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`, verified store binaries, four physical slots, 131072 context per slot. Production v10 was untouched.
- Full OpenCode2.2.5 twelve-tool surface: edit, execute, glob, grep, question, read, shell, skill, subagent, webfetch, websearch, write; CodeMode catalogue retained. No six-read or thirty-turn restriction. No extra explicit task-specific skill bundle was added, matching the pinned A3B briefs.
- Common sampler: temperature0.6, top_p0.95, top_k20, min_p0, repeat1, presence0, seed223355. Primary request cap32768 and condition allowance120000 generated tokens. Thinking ON uses the model's embedded native default xhigh; OFF disables thinking. This is not a matched reasoning-effort comparison against A3B's earlier medium profile.
- Original wall windows: 1800s GPU, 3600s CPU. All interrupted attempts remain censored outcomes against their own declared window. A late artifact is assessed separately from normal self-completion. No claim of CPU/GPU causality or intrinsic capability ceiling follows from these time windows.

Native qualification established ON/OFF reasoning control, preserved tool history, syntax-error repair through execute, read/write file custody, all four physical slots, real CPU/GPU residency and positive draft proposals/acceptance. Complete three-shard Q38FN identity is bound; the first shard is metadata, not the whole model.

## Acceptance and guidance

An artifact requires the original deterministic checks, exact-source independent review and explicit main adoption. Neither a worker completion message nor a checker return code alone counts as accepted. Review sees the original source, exact patch, original brief and actual consumed feedback; it sees no accepted implementation or other candidate.

One actionable CI correction is a same-session continuation with check output, not an independently implemented patch. Fresh paid planning retries are separate guided conditions; the coach supplies source-specific pointers but no code or final deliverable. Prior local cost remains charged. Registered-temperature and longer-wall supplements are reported separately rather than replacing original results.

At the interim checkpoint Q38FN MM and detailed W66 nonthinking are independently accepted normal completions without corrective guidance. Each consumed one final independent review. GPU PFX nonthinking is now accepted after one CI correction, one paid source diagnosis and an additional main arithmetic reminder; its original initial attempt remains censored. Two distinct source reviews were consumed for that guided branch. The complete per-condition table will replace this checkpoint after the remaining work closes.

## Defects repaired during this repeat

1. The first GPU qualification exposed C22's incompatibility between device DFlash selection and stochastic temperature0.6. No real GPU task had run. The second epoch uses the supported stochastic host selector (`LLAMA_DFLASH_DEV_SELECT=0`); native stochastic/speculation controls passed before dispatch. The aborted first epoch remains in evidence.
2. CPU OpenMP `cores` places could include SMT siblings outside the intended physical CPU set. Explicit singleton physical places0–95 and an all-thread affinity check replaced the overly broad placement and the mistaken leader-only check. Actual four-node shard residency and compute placements passed before dispatch.
3. The PFX independent parser incorrectly rejected a table containing a wholly blank spacer column. V7 permits empty spacers while retaining exact pinned source, event count/order, line/value and scope checks. Twenty-eight controls include the historical accepted answer, valid spacer positive and duplicate/missing/wrong-value negatives. The old verdict was withdrawn before its feedback reached the worker. The repaired parser then truthfully found46 versus41 rows in the GPU partial artifact; a bounded CI correction received that finding.
4. A completion watcher could miss a terminal file created between an owner snapshot and watcher startup. Explicit owner acknowledgments and content-deduplicated notifications now cover that race; a zero-model race control passed. No native work was rerun for this monitoring defect.
5. Nine CPU file-custody qualification records carried an erroneous hardcoded GPU instrumentation label. An exact-file amendment binds their unchanged raw records to the original CPU PID/birth proof. Offline projection corrects those nine labels while retaining the raw labels; 912 other shared receipt projections were identical at the validation checkpoint. No real-task assignment or model call changed.

Closed-budget artifacts also required an explicit grading adapter, because the original adapter admitted only normal completion. The separate adapter checks elapsed budget, drained reservations, scope, exact candidate bytes and reference custody; it does not rewrite the native interrupted status. Missing tests in CPU MM thinking and TU nonthinking are genuine incomplete deliverables, not grounds to weaken acceptance.

6. The final GPU TU source audit exposed an additional coverage gap despite old-checker PASS and paid reviewer ACCEPT: an `unshare` executable-launch permission error could be mistaken for namespace setup failure when the executable path contains `/proc/self/`. V5 adds this original-requirement diagnostic case. Eight contained controls preserve the pinned main-only positive and reject the exact GPU candidate and a synthetic broadened classifier. Main rejected the artifact, preserving both old verdicts and paid costs. This is an injected classification control, not a claim the normal worker launcher selects `/proc/self/exe`. The canonical checker/test patch is prepared for application after source-locked work and archive capture finish.

A separate CPU PFX thinking supplement carries its own budget-closed document and adopted paid diagnosis into a fresh session on slot0 or3. The original budget outcome remains censored. Prior charged allowance is debited; no prior reasoning or tool history is transferred, and slot cache warmth is unmeasured. This is explicitly a checkpoint/restart workflow variant, not an isolated guidance intervention.

The future owner-v3 race controls and scheduler controls are tested scratch improvements; active epoch02 and its frozen task runner were not silently replaced while jobs ran.

## Cost and timing interpretation

Local tokens are treated as free for the user's benefit question, but elapsed time and paid review, planning, management and harness engineering still count. Separate exports retain actual recorded input, cached and uncached input, output and reasoning subsets, including unsuccessful paid calls and context compactions. Management totals include the owned helper lineage and have an explicit cutoff; closing work after that cutoff is unmetered, not zero.

The accepted Q38FN MM result took2615.95s of worker wall time including tools; its source review took20.04s and29513 uncached input/456 output tokens. The reused main-only implementation took140.12s and13029 uncached input/2973 output. Detailed W66 took3393.22s plus28.48s review, whose usage was17774 uncached input/813 output. Output-token reduction alone is not net premium-token savings. Cache reuse differs between historical baseline and current review, and historical owner review is not isolated in the main-only implementation baseline.

The existing main-only baseline used729.09s across all seven case/brief conditions, including the first failed TU implementation and repair:174065 uncached input and20498 output tokens. It is seven productive conditions, not a denominator that can be multiplied by every exploratory local mode/profile and called a saved task. Post-hoc selection of the best local mode is not free routing knowledge.

Final exports will provide per-attempt and per-mode latency, upstream/delivered TTFT, native prefill and decode rates, per-stream and approximate aggregate phase rates, cache and paired speculative counters, concurrent resource samples and all failures/cancellations. Aggregated native intervals are approximate and include post-terminal drain where recorded; they are not task throughput. Native counters missing on interrupted requests remain unknown. Charged generation allowance is not observed generation; visible reasoning characters are not reasoning tokens.

## Evidence custody

Private branch: `codex/27b-q38fn-canary-20261127`. Protocol: [27b-q38fn-full-tools-repeat-20261127.md](../design/27b-q38fn-full-tools-repeat-20261127.md). Runtime source and raw receipts remain under `/mnt/raid0/llm/tmp/ws58-27b-q38fn-repeat-20261127`; final selected, compressed, content-verified evidence will be archived in this repository. Model binaries, private Codex rollouts and dependency trees are excluded. The exported manager usage contains counters and hashes, not conversation text.

Next: codex-a3b-pilot closes the remaining conditions and bounded corrections, audits candidates, publishes the final tables and evidence, and verifies owned-process cleanup.
